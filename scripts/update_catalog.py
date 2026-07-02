#!/usr/bin/env python3
import os
import zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom

BASE_URL = os.environ.get("PAGES_URL", "").rstrip("/")


def epub_metadata(epub_path):
    """Extract title from EPUB OPF metadata (stdlib only, no deps)."""
    try:
        with zipfile.ZipFile(epub_path) as z:
            container = ET.fromstring(z.read("META-INF/container.xml"))
            ns_c = "urn:oasis:names:tc:opendocument:xmlns:container"
            opf_path = container.find(f".//{{{ns_c}}}rootfile").get("full-path")
            opf = ET.fromstring(z.read(opf_path))
            ns_dc = "http://purl.org/dc/elements/1.1/"
            title_el = opf.find(f".//{{{ns_dc}}}title")
            return title_el.text if title_el is not None else None
    except Exception:
        return None


def load_url_index():
    """filename → url mapping from index.tsv (articles fetched from URLs)."""
    index = {}
    if os.path.exists("library/index.tsv"):
        with open("library/index.tsv", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 3:
                    index[parts[0]] = {"url": parts[2], "date": parts[3] if len(parts) >= 4 else ""}
    return index


def collect_entries():
    url_index = load_url_index()
    entries = []

    for filename in os.listdir("library"):
        if not filename.endswith(".epub"):
            continue

        path = os.path.join("library", filename)

        # Title: from EPUB metadata, fallback to filename
        title = epub_metadata(path)
        if not title:
            title = filename[11:].replace("-", " ").replace(".epub", "").strip()
            title = title.title() if title else filename

        # Date: from index.tsv, then filename prefix, then file mtime
        meta = url_index.get(filename, {})
        date = meta.get("date", "")
        if not date:
            if len(filename) >= 10 and filename[4] == "-" and filename[7] == "-":
                date = filename[:10] + "T00:00:00Z"
            else:
                mtime = os.stat(path).st_mtime
                date = datetime.fromtimestamp(mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        entries.append({
            "filename": filename,
            "title": title,
            "url": meta.get("url", ""),
            "date": date,
        })

    entries.sort(key=lambda x: x["date"], reverse=True)
    return entries


def generate_opds(entries):
    ATOM = "http://www.w3.org/2005/Atom"
    OPDS = "http://opds-spec.org/2010/catalog"

    feed = Element("feed")
    feed.set("xmlns", ATOM)
    feed.set("xmlns:opds", OPDS)

    SubElement(feed, "title").text = "Reading Pipeline"
    SubElement(feed, "id").text = "urn:reading-pipeline:catalog"
    SubElement(feed, "updated").text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    self_link = SubElement(feed, "link")
    self_link.set("rel", "self")
    self_link.set("href", f"{BASE_URL}/catalog.xml")
    self_link.set("type", "application/atom+xml;profile=opds-catalog;kind=navigation")

    for e in entries:
        entry = SubElement(feed, "entry")
        SubElement(entry, "title").text = e["title"]
        SubElement(entry, "id").text = f"urn:reading-pipeline:{e['filename']}"
        SubElement(entry, "updated").text = e["date"][:19] + "Z"
        if e["url"]:
            SubElement(entry, "summary").text = e["url"]

        link = SubElement(entry, "link")
        link.set("rel", "http://opds-spec.org/acquisition")
        link.set("href", f"{BASE_URL}/library/{e['filename']}")
        link.set("type", "application/epub+zip")

    raw = tostring(feed, encoding="unicode")
    dom = xml.dom.minidom.parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw}')
    return dom.toprettyxml(indent="  ", encoding=None).replace(
        '<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>'
    )


def main():
    entries = collect_entries()
    catalog = generate_opds(entries)
    with open("catalog.xml", "w", encoding="utf-8") as f:
        f.write(catalog)
    print(f"Catalog updated: {len(entries)} entry/entries")


if __name__ == "__main__":
    main()
