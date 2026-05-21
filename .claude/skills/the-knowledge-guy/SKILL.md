---
name: the-knowledge-guy
description: >-
  Knowledge router AND interactive teacher across every book-derived skill in
  this project. Two modes — (1) **ask**: auto-discovers all domain skills
  (finance, vuln hunting, AI security, red-teaming, personal growth, ...),
  picks the relevant ones, invokes them in parallel as focused subagents,
  and synthesises one comprehensive cross-domain answer; (2) **walk**:
  proposes a curriculum and walks the user through it interactively — one
  concept at a time, taught from the source chapters, then quizzed via
  forced-choice questions, with progress saved across sessions.
when_to_use: >-
  **Ask mode** triggers — "ask the knowledge guy", "what do my books say
  about", "consult all my skills", "comprehensive answer", "cross-domain",
  "which of my skills covers", any open-ended question.
  **Walk mode** triggers — "walk", "teach", "lesson", "tour", "learn",
  "guide", "teach me", "walk me through", "guide me through", "tour of",
  "lesson on", any argument ending with `--walk`, or the literal "resume".
  **Nutshell mode** triggers — "nutshell <book>", "summarise <book>",
  "summarize <book>", "summary <book>", "tldr <book>" — returns a
  per-chapter micro-summary skim of the whole book.
  **Other artifact triggers** — "compare <topic>", "comparison <topic>",
  "cheatsheet <book>", "glossary [<book>]", "concept map <book>",
  "toolkit <book> <chapter>", "library" / "bookshelf" — each produces
  the matching HTML artifact (see Step 0.5 below for the full list).
allowed-tools: >-
  Bash(ls *) Bash(find *) Bash(cat *) Bash(test *) Bash(pwd)
  Bash(mkdir *) Bash(date *) Bash(grep *)
  Read Write Edit Glob Grep Agent Skill AskUserQuestion
argument-hint: <question>  |  walk <topic>  |  resume  |  nutshell <book>  |  compare <topic>  |  cheatsheet <book>  |  glossary  |  concept-map <book>  |  toolkit <book> <ch>  |  library  |  add <path-to-pdf-or-epub>
---

# the-knowledge-guy — knowledge router + interactive teacher

You are a router across the book-derived skills installed in this project.
Each domain skill is a two-tier knowledge base (concept map + on-demand
chapters) produced by `book-to-skill`. You have **several modes** —
all of them produce both a text response in chat AND an HTML artifact
in `artifacts/` using the shared design system:

- **Ask mode (default)** — fan out parallel subagents and synthesise one
  comprehensive cross-domain essay.
- **Walk mode** — propose a curriculum on a topic, then *teach it
  interactively* with quizzes after each step and progress saved to
  memory so the user can resume across sessions. Procedure in
  [walk-mode.md](walk-mode.md); worked transcripts in
  [examples.md](examples.md).
- **Nutshell mode** — per-chapter micro-summary skim of a whole book.
- **Library mode** — render the bookshelf overview.
- **Comparison mode** — one concept across multiple books, side by side.
- **Cheatsheet mode** — operational one-pager for a book.
- **Glossary mode** — A-Z term lookup, per book or cross-library.
- **Concept-map mode** — Tier-1 framework graph for a book.
- **Toolkit mode** — Tier-2 deep-dive on a specific chapter.
- **Ingest mode** — hand off a PDF/EPUB to `book-to-skill`.

The user's argument is `$QUERY`. Treat the entire argument string as one
value.

---

## Step 0 — Artifacts awareness (do this first, every invocation)

Every output you produce gets written to `artifacts/` at the project
root, using the design system in
`.claude/skills/the-knowledge-guy/design-system/`. The folder is the
user's catalog and your cache. Before doing anything else:

```bash
ARTIFACTS="$(pwd)/artifacts"
test -d "$ARTIFACTS" || mkdir -p "$ARTIFACTS"
ls "$ARTIFACTS" 2>/dev/null
ls "$ARTIFACTS"/nutshells "$ARTIFACTS"/cheatsheets "$ARTIFACTS"/toolkits \
   "$ARTIFACTS"/concept-maps "$ARTIFACTS"/glossaries "$ARTIFACTS"/walks \
   "$ARTIFACTS"/comparisons "$ARTIFACTS"/synthesis 2>/dev/null
```

Use this listing to:

- **Reuse cached artifacts.** Deterministic outputs (nutshell, toolkit,
  cheatsheet, concept-map, per-book glossary, library) have predictable
  filenames — see
  [design-system/layouts.md](design-system/layouts.md) "Filename rules"
  for the full table. If the target file already exists, READ it and
  emit it verbatim; do not regenerate unless `$QUERY` ends with
  `--regenerate`.
- **Surface related artifacts.** If the user asks about Sethi and a
  cheatsheet for sethi-rich-life already exists, mention the path at
  the end of your response so they can open it.
- **Update the index.** After writing any new artifact, regenerate
  `artifacts/index.html` so the catalog stays current. The index is a
  self-contained editorial page listing every file in `artifacts/`
  grouped by use case, most recent first. Use the same design system.

---

## Mode dispatch (after Step 0)

Inspect `$QUERY`, checking in this order:

1. **Resume** — if `$QUERY` is the literal `resume`, **walk mode** (resume
   an existing walk — see walk-mode.md Step 1).
2. **Walk** — starts with `walk`, `teach`, `lesson`, `tour`, `learn`,
   `guide`; OR starts with "teach me", "walk me through", "guide me
   through", "tour of", "lesson on"; OR ends with `--walk` (strip the
   flag, keep the topic) → **walk mode**.
3. **Nutshell** — starts with `nutshell`, `summarise`, `summarize`,
   `summary`, or `tldr` → **nutshell mode**.
4. **Library** — equals `library`, `bookshelf`, `books`, or `shelf`
   (with or without trailing args) → **library mode** below.
5. **Comparison** — starts with `compare`, `comparison`, `comparison of`,
   `vs`, or contains ` vs ` between book/topic tokens → **comparison
   mode** below.
6. **Cheatsheet** — starts with `cheatsheet`, `cheat-sheet`, `cheat sheet`,
   or `reference card` → **cheatsheet mode** below.
7. **Glossary** — starts with `glossary`, `terms`, `define`, or
   `definitions` → **glossary mode** below.
8. **Concept-map** — starts with `concept-map`, `concept map`,
   `framework graph`, `framework map`, `frameworks of`, or `map of` →
   **concept-map mode** below.
9. **Toolkit** — starts with `toolkit`, `chapter`, `deep-dive`, or
   `deep dive` (typically followed by `<skill> <book_number>`) →
   **toolkit mode** below.
10. **Ingest** — `$QUERY` matches any of:
    - contains a token of the form `\S+\.(pdf|epub)` (case-insensitive), OR
    - starts with `add book`, `add this book`, `import book`, `study this`,
      `study pdf`, `study epub`, `convert book`, `convert pdf`,
      `convert epub`, `ingest`, `new book`, `make a skill from`,
      `turn this into a skill`, `book-to-skill`
    → **ingest mode**. Order matters: walk triggers are checked first,
    so "walk me through ~/foo.pdf" still walks an existing skill rather
    than re-importing.
11. **Default** — **ask mode**, continue with this file.

**Walk mode hands off to `walk-mode.md` from its Step 1. Nutshell /
library / comparison / cheatsheet / glossary / concept-map / toolkit /
ingest jump to their named section below. Otherwise continue with the
ask-mode procedure.**

---

## Step 0.5 — HTML emission (applies to every mode)

Every mode below ends with the same final step: **emit an HTML
artifact** to `artifacts/` using the shared design system. The
procedure is identical regardless of mode:

1. Read `.claude/skills/the-knowledge-guy/design-system/shell.html`.
2. Open `design-system/layouts.md` and find the section matching this
   mode. Note the **path**, **title**, **EXTRA_CSS**, and **body
   template**.
3. Substitute mode-specific data into the body template (see each
   layout's `{{}}` placeholders).
4. Substitute `{{TITLE}}` + `{{EXTRA_CSS}}` + `{{BODY}}` into the
   shell.
5. Write the result to `artifacts/<subfolder>/<filename>.html` per
   the layout's path rule.
6. Regenerate `artifacts/index.html` so the catalog reflects the new
   artifact (group it under its use case, most recent first).
7. End your chat response with one line of the form:
   *"🖼  Wrote `artifacts/<subfolder>/<filename>.html` — open it for
   the rich rendering."*

**Cache rule.** Before generating, check whether the target file
already exists. For **deterministic** artifacts (nutshell, toolkit,
cheatsheet, concept-map, per-book glossary, library), reuse the
cached file unless the user passed `--regenerate`. For
**non-deterministic** artifacts (synthesis, comparison, walk-recap),
always create a new dated file.

**Never invent CSS.** Pull the EXTRA_CSS block from `layouts.md`
verbatim. If a layout needs styling beyond what's documented, use
inline `style=""` for one-off tweaks; do not introduce ad-hoc utility
classes. New layouts belong in `layouts.md`, not in arbitrary
artifacts.

---

## Nutshell mode (per-chapter micro-summary skim)

Used when the user wants a whole-book skim — one short block per
chapter, ~100 words each, the whole book in one scrollable response.
The artifact lives at `<skill>/nutshell.md` and is pre-generated at
ingest time by `book-to-skill` (Stage 2.5). For skills ingested before
that stage existed, the file is generated on first request and cached.

### Step N1 — Resolve the target skill

Strip the trigger verb from `$QUERY` (`nutshell`, `summarise`,
`summarize`, `summary`, or `tldr`). The remainder is `$TARGET`.

If `$TARGET` is empty:

> "Which book? Run `/the-knowledge-guy nutshell <skill-slug>` — e.g.
> `nutshell bogle-common-sense-investing`. Installed skills:
> `<list from filesystem>`."

Then stop.

Discover installed skills the same way as Step 1 below:

```bash
SKILLS_ROOT="$(pwd)/.claude/skills"
find "$SKILLS_ROOT" -maxdepth 2 -name SKILL.md
```

Exclude `the-knowledge-guy` and `book-to-skill`. For each remaining
skill, read frontmatter (`Read` with `limit: 40`) and parse `name` +
`description`.

Match `$TARGET` against each skill's slug and the book title that
appears in its description (case-insensitive substring + token overlap):

- **1 match** → use it.
- **0 matches** → tell the user, list installed skills, stop.
- **2+ matches** → use `AskUserQuestion` to disambiguate (up to 4
  options, each option's label is the slug, description is the
  one-line book title).

### Step N2 — Read the cached nutshell (fast path)

```bash
test -f "${SKILL_DIR}/nutshell.md" && cat "${SKILL_DIR}/nutshell.md" > /dev/null && echo EXISTS || echo MISSING
```

If `EXISTS`, `Read` `${SKILL_DIR}/nutshell.md` and emit it verbatim as
the chat response. Then follow **Step 0.5** to render the HTML artifact
at `artifacts/nutshells/<skill-slug>.html` using the layout-1 template
(parse the cached markdown into `book-title` / `book-thesis` / chapters
list). The HTML is cached too — reuse if it exists unless the user
passed `--regenerate`.

### Step N3 — Self-heal (slow path, first request only)

If `nutshell.md` is `MISSING` (skill was ingested before Stage 2.5
existed), generate it now using the same procedure as `book-to-skill`
Step 8.5:

1. Read `${SKILL_DIR}/chapters_manifest.json`.
2. Resolve the book-to-skill install path so you can read the template:

   ```bash
   BTS_DIR="$(find "$SKILLS_ROOT" -maxdepth 2 -type d -name book-to-skill | head -1)"
   test -f "${BTS_DIR}/reference/nutshell-template.md" || { echo "Template missing — cannot generate nutshell"; exit 1; }
   ```

3. Read the template once into memory. Read the one-line thesis from
   `${SKILL_DIR}/raw/spine.md` (the line under `## Thesis`).
4. **Skip** manifest entries whose `word_count < 300` OR whose
   `book_number` starts with `fm` / `bm` (front and back matter — index,
   acknowledgments, copyright, etc.). Even if a front-matter entry is
   long enough, the user does not want it in a skim.
5. Determine each kept chapter's display label:
   - Prefer the manifest entry's `book_number` field (`ch07`, `intro`,
     `preface`, `appendix-a`, …). This is the canonical label —
     `book-to-skill` Stage 2.5 and the backfill script both populate
     it.
   - **Fallback** for extremely old manifests without `book_number`:
     compute one on the fly using the same rules as
     `book-to-skill/scripts/extract.py:assign_book_numbers` (parses
     "Chapter 7 — …", "7. …", "Introduction", "Appendix A", etc.).
     If even that fails, use `ch{index:02d}` as last resort and surface
     a one-line warning at the top of the output.
6. Fan out in a single message: one parallel `Agent` call per remaining
   chapter, `subagent_type: general-purpose`. Each subagent prompt:

   ```
   You are generating one per-chapter nutshell block for a skill skim.

   Read this template (schema + voice rules):
     <inline contents of nutshell-template.md>

   Read this single chapter toolkit file and base your block on it
   ONLY — do not read other chapters, do not invent content:
     <SKILL_DIR>/<chapter file from manifest>

   Context for tone (the book's whole-book thesis):
     <one-line thesis>

   Output exactly one nutshell block following the template's
   "Required shape" — starts with `## <book_number> — <title>`,
   80-120 words, 3-5 bullets. No preamble, no closing remarks, no
   markdown fences.

   Skill slug for the citation line: <SKILL_NAME>
   Book number (use VERBATIM in heading and citation): <book_number>
   Chapter title: <from manifest, with any leading "Chapter N — " /
                  "N. " stripped>
   ```

7. Concatenate returned blocks in manifest order. Prepend:

   ```
   # <Book title> — in a nutshell

   > <one-line thesis from spine.md>
   ```

8. Write the result to `${SKILL_DIR}/nutshell.md` with `Write`.
9. Emit the file contents as the response. Prefix the response with
   one italicised line: *"Generated and cached `nutshell.md` for
   `<skill-slug>` (first request — future calls will be instant)."*

If a subagent fails or returns a malformed block (no `## <book_number>`
heading, or > 180 words), insert a single-line stub for that chapter
(`## <book_number> — <title>\n\n*Nutshell generation failed.*`) and
continue.

Note: to eagerly pre-generate for all installed skills at once, the
user can simply re-run `nutshell <slug>` for each one. No backfill
script is provided.

---

## Library mode (bookshelf overview)

Triggered by `library`, `bookshelf`, `books`, `shelf`.

1. Discover installed skills the same way as Step 1 (filesystem scan,
   exclude self + `book-to-skill`).
2. For each, read frontmatter to get `name`, `description`, and pull
   chapter count from `chapters_manifest.json` if present.
3. Emit the chat response as a short text list (one line per book:
   `<slug> · <N> chapters · <one-line description>`).
4. **Render `artifacts/library.html`** using the layout-10 template in
   `design-system/layouts.md`. Always regenerate this file (it changes
   any time skills are added or removed). Group books into genres
   inferred from each skill's description (security / finance /
   productivity / etc.). Use a representative spine color per book —
   pick a warm/cool palette consistent with the synthesis aesthetic.

---

## Comparison mode (one concept across multiple books)

Triggered by `compare`, `comparison`, `<topic> vs <topic>`.

1. Strip the trigger verb and extract `$TOPIC` plus optional skill
   slugs (`compare margin of safety across graham,housel,bogle`).
2. If no skills are explicitly named, run the **ask-mode routing**
   procedure (Step 1-2 below) to find every skill that plausibly
   touches the topic.
3. Fan out one subagent per skill (same prompt template as Step 3),
   but ask each for **how this skill specifically handles `$TOPIC`** in
   200-300 words with a one-word stance: `agree` / `extend` / `tension`
   relative to the dominant framing.
4. The orchestrator builds 4-6 sub-concepts (rows) and tags each cell
   with the right stance. Render as the layout-5 comparison table.
5. **Render `artifacts/comparisons/YYYY-MM-DD-<topic-slug>.html`**
   using the layout-5 template. Always create a new dated file — every
   comparison is unique.
6. Chat response: a 2-3 sentence summary of where the books converge
   and where they tension, plus the artifact path.

---

## Cheatsheet mode (operational one-pager for a book)

Triggered by `cheatsheet <book>` or `cheat-sheet <book>`.

1. Resolve `<book>` against installed skill slugs the same way Nutshell
   does (substring + fuzzy match, disambiguate via `AskUserQuestion`
   if needed).
2. Check `<skill-dir>/cheatsheet.md` — every book-to-skill output
   includes one. Read it.
3. Convert the markdown cheatsheet into the layout-8 HTML body:
   tables become `<table>`s inside `.block` cards, numbered lists
   become `<ol class="steps">`, bullet lists with operational verbs
   become `<ul class="commands">`. Group 2 columns of cards.
4. **Render `artifacts/cheatsheets/<skill-slug>.html`** using the
   layout-8 template. **Cached** — reuse if it exists unless
   `--regenerate`.
5. Chat response: a tight 5-7 line summary of the most important rules
   from the cheatsheet, plus the artifact path.

---

## Glossary mode (A-Z term lookup)

Triggered by `glossary`, `terms`, `define`, `definitions`.

- **No book argument** → cross-library mode. Walk every installed
  skill's `glossary.md`, merge entries (dedupe by term, keep first
  source), tag each with its source skill. Write to
  `artifacts/glossaries/full-library.html`.
- **Book argument** (`glossary <book>`) → per-book glossary. Read just
  that skill's `glossary.md`. Write to
  `artifacts/glossaries/<skill-slug>.html`.

Render using the layout-7 template (search input, A-Z bar, `<dl>`
entries with source-skill chips and chapter cross-refs). **Cached** —
reuse unless `--regenerate`.

Chat response: the entry the user most likely wanted (best-effort
keyword match against the query), plus the artifact path so they can
browse the full A-Z.

---

## Concept-map mode (Tier-1 framework graph for a book)

Triggered by `concept-map <book>`, `concept map <book>`,
`framework graph <book>`, `frameworks of <book>`.

1. Resolve `<book>` against installed skill slugs.
2. Read the skill's `SKILL.md` and pull out the **thesis** (top section)
   plus the **6-10 core frameworks** (from the concept-map section).
   Each framework has a name, a one-line description, a chapter
   pointer, and may declare relationships to others (`derives-from`,
   `tensions-with`).
3. Position the thesis at the center; arrange the frameworks in a
   loose radial layout (no overlap with the central node). For each
   "tensions-with" relationship between frameworks, add a dashed edge.
4. **Render `artifacts/concept-maps/<skill-slug>.html`** using the
   layout-9 template with the `<svg class="edges">` lines hand-placed
   to match node positions. **Cached** — reuse unless `--regenerate`.
5. Chat response: name the thesis and list the 6-10 frameworks as a
   bullet list, plus the artifact path.

---

## Toolkit mode (Tier-2 deep-dive on one chapter)

Triggered by `toolkit <book> <chapter>`, `chapter <book> <chapter>`,
`deep-dive <book> <chapter>`.

1. Resolve `<book>` to a skill slug.
2. Resolve `<chapter>` to a `book_number` from the skill's
   `chapters_manifest.json` (matches by book_number directly, or by
   chapter title substring).
3. Read `<skill-dir>/chapters/<book_number>-<slug>.md` (the existing
   per-chapter toolkit file produced by Stage 1 of book-to-skill).
4. Convert its sections to the layout-6 HTML body:
   - "Core Idea" → drop-cap lede.
   - "Frameworks Introduced" → one `.frame` block per framework.
   - "Encryption keys" / tables / code → `.ascii` blocks.
   - "Anti-patterns" → `.callout.warn` cards.
   - "Defender's playbook" / good practices → `.callout.good` cards.
5. **Render `artifacts/toolkits/<skill-slug>-<book_number>.html`**
   using the layout-6 template. **Cached** — reuse unless
   `--regenerate`.
6. Chat response: the Core Idea sentence + a 3-bullet "what this
   chapter gives you" summary, plus the artifact path.

---

## Ingest mode (handoff to `book-to-skill`)

Used when the user wants to add a new book to their skills mid-conversation.

### Step I1 — Extract the path

Parse `$QUERY` and find the first token matching `\S+\.(pdf|epub)`
(case-insensitive). Strip surrounding quotes. Expand `~/` to `$HOME/`.
If a second token of the form `[a-z0-9-]+` follows the path, treat it as
the optional skill slug.

If no path is found, print:

> "I detected a book-ingest request, but couldn't find a `.pdf` or
> `.epub` path in your message. Run `/book-to-skill <path>` directly, or
> re-ask me with the path included."

Then stop. Do **not** call `Skill` with a guessed path.

### Step I2 — Validate the path

```bash
test -f "$PATH_VALUE" || { echo "Path not found: $PATH_VALUE"; exit 1; }
```

If the file does not exist, tell the user and stop.

### Step I3 — Mid-walk confirmation (only if a walk is in progress)

Check `$HOME/.claude/projects/-Users-vitaly-MyPlace-projects-the-knowledge-guy/memory/`
for any `walk-*.md` with `Status: in_progress`. If at least one exists,
use `AskUserQuestion` to confirm:

- "Pause the current walk and ingest this book now" (recommended)
- "Cancel — I'll resume the walk first"

If the user picks pause, update the walk memory's `Last updated:` line
to today's date (no other state change — resume logic picks back up).

### Step I4 — Hand off via the Skill tool

Call:

```
Skill(skill="book-to-skill", args="<path> [<slug>]")
```

`book-to-skill` has `context: fork`, so it runs in a fresh fork — the
heavy stages 0-5 output does not pollute this conversation.

### Step I5 — Post-ingest report

When the Skill call returns, summarise the result in 2-3 lines (skill
name created, chapter count if surfaced). Then suggest a next step:

- If a walk was paused: "Run `/the-knowledge-guy resume` to continue the
  paused walk, or `/the-knowledge-guy walk <topic>` to start a walk on
  the newly added skill."
- Otherwise: "Run `/the-knowledge-guy walk <topic>` to start a walk on
  the newly added skill."

---

## Step 1 — Discover installed domain skills

Run this once to enumerate skills:

```bash
SKILLS_ROOT="$(pwd)/.claude/skills"
test -d "$SKILLS_ROOT" || { echo "No .claude/skills dir at $(pwd)"; exit 1; }
find "$SKILLS_ROOT" -maxdepth 2 -name SKILL.md
```

For each `SKILL.md` returned, use `Read` with `limit: 40` to load only the
YAML frontmatter. Parse the `name`, `description`, and `when_to_use`
fields into an in-memory registry.

**Exclude from the registry:**

- `the-knowledge-guy` itself (you are the router; do not recurse).
- `book-to-skill` (it is a *generator* of skills, not a knowledge domain;
  it is reached only via ingest mode above, not via ask/walk routing).
- Any skill whose frontmatter is missing or unparseable — log it but
  continue.

If the registry is empty after exclusions, stop and tell the user:

> "No domain skills are installed yet. Run `/book-to-skill /path/to/book.pdf`
> on a PDF or EPUB to add one, then ask me again."

---

## Step 2 — Route

Match `$QUERY` against each registered skill's combined
`description + when_to_use` text. Pick **every** skill whose vocabulary
plausibly overlaps the query — comprehensive synthesis is the point, so
err on the side of including a skill when in doubt.

Routing rules:

- **Clear single-domain query** (e.g. "how do I bypass AMSI?") → route to
  that one skill only. State the routing decision in one line before
  fanning out.
- **Multi-domain query** (e.g. "how do I find vulnerabilities in an ML
  serving stack?") → route to every plausibly relevant skill.
- **No matches** → route to **all** registered domain skills and tell the
  user no skill was an obvious fit, so you're broadcasting.
- **Meta queries** ("what skills do I have?", "list my books") → answer
  directly from the registry without fanning out.

Before Step 3, print a one-line plan:

> Routing to: `skill-a`, `skill-b` — spawning N parallel subagents.

---

## Step 3 — Fan out (single message, N parallel Agent calls)

In **one message**, emit one `Agent` tool call per matched skill. They run
in parallel; do not call them sequentially. Each subagent:

- `subagent_type`: `general-purpose`
- `description`: `Consult <skill-name>`
- `prompt`: (template below)

Prompt template for each subagent — substitute `<SKILL_NAME>`,
`<SKILL_DIR>` (absolute path), and `<QUERY>`:

```
You are a focused domain expert acting as a single book-skill consultant.

Load ONLY this skill:
  <SKILL_DIR>/SKILL.md

Read its concept map and topic index. If the question maps to specific
chapters, also read those files under <SKILL_DIR>/chapters/. Do not load
any other skill.

Answer this question using ONLY this skill's knowledge:
  <QUERY>

Rules:
- 200-400 words.
- Cite framework names verbatim and reference chapter numbers when you
  draw from them (e.g. "ch07-kerberoasting").
- If the question is outside this skill's domain, reply with a single
  line: "OUT OF SCOPE — <skill-name> doesn't cover this." Do not invent.
- Do not hedge, do not summarise the whole book — answer the question.

Return only your answer; the orchestrator will synthesise across skills.
```

If a subagent fails, note the failure but continue with the others.

---

## Step 4 — Synthesise

Collect every subagent report. Filter out any that returned
`OUT OF SCOPE — …`; keep the skill names for the footer. Then write
**one unified essay** that braids all remaining reports into a single
coherent answer — not a stack of per-skill sections. Shape:

```
## <Title that names the question's core>

<Opening paragraph — the direct answer in 3-5 sentences, already braided
 across skills with inline citations like [bogle-common-sense-investing
 ch3] or [forshaw-windows-security ch14].>

<Body — several paragraphs of unified narrative that integrate every
 consulted skill's contribution. Cite inline at the point of each claim,
 not in trailing per-skill blocks. Where two skills disagree, surface the
 tension in-line ("Graham would call this speculation
 [graham-intelligent-investor ch1]; Housel reframes it as a reasonable
 bet on optimism [housel-psychology-of-money ch5]") rather than smoothing
 it over.>

<Optional visualization — ASCII diagram, flowchart, comparison table, or
 mermaid block — placed where it clarifies a structural concept. See
 visualization rules below.>

<Closing paragraph — what the synthesis implies for the user's situation,
 or what to read next.>

---
**Sources consulted:** `skill-a` · `skill-b` · `skill-c`
**Out of scope:** `skill-x` (filtered)
**Go deeper:** `skill-a` → `chapters/<book_number>-…md` · `skill-b` →
`chapters/<book_number>-…md` (e.g. `ch07-taxes-are-costs-too.md`,
`intro-day-zero.md`, `appendix-a-common-ports.md`)
```

Length scales with the question. Roughly the **sum** of the subagent
reports, not one report — accumulation is the point. But do not pad: if
one skill answered fully, a short essay is the correct output.

### Step 5 — Emit the synthesis HTML artifact

After the chat response, follow **Step 0.5** to render the synthesis
as HTML using the layout-2 template. Path:
`artifacts/synthesis/YYYY-MM-DD-<query-slug>.html`. Always create a
new file (every ask is unique). The HTML version uses the same
paragraphs, the same `<span class="cite">` chips, the same `.pull`
quote, the same `.ascii` block; do not re-do the synthesis work — just
re-encode the text response into the layout-2 body template. End your
response with the artifact path so the user can open it.

### Visualization rules

- Add a visualization **whenever it aids understanding** of a structural
  concept: an ordered process, a hierarchy, a comparison across 3+
  items, a decision tree, a timeline, a state machine, or a tradeoff
  matrix. Skip for purely factual or single-claim answers.
- Prefer **ASCII diagrams** and **markdown tables** — they always
  render in the terminal. Use **mermaid** blocks only for graphs/flows
  the user will view in a renderer.
- At most one visualization per answer, unless the question genuinely
  spans multiple structural concepts.
- Caption it with a one-line source attribution, e.g. *"Kerberos
  AS/TGS/AP exchange — adapted from [forshaw-windows-security ch14]"*.
- Never invent structure not present in the consulted skills. A
  visualization re-presents cited content; it is not new analysis.

---

## Quality rules

1. **Never read a domain SKILL.md yourself.** That is the subagents' job.
   You only read frontmatter (≤ 40 lines per skill) for routing.
2. **Always fan out in parallel** — one message with N `Agent` calls.
   Sequential fan-out defeats the design.
3. **Cite inline at the point of each claim**, using the form
   `[skill-name <book_number>]` — `book_number` is the book-native
   label from `chapters_manifest.json` (`ch07`, `intro`, `preface`,
   `appendix-a`). Never use the manifest `index`. No trailing per-skill
   "perspectives" blocks — the essay is unified, citations live where
   the claim does.
4. **Don't invent across skills.** If two skills disagree, surface the
   disagreement; do not paper over it with a smoothed consensus.
5. **Drop-in extensibility is sacred.** Never hardcode skill names in
   routing logic — always re-discover from the filesystem.
6. **Exclude `book-to-skill` and self** from routing, every time.
7. **Visualize structural concepts.** When the answer describes a
   process, hierarchy, comparison, or tradeoff, include an ASCII
   diagram, table, or mermaid block per the visualization rules in
   Step 4.
