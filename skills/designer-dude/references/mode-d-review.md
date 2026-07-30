# Mode D — Live-site review and fixes

The heaviest mode. Measure a shipped page, score it from evidence, then ship
the fixes.

**Use the `browse` skill for anything driving a browser.** Never evaluate from
source alone, and never claim to have rendered a page you did not. If no
browser is available, say so and downgrade explicitly to a source-only review
with every visual pillar marked `--provisional` — a source-only review cannot
honestly grade Hierarchy, Motion, or the user-eye filter.

**Check `free -g` first.** Under ~8GB available, say so and stop rather than
starting a browser and a dev server on top of it.

---

## 0. Decide what you are reviewing, and get in

Two things kill a run before it starts: reviewing the wrong surface, and
reviewing only the pages that do not need a login.

**Pick surfaces, not pages.** A product's design lives on 3–5 representative
surfaces: the densest list/table, the most complex form, a detail page, an
empty state, and one error state. Reviewing the marketing homepage and calling
it a product review is the most common way this mode produces a useless score.

**Get past the login.** If the product has one, the interesting design is
behind it, and "I reviewed the public pages" must never be presented as a
product review.

- Look for an existing authenticated session first: a Playwright storage state
  the project already produces (`pnpm ut:login` or similar in `package.json`),
  a seeded dev account in `.env.example` / `prisma/seed.*` / the README.
- The Playwright MCP browser keeps cookies for the whole session, so **log in
  once** and every later probe run inherits it.
- Never use real user credentials and never register a real third-party
  account. If there is no test account, ask for one, and until you have it,
  **name the surfaces you could not reach** rather than scoring around them.
- `probe-runner.mjs` runs in the current browser context, which is exactly why
  the login carries over.

**Note on tooling.** The runner uses `browser_run_code_unsafe` with a
`filename`, which is how the probe source and its JSON stay out of context. Use
it against local dev and seeded test accounts. On a page holding a **real
user's** authenticated session, do not: use `browser_evaluate` with a
`filename` to save the result instead, and paste the probe body.

---

## 1. Load the prior baseline first

Check `.design/baseline.json`. If it exists, read it: it holds the previous
run's per-pillar grades, overall score, and every finding with its resolution.

Open the report with a **status table** rather than starting from zero:

| ID | Finding | Prior | Now |
|---|---|---|---|
| FINDING-003 | Tag chip contrast 2.9:1 | High | **FIXED** |
| FINDING-007 | Radius scale has 6 values | Medium | **STILL PRESENT** |
| FINDING-011 | Hero accent covers 25% | Low | **REGRESSED** |

This is what turns repeat reviews into progress instead of a treadmill.
Without it every run re-litigates the same list and the user cannot tell
whether the work is landing.

**Suppress confirmed false positives.** If the baseline records a finding the
user rejected with a reason, do not raise it again — unless the surrounding
code changed. Re-raising a rejected finding burns trust faster than missing one.

---

## 2. Measure

### 2a. Static layer (cheap, run it first)

```bash
S=~/.claude/skills/designer-dude/scripts
bash $S/micro-checks.sh <project-root>
python3 $S/contrast.py --css <the token file>      # or --design-md DESIGN.md
```

Read the file-count line `micro-checks.sh` prints. If it looks far too small
for the project, the stack detection missed something and every count below it
is noise.

### 2b. Rendered layer (the one that matters)

Write the config, then run the probe. Both paths are absolute:

```jsonc
// ~/.cache/designer-dude/probe-config.json
{
  "outDir": "/abs/path/to/repo/.design",
  "label": "dashboard",
  "url": "http://localhost:3000/dashboard",
  "viewports": [[1440,900],[1024,768],[768,1024],[390,844],[320,720]],
  "dark": true,
  "reducedMotion": true,
  "waitMs": 700,
  "fullPage": true
}
```

```
browser_run_code_unsafe({ filename: "<skill>/scripts/probe-runner.mjs" })
```

It writes `.design/probe-<label>.json` plus `.design/screenshots/<label>-*.png`
and returns a ~15-line summary. Repeat per surface, changing `label` and `url`.

**This is the evidence.** It covers the viewport sweep, the dark-mode pass, the
reduced-motion pass, lab performance, console errors and failed requests — four
things earlier versions of this mode graded without ever capturing.

Lab performance is one machine on one network. Label it lab, or re-measure
against a production build (`serve.sh --prod`) before quoting it as a Core Web
Vitals result — the budgets are defined at p75 of real field data.

### 2c. Look at the screenshots

Read them. Actually look. The probe cannot tell you where the eye goes, whether
the primary action is obvious, whether the page looks decided or assembled, or
whether the copy is true. That is the half of the job that is yours, and it
carries 29 points (Hierarchy 15 + Content 10 + IA 4) before Typography's
judgement calls are counted.

---

## 3. Judge, then confirm

```bash
python3 $S/probe-report.py .design/probe-dashboard.json \
        --emit-findings .design/findings-dashboard.json
```

**Every row is a CANDIDATE.** Confirm each one before it becomes a finding:

- Open the selector in the browser or the source and look at it.
- Check it against the **does NOT dock for** list in `scoring.md`. Several
  confident-sounding candidates are the correct engineering choice.
- Set `"status": "confirmed"` or `"rejected"` in the findings file. Record the
  reason on every rejection — it suppresses the candidate in future runs.
- Then **add the findings only your eye can see**: hierarchy, voice, IA, taste,
  domain correctness. Same shape, with `"source": "eye"`.

Assign **FINDING-NNN IDs** at this point. One ID = one atomic change. Those IDs
flow into commits, screenshots, the baseline, and the report.

---

## 4. Score

```bash
python3 $S/score.py --findings .design/findings-dashboard.json \
        --hierarchy B --ia B+ --content B --consistency B \
        [--wcag-fail] [--baseline <prior>] [--provisional motion,responsive] \
        --target 90 --out-json .design/scorecard-dashboard.json
```

Rules the script enforces, so do not fight them: eye-only pillars need an
explicit letter; pillars without captured evidence go in `--provisional` and cap
at B+; an unresolved WCAG AA failure caps Overall at C+.

Grade the **cross-page consistency** letter only after probing 3+ surfaces. Get
the mechanical half measured rather than felt:

```bash
python3 $S/probe-report.py --compare .design/probe-*.json
```

It reports whether the primary face, radius scale, type scale and spacing scale
are shared, names the one-off tokens ("only this surface uses radius 22"), and
suggests a letter. Confirm it against the screenshots before passing
`--consistency`: matching tokens are necessary for a product to look like
itself, not sufficient.

One caveat worth knowing: state coverage (hover, focus-visible, disabled) is
measured by matching stylesheet rules, which **cannot be read across origins**.
On a page whose CSS is served from a CDN the probe reports
`inaccessibleStylesheets` and `probe-report.py` refuses to grade it rather than
reporting 0% coverage as a defect. Probe the local build for that signal.

---

## 5. Triage before touching code

- **High** — breaks first impression or trust: WCAG fails, eye cannot find the
  primary CTA, broken mapping, any slop brand-killer. Fix first.
- **Medium** — felt subconsciously: spacing drift, radius inconsistency, weak
  hierarchy, color noise, missed perf budgets.
- **Polish** — nits separating good from great. Only if budget remains.
- **Deferred** — not fixable from source (third-party widget, copy owned by
  another team, backend-rendered asset). Mark and move on regardless of impact.
  It still counts against the grade: a defect nobody can fix here is one the
  user is still shipping.

Sort by **points per hour**, not severity alone. `score.py --target` names which
pillars actually move the composite; a perfect Motion pillar buys at most 4
points, Typography buys 15.

---

## 6. The fix loop

Mode D is actionable, not advisory. A review ending at "here is what is wrong"
is half a skill. Run this unless the user said **report only**.

Per finding, in impact order:

1. **Locate source.** Grep for the class, component, or token. Touch only files
   tied to the finding. Prefer token/CSS changes over structural rewrites.
2. **Token cascade check.** If changing a DESIGN.md token, enumerate every
   consumer *before* editing. If the cascade exceeds 10 files, stop and ask.
3. **Never regress DESIGN.md.** If a fix requires changing an established
   token, stop and ask. DESIGN.md is the source of truth.
4. **Fix.** Minimal change. No refactors, no "while I'm here" cleanup, no
   unrelated edits. CSS/token > component edit > structural change.
5. **Verify contrast fixes with the calculator**, not by eye:
   `contrast.py "<new>" "<surface>"` also prints the nearest passing colour with
   the hue held.
6. **Commit atomically. One commit per fix, never bundled.** **Match the
   repository's existing commit convention** — run `git log --oneline -20` and
   read it first. If the repo uses Conventional Commits,
   `style(design): FINDING-NNN <description>` fits. If it uses plain imperative
   subjects, write `Fix tag chip contrast (FINDING-003)`. Do not impose a
   convention the repo does not use.
7. **Re-test.** Re-run the probe for the affected surface, confirm the specific
   measurement moved, screenshot to `screenshots/finding-NNN-after.png` paired
   with `-before.png`, and check the console for new errors.
8. **Classify:** **verified** (re-probe confirms, no new errors) ·
   **best-effort** (applied, not fully verifiable — needs auth or a specific
   state) · **reverted** (regression detected → `git revert HEAD` → mark
   deferred).

### Stop conditions

**Stop and check in when any one is true:**

- **Any revert.** Something was misunderstood. Do not proceed on momentum.
- **A single fix touches more than 3 component files**, or a token cascade
  exceeds 10 consumers.
- **You are about to touch a file not tied to the finding.** That is scope
  creep; it is where design fixes turn into regressions.
- **Every 10 fixes** — summarize and confirm before continuing.
- **A fix requires a design decision you cannot make** (which of two things is
  the primary action; what the product's voice is). Ask; do not invent it.
- **Hard cap: 30 fixes per run.** No exceptions.

When you stop, show what is done, what is left, and the running score delta.
Then ask.

---

## 7. Final audit

1. **Re-probe every surface you changed.** Not a diff-based assumption — a grade
   may only improve on fresh measurement.
2. Re-score with `--baseline <prior overall>`.
3. **If any score regressed, warn prominently, at the top.** Something went
   sideways.
4. Re-run `micro-checks.sh` if you touched tokens.
5. **Write `.design/baseline.json`** for the next run:

```json
{
  "date": "2026-07-30",
  "surfaces": [
    {"label": "dashboard", "url": "/dashboard", "overall": 84.2,
     "pillars": {"typography": "B-", "hierarchy": "C", "...": "..."}},
    {"label": "property-detail", "url": "/properties/1", "overall": 81.0,
     "pillars": {"...": "..."}}
  ],
  "consistency": "B",
  "overall": 82.6,
  "slop": "B-",
  "provisional": ["motion"],
  "cappedByWcag": false,
  "findings": [
    {"id": "FINDING-003", "summary": "Tag chip contrast 2.9:1", "pillar": "color",
     "severity": "critical", "status": "fixed", "commit": "a1b2c3d",
     "verifiedBy": "probe re-run: 0 failures"},
    {"id": "FINDING-007", "summary": "Radius scale has 6 values", "pillar": "craft",
     "severity": "major", "status": "rejected",
     "note": "user: intentional, three are theme-specific"}
  ]
}
```

Findings the user rejected keep `"status": "rejected"` plus the reason, and are
suppressed on future runs.

---

## Where files go

Everything lives under **`.design/`** at repo root — not scattered through it:

```
.design/
  probe-<label>.json          measurements
  findings-<label>.json       candidates + your confirmations
  scorecard-<label>.json      score.py --out-json
  baseline.json               cross-run state
  audit-<label>-<date>.md     the written report
  screenshots/
    <label>-1440x900.png      per-viewport, per-run
    finding-NNN-before.png
    finding-NNN-after.png
```

Offer to gitignore `.design/screenshots/` and keep the JSON + reports committed
— the baseline is only useful if it survives, and the PNGs are large. Do not
commit anything into the user's repo without saying so.

---

## Output format — inline first

**The user reads the terminal, not the report file.** Always surface the
scorecard and top-fixes chart inline, even when you also write the report.
Never hide findings in a file and call the job done: the report is the archive,
not the delivery.

**1. Headline grades** — one line. `score.py` prints it:

```
Overall: B (84) · Craft: B+ · Clarity: B · Brand Coherence: B− · Slop: B−
```

**2. Status vs prior baseline** — the table from step 1, if a baseline existed.

**3. Per-pillar table** — 11 rows, 4 columns (Pillar · Grade · Why · Evidence).
Keep each `Why` to one clause; `Evidence` names the measurement or the
screenshot. Mark provisional pillars.

**4. Top-fixes chart** — always a table, never a prose list:

```
| # | Fix                                           | Pillar     | Effort | Points |
|---|-----------------------------------------------|------------|:------:|:------:|
| 1 | Swap Inter for Instrument Serif on headlines  | Typography |  45m   | +2.10  |
| 2 | Fix tag-chip contrast (slate-500 → slate-300) | A11y       |   2m   | +1.12  |
| 3 | Delete duplicate radial glow (layout.tsx:104) | Color      |   5m   | +0.30  |
```

`Points` comes from `score.py --target`, so the ranking is arithmetic rather
than vibes. Five rows max; rank by points per minute and cut the rest.

**5. Path to the target** — paste `score.py --target`'s per-pillar table, and
say plainly if the target is unreachable from here.

**6. Atomic-wins offer** — "Want me to apply #1, #2, #3 now?" Do not apply
without consent.

Close with a PR-ready one-liner:

> Design review of N surfaces found M issues, fixed K. Score X → Y, slop X → Y.
> Surfaces not reached: <list, or "none">.
