# Report Template

Write to `docs/reports/marketing-test-reports/marketing-test-<YYYYMMDD-HHMMSS>.md`.

**Write for a marketer, not a QA lead.** Lead with the verdict and the content autopsy. The bug
table is supporting evidence, not the headline.

---

```markdown
# Sheevook Marketing Test — <YYYY-MM-DD HH:MM>

Mode: full | diff | focus:<surface> | output-only
URL: http://localhost:3000   Branch: <branch>   Commit: <sha>
AI layer: live-anthropic | deterministic-fallback     <-- decides how Output was judged
Browser: <real Chromium / MCP / none - text-only>
Environment notes: <sibling sessions, seed state, account residue>

## Verdict

<Two or three sentences. Would a senior marketing team run their launch on this?
What is the ceiling, and what single thing is holding it there?>

## The two scores

| Axis | Score | Trend |
|---|---|---|
| Product UX | X/10 | +/- vs prior |
| Marketing Output Quality | X/10 | +/- vs prior (same ai_layer only) |

<If UX is high and Output is low - or the reverse - THAT CONTRAST IS THE HEADLINE. Write it here,
in one blunt sentence. A tool that is a joy to use and emits content nobody would post is a
failed product, and this section is where that gets said.>

Task completion: N/M personas (X%) - A: Full, B: Partial (blocked at ...), ...

## Content autopsy

<The most important section. For each artifact, verbatim, with its ruling.>

### <platform> - <RULING: POST IT | REWRITE | WOULD BE REMOVED>
> <the generated content, verbatim, unmodified>

**<Expert name>:** <the practitioner's reason, in their voice. Specific. What exactly is wrong,
and what would they have written instead?>
Hook X/5 - PoV X/5 - Nativeness X/5 - Specificity X/5 - Spread X/5 - **Veracity X/5**

<Veracity 1 CAPS this artifact at REWRITE and 4/10 no matter what the other five say - and is
WOULD BE REMOVED + critical on Reddit/HN. Name the fabricated claim and what you checked it
against (master / brand.facts / brand.valueProps / brand links).>

### Veracity + did the app's own lenses catch it?

<Mandatory every run, even when every artifact is clean - "nothing to catch" and "nothing was
caught" are different facts and only the first is good news.>

| Artifact | Fabricated claim | App verdict on it | Detector caught it? |
|---|---|---|---|
| tumblr | opening anecdote invented | 83 green "Solid" | **NO** |

<A fabrication the app rendered green is a SECOND finding, higher severity than the artifact
itself: the artifact is one bad post, a blind detector passes every future one. File both.>

### Is the tailoring real?
<Mandatory every run. Do the variants differ structurally, or only in length and hashtag count?
State the result even when the answer is "yes, tailoring is real" - a confirmed negative is worth
recording.>

## Grounding integrity (workspace discovery)

<Mandatory whenever discovery ran. CLAUDE.md promises it never invents a fact/price/quote/
competitor, and never overwrites a user-filled field. Both are testable; both are critical.
A fabricated fact here propagates into EVERY AI call via brandContext().>

| Check | Result |
|---|---|
| Facts in derived profile that are NOT on the source page | none / <list - each is critical> |
| Sparse/empty-page test (did it fill the vacuum?) | passed / **INVENTED** |
| Hand-filled brand fields survived discovery untouched | yes / **OVERWRITTEN** |
| Usable profile with ANTHROPIC_API_KEY unset (deterministic-first) | yes / no |

## Panel confidence (calibration — every 5th run, or --calibrate)

Planted: 5 | Caught: N | Missed: M | **False-negative rate: M/5**
Per lane: platform-expert _/_ · adversarial _/_ · virality _/_ · brand _/_
Repo suite caught on its own: _/5

<For each miss: what it was, who should have caught it, and WHY they didn't. The why is the
product of this exercise, not the ratio. A 2+/5 FN rate means fix the skill before trusting
another run.>

<Report the PER-LANE rate, not just the aggregate: at run #14 the adversarial persona caught 4 of
5 including plants it did not own, so a perfect aggregate hid largely unresolved owning lanes. A
plant caught only by a cross-catch is a MISS for its owner.>

**If calibration is overdue, this section still appears** and says so:

> Calibration overdue by N runs — this panel's false-negative rate is unmeasured, so "no critical
> findings" in this report is not evidence of absence.

## Domain accuracy findings

| # | Platform | Claim in code | Reality | Citation | Severity | Disposition |
|---|---|---|---|---|---|---|
| D1 | twitter | `hardLimit: 280` | correct | ground-truth STABLE | - | - |
| D2 | ... | | | research/platforms/twitter-x.md §4 | high | RESEARCH-DRIFT |

<Ungrounded claims go BELOW, under [UNVERIFIED]. They are named so the next run can chase them,
and they are NOT scored as defects and NOT handed to Phase 5.>

### [UNVERIFIED] - could not be grounded this run
- <claim> - needs: <what would ground it>

## Platform coverage

| Platform | Ran this run? | Last covered | Findings |
|---|---|---|---|
| twitter | yes | 2026-07-11 | D2, O1 |
| tiktok | **no** | never | - |
...

<Every skipped platform is named. Silent coverage gaps are how a wrong rule survives six runs.>

## Panel sessions

### A - Dana Whitmore (Fractional CMO)
Goal: <...>  Completion: Full/Partial/Failed  Score: X/10
<Narrative with THINKING blocks and PULSE readings. Findings tagged
[OBSERVED]/[INFERRED]/[SIMULATED] with evidence.>
Would she switch? <...>

<...repeat for B-F and each platform expert...>

## Where the panel disagreed

<Conflicts are signal. B's edge is F's ban risk; D's sharp voice is A's brand risk. A product
decision that pleases all six usually pleases none. Surface the real tensions here.>

## Consolidated findings

| # | Severity | Finding | Confidence | Evidence | Found by | Disposition |
|---|---|---|---|---|---|---|
| 1 | critical | ... | [OBSERVED] | screenshot / console / file:line | C | FIX-NOW |

Every finding has a disposition: FIX-NOW | BACKLOG | RESEARCH-DRIFT | FALSE-POSITIVE |
UNVERIFIED | PRODUCT-BOUNDARY. A finding with no disposition is a bug in the run.

## Status vs. prior baseline

| Prior finding | Status |
|---|---|
| ... | FIXED / STILL_PRESENT / REGRESSED |

<Anything STILL_PRESENT for 3+ runs is structural. Say so.>

## Suppressed by prior learnings

<Verified false positives that came up again. List them so the user can audit the suppression -
never silently drop.>

## Competitor delta

| Tool | What they do better | What Sheevook does better |
|---|---|---|
| Buffer / Hootsuite / Later / Typefully / AdCreative.ai | ... | ... |

**What would make a marketer switch?** <...>
**What would stop them?** <...>
```

---

## `baseline.json` schema

```json
{
  "date": "2026-07-11",
  "report": "marketing-test-20260711-143000.md",
  "previous_baseline": "<prior report filename or null>",
  "mode": "full",
  "url": "http://localhost:3000",
  "branch": "main",
  "commit": "<sha>",
  "ai_layer": "deterministic-fallback",
  "browser": "real headless Chromium via no-root sysroot",
  "environment_note": "sibling claude session live in this tree; read-only on code",
  "seed_state": "fresh | existing-account | reseeded",

  "prior_fixes_survived": {
    "checked": true,
    "present": ["lib/community/engagement.ts:158", "lib/tailoring/titles.ts:164"],
    "missing": [],
    "note": "missing != regressed - a fix lost to a sibling checkout is NOT a product regression"
  },

  "scores": { "product_ux": 6, "marketing_output": 4 },
  "task_completion_rate": "5/6",

  "panel": [
    { "id": "A", "name": "Dana Whitmore", "role": "Fractional CMO",
      "goal": "...", "completion": "Full", "score": 6, "would_switch": "no - not yet" }
  ],
  "persona_coverage": {
    "A": "2026-07-18", "B": "2026-07-18", "C": "2026-07-18",
    "D": "2026-07-15", "E": "2026-07-18", "F": "2026-07-18"
  },
  "personas_skipped": [
    { "id": "D", "reason": "data lane requires solo run", "owed_since_runs": 2 }
  ],

  "platform_experts_ran": ["twitter", "reddit", "linkedin"],
  "platform_coverage": {
    "twitter": "2026-07-17", "linkedin": "2026-07-18", "reddit": "2026-07-17",
    "instagram": "2026-07-17", "tiktok": "2026-07-17", "facebook": "2026-07-17",
    "youtube": "2026-07-18", "threads": "2026-07-18", "pinterest": "2026-07-17",
    "snapchat": "2026-07-18", "tumblr": "2026-07-17", "hackernews": "2026-07-17",
    "bluesky": null, "discord": null, "telegram": null
  },
  "platforms_without_expert_card": [],

  "grounding_integrity": {
    "discovery_ran": true,
    "invented_facts": [],
    "sparse_page_test": "passed",
    "user_fields_preserved": true,
    "deterministic_first_ok": true
  },
  "calibration": {
    "due": false,
    "last_run": "2026-07-17",
    "runs_overdue": 0,
    "planted": 5, "caught": 5, "missed": 0,
    "false_negative_rate": "0/5",
    "per_lane": { "platform_expert": "2/2", "adversarial": "1/1", "virality": "1/1", "brand": "1/1" },
    "cross_catches": [],
    "repo_suite_caught": "1/5"
  },

  "artifacts": [
    { "platform": "reddit", "ruling": "WOULD BE REMOVED",
      "hook": 2, "pov": 2, "nativeness": 1, "specificity": 3, "spread": 2,
      "veracity": 1,
      "veracity_note": "opening anecdote fabricated - not in master or brand.facts",
      "app_lenses_caught_it": false,
      "reason": "reads as self-promo; rule 1 of most subs" }
  ],
  "tailoring_is_real": true,

  "domain_accuracy_findings": [
    { "id": "D2", "platform": "twitter", "severity": "high",
      "claim": "...", "reality": "...", "citation": "research/platforms/twitter-x.md §4",
      "disposition": "RESEARCH-DRIFT" }
  ],
  "unverified": ["..."],

  "bug_counts": { "critical": 0, "high": 3, "medium": 5, "low": 4 },
  "previous_baseline_status": { "fixed": [], "still_present": [], "regressed": [] },
  "suppressed": ["oauth_tokens_plaintext", "shortlink_bad_slug_302"],
  "post_run_implementation": null
}
```

## `learnings.md` — ledgers FIRST, then a rolling 5-run window

**The file must open with the routing block below**, because Phase 0 reads it to route the run and
a debt recorded below the fold does not get paid. Bluesky sat at `NEVER` for six runs and persona
D went unfielded while both were faithfully recorded — in prose, far down the file. **Target the
whole file under ~200 lines**; promote durable facts out to `harness.md` / the expert cards /
the suppression list rather than letting run blocks accumulate them. See SKILL.md Phase 3
hygiene rules.

```markdown
# Marketing test learnings

## Platform coverage ledger        <- FIRST. Every key in platforms.ts, NEVER if unaudited.
twitter: 2026-07-17 | linkedin: 2026-07-18 | ... | bluesky: NEVER | discord: NEVER | telegram: NEVER

## Persona ledger
A: 2026-07-18 | B: 2026-07-18 | C: 2026-07-18 | D: 2026-07-15 (OWED) | E: 2026-07-18 | F: 2026-07-18

## Calibration
last: 2026-07-17 (run #14) | FN rate 0/5 | due at run #19 | OVERDUE BY: 0

## Next run must do
1. <the owed persona>  2. <the NEVER platform>  3. <the structural item>
```

Then, below that, prepend a run block:

```markdown
## Run YYYY-MM-DD HH:MM (<mode>)
- **environment:** <ports, browser, ai_layer, sibling sessions, seed state>
- **prior fixes survived:** <present / missing - missing is NOT a regression>
- **ground-truth promoted:** <VOLATILE facts verified live this run -> update domain-accuracy.md>
- **verified-false-positive:** <finding> - <why it is not a bug. Never re-flag.>
- **regression-risk:** <what to re-check next run and how>
- **open findings:** <carried forward, with age in runs, EACH WITH file:line evidence - not a
  summary sentence. A brief is not evidence: carrying a prior run's PROSE as fact has produced a
  false finding twice. A STILL_PRESENT claim must be re-proven, or it is UNVERIFIED.>
- **structural (3+ runs):** <anything STILL_PRESENT three runs running>
```
