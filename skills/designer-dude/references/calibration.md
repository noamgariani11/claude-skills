# Calibration - anchors, and how not to inflate

Load this when scoring anything, and **always before a Mode F campaign**.

A letter grade with no fixed reference point drifts. Across a
run-it-until-it-is-90 campaign it drifts in one direction: upward, because each
run wants to show progress. These are the anchors that stop it.

---

## The first rule: benchmark the rubric, not just the page

**If the rubric would grade a reference-grade product badly, the rubric is
wrong.** Not the product.

That is not a thought experiment. Every number in the table below was measured
with this skill's own probe, and the first run graded `linear.app`'s slop an
**F** - because the detectors ignored opacity, area and saturation, so a
4%-alpha decorative glow registered as a "gradient-mesh orb hero" and a
dark-theme hairline registered as a "coloured accent border". The tells were
tightened until the grades were plausible, and the fixture (which stacks every
slop pattern deliberately) still scored F.

Do this whenever you change a threshold:

```bash
S=~/.claude/skills/designer-dude/scripts
node $S/probe-selftest.mjs                                   # recall: pass must equal total (the total grows as cases are added)
node $S/probe-selftest.mjs --precision                       # correct constructs remain silent
node $S/probe-selftest.mjs --mutations                       # isolated sensitivity + inert stability
node $S/probe-selftest.mjs --pipeline                        # finding and score semantics stay wired
node $S/probe-selftest.mjs --runner                          # evidence driver stays integrated
python3 $S/evidence-gates.py --selftest                      # external-evidence schemas reject weak claims
python3 $S/calibration-snapshot.py --selftest                # pinned reference bytes detect drift
node $S/act-benchmark.mjs --out /tmp/act-benchmark.json       # independent W3C holdout for mapped a11y rules
node $S/probe-selftest.mjs --url https://linear.app --out /tmp/li.json
python3 $S/probe-report.py /tmp/li.json --quiet | grep "AI Slop"
```

A threshold that fails a reference site is a bug in the threshold. Fix it there,
in source, where the fix is reviewable - not by quietly ignoring the output.

The planted and clean fixtures protect local recall and precision; they are not
an independent claim of general validity. Before a detector graduates into
scoring, run the frozen holdout and expert-correlation gates in
`evidence-validation.md`. Keep predictions separate from labels. A live-site
anchor is also frozen with `calibration-snapshot.py`; otherwise a redesign can
change the benchmark while leaving this document untouched.

`--url` is used here deliberately: an anchor run wants a throwaway browser, no
login, and no interference with whatever the review session has open. **But do
not calibrate a hover, focus or motion threshold from JSON alone.** Those live
in the live browser: open the anchor through the `browse` skill
(`browser-verification.md`), hover the same class of component you are grading
on the target, and see what a reference product's row hover actually does
before deciding what yours must do. Half the thresholds in this file exist
because a real site was looked at and the rubric was wrong about it.

### The override passes, calibrated 2026-07-30

The four user-override passes (forced-colors, prefers-contrast, SC 1.4.12 text
spacing, 200% text zoom) are graded as **deltas against the 1440 baseline**, not
as absolutes - system colours and doubled text legitimately move every number,
so only a metric that got WORSE is attributable to the override. Calibrated
three ways before shipping:

| Check | Result |
|---|--:|
| `fixtures/clean.html` with all four passes plus content stress | **0 candidates** |
| a planted fixture: `width:1400px` + `white-space:nowrap`, fine at 1440 | 1.4.4 overflow candidate raised, correctly |
| **linear.app** with all four passes | **0 override candidates** (its 25 other candidates are the pre-existing set) |

linear.app is the load-bearing one. Under forced colours its checked text nodes
went **up** (410 → 421) and its failures to zero; under 200% zoom its failures
**fell** 120 → 32. A delta check that fired on either would be measuring the
override, not the page.

---

## Measured anchors (2026-07-30, desktop 1440x900, marketing surfaces)

These are facts about real pages, taken with `probe.js`. They are the answer to
"is 12 distinct radii a lot?" and "how many contrast failures is normal?".

| Measure | claude.com | linear.app | stripe.com | vercel.com | fixture (deliberately bad) |
|---|--:|--:|--:|--:|--:|
| Contrast failures / checked | **0 / 166** | 120 / 410 | 14 / 418 | 3 / 165 | 4 / 32 |
| Focus rings invisible / tested | 0 / 11 | 0 / 54 | 11 / 55 | 3 / 8 | 2 / 8 |
| Targets under 24px | 5 | 29 | 101 | 2 | 4 |
| Font families rendered | 2 | 2 | 1 | 2 | 2 |
| Distinct font sizes | 11 | 14 | 14 | 8 | 9 |
| Median measure (ch) | 66 | 72 | 52 | n/a | **141** |
| Distinct radii | 6 | 13 | 8 | **3** | 9 |
| Distinct shadows | 5 | 11 | 3 | 2 | 0 |
| Distinct spacing values | **13** | 74 | 33 | 18 | 16 |
| Off-4px spacing values | **1** | 53 | 16 | 4 | 10 |
| Distinct text colours | 7 | 15 | 17 | **6** | 5 |
| Accent pixel share | 0% | 0% | 1% | 0% | 0.5% |
| Measured slop grade | **A** | B+ | B+ | **A** | **F** |

The fixture column is a small page, so its absolute counts are low - read it
for *ratios*, not volume: 4 failures in 32 text nodes is a 12% failure rate
against claude.com's 0%, and a 141ch measure is nearly double the comfortable
maximum. Its slop F comes from stacking the patterns, not from page size.

### Two rig corrections, 2026-08-03 - both found by a campaign, both re-anchored

Re-measured after each: `linear.app` B+, `vercel.com` A, `stripe.com` B+,
`claude.com` **A** (was B+), accent share still 0% on all four, both selftests
green (63/63 recall, 44/44 precision).

1. **Accent share ignored gradient-painted area.** `accentPixelShare` marked
   cells from `backgroundColor` only, so the cheapest way to hide accent
   overuse from this probe was to paint the section as a gradient - and
   "indigo-to-purple across the whole hero" is item one on the slop list. The
   metric was rewarding the pattern it exists to catch. Found when a page
   header was repainted from a two-stop gradient to the identical flat token:
   2% -> 66.6% on **pixel-identical screenshots**. Gradient stops are now
   scored on the most saturated stop, by the same spread-times-alpha bar as a
   flat fill. Photographic scrims stay silent - `black/80 -> transparent` has a
   channel spread of zero.

2. **The three-up tell fired on three real things.** The slop-list item is a
   "stock 3-icon feature row" - interchangeable cards of icon, two-word
   heading and one line of category filler. The detector only counted columns,
   so three priced services each with its own bullet list and its own action
   scored the same as "Fast / Secure / Simple". It was firing on claude.com
   too, which is what settled it. A card now exempts the grid if it offers an
   action of its own or carries more than a sentence. `clean.html` C61 guards
   it.

The shared lesson, and it is the reason both survived nine rounds: **a metric
that is blind to one rendering path silently grades the OTHER path harder.**
Neither bug produced a wrong-looking number - they produced a flattering one,
on the page that happened to use the path the probe could not see.

### The copy and chrome checks, anchored (2026-07-30)

Added with the `chrome` probe section and the copy tells. The point of the
anchor is that **a well-built site scores zero on all of them**: a check that
fires on linear.app is a preference wearing a threshold's clothes.

| Measure | linear.app | fixture (deliberately bad) |
|---|--:|--:|
| Em dashes in copy (per 1k chars) | 1 (**0.1**) | 4 |
| Decorative `01`/`02`/`03` step numbers | **0** | 3 |
| LLM sentence frames | **0** | 2 |
| `color-scheme` declared | **dark** | none |
| Dark surface with no `color-scheme` | **false** | **true** (dark pass) |
| Hidden scrollbars / scroll regions | **0 / 1** | 1 |
| Stripped selects / selects | **0 / 0** | 1 / 1 |
| Native `title` tooltips | **0** | 1 |

Two calibration decisions came out of this run and both are load-bearing:

- **Em dashes are a rate, not a count.** linear.app carries one, which is a
  writer using punctuation. The threshold is 3 per 1,000 characters, and
  `clean.html` guards it: docking a page for a single correct em dash is how a
  slop detector gets muted and then ignored when it is right.
- **The `01` detector needs a repeat under a shared parent.** A lone padded
  number is data - a unit number, a version, a jersey. `clean.html` C31 plants
  exactly that and it must stay silent.

### Prose-link and ARIA checks, anchored (2026-08-03)

These checks were added contrastively: the bad fixture must fire, the clean
fixture must stay at zero, and current production references must show whether
the heuristic is measuring a defect or merely a framework convention.

| Measure | claude.com | linear.app | stripe.com | vercel.com | clean fixture |
|---|--:|--:|--:|--:|--:|
| Colour-only prose links | 0 | 0 | 0 | 0 | 0 |
| Required broken ARIA IDREFs | 1 | 0 | 0 | 0 | 0 |
| Deferred/lazy `aria-controls` targets | 1 | 3 | 0 | 1 | 0 |
| Repeated-landmark name issues | 0 | 1 | 0 | 0 | 0 |
| SC 2.5.8 under-24px failures | 1 | 8 | 0 | 0 | 0 |
| Under-24px exceptions (Spacing + Inline) | 7 | 21 | 102 | 0 | 4 |

The load-bearing decision is the split between **required** IDREFs and
`aria-controls`. Linear, Claude and Vercel all keep control references while a
collapsed panel is not mounted. Reporting that as an immediate 4.1.2 failure
would create five false hard-cap candidates across three references. The probe
therefore emits a non-WCAG manual candidate until the trigger is exercised;
only a target still absent when expanded/selected, or a missing naming,
description, error or ownership reference, enters the hard-failure bucket.

The target-size rows make the denominator explicit. Stripe has 102 sub-24px
targets and **zero failures** because every one clears WCAG 2.5.8 via the
Inline or Spacing exception. Quoting “102 small targets” as 102 failures is
precisely the false-positive workload the exception pass exists to prevent.

### What the anchors actually teach

1. **Zero contrast failures is achievable.** claude.com: 166 text nodes, zero
   AA failures. When a product has 40, that is a choice, not an inevitability.
2. **Reference-grade products still measure imperfect.** Linear ships 120
   contrast failures on its marketing page and 74 spacing values. Design-led
   does not mean flawless - so a page with a handful of findings is not
   automatically a C.
3. **Restraint shows up numerically.** vercel.com: 3 radii, 2 shadows, 6 text
   colours. That is what "decided, not assembled" looks like as data.
4. **13 spacing values with 1 off-base** (claude.com) is what a real scale
   looks like. **74 with 53 off-base** (linear.app) is per-component
   improvisation, even on a beautiful site.
5. **Small targets are the most-ignored failure at this tier.** Stripe ships
   101 sub-24px targets. Everyone is bad at 2.5.8. Say it anyway.

**Do not quote these numbers as current facts forever.** They are dated. Any of
these sites can redesign next week; re-measure before citing.

### On Tailwind, the framework supplies the denominator

The counts above - distinct font sizes, radii, shadows, spacing values - mean
something different on a Tailwind project, because Tailwind *hands you* a scale
before anyone decides anything. Read them against what the framework ships
(verified against `node_modules/tailwindcss/theme.css`, v4.3):

| Scale | Tailwind default | vercel.com | claude.com |
|---|--:|--:|--:|
| Type steps | **13** (`text-xs`…`text-9xl`) | 8 | 11 |
| Radii | **9** (`xs`…`4xl` + `full`) | 3 | 6 |
| Shadows | **7** (`2xs`…`2xl`) | 2 | 5 |
| Spacing | unbounded in v4 (dynamic) | 18 | 13 |

Two corrections this forces:

1. **Do not dock a Tailwind product for an irregular type ratio.** The rubric's
   Typography A says "sizes on a visible ratio", and Tailwind's default scale
   is *not* one: the steps run 12/14/16/18/20/24/30/36/48/60/72/96/128px, whose
   successive ratios wander from **1.111 to 1.333**. A stock-Tailwind product
   will always fail a ratio-purity test, which makes that test a false-positive
   generator on the most common stack in the corpus. **The real signal is how
   many of the 13 steps are in use.** Eleven distinct sizes on a bespoke system
   is a pile; eleven on Tailwind is "nobody chose", which is the same grade for
   a different and more useful reason. Say the useful one.
2. **A Tailwind product measuring 8–9 distinct radii has shipped the default
   scale untouched.** That is not a drifting scale - it is an absent decision,
   and it is the measurable half of slop item 5. Same for 6–7 shadows. Naming
   it as "you are shipping Tailwind's defaults" lands harder, and is more
   actionable, than "your radius scale has 9 values".

**Spacing needs its own note in v4.** The scale is now derived from a single
`--spacing` variable and is *dynamic*, so `p-13` and `mt-19` compile silently -
"is it a multiple of 4" no longer proves a scale exists. On Tailwind, an
off-4px spacing value comes from one of exactly two places, and the fix differs:
the half-steps (`p-0.5`/`1.5`/`2.5`/`3.5` → 2/6/10/14px), which are legitimate
at small sizes, or arbitrary values (`p-[13px]`), which are the finding. Check
which before writing it up.

**One measurable defect the default scale creates:** every step from `text-5xl`
up ships `line-height: 1`. A display heading that wraps to two lines at that
leading collides descenders with the next line's caps. It is invisible at
desktop width and appears at 390px, which is why it survives review. If the
probe reports a heading with computed line-height ≤ 1.05 that wraps, that is a
confirmed finding, not a taste call - fix with the paired form (`text-6xl/tight`).

### The consistency check is calibrated too

`probe-report.py --compare` was tuned the same way, and it needed it. The first
version scored **three pages of claude.com an F** - because it compared
truncated top-8 token lists, treated `anthropicSans` and `Anthropic Sans` as
different faces, and divided shared tokens by the union, which punishes a
surface for merely using fewer values. After fixing all three (full value sets,
normalised names, overlap-over-smallest, and voice judged on the primary face
rather than the whole family set):

- three pages of one design system → **B**, with the one genuine drift named
  (claude.com/news renders system-ui as its primary face, not the brand sans)
- three different companies → **F**

If your consistency check cannot tell those two cases apart, it is measuring
nothing. Re-run both after touching it.

---

## Grade anchors - what each letter means in practice

Concrete, so "B+" means the same thing in run 1 and run 9.

**Typography**
- **A** - 2–3 families with real contrast, sizes on a visible ratio, body
  measure 45–75ch, leading 1.4–1.6, tabular numerals in numeric columns,
  typographic quotes. (claude.com's marketing type is about here.)
- **B+** - the scale is real but has 1–2 near-duplicate steps, or the display
  face lacks tracking at large sizes, or one long-copy block runs past 78ch.
- **B** - a competent neutral sans doing all the work; nothing wrong, no voice.
- **C** - sizes are a pile rather than a scale (10+ in real use), or measure is
  unbounded, or Inter/Roboto is the display voice.
- **D/F** - text is hard to read at default zoom.

**Color & Contrast**
- **A** - semantic role tokens, zero AA failures in both themes, accent under
  10% of pixels, dark mode with its own palette.
- **B** - passes AA but the accent is doing too much, or the dark theme is the
  light palette with the lightness flipped.
- **C+ or lower, always** - any unresolved AA failure. And the composite caps
  at C+ regardless of the rest.

**Visual Hierarchy**
- **A** - the eye lands on the primary action in under a second, on every
  viewport, and the second and third stops are the right ones.
- **B** - you can find the primary action, but two things compete for it.
- **C** - you have to read the page to find out what it wants you to do.
- **F** - the primary action is below the fold on desktop, or invisible on
  mobile.

**Accessibility** - this one is not a smooth scale. Zero AA failures with a
clean keyboard pass is an A. **One** unresolved AA failure is a B at best plus
the composite cap. Several, or a keyboard trap, is D or F. Do not average your
way out of it.

**Craft** - A means every detail visibly answered a question: 2–3 radii, 3–4
coherent shadows, aligned numerals, one date format, a clean console. B means
one or two scales have drifted. C means the page is assembled from parts.

---

## Anti-inflation, mechanically

1. **A grade may not improve without fresh evidence.** Not a diff, not a
   reasonable expectation that the fix worked - a re-probe and a re-look. If a
   pillar was not re-measured this run, it keeps its previous grade.
2. **Re-verify the fixes you made, not the ones you meant to make.** The
   `-before`/`-after` screenshot pair and a re-run probe are the proof. "Applied
   the token change" is not.
3. **Never regrade upward on the same evidence.** If run 4 and run 5 have
   identical probe output, they have identical grades. Finding a kinder reading
   of the rubric is not progress.
4. **Confirmed findings only.** `score.py` shouts about `status: "candidate"`.
   A threshold breach is not a defect until you looked.
5. **Eye-only pillars need a letter you can defend.** `score.py` refuses to
   derive Hierarchy, IA, Content or Consistency from silence. If you did not
   look at the page this run, mark them `--provisional` and take the B+ cap.
6. **Every override is printed.** Overriding a derived grade is allowed and
   loud. Say why in the report, in one clause.
7. **Report regressions before improvements.** `--baseline` prints them; they
   belong at the top.
8. **Count the findings you rejected.** A run that rejects most of its own
   candidates is either measuring the wrong things or rationalising. Say which.

---

## The scores that should make you suspicious

- **A jump of more than ~6 points in one run.** Either a WCAG cap was lifted
  (say so explicitly - that is a legitimate jump) or the grading got looser.
- **Every pillar improving at once.** Real fixes are local. A uniform lift
  means the rubric moved, not the product.
- **A+ anywhere.** A+ is "considered and delightful, rare". If you are handing
  them out to reach a target, the target is now measuring nothing.
- **Slop grade improving without a single deleted element.** Slop is structural.
  It improves when patterns are removed, not when copy is reworded.
- **90+ on a first run.** Possible, but check the evidence ledger before
  believing it: an unprobed pillar defaults to no findings, which looks like an
  A until `--provisional` is applied.

---

## Reaching 90+ is genuinely hard - say so up front

The composite is a weighted mean of letter values, so (and `score.py --target`
prints this arithmetic):

- every pillar at **B+** → **85**
- every pillar at **A−** → **88**
- every pillar at **A** → **92** (the findings ceiling)
- every pillar at **A+** → **100**, and only in findings mode with eleven
  verified credits (each covering 2+ distinct surfaces), measured slop A, and
  the current attributable human `perfectionCertification` in `scoring.md`

**A card of straight A−s scores 88, not 90.** So 90+ requires real A grades on
the heavy pillars - Typography and Hierarchy are 30 of the 100 points, and
Spacing is another 12. It is not reachable by fixing twelve minor findings.

When a user asks for 90+, the honest first answer names what that costs:
typography with an actual voice, a hierarchy that survives a squint test at
three viewports, zero WCAG failures, and a spacing scale that holds across
pages. See `mode-f-campaign.md` for how to run that as a campaign rather than a
treadmill - including when to stop and say "this is 87 and the last three points
need a design decision that is yours, not mine."
