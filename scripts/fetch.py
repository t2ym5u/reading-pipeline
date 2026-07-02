#!/usr/bin/env python3
import sys
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse
import trafilatura


def slugify(text):
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", text)[:60].strip("-")


def fetch_article(url):
    raw = trafilatura.fetch_url(url)
    if not raw:
        sys.exit(f"Cannot fetch: {url}")

    meta = trafilatura.extract_metadata(raw)
    title = meta.title if (meta and meta.title) else urlparse(url).netloc

    content_html = trafilatura.extract(
        raw, output_format="html", include_images=False, no_fallback=False
    )
    if not content_html:
        sys.exit("Cannot extract article content")

    return title, content_html


def make_epub(title, content_html, url, output_path):
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>{title}</title></head>
<body>
<h1>{title}</h1>
<p><small>Source : <a href="{url}">{url}</a></small></p>
{content_html}
</body>
</html>"""

    with tempfile.NamedTemporaryFile(
        suffix=".html", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(html)
        tmp = f.name

    try:
        subprocess.run(
            ["pandoc", tmp, "-o", output_path, "--metadata", f"title={title}"],
            check=True,
        )
    finally:
        os.unlink(tmp)


def set_output(name, value):
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{name}={value}\n")


def main():
    url = sys.argv[1].strip()
    os.makedirs("library", exist_ok=True)

    print(f"Fetching: {url}")
    title, content_html = fetch_article(url)

    date = datetime.now(timezone.utc)
    slug = slugify(title) or slugify(urlparse(url).path)
    filename = f"{date.strftime('%Y-%m-%d')}-{slug}.epub"
    path = os.path.join("library", filename)

    print(f"Converting to EPUB: {title}")
    make_epub(title, content_html, url, path)
    print(f"Saved: {path}")

    with open("library/index.tsv", "a", encoding="utf-8") as f:
        f.write(f"{filename}\t{title}\t{url}\t{date.isoformat()}\n")

    set_output("epub_filename", filename)
    set_output("epub_title", title)


if __name__ == "__main__":
    main()
