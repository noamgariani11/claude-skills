# Behavioral, internationalization, and cross-engine evidence

Load this for Mode D/F whenever the product contains asynchronous actions,
custom ARIA widgets, translated content, RTL locales, or a target above 92.
These checks are evidence layers, not a license to infer requirements.

## Contents

1. Evidence classes
2. Deterministic checks
3. Runner configuration
4. Status announcements and interaction timing
5. APG widget contracts
6. Authentication, dragging, and redundant entry
7. Internationalization and color-vision passes
8. Cross-engine critical surfaces
9. Artifact regression
10. Perfection evidence

## 1. Evidence classes

Keep these three classes separate in every ledger:

| Class | May become a scored finding? | Examples |
|---|---:|---|
| Deterministic | Yes, after confirmation | invalid `lang`, browser-confirmed Label in Name, complete focus obstruction |
| Configured behavior | Yes, because the expected action/contract was declared | a save action fails to announce; a configured tablist ignores arrow keys |
| Advisory simulation | No, not from the simulation alone | color-vision screenshot, LoAF entry, pixel/saliency change |

Never turn “not run” into “passed.” Record unavailable evidence as an evidence
gap. Never turn a changed simulation screenshot into a defect without naming
the semantic distinction that was lost.

## 2. Deterministic checks

The probe now measures:

- complete focus obstruction after scrolling each reachable control into view
  (WCAG 2.4.11); partial obstruction remains a review item;
- a sufficient WCAG 2.4.13 AAA focus-outline signal. Anything not proven by a
  solid ≥2px, ≥3:1 outline remains unproven, not failed;
- visible-label/accessibility-name candidates, then the runner confirms them
  against the browser-computed ARIA snapshot (WCAG 2.5.3);
- syntactically invalid `lang` values;
- invalid HTML `autocomplete` token sequences;
- clipping deltas under stress passes.

`inputPurposeReview` is contextual. An email field may collect a colleague’s
address rather than the current user’s. Confirm that WCAG 1.3.5 applies before
promoting it to a finding.

## 3. Runner configuration

Add only applicable passes to `~/.cache/designer-dude/probe-config.json`:

```json
{
  "outDir": "/abs/repo/.design",
  "label": "dashboard",
  "url": "http://localhost:3000/dashboard",
  "stableScreenshots": true,
  "i18n": {"textExpansion": true, "rtl": true},
  "visionDeficiencies": ["achromatopsia", "deuteranopia"],
  "announcements": [
    {"label": "save invoice", "click": "button[type=submit]",
     "wait": 500, "expected": "saved|updated"}
  ],
  "widgets": [
    {"label": "invoice views", "kind": "tablist",
     "selector": "[role=tablist]"}
  ]
}
```

The runner writes every result into `behavioralEvidence`,
`visionDeficiencyPasses`, `screenshotStability`, and the normal `runs` array.
It also writes before/after ARIA snapshots for announcement actions.

## 4. Status announcements and interaction timing

Configure an announcement only when the named action produces a visual status
change that WCAG 4.1.3 covers: success, error, progress, waiting, or changed
result count. Do not configure tabs, disclosures, or ordinary content changes
as status messages.

Supported triggers:

```json
{"label":"save", "click":"#save", "expected":"saved"}
{"label":"refresh", "press":{"selector":"#refresh", "key":"Enter"}}
{"label":"filter", "fill":{"selector":"#query", "value":"overdue"}}
```

The observer starts before the action. It records text entering
`aria-live`, `role=status`, or `role=alert`, so short-lived announcements are
not lost by a late DOM snapshot. An `expected` value is a case-insensitive
regular expression. Invalid expressions fail explicitly.

The same action captures Event Timing and Long Animation Frame entries:

- an event over 200ms is a lab interaction candidate, not field INP;
- a LoAF over 100ms is diagnostic evidence of UI-thread congestion;
- unsupported APIs remain `supported:false`, never zero-duration passes.

Field INP at p75 remains authoritative.

## 5. APG widget contracts

Supported configured kinds are `tablist`, `radiogroup`, `menu`, `listbox`,
`tree`, `toolbar`, and `dialog`. Each composite contract requires at least two items and exercises
both the forward and reverse APG key. It accepts focus movement,
`aria-activedescendant` movement, or selected/checked state movement.

This is deliberately opt-in. A role identifies the broad pattern, but product
context still decides which rendered instance should be tested and whether it
is open/reachable. Use `url` and `open` when needed:

```json
{"label":"actions menu", "kind":"menu", "selector":"#actions-menu",
 "open":"#actions-trigger", "url":"http://localhost:3000/invoices/42"}
```

A configured contract that does not respond is a WCAG 2.1.1 candidate. A
static ARIA snapshot never substitutes for actual screen-reader testing;
perfection still requires assistive-technology evidence.

For `dialog`, configure `open` and the dialog selector. The runner verifies
initial focus, Tab containment, Escape dismissal, and focus restoration.

## 6. Authentication, dragging, and redundant entry

These WCAG 2.2 checks require product context, so configure relationships
instead of guessing them from markup:

```json
{
  "authChecks": [
    {"label":"sign in password", "selector":"#password",
     "expectedAutocomplete":"current-password"}
  ],
  "dragAlternatives": [
    {"label":"reorder invoice", "dragSelector":".drag-handle",
     "alternativeSelector":"button[aria-label='Move invoice']"}
  ],
  "redundantEntries": [
    {"label":"shipping email", "firstSelector":"#email",
     "value":"test@example.com", "advance":"#next",
     "secondSelector":"#confirm-email"}
  ]
}
```

Authentication checks dispatch a cancelable paste event and validate the
declared password/OTP autocomplete token. Blocking paste is a WCAG 3.3.8
candidate; missing metadata alone remains contextual because another
cognitive-function-free authentication method may exist.

A drag alternative must be visible, enabled, and keyboard reachable. The
config declares that it is intended to be equivalent; the reviewer must still
confirm it produces the same result before closing WCAG 2.5.7.

A redundant-entry journey fills the first step, advances, then requires the
prior value to be auto-populated in `secondSelector` or exposed through
`availableSelector`. Configure only repeated information in the same process;
security, essential re-entry, and expired information are WCAG exceptions.

## 7. Internationalization and color-vision passes

`textExpansion` pseudo-localizes visible text and expands words by roughly
35%, probes, then restores the DOM. It is useful for every content-bearing
product. New overflow or clipping is a regression candidate.

`rtl` sets structural direction and probes the delta. Enable it when an RTL
locale is supported or being evaluated. Do not penalize an explicitly
English-only product merely because RTL was not configured; record the scope.

Reviewed locale profiles are stronger than either synthetic pass because they
exercise real line breaking, shaping, mixed direction and product vocabulary:

```json
{
  "i18n": {
    "textExpansion": true,
    "rtl": true,
    "profiles": [
      {
        "label": "ja-JP",
        "locale": "ja-JP",
        "dir": "ltr",
        "text": {"#page-title": "請求書の承認", "#save": "保存する"},
        "attributes": {"#search": {"placeholder": "請求書を検索"}}
      },
      {
        "label": "ar-EG",
        "locale": "ar-EG",
        "dir": "rtl",
        "text": {"#page-title": "مراجعة الفواتير", "#save": "حفظ التغييرات"}
      }
    ]
  }
}
```

Use stable unique selectors and reviewed translations. The runner sets the
document language/direction and browser Intl locale, restores every mutated
text/attribute afterward, and marks a profile `partial` if any selector is
missing. A partial profile cannot certify perfection. Never machine-translate
copy merely to turn this gate green.

Color-vision simulations use Chromium’s emulation protocol. They produce
review screenshots only. Confirm a finding only when a named semantic
distinction—error/success, selected/unselected, chart series, required field—
disappears without a second cue.

## 8. Cross-engine critical surfaces

Create `.design/cross-engine-config.json` and run:

```bash
node "$S/cross-engine.mjs" --config .design/cross-engine-config.json
```

```json
{
  "outDir": "/abs/repo/.design",
  "label": "critical",
  "skillDir": "/abs/designer-dude/scripts",
  "surfaces": [
    {"label":"dashboard", "url":"http://localhost:3000/dashboard"},
    {"label":"settings", "url":"http://localhost:3000/settings"}
  ],
  "viewports": [[1440,900],[390,844]],
  "engines": ["chromium","firefox","webkit"],
  "storageState": "/abs/test-account-state.json"
}
```

Use seeded test accounts only. The script writes screenshots, ARIA trees, and
invariant metrics per engine. Accessible-name failures are recomputed from
each engine's own accessibility tree rather than copied from DOM fallbacks. It
reports only worsening measurable invariants;
pixel identity across engines is neither expected nor desirable. An unavailable
engine is an evidence gap and exits non-zero.

## 9. Artifact regression

The runner captures twice with animations disabled and the caret hidden.
`screenshotStability.status=unstable` invalidates that visual baseline until
the volatile region is stabilized or explicitly masked.

Compare a pinned before/current pair:

```bash
python3 "$S/artifact-regress.py" \
  --baseline .design/baseline \
  --current .design \
  --mask-config .design/artifact-masks.json \
  --out .design/artifact-regression.json
```

The tool has no image-library dependency. It decodes 8-bit non-interlaced PNG,
applies explicit rectangle masks, thresholds anti-alias noise, writes red diff
images for regressions, and compares normalized `.aria.yml` trees. A mask file
may also contain `ariaIgnorePatterns` for known volatile text.

Do not auto-approve a changed baseline. Inspect the diff, connect it to a
confirmed intentional change, then replace the baseline in the same review.

## 10. Perfection evidence

The literal 100 gate additionally requires:

- complete recall, precision, isolated-mutation, and end-to-end pipeline ratios;
- verified focus sweep, browser-computed accessible names, and Label in Name review;
- verified or reasoned-not-applicable announcements, widget contracts,
  authentication, drag alternatives, and redundant-entry journeys;
- verified text expansion and verified/reasoned-not-applicable RTL;
- complete reviewed locale profiles when localization is in scope;
- passing Chromium, Firefox, and WebKit evidence;
- stable visual and ARIA regression evidence.

The additional independent-label, expert-correlation, representative-sample,
real-user, real-AT and longitudinal calibration gates live in
`evidence-validation.md`. They cannot be inferred from this runner.

Every referenced output must appear in the certification’s SHA-256 artifact
manifest. “Not applicable” always requires a reason; it is never a blank pass.

## 11. Deliberate non-detectors

Do not turn these signals into findings without a named user task, semantic
contract, or independently confirmed failure:

- generic “visual clutter,” saliency, attention-map, or aesthetic scores;
- raw pixel changes under a color-vision or reduced-contrast simulation;
- cross-engine pixel identity, font-rasterization differences, or subpixel drift;
- absence of container queries, vertical writing, foldable layouts, or an
  experimental media preference when the product scope does not require it;
- a drag alternative’s claimed equivalence without completing the same task;
- RTL failure for a product with a documented single-direction locale scope;
- a custom focus style failing the conservative AAA proof when it remains
  visible—the proof is sufficient evidence, not a necessary design recipe.

The 320 CSS-pixel viewport is the WCAG reflow test equivalent to 400% zoom on
a 1280 CSS-pixel canvas. Browser zoom may still be useful for manual assistive-
technology review, but do not double-count the same reflow defect.

These boundaries are part of precision, not omissions. A detector graduates
to scoring only after it has a stable semantic definition, planted-defect
recall, clean-fixture precision, an isolated mutation, and an end-to-end
report-to-score assertion. Otherwise record it as advisory evidence or a
review question.
