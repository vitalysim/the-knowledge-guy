#!/usr/bin/env python3
"""
lint_practice.py — validate a skill's Stage-3 practice files and PROVE every
runnable lab works.

For each `practice/<book_number>-<slug>.json` it checks the frozen contract in
`reference/practice-template.md`:

  HARD ERRORS (exit 1 regardless of --strict — a broken practice file is worse
  than none):
    * malformed JSON / missing required top-level or per-exercise fields
    * unknown `family` or `type` (the enum the renderer switches on)
    * MCQ-shaped item without exactly one correct option, or `answer` that
      doesn't point at it
    * filename stem != "<book_number>-<slug>", or the file's `book_number`
      has no matching chapter in chapters_manifest.json
    * a runnable lab whose model `solution_code` + `check` does NOT pass
      (executed for real), or whose `starter_code` DOES pass (teaches nothing)
    * duplicate exercise `id` within a file

  WARNINGS (exit 1 only with --strict):
    * `tests.book_number` that doesn't resolve to a real chapter
    * a `references[]` entry missing a url or retrieved date
    * a chapter practice file with zero `auto` exercises
    * `web_research_used: true` but no research cache on disk
    * a JS lab when `node` isn't installed (its execution check is skipped)

Runnable labs are executed in an isolated subprocess with a wall-clock timeout.
Python runs in the book-to-skill venv (or the current interpreter); JS runs in
`node` if available. Per the contract, labs are pure functions (no I/O, network,
clock, randomness), so a plain isolated interpreter with a timeout is enough.

Usage:
  lint_practice.py <skill_dir>
  lint_practice.py <skill_dir> --strict
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

FAMILIES = {"auto", "runnable", "open"}
AUTO_TYPES = {
    "mcq", "predict-output", "fix-the-bug", "spot-anti-pattern",
    "fill-in-the-blank", "reorder-steps",
}
SINGLE_CORRECT_TYPES = {"mcq", "predict-output", "fix-the-bug", "spot-anti-pattern"}
OPEN_TYPES = {"design-task", "explain", "threat-model", "repro-writeup"}
RUNNABLE_TYPES = {"lab"}
ALL_TYPES = AUTO_TYPES | OPEN_TYPES | RUNNABLE_TYPES

# Menu-number → genre-slug, mirroring book-to-skill Step 2. Defends against a
# metadata.json that stored the menu number instead of the slug.
_GENRE_BY_NUM = {
    "1": "technical", "2": "vuln-hunting", "3": "financial", "4": "scientific",
    "5": "legal", "6": "textbook", "7": "reference", "8": "business",
    "9": "psychology", "10": "history", "11": "productivity", "12": "biography",
    "13": "narrative", "14": "general",
}


def resolve_genre(metadata: dict) -> str:
    g = str(metadata.get("genre", "")).strip()
    if g.isdigit():
        return _GENRE_BY_NUM.get(g, "general")
    return g or "general"


def venv_python() -> str:
    cand = Path(__file__).resolve().parent.parent / ".venv" / "bin" / "python"
    return str(cand) if cand.is_file() else sys.executable


def have_node() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, timeout=10)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def run_program(runtime: str, program: str, timeout_ms: int) -> tuple[bool, str]:
    """Execute a self-contained program; return (exited_zero, captured_stdout)."""
    timeout = max(1.0, (timeout_ms or 5000) / 1000.0)
    try:
        if runtime == "python":
            cmd = [venv_python(), "-I", "-c", program]
        else:  # js
            cmd = ["node", "-e", program]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, (p.stdout or "")
    except subprocess.TimeoutExpired:
        return False, "<timed out>"
    except OSError as e:
        return False, f"<could not run {runtime}: {e}>"


def check_program(ex: dict, code: str) -> tuple[bool, str]:
    """Build <code> + harness per the lab's check kind and run it."""
    chk = ex.get("check", {})
    runtime = ex.get("runtime", "js")
    harness = chk.get("harness", "")
    sep = "\n;\n" if runtime == "js" else "\n"
    program = code + sep + harness
    ok, out = run_program(runtime, program, chk.get("timeout_ms", 5000))
    if chk.get("kind") == "stdout":
        ok = ok and out.strip() == str(chk.get("expected_stdout") or "").strip()
    return ok, out


def load_manifest(skill_dir: Path) -> set[str]:
    """Return the set of valid book_numbers, or an empty set if no manifest."""
    mpath = skill_dir / "chapters_manifest.json"
    if not mpath.is_file():
        return set()
    try:
        m = json.loads(mpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {c.get("book_number") for c in m.get("chapters", []) if c.get("book_number")}


def lint_file(path: Path, valid_bn: set[str], node_ok: bool,
              seen_ids: set[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"], []

    bn = doc.get("book_number")
    if not bn:
        errors.append("missing top-level `book_number`")
    for field in ("skill_slug", "chapter_file", "exercises"):
        if field not in doc:
            errors.append(f"missing top-level `{field}`")

    # filename stem must be "<book_number>-<slug>"
    if bn and not path.stem.startswith(bn + "-"):
        errors.append(f"filename stem `{path.stem}` does not start with `{bn}-`")
    if bn and valid_bn and bn not in valid_bn:
        errors.append(f"book_number `{bn}` has no matching chapter in the manifest")

    exercises = doc.get("exercises") or []
    auto_count = 0
    for ex in exercises:
        xid = ex.get("id", "<no-id>")
        fam = ex.get("type_family") or ex.get("family")
        typ = ex.get("type")

        if xid in seen_ids:
            errors.append(f"[{xid}] duplicate exercise id across the skill")
        seen_ids.add(xid)

        if fam not in FAMILIES:
            errors.append(f"[{xid}] unknown family `{fam}`")
        if typ not in ALL_TYPES:
            errors.append(f"[{xid}] unknown type `{typ}`")
            continue
        if fam == "auto":
            auto_count += 1
        for field in ("prompt", "concept", "tests"):
            if not ex.get(field):
                errors.append(f"[{xid}] missing `{field}`")

        tbn = (ex.get("tests") or {}).get("book_number")
        if tbn and valid_bn and tbn not in valid_bn:
            warns.append(f"[{xid}] tests.book_number `{tbn}` not in the manifest")

        for ref in ex.get("references") or []:
            if not ref.get("url") or not ref.get("retrieved"):
                warns.append(f"[{xid}] a reference is missing url or retrieved date")

        # MCQ invariant
        if typ in SINGLE_CORRECT_TYPES:
            opts = ex.get("options") or []
            correct = [o for o in opts if o.get("correct")]
            if len(correct) != 1:
                errors.append(f"[{xid}] must have exactly one correct option (has {len(correct)})")
            elif ex.get("answer") != correct[0].get("key"):
                errors.append(f"[{xid}] `answer` does not match the correct option's key")
        elif typ == "fill-in-the-blank":
            blanks = ex.get("blanks") or []
            if not blanks or any(not b.get("accepted") for b in blanks):
                errors.append(f"[{xid}] fill-in-the-blank needs blanks[] each with accepted[]")
        elif typ == "reorder-steps":
            steps = {s.get("id") for s in ex.get("steps") or []}
            order = set(ex.get("correct_order") or [])
            if not steps or steps != order:
                errors.append(f"[{xid}] reorder-steps `correct_order` must permute the step ids")

        # Runnable lab: execute for real.
        if fam == "runnable" or typ == "lab":
            rt = ex.get("runtime", "js")
            if not ex.get("solution_code") or not (ex.get("check") or {}).get("harness"):
                errors.append(f"[{xid}] lab needs solution_code and check.harness")
                continue
            if rt == "js" and not node_ok:
                warns.append(f"[{xid}] node not installed — lab execution skipped (cannot prove it works)")
                continue
            sol_ok, sol_out = check_program(ex, ex["solution_code"])
            if not sol_ok:
                errors.append(f"[{xid}] model solution does NOT pass its own check: {sol_out.strip()[:200]}")
            if ex.get("starter_code"):
                start_ok, _ = check_program(ex, ex["starter_code"])
                if start_ok:
                    errors.append(f"[{xid}] starter_code already passes the check — exercise teaches nothing")

    if exercises and auto_count == 0:
        warns.append("no `auto` (self-checkable) exercises in this chapter")

    # research cache sanity
    sourcing = doc.get("sourcing") or {}
    if sourcing.get("web_research_used") and sourcing.get("research_cache"):
        cache = path.parent.parent / sourcing["research_cache"]
        if not cache.is_file():
            warns.append(f"web_research_used but cache `{sourcing['research_cache']}` is missing")

    return errors, warns


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skill_dir", help="path to the generated skill directory")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on warnings too (errors always exit non-zero)")
    args = ap.parse_args()

    skill_dir = Path(args.skill_dir)
    practice_dir = skill_dir / "practice"
    if not practice_dir.is_dir():
        print(f"No practice/ dir under {skill_dir} — nothing to lint (Stage 3 not run).")
        return 0

    files = sorted(practice_dir.glob("*.json"))
    if not files:
        print(f"No practice JSON files in {practice_dir}.")
        return 0

    valid_bn = load_manifest(skill_dir)
    node_ok = have_node()
    seen_ids: set[str] = set()

    total_err = total_warn = 0
    for f in files:
        errs, warns = lint_file(f, valid_bn, node_ok, seen_ids)
        if errs or warns:
            print(f"\n{f.name}")
            for e in errs:
                print(f"  ERROR  {e}")
            for w in warns:
                print(f"  warn   {w}")
        total_err += len(errs)
        total_warn += len(warns)

    print(f"\n{len(files)} practice file(s) checked, "
          f"{total_err} error(s), {total_warn} warning(s).")
    if total_err:
        return 1
    return 1 if (args.strict and total_warn) else 0


if __name__ == "__main__":
    raise SystemExit(main())
