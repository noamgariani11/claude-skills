# Fixture expectations

Two fixtures, because a measurement rig has two ways to fail.

**`selftest.html` - recall.** A page of **deliberate, enumerated defects**, so
`probe.js` can be re-validated after any edit: a measurement tool nobody
re-checks drifts into confident silence, where the check stops firing, the
scorecard keeps printing A, and the skill's whole value quietly inverts.

**`clean.html` - precision.** A page of constructs that are correct,
deliberate, or explicitly exempt, which must produce **zero** findings - from
the probe *and* from `probe-report.py`'s thresholds. Every construct on it is a
false positive that once cost a real review round: pure-black UA defaults on
`<head>` children, `transition: all` read from the CSS initial value, Tailwind's
half-steps read as spacing drift, computed `mx-auto` margins read as authored
values, and sub-24px targets that satisfy WCAG 2.5.8's exceptions. **A false
positive is more expensive than a miss**: it survives triage, gets argued in the
ledger, and spends the user's trust in the number.

```bash
node ~/.claude/skills/designer-dude/scripts/probe-selftest.mjs
# expect: probe-selftest reports pass == total (green line), not a fixed number

node ~/.claude/skills/designer-dude/scripts/probe-selftest.mjs --precision
# expect: pass == total correct constructs left alone
#         probe-report on the clean fixture: 0 candidates

node ~/.claude/skills/designer-dude/scripts/probe-selftest.mjs --mutations
# expect: every isolated mutation moves its detector
#         inert DOM changes leave the measurement fingerprint stable
```

**Run all three after any `probe.js` or `probe-report.py` edit.** A threshold
that catches everything passes recall and fails precision; a detector keyed to
an unrelated fixture neighbour can pass both aggregate fixtures and fail the
differential mutation gate.

The assertions themselves live in `probe-selftest.mjs` (the `EXPECT` table) so
they run rather than merely being described. This file is the human-readable
index of what is planted and why.

| ID | Planted defect | Must be caught by |
|---|---|---|
| D1 | Pure `#000` text on pure `#fff` | `color.pureBlackOrWhiteText` |
| D2 | `#a8a8a8` muted text on white (~2.3:1) | `color.textContrast.failures`, with ratio + APCA + selector |
| D3 | Eight arbitrary radii, no scale | `system.radius.distinct` |
| D4 | 7px / 11px / 13px spacing, off the 4px base | `system.spacing.offFourBase` |
| D5 | `outline: none` with no replacement | `interaction.focusRing.invisible` (tested by focusing) |
| D6 | Clickable `<span>` with `cursor: default` | `interaction.missingPointerCursor` |
| D7 | Blue→purple hero gradient + gradient-clipped headline | `slop.purpleOrIndigoGradients`, `slop.gradientClippedText` |
| D8 | Glassmorphism on every card | `slop.backdropBlurElements` |
| D9 | Symmetrical three-up feature grid, icons in coloured circles | `slop.threeUpFeatureGrids`, `slop.iconsInColouredCircles` |
| D10 | Coloured left-border card | `slop.colouredLeftBorderCards` |
| D11 | Infinite spin animation, 900ms `transition: all` | `motion.infiniteAnimations`, `motion.transitionsOver600ms` |
| D12 | Two 16×16 buttons butted together - undersized **and** crowded | `interaction.belowWcagTarget24` |
| D13 | Unbounded measure (141ch) with 1.15 leading | `typography.offenders.measureOutOfBand`, `.leadingOutOfBand` |
| D14 | `#e6e6e6` field border (~1.3:1) | `color.nonTextContrast.fieldBorderFailures` |
| D15 | Centred text throughout | `slop.centredShare` |
| D16 | Six z-index values including 9999 | `system.zIndex.distinct` |
| D17 | `h1` → `h4`, skipping levels | `a11y.headings.skippedLevels` |
| D18 | Input with no label; another with placeholder only | `a11y.fieldsMissingLabel`, `.fieldsPlaceholderOnly` |
| D19 | `<img>` with no `alt` and no dimensions | `a11y.imagesMissingAlt` |
| D20 | Icon-only button with no accessible name | `a11y.controlsMissingAccessibleName` |
| D21 | Duplicate `id="dupe"` | `a11y.duplicateIds` |
| D22 | `aria-hidden` wrapping a focusable link | `a11y.ariaHiddenContainingFocusable` |
| D23 | `tabindex="3"` | `a11y.positiveTabindex` |
| D24 | 3000px-wide element | `layout.horizontalOverflow` + the offending selector |
| D25 | Ambiguous row+column-header table with no explicit association, no caption, left-aligned currency | `app.tables[].needsHeaderAssociations`, `.hasHeaderAssociations`, `.numericRightAligned` |
| D26 | 13/15/19/26px sizes - a pile, not a scale | `typography.adjacentRatios` |
| G1 | "Unlock the power of", "Welcome to", "all-in-one"… | `slop.genericMarketingCopy` |
| G2 | "Powered by GPT-4" | `slop.aiBadgeCopy` |
| G3 | 🚀 in an `h1` | `slop.emojiInHeadingsOrButtons` |

Plus structural assertions: the type scale, family count and median measure must
compute; every contrast failure must carry a numeric ratio and an APCA value;
the focus-ring test must actually have focused several elements; and
`errors` must be empty - a section that threw is a silent blind spot.

## What `clean.html` proves (the `REJECT` table)

| ID | Correct construct | Must NOT be reported as |
|---|---|---|
| C1 | `<html>`/`<meta>`/`<script>` inheriting the UA's black | pure `#000` text |
| C4/C5 | An isolated 20px icon button with 48px of nothing around it | a 2.5.8 failure - it passes the **Spacing** exception, and the probe must say so |
| C6 | Targets that are 44px or under 24px-and-exempt | a 24–44px Fitts finding |
| C6b | The canonical `sr-only` skip link (1×1, clipped until focused) | a 1×1 tap target - docking a page for doing the accessible thing |
| C7 | A `disabled` button with `cursor: default` | a missing pointer cursor |
| C9 | 6px/10px half-steps used systematically + a computed `margin: auto` | off-4px-base spacing drift |
| C10 | Elements with no `transition` declared (computed `transition-property: all`) | `transition: all` sprawl |
| C13–C19 | Labelled fields, `aria-label`ed icon button, alt text, sequential headings, `aria-hidden` on a leaf `<svg>` | accessibility defects |
| C21–C23 | 62ch measure, 1.55 leading, typographic apostrophes | typography defects |
| C24–C25 | A page with no gradient, no glass, no 3-up grid, no filler copy | slop tells |
| C26 | `<table>` with `th[scope]` and a caption | an unassociated ambiguous data table |
| C27 | 3 radii, 2 shadows, 2 z-index layers | scale sprawl |

Plus the end-to-end check: `probe-report.py` must return **0 candidates** on it.
That is what tests the *thresholds*, not just the measurements - an honest probe
and a threshold set one notch too tight produce the same wasted round.

## Adding a check to probe.js

1. Plant the defect in `selftest.html`, with a `D<n>` comment saying what it is.
2. Add the assertion to `EXPECT` in `probe-selftest.mjs`.
3. Add the row above.
4. Add the threshold to `probe-report.py` - the probe measures, the report
   judges. Never put a threshold in `probe.js`.
5. **Add the correct-but-adjacent construct to `clean.html`** and a `REJECT`
   row for it. Nearly every check has a legitimate case that looks like the
   defect from a distance; that case is what you will be arguing about in a
   ledger three rounds from now if it is not pinned here.
6. Run BOTH selftests (`N/N` and `0 candidates`) **and** re-run the calibration
   anchors in `references/calibration.md`. A new check that fires on claude.com
   or vercel.com is a false-positive engine, not a check.

## What the fixture is not

It is not a design. It is not a benchmark for absolute counts - it is a small
page, so read its numbers as ratios (4 contrast failures in 32 text nodes) and
compare against the measured anchors in `calibration.md`.

## D27 - hover-only content (added 2026-07-30)

Two plants, both unreachable on a coarse pointer:

- `.hovermenu .drawer` - a nav drawer with `display:none` lifted only by
  `.hovermenu:hover`. Contains a real `<a href>`.
- `.rowitem .rowaction` - a row action at `opacity:0` lifted only by
  `.rowitem:hover`. Contains a real `<button>`.

Detected as `states.hoverOnlyContentCount >= 2`, with at least one entry
carrying `interactive: true`. `probe-report.py` raises it CRITICAL / WCAG 2.1.1
on a run where `meta.device.pointerCoarse` is true.

The matching precision guard is **C29** in `clean.html`: the same reveal
patterns done correctly (`:hover` **plus** `:focus-within`, an
`aria-expanded` toggle, and a hover that only changes opacity between two
visible states) must produce `hoverOnlyContentCount === 0`. Recall without that
guard would flag every well-built menu on the page.

## D28-D35 - copy tells and browser chrome (added 2026-07-30)

Eight plants covering the two layers a screenshot cannot show you: the shape of
the words, and the parts of the UI the operating system draws.

| ID | Plant | Detected as |
|---|---|---|
| D28 | `.steps` with `01` / `02` / `03` as section ornament | `slop.decorativeStepNumbers >= 3` |
| D29 | a paragraph carrying four em dashes | `slop.emDashesInCopy`, `slop.emDashesPer1kChars` |
| D30 | "isn't just a tool, but a partner" plus "in today's fast-paced world" | `slop.llmSentenceFrames.length >= 2` |
| D31 | `<button title="Archives the property...">` | `chrome.nativeTitleTooltips >= 1` |
| D32 | a 60px scroll region with `scrollbar-width: none` | `chrome.hiddenScrollbars >= 1` |
| D33 | `<select style="appearance:none">` with no replacement chevron | `chrome.unstyledStrippedSelects >= 1` |
| D34 | no `color-scheme` anywhere in the page | `chrome.colorScheme === "normal"` |
| D35 | a `prefers-color-scheme: dark` block with no `color-scheme` declared | `chrome.darkSurfaceWithoutColorScheme === true` **in the dark pass** |
| D36 | `01`/`02`/`03` one per `<li>`, so each numeral has a different grandparent | `slop.decorativeStepNumbers >= 6` |
| D37 | a row whose `:hover` fill is the colour its own container already is | `states.inertHoverFills >= 1` |
| D38 | a 520px row painting a hover fill with `padding-inline: 0` | `states.hoverFillsWithoutPadding >= 1` |
| D39 | a hover fill that moves hue at the same lightness | `states.hueOnlyHoverFills >= 1` |
| D43 | a prose link with no underline, <3:1 against surrounding text, and no hover/focus cue | `states.colorOnlyLinks.count >= 1` |
| D44 | an `aria-labelledby` IDREF pointing to no element | `a11y.requiredBrokenAriaReferences.count >= 1` |
| D44b | a collapsed trigger whose `aria-controls` target is lazily absent at rest | `a11y.deferredAriaControls.count >= 1` (manual candidate, not a hard failure) |
| D45 | a custom `role=tab` missing its required selected state | `a11y.ariaRoleStateIssues.count >= 1` |
| D46 | two navigation landmarks with no distinct accessible names | `a11y.landmarkNameIssues.count >= 1` |

D35 is the only assertion in this file that needs its own probe run: the
boolean is meaningless until a dark surface exists, so `probe-selftest.mjs`
emulates `prefers-color-scheme: dark`, re-probes, and asserts there. It is
worth the extra pass, because a dark theme shipping with light OS scrollbars, a
white `<select>` popup and yellow autofill is one missing declaration and is
invisible in every screenshot anyone takes.

Precision guards in `clean.html`, all of which must stay silent:

- **C30** `color-scheme: light dark` declared, so the chrome check passes.
- **C31** a lone `01` as unit-number DATA is not ornament. The detector requires
  the padded number to be a leaf element's whole text AND to repeat in the same
  SHAPE (same tag, class and size, under the same parent tag), precisely so a
  jersey number, a version, or a table cell never reaches a scorecard.

  D36 is why the gate is shape and not the grandparent's selector. Grouping by
  grandparent identity meant one numeral per `<li>` landed in six buckets of
  one, and the single most-shipped form of the ornament measured zero. A
  precision guard that also destroys recall is not a guard.
- **C32** a **native** `<select>` keeping its own chevron is correct
  engineering. `scoring.md` does not dock for choosing one, and neither does
  this check: it fires only when `appearance: none` removed the arrow and
  nothing replaced it.
- **C33** a scroll region with an ordinary unstyled scrollbar. An unstyled
  scrollbar is a preference; a **hidden** one is a defect, and the probe must
  never confuse the two.
- **C34** `title` that merely repeats an element's own visible text is
  redundant markup, not a tooltip carrying information nothing else does.
- **C36** a hover fill that is a visible step from the row's own backdrop.
  Hover coverage is not the question; whether the paint changes is. The check
  fires under a 1.02 WCAG ratio between hovered and rest fill AND under 6/255
  of channel distance. Both conditions are needed: a luminance ratio alone
  cannot tell "the same colour" from "a different colour at the same
  lightness", and merging the two would report a real (if weak) hue-shift
  hover as though nothing happened. D39 is the separated case.
- **C37** a hover fill on a wide row that has inline padding to sit in. The
  unpadded check is for bands that stop at the first glyph, not for every row
  with a background.
- **C35** a single em dash in a page of human prose. The check is a **rate**,
  not a count, because docking a page for one correct em dash is how a slop
  detector gets muted and then ignored when it is right.
- **C39** genuine typographic and mathematical marks in prose - a multiplication sign, a real ellipsis and a plus-minus - are typography, not the glyph-standing-in-for-an-icon tell. Docking a page for setting maths correctly is how a slop detector gets muted.
- **C40** A 32px-tall nav link on a pointer-first desktop surface is period-normal craft, not an undersized target: linear.app measures 114 in the same 24-44px band. WCAG 2.5.8's 24px floor is what must hold, and does.
- **C41** A skip link must appear on :focus, not :focus-visible - it exists only for keyboard users and focus-visible heuristics can suppress it. A lone plain :focus rule is therefore correct, not a missing focus-visible.
- **C42** A hover that steps a border from a 40%-alpha wash to the same hue at full strength IS a visible change. Comparing declared tokens (both var(--color-warn)) without resolving the alpha modifier reports it as inert.
- **C43** An ellipsis-truncated row: the fill has 16px of inset on both sides. Measuring the untruncated Range rect of clipped text reports the ink as overflowing the band when it is visibly inside it.
- **C44** Text over a system-coloured backdrop under forced-colors stays visible; the probe simply cannot resolve a composited backdrop for it and skips it. A drop in MEASURABLE nodes is not a drop in visible ones - verified by diffing rendered text nodes, 445 before and 445 after.
- **C45** A 10%-alpha status wash spanning wide rows is not accent dominance. probe.js marks a grid cell for any fill with alpha>0.05 without weighting by alpha, so a barely-there tint is charged the same as a solid accent fill.
- **C46** A disabled state expressed as a conditional class rather than a ':disabled' CSS rule is still a designed disabled state. The launcher's disabled button is dashed and unfilled precisely so armed vs disarmed is not a subtle read.
- **C47** A full-height LEFT SIDEBAR is sticky but consumes no vertical space. The short-viewport chrome threshold must measure vertical occupancy, not the height of any sticky box.
- **C48** A scrollable nav (overflow-y:auto) whose items are below the fold is NOT content loss under SC 1.4.4, which permits scrolling in one dimension.
- **C49** A redirect stub legitimately has no h1. Probe canonical URLs; the h1 check must not run against a document that only redirects.
- **C50** flex-shrink-0, flex-grow and bg-gradient-to-l are DEPRECATED ALIASES in Tailwind 4.3.x and still emit correct CSS. They are not dead classes and must not be reported as such.
- **C51** An input WRAPPED in a label element is correctly named; only a bare input with nothing but a placeholder is unnamed.
- **C52** overflow:hidden with text-overflow:ellipsis is the correct way to truncate; it is not clipping.
- **C53** On a narrow viewport a single full-width primary action legitimately occupies a large pixel share. The accent-share threshold is about a page drowned in colour, so it must be judged at the design viewport, not at 320-390px where one correct button dominates by arithmetic.
- **C54** A position:fixed transparent header over a dark hero. The header's ancestor chain is <body> (paper), but the text is painted over the near-black hero, where white-at-0.75 measures 11.19:1. Resolving the backdrop by DOM walk alone reports 1.03:1 and invents a critical WCAG failure on every dark-hero page.
- **C55** Text on a position:fixed bar is correct code. The contrast walk must resolve the fixed element's own background rather than recording the backdrop as 'inherited' and emitting a ~1.0 ratio that contradicts the fg/bg pair it recorded.
- **C56** A skip link is the recommended WCAG 2.4.1 technique: sr-only at rest, revealed on focus. Tailwind's focus:not-sr-only pattern keeps the px-4/py-2 padding utilities applied while sr-only is active, so the border box measures 32x16 with a 1x1 content box and a zero-area clip. It paints nothing and is not a target until focused, so it must not raise a 2.5.8 target-size candidate.
- **C57** An element that paints its OWN opaque background is never in doubt about what its text sits on, whatever is behind the box. When an app shell is wrapped in one position:fixed div, every descendant is 'out of flow' by ancestor, and hit-testing past the element's own background reported a primary button as white-on-white (1:1) when it measures 6.70:1.
- **C58** One universal ':focus-visible { outline: ... }' rule is the most correct way to ship a focus ring - it covers every element including ones no component file knows about. The state-coverage walk stripped the pseudo to an empty base and dropped it, and on a Tailwind build the 400-base cap filled with utility selectors before the app's own rule was ever read, so a product with a perfect focus ring measured 5% coverage.
- **C59** A position:fixed action button overlaps body text at some scroll position by definition, at every breakpoint. That is the pattern, not a defect. Dock only when it covers a control (this one stands down over the contact form via IntersectionObserver).
- **C60** One tracking value applied to exactly one role at every one of its call sites is a decision, not drift, even when it overrides a scale default. Drift is many values for one role.
- **C61** Body-copy links with a persistent underline are distinguishable without colour and must never trigger the colour-only link check.
- **C62** Existing valid `aria-controls` wiring and native controls do not trigger the broken-reference or custom-role checks.
- **C63** A small, simple table with one obvious header direction is valid with `<th>` alone; W3C H63 does not require `scope` until associations become ambiguous or the table becomes larger/complex.
- **C64** Repeated navigation landmarks with short, unique accessible names remain distinguishable in landmark navigation.
- **D47** A focused control entirely covered by fixed author content is detected by the keyboard focus sweep (WCAG 2.4.11).
- **D48** A control whose accessible name omits its visible label is a Label in Name candidate (WCAG 2.5.3).
- **D49** Syntactically invalid `lang` metadata is detected.
- **D50** An invalid `autocomplete` token sequence is detected.
- **C65** An accessible name may add context after the complete visible label.
- **C66** A valid nested BCP 47 language tag remains clean.
- **C67** A valid section/contact autocomplete sequence remains clean.
- **C68** Fixed UI that does not completely cover a focused control is not reported as focus obscuration.
- **D51** A tag whose primary language is not registered/recognized is a
  Language-of-Page/Parts failure; strict trailing-subtag grammar alone is not.
- **C69** Known language primaries remain clean.
- **C70** A known primary language remains WCAG-clean when trailing subtags are
  not strict RFC 5646; the syntax difference stays advisory.
- **C71** Hidden, disabled, and empty autocomplete declarations are
  inapplicable rather than invalid-purpose failures.
- **C72** An invalid `lang` owner whose meaningful descendants all redeclare
  their language is outside Language-of-Parts applicability.
