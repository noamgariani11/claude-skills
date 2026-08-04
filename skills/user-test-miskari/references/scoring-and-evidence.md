<!-- VENDORED into /user-test-miskari on 2026-07-11 from /user-test. This skill OWNS this copy: edit it here. Do NOT re-point the skill at /user-test's version - an unrelated edit there silently changed this skill's score calibration mid-trend. -->

# Scoring & Evidence Rules

Scores are harsh. Evidence is mandatory. These rules exist because AI generates plausible-sounding confidence that isn't earned.

---

## Scoring Calibration

| Score | What it means | How common |
|-------|--------------|------------|
| 9-10  | Exceptional. Would pay for it today. Zero friction on core flow.      | Almost never |
| 7-8   | Good. Accomplished the goal. Friction was minor. Would come back.     | Top 20% of apps |
| 5-6   | Mediocre. Got partway. Some things worked, some didn't.               | Most apps land here |
| 3-4   | Poor. Confused often. Gave up or nearly gave up. Multiple blockers.   | Common for early-stage |
| 1-2   | Broken. Couldn't do the basic thing. Left immediately.                | Rare but possible |

**Default assumption:** start at 5 and adjust. A 5 is not an insult, it is where most apps start. Do not inflate scores to be kind. A score that does not match the narrative is useless.

---

## Score Gating (enforced)

To earn **≥7**, both conditions must hold:

1. **Task completion:** Full (not Partial, not Failed)
2. **Evidence-backed positive moment:** at least one [OBSERVED] finding that is unambiguously good (no friction, no hesitation). Must include a screenshot filename or console/network evidence.

If either is missing, **cap the score at 6**, no matter how nice the experience felt. Log the cap decision:

```
SCORE CAP: T[N] capped at 6 — task completion: Partial, no evidence-backed positive moment.
```

To earn **≥9**, add: zero high/critical bugs encountered, zero friction points logged for this tester.

---

## Confidence Tagging (every finding)

Tag every bug, friction point, and observation with one of:

- **[OBSERVED]** — screenshot evidence, console output, or measurable fact. Indisputable.
- **[INFERRED]** — behavioral pattern visible in the interaction sequence. Strong but interpretive.
- **[SIMULATED]** — emotional reaction, trust judgment, "would they leave?" Educated guess from persona modeling.

**Proof requirement for [OBSERVED]:** every [OBSERVED] finding must cite at least one of: a screenshot filename, a console error line, a network request/response, a DOM snapshot, or a timing measurement. If you cannot cite evidence, the finding is not [OBSERVED] — downgrade to [INFERRED] or [SIMULATED] automatically.

Format examples:
```
[OBSERVED] BUG [high]: Button returns 404 | Console: "GET /api/foo 404" | Screenshot: t1-05.png
[INFERRED] FRICTION [medium]: User hesitated before clicking | 3 snapshots show same page unchanged
[SIMULATED] FRICTION [low]: "I don't trust this page" | Based on persona's skeptical mood
```

In consolidated tables, add a `Confidence` column.

---

## False-Positive Guardrails

AI-driven testing pattern-matches on "things changed" and confidently calls them bugs. The guardrails below are non-optional. Apply them BEFORE flagging a finding as `[OBSERVED] BUG [high|critical]`.

### Rule 1 — Numeric drift below threshold is noise, not a bug

If the only evidence is a number that changed, demand a meaningful delta:

| Metric | Threshold below which it's noise |
|---|---|
| Score / counter / rating displayed to user | ±1 (single point) |
| Layout shift in pixels | ±4px |
| Network/render timing | ±100ms |
| Token count, character count | ±1 |
| Ordering of items in a list of equal-priority items | any reordering with no other signal |

A "score went 51 → 50 after I added a task" finding fails this rule unless you can ALSO show: (a) it reproduces on a second add, AND (b) you traced the delta to a specific line of math (not Math.round(), not floating-point). The 2026-04-26 run's F7 score-disincentive was a Math.round() artifact and should never have been flagged HIGH.

### Rule 2 — Prediction is not observation

If you wrote "the user would feel..." or "this would surprise them" without observing it (no FRICTION timing, no friction text, no abandonment), the finding is `[SIMULATED]` at most. Do not promote a simulation to `[OBSERVED]` because it sounds plausible.

### Rule 3 — Reproduce before flagging anything HIGH

Anything tagged `[high]` or `[critical]` must reproduce on a second attempt within the same session. If a behavior happens once and you can't get it to happen again, downgrade to `[medium]` and tag `[INTERMITTENT]` in the description. The 2026-04-26 hydration mismatch was correctly flagged HIGH because it was confirmed reproducible only on the `/profile→/settings` redirect path (not on direct `/settings` load) — the path-conditional repro IS the evidence.

### Rule 4 — Source-or-suppress for code-level claims

If a finding makes a code-level claim ("the input is unsanitized," "this isn't wrapped in `<form>`," "the unique index conflicts"), you must either:

- (a) cite the file:line that demonstrates the bug, OR
- (b) demote the claim to `[SIMULATED]` and label it "needs code review."

Live-tester findings without code-level claims are exempt — a Skimmer can say "I can't find the button" without grepping. But the moment you write "the API doesn't sanitize," the source has to back it up.

### Rule 5 — Match observation against the prior `learnings.md` suppression list

Phase 0.7 loads `docs/reports/user-test-reports/learnings.md`. If the current finding matches a prior `verified-false-positive` entry (fuzzy title match), suppress it OR explicitly re-prove it. Suppress format in the report:

```
[SUPPRESSED — verified-false-positive in run YYYY-MM-DD]: [original finding]
Why suppressed: [the prior reason]
Re-proof attempted: [yes/no, what changed]
```

Do not re-flag a suppressed finding without a re-proof step. Do not silently drop it either — list it in a "Suppressed by prior learnings" footnote so the user can audit.

---

## Cognitive Load Simulation (personas forget)

AI remembers everything. Real users don't.

- After 3+ pages, a persona may only reference what a real person would retain: the main headline, the CTA they clicked, maybe one number or key phrase.
- If critical info appeared only once and early (page 1-2), test whether the persona "remembers" it on page 5+. If they wouldn't, that is an information-architecture finding, not a memory success.
- Skimmer forgets fastest. Careful Reader retains more. Mobile Tapper retains visuals better than text.
- When a persona "decides" based on something seen earlier, verify a real person would still have that info. If not, flag.

---

## Task Completion Tracking

Every persona's GOAL must be phrased as a concrete, completable task with binary success:

```
TASK: "Find out how much it would cost to fix a leaky faucet"
SUCCESS CRITERIA: Reached a page or response showing a dollar estimate
```

Not "explore the repair features" — unmeasurable. Track:
- **Steps taken** (count every navigation + interaction)
- **Wrong turns** (pages that didn't advance the goal)
- **Goal completion:** Full / Partial / Failed
- **Failure point:** the exact step where they gave up, if applicable

Task completion rate across all live personas is the single most important metric:
```
TASK COMPLETION: 2/3 (67%) — T1: Full, T2: Partial (stuck on billing), T3: Full
```

## Provenance is checked PER SURFACE, not once per number

A persona asked for "the source and as-of date" of a material number treats the requirement as
discharged the moment ANY surface supplies it, then reads every other surface for the VALUE only.
That is how a provenance regression on a single surface survives a confident-looking check.

Measured, 2026-08-03: the notice date was stripped from `/tax/assessments`. Marcus visited the
route, and even filed a Low bug about a missing notice date on one row - but he had already taken
the provenance from `/tax/opportunities`, a sibling surface where the label was intact, so he
tagged the material 2025 value **[ACCURATE]** rather than **[UNLABELED]**. The plant was missed.

It is the same shape as the 2026-07-17 miss (three agreeing deadline surfaces treated as proof, the
fourth never re-checked): **a check satisfied on one surface is not re-run on the rest.**

So state it as a per-surface obligation:

> For EVERY surface that renders this figure, say whether THAT surface names its source and its
> as-of date. "I got the provenance from another screen" is not a pass for the screen in front of
> you - a reader who lands here sees only this one.

And prefer the mechanical route where it exists: label PRESENCE is a consistency property, so a
`crossSurfaceChecks` entry asserting the provenance label appears wherever the value does catches
this class for free, on every run, without spending an agent.
