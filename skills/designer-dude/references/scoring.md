# Scoring reference

Load this for Mode C, Mode D, and Mode F. Three things get graded
independently. None are curved.

1. **Each of 11 pillars** — its own letter grade (A+ to F).
2. **Overall Design Score** — weighted composite → letter + 0–100 number.
3. **AI Slop Score** — standalone letter grade.

Every grade goes on the report. A page can be A on craft, C on content,
F on slop. That is the honest read.

---

## The pipeline: measure, then judge, then grade

Grading a page from a screenshot is guessing, and a guess dressed as a grade
costs the user real work. So the number comes out of a chain where every step
is auditable:

```bash
S=~/.claude/skills/designer-dude/scripts

# 1. MEASURE — facts, not opinions. Writes JSON + screenshots to disk.
#    (write the config first; exact file in mode-d-review.md)
#    browser_run_code_unsafe({ filename: "$S/probe-runner.mjs" })

# 2. JUDGE the measured layer — thresholds live in source, not in your head
python3 $S/probe-report.py .design/probe-<page>.json \
        --emit-findings .design/findings-<page>.json

# 3. CONFIRM every candidate, reject the false ones, ADD what only your eye
#    sees (hierarchy, voice, IA, taste). Edit findings-<page>.json:
#    set "status": "confirmed" | "rejected", and add your own entries.

# 4. GRADE — derived from the confirmed findings
python3 $S/score.py --findings .design/findings-<page>.json \
        --hierarchy B --ia B+ --consistency B --target 90

# supporting tools
bash $S/micro-checks.sh <project-root>            # static/countable claims
python3 $S/contrast.py --css src/app/globals.css  # palette, per theme
node $S/probe-selftest.mjs                        # after ANY probe.js edit
```

**Never do the weighted sum by hand, and never retype a number you did not
run.** Eleven letter→number conversions, a weighted sum and four sub-averages
is precisely the arithmetic that goes quietly wrong, and a scorecard with bad
maths is worse than none: it launders a guess as a measurement.

`score.py --selftest` verifies the grade tables and the demotion maths.

### Why grades come from findings

`score.py --findings` starts every pillar at A and demotes it by the severity
of each unresolved finding. That makes a grade **a function of documented
evidence**, so the same evidence scores the same next week, and a
run-it-again-until-it-is-90 campaign measures the product instead of your mood.

Demotion, executed by the script (`FULL_LETTER = 11` points, A = 92):

| Severity | Cost | Meaning |
|---|---|---|
| **critical** | a full letter | WCAG fail, unreadable, broken mapping, the eye cannot find the primary action |
| **major** | half a letter | a senior designer flags it on first scroll |
| **minor** | a quarter | polish, small inconsistency |
| **petty** | 0 | noted, never moves a grade |

Two minors = one major. Four minors = one critical. A single critical takes a
pillar from A to B, so no pillar with an unresolved critical reads above B.

A finding stops counting only at `status: "fixed"` or `"rejected"`.
**`"deferred"` still counts** — a defect nobody can fix from here is still a
defect the user is shipping.

---

## The evidence rule

**A pillar you did not capture evidence for cannot be graded A.** Pass it in
`--provisional` and it is capped at B+ and labelled in the output.

| Pillar | What must exist before you grade it |
|---|---|
| Typography | probe run (families, scale, measure, leading) |
| Visual Hierarchy | a screenshot you actually looked at, at ≥2 viewports |
| Spacing & Layout | probe run + a screenshot |
| Color & Contrast | probe contrast pass, both themes if a dark mode exists |
| Interaction & Performance | probe focus/cursor/target pass + lab perf, states exercised |
| Content & Voice | you read the copy on the page |
| Accessibility | probe a11y pass **plus** a manual keyboard pass |
| Responsiveness | probe at 320 / 768 / 1440 minimum |
| Craft | probe system scales + screenshots |
| Information Architecture | you navigated the product, not just one page |
| Motion | a reduced-motion probe pass |
| Cross-page consistency | 3+ pages probed |

`probe-report.py` prints this ledger every run, splitting what it measured from
what only your eye can answer. Read it before writing grades.

---

## The user-eye filter (runs on every pillar)

The probe cannot do this part. Before scoring, imagine a first-time user
landing cold:

- **Where does the eye go first? Second? Third?** Does that match what is
  important? (Yarbus eye-tracking, Nielsen F/Z scan.)
- **What does the eye skip entirely?** If the primary CTA got skipped,
  hierarchy failed — dock points even if everything is pretty.
- **What causes friction — a pause, a squint, a scroll-back?** Friction is
  the signal. The Aesthetic-Usability Effect cuts both ways: it buys
  goodwill but does not excuse broken mapping.
- **Would the eye feel tired after 30 seconds?** Visual noise, competing
  accents, and unresolved tension all drain it.
- **Does this look decided, or assembled?** Assembled is a slop tell.

A pillar earns an A only if the eye flows through it without effort.

**Bands:** **A+** considered and delightful, rare · **A** strong, one nit at
most · **A−** strong with a rough edge · **B+/B/B−** solid, real issues ·
**C+/C/C−** functional, generic, or sloppy · **D** the eye is working against
it · **F** actively hurts the product.

**Never award a grade without naming element + rule + fix.**

---

## The 11 pillars

Weights sum to 100. Accessibility carries 8 and additionally triggers the hard
cap below. The **App column** is what an A means on a dense product surface
rather than a marketing page — load `enterprise.md` when the target is a real
application.

| # | Pillar | W | What an A looks like | On an app surface |
|---|---|:-:|---|---|
| 1 | **Typography** | 15 | Type scale on a ratio (1.2 / 1.25 / 1.333). Measure 45–75ch. Leading 1.4–1.6 body / 1.1–1.25 display. Pairing has real contrast (weight + category). Real quotes and apostrophes. No Inter/Roboto/Arial/Poppins as the voice. No orphans in headlines. | Tabular numerals in every numeric column. A dense size (12–13px) used deliberately, not accidentally. Label distinguishable from value without colour. |
| 2 | **Visual Hierarchy** | 15 | One primary action per screen (Von Restorff). Eye finds it in <1s. Weight and color carry hierarchy, not size alone. F/Z/center-stage scan matches content intent. | The row you must act on is findable in a 200-row table. Toolbar action, page action and row action are three distinguishable things. |
| 3 | **Spacing & Layout** | 12 | Grid is felt. Spacing on a 4/8 base. Related elements clustered (Gestalt proximity), unrelated separated. Sections breathe. Nothing floats, nothing crams. | Density is a decision: 40–56px rows, not 72px of air. Form groups read as groups. No 1440px-wide single-column form. |
| 4 | **Color & Contrast** | 10 | Semantic roles (surface/text/accent/semantic), not color-named tokens. oklch-coherent; Display P3 where supported. WCAG AA minimum, AAA on body where achievable. No pure `#000`/`#FFF`. Accent ≤10% of pixels. Dark mode designed, not inverted. | Status colour is never the only signal. Semantic states legible at 12px. Selected-row tint distinguishable from hover tint. |
| 5 | **Interaction & Performance** | 10 | Hover / focus-visible / active / disabled / loading / empty / error all designed. Focus ring never removed without replacement. Targets ≥44px (Fitts; WCAG 2.5.8 requires ≥24px). Perceived feedback <100ms. **Perf is UX: LCP ≤2.5s, INP ≤200ms, CLS <0.1** at p75 CrUX. Unreserved image dimensions and long main-thread work are design failures. Clickable elements show `cursor: pointer`. | Pending state on every mutation. Bulk actions report partial failure per item. Destructive actions are undoable or confirmed, never both silent and instant. |
| 6 | **Content & Voice** | 10 | Copy earns its space. Specific verbs, specific nouns. No "Welcome to", "Unlock the power of", "Your all-in-one". Microcopy matches brand voice. Labels precede inputs. Error copy helps rather than scolds. No AI self-reference emoji. | Domain vocabulary is the user's, not the schema's. Empty states say what to do next. Errors name the field and the fix. |
| 7 | **Accessibility** | 8 | WCAG 2.2 AA. Keyboard-reachable. Landmarks, labels, alt text, heading order. Color never the only signal. Motion-reduce works. Form errors announced. Hits the 2.2 SCs most sites miss: 2.4.11 focus not obscured, 2.5.7 dragging alternative, 2.5.8 target size 24×24, 3.3.7 redundant entry, 3.3.8 accessible authentication. | Tables use `th[scope]`. Sortable headers expose `aria-sort`. Modals trap focus and restore it. Live regions announce async results. |
| 8 | **Responsiveness** | 7 | Intentional at 320 / 768 / 1024 / 1440 / 1920. Type scale adapts. Touch targets reflow. Nothing unintentionally horizontal-scrolls. Breakpoints are design decisions, not media queries. | Tables have a real small-screen answer (card view, priority columns, or a scroll region with a pinned first column) rather than a squeeze. |
| 9 | **Craft & Considered Details** | 5 | Icon strokes consistent. Radius scale disciplined. Shadows coherent (single light source). No 1px misalignment. Assets at correct DPR. Favicon exists. Console clean. Every detail visibly answered a question — **decided, not assembled**. | Numbers align on the decimal. Dates in one format. Sort order is deterministic on ties. |
| 10 | **Information Architecture** | 4 | The user's mental model matches the UI (Norman). Nav reflects the job, not the org chart. Labels use user language, not internal jargon. Search exists where depth >2 levels. | The object model is visible: a user can predict where a record lives. Deep links survive a refresh. |
| 11 | **Motion** | 4 | Motion earns its place (continuity / feedback / delight — one at a time). 150–300ms UI, 400–600ms transitions. Ease-out on enter, ease-in on exit. `prefers-reduced-motion` honored. | Nothing animates in a list of 200 rows. Skeletons match the shape of what arrives. |

### The accessibility hard cap

**Any unresolved WCAG 2.2 AA failure caps the Overall score at C+**, no matter
how the weighted sum lands. Pass `--wcag-fail`.

A product that looks immaculate and locks out keyboard users has not earned a
B. The weight alone could not express that, because weighting is linear and
exclusion is not. State the cap explicitly and name the failure that triggered
it.

Do not apply the cap for: WCAG AAA misses, WCAG 3 draft requirements, APCA Lc
values, or **4.1.1 Parsing, which is obsolete** — never dock for it.

---

## Composite sub-scores

- **Overall** — weighted 0–100 across the 11 pillars.
- **Craft** — mean of Typography, Spacing, Color, Motion, Craft & Details.
- **Clarity** — mean of Hierarchy, Interaction & Performance, IA, A11y.
- **Brand Coherence** — mean of Content/Voice and a **cross-page consistency
  check** (do 3+ pages look like one product — same type hierarchy, same radius
  scale, same accent usage?). Pass it as `--consistency`. It deliberately does
  not reuse Typography; that is already inside Craft.
- **Slop** — the standalone A–F grade below.

### Grade values and bands

The script owns these. They are **round-trip stable**: every letter's numeric
value maps back to the same letter.

| Letter | Value | Band |
|---|:---:|:---:|
| A+ | 97 | 95–100 |
| A | 92 | 90–94 |
| A− | 88 | 87–89 |
| B+ | 85 | 84–86 |
| B | 81 | 80–83 |
| B− | 78 | 77–79 |
| C+ | 75 | 74–76 |
| C | 71 | 70–73 |
| C− | 68 | 67–69 |
| D | 63 | 60–66 |
| F | 50 | <60 |

**Never round up.** An 86.9 is a B+, not an A−. The script floors for you.

**What a target actually costs** (`score.py --target` prints this): every
pillar at B+ scores 85, at A− scores 88, at A scores 92. So **90+ is
unreachable without real A grades on the heavy pillars** — Typography and
Hierarchy carry 30 points between them. Say that out loud before starting a
campaign; see `mode-f-campaign.md`.

---

## AI Slop Score (A–F) — standalone, weighted

`probe-report.py` computes the measurable part and prints the grade plus the
tells that fired. Start at A. Hits are weighted by severity. **Three
full-letter hits = D. Five = F.**

**Contrastive corpus check — do this before finalizing the grade.** The list
below names what slop *is*. The corpus (see `canon.md`) shows what shipped
systems actually do. Spot-check the target's palette, type, and hero against
2–3 corpus files. If it clusters with the slop tells and away from every real
system, say so with the contrast: *"No system in the corpus uses a blue→purple
hero gradient; this leans on it."* A positive reference lands harder than the
rule alone.

### Brand killers — drop a full letter each

1. **Purple / violet / indigo gradient**, especially blue→purple. The single
   strongest "ChatGPT wrapper" tell. *(measured: `slop.purpleOrIndigoGradients`)*
2. **Gradient-mesh orb hero.** Also animated beams, sparkle trails, glow auras
   behind buttons. *(measured: `largeRadialGradients`)*
3. **Three-column feature grid** — icon-in-colored-circle, bold title,
   two-line description, perfectly symmetrical. *(measured: `threeUpFeatureGrids`)*
4. **Bento-grid hero** paired with "Build the future" / "The future of X" /
   "The platform for Y".
5. **Default shadcn grays + unmodified Lucide icons + uniform `rounded-xl`.**
   A theme is not a design. *(partly measured: `system.radius.distinct == 1`)*
6. **Inter or Poppins as the body voice.** Inter is a fine fallback, never a
   face. *(measured: the most-used rendered family)*
7. **Centered-everything.** Real design picks alignment per element.
   *(measured: `centredShare`)*
8. **Glassmorphism on every card.** *(measured: `backdropBlurElements`)*

### Hits — drop half a letter each

9. **Icons in colored circles** as decoration. *(measured)*
10. **Uniform bubbly border-radius.** A radius scale is 2–3 meaningful values.
11. **Decorative blobs / floating orbs / wavy dividers.**
12. **Emoji as design elements.** 🚀 in headers, emoji bullets, emoji in
    buttons. *(measured)*
13. **Colored left-border on cards** (`border-left: 3px solid <accent>`). *(measured)*
14. **Generic hero copy.** "Welcome to X", "Unlock the power of…", "Your
    all-in-one solution for…", "Transform your workflow". *(measured)*
15. **Cookie-cutter section rhythm.** Hero → 3 features → testimonials →
    pricing → CTA at uniform heights. No surprises, no memory.
16. **Gradient text on headlines** for no reason. *(measured)*

### Nits — drop a quarter letter each

17. **Fake marquee logo strip** ("As seen in…" with identical gray logos). *(measured)*
18. **"Powered by GPT-4" / "Built with Claude" badges.** *(measured)*
19. **Stock "diverse team" hero photo** with the laptop and the coffee.
20. **Fake dashboard screenshots** with meaningless sparklines.
21. **Identical 3-testimonial carousel** with placeholder-looking avatars.

**Font blacklist:** Papyrus, Comic Sans, Lobster, Bradley Hand.
**Never-as-primary:** Inter, Roboto, Arial, default Helvetica, Poppins,
Montserrat, personality-free system-ui. Fine as fallbacks, never as the face.

---

## Taste claims vs. rules — know which you are wielding

Some entries above are defensible on evidence (contrast ratios, target sizes,
measure). Others are **period taste** — true of 2026, and dated eventually.
Slop items 1–8 in particular are fashion calls, correct now because the
pattern signals low effort *today*. `probe-report.py` tags every candidate
`rule` or `taste call` for exactly this reason.

When a user pushes back on a taste call with an actual argument — their
audience expects the convention, the pattern tests well, the brand predates
the trend — **update**. Do not defend a fashion call as though it were a
contrast ratio:

> That is a taste call, not an accessibility one. The gradient is not broken;
> it reads as generic to anyone who has seen ten AI landing pages this year.
> If your buyers have not, it costs you less than it costs you with investors.

The three things that are never taste calls: **WCAG failures, contrast math,
and performance budgets.** Hold the line on those.

---

## Things this rubric does NOT dock for

Guard-rails against confident wrongness. Each of these has been mistaken for a
defect — several by this skill's own tooling before it was fixed.

- **A native `<select>`.** Often the better choice — superior mobile and
  screen-reader behavior. Flag only when it genuinely clashes with a
  heavily-styled form, or when the design needs option content a `<select>`
  cannot render. A broken *custom* dropdown is the real finding.
- **Unstyled scrollbars.** A preference, not a defect. Custom scrollbars
  frequently reduce hit-area and affordance. Raise as optional polish; never
  dock a full grade. If styled: thumb ≥8px, ≥3:1 against its track.
- **`№` and other typographic marks.** House style, not a defect, and not
  evidence of AI authorship.
- **System fonts on a deliberately utilitarian product.** Internal tools and
  dashboards can correctly choose boring.
- **WCAG 4.1.1 Parsing.** Obsolete.
- **Sparse copy.** Restraint is not laziness.
- **An absent dark mode.** Only a finding if the product promises one or the
  audience expects one.
- **A `*-soft` / `*-subtle` token failing as a foreground.** Those are tinted
  *surfaces*. Check the text drawn ON them, not them as text.
- **`wash`-style fill-only tokens paired with text.** Many systems forbid that
  pairing by house rule; read the project's styling notes before calling the
  ratio a defect. `contrast.py` puts these in a separate CHECK section.
- **A raw `<img>` carrying a suppression comment that explains why.** Read the
  comment: presigned URLs and private dynamic hosts are real reasons
  `next/image` cannot be used.
- **Lab LCP/CLS from a dev server.** Dev numbers are not production numbers.
  Label them lab, or re-measure against a production build.
- **A grep count.** `micro-checks.sh` proves a pattern exists, not that it is a
  defect. Ten `<select>` hits are ten places to look, not ten findings.

---

## Anti-inflation rules

A skill that gets re-run until the score is high enough will inflate unless the
scoring resists it. `calibration.md` holds the anchors; these are the
mechanics:

1. **Re-capture evidence every run.** A pillar's grade may not improve on the
   strength of a diff. If it was not re-probed and re-looked-at, it keeps its
   prior grade.
2. **No silent A on eye-only pillars.** `score.py` refuses to derive Hierarchy,
   IA, Content or Consistency from an empty finding list. Passing a letter
   there is a claim that you looked.
3. **Candidates are not findings.** `score.py` shouts when it sees
   `status: "candidate"`. Confirm or reject before quoting the number.
4. **Overrides are printed.** Overriding a derived grade is legitimate and
   loud; an unexplained override is how a scorecard stops measuring anything.
5. **Regressions get reported first.** `--baseline` shouts. Put that at the top
   of the report, not the bottom.
