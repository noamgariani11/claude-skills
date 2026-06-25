---
name: round-trip-stocks
description: >-
  Find large companies whose stock price is currently sitting at a level it
  first reached many years or decades ago — a "round trip" or "lost decade(s)"
  where long-term price gains have been erased (e.g. Intel ~$20 in 2025 = ~$20
  in the late 1990s; Royal Caribbean ~$19 in 2020 = mid-1990s levels). Researches
  live market data, verifies the matching historical year, and excludes names
  that have since recovered. Supports filters like "currently depressed only,"
  "no/low dividend," market-cap floor, and minimum number of years/decades.
  Use when the user asks to "find round-trip stocks," "stocks back at old prices,"
  "lost decade stocks," "companies trading where they were decades ago," or
  references the Intel/Royal Caribbean pattern.
---

# Round-Trip Stocks

Find large, recognizable companies whose stock **right now** trades at a price
it held many years or decades earlier — so an investor holding since then has
little or no price appreciation to show for it. Investors call this a **"round
trip"** or a **"lost decade(s)."**

## Canonical examples (the mental model)

- **Intel (INTC)** — ~$18–20 in 2024–2025, a level last seen in the late 1990s.
- **Royal Caribbean (RCL)** — ~$19 intraday low in March 2020, a mid-to-late-1990s level.
- **Cisco (CSCO)** — peaked ~$80 in March 2000, didn't reclaim it until Dec 2025 (~25-year round trip).
- **Carnival (CCL)** — $6.11 in Oct 2022, a ~30-year low (~1992 levels).

These last two illustrate a key rule: **a round trip only counts if it still
holds.** Cisco, Intel, RCL, and Carnival have all since recovered, so by default
they are *excluded* from a "currently exists" answer.

## Step 1 — Clarify scope (ask only if the user didn't already specify)

Use `AskUserQuestion` to lock these down. Skip any the user already gave.

1. **Currently depressed only, or historical too?**
   - *Currently depressed only* (default): only names sitting at an old price
     level **as of today**. Exclude anything that has recovered.
   - *Historical allowed*: include famous past round trips even if recovered.
2. **Dividend filter?**
   - *Any* (default).
   - *No / low dividend only*: for non-payers, a price round trip equals a true
     total-return round trip ($0 made). This skews toward newer names (PayPal,
     Block, Moderna) and recent dividend-cutters (Boeing), so round trips are
     usually ~5–10 years rather than multi-decade. Flag that tradeoff.
3. **Minimum age of the round trip?** e.g. "at least a decade," "20+ years."
4. **Size floor?** Default to large/mega-cap (recognizable names, > ~$10B).
   Offer to extend to mid-caps (Roku, Snap, Zoom, DocuSign), where round trips
   are often more extreme.

## Step 2 — Research methodology

Look up the **current date** in context first — the market keeps moving and
"recovered" is relative to today.

The pattern is produced by two ingredients:
1. A **bubble or boom peak** — dot-com 2000, COVID-travel 2021, the COVID-crash
   bottom of 2020, a sector mania.
2. A **structural decline** afterward that drags the price back to an old level.

The categories that produce the most round trips:
- **Legacy tech / semis** — Intel, Cisco, Qualcomm, TI, Nokia
- **Telecom** — AT&T, Verizon, Vodafone
- **Legacy pharma** — Pfizer, Bristol-Myers Squibb, Viatris
- **Big retail / staples** — Walgreens, Kraft Heinz, Conagra
- **Travel / leisure** — Royal Caribbean, Carnival
- **Post-2021 growth wreckage** — PayPal, Block, Moderna, Adobe, Salesforce,
  Roku, Snap, Zoom, DocuSign, Peloton

Run **parallel `WebSearch`/`WebFetch` calls** (batch them in one message). For
each candidate, establish three numbers:
- **Current price** (today / most recent close).
- **The matching historical year** — when it last traded at that price *on the
  way up* (not just on the way down from a peak). Phrasings like "lowest since
  1998" or "X-year low" in headlines are gold.
- **Peak** it round-tripped from, for context.

Good primary sources: Macrotrends (`/stocks/charts/<TICKER>/.../stock-price-history`),
stockanalysis.com history pages, and dated news headlines ("hits lowest level
since YYYY"). Cross-check at least the current price and the matching year.

### Verification rules (do not skip)

- **Exclude recovered names** when scope is "currently depressed only." Always
  re-check the *current* price; a name that fit last year may have rallied.
- **Beware split / spinoff / dividend adjustments.** Adjusted charts can show a
  fake "lost decade" (or hide a real one). For dividend-heavy names (Pfizer,
  AT&T, Vodafone) note that price ≠ total return.
- **Beware delisted / acquired names** (e.g. Walgreens went private at $11.45 in
  Aug 2025). They were round trips but you can't buy them — call this out.
- **"On the way up" vs "on the way down."** A price last seen 10 years ago while
  *crashing* from a peak is a weaker example than one last seen 10 years ago
  while the stock was *rising*. Prefer the latter; note which it is.

## Step 3 — Output format

Lead with one sentence naming the pattern and the active filters. Then group
results by strength:

- **Strongest current cases** — clean fit: depressed today, clear matching year.
- **Solid but with a caveat** — e.g. dividend muddies total return, young
  company, recently bounced off the low.
- **Borderline / excluded** — recovered too much, delisted, or acquisition-driven
  pop. Briefly say *why* each was cut (this is as useful as the inclusions).

For each name give: **ticker, current price, the matching historical year, and
the peak it fell from**, in one tight line plus a sentence of context. Convert
relative dates to absolute. End with a **Sources** list of markdown links to
every page actually used, and offer to (a) pull a split-adjusted price-vs-year
table to confirm a precise matching year, or (b) widen the screen (mid-caps,
other sectors, or drop a filter).

## Notes

- Default to thoroughness for this kind of screen — fan out many searches in
  parallel rather than checking one ticker at a time.
- Be honest about confidence. If a matching year isn't pinned down, say so
  rather than inventing one.
- Total-return caveat is the single most important nuance: a flat price with a
  fat dividend is *not* the same as a flat price with no dividend.
