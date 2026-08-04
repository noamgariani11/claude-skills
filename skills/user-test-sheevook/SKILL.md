---
name: user-test-sheevook
description: |
  Sheevook-specialized marketing testing. A senior expert panel - fractional CMO, growth/virality
  strategist, performance media buyer, brand-positioning strategist, analytics & attribution lead,
  and community manager - plus a rotating bench of fifteen platform practitioners (X, LinkedIn,
  Instagram, TikTok, Facebook, YouTube, Reddit, Threads, Bluesky, Discord, Telegram, Pinterest,
  Snapchat, Tumblr, Hacker News) who each know their own platform's organic algorithm AND its ads
  manager for real. Tests the core loop (create -> tailor
  -> approve -> schedule -> publish -> analyze), ad campaign building, the analytics learning loop,
  the community reply queue, CSV import/export, and journey-stage placement. Scores TWO things:
  the product UX, and - unique to this skill -
  the marketing artifacts the app actually generates (would this post perform? would this get
  removed by a mod? is this ad set structured like a real buyer would build it? is any claim in it
  fabricated?). Includes
  domain-accuracy auditing of `lib/tailoring/platforms.ts`, `lib/ads/formats.ts`, and
  `lib/ads/networks.ts` against `research/` and live platform docs, plus planted-defect
  calibration that measures what the panel MISSES. Each persona runs as an
  isolated Agent subprocess. Use when you want "would a real marketing team run their launch on
  this, and would the content it made actually work?" - not generic UX.
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

# /user-test-sheevook — Sheevook Marketing Expert Testing

This skill answers: **"Would a senior marketing team trust Sheevook to run their launch — and
would the content it produced actually perform?"**

Sheevook's value is not its UI. It is the *artifact*: a tailored post, a Reddit comment that
won't get removed, an ad campaign a media buyer would recognize. A generic user test can tell you
the Composer's empty state is weak. It cannot tell you the X hard limit is wrong, the Reddit
variant reads like an ad, or the Meta campaign has no objective a buyer would ever pick.

So this skill scores **two axes**, and reports them separately:

| Axis | Question | Judged by |
|---|---|---|
| **Product UX** (/10) | Can a marketer actually do their job in this app? | Strategy panel |
| **Marketing Output Quality** (/10) | Would what it generated actually perform? | Platform experts + Virality |

**A run can pass UX and fail Output. That is a valid and important verdict — say it loudly.**

Load references on demand. Do not read them all at once.

| When you need | Load |
|---|---|
| The six strategy-panel persona cards (A–F), data lanes, diversity rules | `references/personas.md` |
| The fifteen platform-expert cards, rotation rules, per-platform checklists | `references/platform-experts.md` |
| Ground-truth tables + the anti-hallucination citation rule (**read before any accuracy claim**) | `references/domain-accuracy.md` |
| How to judge a generated post / ad — the output rubric | `references/output-quality.md` |
| Critical workflow protocols (core loop, ads, analytics, community, connections) | `references/workflows.md` |
| Environment + harness facts (ports, login, seed, rate-limit trap, Chromium) | `references/harness.md` |
| Confidence tags, score gating, false-positive guardrails | `references/scoring-and-evidence.md` |
| Persona internal-reasoning format | `references/chain-of-thought.md` |
| Report shape | `references/report-template.md` |
| Planted-defect calibration — measuring what the panel MISSES (every 5th run, or `--calibrate`) | `references/calibration.md` |

---

## Core Philosophy

1. **Grade the output, not just the app.** Every run must quote at least one artifact the app
   actually generated and render a verdict on it. A report with no content autopsy did not run
   this skill.
2. **Experts, not archetypes.** These personas have done the job. They use real vocabulary
   (CPM, hook rate, thumbstop, karma, shadowban, PMax, Advantage+) and they have priors about
   what works. They are not "a user who is a bit technical."
3. **Cite or shut up.** A platform expert asserting "X's limit is 280" from memory is exactly as
   dangerous as the app being wrong. Every domain-accuracy finding cites the ground-truth table,
   a `research/` doc, or a live `WebFetch`. Ungrounded claims are `[UNVERIFIED]` and cannot be
   scored as defects. See `references/domain-accuracy.md`.
4. **Know which brain is running.** With `ANTHROPIC_API_KEY` unset the app emits *deterministic
   rule-based* output by design (CLAUDE.md: "the app works with NO API key"). Judging fallback
   output as "AI slop" is an invalid finding. Every run states which mode it observed.
5. **Honest failure is not a bug.** Publishing genuinely requires a live OAuth connection, and
   the app refuses to fake success (CLAUDE.md). A connect-wall is a *product boundary*, not
   brokenness. Do not score it as a defect. Do score a confusing or dishonest one.
6. **The report is for a marketer, not a QA lead.** Lead with the verdict and the content
   autopsy. The bug table is supporting evidence.

---

## Phase 0: Prep

### 0.1 — Parse mode

| Flag | Behavior |
|---|---|
| *(none)* | `full` — strategy panel + rotated platform experts + technical + adversarial |
| `--diff` | Personas scoped to surfaces the working tree / recent commits touched. Pre-push mode. |
| `--focus <surface>` | e.g. `--focus ads` — surgical depth on one surface |
| `--platform x,reddit` | Force specific platform experts (overrides rotation) |
| `--output-only` | Skip UX personas entirely. Generate artifacts, judge them. Cheap + fast. |
| `--calibrate` | Plant 5 defects on a throwaway branch, run normally, measure what the panel MISSED. See `references/calibration.md`. Run every 5th run — a skill that never measures its false-negative rate cannot be trusted when it reports "no critical findings". |

### 0.2 — Detect the URL and verify it is actually Sheevook

Never trust the first port that answers — this box routinely runs several apps, Sheevook has
served on 3000/3001/3005 at different times, and it **moves mid-run**. Run the canonical port
scan in `references/harness.md` ("Never trust the first port that answers"), which is the single
maintained copy of the scan list, and **re-check the port during long runs, not just at the
start**.

The served `<title>` must read **Sheevook**. If no local server is up, offer to start one
(`pnpm dev`), or accept a remote/Vercel URL as an argument.

### 0.3 — Concurrent-session + DB safety check

Sibling `claude` sessions edit this repo live and have reseeded the DB mid-run before, invalidating
the personas' login. Before anything else:

```bash
# Who else is in this repo?
for pid in $(pgrep -x claude); do printf '%s -> ' "$pid"; readlink /proc/$pid/cwd; done
stat -c '%y %n' .data/marketing.db 2>/dev/null
```

If a sibling session owns this working tree, run **read-only on code** (no Phase 5 edits) and say
so in the report's environment note. Snapshot the DB mtime; if it changes mid-run, the personas'
account may have been destroyed — re-check before trusting a login failure as a bug.

### 0.4 — Auth wall + first-run state

Sheevook ships **no demo data**. A fresh workspace opens on onboarding and the core loop cannot be
tested without an account. Determine which state you're in:

- **Empty / no account** → `/setup` creates the single account. The first persona through creates
  it; everyone else logs in. Note the account + brand as run residue.
- **Existing account** → you need credentials. If a sibling session owns the account, do **not**
  reseed. Mint a session instead (see `references/harness.md`).

`pnpm seed` is the only reset and it **destroys the existing account**. Never run it without
asking the user first.

### 0.5 — Which brain is running

```bash
# Deterministic fallback, or real AI?
[ -n "$ANTHROPIC_API_KEY" ] && echo "AI: live" || echo "AI: deterministic fallback"
grep -rn "gate\|cache" lib/ai/gate.ts | head -3
```

Record this in `baseline.json` as `ai_layer`. It changes how output quality is judged — see
`references/output-quality.md`, "Judging fallback output".

### 0.6 — Route + surface + PLATFORM ROSTER discovery

```bash
find app -name page.tsx | sed 's|/page.tsx||' | sort

# The platform roster is derived from CODE, never from a reference file's count.
grep -nE '^  [a-z]+: \{' lib/tailoring/platforms.ts | sed 's/:.*//;s/^ *//'
ls research/platforms/*.md
```

Map surfaces to persona ownership (`references/personas.md` → focus routing).

**Reconcile the roster three ways** — `platforms.ts` keys ↔ expert cards in
`references/platform-experts.md` ↔ the ledger in `learnings.md`. This file has claimed "twelve
platforms" while the code shipped 13 and then 15, and **a platform with no expert card cannot be
rotated to, so its rule block is never audited** — Bluesky went six runs that way. Any mismatch is
a `medium` finding in its own right, and the missing card gets written before the next run.

### 0.7 — Baseline + learnings

```bash
ls docs/reports/marketing-test-reports/            # this skill's own store
cat docs/reports/marketing-test-reports/baseline.json 2>/dev/null
cat docs/reports/marketing-test-reports/learnings.md 2>/dev/null
```

First run: no baseline — say so and establish one. Otherwise load:
- the **verified-false-positive** list (suppress or re-prove; never silently re-flag)
- the **platform coverage ledger** (which experts ran when → drives rotation)
- the **persona ledger** (which of A–F ran when → drives Phase 1; see below)
- the **open findings** (drives the Status-vs-Prior-Baseline table)
- the **calibration slot** (see below — this one can convert the whole run)

Also read `docs/reports/user-test-reports/learnings.md` **read-only** — the generic `/user-test`
skill has already paid for harness lore (rate-limit trap, login selector, tour false positive).
Do not re-learn what it already knows. Do not write there.

**Calibration debt is blocking.** If the ledger shows calibration due or overdue (every 5th run),
**this run converts to `--calibrate`** unless the user explicitly declines. It has now been owed
across three due slots while every report dutifully recorded that it was owed — a debt that is
only ever recorded is not a protocol. If the user declines, the report's verdict must state that
the panel's false-negative rate is unmeasured. See `references/calibration.md`.

**Carry EVIDENCE, not prose — this went wrong two runs running.** A prior run's *conclusion*
briefed as fact has twice been false (`ORG-BENCH-UNTESTED` was briefed as "no test covers the
module"; two suites did). Both times the technical reviewer caught the coordinator.

- An open finding carried into a persona brief must carry its **file:line evidence** from the
  prior report, not its summary sentence.
- A `STILL_PRESENT` claim must be **re-proven this run** before it appears in the report. If it
  cannot be re-proven, it is `UNVERIFIED`, not `STILL_PRESENT`.
- Where a brief states a diagnosis ("the fixtures never get the crawler shape"), mark it as the
  prior run's **hypothesis**, so the agent tests it rather than inheriting it.

### 0.8 — Change delta (drives rotation and `--diff`)

```bash
git diff --stat HEAD                                   # uncommitted (runs often test a dirty tree)
git log --oneline -15
git diff --name-only HEAD -- lib/tailoring lib/ads lib/analytics lib/voice
```

Platform files touched → those platform experts get priority in the rotation.

### 0.9 — Fix-survival check (do this BEFORE anyone scores anything)

**Every Phase 5 in this skill's history has ended uncommitted**, layered on top of sibling
sessions' work, and every learnings block closes with some version of *"if the next run finds
these missing, they were lost to a sibling checkout, not un-done."* That instruction has never
been turned into a step. It is one now.

Read the prior run's `post_run_implementation.fixed` inventory from `baseline.json` (it records
file:line for each fix) and **spot-check that each fix is still physically present**:

```bash
cat docs/reports/marketing-test-reports/baseline.json | grep -A40 post_run_implementation
git log --oneline -8            # did a sibling commit or revert over them?
git status --short | head -30
```

Then classify the run's starting state and **say which in the report's environment note**:

| State | Meaning | Consequence |
|---|---|---|
| **Fixes present** | Normal. Score against them. | Findings they closed should read `FIXED`. |
| **Fixes missing** | Lost to a sibling `checkout`/reseed — **not a product regression.** | Re-apply from the inventory (or note them as lost). **Do NOT file them as `REGRESSED`.** |

This distinction is the whole point: a lost fix and a regressed fix look identical from the UI,
and mislabelling the first as the second manufactures a phantom regression, sends a persona to
re-find a solved bug, and corrupts the trend line the baseline exists to carry.

---

## Phase 1: Panel Selection

**Tier 1 — Strategy panel (all six, every run except `--output-only`):**
A Senior Marketer/CMO · B Growth & Virality · C Performance Media Buyer · D Brand & Positioning ·
E Analytics & Attribution · F Community Manager. Cards in `references/personas.md`.

> **Personas get a ledger too, and an owed persona is MANDATORY.** "All six every run" was the
> rule, and D was still silently dropped at run #16 — surfacing only as a prose note ("Persona D
> NOT fielded, owed"), which is the same failure mode as the calibration debt and the Bluesky gap.
> Keep a persona ledger in `learnings.md` alongside the platform one:
>
> ```
> ## Persona ledger
> A: 2026-07-18 | B: 2026-07-18 | C: 2026-07-18 | D: 2026-07-15 (OWED) | E: 2026-07-18 | F: 2026-07-18
> ```
>
> A persona not fielded last run **runs this run before any optional work**, and any drop is
> stated in the report with its reason. D is the most-dropped because her data lane forces her to
> run alone — that constraint is a scheduling cost, not a licence to skip her, and her two
> signature tests (the **overwrite test** and the **consistency test**) are the only coverage of
> a `critical`-severity promise: discovery proposes and never overwrites.

**Tier 2 — Platform experts (3–4 per run):** pick by, in order:
1. `--platform` if given (overrides everything).
2. Platforms whose rules/adapters the diff touched (Phase 0.8).
3. **Any platform reading `NEVER`** — unmeasured beats merely stale; at least one slot per run
   goes here while any exists.
4. Staleness — longest since last covered, per the ledger in `learnings.md`.

Round-robin so all fifteen are covered within ~5 runs. **Every skipped platform is named in the
report with its last-covered date.** No silent coverage gaps.

**Tier 3 — Closers (every run):** Technical Reviewer, Adversarial Marketer.

### Data lanes — parallel personas must not corrupt each other's reality

Personas run concurrently against ONE SQLite DB and ONE brand. Without lanes they overwrite each
other's drafts and then report the damage as bugs.

- Each persona works **only** on content it created, prefixed with its own tag
  (`[A]`, `[B]`, …) in the title/body so ownership is greppable.
- Nobody deletes anything they did not create. Nobody edits brand settings except **D**
  (whose entire job is brand settings) — D therefore runs **alone**, after the others, or the
  others must treat mid-run brand changes as expected, not as a bug.
- Nobody runs `pnpm seed`. Ever. Mid-run reseeds have destroyed two prior runs.
- Connections/OAuth state is global: only **E** touches `/platforms` connect flows.

---

## Phase 2A: Senior Marketer first — breadth + gate

Persona **A** runs alone, first, as an isolated `Agent`. She creates the account if needed, sets up
the brand, and drives the whole core loop for a real launch. She is the gate.

**Gate rule (mandatory after A returns):**

- If A could **not complete the core loop** (create → tailor → approve → schedule) for reasons
  that are not an honest external prerequisite (OAuth connection), the product is broken at the
  trunk. **Stop.** Do not field ten more agents to re-discover the same wall. Report A's finding,
  the blocker, and the fix. A capped run is a cheap run.
- If A completed it, the artifacts she generated become **the corpus the platform experts judge**
  in Phase 2C. Capture them verbatim (see `references/output-quality.md`).

Then recalibrate: **never send a persona at a wall you have already decided to build.** If A found
that ads require a live Meta connection nobody has, C's goal becomes "evaluate the campaign
*builder* and the structure it produces," not "launch a campaign."

---

## Phase 2B: Remaining strategy panel (isolated agents, in parallel)

B, C, D, E, F run as isolated `Agent` subprocesses, in parallel, each with its card, its lane, its
goal, and its success criteria. They share no state and must not see each other's findings — that
independence is the whole point of the panel.

Each returns: session narrative with `THINKING:` blocks, PULSE readings, tagged findings, task
completion (Full/Partial/Failed), score with the gating rule applied, and — for B — an output
verdict on every artifact it saw.

---

## Phase 2C: Platform experts (isolated agents, in parallel)

Each selected platform expert does **three jobs**, in this order:

1. **Organic ground truth.** Audit their platform's block in `lib/tailoring/platforms.ts`
   (hardLimit, sweetSpot, hashtags, links, hookWindow, rankingSignals, contentFormats, cadence,
   contentBlueprint, writerPersona, mediaSpec) against `research/platforms/<platform>.md` and the
   ground-truth table. **Drift between code and research is a finding by definition** — CLAUDE.md
   definition-of-done #4 requires them to match, and so does `tests/tailoring.test.ts`.
2. **Ads ground truth** (where the network exists in `lib/ads/networks.ts`): are the campaign
   types and ad formats in `lib/ads/formats.ts` real ones a buyer would actually see in that ads
   manager? Wrong/invented objectives are a high-severity trust defect.
3. **Output judgment.** Take the variant the app *actually produced* for their platform (Phase 2A
   corpus) and rule on it: **POST IT / REWRITE / WOULD BE REMOVED.** Quote the artifact verbatim.
   Rubric in `references/output-quality.md` — **including dimension 6, veracity**: check every
   statistic, anecdote, testimonial, and URL against the master, `brand.facts`, and
   `brand.valueProps`. A fabrication caps the artifact at REWRITE and 4/10 regardless of craft,
   and on Reddit or Hacker News it is WOULD BE REMOVED and `critical`. Report separately whether
   the app's own lenses caught it.

An expert who only reviewed the UI and skipped jobs 1–3 has not done the work. Reject and re-run.

---

## Phase 2D: Technical Reviewer

Not a persona — a code reviewer with marketing context. Checks:

- **Repository boundary**: SQL only in `lib/db/repositories/*`; routes/components never raw SQL.
- **Auth gating**: every new `app/api/*` route uses `handler()`; `{ public: true }` only on
  `/api/auth/*`, `/api/cron/*`, `/api/attribution`. Pages behind `requireAuth()`.
- **Project scoping**: id-addressed mutations resolve `brandId` and reject cross-project access.
  (This was `STILL_PRESENT` for two `/user-test` runs — verify it.)
- **AI honesty**: every AI call has a deterministic fallback; no path breaks without a key.
- **Publishing honesty**: no hardcoded "posted!", no invented metrics, tokens server-only
  (`PublicConnection`).
- **Tailoring purity**: `lib/tailoring` takes data in, returns data out — no I/O.
- **Discovery grounding**: discovery reaches AI calls **only** via `brandContext()`
  (`lib/discovery/context.ts`). A surface that wires discovery in by hand is an architecture
  finding. Verify the deterministic-first claim: crawl/extract/classify/local/norms are pure and
  free, with at most **two** AI calls that only *refine*.
- **Lens purity**: `lib/conversion`, `lib/geo`, `lib/voice`, `lib/stress-test` are pure and
  zero-AI-cost. An AI call hiding in a "free" lens is a cost regression — see the repo's
  cost-minimization rule (gate + cache every AI call via `lib/ai/gate.ts`).
- **Workspace authz** (newer than most of this checklist): `lib/workspace` resolves session user →
  workspace + role; owner/admin gates guard the sharp surfaces (admin monitor, billing, member
  management). Per-user `sessionVersion` revocation must revoke **one** user's cookies, not
  everyone's. Cross-workspace access is **404, never 403**.
- **AI disclosure carry**: `MediaAsset.aiGenerated` must survive to publish via
  `lib/publishing/media-link.ts` and must never be stripped. **Known gap — do not report it as
  fixed:** the flag is only actually *transmitted* to TikTok (`post_info.is_aigc`). A claim that
  disclosure is discharged because the column is populated is **wrong**; EU AI Act Art. 50 applies
  from 2026-08-02.

### The test-shape audit (standing check — recurring across three runs)

**The suite is constrained from below and never from above: it polices omissions and is blind to
inventions — the higher-severity class.** Calibration proved it: a planted fake ad objective passed
**56/56**, a planted LinkedIn `hardLimit` drift passed **1263/1264**. The mechanism is the
assertion *shape*: a `toContain` **subset** check means a test named *"meta spans the full ODAX
objective lineup"* **is satisfied by eight entries** — which is why Pinterest's 3-of-5 objectives
survive, **the test protects the defect**.

**The check:** every registry-shaped table (`formats.ts` objectives, `platforms.ts` limits) must
be pinned by an **exact-set** assertion, not a subset. A subset-shaped assertion over a registry
is `high`: it **cannot fail on an invention**. Not "add more tests" — same-shape tests change
nothing.

### Phase 2E: Adversarial Marketer

Tries to make the app *lie to a marketer*. Highest-value attacks:

- **Make workspace discovery invent a fact.** Point `lib/discovery` at a sparse, near-empty, or
  parked domain and see whether it fills the vacuum with a confident brand profile. CLAUDE.md's
  non-negotiable is that it **never invents a fact, price, quote, or competitor**. A fabricated
  fact here is `critical` and propagates into *every* AI call via `brandContext()` — it is the
  single most damaging failure the product can have. Full protocol in `workflows.md` Workflow 8.
- Publish to a platform with no connection — does it fake success or fail honestly?
- Push an unapproved/rejected variant to `published`.
- Get a fabricated metric out of `/analytics` (a number the platform API never returned).
- Schedule into the past; schedule two posts into the same slot; corrupt a posting window.
- Make the tailoring engine emit content that violates its own `validate()` rules.
- Get one project's content into another project's campaign.

**Run auth/rate-limit chaos LAST.** `lib/rate-limit.ts` keys all of localhost to
`clientKey="local"`, so adversarial curls throttle the browser personas' logins — a prior run
self-DoS'd this exact way.

---

## Phase 3: Report

Write to `docs/reports/marketing-test-reports/marketing-test-<YYYYMMDD-HHMMSS>.md` using
`references/report-template.md`. Mandatory Sheevook sections:

- **Verdict** — would a marketing team run their launch on this? What's the ceiling, what's
  blocking it?
- **The two scores, separately** — Product UX /10, Marketing Output Quality /10. If UX is high and
  Output is low, that contrast IS the headline. Write it as the headline.
- **Content autopsy** — the generated artifacts, verbatim, each with its platform expert's
  POST IT / REWRITE / WOULD BE REMOVED ruling and the reason.
- **Veracity result** — for every artifact: was any claim fabricated, and **did the app's own
  lenses catch it?** State the second even when the answer is "nothing to catch." An artifact that
  is clean and a detector that is blind are different facts, and only the first is good news.
- **Panel confidence** — the calibration false-negative rate and the date it was measured. If
  overdue, say so **in the verdict**: an unmeasured panel cannot claim a clean report is clean.
- **Domain accuracy findings** — wrong limit, wrong format, invented ad objective, code↔research
  drift. Each with a citation. Ungrounded → `[UNVERIFIED]`, not a defect.
- **Platform coverage ledger** — who ran, who was skipped, last-covered date for each of the
  fifteen (`NEVER` for unaudited), plus the persona ledger and any platform with no expert card.
- **Status vs. prior baseline** — FIXED / STILL_PRESENT / REGRESSED.
- **Competitor delta** — vs Buffer, Hootsuite, Later, Typefully, AdCreative.ai. What would make a
  marketer switch, and what would make them not?
- **Suppressed by prior learnings** — the false-positive footnote.

Then write `baseline.json` (schema in the report template) and prepend a run block to
`docs/reports/marketing-test-reports/learnings.md`, keeping a rolling 5-run window. Update the
platform coverage ledger **and the persona ledger** there.

### `learnings.md` hygiene — an unread ledger is why three debts went unpaid

The file grew to ~385 lines / ~30k tokens under a nominal "rolling 5-run window," because Phase 5
blocks accreted *alongside* run blocks and nothing was ever promoted out. **Bluesky sat at `NEVER`
for six runs, persona D went unfielded, and calibration was skipped three times — every one of
them faithfully recorded, far down a file nobody finished.** `calibration.md` names this decay
mode exactly: fix it *by cutting, not by adding*. It was restructured on 2026-07-19; keep it that
way with three rules, applied every run:

1. **Ledgers first.** Platform ledger, persona ledger, calibration slot, next-run priorities —
   before any narrative. Everything Phase 0 needs to *route* the run must be readable without
   scrolling.
2. **Promote, don't accumulate.** A durable environment fact moves to `harness.md` (edited in
   place); a settled non-bug to the suppression list; a corrected platform fact into the expert
   card. Then **delete it from the run block.** This file is for what *changed*, not what *is*.
3. **Compress a Phase 5 block once the next run confirms the fixes survived** (Phase 0.9). Keep
   the file:line inventory and `regression-risk` notes — still needed to re-apply after a sibling
   checkout — and cut the narrative. The full report is always on disk; nothing is lost by cutting.

**Target: under ~200 lines.** Over that with a 5-run window means the run blocks are too long, not
the window too wide.

---

## Phase 4: Finish — findings must LEAVE this loop

Every finding gets a forced disposition. Nothing is allowed to sit in the report unrouted:

| Disposition | Meaning |
|---|---|
| `FIX-NOW` | Blocks the core loop or the app lies to the user. Offer Phase 5. |
| `BACKLOG` | Real, not blocking. Written into `learnings.md` open findings. |
| `RESEARCH-DRIFT` | Code and `research/*.md` disagree. Route to whichever is wrong — **both** files must end up in sync (definition-of-done #4). |
| `FALSE-POSITIVE` | Verified not a bug. Written to the suppression list with the reason. |
| `UNVERIFIED` | Could not be grounded. Named, but not scored. |
| `PRODUCT-BOUNDARY` | Honest limitation (OAuth wall). Not a defect. Recorded so it isn't re-flagged. |

A finding with no disposition is a bug in this skill's run, not a finding.

---

## Phase 5: Offer to implement

Ask before touching anything. If a sibling `claude` session owns the tree (Phase 0.3), **decline**
and say why — interleaved edits have produced broken files here before.

If accepted:

1. Fix `FIX-NOW` items first, atomically, one concern per commit.
2. **A tailoring/platform rule fix ships in THREE places or it isn't done**:
   `lib/tailoring/platforms.ts` + `research/platforms/<platform>.md` + `tests/tailoring.test.ts`.
   This is CLAUDE.md's definition-of-done #4 and the reason drift keeps recurring.
3. Gates must pass: `pnpm build`, `pnpm lint`, `pnpm test`.
4. Re-verify in the running app, not just in tests.
5. Record what you changed in `learnings.md` as a `regression-risk` note for the next run.

---

## Operating Principles

- **The corpus is the point.** If a run produces no generated artifacts to judge, it failed —
  go back and produce some, even by hand-driving the Composer.
- **Suppress what's already settled.** Plaintext OAuth tokens (by design), bad-slug 302,
  Composer preselecting all platforms — all verified false positives. Don't re-litigate them.
- **Deterministic ≠ bad.** A prior run found the rule-based tailoring genuinely good. That's a
  finding worth keeping, not a caveat.
- **Cap the run when the trunk is broken.** Ten experts describing the same wall is waste.
- **This skill compounds — but only if debts become RULES.** The ground-truth table, the two
  ledgers, the suppression list, and the harness facts are the assets. Every run should leave them
  sharper than it found them.
- **A debt that is only recorded is not a protocol.** Three separate assets decayed the same way:
  Bluesky sat at `NEVER` for six runs, persona D went unfielded, and calibration was skipped
  across three due slots — each one faithfully written down, in prose, in a part of a growing file
  nobody reached. **The fix is never a better note; it is a gate in Phase 0 and a shorter file.**
  If this run discovers a new recurring debt, encode it as a Phase 0 check, do not append a
  reminder.
- **Prefer cutting to adding.** These reference files are read by agents under load. When a
  section stops earning its length, delete it — `calibration.md` records that a rising
  false-negative rate usually means a file grew past the point where agents finish it.
