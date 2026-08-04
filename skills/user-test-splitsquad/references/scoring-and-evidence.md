<!-- VENDORED into /user-test-splitsquad on 2026-07-21 from /user-test-sheevook (itself from /user-test). This skill OWNS this copy: edit it here. Do NOT re-point the skill at another skill's version — an unrelated edit there would silently change this skill's score calibration mid-trend. -->

# Scoring & Evidence Rules

**These rules govern the Product UX score.** The Money Integrity score has its own rubric in
`money-integrity.md` — do not apply this calibration table to a number.

Scores are harsh. Evidence is mandatory. These rules exist because AI generates plausible-sounding
confidence that isn't earned.

---

## Scoring Calibration

| Score | What it means | How common |
|-------|--------------|------------|
| 9-10  | Exceptional. Would use it with real friends today. Zero friction on core flow. | Almost never |
| 7-8   | Good. Accomplished the goal. Friction was minor. Would come back.              | Top 20% of apps |
| 5-6   | Mediocre. Got partway. Some things worked, some didn't.                        | Most apps land here |
| 3-4   | Poor. Confused often. Gave up or nearly gave up. Multiple blockers.            | Common for early-stage |
| 1-2   | Broken. Couldn't do the basic thing. Left immediately.                         | Rare but possible |

**Default assumption:** start at 5 and adjust. A 5 is not an insult, it is where most apps start.
Do not inflate scores to be kind. A score that does not match the narrative is useless.

---

## Score Gating (enforced)

To earn **≥7**, both conditions must hold:

1. **Task completion:** Full (not Partial, not Failed)
2. **Evidence-backed positive moment:** at least one [OBSERVED] finding that is unambiguously good
   (no friction, no hesitation). Must include a screenshot filename or console/network evidence.

If either is missing, **cap the score at 6**, no matter how nice the experience felt. Log the cap:

```
SCORE CAP: <persona> capped at 6 — task completion: Partial, no evidence-backed positive moment.
```

To earn **≥9**, add: zero high/critical bugs encountered, zero friction points logged.

**SplitSquad-specific cap:** a persona who encountered a **wrong number** during their session
cannot score above **4** on UX, whatever the interface felt like. The interface's job is to be
believed; a number they can't trust makes the rest of it decoration.

---

## Confidence Tagging (every finding)

- **[OBSERVED]** — screenshot evidence, console output, a hand derivation, or a measurable fact.
  Indisputable.
- **[INFERRED]** — behavioral pattern visible in the interaction sequence, or a code read without a
  runtime observation. Strong but interpretive.
- **[SIMULATED]** — emotional reaction, trust judgment, "would they leave?" Educated guess from
  persona modeling.

**Proof requirement for [OBSERVED]:** cite at least one of — a screenshot filename, a console error
line, a network request/response, a DOM snapshot, a timing measurement, or **a written-out
arithmetic derivation**. If you cannot cite evidence, downgrade to [INFERRED] or [SIMULATED].

**In localStorage mode, any finding about a DB-only route is [INFERRED] by default** — the code
path was read, not run. Tag it honestly.

```
[OBSERVED] BUG [critical]: ¥12,000 counted as $12,000 | derivation: no JPY rate; convertCurrency
  returns amount×1 | src/utils/currency.ts:40 | Screenshot: c-07-balance.png
[INFERRED] BUG [high]: subscription PATCH mass-assigns payerId | route read, not exercised (no DB)
[SIMULATED] FRICTION [low]: "I don't trust this total" | based on persona's ledger-keeping habit
```

---

## False-Positive Guardrails

Apply these BEFORE flagging anything as `[OBSERVED] BUG [high|critical]`.

### Rule 1 — Sub-threshold drift is noise, not a bug

| Metric | Threshold below which it's noise |
|---|---|
| **Money: a single non-accumulating cent from float division** | ±$0.01 on one expense |
| Layout shift in pixels | ±4px |
| Network/render timing | ±100ms |
| Ordering of equal-priority list items | any reordering with no other signal |

**The money row has a hard exception.** A cent is noise only if you have shown it does **not**
accumulate (run the 20-expense test) and does **not** survive into a settle-up transfer. A cent
that can never clear is `high`, not noise. And a **conservation break of any size** is never noise
— it is the visible end of a mechanism that can also lose a dollar.

### Rule 2 — Prediction is not observation

If you wrote "the user would feel..." without observing it, the finding is `[SIMULATED]` at most.
Do not promote a simulation to `[OBSERVED]` because it sounds plausible.

### Rule 3 — Reproduce before flagging anything HIGH

Anything `[high]` or `[critical]` must reproduce on a second attempt in the same session. If it
happens once and won't recur, downgrade to `[medium]` and tag `[INTERMITTENT]`.

**For a money finding, "reproduce" means re-derive.** Show the arithmetic twice, ideally from two
different starting points (the expense list and the balance card).

### Rule 4 — Source-or-suppress for code-level claims

A code-level claim ("the weight defaults with `||`", "the webhook has no idempotency") must cite
`file:line` or be demoted to `[SIMULATED]` and labeled "needs code review." Live-tester findings
without code claims are exempt — a persona can say "I can't find the button" without grepping.

### Rule 5 — Match against the suppression list

Phase 0.6 loads `docs/reports/user-test-reports/learnings.md` plus the standing suppression table
in `harness.md`. If a finding matches a prior `verified-false-positive` (fuzzy title match),
suppress it OR explicitly re-prove it:

```
[SUPPRESSED — verified-false-positive in run YYYY-MM-DD]: <original finding>
Why suppressed: <the prior reason>
Re-proof attempted: <yes/no, what changed>
```

Never re-flag without a re-proof; never silently drop — list it in the "Suppressed by prior
learnings" footnote so the user can audit.

### Rule 6 — Domain claims need a citation, not recall

A claim about Stripe/Venmo/Zelle behavior, a competitor's feature or price, or an FX rate is **not**
an observation — it is a factual assertion about the outside world, and model recall of these is
stale by construction. It must cite `domain-accuracy.md`, the repo's `research/`, or a live
`WebFetch`. Otherwise it is `[UNVERIFIED]` and cannot be scored.

**Split-math invariants are the exception** — they are derivable, so a violation is provable by
construction. Show the derivation and you have your citation.

### Rule 7 — Mode boundaries are not defects

Before flagging: is this thing missing because of `hasDb === false`, a missing `CRON_SECRET`, a
missing Stripe key, or absent Vision credentials? An honest limitation of the mode you're running
in is `MODE-BOUNDARY`, not a bug. **What is always a bug: a limitation the app hides behind a
success state.**

---

## Cognitive Load Simulation (personas forget)

AI remembers everything. Real users don't.

- After 3+ pages, a persona may only reference what a real person would retain: the main headline,
  the CTA they clicked, maybe one number.
- **Money is the exception with a twist:** people remember *their own* number and forget everyone
  else's. A persona who "recalls" the whole balance table from four screens ago is not modeling a
  user. If the app requires holding several numbers at once, that IS the information-architecture
  finding.
- If critical info appeared only once and early, test whether the persona "remembers" it later. If
  they wouldn't, that is a finding, not a memory success.

---

## Task Completion Tracking

Every persona's GOAL is a concrete, completable task with binary success:

```
TASK: "Take a 4-person, 8-expense trip from empty to a settle-up plan"
SUCCESS CRITERIA: a plan exists naming specific people and amounts, and every number is explicable
```

Not "explore the expense features" — unmeasurable. Track **steps taken**, **wrong turns**,
**goal completion** (Full / Partial / Failed), and the **failure point** if any.

```
TASK COMPLETION: 4/6 (67%) — A: Full, B: Full, C: Partial (no JPY option), D: Full, E: Partial, F: Failed (no DB)
```
