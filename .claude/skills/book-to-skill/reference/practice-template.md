# Practice File Template — Stage 3 (Practice) Output

Each eligible chapter produces one **practice set**:
`practice/<book_number>-<slug>.json` (canonical) plus a
`practice/<book_number>-<slug>.md` mirror (human-readable, greppable).
`book_number` is the canonical book-native label assigned by
`extract.py:assign_book_numbers` — see `concept-map-spec.md` → "Field
meanings". **Never use the manifest `index`** in filenames, in the
`book_number` field, or in citations; it drifts from the book's own
numbering. The filename stem **must** equal `<book_number>-<slug>` of the
matching chapter in `chapters_manifest.json`.

This file is the **frozen contract** between the two halves of the system:

- `/book-to-skill` Stage 3 **writes** these JSON files.
- `/the-knowledge-guy` `course` mode **reads** them to render interactive
  per-chapter sites; the `check` sub-mode reads them to grade open tasks.
- `book-to-skill/scripts/lint_practice.py` **validates** every file against
  this contract and **executes** every runnable lab to prove it works.

Both halves treat the schema below as canonical. Do not add fields a renderer
must guess at, or rename a field on one side only — silent field/enum drift is
the single highest-risk failure of this feature, and this file is the defense.

---

## Why a practice set exists

The `chapters/<book_number>-<slug>.md` toolkit captures *theory* — the
chapter's frameworks, anti-patterns, code, and takeaways. A practice set
captures the **doing**: the exercises that turn reading into skill. Some books
ship their own exercises; most don't. Stage 3 **extracts** the book's own where
they exist, **generates** faithful ones where they don't, and for cyber /
technical chapters may **web-research** current detail to build a realistic lab.

Practice is **additive**. A chapter with no practice file simply has no course
page exercises — it renders theory-only. Practice never changes the chapter
numbering contract, so it **does not bump** `chapters_manifest.json`'s
`schema_version` (which stays `2`). The course renderer discovers practice by
**file presence**, matching `book_number` against the manifest.

---

## The three exercise families

Every exercise belongs to exactly one **family**. The family decides where the
"checking" happens, which is the load-bearing distinction:

| Family | Checked by | Offline? | Examples (`type`) |
|---|---|---|---|
| `auto` | client-side JS, instantly | yes | `mcq`, `predict-output`, `fix-the-bug`, `fill-in-the-blank`, `reorder-steps`, `spot-anti-pattern` |
| `runnable` | learner runs code in a sandboxed iframe; a deterministic check decides pass/fail | yes for `js`; needs network on first run for `python` (Pyodide) | `lab` |
| `open` | graded by Claude via the "check with Claude" hatch, against a rubric | no (needs a chat turn) | `design-task`, `explain`, `threat-model`, `repro-writeup` |

Aim for **4–8 exercises per chapter**: at least 2 `auto`, at least 1 `runnable`
(only when the chapter has a real code example — otherwise skip and note it),
and at least 1 `open`. A faithful 4-exercise set beats a padded 8.

**Skip** front/back matter (`book_number` starting `fm` / `bm`) and any chapter
with `word_count < 300` — the same rule the nutshell uses. Skipped chapters get
no practice file.

---

## Top-level schema

```jsonc
{
  "schema_version": 1,                 // THIS file's schema, independent of the manifest's
  "skill_slug": "from-day-zero-to-zero-day",
  "book_number": "ch07",               // the join key — MUST equal a manifest chapter's book_number
  "chapter_file": "chapters/ch07-quick-and-dirty-fuzzing.md",  // == manifest `file`, verbatim
  "chapter_title": "Chapter 7: Quick and Dirty Fuzzing",
  "genre": "vuln-hunting",             // the skill's genre profile
  "built_at": "2026-06-06T14:30:00Z",  // ISO 8601; stamp AFTER generation (clock is unavailable mid-run)
  "sourcing": {
    "mode": "generate",                // "extract" | "generate" | "research" (the dominant path)
    "book_had_exercises": false,
    "web_research_used": true,
    "research_cache": "raw/research/ch07.md"   // path, or null
  },
  "exercises": [ /* … exercise objects, see below … */ ]
}
```

---

## Exercise objects

### Common fields (every exercise carries these)

```jsonc
{
  "id": "ch07-q1",            // unique WITHIN the file; format <book_number>-<short>. Stable — it is the localStorage key.
  "family": "auto",           // "auto" | "runnable" | "open"
  "type": "mcq",              // the specific shape (enums below)
  "difficulty": "core",       // "intro" | "core" | "stretch"
  "concept": "Mutation- vs generation-based fuzzing",   // prose: what this tests
  "tests": {                  // the citation — MUST resolve
    "book_number": "ch07",    //   to a real manifest chapter (usually this chapter)
    "framework": "Fuzzing Taxonomy (4 axes)"   //   SHOULD name a real Frameworks-Introduced / Anti-pattern from the chapter toolkit
  },
  "prompt": "…markdown prompt…",
  "references": []            // web sources: [{ "title": "...", "url": "...", "retrieved": "2026-06-06" }]
}
```

### `auto` family

Auto-checkable, client-side, offline. The correct answer **is** embedded in the
page — this is intrinsic to client-side checking and acceptable for self-paced
learning. Six `type`s:

**`mcq` / `predict-output` / `fix-the-bug` / `spot-anti-pattern`** — single
correct option:

```jsonc
{
  "id": "ch07-p1", "family": "auto", "type": "predict-output", "difficulty": "core",
  "concept": "…", "tests": { "book_number": "ch07", "framework": "…" },
  "prompt": "Given this loop, what condition causes `break` to fire?",
  "snippet": { "language": "bash", "code": "while true; do …; done" },   // OPTIONAL code shown above the options
  "options": [
    { "key": "a", "text": "…", "correct": false, "why": "…why this distractor is wrong…" },
    { "key": "b", "text": "…", "correct": true,  "why": "…why this is right…" }
  ],
  "answer": "b",              // MUST equal the key of the single option with correct:true
  "explanation": "…shown after the learner answers; cites the chapter…",
  "references": []
}
```
**Invariant:** exactly **one** option has `correct: true`, and `answer` equals
its `key`. The lint hard-fails zero-correct or multi-correct items.

**`fill-in-the-blank`** — one or more blanks, accepted answers
case-insensitive:
```jsonc
{
  "id": "…", "family": "auto", "type": "fill-in-the-blank", …,
  "prompt": "A process killed by signal N exits with code ____.",
  "blanks": [ { "id": "b1", "accepted": ["128+N", "128 + N", "128+signal"] } ],
  "explanation": "…"
}
```

**`reorder-steps`** — present `steps` shuffled, learner orders them:
```jsonc
{
  "id": "…", "family": "auto", "type": "reorder-steps", …,
  "prompt": "Order the radamsa crash-hunting loop.",
  "steps": [ { "id": "s1", "text": "mutate the sample" }, { "id": "s2", "text": "feed it to the target" }, … ],
  "correct_order": ["s1", "s2", "s3"],
  "explanation": "…"
}
```

### `runnable` family — `type: "lab"`

The learner edits code and clicks **Run**; the page executes it in a sandboxed
iframe and runs a **deterministic check** to decide pass/fail.

```jsonc
{
  "id": "ch07-lab1", "family": "runnable", "type": "lab", "difficulty": "core",
  "concept": "Bounding a parser write so it can't overflow (CWE-787)",
  "tests": { "book_number": "ch07", "framework": "AddressSanitizer as fuzzing telemetry" },
  "runtime": "js",            // "js" (native, offline) | "python" (Pyodide, CDN on first run)
  "prompt": "Fix `parse_record` so the check passes. Do not change the check.",
  "starter_code": "function parseRecord(buf, length) {\n  const out = [0,0,0,0,0,0,0,0];\n  for (let i = 0; i < length; i++) out[i] = buf[i];  // BUG\n  return out;\n}\n",
  "solution_code": "function parseRecord(buf, length) {\n  const out = [0,0,0,0,0,0,0,0];\n  const n = Math.min(length, out.length, buf.length);\n  for (let i = 0; i < n; i++) out[i] = buf[i];\n  return out;\n}\n",
  "check": {
    "kind": "assert",         // "assert" | "stdout"
    "harness": "const r = parseRecord([1,2,3,4,5,6,7,8,9,10], 10);\nif (r.length !== 8) throw new Error('must not grow past 8 slots');\nif (JSON.stringify(r) !== JSON.stringify([1,2,3,4,5,6,7,8])) throw new Error('copy first 8 only');",
    "expected_stdout": null,  // used only when kind == "stdout"
    "timeout_ms": 5000
  },
  "hints": [ "What stops `i` from exceeding the output length?", "Clamp to the smallest of the three lengths." ],
  "references": []
}
```

**Check semantics** (identical for the in-browser runner and `lint_practice.py`):
- The runnable program is `<learner-or-solution code>` followed by a newline and
  `check.harness`.
- `kind: "assert"` → **pass iff the program runs to completion without throwing**
  (JS) / raising (Python). The harness asserts on a function the learner defines;
  the `prompt` states that function's name + signature.
- `kind: "stdout"` → run the program, capture stdout, **pass iff
  `stdout.trim() == expected_stdout.trim()`**. Here the harness is a driver that
  calls the function and prints.

**Lab safety rails (non-negotiable — these keep labs deterministic and the
executor a plain timed subprocess):**
- **Pure functions only.** No file I/O, no network, no `Date`/`time`/clock, no
  randomness, no environment access, no threads.
- Keep `harness` small and total. It must pass on `solution_code` and **fail**
  on `starter_code` (otherwise the exercise teaches nothing).
- Prefer `runtime: "js"` whenever the concept allows — JS runs natively in the
  iframe with zero dependencies. Use `python` only when Python is the point;
  it lazy-loads Pyodide from a CDN on first Run and degrades to "check with
  Claude" when offline.

### `open` family

Graded by Claude, not the browser. **The renderer emits only `prompt` and an
attempt box plus a "Check with Claude" button** — it **must NOT render `rubric`
or `model_answer` into the HTML** (they are the grading key and would leak into
page source). Those two fields are **server-side only**, consumed exclusively by
the `check` sub-mode.

```jsonc
{
  "id": "ch07-open1", "family": "open", "type": "design-task", "difficulty": "stretch",
  "concept": "Choosing a fuzzing strategy end-to-end",
  "tests": { "book_number": "ch07", "framework": "Fuzzing Taxonomy (4 axes)" },
  "prompt": "You are handed a closed-source IoT firmware that speaks a custom TLV protocol over UDP 5683. Outline your first 30 minutes of fuzzing.",
  "rubric": [                 // SERVER-SIDE ONLY — never rendered
    { "criterion": "Classifies the target on the 4 taxonomy axes", "weight": 3 },
    { "criterion": "Picks boofuzz (protocol/TLV) over radamsa, with justification", "weight": 3 },
    { "criterion": "Names a crash-detection mechanism", "weight": 2 },
    { "criterion": "Gives an escalation path to coverage-guided fuzzing", "weight": 2 }
  ],
  "model_answer": "…SERVER-SIDE ONLY. Used by the grader; never rendered…",
  "references": [ { "title": "boofuzz docs", "url": "https://boofuzz.readthedocs.io/", "retrieved": "2026-06-06" } ]
}
```

---

## Field-visibility rule (the renderer's whitelist)

The course renderer must **whitelist fields per family** when it inlines the
`#kg-exercises` JSON island — never dump the raw object into the page:

| Family | Rendered into the page | Withheld (never in HTML) |
|---|---|---|
| `auto` | everything except per-option `why` is shown after answering; `options`, `answer`, `explanation` embedded (client checks need them) | — |
| `runnable` | `prompt`, `starter_code`, `check`, `solution_code` (behind a "Reveal solution" button) | — |
| `open` | `prompt` only (+ attempt box + button carrying `id`) | **`rubric`, `model_answer`** |

This is the one place a renderer mistake leaks an answer key. The lint cannot
catch a leak (it validates JSON, not HTML), so the rule lives here and in the
`course` mode procedure.

---

## Extract vs Generate vs Research (the per-chapter decision)

Decided inside each per-chapter Stage 3 subagent, which holds the raw slice and
the chapter toolkit:

1. **Extract** — if the raw chapter text contains exercise signals (`Exercise`,
   `Exercises`, `Problems`, `Try it`, `Lab`, `Challenge`, `Review Questions`,
   `Q1`…), lift the author's exercises and **complete** them: an author
   exercise often lacks an answer, a check, or a rubric — supply the missing
   piece in the schema above, preserving the author's wording in `prompt`. Set
   `sourcing.book_had_exercises = true`.
2. **Generate** — otherwise synthesize from the chapter toolkit (Frameworks
   Introduced, Anti-patterns, Code Examples, Reference Tables) + the raw slice.
   Every generated exercise's `tests.framework` **must name a real
   Frameworks-Introduced / Anti-pattern entry** from the toolkit — this is what
   keeps generated practice faithful to the book rather than generic.
3. **Web-research escape hatch** — only when the chapter is cyber / technical
   **and** a realistic lab needs current external detail (tool flags, a
   CWE/CVE, a public CTF-style scenario). Run `WebSearch` / `WebFetch`, distill
   findings to `raw/research/<book_number>.md` (with URLs + the retrieval date
   from a single `date` call), and draw on that cache for the lab and its
   `references[]`. Set `sourcing.web_research_used = true`,
   `sourcing.mode = "research"`. **On resume, if the cache file exists, read it
   instead of searching again** — this is what makes Stage 3 reproducible and
   keeps re-renders network-free.

---

## Genre practice profiles

What "practice" means differs by genre. Stage 3 targets the three
code-bearing profiles first; others degrade to `auto` + `open` only.

- **technical** — *can you apply the API/pattern correctly?* Dominant:
  `runnable` labs (fix-the-bug, implement-the-pattern) grounded in the
  chapter's Code Examples; `predict-output`; `mcq` on trade-offs. Open task:
  "design X using pattern Y", rubric scores correct preconditions + trade-off
  awareness.
- **textbook** — *did you learn what the section's exercise was meant to teach?*
  Prefer **extract** (textbooks have exercises), then complete them with the
  answers/checks/rubrics the book omits. `reorder-steps` and
  `fill-in-the-blank` shine (algorithm steps, theorem conditions). Carry a
  `tests` framework that names the section's concept so a future renderer can
  sequence by the learning DAG. This realizes the `exercises.md` the textbook
  genre profile has always promised — as structured, checkable JSON.
- **vuln-hunting** — *can you find / triage / patch the bug class?* Dominant:
  `spot-anti-pattern` (spot the sink), `fix-the-bug` (patch the vuln),
  `runnable` labs that **model** a vulnerable parser / protocol handler as a
  pure function (bounds, taint, parser state), and `open` `threat-model` /
  `repro-writeup` tasks. The web-research hatch fires here most often.
  **Safety:** labs teach the *reasoning* — they never fetch real exploits,
  never need a live target, never run untrusted binaries. Live work stays in
  the user's own environment (consistent with each skill's Scope & Limits).
- **everything else** (`financial`, `scientific`, `reference`, `business`,
  `psychology`, …) — `auto` + `open` only; add a `runnable` lab solely where a
  formula or computation is naturally code (e.g. a financial calculator).

---

## Quality bar

- **`book_number` is canonical.** Filename stem, the `book_number` field, and
  every `tests.book_number` come verbatim from `chapters_manifest.json`. Never
  reconstruct, never use `index`.
- **Faithful, not generic.** Every exercise ties to a real framework /
  anti-pattern / code example from the chapter toolkit.
- **Every runnable lab works.** Its `solution_code` + `check` passes, and its
  `starter_code` + `check` fails. `lint_practice.py` proves this by executing
  both — a lab whose model solution can't pass its own check is a hard error,
  always.
- **Distractors are misconceptions, not nonsense** — the kind a learner picks
  because they *almost* understand (same discipline as walk-mode quizzes).
- **`rubric` and `model_answer` never reach the browser.**
