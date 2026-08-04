# Colour: matching, not just contrasting

Load this before grading **Colour & Contrast**, before proposing a palette in
Mode A, and any time a fix changes a colour token.

`contrast.py` answers "is this legible". It does not answer "do these colours
belong to each other", and that second question is what makes a product look
designed. A palette can pass every WCAG check and still look like three
products glued together: a cold grey neutral, a warm orange accent, a red that
came from Tailwind's default, a green that came from somewhere else, and a
purple nobody can explain. Every ratio passes. It still looks wrong.

This file is the second question.

---

## 1. Work in oklch, and know why

Use `oklch()` for anything you author. Not fashion: three concrete properties.

- **L is perceptual.** In HSL, `hsl(60 100% 50%)` (yellow) and
  `hsl(240 100% 50%)` (blue) claim the same lightness and differ by roughly 12x
  in luminance. Any "50% tint" rule built on HSL produces a ramp that is even in
  the code and lumpy on screen. In oklch, equal L reads as equal lightness
  across hues, so **one lightness scale can serve every hue** and contrast
  becomes predictable before you measure it.
- **C is independent of L.** You can hold saturation constant while walking
  lightness, which is what a coherent ramp is.
- **Hue is stable.** Darkening an sRGB blue by multiplying channels drags it
  toward purple. In oklch it stays the hue you chose.

Practical consequence: **the contrast of a pairing is roughly predictable from
the L gap.** As a working rule on a white-ish page, body text wants L around
0.45 or below; a mid-grey at L 0.55-0.60 is the zone where "muted" text
quietly stops passing. Predictable is not the same as measured. Always confirm
with `contrast.py`, because chroma and hue move the ratio at the margins and
the margin is where the failures live.

**Do not ship raw oklch with no fallback if the browser floor demands it.** In
2026 the support is fine everywhere that matters; check the project's own
browserslist rather than assuming either way.

---

## 2. The lightness ladder

Build one ladder. Use it for every hue in the system, including the neutrals.
A serviceable 11-step ladder:

```
0.97  0.93  0.86  0.75  0.65  0.54  0.45  0.37  0.27  0.19  0.13
 50   100   200   300   400   500   600   700   800   900   950
```

Three rules for the ladder:

- **Monotonic and smooth.** Sort a ramp by step and the L values must fall
  monotonically with no step more than about 1.6x the size of its neighbours. A
  ramp with a flat spot has two steps nobody can tell apart, and a ramp with a
  cliff has a gap where a needed value should have been.
- **Chroma is a curve, not a constant.** Peak chroma sits in the middle
  (roughly steps 400-600) and falls toward both ends, because a very light or
  very dark colour cannot hold much chroma without leaving the gamut. Holding C
  constant across the ramp is the most common oklch mistake: the 50 step looks
  radioactive and the 950 step clips.
- **Stay in gamut.** Check the target gamut before committing. If the project
  ships P3, gate the extra chroma behind
  `@media (color-gamut: p3)` and keep the sRGB value as the base, so the design
  does not depend on a display the user may not have.

---

## 3. Colour matching: the five coherence tests

This is the part `contrast.py` could not answer before. Run all five.

### Test 1 - Neutral temperature

Pure grey (C = 0) is the safe answer and reads slightly cold and slightly
cheap. A tinted neutral is the single highest-leverage colour decision most
products never make: give the neutrals a small chroma (roughly 0.004-0.02)
pulled toward the accent's hue, or deliberately away from it.

The failure is **mixed** temperature: a warm surface, a cold border, and a
neutral text token from a third source. Measure it: convert every neutral token
to oklch and look at the hue values of those with C > 0.003. If they scatter
across more than about 40 degrees, the neutrals do not agree, and that
disagreement is visible as a faint dinginess nobody can name.

### Test 2 - Hue family count

Count distinct hue families in use (cluster hues within 25 degrees). A coherent
product palette is:

- **1 accent** hue family, plus
- **1 neutral** family, plus
- **semantic** hues that exist because they carry meaning: success, warning,
  danger, and optionally info.

That is 4-6 families total. **Seven or more chromatic families with no
semantic job is the finding**, and it usually means someone imported a whole
default palette and used whatever looked nice per component. A second accent is
legitimate only if it has a named job (a secondary brand hue for data
visualisation, or a distinct product line).

### Test 3 - Chroma agreement

Within a role, chroma should agree. If the accent at step 500 has C = 0.19 and
the danger at step 500 has C = 0.08, the danger reads washed-out next to the
accent and the pair looks unrelated. Line the semantic hues up at the same step
and compare C: a spread of more than about 2x across the semantic set means
they came from different places.

The corollary: **the accent may sit slightly higher in chroma than everything
else on purpose.** That is what makes it the accent. Just make it a decision,
and make the rest agree with each other.

### Test 4 - Semantic hue separation

Success, warning, and danger must be distinguishable from each other **and**
from the accent. Two traps:

- **A blue accent with a blue info state.** The user cannot tell "this is
  interactive" from "this is a notice".
- **A green accent with a green success state**, or a red accent with a red
  danger state. Whenever the accent collides with a semantic hue, move the
  semantic one or change the semantic signal to shape plus text.

And the one that is not a taste call: **roughly 8% of men have a red-green
colour vision deficiency.** Success and danger differing only in hue is a WCAG
1.4.1 failure in practice. Add an icon, a word, or a lightness difference
large enough to survive desaturation. Screenshot the UI, desaturate it, and
check you can still read the states. That is a two-minute test and it catches
the real failure every time.

### Test 5 - The accent budget

Accent should be **under about 10% of visible pixels**. The probe measures
`accentShare`. Over 10% and the accent stops being an accent, which means the
primary action stops standing out, which is a Hierarchy failure that presents
as a Colour one. Under 1% on a marketing page usually means the brand is not
present.

Where the accent goes, in order: the primary action, the current-location
indicator, the focus ring, links. Not: every card border, every icon, every
heading.

---

## 4. Building a palette from nothing

When you have to propose one (Mode A), in this order:

1. **Pick the accent hue from the product's job**, and say why in one clause.
   Blue is the default because it is safe; that is exactly why it says nothing.
   Finance and trust skew blue and green; craft and editorial skew warm; a
   product used for eight hours a day wants an accent that does not fatigue,
   which means lower chroma than a marketing site would use.
2. **Set the neutral temperature** relative to it. Same-side-of-the-wheel
   neutrals feel harmonious and can go muddy; opposite-side neutrals feel
   crisp and can go clinical. Pick one and commit.
3. **Build the ladder** (section 2) for the neutral first, because 90% of the
   pixels are neutrals. Get that right and the product already looks composed.
4. **Derive the accent ramp on the same L ladder**, adjusting chroma along the
   curve.
5. **Choose semantic hues that clear Test 4** against the accent.
6. **Assign semantic roles, not colour names.** `--color-surface`,
   `--color-surface-raised`, `--color-ink`, `--color-muted`, `--color-border`,
   `--color-accent`, `--color-accent-strong`, `--color-danger`. A token called
   `--blue-500` in component code means the theme cannot change, and it means
   nobody can tell what the colour is *for*.
7. **Check every real pairing** with `contrast.py --css`, in both themes,
   before showing anyone anything.

Three directions, never one. And name what each one costs.

---

## 5. Dark mode is a design, not a filter

Inverting a light theme produces a bad dark theme every time. The rules that
actually differ:

- **Never pure black.** `#000` with light text creates halation: the text
  smears for astigmatic readers, which is a large fraction of people. Base
  surface around L 0.15-0.20. Never pure white text either; L around 0.92-0.95.
- **Elevation flips.** In light mode, higher surfaces get shadows. In dark
  mode, shadows do almost nothing, so **higher surfaces get lighter**. A dark
  theme that keeps using shadows for elevation reads flat.
- **Chroma comes down.** The same accent chroma that looks confident on white
  vibrates on a dark surface. Typically pull C down 10-25% and raise L.
- **Contrast targets invert their difficulty.** Light-on-dark at the same
  measured ratio reads *heavier*; text can look bolder than intended. Consider
  a slightly lighter weight for dark-mode body text if the face supports it.
- **Semantic colours need their own dark values.** A danger red tuned for white
  is usually too dark on a dark surface and drops under 4.5:1.
- **Declare `color-scheme`.** `:root { color-scheme: light dark }` (or `dark`
  on the dark theme) is what makes the browser's own chrome follow: scrollbars,
  `<select>` popups, autofill, date pickers, spin buttons, the caret. A dark app
  with a white OS scrollbar and a white select popup is not a dark app. See
  `components.md` section 7.
- **Screenshot both.** The probe runs a dark pass. Look at it. Dark-mode
  regressions are invisible to anyone developing in light mode, and they are
  the most common thing a design fix breaks.

---

## 5a. A theme nobody can reach

A dark theme keyed only to `@media (prefers-color-scheme: dark)` is reachable
only by changing an OS setting. That is a real gap, and it cuts both ways: the
visitor reading in bright sun who wants the light theme their laptop is not set
to, and the one whose OS flipped at sunset and now cannot get back. **A dark
theme with no in-page switch is a finding** (major, Colour pillar) even when
the theme itself is beautifully designed. It is also the cheapest finding on
this list to fix, because the tokens already exist -- only the selector they
hang off has to change.

Grade what exists before writing anything:

| What you find | Verdict |
|---|---|
| No dark theme at all | See "when to build one" below |
| Dark tokens under `prefers-color-scheme` only | Finding: no switch. Rekey + add control |
| Dark tokens under a class/attribute, control present | Correct. Check the pre-paint script exists |
| Control present, but the page flashes light on load | Finding: theme resolved after paint |
| Both a media query and an attribute, tokens duplicated | Finding: two sources of truth; they will drift |

### Rekeying the tokens

One block, one selector. Do **not** keep the media query as a second copy of
the token list -- duplicated dark tokens drift, and the drift shows up months
later as one colour that is right in one path and wrong in the other. The
system preference reaches the page through the script below, not through a
second CSS block.

```css
:root                      { color-scheme: light; --surface: oklch(0.99 0.004 85); /* ... */ }
:root[data-theme="dark"]   { color-scheme: dark;  --surface: oklch(0.20 0.014 250); /* ... */ }
```

`color-scheme` moves **into** the two blocks. A manual switch and a blanket
`color-scheme: light dark` contradict each other: the visitor picks dark, and
the scrollbars and `<select>` popups stay light because the browser is still
following the OS. Declaring it per theme is what keeps the chrome in step.

Tailwind v4: pair this with `@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));`
so any surviving `dark:` utilities follow the same switch. See `tailwind.md` §13.

### Resolving before first paint

The attribute has to be on `<html>` **before the first paint**, which means a
synchronous inline script in `<head>`. Anything later -- a `defer`d script, an
effect in a client component, a framework provider -- paints the light theme
and then snaps to dark. That flash is worse than shipping no dark theme, and
it is the single most common way this feature is implemented badly.

```html
<script>
  (function () {
    try {
      var s = localStorage.getItem('theme');
      document.documentElement.dataset.theme =
        (s === 'light' || s === 'dark') ? s
          : (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    } catch (e) { document.documentElement.dataset.theme = 'light'; }
  })();
</script>
```

Precedence is: **stored choice > OS preference > light**. The `try` matters --
storage throws in locked-down browsers, and an exception here leaves the page
with no theme at all. In React/Next, this element is why `<html>` needs
`suppressHydrationWarning`; scope that to `<html>` and nowhere else, since the
script mutates only that element.

### The control

- **Two states, not three,** unless the product is a settings-heavy tool. The
  "System" option in a three-way is the default already; a visitor who never
  touches the control is following the OS regardless, which is the behaviour
  the third option promises. Two states is the smaller, clearer control.
- **Icon shows the destination, not the state.** Moon while light (press for
  dark), sun while dark. The label follows: `aria-label="Switch to dark theme"`.
  A label that names the current state tells a screen-reader user the one thing
  they could already get from the page.
- **Let CSS pick the icon, not JavaScript.** Render both and hide one with
  `:root[data-theme="light"] .icon-sun { display: none }`. A component that
  waits for hydration to know which icon to draw either flickers or renders
  blank on the server.
- **Hide the control when the script did not run.** `.theme-toggle { display:
  none }` with `:root[data-theme] .theme-toggle { display: inline-flex }`. A
  switch that cannot switch is worse than no switch. (Put these rules outside
  `@layer` so they beat the utility classes on the same element.)
- **Persist the choice** under one key, and **keep following the OS until the
  visitor picks a side** -- subscribe to `matchMedia` change and apply it only
  when nothing is stored. Once they choose, their choice outranks the system.
- **The attribute on `<html>` is the state.** Read it; do not keep a second
  copy in component state that can drift from what the page is painting. In
  React, `useSyncExternalStore` over a `MutationObserver` on that attribute is
  the honest subscription, and it keeps lint's set-state-in-effect rule happy.
- **Put it where a control lives**, not floating: the header cluster next to
  the primary action on desktop, and in the mobile header row too. A toggle
  that exists only in a desktop nav is missing on the viewport where "the
  screen is too bright" is most often felt.
- It is a `<button>`, it gets `cursor-pointer`, a visible focus ring, and a
  >=24px hit target like anything else. `components.md` applies to it.

### When to build one

**Absent dark mode is not automatically a finding** (`scoring.md` keeps it off
the docking list). Build one when any of these is true, and say which:

- The product promises one, or the codebase half-implements one (stray `dark:`
  utilities, a `--surface-dark` token nothing reads, an unreachable media block).
- The audience expects one: developer tools, editors, dashboards, anything
  read for hours, anything read at night.
- The user asked for one.
- The palette already carries the roles a dark theme needs (semantic tokens for
  surface/text/border/state rather than hardcoded hexes at call sites), so the
  work is deriving values rather than rewriting the product's colour layer.

And say so rather than building when the opposite holds: **a product with no
token layer needs the token layer first.** Deriving a dark theme on top of
three hundred hardcoded `bg-white text-gray-900` call sites means touching
every one of them, which is a refactor, not a design fix. Report it that way,
scoped and costed, and let the user decide.

Deriving the values themselves is section 5 plus `contrast.py`: every pairing
the components actually use gets measured before it ships, in both themes. A
dark theme is not done when it looks right in a screenshot of the home page.

**Walk it in the browser before calling it done.** `contrast.py` grades the
token file and the probe's dark pass grades the rest state; neither can see
the two places a dark theme actually fails. Through the `browse` skill
(`browser-verification.md`), with the theme switched:

- **Hover and focus every repeated component.** A tint picked against paper
  routinely lands on the wrong side of the dark surface - `surface-sunken` is
  *below* the page in light and a hover that lifted in one theme can sink in
  the other. The probe measures the inert and hue-only cases per theme, so run
  it in both; the numbers only exist for the pass you actually ran.
- **Look at the chrome the page does not paint** - scrollbar, `<select>`
  popup, caret, autofill, the focus ring the UA draws. That is what
  `color-scheme` is for, and it is invisible in a screenshot of the document.

---

## 6. Contrast, precisely

- **4.5:1** body text. **3:1** large text (18.66px bold or 24px regular) and
  **every non-text UI boundary** that carries meaning: input borders, focus
  rings, toggle tracks, chart series, icon-only buttons (SC 1.4.11).
- **AAA is 7:1** and is a worthy target for body copy specifically. It is not a
  failure to miss it, and never apply the WCAG hard cap for an AAA miss.
- **Focus rings need 3:1 against both the control and the page.** A ring that
  clears against the button and vanishes against the page behind it fails
  wherever the button is. Two checks, not one.
- **Disabled controls are exempt** from contrast requirements, and should still
  be legible. Exempt is not a licence for 2:1.
- **Placeholder text is not exempt**, because users read it.
- **APCA is advisory.** It models real perception better than WCAG 2 does, and
  it is not the standard anyone is held to. `contrast.py` prints it as advice.
  Never fail a design on APCA alone, and never pass one on APCA when WCAG 2
  fails.
- **Test on the composited backdrop.** Text over an image, a gradient, or a
  translucent surface has to pass against its *worst* backdrop pixel, not the
  token underneath. The probe composites; a hand check usually does not.

---

## 7. The tells

| Tell | What it means |
|---|---|
| Every colour is a Tailwind default at step 500 | Nobody chose. Slop item 5. |
| Neutrals from `slate` and semantics from `red`/`green`/`amber` untouched | Four unrelated hue systems shipped as one |
| Accent used for a card border, a heading, an icon, and a badge | Accent budget blown; nothing is emphasised |
| Two greys within 3 L points of each other | The scale has a duplicate step nobody can use |
| A hover state that changes hue rather than lightness | Reads as a different colour, not a state |
| Semantic colour is the only signal for status | 1.4.1 failure |
| Dark theme is the light theme with `filter: invert` | Every image is wrong and every shadow is inverted |
| `#000` or `#FFF` anywhere in the token file | Nobody looked at it on a real screen |
| The selected-row tint and the hover tint are the same | Cannot tell where you are in a table |
| Gradient used to hide an undecided palette | Two colours because one could not be chosen |

---

## 8. Running the tools

```bash
S=~/.claude/skills/designer-dude/scripts

# every pairing in the token file, per theme, with hue-preserving fixes
python3 $S/contrast.py --css src/app/globals.css

# palette coherence: ramps, hue families, chroma agreement, neutral temperature
python3 $S/contrast.py --harmony --css src/app/globals.css

# one pairing, with the nearest passing colour
python3 $S/contrast.py "oklch(0.62 0.14 250)" "#ffffff"

# a proposed palette before a line of it is built
python3 $S/contrast.py --design-md DESIGN.md
```

`--harmony` reports the five coherence tests as measurements. Like every other
output in this skill, its rows are **candidates**: a two-accent palette can be
correct, a wide neutral hue spread can be a deliberate warm/cool split between
surfaces and text. Confirm before it becomes a finding, and record the reason
when you reject one.
