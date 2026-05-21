#!/usr/bin/env python3
"""Rewrite legacy `chNN` shorthand inside walk-memory files so they
match the new `book_number`-based numbering produced by
`backfill_book_numbers.py`.

Walk memory files live at
`~/.claude/projects/-Users-vitaly-MyPlace-projects-the-knowledge-guy/memory/walk-*.md`
and contain a `- Skills: <comma-separated-slugs>` line plus a curriculum
that uses shorthand like `housel/ch04` or `forshaw/ch14` to point at
chapters.

When a skill was backfilled, its manifest's old extraction-order `chNN`
labels were replaced with book-native `book_number`s (e.g. `housel/ch04`
was manifest idx 4 = "Luck & Risk" = book_number `ch02`). The walk
*functionally* still works (resume goes by step number) but the
shorthand drifts from the actual chapter files. This script syncs
the shorthand in place, leaving everything else untouched.

Idempotent: re-running on an already-migrated walk file is a no-op.

Usage:
  ./upgrade_walk_memory.py [memory_dir]          # rewrite in place
  ./upgrade_walk_memory.py [memory_dir] --dry-run

If `memory_dir` is omitted, defaults to
`~/.claude/projects/-Users-vitaly-MyPlace-projects-the-knowledge-guy/memory/`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_MEMORY_DIR = Path(
    "~/.claude/projects/-Users-vitaly-MyPlace-projects-the-knowledge-guy/memory"
).expanduser()
SKILLS_ROOT = Path(__file__).resolve().parents[2]  # .../.claude/skills


def _load_index_to_bn(skill_dir: Path) -> dict[int, str] | None:
    mpath = skill_dir / "chapters_manifest.json"
    if not mpath.is_file():
        return None
    try:
        m = json.loads(mpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    out: dict[int, str] = {}
    for ch in m.get("chapters", []):
        bn = ch.get("book_number")
        idx = ch.get("index")
        if bn and isinstance(idx, int):
            out[idx] = bn
    return out


def _resolve_skill(short: str) -> Path | None:
    """Map a memory-file shorthand (`housel`, `forshaw`) to an installed
    skill dir. Match on slug prefix; if multiple match, return the first.
    Returns None if no skill starts with this prefix.
    """
    short = short.lower()
    candidates = [d for d in SKILLS_ROOT.iterdir()
                  if d.is_dir() and d.name.startswith(short)
                  and d.name not in ("the-knowledge-guy", "book-to-skill")]
    return candidates[0] if candidates else None


def upgrade(walk_md: Path, dry_run: bool) -> bool:
    """Rewrite stale chNN shorthand in one walk file. Returns True if
    file was changed (or would be, in --dry-run)."""
    text = walk_md.read_text(encoding="utf-8")
    # The Skills: line lists which skills this walk uses. We resolve
    # each shorthand against that set.
    skills_match = re.search(r"^- Skills:\s*(.+)$", text, re.M)
    if not skills_match:
        return False
    skills_slugs = [s.strip() for s in skills_match.group(1).split(",")]
    # Build map: shorthand_prefix -> {index -> book_number}
    by_prefix: dict[str, dict[int, str]] = {}
    for slug in skills_slugs:
        skill_dir = SKILLS_ROOT / slug
        if not skill_dir.is_dir():
            continue
        idx_map = _load_index_to_bn(skill_dir)
        if not idx_map:
            continue
        # Use the first hyphen-separated word of the slug as the
        # shorthand prefix the walk likely used (e.g. housel-… → housel).
        prefix = slug.split("-", 1)[0].lower()
        by_prefix[prefix] = idx_map

    if not by_prefix:
        return False

    # Pattern: <prefix>/chNN or bare chNN inside a step line that
    # already named the prefix earlier (rare).
    # Be conservative: only rewrite occurrences of the form
    # "<prefix>/ch<NN>" plus follow-ons " + ch<NN>" (same paren group).
    changes = 0

    def _rewrite_chunk(prefix: str, idx_map: dict[int, str], chunk: str) -> str:
        nonlocal changes
        def _bare(m: re.Match) -> str:
            nonlocal changes
            old_n = int(m.group(1))
            new_bn = idx_map.get(old_n)
            if not new_bn:
                return m.group(0)  # leave unmapped intact
            if not new_bn.startswith("ch"):
                # Named (intro/preface/etc.) — use as-is.
                replacement = new_bn
            else:
                replacement = new_bn
            if replacement != f"ch{old_n:02d}" and replacement != f"ch{old_n}":
                changes += 1
            return replacement
        return re.sub(r"\bch(\d{1,3})\b", _bare, chunk)

    def _rewrite_ref(m: re.Match) -> str:
        prefix = m.group(1)
        rest = m.group(2)  # e.g. "ch04 + ch03" or just "ch06"
        idx_map = by_prefix.get(prefix.lower())
        if not idx_map:
            return m.group(0)
        new_rest = _rewrite_chunk(prefix, idx_map, rest)
        return f"{prefix}/{new_rest}"

    # Match `<prefix>/` followed by a chunk that may contain ch-refs
    # joined by " + " (the existing shorthand style in walk memories).
    new_text = re.sub(
        r"\b([a-z][a-z0-9]+)/((?:ch\d{1,3})(?:\s*\+\s*ch\d{1,3})*)",
        _rewrite_ref, text,
    )

    if new_text == text:
        return False

    if dry_run:
        print(f"  {walk_md.name}: {changes} reference(s) would be rewritten")
    else:
        walk_md.write_text(new_text, encoding="utf-8")
        print(f"  {walk_md.name}: {changes} reference(s) rewritten")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("memory_dir", nargs="?", default=str(DEFAULT_MEMORY_DIR))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    memory_dir = Path(args.memory_dir).expanduser()
    if not memory_dir.is_dir():
        print(f"ERROR: not a directory: {memory_dir}", file=sys.stderr)
        return 1

    walk_files = sorted(memory_dir.glob("walk-*.md"))
    if not walk_files:
        print(f"  no walk-*.md files found in {memory_dir}")
        return 0

    rc = 0
    for w in walk_files:
        try:
            upgrade(w, args.dry_run)
        except Exception as e:
            print(f"  ERROR upgrading {w.name}: {e}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
