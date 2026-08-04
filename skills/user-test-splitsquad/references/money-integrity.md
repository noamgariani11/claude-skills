# Money Integrity — how to judge a number

This is the axis that makes this skill worth running. Product UX is judged with
`scoring-and-evidence.md`. **Do not apply that calibration table to a number.**

The unit of judgment is not a screen — it is a **displayed figure with a derivation**: a per-person
share, a balance, a settle-up transfer, a total on an export. Every one of them gets a ruling.

| Ruling | Meaning |
|---|---|
| **TRUST IT** | Re-derived by hand, matches to the cent, provenance clear. |
| **RECONCILE BY HAND** | Arithmetically defensible but unverifiable from the UI, or off by rounding noise, or the rate/source isn't stated. A user would have to check it themselves. |
| **WOULD START A FIGHT** | Wrong, or right-but-dishonest. Someone in the group is being charged something they can't be shown to owe. |

---

## The capture protocol (persona A, Phase 2A)

Without this, there is no money axis. For every expense entered, record **inputs and outputs
together**, verbatim:

```
EXPENSE [A-3] "Mercado lunch"
INPUTS:  subtotal 118.00 EUR | tax 8.5% | tip 12% | payer samira
         split equal | participants samira:1 marco:1 pilar:1
         trip currency EUR | my base USD
APP SAYS: total €142.19 | shares  samira €47.40  marco €47.40  pilar €47.40
          balance after: samira +€94.79  marco −€47.40  pilar −€47.40
SCREENSHOT: a-03-expense.png
```

Then, for the trip as a whole: every balance on `BalanceCard`, the full settle-up plan, and the
export totals. **Screens, not summaries.** An expert cannot re-derive a number that was paraphrased.

---

## The six dimensions

Score each 1–5. The ruling follows from the profile, not from an average.

### 1. Conservation — *does money appear or vanish?*

- `Σ shares == expense total`, to the cent, for **every** split type.
- `Σ net balances == 0` across the trip, and across all trips.
- Payments move value between people; they never change the total.

**A conservation break is `critical` regardless of size.** A cent that doesn't sum is the visible
end of a mechanism that can also lose a dollar.

### 2. Rounding — *who eats the penny?*

- $100 ÷ 3 = 33.333…. Two-decimal display shows 33.33 ×3 = 99.99. **Where is the missing cent?**
  A correct app either allocates the remainder deterministically (someone eats it, consistently) or
  keeps full precision internally and reconciles at settle-up. An app that does neither drifts.
- The test that matters is **accumulation**: 20 expenses, three ways. Is the total error still
  under a cent, or has it grown?
- **Display vs math:** `Intl.NumberFormat(maximumFractionDigits: 2)` formats; it does not round the
  value. Any screen where the displayed total ≠ the sum of the displayed parts is a finding even
  when the floats behind it are perfect — **the user believes the display.**

Scoring: a single-cent artifact of float division, non-accumulating, is `low` at most. The same
cent surviving into a settle-up transfer that can never clear is `high`.

### 3. Currency truth — *what rate, from when, and what if there isn't one?*

- Unknown currency code → **1:1 against USD is money invented from nothing. `critical`.**
- Live rate vs static fallback vs cached: can the user tell which, and as of when?
- Historical expenses re-valued at today's rate = a trip whose cost changes overnight. Whatever the
  app does, it must claim the same thing it does.
- Round-trip A→B→A within a cent.

### 4. Attribution — *is the right person charged the right amount?*

- An explicit weight of `0` charges **exactly zero**, in every split type. (`?? 1` vs `||` — grep
  the path.)
- `exact` weights that don't sum to the total: is the delta scaled proportionally, or does one
  person absorb it? Whatever it does, is it visible?
- `percentage` weights that don't sum to 100: normalized, or is the remainder lost?
- Tax and tip apply **proportionally to shares**, not to one person.
- **Multi-payer**: `Expense.payers[]` exists. Does the canonical `computeBalances` honor it, or
  credit only `payerId`? If two surfaces disagree about who fronted the money, both are wrong to
  the user.
- **Itemized receipts**: assigned items produce shares that still sum to the total; unassigned
  items are handled explicitly, never dropped.

### 5. Settlement correctness — *does the plan actually settle?*

- Apply every transfer in the plan on paper. **Every member must land at zero.**
- Transfer count should be ≤ n−1 for n non-zero members. More than that is a suboptimal plan, not a
  wrong one — `medium` unless it's wildly off.
- **Determinism:** the same balances must produce the same plan across reloads. Equal-amount ties
  with no explicit tie-break reorder freely; a settle-up plan that changes when nothing changed is
  a trust defect (`medium`–`high`) even when both versions are valid.
- Payment sign: debtor → creditor. **A flipped sign doubles the imbalance instead of clearing it.**
- Overpayment flips the direction correctly and by the right amount.

### 6. Honesty — *does the app assert a state the data doesn't support?*

**This dimension caps the others.** A `1` here caps the artifact at **WOULD START A FIGHT** and
4/10 no matter how good the arithmetic is.

Check every claim of state:

- "All settled up" while the ledger nets non-zero.
- A payment rendered as complete while its status is `pending`/`processing`.
- A settle-up modal implying it *sent* money it can only *record* (Venmo/Zelle are handoffs).
- A "saved" toast over a write that failed (localStorage quota, DB absent, network error).
- A notification described as sent that was queued and discarded.
- A stubbed endpoint returning a success shape. (`/api/settlements` is a documented stub — an
  honest boundary; a stub that returns fabricated data is not.)
- A converted amount presented with no indication it was converted.

**An honest failure is not a defect.** The DB layer is deliberately additive, the SWR fetcher
returns empty shapes on error by design, and publishing money through a rail the app can't observe
is genuinely impossible. Score the *dishonesty*, never the *limitation*.

---

## Deriving the Money Integrity score (/10)

Start at 5 and adjust from the dimension profile of the whole corpus, not one artifact:

| Score | Means |
|---|---|
| 9–10 | Every number re-derived to the cent; provenance visible; settle-up plan lands everyone at zero; no state claim exceeds the data. Almost never. |
| 7–8 | Arithmetic sound, at most cosmetic provenance gaps. A cautious treasurer would ship it. |
| 5–6 | Right on the happy path; breaks or becomes unverifiable at an edge (a currency, a split type, an overpayment). |
| 3–4 | A real number is wrong, or a screen asserts a state the data doesn't support. |
| 1–2 | Conservation breaks, or money is invented (unknown-currency 1:1, doubled imbalance). |

**Hard caps, applied before anything else:**

- Any **conservation break** or **invented money** → cap at **2**.
- Any **honesty failure** (dimension 6 = 1) → cap at **4**.
- **No hand reconciliation performed** → the axis is **not scored at all.** Report it as unscored
  and say why. A Money Integrity score with no derivation behind it is the exact false confidence
  this skill exists to prevent.
