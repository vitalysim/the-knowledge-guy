# Genre Profiles

The right way to extract a book depends on what kind of book it is. The
**fundamental unit of knowledge** differs by genre, and that unit should drive
the chunk boundary and the extraction schema — not just which sections get
emphasised.

Pick exactly one profile in Step 2. If the book genuinely straddles two,
pick the one matching the *reason the user wants the skill*, and note the
secondary genre in the skill's `SKILL.md` scope section.

Each profile defines five things:
- **Unit** — the atomic piece of knowledge the map step extracts.
- **Boundary** — how to chunk the book for the map step.
- **Map emphasis** — which chapter-template sections carry the weight.
- **Reduce emphasis** — what the Stage 2 concept map must foreground.
- **Don't pick this if…** — the most common miscategorisation to avoid.

If unsure between two profiles, jump to the **Selector heuristics** at
the bottom of this file before committing.

---

## technical

General programming / engineering / architecture books.

- **Unit**: a pattern, technique, API, or design decision — each with
  preconditions, mechanics, and trade-offs.
- **Boundary**: by chapter. Chapters are usually clean topic units.
- **Map emphasis**: `Frameworks`, `Code Examples`, `Reference Tables`,
  `Anti-patterns`. Preserve exact syntax and exact API names.
- **Reduce emphasis**: a dependency graph — which concepts build on which,
  and which trade-offs recur across chapters.
- **Images**: keep diagrams and screenshots; they often *are* the content.
- **Don't pick this if…** the book is mostly *exploitation* (→ `vuln-hunting`),
  mostly *self-contained recipes* (→ `reference`), or has *exercises after
  each section* (→ `textbook`).

## vuln-hunting

Offensive security, exploitation, bug-hunting, reverse-engineering books.

- **Unit**: a vulnerability class or technique — `precondition → method →
  detection signal → variants → mitigation`. Highly structured and
  order-independent; deduplicates cleanly across chapters.
- **Boundary**: by chapter, but expect the same bug class to recur — the
  reduce step must merge recurrences into one node.
- **Map emphasis**: `Frameworks` (techniques), `Anti-patterns` (what wastes a
  hunter's time / what gets you a duplicate), `Code Examples` (payloads, PoC
  snippets — preserve exactly), `Key Takeaways` as detection signals.
- **Reduce emphasis**: a technique catalogue cross-referenced by target
  surface (web / binary / cloud / mobile) and by primitive (read / write /
  exec). This is the highest-value reduce output of any genre.
- **Images**: keep — call graphs, packet diagrams, and exploit-flow figures
  carry precise meaning. Reconstruct flow diagrams as text or mermaid.
- **Don't pick this if…** the book is *defensive* security / blue-team
  (use `technical`) or *general programming with security examples* (also
  `technical`).

## financial

Investing, valuation, markets, corporate finance, quant books.

- **Unit**: a model, formula, ratio, or decision rule — with its assumptions
  and the conditions under which it fails.
- **Boundary**: by chapter.
- **Map emphasis**: `Frameworks` (models), `Reference Tables`, `Key Concepts`
  (define terms precisely — the same word can mean different things in
  different chapters), `Anti-patterns` (when a model misleads).
- **Reduce emphasis**: a decision map — which model applies to which
  situation. **Do not over-merge**: two chapters using "duration" or
  "leverage" may mean subtly different things; keep them distinct nodes if so.
- **Images**: keep charts and tables; describe what each chart demonstrates,
  not its exact pixel values.
- **Don't pick this if…** it's primarily *behavioural* / psychology of money
  (→ `psychology`), *personal-finance memoir / story* (→ `narrative`), or
  *org-level strategy* with finance as backdrop (→ `business`).

## scientific

Academic texts, research-method books, dense reference works.

- **Unit**: a concept, mechanism, method, or result — with its evidence basis.
- **Boundary**: by chapter, unless chapters are very long — then chunk by
  major section.
- **Map emphasis**: `Key Concepts`, `Frameworks` (methods/mechanisms),
  `Reference Tables`, `Connects To`.
- **Reduce emphasis**: a concept map proper — nodes and typed edges
  (`causes`, `requires`, `contradicts`, `is-a`).
- **Images**: keep figures and diagrams; OCR equation images via vision.
- **Don't pick this if…** the book has *exercises* after sections
  (→ `textbook`), it's a *popular synthesis* of research findings
  (→ `psychology`), or a *recipe-style methods cookbook* (→ `reference`).

## legal

Statutes, case law, regulatory texts, doctrinal commentary, compliance.

- **Unit**: a rule (statute, regulation, doctrine, precedent) — with its
  exceptions, jurisdictional scope, citations, and the elements that must be
  proved.
- **Boundary**: by rule, not chapter. A single section may contain many
  rules; a single rule may be elaborated across multiple sections. The map
  step must isolate one rule per chunk.
- **Map emphasis**: `Frameworks` (the rule's elements / tests), `Key Concepts`
  (defined terms — legal definitions are precise and load-bearing, preserve
  verbatim), `Anti-patterns` (common misapplications, distinguishable
  cases), `Connects To` (related rules, citing cases), `Reference Tables`
  (jurisdictional variations, statute-of-limitations matrices).
- **Reduce emphasis**: a rule index with cross-references — precise wording
  preserved, exceptions enumerated, jurisdictions noted. **Never paraphrase
  legal definitions**; the synthesis must cite chapter + section verbatim
  where the rule lives. This is the one genre where over-merging is
  dangerous: two doctrines with similar names can have opposite effects.
- **Images**: skip unless the source includes structured forms (claim charts,
  regulatory flowcharts) — keep those, with their decision logic transcribed
  to text.
- **Don't pick this if…** it's a *narrative biography of a lawyer or case*
  (→ `biography` / `narrative`), or a *general technical book that happens
  to mention compliance* (→ `technical`).

## textbook

Pedagogical course material with explicit prerequisites and exercises.

- **Unit**: a concept + worked example + exercise. Textbooks teach one
  concept at a time and *expect* the reader to do the exercise before moving
  on; the exercise is part of the unit, not an appendix.
- **Boundary**: by section, not chapter. Chapters bundle 3-8 sections, each
  its own concept. Use section headings — most textbooks number them
  (`§3.2`, `2.4.1`).
- **Map emphasis**: `Core Idea`, `Frameworks` (the formalism / algorithm /
  theorem), `Code Examples` *or* `Reference Tables` (the worked example —
  preserve exactly), `Key Takeaways` (what the exercise was meant to teach),
  `Connects To` (explicit prerequisites — "assumes §2.3").
- **Reduce emphasis**: a learning DAG — nodes are concepts, edges are
  prerequisites. Captures the path a learner must take. Pair with a separate
  `exercises.md` listing the worked examples by section so a learner can
  practise without re-reading.
- **Images**: keep diagrams and equation figures; reconstruct geometric /
  circuit / proof diagrams as text or mermaid.
- **Don't pick this if…** there are *no exercises* (→ `scientific` or
  `technical` depending on tone), or it's a *practitioner reference*
  organised by lookup rather than learning path (→ `reference`).

## reference

Cookbooks, recipe collections, pattern catalogues, API doc-books, "X in
Practice" style how-tos.

- **Unit**: one self-contained recipe / pattern / API entry — with inputs,
  steps, outputs, failure modes, and "when to use this". Recipes don't depend
  on each other narratively, even when the author groups them.
- **Boundary**: **by recipe, not chapter.** Chapters are usually category
  buckets ("salads", "sorting algorithms", "auth patterns") and each recipe
  inside is the real unit. Use the chapter as metadata (category tag), not
  as the chunk.
- **Map emphasis**: `Frameworks` (the recipe itself, with explicit
  *when to use* — non-negotiable for references), `Code Examples` (preserve
  exactly — these books *are* their snippets), `Reference Tables`
  (ingredients / parameters / inputs), `Anti-patterns` (common failure
  modes).
- **Reduce emphasis**: a tagged index, not a concept map. Group recipes by
  *target situation* (what problem each solves) and *primitive* (what each
  does to the inputs). The topic index is the load-bearing artefact here;
  the concept map is thin and optional.
- **Images**: keep recipe photos / diagrams only if they convey technique
  (a finished plating tells you nothing; a knife-cut sequence tells you
  everything).
- **Don't pick this if…** the recipes *do* depend on each other / build a
  larger system (→ `technical` or `textbook`).

## business

Leadership, management, strategy, corporate decision-making.

- **Unit**: an organisational decision rule or operating principle — *who*
  it applies to (a team, a board, a CEO), the *signal* that invokes it, and
  the *outcome it shapes*. Sibling to `productivity`, which is about the
  individual; `business` is about the org.
- **Boundary**: by chapter, but watch for the case-study trap — many
  business books wrap one principle in three anecdotes. The chunk is the
  principle, not the anecdote.
- **Map emphasis**: `Frameworks` (the named rule / matrix / model —
  preserve exact names: "BCG matrix", "Five Forces", "Hedgehog concept"),
  `Mental Models`, `Anti-patterns` (failure modes named by the author),
  `Reference Tables` (org structure tables, decision matrices).
- **Reduce emphasis**: a decision map — for each common org-level situation
  (new market entry / layoff / pivot / succession), which frameworks the
  book recommends. Strip motivational filler aggressively; business books
  over-pad.
- **Images**: keep 2x2 matrices, org charts, value-chain diagrams; describe
  what each demonstrates.
- **Don't pick this if…** the focus is on *individual habits / mindset*
  (→ `productivity`), on the *founder's life story* (→ `biography`), or on
  *market history* (→ `history`).

## psychology

Popular cognitive science / behavioural science — Kahneman, Ariely,
Cialdini, Thaler, Duckworth, Pinker-style synthesis books.

- **Unit**: a named effect or bias (e.g. "loss aversion", "anchoring",
  "availability heuristic") — with its conditions, the experiment that
  established it, and where in everyday life it shows up.
- **Boundary**: by chapter, with the same recurrence handling as
  `vuln-hunting` — the same bias appears across multiple chapters and must
  be merged at reduce time into one node.
- **Map emphasis**: `Key Concepts` (the named effect, exact formulation),
  `Frameworks` (the experimental paradigm), `Mental Models` (how to spot
  the effect in the wild), `Anti-patterns` (the mistake the bias produces),
  `Connects To` (related effects).
- **Reduce emphasis**: a catalogue of effects cross-referenced by the
  domain where they bite (decisions / memory / perception / social /
  negotiation).
- **Images**: keep experiment figures and replicable diagrams; describe
  charts as the claim they support, not pixel values.
- **Don't pick this if…** the book is *prescriptive self-help* with named
  effects as garnish (→ `productivity`), or *peer-reviewed academic
  psychology* with statistical rigour (→ `scientific`).

## history

Event-driven non-fiction — eras, dynasties, wars, technologies-in-context.

- **Unit**: an event with *dated causes, actors, and consequences* — the
  historiographic atom, not the narrator's prose.
- **Boundary**: by era / period, often spanning multiple chapters. Where
  chapters cleanly map to eras, use them; where they don't (e.g. the author
  backtracks for context), chunk by the era arc.
- **Map emphasis**: `Core Idea`, `Key Concepts` (preserve exact proper
  nouns, dates, place names), `Mental Models` (the author's explanatory
  frame), `Connects To` (cause/effect across eras), `Reference Tables`
  (timelines, treaty lists, succession charts).
- **Reduce emphasis**: a timeline + causal graph — events as nodes, with
  typed edges (`caused-by`, `responded-to`, `prefigured`, `concluded`).
  Don't merge similar events from different eras — history's whole point is
  *when and why*.
- **Images**: keep maps, family trees, and reproduced documents; describe
  maps as text (what they reveal, not pixel detail).
- **Don't pick this if…** the book is *one person's life arc*
  (→ `biography`) or a *big-idea book that uses history as backing*
  (→ `narrative`).

## productivity

Self-improvement, habits, decision-making, time management, mindset.
Individual-focused. (For org-focused, use `business`.)

- **Unit**: a framework or principle — usually *one core idea elaborated*
  across the whole book, plus motivational connective tissue.
- **Boundary**: **by framework, not by chapter.** Naive per-chapter chunking
  produces near-duplicate fragments of the same framework. Chunk so each unit
  is one framework even if it spans chapters. Here the reduce step does the
  real work; the map step is lightweight.
- **Map emphasis**: `Frameworks`, `Mental Models`, `Key Takeaways`. Skip
  empty `Code Examples` / `Reference Tables` sections entirely.
- **Reduce emphasis**: a single clean statement of the core framework and
  how the sub-ideas hang off it. Strip the motivational filler.
- **Images**: usually decorative — the extractor's high `min-image-dim`
  already skips most; ignore the rest unless a figure states a framework.
- **Don't pick this if…** the unit is a *named cognitive bias backed by
  experiments* (→ `psychology`), the focus is *org-level*
  (→ `business`), or the book is one person's *memoir of habits formed*
  (→ `biography`).

## biography

Memoirs and biographies — single-life arcs organised chronologically.

- **Unit**: a turning-point decision, pivot, or formative experience —
  *what was decided, what was at stake, what changed*. Not a chapter
  recap.
- **Boundary**: by life period, not chapter. A subject's "wilderness years"
  or "second act" often spans several chapters; chunking by chapter shreds
  the arc. Use the spine to detect arc boundaries.
- **Map emphasis**: `Core Idea` (the period's stakes), `Mental Models` (how
  the subject made the decisions of that period), `Key Takeaways`
  (transferable lessons), `Connects To` (people / events / books that
  shaped them). Skip `Code Examples`, `Reference Tables`.
- **Reduce emphasis**: a timeline + decision catalogue — eras of the
  subject's life on one axis, the load-bearing decisions on the other, with
  the lessons distilled from each.
- **Images**: usually decorative photos; skip unless a figure carries data
  (family tree, org chart, map of journeys).
- **Don't pick this if…** the book is *multi-life history*
  (→ `history`), or a *self-improvement book lightly framed as memoir*
  (→ `productivity`).

## narrative

Case-study-driven or argument-driven non-fiction (big-idea books, deep
journalism, intellectual histories that aren't about an era).

- **Unit**: an argument or a transferable lesson drawn from a case.
- **Boundary**: **by argument, not by chapter** — arguments often span
  several chapters. If chapter boundaries sever an argument, chunk by the
  argument arc instead.
- **Map emphasis**: `Core Idea`, `Mental Models`, `Key Takeaways`,
  `Connects To`. Capture the lesson, not the anecdote.
- **Reduce emphasis**: the book's central thesis and the chain of arguments
  supporting it.
- **Images**: usually skippable.
- **Don't pick this if…** the chronology and dates are *load-bearing*
  (→ `history`), the unit is *one person's life* (→ `biography`), or the
  argument is *one core idea elaborated with motivational prose*
  (→ `productivity`).

## general

Use only when the book genuinely does not fit the above, or the user is
unsure. Treat as `technical` with all schema sections optional — the map
step keeps whichever sections have real content and drops the rest.

---

## Selector heuristics

When the user picks "Not sure" or the choice looks miscategorised, apply
these *before* committing to a profile:

1. **Has worked examples followed by exercises?** → `textbook`, not
   `scientific`.
2. **Self-contained chunks the reader can apply independently?** →
   `reference`, not `technical` (even if it's a programming book).
3. **Dated events with multiple actors and consequences?** → `history`,
   not `narrative`.
4. **Life arc of one person, organised chronologically?** → `biography`,
   not `narrative`.
5. **Defined terms whose exact wording matters?** → `legal`, not
   `technical` (statutes, contracts, doctrines).
6. **One core idea elaborated across many chapters with motivational
   prose?** → `productivity`, not `narrative`.
7. **Bug classes / exploitation techniques as the main content?** →
   `vuln-hunting`, even if the surface frame is "programming".
8. **Org-level (CEOs, teams, strategy)?** → `business`, not
   `productivity`.
9. **Named biases or cognitive effects as the unit?** (Kahneman, Ariely,
   Cialdini-style) → `psychology`, not `scientific` or `productivity`.

If two profiles still fit, pick the one matching *why the user wants the
skill*. Tell the user which secondary profile you considered and why you
didn't pick it; record it in the generated `SKILL.md`'s scope section.
