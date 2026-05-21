# Chapter File Template — Stage 1 (Map) Output

Each chapter produces one file: `chapters/<book_number>-<slug>.md`,
where `book_number` is the canonical book-native label assigned by
`extract.py:assign_book_numbers` (`ch01`, `intro`, `preface`,
`appendix-a`, `fm`, `bm`, `part-1`, …) — see
`concept-map-spec.md` → "Field meanings" for the full vocabulary.
**Never use the manifest `index`** in filenames or in cross-references
between chapters; it counts every extracted segment (including
front/back matter) and drifts from the book's own numbering. This is
the **detail tier** — loaded on demand when the concept map in
`SKILL.md` is not enough.

When a chapter references another, cite by `book_number`:
`see [ch07-taxes-are-costs-too](ch07-taxes-are-costs-too.md)`,
`see the [Introduction](intro-day-zero.md)`.

The job is **extraction, not summary.** A chapter file is a toolkit of the
chapter's named frameworks, exact techniques, and anti-patterns — not a recap
of what the chapter "talks about". Write in practitioner voice: "Use X when Y",
not "the chapter explains X".

## Target size

800–1,400 tokens per file. Dense, not verbose. A tight 1,000-token extraction
beats a 6,000-token excerpt. If a chapter is genuinely huge, keep the file
tight and push secondary detail into `Key Takeaways` as terse lines.

## Template

Use this structure. Keep sections that have real content; drop sections the
genre profile marks as irrelevant (e.g. omit `Code Examples` for productivity
books). Never invent content to fill a section.

```markdown
# Chapter <N>: <Full Title>

## Core Idea
<1–2 sentences: the single most important thing this chapter teaches.>

## Frameworks Introduced
- **<Exact Framework Name>**: <the author's precise formulation>
  - When to use: <specific trigger situation>
  - How: <steps or criteria>
(Preserve exact names. "The 5 Whys" is not "ask why a few times".)

## Key Concepts
- **<Term>**: <precise one-sentence definition>
(5–10 of the most load-bearing terms in this chapter.)

## Mental Models
<2–4 thinking tools, written as "Use X when Y" or "Think of X as Y".>

## Anti-patterns
- **<What to avoid>**: <why it fails>

## Code Examples            (technical / vuln-hunting / scientific only)
```<language>
<the single most instructive snippet — preserve indentation exactly>
```
- **Demonstrates**: <one line>

## Reference Tables         (technical / financial / scientific only)
<Reproduce any comparison matrix or decision table as markdown.>

## Figures                  (only if the chapter has [[IMAGE]] placeholders)
- **<figure id>**: <what the diagram conveys — components and relationships,
  reconstructed flow, or salient text. From a real vision read, not a guess.>

## Key Takeaways
1. <Actionable insight a practitioner must remember>
2. ...
(3–7 items.)

## Connects To
- **Ch <N>**: <why this chapter relates>
- **<Concept>**: <external standard / concept it links to>
```

## Handling image placeholders

When a chapter slice contains `[[IMAGE: images/... ]]` or
`[[PAGE_SCAN: images/... ]]`:

1. `Read` the referenced image file — Claude Code's native image understanding
   loads the actual pixels.
2. Fold the understanding into the chapter file **as text**:
   - a flowchart → a described process, or a reconstructed mermaid diagram;
   - an architecture drawing → its components and how they relate;
   - a screenshot / scanned page → its salient text and what it shows;
   - a chart → what it demonstrates (the trend/claim), not pixel values.
3. The image is read **once, here.** It is never referenced again — the
   generated skill stays pure text, so it loads fast and cheap at use time.
4. For a `PAGE_SCAN`, the image *is* the page's text — read it as the chapter
   body, not as a figure.

If a figure is purely decorative, say so in one line and move on. Do not burn
tokens describing chapter ornaments.

**Read failures — do not invent.** If `Read` fails, or the image is blank,
tiny (decoded < ~1 KB), or genuinely uninterpretable, write a one-liner and
move on:

```
**Fig N**: [image at `images/<file>` could not be read]
```

Never reconstruct from the surrounding caption alone — a guessed figure is
worse than an admitted gap. If multiple images in a row fail, note it once
at the top of the Figures section: "*Several figures could not be loaded;
their captions are preserved as text in the chapter body.*"

## Quality bar

- Preserve the author's exact terminology and naming.
- Density over completeness — extract signal, drop filler.
- Never copy raw book text; always synthesise.
- Every framework needs a *when to use*, or it is not actionable.
