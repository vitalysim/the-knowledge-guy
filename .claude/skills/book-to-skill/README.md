# book-to-skill

Convert a technical or non-fiction book (PDF or EPUB) into a structured Claude
Code skill — one that is **expert by default and deep on demand**.

The generated skill is not a summary. It is a two-tier knowledge base:

- **`SKILL.md`** — always loaded. A concept map of the book's frameworks and
  how they connect, plus a topic index. This makes Claude reason like someone
  who has internalised the book.
- **`chapters/`** — loaded on demand. The detail: each chapter's exact
  techniques, code, tables, anti-patterns, and figure descriptions. Paged in
  only when the concept map is not enough.

A 600-page book becomes a skill that costs a few thousand tokens to consult,
not 400K.

**Output location.** Generated skills are written to the **current project's**
`./.claude/skills/<slug>/` — never to `~/.claude/skills/`. Run
`/book-to-skill` from the project where you want the skill to live.

## What makes this version different

- **Map-reduce pipeline.** Each chapter is extracted independently (the *map*),
  then a *reduce* pass reads all the chapter extractions and builds a concept
  map — relationships that no single chapter contains. It does not summarise
  summaries.
- **Handles images.** Embedded figures are extracted and anchored inline; the
  skill reads them with Claude Code's native image understanding and folds the
  meaning into the chapter files as text.
- **Handles scanned books.** Image-only pages are detected and rendered;
  vision reads them as text. A scanned PDF that other converters reject just
  works (at a higher cost, which the pre-flight estimate shows you).
- **Genre-aware.** Six genre profiles change the chunk boundary and extraction
  schema — a vuln-hunting book and a productivity book are not extracted the
  same way.
- **Survives long books.** Chapters run as parallel subagents; the run is
  checkpointed and re-running resumes where it stopped.
- **Pre-flight cost estimate** before any generation.

## Install

This skill uses [`uv`](https://docs.astral.sh/uv/) for Python virtual-env and
package management. Install it first if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # or: brew install uv
```

Then copy the `book-to-skill/` folder into your skills directory and run the
setup script:

```bash
cp -r book-to-skill ~/.claude/skills/
bash ~/.claude/skills/book-to-skill/scripts/setup.sh
```

`setup.sh` creates a uv-managed venv at
`~/.claude/skills/book-to-skill/.venv` and installs PyMuPDF, ebooklib,
beautifulsoup4, and pypdf into it. The extractor is always invoked through
that venv — no system-Python pollution, no `pip --break-system-packages`.

If you received this as a `.skill` file, install it the way you install any
Claude Code skill, then run `setup.sh` once.

## Use

In Claude Code:

```
/book-to-skill ~/books/ddia.pdf
/book-to-skill ~/books/the-web-application-hackers-handbook.pdf wahh
/book-to-skill ~/books/thinking-in-systems.epub          # proposes a name
/book-to-skill ~/papers/some-book.pdf — analyze only     # preview, no files
```

Then use the generated skill:

```
/<slug>            load the concept map and core frameworks
/<slug> <topic>    find and explain a topic — jumps to the right chapter
/<slug> ch07       open a specific chapter
```

## How it works

```
Stage 0  EXTRACT   scripts/extract.py → text + images + per-chapter slices
Pass 0   SPINE     thesis + framework inventory, fed to every chapter extractor
Stage 1  MAP       each chapter → one chapter file   (parallel subagents)
Stage 2  REDUCE    all chapter files → concept map + topic index → SKILL.md
```

`scripts/extract.py` is pure plumbing — mechanical text/image extraction only.
All understanding (what a framework is, what a figure means, how concepts
relate) is done by Claude while executing `SKILL.md`.

## Layout

```
book-to-skill/
├── SKILL.md                      orchestration procedure
├── README.md
├── requirements.txt
├── scripts/
│   ├── extract.py                Stage 0 — text, images, offsets, scan detection
│   └── setup.sh                  dependency installer
└── reference/
    ├── genre-profiles.md         6 genre profiles (unit / boundary / schema)
    ├── chapter-template.md       Stage 1 per-chapter output schema
    └── concept-map-spec.md       Stage 2 concept map + topic index + SKILL.md template
```

## Requirements

- Claude Code with subagent (`Task`) support for parallel chapter extraction.
- [`uv`](https://docs.astral.sh/uv/) for venv + package management.
- Python 3.10+ (uv will fetch one if your system doesn't have it).
- PyMuPDF for image and scanned-page support. Without it the extractor falls
  back to text-only and skips images.

## Limitations

- Multi-column layouts beyond two columns are not reconstructed precisely.
- Scanned books are supported but cost more (every page is a vision read) —
  the pre-flight estimate makes this visible before you commit.
- DRM-protected files cannot be opened.
