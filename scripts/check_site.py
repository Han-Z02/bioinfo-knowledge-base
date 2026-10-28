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
SEARCH_INDEX = DOCS / "search-index.json"
MAX_SEARCH_HTML_BYTES = 300_000
MAX_SEARCH_INDEX_BYTES = 2_000_000
INDEX_NOTE_IDS = {
    "KB-000133",
    "KB-000134",
    "KB-000135",
    "KB-000136",
    "KB-000137",
}
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
    manifest_url_strings = {note["url"] for note in notes}
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
    untagged = [
        note.get("kb_id") or note.get("kbId")
        for note in notes
        if not note.get("tags")
    ]
    if untagged:
        warnings.append(f"untagged notes ({len(untagged)}): {', '.join(untagged[:8])}")
    home_text = (DOCS / "index.html").read_text(encoding="utf-8")
    recent_match = re.search(
        r'<div class="recent-grid">(.*?)</div></section>',
        home_text,
        re.DOTALL,
    )
    if not recent_match:
        errors.append("index.html: recent-grid block is missing")
    else:
        recent = recent_match.group(1)
        if recent.count('<article class="recent-item">') != 10:
            warnings.append("index.html: recent-update list does not contain 10 cards")
        leaked_index_ids = sorted(kb_id for kb_id in INDEX_NOTE_IDS if kb_id in recent)
        if leaked_index_ids:
            errors.append(
                "index.html: library index notes remain in recent updates: "
                + ", ".join(leaked_index_ids)
            )

    search_file = DOCS / "search.html"
    search_text = search_file.read_text(encoding="utf-8")
    search_html_bytes = len(search_text.encode("utf-8"))
    if search_html_bytes > MAX_SEARCH_HTML_BYTES:
        errors.append(
            f"search.html: {search_html_bytes:,} B exceeds "
            f"{MAX_SEARCH_HTML_BYTES:,} B; run optimize_site.py"
        )
    if not re.search(r'<script id="kb-search-data"[^>]*data-src="search-index\.json"', search_text):
        errors.append("search.html: external search-index.json reference is missing")
    inline_match = re.search(
        r'<script id="kb-search-data" type="application/json">(.*?)</script>',
        search_text,
        re.DOTALL,
    )
    if inline_match and len(inline_match.group(1).strip()) > 1000:
        errors.append("search.html: inline search payload remains; run optimize_site.py")

    search_notes = None
    search_payload = ""
    if not SEARCH_INDEX.is_file():
        errors.append("docs/search-index.json is missing")
    else:
        search_index_text = SEARCH_INDEX.read_text(encoding="utf-8")
        index_bytes = len(search_index_text.encode("utf-8"))
        if index_bytes > MAX_SEARCH_INDEX_BYTES:
            errors.append(
                f"search-index.json: {index_bytes:,} B exceeds "
                f"{MAX_SEARCH_INDEX_BYTES:,} B"
            )
        try:
            search_notes = json.loads(search_index_text)
        except json.JSONDecodeError as exc:
            errors.append(f"search-index.json: invalid JSON: {exc}")
        else:
            search_payload = json.dumps(search_notes, ensure_ascii=False)
            if not isinstance(search_notes, list):
                errors.append("search-index.json: payload must be a JSON array")
                search_notes = None
            elif len(search_notes) != len(notes):
                errors.append(
                    f"search notes={len(search_notes)} but manifest notes={len(notes)}"
                )
            elif len({item["url"] for item in search_notes}) != len(search_notes):
                errors.append("search-index.json: duplicate note URLs")
            elif {item["url"] for item in search_notes} != manifest_url_strings:
                errors.append("search-index.json: URLs do not match the manifest")
            if EMAIL_WITH_PASSWORD.search(search_payload):
                errors.append("search-index.json: email/password pair remains")
            if CHINESE_MOBILE.search(search_payload):
                errors.append("search-index.json: Chinese mobile number remains")
            if PUBLIC_IP_URL.search(search_payload):
                errors.append("search-index.json: literal public IP URL remains")
            if SECRET_TOKEN.search(search_payload):
                errors.append("search-index.json: high-confidence secret token remains")
            if any(path in search_payload for path in LOCAL_USER_PATHS):
                errors.append("search-index.json: local user path remains")
    if f"在 {len(notes)} 篇笔记" not in search_text:
        errors.append(f"search.html: note-count copy does not equal {len(notes)}")

    local_refs = 0
    asset_version = hashlib.sha256(
        (DOCS / "assets" / "site.css").read_bytes()
        + (DOCS / "assets" / "site.js").read_bytes()
    ).hexdigest()[:10]
    for page in pages:
        text = page.read_text(encoding="utf-8")
        images = re.findall(r"<img\b[^>]*>", text, flags=re.IGNORECASE)
        if len(images) > 1 and any("loading=" not in tag for tag in images[1:]):
            warnings.append(f"{page.relative_to(ROOT)}: deferred images lack loading= attributes")
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
