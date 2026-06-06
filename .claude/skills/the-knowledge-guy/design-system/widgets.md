# Concept Widgets — the interactive-illustration contract

A **concept widget** is a small, manipulable SVG illustration in a course
lesson's **theory** section: the learner toggles / steps / drags and the diagram
re-colors to teach a structural, process, or threshold idea (toggle a sanitizer
and watch taint stop at it; step a pipeline; drag a write-length past a buffer's
capacity and watch it turn critical).

This file is the **frozen contract** between three parties:

- the **teaching subagent** (walk-mode Step-6b, reused by `course` mode) emits a
  widget spec as JSON,
- the **widget engine** in `design-system/shell.html` renders + animates it,
- **`book-to-skill/scripts/lint_concept_widgets.py`** validates it.

Widgets are the interactive sibling of the static `.plate` / `svg.illus`
diagrams. Authoring rule: **0–1 widget + 0–1 static illustration per chapter, and
only where it earns its place** — the same bar the pipeline already uses to
decide whether a chapter gets a runnable lab. Most concepts stay prose-only.

---

## The core invariant (what keeps widgets theme-safe)

**The engine only ever swaps CSS classes — it never sets a `fill`, `stroke`, or
inline `style` color on any element.** Every color resolves from a design-system
variable through the existing `.plate` / `.illus` classes. So themes invert for
free, a theme-toggle *mid-interaction* recolors correctly with no re-render, and
a widget can never introduce a non-system color. Bespoke static SVG is held to
the same rule by the lint.

---

## Top-level shape

One JSON island per page — `<script type="application/json" id="kg-concept-widgets">` —
an **array** of widget objects (mirrors `#kg-exercises`). Each object's `id`
matches an empty `<figure class="widget" data-widget-id="<id>"></figure>` mount in
the theory section; the engine fills the figure from the spec.

```jsonc
[ { "id": "taint-flow", "type": "toggle-state", "surface": "illus", "title": "Sanitizer gate", … } ]
```

### Shared fields (every widget)

| field | req | meaning |
|---|---|---|
| `id` | yes | unique within the page; matches the `data-widget-id` mount |
| `type` | yes | one of the closed enum: `flow` `toggle-state` `stepper` `slider` `compare` |
| `surface` | yes | `"plate"` (Tier-1 framed, neutral) or `"illus"` (Tier-2 inline, allows semantic state) |
| `title` | yes | mono uppercase label in the widget head |
| `caption` | no | default italic caption under the SVG (overridden by step/toggle/slider captions) |

**Fixed `viewBox="0 0 640 280"`.** All coordinates are author-supplied and
lint-bounded to that frame (including `x±w/2`, `y±h/2`).

### Reusable objects

**`node`** (used by `flow`, `toggle-state`, `stepper`):
```jsonc
{ "id": "src", "label": "Source", "sub": "argv[1]", "x": 90, "y": 140, "w": 120, "h": 52, "kind": "normal" }
```
- `x,y` = the node's **center**; `w,h` optional (default `120×52`).
- `kind` — the node's resting identity. `plate`: `normal | accent | muted`.
  `illus`: `normal | accent | ok | warn | crit | ins`.

**`edge`** (used by `flow`, `toggle-state`, `stepper`):
```jsonc
{ "id": "e1", "from": "src", "to": "proc", "emph": false, "label": "flows" }
```
- `from`/`to` **must** reference declared node ids. The engine routes an
  orthogonal path with an arrowhead; `label` (optional) renders as a mono pill.
- `emph` — resting emphasis (accent edge) when not driven by a step/toggle.

---

## Class vocabulary (engine emits ONLY these — never raw colors)

| | node base | node highlight | node semantic | edge base | edge emph |
|---|---|---|---|---|---|
| `plate` | `node-bg` (`normal`), `node-bg-2` (`muted`) | `node-accent` | — (not on plate) | `edge` | `edge-emph` |
| `illus` | `il-node` (`normal`/`muted`) | `il-node-acc` | `il-node-ok` / `-warn` / `-crit` / `-ins` | `il-edge` | `il-edge-emph` |

Arrowheads: the engine injects `arrow` + `arrow-emph` markers (plate) or
`il-arrow` + `il-arrow-emph` (illus) into `<defs>` and switches an edge's
`marker-end` between them when its state changes.

**Theme-safety rule (lint-enforced):**
- Any **semantic** value (`ok` / `warn` / `crit` / `ins`) — as a node `kind`, a
  toggle `nodeClass` value, or a slider threshold state — **requires
  `surface:"illus"`** (that's where `--ok/--warn/--crit/--insight` live).
- `plate` widgets are limited to `normal/accent/muted`, preserving the
  one-accent rule on Tier-1.
- Edge state is `normal` or `emph` **only** — there is no danger-colored edge
  class. Show danger on the **target node** (`il-node-crit`), not the edge.

### Node state resolution (how the engine picks a class)

Low-level `kind → class` (used directly by `toggle-state`, `slider`, `compare`):
`plate`: normal→`node-bg`, accent→`node-accent`, muted→`node-bg-2`.
`illus`: normal/muted→`il-node`, accent→`il-node-acc`, ok→`il-node-ok`,
warn→`il-node-warn`, crit→`il-node-crit`, ins→`il-node-ins`.

`flow` / `stepper` active/inactive (an "effective kind" feeds the table above):
- **active** + semantic base kind → that semantic class (it "lights up").
- **active** + non-semantic base kind → `accent` highlight.
- **inactive** + semantic base kind → `normal` (dimmed until the step reaches it).
- **inactive** + non-semantic → its authored kind (`normal`/`accent`/`muted`).

---

## The five widget types

### `flow` — a steppable pipeline

Prev / Next / **Play** walk an ordered set of steps; each step lights up some
nodes + edges and shows a caption.

```jsonc
{ "id":"taint-flow", "type":"flow", "surface":"plate", "title":"Taint flow",
  "nodes":[ {"id":"src","label":"Source","sub":"argv[1]","x":90,"y":140},
            {"id":"proc","label":"strcpy","sub":"copy","x":320,"y":140},
            {"id":"sink","label":"Sink","sub":"buf[64]","x":550,"y":140} ],
  "edges":[ {"id":"e1","from":"src","to":"proc","label":"flows"},
            {"id":"e2","from":"proc","to":"sink","label":"overflows"} ],
  "steps":[ {"active":["src"],            "activeEdges":[],          "caption":"Untrusted input enters at the source."},
            {"active":["src","proc"],     "activeEdges":["e1"],      "caption":"It reaches strcpy unchecked."},
            {"active":["src","proc","sink"],"activeEdges":["e1","e2"],"caption":"It overflows the fixed buffer."} ] }
```
Required: `nodes`, `edges`, `steps[]` (≥2; each `{active[],activeEdges[],caption}`).

### `toggle-state` — booleans re-color the diagram

```jsonc
{ "id":"sanitizer", "type":"toggle-state", "surface":"illus", "title":"Sanitizer gate",
  "nodes":[ {"id":"in","label":"Input","x":80,"y":140},
            {"id":"san","label":"escape()","x":320,"y":140,"kind":"ok"},
            {"id":"db","label":"Query","x":560,"y":140} ],
  "edges":[ {"id":"e1","from":"in","to":"san"}, {"id":"e2","from":"san","to":"db"} ],
  "toggles":[ {"id":"t1","label":"Sanitizer on","default":true,
      "on":  {"nodeClass":{"san":"ok"},  "edgeClass":{"e2":"normal"}, "caption":"Tainted input is neutralised at escape(); the query is safe."},
      "off": {"nodeClass":{"san":"crit"},"edgeClass":{"e2":"emph"},   "caption":"Sanitizer off — taint flows straight to the query. Injection."} } ] }
```
Required: `nodes`, `edges`, `toggles[]` (1–3). Each toggle has a `default`
boolean and `on`/`off` branches; a branch may set `nodeClass[nodeId]→kind`,
`edgeClass[edgeId]→normal|emph`, and a `caption`. Toggles apply in array order
(last write wins per element) — keep toggles affecting disjoint elements.

### `stepper` — highlight arbitrary parts in sequence

Same `nodes`/`edges`/`steps[]` model as `flow`, but Prev / Next only (no Play),
and steps may highlight any nodes/edges (not necessarily cumulative). Use for
"the algorithm visits X, then Y, then Z."

### `slider` — a value crosses a threshold

```jsonc
{ "id":"overflow", "type":"slider", "surface":"illus", "title":"Write length vs capacity",
  "slider":{ "min":0,"max":128,"step":1,"default":40,"threshold":64,"unit":"bytes","label":"Write length" },
  "visual":{ "kind":"bar", "capacityNode":"cap", "fillNode":"fill" },
  "nodes":[ {"id":"cap","label":"Capacity 64B","x":320,"y":96,"w":480,"h":40,"kind":"muted"},
            {"id":"fill","label":"","x":80,"y":150,"w":40,"h":40,"kind":"normal"} ],
  "below":{ "caption":"The write fits inside the 64-byte buffer." },
  "atOrAbove":{ "caption":"The write exceeds capacity — out-of-bounds write (CWE-787)." } }
```
Required: `slider{min,max,step,default,threshold,unit,label}`,
`visual{kind:"bar",fillNode,capacityNode}`, `nodes` (incl. the `fillNode` and
`capacityNode`), `below{caption}`, `atOrAbove{caption}`. The control is a native
`<input type="range">`. The engine scales the `fillNode` rect's **width** across
the `capacityNode`'s span (geometry only), shows a live `value unit` readout, and
re-classes the fill node to `crit` (≥`threshold`) or `normal` (below). `slider`
requires `surface:"illus"` (it uses the crit state).

### `compare` — select a panel to see when it wins

```jsonc
{ "id":"fuzz-choice", "type":"compare", "surface":"illus", "title":"Mutation vs generation",
  "panels":[ {"id":"mut","label":"Mutation","sub":"radamsa","x":175,"y":140,"w":270,"h":120,
              "detail":"Pipe a corpus through radamsa. No spec needed — best for proprietary formats."},
             {"id":"gen","label":"Generation","sub":"boofuzz","x":465,"y":140,"w":270,"h":120,
              "detail":"Declare the grammar. Pays off only with a documented spec."} ],
  "caption":"Pick an approach to see when it wins." }
```
Required: `panels[]` (exactly 2 or 4; each `{id,label,sub?,x,y,w,h,detail}`).
Selecting a panel re-classes it to `accent`, de-selects siblings, and shows its
`detail` in the caption. Panels are focusable buttons (keyboard + touch).

---

## State is ephemeral (deliberate)

Widget interaction state is **not** persisted. Reasons: widgets are
*exploration*, not graded mastery — the `localStorage['kg-lab-progress-v1']`
store is keyed by exercise `status` and drives the mastery meter; a "user dragged
a slider" event has no `status` and would corrupt that math. And a course page
must be reproducible/cacheable — re-opening should show the pristine teaching
state (step 0, default toggles, default slider), not a half-dragged remnant. So
every widget resets to its authored defaults on load.

---

## Motion + accessibility

- All motion (state-change `transition`s, the `flow` Play `@keyframes`) lives
  inside `@media (prefers-reduced-motion: no-preference)`, scoped to
  `.widget svg`. Reduced-motion users get instant state changes; **Play** jumps
  straight to the final step.
- Controls are native and labelled: slider = `<input type="range">`; toggles =
  `<button role="switch" aria-checked>`; steppers/Play/compare = `<button>`s.
  The SVG carries `role="img"` + `<title>`/`<desc>`; the caption strip is
  `aria-live="polite"` so step/toggle/slider changes are announced.

---

## Bespoke static SVG (the non-widget path)

For a structural diagram **no widget covers** (a memory layout, a nested-box
hierarchy), the subagent may instead emit **one** static inline SVG — a
`<svg class="illus" viewBox="…">` or a `<div class="plate">…</div>` — placed in
the `#theory-illustration` slot. It is inert (no JS, no animation) and must use
**only** design-system classes (`il-*` / `node-*` / `edge-*` / `arrow*` /
`zone-label`). **Never** `fill="#…"`, `stroke="#…"`, `style="…color…"`, a
`<script>`, or an `on*=` handler — `lint_concept_widgets.py` rejects all of
these. `fill="none"`, `fill="currentColor"`, `stroke-opacity`, and `var(--…)`
are allowed.

---

## Quality bar

- **Theme-safe by construction.** Classes only; never a color attribute.
- **Faithful + earned.** A widget must teach a real structural/process/threshold
  idea from the chapter; default to prose. Never illustrate a definition a
  sentence already nails.
- **In-frame + referential-integrity.** Coordinates within `0 0 640 280`; every
  edge/step/toggle id references a declared node/edge. The lint hard-fails
  violations and the engine renders a visible stub rather than a broken page.
