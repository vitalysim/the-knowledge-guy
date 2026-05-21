# Concept Map Spec — Stage 2 (Reduce) Output

Stage 2 reads **all** the chapter files from Stage 1 and produces the
**expert tier**: the `SKILL.md` the user loads. The generated `SKILL.md` is
what makes Claude behave like someone who has internalised the book.

The critical rule: Stage 2 **builds a concept map, it does not summarise the
summaries.** Summarising chapter summaries just yields a shorter book report
and loses detail twice. A concept map is a different artifact — *nodes and
edges*: the concepts the book teaches and how they relate. Those relationships
live *between* chapters, so no single chapter file contains them; surfacing
them is the whole point of the reduce step.

## Reduce procedure

1. Read every `chapters/ch*.md` file and the `spine.md` from Pass 0.
2. **Consolidate** — this is the real work, and it is not summarisation:
   - Deduplicate frameworks that recur across chapters into one node.
   - Resolve refinements — where a later chapter sharpens a concept
     introduced earlier, merge into one node and note the progression.
   - For `financial` / `scientific` genres: do **not** over-merge — the same
     term across chapters can mean different things; keep distinct nodes.
   - Identify the 6–10 load-bearing frameworks for the Core section.
3. Build the **concept map** (below).
4. Build the **topic index** (below) — the bridge to the chapter files.
5. Generate the supporting files, scaled to book size (below).
6. Write the master `SKILL.md` from the template (below).

## Concept map format

Two parts. First, a node/edge list — the authoritative form:

```markdown
## Concept Map

### Core Frameworks (nodes)
- **<Framework>** — <one-line what it is and when it applies> · ch<N>

### Relationships (edges)
- **<A>** → builds on → **<B>**
- **<A>** → is the failure mode of → **<B>**
- **<A>** → is an instance of → **<B>**
- **<A>** → trades off against → **<B>**
```

Use a small, consistent edge vocabulary: `builds on`, `requires`,
`instance of`, `failure mode of`, `trades off against`, `contradicts`,
`refines`. Edges are what a flat summary cannot capture — prioritise them.

Optionally add a mermaid `graph` if it aids navigation, but the text node/edge
list is the source of truth and must always be present.

## Topic index — the bridge tier

The topic index is how Claude jumps from `SKILL.md` to the right chapter file
when the concept map is not enough. **It must be excellent**, or "go to the
chapter" degrades into "grep and guess". Requirements:

- Map the **vocabulary a user would actually ask in** — not just chapter
  titles.
- Include synonyms and BOTH the author's term and the common term
  (e.g. `Eventual consistency`, `BASE`).
- A framework spanning multiple chapters points to **all** of them.
- Alphabetical, with multiple chapter pointers per term where relevant.

```markdown
## Topic Index
- **<Term / synonym>** → ch<N>[, ch<N>]
```

**Cap: 2,000 tokens.** Above that, the master `SKILL.md` body risks
silent truncation (which eats the end of the file — exactly where the
topic index lives). When the full vocabulary exceeds the cap:

1. Keep the highest-frequency ~60 terms inline in `SKILL.md`'s Topic
   Index section (the ones a user is most likely to ask).
2. Write the complete list to `topic-index-full.md` alongside `SKILL.md`.
3. Link to it from the inline section:
   `> Full vocabulary: [topic-index-full.md](topic-index-full.md) — every
   indexed term with chapter pointers.`

## Supporting files — scale by book size

Caps must scale with the book, or a large book gets silently truncated:

| Book size            | glossary | patterns | cheatsheet |
|----------------------|----------|----------|------------|
| small (< 12 ch)      | ≤ 1,500  | ≤ 2,000  | ≤ 1,000    |
| medium (12–25 ch)    | ≤ 3,000  | ≤ 3,500  | ≤ 1,500    |
| large (> 25 ch)      | shard*   | ≤ 5,000  | ≤ 2,000    |

*Shard: split the glossary into `glossary/part-1.md` … by book part or
alphabetically, each loaded on demand, and list the shards in `SKILL.md`.
Never truncate the vocabulary to fit one file.

**Sharding worked example** (trigger: > 250 terms OR > 50 chapters):

```
glossary/
├── a-h.md     # ~80 terms, A through H
├── i-p.md     # ~90 terms, I through P
└── q-z.md     # ~85 terms, Q through Z
```

In `SKILL.md`, list them as:

```markdown
## Supporting Files
- Glossary (sharded — load the one matching your term):
  - [glossary/a-h.md](glossary/a-h.md) — A–H
  - [glossary/i-p.md](glossary/i-p.md) — I–P
  - [glossary/q-z.md](glossary/q-z.md) — Q–Z
```

Choose shard boundaries so each file stays ≤ 3,000 tokens. Prefer
alphabetical splits over by-Part splits — users look up terms, they don't
know which Part a term came from.

- `glossary.md` — every significant term, alphabetical, `**Term** — def (ch N)`.
- `patterns.md` — all concrete techniques/patterns, each with
  `When to use` / `How` / `Trade-offs`.
- `cheatsheet.md` — decision tables and quick-reference rules; a single page.

## chapters_manifest.json — canonical chapter list

At the end of Stage 2 (reduce), write `chapters_manifest.json` alongside
`SKILL.md`. It is the canonical post-build record of what was produced
and is consumed by future skill invocations + by resume logic:

```json
{
  "schema_version": 2,
  "skill_slug": "<slug>",
  "built_at": "2026-05-17T14:30:00Z",
  "chapters": [
    {
      "index": 1,
      "book_number": "intro",
      "title": "Introduction",
      "slug": "introduction",
      "file": "chapters/intro-introduction.md",
      "word_count": 837,
      "token_estimate": 1358,
      "status": "extracted"
    },
    {
      "index": 2,
      "book_number": "ch01",
      "title": "Chapter 1 — A Parable",
      "slug": "a-parable",
      "file": "chapters/ch01-a-parable.md",
      "word_count": 1023,
      "token_estimate": 1370,
      "status": "extracted"
    },
    {
      "index": 20,
      "book_number": "fm-2",
      "title": "Acknowledgments",
      "slug": "acknowledgments",
      "file": "chapters/fm-2-acknowledgments.md",
      "word_count": 100,
      "token_estimate": 140,
      "status": "extracted"
    }
  ]
}
```

### Field meanings

- `index` — extraction order (stable internal id, 1..N over everything
  the extractor produced including front and back matter). **Never
  displayed to users; never used in filenames.** It exists so that
  extraction order is preserved across regenerations.
- `book_number` — the book-native label. Assigned by
  `extract.py:assign_book_numbers` from the chapter title:
  - `ch01`, `ch02`, … for numbered chapters (parses "Chapter 7 — …",
    "7. …", "Chapter VII", etc.).
  - `intro`, `preface`, `prologue`, `postscript`, `epilogue`,
    `foreword`, `afterword`, `appendix` (bare) — named segments.
  - `appendix-a`, `appendix-b`, … — lettered appendices.
  - `part-1`, `part-2`, … — Part dividers.
  - `fm`, `fm-2`, `fm-3`, … — front matter (praise / TOC / dedication
    / copyright / acknowledgments / cover / contents / …). Duplicates
    are auto-suffixed with `-2`, `-3`, …
  - `bm`, `bm-2`, … — back matter (index / colophon / bibliography
    / glossary / further reading / …).
  - `null` (rare) — classification failed; renderers fall back to
    `ch{index:02d}`.
- `file` — relative path, must start with `chapters/` and the
  filename's stem must equal `<book_number>-<slug>`.
- `status` — `extracted`, `failed`, or `skipped`. Used in Step 10
  validation and resume.

### Schema versioning

`schema_version: 2` indicates `book_number` is present. Older skills
with `schema_version: 1` (or no version field) lack `book_number`; the
`backfill_book_numbers.py` script populates it retroactively.

## Master SKILL.md template

The generated skill's `SKILL.md` body stays **under ~4,000 tokens** —
progressive disclosure keeps detail in the chapter files. Front-load the
most important content; truncation eats the end.

```markdown
---
name: <skill-slug>
description: Expert knowledge from "<Full Title>" by <Author>. Use when
  applying <author>'s frameworks for <3–6 key topics>, or when the user asks
  about <2–3 distinctive concepts from the book>.
when_to_use: <10–15 comma-separated trigger phrases from the book's topics>
allowed-tools: Read Grep
argument-hint: [topic, framework name, or chapter number]
---

# <Full Title>
**Author**: <Author> | **Pages**: ~<N> | **Chapters**: <N> | **Built**: <date>

## How to Use This Skill
- `/<slug>` — load the concept map and core frameworks.
- `/<slug> <topic>` — I look up the topic index and read the right chapter.
- `/<slug> ch<N>` — I load that specific chapter file.
- Ask "what chapters do you have?" for the full index.
When a question goes beyond the Core Frameworks below, I read the relevant
chapter file before answering — I do not guess.

## Book Thesis
<2–3 sentences from the Pass 0 spine: what the book argues, overall.>

## Concept Map
<node list + edge list, per the format above>

## Core Frameworks & Mental Models
<~2,000 tokens: the 6–10 load-bearing frameworks, exact names preserved,
written as "Use X when Y" / "Prefer X over Y because Z". A toolkit, not a
summary.>

## Chapter Index
| # | Title | Key Frameworks |
|---|-------|----------------|
| [ch01](chapters/ch01-<slug>.md) | <Title> | <f1>, <f2> |

## Topic Index
<alphabetical term → chapter map, per the spec above>

## Supporting Files
- [glossary.md](glossary.md) — all key terms
- [patterns.md](patterns.md) — techniques & patterns
- [cheatsheet.md](cheatsheet.md) — quick reference

## Scope & Limits
Covers the content of this book only. <If a secondary genre was noted, say so.>
For implementation in a live codebase, combine with project tools. For topics
beyond the book, ask Claude directly.
```
