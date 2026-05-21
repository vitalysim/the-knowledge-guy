# Layouts — per-use-case body templates

Every layout below uses **only** classes defined in `shell.html`. The
new design system (Knowledge Guide · Modern) ships every component
ready to use — `.source`, `.def`, `.qna`, `.tutorial`, `.worked`,
`.capsule`, `.excerpt`, `.callout.*`, `.compare`, `.rules`, `.plate`,
etc. — so per-use-case `{{EXTRA_CSS}}` is usually **empty**.

The full visual contract lives in
[`reference/full-demo-light.html`](reference/full-demo-light.html) and
[`reference/full-demo-dark.html`](reference/full-demo-dark.html) — open
those in a browser when you need a refresher on which component to
reach for.

To render any artifact:

1. Read `shell.html`.
2. Open the section for this use case in this file.
3. Fill in `{{TITLE}}`, `{{EXTRA_CSS}}` (often empty), and `{{BODY}}`.
4. Write to the path under `artifacts/`.

**Hard rules** (do not violate):

- Use the document chrome — eyebrow + h1 + lede + meta-bar + (optional)
  toc — at the start of **every** artifact.
- Use `.source` cards for citations, not inline footnotes. Cite once
  per claim, with `.id-pill`, `.id-dom` (book), `.src-locator` (page /
  chapter / section).
- Single accent — `--accent` (cobalt). Never introduce a second hue.
  Use `--ok / --warn / --crit / --insight` only for true semantic
  state, sparingly.
- Mono is architecture (kickers, meta labels, code, tags) — not
  decoration. Don't make body copy mono.
- Plate diagrams use SVG with `--plate-*` CSS variables so they invert
  cleanly in dark mode. Never hardcode colors in SVG.

---

## 1 · Nutshell

**Path:** `artifacts/nutshells/<book-slug>.html` (cached; reuse unless
`--regenerate`)

**Title:** `Nutshell — <Book title>`

**EXTRA_CSS:** *(none)*

**Body skeleton:**

```html
<div class="wrap">

  <!-- Opener -->
  <span class="eyebrow"><span class="dot"></span>Nutshell · {{skill-slug}}</span>
  <h1>{{book-title}}</h1>
  <p class="lede">{{book-thesis}}</p>

  <div class="meta-bar">
    <div class="cell"><span class="lbl">Chapters</span><span class="val">{{N}}</span></div>
    <div class="cell"><span class="lbl">Reading time</span><span class="val">~{{N*0.5}} min</span></div>
    <div class="cell"><span class="lbl">Source</span><span class="val">{{author-lastname}}</span></div>
    <div class="cell"><span class="lbl">Format</span><span class="val">Per-chapter skim</span></div>
  </div>

  <!-- TOC -->
  <div class="toc">
    <span class="toc-head">In this book</span>
    {{for each chapter:
      <a href="#{book_number}"><span class="num">{book_number}</span>{title}</a>
    }}
  </div>

  {{for each chapter:
    <section class="sect" id="{book_number}">
      <div class="sect-head">
        <div class="left">
          <span class="kicker"><span class="num">{book_number}</span> · chapter</span>
          <h2>{title}</h2>
        </div>
      </div>
      <div class="capsule">
        <p class="capsule-lede">{in_a_nutshell-line}</p>
        <ul class="capsule-list">
          {bullets as <li>}
        </ul>
      </div>
    </section>
  }}

</div>
```

Notes:
- `.capsule` is the new system's "summary block" component — see demo
  section 11.
- For chapters with a memorable phrase, use an `<blockquote class="excerpt">`
  with `<span class="excerpt-attrib">— {{author}}</span>`.

---

## 2 · Synthesis (cross-book ask)

**Path:** `artifacts/synthesis/YYYY-MM-DD-<query-slug>.html` (never
reused)

**Title:** `Synthesis — <one-line query summary>`

**EXTRA_CSS:** *(none)*

**Body skeleton:**

```html
<div class="wrap">

  <span class="eyebrow"><span class="dot"></span>The Knowledge Guy · cross-domain synthesis</span>
  <h1>{{single-sentence-thesis}}</h1>
  <p class="lede">{{drop-cap-lede 3-5 sentences braiding skills}}</p>

  <div class="meta-bar">
    <div class="cell"><span class="lbl">Question</span><span class="val">{{user-question-truncated}}</span></div>
    <div class="cell"><span class="lbl">Sources</span><span class="val">{{N consulted}}</span></div>
    <div class="cell"><span class="lbl">Out of scope</span><span class="val">{{N filtered}}</span></div>
    <div class="cell"><span class="lbl">Generated</span><span class="val">{{date}}</span></div>
  </div>

  <!-- Body paragraphs; cite by inserting a .source card after a claim,
       not inline. Use one .source card per book that contributed. -->

  <section class="sect">
    <p>{{paragraph synthesising 2-3 books on one sub-question}}</p>

    <div class="source ok">
      <div class="src-id">
        <span class="id-pill">{{skill-slug}}</span>
        <span class="id-dom">{{book-title}}</span>
        <span class="id-status">cited</span>
      </div>
      <div class="src-title">{{chapter title or framework name}}</div>
      <div class="src-byline">{{author}}</div>
      <div class="src-locator">
        <div class="cell"><span class="lbl">Chapter</span><span class="val">{{book_number}}</span></div>
        <div class="cell"><span class="lbl">Concept</span><span class="val">{{short label}}</span></div>
      </div>
    </div>

    <p>{{paragraph that surfaces tension between two books}}</p>
  </section>

  <!-- Pull quote when you have a memorable line -->
  <blockquote class="excerpt">
    <p>{{the memorable line from the synthesis}}</p>
    <span class="excerpt-attrib">— synthesis</span>
  </blockquote>

  <!-- Optional: comparison table when 3+ books take stances -->
  <section class="sect">
    <table class="compare">
      <thead><tr><th>Author</th><th>Stance</th><th>Operative concept</th></tr></thead>
      <tbody>
        {{rows}}
      </tbody>
    </table>
  </section>

  <!-- Closing implications -->
  <section class="sect">
    <p>{{closing paragraph}}</p>
  </section>

</div>
```

Use a `.callout.insight` block where one author reframes the others'
position in a non-obvious way.

---

## 3 · Walk session (in progress)

**Path:** `artifacts/walks/<topic-slug>-step-<N>.html` (overwritten
per step)

**Title:** `Walk · <topic> · step <N>/<total>`

**EXTRA_CSS:** *(none — use `.tutorial`, `.qna`, `.callout.*` from shell)*

**Body skeleton:**

```html
<div class="wrap">

  <span class="eyebrow"><span class="dot"></span>Walk in progress · {{topic}}</span>
  <h1>{{step-title}}</h1>
  <p class="lede">{{lede capturing what this step teaches}}</p>

  <div class="meta-bar">
    <div class="cell"><span class="lbl">Step</span><span class="val">{{N}} / {{total}}</span></div>
    <div class="cell"><span class="lbl">From</span><span class="val">{{skill-slug}}</span></div>
    <div class="cell"><span class="lbl">Chapter</span><span class="val">{{book_number}}</span></div>
    <div class="cell"><span class="lbl">Depth</span><span class="val">{{beginner|intermediate|expert}}</span></div>
  </div>

  <!-- Progress strip as a horizontal toc -->
  <div class="toc" style="margin-top:24px">
    <span class="toc-head">Curriculum</span>
    {{for each step:
      <a href="#"{{ if done: ' style="opacity:.55"' }}>
        <span class="num">{{N}}</span>{{concept}}{{ if done: ' ✓' }}
      </a>
    }}
  </div>

  <!-- Tutorial step (component from demo section 09) -->
  <section class="sect">
    <span class="kicker">teaching</span>
    <h2>{{step-name}}</h2>
    <div class="tutorial">
      <div class="tut-num">{{N}}</div>
      <div class="tut-body">
        <p>{{teaching paragraph 1 with inline code if needed}}</p>
        <p>{{teaching paragraph 2}}</p>
        <p>{{teaching paragraph 3}}</p>
      </div>
    </div>
  </section>

  <!-- Quiz as a Q&A block -->
  <section class="sect">
    <span class="kicker">quick check</span>
    <h2>Quiz</h2>
    <div class="qna">
      <div class="qna-q">
        <span class="qna-tag">Q</span>
        <p>{{question}}</p>
      </div>
      <div class="qna-a">
        <span class="qna-tag">A</span>
        <p>{{Four labeled options — A/B/C/D. The correct answer is marked here only after the user picks; before that, render plain choices.}}</p>
      </div>
    </div>
  </section>

  <!-- After-quiz feedback (only when answered): use .callout -->
  {{if correct: <div class="callout ok"><strong>Correct.</strong> {{why}}</div>}}
  {{if wrong:   <div class="callout warn"><strong>Not quite.</strong> {{correction}}</div>}}

</div>
```

---

## 4 · Walk recap (completion)

**Path:** `artifacts/walks/<topic-slug>-recap.html` (durable)

**Title:** `Walk recap · <topic>`

**EXTRA_CSS:** *(none)*

**Body skeleton:**

```html
<div class="wrap">

  <span class="eyebrow"><span class="dot"></span>Walk complete · {{topic}}</span>
  <h1>{{punchline of what was mastered}}</h1>
  <p class="lede">{{2-3 sentence summary of the walk}}</p>

  <div class="meta-bar">
    <div class="cell"><span class="lbl">Cleared</span><span class="val">{{X}} / {{N}}</span></div>
    <div class="cell"><span class="lbl">Revisit</span><span class="val">{{Y}}</span></div>
    <div class="cell"><span class="lbl">Quiz accuracy</span><span class="val">{{pct}}%</span></div>
    <div class="cell"><span class="lbl">Elapsed</span><span class="val">{{duration}}</span></div>
  </div>

  <!-- What you own now -->
  <section class="sect">
    <span class="kicker">what you own now</span>
    <h2>The takeaways</h2>
    {{for each mastered concept:
      <div class="capsule">
        <p class="capsule-lede">{{concept name}}</p>
        <p>{{one-line synthesis of what you can defend}}</p>
        <p class="muted"><code>{{skill-slug}}/{{book_number}}</code></p>
      </div>
    }}
  </section>

  <!-- Worth a second look -->
  {{if any fumbles:
    <section class="sect">
      <span class="kicker">worth a second look</span>
      <h2>Where you stumbled</h2>
      {{for each fumble:
        <div class="callout warn">
          <strong>{{concept}}</strong>
          <p>{{what you picked vs. correct + why}}</p>
          <p class="muted">Tagged for review on next walk · <code>{{skill}}/{{book_number}}</code></p>
        </div>
      }}
    </section>
  }}

  <!-- Where to go next -->
  <section class="sect">
    <span class="kicker">follow-on walks</span>
    <h2>Where to go next</h2>
    <div class="toc">
      {{for each suggested walk:
        <a href="#"><span class="num">▸</span>{{title}}</a>
      }}
    </div>
  </section>

</div>
```

---

## 5 · Cross-domain comparison

**Path:** `artifacts/comparisons/YYYY-MM-DD-<topic-slug>.html`

**Title:** `Comparison — <topic> across N books`

**EXTRA_CSS:** *(none)*

**Body skeleton:**

```html
<div class="wrap">

  <span class="eyebrow"><span class="dot"></span>Cross-domain comparison</span>
  <h1>{{title naming the disagreement}}</h1>
  <p class="lede">{{lede setting up the dimensions being compared}}</p>

  <div class="meta-bar">
    <div class="cell"><span class="lbl">Topic</span><span class="val">{{topic}}</span></div>
    <div class="cell"><span class="lbl">Authors</span><span class="val">{{N}}</span></div>
    <div class="cell"><span class="lbl">Sub-concepts</span><span class="val">{{M}}</span></div>
    <div class="cell"><span class="lbl">Generated</span><span class="val">{{date}}</span></div>
  </div>

  <section class="sect">
    <table class="compare">
      <thead>
        <tr>
          <th>Sub-concept</th>
          {{for each author: <th>{{author}}<br><span class="th-sub">{{book}}</span></th>}}
        </tr>
      </thead>
      <tbody>
        {{for each row:
          <tr>
            <td class="row-label"><strong>{{concept}}</strong><br><span class="row-sub">{{sub}}</span></td>
            {{for each cell:
              <td>
                <span class="tag-stance {{agree|extend|tension}}">{{stance}}</span>
                <p>{{body}}</p>
                <p class="muted"><code>{{cite}}</code></p>
              </td>
            }}
          </tr>
        }}
      </tbody>
    </table>
  </section>

  <!-- Closing synthesis -->
  <section class="sect">
    <p>{{paragraph naming the real fault line and the practical takeaway}}</p>
  </section>

</div>
```

For the `agree / extend / tension` stance pills, use the
`.tag` modifier patterns: `.tag.ok` for agree, `.tag.insight` for
extend, `.tag.warn` for tension.

---

## 6 · Chapter toolkit (Tier-2 deep dive)

**Path:** `artifacts/toolkits/<book-slug>-<book_number>.html`

**Title:** `<book_number> — <chapter title> · <book-slug>`

**EXTRA_CSS:** *(none)*

**Body skeleton:**

```html
<div class="wrap">

  <span class="eyebrow"><span class="dot"></span>Chapter toolkit · Tier 2</span>
  <h1>{{chapter title}}</h1>
  <p class="lede">{{the chapter's "Core Idea" — one paragraph}}</p>

  <div class="meta-bar">
    <div class="cell"><span class="lbl">Book</span><span class="val">{{book title}}</span></div>
    <div class="cell"><span class="lbl">Chapter</span><span class="val">{{book_number}}</span></div>
    <div class="cell"><span class="lbl">Author</span><span class="val">{{author}}</span></div>
    <div class="cell"><span class="lbl">Tier</span><span class="val">2 · toolkit</span></div>
  </div>

  <!-- Frameworks introduced -->
  <section class="sect">
    <span class="kicker">frameworks introduced</span>
    <h2>The primitives</h2>
    {{for each framework:
      <div class="def">
        <span class="def-tag">framework</span>
        <h3 class="def-term">{{framework name}}</h3>
        <p class="def-etymon"><em>when it fires:</em> {{trigger}}</p>
        <p class="def-body">{{1-3 sentence explanation with inline <code> for identifiers}}</p>
      </div>
    }}
  </section>

  <!-- Data tables / enums as .rules -->
  {{if any enums or data tables:
    <section class="sect">
      <span class="kicker">{{table name}}</span>
      <table class="rules">
        <thead><tr><th>{{col1}}</th><th>{{col2}}</th><th>{{col3}}</th></tr></thead>
        <tbody>{{rows}}</tbody>
      </table>
    </section>
  }}

  <!-- Anti-patterns as crit/warn callouts -->
  <section class="sect">
    <span class="kicker">anti-patterns to hunt</span>
    <h2>What to look for</h2>
    {{for each anti-pattern:
      <div class="callout warn">
        <strong>{{name}}</strong>
        <p>{{1-2 sentences}}</p>
        <p class="muted"><em>Mitigation:</em> {{mitigation}}</p>
      </div>
    }}
  </section>

  <!-- Defender's playbook as ok callouts -->
  <section class="sect">
    <span class="kicker">defender's playbook</span>
    <div class="callout ok">
      <strong>The defaults that actually defend.</strong>
      <ul>{{practices}}</ul>
    </div>
  </section>

  <!-- Optional: plate diagram if the chapter has a key flow -->
  {{if structural flow worth diagramming:
    <!-- See § plate-concept in reference/full-demo-light.html -->
    <div class="plate">{{...}}</div>
  }}

</div>
```

---

## 7 · Glossary

**Path:** `artifacts/glossaries/<book-slug>.html` *or*
`artifacts/glossaries/full-library.html`

**Title:** `Glossary — <book or library>`

**EXTRA_CSS:** *(none)*

**Body skeleton:**

```html
<div class="wrap">

  <span class="eyebrow"><span class="dot"></span>Glossary · {{scope}}</span>
  <h1>{{Title — "Terms in <book>" or "Cross-library terms"}}</h1>
  <p class="lede">{{lede explaining the scope and conventions}}</p>

  <div class="meta-bar">
    <div class="cell"><span class="lbl">Terms</span><span class="val">{{N}}</span></div>
    <div class="cell"><span class="lbl">Source skills</span><span class="val">{{M}}</span></div>
    <div class="cell"><span class="lbl">Coverage</span><span class="val">A–Z</span></div>
  </div>

  <!-- A-Z bar as a toc -->
  <div class="toc">
    <span class="toc-head">Jump to</span>
    {{for each letter A-Z (only present ones bold):
      <a href="#sec-{{letter}}"><span class="num">{{letter}}</span></a>
    }}
  </div>

  {{for each letter section:
    <section class="sect" id="sec-{{letter}}">
      <span class="kicker">{{letter}}</span>
      <h2>{{letter}}</h2>
      {{for each term:
        <div class="def">
          <span class="def-tag">{{source-skill}}</span>
          <h3 class="def-term">{{term}}</h3>
          {{if etymology/synonym: <p class="def-etymon"><em>also:</em> {{aka}}</p>}}
          <p class="def-body">{{definition}}</p>
          <p class="muted"><code>{{chapter refs as code chips}}</code></p>
        </div>
      }}
    </section>
  }}

</div>
```

---

## 8 · Cheatsheet

**Path:** `artifacts/cheatsheets/<book-slug>.html`

**Title:** `Cheatsheet — <book title>`

**EXTRA_CSS:**

```css
/* Cheatsheet wants two columns of dense blocks. */
.cheat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin: 20px 0; }
.cheat-grid > .span-2 { grid-column: 1 / -1; }
@media (max-width: 720px) { .cheat-grid { grid-template-columns: 1fr; } }
```

**Body skeleton:**

```html
<div class="wrap">

  <span class="eyebrow"><span class="dot"></span>Cheatsheet · {{skill-slug}}</span>
  <h1>{{book title}}</h1>
  <p class="lede">{{lede — the entire book as one operational page}}</p>

  <div class="meta-bar">
    <div class="cell"><span class="lbl">Format</span><span class="val">One-pager</span></div>
    <div class="cell"><span class="lbl">Tables</span><span class="val">{{N}}</span></div>
    <div class="cell"><span class="lbl">Print</span><span class="val">A4 / Letter</span></div>
  </div>

  <div class="cheat-grid">

    {{for each compact table:
      <section class="sect">
        <span class="kicker">{{block name}}</span>
        <h3>{{title}}</h3>
        <table class="rules">{{rows}}</table>
      </section>
    }}

    {{for each step-list:
      <section class="sect">
        <span class="kicker">{{ladder name}}</span>
        <h3>{{title}}</h3>
        <ol class="tutorial-steps">{{numbered steps}}</ol>
      </section>
    }}

    <!-- Wide blocks (commandments, principles) span both columns -->
    <section class="sect span-2">
      <span class="kicker">{{e.g. commandments}}</span>
      <h3>{{title}}</h3>
      <ol>{{numbered items with inline <code> where applicable}}</ol>
    </section>

  </div>

</div>
```

---

## 9 · Concept map (Tier-1 plate)

**Path:** `artifacts/concept-maps/<book-slug>.html`

**Title:** `Concept map — <book title>`

**EXTRA_CSS:** *(none)*

**Body skeleton:**

```html
<div class="wrap">

  <span class="eyebrow"><span class="dot"></span>Concept map · {{skill-slug}} · Tier 1</span>
  <h1>{{thesis as headline}}</h1>
  <p class="lede">{{lede explaining how the frameworks compose}}</p>

  <div class="meta-bar">
    <div class="cell"><span class="lbl">Frameworks</span><span class="val">{{N}}</span></div>
    <div class="cell"><span class="lbl">Edges</span><span class="val">{{M}}</span></div>
    <div class="cell"><span class="lbl">Chapters covered</span><span class="val">{{K}}</span></div>
  </div>

  <!-- Plate component — see reference/full-demo-light.html § plate-concept -->
  <div class="plate">
    <div class="plate-head">
      <span>Concept map</span>
      <span class="plate-meta">{{date}} · {{book}}</span>
    </div>
    <div class="plate-body">
      <svg viewBox="0 0 800 540" preserveAspectRatio="xMidYMid meet">
        <!-- thesis at center, frameworks orbiting -->
        <!-- USE THE SAME SVG CONVENTIONS AS reference/full-demo-*.html § plate-concept:
             - var(--plate-stroke) for primary strokes
             - var(--plate-stroke-soft) for secondary
             - var(--plate-text) for labels
             - var(--plate-accent) for the thesis node fill
        -->
      </svg>
    </div>
    <div class="plate-legend">
      <span><i class="leg solid"></i> derives from thesis</span>
      <span><i class="leg dashed"></i> tensions with</span>
    </div>
  </div>

  <!-- Selected-framework detail as a .def below the plate -->
  <section class="sect">
    <span class="kicker">selected · {{node name}}</span>
    <div class="def">
      <span class="def-tag">framework</span>
      <h3 class="def-term">{{node name}}</h3>
      <p class="def-body">{{explanation}}</p>
    </div>
  </section>

</div>
```

The plate SVG is the heart of this layout. Pull node positions and
edge list from the source skill's `SKILL.md` concept-map section.

---

## 10 · Library index

**Path:** `artifacts/library.html`

**Title:** `Library — Your bookshelf`

**EXTRA_CSS:**

```css
.shelves { display: grid; gap: 40px; margin-top: 32px; }
.shelf > h2 { margin-bottom: 16px; }
.book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
```

**Body skeleton:**

```html
<div class="wrap">

  <span class="eyebrow"><span class="dot"></span>Library · {{N}} books · {{M}} chapters</span>
  <h1>The Knowledge Guide bookshelf</h1>
  <p class="lede">{{lede explaining drop-in extensibility — every book becomes a skill, the router picks it up}}</p>

  <div class="meta-bar">
    <div class="cell"><span class="lbl">Books</span><span class="val">{{N}}</span></div>
    <div class="cell"><span class="lbl">Chapters</span><span class="val">{{M}}</span></div>
    <div class="cell"><span class="lbl">Genres</span><span class="val">{{count}}</span></div>
    <div class="cell"><span class="lbl">Last ingest</span><span class="val">{{date}}</span></div>
  </div>

  <div class="shelves">
    {{for each genre:
      <section class="shelf">
        <span class="kicker">shelf</span>
        <h2>{{genre name}}</h2>
        <div class="book-grid">
          {{for each book in this genre — use .source card as the book card:
            <div class="source insight">
              <div class="src-id">
                <span class="id-pill">{{skill-slug}}</span>
                <span class="id-dom">{{author-lastname}}</span>
                <span class="id-status">{{N}} ch</span>
              </div>
              <div class="src-title">{{book title}}</div>
              <div class="src-byline">{{author}}</div>
              <p>{{one-line blurb}}</p>
              <div class="src-tags">
                <span class="tag">Nutshell</span>
                <span class="tag">Walk</span>
                <span class="tag">Ask</span>
              </div>
            </div>
          }}
        </div>
      </section>
    }}
  </div>

</div>
```

---

## Filename rules (single source of truth)

| Use case | Path | Cacheable? |
|---|---|---|
| Nutshell | `nutshells/<skill-slug>.html` | yes |
| Synthesis | `synthesis/YYYY-MM-DD-<slug>.html` | no |
| Walk step | `walks/<topic-slug>-step-<N>.html` | overwritten per step |
| Walk recap | `walks/<topic-slug>-recap.html` | yes (durable) |
| Comparison | `comparisons/YYYY-MM-DD-<topic-slug>.html` | no |
| Toolkit | `toolkits/<skill-slug>-<book_number>.html` | yes |
| Glossary (book) | `glossaries/<skill-slug>.html` | yes |
| Glossary (library) | `glossaries/full-library.html` | yes |
| Cheatsheet | `cheatsheets/<skill-slug>.html` | yes |
| Concept map | `concept-maps/<skill-slug>.html` | yes |
| Library | `library.html` (root of artifacts/) | yes |

## Index page

`artifacts/index.html` must be regenerated after every artifact write.
Use the same shell + the **library** layout's `.shelves` pattern, but
group by use-case instead of genre. Each entry is a `.source` card
pointing at the artifact path with a kicker chip telling you what
kind of artifact it is.
