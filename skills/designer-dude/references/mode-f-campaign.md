# Mode F — Campaign to a target score

Load this when the ask is **"keep running this until it scores 90+"** or "make
this enterprise-grade" rather than "review this page".

A campaign is a sequence of Mode D runs with one shared ledger, ordered by what
actually moves the number, with guards so the score cannot drift upward on its
own. Without those guards, repeat-running a subjective rubric is a machine for
manufacturing agreement.

---

## Round 0 — say what the target costs, before doing any work

Do this first, every time, and put it in the first message. It takes one
command and it prevents the most expensive failure mode: three rounds of real
work that could never have reached the number.

```bash
python3 ~/.claude/skills/designer-dude/scripts/score.py \
  --findings .design/findings-<surface>.json --hierarchy .. --target 90
```

The arithmetic that matters:

| If every pillar were | Composite |
|---|--:|
| B+ | 85 |
| A− | **88** |
| A | 92 |
| A+ | 97 |

**A card of straight A−s scores 88.** So a 90 target means real A grades on the
heavy pillars — Typography (15) and Hierarchy (15) are 30 points between them,
Spacing is 12. Twelve minor fixes will not get there; they are worth about 3
points in total.

State it plainly:

> 90+ needs A-level typography and hierarchy, not polish. Concretely: a display
> face with a voice on a ratio scale, one unmistakable primary action per
> surface at three viewports, zero WCAG failures in both themes, and a spacing
> scale that holds across pages. That is roughly three rounds. Round 1 buys the
> most: <the top rows of the --target table>.

If the current score is capped by a WCAG failure, say that nothing else moves
the number until it is fixed — because arithmetically, nothing does.

---

## What actually has to be true for 90+

Not a checklist to tick; the substantive conditions. If one is missing, the
number is not reachable and no amount of re-running will find it.

1. **A type system with a voice.** One display face chosen on purpose, a
   ratio-based scale (6–8 steps in real use, no near-duplicates), measure
   45–75ch, tabular numerals wherever numbers align. A neutral sans doing
   every job is a B ceiling, forever.
2. **One primary action per surface, provably.** Squint at the screenshot at
   1440, 768 and 390. If the eye does not land on the same element each time,
   Hierarchy is not an A no matter how tidy the page is.
3. **Zero WCAG AA failures, both themes.** Not "mostly". The cap is absolute
   and the probe counts every text node.
4. **Scales that hold:** 2–3 radii plus a pill, 3–4 coherent shadows, spacing on
   a 4/8 base with 6–8 named steps, a z-index scale of 4–6 named layers.
5. **Copy that says something.** Specific nouns and verbs, no category filler,
   empty states that name the next action, errors that name the field and the
   fix.
6. **Consistency across 3+ surfaces.** Same type hierarchy, same radius scale,
   same accent discipline. One beautiful page in a product of mediocre ones
   scores the page, not the product — and Brand Coherence will say so.
7. **Performance inside budget on a production build.** Dev-server numbers are
   not evidence.
8. **A clean keyboard pass and a clean console.** Both are cheap and both are
   noticed.

---

## The campaign ledger

One file, `.design/campaign.md`, appended each round. Never rewritten — the
history is the anti-drift device:

```markdown
# Campaign: <product> → target 90

| Round | Date | Surfaces probed | Overall | Slop | Capped | Provisional | Delta |
|---|---|---|--:|---|---|---|--:|
| 1 | 2026-07-30 | dashboard, property, form | 71.9 | F | WCAG 1.4.3 | motion | — |
| 2 | 2026-08-02 | same 3 | 81.4 | B− | no | — | +9.5 |

## Round 2
- Fixed: FINDING-003 (contrast, verified: probe 0 failures), FINDING-007 ...
- Rejected: FINDING-012 (native select is correct here)
- Deferred: FINDING-019 (third-party widget)
- Grade moves: a11y F→A (cap lifted), color C−→A−, typography C→B
- Still blocking A: Typography (no display face chosen — needs a decision),
  Hierarchy (two competing CTAs on /dashboard)
- Decision needed from you: <the one question>
```

Every round records what was **fixed and verified**, what was **rejected and
why**, what is **deferred**, and — most importantly — **what is blocking the
next grade**. A round that cannot name its blockers did not measure anything.

---

## Round structure

1. **Re-measure first, always.** Fresh probe on every surface in scope. A grade
   may not improve on the strength of a diff.
2. **Read the `--target` table** and work top-down. The first row is the most
   points available; do not start with Motion because it is easy.
3. **Do structural work early.** Type system, colour system and hierarchy gate
   the A grades and they get more expensive the more components exist. Polish
   last, and only if points remain.
4. **Fix, verify, commit atomically** per Mode D's fix loop. One commit per
   finding, matching the repo's own convention.
5. **Re-probe, re-score with `--baseline`**, append to the ledger.
6. **Report the delta and the next blocker**, then stop and check in. Do not
   chain rounds silently: the user should get a decision point between each one.

Per-round budget: **30 fixes maximum** (Mode D's cap), and stop at the first
revert.

---

## Guards against grading your own homework

The whole risk of this mode is that the number goes up while the product does
not. In order of importance:

1. **Fresh evidence or no improvement.** Unprobed pillar → previous grade, or
   `--provisional` and its B+ cap.
2. **Identical evidence, identical grade.** If two rounds produce the same probe
   output, they produce the same score. A kinder reading of the rubric is not
   progress.
3. **No A+ farming.** A+ is "considered and delightful, rare". If A+ grades are
   appearing to close a gap, the scorecard has stopped measuring anything — and
   `--target` deliberately stops recommending steps at A.
4. **Rejections are counted and justified.** A round that rejects most of its
   own candidates is either measuring the wrong things or rationalising. Say
   which, in the ledger.
5. **The cap is not negotiable.** Never present a capped score as the real one,
   and never quietly drop `--wcag-fail` because the failure is "minor" or "on a
   page nobody visits".
6. **Benchmark check at every threshold change.** If you tune a threshold
   mid-campaign, re-run the reference sites in `calibration.md`. A threshold that
   flatters your target while failing linear.app is not a threshold.
7. **Cross-check the eye pillars against a screenshot each round.** Hierarchy
   and Content are 25 points and cannot be measured. If they are moving, there
   must be a screenshot and a sentence saying what changed.

---

## When to stop, and say so

Stop the campaign and report honestly when:

- **The remaining points need a decision that is not yours.** "Which of these
  two is the primary action", "what is this product's voice", "is this density
  right for your users" — these are the user's calls. Ask; do not invent a
  brand and score yourself on it.
- **`--target` says the target is unreachable below A+.** Report the ceiling
  from here and what structural change would raise it.
- **Two consecutive rounds move the composite by less than a point.** The cheap
  work is done. Say what the expensive work is.
- **The fixes are starting to fight the product.** If a "fix" makes the app
  worse for its actual users to satisfy a rubric line, the rubric loses. Say so
  and mark the finding rejected — with the reason, so it stays rejected.
- **The score is high and the product is still bad.** This is the one that
  matters most. If the number says 91 and the thing does not feel like a
  product you would ship, **say that instead of the number**. Then name what the
  rubric is not capturing — that gap is a bug in this skill, and it is worth
  fixing here rather than hiding behind a passing grade.

A final campaign report says: where it started, where it ended, what changed,
what was rejected and why, what is deferred, and what the next round would need
from the user. Not just the number.

---

## An honest ending beats a passing one

The point of a target is to force the structural work that a page-by-page review
keeps deferring. It is not to produce a 90. If the truthful answer at the end of
a campaign is:

> 87. The last three points are Typography and Hierarchy. Typography needs a
> display face chosen and licensed — a decision, not a fix. Hierarchy needs the
> dashboard to stop offering four equal actions, which is a product question
> about what users come here to do. Both are yours. Everything mechanical is
> done, WCAG is clean in both themes, and the scales hold across five surfaces.

…that is a better outcome than a 90 assembled from generous readings, and it is
what a senior designer would actually hand back.
