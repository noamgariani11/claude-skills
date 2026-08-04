# Output Quality — judging what the app actually made

The other half of the verdict. A beautiful app that emits unusable content is a failed product,
and only this axis catches it.

**Rule zero: no corpus, no run.** If Phase 2A produced no artifacts, the run has no output axis
and is incomplete. Go back and hand-drive the Composer until you have at least one variant per
platform under test.

---

## Capturing the corpus

Persona A captures, **verbatim**, for each generated artifact:

```
ARTIFACT <id>
platform:   reddit
source:     /content/new -> tailor  (or: /studio, /ads/[id])
brand_state: edge=7, POV="ci is a tax on shipping", voice=direct
ai_layer:   deterministic-fallback | live-anthropic
--- content ---
<the exact text, unmodified, including any `Title:` line>
--- end ---
```

Never paraphrase an artifact. A paraphrase cannot be judged — half of what's wrong with generated
marketing copy lives in the exact words.

---

## Judging fallback output (read this before you score anything)

With `ANTHROPIC_API_KEY` unset, Sheevook emits **deterministic, rule-based** output. This is
by design (CLAUDE.md: "Every AI call has a fallback... the app works with NO API key").

- **Judging fallback output as "AI slop" is an invalid finding.** It isn't AI output at all.
- Judge it as what it is: *a template*. The right questions are "is the template well-built?",
  "does it respect the platform rules?", "does it leave the right holes for the human?"
- A prior run found the rule-based tailoring genuinely good. **That is a finding worth reporting,
  not a caveat to bury.**
- **Score the two modes separately.** Never compare a fallback run's Output score against a
  live-AI run's baseline — record `ai_layer` in `baseline.json` and only compare like with like.

---

## The ruling

Every artifact gets exactly one:

| Ruling | Bar |
|---|---|
| **POST IT** | I would publish this under my own account, unedited, today. |
| **REWRITE** | Salvageable. Name the specific defect and the specific fix. |
| **WOULD BE REMOVED** | Deleted by a mod, downvoted to zero, flagged, or gets the account actioned. |

`WOULD BE REMOVED` is `critical` on Reddit and Hacker News — the damage (a banned account, a
domain-level ban) is **unrecoverable**, and the app can genuinely post to both.

---

## The rubric

Score each artifact 1–5 on each dimension. **Output Quality /10 = (mean × 2), rounded** — subject
to the veracity cap in dimension 6, which is applied **after** the mean and can override it.

### 1. Hook (weight: this is most of the score on X/TikTok/LinkedIn)
Does the first line/frame earn the second?
- **5** — could be screenshotted alone and still land.
- **3** — states the topic. Doesn't compel.
- **1** — preamble. "In today's world…", "I wanted to share…", "Excited to announce…"

### 2. Point of view
Does it say something a competitor could not say, and would some reasonable person disagree?
- **5** — a real, falsifiable stance.
- **3** — true but universally agreeable. (This is the boring zone. Most output lands here.)
- **1** — a definition with a logo on it.

Cross-check the app's own `lib/voice` boringScore. **If the app scores its own beige output as
fine, that's a defect in the detector** — report it separately from the artifact's own score.

### 3. Platform nativeness
Would a regular on this platform recognize this as one of theirs?
- **5** — indistinguishable from a good organic post.
- **3** — clearly cross-posted from somewhere else.
- **1** — violates a platform rule (link in an IG caption, hashtags in an X ad, self-promo on
  Reddit, editorialized HN title).

### 4. Specificity
- **5** — concrete nouns, real numbers, a named situation.
- **1** — "solutions", "seamless", "leverage", "empower", "game-changing", "revolutionize".

### 5. Would it spread? (STEPPS — apply loosely, don't ritualize)
Social currency · Triggers · Emotion · Public · Practical value · Story. A post needs **one**
of these badly, not all six weakly. Score 5 if one is strong; 1 if none are present.

### 6. Veracity — is every claim in it TRUE? (a cap, not an average)

**Added after run #14, where persona B scored a fabricated first-person anecdote 4.2/5 "because
the rubric had no box for the lie."** A fabrication scores *well* on the first five dimensions by
construction — an invented story is specific, has a point of view, and is native. Without this
axis the rubric actively rewards lying. Meanwhile the app's own live AI adversarial reader read
that same post, raised a `critical` about **register**, and never noticed the opening claim was
invented. Both the app and this skill were blind in the same place.

Check every one of these against the master content, `brand.facts`, and `brand.valueProps`
(all three reach the model via `brandContext()`, so a number absent from the master but present in
brand facts **is grounded** — see the verified-false-positive in `harness.md`):

| Claim type | The test |
|---|---|
| **Statistic** (`40%`, `3x`, `72h`) | Does that *same figure* appear in a source? Not a digit collision — "20%" is **not** grounded by "20+ agents". |
| **First-person anecdote** ("we spent a week…", "I migrated…") | Did this happen? `sourceTellsFirstHandStory()` false means the model was told it may **not** tell one. |
| **Third-party social proof** ("teams tell us…", a quoted customer) | A synthetic customer is never permitted — CLAUDE.md forbids generating a fake testimonial, review, or face **at all**. |
| **URL** | Does the origin+path exist in the master or brand links? An invented deep link is a fabrication even when the domain is real. |
| **Competitor claim** | Named rival, their pricing, their limitations — discovery may not invent any of these. |

- **5** — every claim traceable to a source. Non-factual copy (pure POV, no claims) also scores 5;
  having nothing to verify is not a defect.
- **3** — a claim that is *probably* true but that you could not trace. Note it; do not cap.
- **1** — **anything fabricated.**

> **The cap, and it is absolute: veracity 1 ⇒ the artifact cannot be rated above REWRITE, cannot
> score above 4/10 no matter what the other five dimensions say, and the finding is at minimum
> `high`.** On Reddit or Hacker News a fabrication is **WOULD BE REMOVED** and `critical` — a
> fabricated claim in a community that fact-checks is how an account and a domain get banned.

**Report the app's own detection separately from the artifact's score.** If the app rendered
`issues: []` or a green verdict on a post containing a fabrication, that is a **second, distinct,
higher-severity finding** than the artifact itself: the artifact is one bad post, the blind
detector will pass every future one. Name both.

---

## The AI-slop detector (automatic REWRITE, no debate)

Any of these present → cannot score above 3 on PoV, and the artifact is at best REWRITE:

- Opening with "In today's fast-paced/ever-evolving/digital world"
- "I'm excited/thrilled/humbled to announce"
- Emoji-stuffed headings, or a 🚀 anywhere near the word "launch"
- The rule-of-three cadence everywhere ("faster, simpler, smarter")
- "Let me know your thoughts in the comments!" / "What do you think? 👇"
- Hedged both-sides takes with no actual position
- Em-dash-heavy AI cadence (this repo went **em-dash-free** deliberately — an em-dash in generated
  output is itself a finding: `lib/` should not be emitting them)
- "It's not just X, it's Y"
- Any sentence that would be equally true for any company in the category

These map 1:1 to CLAUDE.md's "no AI slop" rule and to `lib/voice`'s purpose. **The app has
machinery to catch these** (`boringScore`, the rewrite gate, the stress-test panel). Persona B's
job includes testing whether that machinery actually fires — **feed it deliberate slop and see.**
Slop that sails through the app's own detector is a `high` finding.

---

## Judging an ad (Persona C + the platform experts)

An ad is judged on **structure**, not just copy. A campaign with great copy and no coherent
structure is unbuyable.

1. **Objective → campaign type coherence.** Does the picked campaign type actually serve the
   picked objective? (Awareness objective → Search campaign = incoherent.)
2. **Creative ↔ format fit.** Does the creative meet the real spec for that format — aspect ratio,
   duration, headline/primary-text character limits (ad limits are **stricter** than organic)?
3. **Is it buyable?** Budget in integer cents, a target, a measurable outcome. If a media buyer
   couldn't take this into the ads manager and build it, it's not a campaign, it's a mood board.
4. **Measurement.** How would you know it worked? If the tool has no answer, say so.
5. **Copy.** Same rubric as above, plus: ads get ~3 seconds, not 30.

---

## The tailoring-is-fake test (run this every single time)

Diff the generated variants for the same source content across platforms.

> **If the variants differ only in length and hashtag count, the tailoring is cosmetic** — and the
> personalization engine, which is the entire premise of the product, is not doing its job.

Look specifically for: does the X variant have a different *structure* than the LinkedIn one? Does
the Reddit one drop the marketing voice entirely? Is the Threads variant just the X variant?
(That last one is the most common failure — see the Threads card.)

This is the highest-value finding this skill can produce. Check for it in every run, and state the
result explicitly in the report **even when the answer is "no, tailoring is real"** — a confirmed
negative is worth recording.
