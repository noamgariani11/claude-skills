# Mode D - Live-site review and fixes

The heaviest mode. Measure a shipped page, score it from evidence, then ship
the fixes.

**Use the `browse` skill for anything driving a browser.** Never evaluate from
source alone, and never claim to have rendered a page you did not. If no
browser is available, say so and downgrade explicitly to a source-only review
with every visual pillar marked `--provisional` - a source-only review cannot
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
user rejected with a reason, do not raise it again - unless the surrounding
code changed. Re-raising a rejected finding burns trust faster than missing one.

---

## 2. Measure

### 2a. Static layer (cheap, run it first)

```bash
S=~/.claude/skills/designer-dude/scripts
bash $S/env-check.sh <project-root>       # what this machine can measure AT ALL
bash $S/micro-checks.sh <project-root>
python3 $S/contrast.py --css <the token file>            # or --design-md DESIGN.md
python3 $S/contrast.py --harmony --css <the token file>  # ramps, hue families, temperature
```

Run **both** contrast passes. The first answers "is this legible", the second
answers "do these colours belong to each other", and a palette can pass every
ratio and still look like three products glued together. `color.md` has the
five coherence tests the `--harmony` output maps onto.

Read the file-count line `micro-checks.sh` prints. If it looks far too small
for the project, the stack detection missed something and every count below it
is noise.

**On a Tailwind project, read §15 before anything else in the output.** It pins
the major version, and that decides whether other hits are defects or correct
code - `bg-gradient-to-r` and `flex-shrink-0` are right on v3 and generate **no
CSS at all** on v4. Its other rows roll up rather than stack: a zero
Preflight-cursor-restore explains §1's pointer hits as *one* root cause with one
fix, not N findings, and the token-layer count is the measurable half of
Colour (4) and slop item 5. Interpret the scale counts through
`calibration.md` → "On Tailwind, the framework supplies the denominator", or
you will grade a stock scale as a drifting one. Reference: `tailwind.md`.

### 2b. Rendered layer (the one that matters)

Write the config, then run the probe. Both paths are absolute:

```jsonc
// ~/.cache/designer-dude/probe-config.json
{
  "outDir": "/abs/path/to/repo/.design",
  "label": "dashboard",
  "url": "http://localhost:3000/dashboard",
  "viewports": [[1920,1080],[1440,900],[1024,768],[768,1024],[390,844],[320,720]],
  "dark": true,
  "reducedMotion": true,
  "landscapePhone": true,
  "touchBelowPx": 500,
  "waitMs": 700,
  "fullPage": true,
  "stableScreenshots": true,

  // Override passes: all four default ON. Each re-measures at 1440x900 with
  // ONE user override applied, so any regression is attributable to it.
  "forced-colors": true,   // Windows High Contrast
  "contrast-more": true,   // prefers-contrast: more
  "text-spacing": true,    // SC 1.4.12, the SC's own metrics
  "text-zoom-200": true,   // SC 1.4.4, 200% text at an unchanged viewport

  // Content stress: opt-in, mutates the page, reloads after.
  "stress": true,

  // Applicability is explicit. Read behavioral-verification.md before these.
  "i18n": { "textExpansion": true, "rtl": true },
  "visionDeficiencies": ["achromatopsia", "deuteranopia"],
  "announcements": [
    { "label": "save", "click": "button[type=submit]", "wait": 500,
      "expected": "saved|updated" }
  ],
  "widgets": [
    { "label": "record tabs", "kind": "tablist", "selector": "[role=tablist]" }
  ],

  // The states a happy-path probe never sees. A URL the app already has, or
  // one selector to click.
  "states": [
    { "label": "empty", "url": "http://localhost:3000/properties?filter=none" },
    { "label": "error", "url": "http://localhost:3000/properties/does-not-exist" },
    { "label": "form-invalid", "click": "form button[type=submit]", "wait": 400 }
  ]
}
```

**Configure the states.** Until you do, `probe-report.py` says so in its notes
rather than pretending they were checked - loading, empty, error and
permission-denied are otherwise the one part of the rubric graded by reading
source while everything else is measured. Seeded fixtures are the kindest
content a product ever gets; a layout graded only against them is graded
against the demo, which is what `"stress": true` exists to stop.

```
browser_run_code_unsafe({ filename: "<skill>/scripts/probe-runner.mjs" })
```

It writes `.design/probe-<label>.json`, `.design/screenshots/<label>-*.png`,
and `.design/accessibility/<label>-*.aria.yml` (the browser-computed accessible
tree for each pass), then returns a short summary. Repeat per surface, changing
`label` and `url`.

**This is the evidence.** It covers the viewport sweep, the dark-mode pass, the
reduced-motion pass, the four override passes, any configured states, lab
performance, console errors and failed requests - all of which earlier versions
of this mode graded without ever capturing.

The override passes are read as **deltas against the 1440 baseline**, never as
absolutes: system colours and 200% text legitimately move numbers, so the
finding is always "this override made something worse", which is attributable.
An override the browser refused is recorded `unavailable` and reported as
UNCHECKED - not as clean.

#### The device matrix, and why each row exists

Every row catches something no other row does. Dropping one is fine; dropping
it silently is not - say which you skipped.

| Pass | Catches |
|---|---|
| 1920×1080 | no `max-width`: measure runs past 75ch on a wide monitor |
| 1440×900 | the design target - where everything looks fine |
| 1024×768 | small laptop / tablet landscape; first breakpoint to collapse |
| 768×1024 | tablet portrait; where nav and table decisions land |
| 390×844 **+touch** | the real phone target |
| 320×720 **+touch** | smallest supported (iPhone SE); horizontal overflow appears here, and it is the WCAG 1.4.10 reflow width |
| 844×390 **+touch** | landscape phone - the *short* viewport. `100vh` heroes, sticky headers and fixed bars eat the screen here and nowhere else |
| dark 1440 | contrast in the other theme |
| reduced-motion 1440 | whether the motion guard actually works |

**Narrow passes get real touch emulation** - `pointer: coarse`, `hover: none`,
`maxTouchPoints: 5` - via CDP, because `setViewportSize` only resizes the
window. Without it a "390px" run is a desktop browser in a narrow column:
hover still works, coarse-pointer CSS branches never execute, and the report
would claim mobile coverage it never had. The runner prints `[touch]`,
`[mouse]` or `[NO-EMU]` per row; **if you see `[NO-EMU]` the CDP session was
refused and Responsiveness cannot be graded above provisional.**

The preference passes stay on mouse on purpose. Mixing touch into the dark run
makes a contrast regression and a coarse-pointer regression indistinguishable.

Lab performance is one machine on one network. Label it lab, or re-measure
against a production build (`serve.sh --prod`) before quoting it as a Core Web
Vitals result - the budgets are defined at p75 of real field data.

#### Getting a production build up, when the obvious command refuses

Perf is **half of the Interaction pillar's definition** (weight 10), and it is
the half most often skipped, because dev-server numbers are worthless and the
production command tends to fail for a reason that has nothing to do with
design. Skipping it silently is not an option: grade it from a measurement, or
pass `--perf-unmeasured` to `score.py` and let the pillar cap at A−. Do not
print a letter over an observation.

Work through this before giving up:

1. **Read the project's own docs first.** `CLAUDE.md` / `README.md` /
   `DEPLOY.md` usually document exactly why `build && start` refuses and what
   to point it at. This is the step most often skipped, and the answer is
   almost always already written down.
2. **A refusing production start is usually an environment guard, not a build
   failure** - a role check, a missing secret, a `NODE_ENV=production`
   assertion. Point it at the gate/CI env file the project already keeps for
   this (`.env.gates.local`, `.env.test`, `.env.ci`) rather than editing the
   guard. Never weaken a production safety check to take a measurement.
3. **A static export or preview deploy counts.** A Vercel/Netlify preview URL
   is a production build on production infrastructure - probe that instead.
4. **Failing all three, say what you could not measure**, pass
   `--perf-unmeasured`, and put it in the ledger as a blocker with the reason.
   An unreported gap reads as "checked and fine".

### 2c. Exercise the states - hover and focus, by hand

**Full protocol in `references/browser-verification.md`; load it before this
step.** It carries the `browse` handoff, the four-part state pass, the
screenshot conventions and the memory rules. The short version is below.

**Required, not optional. A screenshot is taken with no pointer over anything
and nothing focused, so a review built only on screenshots grades the rest
state and calls it the design.**

For every *repeated* interactive component on the surface - the list row, the
card, the nav item, the table row, the tab - do this once:

1. `browser_hover` the second instance (not the first; the first is often
   styled specially and the second is what the template really does).
2. Screenshot the container, not the element, so you can see whether the fill
   covers the row, has margins, and lines up with the rule above it.
3. `browser_press_key` Tab to it and screenshot the focus ring on the same
   backdrop.

What this catches that nothing else does:

- A hover fill the colour of the section it sits on - the rule exists, coverage
  reads 100%, and hovering does nothing. The probe now measures this
  (`states.inertHoverFills`), but only for backgrounds it can resolve; the
  screenshot is what catches the rest.
- A fill that stops at the first glyph because the row has no inline padding.
- A fill narrower or wider than the row's own hairline.
- A focus ring that clears the control and disappears against the page.
- Motion that only reveals itself in the transition.

Do it in **both themes** if the product has a dark mode. A hover tint chosen
against paper is routinely invisible on the dark surface, and vice versa.

### 2d. Look at the screenshots

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
- For anything touching a control, check the spec and the severity in
  `components.md` before writing it up. For anything about alignment, read
  `alignment.md` first - a centred hero is not a finding.
- Set `"status": "confirmed"` or `"rejected"` in the findings file. Record the
  reason on every rejection - it suppresses the candidate in future runs.
- Then **add the findings only your eye can see**: hierarchy, voice, IA, taste,
  domain correctness. Same shape, with `"source": "eye"`.

Assign **FINDING-NNN IDs** at this point. One ID = one atomic change. Those IDs
flow into commits, screenshots, the baseline, and the report.

### 3b. Every rejection becomes a precision case - not optional

A rejection is the most valuable output of triage and the only one that has
been evaporating. The reason went into a ledger line, the threshold stayed as
it was, and the next campaign rediscovered the same false positive and argued
it again. A false positive costs more than a miss: it survives triage, it gets
debated, and it teaches the user to distrust the number.

So close the round by turning each one into a permanent guard:

```bash
python3 $S/fixture-case.py --from-findings .design/findings-dashboard.json
# for each one it lists:
python3 $S/fixture-case.py --why "<why this construct is CORRECT>" \
        --html '<the smallest snippet that reproduces it>' \
        --record-in .design/findings-dashboard.json --finding-id P012
node $S/probe-selftest.mjs --precision     # must stay silent
node $S/probe-selftest.mjs --mutations     # isolated defects move; inert churn does not
node $S/probe-selftest.mjs --pipeline      # findings map to severity, score and WCAG cap
node $S/probe-selftest.mjs --runner        # configured browser evidence works end to end
```

If the precision run now reports a candidate, **the threshold is wrong, not the
fixture** - that is the whole point of the exercise, and fixing it at source is
what stops the same argument happening in three months. Triage that compounds
into the rig beats triage that ends in prose.

---

## 4. Score

```bash
python3 $S/score.py --findings .design/findings-dashboard.json \
        --hierarchy B --ia B+ --content B --consistency B \
        [--wcag-fail] [--perf-unmeasured] [--baseline <prior>] \
        [--provisional motion,responsive] \
        --target 90 --out-json .design/scorecard-dashboard.json
```

Rules the script enforces, so do not fight them: eye-only pillars need an
explicit letter; pillars without captured evidence go in `--provisional` and cap
at B+; an unresolved WCAG AA failure caps Overall at C+; unmeasured Core Web
Vitals cap Interaction at A−.

**The ceiling to know before promising anything:** demotion-only scoring means a
card with every defect fixed scores exactly **92.00**. Anything above that needs
an A+ **credit** - a named criterion from `scoring.md`, evidence, 2+ surfaces,
zero open findings on that pillar. `--target 95` prints how many credits the
number would take and what claiming them would mean.

Before writing a single credit, let the measurements try to **falsify** it:

```bash
python3 $S/probe-report.py --credits .design/probe-*.json \
        --emit-credits .design/credits.json
```

Several clauses of every A+ criterion are measurable, and a measurable clause
that fails means the credit is not available however good the argument is:
`BLOCKED` is final. `OPEN` is not a credit either - it means the machine
clauses hold and the `??` ones are still yours to argue. The stubs it writes
are `status: "candidate"`, which `score.py` refuses to count, deliberately: this
tool can only ever block a credit, never award one. That keeps the one part of
the scale that moves upward attached to the same rig as the rest of it.

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

### 4b. Hand the A-graded surfaces to `user-test`

All eleven pillars grade **form**. Not one of them asks whether the design
serves the task, which is why this skill has always carried the escape hatch
"if the score is high and the product is still bad, say that instead of the
number". That sentence is an admission that the rubric has a hole in it, and a
disclaimer is a weak patch for a hole you can measure through.

So measure through it. After scoring, hand the surfaces that graded **A or
above** to the `user-test` skill (or a project-specific one - `user-test-miskari`
here), focused rather than broad:

```
Skill(user-test) with: --focus <surface>   # one call per A-graded surface
```

Then read the result against the scorecard:

| What the personas hit | What it becomes |
|---|---|
| A task **failed** on an A-graded surface | a `critical` finding on Hierarchy (the eye went to the wrong thing) or Content (the words did not say what to do) |
| A task completed, but by a route the design did not intend | a `major` finding on Hierarchy or IA |
| Persona confusion with no failed task | a `minor` finding, or a note - do not inflate it |

This is the only mechanism in the skill that can move a grade **down** on
evidence the probe cannot see, which is exactly why it belongs after an A and
not after a C. A rubric that can only find its own kind of defect will always
end a campaign agreeing with itself.

Say in the report which surfaces went through this and which did not. An
A-graded surface nobody tried to use is an A on the drawing, not on the product.

One caveat worth knowing: state coverage (hover, focus-visible, disabled) is
measured by matching stylesheet rules, which **cannot be read across origins**.
On a page whose CSS is served from a CDN the probe reports
`inaccessibleStylesheets` and `probe-report.py` refuses to grade it rather than
reporting 0% coverage as a defect. Probe the local build for that signal.

---

## 5. Triage before touching code

- **High** - breaks first impression or trust: WCAG fails, eye cannot find the
  primary CTA, broken mapping, any slop brand-killer. Fix first.
- **Medium** - felt subconsciously: spacing drift, radius inconsistency, weak
  hierarchy, color noise, missed perf budgets.
- **Polish** - nits separating good from great. Only if budget remains.
- **Deferred** - not fixable from source (third-party widget, copy owned by
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
   repository's existing commit convention** - run `git log --oneline -20` and
   read it first. If the repo uses Conventional Commits,
   `style(design): FINDING-NNN <description>` fits. If it uses plain imperative
   subjects, write `Fix tag chip contrast (FINDING-003)`. Do not impose a
   convention the repo does not use.
7. **Re-test.** Re-run the probe for the affected surface, confirm the specific
   measurement moved, screenshot to `screenshots/finding-NNN-after.png` paired
   with `-before.png`, and check the console for new errors.
8. **Classify:** **verified** (re-probe confirms, no new errors) ·
   **best-effort** (applied, not fully verifiable - needs auth or a specific
   state) · **reverted** (regression detected → `git revert HEAD` → mark
   deferred).

### Building a dark mode

This is the one fix that is a **build**, not an edit, and it has its own rules
because the generic ones would either block it or let it sprawl.

Do it when `color.md` section 5a says a trigger fired — the product promises a
dark mode, the audience expects one, orphaned dark tokens show someone started
one, or the user asked. Do **not** do it on taste alone; an absent dark mode is
not a finding by default (`scoring.md`).

Two shapes, and they are not the same job:

1. **A dark theme exists but only the OS can reach it.** Rekey the tokens from
   the media query to `[data-theme="dark"]`, add the pre-paint script and the
   control. The values are already designed, so this is one CSS block, one
   script, one component. Land it as a normal fix.
2. **No dark theme exists.** Derive the values first (section 5 of `color.md`),
   measure every pairing the components actually use with `contrast.py` in the
   new theme, *then* add the switch. Announce it before starting: it is bigger
   than a fix and it is the one item that can eat a whole run's budget.

Before starting shape 2, check the product has a token layer. If colour is
restated at three hundred call sites (`bg-white text-gray-900` on every
element), the honest answer is "the token layer is the prerequisite" — report
it scoped and costed and let the user decide. Do not begin a three-hundred-file
refactor inside a design fix loop.

Either shape counts as **one** finding and is exempt from the 3-file stop
condition — a theme touches a stylesheet, a document head and a nav by
construction. It is not exempt from anything else: atomic commits, the probe
re-run, and the regression gate all still apply.

Verification is specific, and a screenshot of the home page is not it:

- Cold-load a page with the switch set each way. **No flash of the wrong theme
  on either.** This is the failure this feature ships with most often.
- Toggle both directions, then reload, then navigate to another route. The
  choice survives all three or it is not done.
- Re-run the probe's dark pass over every surface, not just the one you were
  looking at. `contrast.py` on the pairings, both themes.
- Check the console for hydration warnings — the pre-paint script mutates
  `<html>` before the framework sees it, and a missing `suppressHydrationWarning`
  (or its equivalent) shows up here.
- Look at the browser's own chrome in dark: scrollbar, `<select>` popup, caret.
  Light chrome means `color-scheme` did not follow the switch.
- Check the control at 390px, not only at 1440. It is a header control, and the
  mobile header is the row that runs out of space.

### Stop conditions

**Stop and check in when any one is true:**

- **Any revert.** Something was misunderstood. Do not proceed on momentum.
- **A single fix touches more than 3 component files**, or a token cascade
  exceeds 10 consumers.
- **You are about to touch a file not tied to the finding.** That is scope
  creep; it is where design fixes turn into regressions.
- **Every 10 fixes** - summarize and confirm before continuing.
- **A fix requires a design decision you cannot make** (which of two things is
  the primary action; what the product's voice is). Ask; do not invent it.
- **Hard cap: 30 fixes per run.** No exceptions.

When you stop, show what is done, what is left, and the running score delta.
Then ask.

---

## 7. Final audit

**Snapshot the probes before the first fix** (`cp .design/probe-*.json
.design/baseline/`). Everything below depends on having a before.

1. **Re-probe every surface you changed** - and, if you touched a token, at
   least one surface you did **not** intend to change. A token reaches
   everything, and a cascade regression on an unvisited page is invisible until
   a user finds it. Not a diff-based assumption: a grade may only improve on
   fresh measurement.
2. **Run the regression gate before you re-score:**

   ```bash
   python3 $S/regress.py --before .design/baseline/probe-*.json \
                         --after  .design/probe-*.json \
                         --json   .design/regressions.json
   ```

   It matches surfaces by label and runs by viewport tag, and exits 1 on any
   critical or major regression. Then run the project's own gates
   (`typecheck`, `lint`, `build`) - the build is usually the only thing that
   catches a server/client bundle-boundary break, and a component edit is
   exactly how that happens. Protocol and the revert rules: `regression.md`.
3. **Look at the before/after screenshots** at 1440, 390 and the dark pass.
   Five seconds each, and it catches the class of regression that has no
   metric: a shifted layout, a component that lost its shape, text that now
   wraps differently.
4. Re-score with `--baseline <prior overall>`.
5. **If anything regressed - a score, a metric, or a gate - warn prominently,
   at the top, above the good news.** Something went sideways, and a report
   that leads with the improvement has buried the finding.
6. Re-run `micro-checks.sh` if you touched tokens, and `contrast.py --harmony`
   if you touched colour.
6b. **Record the ratchet, so the round defends itself:**

   ```bash
   bash $S/ratchet.sh --emit <project-root>     # writes .design/ratchet.json
   ```

   Then wire the check into the project's own gate (this repo runs CI as
   `.githooks/pre-push`, never a workflow file):

   ```bash
   bash ~/.claude/skills/designer-dude/scripts/ratchet.sh . || exit 1
   ```

   It is static, DB-free and takes a second, and it can only fail on a **new**
   regression - so it is safe to wire in on day one. Without it, every count
   this round drove down starts drifting back up on the next feature branch and
   nobody notices until the next campaign re-measures and does the work twice.
7. **Write `.design/baseline.json`** for the next run:

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

Everything lives under **`.design/`** at repo root - not scattered through it:

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
  accessibility/
    <label>-1440x900.aria.yml computed roles, names, states, hierarchy
```

Offer to gitignore `.design/screenshots/` and `.design/accessibility/`, then
keep the JSON + reports committed - the baseline is only useful if it survives,
while PNGs are large and accessibility trees contain rendered names and text
that may be sensitive. Do not commit any artifact without saying so.

**One file per surface, kept.** `probe-<label>.json` and `findings-<label>.json`
are per surface and are never reused for a different one: change `label`
whenever you change `url`. A run that probes four surfaces and leaves one
`probe-dashboard.json` behind has thrown away its own evidence - and it shows up
next round as cross-surface consistency silently degrading from *measured* to
*felt*, because `probe-report.py --compare` needs **3+ files that still exist**.
Before scoring, check you have one probe file per surface you claim to have
reviewed. If you do not, you did not review them.

---

## Output format - inline first

**The user reads the terminal, not the report file.** Always surface the
scorecard and top-fixes chart inline, even when you also write the report.
Never hide findings in a file and call the job done: the report is the archive,
not the delivery.

**`voice.md` governs how it reads.** Verdict in the first two lines, regressions
before good news, tables instead of prose lists, five fixes instead of twenty,
and none of the tells. A review nobody finishes is a review nobody actioned,
and you spent the whole run earning the right to be read.

**1. Headline grades** - one line. `score.py` prints it:

```
Overall: B (84) · Craft: B+ · Clarity: B · Brand Coherence: B− · Slop: B−
```

**2. Status vs prior baseline** - the table from step 1, if a baseline existed.

**3. Per-pillar table** - 11 rows, 4 columns (Pillar · Grade · Why · Evidence).
Keep each `Why` to one clause; `Evidence` names the measurement or the
screenshot. Mark provisional pillars.

**4. Top-fixes chart** - always a table, never a prose list:

```
| # | Fix                                           | Pillar     | Effort | Points |
|---|-----------------------------------------------|------------|:------:|:------:|
| 1 | Swap Inter for Instrument Serif on headlines  | Typography |  45m   | +2.10  |
| 2 | Fix tag-chip contrast (slate-500 → slate-300) | A11y       |   2m   | +1.12  |
| 3 | Delete duplicate radial glow (layout.tsx:104) | Color      |   5m   | +0.30  |
```

`Points` comes from `score.py --target`, so the ranking is arithmetic rather
than vibes. Five rows max; rank by points per minute and cut the rest.

**5. Path to the target** - paste `score.py --target`'s per-pillar table, and
say plainly if the target is unreachable from here.

**6. The verdict, in one plain line** - beside the number, never instead of it:

> **Would I ship it, and would I show it to another designer?** Ship it, yes.
> Show it, not yet - it is correct everywhere and memorable nowhere.

Write this before you look at the composite, so the number does not write it for
you. If the verdict and the score disagree, **the verdict is the finding**: say
so, and name what the rubric did not capture. That gap is a bug in this skill
and it is worth fixing here rather than hiding behind a grade. A number nobody
would defend in a sentence of English is a number that has stopped measuring.

**7. Atomic-wins offer** - "Want me to apply #1, #2, #3 now?" Do not apply
without consent.

Close with a PR-ready one-liner:

> Design review of N surfaces found M issues, fixed K. Score X → Y, slop X → Y.
> Surfaces not reached: <list, or "none">.
