---
name: user-test-splitsquad
description: |
  SplitSquad-specialized user testing for a shared-expense app. A six-person group panel — the
  trip organizer, the cent-counting roommate, the international traveler, the group treasurer who
  actually chases the money, the stranger who arrives through an invite link with no account, and
  the housemate running recurring bills and subscriptions — plus a rotating bench of ten domain
  experts (bookkeeper/CPA, payments-ops, Splitwise power user, FX/treasury, receipt-OCR skeptic,
  offline/localStorage durability, privacy, accessibility, email deliverability, app-security).
  Scores TWO things: the product UX, and — unique to this skill — MONEY INTEGRITY: does every
  screen's number survive being re-derived by hand, does the app create or destroy money in
  rounding and FX, and would the settle-up plan it produced actually leave the group square?
  Includes conservation/rounding/FX auditing of `src/utils/balances.ts`, `currency.ts`, and
  `debtSimplification.ts` against the invariants in `references/domain-accuracy.md`, plus
  planted-defect calibration that measures what the panel MISSES. Each persona runs as an
  isolated Agent subprocess. Use when you want "would six friends trust this app with a real
  trip's money, and would anyone get shortchanged?" — not generic UX.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebFetch
  - AskUserQuestion
  - Agent
---

# /user-test-splitsquad — SplitSquad Group-Money Testing

This skill answers: **"Would six friends run a real trip's money through this — and would every
one of them agree with the final number?"**

SplitSquad's value is not its UI. It is the **number**: a balance, a "you owe Marco $42.17", a
settle-up plan, a trip report. A generic user test can tell you the expense form has a weak empty
state. It cannot tell you that ¥12,000 was counted as $12,000, that an excluded participant was
silently charged, that the settle-up plan leaves 3¢ stranded forever, or that the app says
"all settled up" while the ledger still nets to −$8.

So this skill scores **two axes**, and reports them separately:

| Axis | Question | Judged by |
|---|---|---|
| **Product UX** (/10) | Can a group actually run their money in this app? | Group panel |
| **Money Integrity** (/10) | Do the numbers survive being re-derived by hand? | Bookkeeper + FX + adversarial |

**A run can pass UX and fail Money Integrity. That is the most important verdict this skill can
return — say it loudly.** A beautiful expense tracker that quietly shortchanges one person is
worse than a spreadsheet, because the spreadsheet does not have the group's trust.

Load references on demand. Do not read them all at once.

| When you need | Load |
|---|---|
| The six group-panel persona cards (A–F), data lanes, diversity rules | `references/personas.md` |
| The ten domain-expert cards, rotation rules, per-expert checklists | `references/experts.md` |
| Money invariants, FX ground truth, competitor + payment-rail facts, the citation rule (**read before any accuracy claim**) | `references/domain-accuracy.md` |
| How to judge a balance / settle-up plan / export — the money rubric | `references/money-integrity.md` |
| Critical workflow protocols (core loop, settle-up, FX, invites, recurring, receipts) | `references/workflows.md` |
| Environment + harness facts (ports, no-DB mode, seed people, browser rules) | `references/harness.md` |
| Confidence tags, score gating, false-positive guardrails | `references/scoring-and-evidence.md` |
| Persona internal-reasoning format | `references/chain-of-thought.md` |
| Report shape + `baseline.json` schema | `references/report-template.md` |
| Planted-defect calibration — measuring what the panel MISSES (every 5th run, or `--calibrate`) | `references/calibration.md` |

---

## Core Philosophy

1. **Re-derive the number, don't admire the screen.** Every run must take at least one balance the
   app displayed and reproduce it by hand from the expense list. A report with no reconciliation
   did not run this skill.
2. **Group members, not archetypes.** These personas are in a group chat together. They have money
   histories with each other, and one of them will absolutely argue about $3. That argument is the
   product's real test.
3. **Cite or shut up.** An expert asserting "Venmo caps transfers at $X" or "Splitwise rounds the
   other way" from memory is exactly as dangerous as the app being wrong. Every domain-accuracy
   finding cites `references/domain-accuracy.md`, the repo's `research/`, a test in
   `src/utils/__tests__/`, or a live `WebFetch`. Ungrounded claims are `[UNVERIFIED]` and cannot be
   scored as defects.
4. **Know which storage layer is running.** With `POSTGRES_URL` unset (`hasDb` in
   `src/lib/db/index.ts`), the app boots on seed data and persists to localStorage — by design.
   Judging localStorage-mode behavior as "data loss" is usually invalid; judging *silent* fallback
   that looks like a save is valid. Every run states which mode it observed.
5. **A missing feature is not a lie; a fake success is.** `/api/settlements` is a documented stub,
   and the DB layer is deliberately additive. An honest "not available without a database" is a
   product boundary. A screen that says *settled* when nothing settled is `critical`.
6. **The report is for the person who has to tell their friends what they owe.** Lead with the
   verdict and the reconciliation. The bug table is supporting evidence.

---

## Phase 0: Prep

### 0.1 — Parse mode

| Flag | Behavior |
|---|---|
| *(none)* | `full` — group panel + rotated domain experts + technical + adversarial |
| `--diff` | Personas scoped to surfaces the working tree / recent commits touched. Pre-push mode. |
| `--focus <surface>` | e.g. `--focus settle-up` — surgical depth on one surface |
| `--expert cpa,fx` | Force specific domain experts (overrides rotation) |
| `--money-only` | Skip UX personas. Build a trip, capture every number, audit the math. Cheap + fast. |
| `--calibrate` | Plant 5 defects in a worktree, run normally, measure what the panel MISSED. See `references/calibration.md`. Run every 5th run — a skill that never measures its false-negative rate cannot be trusted when it reports "the math checks out". |

### 0.2 — Detect the URL and verify it is actually SplitSquad

Never trust the first port that answers. This box runs several apps at once, and **:3000 has been
held by an unrelated picoCTF site** while SplitSquad was elsewhere. Run the canonical port scan in
`references/harness.md`, which is the single maintained copy of the scan list, and **re-check the
port during long runs, not just at the start**.

The served `<title>` must contain **SplitSquad**. If no server is up, start one **through the
`browse` skill's `serve.sh`** — never `npm run dev &` (global CLAUDE.md, memory-cap rule).

### 0.3 — Storage mode + first-run state (this decides half the findings)

```bash
ls -a | grep -E '^\.env' || echo "NO .env — localStorage mode"
grep -n "hasDb" src/lib/db/index.ts | head -3
```

- **No `POSTGRES_URL` → localStorage mode.** The app boots with seed people (Samira, Marco, Pilar,
  Aiden) and seed trips, persists under `splitsquad-local-state`, and the SWR hooks return empty
  shapes on error so the local state keeps rendering. **Credential login cannot work without a
  DB** — a persona blocked at sign-in in this mode has found a *mode boundary*, not necessarily a
  bug. What *is* a bug: a sign-in surface that gives no honest account of why.
- **With a DB** → note it in `baseline.json` as `storage: postgres`; DB-only routes become
  testable and the authz/tenancy checks in `references/experts.md` (security) turn on.

Record `storage` in `baseline.json`. **Never compare Money Integrity scores across storage modes
without saying so.**

### 0.4 — Gates first, personas second

```bash
npm test          # pure money logic — 6 files / 85 tests as of 2026-07-21
npm run lint
npm run build     # slow; run it once, early. A red build caps the run.
```

A failing build is a `P0` on its own and it changes the run: personas test what is *served*, which
may not be what the repo *builds*. Say which in the report's environment note.

### 0.5 — Route + surface discovery

```bash
find src/app -name page.tsx | sed 's|/page.tsx||' | sort
find src/app/api -name route.ts | sort | wc -l
```

**Derive surfaces from code, never from a reference file's list.** The app moved its dashboard from
`/` to `/app` and added `/login` after CLAUDE.md was written; a persona sent to `/` for the
dashboard is testing a landing page. Reconcile the route list against the persona cards' Surfaces
lines and against `learnings.md`'s coverage ledger — **a surface with no persona owner is never
audited**, and any mismatch is a `medium` finding in its own right.

### 0.6 — Baseline + learnings + the neighbouring bug ledger

```bash
ls docs/reports/user-test-reports/
cat docs/reports/user-test-reports/baseline.json 2>/dev/null
cat docs/reports/user-test-reports/learnings.md 2>/dev/null
cat docs/reports/bugs/latest.json 2>/dev/null      # /bug-hunt's store — READ ONLY
```

First run: no baseline — say so and establish one. Otherwise load the **verified-false-positive**
list, the **surface coverage ledger**, the **persona ledger**, the **open findings**, and the
**calibration slot**.

`docs/reports/bugs/` belongs to `/bug-hunt`. **Read it for lore; never write there.** It already
paid for a 27-finding static sweep (build failure, unknown-currency 1:1 conversion, trip-order-
dependent ledger, weekly/yearly subscriptions never charging). Do not re-discover those from
scratch — **but do not carry them as fact either**: re-prove anything you intend to report.

**Calibration debt is blocking.** If the ledger shows calibration due or overdue (every 5th run),
**this run converts to `--calibrate`** unless the user explicitly declines. If they decline, the
report's verdict must state that the panel's false-negative rate is unmeasured.

**Carry EVIDENCE, not prose.** An open finding carried into a persona brief carries its
`file:line` from the prior report, not its summary sentence. A `STILL_PRESENT` claim must be
**re-proven this run** or it is `UNVERIFIED`. Where a brief states a diagnosis, mark it as the
prior run's **hypothesis** so the agent tests it rather than inheriting it.

### 0.7 — Change delta (drives rotation and `--diff`)

```bash
git status --short | head -30
git log --oneline -15
git diff --name-only HEAD -- src/utils src/context src/app/api
```

Money files touched (`balances.ts`, `currency.ts`, `debtSimplification.ts`, `AppStateContext.tsx`)
→ the bookkeeper and FX experts get priority in the rotation, and the Money Integrity axis is
re-derived from scratch rather than trended.

### 0.8 — Fix-survival check (before anyone scores anything)

Read the prior run's `post_run_implementation.fixed` inventory from `baseline.json` and
spot-check each fix is still physically present (`git log --oneline -8`, `git status --short`).

| State | Meaning | Consequence |
|---|---|---|
| **Fixes present** | Normal. Score against them. | Findings they closed should read `FIXED`. |
| **Fixes missing** | Lost to a checkout/stash — **not a product regression.** | Re-apply or note as lost. **Do NOT file as `REGRESSED`.** |

A lost fix and a regressed fix look identical from the UI. Mislabelling the first manufactures a
phantom regression and corrupts the trend line the baseline exists to carry.

---

## Phase 1: Panel Selection

**Tier 1 — Group panel (all six, every run except `--money-only`):**
A Trip Organizer · B Cent-Counter · C International Traveler · D Group Treasurer ·
E Invited Stranger · F Recurring-Bills Housemate. Cards in `references/personas.md`.

> **Personas get a ledger, and an owed persona is MANDATORY.** Keep it in `learnings.md`:
>
> ```
> ## Persona ledger
> A: 2026-07-21 | B: 2026-07-21 | C: 2026-07-21 | D: 2026-07-18 (OWED) | E: 2026-07-21 | F: NEVER
> ```
>
> A persona not fielded last run **runs this run before any optional work**, and any drop is stated
> in the report with its reason. D and F are the most-droppable (D needs a solo data lane; F's cron
> surfaces need a DB) — that is a scheduling cost, not a licence to skip them. D owns the only
> coverage of settle-up correctness, which is the app's whole promise.

**Tier 2 — Domain experts (3–4 per run):** pick by, in order:
1. `--expert` if given.
2. Experts whose files the diff touched (Phase 0.7).
3. **Any expert reading `NEVER`** — unmeasured beats merely stale; at least one slot per run goes
   here while any exists.
4. Staleness — longest since last covered, per the ledger.

Round-robin so all ten are covered within ~3 runs. **Every skipped expert is named in the report
with its last-covered date.** No silent coverage gaps.

**Tier 3 — Closers (every run):** Technical Reviewer, Adversarial Freeloader.

### Data lanes — parallel personas must not corrupt each other's ledger

State lives in **one localStorage key per browser context** (`splitsquad-local-state`), and — when
a DB is present — in one shared Postgres. Without lanes, personas overwrite each other's trips and
then report the damage as a money bug.

- Each persona works **only** in a trip it created, named with its own tag (`[A] Lisbon`, `[B]
  Groceries`) so ownership is greppable.
- Nobody deletes or edits an expense they did not create. Nobody edits **people** except A.
- **Only D creates payments / settlements.** A payment is the one mutation that changes *everyone
  else's* balances, so a stray settle-up from another persona invalidates every concurrent
  reconciliation.
- Nobody clears localStorage or reseeds mid-run. If a reset is needed, it happens between phases
  and is recorded.
- **One browser-driving agent at a time** — see the shared-browser trap in `references/harness.md`.

---

## Phase 2A: Trip Organizer first — breadth + gate

Persona **A** runs alone, first, as an isolated `Agent`. She creates a trip, adds members, enters a
week of real expenses across split types, and drives the whole core loop. She is the gate.

**Gate rule (mandatory after A returns):**

- If A could **not complete the core loop** (create trip → add expenses → see balances → produce a
  settle-up plan) for reasons that are not an honest mode boundary (no DB, no Stripe key), the
  product is broken at the trunk. **Stop.** Report A's finding and the fix. A capped run is a
  cheap run.
- If A completed it, **the trip she built is the corpus** — every displayed number, captured
  verbatim with the inputs that produced it, is what the domain experts re-derive in Phase 2C.
  Capture protocol in `references/money-integrity.md`. **If she skips the capture, the run has no
  money axis.**

Then recalibrate: **never send a persona at a wall you have already decided to build.** If A found
that Stripe checkout needs keys nobody has, D's goal becomes "evaluate the settle-up *plan* and the
handoff to Venmo/Zelle," not "pay through the app."

---

## Phase 2B: Remaining group panel (isolated agents)

B, C, D, E, F run as isolated `Agent` subprocesses, each with its card, its lane, its goal, and its
success criteria. They share no state and must not see each other's findings — that independence is
the whole point of the panel. **Only one may drive the browser at a time; the rest reason over the
captured corpus, the code, and `curl` against route handlers.**

Each returns: session narrative with `THINKING:` blocks, PULSE readings, tagged findings, task
completion (Full/Partial/Failed), score with the gating rule applied, and — for B and D — a money
verdict on every number they saw.

---

## Phase 2C: Domain experts (isolated agents)

Each selected expert does **three jobs**, in this order:

1. **Invariant audit.** Take their slice of the money math and check it against the invariants in
   `references/domain-accuracy.md` — conservation, rounding, sign, currency provenance,
   determinism. Read the code (`src/utils/balances.ts`, `currency.ts`, `debtSimplification.ts`) and
   the tests that pin it. **Drift between a stated invariant and the code is a finding by
   definition.**
2. **Test-shape audit.** 85 tests all pass. Ask the higher-value question: *what shape are they?*
   A suite that only asserts "share ≥ 0" or spot-checks one split type cannot fail on a
   conservation break. See the standing check in Phase 2D.
3. **Corpus judgment.** Take the numbers the app *actually displayed* (Phase 2A corpus) and rule
   on each: **TRUST IT / RECONCILE BY HAND / WOULD START A FIGHT.** Show the hand derivation.
   Rubric in `references/money-integrity.md` — **including dimension 6, honesty**: does any screen
   assert a state (settled, paid, sent, saved) that the underlying data does not support? A false
   assertion caps the artifact at WOULD START A FIGHT and 4/10 regardless of accuracy elsewhere.

An expert who only reviewed the UI and skipped jobs 1–3 has not done the work. Reject and re-run.

---

## Phase 2D: Technical Reviewer

Not a persona — a code reviewer with group-money context. Checks:

- **Single source of truth**: `calculateExpenseTotal` / `resolveShares` / `computeBalances` live in
  `src/utils/balances.ts` and nothing re-implements them. **A second implementation of the math is
  a `high` finding on sight** — `GlobalBalanceCard.tsx` and `CrossTripBalanceView.tsx` have both
  carried their own arithmetic, and a view that disagrees with the canonical balance is the exact
  bug the user experiences as "the app can't decide what I owe."
- **The `?? 1` rule**: weight-based splits must use `?? 1`, never `|| 1`. An explicit `0` means
  *excluded*; `||` silently charges them. Grep for it every run.
- **Multi-payer wiring**: `Expense.payers[]` exists in the type, is written by
  `POST /api/expenses`, and is honored by `GlobalBalanceCard` — **verify whether the canonical
  `computeBalances` honors it too.** If it credits only `payerId`, every multi-payer expense
  mis-attributes money, and the two surfaces disagree. Report the *current* state with file:line;
  do not inherit this paragraph as a finding.
- **Cron discipline**: every cron route calls `requireCronSecret(request)` and fails closed.
- **Rate limiting**: auth-sensitive and expensive routes gate on `checkRateLimit()`. Note that the
  store is per-instance and in-memory — that is a documented boundary, not a defect; an
  *unbounded* store or a client-controllable key is a defect.
- **Money in the DB layer**: raw SQL only under `src/lib/db/`; routes never inline SQL. Amounts
  round-trip without precision loss.
- **Honest fallback**: the SWR fetcher deliberately returns empty shapes on error. Check no write
  path does the same — a POST that "succeeds" into nothing (fabricating an unsaved entity) is
  `high`.
- **Stripe**: webhook signature verified, event idempotency, DB failures surfaced (not swallowed
  behind a 200), refunds recorded at their actual amount.

### The test-shape audit (standing check)

**The suite is constrained from below and never from above.** 85 green tests over pure money logic
is a real asset — and it is also exactly the shape that hides an invention. The check:

- Every money invariant in `references/domain-accuracy.md` must be pinned by an **exact** assertion
  (shares sum to the total, to the cent) rather than a bound or a spot-check. An invariant with no
  exact-set test **cannot fail on a rounding regression**.
- Every split type × every currency path needs at least one case. A split type with no test is not
  covered by "85 tests pass."
- There are **no component and no E2E tests**. That is a stated repo fact, not a discovery — the
  finding worth filing is *which specific money-bearing UI path* is therefore unpinned.

### Phase 2E: Adversarial Freeloader

Tries to make the app **lie about who owes what**. Highest-value attacks:

- Enter an expense in a currency with no rate (`JPY`, `THB`, `CHF`) and see whether it is silently
  converted 1:1 against USD. **A wrong FX conversion is money invented from nothing** — `critical`.
- Set one participant's weight to `0` and confirm they are charged nothing, in every split type.
- Make the exact-split weights sum to something other than the total, and see who eats the delta.
- Split $0.01 three ways; split $100 three ways; check the pennies over 20 expenses.
- Record a payment larger than the debt; record a payment to yourself; record a negative payment.
- Reorder trips (or add a second trip) and see whether cross-trip balances change — an order-
  dependent ledger invents mutual debts.
- Settle up, then edit the underlying expense. Does the balance re-open honestly, or does the app
  keep claiming settled?
- Accept an invite token twice; accept an expired one; open a `trip-preview` token for a trip
  you were removed from.
- Push the app past localStorage quota with a large receipt image and see whether the save is
  honest about failing.

**Run auth/rate-limit chaos LAST**, after every browser persona has finished — the in-memory
limiter is per-instance and shared with the personas' own requests.

---

## Phase 3: Report

Write to `docs/reports/user-test-reports/user-test-<YYYYMMDD-HHMMSS>.md` using
`references/report-template.md`. Mandatory SplitSquad sections:

- **Verdict** — would a group run a real trip on this? What's the ceiling, what's blocking it?
- **The two scores, separately** — Product UX /10, Money Integrity /10. If UX is high and Money is
  low, that contrast IS the headline. Write it as the headline.
- **The reconciliation** — the corpus trip, its inputs, the app's displayed numbers, the hand
  derivation, and the delta. Per number: TRUST IT / RECONCILE BY HAND / WOULD START A FIGHT.
- **Conservation result** — for every split type exercised: did shares sum to the total, to the
  cent? State it even when the answer is yes. A confirmed negative is worth recording.
- **Currency provenance** — which rates were live vs static fallback, which codes had no rate at
  all, and what the app did about it.
- **Settle-up audit** — does executing the plan leave every member at zero? How many transfers,
  and is the plan deterministic across reloads?
- **Panel confidence** — the calibration false-negative rate and the date measured. If overdue, say
  so **in the verdict**: an unmeasured panel cannot claim a clean report is clean.
- **Domain accuracy findings** — each with a citation. Ungrounded → `[UNVERIFIED]`, not a defect.
- **Coverage ledger** — which personas and experts ran, which were skipped, last-covered date for
  each of the ten experts (`NEVER` for unaudited), plus any surface with no persona owner.
- **Status vs. prior baseline** — FIXED / STILL_PRESENT / REGRESSED.
- **Competitor delta** — vs Splitwise, Tricount, Settle Up, Splid (see `research/competitive/
  landscape.md`). What would make a group switch, and what would make them not?
- **Suppressed by prior learnings** — the false-positive footnote.

Then write `baseline.json` (schema in the report template) and prepend a run block to
`docs/reports/user-test-reports/learnings.md`, keeping a rolling 5-run window.

### `learnings.md` hygiene

1. **Ledgers first.** Expert ledger, persona ledger, calibration slot, next-run priorities — before
   any narrative. Everything Phase 0 needs to *route* the run must be readable without scrolling.
2. **Promote, don't accumulate.** A durable environment fact moves to `harness.md` (edited in
   place); a settled non-bug to the suppression list; a corrected money fact into
   `domain-accuracy.md`. Then **delete it from the run block.**
3. **Compress a Phase 5 block once the next run confirms the fixes survived** (Phase 0.8). Keep the
   `file:line` inventory and `regression-risk` notes; cut the narrative.

**Target: under ~200 lines.** Over that with a 5-run window means the run blocks are too long, not
the window too wide.

---

## Phase 4: Finish — findings must LEAVE this loop

| Disposition | Meaning |
|---|---|
| `FIX-NOW` | Blocks the core loop, or the app is wrong about money. Offer Phase 5. |
| `BACKLOG` | Real, not blocking. Written into `learnings.md` open findings. |
| `TEST-GAP` | The math is right but nothing pins it. Route to a test, not a code change. |
| `FALSE-POSITIVE` | Verified not a bug. Written to the suppression list with the reason. |
| `UNVERIFIED` | Could not be grounded. Named, but not scored. |
| `MODE-BOUNDARY` | Honest limitation of localStorage / no-Stripe / no-DB mode. Not a defect. |

A finding with no disposition is a bug in this skill's run, not a finding.

---

## Phase 5: Offer to implement

Ask before touching anything.

1. Fix `FIX-NOW` items first, atomically, one concern per commit.
2. **A money fix ships in TWO places or it isn't done**: the canonical function in `src/utils/`
   **and** a test in `src/utils/__tests__/` that would have caught it. A money change with no new
   test is not a fix, it is a different set of numbers.
3. Gates must pass: `npm test`, `npm run lint`, `npm run build`.
4. Re-verify in the running app, not just in tests — the bug the user feels is the *displayed*
   number.
5. Record what you changed in `learnings.md` as a `regression-risk` note for the next run.

---

## Operating Principles

- **The reconciliation is the point.** If a run produces no hand-derived numbers to compare
  against, it failed — go back and build a trip, even by hand-driving the expense form.
- **Cap the run when the trunk is broken.** Ten experts describing the same wall is waste.
- **Suppress what's already settled.** Don't re-litigate documented mode boundaries (`/api/
  settlements` is a stub; the DB layer is additive; the SWR fetcher returns empty on error).
- **Rounding noise is not a bug — until it accumulates.** One cent on one expense is float
  behavior. One cent that survives into the settle-up plan and never clears is a real defect. The
  threshold rules are in `references/scoring-and-evidence.md`; apply them before flagging.
- **This skill compounds — but only if debts become RULES.** The invariant table, the two ledgers,
  the suppression list, and the harness facts are the assets. Every run should leave them sharper.
- **A debt that is only recorded is not a protocol.** If this run discovers a new recurring debt,
  encode it as a Phase 0 check — do not append a reminder.
- **Prefer cutting to adding.** These files are read by agents under load. When a section stops
  earning its length, delete it.
