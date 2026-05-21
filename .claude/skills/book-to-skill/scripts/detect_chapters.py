#!/usr/bin/env python3
"""
detect_chapters.py — heading-pattern detector for manual chapter re-split.

Runs on an existing extraction's full_text.txt and reports every plausible
chapter start by scanning multiple heading patterns: "Chapter N", "Part N"
+ Roman numerals, all-caps title lines, and "N. Title". Use it when the
extractor's auto-chunking over-merges Parts and the SKILL.md orchestrator
needs concrete numbers to drive a re-split into raw/chapters_split/.

Output (stdout, JSON list):
  [{"index": 1, "char_start": 0, "title": "...", "pattern": "chapter_word"}, ...]

Each candidate is the first character of the matching line in full_text.txt.
Adjacent matches within 400 chars are deduped (a heading echoed in a
running header collapses to one).

Usage:
  detect_chapters.py /path/to/raw/full_text.txt
  detect_chapters.py /path/to/raw/full_text.txt --json     (default)
  detect_chapters.py /path/to/raw/full_text.txt --table    (human-readable)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PATTERNS = [
    # (name, regex). Lines must match in full (after lstrip) and be < 90 chars.
    ("chapter_word",  re.compile(r"^chapter\s+\d+\b.*", re.IGNORECASE)),
    ("chapter_roman", re.compile(r"^chapter\s+[ivxlcdm]+\b.*", re.IGNORECASE)),
    ("part_word",     re.compile(r"^part\s+(?:\d+|[ivxlcdm]+)\b.*", re.IGNORECASE)),
    ("numbered_dot",  re.compile(r"^\d{1,2}\.\s+[A-Z][A-Za-z].*")),
    ("numbered_sp",   re.compile(r"^\d{1,2}\s+[A-Z][A-Za-z].*")),
    ("all_caps",      re.compile(r"^[A-Z][A-Z0-9 \-–—:'’]{6,80}$")),
]


def _is_spaced_letters(stripped: str) -> bool:
    """Detect typeset spaced-letter headers like 'N O T E' or 'BR IE F'.

    A real all-caps chapter title has at least one contiguous run of 4+
    letters. Spaced-letter typography breaks every word into singletons
    or pairs, so the longest contiguous-letter run is < 4.
    """
    longest = 0
    run = 0
    for ch in stripped:
        if ch.isalpha():
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest < 4


def detect(text: str, dedup_window: int = 600) -> list[dict]:
    raw = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if 0 < len(stripped) < 90:
            for name, rx in PATTERNS:
                if rx.match(stripped):
                    # Filter all-caps spaced-letter headers (running headers,
                    # title-page typography) — they are noise, not chapters.
                    if name == "all_caps" and _is_spaced_letters(stripped):
                        break
                    raw.append({
                        "char_start": offset,
                        "title": stripped,
                        "pattern": name,
                    })
                    break
        offset += len(line)

    deduped: list[dict] = []
    seen_titles: dict[str, int] = {}
    for cand in raw:
        # Char-window dedup (running headers repeat closely).
        if deduped and cand["char_start"] - deduped[-1]["char_start"] < dedup_window:
            continue
        # Title-frequency dedup: if the same title appears > 3× anywhere,
        # treat all but the first occurrence as a running header echo.
        title_key = cand["title"].lower()
        seen_titles[title_key] = seen_titles.get(title_key, 0) + 1
        if seen_titles[title_key] > 1:
            continue
        deduped.append(cand)
    for i, c in enumerate(deduped, 1):
        c["index"] = i
    return deduped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("full_text", help="path to raw/full_text.txt")
    ap.add_argument("--table", action="store_true",
                    help="human-readable output instead of JSON")
    args = ap.parse_args()

    path = Path(args.full_text)
    if not path.is_file():
        print(f"ERROR: not a file: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8", errors="replace")
    cands = detect(text)

    if args.table:
        print(f"{len(cands)} candidate chapter starts in {path}\n")
        print(f"{'#':>3}  {'char':>9}  {'pattern':<14}  title")
        print("-" * 80)
        for c in cands:
            print(f"{c['index']:>3}  {c['char_start']:>9,}  "
                  f"{c['pattern']:<14}  {c['title'][:60]}")
    else:
        json.dump(cands, sys.stdout, ensure_ascii=False, indent=2)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
