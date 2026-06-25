---
name: user-test-2
description: |
  Emotional journey mapping — five distinct characters (not archetypes) navigate the app
  and report how it made them feel at every step. Captures micro-moments: the exact word,
  button, or screen that shifted their emotional state. A Copy & Tone Critic reads all
  visible text. A 60-second Cold Reader forms a gut impression with zero context. Output
  is a narrative emotional map and first-person persona stories, not a bug table or score.
  No baseline tracking. No adversarial pass. No 1–10 score. Use when you want to know
  how real people feel going through the app, not just what breaks.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# /user-test-2 — Emotional Journey Mapping

Different strategy than `/user-test`. This skill answers: **"How does this app make people feel?"** — not "what is broken?" We care about trust arcs, micro-moments, emotional drop-offs, and the gut reaction a new visitor has before they understand the product.

---

## Core Philosophy

- **Feeling over finding.** We log emotions first, bugs second. A persona might successfully complete a task but feel anxious the whole time — that matters.
- **Characters, not archetypes.** Each persona has a backstory, a current emotional state, a specific hope, and a specific fear. They are people, not test profiles.
- **Micro-moments.** We capture the exact phrase, button label, animation, or screen that changed the persona's emotional state. These are the leverage points.
- **Narrative first.** The report reads like a story. Tables are summaries, not the main content.
- **No score 1–10.** Replaced with: emotional arc + "would come back?" verdict + trust rating.
- **No baseline.** Every run is standalone. Each run captures the current emotional truth.

---

## Phase 0: Setup

### 0.1 — Detect URL

Accept any of these, in priority order:
1. A URL the user passed in the trigger
2. A local dev server (check ports 3000, 3001, 4000, 5173, 8080):
   ```bash
   for port in 3000 3001 4000 5173 8080; do
     code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port" 2>/dev/null)
     [ "$code" != "000" ] && echo "FOUND: http://localhost:$port" && break
   done
   ```
3. A Vercel preview if CLI is installed

If nothing resolves, tell the user and stop.

### 0.2 — Auth wall check

```bash
curl -sI -L "$URL" 2>/dev/null | grep -Ei "^location:" | tail -1
curl -s "$URL" 2>/dev/null | grep -Ei "sign[ -]?in|log[ -]?in|please authenticate" | head -3
```

If there's an auth wall, ask the user for test credentials. If they decline, we test the login/landing surface only and note what couldn't be reached.

### 0.3 — App value proposition read

Before designing personas, read the landing page and answer these questions internally:
- What does this app claim to do in one sentence?
- Who is the obvious target user?
- What emotion does the landing page try to create? (confidence? relief? excitement?)
- What is the primary call to action?

These answers shape persona design. Don't ask the user — derive them from the app itself.

### 0.4 — Route discovery

```bash
find src/app -name "page.tsx" -o -name "page.jsx" 2>/dev/null | sort
find pages src/pages -name "*.tsx" -o -name "*.jsx" 2>/dev/null | grep -v "^_" | sort
```

This gives us the full surface map. Personas will not cover all routes — they follow natural flows.

### 0.5 — Setup output directory

```bash
mkdir -p .gstack/user-test-2-reports
_DATE=$(date +%Y%m%d-%H%M%S)
_REPORT_FILE=".gstack/user-test-2-reports/journey-${_DATE}.md"
```

---

## Phase 1: The 60-Second Cold Reader

Before designing the main personas, run a single "cold read" — a person with zero context who has 60 seconds to form a gut impression.

**Who they are:** Someone who clicked a link in an email or saw a social post and landed here. They have no idea what this is. They are mildly curious but have no urgency.

**What they do:**
1. Navigate to the landing page. Take a screenshot.
2. Read ONLY what's visible above the fold (no scrolling yet).
3. Answer these questions from their perspective, in first person:
   - "In 5 words, what does this do?"
   - "Do I trust this enough to scroll down?"
   - "What's the one thing that could make me leave right now?"
   - "What's the one thing making me want to stay?"
4. Scroll down once. Screenshot.
5. Find the primary CTA. What does it promise? Does it feel safe to click?
6. Final verdict: **Stay** / **Leave** / **Bookmark for later**

**Report format:**
```
## 60-Second Cold Read

**First words visible:** [exact headline text]
**Gut read:** [their 5-word answer to "what does this do"]
**Trust level on arrival:** [Skeptical / Neutral / Open]
**Stay or leave?** [verdict + one-sentence reason]

**Micro-moment (positive):** "[exact phrase or element]" → [how it made them feel]
**Micro-moment (negative):** "[exact phrase or element]" → [how it made them feel]

**Cold reader's first-person voice:**
> [2–4 sentences in their natural voice — what they actually thought]
```

---

## Phase 2: Persona Design

Design **4 personas**. They are **not archetypes** — they are specific people with emotional contexts.

### Design rules

Each persona must have ALL of these:

| Field | Description |
|---|---|
| Name + age | Specific person |
| Situation | What's happening in their life right now that brought them to this app |
| Emotional state on arrival | How are they feeling as they open this tab? (e.g., "stressed about a letter she received") |
| Hope | The specific thing they're hoping this app will help them with |
| Fear | The thing they're afraid of (being scammed, being confused, wasting time, being judged) |
| Patience level | How long before they give up and leave |
| Device | Desktop or mobile |
| Tech comfort | Low / Medium / High (not a technical score — more "how confident do they feel with digital things") |
| Trigger to leave | The specific thing that would make them close the tab instantly |
| Delight hope | The specific moment they're secretly hoping for |

### Diversity requirements

Across all 4 personas:
- At least 2 different age brackets (e.g., 30s and 50s)
- At least 2 different emotional states on arrival (e.g., one anxious, one casual)
- At least 1 low-patience and 1 high-patience persona
- At least 1 mobile user
- At least 2 different "primary goals" (what they're trying to accomplish)
- No two personas share the same Hope

### Do NOT use

- The words "Skimmer," "Careful Reader," or "Mobile Tapper"
- Archetype letters (A, B, C)
- Technical attributes like "uses `snapshot -i`"
- Generic descriptions like "tech-savvy user"

### Persona card format

```
## Persona: [Name], [age]

**Situation:** [2–3 sentences about their life right now]
**Device:** [desktop/mobile/tablet] | **Tech comfort:** [Low/Medium/High]
**Emotional state on arrival:** [one concrete phrase: "nervous and slightly overwhelmed"]
**Hope:** [specific outcome they want from this visit]
**Fear:** [specific thing they worry about]
**Patience:** [e.g., "leaves if nothing useful happens in 3 minutes"]
**Trigger to leave:** [specific thing]
**Delight hope:** [the moment they're secretly hoping for]
**Journey goal (binary):** [measurable task with pass/fail — same discipline as user-test but framed human-ly]
```

Print all 4 persona cards before Phase 3.

---

## Phase 3: Journey Sessions

Run each persona's session as an isolated **Agent** subagent. Each agent gets the persona card and the URL and navigates the app as that person.

### Agent instructions for each persona session

Each agent must:

1. **Set the viewport** appropriate to device (mobile: 375x812; desktop: 1280x800 or 1440x900)
2. **Navigate** to the app. Screenshot.
3. **Report the arrival moment** — what is the first thing they see? How does it hit them emotionally?
4. **Pursue the journey goal** — 5–10 interactions max
5. **At each step**, log:
   - What they did
   - What they saw
   - Their **emotional state** using ONE of these tags:
     - `[HOPEFUL]` — something is promising
     - `[CURIOUS]` — engaged but uncertain
     - `[CONFUSED]` — lost or unclear
     - `[FRUSTRATED]` — something is wrong or blocking
     - `[DISTRUSTFUL]` — something feels off or sketchy
     - `[RELIEVED]` — a fear was resolved
     - `[DELIGHTED]` — something exceeded expectations
     - `[ANXIOUS]` — worried about an outcome
     - `[BORED]` — disengaged, losing interest
     - `[LOST]` — genuinely can't find what they need
   - Any **micro-moment** — the exact phrase, label, animation, or element that triggered the emotion
6. **Write the journey in first person** — the persona's own voice, not a QA report
7. At the end:
   - **Would you come back?** Yes / Maybe / No — and why in their voice
   - **Would you recommend this to someone like you?** Yes / Maybe / No
   - **Trust rating:** "I trust this with my [time only / basic info / credit card / sensitive documents]"
   - **The moment things changed** — one sentence: "I started to trust/distrust when..."
   - **What would make it perfect for you** — one concrete ask, from their perspective

### Journey session output format

```
## [Name]'s Journey

**Goal:** [their binary task]
**Device:** [device] | **Emotional state on arrival:** [their state]

---

### Step 1: Arrival
*[Screenshot ref]*
[EMOTION TAG] — "[their voice, 1–2 sentences]"
**Micro-moment:** "[exact phrase/element]" → [why it hit them that way]

### Step 2: [what they did]
...

---

### [Name]'s verdict

**Journey outcome:** Completed / Partial / Gave up at [step N]
**Would come back?** [Yes/Maybe/No] — "[their reason in their voice]"
**Would recommend?** [Yes/Maybe/No]
**Trust level:** "I trust this with my [___]"
**The moment things changed:** "[one sentence]"
**One ask:** "[their specific want]"

**Emotional arc:** [Arrival → Step 2 → Step 5 → End — using emotion tags to show the arc]
Example: `[ANXIOUS] → [CURIOUS] → [CONFUSED] → [FRUSTRATED] → gave up`
```

---

## Phase 4: Copy & Tone Critic

A separate **Agent** subagent that reads the app as a copywriter/editor, not a user.

This agent:
1. Visits every page the 4 personas visited
2. Screenshots each page
3. Reads all visible text critically

**What it evaluates:**

### A. Clarity
- Is the headline immediately clear? (Test: can a 12-year-old understand it?)
- Are there jargon terms that need a glossary? List them.
- Are there sentences over 20 words that could be cut in half?

### B. Tone match
- What emotional tone does the copy attempt? (Confident? Reassuring? Urgent? Friendly?)
- Does the tone match the user's emotional state on arrival? (If users arrive anxious, does the copy calm them? Or does it make them more anxious?)
- Does the tone shift awkwardly between pages?

### C. CTAs
- Is every CTA specific about what happens next? ("Submit" = vague. "Get my free estimate" = specific.)
- Are there CTAs that create anxiety instead of confidence?
- Are there missing CTAs — moments where the user clearly wants to do something but can't?

### D. Trust signals
- Social proof: testimonials, user counts, ratings — present? Credible?
- Safety signals: privacy policy link visible? Pricing clear before commitment?
- Competence signals: does the copy sound like it was written by experts or marketing interns?

### E. Emotional resonance
- Is there a sentence or phrase that would genuinely move the target user?
- Is there copy that would make the target user roll their eyes?

**Output format:**
```
## Copy & Tone Audit

### Clarity grade: [A/B/C/D/F]
[2–3 sentences of evidence]

**Jargon list:** [terms that need explaining]
**Longest confusing sentence:** "[quote]" — suggested rewrite: "[rewrite]"

### Tone match grade: [A/B/C/D/F]
**Intended tone:** [what the copy is going for]
**Actual landing:** [what it actually feels like]
**Tone break:** [where the tone shifts unexpectedly]

### CTA audit
| Page | CTA text | Verdict | Suggested improvement |
|---|---|---|---|
...

### Trust signals
**Present:** [what's there]
**Missing:** [what's absent that would build trust]
**Trust-breaking:** [anything that actively erodes trust]

### Best line in the app
"[quote]" — [why it works]

### Worst line in the app
"[quote]" — [why it hurts, suggested replacement]
```

---

## Phase 5: Synthesis Report

Write the full report to `$_REPORT_FILE`.

### Report structure

```markdown
# Emotional Journey Report — [App Name / URL]
*[Date] | [N] personas + cold read + copy audit*

---

## How It Made People Feel: The Summary

[3–4 sentences written as a human summary, not a list. What was the dominant emotional experience? Who had a good time? Who didn't? What single change would most improve the emotional experience?]

---

## Emotional Journey Map

| Stage | [Persona 1] | [Persona 2] | [Persona 3] | [Persona 4] |
|---|---|---|---|---|
| Arrival | [tag] | [tag] | [tag] | [tag] |
| First interaction | | | | |
| Mid-journey | | | | |
| Goal attempt | | | | |
| Resolution | | | | |
| **Would come back?** | Yes/Maybe/No | | | |
| **Trust level** | | | | |

*Emotion tags: [HOPEFUL] [CURIOUS] [CONFUSED] [FRUSTRATED] [DISTRUSTFUL] [RELIEVED] [DELIGHTED] [ANXIOUS] [BORED] [LOST]*

---

## The Cold Reader's Verdict

[Paste the 60-second cold read summary here]

---

## Micro-Moments That Mattered

[The top 5–8 moments (positive or negative) where a specific element caused a clear emotional shift. Ordered by impact.]

### [1] [Element name or quote]
**Found by:** [persona(s)]
**Triggered:** [emotion tag]
**Why it matters:** [one sentence]

...

---

## The Trust Arc

[Narrative paragraph: At what point did users start trusting the app? Did trust build, stall, or break? Was there a moment that converted skeptics? Was there something that broke an established trust?]

**Trust timeline:**
- [PERSONA 1]: Trusted after [step N] when they saw [element]
- [PERSONA 2]: Never fully trusted — distrusted when [moment]
...

---

## Who This App Is For Right Now

Based on the 4 journeys:

**This app works for:** [description of who had a good journey — what made them succeed]
**This app struggles with:** [description of who had a bad journey — what made them fail]
**Biggest gap:** [the segment that clearly needs this but currently bounces]

---

## Copy & Tone Summary

[Paste key findings from Phase 4]

---

## The Personas' Voices

[For each persona, 2–3 sentence summary in their voice. What they'd say if telling a friend about the app.]

**[Name]:** "[first-person summary]"
...

---

## Top Opportunities

[Ordered by emotional impact, not technical severity]

### [1] [Opportunity title]
**Emotional trigger:** [which emotion, which moment]
**Who it affects:** [which personas]
**What to change:** [specific, concrete suggestion]
**Emotional outcome of the change:** [what would users feel instead]

...

---

## What's Working

[Honest positives — the moments that delighted, the copy that landed, the flows that felt good. Don't skip this because it's easy to skip.]

---

## Appendix: Full Persona Journeys

[Full narrative sessions from Phase 3 for each persona]
```

---

## Phase 6: Finish

1. Save the report to `$_REPORT_FILE`
2. Print the report path
3. Print a brief in-chat summary:
   ```
   ---
   Journey Report saved to: [path]

   Emotional snapshot:
   - Cold reader: [Stay/Leave/Bookmark] — [one-line reason]
   - [Persona 1]: [dominant emotion] → [verdict]
   - [Persona 2]: [dominant emotion] → [verdict]
   - [Persona 3]: [dominant emotion] → [verdict]
   - [Persona 4]: [dominant emotion] → [verdict]

   Most impactful micro-moment: "[quote/element]"
   Biggest trust gap: [one sentence]
   Top opportunity: [one sentence]
   ---
   ```
4. Ask the user if they'd like to implement the top opportunities now.

---

## Phase 7: Implementation (triggered by user saying yes)

If the user wants to act on the findings, run this phase. It converts the "Top Opportunities" from the report into surgical code changes.

### 7.1 — Enter plan mode

Call `EnterPlanMode` before touching any files.

### 7.2 — Explore the codebase

For each opportunity in the report, grep and read to find:
- The exact file(s) and line numbers involved
- Whether the thing already exists (don't re-implement what's there)
- Any reusable component or utility that applies

Run these explorations in parallel using the Explore agent type. Cover:
- The specific UI component or page that surfaced the emotional problem
- Any shared component (tooltip, banner, empty-state) that could be reused
- The nav or layout file for label/copy changes

### 7.3 — Write the plan

Write the plan to the plan file. For each opportunity:
- One sentence: what the emotional problem is
- The exact file + what changes (string replacement, new line, removed block)
- The expected emotional outcome

**Scoping rules — enforce these strictly:**
- No new pages. No new route files.
- No new shared abstractions unless 3+ call sites benefit.
- Prefer editing existing copy over adding new UI.
- A label rename is 1 line. A tooltip is 3 lines. A reframed heading is 2 lines. If a fix needs more than ~20 lines, question whether it's surgical.
- If an opportunity from the report would require a new data-fetching hook, a new DB query, or a new component file, flag it as out-of-scope for this phase and note it separately for the user.

List the files to touch as a table: file | finding | change size.

### 7.4 — Get approval

Call `ExitPlanMode` with a `allowedPrompts` entry for `pnpm typecheck`. Wait for user approval before writing any files.

### 7.5 — Implement

Make all edits. Where multiple files are independent, edit them in parallel (multiple `Edit` calls in one response).

Order of operations:
1. Shared utility files first (glossary, constants, types)
2. Component files
3. Page files
4. Config / layout files last

### 7.6 — Verify

```bash
pnpm typecheck 2>&1 | grep -E "error|TS[0-9]" | head -20
```

If errors: fix them before reporting done. Do not skip.

### 7.7 — Report

Print a compact summary:

```
Implemented [N] fixes across [M] files:

✓ [Finding 1 title] — [file changed]
✓ [Finding 2 title] — [file changed]
...

typecheck: clean
```

---

## Operating Principles

- **Write in the persona's voice, not a QA report voice.** "I couldn't find the button" not "Button was not discoverable."
- **Emotion tags are mandatory at every step.** No tag = no emotional data. The map is the output.
- **Micro-moments are the product.** A specific phrase or button that changed a feeling is more valuable than a general "confusing UI."
- **Copy critic is separate.** Don't let personas critique copy as QA findings — route copy observations to Phase 4.
- **No score inflation or deflation.** No scores at all. The emotional arc IS the score.
- **Honesty about what the personas can't test.** If auth is required and we have no credentials, say so — don't simulate it.
- **Positives are as important as negatives.** If something delighted, document it exactly the same way. The goal is the full emotional truth, not a complaint list.
- **Implementation is surgical.** The report finds feelings; Phase 7 fixes them with the minimum viable code change. Prefer 5 lines over 50. No speculative abstractions.
