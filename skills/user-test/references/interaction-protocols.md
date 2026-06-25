# Interaction Protocols

How to drive the browser. Prefer Playwright MCP if available, otherwise fall back to gstack browse.

---

## Detecting What's Available

```bash
# Check for Playwright MCP tools in the session
# If mcp__playwright__* is available, use those — they are the primary driver.

# Otherwise, locate gstack browse binary:
_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
B=""
[ -n "$_ROOT" ] && [ -x "$_ROOT/.claude/skills/gstack/browse/dist/browse" ] && B="$_ROOT/.claude/skills/gstack/browse/dist/browse"
[ -z "$B" ] && B=~/.claude/skills/gstack/browse/dist/browse
[ -x "$B" ] && echo "BROWSE_READY: $B" || echo "BROWSE_NEEDS_SETUP"
```

If browse needs setup: `cd ~/.claude/skills/gstack && ./setup`. If that fails, do a text-only analysis from source code and flag the limitation loudly in the report.

---

## gstack browse ($B) — Command Reference

```bash
$B viewport 375x812           # Set viewport (FIRST command per persona)
$B goto http://localhost:3000 # Navigate
$B snapshot -i                # Interactive elements only (Skimmer)
$B snapshot                   # Full tree (Careful Reader)
$B snapshot -i -C             # Interactive + cursor-interactive (Mobile Tapper)
$B snapshot -D                # Diff against previous snapshot
$B fill @e3 "realistic input" # Fill form field
$B click @e5                  # Click element
$B scroll                     # Scroll to bottom
$B console --errors           # Check for JS errors
$B network                    # Failed / slow / 4xx / 5xx requests
$B perf                       # Load timing
$B screenshot screenshots/t1-01-landing.png
$B responsive screenshots/t1-responsive   # Mobile + tablet + desktop
$B links                      # List all links (Careful Reader uses this)
$B press Tab                  # Keyboard navigation test
$B back                       # Browser back button
$B reload                     # Refresh
$B js "expression"            # Arbitrary JS eval in page
$B css "selector" "property"  # Read CSS value
```

---

## Playwright MCP — Command Equivalents

If `mcp__playwright__*` is available, prefer these:

- `mcp__playwright__browser_resize` → viewport
- `mcp__playwright__browser_navigate` → goto
- `mcp__playwright__browser_snapshot` → snapshot
- `mcp__playwright__browser_click` → click
- `mcp__playwright__browser_fill_form` → fill
- `mcp__playwright__browser_take_screenshot` → screenshot
- `mcp__playwright__browser_press_key` → press
- `mcp__playwright__browser_console_messages` → console
- `mcp__playwright__browser_navigate_back` → back
- `mcp__playwright__browser_evaluate` → js eval

Use whichever is available. Do NOT mix the two within a single persona session.

---

## Screenshot Conventions

- Prefix every file with the tester number: `t1-`, `t2-`, `t3-`, `tech-`, `adv-`
- Include a zero-padded sequence number: `t1-01-landing.png`, `t1-02-form.png`
- Include a short semantic label: `-landing`, `-form-error`, `-confirmation`
- Always use the Read tool on PNGs you capture so you can actually see them when describing findings

---

## Baseline File (regression mode)

After every run, save a baseline so the next run can do deltas. Schema:

```jsonc
{
  "date": "YYYY-MM-DD",
  "report": "user-test-YYYYMMDD-HHMMSS.md",
  "previous_baseline": "user-test-YYYYMMDD-HHMMSS.md",
  "mode": "full | diff | focus",
  "url": "http://localhost:3000",
  "branch": "dev",
  "auth_session_active": true,
  "gate_handling": "default | restrict-to-unauth-surfaces | test-gate-as-feature | substitute-casual-browser",

  "personas": [
    {
      "name": "Brad",
      "archetype": "Skimmer",
      "viewport": "1280x720",
      "visit": "first",
      "goal": "...",
      "score": 5,
      "task_completed": "full | partial | no | gated"  // "gated" = Skimmer hit a known gate; don't penalize composite
    }
  ],
  "task_completion_rate": 0.50,
  "composite_score": 6.0,
  "routes_visited": ["/", "/tools", ...],

  "tech_findings": 4,
  "adversarial_summary": {
    "findings": 14, "fragile": 1, "broken": 0,
    "plants_total": 3, "plants_cleaned": 3, "residue": ["..."]
  },

  // Codex multi-attempt record. Each entry: { model, status: "ok|model_rejected|shell_snapshot|empty|truncated|failed", duration_ms }
  "codex_status": "OK | FAILED",
  "codex_attempts": [
    { "model": "default", "status": "shell_snapshot" },
    { "model": "o3", "status": "ok" }
  ],
  "codex_summary": { "corroborated": N, "new_verified": N, "new_unverified": N, "disputed": N, "out_of_scope": N },

  "bug_counts": { "critical": 0, "high": 2, "medium": 4, "low": 3 },

  // Status against the immediately-prior baseline (FIXED / STILL_PRESENT / REGRESSED / NOT_RETESTED / SUPPRESSED)
  "previous_baseline_status": { "<issue-key>": "<status with one-line evidence>" },

  // New severity-≥-High items introduced this run (free-form list, used by the Status table)
  "new_critical_or_high_in_this_run": ["..."],

  // Run-over-run trend, computed in Phase 4. Drives the Score Trends table in the report.
  "score_trend": {
    "composite": { "prior": 5.4, "current": 6.0, "delta": 0.6 },
    "personas": [
      { "name": "Brad",   "archetype": "Skimmer",        "prior": 4, "current": 5, "delta": 1 },
      { "name": "Linda",  "archetype": "Careful Reader", "prior": 5, "current": 7, "delta": 2 },
      { "name": "Marcus", "archetype": "Mobile Tapper",  "prior": 7, "current": 6, "delta": -1 }
    ],
    "bug_counts": {
      "critical": { "prior": 2, "current": 0, "delta": -2 },
      "high":     { "prior": 8, "current": 2, "delta": -6 },
      "medium":   { "prior": 9, "current": 4, "delta": -5 },
      "low":      { "prior": 8, "current": 3, "delta": -5 }
    },
    "direction": "improved | regressed | unchanged | first run"
  },

  // Stable cross-run record of every distinct finding. Mutated in place each run.
  "issue_history": {
    "maintenance_score_row_contradiction": {
      "first_seen": "2026-04-26",
      "last_seen":  "2026-04-27",
      "runs_seen":  ["2026-04-26", "2026-04-27"],
      "severity":   "H",
      "state":      "OPEN",
      "title":      "/maintenance cold-start: score and stat-row disagree about overdue",
      "fixed_in_run":       null,
      "suppression_reason": null
    }
  }
}
```

When a baseline exists at start of a run (Phase 0.7):
- Read `issue_history` and `score_trend` to seed the Status + Trend + Recurring tables.
- Offer to reuse the same persona definitions (same names, archetypes, goals) only if the diff vs prior baseline is small.
- Show score deltas: `T1: 4/10 → 5/10 (+1, ▲)`.
- For each entry in `issue_history` with `state: OPEN`, mark FIXED / STILL_PRESENT / REGRESSED in the report's Status table.
- Track bugs new to this run.

In Phase 4, recompute `score_trend` and update `issue_history` per the rules in SKILL.md § "Phase 4: Finish."
