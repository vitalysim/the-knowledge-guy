# Walk mode — interactive guided teacher

This is the procedure for **walk mode** of `the-knowledge-guy`. You arrived
here because mode dispatch in `SKILL.md` matched a walk trigger
(`walk`/`teach`/`lesson`/`tour`/`learn`/`guide`, `--walk` suffix, or the
literal `resume`).

The argument is `$QUERY`. Strip the trigger verb to get `$TOPIC`
(e.g. `walk me through Kerberos` → `$TOPIC = "Kerberos"`).
For `$QUERY == "resume"`, leave `$TOPIC` empty.

You build a curriculum, materialise it as a visible task list, then loop:
**teach → quiz → record → next**, saving progress to memory after every
step so the user can resume across sessions. Worked transcripts are in
[examples.md](examples.md).

---

## Step 1 — Resume check (always, before anything else)

```bash
MEM_DIR="$HOME/.claude/projects/-Users-vitaly-MyPlace-projects-the-knowledge-guy/memory"
mkdir -p "$MEM_DIR"
ls "$MEM_DIR"/walk-*.md 2>/dev/null
```

For each walk file found, `Read` it (`limit: 30`) and parse its
frontmatter (`name`, `description`) plus the `Status:` line.

- If `$QUERY == "resume"` and at least one walk has `Status: in_progress`,
  ask the user (via `AskUserQuestion`) which open walk to resume — list up
  to 4. If none are open, tell the user and offer to start a new walk.
- If `$TOPIC` is non-empty and any open walk's name/topic overlaps the
  topic slug, ask: **Resume that walk** / **Restart this topic from
  scratch** / **Start a different walk on this topic** (e.g. forking).

If resuming: skip to Step 6 at the saved current step. Otherwise continue
to Step 2.

---

## Step 2 — Route + scope

Run the **same discovery** as ask mode (see `SKILL.md` Step 1):

```bash
SKILLS_ROOT="$(pwd)/.claude/skills"
find "$SKILLS_ROOT" -maxdepth 2 -name SKILL.md
```

Read each frontmatter (`limit: 40`), exclude `the-knowledge-guy` and
`book-to-skill`, parse `name + description + when_to_use`.

Match `$TOPIC` against each candidate's vocabulary. Walks have **stricter
routing** than ask mode — the goal is a coherent curriculum, not maximal
coverage:

- **Single-skill walk** when one skill clearly owns the topic
  (e.g. "access tokens" → forshaw-windows-security; "fuzzing for beginners"
  → from-day-zero-to-zero-day).
- **Multi-skill walk** *only* when the topic genuinely needs braided
  perspectives (e.g. "Kerberoasting end-to-end" needs forshaw mechanics
  *and* hack-like-a-legend tradecraft; "vulns in ML serving stacks" needs
  from-day-zero *and* farlow-ai-security).
- **No matches** → run the *No-coverage recovery* below, then either
  exit, broadcast in ask mode, or hand off to ingest mode.

Print one line:

> Walking through **<topic>** via `<skill-a>` (+ `<skill-b>` for tradecraft).
> Generating curriculum…

### No-coverage recovery

When `$TOPIC` matches none of the installed skills, list the installed
skills with one-line topic summaries drawn from each `when_to_use`, then
use `AskUserQuestion` to offer three options:

1. **Broadcast across all skills (ask mode)** — switch to ask mode and
   fan out across every domain skill anyway. Pick this when the topic is
   adjacent to several skills.
2. **Add a new book first (ingest)** — collect a PDF/EPUB path with a
   second `AskUserQuestion`, then hand off to `book-to-skill` via
   `Skill(skill="book-to-skill", args="<path>")` exactly like *Ingest
   mode* in `SKILL.md`. When the child returns, restart this walk from
   Step 2 — the new skill should now match.
3. **Cancel** — stop. Tell the user how to re-invoke once they know
   which skill to use.

Default selection: (1) when the topic is broad/cross-domain; (2) when
the topic is clearly outside every installed skill's vocabulary.

---

## Step 3 — Generate the curriculum (one subagent)

Spawn a single `Agent` (subagent_type `general-purpose`). Prompt:

```
You are a curriculum designer for a guided technical walk.

Topic: <TOPIC>
Source skills: <list of matched skill slugs>

For each source skill, READ ONLY:
  - <skill-dir>/SKILL.md       (concept map + topic index)
  - <skill-dir>/chapters_manifest.json   (chapter list)
Do NOT load chapter bodies — the step-execution subagents will do that.

Design a 5-10 step curriculum on <TOPIC>:
  - Each step: one focused concept, in pedagogical order (prereqs first,
    simple → complex).
  - Each step points to exactly one chapter file (the primary source).
    A step may cite a secondary chapter, but only one is the "teaching"
    chapter.
  - For multi-skill walks, tag each step with the source skill; interleave
    skills so prerequisites land before applications (typically: mechanics
    from the internals book first, tradecraft from the ops book after).
  - Avoid trivia. Aim at the load-bearing concepts a practitioner must own.

Output a JSON array on a single line (one object per step) and nothing else.
The `chapter` field must use the **book-native** filename
(`chapters/<book_number>-…md`, e.g. `chapters/ch07-taxes-are-costs-too.md`,
`chapters/intro-day-zero.md`, `chapters/appendix-a-common-ports.md`).
Pull the filename verbatim from `chapters_manifest.json`'s `file` field
— never reconstruct it from the manifest `index`, which is extraction
order and drifts from the book's own chapter numbering.
[
  {"step":1,"concept":"…","skill":"<slug>","chapter":"chapters/<book_number>-…md","prereq_for":[2,3]},
  ...
]
```

Parse the JSON. If parse fails or fewer than 3 steps come back, retry once
with a stricter prompt; if it still fails, fall back to a hand-built
4-step skeleton (intro → primary mechanism → common attack/use → recap)
sourced from the matched skill's concept-map nodes.

---

## Step 4 — Confirm via `AskUserQuestion`

Present the outline to the user as a numbered list (concept + chapter
ref + source skill). Then ask **two** questions in one `AskUserQuestion`
call:

1. **How to start?**
   - Start at step 1 *(Recommended)*
   - Skip ahead — let me say which step
   - Quit, this isn't right

2. **Depth + quizzes**
   - Beginner + quizzes on *(Recommended for new topics)*
   - Intermediate + quizzes on
   - Expert + quizzes on
   - Tour only — no quizzes
   - Beginner + quizzes on, but use **`preview`** for code/snippet
     comparisons whenever it helps

Record the answers as `$START_STEP`, `$DEPTH`, `$QUIZZES`.

---

## Step 5 — Materialise the curriculum as a task list

For each step in the curriculum, call `TaskCreate`:

- `subject`: the concept (≤ 60 chars)
- `description`: `<skill> / <chapter ref>`
- `activeForm`: `Teaching <concept>`

Then write the initial walk memory file (Step 7 schema). Set `Status:
in_progress`, `Current step: $START_STEP`.

---

## Step 6 — Step loop

For each step `i` from `$START_STEP` to the last:

### 6a. Mark the task in_progress

`TaskUpdate(taskId=<i>, status="in_progress")`.

### 6b. Teach (one focused subagent)

Spawn one `Agent` per step (or N parallel agents if a multi-skill step
needs both perspectives). Prompt template:

```
You are a teacher for ONE step of a guided walk.

Read ONLY: <skill-dir>/SKILL.md (for orientation) and
           <skill-dir>/<chapter-ref> (the teaching source).

Teach this ONE concept: <step.concept>
Target audience depth: <DEPTH>     (beginner | intermediate | expert)

Format:
  - 250-400 words. Practitioner voice. Preserve exact terminology.
  - Open with the one-sentence "what is this and why does it matter".
  - Include exactly ONE concrete worked example (a command, an SDDL
    string, a protocol message, a code snippet — whatever fits).
  - End with a one-line "this connects to: …" pointing forward to the
    next concept (<next.concept>) if there is one.

Do NOT quiz the user; the orchestrator will.
Do NOT recap the whole book.
```

Present the subagent's teaching to the user verbatim (or near-verbatim —
you may add a short header like `### Step 3/8 — Access check pipeline`).

### 6c. Quiz (if `$QUIZZES == on`)

Generate the quiz **yourself** (the orchestrator), based on the teaching
just delivered. Use `ultrathink` for harder steps to produce sharp
distractors.

Quiz design rules:

- 3 or 4 options. **Exactly one correct.**
- Distractors are *plausible misconceptions* — the kind a learner would
  pick because they almost-understand. Never use nonsense distractors.
- Quiz the *concept* just taught, not trivia (file names, page numbers).
- Use the `preview` field of `AskUserQuestion` when comparing code, SDDL,
  protocol messages, or any snippets — the user gets a side-by-side view
  and can really *see* the difference.
- Avoid leading wording ("Which is the correct way to…" → "Which of these
  will succeed?").

Call `AskUserQuestion` with a single question. After the answer:

- **Right** — 2-3 sentences of *why* (cite chapter). Then ask:
  - Next step *(Recommended)*
  - Go deeper here (re-teach with more depth or pull in a sibling chapter)
  - Pause — save and quit; resume later
  - Quit without saving completion

- **Wrong** — name what the chosen distractor assumes; explain why the
  correct answer is different; then ask:
  - One more quiz on this concept (sibling question)
  - Continue to next step anyway
  - Pause / quit

### 6d. Record + advance

Append to the walk memory file (Step 7):

```
N. ✅ <concept> (<skill>/<chapter>) — quiz: correct
```

or

```
N. ⚠  <concept> (<skill>/<chapter>) — quiz: wrong → recovered | not recovered
```

(or `✅ tour` if `$QUIZZES == off`). Update `Last updated:`,
`Current step: i+1` in the frontmatter section.

`TaskUpdate(taskId=<i>, status="completed")`.

### 6d.5 Emit step snapshot HTML

After every teach+quiz cycle, render the current step as an HTML
artifact using the **layout-3 (walk-session) template** from
`design-system/layouts.md`. Path: `artifacts/walks/<topic-slug>-step-<N>.html`.
This file is **overwritten on every step** — only the latest step
snapshot survives until the recap (Step 8) is generated. Include the
progress strip (with done / current / future markers), the teaching
paragraphs, the quiz card, and the meta footer. End the chat turn
with the artifact path so the user can open the rich version.

### 6e. On pause / quit

Update memory frontmatter: `Status: in_progress` (pause) or `abandoned`
(quit-without-completion). Tell the user how to resume:
`/the-knowledge-guy resume`.

---

## Step 7 — Memory schema

File: `$MEM_DIR/walk-<slug>.md` where `<slug>` is `<topic-kebab-case>`
truncated to ~40 chars. If a file with that slug exists and is completed,
append `-2`, `-3`, etc.

```markdown
---
name: walk-<slug>
description: Active /the-knowledge-guy walk on "<topic>". Step N/M.
metadata:
  type: project
---

# Walk: <topic>

- Skills: <skill-a>, <skill-b>
- Depth: <beginner|intermediate|expert>
- Quizzes: <on|off>
- Started: <YYYY-MM-DD>
- Last updated: <YYYY-MM-DD>
- Current step: <N>
- Status: <in_progress|completed|abandoned>

## Curriculum
1. ✅ <concept> (<skill>/<chapter>) — quiz: correct
2. ⚠  <concept> (<skill>/<chapter>) — quiz: wrong → recovered
3. ▶  <concept> (<skill>/<chapter>) — current
4. ⏳ <concept> (<skill>/<chapter>)
...

## Notes
- <off-script questions the user asked, fumbles worth revisiting,
   "go deeper" detours taken>
```

Also append (or update) one line in `$MEM_DIR/MEMORY.md`:

```
- [Walk: <topic>](walk-<slug>.md) — step N/M, last touched <date>
```

If `MEMORY.md` doesn't exist, create it with no frontmatter (it is an
index, not a memory — see CLAUDE.md auto-memory conventions).

Use a single `Bash` `date +%Y-%m-%d` to get the date; never invent dates.

## Course memory (shared with `course` / `check`)

`course` mode and its `check` sub-mode (see `SKILL.md`) reuse this exact
grammar in a sibling file, `$MEM_DIR/course-<skill-slug>.md`. A **course
is a kind of walk** — same frontmatter and the same `✅ / ⚠ / ▶ / ⏳`
markers — so a future reader (chat or human) parses both identically.

This markdown is the **durable source of truth** for course progress; the
browser's `localStorage` (key `kg-lab-progress-v1`) is only a live cache.
They sync at two one-directional points (no merge conflicts): (1)
**browser → markdown** when the user pastes a `check …` command (the
"Check with Claude" button) and `check` records the result; (2) **markdown
→ browser** the next time `course` re-renders a page (it can seed the
current state into the page). Auto-checked quiz/lab progress that never
goes through a `check` round-trip lives only in the browser — that is the
known, deliberate limit of a backend-free design.

```markdown
---
name: course-<skill-slug>
description: Interactive course for "<book>". <N> chapters, <M> exercises.
metadata:
  type: project
---

# Course: <book title>

- Skill: <skill-slug>
- Chapters: <N>   - Exercises: <M>
- Started: <YYYY-MM-DD>
- Last updated: <YYYY-MM-DD>
- Status: <in_progress|completed>

## Chapters
1. ⏳ ch01 — <title>  (artifacts/courses/<slug>/ch01.html)
2. ▶  ch07 — <title>  (artifacts/courses/<slug>/ch07.html)

## Practice
- ch07-q1 ✅ graded: pass        # open tasks: set by `check`
- ch07-open1 ⚠ graded: revisit   # the one thing to fix lands in ## Notes
...

## Notes
- <fumbles, the single fix `check` surfaced, "go deeper" detours>
```

The `MEMORY.md` index line mirrors the walk form:
`- [Course: <book>](course-<slug>.md) — <M> exercises, last touched <date>`.

If a skill is re-backfilled and its `book_number` labels shift, the
`course-<slug>.md` references and the `practice/<book_number>-*.json`
filenames drift — run `book-to-skill/scripts/upgrade_course_memory.py`
(sibling of `upgrade_walk_memory.py`) to repair them.

---

## Step 8 — Recap + follow-on (after the last step)

Set memory frontmatter `Status: completed` and update the `MEMORY.md`
line to `<concept-count>/<concept-count>, completed <date>`.

Then produce a one-screen recap:

```
## Walk complete: <topic>

✅ Concepts mastered (N):
- <concept> — <one-line why this matters>
- ...

⚠  Concepts to revisit:
- <concept> — <what the fumble suggested> (re-read <chapter ref>)

🎯 Suggested follow-on walks
- /the-knowledge-guy walk <related-topic-1>   (from <skill>)
- /the-knowledge-guy walk <related-topic-2>   (from <skill>)
- /the-knowledge-guy walk <cross-domain-topic>   (multi-skill)
```

Pick follow-on topics by scanning the **topic indexes** of all installed
skills for nearby concepts. Prefer one *deeper* (next chapter in the same
skill), one *adjacent* (sibling concept), and one *cross-domain* (a topic
in another skill that connects).

### Step 8.5 — Emit the recap HTML artifact

Render the recap as HTML using the **layout-4 (walk-recap) template**
from `design-system/layouts.md`. Path:
`artifacts/walks/<topic-slug>-recap.html`. This file is the **durable
record** of the completed walk — keep it permanently; do not
overwrite. Include the stats strip (cleared / revisit / chapters /
quiz accuracy), the "What you own now" list (one `<li>` per mastered
concept), the "Worth a second look" callout(s) for any fumbles, a
pull-quote if you have a memorable line from the walk, and the
"Where to go next" pills with the same follow-on suggestions above.
Optionally delete the in-progress step snapshots
(`artifacts/walks/<topic-slug>-step-*.html`) — the recap supersedes
them. End the chat response with the recap artifact path.

---

## Quality rules

1. **Forced choice, not free text.** Quizzes always use `AskUserQuestion`
   with 3-4 options. Never ask "what do you think?" — that defeats active
   recall.
2. **Distractors are misconceptions.** A wrong answer must teach
   something. If your distractors are all obviously dumb, the quiz is too
   easy.
3. **Use `preview` for snippets.** When comparing SDDL strings, protocol
   messages, code, or commands, set the `preview` field on each option so
   the user sees them side-by-side. This is the single most useful UX
   feature for technical quizzes.
4. **Save after every step.** Memory writes are cheap; a crash-resilient
   walk is the whole point. Never batch saves to the end.
5. **One concept per step.** If a step's subagent dumps three concepts on
   the user, the curriculum was wrong — fix it on the fly by inserting a
   step rather than letting the user drown.
6. **Cite chapters always.** Every teaching block and every "right
   because…" rationale points at a chapter file. The user must be able to
   trace anything back to the source.
7. **Drop-in extensibility.** Walks discover skills the same way as ask
   mode — never hardcode names. A new book added via `/book-to-skill`
   should be walkable immediately.
8. **`book-to-skill` is not walkable.** It's a generator, not a knowledge
   domain. Same exclusion as ask mode.

---

## Capabilities used (from Claude-Code-Capabilities-Reference)

- **`AskUserQuestion`** — quizzes + branch points. `preview` field is
  the killer feature for technical content.
- **Auto-memory** (`~/.claude/projects/<project>/memory/`) — resume across
  sessions; `MEMORY.md` auto-loads at session start so the user sees their
  open walks.
- **Parallel `Agent` subagents** — multi-skill teaching steps run in
  parallel; same fan-out as ask mode.
- **`TaskCreate` / `TaskUpdate`** — curriculum as a live task list.
- **Progressive disclosure** — this file is loaded only when walk mode
  fires; `SKILL.md` stays small.
- **`Read` with `limit:`** — frontmatter-only reads for routing keep the
  router context tight.
- **`ultrathink`** in the quiz-generation phase for hard steps.
