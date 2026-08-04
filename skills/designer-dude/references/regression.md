# The no-regression contract

Load this before the Mode D fix loop and before every Mode F round. It is the
half of the job that is not "find things".

A design review that finds ten real defects and introduces one regression has
not netted nine wins. It has spent the user's trust, because now every future
change from this skill has to be checked by hand. **The bar is: the product is
strictly better after the round than before it, on every measured axis, on
every surface, in both themes.** Not better on average. Strictly better, or
explained.

This is enforceable, not aspirational, because the probe already measures the
things that break.

---

## 1. Why design fixes regress

Design changes look local and are not. The failure modes, in the order they
actually happen:

| Class | What it looks like | Caught by |
|---|---|---|
| **Token cascade** | Darkened one grey for contrast; nine other pairings moved, two now fail | `contrast.py --css`, probe contrast pass |
| **Theme asymmetry** | Fixed it in light, broke it in dark, never looked | dark probe pass |
| **Viewport asymmetry** | Fixed the 1440 layout, introduced horizontal overflow at 320 | viewport sweep |
| **State deletion** | Replaced a component's classes; the `:active` and `:disabled` rules went with them | `states.*Coverage` |
| **Focus removal** | Restyled a button, `outline-none` came along for the ride | `focusRing.invisible` |
| **Focus obstruction** | Sticky/fixed chrome completely covers the focused control | `focusRing.completelyObscured` |
| **Name drift** | Visible label changed; stale `aria-label` no longer contains it | browser-confirmed `browserLabelInName` |
| **I18n break** | Translation growth or RTL direction introduces clipping/overflow | text-expansion / RTL probe delta |
| **Target shrink** | Tightened padding for density; the link is now 22px | `belowWcagTarget24` |
| **Reflow** | Changed a font stack or a size; measure, leading, and line count all moved | typography offenders, screenshots |
| **Silent no-op** | Wrote v3 Tailwind syntax into a v4 build. Nothing changed, nothing errored | re-probe showing zero movement |
| **Bundle break** | Touched a component that crossed the server/client boundary | the project's own build |
| **Semantic loss** | Swapped a `<button>` for a styled `<div>` to control its look | `controlsMissingAccessibleName` |
| **Scope creep** | "While I was in there" | the diff |

The last one is the most common and the least excusable. Mode D's rule stands:
touching a file not tied to the finding is a stop condition.

---

## 2. Before you change anything: the snapshot

Cheap, and the whole guard depends on it.

```bash
mkdir -p .design/baseline
cp .design/probe-*.json .design/baseline/
mkdir -p .design/baseline/screenshots .design/baseline/accessibility
cp .design/screenshots/*.png .design/baseline/screenshots/
cp .design/accessibility/*.aria.yml .design/baseline/accessibility/
git status --porcelain          # know whose uncommitted work is in this tree
git log --oneline -20           # learn the commit convention before you use it
```

Two rules:

- **Never start a fix loop on a dirty tree you did not dirty.** If someone
  else's work is uncommitted, say so and stop. You cannot revert cleanly out of
  a tree you do not own, and `git add -A` in that situation is how a design
  round eats a colleague's afternoon.
- **The baseline is the probe from before the first fix**, not from three
  rounds ago. Copy it at the top of every round.

---

## 3. During: per-fix verification

The Mode D loop already says fix, verify, commit atomically. The verification
step is specifically:

1. **The measurement you targeted moved.** Not "the code changed". If
   `textContrast.failures` was 4 and is still 4, the fix did not land, and the
   most likely reason is v3 syntax in a v4 project or a token that something
   else overrides. Check `tailwind.md` section 0.
2. **Nothing else moved the wrong way** on that surface.
3. **The console is clean** and no new failed requests appeared.
4. **The commit is one finding.** So that a revert is one command.

For a contrast or token change, run the cascade check *before* editing:

```bash
grep -rn "var(--color-muted)\|text-muted" src | wc -l   # how many consumers?
python3 $S/contrast.py --css src/app/globals.css        # every pairing, both themes
```

If the cascade exceeds 10 consumers, stop and ask. That is not caution, it is
arithmetic: a token with 40 consumers is 40 chances to regress and you can only
look at the ones you thought of.

---

## 4. After: the mechanical gate

Re-probe every surface you touched, then:

```bash
S=~/.claude/skills/designer-dude/scripts
python3 $S/regress.py --before .design/baseline/probe-*.json \
                      --after  .design/probe-*.json \
                      --json   .design/regressions.json
python3 $S/artifact-regress.py --baseline .design/baseline \
                              --current .design \
                              --out .design/artifact-regression.json
```

It matches surfaces by label and runs by viewport tag, then reports every
measured metric that moved the wrong way, split by severity. It exits 1 on any
critical or major regression.

**Read it before you re-score.** A round that improved the composite while
`regress.py` exits 1 has not improved the product, and reporting the new number
without the regression line is the exact failure the anti-inflation rules exist
to prevent.

`regress.py` defends the round. **`ratchet.sh` defends the months after it**,
which is the part that has been going undefended: every count a campaign drove
down starts drifting back up on the next feature branch, and nobody notices
until the next campaign re-measures and pays for the work twice.

```bash
bash $S/ratchet.sh --emit <root>     # end of round: record the floor
bash $S/ratchet.sh <root>            # in .githooks/pre-push: fail on a new regression
```

It is static, DB-free and takes a second, and it can only fire on an increase -
never on code that was already there - which is what makes it safe to wire into
a hook the day you write it. Raising a recorded ceiling is allowed, but it has
to be deliberate: re-emit in the same commit and say why in the body.

Then run **the project's own gates**, because design changes break builds:

```bash
# whatever this repo actually uses - read package.json / CLAUDE.md first
pnpm typecheck && pnpm lint && pnpm build
```

The build gate matters more than it looks. It is usually the only thing that
catches a server/client bundle-boundary break, and a component edit is exactly
how that happens.

---

## 5. What counts as a regression, and what does not

**Always a regression, always revert or explain:**

- Any new WCAG failure of any kind, on any surface, in either theme.
- A focus ring, a state, or an accessible name that existed and now does not.
- A new console error or failed request.
- Horizontal overflow at any probed viewport.
- A target that dropped under 24x24.

**A regression unless argued in the ledger:**

- Coverage of hover, focus-visible, active, or disabled falling.
- A slop tell count rising.
- Accent share crossing 10%.
- LCP worsening by more than about 15%, or CLS crossing 0.1.

**Not a regression, do not chase:**

- A count that moved because the *page content* changed (more rows in a seeded
  table means more targets, more text nodes, more elements). Confirm against
  the screenshot before treating a count as a code regression.
- Scale counts rising because a *new legitimate component* landed.
- Lab performance noise inside about 15%. One machine, one network.
- A metric that only exists in the after-probe, because the check is new.
  `regress.py` skips those on purpose; a new check finding an old defect is a
  finding, not a regression.

---

## 6. The revert protocol

When a regression is confirmed:

1. `git revert <sha>` the single commit. Do not "fix forward" mid-round.
   Fix-forward on top of a misunderstanding is how one bad fix becomes three.
2. Re-probe. Confirm the metric returned to baseline.
3. Mark the finding `deferred`, with the reason: what broke, and what a correct
   fix would need. It **keeps counting against the grade**, which is right: a
   defect nobody could safely fix from here is still one the user is shipping.
4. **Stop the round.** Mode D lists any revert as a stop condition, and it
   means it. A revert means something was misunderstood, and the next fix was
   planned by the same understanding.
5. Report it at the top of the write-up, above the good news.

---

## 7. The visual regression pass the probe cannot do

Numbers do not catch everything. **Three** things need your eyes and a live
browser, every round. Drive it through the `browse` skill; the session order,
the screenshot conventions and the memory rules are in
`browser-verification.md`.

**Screenshot + ARIA diff.** The runner double-captures with animations disabled;
an unstable capture cannot become a baseline. `artifact-regress.py` compares
the pinned PNG and `.aria.yml` sets, writes a diff image for every visual
regression, and fails missing/new/dimension-shifted artifacts. Open the 1440,
the 390, the dark pass, and every generated diff. You are looking for: a
layout that shifted, a component that lost its shape, text that now wraps
differently, an element that vanished. Five seconds each, and it catches the
class of regression that has no metric.

**The states, re-exercised.** A screenshot pair compares two rest states, so a
fix that broke a hover, a focus ring or a pressed state passes a screenshot
diff untouched. Re-run the §2c state pass on any component the round edited,
and on any component that consumes a token the round changed. Interaction is
the pillar most likely to regress silently, because most of it does not exist
until a pointer or a key is on the element - and the automatable part of that
(`inertHoverFills`, `hueOnlyHoverFills`, `inertHoverBorders`,
`hoverFillsCoveringOwnRule`, `hoverFillsWithoutPadding`) is in `regress.py`
precisely because a tint edit can turn a working hover into a dead one without
touching a single rest-state pixel.

**The surfaces you did not fix.** A token change reaches everything. If you
edited a token, re-probe at least one surface you did **not** intend to change.
That single extra probe is the highest-value minute in the round, because a
cascade regression on an unvisited page is invisible until a user finds it.

---

## 8. The ledger line

Every Mode F round records this, whether or not anything regressed:

```markdown
- Regression check: `regress.py` clean across 4 surfaces (12 improvements),
  gates green (typecheck, lint, build). Dark pass re-screenshotted.
```

or

```markdown
- Regression check: FAILED. FINDING-014's token change dropped
  `states.focusVisibleCoverage` 82 -> 61 on properties and dashboard.
  Reverted a1b2c3d, FINDING-014 -> deferred. Round stopped at 6 of 11 fixes.
```

A round with no regression line did not check.
