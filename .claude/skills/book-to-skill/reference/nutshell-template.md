# Nutshell template — one block per chapter (~100 words)

A nutshell is a micro-summary of a single chapter. It is **not** the
chapter toolkit (that's `chapters/<book_number>-*.md`, which is
800-1,400 words of frameworks, anti-patterns, and takeaways). A
nutshell is the "if-you-only-read-five-bullets" view, suitable for
skimming the whole book in one scroll.

## Numbering rule (critical)

**Every heading and citation uses the chapter's `book_number` from
`chapters_manifest.json`, never the manifest `index`.**

`book_number` is the book's own label, normalised: `ch01`, `ch02`, …
for numbered chapters; `intro`, `preface`, `prologue`, `postscript`,
`epilogue`, `foreword`, `appendix`, `appendix-a`, … for named
segments; `part-1`, `part-2`, … for Part dividers. The manifest
`index` is extraction order (1..N over everything the extractor
produced, including front matter) and drifts from the book's
numbering — using it would make Sethi's Introduction render as
`ch07`. See `concept-map-spec.md` → "Field meanings" for the full
vocabulary.

If a manifest entry has `book_number: null` (extremely old skills),
fall back to `ch{index:02d}` for that one entry and surface a
warning.

## Voice and length

- 80-120 words total per block. Hard ceiling 150.
- 3-5 bullets. Never fewer than 3, never more than 5.
- Snappy, declarative. No hedging ("perhaps", "it could be argued").
- Present tense, active voice. Talk to the reader, not about the book.
- Cite the chapter once at the end, not at every bullet.

## Required shape

```
## <book_number> — <Chapter title from chapters_manifest.json>

> **In a nutshell:** <One sentence — the chapter's core claim. The line
> a reader should remember a year later.>

- <The named framework, rule, or claim introduced here.>
- <The mechanism, number, example, or parable that makes it stick.>
- <The contrarian turn or the thing most readers get wrong.>
- <(Optional) So what — how to apply this today.>
- <(Optional) The memorable phrase, figure, or quote.>

*From [<skill-slug> <book_number>].*
```

`<book_number>` appears verbatim in the heading and citation —
`ch07`, `intro`, `preface`, `appendix-a`. Do not pad it; do not
re-number it; do not substitute the manifest index. For the title
text after the em-dash, strip any leading "Chapter N — " /
"Chapter N: " / "N. " from the manifest title (`ch07`'s heading
already carries the number, so duplicating it inside the title is
ugly).

## What to extract

Read the chapter's toolkit file (`chapters/<book_number>-*.md`) and pull:

1. The chapter's **core idea** — usually already labelled in the
   toolkit's "Core Idea" section. This becomes the `In a nutshell` line.
2. The **named framework** or claim from "Frameworks Introduced".
3. The **load-bearing mechanism** — a number, example, parable, or
   figure that anchors the claim.
4. The **contrarian twist** from "Anti-patterns" or the takeaways. What
   would a naive reader get wrong?
5. (Optional) The **so-what** from "Key Takeaways" — one actionable
   line.
6. (Optional) The **memorable phrase** — a quotable line, a figure
   number, or a named parable.

## What to avoid

- Do not list every framework in the chapter — pick the one that
  defines it.
- Do not invent content not in the toolkit file. If the chapter is
  thin, a 3-bullet nutshell is correct.
- Do not summarise the whole book in one chapter's nutshell. Each
  block speaks for its own chapter only.
- Do not include cross-references ("see ch12 for…") — the whole book
  ships together; the reader will scroll.
- Skip front-matter, acknowledgments, and any chapter with
  `word_count < 300` in the manifest. The orchestrator filters these
  before fanning out.

## Example (Bogle, ch4 — Cast Your Lot with Business)

```
## ch04 — Cast Your Lot with Business

> **In a nutshell:** Stock returns over the long run are produced by
> businesses earning money, not by traders trading slips of paper.

- The **investment return** of a stock is its dividend yield plus
  earnings growth. The **speculative return** is the change in P/E
  multiple — and over decades it averages to near zero.
- Since 1900, US stocks returned ~9.5% / year. Of that, 9.0% came from
  dividends + earnings growth; only 0.5% came from rising P/E.
- The headlines obsess over the speculative half, but the wealth comes
  from the investment half. Own the business, ignore the casino.
- *So what:* buy the whole market and hold it. You capture the
  investment return by default.

*From [bogle-common-sense-investing ch4].*
```
