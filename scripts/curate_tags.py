#!/usr/bin/env python3
"""Add a small, reproducible tag set to notes that currently have none."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MANIFEST = DOCS / "site-manifest.json"
SEARCH_INDEX = DOCS / "search-index.json"

TAG_MAP: dict[str, list[str]] = {
    "KB-000057": ["Zotero", "Obsidian", "文献管理", "工作流"],
    "KB-000053": ["论文精读", "Deep-Phase", "凝聚体", "深度学习", "核仁"],
    "KB-000051": ["论文精读", "透明质酸", "组织力学", "再生", "纤维化"],
    "KB-000047": ["论文精读", "皮肤微生物组", "免疫检查点抑制剂", "皮肤毒性"],
    "KB-000045": ["论文精读", "OXGR1", "玫瑰痤疮", "血管舒张", "代谢物"],
    "KB-000042": ["论文精读", "铁死亡", "犬尿氨酸", "铁蛋白自噬", "肿瘤免疫"],
    "KB-000040": ["论文精读", "GREM1", "LEPR+骨骼细胞", "植入周纤维化", "BMP/WNT"],
    "KB-000032": ["论文精读", "放射性黏膜炎", "铁死亡", "成纤维细胞", "多胺"],
    "KB-000025": ["论文精读", "LEPR+骨骼细胞", "植入周纤维化", "ADGRF5", "骨形成"],
    "KB-000023": ["论文精读", "单细胞多组学", "图嵌入", "调控推断", "GLUE"],
    "KB-000011": ["NCBI", "SRA", "数据下载", "生物信息学"],
    "KB-000002": ["放射性颌骨骨坏死", "单细胞测序", "公共数据集", "GEO"],
    "KB-000001": ["scRNA-seq", "放射性口腔黏膜炎", "公共数据集", "GEO"],
}


def update_json_surfaces() -> list[dict]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed: list[dict] = []
    for section in manifest["sections"]:
        for note in section["notes"]:
            if note.get("tags"):
                continue
            kb_id = note.get("kbId") or note.get("kb_id")
            tags = TAG_MAP.get(kb_id)
            if tags:
                note["tags"] = tags
                changed.append(note)
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    search_notes = json.loads(SEARCH_INDEX.read_text(encoding="utf-8"))
    by_id = {
        (note.get("kbId") or note.get("kb_id")): note
        for note in changed
    }
    for note in search_notes:
        replacement = by_id.get(note.get("kbId"))
        if replacement:
            note["tags"] = replacement["tags"]
    SEARCH_INDEX.write_text(
        json.dumps(search_notes, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return changed


def tag_html(tag: str, class_name: str) -> str:
    return f'<span class="{class_name}">{html.escape(tag)}</span>'


def update_note_pages(changed: list[dict]) -> int:
    updated = 0
    for note in changed:
        page = DOCS / note["url"]
        text = page.read_text(encoding="utf-8")
        if '<div class="tags">' in text:
            continue
        match = re.search(r'<div class="meta-badges">.*?</div>', text, re.DOTALL)
        if not match:
            continue
        tags = "".join(tag_html(tag, "tag") for tag in note["tags"])
        block = f'\n<div class="tags">{tags}</div>'
        text = text[: match.end()] + block + text[match.end() :]
        page.write_text(text, encoding="utf-8")
        updated += 1
    return updated


def update_section_cards(changed: list[dict]) -> int:
    by_basename = {Path(note["url"]).name: note["tags"] for note in changed}
    updated = 0
    for page in sorted(DOCS.glob("*/*.html")):
        text = page.read_text(encoding="utf-8")
        if 'class="kb-note-card"' not in text:
            continue
        original = text

        def replace_card(match: re.Match[str]) -> str:
            nonlocal updated
            article = match.group(0)
            for basename, tags in by_basename.items():
                if f'href="notes/{basename}"' not in article:
                    continue
                if '<div class="tag-row">' in article:
                    return article
                tag_row = '<div class="tag-row">' + "".join(
                    tag_html(tag, "tag-pill") for tag in tags
                ) + "</div>"
                article = article.replace('<a class="open-note"', tag_row + '<a class="open-note"', 1)
                article = re.sub(
                    r'data-search="([^"]*)"',
                    lambda m: f'data-search="{m.group(1)} {" ".join(tags)}"',
                    article,
                    count=1,
                )
                updated += 1
                return article
            return article

        text = re.sub(
            r'<article class="kb-note-card".*?</article>',
            replace_card,
            text,
            flags=re.DOTALL,
        )
        if text != original:
            page.write_text(text, encoding="utf-8")
    return updated


def main() -> int:
    try:
        changed = update_json_surfaces()
        note_pages = update_note_pages(changed)
        cards = update_section_cards(changed)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Notes tagged: {len(changed)}")
    print(f"Note pages updated: {note_pages}")
    print(f"Section cards updated: {cards}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
