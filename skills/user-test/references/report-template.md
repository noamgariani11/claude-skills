# Report Template

Write the full report to `$_REPORT_FILE` using this structure. Sections marked (optional) are omitted when empty. Sections marked (mode-only) apply only in that mode.

---

```markdown
# [Report Title — varies by mode]
**Date:** [today]
**App URL:** [URL]
**Testers:** [T1 name/archetype] · [T2 name/archetype] · [T3 name/archetype]
**Routes Covered:** [N of M pages]

---

## Focus Target (focus-mode only)

**Page / Feature:** [name as given by user]
**Resolved Route:** [e.g. /dashboard/maintenance]
**Source File(s):** [e.g. src/app/dashboard/maintenance/page.tsx]
**What it's supposed to do:** [one sentence from reading the source]
**Sub-flows tested:** [list]
**Entry paths used:**
- T1: [how they arrived]
- T2: [how they arrived]
- T3: [how they arrived]

---

## Changes Under Test (diff-mode only)

| File Changed | Route/Feature Affected | Type of Change |
|--------------|-----------------------|----------------|

**Blast radius routes:** [routes tested due to shared dependencies]

---

## Executive Summary

[3-4 sentences. No file paths, no CSS selectors, no technical jargon. A CEO or PM should grok it in 60 seconds.]

**Task Completion Rate: [N/3] ([percentage]%)**
**Regression vs. last run:** [improved / unchanged / regressed / first run]

---

## Score Trends (mandatory if `baseline.json` exists; one-line summary if first run)

Composite + per-persona deltas vs prior baseline. Use ▲ for delta ≥ +0.3, ▼ for ≤ −0.3, → for within ±0.3. Bug-count deltas use the same arrows but with absolute counts (any new Critical = ▼ regardless of magnitude).

| Metric | Prior | Current | Δ | Trend |
|---|---|---|---|---|
| Composite score | [X.X] | [X.X] | [+/-X.X] | ▲/▼/→ |
| Brad (Skimmer) | [N/10] | [N/10] | [+/-N] | ▲/▼/→ |
| Linda (Careful Reader) | [N/10] | [N/10] | [+/-N] | ▲/▼/→ |
| Marcus (Mobile Tapper) | [N/10] | [N/10] | [+/-N] | ▲/▼/→ |
| Critical bugs | [N] | [N] | [+/-N] | ▲ if 0 net new, else ▼ |
| High bugs | [N] | [N] | [+/-N] | ▲/▼/→ |
| Medium bugs | [N] | [N] | [+/-N] | ▲/▼/→ |
| Low bugs | [N] | [N] | [+/-N] | ▲/▼/→ |

**What improved this run** (3-5 bullets, evidence-backed): [list]
**What regressed this run** (call out loudly if non-empty): [list, or "nothing regressed"]

---

## Recurring Issues (omit if empty)

Issues from `issue_history` where `runs_seen.length >= 2`. Sorted by severity then by run count. **N=3+ runs = structural decision** — surface with that framing, not as a fresh finding.

| Issue | Severity | First seen | Runs seen | State | Recommendation |
|---|---|---|---|---|---|
| [stable-key] [title] | [C/H/M/L] | [date] | N (`[date1, date2, date3]`) | OPEN/FIXED/SUPPRESSED | [structural-decision / fix-now / continue-monitoring] |

**Regressions detected this run** (issues that were FIXED in a prior run and reappeared): [list with file:line if available; flag as own-goals]

---

## Status vs. Prior Baseline (mandatory if `baseline.json` exists)

For every finding listed in the prior baseline's `new_critical_or_high_in_this_run` and the `previous_baseline_status` keys, emit a row. Status is one of:

- **FIXED** — verified the prior bug no longer reproduces (cite the verification step)
- **STILL_PRESENT** — same root cause, same symptoms; mark `[recurring N runs]` if STILL_PRESENT 3+ runs in a row
- **REGRESSED** — was FIXED in a prior baseline, now broken again (call this out loudly — own-goal)
- **NOT_RETESTED** — out of scope this run (e.g., Skimmer didn't get to that route); explain why
- **SUPPRESSED** — matched a `verified-false-positive` in `learnings.md`; do not re-flag

| Prior Bug | Severity | Status | Evidence This Run |
|---|---|---|---|
| [name from baseline] | [H/C] | **STILL_PRESENT** [recurring 3 runs] | [screenshot, console, or "verified by Linda step 4"] |
| [name] | [H] | **FIXED** | [what's different now] |
| [name] | [M] | **NOT_RETESTED** | [why — gate, focus mode, etc.] |

A bug **STILL_PRESENT for 3+ consecutive runs** is no longer a bug report — it's a structural decision the product is accepting. Surface it in the Cross-Tester Summary as "this product accepts the trade-off; recommend stop testing it OR investigate root cause" — not as a HIGH finding.

---

## Cross-Tester Summary

[5-7 sentences synthesizing what all three testers experienced. Patterns across testers. What the app consistently succeeded or failed at. No spin.]

**Overall Scores:**
- [Name 1] ([archetype]): [X/10] — "[one sentence in their voice]"
- [Name 2] ([archetype]): [X/10] — "[one sentence in their voice]"
- [Name 3] ([archetype]): [X/10] — "[one sentence in their voice]"

**Score caps applied:** [list any scores capped at 6 per evidence rules, with reason]

---

## Emotional Journey Comparison

| Step | T1 Trust/Conf/Engage | T2 Trust/Conf/Engage | T3 Trust/Conf/Engage | Divergence |
|------|---------------------|---------------------|---------------------|------------|

**Key divergence points:** [where testers disagreed by 2+ points]

---

## Tester Sessions

Per-tester narrative. Each tester gets: First Impression · Goal Walkthrough (w/ PULSE inline) · Information Hierarchy · Design Critique · Verdict. Bugs and friction are NOT duplicated here — they live in the Consolidated Bug List below, cross-referenced by tester ID.

### Tester 1: [Name] — [Archetype] · [viewport] · Visit: [first/return]
**Goal:** [task + success criteria]
**Score:** [X/10] · **Task:** [Full/Partial/Failed]

[Narrative, present tense, their voice. PULSE readings inline.]

### Tester 2: [Name] — [Archetype] · [viewport] · Visit: [first/return]
[same]

### Tester 3: [Name] — [Archetype] · [viewport] · Visit: [first/return]
[same]

---

## Consolidated Bug List

Deduplicated across all testers, tech reviewer, adversarial user, and codex. Severity = worst rating among sources.

| # | Severity | Confidence | Description | Found By | Steps | Evidence |
|---|----------|-----------|-------------|----------|-------|----------|

Severity: Critical (blocked goal), High (seriously hurt experience), Medium (annoying, got past it), Low (noticed, wouldn't mention)
Confidence: [OBSERVED] / [INFERRED] / [SIMULATED]
Evidence: screenshot filename, console line, network entry, or "—" for [INFERRED]/[SIMULATED]

---

## Technical Reviewer Findings

| # | Category | Severity | Finding | Evidence | Missed By |
|---|----------|----------|---------|----------|-----------|

Categories: console-error, performance, accessibility, edge-case, design-system, cross-session-pattern

---

## Adversarial User Findings

| # | Category | What They Did | Result | Verdict | User Impact |
|---|----------|---------------|--------|---------|-------------|

Categories: input-chaos, nav-abuse, timing, state-corruption, trust-gap
Verdicts: robust / fragile / broken

**Robustness Score: [N] robust / [N] fragile / [N] broken out of [N] tests**

---

## Codex Code Review (optional — omit entire section if codex unavailable)

**Raw Codex report:** `$_CODEX_OUT`
**Codex summary** (from `baseline.json`): corroborated [N], new+code-verified [N], new+unverified [N], disputed [N], out-of-scope [N].

### Corroborated Findings (Codex + live tester)

These roll into the main Consolidated Bug List above with the live evidence as primary. Listed here only for the codex-side reasoning.

| # | Severity | Finding | Codex File:Line | Live Cross-Ref |
|---|----------|---------|-----------------|----------------|

### Codex-Only Findings, Code-Verified

Codex flagged it; Phase 2E grep/Read confirmed the cited file:line matches the claim. These also roll into the Consolidated Bug List.

| # | Severity | Finding | File:Line (verified) | Why Live Testers Couldn't Catch It |
|---|----------|---------|----------------------|-----------------------------------|

### Codex Flags Requiring Manual Review (NEW + UNVERIFIED)

Codex made a claim, but Phase 2E couldn't confirm the cited code matches the claim (or no precise reference was given). These are NOT in the Consolidated Bug List. Treat as leads, not bugs. If >50% of codex findings land here, flag the imbalance ("codex coverage diverged from persona coverage; consider re-running codex with a tighter prompt").

| # | Codex Claim | Severity Codex Asserted | Reference Given | Why Unverified |
|---|-------------|--------------------------|-----------------|----------------|

### Disputed / Down-ranked

| # | Codex Claim | Why Down-ranked |
|---|-------------|-----------------|

**Codex style/refactor suggestions:** [N] items — see raw report.

---

## Competitive Expectation Gaps

| Persona | Expected Like | Gap | Impact |
|---------|---------------|-----|--------|

---

## State Resilience Findings

| Test | Tester | What Happened | Data Lost? | UX Impact |
|------|--------|---------------|-----------|-----------|
| Refresh mid-flow | T1 | | | |
| Back after submit | T2 | | | |
| Deep link | T3 | | | |

---

## Information Hierarchy Problems

| # | Page | What's There | What Users Got | Problem |
|---|------|--------------|----------------|---------|

---

## What Was Missing

| # | What They Wanted | Who | Exact Moment | Why It Mattered |
|---|------------------|-----|--------------|-----------------|

---

## Quantitative Metrics

| Metric | T1 | T2 | T3 | Signal |
|--------|----|----|----|--------|
| Pages visited | | | | |
| Interactions | | | | |
| Wrong turns | | | | |
| JS errors | | | | |
| Task completion | | | | |
| Steps to complete | | | | |
| Failure point | | | | |
| Avg page load | | | | |

---

## Route Coverage

| Route | Visited By | Notes |
|-------|-----------|-------|

**Routes never visited:** [list — discoverability problems]

---

## Developer Diagnosis

**Para 1 — Promise vs. reality.** What does the landing page promise and what does the app deliver? Name the gap if there is one.

**Para 2 — Highest-leverage fix.** One change that would most improve completion rates.

**Para 3 — The invisible problem.** What the developer probably doesn't notice. Something that works as coded but creates friction in use.

**Para 4 — Navigation verdict.** Does the structure make sense from the outside?

**Para 5 (optional) — What works.** If something was genuinely impressive across testers.

---

## Prioritized TODO List

### P0 — Users are leaving because of these
- [ ] [Fix] — [testers, impact]

### P1 — Hurting the experience significantly
- [ ] [Fix] — [testers, impact]

### P2 — Friction and polish
- [ ] [Fix] — [testers, impact]

### P3 — Feature gaps / design / copy
- [ ] [Change] — [who wanted it, why]

---

## Screenshot Index

| Tester | Step | File | What it shows |
|--------|------|------|---------------|

---
*Generated by /user-test*
```

---

## Final In-Chat Summary (separate from the saved report)

After writing and printing the report, output this in the conversation:

```md
# User Test Summary

## What We Did
- Mode: [full / diff / focus]
- URL: [url]
- Routes covered: [N]
- Screenshots: [N]
- Report: [path]

## The People Who Tested

### [T1 Name] — [archetype], [visit]
- **Who they are:** [1-2 sentences]
- **Goal:** [task]
- **What happened:** [2-4 sentence narrative]
- **Outcome:** [completed/partial/failed] · **Score:** [X/10]
- **Their verdict:** "[one-sentence quote]"

### [T2 Name] — [archetype], [visit]
[same]

### [T3 Name] — [archetype], [visit]
[same]

### Technical Reviewer
- **Top findings:** [3-5 bullets]
- **Their verdict:** "[quote]"

### Adversarial User
- **What actually broke:** [bullets]
- **Their verdict:** "[quote]"

### Codex (if available)
- **New issues:** [N] · **Corroborated:** [N]
- **Most important catch:** [one sentence]

## Headline Findings
[3-6 bullets — what matters most]

## Score Trend vs Last Run
- **Composite:** [prior] → [current] ([delta], ▲/▼/→)
- **Direction:** improved / regressed / unchanged / first run
- **Top mover:** [persona name + delta + one-sentence why]

## Recurring Issues (only if any have runs_seen ≥ 2)
- [issue title] — [N runs in a row] — [state: OPEN/REGRESSED] — [recommendation]

## Scores at a Glance
| Tester | Archetype | Task | Score | Δ vs prior |
|---|---|---|---|---|
```

---

## Engineering Action Items (separate final block)

```md
# Engineering Action Items — [App Name]

## P0 — Ship a fix today
- [ ] **[Short title]**
  - Change: [concrete change]
  - Where: [file:line or route]
  - Why: [tester + observation]
  - Done when: [verifiable criterion]

## P1 — This week
- [ ] ...

## P2 — Next sprint / polish
- [ ] ...

## P3 — Backlog
- [ ] ...
```

Every P0 and P1 item MUST have all four fields filled in. P2/P3 may be terser but still need Change + Why.

---

## Status Line (final line of output)

**STATUS: DONE — Composite [X.X] ([+/-X.X] vs prior) [▲/▼/→] · T1: [X/10] [Δ] · T2: [X/10] [Δ] · T3: [X/10] [Δ] · Tech: [N] findings · Adv: [N] broken/[N] tested · Codex: [N] new/[N] corroborated · [N] bugs · [N] friction · [N] TODOs · [N] recurring [≥2 runs] · [N] regressions**

Follow with one raw sentence from each tester, one from the technical reviewer, one from the adversarial user, and one from Claude on Codex's most important catch (if applicable).
