# Component craft

Load this whenever a finding touches a specific control: buttons, links,
inputs, selects, menus, tooltips, modals, toasts, tabs, tables, scrollbars,
cards, badges, nav. Also load it before grading **Interaction & Performance**
or **Craft**, because those two pillars are mostly the sum of what is on this
page.

The rest of this skill grades systems. This file grades *things you click*.
That is where "designed" and "assembled" actually diverge, and it is the layer
generated UI gets wrong most reliably: the system looks fine in the token file
and then every control is a default.

**How to use it.** Each section has a **spec** (what an A looks like), the
**tells** (what to look for), and the **verdict rule** (what severity it
carries). Do not report a section as a finding because the spec has an item the
target lacks; report it when the tell is present and the verdict rule fires.
Read `scoring.md` -> "Things this rubric does NOT dock for" first. Restraint is
not a defect, and a control that is plain on purpose is not the same as a
control nobody thought about.

---

## 0. The seven states, and the two nobody designs

Every interactive element has seven states. Six are cheap and one is
forgotten:

| State | The rule | Usually missing? |
|---|---|---|
| **rest** | The default. Reads as interactive without being loud. | no |
| **hover** | A change the eye can see at a glance, on pointer devices only. | no |
| **focus-visible** | A ring that clears 3:1 against **both** the control and the page behind it. | often |
| **active / pressed** | Something moves or darkens within 100ms of pointerdown. | **usually** |
| **disabled** | Reads unavailable without going invisible, and explains itself. | often |
| **loading** | The control keeps its width, the label survives, the click is blocked. | **usually** |
| **error / invalid** | Names the field and the fix, and is not carried by red alone. | often |

**Active and loading are the two that separate a designed control from a
styled one.** A button with no pressed state feels dead on touch, where there
is no hover to confirm the tap landed. A submit button with no loading state
gets double-clicked, and double-submits are a data bug wearing a design
costume.

The probe measures state-rule coverage by matching stylesheet rules. Coverage
under ~60% on interactive elements is a **major** finding on Interaction; zero
`:active` rules anywhere is a **major** on its own, because it means nobody
went past the defaults.

**Disabled needs a reason.** A greyed-out button with no explanation is a dead
end. Either say why in adjacent text, or keep the button live and explain on
click. Never rely on a `title` attribute to carry it (see Tooltips).

### Hover is graded on what it paints, not on whether a rule exists

Rule coverage is a proxy, and it has a blind spot big enough to drive a
component through. Five ways a hover state passes coverage and fails a user:

1. **The fill is the colour already behind it.** `hover:bg-surface-sunken` on a
   section whose background *is* `surface-sunken`. Nothing happens. This is
   overwhelmingly a **shared-component** bug: the tint was chosen against the
   one background the author had on screen, and the component also renders on
   another. A component that lands on more than one surface needs a tint that
   is a step from *every* surface it lands on - which usually means a tinted
   accent wash rather than a neighbouring grey.
   *(measured: `states.inertHoverFills`, WCAG ratio of hovered fill vs rest
   fill, below 1.02)*
2. **The fill has nowhere to sit.** A full-width row with `padding-inline: 0`
   paints a band that starts at the first glyph and ends at the last. It looks
   like a rendering artefact, not a row. Give the row inline padding and pay it
   back on the list with a negative margin, so the text keeps its alignment
   with the heading above and only the band and the rule extend.
   *(measured: `states.hoverFillsWithoutPadding`)*
3. **The fill covers less than the hit area.** If the whole row is the anchor,
   the whole row is what must light up. A tint narrower than the clickable box
   teaches the wrong target.
4. **The fill and the row's separator are painted on the same box.** A
   background paints *under* its own border, so `border-t` plus `hover:bg-*` on
   one element means hovering erases the hairline and the band's top edge lands
   exactly where the previous row ended. It reads as the highlight crowding the
   row above rather than sitting inside its own. Put the rule on the row and
   the tint on a child with a small block margin and a radius: same width,
   separated by air. (In a table, a fill covering the row rule is the
   convention and is not a defect.)
   *(measured: `states.hoverFillsCoveringOwnRule`, scoped to a border on one
   horizontal edge with no vertical sides, so a bordered card that tints on
   hover never fires)*
5. **The fill crowds the text vertically.** Same defect as 2, one axis over.
   *(measured with 2: ink at least 8px from the fill's inline edges, 6px from
   its block edges)*

A sixth, which is not about the fill: **the tint moves hue without moving
lightness.** A cool wash over a warm neutral at the same lightness is a real
change on a good screen and no change at all in greyscale, on a cheap panel,
or for a colour vision deficiency in that axis.
*(measured: `states.hueOnlyHoverFills`)* Its sibling on the border:
`border-line hover:border-line` re-declares the colour already there.
*(measured: `states.inertHoverBorders`)*

**So: hover every repeated component before grading Interaction.** The probe
computes most of these from the CSS, and every one of them is invisible in an
ordinary screenshot - a screenshot is taken with no pointer over anything.
Every check in this section was added *after* a human hovered something and
said "that's wrong", which is the honest description of what the pass is for.
One `browser_hover` plus one screenshot of the CONTAINER (not the element -
the defect is usually the relationship to its neighbours) per repeated
row/card/nav-item is the whole cost, and it is not optional on a Mode D or
Mode F run. Protocol: `browser-verification.md`.

---

## 1. Buttons

The single most-graded control, and the one where AI-authored UI is most
uniform.

### Spec

- **A hierarchy of exactly three, plus destructive.** Primary (solid fill),
  secondary (outline or tonal), tertiary/quiet (text-only). More than three
  weights and none of them mean anything. Destructive is its own axis, not a
  fourth weight.
- **One primary per surface.** Two solid accent buttons side by side is a
  hierarchy failure, not a button failure, but it shows up here first.
- **Sizes on the scale**, typically 3: sm 32px, md 40px, lg 48px height. Every
  size keeps the same corner radius family and the same label ramp. A button
  whose height is not on the spacing scale is a craft tell.
- **Horizontal padding beats vertical.** Roughly 1.75x to 2.5x the vertical.
  Equal padding all round reads like a `<div>` someone added a background to.
- **Label is a verb.** "Save changes", not "Submit". Sentence case unless the
  brand is committed to something else. Never truncate a button label.
- **Icons are optically centered**, sized 1em to 1.25em against the label, with
  a gap of 6-8px, and given `aria-hidden` when the label already says it. An
  icon-only button gets an accessible name and a tooltip.
- **Minimum target 44x44 on touch** (Fitts), and never below the WCAG 2.2 SC
  2.5.8 floor of 24x24 including spacing. A 28px-tall text button is fine on a
  desktop toolbar and wrong as a mobile primary. Grow the hit area with padding
  or a pseudo-element rather than growing the visual box.
- **Loading keeps the width.** Swap the label for a spinner plus the same
  label, or reserve the width. A button that shrinks to a spinner shifts the
  layout under the user's finger.
- **Cursor is `pointer` on anything clickable.** On Tailwind v4 this is not
  automatic: Preflight sets `cursor: default` on `button`, so a project that
  never restored it has a *single root cause* and a one-line fix, not N
  findings. Check `tailwind.md` before writing this up as many.

### Tells

- All buttons the same fill, so the eye cannot rank them.
- `rounded-xl` or `rounded-full` on everything, including a dense toolbar.
- A gradient fill on the primary. Gradient buttons date a product instantly and
  make the label harder to keep at 4.5:1 across the sweep.
- A glow or coloured drop-shadow under the primary ("aura button").
- Uppercase micro-labels with heavy letter-spacing used as the button voice.
- The secondary button is a *lighter tint of the accent*, which puts two accent
  weights next to each other and kills the primary's Von Restorff advantage.
  Secondary should be neutral.
- Buttons and links used interchangeably. A button does a thing; a link goes
  somewhere. `<a>` styled as a button is fine; `<div onclick>` is not, ever.

### Verdict rule

Label contrast below 4.5:1, or a hit area under 24x24, is **critical** (WCAG).
Missing focus-visible is **critical**. No `:active` state, or no loading state
on a mutating button, is **major**. Radius or size drift is **minor** unless it
is the whole system, in which case it is one **major** on Craft.

---

## 2. Links and text-level interaction

### Spec

- **In body copy, links are underlined.** Colour alone is a WCAG 1.4.1 failure
  unless the link clears 3:1 against the surrounding text as well as the
  background, which almost nothing does. Underline offset 2-3px, thickness
  matched to the stroke, `text-decoration-skip-ink: auto`.
- **In nav and UI chrome, links may drop the underline**, because position and
  grouping already say "interactive". Bring it back on hover.
- Visited state matters on content sites and nowhere else. Do not dock a
  product app for missing `:visited`.
- **External links say so** if leaving is consequential, and never open a new
  tab silently for ordinary navigation.
- Link text is the destination. "Read the deployment runbook", never "click
  here" or a bare URL in prose.

### Tells

Underline removed globally in the reset and never restored. Link colour that is
the body colour plus 10% chroma. A whole paragraph as one link. Hit areas under
24px on stacked footer links, which is where small-target failures cluster.

### Verdict rule

Colour-only links in body copy: **critical** (1.4.1). Everything else here is
**minor** to **major** by density.

---

## 3. Inputs, textareas, and form fields

### Spec

- **The border carries 3:1** against the surface (WCAG 1.4.11). This is the
  single most common real failure in otherwise-clean design systems, because
  hairline borders are chosen for looks and land at 1.5:1.
- **A visible label, above the field, always.** Placeholder-as-label fails the
  moment the user types and fails permanently for anyone using zoom or a screen
  reader. Floating labels are acceptable when the resting position is legible
  and the animation honours reduced motion.
- **Placeholder is an example, not an instruction.** `MM/DD/YYYY` yes,
  "Enter your date of birth" no.
- **Help text sits under the field before the error**, and does not vanish when
  the error appears. If it disappears, the user loses the format rule at
  exactly the moment they need it.
- **Errors name the field and the fix**, sit adjacent to the field, are
  associated with `aria-describedby`, and are not carried by red alone: add an
  icon or the word.
- **Field height matches button height** on the same row. A 40px input beside a
  36px button is the most visible 4px in UI design.
- **Autofill is styled.** Chrome's yellow autofill background overrides your
  surface token and frequently drops the text to an unreadable pairing in dark
  mode. Set `-webkit-autofill` colours or `color-scheme`.
- **Numeric inputs use tabular numerals** and right-align when they sit in a
  column of numbers.
- Required and optional: mark whichever is rarer, and say which convention in
  the form header. An asterisk with no legend is not a label.

### Tells

Placeholder-only labels. Red border with no message. Native validation bubbles
left on (`novalidate` absent plus no custom messaging) so the browser's own
tooltip is the error UI. Inputs with `outline: none` and no replacement.
`disabled` fields used where `readonly` is meant, which drops them out of the
tab order and out of copy-paste.

### Verdict rule

Border under 3:1, or focus removed, or label absent: **critical**. Placeholder
as the only label: **critical** (it is a 3.3.2 failure). Help-text-replaced-by-
error: **major**. Height mismatch: **minor**, but a systemic one is **major** on
Craft.

---

## 4. Selects, dropdowns, menus, and comboboxes

Four different controls that AI-authored UI treats as one. Getting the choice
right matters more than the styling.

| Control | Use when | Do not |
|---|---|---|
| **native `<select>`** | 2-15 options, plain text labels, mobile matters | Use for multi-select or rich rows |
| **custom listbox** | options need icons, descriptions, or grouping | Reach for it because the native one "looks bad" |
| **menu** (actions) | the items *do* things | Use a `<select>` for actions |
| **combobox** | the list is long enough that typing beats scrolling | Ship without keyboard filtering |

### The native select is not a defect, but "untouched" is

`scoring.md` correctly refuses to dock for choosing a native `<select>`, and
that stands: it wins on mobile and with assistive tech. What it does **not**
excuse is leaving it visually unrelated to the rest of the form. A native
select still has to:

- share the field height, radius, font, and **3:1 border** with its sibling
  inputs;
- carry the same focus ring;
- have `appearance: none` plus **your own chevron** if you removed the native
  one, positioned with enough right padding that a long option label never runs
  under it (this is the classic tell: text overlapping the arrow);
- inherit `color-scheme` so the **option popup** is not a white OS panel
  dropping out of a dark app. This is the one that gets missed, because the
  popup is drawn by the OS and never appears in a screenshot of the page.

A select that keeps the native chevron and matches the form otherwise is
**correct and gets no finding**. A select that is `appearance: none` with no
replacement chevron is a **major**: you removed the affordance.

### Custom dropdowns: the bar is higher, because you took on the work

- Opens on click, not hover.
- **Full keyboard**: Up/Down move, Home/End jump, typeahead selects, Enter
  commits, Escape closes and **returns focus to the trigger**.
- Correct roles (`listbox`/`option` or `menu`/`menuitem`), `aria-expanded` on
  the trigger, `aria-activedescendant` or roving tabindex.
- **Positioned so it never clips**: flips above when the viewport bottom is
  close, shifts horizontally rather than overflowing, and scrolls internally
  past ~8 items with a maximum height on the scroll container.
- Selected and hovered are **two different treatments**. A checkmark plus a
  tint for selected, a background shift for hovered. If both are the same
  tint, a keyboard user cannot tell where they are.
- The panel has its own elevation, and its radius is the *inner* radius, not
  the same value as the card behind it (nested radius: inner = outer minus the
  padding, or it looks pinched).
- Closes on outside click, Escape, and scroll of an ancestor.

### Tells

Hover-opened menus that close before the pointer arrives (the diagonal problem;
either add an intent triangle or open on click). Dropdown panels rendered
inside an `overflow: hidden` ancestor and clipped. A menu that traps focus with
no Escape. Options at 13px with 6px of vertical padding, so every row is a
24px target. Two panels of different widths for the same control.

### Verdict rule

No keyboard operation, or focus not returned on close: **critical**. Clipped
panel, missing chevron after `appearance: none`, selected and hover
indistinguishable: **major**. Width or elevation drift between menus:
**minor**.

---

## 5. Checkboxes, radios, and switches

### Spec

- **Semantics first**: a real `<input type="checkbox">` under an
  `appearance: none` skin, or a fully-implemented ARIA widget. Never a `<div>`
  with a click handler, which is the pattern that most often *looks* right and
  is completely unusable by keyboard.
- The **label is part of the target**. Wrap it or use `for`. A 16px box with a
  20-character label beside it that is not clickable is a 16px target.
- The box itself is 16-20px, the *hit area* is 24px minimum and 44px on touch.
- Unchecked has a **3:1 border**. This is the same failure as inputs and it is
  everywhere: a light grey unchecked box on white is invisible to a lot of
  people.
- Checked state is not carried by colour alone: the checkmark or dot is the
  signal, colour is the reinforcement.
- **Indeterminate** exists on any tree or select-all.
- **Radio versus checkbox versus switch is a semantic call, not a style call.**
  Radios are one-of-many and need a `fieldset`/`legend`. A switch takes effect
  immediately; a checkbox waits for submit. A switch inside a form with a Save
  button is a lie about when the change happens.
- Switches need a state that is legible without colour: a knob position plus
  optionally a label. Red/green switches are unusable for a meaningful slice of
  users.

### Verdict rule

Non-semantic implementation without full ARIA and keyboard: **critical**.
Label not clickable, unchecked border under 3:1: **major**. Switch/checkbox
mismatch with commit timing: **major**, because it misleads.

---

## 6. Tooltips, hover cards, and popovers

The user called these "hover boxes", and they are one of the most reliable
tells of unfinished UI.

### The native `title` attribute is not a tooltip

`title` renders the OS box: slow to appear, unstyled, invisible on touch,
unreachable by keyboard, and it disappears while you are reading it. If a
product's hover help is `title`, **that is a finding**, and it is usually
systemic (one component, N instances, one fix).

This is a **design/interaction finding, not a WCAG 1.4.13 conformance
failure**. That criterion explicitly exempts additional content controlled by
the user agent and names HTML `title` tooltips as the example. A custom tooltip
is author-controlled and does owe the three 1.4.13 behaviours below; do not use
the native tooltip's poor UX to trigger the WCAG hard cap.

**Three exceptions, all real, all of which will show up in a grep:**

- `title` on an `<iframe>`, or as a supplementary label on a control that
  already has a visible accessible name. Correct markup.
- `title` repeating the element's own visible text. Redundant, not a defect.
- **`truncate` (or `text-overflow: ellipsis`) paired with `title={fullValue}`.**
  This is the conventional way to expose text the layout had to cut, it is what
  users expect from a truncated cell, and every alternative costs more than it
  buys. A dense table will have dozens of these and **none of them are
  findings.** Measured on a real product, this pattern was two thirds of every
  `title` in the codebase.

Judge the *rendered black box carrying information nothing else carries*, not
the attribute. If the tooltip is the only place a fact exists, that is the
finding; if it is a longer version of a fact already on screen, it is not.

### Spec for a real tooltip

- Appears after ~150-500ms hover, immediately on keyboard focus, and stays
  while the pointer travels toward it (SC 1.4.13 Content on Hover or Focus:
  **hoverable, dismissable with Escape, and persistent**).
- Carries **supplementary** text only. Anything essential, anything
  interactive, and anything long belongs in the page or in a popover. A tooltip
  with a link in it is a bug: you cannot reach the link.
- Maximum ~200-320px wide, 2 lines is the target, sentence case, no period on a
  fragment.
- Its own elevation and a small arrow that actually points at the trigger's
  centre. Flips at viewport edges.
- Contrast: many systems invert the tooltip (dark box in a light theme). That
  is fine and often good, but it has to clear 4.5:1 *in both themes*, and the
  inverted box in dark mode is the pairing that quietly fails.
- Never on a touch-only affordance. If the information is only available on
  hover, it does not exist on a phone.

### Hover cards and popovers

- Hover cards are for *preview*, open on intent (hover with delay plus a safe
  triangle), and must also be reachable by focus.
- Popovers are for *interaction*, open on click, take focus, close on Escape,
  and return focus. Use the platform `popover` attribute and the top layer where
  available so the panel cannot be clipped or z-index-fought.
- Neither should animate on `prefers-reduced-motion: reduce` beyond an opacity
  fade.

### Verdict rule

`title`-attribute tooltips carrying real information: **major** (and
**critical** if it is the only way to get the information). Not dismissable or
not hoverable: **critical** (1.4.13). Hover-only content with no focus
equivalent: **critical**. Arrow misalignment, width drift: **minor**.

---

## 7. Scrollbars and scroll regions

`scoring.md` says an unstyled scrollbar is a preference, not a defect. That
stands. But three things in this area *are* defects, and they are what the user
actually notices:

1. **A light OS scrollbar in a dark theme.** Caused by not declaring
   `color-scheme: dark` (or `light dark`) on `:root`. One line, and it also
   fixes native form controls, the `<select>` popup, autofill colours, and the
   spinner buttons. Not declaring `color-scheme` in a product with a dark theme
   is a **major** finding with a one-line fix, and it is the single highest
   value-per-character change in this entire file.
2. **A hidden scrollbar on a scrollable region.** `scrollbar-width: none` or
   `::-webkit-scrollbar { display: none }` on a region the user must scroll
   removes the only affordance saying more content exists, and it removes a
   pointer-only user's ability to drag it. **Major.** If the design needs the
   chrome gone, use an overlay scrollbar that appears on hover *and* keep a
   visible edge fade or a "more" affordance.
3. **Layout shift when the scrollbar appears.** A page that jumps horizontally
   between a short and a tall route. Fix with `scrollbar-gutter: stable`.
   **Minor** alone, **major** if it shifts a fixed header or a modal.

### If you do style them

`scrollbar-color: <thumb> <track>` is the standard property and now covers the
field; `::-webkit-scrollbar` remains for finer control. Thumb at least 8px
wide, at least 3:1 against its track, a hover state, and a radius that belongs
to the system. Never style the scrollbar so it is invisible until hover on a
region whose scrollability is not otherwise obvious.

### Scroll regions generally

- A horizontally-scrolling table needs a visible cue: a shadow on the pinned
  column, a fade at the edge, or a scrollbar. Silent horizontal scroll is a
  discoverability failure.
- `overflow: hidden` on `body` to "fix" a layout is a **major**: it breaks
  keyboard scrolling and traps zoom users.
- Sticky headers inside scroll regions must not obscure the focused element
  (SC 2.4.11 Focus Not Obscured). Add `scroll-margin-top`.

---

## 8. Modals, dialogs, drawers, and sheets

### Spec

- Focus moves in on open, is **trapped**, and returns to the trigger on close.
  Escape closes. Background does not scroll. Use `<dialog>` and the top layer
  unless there is a reason not to.
- The title is the first thing a screen reader hears (`aria-labelledby`) and it
  names the decision, not the feature.
- **Buttons in one order across the whole product.** Pick platform order and
  keep it. Destructive confirmations put the safe action as the visual default
  and name the destructive verb ("Delete 3 properties", not "OK").
- The backdrop is a scrim with enough opacity to actually recede (typically
  0.4-0.6 in light, lower in dark plus a blur if the system uses one). A 0.1
  scrim reads as a rendering bug.
- Sized to content with a max height, and the body scrolls, not the whole
  dialog. Header and footer stay put.
- On small screens, a full-height sheet is usually right; a 640px modal
  squeezed into 360px is not responsive design.

### Tells

Nested modals. A modal for something that should be a page. A destructive
confirm that is both silent and instant elsewhere in the same product, so the
convention is not a convention. Close-only-by-X with no Escape.

### Verdict rule

No focus trap or no focus return: **critical**. Background scrolls behind:
**major**. Inconsistent button order across surfaces: **major** on Craft, and
it is a real error source, not a nit.

---

## 9. Toasts, banners, and inline feedback

- **Match the channel to the consequence.** Transient success goes in a toast.
  An error the user must act on goes inline, next to the thing. An error that
  blocks the page goes in a banner. An error in a toast that disappears after
  4 seconds is a design failure that reads as a backend failure.
- Toasts need `role="status"` (polite) or `role="alert"` (assertive, sparingly),
  a minimum life proportional to the reading time, and a pause on hover or
  focus. WCAG 2.2 SC 2.2.1: anything auto-dismissing that carries essential
  information needs a way to extend it.
- Stack with a maximum of about 3, then collapse. Never cover the primary
  action or the element that caused them.
- Semantic colour is the reinforcement; the icon and the words are the signal.
- **Undo beats confirm** for reversible destructive actions. A toast with Undo
  is better design than a modal asking "are you sure".

---

## 10. Tabs, accordions, and disclosure

- Tabs are for peer views of the same object, never for a sequence (that is a
  stepper) and never for unrelated pages (that is nav).
- Full keyboard: arrows move between tabs, Tab moves into the panel. Selected
  tab is not indicated by colour alone: an underline or a filled pill.
- The selected tab must survive a refresh if the tab is addressable. Tabs that
  lose state on reload are an IA finding.
- Accordions: the whole header row is the target, the chevron rotates rather
  than swapping glyphs, `aria-expanded` is on the button, and the animation is
  height-safe. Do not put the only copy of critical information behind one.
- Never nest an accordion inside an accordion.

---

## 11. Tables and data density

Covered in depth in `enterprise.md`; the component-level rules:

- **Tabular numerals in every numeric column**, right-aligned, decimals
  aligned, units in the header rather than repeated in every cell.
- Row height is a decision: 40-56px for scannable, 32-36px for dense. Not 72px
  of air, and not 28px because it fit.
- Header is sticky; ambiguous, large, row+column, or spanning header structures
  use `scope` (or `headers`/`id` for multi-level relationships), while a small
  one-direction table may rely on `<th>` alone. Sortable headers expose `aria-sort`
  plus a visible arrow with a **deterministic tie-break**.
- **Hover and selected are different treatments**, and the selected tint must
  survive on top of the zebra tint if there is one. Test the three-way overlap:
  zebra + hover + selected.
- Row actions: visible on hover is acceptable on desktop only if the same
  actions are reachable another way (keyboard focus reveals them, or a row menu
  that is always present). Hover-only row actions are a **critical**
  accessibility finding on touch.
- Empty, loading, error, and filtered-to-empty are **four different states**
  with four different messages. "No data" for a filter that matched nothing is
  the most common wrong answer; say "No properties match these filters" and
  offer to clear them.

---

## 12. Cards, badges, chips, and avatars

- A card needs a reason to be a card. A card is a boundary around something
  that could stand alone. A grid of cards each containing one line of text is a
  list with extra borders.
- One elevation strategy per product: border, or shadow, or tint. Picking all
  three per component is the "assembled" tell.
- **Nested radius**: inner radius = outer radius minus the gap. Equal radii on
  nested boxes look pinched at the corners.
- Whole-card links: use one real anchor with a stretched pseudo-element rather
  than wrapping everything, so text stays selectable and nested controls still
  work.
- Badges and chips carry meaning: they need a text label, not just a colour
  dot, and they need to be distinguishable from buttons. A chip that looks like
  a button but is not clickable is a mapping failure.
- Avatars need an initials fallback that derives colour deterministically from
  the id, not randomly per render, and the initials must clear 4.5:1 on every
  generated background. Randomly-tinted avatar backgrounds are the most common
  place a design system ships an untested contrast pairing.

---

## 12b. Rows: lists, catalogues, and the whole-row link

A rule-separated list of rows is the honest alternative to a grid of cards, and
it is where AI-authored UI most often gets the *composition* right and the
*craft* wrong. The spec:

- **One anchor per row, and the row is the anchor.** Not the title. The
  accessible name is then the row's content, which is why the row must not also
  contain six repetitions of "Learn more" - a screen-reader user gets a list of
  identically-named links, and a sighted user gets a CTA competing with the row
  it sits inside. If the row is clickable, one arrow or chevron carries it.
- **The hover fill covers the whole row, with margins.** See §0 above.
- **The rule and the fill agree in width, and disagree in box.** One width for
  both, so the column reads as one thing - a hairline at content width with a
  tint 16px wider (or the reverse) reads as a mistake even when nobody can say
  why. But they must not be the same ELEMENT: the rule belongs to the row, the
  tint to a child inside it with ~6px of block margin and a radius. That gap is
  what turns a slab that starts where the last row ended into a highlight that
  sits inside its own row.
- **The left rail is a column, and it holds something that earns it.** An icon
  at text weight, a thumbnail, a date. Not an ordinal, unless the order is real
  (see `scoring.md` slop 23).
- **Rows in a two-column grid share a baseline.** CSS grid rows sync
  automatically; a flex-wrap fake does not, and the rules stop lining up across
  the gutter the moment one tagline wraps.
- **Nothing inside the row is separately focusable** unless it is a genuinely
  separate action. A nested link inside a row link is a keyboard trap of the
  boring kind: two tab stops that go to the same place.
- **On mobile the row goes full-bleed or it does not.** Half-bleed - a tint
  that reaches one edge and stops 4px short of the other - is the tell that
  the negative margin was guessed rather than derived from the container's
  padding.

---

## 13. Navigation and chrome

- The current location is visible in the nav at every level, and not by colour
  alone.
- A nav item's target is the whole row or tab, not the text.
- Icon-only nav needs labels on hover **and** an accessible name, and should be
  expandable. Icon-only rails without labels fail recognition-over-recall
  (Nielsen) for anyone who is not a daily user.
- A visible-on-focus skip link is the first focusable element on pages with a
  large repeated header. It is cheap and helps mainstream keyboard users, but
  its absence is not automatically WCAG 2.4.1: correctly structured headings
  or landmarks are also sufficient bypass mechanisms.
- Breadcrumbs use the real hierarchy, not the history.
- The mobile menu is reachable by keyboard, traps focus while open, and closes
  on route change.

---

## 14. Cursors and pointer affordances

- `pointer` on everything that activates. `text` on text. `not-allowed` on
  disabled, `wait` never, `grab`/`grabbing` on draggables, `col-resize` on
  column handles.
- Do not put `pointer` on non-interactive things. A cursor that lies is worse
  than a default cursor.
- Anything draggable needs a non-drag alternative (SC 2.5.7): a menu item, a
  pair of arrow buttons, or a number field.
- Custom cursors are almost always wrong outside a canvas app.

---

## 15. The one-line audit sweep

When you need to know quickly whether a codebase has done this work at all:

```bash
# native tooltips carrying real content
grep -rn 'title="' src --include=*.tsx | grep -v 'iframe\|svg\|<title' | wc -l
# focus removed with no replacement
grep -rn 'outline-none\|outline: *none' src | grep -v 'focus-visible' | wc -l
# hand-rolled toggles
grep -rn '<div[^>]*onClick' src --include=*.tsx | wc -l
# the dark-scrollbar one-liner
grep -rn 'color-scheme' src | wc -l
# selects stripped of their chevron with nothing put back
grep -rn 'appearance-none' src --include=*.tsx | grep -i select
```

Each of these is a **candidate count**, not a finding count. `micro-checks.sh`
exists for exactly this and `scoring.md` is explicit that a grep count proves a
pattern exists, not that it is a defect. Open the top three hits and look.
