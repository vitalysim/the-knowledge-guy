---
name: book-to-skill
description: >-
  Converts a technical or non-fiction book (PDF or EPUB) into a structured,
  two-tier Claude Code skill — extracting the author's named frameworks,
  techniques, anti-patterns, figures, and concept relationships into a
  knowledge base that loads cheaply and deepens on demand. Handles embedded
  images and scanned pages via native image understanding. Use this whenever
  the user wants to turn a book into a skill, study a book through Claude,
  apply an author's frameworks while working, or build a reusable knowledge
  base from a PDF or EPUB — even if they don't say the word "skill".
when_to_use: >-
  Trigger phrases — "turn this book into a skill", "create a skill from this
  PDF", "create a skill from this EPUB", "convert PDF to skill", "convert EPUB
  to skill", "I want to study X book", "add this book to my skills", "make a
  skill out of this book", "analyze this book", "extract frameworks from this
  book", "build a knowledge base from this book". Accepts a path to a PDF or
  EPUB and an optional skill-name slug.
disable-model-invocation: false
context: fork
agent: general-purpose
allowed-tools: >-
  Bash(uv *) Bash(bash *) Bash(mkdir *) Bash(cp *) Bash(mv *)
  Bash(rm *) Bash(find *) Bash(wc *) Bash(echo *) Bash(cat *) Bash(ls *)
  Bash(test *) Bash(file *) Bash(date *) Read Write Glob Grep Task
argument-hint: <path-to-pdf-or-epub> [skill-name-slug]
arguments: [book_path, skill_name]
effort: high
---

# Book-to-Skill Converter

> **Empty-args guard (read first).** This guard fires **only** when the
> user invoked `/book-to-skill` with no positional argument at all
> (i.e. `$book_path` is the empty string or unset). In that one case,
> reply only with:
>
> > book-to-skill needs a PDF or EPUB path.
> > Usage: `/book-to-skill /path/to/book.pdf [skill-name]`
>
> and end the turn — do not invoke any other skill, do not resume any
> prior walk, do not load `the-knowledge-guy`.
>
> **If `$book_path` is non-empty, do NOT trigger this guard.** Whether
> the path is valid (exists, is a PDF/EPUB, etc.) is checked by Step 0
> below using `test -f` and `file`. Never decide validity from the path
> string alone — always run the actual filesystem check first.

Turn a book into a Claude Code skill that is **expert by default and deep on
demand**. The result is not a book report — it is a toolkit of the author's
crystallised frameworks, plus a concept map of how those frameworks connect.

## Philosophy

- **Extract structure, not summaries.** Capture named frameworks, exact
  techniques, anti-patterns, and figures — not chapter recaps.
- **Plumbing in Python, intelligence in Claude.** `scripts/extract.py` does
  only mechanical extraction. Every act of *understanding* — what a framework
  is, what a diagram means, how concepts relate — is Claude's work.
- **Two tiers.** The generated `SKILL.md` is the always-loaded expert (a
  concept map + topic index). The `chapters/` files are the depth, paged in
  only when needed. This is why a 600-page book becomes a skill that costs a
  few thousand tokens to consult, not 400K.
- **Raw stays with the skill.** The mechanical extraction (full text,
  per-chapter raw text, images, metadata, spine) is preserved inside the
  generated skill at `<slug>/raw/`. The chapter `.md` files are summaries;
  the raw lets the skill (and the user) re-read original passages, quote
  exactly, or re-extract a chapter without re-running Stage 0.

## Architecture — a map-reduce pipeline

```
Stage 0  EXTRACT   extract.py → text + images + per-chapter slices + offsets
Pass 0   SPINE     fast read of ToC + intros → the book's thesis & framework list
Stage 1  MAP       each chapter → one chapter file   (parallel subagents)
Stage 2  REDUCE    all chapter files → concept map + topic index → SKILL.md
```

Stage 1 maps over chapters; Stage 2 reduces over chapter *extractions*. Stage 2
never sees the full text — only the small chapter files — so book length never
breaks the context budget. The reduce step **consolidates and connects**; it
does not summarise summaries.

## Modes

Route by what the user asks:

1. **Full conversion** (default) — a PDF/EPUB path with no special request.
   Run all steps.
2. **Analyze only** — "analyze", "just extract", "let me review first". Run
   Steps 0–5, produce the extraction report, stop. Do not generate skill files.
3. **Resume** — a prior run was interrupted, or the user says "resume". See
   *Resuming* at the end; re-run is safe and skips completed work.

---

## Step 0 — Out-of-scope check

If the argument is not a path to a PDF or EPUB, stop:
> "book-to-skill needs a PDF or EPUB path. Usage:
> `/book-to-skill /path/to/book.pdf [skill-name]`"

## Step 0.5 — Resolve the book-to-skill install path

The skill can live in **either** the current project's `.claude/skills/` or
the user's `~/.claude/skills/`. Resolve which once and reuse:

```bash
BTS_DIR=""
for cand in "$(pwd)/.claude/skills/book-to-skill" "$HOME/.claude/skills/book-to-skill"; do
  if [ -f "$cand/scripts/extract.py" ]; then BTS_DIR="$cand"; break; fi
done
test -n "$BTS_DIR" || { echo "book-to-skill: install not found"; exit 1; }
```

Every reference below to `${BTS_DIR}` is this resolved path. Do not hard-code
either location.

## Step 1 — Validate input and dependencies

```bash
test -f "$0" && file "$0"
```

Confirm the extension is `.pdf`/`.epub` or the magic bytes are `%PDF`/`PK`.
Then ensure the extraction libraries are present:

```bash
bash "${BTS_DIR}/scripts/setup.sh"
```

`setup.sh` requires [`uv`](https://docs.astral.sh/uv/) — it creates a venv at
`${BTS_DIR}/.venv` and installs PyMuPDF, ebooklib,
beautifulsoup4, and pypdf into it via `uv pip install`. PyMuPDF is
the primary backend (text + images + tables + outline + page rendering in one
library). If it cannot be installed, the extractor falls back to text-only and
**images and scanned pages will be skipped** — tell the user if that happens.

## Step 2 — Identify the genre

Read `reference/genre-profiles.md`. Then ask the user:

> "What kind of book is this? It changes how I extract.
>
> ─ Preserve tables / code / exact wording ─
>  1. **Technical** — programming, engineering, architecture
>  2. **Vuln-hunting / security** — offensive security, exploitation, RE
>  3. **Financial** — investing, valuation, markets, quant
>  4. **Scientific** — academic, research methods, dense reference
>  5. **Legal / regulatory** — statutes, case law, compliance, doctrine
>  6. **Textbook** — pedagogical, sections + exercises
>  7. **Reference / cookbook** — recipe-style, self-contained primitives
>
> ─ Prose-driven ─
>  8. **Business / leadership** — org-level frameworks, decision rules
>  9. **Psychology** — biases, effects, popular cog-sci (Kahneman, Ariely)
> 10. **History** — eras, events, causes, dated actors
> 11. **Productivity** — habits, decision-making, mental models
> 12. **Biography / memoir** — life arcs, turning-point decisions
> 13. **Narrative non-fiction** — case-study or argument-driven
> 14. **Not sure** — I'll treat it as general"

Store the choice as `GENRE`. It selects the profile that governs the chunk
boundary, the chapter schema, and the reduce emphasis for the rest of the
run. If the user is unsure between two, consult the **Selector heuristics**
section at the bottom of `genre-profiles.md` before committing.

## Step 3 — Extract (Stage 0)

Best-effort sweep of stale staging dirs from previous runs (never fail
the run on this):

```bash
find /tmp -maxdepth 1 -name 'book_skill_work*' -type d -mtime +1 \
  -exec rm -rf {} \; 2>/dev/null || true
```

```bash
uv run --python "${BTS_DIR}/.venv/bin/python" \
  "${BTS_DIR}/scripts/extract.py" "$0" \
  --mode <technical|text> --genre <GENRE> --work-dir /tmp/book_skill_work
```

(Equivalent: `"${BTS_DIR}/.venv/bin/python" "${BTS_DIR}/scripts/extract.py"
…` — the venv created by `setup.sh` is the single source of truth for the
extractor's dependencies.)

Use `--mode technical` for genres **1–7** (anything that needs tables,
code, or exact wording preserved — technical, vuln-hunting, financial,
scientific, legal, textbook, reference). Use `--mode text` for genres
**8–13** (prose-driven — business, psychology, history, productivity,
biography, narrative). For `general` (14), default to `--mode text` unless
the user overrides.

The work-dir is a staging area; Step 6 moves everything into the generated
skill at `<slug>/raw/` once the slug is known. This writes to
`/tmp/book_skill_work/`:

- `full_text.txt` — assembled reading-order text, with `[[IMAGE: ...]]` and
  `[[PAGE_SCAN: ...]]` placeholders anchored where they occur.
- `raw_chapters/chNN.txt` — each chapter pre-cut as its own file.
- `images/` — every kept figure, plus rendered pages of scanned PDFs.
- `metadata.json` — chapter offset map, image manifest, token estimates,
  granularity diagnosis, and scan-ratio fields:
  - `chapters_source` — `"raw_chapters"` initially, becomes `"chapters_split"`
    when a manual re-split is in effect.
  - `granularity_warning` — non-null when chapters look over-merged.
  - `scan_cost_warning` — true when ≥ 10% of pages are image-only.
  - `is_scanned_document` — true when ≥ 55% are image-only.

Read `metadata.json`. Surface both warnings to the user before continuing:
- `is_scanned_document: true` → chapter text will come from vision OCR;
  expect higher cost.
- `scan_cost_warning: true` (and not fully scanned) → some pages are
  image-only; vision-OCR cost will be elevated.

### Granularity check — automated, with mechanical re-split path

If `metadata.json["granularity_warning"]` is non-null, the auto-detected
chapters are likely Parts (not real chapters). Don't guess — run the
heading detector:

```bash
"${BTS_DIR}/.venv/bin/python" "${BTS_DIR}/scripts/detect_chapters.py" \
  /tmp/book_skill_work/full_text.txt --table
```

Diff its candidate count against `metadata.json["chapter_count"]`. If the
detector finds notably more (e.g. extractor says 7, detector says 14+),
present the user the numbers and proceed to re-split:

1. For each candidate `i` with `char_start=S_i` (and next start `S_{i+1}`,
   or end-of-file), write `/tmp/book_skill_work/chapters_split/chNN.txt`
   containing `full_text[S_i:S_{i+1}]`.
2. Overwrite `metadata.json["chapters"]` with the new list of
   `{index, title, slug, char_start, char_end, est_tokens,
   raw_text_path}` entries pointing at `chapters_split/`.
3. Set `metadata.json["chapters_source"] = "chapters_split"`.

From this point onward, Stage 1 reads `chapters_split/` instead of
`raw_chapters/`. Step 6 moves both directories into the skill's `raw/`
so the original auto-extraction is preserved as a record.

## Step 4 — Pre-flight cost estimate

Read pricing from `${BTS_DIR}/reference/pricing.json` and inject it into
the estimate. If `pricing.as_of` is more than 90 days behind today's
date, prepend: `⚠ Reference prices are dated <as_of> — verify current
rates at the source URL before committing.`

From `metadata.json`, present an estimate **before generating anything**:

```
📖 <title> (<format>) — <page_count> pages, <chapter_count> chapters
📄 Text ~<estimated_text_tokens/1000>K tokens | Images <image_count> (~<estimated_image_tokens/1000>K vision tokens)
⚠ <scanned_pages> of <page_count> pages are image-only (~10× vision cost)   ← only if scan_cost_warning
⚠ Chapter granularity: <granularity_warning>                                 ← only if non-null

💰 Estimated token cost (full conversion):
   Input  ≈ <estimated_total_tokens × 1.4>   (chapter reads + image reads + prompts)
   Output ≈ <chapter_count × 1,100 + 9,000>  (chapter files + SKILL.md + supporting files)

   Reference API prices (per MTok, as of <pricing.as_of>):
     <for each model in pricing.models: label — $<input> in / $<output> out>

📁 Will generate: SKILL.md + <chapter_count> chapter files + glossary + patterns + cheatsheet + nutshell + chapters_manifest.json
➡  Proceed with full conversion? (or say "analyze only" to preview first)
```

Wait for confirmation. If the user says "analyze only", switch to Mode 2.

## Step 5 — Pass 0: build the spine

A chapter extractor that hasn't seen the whole book cannot tell what is central
versus incidental. Fix that cheaply first.

Build the spine **mechanically**, not impressionistically — every chapter
extractor reads it, so weak input here propagates everywhere.

1. Read `full_text.txt` chars `0–8,000` (front matter + ToC region).
2. For each chapter listed in `metadata.json["chapters"]`, read the first
   1,000 characters of its raw file (whichever directory
   `metadata.json["chapters_source"]` points at).
3. Synthesise the three sections below from those fragments only. Do not
   pull from the full chapter bodies — that's Stage 1's job.

Write to `/tmp/book_skill_work/spine.md`:

```markdown
# Spine — <Title> by <Author>
## Thesis
<2–3 sentences: what the whole book argues.>
## Framework Inventory
- <Framework name> — <one line> (≈ ch<N>)
## Domain & Vocabulary
<the subject area and 5–10 distinctive terms the book uses.>
```

The spine is passed to **every** chapter extractor in Stage 1 so each one
extracts in light of where the book is going.

**If Mode 2 (analyze only):** produce the extraction report now from the spine
plus a skim of the chapter files — frameworks, principles, techniques,
anti-patterns, a suggested skill name, and a detected-chapters table — then
stop.

## Step 6 — Purpose, skill name, scaffolding

Ask the purpose (weights what the Core section foregrounds):
> "What should this skill help you do? (1) apply the author's frameworks while
> working (2) think with the author's mental models (3) reference specific
> chapters (4) all of the above"

Determine the skill slug: use argument `$1` if given; otherwise propose
`{author-lastname}-{core-concept}` and `{book-title-hyphenated}` and let the
user pick.

**Output destination — project-local.** The generated skill is written to the
**current working directory's** `.claude/skills/<slug>/` — i.e. the project
the user invoked `/book-to-skill` from. Resolve once and reuse:

```bash
SKILLS_ROOT="$(pwd)/.claude/skills"
SKILL_DIR="${SKILLS_ROOT}/<slug>"
mkdir -p "${SKILL_DIR}/chapters" "${SKILL_DIR}/raw" || {
  echo "FATAL: cannot create ${SKILL_DIR} — check permissions on $(pwd)/.claude/" >&2
  exit 1
}
```

`mkdir -p` will also create `$(pwd)/.claude/` if missing — the user has
explicitly asked for project-local skills. If the hard error fires, stop;
do not silently fall back to `~/.claude/skills/`. Confirm `${SKILL_DIR}/`
does not already exist with content; if it does, append `-2` or ask.

**Legacy-skill check.** If `${SKILL_DIR}/chapters_manifest.json`
already exists from a prior run, inspect it:

```bash
sv=$(python3 -c "import json,sys;print(json.load(open('${SKILL_DIR}/chapters_manifest.json')).get('schema_version',1))" 2>/dev/null)
if [ "$sv" != "2" ]; then
  echo "⚠  Existing manifest is schema_version=$sv (legacy chapter numbering)."
  echo "   Run: ${BTS_DIR}/scripts/backfill_book_numbers.py ${SKILL_DIR}"
  echo "   Or delete the manifest to start fresh, then re-run /book-to-skill."
  exit 1
fi
```

This stops Stage 1 before it would overwrite chapter files with the
wrong numbering, which would silently corrupt SKILL.md links and
nutshell citations. The user can resolve by either running
`backfill_book_numbers.py` (preferred — preserves any existing chapter
content) or deleting the manifest (preferred only for a full re-extract).

**Move the raw extraction into the skill.** The work-dir from Step 3 is
staging; the raw extraction is part of the skill from now on. Move it in and
write `progress.json` inside it:

```bash
mv /tmp/book_skill_work/full_text.txt    "${SKILL_DIR}/raw/"
mv /tmp/book_skill_work/raw_chapters     "${SKILL_DIR}/raw/"
mv /tmp/book_skill_work/chapters_split   "${SKILL_DIR}/raw/" 2>/dev/null || true
mv /tmp/book_skill_work/images           "${SKILL_DIR}/raw/" 2>/dev/null || true
mv /tmp/book_skill_work/metadata.json    "${SKILL_DIR}/raw/"
mv /tmp/book_skill_work/spine.md         "${SKILL_DIR}/raw/"
echo '{"stage1_done": [], "stage2_done": false}' > "${SKILL_DIR}/raw/progress.json"
```

`chapters_split/` only exists if a manual re-split was performed in Step 3.
When present, it takes precedence in Stage 1.

From this point onward, **every path that used to point into
`/tmp/book_skill_work/` now points into `${SKILL_DIR}/raw/`** (chapter raw
text, spine, metadata, images, progress).

## Step 7 — Stage 1: MAP (chapter extraction)

Read `reference/chapter-template.md`. Then, for each chapter in
`metadata.json`, generate
`${SKILLS_ROOT}/<slug>/chapters/<book_number>-<slug>.md` (the
project-local skills root resolved in Step 6).

**Filename prefix uses `book_number`, not the manifest `index`.**
`metadata.json["chapters"][*].book_number` is the book-native label
that `extract.py` assigns: `ch07` for "Chapter 7 — …", `intro` for
the Introduction, `preface`, `appendix-a`, `fm` / `fm-2` for front
matter, `bm` for back matter, `part-1` for "Part I". The `index`
field is still present but is extraction order only — never use it
in filenames or in user-facing labels. If `book_number` is missing
(extremely old skills), fall back to `ch{index:02d}` and log it.

**Choose the chapter source directory once, up front:**

```
if metadata.json["chapters_source"] == "chapters_split":
    CHAPTERS_DIR = "${SKILL_DIR}/raw/chapters_split"
else:
    CHAPTERS_DIR = "${SKILL_DIR}/raw/raw_chapters"
```

Pass `CHAPTERS_DIR` into every subagent task. Don't hardcode `raw_chapters/`
— a manual re-split won't take effect otherwise.

**Resume = filesystem is ground truth.** Before spawning subagents, list
existing files in `${SKILL_DIR}/chapters/`. For every
`<book_number>-*.md` that already exists and is `> 500 bytes` and does
not contain "extraction failed", that chapter is done — skip it.
`progress.json` is a running log only; do not use it to drive resume
decisions.

**Parallelise.** Spawn the chapters as parallel subagents with the `Task` tool
— independent contexts keep each extraction sharp and the run survives length.
Batch them (e.g. 5–8 at a time) for a long book. Give each subagent this task:

```
Extract one chapter into a Claude Code skill chapter file.

Inputs (substitute <SKILL_DIR> with the absolute project-local path from
Step 6 and <CHAPTERS_DIR> with the source chosen above):

  - Chapter raw text:  <CHAPTERS_DIR>/<book_number>.txt
  - Book spine:        <SKILL_DIR>/raw/spine.md   (read for context)
  - Genre profile:     <paste the relevant profile from genre-profiles.md>
  - Chapter template:  <BTS_DIR>/reference/chapter-template.md
                       (substitute the path resolved in Step 0.5)

Steps:
  1. Read the spine, then the chapter raw text.
  2. If the raw text is < 300 chars or obviously garbled (e.g. < 50% real
     words), do NOT invent content. Write a stub:
       # <Book number> — extraction failed
       Raw source is <X> chars / appears corrupted. Inspect
       <CHAPTERS_DIR>/<book_number>.txt and re-extract if needed.
     Save to <SKILL_DIR>/chapters/<book_number>-extraction-failed.md and
     report "CHAPTER FAILED: <book_number>" to the orchestrator. Do not
     proceed.
  3. For every [[IMAGE: images/..]] or [[PAGE_SCAN: images/..]] placeholder,
     Read <SKILL_DIR>/raw/<that path> and fold its meaning into the chapter
     file as text (per the template's image-handling section — including
     its rules for failed reads).
  4. Write the chapter summary file to:
     <SKILL_DIR>/chapters/<book_number>-<chapter-slug>.md
     following the chapter template, adapted to the genre profile. The raw
     source remains at <CHAPTERS_DIR>/<book_number>.txt — do not delete or
     modify it.

Extract structure, not summary. Preserve exact framework names. 800–1,400
tokens. Report the chapter title and key frameworks when done.
```

After each batch, append completed chapter numbers to
`${SKILL_DIR}/raw/progress.json`. If a subagent fails, retry that one
chapter — do not restart the run.

## Step 8 — Stage 2: REDUCE (concept map)

**Lint first.** Run the quality check on the chapter files before reduce
reads them — surfaces runaway word counts, missing structural headings,
and verbatim-quote copy-pastes:

```bash
"${BTS_DIR}/.venv/bin/python" "${BTS_DIR}/scripts/lint_chapters.py" \
  "${SKILL_DIR}"
```

Lint warnings are advisory: show them to the user. Re-run any chapter
that fails badly before reading on (a chapter with "extraction failed"
or 6,000 words will degrade the concept map). Do not block — the user
decides.

Read `reference/concept-map-spec.md`. Then:

1. Read **every** generated `chapters/ch*.md` file and `spine.md`.
2. **Consolidate** — dedupe recurring frameworks into single nodes, resolve
   refinements, pick the 6–10 load-bearing frameworks. (For financial/
   scientific genres, do not over-merge terms that differ subtly.)
3. Build the **concept map** (node list + typed edges).
4. Build the **topic index** — map the vocabulary a user would actually ask
   in, with synonyms and multi-chapter pointers. This is the bridge between
   the two tiers; a weak index makes "go to the chapter" fail.
5. Generate `glossary.md`, `patterns.md`, `cheatsheet.md`, sizing/sharding
   them to the book per the spec's scaling table.
6. If the topic index exceeds ~2,000 tokens (cap in `concept-map-spec.md`),
   keep the highest-frequency ~60 terms inline in `SKILL.md` and write the
   full version to `${SKILL_DIR}/topic-index-full.md`, linked from `SKILL.md`.
7. Write `${SKILL_DIR}/chapters_manifest.json` (schema in
   `concept-map-spec.md`).
   - Set `schema_version: 2` at the top.
   - Read `${SKILL_DIR}/raw/metadata.json` once. For each manifest
     entry, **copy `book_number` verbatim** from the matching
     metadata chapter (matched by `index`). `book_number` is the
     canonical label — never reconstruct it from `index` or from
     filenames; the source of truth is `extract.py:assign_book_numbers`
     and its output already lives in `metadata.json`.
   - `file` must equal `chapters/<book_number>-<slug>.md` (the
     filename Stage 1 actually wrote).
   - `status` is `extracted` | `failed`, derived from whether the
     file contains an "extraction failed" stub.
   - Refuse to write the manifest if any chapter is missing
     `book_number` in metadata — print the failing entries and stop;
     a missing `book_number` indicates extract.py did not run with
     `assign_book_numbers`, and proceeding would corrupt downstream
     renderers.

Set `stage2_done: true` in `${SKILL_DIR}/raw/progress.json` (log only).

## Step 8.5 — Stage 2.5: NUTSHELL (per-chapter micro-summaries)

Produce `${SKILL_DIR}/nutshell.md` — a per-chapter micro-summary skim
of the whole book, one ~100-word block per chapter, that the user can
scroll in a single response via `/the-knowledge-guy nutshell <slug>`.

This stage maps over the **chapter toolkit files**, not the raw text,
so cost scales with chapter count, not book size.

1. Read `${BTS_DIR}/reference/nutshell-template.md` (the schema and
   voice rules).
2. Read `${SKILL_DIR}/chapters_manifest.json`. **Skip** an entry if
   *any* of the following holds:
   - `word_count < 300` (front matter, acknowledgments, dedications,
     stubs).
   - `book_number` equals `fm` / `bm` or starts with `fm-` / `bm-`
     (any front- or back-matter slot, even if it happens to exceed the
     word threshold — the user wants chapters in a nutshell skim,
     not indexes or copyright pages).
3. For every remaining entry, spawn a parallel subagent (single
   message, N `Task` calls). Each subagent gets:
   - The template (inline).
   - The chapter's toolkit file path (`${SKILL_DIR}/<file>`).
   - The chapter index, title, and skill slug.
   - The one-line thesis from `${SKILL_DIR}/raw/spine.md` for tone.

   Each subagent returns exactly one nutshell block (80-120 words,
   3-5 bullets) following the template's "Required shape" section.
   No preamble, no closing remarks — just the block.

4. Concatenate the returned blocks in manifest order. Prepend:

   ```
   # <Book title> — in a nutshell

   > <one-line thesis pulled from spine.md>
   ```

5. Write to `${SKILL_DIR}/nutshell.md`. Target total length: ~2-3K
   tokens for a typical 15-25 chapter book.

If a subagent fails or returns a malformed block (no
`## <book_number>` heading, or >180 words), retry once. If it fails
twice, write a single-line stub for that chapter
(`## <book_number> — <title>\n\n*Nutshell generation failed.*`) and
continue — do not block the whole stage.

## Step 9 — Write the master SKILL.md

Using the template in `concept-map-spec.md`, write
`${SKILLS_ROOT}/<slug>/SKILL.md`. Keep the body under ~4,000 tokens and
front-load it (truncation eats the end). It must contain: the book thesis, the
concept map, the Core Frameworks section, the chapter index (linked), the
topic index, and the supporting-files links.

## Step 10 — Validate, clean up, report

Validate before declaring done:

```bash
test -f "${SKILLS_ROOT}/<slug>/SKILL.md"
test -f "${SKILLS_ROOT}/<slug>/chapters_manifest.json"
test -f "${SKILLS_ROOT}/<slug>/nutshell.md"
ls "${SKILLS_ROOT}/<slug>/chapters/" | wc -l   # == chapter_count
# Surface any chapters that bailed out during Stage 1:
grep -l "extraction failed" "${SKILLS_ROOT}/<slug>/chapters/"*.md || true
# Surface any nutshell blocks that failed:
grep -l "Nutshell generation failed" "${SKILLS_ROOT}/<slug>/nutshell.md" || true
# schema_version + book_number presence — every entry must have one,
# and every `file` field must reference a chapter that actually exists.
python3 - <<'PYEOF'
import json, os, sys
p = "${SKILLS_ROOT}/<slug>/chapters_manifest.json"
m = json.load(open(p))
assert m.get("schema_version") == 2, f"manifest schema_version != 2 ({m.get('schema_version')!r}); see Step 8."
bad = [c for c in m["chapters"] if not c.get("book_number")]
assert not bad, f"{len(bad)} chapter(s) missing book_number: {[c.get('title') for c in bad]}"
unc = [c for c in m["chapters"] if c["book_number"].endswith("-unclassified")]
if unc:
    print(f"⚠  {len(unc)} chapter(s) fell back to chNN-unclassified — titles the parser couldn't classify:")
    for c in unc: print(f"     idx={c['index']} title={c.get('title')!r}")
miss = [c["file"] for c in m["chapters"] if not os.path.isfile("${SKILLS_ROOT}/<slug>/" + c["file"])]
assert not miss, f"{len(miss)} manifest file(s) point at non-existent chapters: {miss}"
print(f"✅ Schema version: 2 ({len(m['chapters'])} chapters, all with book_number)")
PYEOF
```

If any chapter file contains "extraction failed", list those chapter
numbers prominently in the final report — the user needs to know which
chapters are stubs, not silently treat the run as fully successful.

Check that every chapter index entry links to a file that exists and that the
topic index points only to real chapters. Also confirm the raw extraction was
preserved inside the skill:

```bash
test -d "${SKILL_DIR}/raw/raw_chapters"
test -f "${SKILL_DIR}/raw/full_text.txt"
test -f "${SKILL_DIR}/raw/metadata.json"
test -f "${SKILL_DIR}/raw/spine.md"
```

Then remove the staging directory only (the raw lives inside the skill now):

```bash
rm -rf /tmp/book_skill_work
```

**Do not delete `${SKILL_DIR}/raw/`** — it is part of the skill. The
generated `SKILL.md` should reference it so future invocations of the skill
can re-read original passages, quote exactly, or re-extract a chapter
without re-running Stage 0.

Report:

```
✅ Skill created: ./.claude/skills/<slug>/   (project-local)

📚 <Title> — <Author>   (<page_count> pages, <chapter_count> chapters)

  SKILL.md                  — concept map + core frameworks + indexes
  chapters/                 — <N> chapter summary files (loaded on demand)
  chapters_manifest.json    — canonical chapter list with status per file
  raw/                      — original extraction: full_text.txt, raw_chapters/,
                              chapters_split/ (if re-split), images/,
                              metadata.json, spine.md
  glossary.md / patterns.md / cheatsheet.md
  nutshell.md               — per-chapter micro-summary skim (use via /the-knowledge-guy nutshell <slug>)
  topic-index-full.md       — only when topic index exceeded the inline cap

Usage:
  /<slug>            → load the concept map and core frameworks
  /<slug> <topic>    → find and explain a topic (jumps to the right chapter)
  /<slug> ch<N>      → open a specific chapter
```

---

## Resuming an interrupted run

A long book is a long run; make it survivable. Re-running `/book-to-skill` with
the same arguments is always safe:

- **Extraction**: `extract.py --resume` reuses a prior extraction when the
  source file hash matches — no re-extraction.
- **Stage 1**: chapter files in `${SKILL_DIR}/chapters/` are the authoritative
  checkpoint. A `chNN-*.md` that exists, is `> 500 bytes`, and does NOT
  contain "extraction failed" is considered done — skip it. Recompute the
  todo set from the filesystem on every resume; do not trust
  `progress.json` (it is a running log, not the source of truth).
- **Stage 2**: only runs once all chapter files exist (failed stubs count
  as "exists" — they will be flagged in the final report, not retried
  automatically).
- **Stage 2.5 (nutshell)**: if `${SKILL_DIR}/nutshell.md` already exists
  and is non-empty, skip it on resume. To regenerate, delete the file
  and re-run.

If a run dies at chapter 28 of 40, re-running picks up at chapter 29.

## Upgrading legacy skills

Skills generated before `extract.py:assign_book_numbers` existed have
`chapters_manifest.json` with `schema_version: 1` (or no version field),
meaning their chapter filenames use extraction-order indices instead of
the book's own chapter numbers — Sethi's Introduction lives at
`chapters/ch07-…` instead of `chapters/intro-…`, etc. The Step 6
legacy-check stops a fresh run on such a skill; the fix is to upgrade
in place.

Two scripts handle this. Both are idempotent (re-running is a no-op):

- **`scripts/backfill_book_numbers.py <skill-dir>`** — parses each
  manifest title, computes the canonical `book_number`, renames every
  `chapters/<old>-<slug>.md` to `chapters/<book_number>-<slug>.md`,
  rewrites cross-references inside the chapter bodies and SKILL.md,
  and bumps `schema_version` to 2. Supports `--dry-run` to preview.
- **`scripts/relabel_nutshell.py <skill-dir>`** — after backfill, fixes
  the cached `nutshell.md` headings (`## ch07 — …` becomes
  `## intro — …`) and the `*From [skill ch07].*` citations.
  Deterministic; no LLM cost.

Detect a legacy skill in one line:

```bash
python3 -c "import json,sys;m=json.load(open(sys.argv[1]));sys.exit(0 if m.get('schema_version')==2 else 1)" "${SKILL_DIR}/chapters_manifest.json" \
  || echo "legacy schema — run scripts/backfill_book_numbers.py ${SKILL_DIR}"
```

Run both after pulling a skill from elsewhere, or any time
`/book-to-skill` complains "Skill uses legacy numbering".

## Quality rules

1. Extract structure, not summaries — frameworks and exact formulations, never
   chapter recaps.
2. Preserve the author's precision — "The 5 Whys" ≠ "ask why a few times".
3. Density over completeness — a tight 1,000-token extraction beats a 6,000-
   token excerpt.
4. Stage 2 builds a concept map; it does not summarise the summaries.
5. The topic index is critical — it is how the two tiers connect.
6. Read images, don't guess them — a figure's meaning comes from a real vision
   read; the description goes into the chapter file as text.
7. Never copy raw book text — always synthesise.
8. Front-load `SKILL.md` — compaction keeps the start, drops the end.
