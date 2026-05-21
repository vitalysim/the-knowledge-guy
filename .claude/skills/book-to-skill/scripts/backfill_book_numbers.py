#!/usr/bin/env python3
"""Backfill `book_number` into an existing skill's chapters_manifest.json
and rename on-disk chapter files to match.

Why this exists: skills generated before `extract.py:assign_book_numbers`
existed have manifests whose `index` field is extraction order (counts
front matter), so book ch1 lands at `chapters/ch07-…md` or worse.
Renderers (nutshell, walk, citations) inherit the wrong numbering.

What this script does:
  1. Reads `<skill-dir>/chapters_manifest.json`.
  2. For each entry, computes `book_number` from the title using
     `extract.assign_book_numbers` (the single source of truth).
  3. Renames `chapters/<old-prefix>-<slug>.md` →
     `chapters/<book_number>-<slug>.md` on disk.
  4. Updates the manifest's `file` field per entry, adds the
     `book_number` field, bumps `schema_version` to 2.
  5. Rewrites references to old filenames inside:
        - the skill's `SKILL.md` (chapter index + inline mentions)
        - every chapter body (cross-references)
        - the skill's `nutshell.md` heading + citations (separate pass:
          see `relabel_nutshell.py`)
  6. Updates the skill's `raw/raw_chapters/<old-prefix>.txt` filenames
     (the original raw slices) for consistency with future extractions.

Idempotent: if every entry already has `book_number` and the on-disk
filenames already match `<book_number>-<slug>.md`, the script reports
"nothing to do" and exits 0.

Use:
  ./backfill_book_numbers.py /path/to/.claude/skills/<slug>          # apply
  ./backfill_book_numbers.py /path/to/.claude/skills/<slug> --dry-run

The --dry-run mode prints planned renames and manifest diffs without
touching disk.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Import assign_book_numbers from the sibling extract.py — single source
# of truth for the title → book_number mapping.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import assign_book_numbers  # noqa: E402


_REDUNDANT_PREFIXES = {
    "intro":      [r"intro(duction)?-"],
    "preface":    [r"preface-"],
    "prologue":   [r"prologue-"],
    "postscript": [r"post[-]?script-"],
    "epilogue":   [r"epilogue-"],
    "foreword":   [r"fore[-]?word-"],
    "afterword":  [r"after[-]?word-"],
    "appendix":   [r"appendi[cx]es?-"],
    "fm":         [r"front-matter-"],
    "bm":         [r"back-matter-"],
}

def _strip_redundant_prefix(slug: str, bn: str, title: str) -> str:
    """Drop a leading slug fragment that just echoes book_number."""
    s = slug.lower()
    # ch07 / ch00 / ch99: drop "chapter-7-", "chapter-07-", "ch-7-".
    if bn.startswith("ch") and bn[2:].isdigit():
        n = bn[2:].lstrip("0") or "0"
        for pat in (rf"^chapter-{n}-", rf"^chapter-0?{n}-",
                    rf"^ch-{n}-", rf"^ch{n}-"):
            s2 = re.sub(pat, "", s, count=1)
            if s2 != s:
                s = s2
                break
    # appendix-a / appendix-b: drop "appendix-a-".
    elif bn.startswith("appendix-"):
        letter = bn.split("-", 1)[1]
        s = re.sub(rf"^appendix-{letter}-", "", s, count=1)
        s = re.sub(r"^appendix-", "", s, count=1)
    # part-1 / part-2: drop "part-1-", "part-i-".
    elif bn.startswith("part-"):
        s = re.sub(rf"^part-{bn.split('-', 1)[1]}-", "", s, count=1)
        s = re.sub(r"^part-", "", s, count=1)
    # Named (intro / preface / fm / bm / …).
    else:
        for pat in _REDUNDANT_PREFIXES.get(bn, []):
            s = re.sub(rf"^{pat}", "", s, count=1)
    return s or "section"


def compute_renames(manifest: dict) -> list[dict]:
    """Return a list of {entry, old_file, new_file, book_number} plans.
    Mutates `manifest['chapters']` in place to add `book_number`.
    """
    chs = [{"title": c.get("title", "")} for c in manifest["chapters"]]
    assign_book_numbers(chs)

    plans = []
    for entry, computed in zip(manifest["chapters"], chs):
        bn = computed["book_number"] or f"ch{entry['index']:02d}"
        entry["book_number"] = bn

        old_file = entry.get("file") or ""
        slug = entry.get("slug") or "section"
        # Recover the slug portion from the old filename so we rename
        # what's actually on disk (extractor + Stage 1 sometimes choose
        # different slugs than the manifest's `slug` field).
        if old_file:
            m = re.match(r"chapters/([^/]+?)-(.+)\.md$", old_file)
            if m:
                slug = m.group(2)
        # Strip ugly duplicate prefixes the manifest slug may carry:
        #   bn="preface",    slug="preface-preface"          → "preface"
        #   bn="appendix-a", slug="appendix-a-common-ports"  → "common-ports"
        #   bn="ch07",       slug="chapter-7-taxes"          → "taxes"
        #   bn="fm",         slug="front-matter-praise"      → "praise"
        slug = _strip_redundant_prefix(slug, bn, entry.get("title", ""))
        new_file = f"chapters/{bn}-{slug}.md"
        plans.append({
            "entry": entry,
            "old_file": old_file,
            "new_file": new_file,
            "book_number": bn,
        })
        entry["file"] = new_file
    return plans


def rewrite_text(text: str, old_to_new_filename: dict[str, str]) -> str:
    """Rewrite occurrences of old chapter filenames to new ones.

    Matches both:
      - bare filename: `ch07-introduction.md`
      - relative path: `chapters/ch07-introduction.md`
    Sorted longest-first to avoid partial-prefix collisions
    (`ch01` vs `ch01-foo` etc.).
    """
    for old, new in sorted(old_to_new_filename.items(),
                           key=lambda kv: -len(kv[0])):
        if old == new:
            continue
        old_stem = Path(old).name              # ch07-introduction.md
        new_stem = Path(new).name              # intro-introduction.md
        old_base = old_stem[:-3]               # ch07-introduction
        new_base = new_stem[:-3]               # intro-introduction
        # Replace fully-qualified paths first, then bare stems.
        text = text.replace(old, new)
        text = text.replace(old_stem, new_stem)
        # Replace bare base only when followed by a word boundary so
        # we don't corrupt unrelated identifiers.
        text = re.sub(rf"\b{re.escape(old_base)}\b", new_base, text)
    return text


def _synthesize_manifest(skill_dir: Path) -> dict | None:
    """Build a manifest from chapter files on disk for skills generated
    before manifests existed. The filename prefix is assumed to already be
    a book_number-ish label (the convention these old skills happen to
    use); each file's H1 supplies the title."""
    chapters_dir = skill_dir / "chapters"
    if not chapters_dir.is_dir():
        return None
    files = sorted(chapters_dir.glob("*.md"))
    if not files:
        return None
    out = []
    for i, f in enumerate(files, start=1):
        m = re.match(r"^([^-]+(?:-[a-z])?)-(.+)$", f.stem)
        if not m:
            continue
        prefix, slug = m.group(1), m.group(2)
        first_line = ""
        try:
            with f.open(encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("# "):
                        first_line = line[2:].strip()
                        break
        except OSError:
            pass
        out.append({
            "index": i,
            "title": first_line or slug.replace("-", " ").title(),
            "slug": slug,
            "file": f"chapters/{f.name}",
            "word_count": max(1, f.stat().st_size // 6),  # crude
            "token_estimate": max(1, f.stat().st_size // 4),
            "status": "extracted",
        })
    return {
        "schema_version": 1,
        "skill_slug": skill_dir.name,
        "synthesized_from_disk": True,
        "chapters": out,
    }


def backfill(skill_dir: Path, dry_run: bool) -> int:
    manifest_path = skill_dir / "chapters_manifest.json"
    if not manifest_path.is_file():
        synth = _synthesize_manifest(skill_dir)
        if synth is None:
            print(f"ERROR: {manifest_path} not found and no chapters/ to synthesize from",
                  file=sys.stderr)
            return 1
        print(f"  {skill_dir.name}: no manifest — synthesising from chapters/")
        manifest = synth
        # Persist it (unless dry-run) so future runs are normal.
        if not dry_run:
            manifest_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if "chapters" not in manifest:
        print(f"ERROR: {manifest_path} has no 'chapters' field",
              file=sys.stderr)
        return 1

    already_done = all(
        c.get("book_number") and (c.get("file") or "").startswith(
            f"chapters/{c['book_number']}-")
        for c in manifest["chapters"]
    )
    if already_done and manifest.get("schema_version") == 2:
        print(f"  {skill_dir.name}: already backfilled — nothing to do")
        return 0

    plans = compute_renames(manifest)
    manifest["schema_version"] = 2

    # Build the rename map for downstream text rewrites.
    old_to_new = {p["old_file"]: p["new_file"]
                  for p in plans if p["old_file"] and p["old_file"] != p["new_file"]}

    print(f"=== {skill_dir.name} ===")
    for p in plans:
        marker = "  " if p["old_file"] == p["new_file"] else "→ "
        print(f"  {marker}{p['book_number']:>12}  {p['old_file']!s:<50}  ⇒  {p['new_file']}")

    if dry_run:
        print(f"  (dry-run: no files written)")
        return 0

    chapters_dir = skill_dir / "chapters"
    # 1. Rename chapter files on disk.
    for p in plans:
        if not p["old_file"] or p["old_file"] == p["new_file"]:
            continue
        old_path = skill_dir / p["old_file"]
        new_path = skill_dir / p["new_file"]
        if not old_path.exists():
            # File listed in manifest but missing on disk — skip without
            # erroring (the manifest may include "skipped" entries).
            continue
        if new_path.exists() and new_path != old_path:
            print(f"  WARN: target exists, skipping rename: {new_path.name}",
                  file=sys.stderr)
            continue
        old_path.rename(new_path)

    # 2. Rewrite cross-references inside each chapter body.
    if chapters_dir.is_dir():
        for ch_file in chapters_dir.glob("*.md"):
            original = ch_file.read_text(encoding="utf-8")
            rewritten = rewrite_text(original, old_to_new)
            if rewritten != original:
                ch_file.write_text(rewritten, encoding="utf-8")

    # 3. Rewrite the skill's SKILL.md (chapter index + inline mentions).
    skill_md = skill_dir / "SKILL.md"
    if skill_md.is_file():
        original = skill_md.read_text(encoding="utf-8")
        rewritten = rewrite_text(original, old_to_new)
        # Chapter-index tables typically have a display label adjacent to
        # the link, e.g. `[ch02](chapters/ch01-a-parable.md)` — the link
        # is now correct but the label is stale. Resync any
        # `[<label>](<path>.md)` where the path's stem prefix differs
        # from the label, by replacing the label with the new prefix.
        def _resync_label(m: re.Match) -> str:
            label, path = m.group(1), m.group(2)
            stem = Path(path).stem  # ch01-a-parable
            new_prefix = stem.split("-", 1)[0]
            # Compose long prefix if it's appendix-X or fm-N / bm-N.
            parts = stem.split("-")
            if parts[0] in ("appendix", "fm", "bm") and len(parts) > 1 and \
               (parts[1].isalpha() and len(parts[1]) == 1 or parts[1].isdigit()):
                new_prefix = f"{parts[0]}-{parts[1]}"
            if label != new_prefix and re.fullmatch(r"ch\d+|intro|preface|prologue|postscript|epilogue|foreword|afterword|appendix|appendix-[a-z]|part-\w+|fm|fm-\d+|bm|bm-\d+",
                                                   label):
                return f"[{new_prefix}]({path})"
            return m.group(0)
        rewritten = re.sub(
            r"\[([A-Za-z0-9\-]+)\]\((chapters/[^)]+\.md)\)",
            _resync_label, rewritten,
        )
        if rewritten != original:
            skill_md.write_text(rewritten, encoding="utf-8")

    # 4. Rename raw/raw_chapters/<old>.txt → <new>.txt (best-effort —
    #    these are not used at render time but should stay consistent).
    raw_dir = skill_dir / "raw" / "raw_chapters"
    if raw_dir.is_dir():
        for p in plans:
            if not p["old_file"]:
                continue
            old_stem = Path(p["old_file"]).stem.split("-", 1)[0]  # e.g. "ch07"
            new_stem = p["book_number"]
            if old_stem == new_stem:
                continue
            old_txt = raw_dir / f"{old_stem}.txt"
            new_txt = raw_dir / f"{new_stem}.txt"
            if old_txt.exists() and not new_txt.exists():
                old_txt.rename(new_txt)

    # 5. Write back the updated manifest.
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  done: schema_version=2, {len(plans)} entries")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("skill_dir", nargs="+",
                        help="path(s) to skill directories to backfill")
    parser.add_argument("--dry-run", action="store_true",
                        help="print planned renames without touching disk")
    args = parser.parse_args()

    rc = 0
    for path in args.skill_dir:
        skill_dir = Path(path).resolve()
        if not skill_dir.is_dir():
            print(f"ERROR: not a directory: {skill_dir}", file=sys.stderr)
            rc = 1
            continue
        rc |= backfill(skill_dir, args.dry_run)
    return rc


if __name__ == "__main__":
    sys.exit(main())
