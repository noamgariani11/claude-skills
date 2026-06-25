---
name: user-test-miskari
description: |
  Miskari-specialized user testing. Six domain-expert personas — commercial property
  manager, tax protest specialist, residential landlord, passive investor, small business
  owner, and property accountant — each with real CRE vocabulary and professional
  skepticism. Tests the critical real-estate workflows (protest end-to-end, property
  onboarding, lease renewal, vendor radar, bank reconciliation, portfolio dashboard)
  against what a paying professional would actually expect. Includes domain accuracy
  checks (is the NOI math right? do the comps match DCAD? is the cap rate credible?),
  comparison to competitor tools (AppFolio, Buildium, Yardi, Excel), expert feature-gap
  capture, tax-season-aware priority adjustment, and a professional verdict decision
  matrix. Each persona runs as an isolated Agent subprocess. Use when you want
  "would a real property manager pay for this?" signal, not generic UX.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
  - Agent
---

# /user-test-miskari — Miskari Property Management Expert Testing

This skill answers: **"Would a working commercial real estate professional trust and pay for Miskari?"** It tests the product through the lens of people who already know what NOI is, have filed DCAD protests before, and will immediately notice if the $/sqft math is wrong.

Load specialized references from `references/` on demand. Do not read all at once.

| When you need | Load |
|---|---|
| All six persona cards + diversity rules + focus routing | `references/personas.md` |
| Critical workflow protocols + domain accuracy checks | `references/workflows.md` |
| Domain trust signals, competitor comparisons, professional skepticism triggers | `references/domain-trust.md` |
| Score calibration, evidence rules, confidence tagging, cognitive load | `/home/drago/.claude/skills/user-test/references/scoring-and-evidence.md` |
| Chain of Thought format, PULSE | `/home/drago/.claude/skills/user-test/references/chain-of-thought.md` |
| Report template, in-chat summary, engineering action items | `/home/drago/.claude/skills/user-test/references/report-template.md` |
| Browser commands (Playwright / gstack), baseline schema | `/home/drago/.claude/skills/user-test/references/interaction-protocols.md` |

---

## Core Philosophy

**The customer is the center of everything Miskari does.** The goal is not to find bugs. The goal is to understand what a paying professional actually thinks, needs, and would use every day — and to surface that insight fast enough to drive real product improvements.

The persona's domain expertise is the point. A 15-year commercial property manager will catch things no generic UX tester ever could: the wrong protest deadline, the missing $/sqft source date, the NOI that doesn't explain what moved. These observations are gold. The skill's job is to amplify that signal and translate it into specific, actionable improvements.

**What this skill produces:**
- Direct feedback a working professional would give — unfiltered through generic UX heuristics
- Domain-specific catches that only someone with field experience would notice
- Feature gaps: things the professional expected to exist that don't
- A clear, reproducible verdict: "would a professional pay for this?" with defined criteria
- Findings prioritized by customer impact, not technical severity

Operating principles:
- **Professional skepticism is the baseline.** These users spot a wrong cap rate, stale comps, or a missing protest deadline immediately. Trust is harder to earn from a professional than from a consumer.
- **Domain accuracy > aesthetic polish.** A pixel-perfect UI with wrong NOI loses. An unremarkable UI with accurate, labeled, timely data wins.
- **Every finding maps to a customer impact.** Not "button is hard to find" but "a property manager would miss their protest deadline because this isn't visible."
- **Feature gaps are findings too.** When an expert says "I expected to be able to do X here" — that's a product gap, as important as any bug.
- **Competitor pressure is constant.** Every persona has a mental benchmark — AppFolio, Buildium, Yardi Breeze, or their own Excel model. "Better than my spreadsheet" is the minimum bar.
- **Workflow continuity matters.** Real estate workflows span days or weeks. A tool that breaks mid-flow or loses state is worse than no tool.
- **Show your sources.** Professionals need provenance. "As of DCAD 2025 roll" is credible. An unlabeled number is suspicious.
- **The phone call test.** If it takes less effort to make a phone call than to find the answer in Miskari, Miskari lost.
- **Improvements should be rapid and high-value.** The report's customer-impact table is the primary engineering deliverable — make it specific enough to act on immediately.
- **Multi-tenant is non-negotiable.** Any cross-org data exposure is Critical, always.

---

## Phase 0: Prep

### 0.1 — Infer mode

Same rules as `/user-test`. If a flag is passed (`--diff`, `--focus <page>`, `--flow <workflow-name>`), apply it. `--flow` is Miskari-specific: restrict testing to one of the six critical workflows (protest, onboarding, lease-renewal, vendor-radar, reconciliation, dashboard).

### 0.2 — Detect URL

```bash
for port in 3000 3001 4000 5173 8080; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port" 2>/dev/null)
  [ "$code" != "000" ] && echo "FOUND: http://localhost:$port" && break
done
```

Accept user-provided URL first. Fall back to dev server. If nothing resolves, tell the user to run `pnpm dev` or `pnpm start:dev` and stop.

### 0.3 — Tax season detection (adjusts P0 priorities for the run)

```bash
_MONTH=$(date +%m)
if [ "$_MONTH" -ge 1 ] && [ "$_MONTH" -le 5 ]; then
  echo "TAX_SEASON=true"
  _TAX_SEASON=true
else
  echo "TAX_SEASON=false"
  _TAX_SEASON=false
fi
```

**If `_TAX_SEASON=true`:** protest deadline accuracy is P0 for this run — it gates everything else. Any wrong deadline shown on a Texas property blocks the entire protest workflow for every professional who relies on it. The domain gate in Phase 2A automatically fails on a wrong deadline during tax season, regardless of other findings.

**If `_TAX_SEASON=false`:** protest deadline accuracy is still important but the primary P0 shifts to bill/lease deadline accuracy (the non-seasonal workflows dominate day-to-day use).

Log the season determination at the start of the run: `"Running in [tax season / off-season] mode — [month]. P0 priorities: [list]."`

### 0.4 — Auth wall + seed data check

```bash
curl -sI -L "$URL" 2>/dev/null | grep -Ei "^location:" | tail -1
curl -s "$URL" 2>/dev/null | grep -Ei "sign[ -]?in|log[ -]?in|please authenticate" | head -3
```

Miskari is always auth-gated. Ask the user for credentials. The default dev seed is `dev@example.com` / `devpassword` (org: "dev") — confirm whether to use those or a production-like dataset.

**Seed data quality check.** Domain-expert personas cannot meaningfully assess the protest workflow without real-looking assessment data, or the reconciliation flow without transactions. Before persona design, ask:
- Does the test environment have at least 3 properties with assessment records?
- Are there any active leases with upcoming renewals?
- Is the reconciliation view connected to Plaid (or has test transactions)?

If seed data is thin, note which workflows will be incomplete. Do not test the protest workflow against a portfolio with zero assessment records — that is a setup failure, not a product finding.

### 0.5 — Route discovery

```bash
find src/app -name "page.tsx" | sort
```

Key Miskari surfaces to verify exist before persona design:
- `/tax` (assessments/protests/opportunities/cap-rates)
- `/protests/[id]` (protest detail + operations)
- `/leases` and `/leases/renewals`
- `/contracts` (vendor contract renewal radar)
- `/reconcile` (bank reconciliation)
- `/reports` (portfolio analytics)
- `/dashboard`
- `/properties/[id]` (property detail with comps snapshot)

### 0.6 — Baseline check

```bash
ls -t .gstack/user-test-miskari-reports/baseline.json 2>/dev/null | head -1
ls -t .gstack/user-test-miskari-reports/learnings.md 2>/dev/null | head -1
```

Read both if present. Apply the same baseline/suppression/recurring-pattern logic as `/user-test` (details in `/home/drago/.claude/skills/user-test/SKILL.md` Phase 0.7).

### 0.7 — Setup output

```bash
mkdir -p .gstack/user-test-miskari-reports/screenshots
_DATE=$(date +%Y%m%d-%H%M%S)
_REPORT_FILE=".gstack/user-test-miskari-reports/miskari-${_DATE}.md"
```

---

## Phase 1: Persona Selection

Load `references/personas.md`. It defines six Miskari-specific personas.

### Selection rules

**Full mode (default):** Select 3 personas. Always include one from {Commercial PM (A), Tax Protest Specialist (B)}. Then pick the 2 remaining based on which features the current diff/focus touches.

**Diff mode (`--diff`):** Select 2 personas most relevant to the changed surface. If the diff touches `/tax` or `/protests`, always include B.

**Focus mode (`--focus <page>`):** Select the 2 personas from the routing table in `references/personas.md` § "Focus routing."

**Flow mode (`--flow <name>`):** Select the single most relevant persona for that workflow + A (Commercial PM) as a cross-check.

### Diversity check

- No two personas in the same run may share the same primary workflow
- At least one persona must be a "power user" who probes edge cases
- At least one persona must be a "trusting pragmatist" who just wants the task done

For each selected persona, define a **concrete GOAL** with binary success criteria tied to the relevant workflow in `references/workflows.md`. Print each persona card header (name, role, goal, viewport) before Phase 2. Do NOT print their private biography.

---

## Phase 2A: Domain Expert First — Breadth + Gate

Run the most experienced persona first (Commercial PM or Tax Protest Specialist when available). This is the Miskari equivalent of the Skimmer, but the gate is not "is the app loadable" — it is: **"Does the data look real to someone who has seen DCAD assessments before?"**

Run this persona as an **isolated Agent subprocess**. The agent receives only:
- The persona card from `references/personas.md`
- The app URL
- The GOAL with binary success criteria
- The workflow protocol from `references/workflows.md` for their assigned flow
- The domain skepticism triggers from `references/domain-trust.md`
- The scoring rules from `/home/drago/.claude/skills/user-test/references/scoring-and-evidence.md`
- The PULSE format from `/home/drago/.claude/skills/user-test/references/chain-of-thought.md`

The agent must NOT be given findings from prior agents or any other run context. Isolation is mandatory — cross-persona contamination defeats the purpose.

**Agent instructions for Phase 2A:**
1. Set viewport as defined in the persona card
2. Navigate to the persona's primary landing point (not always `/dashboard` — Marcus goes to `/tax`, James goes to `/reconcile`)
3. **Domain first-impression check:** Are numbers labeled with sources/dates? Are dollar amounts in a realistic range? Apply [ACCURATE] / [SUSPICIOUS] / [WRONG] / [UNLABELED] tags from the first screen
4. Pursue the GOAL using the assigned workflow protocol
5. At each step, apply the domain skepticism triggers
6. Log bugs/friction with confidence tags AND domain-accuracy verdicts
7. At the end: record a PULSE reading, a competitor comparison moment, and a **feature gap list** (things the persona expected to find that didn't exist)
8. Budget cap: ~700 words

### Domain gate (mandatory after Phase 2A returns)

Evaluate the Phase 2A findings against this threshold before running remaining personas:

**Gate FAILS (stop and surface to user before continuing) if ANY of:**
- A [WRONG] finding involving a statutory date (protest deadline, lease expiration, notice deadline)
- Two or more [WRONG] findings on financial math (NOI, cap rate, rent-vs-market $/sqft)
- A [WRONG] finding on multi-tenant isolation (seeing another org's data)
- `_TAX_SEASON=true` AND the protest deadline shown is incorrect for any Texas property

**Gate PASSES with warning (continue, but elevate to P0 in report) if:**
- One [WRONG] finding on a non-statutory number
- Two or more [UNLABELED] findings on material data (assessed value, comps, NOI)
- Task completion is Failed (persona couldn't complete their primary workflow)

**Gate PASSES cleanly if:**
- No [WRONG] findings, no more than one [SUSPICIOUS], task completion is Full or Partial

When the gate fails, ask the user via `AskUserQuestion`:
1. **Fix and re-run** — halt testing, implement the fix, re-run from Phase 2A
2. **Continue with the failure logged as Critical** — proceed with all remaining personas knowing the data accuracy issue exists
3. **Restrict to non-affected workflows** — skip workflows that touch the broken surface

---

## Phase 2B: Remaining Personas (isolated agents, run in parallel)

After Phase 2A clears (or the user chooses to continue), launch remaining persona agents **in parallel** — each is an independent Agent subprocess with no knowledge of what Phase 2A found.

Each agent receives the same package as Phase 2A: persona card, URL, GOAL, workflow protocol, skepticism triggers, scoring rules. Nothing else.

**Each agent must:**
1. Set viewport per persona card
2. Navigate to their primary landing point
3. Pursue their GOAL with the workflow protocol
4. Apply domain skepticism triggers and accuracy tags
5. Perform one **competitor comparison moment** — at the most important screen in their flow, explicitly ask: "Is this better, worse, or the same as [their benchmark tool]?" and record the verdict
6. Perform one **state resilience test**: refresh mid-form (T1), back after submit (T2), or deep-link to a detail page (T3)
7. Record a final PULSE reading
8. Produce a **feature gap list** — things the persona expected to find or do that weren't there. Minimum: look for 3. Format each as: `"Expected: [what] at [where] — [why a professional would expect it]"`

---

## Phase 2C: Domain Technical Reviewer

Not a persona. A property-management-software QA engineer who knows the domain. Run as an Agent subprocess after Phase 2B completes — it gets to read the Phase 2A and 2B findings to audit what the personas missed.

**Miskari-specific tasks (in addition to standard tech review):**

1. **Financial math audit** — verify: NOI = gross income − opex; cap rate = NOI ÷ value; recurring bill totals match the schedule view; reconcile balance ties to Plaid transactions. Compute each one independently and compare to what the app shows.

2. **Data freshness audit** — check every "as of" label on material data. Are comps dated? Are cap rates labeled with a roll year? Are utility rate comparisons dated? Flag any [UNLABELED] material number.

3. **Cross-surface consistency** — does the same property show the same appraised value on the assessment list, the protest detail, and the cap-rate tab? Check at least 2 properties.

4. **Protest deadline accuracy** — if test data includes a Texas property, verify the protest deadline shown matches the statutory rule: later of May 15 or 30 days after the notice date (not just May 15 universally).

5. **Feature gap audit** — combine the feature gap lists from all personas, de-duplicate, and add any gaps the technical reviewer notices from the route list that no persona visited.

6. **Standard tasks:** console/network audit on every visited route, accessibility probe (alt text, tab order, focus ring, contrast, touch targets on 375px), edge cases (empty portfolio, property with no assessment, lease with no end date).

Output format per finding:
```
DOMAIN TECH [category]: [finding] | Evidence: [screenshot/console/measurement] | Severity: [C/H/M/L] | Domain impact: [would this make a professional distrust the data?]
```

---

## Phase 2D: Adversarial Miskari User

Not a persona — a skeptical professional who has been burned by two PM tools with garbage data. They are actively looking for reasons NOT to trust Miskari.

Run as an isolated Agent subprocess. This agent's job is to find holes in the data, not the UX.

**What they probe:**
1. **Math manipulation** — edit a bill amount mid-flow, check if dashboard totals update immediately or show stale aggregates
2. **Cross-org data leak** — attempt to access routes with modified org context; probe whether RLS isolation holds
3. **Document boundary** — attempt to access a document URL from property A while authenticated as property B (try guessing a plausible UUID)
4. **Implausible data injection** — enter an assessed value of $1 and $999,999,999; check if the opportunity score and income approach handle boundary values gracefully
5. **Concurrency trap** — open the same protest in two tabs, make different edits, submit both; check which wins and whether the loser is surfaced
6. **Empty state traps** — navigate every analytics/report view with zero data; check for division-by-zero or misleading "no data" screens
7. **Stale session** — let session expire mid-form fill; check if form data is preserved after re-authentication

**Plant/cleanup discipline (mandatory):** every record created must be tracked and deleted. Before Phase 3:
```
PLANTS:
- protest id=X (implausible value test) → cleanup: DELETE via UI or noted as residue
CLEANUP STATUS: N/N verified deleted
```

---

## Phase 3: Report

Load the report template from `/home/drago/.claude/skills/user-test/references/report-template.md`. Use the standard structure, then add these Miskari-specific sections.

### Miskari-specific report sections

**Insert after "Executive Summary":**

#### Domain Trust Ratings

| Persona | Domain Trust | Reason |
|---|---|---|
| [name] | **Trusted** / **Conditional** / **Distrusted** | [one sentence: what tipped it] |

- **Trusted** — no [WRONG] findings, ≤1 [SUSPICIOUS], task completed, would recommend to a colleague
- **Conditional** — 1 [WRONG] or 2+ [SUSPICIOUS] or task Partial; useful but they'd verify data externally before relying on it
- **Distrusted** — 2+ [WRONG] findings, or any [WRONG] on a statutory date, or task Failed due to data error

**Insert after "Consolidated Bug List":**

#### Data Accuracy Findings

All findings tagged [WRONG] or [UNLABELED] from any agent, consolidated here separately from the main bug list. These are the domain-specific trust failures.

| # | Tag | Surface | Finding | Persona | Domain impact |
|---|---|---|---|---|---|
| | [WRONG] / [UNLABELED] | [route] | [what's wrong] | [who found it] | [what professional would do differently because of this] |

**Insert after "Adversarial User Findings":**

#### Expert Feature Gaps

Things domain experts expected to find or do in Miskari that don't exist. These are product opportunities, not bugs. Ordered by how many personas independently surfaced the same gap.

| Gap | Who expected it | Where | Why a professional expects it | Priority |
|---|---|---|---|---|
| [what's missing] | [N personas] | [route/surface] | [domain reason] | P1/P2/P3 |

De-duplicate across all Phase 2 agents and the Technical Reviewer. A gap surfaced by 2+ independent personas is P1 by default.

**Insert after "Expert Feature Gaps":**

#### Competitor Delta

| Persona | Their benchmark | Advantage over it | Parity | Gap vs it |
|---|---|---|---|---|
| [name] | [AppFolio / Buildium / Yardi / Excel] | [what Miskari does better] | [same capability] | [what the benchmark does that Miskari doesn't] |

**Insert after "Competitor Delta":**

#### Professional Workflow Completion

| Workflow | Persona | Steps completed | Stall point | Output credible? |
|---|---|---|---|---|
| [protest / onboarding / lease-renewal / vendor-radar / reconciliation / dashboard] | [name] | N/M | [step where they stalled or gave up] | Yes / No / Partial |

"Output credible" means: would the final artifact (hearing packet, renewal offer, reconciliation export) pass scrutiny from a professional in that field?

**Replace the standard "Prioritized TODO List" with:**

#### Customer Impact Prioritization

The findings that most directly affect whether a professional would pay for and keep using Miskari. Ordered by customer impact ÷ estimated effort. This is the primary engineering deliverable.

| Rank | Finding | Customer impact | Effort | Why first |
|---|---|---|---|---|
| 1 | [title] | [what changes for the paying customer] | S / M / L | [why this one before the others] |

Customer impact is the ranking criterion — not technical severity. A workflow-blocking data issue is #1 even if the fix is one line. A security hardening that only affects an adversarial edge case is lower, even if technically Critical. Both get fixed; this ranking says where to start.

**End the report with:**

#### What They'd Tell a Colleague

One paragraph per persona, written in their voice. If someone at their networking event asked "have you tried Miskari?" — what would they say? This is the product-market fit signal in human terms.

**[Persona name]:** "[2-3 sentences in their authentic voice — what they'd actually say to a peer]"

---

## Phase 4: Finish

Same as `/user-test` Phase 4 (details in `/home/drago/.claude/skills/user-test/SKILL.md`), with these additions to `baseline.json`:

```json
{
  "tax_season": true,
  "domain_trust": {
    "Sandra": "trusted | conditional | distrusted",
    "Marcus": "trusted | conditional | distrusted"
  },
  "data_accuracy_findings": 0,
  "wrong_math_instances": 0,
  "wrong_statutory_dates": 0,
  "feature_gaps": [
    { "gap": "...", "n_personas": 2, "priority": "P1" }
  ],
  "competitor_delta": {
    "advantages": ["..."],
    "gaps": ["..."],
    "parity": ["..."]
  },
  "workflows_tested": ["protest", "onboarding"],
  "workflows_completed": ["onboarding"],
  "domain_gate_result": "clean | warning | failed",
  "professional_verdict": "would_pay | maybe | would_not_pay"
}
```

**`professional_verdict` decision matrix (apply mechanically, not by feel):**

| Domain trust (worst across personas) | Workflow completion (best across personas) | Verdict |
|---|---|---|
| Trusted | Full | `would_pay` |
| Trusted | Partial | `maybe` |
| Conditional | Full | `maybe` |
| Conditional | Partial | `maybe` |
| Distrusted | Any | `would_not_pay` |
| Any | Failed (all personas) | `would_not_pay` |

"Trusted" requires: no [WRONG] findings, no wrong statutory dates, ≤1 [SUSPICIOUS] total across all personas.
"Conditional" requires: 1 [WRONG] or 2+ [SUSPICIOUS], but no wrong statutory dates and at least one persona completed their task.
"Distrusted" is triggered by: 2+ [WRONG], OR any wrong statutory date, OR task Failed due to data error (not UX confusion).

Save to `.gstack/user-test-miskari-reports/baseline.json`. Append to `.gstack/user-test-miskari-reports/learnings.md`.

**Domain trust trend** — track in baseline across runs. If Marcus (Tax Specialist) improves from Distrusted → Conditional → Trusted over 3 runs, that is the most important trend in the product's history.

---

## Phase 5: Offer to Implement

Same as `/user-test` Phase 5. When implementing Miskari findings, follow `CLAUDE.md` conventions:
- Never use bare `prisma` against tenant tables — use `orgPrisma(orgId)`
- Money is integer cents in BigInt columns (`*Cents` suffix) — use `bigCents()` / `formatCents()`
- `assertRefsInOrg(db, refs)` for any user-supplied FK
- Text color is `ink` or `muted` only — never lighter for de-emphasis
- Foreground on solid fill is `text-paper`, never `text-white`
- `revalidatePath()` on affected routes after every mutation
- Job handlers must not call `revalidatePath()` (no request context in the worker)

---

## Operating Principles

**Customer is number one.** Every finding, verdict, and recommendation exists to improve the experience for the professional paying for Miskari. Not to produce an interesting report. To make the product measurably better for the person who depends on it.

- **The professional knows more than the tester.** When the persona is a 15-year property manager and the data looks wrong — the data is probably wrong. Never rationalize the concern away.
- **Domain accuracy outranks UX polish.** A confusing button is Medium. A wrong protest deadline is Critical. A missing data source label on an assessed value is High.
- **Feature gaps are first-class findings.** "I expected to be able to do X" from a domain expert is a product requirement, not a complaint. Surface it clearly.
- **Isolated agents prevent cross-contamination.** Each persona runs as a separate subprocess with no knowledge of what others found. This is not optional — shared-state testing produces anchored results.
- **Sources are not optional.** Any number shown without provenance is [UNLABELED] — professionals need to know whether to trust a number before acting on it.
- **The phone call test.** If the persona reaches for an external source (DCAD portal, Zillow, a spreadsheet, a phone call) to verify something Miskari showed — that is a trust failure. Surface it.
- **Seasonal context is always checked.** Phase 0.3 auto-detects tax season and adjusts P0 priorities. The tester never needs to know what time of year it is — the skill adjusts automatically.
- **The professional verdict is computed, not felt.** The `professional_verdict` field uses the decision matrix. No manual override. If the matrix says `would_not_pay`, the report says so — even if individual UX elements were pleasant.
- **"Better than spreadsheet" is the floor.** If verification takes longer than doing it manually, Miskari failed.
- **Multi-tenant is non-negotiable.** Any cross-org data exposure is Critical, always, regardless of how it was found.
