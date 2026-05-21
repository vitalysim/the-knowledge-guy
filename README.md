# the-knowledge-guy

> Turn any PDF or EPUB into a structured Claude Code skill —
> then ask your whole bookshelf a single question.

```
        ┌─────────────────────────────────────────────────────┐
        │  /book-to-skill /path/to/book.pdf                   │
        └────────────────────────────┬────────────────────────┘
                                     ▼
   Stage 0    EXTRACT     PyMuPDF → text + images + chapter slices
   Pass  0    SPINE       fast read of ToC + intros → thesis + frameworks
   Stage 1    MAP         one chapter → one toolkit file   (parallel subagents)
   Stage 2    REDUCE      chapter files → concept map + topic index → SKILL.md
   Stage 2.5  NUTSHELL    chapter files → per-chapter ~100-word skim

        ┌─────────────────────────────────────────────────────┐
        │  /the-knowledge-guy <question>                      │
        └────────────────────────────┬────────────────────────┘
                                     ▼
   ask · walk · nutshell · library · comparison · cheatsheet ·
   glossary · concept-map · toolkit          →  artifacts/*.html
```

*From a PDF on disk to a queryable knowledge skill in one command;
from a question to a cross-domain answer in another.*

---

## What this is

A long book is 400K+ tokens; you forget the middle by the end; asking
a question that spans three books is impossible. Existing tools
either stuff everything into context (expensive, forgetful) or
hand-write summaries (lossy, immediately stale).

`/book-to-skill` is a **map-reduce ingest pipeline** that turns a
PDF or EPUB into a two-tier Claude Code skill: an always-loaded
concept map (~3K tokens — thesis, 6-10 load-bearing frameworks,
chapter and topic indexes) plus on-demand chapter toolkits (~1K
tokens each — frameworks, techniques, anti-patterns, worked
examples). A 600-page book becomes a skill that costs a few thousand
tokens to consult instead of four hundred.

`/the-knowledge-guy` is the **router and interactive teacher** across
every installed skill. It auto-discovers skills from the filesystem
at every invocation, routes any question to every plausibly relevant
book in parallel, and synthesises one answer with inline citations.
It can also teach a topic step by step with quizzes and resumable
progress.

The architectural rule that holds it together: **plumbing in Python,
intelligence in Claude.** `extract.py` does mechanical PDF → text +
slices + image manifest, and that is *all* it does. Every act of
understanding — framework extraction, concept mapping, synthesis,
quiz authoring — is an LLM call.

Both skills follow Anthropic's `SKILL.md` open standard — consumed
natively by Claude Code, Claude Desktop, claude.ai, the Claude API,
OpenAI Codex CLI, and GitHub Copilot. See *Install on your platform*
below.

## Quick start

```bash
/book-to-skill /path/to/book.pdf                                  # ingest
/the-knowledge-guy what do my books say about margin of safety?   # ask
/the-knowledge-guy walk me through Kerberos                       # tutor
/the-knowledge-guy nutshell <skill-slug>                          # skim
/the-knowledge-guy resume                                         # resume
```

Every invocation also writes a self-contained HTML artifact to
`artifacts/`.

## The system, in two pieces

### `/book-to-skill` — the ingest pipeline

Map-reduce in five stages (see the hero diagram). What's worth
knowing:

- **Two-tier output.** `SKILL.md` is always loaded;
  `chapters/<book_number>-<slug>.md` is paged in on demand. The
  tier-1 file is front-loaded so compaction keeps the start safely.
- **`book_number` is the canonical chapter label** — `ch07`, `intro`,
  `appendix-a`, `part-1`, `fm`, `bm`. The book's own chapter numbers,
  never extraction order. The manifest also carries an internal
  `index` — never user-facing.
- **`schema_version: 2`** plus three idempotent helper scripts so
  legacy skills upgrade in place without re-extracting.
- **Resume is filesystem-driven.** Re-running on a partial run is
  always safe; chapter files in `chapters/` are the checkpoint.
- **`raw/` stays with the skill** — full text, slices, images,
  metadata, Pass-0 spine. Re-extracting one chapter never re-runs
  Stage 0.
- **Seven genre profiles** (technical / vuln-hunting / financial /
  scientific / productivity / narrative non-fiction / general) tune
  chunk boundaries, the chapter schema, and the reduce emphasis.

### `/the-knowledge-guy` — the router + teacher

Auto-discovery, no registry. Reads `.claude/skills/*/SKILL.md`
frontmatter at every invocation; drop a skill in, the router picks it
up on the next call. Excludes itself and `book-to-skill` from
routing, every time.

| Mode | What it does | Trigger |
| ---- | ------------ | ------- |
| **ask** | Cross-domain synthesis essay with inline citations | open-ended question |
| **walk** | Interactive curriculum with quizzes, progress saved across sessions | `walk me through <topic>` |
| **nutshell** | Whole-book per-chapter skim (~100 words/chapter) | `nutshell <book>` |
| **library** | Bookshelf overview | `library` |
| **comparison** | One concept across multiple books, tagged agree / extend / tension | `compare <topic>` |
| **cheatsheet** | Operational one-pager per book | `cheatsheet <book>` |
| **glossary** | A-Z term lookup, per-book or cross-library | `glossary [<book>]` |
| **concept-map** | Tier-1 framework graph for a book | `concept-map <book>` |
| **toolkit** | Tier-2 deep dive on one chapter | `toolkit <book> <chapter>` |
| **ingest** | Hand off a PDF/EPUB to `book-to-skill` | `add <path>.pdf` |
| **resume** | Pick up an interrupted walk | `resume` |

Ask mode never reads a domain `SKILL.md` itself — it reads only the
40-line frontmatter for routing, then fans out one parallel subagent
per matched skill. Each subagent loads exactly one book and answers
in 200-400 words with chapter citations. The orchestrator synthesises
the reports into one unified essay.

## Every output is also an HTML artifact

Every invocation writes both text to chat *and* a self-contained HTML
file to `artifacts/`, using a shared design system ("Knowledge Guide
· Modern" — Bricolage Grotesque + JetBrains Mono, single cobalt
accent, light/dark + density toggle persisted in `localStorage`).
Catalog at `artifacts/index.html` is auto-updated on every write.

```
artifacts/
├── index.html                              ← auto-updated catalog
├── library.html                            ← bookshelf overview
├── nutshells/<book-slug>.html              ← cached, deterministic
├── synthesis/YYYY-MM-DD-<query-slug>.html  ← dated, never reused
├── walks/<topic>-step-<N>.html             ← overwritten per step
├── walks/<topic>-recap.html                ← durable
└── comparisons/  toolkits/  cheatsheets/
    concept-maps/  glossaries/              ← cached per slug
```

Deterministic outputs (nutshell, toolkit, cheatsheet, concept-map,
per-book glossary, library) are cached and reused; non-deterministic
ones (synthesis, comparison, walk-recap) accumulate as dated files.
The design system lives at
[`.claude/skills/the-knowledge-guy/design-system/`](./.claude/skills/the-knowledge-guy/design-system/)
— `shell.html`, `layouts.md`, and a full visual contract at
`reference/full-demo-light.html`.

## Honest limitations

- Optimised for 50–500 page **technical or non-fiction prose**.
  Cookbooks, reference manuals, and dense math textbooks extract
  less cleanly.
- Stage 0 requires PyMuPDF; scanned PDFs without an OCR layer fall
  back to text-only (no figures).
- Image-heavy books cost extra at extraction time — the pipeline
  reads every kept figure with a vision call.

## Design principles

1. **Auto-discovery over configuration.**
2. **Two tiers per skill — Tier 1 always loaded, Tier 2 paged in.**
3. **Plumbing in Python, intelligence in Claude.**
4. **Parallel by default** — multi-skill answers and multi-step
   teaching both fan out in a single message.
5. **Raw stays with the skill** — re-extraction never re-runs Stage 0.
6. **Filesystem-driven resume; idempotent upgrade scripts.**

## Repository layout

```
the-knowledge-guy/
├── README.md · CLAUDE.md
├── artifacts/                  ← every HTML output lands here
└── .claude/skills/
    ├── book-to-skill/
    │   ├── SKILL.md            ← pipeline runbook
    │   ├── reference/          ← templates, genre profiles, concept-map spec
    │   └── scripts/            ← extract.py · detect_chapters.py · lint_chapters.py
    │                             backfill_book_numbers.py · relabel_nutshell.py
    │                             upgrade_walk_memory.py
    ├── the-knowledge-guy/
    │   ├── SKILL.md            ← mode dispatch + all modes
    │   ├── walk-mode.md        ← interactive curriculum + quiz procedure
    │   └── design-system/      ← shell.html · layouts.md · reference/
    └── <book-derived skills>/  ← one per ingested book
```

## Install on your platform

This repo ships **two skills** — `book-to-skill` and
`the-knowledge-guy`. Both must be installed. Generated book-skills
(from running `/book-to-skill`) sit alongside them and are picked
up by the router automatically. Requires
[`uv`](https://docs.astral.sh/uv/) for the per-skill Python venv
(PyMuPDF + ebooklib + beautifulsoup4 + pypdf).

### Universal install — clone once, symlink everywhere

Covers Claude Code + Claude Desktop in one step:

```bash
git clone https://github.com/vitalysim/the-knowledge-guy.git ~/the-knowledge-guy
mkdir -p ~/.claude/skills
ln -s ~/the-knowledge-guy/.claude/skills/book-to-skill      ~/.claude/skills/
ln -s ~/the-knowledge-guy/.claude/skills/the-knowledge-guy  ~/.claude/skills/
~/the-knowledge-guy/.claude/skills/book-to-skill/scripts/setup.sh
```

Symlinking (rather than copying) means `git pull` upgrades both
skills in place. Other platforms (web, API, Codex, Copilot) add a
second link, a ZIP upload, or an API registration — see below.

### Claude Code (CLI) — `~/.claude/skills/`

The universal install above covers this. Project-scoped alternative:
drop the two skills into `<your-project>/.claude/skills/` instead.
Skills hot-reload — no restart needed.
Docs: <https://code.claude.com/docs/en/skills>

### Claude Desktop (macOS / Windows) — shared user-scope dir

The desktop app reads the same `~/.claude/skills/` as the CLI. If
you ran the universal install, the app picks the skills up on next
launch. Available on Free / Pro / Max / Team / Enterprise since
April 13, 2026.
Docs: <https://support.claude.com/en/articles/12512180-use-skills-in-claude>

### claude.ai (web) — ZIP upload via Settings

```bash
cd ~/the-knowledge-guy/.claude/skills
zip -r book-to-skill.zip      book-to-skill
zip -r the-knowledge-guy.zip  the-knowledge-guy
```

Then in claude.ai: **Settings → Customize → Skills → Create skill →
Upload .zip**. Repeat for each ZIP. Requires Code Execution + File
Creation enabled. Note: claude.ai can't write to a local
`artifacts/` folder — HTML artifacts in web sessions render inline
in the chat container instead.
Docs: <https://support.claude.com/en/articles/12512180-use-skills-in-claude>

### Anthropic API / Agent SDK — `container.skills`

Register each skill as a custom skill, then reference both in
`container.skills` with the beta header (code execution must be
enabled; up to 8 skills per request):

```python
client.messages.create(
    model="claude-opus-4-7", max_tokens=4096,
    container={"skills": [{"type": "custom", "skill_id": "<id-1>"},
                          {"type": "custom", "skill_id": "<id-2>"}]},
    extra_headers={"anthropic-beta": "skills-2025-10-02,code-execution-2025-08-25"},
    messages=[{"role": "user", "content": "/the-knowledge-guy library"}],
)
```

Docs: <https://platform.claude.com/docs/en/build-with-claude/skills-guide>

### OpenAI Codex CLI — `~/.agents/skills/`

Codex CLI (since Dec 2025) consumes `SKILL.md` as-is from
`~/.agents/skills/`:

```bash
mkdir -p ~/.agents/skills
ln -s ~/the-knowledge-guy/.claude/skills/book-to-skill      ~/.agents/skills/
ln -s ~/the-knowledge-guy/.claude/skills/the-knowledge-guy  ~/.agents/skills/
```

Codex's tool runtime differs from Claude Code's (no `Skill` tool, no
`AskUserQuestion`), so the **walk** and **ingest** modes degrade to
prompted-text fallbacks; **ask**, **nutshell**, **library**, and the
other read-only modes work directly.
Docs: <https://developers.openai.com/codex/skills>

### GitHub Copilot — `.github/skills/` per repo

Copilot's skill support (April 2026) is project-scoped. For each
repo where you want the skills available:

```bash
cd <your-repo>
mkdir -p .github/skills
cp -R ~/the-knowledge-guy/.claude/skills/book-to-skill      .github/skills/
cp -R ~/the-knowledge-guy/.claude/skills/the-knowledge-guy  .github/skills/
```

Active in Copilot's agent mode. The Python venv assumed by
`book-to-skill` won't exist in Copilot's container — ingest mode
doesn't run there; query modes do.
Docs: <https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills>
and <https://code.visualstudio.com/docs/copilot/customization/agent-skills>

### Porting to platforms without native skill support

- **Cursor IDE** — uses `.cursor/rules/*.mdc`; adaptation is
  mechanical (frontmatter conversion + per-file split).
  [Docs](https://cursor.com/docs/rules).
- **Zed Editor** — native support pending
  ([zed#49057](https://github.com/zed-industries/zed/issues/49057));
  paste `SKILL.md` content into the system prompt in the interim.
- **Cline / Roo / Aider / Continue** — no standardised skills
  mechanism as of May 2026; stopgap is to paste the runbook text
  from `book-to-skill/SKILL.md` and `the-knowledge-guy/SKILL.md`
  into the platform's system-prompt or rules file.

### Compatibility matrix (May 2026)

| Platform | Native skills? | Install location | Consumes `SKILL.md` as-is? |
| --- | --- | --- | --- |
| **Claude Code (CLI)** | ✓ | `~/.claude/skills/` or `./.claude/skills/` | yes |
| **Claude Desktop** (mac/win) | ✓ | `~/.claude/skills/` | yes |
| **claude.ai** (web) | ✓ | Settings → Customize → Skills (ZIP upload) | yes |
| **Anthropic API / Agent SDK** | ✓ | `container={"skills":[…]}` + beta header | yes |
| **OpenAI Codex CLI** (Dec 2025+) | ✓ | `~/.agents/skills/` | yes |
| **GitHub Copilot** (Apr 2026+) | ✓ | `.github/skills/` per repo | yes |
| **Cursor IDE** | needs adapt | `.cursor/rules/*.mdc` | no — manual conversion |
| **Zed Editor** | pending | — | — |
| **Cline / Roo / Aider / Continue** | no | — | — |

After install, ingest your first book with
`/book-to-skill /path/to/book.pdf` (genre prompt → cost estimate →
name). A 600-page book takes ~10-20 min wall-clock and roughly $1-3
in API costs depending on model.

## Upgrading legacy skills

Three idempotent helper scripts handle older skills:
`backfill_book_numbers.py` populates `book_number` and renames
chapter files, `relabel_nutshell.py` fixes cached nutshell headings
after backfill, `upgrade_walk_memory.py` rewrites stale
`<slug>/chNN` shorthand inside walk memory. All three are no-ops on
already-current skills.

## What's next

Designed for but not shipped: voice-mode walks, spaced repetition on
the recorded fumbles, remote channels (desktop / claude.ai), and a
mastery view across overlapping walks.
