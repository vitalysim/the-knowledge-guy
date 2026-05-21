#!/usr/bin/env python3
"""Relabel a skill's `nutshell.md` headings and citations after
`backfill_book_numbers.py` has populated `book_number` in the manifest.

The first pass (when nutshell.md was generated lazily) used the
manifest `index` for headings: `## ch07 — Introduction`,
`*From [sethi-rich-life ch07].*`. Now that the manifest has the
canonical `book_number` (e.g. `intro`, `ch01`, `appendix-a`), this
script rewrites the existing nutshell file in place:

  - Each `## ch<NN> — <title>` becomes `## <book_number> — <title>`,
    matched by title (canonical key — robust to manifest renumbering).
  - Each `*From [<slug> ch<NN>].*` becomes `*From [<slug> <book_number>].*`,
    matched by old `chNN` adjacent to the matching block.

Idempotent: if no `chNN` prefixes remain, reports "nothing to do" and
returns 0.

Use:
  ./relabel_nutshell.py /path/to/skill          # rewrite in place
  ./relabel_nutshell.py /path/to/skill --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _title_key(s: str) -> str:
    """Normalised title used for matching across heading and manifest."""
    # Drop a leading "Chapter N — " / "Chapter N: " / "N. " from titles.
    s = re.sub(r"^\s*(chapter\s+\d+|[\divxlcdm]+)\s*[\.\):—–\-]\s*", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s.strip().lower())


def relabel(skill_dir: Path, dry_run: bool) -> int:
    nutshell = skill_dir / "nutshell.md"
    manifest_path = skill_dir / "chapters_manifest.json"
    if not nutshell.is_file():
        return 0  # nothing to do
    if not manifest_path.is_file():
        print(f"  {skill_dir.name}: no manifest — skipping", file=sys.stderr)
        return 0

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    skill_slug = manifest.get("skill_slug") or skill_dir.name

    # Title → book_number map (normalised key).
    by_title: dict[str, str] = {}
    for ch in manifest["chapters"]:
        bn = ch.get("book_number")
        if not bn:
            continue
        key = _title_key(ch.get("title", ""))
        if key:
            by_title[key] = bn

    text = nutshell.read_text(encoding="utf-8")
    original = text

    # Walk the file block by block. A block starts with `## <prefix> — <title>`
    # and is captured up to (but not including) the next `## ` heading.
    block_re = re.compile(
        r"(?m)^##\s+(?P<prefix>\S+)\s+—\s+(?P<title>.+?)\s*\n(?P<body>.*?)(?=^##\s|\Z)",
        re.S,
    )

    rewrites = 0
    citation_pattern_tpl = (
        r"\*From\s+\[" + re.escape(skill_slug) + r"\s+(?P<old>[A-Za-z0-9\-]+)\]\.\*"
    )

    def replace_block(m: re.Match) -> str:
        nonlocal rewrites
        prefix = m.group("prefix")
        title = m.group("title").strip()
        body = m.group("body")
        bn = by_title.get(_title_key(title))
        if not bn or bn == prefix:
            return m.group(0)  # already correct or unknown — leave alone
        rewrites += 1
        # Rewrite citation inside body if it matches the old prefix.
        new_body = re.sub(
            citation_pattern_tpl,
            lambda mm: f"*From [{skill_slug} {bn}].*"
                       if mm.group("old") == prefix
                       else mm.group(0),
            body,
        )
        return f"## {bn} — {title}\n{new_body}"

    text = block_re.sub(replace_block, text)

    if text == original:
        print(f"  {skill_dir.name}: nothing to relabel")
        return 0

    print(f"  {skill_dir.name}: {rewrites} block(s) relabeled")
    if dry_run:
        return 0
    nutshell.write_text(text, encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("skill_dir", nargs="+")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rc = 0
    for path in args.skill_dir:
        d = Path(path).resolve()
        if not d.is_dir():
            print(f"ERROR: not a directory: {d}", file=sys.stderr)
            rc = 1
            continue
        rc |= relabel(d, args.dry_run)
    return rc


if __name__ == "__main__":
    sys.exit(main())
