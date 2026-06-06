#!/usr/bin/env python3
"""Repair `book_number` drift in Stage-3 practice files and course memory
after a skill is re-backfilled.

`backfill_book_numbers.py` can change a chapter's `book_number` (and rename
its `chapters/<book_number>-<slug>.md` file). When that happens, the
`practice/<book_number>-<slug>.json` files and the
`course-<skill-slug>.md` memory still reference the OLD label, so the
`course` renderer and the `check` sub-mode would look for chapters that no
longer exist. This script re-syncs them.

The stable join key across a backfill is the chapter **title** (and slug);
the `book_number` prefix is exactly what changes. For each practice file we
match its `chapter_title` to the current manifest entry, read that entry's
new `book_number`, and — when it differs — rewrite the file's internal
labels, rename the file (and its `.md` mirror and research cache), and
record an old→new remap. The remap is then applied to each
`course-<skill-slug>.md` memory file (chapter references, exercise-id
prefixes, and `courses/<slug>/<book_number>.html` artifact paths).

Idempotent: when nothing drifted, every step is a no-op.

Usage:
  ./upgrade_course_memory.py [memory_dir]            # rewrite in place
  ./upgrade_course_memory.py [memory_dir] --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_MEMORY_DIR = Path(
    "~/.claude/projects/-Users-vitaly-MyPlace-projects-the-knowledge-guy/memory"
).expanduser()
SKILLS_ROOT = Path(__file__).resolve().parents[2]  # .../.claude/skills
SKIP = {"the-knowledge-guy", "book-to-skill"}


def _manifest_by_title(skill_dir: Path) -> dict[str, dict] | None:
    mpath = skill_dir / "chapters_manifest.json"
    if not mpath.is_file():
        return None
    try:
        m = json.loads(mpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return {c.get("title"): c for c in m.get("chapters", []) if c.get("title")}


def migrate_skill(skill_dir: Path, dry_run: bool) -> dict[str, str]:
    """Rewrite/rename drifted practice files. Returns {old_bn: new_bn}."""
    practice_dir = skill_dir / "practice"
    by_title = _manifest_by_title(skill_dir)
    remap: dict[str, str] = {}
    if not practice_dir.is_dir() or not by_title:
        return remap

    for jf in sorted(practice_dir.glob("*.json")):
        try:
            doc = json.loads(jf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        old_bn = doc.get("book_number")
        ch = by_title.get(doc.get("chapter_title"))
        if not old_bn or not ch:
            continue
        new_bn, slug = ch.get("book_number"), ch.get("slug", "")
        if not new_bn or new_bn == old_bn:
            continue

        remap[old_bn] = new_bn
        # rewrite internal labels
        doc["book_number"] = new_bn
        doc["chapter_file"] = ch.get("file", doc.get("chapter_file", ""))
        for ex in doc.get("exercises", []):
            if isinstance(ex.get("id"), str) and ex["id"].startswith(old_bn + "-"):
                ex["id"] = new_bn + ex["id"][len(old_bn):]
            t = ex.get("tests")
            if isinstance(t, dict) and t.get("book_number") == old_bn:
                t["book_number"] = new_bn
        src = doc.get("sourcing") or {}
        if src.get("research_cache") == f"raw/research/{old_bn}.md":
            src["research_cache"] = f"raw/research/{new_bn}.md"

        new_json = practice_dir / f"{new_bn}-{slug}.json"
        old_md = practice_dir / f"{old_bn}-{slug}.md"
        new_md = practice_dir / f"{new_bn}-{slug}.md"
        cache_old = skill_dir / "raw" / "research" / f"{old_bn}.md"
        cache_new = skill_dir / "raw" / "research" / f"{new_bn}.md"

        if dry_run:
            print(f"  [{skill_dir.name}] {jf.name} -> {new_json.name} ({old_bn} -> {new_bn})")
            continue

        jf.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        jf.rename(new_json)
        if old_md.is_file():
            old_md.rename(new_md)
        if cache_old.is_file():
            cache_old.rename(cache_new)
        print(f"  [{skill_dir.name}] {jf.name} -> {new_json.name} ({old_bn} -> {new_bn})")

    return remap


def migrate_memory(mem_file: Path, skill_slug: str, remap: dict[str, str], dry_run: bool) -> bool:
    if not remap:
        return False
    text = mem_file.read_text(encoding="utf-8")
    new = text
    for old_bn, new_bn in remap.items():
        # chapter refs `<skill>/<old_bn>`, exercise ids `<old_bn>-`, artifact
        # paths `courses/<slug>/<old_bn>.html`, and bare `<old_bn>` at line
        # starts like "1. ⏳ ch01 —". Use word boundaries to stay safe.
        new = re.sub(rf"(?<![\w-]){re.escape(old_bn)}(?=[\s/\-.])", new_bn, new)
    if new == text:
        return False
    if dry_run:
        print(f"  {mem_file.name}: would rewrite {len(remap)} label(s)")
    else:
        mem_file.write_text(new, encoding="utf-8")
        print(f"  {mem_file.name}: rewrote {len(remap)} label(s)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("memory_dir", nargs="?", default=str(DEFAULT_MEMORY_DIR))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # 1. migrate practice files for every installed skill, collecting remaps
    remaps: dict[str, dict[str, str]] = {}
    for d in sorted(SKILLS_ROOT.iterdir()):
        if d.is_dir() and d.name not in SKIP:
            r = migrate_skill(d, args.dry_run)
            if r:
                remaps[d.name] = r

    # 2. apply each skill's remap to its course memory file
    memory_dir = Path(args.memory_dir).expanduser()
    if memory_dir.is_dir():
        for slug, remap in remaps.items():
            mf = memory_dir / f"course-{slug}.md"
            if mf.is_file():
                migrate_memory(mf, slug, remap, args.dry_run)

    if not remaps:
        print("  no book_number drift found — nothing to migrate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
