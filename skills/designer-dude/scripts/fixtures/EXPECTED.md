# Fixture expectations

Two fixtures, because a measurement rig has two ways to fail.

**`selftest.html` — recall.** A page of **deliberate, enumerated defects**, so
`probe.js` can be re-validated after any edit: a measurement tool nobody
re-checks drifts into confident silence, where the check stops firing, the
scorecard keeps printing A, and the skill's whole value quietly inverts.

**`clean.html` — precision.** A page of constructs that are correct,
deliberate, or explicitly exempt, which must produce **zero** findings — from
the probe *and* from `probe-report.py`'s thresholds. Every construct on it is a
false positive that once cost a real review round: pure-black UA defaults on
`<head>` children, `transition: all` read from the CSS initial value, Tailwind's
half-steps read as spacing drift, computed `mx-auto` margins read as authored
values, and sub-24px targets that satisfy WCAG 2.5.8's exceptions. **A false
positive is more expensive than a miss**: it survives triage, gets argued in the
ledger, and spends the user's trust in the number.

```bash
node ~/.claude/skills/designer-dude/scripts/probe-selftest.mjs
# expect: probe-selftest: 40/40 planted defects detected

node ~/.claude/skills/designer-dude/scripts/probe-selftest.mjs --precision
# expect: 29/29 correct constructs left alone
#         probe-report on the clean fixture: 0 candidates
```

**Run both after any `probe.js` or `probe-report.py` edit.** A threshold that
catches everything passes the first and fails the second.

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
| D12 | Two 16×16 buttons butted together — undersized **and** crowded | `interaction.belowWcagTarget24` |
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
| D25 | Data table with no `scope`, no caption, left-aligned currency | `app.tables[].hasScope`, `.numericRightAligned` |
| D26 | 13/15/19/26px sizes — a pile, not a scale | `typography.adjacentRatios` |
| G1 | "Unlock the power of", "Welcome to", "all-in-one"… | `slop.genericMarketingCopy` |
| G2 | "Powered by GPT-4" | `slop.aiBadgeCopy` |
| G3 | 🚀 in an `h1` | `slop.emojiInHeadingsOrButtons` |

Plus structural assertions: the type scale, family count and median measure must
compute; every contrast failure must carry a numeric ratio and an APCA value;
the focus-ring test must actually have focused several elements; and
`errors` must be empty — a section that threw is a silent blind spot.

## What `clean.html` proves (the `REJECT` table)

| ID | Correct construct | Must NOT be reported as |
|---|---|---|
| C1 | `<html>`/`<meta>`/`<script>` inheriting the UA's black | pure `#000` text |
| C4/C5 | An isolated 20px icon button with 48px of nothing around it | a 2.5.8 failure — it passes the **Spacing** exception, and the probe must say so |
| C6 | Targets that are 44px or under 24px-and-exempt | a 24–44px Fitts finding |
| C6b | The canonical `sr-only` skip link (1×1, clipped until focused) | a 1×1 tap target — docking a page for doing the accessible thing |
| C7 | A `disabled` button with `cursor: default` | a missing pointer cursor |
| C9 | 6px/10px half-steps used systematically + a computed `margin: auto` | off-4px-base spacing drift |
| C10 | Elements with no `transition` declared (computed `transition-property: all`) | `transition: all` sprawl |
| C13–C19 | Labelled fields, `aria-label`ed icon button, alt text, sequential headings, `aria-hidden` on a leaf `<svg>` | accessibility defects |
| C21–C23 | 62ch measure, 1.55 leading, typographic apostrophes | typography defects |
| C24–C25 | A page with no gradient, no glass, no 3-up grid, no filler copy | slop tells |
| C26 | `<table>` with `th[scope]` and a caption | an unassociated data table |
| C27 | 3 radii, 2 shadows, 2 z-index layers | scale sprawl |

Plus the end-to-end check: `probe-report.py` must return **0 candidates** on it.
That is what tests the *thresholds*, not just the measurements — an honest probe
and a threshold set one notch too tight produce the same wasted round.

## Adding a check to probe.js

1. Plant the defect in `selftest.html`, with a `D<n>` comment saying what it is.
2. Add the assertion to `EXPECT` in `probe-selftest.mjs`.
3. Add the row above.
4. Add the threshold to `probe-report.py` — the probe measures, the report
   judges. Never put a threshold in `probe.js`.
5. **Add the correct-but-adjacent construct to `clean.html`** and a `REJECT`
   row for it. Nearly every check has a legitimate case that looks like the
   defect from a distance; that case is what you will be arguing about in a
   ledger three rounds from now if it is not pinned here.
6. Run BOTH selftests (`N/N` and `0 candidates`) **and** re-run the calibration
   anchors in `references/calibration.md`. A new check that fires on claude.com
   or vercel.com is a false-positive engine, not a check.

## What the fixture is not

It is not a design. It is not a benchmark for absolute counts — it is a small
page, so read its numbers as ratios (4 contrast failures in 32 text nodes) and
compare against the measured anchors in `calibration.md`.
