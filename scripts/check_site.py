#!/usr/bin/env python3
"""Validate content counts, local links, public-mode cleanup, and SEO files."""

from __future__ import annotations

import json
import hashlib
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET


BASE_URL = "https://han-z02.github.io/bioinfo-knowledge-base"
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MANIFEST = DOCS / "site-manifest.json"
PLACEHOLDER_TITLES = {"未命名笔记", "中文标题", "文献汇报"}
CHINESE_MOBILE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
PUBLIC_IP_URL = re.compile(
    r"https?://(?!localhost\b|127\.0\.0\.1\b)(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?"
)
EMAIL_WITH_PASSWORD = re.compile(
    r"[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}.{0,60}(?:密码|password)",
    re.IGNORECASE | re.DOTALL,
)
SECRET_TOKEN = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b"
)
LOCAL_USER_PATHS = (
    "/home/hanze/",
    "/Users/HAN/",
    "/mnt/c/Users/HAN/",
)


class Refs(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for key in ("href", "src"):
            value = values.get(key)
            if value:
                self.refs.append(value)


def public_url(page: Path) -> str:
    relative = page.relative_to(DOCS).as_posix()
    if relative == "index.html":
        return BASE_URL + "/"
    if relative.endswith("/index.html"):
        return f"{BASE_URL}/{relative[:-len('index.html')]}"
    return f"{BASE_URL}/{relative}"


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    pages = sorted(DOCS.rglob("*.html"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    notes = []
    for section in manifest["sections"]:
        if section["count"] != len(section["notes"]):
            errors.append(
                f"{section['id']}: count={section['count']} but notes={len(section['notes'])}"
            )
        subsection_counts = Counter(note["subsection"] for note in section["notes"])
        for subsection in section["subsections"]:
            if subsection["count"] != subsection_counts[subsection["id"]]:
                errors.append(
                    f"{section['id']}/{subsection['id']}: count={subsection['count']} "
                    f"but notes={subsection_counts[subsection['id']]}"
                )
        notes.extend(section["notes"])

    note_pages = sorted(DOCS.glob("*/notes/*.html"))
    if len(notes) != len(note_pages):
        errors.append(f"manifest notes={len(notes)} but note pages={len(note_pages)}")
    manifest_urls = {DOCS / note["url"] for note in notes}
    if manifest_urls != set(note_pages):
        missing = sorted(str(page.relative_to(DOCS)) for page in manifest_urls - set(note_pages))
        orphaned = sorted(str(page.relative_to(DOCS)) for page in set(note_pages) - manifest_urls)
        errors.append(
            f"manifest/page mismatch: missing={missing[:3]}, orphaned={orphaned[:3]}"
        )

    titles = Counter(note["title"].strip() for note in notes)
    for title in sorted(PLACEHOLDER_TITLES):
        if titles[title]:
            errors.append(f"placeholder title remains: {title}")
    for title, count in titles.items():
        if count > 1:
            warnings.append(f"duplicate title ({count}): {title[:100]}")

    search_file = DOCS / "search.html"
    search_text = search_file.read_text(encoding="utf-8")
    match = re.search(
        r'<script id="kb-search-data" type="application/json">(.*?)</script>',
        search_text,
        re.DOTALL,
    )
    if not match:
        errors.append("search.html: kb-search-data is missing")
    else:
        try:
            search_notes = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            errors.append(f"search.html: invalid search JSON: {exc}")
        else:
            if len(search_notes) != len(notes):
                errors.append(
                    f"search notes={len(search_notes)} but manifest notes={len(notes)}"
                )
            if len({item["url"] for item in search_notes}) != len(search_notes):
                errors.append("search.html: duplicate note URLs")
            search_payload = json.dumps(search_notes, ensure_ascii=False)
            if EMAIL_WITH_PASSWORD.search(search_payload):
                errors.append("search.html: email/password pair remains in search payload")
    if f"在 {len(notes)} 篇笔记" not in search_text:
        errors.append(f"search.html: note-count copy does not equal {len(notes)}")

    local_refs = 0
    asset_version = hashlib.sha256(
        (DOCS / "assets" / "site.css").read_bytes()
        + (DOCS / "assets" / "site.js").read_bytes()
    ).hexdigest()[:10]
    for page in pages:
        text = page.read_text(encoding="utf-8")
        if page.name != "404.html":
            canonical = f'<link rel="canonical" href="{public_url(page)}">'
            if text.count(canonical) != 1:
                errors.append(f"{page.relative_to(ROOT)}: canonical missing or repeated")

        parser = Refs()
        parser.feed(text)
        for ref in parser.refs:
            parsed = urlparse(ref)
            if (
                not ref
                or ref.startswith(("#", "mailto:", "tel:", "javascript:", "data:"))
                or parsed.scheme
                or parsed.netloc
            ):
                continue
            local_refs += 1
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.exists():
                errors.append(f"{page.relative_to(ROOT)}: broken ref {ref}")
            if parsed.path.endswith(("assets/site.css", "assets/site.js")):
                versions = re.findall(r"(?:^|[?&])v=([^&]+)", parsed.query)
                if versions != [asset_version]:
                    errors.append(
                        f"{page.relative_to(ROOT)}: stale asset version for {ref}"
                    )

        visible = re.sub(
            r"<script\b.*?</script>|<style\b.*?</style>",
            " ",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        visible = re.sub(r"<[^>]+>", " ", visible)
        if CHINESE_MOBILE.search(text):
            errors.append(f"{page.relative_to(ROOT)}: Chinese mobile number remains")
        if PUBLIC_IP_URL.search(text):
            errors.append(f"{page.relative_to(ROOT)}: literal public IP URL remains")
        if EMAIL_WITH_PASSWORD.search(visible):
            errors.append(f"{page.relative_to(ROOT)}: email/password pair remains")
        if SECRET_TOKEN.search(text):
            errors.append(f"{page.relative_to(ROOT)}: high-confidence secret token remains")
        if any(path in text for path in LOCAL_USER_PATHS):
            errors.append(f"{page.relative_to(ROOT)}: local user path remains")

    cleanup_markers = (
        'id="site-lock"',
        "kb-unlock-key",
        "重新打开时仍需解锁",
        'id="kb-payload"',
        "noindex",
        "nofollow",
    )
    for marker in cleanup_markers:
        matches = [page for page in pages if marker in page.read_text(encoding="utf-8")]
        if matches:
            errors.append(f"public-mode marker {marker!r} remains in {len(matches)} pages")

    sitemap_file = DOCS / "sitemap.xml"
    if not sitemap_file.is_file():
        errors.append("docs/sitemap.xml is missing")
    else:
        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        root = ET.parse(sitemap_file).getroot()
        sitemap_urls = {
            node.text
            for node in root.findall("s:url/s:loc", namespace)
            if node.text
        }
        expected_urls = {public_url(page) for page in pages if page.name != "404.html"}
        if sitemap_urls != expected_urls:
            missing = sorted(expected_urls - sitemap_urls)
            extra = sorted(sitemap_urls - expected_urls)
            errors.append(
                f"sitemap mismatch: missing={len(missing)}, extra={len(extra)}"
            )

    robots = (DOCS / "robots.txt").read_text(encoding="utf-8")
    if f"Sitemap: {BASE_URL}/sitemap.xml" not in robots:
        errors.append("robots.txt: sitemap directive is missing")

    print(f"HTML pages: {len(pages)}")
    print(f"Published notes: {len(notes)}")
    print(f"Local refs checked: {local_refs}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"\nFAILED: {len(errors)} error(s)")
        return 1
    print("\nOK: public site checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
