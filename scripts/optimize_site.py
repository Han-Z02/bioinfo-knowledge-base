#!/usr/bin/env python3
"""Post-process generated docs for lighter page loads and stable asset versions."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SEARCH_PAGE = DOCS / "search.html"
SEARCH_INDEX = DOCS / "search-index.json"
MANIFEST = DOCS / "site-manifest.json"

SEARCH_INLINE_RE = re.compile(
    r'<script id="kb-search-data" type="application/json">(.*?)</script>',
    re.DOTALL,
)
SEARCH_EXTERNAL_RE = re.compile(
    r'<script id="kb-search-data"[^>]*data-src="search-index\.json"[^>]*>',
    re.IGNORECASE,
)
SEARCH_EXTERNAL_TAG = (
    '<script id="kb-search-data" type="application/json" '
    'data-src="search-index.json"></script>'
)
IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
ASSET_RE = re.compile(r'((?:\.\./)*assets/site\.(?:css|js))\?v=[^"\'<>\s]+')


def write_search_index() -> tuple[bool, int]:
    """Move the generated inline search payload into a fetchable JSON file."""
    text = SEARCH_PAGE.read_text(encoding="utf-8")
    match = SEARCH_INLINE_RE.search(text)
    changed = False

    if match:
        payload_text = match.group(1).strip()
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"search.html: invalid inline search JSON: {exc}") from exc
        if not isinstance(payload, list):
            raise ValueError("search.html: search payload must be a JSON array")
        SEARCH_INDEX.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        text = text[: match.start()] + SEARCH_EXTERNAL_TAG + text[match.end() :]
        changed = True
    elif not SEARCH_EXTERNAL_RE.search(text):
        raise ValueError("search.html: kb-search-data payload is missing")
    elif not SEARCH_INDEX.is_file():
        raise ValueError("search-index.json is missing; rebuild the inline search payload first")

    if changed:
        SEARCH_PAGE.write_text(text, encoding="utf-8")
    return changed, SEARCH_INDEX.stat().st_size


def add_lazy_loading(text: str) -> tuple[str, int]:
    """Keep the first image eager, defer the rest, and decode asynchronously."""
    matches = list(IMG_RE.finditer(text))
    if not matches:
        return text, 0

    additions: list[tuple[int, int, str]] = []
    changed = 0
    for index, match in enumerate(matches):
        tag = match.group(0)
        extra: list[str] = []
        if "loading=" not in tag:
            extra.append('loading="eager"' if index == 0 else 'loading="lazy"')
        if "decoding=" not in tag:
            extra.append('decoding="async"')
        if index == 0 and "fetchpriority=" not in tag:
            extra.append('fetchpriority="high"')
        if extra:
            replacement = tag[:-1].rstrip() + " " + " ".join(extra) + ">"
            additions.append((match.start(), match.end(), replacement))
            changed += 1

    for start, end, replacement in reversed(additions):
        text = text[:start] + replacement + text[end:]
    return text, changed


def update_lazy_loading() -> int:
    changed = 0
    for page in sorted(DOCS.rglob("*.html")):
        if page == SEARCH_PAGE:
            continue
        text = page.read_text(encoding="utf-8")
        updated, count = add_lazy_loading(text)
        if count:
            page.write_text(updated, encoding="utf-8")
            changed += count
    return changed


def asset_version() -> str:
    return hashlib.sha256(
        (DOCS / "assets" / "site.css").read_bytes()
        + (DOCS / "assets" / "site.js").read_bytes()
    ).hexdigest()[:10]


def update_asset_versions() -> tuple[int, str]:
    version = asset_version()
    changed = 0
    for page in sorted(DOCS.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        updated = ASSET_RE.sub(lambda match: f"{match.group(1)}?v={version}", text)
        if updated != text:
            page.write_text(updated, encoding="utf-8")
            changed += 1
    return changed, version


def sync_footer_time() -> bool:
    """Use the manifest timestamp as the single displayed generation time."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    generated_at = manifest.get("generatedAt")
    if not generated_at:
        return False
    stamp = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    stamp = stamp.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y/%m/%d %H:%M:%S")
    index = DOCS / "index.html"
    text = index.read_text(encoding="utf-8")
    updated = re.sub(
        r"(生成时间：)[^<]+?(?= · 公开版维护：)",
        lambda match: match.group(1) + stamp,
        text,
        count=1,
    )
    if updated == text:
        return False
    index.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    try:
        search_changed, search_bytes = write_search_index()
        lazy_images = update_lazy_loading()
        asset_pages, version = update_asset_versions()
        footer_changed = sync_footer_time()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Search index: {'updated' if search_changed else 'already external'} ({search_bytes:,} B)")
    print(f"Lazy images: {lazy_images} tag(s) updated")
    print(f"Asset version: {version} ({asset_pages} page(s) updated)")
    print(f"Footer timestamp: {'updated' if footer_changed else 'already current'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
