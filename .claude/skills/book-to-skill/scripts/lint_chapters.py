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

# --coverage mode: the cheap, deterministic half of the Step-7.5 coverage check.
# The RAW chapter text is plain extracted PDF/EPUB text — it has no markdown
# code fences or `|` table rows — so the only element we can count reliably in
# the raw is the FIGURE: extract.py injects `[[IMAGE: …]]` / `[[PAGE_SCAN: …]]`
# placeholders into the raw at the exact spots images appear. Every such
# placeholder must be accounted for in the toolkit (a Figures bullet, or a
# one-line "decorative" / "could not be read" note). Frameworks, code, tables,
# anti-patterns, exercises, and definitions are NOT mechanically countable in
# raw text — those are the LLM coverage-audit subagent's job (Step 7.5).
IMG_PLACEHOLDER_RE = re.compile(r"\[\[(?:IMAGE|PAGE_SCAN):", re.I)
FIG_BULLET_RE = re.compile(r"^\s*[-*]\s", re.M)


def _figures_section(md: str) -> str:
    """Text under a '## Figures' heading, up to the next '## '. Empty if none."""
    m = re.search(r"^#{2,}\s*Figures\b", md, re.M | re.I)
    if not m:
        return ""
    rest = md[m.end():]
    nxt = re.search(r"^#{2,}\s", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def coverage_deficits(toolkit_md: str, raw_text: str) -> list[str]:
    """Cheap raw-vs-toolkit coverage deficits (figures only — see note above).

    A deficit means the toolkit accounts for fewer figures than the raw has
    `[[IMAGE]]`/`[[PAGE_SCAN]]` placeholders, so a figure was likely dropped.
    """
    out: list[str] = []
    raw_imgs = len(IMG_PLACEHOLDER_RE.findall(raw_text))
    if raw_imgs:
        fig_sec = _figures_section(toolkit_md)
        low = toolkit_md.lower()
        accounted = (len(FIG_BULLET_RE.findall(fig_sec))
                     + low.count("could not be read")
                     + low.count("decorative"))
        if accounted < raw_imgs:
            out.append(f"figures: raw has {raw_imgs} image placeholder(s), "
                       f"toolkit accounts for {accounted}")
    return out


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
                 by_stem: dict[str, str] | None,
                 coverage: bool = False) -> list[str]:
    warnings: list[str] = []
    text = md_path.read_text(encoding="utf-8", errors="replace")

    if "extraction failed" in text.lower():
        warnings.append("extraction-failed stub present")

    words = len(text.split())
    if words < WORD_MIN:
        warnings.append(f"only {words} words (target {WORD_MIN}-{WORD_MAX})")
    elif words > WORD_MAX and not coverage:
        # In complete-coverage mode toolkits routinely exceed the cap by design,
        # so this warning would be pure noise — demote it.
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
        if coverage:
            for d in coverage_deficits(text, raw_text):
                warnings.append("COVERAGE " + d)
    return warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skill_dir", help="path to the generated skill directory")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any warnings are emitted")
    ap.add_argument("--coverage", action="store_true",
                    help="complete-mode: add raw-vs-toolkit figure-coverage "
                         "deficits and demote the >WORD_MAX warning")
    ap.add_argument("--json", action="store_true",
                    help="with --coverage: emit {book_number: [deficits]} as JSON "
                         "(for the Step-7.5 gap-fill loop)")
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
    cov_by_book: dict[str, list[str]] = {}
    for md in files:
        ws = lint_chapter(md, skill_dir, by_stem, coverage=args.coverage)
        total_warnings += len(ws)
        if args.coverage:
            bn = (by_stem or {}).get(md.stem, md.stem)
            cov_by_book[bn] = [w[len("COVERAGE "):] for w in ws
                               if w.startswith("COVERAGE ")]
        if ws and not args.json:
            print(f"\n{md.name}")
            for w in ws:
                print(f"  - {w}")

    if args.json:
        print(json.dumps(cov_by_book, indent=2))
    else:
        print(f"\n{len(files)} chapter file(s) checked, "
              f"{total_warnings} warning(s) total.")
    return 1 if (args.strict and total_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
