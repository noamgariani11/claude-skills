# Mode F - Campaign to a target score

Load this when the ask is **"keep running this until it scores 90+"** or "make
this enterprise-grade" rather than "review this page".

A campaign is a sequence of Mode D runs with one shared ledger, ordered by what
actually moves the number, with guards so the score cannot drift upward on its
own. Without those guards, repeat-running a subjective rubric is a machine for
manufacturing agreement.

---

## Round 0 - say what the target costs, before doing any work

Do this first, every time, and put it in the first message. It takes two
commands and it prevents the most expensive failure mode: three rounds of real
work that could never have reached the number.

```bash
S=~/.claude/skills/designer-dude/scripts
bash $S/env-check.sh <project-root>          # what this MACHINE can measure
python3 $S/score.py --findings .design/findings-<surface>.json \
        --hierarchy .. --target 90           # what the PRODUCT would have to be
```

**Run `env-check.sh` first, and quote its verdict in the first message.** Two
campaign rounds have been spent discovering that production performance could
not be measured on this machine - the prod server needs a database, the
database needs Docker, Docker is not installed. That is a fact about the
environment, not about the product, and it caps the Interaction pillar for the
whole campaign. It belongs beside the target arithmetic in round 0, not in the
round-4 write-up. The script prints the sentence to say.

The arithmetic that matters:

| If every pillar were | Composite | |
|---|--:|---|
| B+ | 85 | |
| A− | **88** | |
| A | **92** | ← **the findings ceiling**: every defect fixed, nothing left to demote |
| A+ | **100** | only in findings mode via verified credits, one criterion at a time - all eleven, each on 2+ distinct surfaces, plus measured slop A and the current `perfectionCertification` from `scoring.md`, including held-out detector, expert-correlation, representative-sample, user-task, real-AT, locale, three-engine and pinned-calibration evidence (weak/unmeasured slop caps at 97.00; missing certification or manual letters cap at 99) |

**A card of straight A−s scores 88.** So a 90 target means real A grades on the
heavy pillars - Typography (15) and Hierarchy (15) are 30 points between them,
Spacing is 12. Twelve minor fixes will not get there; they are worth about 3
points in total.

**And 92 is where fixing things stops working.** Findings mode only demotes, so
once every pillar is clean the composite is 92.00 and no further review round
can move it. Above that, each point is an **A+ credit** - a named criterion from
`scoring.md`, with evidence, on 2+ surfaces, on a pillar with nothing open. A
credit is a claim that the product is *excellent* on that dimension, not that it
is *free of defects*.

So there are two shapes of campaign, and saying which one you are in is the
whole job of round 0:

- **Target ≤92 - a defect campaign.** Findable, fixable, schedulable. Work the
  `--target` table top-down.
- **Target >92 - a design campaign.** `--target` prints how many credits the
  number needs (e.g. 95 needs five: Typography, Hierarchy, Spacing, Colour,
  Interaction). Those are not tickets. If the product cannot honestly claim
  them, say so **now**, in the first message, and offer the brief instead of
  three rounds that end in the same place.

State it plainly:

> 90+ needs A-level typography and hierarchy, not polish. Concretely: a display
> face with a voice on a ratio scale, one unmistakable primary action per
> surface at three viewports, zero WCAG failures in both themes, and a spacing
> scale that holds across pages. That is roughly three rounds. Round 1 buys the
> most: <the top rows of the --target table>.

If the current score is capped by a WCAG failure, say that nothing else moves
the number until it is fixed - because arithmetically, nothing does.

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
   scores the page, not the product - and Brand Coherence will say so.
7. **Performance inside budget on a production build.** Dev-server numbers are
   not evidence.
8. **A clean keyboard pass and a clean console.** Both are cheap and both are
   noticed.

---

## The campaign ledger

One file, `.design/campaign.md`, appended each round. Never rewritten - the
history is the anti-drift device:

```markdown
# Campaign: <product> → target 90

| Round | Date | Surfaces probed | Overall | Slop | Capped | Provisional | Credits | Delta |
|---|---|---|--:|---|---|---|---|--:|
| 1 | 2026-07-30 | dashboard, property, form | 71.9 | F | WCAG 1.4.3 | motion | - | - |
| 2 | 2026-08-02 | same 3 | 81.4 | B− | no | - | - | +9.5 |

## Round 2
- Fixed: FINDING-003 (contrast, verified: probe 0 failures), FINDING-007 ...
- Rejected: FINDING-012 (native select is correct here)
- Deferred: FINDING-019 (third-party widget)
- Grade moves: a11y F→A (cap lifted), color C−→A−, typography C→B
- Still blocking A: Typography (no display face chosen - needs a decision),
  Hierarchy (two competing CTAs on /dashboard)
- Decision needed from you: <the one question>
```

Every round records what was **fixed and verified**, what was **rejected and
why**, what is **deferred**, and - most importantly - **what is blocking the
next grade**. A round that cannot name its blockers did not measure anything.

---

## Starting from a genuinely bad site

The default round structure assumes a competent product with defects. A site
scoring in the C or D band is a different problem, and running the normal loop
on it produces 200 findings, a demoralised user, and a score that barely moves.

**The diagnosis that decides the plan:** is this a product with defects, or a
product with no system? Two minutes of measurement answers it:

```bash
python3 $S/probe-report.py .design/probe-<surface>.json | head -40
python3 $S/contrast.py --harmony --css <token file>
bash $S/micro-checks.sh <root>
```

If the radius count is over 6, the type sizes over 14, the spacing off-base,
the hue families over 6, and the tokens are colour-named rather than
role-named, then **there is no system, and every individual finding is a
symptom of that**. Fixing 40 symptoms one at a time is the slowest possible
route and it regresses constantly, because each fix is a local decision that
contradicts the next one.

**Install the system first, in this order.** Each step is one round, each is
mostly a token-file change, and each makes the next one cheaper:

| Round | Work | Buys |
|---|---|---|
| 1 | **Tokens and roles.** Rename colour-named tokens to semantic roles, build one lightness ladder, set the neutral temperature, declare `color-scheme`, fix every AA failure. `color.md` sections 2-5. | Lifts the WCAG cap. Nothing else moves the number until this is done. |
| 2 | **The scales.** One spacing base with 6-8 steps, 2-3 radii plus a pill, 3-4 shadows, a 4-6 layer z-scale, one type ratio with 6-8 steps. Delete the near-duplicates rather than adding to them. | Craft and Spacing, and it makes every later fix a one-line change |
| 3 | **The controls.** Buttons, inputs, selects, focus rings, the seven states, target sizes. `components.md` end to end. This is where most of the felt "cheapness" lives. | Interaction, A11y, and the biggest visible jump per hour |
| 4 | **Hierarchy and type voice.** One primary action per surface, a display face chosen on purpose, measure and leading in band. | The two 15-point pillars, which is where 90 actually comes from |
| 5 | **Copy and content.** Empty states, errors, labels, the slop tells. `voice.md`. | Content, and it is cheap once the layout stops fighting |
| 6 | **Motion, polish, the long tail.** | The last 2-4 points |

Two rules specific to this path:

- **Do not fix a symptom in a round whose system change will overwrite it.**
  Hand-patching a button's contrast in round 1 wastes the fix when round 3
  rebuilds the button from tokens. Note it, and let the system change close it.
- **Say the shape of the plan in round 0**, with the honest number: a D-band
  product is typically five to seven rounds from 90, most of it structural, and
  a chunk of it needs decisions only the user can make (the face, the accent,
  what the primary action is). A user who hears that up front stays in the
  campaign. A user who discovers it in round 4 does not.

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
5. **Re-probe, run the regression gate, then re-score with `--baseline`** and
   append to the ledger. The gate is not optional and it is not a formality:

   ```bash
   python3 $S/regress.py --before .design/baseline/probe-*.json \
                         --after  .design/probe-*.json
   ```

   It exits 1 on any critical or major regression. **Read it before you look at
   the new composite.** A round that raised the number while breaking something
   measured has not improved the product, and a campaign that reports the score
   without the regression line is the exact machine for manufacturing agreement
   this mode exists to prevent. Then run the project's own gates, because a
   component edit is how a bundle boundary breaks. Full protocol in
   `regression.md`.
5b. **Record the ratchet and let the rejections compound.** Two things end a
   round properly, and both make the NEXT one cheaper:

   ```bash
   bash $S/ratchet.sh --emit <root>                      # the floor holds
   python3 $S/fixture-case.py --from-findings .design/findings-<surface>.json
   ```

   The first stops this round's counts drifting back up between campaigns. The
   second lists every rejection that does not yet have a precision case - add
   them, then recall, `--precision`, `--mutations`, `--pipeline`, and `--runner`
   must all stay green. A
   campaign that argues the same false positive in rounds 1, 3 and 5 is a
   campaign with no memory.

6. **Predict the next round before running it.** `--target` prints the points
   each remaining pillar upgrade buys. Sum what the next round could plausibly
   land and write that number in the ledger. **If the prediction is under a
   point, do not run the round** - say what the expensive work is instead. The
   "two consecutive rounds under a point" rule below is the backstop; this is
   the version that does not spend a round to learn it.
7. **Report the delta, the prediction, and the next blocker**, then stop and
   check in. Do not chain rounds silently: the user should get a decision point
   between each one.

Per-round budget: **30 fixes maximum** (Mode D's cap), and stop at the first
revert.

### One probe file per surface, kept

`probe-report.py --compare` needs **3+ probe files that still exist** to measure
cross-surface consistency. A round that probes four surfaces into one filename
loses that, and Brand Coherence quietly reverts from measured to felt - in the
direction that always flatters. Check the file count before scoring.

---

## Guards against grading your own homework

The whole risk of this mode is that the number goes up while the product does
not. In order of importance:

1. **Fresh evidence or no improvement.** Unprobed pillar → previous grade, or
   `--provisional` and its B+ cap.
2. **Identical evidence, identical grade.** If two rounds produce the same probe
   output, they produce the same score. A kinder reading of the rubric is not
   progress.
3. **No A+ farming.** A+ is "considered and delightful, rare", and it is
   reachable only through a credit that names a criterion, carries evidence,
   cites 2+ surfaces and sits on a pillar with zero open findings. `--target`
   deliberately never *recommends* a credit - it only prices one. Before
   writing one, run the falsifier:

   ```bash
   python3 $S/probe-report.py --credits .design/probe-*.json
   ```

   `BLOCKED` is final - a measured clause of that criterion fails, and no
   argument outranks it. `OPEN` means only that the machine clauses hold; the
   `??` ones are still yours to argue, and the tool never awards anything (its
   stubs are `status: "candidate"`, which `score.py` refuses to count). Two
   further rules:
   - **Never award a credit in the same round that fixed the pillar's last
     defect.** It belongs to the next round, after a fresh probe confirms the
     fix held.
   - **A credit written while a target is unmet is suspect by construction.**
     If you would not have written it before seeing the gap, do not write it
     after. The findings file keeps it forever; so does the ledger.
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
8. **Put the A-graded surfaces in front of real personas.** Every pillar grades
   form; none asks whether the design serves the task. Once a surface reaches
   A, hand it to `user-test --focus <surface>` (mode-d-review.md §4b) and turn
   any failed task into a `critical` finding on Hierarchy or Content. It is the
   only guard here that can move a grade **down** on evidence the probe cannot
   see, and a rubric that only finds its own kind of defect will always end a
   campaign agreeing with itself.
8. **Interaction may not be graded above B without a hover/focus pass.**
   Mode D §2c and `browser-verification.md`, on every repeated component, in
   both themes, **every round** - a fix landed in round 3 can kill a hover that
   worked in round 2, and `regress.py` tracks the automatable half of that
   precisely because the rest-state screenshots will not show it. A campaign that
   grades ten rounds of rest-state screenshots will hand back an A+ over a row
   whose hover paints the colour it already was. This is not hypothetical: it
   is where this rule came from.
9. **Grade what you shipped, hardest of all.** In a campaign the reviewer and
   the author are the same, and the work most likely to be waved through is
   the work this skill wrote in an earlier round. Before scoring, re-read the
   components you authored *against the slop list*, as though someone else had
   sent them to you. Indexed catalogues, ordinal ornament, decorative labels
   above headings that already say it - these are patterns a design-minded
   author reaches for precisely because they *look* considered. The comment in
   the code explaining why the numeral is there is not evidence that it should
   be; it is evidence that the author knew it needed defending.

---

## When the ceiling is arithmetic - hand back a brief, not a paragraph

`score.py` says it outright: *"Nothing left to move below A: findings ceiling
reached at 92.00."* At that point the campaign is over as a **review**, and the
correct deliverable changes shape. What is left is not a backlog - it is a
design brief, and stopping at "those are briefs, not findings" leaves the user
holding the hard part alone.

So do the brief. Switch to **Mode A** (`mode-a-direction.md`) with one
difference: the product already exists, so the intake is the shipped thing
rather than a blank page. For each pillar the target still needs a credit on,
produce **three directions, not one**, and for each:

| | What it must say |
|---|---|
| **The move** | Concretely what changes. "Söhne for UI, Signifier for display, 1.25 ratio, 7 steps" - not "a stronger type system". |
| **What it buys** | Which A+ criterion it would satisfy, and the points, from `--target`. |
| **What it costs** | Files touched, migration shape, and the risk. "Redefining `text-*` across ~4,800 usages shifts the density of every table." |
| **What it forecloses** | The thing you cannot easily undo afterwards. |
| **Whose call it is** | Almost always the user's. Name the decision in one sentence. |

Three fronts recur, because they are what separates 92 from 95 in every
product: **a type system with a voice** (not a tuned framework default), **a
brand point of view** (something more specific than "warm and restrained"), and
**one interaction or motion moment someone would remember**. Price all three.

Then stop and ask - `AskUserQuestion`, one question, the actual decision. Do not
start implementing a bespoke type system because a score wanted five points.

**Write the brief into the ledger** (or `DESIGN.md` if the user takes a
direction). A campaign that ends with a costed brief and an honest 92 has
delivered more than one that ends with a 95.

---

## When to stop, and say so

Stop the campaign and report honestly when:

- **The remaining points need a decision that is not yours.** "Which of these
  two is the primary action", "what is this product's voice", "is this density
  right for your users" - these are the user's calls. Ask; do not invent a
  brand and score yourself on it.
- **`--target` says the target is unreachable below A+.** Report the ceiling
  from here, then hand back the costed brief above. "Unreachable" is not the
  end of the deliverable, it is a change of deliverable.
- **Two consecutive rounds move the composite by less than a point.** The cheap
  work is done. Say what the expensive work is.
- **The fixes are starting to fight the product.** If a "fix" makes the app
  worse for its actual users to satisfy a rubric line, the rubric loses. Say so
  and mark the finding rejected - with the reason, so it stays rejected.
- **The score is high and the product is still bad.** This is the one that
  matters most. If the number says 91 and the thing does not feel like a
  product you would ship, **say that instead of the number**. Then name what the
  rubric is not capturing - that gap is a bug in this skill, and it is worth
  fixing here rather than hiding behind a passing grade.

  And do not stop at saying it: run the A-graded surfaces through `user-test`
  (guard 8 above). "High score, bad product" almost always means the pillars
  graded the form while the tasks failed, and a persona failing a task is
  evidence you can put in the findings file rather than a feeling you have to
  argue.

A final campaign report says: where it started, where it ended, what changed,
what was rejected and why, what is deferred, and what the next round would need
from the user. Not just the number.

---

## An honest ending beats a passing one

The point of a target is to force the structural work that a page-by-page review
keeps deferring. It is not to produce a 90. If the truthful answer at the end of
a campaign is:

> 87. The last three points are Typography and Hierarchy. Typography needs a
> display face chosen and licensed - a decision, not a fix. Hierarchy needs the
> dashboard to stop offering four equal actions, which is a product question
> about what users come here to do. Both are yours. Everything mechanical is
> done, WCAG is clean in both themes, and the scales hold across five surfaces.

…that is a better outcome than a 90 assembled from generous readings, and it is
what a senior designer would actually hand back.
