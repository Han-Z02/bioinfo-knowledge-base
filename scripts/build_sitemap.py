#!/usr/bin/env python3
"""Add canonical URLs and regenerate the public sitemap."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET


BASE_URL = "https://han-z02.github.io/bioinfo-knowledge-base"
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CANONICAL_RE = re.compile(r'<link rel="canonical" href="[^"]*">')


def public_url(page: Path) -> str:
    relative = page.relative_to(DOCS).as_posix()
    if relative == "index.html":
        return BASE_URL + "/"
    if relative.endswith("/index.html"):
        return f"{BASE_URL}/{relative[:-len('index.html')]}"
    return f"{BASE_URL}/{relative}"


def add_canonical(page: Path, url: str) -> None:
    text = page.read_text(encoding="utf-8")
    text = CANONICAL_RE.sub("", text)
    tag = f'<link rel="canonical" href="{url}">'
    if "</head>" not in text:
        raise ValueError(f"{page}: missing </head>")
    text = text.replace("</head>", tag + "</head>", 1)
    page.write_text(text, encoding="utf-8")


def main() -> None:
    pages = sorted(
        page
        for page in DOCS.rglob("*.html")
        if page.name != "404.html"
    )
    urls = []
    for page in pages:
        url = public_url(page)
        urls.append(url)
        add_canonical(page, url)

    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    urlset = ET.Element(f"{{{namespace}}}urlset")
    for url in urls:
        item = ET.SubElement(urlset, f"{{{namespace}}}url")
        ET.SubElement(item, f"{{{namespace}}}loc").text = url
    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")
    tree.write(DOCS / "sitemap.xml", encoding="utf-8", xml_declaration=True)

    robots = DOCS / "robots.txt"
    lines = [
        line
        for line in robots.read_text(encoding="utf-8").splitlines()
        if not line.lower().startswith("sitemap:")
    ]
    while lines and not lines[-1].strip():
        lines.pop()
    lines.extend(["", f"Sitemap: {BASE_URL}/sitemap.xml"])
    robots.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Updated canonical URLs: {len(pages)} pages")
    print(f"Wrote {DOCS / 'sitemap.xml'} with {len(urls)} URLs")


if __name__ == "__main__":
    main()
