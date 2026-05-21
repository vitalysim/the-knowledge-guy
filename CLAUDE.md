# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **Claude Code skill library**, not an app. There is no build step, no
test runner, no entry point. Two installed entry points carry the whole
system:

- **`/book-to-skill`** (`.claude/skills/book-to-skill/`) — the **ingest
  pipeline**. Map-reduce in 5 stages (Stage 0 EXTRACT → Pass 0 SPINE →
  Stage 1 MAP → Stage 2 REDUCE → Stage 2.5 NUTSHELL) that turns a
  PDF/EPUB into a two-tier knowledge skill: ~3K-token always-loaded
  `SKILL.md` + on-demand `chapters/<book_number>-<slug>.md` toolkits.
  Plumbing in Python (`scripts/extract.py`), intelligence in Claude
  (Stages 1 & 2 are LLM-driven subagent fan-outs).
- **`/the-knowledge-guy`** (`.claude/skills/the-knowledge-guy/`) — the
  **router + interactive teacher** across every installed domain skill.
  Auto-discovers them by scanning `.claude/skills/*/SKILL.md` at every
  invocation. **Eleven modes**: `ask` (default — parallel cross-domain
  synthesis essay), `walk` (interactive curriculum + quizzes, progress
  saved to `~/.claude/projects/<this project>/memory/walk-*.md`),
  `nutshell`, `library`, `comparison`, `cheatsheet`, `glossary`,
  `concept-map`, `toolkit`, `ingest`, `resume`.

**Domain skills** (one per ingested book, e.g. `forshaw-windows-security/`,
`sethi-rich-life/`) are the artifacts `book-to-skill` produces. Each is
independently invokable as `/<slug>`. They are *outputs* of the system,
not part of its surface — treat them as interchangeable demonstrations.

Read `README.md` for the user-facing narrative. Read
`.claude/skills/book-to-skill/SKILL.md` for the pipeline procedure (this
*is* the runbook). Read
`.claude/skills/the-knowledge-guy/SKILL.md` for the router behavior and
all eleven modes.

## Canonical chapter labels — `book_number` (schema_version 2)

The single most important architectural fact, easy to get wrong:

- Every manifest entry has a `book_number` (`ch07`, `intro`, `preface`,
  `appendix-a`, `part-1`, `fm`, `fm-2`, `bm`, …). This is the **only**
  user-facing chapter label. It is the filename prefix, the heading in
  `nutshell.md`, the citation in walks and ask-mode answers.
- The manifest also has `index` — extraction order, 1..N over everything
  the extractor produced (front matter included). **`index` is internal
  only.** Using it in filenames or labels reintroduces the off-by-N
  drift bug that this codebase already fought once.
- Source of truth: `book-to-skill/scripts/extract.py:parse_book_number_kind`
  + `assign_book_numbers`. Display-side renderers (the-knowledge-guy
  nutshell mode, walk-mode.md, citations) must read `book_number` from
  `chapters_manifest.json`, never reconstruct it.

A manifest at `schema_version: 1` is **legacy**. Step 6 of book-to-skill
stops on encountering one and tells the user to run
`backfill_book_numbers.py`. Don't try to "just continue".

## Every output is an HTML artifact

Every `/the-knowledge-guy` invocation writes **both** text to chat and
a self-contained HTML artifact to `artifacts/` at the project root. The
folder is the user's catalog and the skill's cache:

```
artifacts/
├── index.html                              ← auto-updated catalog
├── library.html                            ← bookshelf overview
├── nutshells/<book-slug>.html              ← cached, deterministic
├── synthesis/YYYY-MM-DD-<slug>.html        ← dated, accumulates
├── walks/<topic>-step-<N>.html             ← overwritten per step
├── walks/<topic>-recap.html                ← durable
└── comparisons/  toolkits/  cheatsheets/
    concept-maps/  glossaries/              ← cached per slug
```

The design system is **Knowledge Guide · Modern** at
`.claude/skills/the-knowledge-guy/design-system/` — Bricolage
Grotesque + JetBrains Mono, single cobalt accent, light/dark +
density toggle persisted in `localStorage`, 24 named components.
Three files there:

- `shell.html` — the wrapper. Placeholders `{{TITLE}}`,
  `{{EXTRA_CSS}}`, `{{BODY}}`. Read it, substitute, write.
- `layouts.md` — one section per use case (nutshell / synthesis /
  walk-session / walk-recap / comparison / toolkit / glossary /
  cheatsheet / concept-map / library). Each has the path under
  `artifacts/`, the title, EXTRA_CSS (usually empty — the shell
  already has every component), and the body template.
- `reference/full-demo-light.html` + `-dark.html` — canonical visual
  contract of every component, in both themes.

**Never invent CSS.** Pull EXTRA_CSS from `layouts.md` verbatim. If
you need a one-off tweak, use inline `style=""`. New utility classes
belong in `shell.html`, added deliberately — never per-artifact.

After writing any artifact, regenerate `artifacts/index.html` so the
catalog reflects the new file. Deterministic outputs (nutshell,
toolkit, cheatsheet, concept-map, per-book glossary, library) are
**cached** — reuse the existing file on repeat invocations unless the
user passes `--regenerate`. Non-deterministic ones (synthesis,
comparison, walk-recap) get dated filenames and accumulate.

## Operational commands

These are real scripts in `.claude/skills/book-to-skill/scripts/`. All
are idempotent.

```bash
# Upgrade a legacy (schema_version=1) skill in place
./book-to-skill/scripts/backfill_book_numbers.py <skill-dir> [--dry-run]

# After backfill, resync labels + citations in cached nutshell.md
./book-to-skill/scripts/relabel_nutshell.py <skill-dir> [--dry-run]

# Rewrite stale `slug/chNN` shorthand inside walk memory after backfill
./book-to-skill/scripts/upgrade_walk_memory.py [memory-dir] [--dry-run]

# Quality lint a skill's chapter toolkit files (verbatim-copy detection,
# size sanity, missing headings). Uses the manifest to resolve raw paths,
# so it works for chapters named intro/appendix-a/fm as well as chNN.
./book-to-skill/.venv/bin/python ./book-to-skill/scripts/lint_chapters.py <skill-dir>

# Provision the per-skill Python venv (one-time)
./book-to-skill/scripts/setup.sh
```

The slash commands themselves (`/book-to-skill`, `/the-knowledge-guy`,
`/<book-slug>`) are how the user invokes everything — they execute via
Claude Code's skill runtime; do not try to call them from bash.

## Where to read before editing

| Editing… | Read first |
|---|---|
| Pipeline behavior, stages | `book-to-skill/SKILL.md` (the runbook) |
| Manifest schema, including `book_number` vocabulary | `book-to-skill/reference/concept-map-spec.md` |
| Per-chapter toolkit shape | `book-to-skill/reference/chapter-template.md` |
| Per-chapter nutshell shape + numbering rule | `book-to-skill/reference/nutshell-template.md` |
| Genre-specific extraction profiles | `book-to-skill/reference/genre-profiles.md` |
| Routing, ask synthesis, and the 11 modes | `the-knowledge-guy/SKILL.md` |
| Walk mode procedure | `the-knowledge-guy/walk-mode.md` |
| Worked walk transcripts | `the-knowledge-guy/examples.md` |
| HTML artifact layouts (one per use case) | `the-knowledge-guy/design-system/layouts.md` |
| HTML shell + design tokens | `the-knowledge-guy/design-system/shell.html` |
| Visual contract for every component | `the-knowledge-guy/design-system/reference/full-demo-light.html` |
| Artifact catalog conventions | `artifacts/README.md` |

## Architecture details that span files

- **`extract.py` is pure plumbing.** It does PDF/EPUB → text + images +
  per-chapter raw slices + `metadata.json`. It assigns `book_number` to
  each chapter via `assign_book_numbers` (single source of truth). It
  never summarises — *every* act of understanding happens in Claude.
- **Stages 1 and 2 are LLM-driven subagent fan-outs**, not Python. Stage
  1 maps over chapters (one subagent per chapter, parallel). Stage 2
  reduces over the chapter toolkit files to produce the concept map +
  indexes. Both are driven by prompts in `book-to-skill/SKILL.md`.
- **Resume is filesystem-driven**, not log-driven. A `chapters/<…>.md`
  that exists, is > 500 bytes, and lacks "extraction failed" counts as
  done. Stage 2 only runs once all chapter files exist. `progress.json`
  is a log, not the source of truth.
- **`raw/` stays with the skill.** Every domain skill keeps the
  original `full_text.txt`, per-chapter raw `.txt` slices, images,
  `metadata.json`, and `spine.md` inside `<slug>/raw/`. Re-extracting a
  single chapter never needs to rerun Stage 0.
- **The router never reads a domain `SKILL.md`.** It reads only
  frontmatter (≤ 40 lines per skill) for routing decisions, then fans
  out subagents that each load exactly one `SKILL.md`. Adhere to this —
  reading domain `SKILL.md`s in the router will blow context budgets on
  any non-trivial library.
- **Every mode emits an HTML artifact.** Step 0.5 of
  `the-knowledge-guy/SKILL.md` documents the universal procedure: read
  `design-system/shell.html`, find the matching layout in
  `design-system/layouts.md`, substitute, write to
  `artifacts/<subfolder>/<filename>.html`, refresh
  `artifacts/index.html`. Caching rules per the artifacts section
  above; non-deterministic outputs always create a new dated file.

## Conventions to preserve when editing

- **Cite chapters as `[skill-name <book_number>]` inline** at the point
  of each claim, never in trailing per-skill perspective blocks.
- **Nutshell mode skips entries** where `word_count < 300` **or**
  `book_number` starts with `fm` / `bm` (any front/back matter, even
  long ones). See `book-to-skill/SKILL.md` Step 8.5.
- **Filenames are `<book_number>-<slug>.md`** in `chapters/`. The slug
  is normalised lower-kebab without redundant prefixes
  (`backfill_book_numbers.py:_strip_redundant_prefix` handles cleanup).
- **Drop-in extensibility is sacred** — never hardcode skill slugs in
  routing or rendering. The router rediscovers skills every invocation.
- **Design system: never invent CSS in an artifact.** Pull the
  EXTRA_CSS block from `the-knowledge-guy/design-system/layouts.md`
  verbatim. New components or utility classes go in
  `design-system/shell.html`, edited deliberately; one-off tweaks
  inside an artifact use inline `style=""`. Family coherence across
  every output is the whole point.
- **Citations in ask/synthesis** are inline `[skill-slug <book_number>]`
  in chat text, and `.source` cards (per the demo) in the HTML artifact.
  Don't trail per-skill perspective blocks at the end — the essay is
  unified.

## Walk memory

Walks save state to `~/.claude/projects/<this project>/memory/walk-<slug>.md`.
The file uses shorthand like `housel/ch04` for chapter references; this
shorthand is bound to the *current* `book_number` numbering and will
drift if a skill is re-backfilled. Run `upgrade_walk_memory.py` after
any pipeline change that renumbers chapters.

## Things you should NOT do

- Do not run `book-to-skill/scripts/extract.py` directly to "test it" on
  a real book without coordinating — extraction is hash-cached and
  produces a `.venv` and ~hundreds of MB of cache.
- Do not delete `raw/` from a domain skill. It is part of the skill.
- Do not commit generated artifacts (chapter files, nutshells) from an
  in-progress book ingest — wait for the run to finish; Stage 2
  validation will flag failed chapters.
- Do not assume `chNN` in a filename equals book chapter N. The legacy
  bug this codebase fixed was exactly that conflation.
- Do not write HTML directly into `previews/`. That directory is the
  frozen design exploration; live outputs go to `artifacts/`.
- Do not edit `artifacts/index.html` by hand expecting it to persist —
  it's regenerated on every artifact write.
- Do not introduce a second accent color into the design system. One
  saturated accent (cobalt) is load-bearing; semantic colors
  (`--ok`, `--warn`, `--crit`, `--insight`) are for actual state, used
  sparingly.
