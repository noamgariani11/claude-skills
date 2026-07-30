# Tailwind v4 — the always-load half

**Load this whenever a finding or a fix touches Tailwind class syntax**, which
is most of them on this stack. It is the small file on purpose: the correction
table, the fix table and the grep sweep are needed at fix time on nearly every
run, and `tailwind.md` (the full craft reference — measure, scale, layout,
motion, theming) is a deep read you should pull only when the question is
actually about one of those.

The stack this skill reviews is **Tailwind v4.3.x + Next.js App Router +
React 19 + pnpm + `lucide-react`**.

**Currency:** verified 2026-07-30 against tailwindcss.com. Latest release
4.3.3 (4.3 shipped 2026-05-08). Re-verify before asserting a version-specific
claim older than ~6 months.

**Check the version before writing a single class:** `pnpm ls tailwindcss`, or
the shape of the CSS entry file (`@import "tailwindcss"` = v4, `@tailwind base`
= v3). A fix written in v3 syntax against a v4 build silently does nothing,
which is worse than no fix — it consumes a finding ID and looks like progress.

---

## 1 — The v3 → v4 correction table

The single highest-value table in the skill. Emitting v3 syntax in a fix is a
real defect, not a style quibble — most of these silently do nothing.

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


## 2 — Review checklist (what to actually grep for)

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


## 3 — Fixing correctly (read before the Mode D/F fix loop)

A fix that resolves the finding and introduces a quieter one is worse than no
fix, because it also consumes the finding's ID and looks like progress. These
are the ones where the obvious Tailwind fix is the wrong one.

| Finding | The plausible fix | Why it is wrong | Correct |
|---|---|---|---|
| Focus ring missing / removed | add `focus:border-2 border-accent` | borders occupy layout, so focusing shifts the element by 2px — a new CLS defect on every tab press | `focus-visible:ring-2 ring-accent ring-offset-2` — rings are box-shadow, zero layout cost |
| Elements too cramped | add `mb-4` to each child | reintroduces the trailing gap and margin-collapse; breaks the moment one child is conditionally rendered | `gap-4` on the flex/grid parent — one class, no last-child case |
| Heading collides on mobile | `leading-tight` alongside `text-6xl` | fixes the symptom, leaves the pairing split across two tokens that drift | `text-6xl/tight` — leading stays welded to the size |
| Full-height section jumps on mobile | `h-screen` (or `min-h-screen`) | `vh` ignores collapsing browser chrome; this *is* the bug | `h-dvh` / `min-h-dvh` |
| Long text overflows a flex row | `truncate` | flex items default `min-width:auto`, so it will not shrink and will not truncate | `min-w-0 truncate` on the flex child |
| Hide on mobile | `hidden md:block` on a second copy | ships both copies to the DOM — duplicate landmarks, duplicate `id`s, both payloads | one element that reflows; if genuinely two, only one may carry the landmark/`id` |
| Hide but keep for screen readers | `hidden` | `display:none` removes it from the a11y tree entirely | `sr-only` |
| Hide but keep the space | `opacity-0` | leaves a live, invisible click target | `invisible` |
| Animation feels janky | shorten the `duration-*` | the cost is the property, not the time — `width`/`height`/`top` relayout every frame | animate `transform` / `opacity` (`translate-x-*`, `scale-*`) |
| Buttons feel dead on hover | add `cursor-pointer` to each button | N edits for one root cause; the next button ships wrong too | one `@layer base` rule restoring `button:not(:disabled){cursor:pointer}` — see `tailwind.md` §6 |
| Colour is inconsistent across pages | fix the hex at each call site | the next page repeats it; the cascade is unbounded | change the `@theme` variable — every `bg-`/`text-`/`border-`/`ring-` consumer updates at once |
| Dark mode contrast fails | add a `dark:` twin to the failing class | one of N; the class after it will be forgotten too | scoped vars + `@theme inline` so the token resolves per theme (`tailwind.md` §13) |
| One-off size needed | `text-[13px]` | fine once, a missing token by the third use | third occurrence → `@theme { --text-xs-plus: … }` |

Two rules that follow from the table and are worth stating on their own:

- **Prefer the token fix, then the base-layer fix, then the call-site fix.**
  That ordering is also what keeps a fix inside Mode D's stop conditions — a
  `@theme` edit is one file, where the call-site version is the "single fix
  touches more than 3 component files" trigger. When a token fix would exceed
  10 consumers, that is the documented stop-and-ask, not a reason to fan out.
- **Re-probe after a token fix specifically.** It is the one class of fix whose
  blast radius exceeds what you looked at, and the anti-inflation rule
  ("a grade may not improve without fresh evidence") exists for exactly this.

---

---

## Everything else

`tailwind.md` holds the rest of the craft reference: why utilities are
defensible, `@apply` discipline, the type/measure rules, colour and opacity,
the box model, Preflight in detail, modifiers, arbitrary values, page layout,
animation, responsive design and theme customization. Load it when the question
is about one of those rather than about syntax.
