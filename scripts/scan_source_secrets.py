#!/usr/bin/env python3
"""Scan a local wiki/source tree for patterns that must not be published."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PATTERNS = {
    "cn_mobile": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "public_ip_url": re.compile(
        r"https?://(?!localhost\b|127\.0\.0\.1\b)(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?"
    ),
    "email_password": re.compile(
        r"[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}.{0,80}(?:密码|password)",
        re.IGNORECASE | re.DOTALL,
    ),
    "secret_token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
        r"sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b"
    ),
    "local_user_path": re.compile(
        r"/home/hanze/|/Users/HAN/|/mnt/c/Users/HAN/"
    ),
}
TEXT_SUFFIXES = {
    ".md",
    ".markdown",
    ".txt",
    ".html",
    ".htm",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".js",
    ".ts",
    ".py",
    ".r",
    ".sh",
    ".csv",
    ".tsv",
}


def iter_text_files(root: Path, max_bytes: int):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            if path.stat().st_size > max_bytes:
                continue
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw[:4096]:
            continue
        yield path, raw.decode("utf-8", errors="ignore")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="local wiki/source root")
    parser.add_argument("--max-size", type=int, default=5 * 1024 * 1024)
    args = parser.parse_args()

    if not args.source.is_dir():
        print(f"ERROR: source directory not found: {args.source}", file=sys.stderr)
        return 2

    hits: list[str] = []
    scanned = 0
    for path, text in iter_text_files(args.source, args.max_size):
        scanned += 1
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                hits.append(f"{path}:{line}: {label}")

    print(f"Scanned text files: {scanned}")
    for hit in hits:
        print(f"HIT: {hit}")
    if hits:
        print(f"\nFAILED: {len(hits)} potential source leak(s)")
        return 1
    print("OK: source scan passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
