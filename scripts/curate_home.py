#!/usr/bin/env python3
"""Keep library index pages out of the home page's recent-update list."""

from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SEARCH_INDEX = DOCS / "search-index.json"
INDEX = DOCS / "index.html"

# These are navigation/index notes, not recent knowledge entries.
INDEX_NOTE_IDS = {
    "KB-000133",
    "KB-000134",
    "KB-000135",
    "KB-000136",
    "KB-000137",
}
MAX_PER_SECTION = 3


def recent_card(note: dict) -> str:
    title = html.escape(note.get("title", ""))
    summary = note.get("summary") or note.get("subtitle") or ""
    summary = summary.strip()
    if len(summary) > 220:
        summary = summary[:220].rstrip() + "…"
    summary = html.escape(summary)
    url = html.escape(note.get("url", ""), quote=True)
    kb_id = html.escape(note.get("kbId", ""))
    section = html.escape(note.get("sectionTitle", ""))
    raw_updated = note.get("updated", "")
    try:
        updated = datetime.fromisoformat(
            raw_updated.replace("Z", "+00:00")
        ).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y/%m/%d")
    except ValueError:
        updated = raw_updated[:10].replace("-", "/")
    updated = html.escape(updated)
    return (
        '<article class="recent-item">'
        f'<div class="recent-meta">{section} · {updated}'
        f'<span class="kb-id-badge" aria-label="站内唯一编号 {kb_id}">{kb_id}</span></div>'
        f'<h3><a href="{url}">{title}</a></h3>'
        f'<p>{summary}</p>'
        "</article>"
    )


def main() -> int:
    try:
        notes = json.loads(SEARCH_INDEX.read_text(encoding="utf-8"))
        notes = [note for note in notes if note.get("kbId") not in INDEX_NOTE_IDS]
        notes.sort(
            key=lambda note: (note.get("updated", ""), note.get("kbId", "")),
            reverse=True,
        )
        selected = []
        section_counts: Counter[str] = Counter()
        for note in notes:
            section_id = note.get("section", "")
            if section_counts[section_id] >= MAX_PER_SECTION:
                continue
            selected.append(note)
            section_counts[section_id] += 1
            if len(selected) == 10:
                break
        cards = "".join(recent_card(note) for note in selected)

        text = INDEX.read_text(encoding="utf-8")
        updated, count = re.subn(
            r'(<div class="recent-grid">)(.*?)(</div></section>)',
            lambda match: match.group(1) + cards + match.group(3),
            text,
            count=1,
            flags=re.DOTALL,
        )
        if count != 1:
            raise ValueError("home page recent-grid block was not found")
        if updated != text:
            INDEX.write_text(updated, encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Recent cards refreshed: {len(selected)}")
    print(f"Index notes excluded: {len(INDEX_NOTE_IDS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
