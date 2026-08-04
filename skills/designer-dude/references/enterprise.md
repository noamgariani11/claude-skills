# Enterprise app design - what world-class looks like on a dense surface

Load this whenever the target is an **application** rather than a marketing
page: dashboards, tables, forms, detail pages, admin surfaces, anything a
professional uses for hours to do their job.

The rest of this skill's rubric was written with a page in mind. Most of it
transfers. What does not is the thing enterprise design is actually judged on:
**how much true work a competent user gets done per minute, and how confidently
they can undo a mistake.** A landing page that looks immaculate and an
application that looks immaculate are not the same achievement.

The standard here is Linear, Stripe's dashboard, Figma, and Height - products
where the craft is in the density, the keyboard, and the state handling, not in
the hero.

**Pairs with `components.md`, which is the per-control layer.** This file is
about the surface: what belongs on it, how dense, in what order, and what
happens when it fails. That file is about the thing you click. An app surface
needs both, and the division is worth keeping straight - "the table is too
airy" is a question for this file, "the row action only appears on hover" is a
question for that one.

---

## The three questions that decide the grade

Ask them before any pillar-by-pillar work:

1. **What is the user's job on this screen, and what is the one action that
   completes it?** If the screen offers four equal actions, it has no hierarchy
   regardless of how tidy it looks.
2. **What happens when it goes wrong?** Partial failure, stale data, a
   permission the user does not have, a record another user just changed. An
   app that only designs the happy path is a B ceiling.
3. **Could a power user do this faster than the UI allows?** If the answer is
   "yes, in a spreadsheet", the design has lost to Excel and should say so.

---

## Data tables

The highest-leverage surface in almost every enterprise product, and the one
most often designed like a marketing component.

**Density is a decision, not a default.**

- Row height **40–44px compact, 48–56px comfortable**. Above ~64px you are
  paying a screen of scrolling for air nobody asked for.
- Offer a density toggle on any table users live in, and **persist the choice**.
  The right row height is the one that user picked.
- A typical desktop viewport shows 12–15 comfortable rows. Reviewing 300 records
  is 9 screens compact against 20 comfortable - that difference is the feature.

**Numbers.**

- Right-align numerals; left-align text; align on the decimal for mixed
  precision. Magnitude comparison by eye is the whole point of a column
  (Tufte).
- `font-variant-numeric: tabular-nums` on every numeric column, always. Without
  it digits shift width between rows and the column stops being scannable.
- Currency: one alignment, one precision per column. Show the unit in the header,
  not in 200 cells.

**Structure.**

- Sticky header past ~15 rows. Column meaning must not scroll away.
- Explicit header associations where direction is ambiguous (`scope="col"` /
  `scope="row"`, or `headers`/`id` for multi-level tables), and `aria-sort` on
  any sortable header. A small one-direction table may rely on `<th>` alone.
  Sortable headers
  that only look sortable are a 4.1.2 failure.
- Sort must be **deterministic on ties** - add a stable secondary key, or the
  same query returns rows in different orders and users think data changed.
- Pin the identifying column when horizontal scrolling is unavoidable.
- Zebra striping is a last resort; row hover and adequate row height usually beat
  it, and striping fights selection and status tints.

**Selection and bulk actions.**

- Selected rows need a visible tint that is **distinguishable from hover** -
  two tints, not one used for both.
- Show the count (`3 of 248 selected`) and offer select-all-matching separately
  from select-all-visible. Those are different intents and conflating them
  destroys data.
- Bulk actions appear in a toolbar tied to the selection, and must **report
  per-item outcome on partial failure**: "17 updated, 3 failed" with the three
  named. A bulk action that reports one aggregate error is unusable at scale.
- Destructive bulk actions: undo, or confirm naming the count and the object
  type. Never both instant and silent.

**Empty, loading, and too-much.**

- Distinguish **no data yet** from **no results for this filter**. They need
  different copy and different actions ("Add your first property" vs "Clear
  filters").
- Skeletons must match the shape of what arrives, or the layout jumps and you
  have designed a CLS.
- Never animate rows in a list of 200. Motion in a dense table is noise.

---

## Forms

Enterprise forms are long, conditional, and often filled by someone who does
this thirty times a day.

- **Labels above or beside, never placeholder-only.** A placeholder disappears
  the moment typing starts, fails at zoom, and is a 3.3.2 failure.
- Group with `fieldset`/`legend` or a visible group heading. Gestalt proximity
  does the work; a flat list of 25 fields has no structure.
- **Field width should signal expected input length.** A 4-character year field
  as wide as a street address is a small lie the user pays for.
- Validate on blur, not on every keystroke; show errors adjacent to the field,
  name the fix rather than the rule ("Use MM/DD/YYYY" beats "Invalid format").
- Announce errors in a live region, and move focus to the first invalid field on
  submit failure.
- **Do not re-ask for what the user already gave** (WCAG 3.3.7). Autofill,
  carry-forward, and sensible defaults are accessibility features, not polish.
- Preserve input across a failed submit. Losing 25 fields to a server error is
  the fastest way to be hated.
- Required vs optional: mark the minority. If most fields are required, mark the
  optional ones.
- Keyboard: Enter submits, Escape cancels a modal, Tab order follows visual
  order, and a multi-step form remembers where the user was.

---

## State, feedback, and trust

The pillar list calls for seven states. On an app surface they are not optional:

| State | What it must do |
|---|---|
| **Loading** | Distinguish first load (skeleton) from refresh (subtle indicator). Never block the whole page for one widget. |
| **Pending** | Every mutation shows immediate feedback under 100ms. Disable the trigger to prevent double-submit. |
| **Empty** | Say what this is, why it is empty, and the one next action. |
| **Error** | Name what failed, whether it retried, and what the user can do. Preserve their work. |
| **Partial** | Per-item outcomes for anything batched. |
| **Stale** | If data can go out of date while visible, say when it was fetched and offer refresh. Silent staleness is a correctness bug wearing a UI. |
| **Permission-denied** | Absent is better than present-and-broken, but a disabled control needs a reason on hover/focus. |

**Optimistic updates need a rollback that is visible.** An optimistic write that
silently reverts teaches users not to trust the screen.

**Every row of that table is graded by DRIVING the app, not by reading it.**
The probe can tell you a skeleton exists somewhere in the DOM; it cannot tell
you the mutation gave feedback in 100ms, that the bulk action named which three
of forty items failed, or that the optimistic write rolled back visibly. Go
through the `browse` skill (`browser-verification.md`): log in once - the MCP
browser keeps the session for the whole run, including across subagents -
then reach each state deliberately. Filter a list to nothing for the empty
state, request a record that does not exist for the error state, submit with a
throttled network for pending, and `browser_console_messages` plus
`browser_network_requests` after each one, because a state that looks fine
while logging a 500 is not fine. Mode D's `states` probe config captures the
ones reachable by URL; the rest need clicks, and a state you did not reach is
a state you did not grade - say so rather than scoring around it.

---

## Keyboard and speed

- Every action reachable by keyboard, and the tab order matches the visual
  order. Positive `tabindex` is a bug.
- Focus must be **visible against every surface it lands on**, including inside
  tables and modals.
- Modals: trap focus, restore it to the trigger on close, Escape closes.
- A product used daily earns shortcuts: a command palette, `/` for search,
  `j/k` navigation on lists. Discoverable via a `?` sheet - not a secret.
- Sticky headers must not obscure a focused row (WCAG 2.4.11). Use
  `scroll-margin-top` equal to the header height.

---

## Information architecture at scale

- **The object model must be visible.** A user should be able to predict where a
  record lives without searching. Nav that mirrors the database schema, or the
  org chart, fails this.
- Deep links survive a refresh, and filters/sort/pagination live in the URL. If
  state is only in memory, users cannot share what they are looking at.
- Breadcrumbs on anything more than two levels deep.
- Search wherever depth exceeds two levels, and it must search the objects users
  think in (address, tenant name, invoice number), not just titles.
- Terminology is the user's, not the schema's. `organizationId` never reaches a
  label.

---

## Density, whitespace, and the "enterprise-grade" trap

Two opposite failures, both common:

1. **Consumer-grade air on a professional tool.** 72px rows, 32px gaps, one
   metric per card. It photographs well and it wastes the user's day.
2. **Actual crowding.** 11px type, 2px gutters, no grouping. Dense is not the
   same as cramped: density comes from *removing decoration*, not from
   shrinking type and squeezing gaps.

The resolution is hierarchy at small sizes: two weights, two colours (ink and
muted), and one accent, applied consistently. That is how Linear and Stripe get
information density that still reads as calm.

**Grade dense surfaces on work-per-screen, and calm surfaces on focus.** A
settings page and a reconciliation table should not have the same density, and
grading them by one standard is how a rubric produces bad advice.

---

## What to measure, and with what

The probe already captures the app-specific facts - read them out of
`app` in the probe JSON:

| Question | Where |
|---|---|
| Are rows a sane height? | `app.tables[].medianRowHeight` |
| Sticky header on long tables? | `app.tables[].stickyHeader`, `.rows` |
| Numerals right-aligned? | `app.tables[].numericCells` vs `.numericRightAligned` |
| Headers associated for AT? | `app.tables[].hasScope`, `.sortableHeaders` |
| Selection affordance present? | `app.tables[].selectionCheckboxes` |
| Form labelled properly? | `a11y.fieldsMissingLabel`, `fieldsPlaceholderOnly` |
| Errors announced? | `a11y.liveRegions`, `app.forms[].inlineErrors` |
| Loading designed? | `app.skeletonOrSpinner` |
| Empty states written? | `app.emptyStateSignals` |
| Shortcuts offered? | `app.keyboardHints` |
| Disabled controls explained? | `app.disabledControls` (then check for a reason) |

`probe-report.py` raises candidates for the mechanical ones. The rest are yours,
and they are where an enterprise review earns its keep: nothing automated can
tell you that a bulk action reports one aggregate error instead of three named
failures, and that is the finding a professional user would raise first.

---

## Domain correctness outranks all of it

On a professional tool, a number that is wrong is worse than a layout that is
ugly, and it is not a design finding this skill can hand-wave: if the NOI math,
the proration, the tax total, or the cap rate is wrong, **say so at the top of
the report, before any grade**, and mark it as outside the design score.

A beautifully typeset wrong number is the worst artifact a design review can
bless.
