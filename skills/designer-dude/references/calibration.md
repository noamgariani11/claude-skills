# Calibration — anchors, and how not to inflate

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
**F** — because the detectors ignored opacity, area and saturation, so a
4%-alpha decorative glow registered as a "gradient-mesh orb hero" and a
dark-theme hairline registered as a "coloured accent border". The tells were
tightened until the grades were plausible, and the fixture (which stacks every
slop pattern deliberately) still scored F.

Do this whenever you change a threshold:

```bash
S=~/.claude/skills/designer-dude/scripts
node $S/probe-selftest.mjs                                   # fixture: must stay 40/40
node $S/probe-selftest.mjs --url https://linear.app --out /tmp/li.json
python3 $S/probe-report.py /tmp/li.json --quiet | grep "AI Slop"
```

A threshold that fails a reference site is a bug in the threshold. Fix it there,
in source, where the fix is reviewable — not by quietly ignoring the output.

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
| Measured slop grade | B+ | B+ | B | **A** | **F** |

The fixture column is a small page, so its absolute counts are low — read it
for *ratios*, not volume: 4 failures in 32 text nodes is a 12% failure rate
against claude.com's 0%, and a 141ch measure is nearly double the comfortable
maximum. Its slop F comes from stacking the patterns, not from page size.

### What the anchors actually teach

1. **Zero contrast failures is achievable.** claude.com: 166 text nodes, zero
   AA failures. When a product has 40, that is a choice, not an inevitability.
2. **Reference-grade products still measure imperfect.** Linear ships 120
   contrast failures on its marketing page and 74 spacing values. Design-led
   does not mean flawless — so a page with a handful of findings is not
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

### The consistency check is calibrated too

`probe-report.py --compare` was tuned the same way, and it needed it. The first
version scored **three pages of claude.com an F** — because it compared
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

## Grade anchors — what each letter means in practice

Concrete, so "B+" means the same thing in run 1 and run 9.

**Typography**
- **A** — 2–3 families with real contrast, sizes on a visible ratio, body
  measure 45–75ch, leading 1.4–1.6, tabular numerals in numeric columns,
  typographic quotes. (claude.com's marketing type is about here.)
- **B+** — the scale is real but has 1–2 near-duplicate steps, or the display
  face lacks tracking at large sizes, or one long-copy block runs past 78ch.
- **B** — a competent neutral sans doing all the work; nothing wrong, no voice.
- **C** — sizes are a pile rather than a scale (10+ in real use), or measure is
  unbounded, or Inter/Roboto is the display voice.
- **D/F** — text is hard to read at default zoom.

**Color & Contrast**
- **A** — semantic role tokens, zero AA failures in both themes, accent under
  10% of pixels, dark mode with its own palette.
- **B** — passes AA but the accent is doing too much, or the dark theme is the
  light palette with the lightness flipped.
- **C+ or lower, always** — any unresolved AA failure. And the composite caps
  at C+ regardless of the rest.

**Visual Hierarchy**
- **A** — the eye lands on the primary action in under a second, on every
  viewport, and the second and third stops are the right ones.
- **B** — you can find the primary action, but two things compete for it.
- **C** — you have to read the page to find out what it wants you to do.
- **F** — the primary action is below the fold on desktop, or invisible on
  mobile.

**Accessibility** — this one is not a smooth scale. Zero AA failures with a
clean keyboard pass is an A. **One** unresolved AA failure is a B at best plus
the composite cap. Several, or a keyboard trap, is D or F. Do not average your
way out of it.

**Craft** — A means every detail visibly answered a question: 2–3 radii, 3–4
coherent shadows, aligned numerals, one date format, a clean console. B means
one or two scales have drifted. C means the page is assembled from parts.

---

## Anti-inflation, mechanically

1. **A grade may not improve without fresh evidence.** Not a diff, not a
   reasonable expectation that the fix worked — a re-probe and a re-look. If a
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
  (say so explicitly — that is a legitimate jump) or the grading got looser.
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

## Reaching 90+ is genuinely hard — say so up front

The composite is a weighted mean of letter values, so (and `score.py --target`
prints this arithmetic):

- every pillar at **B+** → **85**
- every pillar at **A−** → **88**
- every pillar at **A** → **92**

**A card of straight A−s scores 88, not 90.** So 90+ requires real A grades on
the heavy pillars — Typography and Hierarchy are 30 of the 100 points, and
Spacing is another 12. It is not reachable by fixing twelve minor findings.

When a user asks for 90+, the honest first answer names what that costs:
typography with an actual voice, a hierarchy that survives a squint test at
three viewports, zero WCAG failures, and a spacing scale that holds across
pages. See `mode-f-campaign.md` for how to run that as a campaign rather than a
treadmill — including when to stop and say "this is 87 and the last three points
need a design decision that is yours, not mine."
