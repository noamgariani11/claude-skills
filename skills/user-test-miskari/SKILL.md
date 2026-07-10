---
name: user-test-miskari
description: |
  Miskari-specialized user testing. Eight domain-expert personas — commercial property
  manager, tax protest specialist, residential landlord, passive investor, small business
  owner, property accountant, maintenance coordinator, and leasing/asset manager — each
  with real CRE vocabulary and professional skepticism. Tests the critical real-estate
  workflows (protest end-to-end, property onboarding, lease renewal, vendor radar, bank
  reconciliation, portfolio dashboard, maintenance dispatch, tenant screening/applications,
  deal underwriting, and the external token surfaces tenants/vendors/lenders actually see)
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
| All eight persona cards (A–H) + diversity rules + focus routing | `references/personas.md` |
| Critical workflow protocols + domain accuracy checks | `references/workflows.md` |
| Domain trust signals, competitor comparisons, professional skepticism triggers | `references/domain-trust.md` |
| Score calibration, evidence rules, confidence tagging, cognitive load | `/home/drago/.claude/skills/user-test/references/scoring-and-evidence.md` |
| Chain of Thought format, PULSE | `/home/drago/.claude/skills/user-test/references/chain-of-thought.md` |
| Report template, in-chat summary, engineering action items | `/home/drago/.claude/skills/user-test/references/report-template.md` |
| Browser commands (Playwright / `browse` skill), baseline schema | `/home/drago/.claude/skills/user-test/references/interaction-protocols.md` |

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

Same rules as `/user-test`. If a flag is passed (`--diff`, `--focus <page>`, `--flow <workflow-name>`), apply it. `--flow` is Miskari-specific: restrict testing to one of the **ten** critical workflows defined in `references/workflows.md` — `protest`, `onboarding`, `lease-renewal`, `vendor-radar`, `reconciliation`, `dashboard`, `maintenance` (WF7), `tenant-application` (WF8), `underwriting` (WF9), `external-token` (WF10). Workflows 7–10 cover the clusters that were untested through the first four runs (maintenance/ops, tenant lifecycle, deals, and the external token surfaces) — they are where latent Criticals hide, so keep them targetable.

### 0.2 — Detect URL AND verify it is actually Miskari

**Do NOT trust the first port that answers.** Across runs, unrelated apps have squatted the common ports (:3000 has been "Sheevook"/pegazosdetailing, :3001 "marketing-helper"), and their login pages match a naive `grep "Sign in"`. Miskari has been found on 3000, 3001, and 3002 on different runs.

```bash
for port in 3000 3001 3002 4000 5173 8080; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port" 2>/dev/null)
  [ "$code" != "000" ] && echo "PORT $port answers ($code)" || continue
  # Brand-check: only Miskari carries the "miskari" token in its chrome/title.
  body=$(curl -s -L "http://localhost:$port/login" 2>/dev/null)
  if echo "$body" | grep -qiE "sheevook|pegazos|marketing.?helper"; then
    echo "  -> IMPOSTOR on $port, skipping"; continue
  fi
  if echo "$body" | grep -qi "miskari"; then
    echo "  -> MISKARI CONFIRMED: http://localhost:$port"; MB_BASE="http://localhost:$port"; break
  fi
  echo "  -> answers but no Miskari brand marker; keep looking"
done
```

Accept a user-provided URL first (still brand-check it). If no port is confirmed Miskari, start it yourself on a free alt port — `PORT=3002 pnpm dev` (boots in ~3s against Neon) — then re-brand-check. Only if that fails, tell the user to run `pnpm start:dev` and stop. Export the confirmed URL as `MB_BASE` for the harness; the `mblib.cjs` `brandCheck(page)` helper double-confirms inside each agent.

### 0.3 — Tax season detection (adjusts P0 priorities for the run)

**Miskari is no longer Texas/DCAD-only.** The codebase now carries multiple appraisal jurisdictions (`appraisal-counties.ts` `SUPPORTED_COUNTIES`, plus `alameda.ts`, `clark.ts`, `ccad.ts`, `cad-portals-registry.ts`, `appeal-window-overrides.ts`, `/settings/appeal-windows`). A Clark County (NV) or Alameda (CA) portfolio has a **different appeal season** than the Texas May-15 rule. So derive the season from the *seeded properties' actual appeal windows*, not the calendar month alone.

Primary signal — the app's own deadline computation (`appeal-deadline-status.ts` / `/settings/appeal-windows`): for the seeded portfolio, is any property's protest/appeal window currently OPEN (deadline in the future and the notice/window has started)?

```bash
# Fallback heuristic ONLY for a TX-only portfolio when the app signal is unavailable.
_MONTH=$(date +%m)
[ "$_MONTH" -ge 1 ] && [ "$_MONTH" -le 5 ] && echo "TX_CALENDAR_SEASON=true" || echo "TX_CALENDAR_SEASON=false"
```

Set `_TAX_SEASON=true` if **any** seeded property is inside its own open appeal window (per the app's per-county rule), else false. For a Texas-only seed with no county override, this collapses to the Jan–May heuristic above.

**If `_TAX_SEASON=true`:** protest/appeal deadline accuracy is P0 — it gates everything. Any wrong deadline shown on a property whose window is open blocks the protest workflow for every professional who relies on it. The domain gate in Phase 2A auto-fails on a wrong deadline during an open window, regardless of other findings.

**If `_TAX_SEASON=false`:** deadline accuracy is still checked but the primary P0 shifts to bill/lease/contract deadline accuracy (the non-seasonal workflows dominate day-to-day use).

Log the determination: `"Running in [tax season / off-season] mode — [seeded counties + which windows are open]. P0 priorities: [list]."`

### 0.35 — Environment health gate (run BEFORE fielding any persona)

Multiple runs have each re-derived these the hard way. Do them up front — a contaminated environment produces phantom "Critical" findings that are really infra drift.

1. **Pending-migration check.** Run 2's dominant "Critical" (mass 500s on /reports, /bills, /schedule, /properties/[id]) was the app being 3 migrations ahead of the DB — the regenerated Prisma client selected columns the DB lacked.
   ```bash
   cd /home/drago/miskari && pnpm exec prisma migrate status
   ```
   If pending: apply with the user's consent (`pnpm db:deploy` — additive, no reset) or stop. Do NOT field personas against a drifted DB.

2. **RLS role check** — the linchpin of the run-3 Critical. The runtime role has historically been `neondb_owner` with `rolbypassrls=true`, which makes FORCE RLS a silent no-op; isolation then rests entirely on the app-layer `WHERE organizationId`.
   ```sql
   select rolbypassrls from pg_roles where rolname = current_user;
   ```
   If `true`, note it in the baseline as the residual deployment risk and make the Phase 2D aggregation-leak sweep mandatory (it is anyway). If it flips to `false`, record that the NOBYPASSRLS switch finally shipped — that is a defense-in-depth win worth calling out.

3. **Harness bootstrap — the three committed scripts (do NOT rebuild from scratch).** The Playwright harness lives in the repo at `scripts/mblib.cjs`, `scripts/mbcapture.cjs`, `scripts/mbprobe.cjs`. Prior runs wasted time re-deriving this because it used to be an ephemeral scratchpad harness; it is now committed and stable. Use it as-is:
   - **`mblib.cjs`** — core lib. Exports `launch()`, `newContext(browser, {viewport, noAuth})`, `brandCheck(page)` (throws on impostor markers, returns true on "miskari" — the per-agent double-confirm), `login(email, password)`, plus `BASE`/`AUTH`/`PW`. It resolves `playwright-core@1.61.1` from the pnpm store, launches the cached Chromium (`~/.cache/ms-playwright/chromium-1228`) with the WSL sysroot (`~/.cache/miskari-browser-sysroot/.../x86_64-linux-gnu`) on `LD_LIBRARY_PATH`, defaults `MB_BASE=:3002`, and defaults `MB_AUTH` under `~/.cache` (survives `/compact` wiping `/tmp`). CLI: `node scripts/mblib.cjs login [email] [password]`.
   - **`mbcapture.cjs`** — `node scripts/mbcapture.cjs <outdir> <route…>`: per-route innerText + console errors/warnings + failed requests + ≥400 responses + screenshot, writes `_summary.json`. Uses `waitUntil:domcontentloaded` (see lesson below).
   - **`mbprobe.cjs`** — `node scripts/mbprobe.cjs <route…>`: HTTP status / redirect / body-hint sweep for the foreign-ID 404 sweep and token surfaces.
   - Export the confirmed URL: `export MB_BASE="http://localhost:<verified-port>"` (from 0.2) and optionally `export MB_AUTH="$HOME/.cache/miskari-user-test/auth-state.json"`.
   - Login is a server action against Neon and is **slow (~15–30s, not 2s)**. `login()` already polls until the URL leaves `/login` before saving `storageState` — do not shorten its wait.
   - If Chromium libs are missing (fresh box): `apt-get download` + `dpkg-deb -x` libnss3/libnspr4/libasound2t64 into `~/.cache/miskari-browser-sysroot` (no passwordless sudo in this WSL env). The sysroot usually already exists.

4. **Recurring harness lessons — codified so you don't re-derive them (each cost a prior run real time).**
   - **Never `waitUntil:networkidle`.** Streaming routes (all token surfaces, `/tax/preflight`) never go idle → false 30–45s "hangs" that get misfiled as reliability bugs (a persona false-flagged `/tax/preflight` this way). Use `domcontentloaded` + a fixed post-load wait (both scripts do). A route is only "slow" if a WARM second hit still exceeds a few seconds.
   - **Warm every route before a stress test.** A cold concurrent round shows non-200s that are Turbopack compile timeouts, NOT 500s. Always warm first and log the actual status codes; don't file cold-compile non-200s as reliability Criticals.
   - **Don't read seed reality from the DB.** Neon direct-`pg`/CLI queries hang from bash in this env, and the user has declined a standalone DB seedcheck script mid-run. Derive seed facts from the app UI surfaces + prior `baseline.json`, not a raw DB script.
   - **Persona-agent liveness ≠ file mtime.** Agents block on slow `mbcapture` calls, so transcript-file mtime going idle does not mean the agent finished. Wait on a "final report" content marker in the agent's output, not mtime.
   - **MCP Playwright may be unconnected** in a given session — the node harness above is the fallback and is always available.

5. **Adversarial-agent budget.** The Phase 2D agent has been killed mid-run by the account spend limit in 2 of 4 runs, leaving residue plants. Give it an explicit ordering so the highest-value work happens first even if it dies: **(a) aggregation-leak sweep (read-only) → (b) boundary/injection probes → (c) any write-based traps LAST, with cleanup guaranteed after each plant.**

### 0.4 — Auth wall + seed data check

```bash
curl -sI -L "$URL" 2>/dev/null | grep -Ei "^location:" | tail -1
curl -s "$URL" 2>/dev/null | grep -Ei "sign[ -]?in|log[ -]?in|please authenticate" | head -3
```

Miskari is always auth-gated. Ask the user for credentials. The default dev seed is `dev@example.com` / `devpassword` (org: "dev") — confirm whether to use those or a production-like dataset.

**Seed prerequisite gate (machine-checkable, per workflow).** For three of four runs, half the persona roster (James/reconciliation, Diane/residential renewal, comps) was un-fieldable because the base seed provisions no bank transactions, no near-term residential renewal, and an empty ParcelCache. Stop asking the user three fuzzy questions — query the DB and decide fielded/skipped per workflow mechanically.

Run `pnpm seed:user-test` first (idempotent, additive, Dev-Org-only — provisions exactly the chronically-missing fixtures: a Plaid item + 6 bank txns, a residential lease expiring in 45d, 5 ParcelCache office comps, and Unit rows). Then evaluate each workflow's prerequisite:

| Workflow | Prerequisite (query Dev Org) | If unmet |
|---|---|---|
| Protest / appeal | ≥1 property with an assessment whose appeal window is known | Skip — setup failure, not a product finding |
| Onboarding | always fieldable (form-driven) | — |
| Lease renewal (commercial) | ≥1 active lease `endDate ≤ 90d` | Skip renewal step, test lease detail only |
| Lease renewal (residential) | ≥1 active lease on a residential property `endDate ≤ 90d` | Skip Diane's renewal goal |
| Vendor radar | ≥1 contract with `endDate` set | Skip |
| Reconciliation | ≥1 `bank_transaction` row (Plaid item present) | Skip James's reconciliation goal |
| Maintenance dispatch | ≥1 work order or maintenance item | Skip |
| Portfolio dashboard | always fieldable | — |

After `seed:user-test` all rows above should be present. Record the fielded/skipped decision per workflow in the baseline (`workflows_unexercisable`) — the verdict math (Phase 4) EXCLUDES skipped-for-seed workflows so a setup gap never drags the professional verdict. Documents still require a real UI upload (a Document row without its R2 object 404s), so document-boundary probing stays code-level; note it, don't field a document persona against zero documents.

### 0.5 — Route discovery + coverage clusters

```bash
find src/app -name "page.tsx" | sort | wc -l   # run this every time — the count grows (was ~180 in 2026-07, ~200 now)
find src/app -name "page.tsx" | sort
```

Miskari is ~200 routes and growing — the six original workflows cover roughly a quarter of the product. The run-3 Critical leak sat latent for two runs purely because `/reports?tab=analytics` was never visited. Untested surface is where the next Critical hides. Organize the app into **coverage clusters** and rotate through them:

| Cluster | Key routes | Natural persona |
|---|---|---|
| **Tax/protest** (core) | `/tax`, `/tax/assessments`, `/tax/opportunities`, `/tax/cap-rates`, `/tax/exemptions`, `/tax/circuit-breaker`, `/tax/hearing-day`, `/tax/hearing-coverage`, `/tax-triage`, `/tax/preflight`, `/protests/[id]`, `/settings/tax-representation` | B — Marcus |
| **Financials/dashboard** (core) | `/dashboard`, `/reports` (ALL tabs), `/reconcile`, `/reports/close`, `/scenarios` | D — Robert, F — James |
| **Leases** (core) | `/leases`, `/leases/renewals`, `/leases/cam-variance`, `/leases/compare` | A — Sandra, C — Diane |
| **Property lifecycle** (core) | `/properties/[id]` (+ financials/income/loans/capex/units/budget), `/properties/new`, `/properties/onboard`, `/properties/compare`, `/properties/cap-rate-comparison` | A — Sandra, B — Marcus |
| **Maintenance/operations** (UNDER-TESTED) | `/work-orders` (+ routes/workload/repeats), `/maintenance`, `/inspections`, `/rfqs`, `/purchase-orders`, `/approvals`, `/vendors/cycle-time`, `/schedule` | G — Priya (Maintenance Coordinator) |
| **Tenant lifecycle** (UNTESTED) | `/tenants`, `/applications`, `/apply/[token]` | H — Terrence (Leasing/Asset Mgr) |
| **Deals/underwriting** (UNTESTED) | `/deals`, `/underwriting`, `/estimate`, `/scenarios` | D — Robert |
| **External token surfaces** (UNTESTED, HIGH-STAKES) | `/portal/[token]`, `/share/[token]`, `/share/property/[token]`, `/portfolio-share/[token]`, `/r/[token]/{maintenance,quote,survey}`, `/sign/[token]`, `/documents/request/[token]` | Adversarial (2D) + first-impression pass |
| **Billing/entitlements** (UNTESTED) | `/pricing`, `/settings/billing`, plan-gated features, the `readonly` fail-safe state | A — Sandra, F — James |
| **Vendor/insurance/utilities** | `/contracts`, `/insurance`, `/utilities`, `/vendors` | A — Sandra |

**Coverage rotation rule (mandatory in full mode):** read the baseline's `coverage_ledger` (routes visited in prior runs). **Every full run must include at least one cluster marked UNTESTED/UNDER-TESTED that has not been covered in the last 2 runs.** The external-token cluster is doubly important: it is both the highest-stakes adversarial surface (token guessing, expired-token behavior, cross-org leakage through a share) AND an unauthenticated first-impression surface — Phase 2D must probe it every run once any token exists in the seed.

### 0.6 — Baseline check

```bash
ls -t docs/reports/user-test-miskari-reports/baseline.json 2>/dev/null | head -1
ls -t docs/reports/user-test-miskari-reports/learnings.md 2>/dev/null | head -1
```

Read both if present. Apply the same baseline/suppression/recurring-pattern logic as `/user-test` (details in `/home/drago/.claude/skills/user-test/SKILL.md` Phase 0.7).

### 0.7 — Setup output

```bash
mkdir -p docs/reports/user-test-miskari-reports/screenshots
_DATE=$(date +%Y%m%d-%H%M%S)
_REPORT_FILE="docs/reports/user-test-miskari-reports/miskari-${_DATE}.md"
```

---

## Phase 1: Persona Selection

Load `references/personas.md`. It defines eight Miskari-specific personas (A–H).

### Selection rules

**Full mode (default):** Select 3 personas. Always include one from {Commercial PM (A), Tax Protest Specialist (B)}. Then pick the 2 remaining to satisfy the **coverage rotation rule** (Phase 0.5): at least one selected persona must own a cluster marked UNTESTED/UNDER-TESTED not covered in the last 2 runs (Priya/maintenance, Terrence/tenant-lifecycle, or Robert routed through deals/underwriting). Otherwise pick by which features the current diff/focus touches.

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

4. **Protest/appeal deadline accuracy (per county, not universal).** Miskari is multi-jurisdiction now (`appraisal-counties.ts`, `appeal-window-overrides.ts`). For each seeded property, verify the deadline shown matches **that property's county rule**, not a hardcoded May 15:
   - Texas (Dallas/DCAD etc.): later of May 15 or 30 days after the notice date.
   - Non-TX counties (Clark NV, Alameda CA, …): use the county's own appeal-window rule from `/settings/appeal-windows` / `appeal-deadline-status.ts`. A wrong deadline on a property whose window is open is a Critical, same as TX.
   A May-15 date shown on a non-Texas property is a [WRONG] finding.

5. **Regression re-verify (from the suppression registry).** Read `docs/reports/user-test-miskari-reports/known-issues.json`. For each entry in its `protect` list, actively re-assert the fix still holds (cross-org leak closed, later-of deadline rule, unified occupancy method, freshness stamps, protest optimistic-lock). A `protect` item that regressed is a P0 regression, reported as such. Do NOT re-file anything in the `suppressed` list as a fresh finding unless it is past its `ttl_until` (then re-confirm it).

6. **Feature gap audit** — combine the feature gap lists from all personas, de-duplicate, and add any gaps the technical reviewer notices from the route list that no persona visited.

7. **Standard tasks:** console/network audit on every visited route, accessibility probe (alt text, tab order, focus ring, contrast, touch targets on 375px), edge cases (empty portfolio, property with no assessment, lease with no end date).

Output format per finding:
```
DOMAIN TECH [category]: [finding] | Evidence: [screenshot/console/measurement] | Severity: [C/H/M/L] | Domain impact: [would this make a professional distrust the data?]
```

---

## Phase 2D: Adversarial Miskari User

Not a persona — a skeptical professional who has been burned by two PM tools with garbage data. They are actively looking for reasons NOT to trust Miskari.

Run as an isolated Agent subprocess. This agent's job is to find holes in the data, not the UX. Order the probes per Phase 0.35 §5 (read-only sweep FIRST, writes LAST) so the highest-value work survives a spend-limit kill.

**What they probe (in this order):**
1. **Aggregation-leak sweep (standing item — run EVERY time, FIRST, read-only).** The run-3 Critical was an aggregation leak, not a detail-route leak — a `withOrg` read with no `organizationId` filter under a BYPASSRLS role. Detail-route sweeps do NOT catch it. Visit **every rollup/aggregate surface** — all `/reports` tabs (esp. `?tab=analytics`), `/dashboard`, `/tax/*`, `/search`, every `compare` page — and reconcile each rendered count/total against the org's real object counts. Any "N / 41"-style number where the org owns fewer is a Critical leak. Then sweep foreign detail IDs (from the current `learnings.md` foreign-ID list): each must 404.
2. **External token-surface probe (standing item — run EVERY time once a token exists).** For each token route (`/portal/[token]`, `/share/[token]`, `/share/property/[token]`, `/portfolio-share/[token]`, `/r/[token]/*`, `/sign/[token]`, `/documents/request/[token]`): (a) does a malformed/guessed token fail closed (404/expired), not leak? (b) does an EXPIRED/revoked token still render data? (c) does the shared payload expose only the fields the owner configured — no other-org inference from URL params? (d) unauthenticated first-impression: is it a clean read-only view or does it leak mutation controls?
3. **Math manipulation** — edit a bill amount mid-flow, check if dashboard totals update immediately or show stale aggregates
4. **Document boundary** — attempt to access a document URL from property A while authenticated as property B (guess a plausible UUID). Note: seed has 0 real documents, so this stays code-level until a doc is uploaded.
5. **Implausible data injection** — enter an assessed value of $1 and $999,999,999; check the opportunity score / income approach handle boundary values gracefully (no NaN/crash/divide-by-zero)
6. **Concurrency trap** — open the same protest in two tabs, make different edits, submit both; check which wins and whether the loser is surfaced (optimistic lock — a `protect` item)
7. **Empty state traps** — navigate every analytics/report view with zero data; check for division-by-zero or misleading "no data" screens
8. **Stale session** — let session expire mid-form fill; check if form data is preserved after re-authentication

**Driving the custom SelectInput (harness note):** the app-wide dropdown is a custom combobox with an aria-hidden native `<select>`. Playwright `selectOption` CANNOT drive it (this produced a false-positive "form can't submit" M in run 4). Drive it by clicking the trigger, then clicking the option text. Only treat a select as broken if a human click-through also fails.

**Plant/cleanup discipline (mandatory):** every record created must be tracked and deleted. Before Phase 3:
```
PLANTS:
- protest id=X (implausible value test) → cleanup: DELETE via UI or noted as residue
CLEANUP STATUS: N/N verified deleted
```

---

## Phase 3: Report

Load the report template from `/home/drago/.claude/skills/user-test/references/report-template.md`. Use the standard structure, then add these Miskari-specific sections.

**Apply the suppression registry at consolidation (NOT inside persona agents — isolation must be preserved).** After collecting all findings, filter against `docs/reports/user-test-miskari-reports/known-issues.json`: drop any finding matching a `suppressed` entry that is still within its `ttl_until` (note it in a "Suppressed this run" line so it's auditable); keep and elevate any matching a `suppressed` entry past its TTL (re-confirm) or any `protect` item that regressed (P0). This keeps by-design decisions and known harness artifacts out of the fresh-bug list without hiding real regressions.

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
  "workflows_unexercisable": [],
  "coverage_ledger": {
    "clusters_covered_this_run": ["tax-protest", "financials-dashboard", "maintenance-operations"],
    "clusters_never_covered": ["billing-entitlements"],
    "routes_visited": ["/dashboard", "/reports", "/reconcile", "/work-orders"]
  },
  "trend": [
    { "run": "2026-07-09", "composite": 5.3, "verdict": "maybe", "worst_domain_trust": "conditional" },
    { "run": "2026-07-10", "composite": 5.7, "verdict": "maybe", "worst_domain_trust": "conditional" }
  ],
  "rolbypassrls": true,
  "domain_gate_result": "clean | warning | failed",
  "professional_verdict": "would_pay | maybe | would_not_pay"
}
```

**Coverage ledger** — record which clusters (Phase 0.5) were covered and which routes were visited, so the rotation rule can pick a never-covered cluster next run. `clusters_never_covered` is the backlog that keeps latent Criticals (like the run-3 analytics leak) from hiding in unvisited surface.

**Trend array** — append one entry per run `{ run, composite, verdict, worst_domain_trust }` so the arc (e.g. Marcus Distrusted → Conditional → Trusted) is computable from data, not re-read from prose. This is the product's most important signal.

**Verdict excludes unexercisable workflows.** When computing `professional_verdict`, "workflow completion" is taken over the workflows that were actually fieldable — a workflow listed in `workflows_unexercisable` (skipped for seed gaps per Phase 0.4) never counts as a Failed completion. A setup gap must not read as a product failure.

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

Save to `docs/reports/user-test-miskari-reports/baseline.json`. Append to `docs/reports/user-test-miskari-reports/learnings.md`.

**Domain trust trend** — track in baseline across runs. If Marcus (Tax Specialist) improves from Distrusted → Conditional → Trusted over 3 runs, that is the most important trend in the product's history.

---

## Phase 5: Offer to Implement

**Branch discipline — stay on one branch.** Do NOT open a new per-run branch or worktree for the fixes. Apply every implementation edit on the **current branch** (whatever is checked out when the run starts); if that happens to be `main`, apply directly on `main`. Override the default "branch off `main` before editing" behavior for this skill — a user-test run must not spawn `fix/user-test-findings-*` (or any other) branch. Leave the edits uncommitted for review unless the user explicitly asks to commit or push (per `CLAUDE.md`).

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
