---
name: user-test
description: |
  Real-user testing with three independent personas (different archetypes and mental
  models), each run as an isolated `Agent` subprocess so they share no state and cannot
  color each other's findings — Skimmer runs first as a gate, then Careful Reader and
  Mobile Tapper run in parallel. Plus a technical reviewer and an adversarial "chaos
  agent." Every persona uses Chain of Thought, every finding is tagged by confidence,
  every [OBSERVED] bug has evidence, and every score is gated on task completion.
  Iterates across runs: each
  run reads the prior `baseline.json` + `learnings.md`, emits a Status-vs-Prior-Baseline
  table (FIXED / STILL_PRESENT / REGRESSED), suppresses verified-false-positives, and
  detects structural blockers (waitlist, paywall) before persona design so it doesn't
  re-test capped surfaces every run. Three modes: full (default), diff-targeted (`--diff`
  for pre-push), focused (`--focus <page>` for surgical depth). Supports remote URLs +
  Vercel previews. Use when asked to "user test", "test as a real user", or similar.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
  - WebSearch
---

# /user-test — Orchestration

Three persona subagents (each its own isolated `Agent` subprocess) + technical reviewer + adversarial user. Optional concurrent Codex review. Reference files in `references/` hold the details — load them on demand, not up front.

## Reference map

| When you need | Load |
|---|---|
| Mode specifics (full, diff, focus) + auto-detection | `references/modes.md` |
| Archetype behavior, diversity rules, return-visitor gating | `references/archetypes.md` |
| Score calibration, evidence rules, confidence tagging, cognitive load | `references/scoring-and-evidence.md` |
| Chain of Thought format, PULSE, visual hierarchy scoring | `references/chain-of-thought.md` |
| Browser commands (Playwright / `browse` skill), baseline schema | `references/interaction-protocols.md` |
| Voice rules and weak-vs-strong examples | `references/voice-rules.md` |
| Report template, in-chat summary, engineering action items | `references/report-template.md` |

Do not read all of these at once. Load a reference the first time you need it during a phase.

---

## Phase Overview

0. **Prep** — infer mode, detect URL, check auth wall, kick off Codex (if available), discover routes.
1. **Persona design** — generate 3 personas (or 2 in diff mode), enforce diversity, gate return-visitor on persistence.
2. **Live sessions**
   - 2A — Skimmer first (fastest archetype, breadth check)
   - 2B — remaining personas, deepen sessions
   - 2C — Technical Reviewer
   - 2D — Adversarial User
   - 2E — Codex coordination (if available)
3. **Report** — single consolidated document.
4. **Finish** — save baseline, print summary + action items.
5. **Offer to implement** — ask whether to comprehensively fix every finding right now.

---

## Phase 0: Prep

### 0.1 — Infer mode from trigger

Read `references/modes.md` § "Mode Auto-Detection Heuristics." Apply:

- If the trigger clearly maps to one mode, confirm inline and proceed: *"Running in [mode] on [target] — proceeding."*
- Only ask with `AskUserQuestion` if the trigger is genuinely ambiguous (e.g., bare "/user-test" with no context).

If a flag was explicitly passed (`--diff`, `--changes`, `--focus X`), skip the question entirely.

### 0.2 — Detect URL (local OR remote)

Accept any of these, in priority order:
1. A URL the user passed in the trigger (e.g., "user test https://preview-xyz.vercel.app")
2. A local dev server:
   ```bash
   for port in 3000 3001 4000 5173 8080; do
     code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port" 2>/dev/null)
     [ "$code" != "000" ] && echo "FOUND: http://localhost:$port" && break
   done
   ```
3. A Vercel preview (if `vercel` CLI is installed and the repo is linked):
   ```bash
   vercel ls --json 2>/dev/null | head -1
   ```
   Offer the latest preview URL to the user before using it.

If none of the above resolves, tell the user what to start and stop. Do not guess.

### 0.3 — Auth-wall check

Before kicking off anything else, probe the landing page for an auth redirect:

```bash
curl -sI -L "$URL" 2>/dev/null | grep -Ei "^location:" | tail -1
curl -s "$URL" 2>/dev/null | grep -Ei "sign[ -]?in|log[ -]?in|please authenticate" | head -3
```

If the root redirects to `/login`, `/sign-in`, `/auth`, or similar, OR body contains login copy:
- Announce: *"Auth wall detected at [URL]. All personas will stall at the login page."*
- Ask the user for test credentials, or confirm we should proceed with login-page-only testing (acceptable for surface-level UX of the login itself).
- If the user has credentials, capture them privately and have Phase 2 personas log in before running their flows.

### 0.4 — Kick off Codex (optional, best-effort)

```bash
mkdir -p docs/reports/user-test-reports/screenshots
_DATE=$(date +%Y%m%d-%H%M%S)
_REPORT_FILE="docs/reports/user-test-reports/user-test-${_DATE}.md"
_CODEX_OUT="docs/reports/user-test-reports/codex-review-${_DATE}.md"

if command -v codex >/dev/null 2>&1; then
  echo "CODEX_AVAILABLE"
  # Pick prompt based on mode (see references/modes.md § "Codex prompt")
  # Invoke with run_in_background: true; record shell ID + $_CODEX_OUT
else
  echo "CODEX_UNAVAILABLE"  # Phase 2E will skip
fi
```

If codex is not on PATH, set an internal flag and skip Phase 2E silently (no pgrep loop, no waiting).

**Failure detection + retry.** Codex fails in a handful of recurring shapes — `shell_snapshot` syntax error in its sandbox bootstrap, empty `mcp startup`, model-not-supported errors (`'gpt-5.5' requires a newer version of Codex`, `'gpt-5' is not supported when using Codex with a ChatGPT account`), or plain non-zero exit. When the background job completes, check the output before classifying:

- **Empty / stub output** (file size < 1KB, OR no `**Findings**`/`**Critical**`/`**High**` headings): treat as failure.
- **Truncated mid-plan** (output ends inside an `exec` call or before the `Findings` section): same.
- **Model-rejected** (output contains `requires a newer version of Codex` or `is not supported when using Codex with a ChatGPT account`): same.
- **Real failure messages** (`error: codex could not...`, non-zero exit code): same.

**Multi-model retry ladder.** When the first attempt fails, try alternate models in sequence — codex installs across machines run different defaults, and models get retired without notice. Walk this ladder, stopping at the first one that produces a `Findings`-shaped report:

1. Default (no `-c model=` flag) — use whatever the user's `codex` is configured for
2. `-c model='"o3"'` — broadly available, low-friction
3. `-c model='"gpt-5-codex"'` — codex-specific tuned model
4. `-c model='"gpt-5"'` — only works on API-keyed installs, fails on ChatGPT-account installs

At the same time, swap the prompt: if attempt 1 used a broad "review the repo" prompt, attempt 2+ should use a tighter file-scoped prompt that names the high-risk files (`src/proxy.ts`, auth routes, webhook handlers, billing routes, schema migrations) and asks for severity-tagged findings only.

If all four attempts fail, set `CODEX_FAILED`, skip Phase 2E, and add a P3 TODO in the report: "Codex CLI broken N runs in a row — recommend `npm i -g @openai/codex@latest` or pin `RATE_LIMIT_BACKEND` style explicit model fallback." Surface it loudly because two consecutive runs without independent code review is itself a finding.

Record `codex_status` and `codex_attempts` (the per-attempt model + outcome) in `baseline.json` so subsequent runs can see if codex is flaky and the same model keeps failing.

### 0.5 — Browser tooling

Prefer Playwright MCP if available. Otherwise use the `browse` skill. See `references/interaction-protocols.md`.

### 0.6 — Route discovery

```bash
# Next.js App Router
find src/app -name "page.tsx" -o -name "page.jsx" 2>/dev/null | sort
# Pages Router
find pages src/pages -name "*.tsx" -o -name "*.jsx" 2>/dev/null | grep -v "^_" | sort
```

For diff mode: also run the diff commands from `references/modes.md` § "Diff Mode."
For focus mode: resolve the target and build the focus manifest per `references/modes.md` § "Focus Mode."

### 0.7 — Baseline check (active, not passive)

```bash
ls -t docs/reports/user-test-reports/baseline.json 2>/dev/null | head -1
ls -t docs/reports/user-test-reports/learnings.md 2>/dev/null | head -1
```

Read both if present. Use them to seed this run, not just for "comparison":

- **Hypotheses to confirm/refute.** From `baseline.json`, lift every entry in `previous_baseline_status` and `new_critical_or_high_in_this_run`. Each becomes a hypothesis the live run should verify or close out (FIXED / STILL_PRESENT / REGRESSED / NOT_RETESTED). The Phase 3 report MUST emit a status row for each one (see `report-template.md` § "Status vs Prior Baseline").
- **Suppression list.** From `learnings.md` (written at the end of every prior run, see Phase 4), lift entries marked `verified-false-positive` or `not-a-bug`. If a finding this run matches one of those, downgrade or drop it without re-flagging — and note the prior verdict inline so the user can see why.
- **Recurring pattern register.** A bug that has been STILL_PRESENT for 3+ consecutive runs is no longer a bug report — it's a structural decision. Stop re-flagging it as if it's news; surface it as "this product accepts this trade-off, see prior runs" in the Status table.

Offer to reuse the same persona set for direct comparison only when the diff against the prior run is small. Otherwise rebuild personas with current goals.

### 0.7.5 — Pre-flight blocker detection (Skimmer escape valve)

The Skimmer is the canary. If the Skimmer's goal is structurally unreachable (waitlist gate, manual approval, paid-only feature), the Skimmer will bounce every time and score will cap at 4 every run. That's noise, not signal.

Detect this before persona design:

```bash
# Manual-approval / waitlist signals
grep -rEi "awaiting approval|request access|join the waitlist|pending approval|manual approval" src/ 2>/dev/null | head -5
# Paywall signals
grep -rEi "no free|out of credits|upgrade to|paid feature|home plan required" src/ 2>/dev/null | head -5
```

Plus probe the auth routes from Phase 0.3: does `/login` show "awaiting approval" copy? Does the homepage's primary registration CTA route to a waitlist?

**If a structural gate is detected**, ask the user via `AskUserQuestion` (one question, three options):

1. **Test the gate as the feature.** Skimmer's goal becomes "evaluate the waitlist UX." Score reflects waitlist quality, not bounce.
2. **Restrict to unauth surfaces.** Skimmer's goal stays consumer-facing but only uses public routes (calculators, marketing). Acknowledge that auth-gated flows aren't tested via Skimmer.
3. **Substitute Casual Browser.** Drop Skimmer for this run, use Casual Browser archetype (curious, no urgency, browses freely). Note in baseline that Skimmer was substituted due to gate.

Record the choice in baseline.json under `gate_handling` so subsequent runs default to the same choice unless the gate is removed.

---

## Phase 1: Persona Design

Load `references/archetypes.md` for the behavior specs and the diversity check.

1. Generate personas (3 in full/focus mode, 2 in diff mode).
2. Run the diversity check. Regenerate any collapsed persona.
3. Return-visitor gating: grep for persistence signals before assigning `VISIT TYPE: return`. Details in `references/archetypes.md` § "Return Visitor Persona (conditional)."
4. For each persona, define a concrete GOAL with binary success criteria (see `references/scoring-and-evidence.md` § "Task Completion Tracking").
5. Print the public header for each persona (name, archetype, goal, viewport). Do NOT print their private biography.

---

## Phase 2A: Skimmer First

Run the Skimmer persona first — shortest viewport, least reading, fastest to surface breadth blockers.

Why first: if the Skimmer bounces immediately (can't figure out what the app is, can't find the CTA), that's a universal problem the other archetypes will also hit. Don't burn tokens on a deeper Careful Reader pass before confirming the front door works.

For the Skimmer session:
1. FIRST browser command: `viewport 1280x720`
2. Navigate to landing. Screenshot. First-impression PULSE. (See `references/chain-of-thought.md` for format.)
3. Goal pursuit — 3-5 steps max with Chain of Thought on each decision.
4. Log bugs/friction inline with confidence tags (`references/scoring-and-evidence.md`).
5. Budget cap: ~500 words for this thin session. If the Skimmer bounces in 2 steps, that's the data.
6. Record into baseline.json `personas[0]` (name, archetype, score, bug_count, task_completed, gate_hit). Do not emit inline HTML comments — they don't survive into the report.

**Gate:** if the Skimmer can't pass a basic "is this app loadable and coherent" check (loads, no blocking error, landing makes some sense), stop and surface this to the user before spending more tokens on deeper personas. Ask whether to continue or bail.

**Skimmer-gated classification.** If the prior `gate_handling` decision is `restrict-to-unauth-surfaces` (or any non-default option recorded in baseline.json) AND the Skimmer's goal would have required the gated surface, the run is *Skimmer-gated*. Don't penalize the score by reflex:

- Mark `personas[0].task_completed: "gated"` (not `"no"`) so the run-over-run delta isn't dragged down by an unfixable cap.
- The composite score should average only over completable runs; if Skimmer is gated, weight Skimmer's score at 0.5 instead of 1 in the composite OR drop it from the composite entirely (note in the report which choice was made and why).
- If the Skimmer has been gated for 3+ consecutive runs, surface that as a structural product decision in the report's "Recurring Issues" section: "the gate is the product; recommend either opening it or rewriting marketing copy so non-gated visitors aren't surprised." Stop re-flagging it as a finding.

---

## Phase 2B: Deepen (Careful Reader + Mobile Tapper, then coverage)

After Skimmer clears the gate:

1. Run the Careful Reader session (viewport 1440x900, detailed input, reads everything).
2. Run the Mobile Tapper session (viewport 375x812 MANDATORY before any page visit).
3. Each tester: one state resilience test — refresh mid-flow (T1), back after submit (T2), deep link (T3).
4. Split remaining unvisited routes across testers so every route is seen at least once (skipped in diff mode for out-of-scope routes, skipped in focus mode entirely for non-focused routes).
5. For each tester, capture a final PULSE reading.
6. For each tester, apply the score cap rules from `references/scoring-and-evidence.md` § "Score Gating." Log any caps explicitly.
7. Append to baseline.json `personas[]`. No inline HTML comments.

---

## Phase 2C: Technical Reviewer

Not a persona. Experienced QA engineer who audits what the personas missed.

Tasks (scoped to visited routes; in focus mode scoped to the focused page):
1. Console & network audit on every visited page
2. Performance spot check on the 3 most-visited pages
3. Accessibility probe: alt text, tab order, focus ring, contrast, touch targets
4. Edge cases: empty states, error states, long input, auth boundaries, 150% zoom
5. Real-user chaos behaviors: rapid back, double-submit, mid-load interaction, two-tab races
6. Design system audit against `DESIGN.md` if present
7. Cross-session pattern detection (bugs 2+ personas hit with different symptoms)

Output format per finding:
```
TECH REVIEW [category]: [finding] | Evidence: [console/net/measurement] | Severity: [C/H/M/L] | Missed by: [which testers, why]
```

Record into baseline.json `tech_findings: N`. No inline HTML comments.

---

## Phase 2D: Adversarial User

Full behavior spec in `references/archetypes.md` § "The Adversarial User (Chaos Agent)."

Every adversarial finding uses this format:
```
ADVERSARIAL [category]: [what they did] | THINKING: "[reasoning]" | RESULT: [what happened] | VERDICT: [robust/fragile/broken] | USER IMPACT: [would a real user hit this? how?]
```

**Plant/cleanup discipline (mandatory).** When the adversarial pass writes anything to the system — registers an account, posts a maintenance task, creates a thread, uploads an attachment, plants an XSS payload — pair every plant with an explicit cleanup. Track plants in a list as you go, then run cleanups before Phase 3:

```
PLANTS:
- maintenance task id=102 (XSS payload)  → cleanup: DELETE /api/maintenance/102
- registered email=adv-flood@example.com → cleanup: admin endpoint or noted as residue
CLEANUP STATUS: 2/2 verified deleted (HTTP 204)
```

If a plant cannot be cleaned (e.g., a registered email has no self-delete), note it as **RESIDUE** in the report's adversarial section. Test data left behind is itself a finding (the app has no self-cleanup) — but it must be visible, not silent.

Checkpoint emitted to baseline.json `adversarial_summary`: `{"findings": N, "fragile": N, "broken": N, "plants_total": N, "plants_cleaned": N, "residue": [...]}`. Don't write inline HTML comments — those don't survive into the report.

---

## Phase 2E: Codex Coordination (skip if unavailable)

If Codex was kicked off in Phase 0:

```bash
while pgrep -f "codex exec" >/dev/null 2>&1 || pgrep -f "codex review" >/dev/null 2>&1; do
  sleep 5
done
test -s "$_CODEX_OUT" && echo "CODEX_READY" || echo "CODEX_EMPTY"
```

If `CODEX_UNAVAILABLE` was set in Phase 0, `CODEX_EMPTY` here, or `CODEX_FAILED` after the Phase 0.4 retry: **skip this phase entirely**. The report's Codex section is omitted. Do NOT block on a waiting loop when codex was never started.

Otherwise, read `$_CODEX_OUT` and classify every finding on **two axes**:

**Axis 1 — Cross-source corroboration:**
- `CORROBORATED` — at least one persona/tech/adv finding describes the same problem
- `NEW` — codex-only, no live cross-reference
- `DISPUTED` — a live tester verified the behavior is intended / not buggy
- `OUT-OF-SCOPE` — applies to code paths not exercised this run

**Axis 2 — Code verification (only for NEW findings):**
- `CODE-VERIFIED` — Codex cited a specific `file:line` and a quick `grep`/`Read` confirms the cited code matches the claim. Only mark VERIFIED if you actually read the cited line.
- `UNVERIFIED` — Codex made a claim without a precise reference, OR the reference exists but the claim doesn't follow from it on inspection.

Format every codex finding:
```
CODEX [severity]: [finding] | Source: [file:line] | Status: CORROBORATED | DISPUTED | NEW+CODE-VERIFIED | NEW+UNVERIFIED | OUT-OF-SCOPE | Cross-ref: [persona/tech/adv id if any] | Verdict: [keep/down-rank/merge/manual-review]
```

**Routing rule for the report:**
- `CORROBORATED` and `NEW+CODE-VERIFIED` → roll into the main Consolidated Bug List with appropriate severity.
- `NEW+UNVERIFIED` → goes to a separate "Codex flags requiring manual review" section. Do NOT inflate the consolidated bug count with these.
- `DISPUTED` and `OUT-OF-SCOPE` → footnote only.

If >50% of codex findings end up `NEW+UNVERIFIED`, that's a smell — codex may be hallucinating against an old code map, OR the personas covered radically different surfaces than codex audited. Note the imbalance in the report.

Update baseline.json `codex_summary` instead of writing inline HTML comments: `{"corroborated": N, "new_verified": N, "new_unverified": N, "disputed": N, "out_of_scope": N}`.

---

## Phase 3: Report

Load `references/report-template.md`. Write the full report to `$_REPORT_FILE`.

Key consolidation rules (vs. the older skill version):
- **No per-tester bug tables.** All bugs land in the single Consolidated Bug List with a `Found By` column. Deduplicate across testers, tech, adv, codex.
- **No separate Design Critique table.** Design findings fold into Consolidated Bug List (tagged `design-system`) or the per-tester narrative.
- **Omit empty sections.** If nothing applies, don't emit the header.
- **Codex section is entirely optional.** Only emit if Codex ran successfully.
- **Focus Target section** only in focus mode. **Changes Under Test** only in diff mode.

---

## Phase 4: Finish

1. **Compute the score trend** before saving baseline. Compare the current run's composite + per-persona scores against the prior baseline:

   ```
   score_trend: {
     composite: { prior: <N>, current: <N>, delta: <N> },
     personas: [
       { name: "Brad",   prior: <N>, current: <N>, delta: <N>, archetype: "Skimmer" },
       { name: "Linda",  prior: <N>, current: <N>, delta: <N>, archetype: "Careful Reader" },
       { name: "Marcus", prior: <N>, current: <N>, delta: <N>, archetype: "Mobile Tapper" }
     ],
     bug_counts: {
       critical: { prior: N, current: N, delta: N },
       high:     { prior: N, current: N, delta: N },
       medium:   { prior: N, current: N, delta: N },
       low:      { prior: N, current: N, delta: N }
     },
     direction: "improved" | "regressed" | "unchanged" | "first run"
   }
   ```

   Direction rule: `improved` if composite delta ≥ +0.3 AND no new Critical AND no net High increase. `regressed` if composite delta ≤ −0.3 OR any new Critical OR High count went up. Otherwise `unchanged`. (First run gets `direction: "first run"` and the deltas are null.)

2. **Update `issue_history`** — a stable cross-run record of every distinct finding:

   ```
   issue_history: {
     "<stable-issue-key>": {
       first_seen: "YYYY-MM-DD",
       last_seen: "YYYY-MM-DD",
       runs_seen: ["YYYY-MM-DD", ...],   // chronological
       severity: "C" | "H" | "M" | "L",
       state: "OPEN" | "FIXED" | "SUPPRESSED",
       title: "<one-line summary>",
       fixed_in_run: "YYYY-MM-DD" | null,
       suppression_reason: "<from learnings.md>" | null
     }
   }
   ```

   Rules for stable-issue-key: lowercased slug of the original title (e.g. `maintenance_score_row_contradiction`). When this run produces a finding, look it up in the prior `issue_history`:
   - **Match found, state OPEN** → append today to `runs_seen`. If `runs_seen.length >= 3`, the report's "Recurring Issues" section MUST surface this issue with its full run history and a "structural decision" recommendation.
   - **Match found, state FIXED** → this is a **REGRESSION**. Reopen: state back to OPEN, append today, log loudly in the report's Status table.
   - **Match found, state SUPPRESSED** → leave as is unless the run explicitly re-verified the issue is back.
   - **No match** → new issue, create entry with first_seen=last_seen=today, runs_seen=[today].
   - When a Status row this run says FIXED, set `state: "FIXED"`, `fixed_in_run: today`. Don't delete the entry — REGRESSION detection needs the history.

3. Save the baseline JSON (schema in `references/interaction-protocols.md` § "Baseline File"). Include `codex_summary`, `codex_attempts`, `adversarial_summary`, `gate_handling`, `score_trend`, `issue_history`, and `previous_baseline_status` fields populated from this run.
4. **Append to `learnings.md`** (a per-project memory the next run reads in Phase 0.7). Schema:

   ```md
   ## Run [date] [time]
   - **verified-false-positive:** [bug name] — [why it isn't a bug, e.g., "Math.round() artifact, score stays within ±1 across runs"]
   - **structural-trade-off:** [thing] — [why we stop re-flagging it, e.g., "closed-beta waitlist by design; tested as feature in run X"]
   - **regression-risk:** [thing] — [what to watch for next run]
   - **codex-flake:** [if codex needed retry] — [pattern, e.g., "shell_snapshot syntax error"]
   ```

   Only add entries that future runs should remember. If nothing changed, write `## Run [date] [time]` followed by `- (no learnings)` so the audit trail is complete.

5. Print the saved-report path.
6. Print the full report.
7. Print the in-chat summary (template in `references/report-template.md`).
8. Print the engineering action items (template in `references/report-template.md`).
9. End with the status line.

---

## Phase 5: Offer to implement

After Phase 4's status line, **ask the user if they want every finding implemented now, in the best way.** This closes the loop so the user doesn't have to write a separate "now go fix everything" prompt.

### When to offer

- Always offer at the end of a successful run (any mode: full, diff, focus).
- Skip the offer if the run produced **zero actionable findings** (no Critical/High/Medium and no broken adversarial probes), OR if the user explicitly disabled it via `--no-implement` on the trigger.
- Never offer if the dev tree is dirty in a way that suggests in-progress work the user might not want disturbed (uncommitted edits to files the fixes would touch). In that case, surface the conflict and let the user resolve before re-asking.

### How to ask

Use `AskUserQuestion` with one question and three options (plus the auto-provided "Other"). Phrase the offer in terms of **scope of fixes**, not yes/no, so the user gets a real choice:

```
Question: "Want me to implement these findings now? I'll follow the project's existing patterns (helpers in CLAUDE.md, design system in DESIGN.md), keep changes minimal, and re-verify each fix end-to-end before reporting done."
Header: "Implement"
Options:
  1. "Implement everything (Recommended)"
     description: "All Critical/High/Medium/Low findings + retract any false positives. Comprehensive fix pass. Ships the same review-quality changes the report recommends."
  2. "Implement P0/P1 only"
     description: "Just the ship-blocker class — Critical and High. Skip Medium/Low and structural-trade-offs. Faster, smaller diff."
  3. "Triage first, then ask"
     description: "Walk each finding briefly with me; pick which to implement after a quick discussion."
```

**Do not phrase it as "yes/no."** A binary prompt invites a reflexive "yes" that sets the wrong scope. The three-option form forces a deliberate choice.

### Operating rules when implementing

If the user picks "Implement everything" or "Implement P0/P1 only", execute the fixes in the same session. Operate under these rules:

1. **Read before you write.** For each finding, open the cited file and trace the actual code path. The report's `Source:` line is a starting point, not a spec. Confirm:
   - the finding still reproduces (a fix may have landed between the report and now);
   - the proposed fix still makes sense once you see the surrounding code;
   - there isn't a richer pattern already in the repo (e.g., a helper in `src/lib/` or `src/server/` that the fix should go through — see CLAUDE.md "Helpers" sections).
   If a finding turns out to be a false positive on inspection, **retract it loudly** in the implementation summary — don't silently skip. Update `issue_history` to `state: "verified-false-positive"` and add a `verified-false-positive` line to `learnings.md` so the next run suppresses it.

2. **Fix the root cause, not the symptom.** A finding like "calculator persists default state on first render" should land as a fix in the persistence hook (one-line gate), not as a special case in each calculator's component. Look one level up before patching.

3. **Follow CLAUDE.md / DESIGN.md / project patterns.**
   - Use `withTransaction` (not raw `BEGIN`/`COMMIT`) for DB transactions.
   - Use `useDelayedAction` (not bare `setTimeout`) inside components.
   - Sanitize `?from=` / `?next=` redirects via `sanitizeReturnTo()`.
   - Match the existing auth-aware CTA pattern when fixing anon dead-ends — don't reinvent.
   - No em-dashes (U+2014) anywhere — site-wide ban.
   - No pure white backgrounds, no emoji icon grids.
   These rules are non-negotiable; CI will block deviations.

4. **One finding per coherent commit-shape.** Don't bundle unrelated fixes. If two findings share a root cause, that's one fix. If they don't, they're separate.

5. **Don't expand scope.**
   - If a finding is HIGH and the proper fix is a 2-line change, don't refactor 200 lines around it. Land the 2-line fix.
   - Skip "while I'm here" cleanups unless the user explicitly asked.
   - "Comprehensive" means *every flagged finding*, not "every place I have an opinion about."

6. **Verify each fix before moving on.** For UI fixes, exercise the flow in a browser (Playwright MCP / `browse` skill). For API fixes, run the original adversarial probe and confirm the response code/shape changed as expected. For shared-helper fixes, run `pnpm exec tsc --noEmit` and `pnpm test` to catch type/test fallout. **Don't claim a fix is done because it compiles.**

7. **Run the project's quality gates at the end.** `pnpm lint && pnpm exec tsc --noEmit && pnpm test`. If anything fails, fix it before reporting done. **Never skip hooks.**

8. **Don't commit or push unless the user explicitly asks.** Per the project's CLAUDE.md commit policy. The implementation lands as uncommitted edits the user can review and stage.

9. **Update artifacts after the implementation pass:**
   - `baseline.json`: bump each fixed finding's `issue_history.state` to `"FIXED"` with `fixed_in_run: today`. Bump `previous_baseline_status` so the next run knows what to retest.
   - `learnings.md`: add `regression-risk` entries for any subtle fixes (e.g., "watch for X if anyone touches Y") and `verified-false-positive` entries for retracted findings.
   - The original report file: append a "Post-run implementation" section at the bottom listing every fix applied, every false positive retracted, and every finding deferred (with a one-line reason).

10. **End with a status table** so the user can verify at a glance:
    ```
    | ID | Title | Status | Verified |
    |---|---|---|---|
    | B-01 | Paint-calc auto-persist | FIXED | dev server roundtrip, banner gone on 2nd visit |
    | B-04 | Login 500→400 | FIXED | curl probe now returns 400 with empty-credentials message |
    | B-05 | Forgot-pw timing | RETRACTED | Already fixed (FLOOR_MS=150 in route.ts); was test artifact |
    ```

### What the user sees

After the question is answered:
- "Implement everything" → execute all 10 rules above across every finding.
- "Implement P0/P1 only" → same rules, scoped to Critical and High.
- "Triage first, then ask" → for each finding, present a one-paragraph "what I'd do" plan and wait for go/no-go before touching files. Useful when the user wants control on a sensitive surface (auth, billing, schema migrations).

### Why this phase matters

Without it, the user has to write a comprehensive prompt by hand to translate the report into action — and that prompt is easy to under-spec ("fix the bugs"), which leads to half-done sweeps. Phase 5 is the skill's commitment that **a /user-test run produces fixes, not just findings**, when the user opts in.

---

## Operating Principles

- **Evidence before confidence.** Every [OBSERVED] finding cites a screenshot, console line, network entry, or measurement. Without evidence, downgrade.
- **Scores are earned, not awarded.** Start at 5. Only reach 7+ with task completion and an evidence-backed positive moment. Log any cap explicitly.
- **Real users forget.** Cognitive-load simulation applies after 3+ pages. Check whether the persona would still retain info from earlier pages before letting them "remember" it.
- **Optional is optional.** If codex isn't installed, the report ships without it. Don't pretend it ran.
- **Budget awareness.** Per-archetype caps in `references/archetypes.md`. Skimmer gates deeper passes. Bail early if the app is completely broken — more testing doesn't help.
- **Honesty over kindness.** A tester who says "fine" when it wasn't is useless. Write what happens.
- **Skepticism on numeric drift.** A ±1 score change, a few-pixel layout shift, a sub-100ms timing change is not a bug by itself — it's measurement noise until it reproduces in 2+ retries OR you can trace it to a code path. See `references/scoring-and-evidence.md` § "False-Positive Guardrails" before flagging anything as HIGH on the basis of "this number changed."
- **The skill iterates.** Every run reads the prior `baseline.json` and `learnings.md`. Bugs flagged STILL_PRESENT 3+ runs in a row are structural decisions, not new findings. Bugs flagged `verified-false-positive` in a prior run are suppressed unless re-verified. Don't retest known-blocked surfaces; flag the block once and route around it.
