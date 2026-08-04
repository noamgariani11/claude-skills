# Domain Accuracy — invariants, ground truth, and the citation rule

This is the highest-risk file in the skill.

An expert who asserts *"Splitwise rounds the remainder to the payer"* or *"Venmo caps a transfer at
$X"* from model memory is **exactly as dangerous as the app being wrong** — and more dangerous,
because a confident wrong correction gets *committed*. Model recall of product and payment-rail
specifics is stale by construction.

Split-math invariants are different: they are **derivable**, not recalled, and that is why they are
the backbone of this file. Anything that is not derivable needs a citation.

---

## The citation rule (non-negotiable)

Every domain-accuracy finding must cite **one** of:

1. **An invariant below** — these are arithmetic, and a violation is provable by construction.
2. **The repo's own artifacts** — `src/utils/__tests__/*.test.ts`, `research/competitive/
   landscape.md`, `CLAUDE.md`, or a `file:line` in the implementation.
3. **A live `WebFetch`** of the third party's own docs (Stripe, Venmo, Zelle, Frankfurter,
   Splitwise). Cite the URL and the date fetched.

A finding with none of these is **`[UNVERIFIED]`**. It is *named* in the report so the next run can
chase it, but it **cannot be scored as a defect** and **cannot be handed to Phase 5**.

> **Never edit `src/utils/balances.ts` or `currency.ts` on the strength of model recall alone.**
> If you cannot derive it or cite it, you do not know it.

### Severity of a money defect

| Finding | Severity |
|---|---|
| Money invented or destroyed (conservation break, unknown-currency 1:1, doubled imbalance) | `critical` |
| A screen asserts a state the data does not support (settled / paid / sent / saved) | `critical` |
| The wrong person is charged (excluded participant, mis-attributed payer, dropped item) | `high` |
| A settle-up plan that does not zero everyone, or is non-deterministic | `high` |
| Converted amount with no visible provenance | `medium` |
| Rounding artifact that does not accumulate | `low` |
| Correct math with no test pinning it | `TEST-GAP`, not a severity |

---

## The invariants (derivable — cite these freely)

Let an expense have subtotal `S`, tax `t%`, tip `p%`, participants `i` with weights `w_i`.

**I1 — Total.** `total = S + S·t/100 + S·p/100`. Tax and tip are both computed off the **subtotal**,
not compounded on each other. (`calculateExpenseTotal`, `src/utils/balances.ts`.)

**I2 — Conservation.** For every split type, `Σ share_i == total` (in the expense's own currency),
to the cent. This is the single most important line in this file.

**I3 — Weight semantics.** For `equal` and `shares`: `share_i = total · (w_i ?? 1) / Σ(w_j ?? 1)`.
A **missing** weight defaults to 1; an **explicit 0** means excluded and must yield exactly 0.
`||` in this path is a defect by construction — it turns an excluded participant into a
full-weight one.

**I4 — Percentage.** Weights are percentages, normalized by their own sum (they need not total
100). If the sum is 0, the fallback is an equal split — and it must still satisfy I2.

**I5 — Exact.** Weights are absolute amounts, scaled by `total / Σw` so I2 holds even when the
entered amounts don't sum to the total. An explicit `0` yields `0`; **only** a total sum of 0 falls
back to an equal split.

**I6 — Degenerate inputs.** Empty participants → the payer alone bears the expense. Non-positive
total weight → equal split. Neither may violate I2, and neither may produce `NaN`. **A `NaN` share
propagates into every balance on screen** and is `critical`.

**I7 — Zero-sum ledger.** Across a trip, `Σ net_i == 0` before near-zero cleanup. Expenses move
value between members; they never change the sum.

**I8 — Payment direction.** A payment from debtor `d` to creditor `c` moves `d`'s negative balance
**up** toward zero and `c`'s positive balance **down** toward zero. The sign convention is the
*opposite* of the expense loop (where the payer is the one owed). Reversing it doubles the
imbalance instead of clearing it, and the result still looks like a plausible number.

**I9 — Settlement completeness.** Applying every transfer from `simplifyDebts` to the balances it
was computed from must leave every member at zero (within the $0.01 cleanup threshold), using at
most `n−1` transfers for `n` non-zero members.

**I10 — FX round-trip.** `convert(convert(x, A, B), B, A) == x` within a cent, for any two codes
that *have* rates. For a code with **no** rate, there is no correct number — only an honest
refusal.

**I11 — Determinism.** The same inputs produce the same outputs across renders, reloads, and array
orderings. Any dependence on trip/expense iteration order in the pairwise ledger, or on an
unstable sort in `simplifyDebts`, breaks this.

**I12 — Currency layering.** `resolveShares(expense, tripCurrency)` converts the expense total from
its own currency into the trip currency; `computeBalances` then converts each share from the trip
currency into the base. A share must be converted **once per hop**, never twice within a hop and
never zero times.

---

## FX ground truth

| Fact | Value | Conf | Source |
|---|---|---|---|
| Static fallback table | `USD 1, EUR 0.92, GBP 0.79, CAD 1.35, AUD 1.48, INR 83.2` — **six codes only**, USD-based | HIGH | `src/utils/currency.ts` |
| Currency picker options | the same six (`currencyOptions`, `AppStateContext`) | HIGH | `src/context/AppStateContext.tsx` |
| Unknown code behavior | `liveRates[code] ?? 1` → converted **1:1 against USD** | HIGH | `src/utils/currency.ts` |
| Live rate source | Frankfurter, proxied by `/api/currency-rates`, no API key, 1-hour in-memory cache, falls back to the static table on failure | HIGH | `src/app/api/currency-rates/route.ts`, `CLAUDE.md` |
| Frankfurter's own data | ECB reference rates, published **once per working day (~16:00 CET)**; **no weekend/holiday updates** | MED — `WebFetch` frankfurter.dev before citing | frankfurter.dev |
| Base for all balances | USD | HIGH | `CLAUDE.md`, `computeBalances` default |

**Consequences worth testing, not assuming:**

- The picker offering only six codes does **not** mean an unsupported code can't reach the math —
  imported, API-posted, or persisted state can carry one. Test the *path*, not the dropdown.
- ECB rates are daily, so "live" is at best yesterday's close for a weekend trip. That is fine —
  **provided the app doesn't imply real-time.**

---

## Payment-rail facts — **`WebFetch` before citing any of these**

Nothing in this section may be asserted from memory. The rows exist to tell you *what to check*,
not what is true.

| Claim to verify | Where to verify it |
|---|---|
| Stripe webhook signature verification requirement + event redelivery semantics | docs.stripe.com/webhooks |
| Stripe minor-unit amount convention (zero-decimal currencies exist) | docs.stripe.com/currencies |
| Partial vs full refund representation | docs.stripe.com/refunds |
| Venmo transfer/request limits and whether any API confirms settlement to a third party | venmo.com help pages |
| Zelle settlement finality and irreversibility | zellepay.com |

**The structural fact that matters more than any limit:** Venmo and Zelle handoffs are
**unobservable** to SplitSquad. The app can record an intent; it cannot know a transfer happened.
Any copy implying otherwise is an honesty defect (`money-integrity.md` dimension 6), and that
judgment needs no citation because it follows from the architecture.

---

## Competitor facts

Ground every comparison in **`research/competitive/landscape.md`** (the repo's own research, dated
July 2026) and `WebFetch` the competitor's own page before asserting a price or feature.
**Never flag a competitor claim from recall.**

Structural facts about the space that experts get wrong:

- **Splitwise is the incumbent**, and debt simplification is *its* signature feature — SplitSquad
  implementing it is table stakes, not differentiation. Do not report it as an innovation.
- A group-expense app's switching cost is **social, not technical**: the blocker is getting five
  other people to move, which is why the no-account preview surfaces (`/invite/[token]`,
  `/trip-preview/[token]`) matter far more than their code size suggests.
- SplitSquad's genuinely unusual properties, worth testing *as* differentiators: it works with **no
  database at all** (localStorage-first), it ships **itemized receipt OCR**, and it carries
  **shared subscriptions** as a first-class object separate from recurring expenses.

---

## Repo structural facts experts get wrong (**not** findings)

- The canonical math lives in `src/utils/balances.ts`. `AppStateContext` **re-exports** it for
  backwards compatibility — that is not a duplicate implementation. A genuine duplicate (a view
  computing its own shares) **is** a finding; check which one you're looking at before filing.
- The dashboard is **`/app`**, sign-in is **`/login`**, and **`/` is a marketing landing page**.
  CLAUDE.md's older text saying `/` is the main app is stale. An expert testing `/` for app
  behavior is testing the wrong route.
- The DB layer is **additive, not authoritative**: with `POSTGRES_URL` set, some data comes from
  API routes via SWR, but primary state still lives client-side, and the fetcher **deliberately**
  returns empty shapes on error. That is documented design, not a swallowed error.
- `reactCompiler: true` — manual `useMemo`/`useCallback` are not expected. Their absence is not a
  performance finding.
- There are **no component tests and no E2E tests**. Stating that is not a discovery; naming the
  specific money-bearing path it leaves unpinned is.

---

## Maintaining this file

One of the skill's compounding assets. Each run:

- When an expert grounds an `UNVERIFIED`/`MED` row against a live doc, **promote it**: write the
  value, date it, cite the URL, and log it in `learnings.md` under `ground-truth promoted`.
- When a fact turns out to be wrong, **overwrite it in place.** A stale line here is worse than no
  line, because it will be trusted.
- Never append a diary. This file records what is true *now*.
- **Re-verify the code before filing any gap this file predicts.** Ground-truth rows go stale in
  the pessimistic direction too — filing a defect the repo already fixed is the exact failure this
  file exists to prevent.
