# Mode A - Direction (aesthetic + system)
### and Mode E - Shotgun exploration

The user needs the look: fonts, colors, spacing, motion, vibe.

---

## Intake gate - required before you propose anything

Without pinned inspiration, direction averages to slop. Gather concrete
references first:

- **Three products you admire** - URLs or screenshots, one sentence each on
  *what specifically*. "I like Linear" is not enough - the type hierarchy?
  the empty states? the warmth?
- **One product you would hate to be mistaken for** - URL plus one sentence
  on the exact tell.

**Open the references when their craft is the question - and do not work from
memory when you do.** A remembered impression of a site is exactly the kind of
confident wrongness this skill exists to avoid: products get redesigned, and
your recollection of one is older than its current type scale. So if the answer
turns on *how the reference actually renders* - its measure, its type scale,
the weight of its hover, whether its restraint is real - open it.

Drive it through the `browse` skill (`browser-verification.md` has the session
order and the budget): **one session for all four references**, navigate,
screenshot at 1440 and 390, and where the question is about a system rather
than a picture, point `probe-config.json` at the reference URL and run
`probe-runner.mjs` in that same browser. It is the rig that grades the target,
so "their measure is 62ch and yours is 96ch" replaces "theirs feels more
readable". `calibration.md` holds the anchors already captured this way; add
yours - and **read it first**, because an anchor already on disk means you do
not need to open that product again at all.

Skip the pass when the user has already said what specifically they admire and
the direction does not hinge on a measurement - then say you worked from their
description rather than from the live page.

(`probe-selftest.mjs --url <u> --out <f>` does the same in a throwaway browser
and is the fallback when the MCP profile is locked by another session. It is
not the default: it cannot inherit a login and it starts a second browser.)

When they name references, **check the corpus** (`ls "$CORPUS"`, see
`canon.md`). If an admired reference has a file there, read it before the
question sequence so your follow-ups are concrete - ask about its actual
choices ("Linear runs Söhne at a tight 1.2 ratio with near-zero accent -
is it the restraint you want, or the specific palette?") rather than
generic taste questions.

**The one exemption:** if the user cannot produce references - they do not
know the space, or they are early and genuinely have no taste anchors yet -
do not deadlock. Say the gate exists and why, then offer a **starter
board**: pull 3 contrasting corpus files, show what each commits to in one
line each, and ask which direction pulls. That gives them references to
react to. Reacting is easier than generating, and it satisfies the gate's
actual purpose, which is pinning taste to something concrete.

Only then start the question sequence.

---

## Question sequence

One at a time, via `AskUserQuestion`. Do **not** list them upfront. Reflect
the last answer in the next question's framing.

1. Who is the primary user - age range, context, job-to-be-done?
2. Three adjectives that should describe the product (at least one
   surprising - not "clean", "modern", or "professional").
3. An aesthetic you absolutely refuse. What does "wrong" look like?
4. Of your three admired references, which single detail would you steal?
5. Of your anti-reference, what specifically do you never want to be?

---

## Deliverable

**Three directions, never one:**

- **Safe** - the category baseline done well.
- **Distinctive** - breaks one convention on purpose. Name the convention
  and why breaking it serves this product.
- **Wildcard** - the one you would ship if it were your own product.

Each with a named aesthetic, a font stack, an oklch-coherent palette (hex,
plus P3 where it matters), and a one-line rationale.

Then write or update **`DESIGN.md`** per the schema below.

---

## Mode E - Shotgun exploration

Reach for this when the user cannot choose between directions, or asks to
"see options." It is Mode A's intake with wider output and a tighter loop.

**Produce 3–5 variants, each genuinely distinct** - not one idea at three
saturations. Distinct means they differ on at least two of: type voice,
color strategy, layout structure, motion character.

**Format, in order of preference:**

1. **Standalone HTML mockups** - one file per variant, self-contained
   (inline CSS, no external fonts unless you embed them), rendering the
   *same real content* so the comparison is fair. Plus a
   `comparison-board.html` that iframes or screenshots them side by side.
   Write to `design-explore/{date}/`. **Then look at them in a browser**, via
   `browse` - `serve.sh --dir design-explore/{date}` serves the directory
   statically, and a variant you have not rendered is a guess about a variant.
   The board is also where the probe is cheap to run per variant, which is how
   "this one is warmer" becomes "this one is 4 hue-families wide and that one
   is 2".
2. **A single comparison board** with inline SVG or CSS blocks, if the
   variants are palette/type only.
3. **Prose with exact tokens**, if the user only wants to think out loud.

**Do not score shotgun variants.** Scoring is for shipped or planned work.
A variant is an option, not a submission - grading them collapses the
divergence you are trying to create.

**After each round, ask exactly one question:** "Warmer, colder, or
restart?" Then converge:

- **Warmer** → push the chosen variant further in its own direction; drop
  the others.
- **Colder** → the direction is wrong; generate a new set away from it.
- **Restart** → the intake was wrong. Return to the questions, do not
  regenerate blind.

Stop at **three rounds**. If nothing has landed by then, the problem is the
brief, not the variants - say so plainly and go back to intake.

---

## DESIGN.md schema (2026)

**Emit the Stitch-compatible format** - the flat YAML-in-markdown
convention used by Google Stitch and the whole `awesome-design-md` corpus.
That is the format AI agents and design tools actually read; a file no tool
can parse is a worse deliverable than one that is slightly less
theoretically pure. The corpus files are the ground-truth template - open
the nearest match and mirror its structure.

Top-level sections, in this order:

```yaml
version: <draft|stable>
name: <Brand>-design-analysis
description: <one paragraph: the system's voltage, type voice, signature mark>

colors:           # flat, role-named keys, hex values
  primary: "#cc785c"
  primary-active: "#a9583e"
  ink: "#141413"
  body: "#3d3d3a"
  muted: "#6c6a64"
  canvas: "#faf9f5"
  surface-soft: "#f5f0e8"
  surface-card: "#efe9de"
  on-primary: "#ffffff"
  success: "#5db872"   # warning / error too

typography:       # named roles, each with the full type spec
  display-xl: { fontFamily: "...", fontSize: 64px, fontWeight: 400, lineHeight: 1.05, letterSpacing: -1.5px }
  title-md:   { fontFamily: "...", fontSize: 18px, fontWeight: 500, lineHeight: 1.4, letterSpacing: 0 }
  body-md:    { fontFamily: "...", fontSize: 16px, fontWeight: 400, lineHeight: 1.55, letterSpacing: 0 }

rounded:          # radius scale, 2–3 meaningful values (+ pill)
  sm: 6px
  md: 8px
  lg: 12px
  pill: 9999px

spacing:          # scale on a 4/8 base
  xs: 8px
  md: 16px
  lg: 24px
  section: 96px

components:       # compose the tokens above via {alias} references
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    padding: 12px 20px
```

### Craft rules inside that format

They live in the values, not a different syntax:

- **Roles, not decoration.** Color keys name a role (`primary`, `ink`,
  `canvas`, `surface-*`, `success`), never a generic ramp (`gray-200`,
  `blue-500`). Components reference tokens via `{colors.primary}` - never
  hardcode a hex inside `components:`.
- **Type scale on a ratio** (1.2 / 1.25 / 1.333) with `fontSize`,
  `lineHeight`, and `letterSpacing` per step. Name variable-font axes
  (weight, optical size, width, slant) when the family is variable.
- **Radius:** 2–3 values used with meaning, not one bubbly radius.
- **Spacing:** 6–8 steps on a 4/8 base, named by role.
- **Motion + anti-patterns:** add a `motion:` block (durations
  `fast`/`base`/`slow`, easings `enter`=ease-out / `exit`=ease-in /
  `standard`=ease-in-out, plus a `prefers-reduced-motion` note) and an
  `anti-patterns:` list naming the slop this brand explicitly refuses. The
  corpus omits these; adding them is this skill's value-add, not a reason
  to abandon the format.

### The five blocks the corpus omits and this skill requires

`DESIGN.md` is what Mode D grades **drift** against. A decision that is not in
this file cannot drift, which sounds convenient and means the opposite: it gets
re-decided per component, differently each time, and the review can only call
it inconsistent after the fact. These five are graded by the rubric and are
absent from every corpus file, so write them.

```yaml
colorScheme: light dark      # what :root declares. Without it the browser
                             # draws scrollbars, the <select> popup, autofill
                             # and the caret in the WRONG theme, and none of
                             # that shows up in a screenshot.

focus:                       # graded at 3:1 against BOTH the control and the
  width: 2px                 # page behind it - two checks, not one
  offset: 2px
  color: "{colors.primary}"
  style: "solid ring, never removed without a replacement"

states:                      # the seven. `active` and `loading` are the two
  hover:    "surface +1 step, never a hue change"     # nobody designs
  active:   "surface +2 steps, 60ms, visible on touch"
  focus:    "{focus}"
  disabled: "opacity .55, cursor not-allowed, reason stated adjacent"
  loading:  "width preserved, label kept, click blocked"
  empty:    "names the next action, never 'No data'"
  error:    "names the field and the fix, not carried by colour alone"

elevation:                   # graded as shadow.distinct; 3-4 coherent steps,
  flat:   "none"             # ONE light source. In dark mode elevation is
  raised: "0 1px 2px rgb(0 0 0 / .06)"    # LIGHTER SURFACE, not a shadow.
  overlay: "0 8px 24px rgb(0 0 0 / .12)"

dark:                        # a design, not an inversion. Only the tokens
  canvas: "#16150f"          # that CHANGE. Base L 0.15-0.20, never #000;
  ink: "#eeece4"             # accent chroma down 10-25%; semantics get their
  primary: "#e0916f"         # own values or they drop under 4.5:1.

voice:                       # Content & Voice is 10 points and is otherwise
  person: "second person, present tense"        # graded from vibes
  banned: ["Welcome to", "Unlock the power of", "seamless", "not just X but Y"]
  numbers: "tabular, units in the header, never a raw ISO timestamp in a list"
  errors: "name the field and the fix; never 'Something went wrong' when the
           system knows what went wrong"
```

Two rules about filling them in:

- **A value you cannot justify in one clause is a value you have not chosen.**
  Write the clause as a comment. "Ring is the accent, because the accent is
  already the interactive colour" is a decision; `2px solid blue` is a default.
- **Run `contrast.py --design-md DESIGN.md` and `--harmony --design-md` before
  showing anyone the file.** A palette that fails before a line of it is built
  is the cheapest possible thing to fix, and the most expensive one to discover
  in round 3 of a campaign.

### Landing the tokens in a Tailwind v4 project

`DESIGN.md` is the source of truth; `@theme` is where it becomes real. On a
Tailwind project the schema above maps 1:1 onto theme variables, and saying
so in the deliverable is what stops the tokens from being decorative:

```css
@theme {
  --color-primary: oklch(0.62 0.11 42);   /* colors.primary */
  --color-ink:     oklch(0.19 0.01 90);   /* colors.ink     */
  --color-canvas:  oklch(0.98 0.01 85);   /* colors.canvas  */
  --radius-md:     0.5rem;                /* rounded.md     */
  --text-display-xl: 4rem;                /* typography.display-xl */
  --ease-enter:    cubic-bezier(0, 0, 0.2, 1);  /* motion.enter */
}
```

Each namespace generates every consumer for free - `--color-primary` yields
`bg-primary`, `text-primary`, `border-primary`, `ring-primary`, `from-primary`.
That is the mechanical argument for role-named tokens, and it is why
`colors: { gray-200: … }` is wrong beyond aesthetics.

Two rules when you write this block:

- **Multi-theme needs `@theme inline`** plus scoped vars on `:root` /
  `.dark`. Without `inline`, `bg-canvas` resolves once at `:root` and the
  theme switcher silently does nothing.
- **Do not also emit a `tailwind.config.js`.** v4 does not read it unless
  `@config` is present, and shipping both guarantees they drift.

Full detail in `references/tailwind.md` §13.

### On oklch and DTCG nesting

The W3C Design Tokens spec (oklch, Display P3, nested `surface.default`) is
the right *mental model* for keeping a palette perceptually coherent -
reason in it. But **ship hex in the Stitch-flat layout** so the file stays
interoperable with the corpus, Stitch, and downstream agents.

If the project already has a DTCG pipeline (Style Dictionary, Tokens
Studio, Terrazzo, or Figma Variables), match *its* names 1:1 instead.
Otherwise the flat Stitch schema wins.

### Accessibility check before you ship a palette

Every direction must clear WCAG AA on its own tokens **before** you present it.
This is not an eyeball step - run the calculator:

```bash
python3 ~/.claude/skills/designer-dude/scripts/contrast.py --design-md DESIGN.md
# or, before the file exists, check the pairings directly:
python3 ~/.claude/skills/designer-dude/scripts/contrast.py "oklch(0.55 0.17 38)" "#faf9f5"
```

It reads oklch as happily as hex, grids every role pairing the naming makes
explicit, checks light and dark blocks **separately** (a flattened palette
exists in neither theme), and when something fails it prints the nearest
passing colour **with the hue held**, so the fix does not cost you the brand.

Check `body` on `canvas`, `muted` on `canvas`, and `on-primary` on `primary` at
minimum. Note what the calculator cannot see: text over images or gradients,
translucent surfaces, and disabled states. Those need the rendered probe.

A beautiful palette that fails contrast is not a direction, it is a rewrite
waiting to happen - and under this skill's rubric it caps the score at C+ the
moment it ships. Presenting three directions where one of them cannot pass is
presenting two directions.
