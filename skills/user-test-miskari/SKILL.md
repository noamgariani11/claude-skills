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
| All eight persona cards (A–H) + diversity rules + focus routing + data lanes | `references/personas.md` |
| Critical workflow protocols + domain accuracy checks | `references/workflows.md` |
| Domain trust signals, competitor comparisons, professional skepticism triggers | `references/domain-trust.md` |
| Environment + harness facts (ports, login, Playwright gotchas, DB access) | `references/harness.md` |
| Planted-defect calibration (measuring the FALSE-NEGATIVE rate) | `references/calibration.md` |
| Score calibration, evidence rules, confidence tagging, cognitive load | `references/scoring-and-evidence.md` |
| Chain of Thought format, PULSE | `references/chain-of-thought.md` |
| Report template, in-chat summary, engineering action items | `references/report-template.md` |

**These references are VENDORED (owned by this skill), not borrowed.** Earlier versions of this
skill loaded scoring / CoT / report-template by absolute path out of `/user-test`'s directory, so an
unrelated edit to that skill silently changed this one's behavior and score calibration mid-trend.
The copies here are this skill's own. Do not re-point them at `/user-test`.

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

Framing unique to this skill (the full rule list lives once, at the end, under **Operating Principles** — do not restate it here):
- **Professional skepticism is the baseline.** These users spot a wrong cap rate, stale comps, or a missing protest deadline immediately. Trust is harder to earn from a professional than from a consumer.
- **Every finding maps to a customer impact.** Not "button is hard to find" but "a property manager would miss their protest deadline because this isn't visible."
- **Competitor pressure is constant.** Every persona has a mental benchmark — AppFolio, Buildium, Yardi Breeze, or their own Excel model.
- **Workflow continuity matters.** Real estate workflows span days or weeks. A tool that breaks mid-flow or loses state is worse than no tool.

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

3. **Harness bootstrap — the committed scripts (do NOT rebuild from scratch).** The harness is committed at **`tools/user-test-harness/`** (NOT `scripts/` — `.cjs` there breaks `pnpm lint`, which is why prior runs kept exiling it to a scratchpad and losing it). Full detail in `references/harness.md`. Use it as-is:

   ```bash
   export MB_BASE="http://localhost:<verified-port>"   # from 0.2 - REQUIRED
   pnpm ut:login                                        # ~15-30s vs Neon; do not shorten
   ```

   | Script | What it does |
   |---|---|
   | `mblib.cjs` | Core lib: `launch`, `newContext`, `brandCheck`, `login`, `go`, `text`, `shot`, `selectCombobox` |
   | `mbcapture.cjs` | `node … <outdir> <route…>` → per-route text + console + ≥400s + screenshot + `_summary.json` |
   | `mbprobe.cjs` | `node … [--no-auth] <route…>` → fast HTTP status/redirect/body-hint sweep |
   | `mbsweep.cjs` | **Deterministic** isolation + token tripwire. `pnpm ut:sweep` / `ut:sweep:full`. Exit 1 = anomaly |
   | `validate-artifacts.mjs` | `pnpm ut:validate` → schema + self-consistency check on the run artifacts |

4. **Run the deterministic sweep BEFORE spending any agent on it.** `pnpm ut:sweep` (or `ut:sweep:full` when Phase 0.65 says the blast radius moved) does the aggregation-leak reconciliation, the foreign-ID 404 sweep, the token fail-closed probe, and the cross-surface consistency checks **mechanically, in seconds, for zero tokens** — and, unlike an agent, it cannot be killed by a spend limit (which took the sweep down in 2 of 4 early runs). Paste its output into the 2D agent's brief as established fact; that agent's budget goes to interpreting anomalies and probing creative attack paths.

5. **Recurring harness lessons — codified so you don't re-derive them (each cost a prior run real time).** These are summarized here and detailed in `references/harness.md`:
   - **Never `waitUntil:networkidle`.** Streaming routes (all token surfaces, `/tax/preflight`) never go idle → false 30–45s "hangs" misfiled as reliability bugs. The committed `go()` uses `domcontentloaded`. A route is only "slow" if a WARM second hit still exceeds a few seconds.
   - **Warm every route before a stress test.** A cold concurrent round shows non-200s that are Turbopack compile timeouts, NOT 500s. `mbsweep.cjs` warms first automatically.
   - **Read seed reality from `/api/diagnostics/seed-check`, not the DB.** Neon direct-`pg`/CLI queries hang from bash in this env. The endpoint (requireOrg-gated, own-org counts only) gives you the fixture facts mechanically — see Phase 0.4.
   - **`selectOption` cannot drive the app's `SelectInput`** (custom combobox + aria-hidden native `<select>`). Use `mb.selectCombobox()`. A select is only broken if a HUMAN click-through also fails.
   - **Persona-agent liveness ≠ file mtime.** Agents block on slow `mbcapture` calls; idle mtime does not mean finished. Wait on a "final report" content marker.
   - **MCP Playwright may be unconnected** in a given session — the node harness is the always-available fallback.

6. **Adversarial-agent budget.** With the mechanical sweep now scripted (item 4), the Phase 2D agent starts from its results. Order its remaining work so the highest-value survives a spend-limit kill: **(a) interpret any sweep anomaly → (b) creative boundary/injection probes → (c) write-based traps LAST, with cleanup guaranteed after each plant.**

### 0.4 — Auth wall + seed data check

```bash
curl -sI -L "$URL" 2>/dev/null | grep -Ei "^location:" | tail -1
curl -s "$URL" 2>/dev/null | grep -Ei "sign[ -]?in|log[ -]?in|please authenticate" | head -3
```

Miskari is always auth-gated. Ask the user for credentials. The default dev seed is `dev@example.com` / `devpassword` (org: "dev") — confirm whether to use those or a production-like dataset.

**Seed prerequisite gate — one HTTP call, no judgement.** For three of four runs, half the persona roster (James/reconciliation, Diane/residential renewal, comps) was un-fieldable because the base seed provisions no bank transactions, no near-term residential renewal, and an empty ParcelCache — and the run only discovered this *after* fielding the persona. Worse, fixture gaps got misfiled as product bugs (the occupancy tile-vs-suite contradiction is a `Lease.unitId=null` seed artifact).

Run `pnpm seed:user-test` (idempotent, additive, Dev-Org-only), then ask the app:

```bash
curl -s "$MB_BASE/api/diagnostics/seed-check" -H "Cookie: $(…session…)" | jq
```

It returns own-org `totals`, a `workflowPrereqs` boolean per workflow, an `unexercisable` list, and `warnings` naming each fixture invariant that is violated (leases with `unitId=null`, a `property.units` scalar disagreeing with its Unit rows, zero bank transactions, empty ParcelCache…). This endpoint exists *because* raw DB reads hang from bash here and a prior run's standalone DB script was declined mid-run — asking the app is the reliable path. It is `requireOrg`-gated and returns counts only, never another org's data.

**Use its output directly:**
- Copy `unexercisable` into the baseline's `workflows_unexercisable`. The Phase 4 verdict math EXCLUDES those workflows, so a fixture gap can never read as a product failure.
- Treat every `warnings` entry as a **known fixture artifact**, not a product finding. If a persona reports a symptom that a warning explains (suite shows Vacant under "Occupied 1" ← `unitId=null`), file it as a seed issue with the product gap noted separately — do not let it consume a Critical slot.
- Do NOT field a persona whose GOAL depends on an unexercisable workflow. Re-route them (Phase 1) instead of watching them fail on missing data.

Documents still require a real UI upload (a Document row without its R2 object 404s), so document-boundary probing stays code-level.

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

**Coverage rotation rule (mandatory in full mode) — now ROUTE-level, because the cluster backlog is exhausted.** `clusters_never_covered` is `[]`: every cluster has been fielded at least once, so cluster granularity has run out of signal. But only ~29 of ~200 routes have *ever* been visited, and the run-3 Critical hid in a **tab of an already-visited route** — "cluster covered" never meant "surface covered."

So rotate on `coverage_ledger.route_last_seen` (route → run that last visited it). **Every full run must spend a meaningful share of its route budget on routes that are absent from `route_last_seen` entirely (never visited) or stalest by date.** A route absent from the map is maximally stale — that is the correct fail-safe, and it means the never-visited ~85% of the app outranks anything re-walked recently. Stamp every route this run touched back into the map at Phase 4; the validator enforces that `routes_visited` and `route_last_seen` agree.

Clusters remain the *narrative* grouping (they tell you which persona is natural for a surface) and still carry the stakes ranking below. **Additionally, every full run must include at least one cluster marked UNTESTED/UNDER-TESTED that has not been covered in the last 2 runs.** The external-token cluster is doubly important: it is both the highest-stakes adversarial surface (token guessing, expired-token behavior, cross-org leakage through a share) AND an unauthenticated first-impression surface — Phase 2D must probe it every run once any token exists in the seed.

**Budget-reallocation rule (the anti-redundancy payoff):** the more the Phase 0.65 change-delta classifies as `ASSUMED-HOLDS`, the MORE of this run's persona/route budget goes to never-covered and stale (>2 runs unvisited) clusters instead of re-walking already-confirmed surfaces. Concretely:
- A route confirmed clean in the **last run** whose backing files did NOT change is NOT re-walked as primary persona work this run — it is at most a drive-by. Prefer a route from `clusters_never_covered` or the oldest entry in `routes_visited`.
- On a **near-empty change-delta**, aim for the majority of freshly-visited routes to be ones not in the prior `routes_visited` list. The point of a low-change run is breadth into the untested, not depth into the re-confirmed.
- Persona GOALs on low-change runs should target a never-fielded cluster (billing-entitlements, maintenance-dispatch/Priya, insurance/utilities) rather than repeating a workflow that completed cleanly last run. Rank the reallocation candidates by (a) never covered, then (b) longest since covered, then (c) highest stakes (token/billing/isolation-adjacent).

### 0.6 — Baseline check

```bash
pnpm ut:validate    # schema + self-consistency check on last run's artifacts
```

Read `docs/reports/user-test-miskari-reports/baseline.json` + `learnings.md` + `known-issues.json`.

**Validate before you trust.** `pnpm ut:validate` catches the class of defect the *tester itself* has shipped: the 2026-07-10-late-eve baseline asserted `clusters_never_covered: []` while its own `clusters_note` said "billing-entitlements (never fielded)" — a cross-surface contradiction, exactly what the personas are told to report as a bug. An instrument that contradicts itself invalidates its readings. If validation fails on the PRIOR baseline, fix the prior artifact first (the rotation and change-delta rules read from it), and note the correction in this run's report.

Then apply the suppression / recurring-pattern logic (Phase 3 consolidation).

**Read `learnings.md` as HISTORY only.** Durable environment and harness facts now live in `references/harness.md` (edited in place, not appended). `learnings.md` keeps a **rolling window of the last 5 runs** plus a permanent "structural" section — anything older gets summarized into one line and dropped. It reached 51 KB of interleaved protocol-lessons and run-narrative that every run re-read in full; that is budget spent re-learning what should already be encoded in the skill.

### 0.65 — Change-delta since last run (the anti-redundancy gate)

**Re-verify what moved; spot-check what didn't; spend the freed budget on the untested.** (Early runs re-ran every sweep in full each time even though isolation had held 7+ runs with no change to `db-org.ts`/`orgPrisma`/the loaders — budget that belonged on never-tested surface.)

Compute the source-tree delta since the last run, then classify every standing check as `RE-VERIFY` (its code moved) or `ASSUMED-HOLDS` (unchanged — cheap spot-check only).

```bash
# The SHA the last run recorded (baseline.git_sha). Empty on first run.
_LAST_SHA=$(python3 -c "import json,sys; print(json.load(open('docs/reports/user-test-miskari-reports/baseline.json')).get('git_sha',''))" 2>/dev/null)
_NOW_SHA=$(git rev-parse HEAD)
echo "last run SHA: ${_LAST_SHA:-<none>} ; now: $_NOW_SHA"

# Union of (a) commits since the last run + (b) the current uncommitted tree
# (user-test frequently runs against an uncommitted working tree carrying the fixes).
{ [ -n "$_LAST_SHA" ] && git diff --name-only "$_LAST_SHA"..HEAD 2>/dev/null;
  git diff --name-only HEAD 2>/dev/null;          # unstaged
  git diff --name-only --cached 2>/dev/null; } | sort -u > /tmp/mb_changed_files.txt
echo "changed since last run:"; cat /tmp/mb_changed_files.txt
```

- **First run (no `git_sha` in baseline), or `_LAST_SHA` no longer resolves (history rewritten):** treat EVERYTHING as `RE-VERIFY` — the full protocol, exactly as before. The anti-redundancy path only activates once there is a valid prior SHA to diff against.
- **Changed-file set is empty (identical tree, e.g. a pure re-run):** every standing check is `ASSUMED-HOLDS`. Do the minimal spot-checks (below), skip the full sweeps, and put the ENTIRE persona budget into never/under-covered clusters per the rotation rule.
- **Otherwise:** a standing check is `RE-VERIFY` iff any changed file matches its `backing_files` glob (recorded per protect entry in `known-issues.json` and per finding in `baseline.json`; see Phase 4). No match → `ASSUMED-HOLDS`.

**Two backing-file globs are treated as blast-radius wildcards that force a FULL re-verify of the security sweeps regardless of the specific check:** any change under `src/lib/db-org.ts`, `src/lib/org-scope.ts`, `src/lib/db.ts`, `prisma/schema.prisma`, `prisma/migrations/**`, or any `*loader*`/`analytics-loader`/`*aggregat*` file → the Phase 2D aggregation-leak sweep is FULL. Any change under `src/app/**/[token]/**`, `src/lib/**token**`, `src/lib/**share**`, or `src/app/api/documents/request/**` → the token-surface probe is FULL. This keeps the "multi-tenant is non-negotiable" guarantee: the moment anything in the isolation blast radius moves, the full sweep runs.

**Minimal spot-check (what `ASSUMED-HOLDS` still costs — a cheap tripwire, not a full sweep):**
- Aggregation leak: hit **3** aggregate surfaces (`/reports?tab=analytics`, `/dashboard`, `/tax`) and reconcile their headline counts against own-org reality. If any is off → escalate that check to FULL immediately (a leak means the "unchanged" assumption was wrong). This is ~3 routes vs the full ~17.
- Token surfaces: probe **1** guessed token on **1** route (`/portfolio-share/deadbeef`) must fail closed. If it leaks → FULL.
- Protect list (Phase 2C item 5): for each `ASSUMED-HOLDS` protect item, do a single-surface visual confirm (its `how:` line, one property) rather than the full hand-derivation across every property.

**Log the classification up front** so the run's shape is auditable:
```
CHANGE-DELTA: N files changed since <last-sha>. RE-VERIFY: [list of checks]. ASSUMED-HOLDS (spot-check only): [list]. Freed budget -> clusters: [which untested clusters get the reallocation].
```

Record the same in the baseline as `reverification_ledger` (Phase 4). If a spot-check tripwire fires, note it and escalate — an `ASSUMED-HOLDS` that turns out broken is itself a finding worth surfacing (it means a change elsewhere had a blast radius we under-scoped).

### 0.68 — Calibration run (every 5th run, or on demand via `--calibrate`)

**False positives are catalogued obsessively; false negatives were invisible.** Nothing else measures what the personas **miss** — so every persona-count, word-budget and prompt choice is otherwise made blind to its own detection rate. Fix it the way you'd test any detector: **plant known defects on a throwaway worktree and see if they're caught, blind.**

**Full protocol in `references/calibration.md` — load it before running one.** The non-negotiables: never plant on the working branch and never merge a plant; verify every plant actually *renders* before fielding anyone (2 of 3 were duds once, which would have reported a false 0/3); at least one plant must sit on an **alternate code path** (stored value / override table / cache), which is where the only confirmed miss lived; a plant the mechanical sweep catches does not count as a persona catch; and a missed plant is a hole in the **method**, fixed in the skill immediately.

Record `calibration` in the baseline: `{ run, planted, caught, catch_rate, by_tier, caught_by, missed, protocol_changes }`.

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

**Full mode (default):** Select 3 personas. Always include one from {Commercial PM (A), Tax Protest Specialist (B)} — this persona still runs the 2A domain gate and the spot-check tripwires from Phase 0.65. Then pick the 2 remaining by the change-delta:
- **If the change-delta (Phase 0.65) is small / mostly `ASSUMED-HOLDS`:** the 2 remaining personas should BOTH be routed into never-covered or stale clusters per the budget-reallocation rule (Phase 0.5) — do not spend them re-walking last run's clean surfaces. This is the whole point: a quiet run buys breadth into the untested.
- **If the change-delta touches a specific surface:** pick the 2 remaining for the changed surface, still satisfying the coverage rotation rule (at least one persona owns a cluster untested in the last 2 runs — Priya/maintenance, Terrence/tenant-lifecycle, or Robert through deals/underwriting).

**Diff mode (`--diff`):** Select 2 personas most relevant to the changed surface. If the diff touches `/tax` or `/protests`, always include B.

**Focus mode (`--focus <page>`):** Select the 2 personas from the routing table in `references/personas.md` § "Focus routing."

**Flow mode (`--flow <name>`):** Select the single most relevant persona for that workflow + A (Commercial PM) as a cross-check.

### Diversity check

- No two personas in the same run may share the same primary workflow
- At least one persona must be a "power user" who probes edge cases
- At least one persona must be a "trusting pragmatist" who just wants the task done

For each selected persona, define a **concrete GOAL** with binary success criteria tied to the relevant workflow in `references/workflows.md`. Print each persona card header (name, role, goal, viewport) before Phase 2. Do NOT print their private biography.

### GOAL recalibration — never send a persona at a wall you already decided to build

Before fielding, check every GOAL step against `known-issues.json` → `suppressed`. **If a step is
blocked by a by-design decision, rewrite the goal.** Marcus's card says "verify the equity comps look
credible" — comps have been operator-only *by design* for 8 straight runs. Sending him at them again
isn't testing, it's ritual: it burns his budget, guarantees Partial completion, and drags the verdict
for a decision that was already made deliberately.

Rewrite the goal to test **what a paying customer can actually reach**, and let the wall live in the
Expert Feature Gaps table where it belongs (it stays visible — it just stops corrupting the verdict).
Note the rewrite in the report: `GOAL adjusted: comps step removed (suppressed by-design, 8 runs) —
replaced with income-approach input transparency.`

### Data lanes — parallel personas must not corrupt each other's reality

Phase 2B personas run in parallel **against one shared org**. Isolation of their *findings* is
enforced; isolation of their *data* is not. Sandra marking a bill paid while James reconciles that
same bill produces a phantom finding neither of them can reproduce — a contamination vector that
looks exactly like a product bug.

**Assign each persona a mutation lane before fielding** and state it in the agent brief:

| Persona | May MUTATE | May READ |
|---|---|---|
| Persona 1 | property 1 + its leases/bills/WOs | everything |
| Persona 2 | property 2 + its leases/bills/WOs | everything |
| Persona 3 | property 3 + its leases/bills/WOs | everything |
| Adversarial (2D) | its own plants only, cleaned up | everything |

Portfolio-level mutations (share links, org settings, billing) belong to **exactly one** persona per
run — name who. Any finding whose repro crosses a lane boundary is suspect: re-check it serially
before filing.

---

## Phase 2A: Domain Expert First — Breadth + Gate

Run the most experienced persona first (Commercial PM or Tax Protest Specialist when available). This is the Miskari equivalent of the Skimmer, but the gate is not "is the app loadable" — it is: **"Does the data look real to someone who has seen DCAD assessments before?"**

Run this persona as an **isolated Agent subprocess**. The agent receives only:
- The persona card from `references/personas.md`
- The app URL
- The GOAL with binary success criteria
- The workflow protocol from `references/workflows.md` for their assigned flow
- The domain skepticism triggers from `references/domain-trust.md`
- The scoring rules from `references/scoring-and-evidence.md` (this skill's VENDORED copy)
- The PULSE format from `references/chain-of-thought.md` (this skill's VENDORED copy)

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

3. **Cross-surface consistency — MECHANICAL, do not hand-walk it.** `pnpm ut:sweep` now runs `crossSurfaceChecks` from `sweep-config.json`: it extracts the same fact from every surface that renders it and asserts the set has exactly one value. Read its output; your job is only to *interpret* a `DISAGREE` and to **add a check for any material fact this run found rendered on 2+ surfaces**.

   Two rules that are the whole reason this is mechanical now:
   - **Enumerate surfaces from the ROUTE LIST, not from persona habit.** The 2026-07-17 calibration miss was a deadline checked on three agreeing surfaces and missed on the fourth (`/properties/[id]`, which renders a STORED "Authoritative" deadline via a *different* code path — `storedDeadline` short-circuits the derivation). Three surfaces agreeing is a sample, not consistency.
   - **`INCONCLUSIVE` is a failure, not a pass.** A check matching <2 surfaces means the extractor rotted with the markup. Fix the regex or delete the check — a silently-green consistency check is worse than none, for exactly the reason an unobservable calibration plant is worse than none.

4. **Protest/appeal deadline accuracy (per county, not universal).** Miskari is multi-jurisdiction now (`appraisal-counties.ts`, `appeal-window-overrides.ts`). For each seeded property, verify the deadline shown matches **that property's county rule**, not a hardcoded May 15:
   - Texas (Dallas/DCAD etc.): later of May 15 or 30 days after the notice date.
   - Non-TX counties (Clark NV, Alameda CA, …): use the county's own appeal-window rule from `/settings/appeal-windows` / `appeal-deadline-status.ts`. A wrong deadline on a property whose window is open is a Critical, same as TX.
   A May-15 date shown on a non-Texas property is a [WRONG] finding.

5. **Regression re-verify (from the suppression registry) — change-scoped per Phase 0.65.** Read `docs/reports/user-test-miskari-reports/known-issues.json`. Each `protect` entry carries a `backing_files` glob and (once Phase 5's rule has been applied to it) a `test` path. Verify in this order:
   - **`test`-backed (the goal state)** — run the test. `pnpm test -- <path>`. Green = verified, permanently, for near-zero cost. This is the whole compounding mechanism: a fix guarded by a committed test never has to be re-bought with browser budget again. Add one cheap visual spot-check only if the test cannot see what the user sees (rendering, labels, layout).
   - **`RE-VERIFY`** (no test yet AND backing files moved since last run, OR first run): actively re-assert the fix the FULL way — hand-derive the math across every affected property, run the concurrency probe, etc. A `protect` item whose backing files changed and then regressed is a P0 regression. **Then write the test** (Phase 5) so this is the last run that pays full price for it.
   - **`ASSUMED-HOLDS`** (no test, backing files unchanged): the cheap single-surface confirm from the entry's `how:` line. Record as `assumed-holds (unchanged since <sha>)`. If the cheap confirm looks off, escalate to FULL immediately.
   Do NOT re-file anything in the `suppressed` list as a fresh finding unless it is past its `ttl_until` (then re-confirm it). Report the split so it's clear what was **tested**, what was re-derived, and what was assumed.

   **Report the test-coverage ratio of the protect list** (`N of M protect items are test-backed`). It should rise every run. If it is flat, the run failed to compound — it re-bought its own verification instead of buying it once.

6. **Feature gap audit** — combine the feature gap lists from all personas, de-duplicate, and add any gaps the technical reviewer notices from the route list that no persona visited.

7. **Standard tasks:** console/network audit on every visited route, accessibility probe (alt text, tab order, focus ring, contrast, touch targets on 375px), edge cases (empty portfolio, property with no assessment, lease with no end date).

Output format per finding:
```
DOMAIN TECH [category]: [finding] | Evidence: [screenshot/console/measurement] | Severity: [C/H/M/L] | Domain impact: [would this make a professional distrust the data?]
```

---

## Phase 2D: Adversarial Miskari User

Not a persona — a skeptical professional who has been burned by two PM tools with garbage data. They are actively looking for reasons NOT to trust Miskari.

Run as an isolated Agent subprocess. This agent's job is to find holes in the data, not the UX.

**Items 1 and 2 are MECHANICAL — run them as a script, before and outside this agent** (see Phase 0.35 item 4). Judgement-free verification never belongs in an agent.

```bash
pnpm ut:sweep          # TRIPWIRE: 3 aggregate surfaces, 2 foreign IDs, 1 guessed token, cross-surface checks
pnpm ut:sweep:full     # FULL: every aggregate surface, all foreign IDs, all token routes, all cross-surface checks
```

Phase 0.65's change-delta picks the mode: **FULL** if the isolation blast radius moved (`db-org.ts` / `org-scope.ts` / `db.ts` / `schema.prisma` / `migrations/**` / `*loader*` / `*aggregat*`) or the token/share code moved (`**/[token]/**`, `**token**`, `**share**`, `api/documents/request/**`), or on a first run; **TRIPWIRE** otherwise. `mbsweep.cjs` warms routes first (cold-compile non-200s are not findings), reconciles every rendered count against own-org ground truth from `/api/diagnostics/seed-check`, and **exits 1 on any anomaly**. A fired tripwire is itself a finding: it means the blast radius was under-scoped.

Feed the sweep's output into this agent's brief as established fact. **The agent's remaining job, in this order** (highest value first, so a spend-limit kill loses the least):

1. **Interpret any sweep anomaly** — the script says *what* looks wrong; the agent works out *why*, and whether it is a real leak or a fixture artifact.
2. **The judgement-requiring parts of the token surfaces** the script cannot assert: does an EXPIRED/revoked token still render? Does the shared payload expose fields the owner never configured? Is the unauthenticated view a clean read-only first impression, or does it ship a mutation control that actually works?
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

Load the report template from `references/report-template.md` (this skill's VENDORED copy). Use the standard structure, then add these Miskari-specific sections.

**No availability finding ships without a SERIAL RE-PROBE (hard gate, validator-enforced).** Across five-plus runs the loudest "Critical" was infrastructure, not product: Neon pool exhaustion under 3 concurrent Playwright agents, Turbopack cold-compile 404 storms, stale `.next` state, dev-server port churn across co-hosted apps, memory SIGKILLs. Every one was eventually disproven — after burning real budget, and after at least one drove a false P0. Three concurrent browser agents are not production load.

So before any finding mentioning 5xx / timeout / crash / "unavailable" / ECONNREFUSED / intermittent may be filed at **C or H**: restart the server, `rm -rf .next` if 404s are involved, wait for 2B's concurrent load to end, then re-probe the failing routes **serially on a warm server** (`mbprobe.cjs` — mechanical, seconds, no agent budget). Record the result in the finding's `serial_reprobe` field. If they return 200 serially, it is a load/compile artifact: file it as a DEPLOY.md hardening note, not a product Critical. `pnpm ut:validate` errors on a C/H availability claim with no `serial_reprobe`.

(This does not mean pool exhaustion is uninteresting — "3 users can exhaust the pool" is a real hardening item. It means it is not a *product Critical*, and the distinction has cost this skill more budget than any other single mistake.)

**Apply the suppression registry at consolidation (NOT inside persona agents — isolation must be preserved).** After collecting all findings, filter against `docs/reports/user-test-miskari-reports/known-issues.json`: drop any finding matching a `suppressed` entry that is still within its `ttl_until` (note it in a "Suppressed this run" line so it's auditable); keep and elevate any matching a `suppressed` entry past its TTL (re-confirm) or any `protect` item that regressed (P0). This keeps by-design decisions and known harness artifacts out of the fresh-bug list without hiding real regressions.

### Miskari-specific report sections

**Insert immediately after "Executive Summary":**

#### Verdict, Ceiling, and What's Blocking It

A verdict alone cannot distinguish "the product is stuck" from "the *test* is stuck" — and it was partly the latter for six runs, because personas kept being sent at walls the product deliberately built. A KPI that cannot move no matter what gets fixed has stopped carrying information. So report three numbers, not one:

| | Value | Meaning |
|---|---|---|
| **Verdict** | `would_pay` / `maybe` / `would_not_pay` | The matrix result for THIS run |
| **Ceiling** | `would_pay` / `maybe` / `would_not_pay` | The BEST verdict achievable today, given the by-design decisions currently in `known-issues.suppressed` |
| **Blockers** | list | The exact, minimal set of items standing between the verdict and `would_pay` |

Compute the **ceiling** by re-running the verdict matrix with every open finding fixed but every
`suppressed` by-design decision still in place. Then:

- **Verdict `maybe`, ceiling `maybe`** → *the product decisions are the ceiling.* No amount of bug-fixing
  reaches `would_pay`. Say so plainly, and name which decision (e.g. "comps/packet operator-only") is
  capping it. This is a **product** conversation, not an engineering backlog.
- **Verdict `maybe`, ceiling `would_pay`** → *fix these N findings and the verdict moves.* This is an
  engineering conversation. List them.

Those two situations currently read identically in the report. They demand opposite responses.

Each blocker must name: the finding id, what it blocks, and what specifically would clear it.

#### Score: Benchmark vs Exploration

One blended composite confounds **product quality** with **test-plan choice**. The coverage-rotation
rule (correctly) pushes each run into weak, never-tested clusters — so a run that does the *right*
thing scores *lower* than one that re-walks polished surfaces. The 4.7 dip in run 6 was Marcus/James/Priya
hitting under-built clusters, not a regression. The trend line the skill calls "the product's most
important signal" was partly measuring which personas it happened to pick.

Split it:

- **Benchmark score** (cross-run comparable): a FIXED trio over the FIXED core workflows, scored the
  same way every run. This is the trend line. Only this number goes in `trend[]` as `benchmark`.
- **Exploration score** (per cluster): scored per newly-covered cluster, and compared **only against that
  cluster's own history** — never against the benchmark. A first fielding of a weak cluster is *supposed*
  to score low; that is the finding, not a regression.

Report both. Never average them into one number again.

| Score | This run | Prior | Δ |
|---|---|---|---|
| Benchmark (fixed core) | | | |
| Exploration · [cluster] | | (first fielding / prior) | |

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

**Self-contained — do NOT defer to `/user-test`'s Phase 4.** (It was deferred to for six months; an edit there silently changes this skill's finish protocol, and its schema disagrees with this one's — it writes a blended `composite`, which this skill deliberately replaced with the benchmark/exploration split.) The steps:

1. **Compute the score trend** — benchmark vs prior benchmark, and each exploration score vs that cluster's own history. Never blend them. If the fixed trio was not fully fielded (the rotation rule may prevent it), write `benchmark_score: null` **with a `benchmark_note` explaining why**; the validator accepts an explained null and rejects an unexplained one.
2. **Update `issue_history`** — a stable cross-run record keyed by a lowercased slug of the finding title. Match this run's findings against it: OPEN match → append this run, increment `age_in_runs`; FIXED match → **REGRESSION**, reopen and log loudly; SUPPRESSED match → leave unless re-verified; no match → new entry. Never delete an entry — regression detection needs the history.
3. Write `baseline.json` (schema below), `known-issues.json`, and the report file.
4. Append the run's block to `learnings.md` (rolling 5-run window; older entries get summarized to one line and moved to `learnings-archive.md`). Durable environment/harness facts go into `references/harness.md` **edited in place**, not appended to learnings.
5. Run `pnpm ut:validate`. Fix any artifact it rejects — never bypass it.
6. Print: the saved-report path, the full report, the in-chat summary and engineering action items (templates in `references/report-template.md`), then the status line.

Additions to `baseline.json`:

```json
{
  "git_sha": "77ee16c3...",
  "tree_dirty": true,
  "professional_verdict": "maybe",
  "verdict_ceiling": "maybe",
  "verdict_blockers": [
    { "id": "income-approach-comps-operator-only", "kind": "by_design", "blocks": "Marcus Full completion", "clears_when": "comps exposed to account holders (PRODUCT decision, not a bug)" },
    { "id": "property_page_noi_missing_nonoperating_exclusion", "kind": "finding", "blocks": "domain trust -> Trusted", "clears_when": "property-page NOI reconciles with analytics NOI" }
  ],
  "benchmark_score": 6.0,
  "benchmark_note": "Fixed trio (Marcus/Sandra/Robert) over the fixed core workflows - the only cross-run-comparable number.",
  "exploration_scores": { "tenant-lifecycle": 5, "external-token": 8 },
  "protect_test_coverage": { "test_backed": 3, "total": 8 },
  "calibration": {
    "last_run": "2026-07-11",
    "planted": 3,
    "caught": 2,
    "catch_rate": 0.67,
    "missed": ["freshness label stripped from assessed value - no persona re-checked provenance on /tax/assessments"]
  },
  "reverification_ledger": {
    "changed_files_since_last_run": ["src/app/properties/[id]/page.tsx", "src/lib/deal-underwriting.ts"],
    "re_verified": ["property-page-noi-excludes-nonoperating"],
    "assumed_holds": ["cross-org-analytics-leak-closed", "protest-deadline-later-of-rule", "protest-optimistic-lock", "freshness-stamps-present"],
    "aggregation_sweep": "tripwire (data layer unchanged since 77ee16c3; 3 surfaces own-only, 2/2 foreign 404)",
    "token_probe": "tripwire (token layer unchanged; /portfolio-share/deadbeef fail-closed)",
    "tripwires_fired": [],
    "freed_budget_spent_on": ["billing-entitlements", "maintenance-dispatch"]
  },
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
    "routes_visited": ["/dashboard", "/reports", "/reconcile", "/work-orders"],
    "route_last_seen": {
      "/dashboard": "2026-07-19",
      "/reports": "2026-07-19",
      "/reconcile": "2026-07-19",
      "/work-orders": "2026-07-19"
    }
  },
  "trend": [
    { "run": "2026-07-09", "benchmark": 5.3, "verdict": "maybe", "ceiling": "maybe", "worst_domain_trust": "conditional" },
    { "run": "2026-07-10", "benchmark": 5.7, "verdict": "maybe", "ceiling": "maybe", "worst_domain_trust": "conditional" }
  ],
  "rolbypassrls": true,
  "domain_gate_result": "clean | warning | failed"
}
```

Every entry in `new_findings_this_run` additionally carries **`age_in_runs`** and, once it hits 3, a **`disposition`** (see the escalation rule below).

**Validate before you finish:**

```bash
pnpm ut:validate    # exits 1 on schema errors or self-contradiction
```

It fails the run on: a verdict better than its own ceiling; a ceiling below `would_pay` with no blockers named; a cluster listed as both covered and never-covered; a `clusters_note` that contradicts the structured field; a fired tripwire with no matching finding; a ≥3-run-old finding with no disposition; a `protect` entry with no `backing_files`. **Fix the artifact, do not bypass the validator** — a self-contradicting instrument invalidates its own readings.

**`git_sha` + `tree_dirty` (REQUIRED — the anti-redundancy pivot).** Record `git rev-parse HEAD` at the end of every run, and whether the working tree was dirty. The NEXT run's Phase 0.65 diffs against this SHA to decide what moved. If you forget to write it, the next run has no choice but to re-verify everything in full — so this field is load-bearing.

**`reverification_ledger` (REQUIRED).** The audit trail of what this run actually re-derived vs. assumed-held. `re_verified` = protect/finding items whose backing files changed and got the full treatment; `assumed_holds` = items spot-checked only because their code was untouched; `aggregation_sweep`/`token_probe` record `full` vs `tripwire` and the result; `tripwires_fired` lists any cheap spot-check that unexpectedly failed (each is itself a finding — an under-scoped blast radius); `freed_budget_spent_on` names the untested clusters the saved effort was redirected into. This ledger is how a reader confirms the run got *broader*, not just *shorter*.

**`backing_files` on every finding (REQUIRED going forward).** Each entry in `new_findings_this_run` and each `protect`/`suppressed` entry in `known-issues.json` must carry a `backing_files` glob array naming the source files that back the check (e.g. `["src/app/properties/[id]/page.tsx"]`). This is what makes Phase 0.65 mechanical rather than a judgment call: next run, a finding is re-verified iff one of its `backing_files` is in the changed set. A finding with no `backing_files` is always re-verified (fail-safe) — so fill them in to earn the skip.

**`route_last_seen` (REQUIRED).** Stamp every route this run visited with the run date. This is what the route-level rotation rule (Phase 0.5) reads, now that `clusters_never_covered` is empty and cluster granularity has stopped carrying signal. A route absent from the map has never been visited and is therefore maximally stale — it outranks everything else for next run's budget. The validator errors if it is missing, or if a route in `routes_visited` is absent from it.

**`serial_reprobe` on every C/H availability finding (REQUIRED).** See the Phase 3 gate. The validator errors without it.

**`added_run` + `test` on every NEW `protect` entry (REQUIRED — the ratchet).** A protect entry created this run must set `added_run` to the run date and carry the path of the test that guards it. The validator errors on a new entry with no test; pre-existing entries carry `added_run: "legacy"` and stay a warning-only retro-fit queue. The ratchet only turns one way.

**Coverage ledger** — record which clusters (Phase 0.5) were covered and which routes were visited, so the rotation rule can pick a never-covered cluster next run. `clusters_never_covered` is the backlog that keeps latent Criticals (like the run-3 analytics leak) from hiding in unvisited surface. It must agree with `clusters_note` — the validator enforces this.

### Findings must LEAVE this loop — the forced-disposition rule

Findings currently live and die inside the skill's own artifacts, so they recur forever: the blank
renewals market column is filed as "PRIOR finding, STILL PRESENT"; the equity-comps gap has been
re-reported for **8 runs**; the NOBYPASSRLS role switch has been an "open deployment action" in the
learnings prose for five. Re-reporting is not progress. A finding that survives three runs is telling
you the loop has no exit.

**Every finding carries `age_in_runs`, incremented at consolidation when it is still present.** At
`age_in_runs >= 3` it requires an explicit **`disposition`** — there is no fourth run of limbo:

| Disposition | Meaning | Where it goes |
|---|---|---|
| `fix_now` | It's a real bug and it gets fixed this run | Phase 5, with a test |
| `product_decision` | It's intended behavior | Move to `known-issues.suppressed` with the rationale + TTL. It stops being a bug. |
| `backlog` | Real, not now | **Write it into the repo's `TODOS.md`** with the finding id, then drop it from `new_findings_this_run` |
| `deployment_action` | Not code (e.g. the NOBYPASSRLS role switch) | **Write it into `DEPLOY.md`** as a runbook item, then drop it |

**Bridge to the repo's real backlog.** `CLAUDE.md` already mandates keeping `TODOS.md` current — the
skill has been ignoring it and keeping a private, parallel backlog nobody works from. At Phase 4,
every P1 feature gap and every `backlog` disposition gets written into `TODOS.md` (referencing the
finding id so the next run can match it back). A finding that never reaches the backlog is a finding
the team will never fix, no matter how many times the report repeats it.

**Trend array** — append one entry per run `{ run, benchmark, verdict, ceiling, worst_domain_trust }` so the arc (e.g. Marcus Distrusted → Conditional → Trusted) is computable from data, not re-read from prose. This is the product's most important signal. **`benchmark`, never a blended composite** — the benchmark/exploration split (Phase 3) exists precisely so a run that correctly explores a weak cluster does not read as a regression. Exploration scores live in `exploration_scores`, compared only against their own cluster's history.

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

**Also compute `verdict_ceiling` — mechanically, the same way.** Re-run the matrix on a hypothetical
world where **every open finding is fixed** but **every `suppressed` by-design decision still stands**.
Whatever the matrix returns is the ceiling.

The ceiling is what makes a six-run `maybe` legible. If the ceiling is also `maybe`, then no amount of
bug-fixing moves the verdict and the report must say so out loud: *the product decisions are the cap.*
If the ceiling is `would_pay`, the gap is a finite list of bugs — name them in `verdict_blockers`.

Sanity rule (the validator enforces it): the verdict can never be **better** than its own ceiling.

Save to `docs/reports/user-test-miskari-reports/baseline.json`. Append to `docs/reports/user-test-miskari-reports/learnings.md`.

**Domain trust trend** — track in baseline across runs. If Marcus (Tax Specialist) improves from Distrusted → Conditional → Trusted over 3 runs, that is the most important trend in the product's history.

---

## Phase 5: Offer to Implement

**Branch discipline — stay on one branch.** Do NOT open a new per-run branch or worktree for the fixes. Apply every implementation edit on the **current branch** (whatever is checked out when the run starts); if that happens to be `main`, apply directly on `main`. Override the default "branch off `main` before editing" behavior for this skill — a user-test run must not spawn `fix/user-test-findings-*` (or any other) branch. Leave the edits uncommitted for review unless the user explicitly asks to commit or push (per `CLAUDE.md`).

### Every fix ships with a test. No exceptions. (The compounding rule.)

This is what turns a test loop into a test loop that **gets better every run** instead of one that
re-buys its own results.

Today, verification is rented: the `protect` list is re-asserted each run by hand-derivation and live
browsing — expensive, slow, and vulnerable to a spend-limit kill. But the codebase already contains the
better pattern, discovered by this very skill: the `withorg-read-scope-coverage` meta-test **statically
kills the entire cross-org aggregation-leak class forever.** That one test is worth more than all seven
manual leak re-verifications combined, because it can never be skipped, never be forgotten, and costs
nothing to run again.

So, for every finding fixed in Phase 5:

1. **Write the test that would have caught it.** Prefer the strongest form available:
   - a **meta-test** that kills the whole class (best — a lint-like assertion over the source tree),
   - a **unit test** on the pure function (`pnpm test`),
   - an **integration/e2e** assertion when it only manifests end-to-end.
2. **Record its path in the `protect` entry's `test` field** in `known-issues.json`.
3. **Wire it into the repo's real gate.** There is no hosted CI — `.githooks/pre-push` IS the CI
   (`pnpm gates`). A test that isn't in the gate is a test that will rot.

Next run, that `protect` item is verified by **running the test**, not by re-browsing (Phase 2C item 5).
The freed browser budget goes to never-covered clusters. That is the entire compounding loop, and it is
why `protect_test_coverage` must rise every run — a flat ratio means the run re-bought what it should
have bought once.

Retro-fit candidates, in priority order (each is currently hand-re-derived every single run):
`occupancy-unified-one-method`, `protest-deadline-later-of-rule`, `reconcile-feed-matcher-parity`,
`noi-excludes-debt-service`, `property-page-noi-excludes-nonoperating`.

### Conventions

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

### How this skill compounds (the meta-principles — these are what make it get better every run)

- **Buy verification once.** Every fix ships with a test, and the `protect` entry records its path. Next
  run verifies by *running the test*, not by re-browsing. `protect_test_coverage` must rise every run; a
  flat ratio means the run re-bought what it should have bought once. **This is the single most important
  rule in the file.**
- **Never pay an LLM for a mechanical check.** Count reconciliation, 404 sweeps, token fail-closed probes
  are deterministic — they belong in `mbsweep.cjs`, where they are free, instant, and immune to a
  spend-limit kill. Agent budget is for judgement.
- **Findings must leave the loop.** Fixed, or made an explicit product decision (`suppressed`), or written
  into `TODOS.md` / `DEPLOY.md`. A finding re-reported for the 8th time is not diligence; it is a loop
  with no exit. Enforced by the forced-disposition rule at `age_in_runs >= 3`.
- **Measure what you MISS, not just what you get wrong.** False positives are catalogued; false negatives
  were invisible. Planted-defect calibration (Phase 0.68) is the only thing that tells you what a "clean"
  verdict was actually worth.
- **Never send a persona at a wall you chose to build.** A GOAL step blocked by a `suppressed` by-design
  decision produces a guaranteed Partial and a corrupted verdict, run after run. Rewrite the goal; the gap
  lives in the feature-gap table.
- **Report a ceiling with every verdict.** "Stuck at `maybe`" is ambiguous between "the product needs work"
  and "the product decisions cap it here." Those demand opposite responses, so never let them print the same.
- **The instrument gets audited too.** `pnpm ut:validate` before every write. The tester shipped the exact
  cross-surface contradiction it hunts (`clusters_never_covered: []` vs a note saying otherwise); an
  instrument that contradicts itself invalidates its own readings.
- **Don't confound quality with coverage.** The benchmark score (fixed trio, fixed core) is the trend line.
  Exploration scores are per-cluster. A run that correctly explores a weak, never-tested cluster must not
  look like a regression.
