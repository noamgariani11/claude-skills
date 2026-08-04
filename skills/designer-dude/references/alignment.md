# Alignment, and when centred is the right answer

Load this before writing up anything about alignment, and **always** before
acting on the probe's `centredShare`, because that number is the easiest one in
the whole rig to misread.

The slop list has an entry called "centred-everything". It is correct, and it
is routinely applied wrong: reviewers see a centred hero and dock the page.
Centring is not the defect. **Undecided alignment is the defect**, and centring
happens to be what undecided looks like most of the time, because it is the
default that requires no thought about where the eye should start.

So the rule is not "centre less". It is: **every element's alignment is a
decision, and the decision is defensible in one clause.**

---

## Centre it when the content is a destination

Centring says "stop here, this is the whole thing". That is exactly right when
the block is short, self-contained, and the only thing asking for attention.

**Centre by default:**

| Surface | Why |
|---|---|
| Marketing hero: eyebrow, headline, subhead, one or two CTAs | One message, no competition, symmetry reads as confidence |
| Empty states | A single instruction in an otherwise blank region needs a focal point |
| Auth cards: sign in, sign up, reset password | One task, no navigation, nowhere else to go |
| Confirmation and success screens | Terminal state, one next action |
| Error and 404 pages | Same |
| Modal and dialog **headers and footers** (bodies usually left) | Short, symmetrical, framed |
| Loading and zero-data states | Focal point in negative space |
| Pricing tier headers, section eyebrows and section titles | Short labels above a symmetrical grid |
| Anything under about 3 lines that sits alone in its own band | Below the threshold where the eye needs a left rail |
| Icons, avatars, badges, spinners within their own box | Optical centring, always |
| Numbers in a stat tile, when the tiles are a symmetrical row | The row is the composition |

**The load-bearing detail:** centred blocks need a **max-width**. A centred
paragraph running to 110ch is worse than the same paragraph left-aligned,
because every line start moves and the eye has to hunt for it on every return
sweep. Centred body copy stays under about 60ch, and centred headlines want
`text-wrap: balance` so the rag is even instead of leaving one orphaned word.

---

## Do not centre when the content is a path

Left alignment (or right, in RTL) gives the eye a fixed return point. Anything
the eye traverses repeatedly needs one.

**Never centre:**

- **Body copy over about 3 lines.** This is the one the probe measures, and the
  40-character floor in `probe.js` is why: it counts long blocks only. A page
  full of centred long paragraphs is a real finding.
- **Form fields and their labels.** Labels left, fields left, a consistent left
  edge down the whole form. A centred form is a column of things the eye cannot
  scan for the one it needs. The *card* holding the form may be centred on the
  page; its contents are not.
- **Lists of any kind**, including nav, menus, and dropdown options. Centred
  list items produce a ragged left edge that destroys scannability.
- **Table cells of text.** Text left, numbers right, and nothing centred except
  a short status column or a checkbox.
- **Anything with a leading icon.** Centred rows with icons put the icons at
  different x positions on every row, which reads as broken.
- **Dense app surfaces generally.** Dashboards, settings, detail pages, tables.
  Density and centring fight each other.

---

## The three alignment failures worth a finding

**1. Both, in the same region.** A centred heading over left-aligned body is
correct and common. A centred heading, left body, and then a centred CTA is
three decisions in one band and it reads as unresolved. Within one band, pick
an axis for the things that repeat.

**2. Centred long-form.** More than about 30% of long text blocks centred is
the threshold where the probe's `centredShare` becomes a real signal. Below
that, look at *which* blocks: five centred section headers on a landing page is
correct design and gets no finding.

**3. No shared edges.** The real quality marker is not left versus centre, it
is whether **things line up with each other at all**. Check for an invisible
vertical rail: does the section eyebrow start where the headline starts, and
where the body starts, and where the CTA starts? Does the card content share a
left edge with the card title? Off-by-a-few-pixels alignment between siblings
is the most common Craft finding and the easiest to fix, because it is almost
always one wrong padding value.

---

## Optical over geometric

Mathematical centring is often visibly wrong. The cases that matter:

- **Icons inside circular or square buttons.** A play triangle centred by its
  bounding box looks left-heavy; nudge it right by roughly 5-8% of its width.
  Arrows, chevrons, and send icons have the same problem.
- **Text in a pill.** Descenders and cap height mean the visual centre is
  usually 1px above the geometric one. Set line-height rather than padding-top
  and padding-bottom separately.
- **Punctuation at line starts** in a centred pull quote hangs outside the
  measure, not inside it.
- **Cards of unequal content height** in a row: align the tops and the
  actions, not the middles. Bottom-align the CTAs with `margin-top: auto` so
  the row of buttons is a straight line even when the copy is not.
- **A lone element in a viewport-height section** looks centred when it sits
  slightly above the true middle, roughly 45%. Perfect vertical centring reads
  as low.

---

## Grading it

Alignment lives in **Spacing & Layout** (12 points) with spillover into
**Craft** (5) for the pixel-level misses.

| Observation | Verdict |
|---|---|
| Long body copy centred across the page | **major** |
| Form contents centred | **major** |
| List or menu items centred | **major** |
| Three alignments inside one band | **minor**, or **major** if it repeats on every section |
| Siblings not sharing a vertical rail | **minor** each, **major** as a systemic pattern |
| Icon not optically centred in a button | **petty** unless it is the primary action |
| Hero, empty state, auth card, or 404 centred | **not a finding.** Correct. |

And the case that has to be stated plainly, because the slop list invites the
mistake: **a centred marketing hero is not AI slop.** The slop tell is a centred
hero *plus* the purple gradient *plus* the three-up feature grid *plus* the
generic headline. Centring is the one element of that cluster that is
independently defensible. Do not dock for it alone, and do not tell a user to
left-align a hero that is working.
