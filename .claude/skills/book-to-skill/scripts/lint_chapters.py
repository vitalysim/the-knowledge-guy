#!/usr/bin/env python3
"""
lint_chapters.py — post-Stage-1 quality check on chapter summary files.

For each chapters/ch*.md file, report any of:
  * word count outside the 200-2,000 band (target: 800-1,400 tokens ≈ 600-1,100 words)
  * "extraction failed" stub (Stage-1 corruption recovery)
  * verbatim copying: any 30-char window that appears in the corresponding
    raw/raw_chapters/chNN.txt (or chapters_split/chNN.txt) more than once
    is flagged (templated boilerplate forgiven up to 3 hits)
  * missing structural headings ("Frameworks", "Key Takeaways" — best-effort
    on a genre-agnostic basis)

Non-blocking — prints warnings to stdout, exits 0 unless invoked with
--strict, in which case any warning -> exit 1.

Usage:
  lint_chapters.py <skill_dir>
  lint_chapters.py <skill_dir> --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


WORD_MIN = 200
WORD_MAX = 2_000
SNIPPET_LEN = 40
# Technical / vuln-hunting / scientific books legitimately quote exact
# command syntax, API names, code fragments — that's the point. Keep the
# verbatim threshold loose enough to flag only obvious copy-paste, not
# correct terminology preservation.
SNIPPET_HITS_ALLOWED = 15
SNIPPET_STEP = 120
EXPECTED_HEADINGS = ("Frameworks", "Key Takeaways")


def _load_manifest_index(skill_dir: Path) -> dict[str, str] | None:
    """Map `chapters/<stem>.md` → `book_number` so raw lookups can find
    `<book_number>.txt` regardless of whether the stem starts with
    `ch07-…`, `intro-…`, `appendix-a-…`, etc. Returns None for legacy
    skills without a manifest."""
    mpath = skill_dir / "chapters_manifest.json"
    if not mpath.is_file():
        return None
    try:
        m = json.loads(mpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    out: dict[str, str] = {}
    for ch in m.get("chapters", []):
        bn = ch.get("book_number")
        f = ch.get("file") or ""
        if bn and f.startswith("chapters/"):
            out[Path(f).stem] = bn
    return out


def find_raw(skill_dir: Path, md_stem: str, idx: int,
             by_stem: dict[str, str] | None) -> Path | None:
    """Locate the raw text slice for a chapter.

    Tries (in order):
      1. `<book_number>.txt` derived from the manifest entry whose
         `file` matches this chapter's filename (canonical, schema_v2).
      2. `ch{idx:02d}.txt` (legacy schema_v1).
    """
    candidates: list[str] = []
    bn = by_stem.get(md_stem) if by_stem else None
    if bn:
        candidates.append(f"{bn}.txt")
    candidates.append(f"ch{idx:02d}.txt")
    for sub in ("chapters_split", "raw_chapters"):
        for name in candidates:
            p = skill_dir / "raw" / sub / name
            if p.is_file():
                return p
    return None


def verbatim_hits(chapter_md: str, raw_text: str) -> int:
    """Count 30-char windows from chapter_md that appear verbatim in raw_text.

    Counts at most one hit per starting position. Returns the number of
    distinct windows that match.
    """
    if len(chapter_md) < SNIPPET_LEN or len(raw_text) < SNIPPET_LEN:
        return 0
    hits = 0
    seen: set[str] = set()
    for i in range(0, len(chapter_md) - SNIPPET_LEN, SNIPPET_STEP):
        snip = chapter_md[i : i + SNIPPET_LEN]
        # Skip snippets that are mostly punctuation/whitespace.
        if sum(c.isalpha() for c in snip) < 24:
            continue
        if snip in seen:
            continue
        seen.add(snip)
        if snip in raw_text:
            hits += 1
    return hits


def lint_chapter(md_path: Path, skill_dir: Path,
                 by_stem: dict[str, str] | None) -> list[str]:
    warnings: list[str] = []
    text = md_path.read_text(encoding="utf-8", errors="replace")

    if "extraction failed" in text.lower():
        warnings.append("extraction-failed stub present")

    words = len(text.split())
    if words < WORD_MIN:
        warnings.append(f"only {words} words (target {WORD_MIN}-{WORD_MAX})")
    elif words > WORD_MAX:
        warnings.append(f"{words} words exceeds {WORD_MAX} target")

    missing = [h for h in EXPECTED_HEADINGS if h.lower() not in text.lower()]
    if len(missing) == len(EXPECTED_HEADINGS):
        warnings.append("none of the standard structural headings present "
                        f"({', '.join(EXPECTED_HEADINGS)})")

    # Verbatim-copy check: look up the raw source by manifest first
    # (schema_v2 — handles `intro`, `appendix-a`, etc.), then by
    # legacy `ch{idx:02d}` if the filename starts with `chNN`.
    idx_match = re.match(r"ch(\d{1,3})", md_path.stem)
    idx = int(idx_match.group(1)) if idx_match else 0
    raw_path = find_raw(skill_dir, md_path.stem, idx, by_stem)
    if raw_path:
        raw_text = raw_path.read_text(encoding="utf-8", errors="replace")
        hits = verbatim_hits(text, raw_text)
        if hits > SNIPPET_HITS_ALLOWED:
            warnings.append(
                f"{hits} verbatim {SNIPPET_LEN}-char windows match raw source "
                f"(threshold {SNIPPET_HITS_ALLOWED}) — possible copy-paste"
            )
    return warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skill_dir", help="path to the generated skill directory")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any warnings are emitted")
    args = ap.parse_args()

    skill_dir = Path(args.skill_dir)
    chapters_dir = skill_dir / "chapters"
    if not chapters_dir.is_dir():
        print(f"ERROR: no chapters/ dir under {skill_dir}", file=sys.stderr)
        return 2

    # Lint every chapter file in chapters/ — not only chNN-* — so
    # `intro-…md`, `preface-…md`, `appendix-a-…md`, `fm-…md`, etc. all
    # get the same quality checks.
    files = sorted(chapters_dir.glob("*.md"))
    if not files:
        print(f"ERROR: no chapter files in {chapters_dir}", file=sys.stderr)
        return 2

    by_stem = _load_manifest_index(skill_dir)

    total_warnings = 0
    for md in files:
        ws = lint_chapter(md, skill_dir, by_stem)
        if ws:
            total_warnings += len(ws)
            print(f"\n{md.name}")
            for w in ws:
                print(f"  - {w}")

    print(f"\n{len(files)} chapter file(s) checked, "
          f"{total_warnings} warning(s) total.")
    return 1 if (args.strict and total_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
