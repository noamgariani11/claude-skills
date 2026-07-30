# Tailwind craft reference

Source: Noel Rappin, *Modern CSS with Tailwind*, 2nd ed. (Pragmatic
Bookshelf, 2022) — chapters 2–4 so far. The book is **Tailwind v3**. The
stack this skill actually reviews is **Tailwind v4.3.x + Next.js App
Router + React 19 + pnpm + `lucide-react`**. Every rule below is stated
in v4 terms; where the book is stale, the v3 form is marked **[v3 — do
not emit]** so it never gets copied into a review or a fix.

Load this file when a finding touches Tailwind syntax, the token system,
the spacing/type scale, or "how should this be expressed in classes."

**Currency:** verified 2026-07-30 against tailwindcss.com. Latest release
4.3.3 (4.3 shipped 2026-05-08). Re-verify before asserting a version-
specific claim older than ~6 months.

---

## 0 — The v3 → v4 correction table

The single highest-value part of this file. Emitting v3 syntax in a fix is
a real defect, not a style quibble — most of these silently do nothing.

| Book says **[v3]** | Emit instead **[v4]** |
|---|---|
| `@tailwind base; @tailwind components; @tailwind utilities;` | `@import "tailwindcss";` |
| `tailwind.config.js` + `theme.extend` | `@theme { --color-…: …; }` in the CSS entry file |
| `plugins: [require('@tailwindcss/typography')]` | `@plugin "@tailwindcss/typography";` |
| `@layer components { .btn { @apply … } }` | `@utility btn { … }` (real CSS, cascade-layered correctly) |
| `bg-gradient-to-r` | `bg-linear-to-r` (plus `bg-radial`, `bg-conic`) |
| `rounded` / `rounded-sm` | `rounded-sm` / `rounded-xs` (whole scale shifted down one) |
| `shadow` / `shadow-sm` | `shadow-sm` / `shadow-xs` (same shift; also `blur`, `drop-shadow`, `backdrop-blur`) |
| `shadow-inner` | `inset-shadow-xs` (inset shadows got a real scale) |
| `ring` (3px, blue-500) | `ring-3` + explicit `ring-blue-500`. Bare `ring` is now **1px `currentColor`** |
| `outline-none` | `outline-hidden` (`outline-none` now genuinely means `outline-style: none`) |
| `border` inherits `gray-200` | Default border color is **`currentColor`** — `border` alone now draws in the text color. Always pair: `border border-rule` |
| `!flex` | `flex!` (important moved to the end) |
| `bg-[--brand]` | `bg-(--brand)` (CSS vars use parens, not brackets) |
| `flex-shrink-*` / `flex-grow-*` | `shrink-*` / `grow-*` |
| `overflow-ellipsis` | `text-ellipsis` |
| `bg-opacity-50`, `text-opacity-50`, `border-opacity-*`, `ring-opacity-*`, `divide-opacity-*`, `placeholder-opacity-*` | slash modifiers only: `bg-black/50` |
| `grid-cols-[max-content,auto]` | `grid-cols-[max-content_auto]` (commas → underscores) |
| `first:*:pt-0` | `*:first:pt-0` (variant stacking now reads left-to-right) |
| `focus:transform-none` to reset a `scale-150` | `focus:scale-none` — transforms are individual properties now; `transition-[opacity,transform]` → `transition-[opacity,scale]` |
| `max-w-screen-md` | **gone.** Use `max-w-3xl`, a container query (`@md:`), or alias it yourself: `@theme { --width-screen-md: var(--breakpoint-md); }` |
| `font-hairline` | never existed in v3 either — the book is wrong. Weights are `font-thin` (100) → `font-black` (900) |
| Preflight gives `button { cursor: pointer }` | **v4 Preflight sets `cursor: default`.** See §6 — this is the #1 source of "why is nothing clickable" polish findings |
| Preflight placeholder = `gray-400` | now `currentColor` at 50% opacity |

Also gone in v4: `corePlugins`, `resolveConfig`, and Sass/Less/Stylus
support. Browser floor is Safari 16.4 / Chrome 111 / Firefox 128 (`@property`,
`color-mix()`).

**New since the book that you should actually reach for:**

- `size-*` — sets width and height together. `size-4` beats `h-4 w-4`, and it
  is the correct sizing for a `lucide-react` icon.
- Container queries are core, no plugin: `@container` on the parent, `@sm:`
  / `@max-md:` on children. For a component that must work in a sidebar
  *and* a full-width page, this is the right tool, not `md:`.
- `text-shadow-*` and `mask-*` (4.1).
- Logical properties everywhere (4.2): `inline-size` / `block-size`
  utilities, `inset-s-*` / `inset-e-*` / `inset-bs-*` / `inset-be-*`.
  `start-*` / `end-*` are deprecated (still work, warn).
- **Scrollbar utilities are first-party (4.3):** `scrollbar-thin` /
  `scrollbar-auto` / `scrollbar-none`, `scrollbar-thumb-*`,
  `scrollbar-track-*` (with opacity modifiers), `scrollbar-gutter-stable`.
  A custom-scrollbar finding no longer needs hand-rolled
  `::-webkit-scrollbar` CSS — call for the utility.
- `zoom-*` and `tab-*` (4.3).
- Palette is oklch and now 26 ramps — `mauve`, `olive`, `mist`, `taupe`
  joined in 4.2. Those four are genuinely useful escapes from the
  slate/zinc/gray default-SaaS gray.

---

## 1 — Why utility classes are defensible (the book's argument, kept)

Worth having ready, because "this HTML is unreadable" is the first thing
every reviewer says.

1. **Locality.** At the point of use, both *what* changed and *how far*
   the change reaches are explicit. No hunting a stylesheet to learn
   whether `.card-title` is also used on the settings page.
2. **Modifiers put state in the markup.** `hover:`, `focus-visible:`,
   `dark:`, `md:`, `group-hover:` mean the element's full behavior is
   visible in one place.
3. **You write far less bespoke CSS**, so you name far fewer things —
   and naming is where CSS architectures actually rot.
4. **Changes are predictable.** Same specificity everywhere; last one
   wins.

The cost is duplication, and the book is right that the answer is *not*
CSS. See §2.

---

## 2 — Duplication: components first, `@apply` almost never

The book offers `@apply` and components as peers. In a React/Next
codebase they are not peers.

**Correct:** extract a component.

```tsx
export function SectionHeading({ children }: { children: React.ReactNode }) {
  return <h2 className="text-2xl font-semibold tracking-tight text-ink">{children}</h2>;
}
```

**Wrong in this stack:**

```css
/* [v3 idiom — do not emit] */
@layer components { .section-heading { @apply text-2xl font-semibold; } }
```

Why: a CSS class cannot carry the props, the `as` polymorphism, the ARIA
wiring, or the variant logic that the component needs anyway. You end up
maintaining both. `@apply` also defeats the thing that makes utilities
readable — you are back to reading a stylesheet to learn what a class does.

**Legitimate `@apply` / `@utility` uses** (short list, hold the line):
- Styling markup you do not control — third-party widget innards, CMS
  output, `dangerouslySetInnerHTML`.
- One or two genuine base-layer resets in `@layer base` (e.g. restoring
  `button { cursor: pointer }`, see §6).
- A token-ish utility used across framework boundaries.

If you do register one, use `@utility name { … }`, not
`@layer components`. `@utility` participates in Tailwind's ordering, so a
later utility class still overrides it — which is the whole point of the
book's `@layer` argument, now handled properly.

> **Next.js gotcha:** `@apply` inside a CSS Module or `styled-jsx` block
> needs `@reference "../app/globals.css";` at the top of that file, or the
> theme variables are not in scope and it silently fails to compile the
> utility.

**Variants:** for a component with real variant matrices, use `cva`
(class-variance-authority) plus `tailwind-merge` via `cn()`. Conditional
classes appended without `twMerge` produce `px-4 px-6` and whichever
Tailwind emitted last wins — not whichever you wrote last. That is a
frequent, invisible bug.

**Never construct class names by interpolation.** The book flags this and
v4's scanner makes it worse — it scans source as plain text and does not
evaluate JS.

```ts
// BROKEN: the class never gets generated
const cls = `text-${color}-300 hover:text-${color}-700`;
// Correct: full literal strings, mapped
const TONE = { rose: "text-rose-300 hover:text-rose-700", sky: "text-sky-300 hover:text-sky-700" } as const;
```

---

## 3 — Typography

### Scale

Thirteen steps, `text-xs` → `text-9xl`, `text-base` = 1rem/1.5rem. Each
step carries a paired line-height. From `text-5xl` up the paired leading
is `1` — **so any display heading needs its leading re-checked by eye**;
`1` is tight enough to collide descenders with the next line at large
sizes on two-line headings.

v4 gives you the slash form to override inline: `text-3xl/9`,
`text-lg/relaxed`. Prefer that over a separate `leading-*` class — it keeps
the pairing in one token.

**Design calls:**
- A page needs ~4–5 type sizes, not 13. Pick them, put them in `DESIGN.md`,
  and treat a sixth as a finding.
- De-emphasize with **size and weight**, never a lighter color. (This is
  also Refactoring UI, and it is a hard rule in the Miskari repo.)
- Body measure 60–75 characters. `max-w-prose` is 65ch and is usually
  right. A full-width paragraph in a 1440px container is a finding.
- `tracking-tight` on display sizes ≥ `text-4xl` is nearly always an
  improvement; `tracking-wide` + `uppercase` + `text-xs` is the correct
  eyebrow/label recipe. Do not track body text.

### Weight

`font-thin` 100 → `font-black` 900. Two facts the book glosses:
- Weights only exist if the loaded font ships them. With `next/font`,
  `weight: ["400","600"]` means `font-bold` (700) **synthesizes** — the
  browser fakes it, and it looks smeared. Check the font import before
  writing a weight finding.
- 100/200 are unreadable below ~24px on most screens. `font-thin` body
  copy is a legitimate contrast/legibility finding.

### Decoration, case, alignment

`underline` / `overline` / `line-through` / `no-underline`; styled with
`decoration-{solid,double,dotted,dashed,wavy}`, `decoration-{0,1,2,4,8}`,
`decoration-{color}`, and `underline-offset-{n}`. For links in body copy,
`underline underline-offset-2 decoration-1` reads far better than a bare
underline sitting on the baseline.

`uppercase` / `lowercase` / `capitalize` / `normal-case`. `capitalize`
is title-case-by-CSS and mangles proper nouns and acronyms — prefer
correct source strings.

`text-left|center|right|justify`. **`text-justify` on the web is a
finding** — no hyphenation engine, so it produces rivers. Say so.

Vertical: `align-{baseline,top,middle,bottom,text-top,text-bottom,sub,super}`.
For aligning a lucide icon with a text label, do not use `align-*` — use
flex: `inline-flex items-center gap-2` with `size-4`.

### Leading and tracking

Relative: `leading-none|tight|snug|normal|relaxed|loose`. Numeric leading
in v4 rides the `--spacing` scale (`leading-6` = 1.5rem), so it behaves
like the book describes but is now driven by one variable.

Rule of thumb: leading goes **down** as size goes up, and **up** as
measure gets wider. `leading-relaxed` on long body copy, `leading-tight`
on headings.

### Special text

`selection:bg-*` / `selection:text-*` — inherited by children, so set it
once at the root. A product that ships default-blue selection on a warm
editorial palette is a small, real polish finding.

`first-letter:` and `first-line:` for editorial drop caps. `before:` /
`after:` exist; the book's advice holds — if the content is meaningful,
put it in a real element, not a pseudo-element the accessibility tree
handles inconsistently.

`marker:text-*` styles list bullets and inherits from the `ul`/`ol`.

### Lists

`list-disc` / `list-decimal` / `list-none`, `list-inside` / `list-outside`.
Preflight strips list styling, so a marketing page rendering markdown with
naked `<ul>`s and no bullets is a Preflight symptom, not a content bug —
that is what `prose` is for.

### Plugins

```css
@import "tailwindcss";
@plugin "@tailwindcss/typography";
@plugin "@tailwindcss/forms";
```

`prose` for long-form / rendered markdown. Sizes `prose-sm|base|lg|xl|2xl`;
grays `prose-gray|slate|zinc|neutral|stone`; per-element overrides
`prose-h1:font-bold`, `prose-a:decoration-1`, and the `prose-headings:`
group. `dark:prose-invert` is required in any themed product — `prose`
hardcodes its own colors and will render near-black text on a dark
surface. That is a WCAG failure, not a nitpick.

`@tailwindcss/forms` is a *reset*, not a design. It still needs the input
border and focus ring designed on top. Note it needs `type="text"` present
to size text inputs.

---

## 4 — Color and opacity

Pattern is uniform: `{prefix}-{color}-{level}` across `text-`, `bg-`,
`border-`, `ring-`, `divide-`, `outline-`, `decoration-`, `caret-`,
`accent-`, `shadow-`, `from-`/`via-`/`to-`, `fill-`, `stroke-`,
`scrollbar-thumb-`. Levels 50 → 950 (v4 added 950). Keywords:
`transparent`, `current`, `inherit`, `black`, `white`.

Opacity is the slash modifier: `text-ink/70`, `bg-black/50`,
`ring-accent/40`. Arbitrary: `bg-red-700/[43%]`.

**Design calls:**
- **Raw palette names in feature code are a finding.** `text-gray-500`
  scattered through components means there is no system. Ship semantic
  tokens in `@theme` — `--color-ink`, `--color-muted`, `--color-paper`,
  `--color-rule`, `--color-accent` — and reference those. This is what
  makes theming, and the light/dark pass, possible at all.
- v4 palettes are **oklch**, so `color-mix()` and gradient interpolation
  behave perceptually. `from-x to-y` interpolates in oklab by default,
  which is why v4 gradients no longer go gray in the middle. If someone
  needs the old muddy behavior for brand-match, `bg-linear-to-r/srgb`.
- Opacity is not a substitute for a color token. `text-ink/40` on a
  patterned or image background has an unpredictable computed contrast —
  measure it, do not eyeball it.
- The four 4.2 additions (`mauve`, `olive`, `mist`, `taupe`) are the
  cheapest available exit from AI-slop gray. Suggest them by name.

---

## 5 — The box

### Spacing

`p{t,b,l,r,x,y}-{n}` and `m{…}-{n}`; each `n` = 0.25rem. In v4 the whole
scale derives from one variable — `@theme { --spacing: 0.25rem; }` — and
is **dynamic**, so `p-13` or `mt-19` now generate even though they are not
in the v3 list. That is a footgun: it means a typo'd spacing value
compiles silently. A repo using nine distinct spacing steps on one screen
has no rhythm; call it.

Margins take `-auto` (`mx-auto` centers) and negatives (`-mt-4`).

Prefer **`gap-*` on a flex/grid parent** to margins on children. Margin
collapse, `:last-child` exceptions, and `space-y-*` all disappear. Reach
for `space-y-*` only when the container cannot be a flex/grid parent —
and note v4 changed its selector to `:not(:last-child)` with
`margin-bottom`, so any v3-era override targeting
`:not([hidden]) ~ :not([hidden])` is now dead code.

The book's aside stands: **most products are under-padded.** Touch targets
need ≥ 24×24 CSS px (WCAG 2.2 AA, 2.5.8) and want 44×44. That is
measurable — hold the line on it.

### Borders

`border-{side}-{width}` with widths 0/1(bare)/2/4/8, sides `t b l r x y`.
Styles `border-{solid,dashed,dotted,double,hidden,none}`. Per-side color:
`border-b-rule`.

**The v4 trap again: bare `border` draws in `currentColor`.** Any
`className="border rounded-lg p-4"` with no color class renders a border
in the text color. In a review, that is a confirmed defect with a
one-token fix.

Radius: `rounded-{none,xs,sm,md,lg,xl,2xl,3xl,4xl,full}` — note the v4
shift, and that `4xl` is new. Per-corner `rounded-tl-*` etc., per-side
`rounded-b-*`. Design call: **one radius per product, two at most**
(a container radius and a control radius). Uniform `rounded-xl` on
everything is on the AI-slop list; so is five different radii on one card.

Rings are box-shadow based, so they do not shift layout — which is exactly
why they are the right tool for focus. In v4, bare `ring` is 1px
`currentColor`; the v3 muscle-memory `ring` (3px blue) is now `ring-3
ring-blue-500`. `ring-inset`, `ring-offset-{n}`, `ring-offset-{color}`.

**Focus recipe for this stack:**
`focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-paper`.
`focus:outline-none` with no replacement is an automatic WCAG 2.4.7
failure and caps the score — see the hard rule in `SKILL.md`.

### Backgrounds, shadows, gradients

`bg-{color}` / `bg-{color}/{opacity}`.

Shadows: `shadow-{2xs,xs,sm,md,lg,xl,2xl,none}`, colorable via
`shadow-{color}` (and `shadow-black/5`), plus `inset-shadow-*` and
`drop-shadow-*`. Design call: elevation should be a **short, ordered set**
tied to meaning (resting card / raised menu / modal), not a per-component
guess. Tinting the shadow with the surface hue instead of pure black is
the single cheapest upgrade from stock-Tailwind to designed.

Gradients: `bg-linear-to-{t,tr,r,br,b,bl,l,tl}` or an angle
(`bg-linear-65`), plus `bg-radial`, `bg-radial-[at_50%_75%]`, `bg-conic`.
Stops `from-*` / `via-* `/ `to-*`, with positions (`from-10% via-30%
to-90%`) and interpolation modifiers (`/oklch`, `/srgb`, `/longer`).
`bg-none` clears.

**The indigo→purple 135° gradient is the single loudest AI-slop tell.**
If you see `bg-linear-to-br from-indigo-500 to-purple-600`, name it. A
gradient earns its place when it is doing depth or focus work, not when it
is decorating a hero.

`bg-clip-text text-transparent` over a gradient gives gradient text. Note
it inherits the gradient's contrast problems and screen readers are fine
but Windows High Contrast mode is not — use sparingly, never for body copy.

Background images: Tailwind gives you positioning, not the URL. In Next.js
the right answer for a content image is usually **`next/image`**, not a CSS
background — you get sizing, lazy loading, and no CLS. Reserve
`bg-[url(...)]` for genuine decoration. Positioning
(`bg-center`, `bg-top-left`, …), tiling (`bg-repeat`, `bg-repeat-x`,
`bg-no-repeat`, `bg-repeat-round`, `bg-repeat-space`), attachment
(`bg-fixed|local|scroll`), and clipping
(`bg-clip-{border,padding,content,text}`) all behave as the book says.
`bg-fixed` parallax is broken on iOS Safari and janky elsewhere — flag it.

Filters: `blur-{xs…3xl}`, `backdrop-blur-*`, `grayscale`, `sepia`,
`brightness-*`, `contrast-*`, `saturate-*`, `invert`, `hue-rotate-*`.
Backdrop blur on a large fixed surface is a real INP/paint cost on
low-end Android — worth a perf note when it wraps a scrolling region.

### Height and width

`w-{n}` / `h-{n}` on the same spacing scale, plus `-auto`, `-px`, `-full`,
`-screen`, `-min`, `-max`, `-fit`; fractions `w-1/2`, `w-7/12`, etc. Use
**`size-{n}`** when both match.

v4 additions worth knowing: `w-dvw` / `h-dvh` (and `svh`/`lvh`).
**`h-screen` on mobile is a bug** — it ignores the collapsing browser
chrome and produces a scroll jump. `h-dvh` is the fix. That is a
confirmed, reproducible finding, not taste.

`min-w-*` / `min-h-*` / `max-w-*` / `max-h-*` all take the full scale in
v4 (not the tiny v3 subset). `max-w-{xs…7xl}` (20rem → 80rem),
`max-w-prose` (65ch), `max-w-full`, `max-w-none`. `max-w-screen-*` is
**gone** — see §0.

`min-w-0` on a flex child is the fix for "my truncated text won't
truncate" — flex items default to `min-width: auto`. Pairs with
`truncate`.

### Visibility

`hidden` (`display:none`, out of layout) vs `invisible`
(`visibility:hidden`, keeps its space) vs `sr-only` (visually gone, still
announced). Three different meanings — using `hidden` for a screen-reader
label destroys it, and `opacity-0` alone leaves an invisible click target.
Getting this wrong is an accessibility finding, not a style one.

---

## 6 — Preflight, and the findings it generates

Preflight zeroes heading styles, list styles, margins, and border widths;
sets `border-style: solid` with a default color; makes images `display:
block`; and gives form controls sane bases.

Two v4 Preflight changes produce recurring, real findings:

1. **`button` gets `cursor: default`, not `cursor: pointer`.** Every
   button and `role="button"` in a v4 app feels dead on hover unless the
   project restored it. The fix belongs in `globals.css`, once:

   ```css
   @layer base {
     button:not(:disabled),
     [role="button"]:not(:disabled) { cursor: pointer; }
   }
   ```

   Check for this **before** writing N separate "missing `cursor-pointer`"
   findings — it is one root cause, one fix.

2. **Placeholders are `currentColor` at 50%.** On a muted-text input that
   can land under 4.5:1. Measure it.

Preflight also means `display: block` images — an inline icon or avatar
that suddenly breaks to its own line is this, and the fix is `inline-block`
or a flex parent, not a margin hack.

---

## 7 — Modifiers

`hover:`, `focus:`, `focus-visible:`, `focus-within:`, `active:`,
`disabled:`, `checked:`, `required:`, `invalid:`, `dark:`, `motion-safe:`,
`motion-reduce:`, `print:`, `first:`, `last:`, `odd:`, `even:`,
`group-*:`, `peer-*:`, `has-*:`, `not-*:`, `*:`, `starting:`, plus
breakpoints and `@container` variants. Stackable, and v4 reads them
**left to right**.

Judgment calls:
- **`hover:` alone is a bug on touch.** Anything that only reveals on
  hover is invisible on a phone. Pair with a focus state and check the
  touch path.
- **`focus:` vs `focus-visible:`.** Use `focus-visible:` for the ring so
  mouse users do not get a ring on click, but never remove `:focus`
  styling without a `focus-visible` replacement.
- **`motion-reduce:`** — any transform/opacity animation over ~200ms needs
  a reduced-motion path. WCAG 2.3.3. Measurable, hold the line.
- **`dark:`** — in v4, class-based dark mode is opt-in:
  `@custom-variant dark (&:where(.dark, .dark *));`. If a repo has `dark:`
  classes and no `@custom-variant`, they are following the OS only — often
  not what the theme toggle in the header implies. Check both.
- `group-has-*` and `peer-checked:` remove most of the JS people write for
  disclosure and custom-control styling. Suggest them when you see state
  mirrored into React purely for styling.

---

## 8 — Arbitrary values

`m-[104px]`, `text-[#34da33]`, `grid-cols-[max-content_auto]`, whole
properties `[mask-type:alpha]`, CSS vars `bg-(--brand)`.

The book's rule is the right one and gets sharper in a design review:
**an arbitrary value is a one-off escape hatch; a repeated arbitrary value
is a missing token.** Three occurrences of `text-[13px]` is a finding —
the fix is `@theme { --text-xs-plus: 0.8125rem; }`, not a fourth
occurrence. Grep for `-\[` when auditing a codebase's system health; the
density of arbitrary values is a decent proxy for whether a design system
actually exists.

---

## 9 — Review checklist (what to actually grep for)

Fast, high-yield sweep on any Tailwind v4 + Next.js codebase:

| Grep | Finding |
|---|---|
| `@tailwind ` | v3 directives; build is on the compat path or broken |
| `tailwind.config` | v3 config still authoritative; theme is not CSS-first |
| `bg-gradient-to-` | v3 gradient syntax, silently dead in v4 |
| `\bborder\b` without a `border-` color nearby | `currentColor` border |
| `focus:outline-none` / `outline-none` | removed focus indicator (WCAG 2.4.7) or v3 spelling |
| `h-screen` | mobile viewport bug; want `h-dvh` |
| `max-w-screen-` | removed in v4 |
| `!\w` prefix important | v3 important position |
| `text-\[|p-\[|m-\[` density | missing tokens |
| `text-(gray\|slate\|zinc)-` in components | no semantic token layer |
| `prose` without `dark:prose-invert` | dark-mode contrast failure |
| `cursor-pointer` repeated on buttons | missing the one Preflight base fix |
| class names built with `${` | classes that never generate |
| `clsx`/`cn` without `tailwind-merge` | conflicting classes resolved by Tailwind order, not author order |

---

## 10 — Page layout

### Container

Tailwind's `container` only sets `max-width` to the current breakpoint. It
does **not** center and does **not** pad. The real class list is
`container mx-auto px-6`.

In v4 there is no `container` config key. To customize it, override the
utility:

```css
@utility container {
  margin-inline: auto;
  padding-inline: --spacing(6);
}
```

**Design call:** most products want a *content* max-width, not a
breakpoint-stepped one. `max-w-6xl mx-auto px-6` gives a stable measure;
`container` snaps width at each breakpoint, which makes the layout jump.
Say which you mean. And viewport meta — `width=device-width,initial-scale=1`
— is handled by Next.js's `viewport` export; a missing one is a routing/
metadata finding, not a CSS one.

### Float, position, z-index

`float-left|right|none`, `clear-left|right|both|none`. Legacy only. If new
code uses floats for layout, that is a finding — grid or flex instead. The
one live use is wrapping text around a pull-quote or image.

`z-{0,10,20,30,40,50,auto}`, negatives `-z-10`, arbitrary `z-[60]`. v4
makes this scale dynamic, so `z-9999` compiles. That is worse, not better.

**Design call:** more than ~4 z-index values in a codebase means there is
no stacking system, and you will eventually get a dropdown behind a modal.
Name the layers in `DESIGN.md` (base / sticky header / dropdown / overlay /
toast) and map each to one value. Arbitrary `z-[9999]` is the symptom.

### Tables

`table-auto` / `table-fixed`, `border-collapse` / `border-separate`,
`border-spacing-*`. `odd:` / `even:` for zebra rows.

**Design calls that matter more than the utilities:**
- Use a real `<table>` for tabular data. A grid of divs loses row/column
  semantics for screen readers. This is an accessibility finding.
- Zebra striping is usually the wrong fix for a dense table — try
  `border-b border-rule` per row plus more vertical padding first. Tufte:
  maximize the data-ink ratio; stripes are ink that carries no data.
- Right-align numeric columns and use `tabular-nums` (`font-variant-numeric`)
  so digits line up. In a money table this is not optional.
- `table-fixed` plus explicit column widths is what makes long cell content
  truncate predictably instead of blowing out the layout.

### Grid

`grid`; `grid-cols-{1..12}` / `grid-cols-none`; `grid-rows-{1..12}`;
`grid-flow-row` / `grid-flow-col` (plus `-dense`); `gap-{n}` / `gap-x-{n}` /
`gap-y-{n}`. Placement: `col-span-{n}` / `row-span-{n}` (`-auto` resets),
`col-start-{n}` / `col-end-{n}` (end is **exclusive**), `row-start/end`.
Specify any two of start / end / span.

v4 makes the counts dynamic, so `grid-cols-15` works, and
`grid-cols-[repeat(auto-fill,minmax(16rem,1fr))]` is the idiom for a card
wall that reflows without breakpoints. Prefer that to three `md:`/`lg:`
column overrides when the cards have a natural minimum width.

### Columns (multi-column flow)

`columns-{1..12}` or `columns-{3xs…7xl}` (the book's `column-` is a typo —
the utility is plural), `columns-auto`, gap via `gap-*`, `break-inside-avoid`
on children.

Use for a masonry-ish photo wall or a long link list. **Do not use for body
copy** — reading order runs down column 1 then back up to column 2, which
means the reader scrolls down and back up on every screen. That is a
finding.

### Flexbox

Parent: `flex`, `flex-row|row-reverse|col|col-reverse` (the book's
`flex-column` is wrong — it is `flex-col`), `flex-wrap|wrap-reverse|nowrap`
(the book's `flex-no-wrap` is v1 syntax).

Children: `basis-{n|fraction|auto|full}`; `grow` / `grow-0`, `shrink` /
`shrink-0` (**v4 names** — `flex-grow-*` / `flex-shrink-*` are removed);
shorthands `flex-1`, `flex-auto`, `flex-initial`, `flex-none`.

The book's `flex-1` vs `flex-auto` distinction is the one worth keeping:
`flex-1` zeroes the basis so items come out **equal**; `flex-auto` starts
from intrinsic size so items stay **proportional to their content**. Equal
columns whose content is unequal is usually the bug.

`order-{1..12}`, `order-first|last|none`, negatives, arbitrary.

**The book's accessibility claim about `order-` is backwards and must not
be repeated.** It suggests reordering so a screen reader hits content
first. In practice `order-*` (and `flex-row-reverse`, and grid placement)
changes only the *visual* order — the DOM order is what keyboard focus and
screen readers follow. A visual order that disagrees with DOM order
produces a tab sequence that jumps around the page. WCAG 2.4.3 (Focus
Order) / 1.3.2 (Meaningful Sequence). **Fix the DOM order; do not fix it
with `order-`.** If you see `order-` used at a breakpoint to rearrange a
sidebar, tab through it before approving.

### Alignment

Main axis: `justify-start|end|center|between|around|evenly|stretch`;
per-item box `justify-items-*`, override `justify-self-*`.
Cross axis: `content-*` (align-content), `items-*` (align-items),
`self-*` (align-self). Both at once: `place-content-*`, `place-items-*`,
`place-self-*`.

Spacing distribution, stated once so a review can cite it: `between` →
`AxBxC`, `evenly` → `xAxBxCx`, `around` → `xAxxBxxCx` (end gaps look half
size). `justify-around` on a nav is the classic "why is the first item
closer to the edge" bug.

Centering: `flex items-center justify-center` or `grid place-items-center`.
The second is shorter and does not need a direction.

---

## 11 — Animation

Tailwind ships four keyframe animations: `animate-spin`, `animate-ping`,
`animate-pulse`, `animate-bounce`, reset with `animate-none`. v4 lets you
register your own as theme variables:

```css
@theme {
  --animate-fade-up: fade-up 300ms ease-out both;
  @keyframes fade-up { from { opacity: 0; translate: 0 8px } to { opacity: 1; translate: 0 0 } }
}
```

### Transitions

`transition` covers color, background-color, border-color, text-decoration-
color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter.
Narrower: `transition-colors`, `transition-opacity`, `transition-shadow`,
`transition-transform`, `transition-none`, `transition-all`.
(The book's `transition-color` singular is wrong.)

Duration `duration-{75,100,150,200,300,500,700,1000}`, delay `delay-*`,
easing `ease-linear|in|out|in-out|initial`, all arbitrary-friendly. Default
duration is 0 — **`hover:bg-x` with no `duration-*` does nothing gradual**,
which is the most common "why isn't my transition working" finding.

v4 adds `transition-discrete` and the `starting:` variant (`@starting-style`),
which is how you animate an element in from `display: none` — relevant for
popovers and `<dialog>` without a JS animation library.

### Transforms

`scale-{n}` / `scale-x-` / `scale-y-`, `rotate-{n}` / `-rotate-{n}`,
`skew-x-` / `skew-y-`, `translate-x-` / `translate-y-` (spacing scale plus
`px`, `full`, fractions), `origin-{center,top,bottom-right,…}`. v4 adds 3D:
`rotate-x-*`, `rotate-y-*`, `rotate-z-*`, `perspective-*`, `transform-3d`,
and these are individual CSS properties now — so reset with `scale-none`,
not `transform-none`.

### Motion: the design rules

This is where a review earns its keep, because the utilities are easy and
the judgment is not.

- **Duration.** UI feedback (hover, focus, small color change) 100–200ms.
  Element entering/leaving 200–300ms. Anything over ~400ms on a frequent
  interaction feels sluggish; over ~600ms it feels broken. A 1000ms
  `hover:scale-110` is a finding, not a flourish.
- **Easing.** `ease-linear` on anything spatial reads mechanical. Entering
  → `ease-out`. Leaving → `ease-in`. Moving between two on-screen states →
  `ease-in-out`. Default `ease` (`ease-in-out`) on everything is the
  stock-Tailwind tell.
- **Animate cheap properties.** `transform` and `opacity` are composited.
  Animating `width`, `height`, `top`, or `margin` triggers layout on every
  frame — a real INP/jank finding on a list.
- **`animate-pulse` is a skeleton, not a spinner.** Skeletons that do not
  match the shape of the content they replace cause a visible layout jump
  on load. Match the block sizes.
- **`animate-spin` goes on the SVG itself**, not a wrapper. With
  `lucide-react`: `<Loader2 className="size-4 animate-spin" aria-hidden />`
  plus a real `aria-live` / `role="status"` label — a spinning icon with no
  accessible name announces nothing.
- **`animate-ping` / `animate-bounce` are attention-grabbers.** One per
  screen, maximum, and only for something that genuinely needs attention.
  Two competing animations is an automatic finding.
- **Reduced motion is mandatory.** Wrap anything beyond a color fade:
  `motion-safe:transition-transform motion-safe:hover:scale-105`, or
  globally in `@layer base` with a `prefers-reduced-motion: reduce` block
  zeroing durations. WCAG 2.3.3. Measurable — hold the line.

### Cursor, selection, resize

`cursor-{auto,default,pointer,text,move,wait,not-allowed,grab,grabbing,…}`.
See §6 — in v4 you need `cursor-pointer` (or the base-layer restore) on
buttons or the whole app feels dead. `cursor-not-allowed` on a disabled
button is correct; on a `disabled` element it needs a wrapper, since
disabled elements do not fire pointer events.

`select-none` on UI chrome (button labels, nav) prevents ugly drag-select.
`select-all` on a copyable token/API key is one of the few genuinely good
uses — the book's blanket "please don't" is too broad; the real rule is
never on body content.

`resize` / `resize-x` / `resize-y` / `resize-none` (the book's `reset-none`
is a typo). **`resize-none` on a `<textarea>` is usually a finding** — you
took away a control the user wanted. v4's `field-sizing-content` is the
better answer: the textarea grows with its content.

---

## 12 — Responsive design

Breakpoints are **min-width and up**, mobile-first: unprefixed = all
widths, then `sm:` 40rem/640px, `md:` 48rem/768px, `lg:` 64rem/1024px,
`xl:` 80rem/1280px, `2xl:` 96rem/1536px. In v4 they live in the
`--breakpoint-*` theme namespace; add one with
`@theme { --breakpoint-3xl: 120rem; }`.

To scope a utility to a *range*, use the `max-*` variants (`max-md:hidden`)
or stack (`md:max-lg:flex`). The book only teaches "negate it at the next
breakpoint up" — that still works and is often clearer, but `max-*` exists
and reads better for one-off exceptions.

Stacking with other modifiers is fine and left-to-right in v4:
`md:hover:font-bold`.

### Patterns worth naming

- **Show/hide:** `hidden lg:block` (appears on desktop), `lg:hidden`
  (mobile-only, e.g. the hamburger). Note both **still render and still
  download** — `hidden` is CSS, not conditional rendering. Two full copies
  of a nav in the DOM is a duplicate-landmark and duplicate-`id`
  accessibility problem, and a payload problem if the hidden branch pulls
  images. Prefer one nav that reflows.
- **Type ramp:** `text-xl md:text-2xl lg:text-4xl`. Correct instinct;
  extract it into a component or a `@utility` once it appears three times.
  v4's `text-3xl/9` slash form keeps leading paired as it scales.
- **Card grid:** `grid gap-4 md:grid-cols-2 lg:grid-cols-4`. Set `gap-*`
  once on the parent instead of `mb-6 lg:mb-0` on children — the book's
  child-margin version is v3-era and produces a trailing gap.
- **Nav:** `hidden lg:flex lg:items-center`, with `divide-y lg:divide-y-0`
  for the stacked state.

### Where the book is dated, and it matters

1. **Container queries are usually the right tool now.** Breakpoints ask
   "how wide is the screen"; a component wants "how wide am I". A card that
   renders in a sidebar *and* a full-width page cannot be fixed with `md:`.
   Put `@container` on the wrapper and use `@sm:` / `@max-md:` on children.
   Core in v4, no plugin. This is the single biggest layout upgrade over
   the book.
2. **Icons come from `lucide-react`, not inline Heroicon SVG paths.** The
   book's hand-pasted hamburger/close `<path d="M4 6h16…">` is exactly the
   thing this repo bans. Use `<Menu className="size-5" aria-hidden />` and
   `<X className="size-5" aria-hidden />`.
3. **The vanilla-JS `classList.add("hidden")` toggle is wrong in React.**
   State drives the class list; do not mutate `classList`. And the book's
   version ships an inaccessible menu — a real disclosure needs
   `aria-expanded`, `aria-controls`, focus moved into the panel, `Escape`
   to close, and focus returned to the trigger. That gap is worth its own
   finding whenever you see a hand-rolled mobile menu.
4. **Test at 320px.** The book's device table starts at 360. 320px
   (iPhone SE) is still the practical floor, and it is where horizontal
   overflow shows up. Also test at 200% zoom — WCAG 1.4.10 reflow requires
   no horizontal scroll at 320 CSS px equivalent.
5. **Long class strings are a real cost.** When one element carries four
   breakpoint variants across six properties, that is the signal to extract
   a component or reach for a container query — not to keep typing.

---

## 13 — Customizing Tailwind

**Chapter 8 of the book is almost entirely obsolete.** Every mechanism it
teaches — `tailwind.config.js`, `theme.extend`, `content`, `safelist`,
`corePlugins`, `separator`, `resolveConfig`, `darkMode` — has been
replaced or removed. The *reasons* to customize are unchanged; the
machinery is different. Do not port any snippet from that chapter as-is.

### The whole-chapter translation

| v3 config key | v4 |
|---|---|
| `theme: { … }` (override) | `@theme { --color-*: initial; … }` — reset the namespace, then redefine |
| `theme.extend: { … }` | plain `@theme { … }` — v4 extends by default |
| `theme.screens` | `@theme { --breakpoint-3xl: 120rem; }` |
| `theme.colors` | `@theme { --color-brand-500: oklch(…); }` |
| `theme.spacing` | `@theme { --spacing: 0.25rem; }` (one variable drives the whole scale) |
| `theme.zIndex`, `theme.borderRadius`, … | namespaced vars: `--radius-*`, `--shadow-*`, `--ease-*`, `--animate-*`, `--text-*`, `--font-*`, `--tracking-*`, `--leading-*`, `--container-*`, `--blur-*`, `--perspective-*`, `--aspect-*` |
| `content: [...]` | automatic (respects `.gitignore`); `@source "../../packages/ui";` for anything outside the CSS file's package |
| `safelist: [...]` | `@source inline("{hover:,focus:,}bg-red-{50,{100..900..100},950}")` |
| blocklist | `@source not inline("…")`, `@source not "path"`, `@source none` |
| `corePlugins: { flex: false }` | **removed.** No replacement, and you did not want it |
| `prefix: "tw"` → `tw-flex` | `@import "tailwindcss" prefix(tw);` → **`tw:flex`**, `tw:hover:bg-x`. It is a variant-style prefix now, not a name prefix |
| `important: true` | `@import "tailwindcss" important;` |
| `separator: "--"` | **removed** |
| `darkMode: "media"` | built in — `dark:` follows `prefers-color-scheme` with no config |
| `darkMode: "class"` | `@custom-variant dark (&:where(.dark, .dark *));` |
| `plugins: [plugin(({addVariant}) => …)]` | `@custom-variant second-of-type (&:nth-of-type(2));` — or keep the JS plugin and load it with `@plugin "./my-plugin.js";` |
| `addUtilities` | `@utility big-bold-text { font-size: 1.5rem; font-weight: 700; }` |
| `matchUtilities` | `@utility tab-* { tab-size: --value(integer); }` |
| `addBase` | `@layer base { h4 { … } }` |
| `resolveConfig` in JS | **removed.** Theme values *are* CSS custom properties — read them with `getComputedStyle(el).getPropertyValue("--color-brand-500")`, or `@theme static` to force emission |

A legacy JS config can still be loaded with `@config "./tailwind.config.js";`.
Treat its presence as migration debt worth a finding, not a crime.

### What a v4 theme actually looks like

```css
@import "tailwindcss";
@plugin "@tailwindcss/typography";
@custom-variant dark (&:where(.dark, .dark *));

@theme {
  --font-sans: var(--font-inter), ui-sans-serif, system-ui, sans-serif;
  --color-brand-500: oklch(0.63 0.19 32);
  --breakpoint-3xl: 120rem;
  --radius-card: 0.75rem;
  --ease-out-quint: cubic-bezier(0.22, 1, 0.36, 1);
}
```

That single block generates `bg-brand-500`, `text-brand-500`,
`border-brand-500`, `ring-brand-500`, `from-brand-500`, `3xl:`,
`rounded-card`, `ease-out-quint` — every consumer of the namespace, for
free. **This is the strongest argument for the token layer**, and it is
what §4's "raw palette names are a finding" is really asking for.

To *replace* rather than extend a namespace, reset it first:
`@theme { --color-*: initial; --color-ink: …; }`. `--*: initial` nukes
the entire default theme — occasionally right for a tightly controlled
design system, usually overkill.

### Themes: the book's biggest miss

The book says "Tailwind's theme is the entire set of defaults, and there's
only one," and that real color themes need CSS variables plus `dark:`.
That was true in v3. In v4 the theme **is** CSS variables, so
multi-theme is first-class:

```css
@theme inline {
  --color-paper: var(--surface);
  --color-ink: var(--content);
}
:root      { --surface: oklch(0.99 0.005 90); --content: oklch(0.22 0.01 90); }
.dark      { --surface: oklch(0.19 0.01 260); --content: oklch(0.94 0.005 260); }
[data-theme="sepia"] { --surface: oklch(0.96 0.03 80); --content: oklch(0.28 0.04 60); }
```

`@theme inline` is load-bearing here: it inlines the variable reference so
`bg-paper` resolves `--surface` **at use time**, picking up whichever
ancestor scope is active. Without `inline`, the value is captured once at
`:root` and your theme switcher silently does nothing. That is a subtle,
high-cost bug and worth checking explicitly whenever a product has a theme
toggle.

Practical consequence: with this in place, `dark:` variants mostly stop
being necessary. A codebase carrying `bg-white dark:bg-gray-900
text-gray-900 dark:text-gray-100` on every element has no token layer —
`bg-paper text-ink` does the same job once. **Doubling every color class
with a `dark:` twin is a system-design finding**, and one of the more
valuable ones you can give, because it removes hundreds of classes and
kills a whole category of "someone forgot the dark variant" contrast bugs.

### Class detection — the failure mode to grep for

v4 auto-detects source files (honoring `.gitignore`), so the book's
`content` glob-maintenance problem is mostly gone. Two live traps remain:

1. **Monorepo / external packages.** Classes in `packages/ui` are not
   scanned from `apps/web/src/app/globals.css` unless you add
   `@source "../../../packages/ui/src";`. Symptom: a shared component
   renders unstyled *only in production*, because dev happened to have the
   class from somewhere else.
2. **Interpolated class names still do not work**, for exactly the reason
   the book gives — the scanner reads source as plain text. See §2. The
   escape hatch is `@source inline(...)`, but reach for the literal-string
   map first: a safelist ships CSS nobody uses, and it hides the problem
   instead of fixing it.

### Variants worth knowing beyond the book's list

The book's tour (`hover`, `focus`, `active`, `disabled`, `checked`,
`first`, `last`, `odd`, `even`, `empty`, `only`, `group-*`, `motion-safe`,
`motion-reduce`, `print`, `ltr`/`rtl`, `portrait`/`landscape`, `target`,
`visited`, `selection`, `marker`, `first-letter`, `first-line`,
`before`/`after`, and the form-state set) is still accurate. Additions
that change what you can build without JS:

- `has-*` — style a parent from its children: `has-[:checked]:border-accent`
  on a label wrapping a radio. Replaces most "mirror this into React state
  purely for styling" code.
- `not-*` — `not-hover:opacity-70`, `not-first:border-t`.
- `*:` and `**:` — style direct / all descendants: `*:not-first:mt-2`.
- `peer-*` — sibling-driven state (`peer-invalid:text-danger`), the correct
  tool for inline form validation messages.
- `@container` + `@sm:` / `@max-md:` — see §12.
- `starting:` — entry animations from `display:none`.
- `supports-[…]:` and arbitrary variants `[&_svg]:size-4` — the latter is
  how you style `lucide-react` icons inside a button variant without
  touching every call site.
- `nth-*`, `in-*`, `inert:`, `open:`, `popover-open:`.

`group-hover` on a touch device has the same problem as `hover:` — see
§12. And a `focus-within:` on a card is usually the accessible companion
to a `group-hover:` reveal.

### Legacy CSS integration

`prefix(tw)` and `important` are the two escape hatches, both unchanged in
intent. Both are **migration tools with a shelf life** — if a codebase has
shipped `@import "tailwindcss" important;` permanently, every utility now
outranks every deliberate override, and the next person to write a
one-off fix will not be able to. Flag it as debt with an owner, not as a
setting.

---

*Book fully digested: chapters 2–8 (Rappin, 2nd ed., 2022). Everything
above is restated for Tailwind 4.3 + Next.js App Router + React 19 +
`lucide-react`. The book's v3 syntax is preserved only in §0 and §13 as
"do not emit" reference.*
