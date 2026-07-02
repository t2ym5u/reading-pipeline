#!/usr/bin/env python3
import os
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom

BASE_URL = os.environ.get("PAGES_URL", "").rstrip("/")


def load_entries():
    index_path = "library/index.tsv"
    if not os.path.exists(index_path):
        return []

    entries = []
    with open(index_path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                entries.append(
                    {
                        "filename": parts[0],
                        "title": parts[1],
                        "url": parts[2],
                        "date": parts[3],
                    }
                )

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
    SubElement(feed, "updated").text = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    self_link = SubElement(feed, "link")
    self_link.set("rel", "self")
    self_link.set("href", f"{BASE_URL}/catalog.xml")
    self_link.set("type", "application/atom+xml;profile=opds-catalog;kind=navigation")

    for e in entries:
        entry = SubElement(feed, "entry")
        SubElement(entry, "title").text = e["title"]
        SubElement(entry, "id").text = f"urn:reading-pipeline:{e['filename']}"
        SubElement(entry, "updated").text = e["date"][:19] + "Z"
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
    entries = load_entries()
    catalog = generate_opds(entries)
    with open("catalog.xml", "w", encoding="utf-8") as f:
        f.write(catalog)
    print(f"Catalog updated: {len(entries)} article(s)")


if __name__ == "__main__":
    main()
