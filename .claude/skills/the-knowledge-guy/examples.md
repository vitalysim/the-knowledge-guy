# Walk mode — worked transcripts

Two examples. Read these once to internalise the *shape* of a walk; the
mechanics are in [walk-mode.md](walk-mode.md). Do not copy the wording —
copy the structure.

---

## Example 1 — Single-skill walk: "walk me through Kerberos"

**Input:** `/the-knowledge-guy walk me through Kerberos`

**Router routes:** `forshaw-windows-security` only (Kerberos is squarely
in one skill).

**Curriculum proposed** (one subagent reads SKILL.md + manifest):

```json
[
 {"step":1,"concept":"Tickets and the KDC role","skill":"forshaw-windows-security","chapter":"chapters/ch14-kerberos.md","prereq_for":[2,3,4,5,6]},
 {"step":2,"concept":"AS-REQ / AS-REP and pre-auth","skill":"forshaw-windows-security","chapter":"chapters/ch14-kerberos.md","prereq_for":[3,4]},
 {"step":3,"concept":"TGS-REQ / TGS-REP and the service ticket","skill":"forshaw-windows-security","chapter":"chapters/ch14-kerberos.md","prereq_for":[4,5,6]},
 {"step":4,"concept":"The PAC — where group SIDs travel","skill":"forshaw-windows-security","chapter":"chapters/ch14-kerberos.md","prereq_for":[5,6]},
 {"step":5,"concept":"S4U2Self and S4U2Proxy (constrained delegation)","skill":"forshaw-windows-security","chapter":"chapters/ch14-kerberos.md","prereq_for":[6]},
 {"step":6,"concept":"Unconstrained delegation and the TGT-in-LSA attack","skill":"forshaw-windows-security","chapter":"chapters/ch14-kerberos.md","prereq_for":[]}
]
```

**Confirmation question** (single `AskUserQuestion` call, 2 questions):

- *How to start?* → Start at step 1 *(rec)* / Skip ahead / Quit
- *Depth + quizzes?* → Beginner + quizzes *(rec)* / Intermediate + quizzes
  / Expert + quizzes / Tour only

User picks: start at 1, intermediate + quizzes.

**`TaskCreate`** × 6 — curriculum visible as a checklist.

**Memory file written:** `walk-kerberos.md` with status `in_progress`,
step 1 marked `▶`.

### Step 1 plays out

`TaskUpdate(1, in_progress)`. Teaching subagent reads `ch14-kerberos.md`
and returns ~300 words explaining tickets and the KDC role.

Router prints:

> **Step 1/6 — Tickets and the KDC role**
>
> *(teaching block)*

Then quizzes (built by the orchestrator with `ultrathink`):

> **Quick check:** A Kerberos ticket has two parts — a *cleartext* part
> the service can inspect, and an *encrypted* part. What's encrypted with
> the **service account's** key (rather than the client's)?

`AskUserQuestion` options (with `preview` per option showing a stylised
ticket dump):

- The whole ticket, including `realm` and `sname`
- The `EncTicketPart` (session key + flags + auth-time + PAC)
  *(correct)*
- Only the PAC
- Just the `authenticator` the client sends with the AP-REQ

User picks the `EncTicketPart` answer.

> ✅ **Correct.** The cleartext part (`realm`, `sname`) lets the *client*
> route the ticket to the right service; the `EncTicketPart` is sealed
> with the service's long-term key, which is why a service can validate
> a ticket without contacting the KDC — and why kerberoasting works when
> that key is weak (`ch14`, AS-REP roasting section).

Then `AskUserQuestion`:

- Next step *(rec)*
- Go deeper here
- Pause
- Quit

User picks Next.

**Memory append:** `1. ✅ Tickets and the KDC role (forshaw/ch14) — quiz:
correct`. Frontmatter `Current step: 2`. `TaskUpdate(1, completed)`.

### Steps 2-5 follow the same shape.

### Step 6 (last)

After the quiz, instead of "next", the router emits the recap.

### End: recap

```
## Walk complete: Kerberos

✅ Concepts mastered (6):
- Tickets and the KDC role — the model that makes everything else click
- AS-REQ/REP and pre-auth — and why pre-auth-off enables AS-REP roasting
- TGS-REQ/REP — service tickets, where kerberoasting lives
- The PAC — group SIDs as Kerberos cargo
- S4U2Self / S4U2Proxy — the protocol behind constrained delegation
- Unconstrained delegation — why "TrustedForDelegation" is a red flag

🎯 Suggested follow-on walks
- /the-knowledge-guy walk Active Directory authorization      (forshaw)
- /the-knowledge-guy walk NTLM relay                          (forshaw)
- /the-knowledge-guy walk Kerberoasting end-to-end            (multi)
```

Memory frontmatter flipped to `Status: completed`. `MEMORY.md` updated.

---

## Example 2 — Cross-domain walk: "walk me through Kerberoasting end-to-end"

**Input:** `/the-knowledge-guy walk me through Kerberoasting end-to-end`

**Router routes:** `forshaw-windows-security` (protocol mechanics) **and**
`hack-like-a-legend` (operational tradecraft). One topic, two
perspectives that braid.

**Curriculum (interleaved):**

```json
[
 {"step":1,"concept":"Why kerberoasting works — service-ticket encryption with the service account key","skill":"forshaw-windows-security","chapter":"chapters/ch14-kerberos.md"},
 {"step":2,"concept":"Finding kerberoastable accounts — SPN enumeration","skill":"hack-like-a-legend","chapter":"chapters/<spn-chapter>.md"},
 {"step":3,"concept":"Requesting service tickets without alerting EDR","skill":"hack-like-a-legend","chapter":"chapters/<requesting-tickets>.md"},
 {"step":4,"concept":"Extracting the cipher and offline cracking with hashcat","skill":"hack-like-a-legend","chapter":"chapters/<hashcat>.md"},
 {"step":5,"concept":"AS-REP roasting as a sibling technique","skill":"forshaw-windows-security","chapter":"chapters/ch14-kerberos.md"},
 {"step":6,"concept":"Detection signals and how blue teams hunt this","skill":"hack-like-a-legend","chapter":"chapters/<detection>.md"}
]
```

(The hack-like-a-legend chapter file names depend on that skill's
extraction — the curriculum-builder subagent gets them from its
`chapters_manifest.json`.)

### Step 3 plays out — a step that needs both perspectives

For a step where the user benefits from both books at once, the router
fans out **two** teaching subagents in parallel:

- Forshaw consultant: "Explain what's happening on the wire when a service
  ticket is requested — TGS-REQ message structure, encryption type
  negotiation, what's logged where."
- Sparc Flow consultant: "Explain the *operational* side — how Rubeus /
  PowerView phrase the request, which encryption type to ask for
  (RC4 = crackable), how to avoid Event 4769 patterns that trigger AMSI/
  MDE."

The orchestrator braids the two reports into one teaching block headed:

> **Step 3/6 — Requesting service tickets without alerting EDR**
>
> **Protocol view (`forshaw-windows-security`):** *…200 words…*
>
> **Operational view (`hack-like-a-legend`):** *…200 words…*
>
> **The connection:** … one paragraph showing how the protocol
> constraints from forshaw shape the tradecraft choices in
> hack-like-a-legend.

Quiz can then test understanding of the *intersection* — e.g. *"Why does
asking for an RC4-HMAC service ticket help an attacker even on a
Windows-2019 domain that supports AES?"* with one correct answer
(`UseSessionKey = 0 + KRB5KDC permits weaker etypes on the principal
when msDS-SupportedEncryptionTypes is unset`) and three distractors that
each capture a real misconception.

### Recap

```
## Walk complete: Kerberoasting end-to-end

✅ You now own the full chain:
- The cryptographic *why* (forshaw ch14)
- The operational *how* (hack-like-a-legend)
- Detection signals and blue-team hunts

⚠  Worth revisiting:
- The PAC validation step — wrong on quiz 4; re-read ch14 "PAC signatures".

🎯 Suggested follow-on walks
- /the-knowledge-guy walk Active Directory ACL attacks       (forshaw)
- /the-knowledge-guy walk LSASS dumping and credential theft  (multi)
- /the-knowledge-guy walk Detection engineering for AD attacks (hack-like-a-legend)
```

---

## Example: ingest mid-walk

```
User: /the-knowledge-guy add ~/Downloads/Designing-Data-Intensive-Applications.pdf

the-knowledge-guy:
  Detected ingest mode (path: ~/Downloads/Designing-Data-Intensive-Applications.pdf).
  An in-progress walk is saved: "The Psychology of Money" (step 2/9).

  [AskUserQuestion]
    Pause the current walk and ingest this book now? (Recommended)
    Cancel — I'll resume the walk first.

User: pause

the-knowledge-guy:
  Pausing walk → updating Last updated on walk-psychology-of-money.md.
  Handing off to book-to-skill...
  [Skill(skill="book-to-skill", args="~/Downloads/Designing-Data-Intensive-Applications.pdf")]

  (book-to-skill runs in a fork — stages 0-5)

  ✅ Created skill: kleppmann-data-intensive-applications (12 chapters)

  Next:
  - /the-knowledge-guy resume         — continue the Psychology of Money walk
  - /the-knowledge-guy walk replication — start a walk on the new skill
```

This transcript shows the **ingest mode** dispatch from `SKILL.md`:
path extraction (Step I1), mid-walk confirmation (Step I3), Skill-tool
handoff (Step I4), and the post-ingest report with both follow-on
options (Step I5).

---

## What these examples illustrate

- **The shape of a curriculum**: 5-8 steps, prereqs first, each tied to
  one chapter.
- **The teach → quiz → record cycle** with `AskUserQuestion`'s `preview`
  field doing real work for technical comparisons.
- **Multi-skill braiding**: parallel subagents per step, one teaching
  block headed by both perspectives + the connection.
- **Memory** is updated after *every* step — never at the end.
- **Suggested follow-on walks** drawn from the topic indexes of all
  installed skills, so the user is naturally pulled across the library.
