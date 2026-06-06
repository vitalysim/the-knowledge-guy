# Design system — the-knowledge-guy

The skill emits an HTML artifact on every invocation. This directory
is the single source of truth for what those artifacts look like.

The chosen design system is **Knowledge Guide · Modern** — a
technical-reader aesthetic built on Bricolage Grotesque + JetBrains
Mono, a single cobalt accent (`#2742d3` light / `#6c89ff` dark), and
its named components for treating books as inspectable data. The
original 24 static components are joined by an **interactive practice
set** added for `course` mode: `.exercise`, `.options/.opt` (with
`.correct`/`.incorrect`/`.chosen` states), `.ex-feedback`, `.runner`
(code editor + sandboxed output + verdict), `.btn` variants,
`.mastery` meter, and `.ex-badge`.

## Files in this directory

- **`shell.html`** — the complete base wrapper. Has three placeholders:
  `{{TITLE}}`, `{{EXTRA_CSS}}`, `{{BODY}}`. Read it, substitute, write
  to `artifacts/…`. Includes:
  - The full Knowledge Guide · Modern CSS (foundations, chrome,
    content components, diagrams, rules table).
  - Manual `[data-theme="light"|"dark"]` overrides on top of the
    built-in `prefers-color-scheme` auto behavior, so the toggle wins.
  - A `[data-density="compact"]` variant.
  - A two-button toggle bar (top-right) wired with `localStorage` so
    the user's choice persists across artifacts.
  - The **lab engine** — a guarded `<script>` that hydrates a
    `#kg-exercises` JSON island into interactive practice (auto-checked
    quizzes, runnable code labs in a sandboxed `<iframe>`, "check with
    Claude" buttons) and persists progress to `localStorage`. It no-ops
    on any page without the island, so it ships harmlessly everywhere.
- **`layouts.md`** — one section per use case (nutshell, synthesis,
  walk-session, walk-recap, comparison, toolkit, glossary, cheatsheet,
  concept-map, library, **course-chapter, course-index**). Each gives
  path, title, EXTRA_CSS (usually empty), and the body skeleton built
  from `shell.html` components.
- **`reference/full-demo-light.html`** /
  **`reference/full-demo-dark.html`** — the canonical demo of every
  component, in both themes. Open these in a browser when you need a
  refresher on which component to reach for or how it markups.
- **`README.md`** — this file.

## How the skill renders HTML

The rendering procedure is the same for every mode:

```
1. Identify use case (nutshell / synthesis / walk-session / …)
2. Read .claude/skills/the-knowledge-guy/design-system/shell.html
3. Open layouts.md, find the section for this use case
4. Read its EXTRA_CSS block (often empty) and body skeleton
5. Substitute {{TITLE}}, {{EXTRA_CSS}}, {{BODY}} into the shell
6. Inside the body, substitute use-case-specific placeholders
   ({{book-title}}, {{TOC}}, {{CHAPTERS}}, etc.) — see layouts.md
7. Write the result to artifacts/<subfolder>/<filename>.html
8. Update artifacts/index.html catalog
9. Tell the user the path so they can open it
```

## Hard rules (do not violate)

- **Every artifact opens with the document chrome:** `.eyebrow` →
  `<h1>` → `.lede` → `.meta-bar`. Optional `.toc` follows if the
  document is long enough. This is the visual signature of the family.
- **Citations are `.source` cards, not inline footnotes.** Treat each
  citation as data: book, author, locator, status. See demo § source.
- **Single accent** — `--accent` (cobalt). Never introduce a second
  hue. `--ok`, `--warn`, `--crit`, `--insight` are for true semantic
  state (correct quiz answer, fumble, dangerous anti-pattern,
  cross-book insight). Use sparingly.
- **Mono is architecture, not decoration.** Use the mono family for
  kickers, meta labels, code, tags, terminal, table-of-contents
  numerals. Do NOT make body copy mono.
- **Plate diagrams** (Tier-1 visualisations) use SVG with `--plate-*`
  CSS variables so they invert cleanly in dark mode. Never hardcode
  colors in SVG — `stroke="#000"` will be invisible in dark mode.
- **Do not invent CSS.** Pull EXTRA_CSS from `layouts.md` verbatim.
  If you need a one-off tweak, use inline `style=""`. New utility
  classes belong in `shell.html`, added deliberately by editing this
  directory — never per-artifact.
- **Do not use frameworks** (Bootstrap, Tailwind, etc.) or external
  CSS files. Every artifact is self-contained — CSS inline, fonts via
  the Google Fonts CDN. The **one** additional allowed CDN request is
  **Pyodide**, lazy-loaded only when a Python lab is Run; it degrades to
  "check with Claude" offline. JS labs need no network — prefer them.
- **Do not render an open task's `rubric` or `model_answer`** into a
  course page — they are the grading key and stay server-side (the
  `check` sub-mode reads them in chat). The renderer whitelists fields
  per exercise family before inlining the `#kg-exercises` island.
- **Do not write HTML directly into `previews/`.** That directory is
  the design exploration archive. Live outputs go to `artifacts/`.
- **Always update `artifacts/index.html`** after writing a new
  artifact. The catalog is the user's way to browse what's been
  generated.

## When in doubt

Open the reference demo at
`reference/full-demo-light.html` (or `-dark.html`) in a browser, find
a section visually similar to what you're building, and use its
markup as a starting point. Every component in the system is named
and demonstrated there.
