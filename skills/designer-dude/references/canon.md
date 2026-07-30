# Canon, benchmarks, and the reference corpus

Load when you need to justify a call, name the bar, or cite a real system.
Cite to help the user trust the call. Do not name-drop gratuitously — one
well-placed citation beats five.

---

## Currency layer — re-verify before you assert

**Last verified: 2026-07-30.**

Design taste and web standards both rot. Every dated claim in this skill
carries an expiry. **If today is more than ~6 months past the date above,
spot-check the time-sensitive claims with WebSearch before asserting them**
— especially the trend calls, which age fastest. `score.py` reads this date and
warns when it is more than 200 days old, so the staleness surfaces itself
instead of waiting to be noticed.

Claims that are load-bearing and dated:

| Claim | Status at last verify |
|---|---|
| WCAG 2.2 is the AA baseline | Current. W3C Recommendation, Oct 2023. |
| WCAG 4.1.1 Parsing is obsolete | Current. Never dock for it. |
| INP replaced FID as a Core Web Vital | Current since March 2024. |
| CWV thresholds: LCP ≤2.5s, INP ≤200ms, CLS <0.1 at p75 | Current. Re-verified against web.dev 2026-07-30, unchanged, no pending successor metric. |
| APCA status | **Draft, not a standard.** Under consideration for WCAG 3, not in the current WCAG 3 draft, and **not backward compatible** with WCAG 2 numbers. `probe.js` and `contrast.py` report Lc as advisory only. Never cite it as conformance; never drop WCAG 2 conformance for it. |
| WCAG 3 status | March 2026 Working Draft. What earlier drafts called **"outcomes" are now "requirements"** — 174 of them. Candidate Recommendation anticipated Q4 2027; Recommendation likely 2028–2030. **Not legally required. Cite as forward-looking only.** |
| Bento grids, gradient-mesh heroes, glassmorphism read as dated | Taste call, true as of mid-2026. Most likely entry on this page to expire. |
| claude.ai palette/type values below | Verified 2026-07-19, but a product can redesign at any time. Re-check before quoting exact hexes at someone. |
| Tailwind is on v4 (CSS-first `@theme`, no `tailwind.config.js`) | Verified 2026-07-30. Latest 4.3.3; v4.3 shipped 2026-05-08. **Version-check the project itself before writing any Tailwind fix** — v3 syntax fails silently on v4. `references/tailwind-v4.md` §1. |

| The measured anchors in `calibration.md` | Measured 2026-07-30 with this skill's own probe. Any of those products can redesign; re-measure before citing a number at someone. |

### Claims that failed verification — do not repeat these

Kept deliberately, because a plausible-sounding wrong fact does more damage
than a gap, and these come up:

- **"Core Web Vitals 2.0", or a new "Visual Stability Index (VSI)" replacing or
  supplementing CLS.** Widely repeated across SEO content sites in 2026.
  **Not corroborated by web.dev**, which documents three stable metrics and no
  pending successor. Do not cite it; if someone else does, this is the answer.
- **A firm WCAG 3 date.** Every confident timeline found for it disagrees with
  the others. The working group has not committed to one. Say "years out" and
  stop.

When a trend claim has expired and you have not re-verified it, say so
rather than asserting: *"This read as dated a year ago; I have not
re-checked whether it still does."* Never invent a currency date.

---

## Reference benchmarks (what "good" looks like in 2026)

- **claude.ai** — the current reference for AI-product craft.
  - Background: **warm cream `#faf9f5`** (olive undertone, never `#ffffff`).
  - Warm neutrals: `#141413` near-black, `#30302e`, `#5e5d59`, `#87867f`,
    `#b0aea5`, `#e8e6dc`, `#f0eee6`.
  - Accent: **terracotta `#d97757`** — a single accent, not a gradient.
  - Secondary cycle: blue `#6a9bcc` · green `#788c5d`. Rotated across
    surfaces, never layered into a rainbow.
  - Type: **Copernicus Book** (display serif) + **Styrene B** (UI sans,
    quirky extended f/j/r/t) + **Tiempos Text** (editorial body).
  - Voice: lowers AI's status rather than hyping it. Complete sentences,
    periods, no exclamation marks, no rocket emoji, no "✨ AI-powered ✨".
  - Motion: streaming text is the only animation that matters. No parallax,
    no confetti, no bounces.
  - Layout: article-like. Reading column ~65–75ch. Artifact side-panel.
- **Stripe Press** — Ivar (Klim) for editorial gravitas; Söhne on product.
  Long-form typography done right.
- **Linear** — Söhne sans, deliberate craft. Saarinen: *"Design is a
  reference, never a deliverable."*
- **Vercel** — Geist (sans + mono). Design-engineering culture, small
  iterative PRs.
- **Arc Browser** — custom editorial serif display + humanist sans.
  Personality without slop.

What they share, and what this skill scores toward: warm neutrals over
cool, editorial display type over geometric sans, single-accent discipline
over rainbow gradients, restrained motion, microcopy that reads like a
human wrote it.

**Benchmark against these — not dribbble shots or competitor SaaS.**

### App-surface benchmarks (different question, different bar)

The list above is mostly marketing craft. When the target is an application,
benchmark the things an application is judged on — density, keyboard, state
handling — against **Linear** (dense lists, command palette, instant feel),
**the Stripe dashboard** (tables and financial data done properly: tabular
numerals, right-aligned currency, real empty and partial-failure states),
**Figma** (modeless direct manipulation), and **Height / Notion** (density
that still reads as calm). See `enterprise.md`.

A product can be A-grade as an app and B-grade as a marketing site, or the
reverse. Grade the surface you are actually looking at, and say which.

---

## The reference corpus (real DESIGN.md files on disk)

74 fully-analyzed DESIGN.md files (500–800 lines each: real hex palettes,
type scales, spacing, radius, component specs) extracted from shipped
products — Claude, Stripe, Linear, Notion, Vercel, Apple, Figma, Cursor,
Coinbase, ElevenLabs, BMW, Ferrari and more. This is the
`awesome-design-md` collection, following the Google Stitch DESIGN.md
convention.

**Prefer citing a real file over citing prose.**

Known location on this machine:

```bash
CORPUS=/home/drago/awesome-design-md/design-md
# Fallback if it has moved:
[ -d "$CORPUS" ] || CORPUS=$(find ~ -maxdepth 5 -type d -name design-md \
  -path '*awesome-design-md*' 2>/dev/null | head -1)
[ -n "$CORPUS" ] && ls "$CORPUS"
```

If it is not there, fall back to the prose benchmarks above and **say so**.
Never invent file paths or token values.

How each mode uses it:

- **Scoring (Modes C/D):** when you dock a pillar, contrast against a real
  exemplar. *"Your accent covers ~25% of the hero; Claude's terracotta on
  its `#faf9f5` canvas (`$CORPUS/claude/DESIGN.md`) holds accent under
  10%."* A finding backed by a real token is harder to argue with than
  "feels too loud."
- **Slop detection:** the slop list says what is bad; the corpus shows what
  good clusters look like. *"None of the 74 reference systems use a
  blue→purple hero gradient; your palette clusters with generic SaaS,
  not with any shipped system."*
- **Mode A authoring:** if a user names an admired reference that exists in
  the corpus (`ls "$CORPUS"`), **load that file as a structural template**
  — match its section order, token granularity, and `{alias}` references.
  Adapt values to the user's brand. Never copy a competitor's palette
  wholesale.

---

## The canon

- **Don Norman — *The Design of Everyday Things*.** Affordances,
  signifiers, feedback, mapping, constraints, conceptual models. If a
  control does not *look* like what it does, it is broken.
- **Ellen Lupton — *Thinking with Type*.** Measure (45–75ch), leading
  (1.4–1.6× body), hierarchy, kerning, orphans and widows.
- **Robert Bringhurst — *The Elements of Typographic Style*.** True small
  caps. Real quotes. One space after periods.
- **Josef Müller-Brockmann — *Grid Systems*.** Swiss grid, modular rhythm.
  Every element answers to a column.
- **Edward Tufte — *The Visual Display of Quantitative Information*.**
  Data-ink ratio. Kill chartjunk. Small multiples beat dials.
- **Dieter Rams — *Ten Principles*.** Ending with: as little design as
  possible.
- **Wathan & Schoger — *Refactoring UI*.** Hierarchy via weight and color,
  not size. Depth via shadow plus subtle color shift. Spacing hierarchy.
  HSL/oklch over hex for palette work. No pure black or white.
- **Noel Rappin — *Modern CSS with Tailwind*.** The utility-first case:
  locality of styling, state made visible in the markup, and duplication
  solved in the component layer rather than in CSS. Written against v3 —
  useful for the *reasoning*, never quote its syntax. See
  `references/tailwind.md` + `references/tailwind-v4.md`, which restate the whole book for v4.
- **Steve Krug — *Don't Make Me Think*.** Obviousness is the feature.
- **Alan Cooper — *About Face*.** Goal-directed design. Modes are bugs.
- **Jon Yablonski — *Laws of UX*.** Hick's (choice cost), Fitts's (target
  size/distance), Miller's 7±2, Jakob's (conventions win), Von Restorff
  (isolation draws attention), Aesthetic-Usability, Doherty (<400ms).
- **William Lidwell — *Universal Principles of Design*.**
- **Brad Frost — *Atomic Design*.** Atoms → molecules → organisms →
  templates → pages.
- **Alla Kholmatova — *Design Systems*.** Functional vs perceptual patterns.
- **Aarron Walter — *Designing for Emotion*.** Functional → reliable →
  usable → pleasurable. Do not chase pleasure before usable.
- **Gestalt.** Proximity, similarity, closure, continuity, figure/ground,
  common fate, common region. Layout is applied Gestalt.

### WCAG 2.2 — the legal baseline

Contrast ≥4.5:1 body, ≥3:1 large text and UI components. Focus visible.
Motion-reduce respected.

The 2.2 success criteria most sites miss:

- **2.4.11 Focus Not Obscured** — sticky headers eating the focused element.
- **2.5.7 Dragging Movements** — a single-pointer alternative is required.
- **2.5.8 Target Size** — 24×24 CSS px minimum (aim for 44 per Fitts).
- **3.3.7 Redundant Entry** — do not re-ask for what the user already gave.
- **3.3.8 Accessible Authentication** — no cognitive-function test.

**4.1.1 Parsing is obsolete — never dock for it.**
