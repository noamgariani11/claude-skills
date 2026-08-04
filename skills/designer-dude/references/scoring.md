# Scoring reference

Load this for Mode C, Mode D, and Mode F. Three things get graded
independently. None are curved.

1. **Each of 11 pillars** - its own letter grade (A+ to F).
2. **Overall Design Score** - weighted composite → letter + 0–100 number.
3. **AI Slop Score** - standalone letter grade.

Every grade goes on the report. A page can be A on craft, C on content,
F on slop. That is the honest read.

---

## The pipeline: measure, then judge, then grade

Grading a page from a screenshot is guessing, and a guess dressed as a grade
costs the user real work. So the number comes out of a chain where every step
is auditable:

```bash
S=~/.claude/skills/designer-dude/scripts

# 1. MEASURE - facts, not opinions. Writes JSON + screenshots to disk.
#    Get the URL from the browse skill, never by starting a server by hand:
#      BASE=$(~/.claude/skills/browse/serve.sh --dir <project>)   # --prod for perf
#    (write the config first; exact file in mode-d-review.md)
#    browser_run_code_unsafe({ filename: "$S/probe-runner.mjs" })
#
# 1b. EXERCISE - hover, Tab, press, in both themes, on every repeated
#     component. The probe reads the rest state; half of Interaction does not
#     exist in it. Protocol: references/browser-verification.md

# 2. JUDGE the measured layer - thresholds live in source, not in your head
python3 $S/probe-report.py .design/probe-<page>.json \
        --emit-findings .design/findings-<page>.json

# 3. CONFIRM every candidate, reject the false ones, ADD what only your eye
#    sees (hierarchy, voice, IA, taste). Edit findings-<page>.json:
#    set "status": "confirmed" | "rejected", and add your own entries.

# 3b. CROSS-SURFACE consistency - measured, not felt (needs 3+ probed surfaces)
python3 $S/probe-report.py --compare .design/probe-*.json

# 4. GRADE - derived from the confirmed findings
python3 $S/score.py --findings .design/findings-<page>.json \
        --hierarchy B --ia B+ --consistency B --target 90

# supporting tools
bash $S/micro-checks.sh <project-root>              # static/countable claims
python3 $S/contrast.py --css src/app/globals.css    # legibility: every pairing, per theme
python3 $S/contrast.py --harmony --css <same file>  # coherence: do the colours belong together
python3 $S/regress.py --before <old probes> --after <new>   # did anything get worse
node $S/probe-selftest.mjs                          # after ANY probe.js edit (recall)
node $S/probe-selftest.mjs --precision              # correct constructs stay silent
node $S/probe-selftest.mjs --mutations              # isolated defects move; inert churn does not
node $S/probe-selftest.mjs --pipeline               # detector -> report -> severity/WCAG -> score/cap
node $S/probe-selftest.mjs --runner                 # every runner evidence path writes and verifies
python3 $S/validate-rig.py --out .design/validation.json  # one content-addressable gate artifact
```

**Never do the weighted sum by hand, and never retype a number you did not
run.** Eleven letter→number conversions, a weighted sum and four sub-averages
is precisely the arithmetic that goes quietly wrong, and a scorecard with bad
maths is worse than none: it launders a guess as a measurement.

`score.py --selftest` verifies the grade tables and the demotion maths.
Confirmed WCAG findings in the ledger derive the C+ cap automatically;
`--wcag-fail` remains available for failures established outside the ledger.

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
**`"deferred"` still counts** - a defect nobody can fix from here is still a
defect the user is shipping.

### The findings ceiling is 92, and credits are the only way past it

Demotion-only scoring has a hard consequence worth stating plainly: **fixing
every defect on every pillar produces a straight-A card, which scores exactly
92.00.** So the top eight points of the scale were unreachable by construction.
Two things went wrong because of that:

- A product that genuinely earned more - a bespoke type system, a voice, a
  motion moment someone remembers - had no way to be told apart from one that
  merely had no open findings.
- "Get this to 95" was a target no amount of work could satisfy, which is only
  discoverable by grinding rounds until the script says *nothing left to move*.

The fix is **not** to award A+ when a gap needs closing - that is grading your
own homework, and `--target` still refuses to schedule an A+. The fix is to
make A+ falsifiable. A pillar reaches A+ by carrying a **credit**:

```json
{ "id": "CREDIT-001", "pillar": "typography", "kind": "credit",
  "criterion": "typography.voice-and-ratio",
  "evidence": "credit-typography.json",
  "surfaces": ["dashboard", "properties", "landing"],
  "status": "verified" }
```

The evidence path resolves beside the findings ledger and contains a current,
reviewed wrapper rather than prose embedded in the path:

```json
{
  "schema": "designer-dude-credit-evidence/v1",
  "status": "pass",
  "pillar": "typography",
  "criterion": "typography.voice-and-ratio",
  "reviewer": "accountable reviewer or team",
  "reviewedAt": "2026-08-03T12:00:00Z",
  "surfaces": ["dashboard", "properties", "landing"],
  "observations": ["Eight named steps follow a 1.25 ratio without near-duplicates."],
  "artifacts": [
    {"path": "probe-dashboard.json", "sha256": "<64 lowercase hex>"}
  ]
}
```

`score.py` opens this JSON and every nested artifact, rejects paths outside the
ledger bundle, recomputes the hashes, and verifies the pillar, exact criterion,
surfaces, reviewer, observations, and 90-day review date. A string that merely
says “measured” no longer creates A+.

`score.py` counts it only if **all** of these hold, and prints the reason when
it does not:

| Gate | Why |
|---|---|
| `criterion` is that pillar's exact A+ criterion id | A credit names the bar it cleared. Another pillar's id does not count. |
| `evidence` is a valid reviewed wrapper whose nested bytes match | A claim without current, reproducible evidence is a guess. |
| `surfaces` names ≥2 **distinct** probed surfaces | Excellence shown on one page scores the page, not the product; repeating its label does not manufacture breadth. |
| `status` is exactly `verified` | At the only altitude that can create a perfect score, candidate or merely confirmed evidence is still an opinion. |
| the pillar has **zero** unresolved findings | A credit records that a defect-free pillar went further. It never buys points back from a defect. |

`--target` above 92 prints exactly how many credits the number needs, heaviest
pillar first, and says what claiming them would mean. Four or more credits on
one card triggers a warning: A+ is *rare*, and a card mostly made of it has
stopped measuring.

**100 is a certification gate.** It is available only in findings mode, with
all eleven pillars clean, all eleven credits explicitly `verified`, two or more
distinct surfaces on every credit, and an AI-slop grade of A embedded by
`probe-report.py --emit-findings` in the findings ledger. A conflicting
`--slop` argument cannot override that measured result. Manual
letter mode tops out at 99 even if every supplied letter is A+: it has no
findings ledger capable of proving perfection. Even those machine gates are
not enough: the same ledger must carry a current, attributable human review of
the product as a whole. Without it, the arithmetic can reach 100 but the
published result is capped at 99.

```json
{
  "perfectionCertification": {
    "status": "verified",
    "reviewer": "name or accountable team",
    "reviewedAt": "2026-08-03T12:00:00Z",
    "surfaces": ["dashboard", "record detail", "settings"],
    "viewports": ["320x568", "768x1024", "1440x900"],
    "states": ["hover", "focus-visible", "active", "disabled", "loading", "empty", "error"],
    "evidence": ["dashboard.png", "detail.png", "settings.png"],
    "ariaSnapshotEvidence": ["dashboard.aria.yml", "detail.aria.yml", "settings.aria.yml"],
    "completeProcesses": [
      {"name": "approve invoice", "status": "verified",
       "steps": ["open record", "approve", "see confirmation"],
       "evidence": "approve-process.md"}
    ],
    "keyboardReview": {"status": "verified", "evidence": "keyboard-pass.md"},
    "assistiveTechReview": {"status": "verified", "evidence": "at-evidence.json"},
    "validationEvidence": {
      "status": "verified", "recall": "68/68", "precision": "52/52",
      "mutations": "18/18", "pipeline": "16/16", "evidence": "validation.json"
    },
    "behavioralReview": {
      "status": "verified", "evidence": "behavior.json",
      "focusSweep": {"status": "verified"},
      "accessibleNames": {"status": "verified"},
      "labelInName": {"status": "verified"},
      "statusAnnouncements": {"status": "verified"},
      "widgetContracts": {"status": "not-applicable", "reason": "native controls only"},
      "accessibleAuthentication": {"status": "not-applicable", "reason": "no authentication surface"},
      "dragAlternatives": {"status": "not-applicable", "reason": "no dragging interactions"},
      "redundantEntry": {"status": "not-applicable", "reason": "no repeated multi-step inputs"}
    },
    "internationalizationReview": {
      "status": "verified", "evidence": "i18n.json",
      "textExpansion": {"status": "verified"},
      "rtl": {"status": "not-applicable", "reason": "English-only declared scope"},
      "localeProfiles": {"status": "verified"}
    },
    "representativeSampling": {"status": "verified", "evidence": "sampling-evidence.json"},
    "usabilityReview": {"status": "verified", "evidence": "usability-evidence.json"},
    "performanceReview": {"status": "verified", "evidence": "performance-evidence.json"},
    "methodValidation": {
      "status": "verified",
      "detectorBenchmark": {"status": "verified", "evidence": "detector-benchmark.json"},
      "actBenchmark": {"status": "verified", "evidence": "act-benchmark.json"},
      "expertCorrelation": {"status": "verified", "evidence": "expert-correlation.json"}
    },
    "calibrationSnapshot": {"status": "verified", "evidence": "calibration-verification.json"},
    "crossEngineReview": {
      "status": "verified", "engines": ["chromium", "firefox", "webkit"],
      "evidence": "cross-engine.json"
    },
    "artifactRegression": {
      "status": "verified", "evidence": "artifact-regression.json",
      "visual": {"status": "verified"}, "aria": {"status": "verified"}
    },
    "artifactManifest": [
      {"path": "dashboard.png", "sha256": "<64 lowercase hex characters>"},
      {"path": "dashboard.aria.yml", "sha256": "<64 lowercase hex characters>"},
      {"path": "approve-process.md", "sha256": "<64 lowercase hex characters>"}
    ]
  }
}
```

The certification needs three distinct surfaces, three viewport captures
spanning ≤390px through ≥1280px, every designed state, three distinct visual
artifacts, three browser-computed accessibility-tree artifacts, at least one
verified complete process with two or more steps, and explicit keyboard and
assistive-technology evidence. It expires with the skill's dated-claim window.
`artifactManifest` must contain **every** referenced evidence file, not only the
three abbreviated examples above. `score.py` resolves relative paths from the
findings ledger, verifies every file exists, and recomputes every SHA-256; a
missing, replaced, or unhashed artifact prevents 100.
It also needs complete non-zero recall, precision, mutation, and full-pipeline
ratios; verified focus and browser-computed Label in Name review; configured
announcement/widget/authentication/drag/redundant-entry evidence (or a reasoned
`not-applicable`); text expansion, applicable RTL, and complete reviewed-locale
fixtures; target-engine coverage; stable visual plus ARIA regression evidence;
a passing held-out detector benchmark; reliable independent expert ratings
whose ordering correlates with the score; a WCAG-EM-shaped representative
sample; passing real-user tasks; versioned real-AT observations; and a current
production field Core Web Vitals at good p75 thresholds; and a current
content-addressed calibration snapshot. Every new evidence path belongs in
`artifactManifest`, including nested detector cases, rated-product captures,
sampling captures, task protocols, AT transcripts, and the calibration
snapshot manifest itself; `score.py` opens and rehashes them. Read
`behavioral-verification.md` for the config and the
strict boundary between deterministic findings, configured behavior, and
advisory simulations. Read `evidence-validation.md` for the external schemas;
none of those gates may be satisfied with generated reviewers or participants.
This does not make subjective judgment objective; it prevents the scorer from
silently pretending no judgment was needed. The representative-surface and
complete-process requirements follow [WCAG-EM 2.0](https://www.w3.org/TR/wcag-em-2/)'s
evaluation scope; they are not a claim that three pages alone establish WCAG
conformance. The `.aria.yml` artifacts use Playwright's
[browser-computed ARIA snapshots](https://playwright.dev/docs/aria-snapshots),
which expose roles, names, hierarchy and states that screenshots cannot.

### Let the measurements falsify a credit before you write it

Every gate above is procedural - names a criterion, has evidence, cites two
surfaces, sits on a clean pillar. None of them is a *measurement*, which left
the scale unmeasured at exactly the altitude where the pressure to be generous
is highest. So run the falsifier first:

```bash
python3 probe-report.py --credits .design/probe-*.json --emit-credits .design/credits.json
```

Several clauses of each criterion are measurable - the primary face, near-
duplicate steps, off-base spacing, accent share, overflow at 320, radius and
shadow counts, whether reduced-motion is honoured, whether the perf number came
from a production build. It reports:

| Verdict | Means |
|---|---|
| **BLOCKED** | a measured clause fails. The credit is not available, however good the argument is. Fix the clause. |
| **OPEN** | the machine clauses hold. This is **not** a credit - the `??` clauses are still yours to argue. |
| **HUMAN** | Hierarchy, Content and IA have no measurable clauses at all. Argue it or drop it. |

It can only ever block. The stubs it writes carry `status: "candidate"`, which
`score.py` does not count, so nothing here can raise a score on its own.

### The A+ criteria (one per pillar, each a conjunction)

These live in `score.py` (`A_PLUS_CRITERIA`) so they are executable rather than
remembered. Every clause must hold - a menu of alternatives is a menu of the
easiest one. `probe-report.py --credits` asserts its own copy of the criterion
ids against that table and refuses to run on drift.

| Pillar | Criterion id | A+ means |
|---|---|---|
| Typography | `typography.voice-and-ratio` | A face chosen and self-hosted for its voice (never Inter/Roboto/Arial/system-as-default), the scale on ONE ratio with no near-duplicate steps, tabular numerals everywhere numbers align. |
| Visual Hierarchy | `hierarchy.singular-primary` | One primary action per surface, argued against what users come to that surface to do - not merely tidy. Same first stop at every probed viewport, and the second and third stops are also intended. |
| Spacing & Layout | `spacing.composed-grid` | A grid that is felt, not just obeyed: one base unit, 6–8 named steps, zero off-base values, rhythm that survives a long page and a dense table on the same screen. |
| Color & Contrast | `color.designed-dark-and-range` | Semantic roles in oklch, a dark theme designed rather than inverted **and reachable from the page without an OS setting** (switch resolved before first paint, choice remembered, `color-scheme` per theme), accent under 10% of pixels, no state carried by colour alone, AAA body text where the palette allows. |
| Interaction & Perf | `interaction.states-and-vitals` | All seven states designed, configured status actions and custom widgets pass behavioral contracts, **and** Core Web Vitals are inside budget on a production build. Observation is not a measurement. |
| Content & Voice | `content.voice-with-a-point-of-view` | Copy that could only belong to this product: the user's domain nouns, empty states that name the next action, errors that name the field and the fix, a voice recognisable unlabelled. |
| Accessibility | `a11y.beyond-aa` | Zero AA failures, browser-confirmed Label in Name, no completely obscured focus, a clean manual keyboard pass including focus return, the 2.2 SCs most sites miss, and at least one thing done for assistive tech that no checker asked for. |
| Responsiveness | `responsive.designed-breakpoints` | Each breakpoint is a decision with its own reason, tables have a real small-screen answer, 320px is as considered as 1440px, and applicable text-expansion/RTL stress adds no clipping or overflow. |
| Craft | `craft.decided-details` | Every detail visibly answered a question: disciplined radius/shadow scales, one light source, deterministic tie-breaks, aligned decimals, clean console, correct-DPR assets, stable visual/ARIA baselines, no critical target-engine regression. |
| Information Architecture | `ia.predictable-object-model` | A user can predict where a record lives before navigating there. Labels are the user's words, deep links survive a refresh, depth beyond two levels is served by search. |
| Motion | `motion.signature-moment` | Motion carries continuity or feedback throughout, honours `prefers-reduced-motion` completely, and the product has one moment someone would remember - without animating a 200-row list. |

If you cannot point at the evidence for every clause, the pillar is an A. That
is not a failure; **A is the grade for excellent work with nothing wrong with
it.** A+ is for work that went further than that, and it should stay rare.

### Performance is half of Interaction, and it is usually ungraded

`interaction.states-and-vitals` cannot be claimed from watching the page feel
smooth. If Core Web Vitals were not measured on a **production** build, pass
`--perf-unmeasured`: the pillar is capped at A− and the report says so. Dev
server numbers are not evidence, and a pillar graded on half its definition
should not read A. `mode-d-review.md` has the recipe for getting a production
build up when the obvious command refuses.

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
| Interaction & Performance | probe focus/cursor/target pass, state-rule coverage, lab perf |
| Content & Voice | you read the copy on the page |
| Accessibility | probe a11y pass **plus** a manual keyboard pass |
| Responsiveness | probe at 320 / 768 / 1440 minimum, **with touch emulation on the narrow passes** and one short/landscape pass. A `[NO-EMU]` row or a missing sub-430px pass caps this pillar at provisional. |
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
  hierarchy failed - dock points even if everything is pretty.
- **What causes friction - a pause, a squint, a scroll-back?** Friction is
  the signal. The Aesthetic-Usability Effect cuts both ways: it buys
  goodwill but does not excuse broken mapping.
- **Would the eye feel tired after 30 seconds?** Visual noise, competing
  accents, and unresolved tension all drain it.
- **Does this look decided, or assembled?** Assembled is a slop tell.

A pillar earns an A only if the eye flows through it without effort.

**Bands:** **A+** considered and delightful, rare - and only via a credit
against the pillar's criterion (above) · **A** strong, one nit at
most · **A−** strong with a rough edge · **B+/B/B−** solid, real issues ·
**C+/C/C−** functional, generic, or sloppy · **D** the eye is working against
it · **F** actively hurts the product.

**Never award a grade without naming element + rule + fix.**

---

## The 11 pillars

Weights sum to 100. Accessibility carries 8 and additionally triggers the hard
cap below. The **App column** is what an A means on a dense product surface
rather than a marketing page - load `enterprise.md` when the target is a real
application.

| # | Pillar | W | What an A looks like | On an app surface |
|---|---|:-:|---|---|
| 1 | **Typography** | 15 | Type scale on a ratio (1.2 / 1.25 / 1.333). Measure 45–75ch. Leading 1.4–1.6 body / 1.1–1.25 display. Pairing has real contrast (weight + category). Real quotes and apostrophes. No Inter/Roboto/Arial/Poppins as the voice. No orphans in headlines. | Tabular numerals in every numeric column. A dense size (12–13px) used deliberately, not accidentally. Label distinguishable from value without colour. |
| 2 | **Visual Hierarchy** | 15 | One primary action per screen (Von Restorff). Eye finds it in <1s. Weight and color carry hierarchy, not size alone. F/Z/center-stage scan matches content intent. | The row you must act on is findable in a 200-row table. Toolbar action, page action and row action are three distinguishable things. |
| 3 | **Spacing & Layout** | 12 | Grid is felt. Spacing on a 4/8 base. Related elements clustered (Gestalt proximity), unrelated separated. Sections breathe. Nothing floats, nothing crams. | Density is a decision: 40–56px rows, not 72px of air. Form groups read as groups. No 1440px-wide single-column form. |
| 4 | **Color & Contrast** | 10 | Semantic roles (surface/text/accent/semantic), not color-named tokens. oklch-coherent; Display P3 where supported. WCAG AA minimum, AAA on body where achievable. No pure `#000`/`#FFF`. Accent ≤10% of pixels. Dark mode designed, not inverted. | Status colour is never the only signal. Semantic states legible at 12px. Selected-row tint distinguishable from hover tint. |
| 5 | **Interaction & Performance** | 10 | Hover / focus-visible / active / disabled / loading / empty / error all designed, and **hover verified by hovering** - a rule that paints the colour already behind it is not a state (`inertHoverFills`), and a full-width row whose fill has no inline padding stops at the glyph (`hoverFillsWithoutPadding`). Focus ring never removed without replacement. Targets ≥44px (Fitts; WCAG 2.5.8 requires ≥24px). Perceived feedback <100ms. **Perf is UX: LCP ≤2.5s, INP ≤200ms, CLS <0.1** at p75 CrUX. Unreserved image dimensions and long main-thread work are design failures. Clickable elements show `cursor: pointer`. | Pending state on every mutation. Bulk actions report partial failure per item. Destructive actions are undoable or confirmed, never both silent and instant. |
| 6 | **Content & Voice** | 10 | Copy earns its space. Specific verbs, specific nouns. No "Welcome to", "Unlock the power of", "Your all-in-one". Microcopy matches brand voice. Labels precede inputs. Error copy helps rather than scolds. No AI self-reference emoji. | Domain vocabulary is the user's, not the schema's. Empty states say what to do next. Errors name the field and the fix. |
| 7 | **Accessibility** | 8 | WCAG 2.2 AA. Keyboard-reachable. Landmarks, labels, alt text, heading order. Color never the only signal. Motion-reduce works. Form errors announced. Hits the 2.2 SCs most sites miss: 2.4.11 focus not obscured, 2.5.7 dragging alternative, 2.5.8 target size 24×24, 3.3.7 redundant entry, 3.3.8 accessible authentication. | Ambiguous/complex tables explicitly associate headers (`scope` or `headers`/`id`); small one-direction tables may use `<th>` alone. Sortable headers expose `aria-sort`. Modals trap focus and restore it. Live regions announce async results. |
| 8 | **Responsiveness** | 7 | Intentional at 320 / 768 / 1024 / 1440 / 1920, **and in landscape**. Type scale adapts. Touch targets reflow. Nothing unintentionally horizontal-scrolls. Breakpoints are design decisions, not media queries. **Nothing is hover-only** - every reveal has a tap or focus path (2.1.1). Fixed chrome does not eat a short viewport, and a `viewport-fit=cover` page pads for the notch. | Tables have a real small-screen answer (card view, priority columns, or a scroll region with a pinned first column) rather than a squeeze. |
| 9 | **Craft & Considered Details** | 5 | Icon strokes consistent. Radius scale disciplined. Shadows coherent (single light source). No 1px misalignment. Assets at correct DPR. Favicon exists. Console clean. Every detail visibly answered a question - **decided, not assembled**. | Numbers align on the decimal. Dates in one format. Sort order is deterministic on ties. |
| 10 | **Information Architecture** | 4 | The user's mental model matches the UI (Norman). Nav reflects the job, not the org chart. Labels use user language, not internal jargon. Search exists where depth >2 levels. | The object model is visible: a user can predict where a record lives. Deep links survive a refresh. |
| 11 | **Motion** | 4 | Motion earns its place (continuity / feedback / delight - one at a time). 150–300ms UI, 400–600ms transitions. Ease-out on enter, ease-in on exit. `prefers-reduced-motion` honored. | Nothing animates in a list of 200 rows. Skeletons match the shape of what arrives. |

### The accessibility hard cap

**Any unresolved WCAG 2.2 AA failure caps the Overall score at C+**, no matter
how the weighted sum lands. Pass `--wcag-fail`.

A product that looks immaculate and locks out keyboard users has not earned a
B. The weight alone could not express that, because weighting is linear and
exclusion is not. State the cap explicitly and name the failure that triggered
it.

Do not apply the cap for: WCAG AAA misses, WCAG 3 draft requirements, APCA Lc
values, or **4.1.1 Parsing, which is obsolete** - never dock for it.

---

## Composite sub-scores

- **Overall** - weighted 0–100 across the 11 pillars.
- **Craft** - mean of Typography, Spacing, Color, Motion, Craft & Details.
- **Clarity** - mean of Hierarchy, Interaction & Performance, IA, A11y.
- **Brand Coherence** - mean of Content/Voice and a **cross-page consistency
  check** (do 3+ pages look like one product - same type hierarchy, same radius
  scale, same accent usage?). Pass it as `--consistency`. It deliberately does
  not reuse Typography; that is already inside Craft.

  `probe-report.py --compare <probe json...>` measures the mechanical half:
  whether the primary type face, radius scale, type scale and spacing scale are
  shared across surfaces, which surfaces use a token nothing else uses, and how
  far accent share varies. It prints a **suggested** letter. Treat it as
  suggested: matching tokens are necessary for a product to look like itself,
  not sufficient. Calibration: three pages of one design system score B, three
  different companies score F.
- **Slop** - the standalone A–F grade below.

### Grade values and bands

The script owns these. They are **round-trip stable**: every letter's numeric
value maps back to the same letter.

**A+ is 100, so the scale actually ends where it says it does.** An all-A+ card
scores exactly 100.00, and reaching it costs an evidence-backed credit on all
eleven pillars, an embedded measured AI-slop grade of A or better, and the
hash-verified human certification above. Weak or absent measured slop caps at
97.00; absent certification caps otherwise-perfect arithmetic at 99. A CLI
`--slop` cannot replace the embedded measurement. These gates are deliberate:
credits are argued, the slop grade is computed, and the remaining human claim
is attributable with immutable evidence.

| Letter | Value | Band |
|---|:---:|:---:|
| A+ | 100 | 95–100 |
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
unreachable without real A grades on the heavy pillars** - Typography and
Hierarchy carry 30 points between them. Say that out loud before starting a
campaign; see `mode-f-campaign.md`.

---

## AI Slop Score (A–F) - standalone, weighted

`probe-report.py` computes the measurable part and prints the grade plus the
tells that fired. Start at A. Hits are weighted by severity. **Three
full-letter hits = D. Five = F.**

**Contrastive corpus check - do this before finalizing the grade.** The list
below names what slop *is*. The corpus (see `canon.md`) shows what shipped
systems actually do. Spot-check the target's palette, type, and hero against
2–3 corpus files. If it clusters with the slop tells and away from every real
system, say so with the contrast: *"No system in the corpus uses a blue→purple
hero gradient; this leans on it."* A positive reference lands harder than the
rule alone.

### Brand killers - drop a full letter each

1. **Purple / violet / indigo gradient**, especially blue→purple. The single
   strongest "ChatGPT wrapper" tell. *(measured: `slop.purpleOrIndigoGradients`)*
2. **Gradient-mesh orb hero.** Also animated beams, sparkle trails, glow auras
   behind buttons. *(measured: `largeRadialGradients`)*
3. **Three-column feature grid** - icon-in-colored-circle, bold title,
   two-line description, perfectly symmetrical. *(measured: `threeUpFeatureGrids`)*
4. **Bento-grid hero** paired with "Build the future" / "The future of X" /
   "The platform for Y".
5. **Default shadcn grays + unmodified Lucide icons + uniform `rounded-xl`.**
   A theme is not a design. *(partly measured: `system.radius.distinct == 1`)*
6. **Inter or Poppins as the body voice.** Inter is a fine fallback, never a
   face. *(measured: the most-used rendered family)*
7. **Centered-everything.** The tell is *undecided* alignment, not symmetry:
   long-form copy, forms, lists and dense app surfaces centred because centring
   is the default that requires no thought. A centred hero, empty state, auth
   card, 404 or section header is **correct design and gets no finding**.
   `centredShare` counts blocks over 40 characters for exactly this reason.
   **Read `alignment.md` before writing this one up** - it is the entry this
   list gets wrong most often, and telling a user to left-align a hero that is
   working costs them real work. *(measured: `centredShare`)*
8. **Glassmorphism on every card.** *(measured: `backdropBlurElements`)*

### Hits - drop half a letter each

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

### Nits - drop a quarter letter each

17. **Fake marquee logo strip** ("As seen in…" with identical gray logos). *(measured)*
18. **"Powered by GPT-4" / "Built with Claude" badges.** *(measured)*
19. **Stock "diverse team" hero photo** with the laptop and the coffee.
20. **Fake dashboard screenshots** with meaningless sparklines.
21. **Identical 3-testimonial carousel** with placeholder-looking avatars.

### The copy tells

Slop is not only visual. Text gives it away faster than layout does, and these
are measured against the target's own rendered copy. Full list and the
rewrite rules in `voice.md`.

22. **The LLM sentence frames** - "not just X, but Y", "it's not about X, it's
    about Y", "isn't just a tool", "in today's fast-paced world", "whether
    you're a A or a B". Half a letter for one, a full letter for two or more.
    *(measured: `llmSentenceFrames`)*
23. **Decorative zero-padded step numbers** - `01` `02` `03` as section
    ornament above the heading that already says it. Half a letter. Numbered
    steps in a real sequence are fine, and should be `1. 2. 3.`
    *(measured: `decorativeStepNumbers`, gated to patterned repeats so a lone
    `01` of data never fires)*

    Two aggravating cases, both of which this skill has itself shipped and
    then had to be told about:

    - **An ordinal on an unordered set is a full letter, not half.** Numbering
      six services `01`–`06` asserts a sequence that does not exist: weekly
      service is not step one of anything, and nothing happens in that order.
      A number that carries no information is ornament; a number that carries
      *wrong* information is worse than ornament.
    - **Zero-padding a set that cannot reach ten is the tell inside the tell.**
      `01 02 03` over three steps borrows the formatting of a longer list to
      look considered. If the numbers earn their place, they are `1 2 3`.

    When you are the one AUTHORING the layout, this is the rule: a numeral goes
    in only if a reader who ignores it would get the content wrong.
24. **Em dashes at a rate no writer sustains** - half a letter above 3 per
    1,000 characters. This is a **rate, not a count**: one em dash is a writer,
    and docking a page for it is how a slop detector gets muted.
    *(measured: `emDashesPer1kChars`)*

**Font blacklist:** Papyrus, Comic Sans, Lobster, Bradley Hand.
**Never-as-primary:** Inter, Roboto, Arial, default Helvetica, Poppins,
Montserrat, personality-free system-ui. Fine as fallbacks, never as the face.

---

## Taste claims vs. rules - know which you are wielding

Some entries above are defensible on evidence (contrast ratios, target sizes,
measure). Others are **period taste** - true of 2026, and dated eventually.
Slop items 1–8 in particular are fashion calls, correct now because the
pattern signals low effort *today*. `probe-report.py` tags every candidate
`rule` or `taste call` for exactly this reason.

When a user pushes back on a taste call with an actual argument - their
audience expects the convention, the pattern tests well, the brand predates
the trend - **update**. Do not defend a fashion call as though it were a
contrast ratio:

> That is a taste call, not an accessibility one. The gradient is not broken;
> it reads as generic to anyone who has seen ten AI landing pages this year.
> If your buyers have not, it costs you less than it costs you with investors.

The three things that are never taste calls: **WCAG failures, contrast math,
and performance budgets.** Hold the line on those.

---

## Things this rubric does NOT dock for

Guard-rails against confident wrongness. Each of these has been mistaken for a
defect - several by this skill's own tooling before it was fixed.

- **A native `<select>`.** Often the better choice - superior mobile and
  screen-reader behavior. Flag only when it genuinely clashes with a
  heavily-styled form, or when the design needs option content a `<select>`
  cannot render. A broken *custom* dropdown is the real finding.
  **The line:** choosing native is not a defect; leaving it *unrelated to the
  form around it* is. It still owes the shared field height, radius, font and
  3:1 border, the same focus ring, and - if `appearance: none` removed the
  native arrow - a replacement chevron with enough right padding that a long
  option never runs under it. `components.md` section 4.
  *(measured: `chrome.unstyledStrippedSelects` fires only on the stripped case)*
- **Unstyled scrollbars.** A preference, not a defect. Custom scrollbars
  frequently reduce hit-area and affordance. Raise as optional polish; never
  dock a full grade. If styled: thumb ≥8px, ≥3:1 against its track.
  **Three things in this area ARE defects**, and they are what users notice:
  a **hidden** scrollbar on a region that must be scrolled
  (`scrollbar-width: none` removes the only affordance saying more exists), a
  **light OS scrollbar in a dark theme** (an undeclared `color-scheme`, which
  also leaves the `<select>` popup, autofill and the caret in the light theme),
  and layout shift when the scrollbar appears (`scrollbar-gutter: stable`).
  *(measured: `chrome.hiddenScrollbars`, `chrome.darkSurfaceWithoutColorScheme`)*
- **A `title` attribute that is correct markup.** On an `<iframe>`, duplicating
  an element's own visible text, or — the big one — paired with `truncate` to
  expose a value the layout had to cut. That last pattern is conventional,
  expected, and typically two thirds of every `title` in a real codebase. The
  finding is the **rendered black OS box carrying information nothing else
  carries**: slow, unstyled, invisible on touch, unreachable by keyboard. Judge
  what the user sees, not the attribute.
- **A centred hero, empty state, auth card, 404, or section header.** Centring
  is correct for a short self-contained block that is a destination. The slop
  tell is *undecided* alignment — centred long-form copy, forms, and lists. See
  `alignment.md`; this is the entry most often applied wrongly, and telling a
  user to left-align a working hero costs them real work.
- **`№` and other typographic marks.** House style, not a defect, and not
  evidence of AI authorship.
- **System fonts on a deliberately utilitarian product.** Internal tools and
  dashboards can correctly choose boring.
- **WCAG 4.1.1 Parsing.** Obsolete.
- **Sparse copy.** Restraint is not laziness.
- **An absent dark mode.** Only a finding if the product promises one or the
  audience expects one — `color.md` section 5a lists the triggers, and says to
  build one rather than only report it when a trigger fires. **A dark theme
  that exists but cannot be switched to from the page is a different matter and
  IS a finding** (major, Colour): OS-only access strands the visitor who wants
  the other theme right now, and stranding them is not a preference call.
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
6. **A credit is evidence, not enthusiasm.** It names a criterion, carries
   evidence, cites 2+ surfaces, and sits on a pillar with nothing open. Writing
   one to close a gap in a target is the single fastest way to turn this
   scorecard into a mirror - and the ledger will show you did it, because the
   credit is a row in the findings file forever. Run `--credits` first: a
   BLOCKED pillar settles the question before the argument starts.
7. **Every rejection becomes a precision case.** `fixture-case.py
   --from-findings` lists the rejections that do not have one yet. A threshold
   that fires on correct code costs more than one that misses, and a rejection
   that lives only in prose gets re-argued next campaign.
8. **All eleven pillars grade form.** None of them asks whether the design
   serves the task. Once a surface grades A, put it in front of `user-test`
   (mode-d-review.md §4b) and turn a failed task into a `critical` finding.
   This is the only route by which the number goes down on evidence the probe
   cannot produce, and it is what stops a high score on a product nobody can
   use.
7. **Never award a credit and a fix in the same breath.** If a round fixed the
   pillar's last defect, the credit belongs to the *next* round, after a fresh
   probe confirms the fix held.
8. **Report the verdict beside the number.** Every scorecard ends with one
   plain-language line: would you ship this, and would you show it to another
   designer? If that line and the number disagree, the line is the finding -
   say so, and name what the rubric missed.
