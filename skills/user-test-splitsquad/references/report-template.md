# Report Template

Write to `docs/reports/user-test-reports/user-test-<YYYYMMDD-HHMMSS>.md`.

**Write for the person who has to tell their friends what they owe, not for a QA lead.** Lead with
the verdict and the reconciliation. The bug table is supporting evidence, not the headline.

---

```markdown
# SplitSquad User Test — <YYYY-MM-DD HH:MM>

Mode: full | diff | focus:<surface> | money-only
URL: http://localhost:<port>   Branch: <branch>   Commit: <sha>
Storage: localStorage-only (no POSTGRES_URL) | postgres    <-- decides what is testable
Gates: npm test <n/n> · npm run lint <pass/fail> · npm run build <pass/fail>
Browser: <Playwright MCP via browse skill / none - text-only>
Environment notes: <ports, seed state, dirty working tree, what was NOT testable and why>

## Verdict

<Two or three sentences. Would six friends run a real trip's money through this? What is the
ceiling, and what single thing is holding it there?>

## The two scores

| Axis | Score | Trend |
|---|---|---|
| Product UX | X/10 | +/- vs prior |
| Money Integrity | X/10 | +/- vs prior (same storage mode only) |

<If UX is high and Money Integrity is low, THAT CONTRAST IS THE HEADLINE. Write it here in one
blunt sentence. A beautiful expense tracker that quietly shortchanges one person is worse than a
spreadsheet, and this is where that gets said.>

<If no hand reconciliation was performed, Money Integrity is UNSCORED. Say so here and say why.>

Task completion: N/M personas (X%) — A: Full, B: Partial (blocked at ...), ...

## The reconciliation

<The most important section. The corpus trip, its inputs, the app's numbers, the hand derivation.>

### <expense / balance / transfer> — <RULING: TRUST IT | RECONCILE BY HAND | WOULD START A FIGHT>

INPUTS:   subtotal 118.00 EUR | tax 8.5% | tip 12% | payer samira | equal | 3 participants
APP SAYS: total €142.19 | shares 47.40 / 47.40 / 47.40 | balance samira +94.79
BY HAND:  118 + 10.03 + 14.16 = 142.19 ✓ | 142.19 / 3 = 47.3966… → 47.40 ×3 = 47.41 over ✗
DELTA:    +€0.01 created by display rounding; does not accumulate across 20 expenses (checked)

**<Expert name>:** <what exactly is wrong, and what the right number is.>
Conservation X/5 · Rounding X/5 · Currency X/5 · Attribution X/5 · Settlement X/5 · **Honesty X/5**

<Honesty 1 CAPS this artifact at WOULD START A FIGHT and the axis at 4/10 no matter what the other
five say. Name the claim and the data that fails to back it.>

### Conservation result

<Mandatory every run. For every split type exercised: did shares sum to the total, to the cent?
State it even when the answer is yes — a confirmed negative is worth recording.>

| Split type | Exercised | Σ shares == total | Notes |
|---|---|---|---|
| equal | yes | ✓ | |
| shares | yes | ✓ | |
| percentage | yes | ✗ | weights summing to 250 created €12.40 |
| exact | no | — | **not covered this run** |
| weight 0 (excluded) | yes | ✓ | charged exactly 0 |

### Currency provenance

| Number | Rate used | Source | Dated | Verdict |
|---|---|---|---|---|
| €142.19 → $154.55 | 0.92 | **static fallback** | 2024 table | RECONCILE BY HAND — no provenance shown |
| ¥12,000 → $12,000 | **1:1** | no rate for JPY | — | **WOULD START A FIGHT — money invented** |

### Settle-up audit

Plan: <every transfer, verbatim>
Applied on paper: <does every member land at zero? show it>
Transfer count: N (≤ n−1? yes/no)   Deterministic across reloads: yes/no
Payment sign correct (I8): yes/no

## Panel confidence (calibration — every 5th run, or --calibrate)

Planted: 5 | Caught: N | Missed: M | **False-negative rate: M/5**
Per lane: bookkeeper _/_ · FX _/_ · treasurer _/_ · adversarial _/_ · cent-counter _/_
Repo suite (`npm test`) caught on its own: _/5

<For each miss: what it was, who should have caught it, and WHY they didn't. The why is the product
of this exercise, not the ratio. 2+/5 means fix the skill before trusting another run.>

**If calibration is overdue, this section still appears** and says so:

> Calibration overdue by N runs — this panel's false-negative rate is unmeasured, so "no money
> defects found" in this report is not evidence of absence.

## Domain accuracy findings

| # | Area | Claim in code | Reality | Citation | Severity | Disposition |
|---|---|---|---|---|---|---|
| D1 | currency.ts:40 | unknown code → rate 1 | converts 1:1 vs USD | invariant I10 | critical | FIX-NOW |

<Ungrounded claims go BELOW, under [UNVERIFIED]. Named so the next run can chase them; NOT scored
as defects and NOT handed to Phase 5.>

### [UNVERIFIED] — could not be grounded this run
- <claim> — needs: <what would ground it>

## Coverage

| Expert | Ran this run? | Last covered | Findings |
|---|---|---|---|
| bookkeeper/CPA | yes | 2026-07-21 | D1, M3 |
| payments-ops | **no** | never | — |
...

| Persona | Ran? | Completion | Score |
|---|---|---|---|
| A Trip Organizer | yes | Full | 6 |
| F Recurring-Bills | **no** — needs a DB | — | — |

<Every skipped persona and expert is named with its reason. Silent coverage gaps are how a wrong
number survives five runs. Also name any ROUTE with no persona owner.>

## Panel sessions

### A — Priya Raghavan (Trip Organizer)
Goal: <...>  Completion: Full/Partial/Failed  Score: X/10
<Narrative with THINKING blocks and PULSE readings. Findings tagged
[OBSERVED]/[INFERRED]/[SIMULATED] with evidence.>
Would she use it with her friends? <...>

<...repeat for B–F and each domain expert...>

## Where the panel disagreed

<Conflicts are signal. B's per-cent precision is A's six extra taps; D's minimum-transfer plan
routes money between people who never ate together, which B and E both find confusing; F's
automation is what B refuses to trust unwatched. Surface the real tensions here.>

## Consolidated findings

| # | Severity | Finding | Confidence | Evidence | Found by | Disposition |
|---|---|---|---|---|---|---|
| 1 | critical | ... | [OBSERVED] | screenshot / file:line / derivation | C | FIX-NOW |

Every finding has a disposition: FIX-NOW | BACKLOG | TEST-GAP | FALSE-POSITIVE | UNVERIFIED |
MODE-BOUNDARY. A finding with no disposition is a bug in the run.

## Status vs. prior baseline

| Prior finding | Status |
|---|---|
| ... | FIXED / STILL_PRESENT / REGRESSED |

<Anything STILL_PRESENT for 3+ runs is structural. Say so.>

## Suppressed by prior learnings

<Verified false positives that came up again. List them so the user can audit the suppression —
never silently drop.>

## Competitor delta

| Tool | What they do better | What SplitSquad does better |
|---|---|---|
| Splitwise / Tricount / Settle Up / Splid | ... | ... |

**What would make a group switch?** <...>
**What would stop them?** <...>
```

---

## `baseline.json` schema

```json
{
  "date": "2026-07-21",
  "report": "user-test-20260721-233000.md",
  "previous_baseline": "<prior report filename or null>",
  "mode": "full",
  "url": "http://localhost:3001",
  "branch": "main",
  "commit": "<sha>",
  "storage": "localstorage-only",
  "gates": { "test": "85/85", "lint": "pass", "build": "pass" },
  "browser": "playwright MCP via browse skill",
  "environment_note": "working tree dirty; :3000 held by an unrelated app",

  "prior_fixes_survived": {
    "checked": true,
    "present": ["src/utils/currency.ts:40"],
    "missing": [],
    "note": "missing != regressed — a fix lost to a checkout is NOT a product regression"
  },

  "scores": { "product_ux": 6, "money_integrity": 3 },
  "money_integrity_scored": true,
  "task_completion_rate": "5/6",

  "panel": [
    { "id": "A", "name": "Priya Raghavan", "role": "Trip Organizer",
      "goal": "...", "completion": "Full", "score": 6, "would_use": "not until FX is fixed" }
  ],
  "persona_coverage": {
    "A": "2026-07-21", "B": "2026-07-21", "C": "2026-07-21",
    "D": "2026-07-18", "E": "2026-07-21", "F": null
  },
  "personas_skipped": [
    { "id": "F", "reason": "cron surfaces need a DB", "owed_since_runs": 1 }
  ],

  "experts_ran": ["bookkeeper", "fx", "durability"],
  "expert_coverage": {
    "bookkeeper": "2026-07-21", "payments_ops": null, "splitwise_power_user": null,
    "fx": "2026-07-21", "receipt_ocr": null, "durability": "2026-07-21",
    "privacy": null, "accessibility": null, "email": null, "security": null
  },
  "surfaces_without_owner": [],

  "conservation": {
    "equal": "pass", "shares": "pass", "percentage": "fail", "exact": "not-covered",
    "excluded_zero_weight": "pass",
    "trip_net_sums_to_zero": true,
    "accumulation_test_expenses": 20,
    "accumulated_error_cents": 0
  },
  "currency": {
    "rates_source": "static-fallback",
    "live_fetch_succeeded": false,
    "unsupported_code_behavior": "1:1 vs USD",
    "round_trip_ok": true
  },
  "settlement": {
    "plan_zeroes_everyone": true,
    "transfer_count": 3,
    "max_expected": 3,
    "deterministic_across_reloads": false,
    "payment_sign_correct": true
  },

  "calibration": {
    "due": false, "last_run": "2026-07-17", "runs_overdue": 0,
    "planted": 5, "caught": 5, "missed": 0, "false_negative_rate": "0/5",
    "per_lane": { "bookkeeper": "2/2", "fx": "1/1", "treasurer": "1/1", "adversarial": "1/1" },
    "cross_catches": [],
    "repo_suite_caught": "2/5"
  },

  "artifacts": [
    { "kind": "balance", "who": "marco", "ruling": "WOULD START A FIGHT",
      "conservation": 5, "rounding": 4, "currency": 1, "attribution": 5,
      "settlement": 4, "honesty": 3,
      "note": "JPY expense converted 1:1 vs USD — balance overstated by ~$11,900" }
  ],

  "domain_accuracy_findings": [
    { "id": "D1", "area": "currency.ts:40", "severity": "critical",
      "claim": "unknown code falls back to rate 1",
      "reality": "silently converts 1:1 against USD",
      "citation": "invariant I10", "disposition": "FIX-NOW" }
  ],
  "unverified": ["..."],

  "bug_counts": { "critical": 1, "high": 3, "medium": 5, "low": 4 },
  "previous_baseline_status": { "fixed": [], "still_present": [], "regressed": [] },
  "suppressed": ["swr_empty_shapes_on_error", "settlements_stub"],
  "post_run_implementation": null
}
```

## `learnings.md` — ledgers FIRST, then a rolling 5-run window

**The file must open with the routing block below**, because Phase 0 reads it to route the run and
a debt recorded below the fold does not get paid. **Target the whole file under ~200 lines**;
promote durable facts out to `harness.md` / `domain-accuracy.md` / the suppression list rather than
letting run blocks accumulate them.

```markdown
# SplitSquad user-test learnings

## Expert coverage ledger        <- FIRST. All ten, NEVER if unaudited.
bookkeeper: 2026-07-21 | payments-ops: NEVER | splitwise: NEVER | fx: 2026-07-21 |
receipt-ocr: NEVER | durability: 2026-07-21 | privacy: NEVER | a11y: NEVER |
email: NEVER | security: NEVER

## Persona ledger
A: 2026-07-21 | B: 2026-07-21 | C: 2026-07-21 | D: 2026-07-18 (OWED) | E: 2026-07-21 | F: NEVER

## Calibration
last: never | FN rate unmeasured | due at run #5 | OVERDUE BY: 0

## Next run must do
1. <the owed persona>  2. <the NEVER expert>  3. <the structural item>
```

Then, below that, prepend a run block:

```markdown
## Run YYYY-MM-DD HH:MM (<mode>)
- **environment:** <port, storage mode, browser, gates, dirty tree>
- **prior fixes survived:** <present / missing — missing is NOT a regression>
- **ground-truth promoted:** <facts verified live this run -> update domain-accuracy.md>
- **verified-false-positive:** <finding> — <why it is not a bug. Never re-flag.>
- **regression-risk:** <what to re-check next run and how>
- **open findings:** <carried forward, with age in runs, EACH WITH file:line or a derivation —
  not a summary sentence. A STILL_PRESENT claim must be re-proven, or it is UNVERIFIED.>
- **structural (3+ runs):** <anything STILL_PRESENT three runs running>
```
