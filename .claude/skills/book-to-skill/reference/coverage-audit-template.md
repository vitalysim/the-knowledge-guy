# Coverage Audit — the verification contract (complete mode)

This file is the **frozen contract** for Step 7.5 (COVERAGE AUDIT), which runs
**only when `WITH_COVERAGE=complete`**. It exists to *prove* that each chapter
toolkit captured every **load-bearing element** present in the raw chapter — and
to drive the gap-fill loop that re-runs any chapter that didn't.

Three parties obey it:
- the **per-chapter audit subagent** returns one JSON verdict per chapter,
- the **orchestrator** (SKILL.md Step 7.5) reads the verdicts to decide which
  chapters to re-extract,
- the **mechanical pre-check** (`lint_chapters.py --coverage`) does the cheap,
  countable half before any audit subagent is spent.

It is the verification sibling of `practice-template.md` and `widgets.md`.

---

## What "load-bearing element" means

The elements a complete-mode toolkit must contain, one type per:

| type | what it is |
|---|---|
| `framework` | a named framework / technique / model (e.g. "The 5 Whys", "Fuzzing Taxonomy") |
| `code` | a fenced code block / command / snippet that teaches something |
| `figure` | a diagram / chart / screenshot (`[[IMAGE]]` / `[[PAGE_SCAN]]` in the raw) |
| `table` | a reference / comparison / decision table |
| `anti-pattern` | a named failure mode the author warns against |
| `exercise` | a problem / "try it" / challenge the author poses |
| `definition` | a key term defined precisely (load-bearing vocabulary) |

**Not** load-bearing (excluded from the audit): narration, prose transitions,
motivational filler, running examples used only to colour a point, and **purely
decorative** figures (ornaments, stock photos, chapter-opener art).

---

## The audit JSON (one object per chapter)

The audit subagent returns **exactly one JSON object**, no prose, no fences —
written by the orchestrator to `${SKILL_DIR}/raw/coverage/<book_number>.json`:

```jsonc
{
  "book_number": "ch07",
  "schema_version": 1,
  "elements": [
    {
      "type": "framework",                     // one of the 7 types above
      "name": "Fuzzing Taxonomy (4 axes)",
      "raw_evidence": "p.122 'every fuzzer …'", // a citable phrase/locator in the RAW
      "load_bearing": true,                     // false = decorative/ornamental → not counted
      "in_toolkit": true,                       // present in the toolkit (by name/content, not verbatim)
      "toolkit_location": "Frameworks Introduced",
      "note": ""
    }
  ],
  "missing": [
    {
      "type": "code",
      "name": "radamsa crash-loop",
      "raw_evidence": "fenced ```bash block, p.118 'while true; do radamsa …'",
      "load_bearing": true,
      "reason": "present in raw, absent from the toolkit's Code Examples"
    }
  ],
  "needs_manual_review": [
    {
      "type": "figure",
      "name": "Fig 7.3",
      "raw_evidence": "[[IMAGE: images/img_p0118_x42.png]]",
      "reason": "image could not be read / illegible"
    }
  ],
  "counts": {
    "raw_load_bearing": 14,
    "covered": 13,
    "decorative_excluded": 2,
    "needs_manual_review": 1
  },
  "coverage": 0.93,
  "verdict": "gaps"                              // "complete" | "gaps"
}
```

### Frozen field rules (the orchestrator + lint depend on these)

- **`elements[]`** lists every element the subagent found in the **raw**, each
  with `type`, `name`, `raw_evidence`, `load_bearing`, `in_toolkit`.
- **`missing[]`** = exactly the subset with `load_bearing == true && in_toolkit == false`.
  **Every `missing` item MUST carry `raw_evidence`** — an item that can't be cited
  in the raw is not a gap. This is the primary guard against hallucinated gaps.
- **`needs_manual_review[]`** = figures/tables the subagent genuinely could not
  interpret (a `[image could not be read]` placeholder in the toolkit, an
  illegible scan). These are **structurally excluded from `missing`** — an
  unreadable figure can *never* drive a re-run; it is surfaced for the human to
  inspect instead.
- **Decorative** elements (`load_bearing == false`) are excluded from `missing`
  **and** from the coverage denominator.
- **`coverage` = `covered / raw_load_bearing`** where `raw_load_bearing` counts
  only `load_bearing == true` elements that are *not* `needs_manual_review`. You
  cannot be penalised for an element that is intentionally a one-liner or
  genuinely unreadable.
- **`verdict`** is `"complete"` iff `missing` is empty **and** `coverage >= 0.95`
  (`THRESHOLD`); otherwise `"gaps"`.

---

## The loop knobs (referenced by SKILL.md Step 7.5)

- **`THRESHOLD = 0.95`** — a chapter "passes" at ≥ 0.95 with no `missing[]`. Not
  1.0, so a single borderline judgment call per ~20 elements doesn't force a round.
- **`N_ROUNDS = 3`** — max gap-fill rounds per chapter. After round 3, a chapter
  that still fails becomes a **residual** (written to `raw/coverage/RESIDUALS.json`
  and surfaced at Step 10), never retried forever. Cost is bounded to ≤ 3
  extractions + ≤ 3 audits per chapter.

A chapter is "audited & passing" — and therefore **skipped on resume** — iff its
`raw/coverage/<book_number>.json` exists, parses, and has `verdict == "complete"`.
Gap-fill deletes that file so the chapter is re-audited the next round. This is
filesystem-driven, idempotent, and independent of `progress.json` (a log only).

---

## The audit subagent prompt (used by Step 7.5)

```
Audit ONE chapter's coverage. Compare the RAW chapter text against the generated
toolkit and return a JSON verdict ONLY — no prose, no code fences.

Inputs (absolute paths substituted by the orchestrator):
  - Raw chapter text: <CHAPTERS_DIR>/<book_number>.txt
  - Generated toolkit: <SKILL_DIR>/chapters/<book_number>-<slug>.md
  - This contract: <BTS_DIR>/reference/coverage-audit-template.md (read it)
  - For any [[IMAGE]]/[[PAGE_SCAN]] in the raw whose meaning you can't verify from
    the toolkit text, you MAY Read <SKILL_DIR>/raw/<that path> to judge whether it
    is load-bearing or decorative.

Steps:
  1. Enumerate every LOAD-BEARING element in the RAW (the 7 types). Mark pure
     ornaments load_bearing:false.
  2. For each, decide in_toolkit: present by name/content (not necessarily
     verbatim)? A framework/definition counts if paraphrased; a code block must
     appear (or its key lines be captured); a table must be reproduced/captured.
  3. missing[] = load_bearing && !in_toolkit, each WITH raw_evidence.
     needs_manual_review[] = figures/tables you could not interpret. NEVER put a
     needs_manual_review item in missing[].
  4. Be conservative: only flag a "missing" element you can cite in the RAW. Do
     NOT invent elements the chapter doesn't contain.
  5. Emit exactly one JSON object per the schema above. coverage = covered /
     raw_load_bearing (decorative + needs_manual_review excluded). verdict =
     "complete" iff missing is empty AND coverage >= 0.95.
```

---

## The gap-fill addendum (injected into the Stage-1 re-run)

When a chapter fails, Step 7.5 re-runs its Stage-1 subagent (the complete-mode
mandate) with this appended — the rule is **add, never shorten**:

```
This chapter's toolkit is INCOMPLETE. Produce a COMPLETE toolkit that ALSO
includes the following load-bearing elements found in the RAW but MISSING from
the current toolkit. Keep EVERYTHING already present — do not shorten or drop
anything — and ADD these:
  <bullet list: each missing[].name + raw_evidence>
  <+ mechanical deficits, e.g. "2 fenced code blocks in the raw are not captured">
The needs_manual_review figures (<list>) need not be reconstructed — leave their
one-line "[image could not be read]" placeholders intact.
```

---

## Quality bar

- **Cite or it isn't a gap.** Every `missing` item needs `raw_evidence`.
- **Unreadable ≠ missing.** A figure that can't be read is `needs_manual_review`,
  surfaced for a human — never a re-run trigger.
- **Decorative ≠ load-bearing.** Ornaments are excluded from both `missing` and
  the denominator; the template's "decorative → one line" rule is the bar.
- **Conservative beats eager.** A false "missing" costs a wasted gap-fill round;
  the `N_ROUNDS=3` cap converts any persistent disagreement into a surfaced
  residual rather than an infinite loop.
