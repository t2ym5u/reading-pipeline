#!/usr/bin/env python3
import os
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom

BASE_URL    = os.environ.get("PAGES_URL", "").rstrip("/")
ENCRYPT_KEY = os.environ.get("EPUB_ENCRYPT_KEY", "")


# ── Crypto helpers ────────────────────────────────────────────────────────────

def _run_openssl(args):
    return subprocess.run(["openssl"] + args, capture_output=True).returncode == 0

def _encrypt(src, dst):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as kf:
        kf.write(ENCRYPT_KEY)
        kf_path = kf.name
    try:
        return _run_openssl([
            "enc", "-aes-256-cbc", "-pbkdf2",
            "-pass", f"file:{kf_path}", "-in", src, "-out", dst,
        ])
    finally:
        os.unlink(kf_path)

def _decrypt(src, dst):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as kf:
        kf.write(ENCRYPT_KEY)
        kf_path = kf.name
    try:
        return _run_openssl([
            "enc", "-aes-256-cbc", "-pbkdf2", "-d",
            "-pass", f"file:{kf_path}", "-in", src, "-out", dst,
        ])
    finally:
        os.unlink(kf_path)


# ── EPUB metadata ─────────────────────────────────────────────────────────────

def epub_title(epub_path):
    try:
        with zipfile.ZipFile(epub_path) as z:
            container = ET.fromstring(z.read("META-INF/container.xml"))
            ns_c = "urn:oasis:names:tc:opendocument:xmlns:container"
            opf_path = container.find(f".//{{{ns_c}}}rootfile").get("full-path")
            opf = ET.fromstring(z.read(opf_path))
            el = opf.find(f".//{{{'{http://purl.org/dc/elements/1.1/}'}}title")
            return el.text if el is not None else None
    except Exception:
        return None


# ── Index (index.tsv / index.tsv.enc) ────────────────────────────────────────

def load_index():
    """Return dict: filename → {title, url, date}. Handles encrypted + plaintext."""
    plain  = "library/index.tsv"
    enc    = plain + ".enc"
    result = {}

    # Decrypt existing encrypted index
    if ENCRYPT_KEY and os.path.exists(enc):
        tmp = plain + ".old"
        if _decrypt(enc, tmp):
            result.update(_read_tsv(tmp))
            os.remove(tmp)

    # Merge any new plaintext entries (written by fetch.py this run)
    if os.path.exists(plain):
        result.update(_read_tsv(plain))

    return result

def _read_tsv(path):
    entries = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                entries[parts[0]] = {
                    "title": parts[1],
                    "url":   parts[2],
                    "date":  parts[3] if len(parts) >= 4 else "",
                }
    return entries

def save_index(entries):
    """Write index.tsv and encrypt it (replacing plaintext + old .enc)."""
    plain = "library/index.tsv"
    enc   = plain + ".enc"

    with open(plain, "w", encoding="utf-8") as f:
        for fname, meta in sorted(entries.items(), key=lambda x: x[1].get("date", "")):
            f.write(f"{fname}\t{meta['title']}\t{meta['url']}\t{meta['date']}\n")

    if ENCRYPT_KEY:
        if _encrypt(plain, enc):
            os.remove(plain)


# ── Catalog entries ───────────────────────────────────────────────────────────

def collect_entries(index):
    entries = []
    for filename in os.listdir("library"):
        if not filename.endswith(".epub"):
            continue

        path = os.path.join("library", filename)
        meta = index.get(filename, {})

        # Title: from index, then EPUB metadata, then filename
        title = (
            meta.get("title")
            or epub_title(path)
            or filename.replace(".epub", "")
        )

        # Date: from index, then file mtime
        date = meta.get("date", "")
        if not date:
            mtime = os.stat(path).st_mtime
            date = datetime.fromtimestamp(mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        entries.append({
            "filename": filename,
            "title":    title,
            "url":      meta.get("url", ""),
            "date":     date,
        })

    entries.sort(key=lambda x: x["date"], reverse=True)
    return entries


# ── OPDS XML ──────────────────────────────────────────────────────────────────

def generate_opds(entries):
    ATOM = "http://www.w3.org/2005/Atom"
    OPDS = "http://opds-spec.org/2010/catalog"

    feed = Element("feed")
    feed.set("xmlns", ATOM)
    feed.set("xmlns:opds", OPDS)

    SubElement(feed, "title").text = "Reading Pipeline"
    SubElement(feed, "id").text    = "urn:reading-pipeline:catalog"
    SubElement(feed, "updated").text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    self_link = SubElement(feed, "link")
    catalog_filename = "catalog.xml.enc" if ENCRYPT_KEY else "catalog.xml"
    self_link.set("rel",  "self")
    self_link.set("href", f"{BASE_URL}/{catalog_filename}")
    self_link.set("type", "application/atom+xml;profile=opds-catalog;kind=navigation")

    for e in entries:
        entry = SubElement(feed, "entry")
        SubElement(entry, "title").text   = e["title"]
        SubElement(entry, "id").text      = f"urn:reading-pipeline:{e['filename']}"
        SubElement(entry, "updated").text = e["date"][:19] + "Z"
        if e["url"]:
            SubElement(entry, "summary").text = e["url"]

        link = SubElement(entry, "link")
        link.set("rel",  "http://opds-spec.org/acquisition")
        link.set("href", f"{BASE_URL}/library/{e['filename']}")
        link.set("type", "application/epub+zip")

    raw = tostring(feed, encoding="unicode")
    dom = xml.dom.minidom.parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw}')
    return dom.toprettyxml(indent="  ", encoding=None).replace(
        '<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>'
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    index   = load_index()
    entries = collect_entries(index)

    # Rebuild index from current library state (adds any new entries)
    new_index = {e["filename"]: {"title": e["title"], "url": e["url"], "date": e["date"]}
                 for e in entries}
    save_index(new_index)

    # Write catalog
    catalog = generate_opds(entries)
    with open("catalog.xml", "w", encoding="utf-8") as f:
        f.write(catalog)

    if ENCRYPT_KEY:
        if _encrypt("catalog.xml", "catalog.xml.enc"):
            os.remove("catalog.xml")
        print(f"Catalog encrypted: {len(entries)} entry/entries → catalog.xml.enc")
    else:
        print(f"Catalog updated: {len(entries)} entry/entries → catalog.xml")


if __name__ == "__main__":
    main()
