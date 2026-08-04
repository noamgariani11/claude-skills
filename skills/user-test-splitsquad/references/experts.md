# The Domain Expert Bench — ten practitioners, 3–4 per run

These are not personas with feelings. They are practitioners auditing a slice of the product
against how their field actually works. Each runs as an **isolated `Agent`** and does the **three
jobs** from SKILL.md Phase 2C:

1. **Invariant audit** — their slice of the math/behavior vs `domain-accuracy.md`.
2. **Test-shape audit** — what pins it, and could that test fail on the defect they're looking for?
3. **Corpus judgment** — rule on the numbers the app actually displayed:
   **TRUST IT / RECONCILE BY HAND / WOULD START A FIGHT.**

An expert who reviewed the UI and skipped jobs 1–3 has not done the work. Reject and re-run.

Rotation: `--expert` overrides everything; then diff-touched files; then **any expert reading
`NEVER`**; then staleness. All ten inside ~3 runs. **Name every skipped expert with its
last-covered date in the report.**

---

## 1. Bookkeeper / CPA — *the highest-value seat on the bench*

**Owns:** `src/utils/balances.ts`, `src/utils/debtSimplification.ts`, the reconciliation.

- Re-derives the corpus independently of persona B. Two independent derivations that agree is the
  only real proof the numbers are right.
- **Conservation:** for every expense, `Σ shares == total` to the cent, for every split type. For
  the whole trip, `Σ net balances == 0`. A ledger that doesn't sum to zero has invented or
  destroyed money — `critical`, always, no matter how small.
- **Double-entry sanity:** every credit has a matching debit. `computeBalances` builds both a `net`
  map and a pairwise `ledger`; check they agree with each other. **They are two representations of
  the same facts, and a disagreement between them is a defect in one of them.**
- **Near-zero cleanup:** balances under `$0.01` are dropped as noise. Is the threshold applied
  consistently to `net` and to `ledger`, and can repeated sub-cent truncation accumulate into a
  visible drift over many expenses?
- **Order dependence:** does the ledger depend on the order trips/expenses are iterated? A
  reordering that changes who owes whom is `high` — it manufactures mutual debts that don't exist.
- **Audit trail:** edit history and activity feed — can he trace a balance change back to the edit
  that caused it?

## 2. Payments Operations — Stripe, ACH, and the money that actually moves

**Owns:** `/api/stripe/*`, `/api/payments`, `SettleUpModal` handoffs, `/payments/success|cancel`.

- **Webhook discipline:** signature verified before the body is trusted; **event idempotency** (a
  redelivered event must not double-record a payment); DB failures surfaced rather than swallowed
  behind a `200`, which silently defeats Stripe's retry; refunds recorded at their **actual**
  amount (a partial refund recorded as full is a money defect).
- **State honesty:** `pending | processing | succeeded | failed | refunded` — does the UI render
  each distinctly, or does anything short of `succeeded` read as paid? A payment shown as complete
  before the rail confirms it is `critical`.
- **The rails it doesn't control:** Venmo/Zelle are *handoffs*. The app can record an intent, never
  observe a settlement. Any copy implying it verified an external transfer is a lie about state.
- **Amount hygiene:** integer minor units at the Stripe boundary; no float dollars crossing into a
  charge; currency code passed through, not assumed USD.
- **Cite, don't recall:** any claim about Stripe/Venmo/Zelle limits or behavior needs a `WebFetch`
  of the provider's docs (`domain-accuracy.md` citation rule). Model recall of payment-rail
  specifics is stale by construction.

## 3. Splitwise Power User — the competitor's muscle memory

**Owns:** the comparison verdict and the "why would we switch" question.

- Has 9 years and 40 groups in Splitwise. Knows exactly which interactions are table stakes:
  add-expense in under 5 seconds, "you owe / you are owed" at the top of everything, simplify
  debts, per-group and total balances, comments on an expense, receipt attachment, reminders.
- **Grounds every comparison in `research/competitive/landscape.md`** rather than memory, and
  `WebFetch`es a competitor's own pricing/feature page before asserting a fact about it. A wrong
  competitor claim in the report discredits the whole document.
- Names the **three things SplitSquad does that Splitwise does not** and the **three things it
  can't do yet that would stop a group switching**. If he can't name three of either, say so — an
  honest "no differentiator found" is a legitimate and important finding.

## 4. FX / Treasury

**Owns:** `src/utils/currency.ts`, `/api/currency-rates`, every converted number on screen.

- **Coverage:** which codes have rates and which fall through to `1:1`. **A silent 1:1 conversion
  of an unknown currency is money invented from nothing — `critical`.** The right behavior is to
  refuse, or to label loudly; the wrong behavior is a plausible number.
- **Provenance:** static fallback vs live Frankfurter proxy vs 1-hour cache. Can a user tell which
  they're looking at, and as of when?
- **Historicity:** are past expenses valued at the rate on the day, or re-valued at today's rate
  every render? Re-valuation makes a finished trip's cost drift with no new spending — decide which
  the app claims, and hold it to that claim.
- **Round-trip:** A→B→A must return the original within a cent.
- **Formatting vs math:** `Intl.NumberFormat` with `maximumFractionDigits: 2` **displays** two
  decimals; it does not round the underlying value. Where display and math diverge, the user
  believes the display. Any place a displayed sum ≠ the sum of displayed parts is a finding, even
  when the underlying floats are correct.

## 5. Receipt-OCR Skeptic

**Owns:** `/api/scan-receipt`, `src/utils/visionApi.ts`, `ReceiptScanner`,
`ItemizedReceiptModal`, `/api/expenses/[id]/items`.

- Feeds it: a clean receipt, a crumpled one, a non-receipt, a foreign-currency receipt, a
  handwritten total, and an image with two totals on it.
- **The rule that matters:** OCR is allowed to be wrong; it is not allowed to be **confidently**
  wrong. Does the app present extracted amounts as facts or as proposals the user confirms? A
  scanned total that silently becomes the expense subtotal without a confirmation step is a money
  defect (`high`) — because nobody re-reads a number that appears to already be correct.
- **Itemized assignment:** items assigned to specific people must produce shares that still sum to
  the expense total, including tax and tip. Unassigned items — who pays for them? An item assigned
  to *nobody* that silently disappears from the total is `high`.
- **Cost + failure:** Vision API needs credentials; without them the failure must be honest, not a
  zeroed-out receipt.

## 6. Durability / Offline (localStorage)

**Owns:** `AppStateContext`, `useDebouncedEffect`, the `splitsquad-local-state` key, the service
worker in `public/sw.js`.

- **The debounce window is a data-loss window.** State is written to localStorage on a debounce;
  close the tab inside it and the last edit is gone. Measure the window and say what is lost.
- **Quota:** receipt images plus a season of expenses against the ~5MB localStorage ceiling. When
  the write fails, does the app notice? A save that silently fails while the UI shows the expense
  is `critical` — the user's state and the app's state have diverged and only one of them survives
  a reload.
- **Shape drift:** persisted state written by an older build, loaded by a newer one. A trip missing
  an `expenses` array, an expense missing `participants` — does the app degrade or crash? Is an
  intentionally *empty* array ever mistaken for "no data" and replaced with seed data? (Silently
  restoring seed trips over a user's empty state destroys real work.)
- **Two tabs:** same app, two tabs, both editing. Last-write-wins over a whole state blob means one
  tab's expenses vanish. Reproduce it before flagging it.

## 7. Privacy / Data Protection

**Owns:** invite + preview tokens, `/api/people`, exports, notification emails.

- **Token scope:** what does an unauthenticated holder of `/trip-preview/[token]` actually receive?
  Diff the API response against what the page renders — **the leak is usually in the payload, not
  the UI.** Other members' emails, unrelated trips, or user IDs that address other endpoints are
  `high`.
- **Lifecycle:** expiry, single use, revocation on member removal.
- **Exports and emails:** does a PDF/CSV or a notification email carry more about other members
  than the recipient should have?
- **Minimization:** is anything collected that the product never uses?

## 8. Accessibility

**Owns:** keyboard paths, focus management, contrast, semantics, on desktop and at 390×844.

- Money-bearing forms first: can the whole expense form and the settle-up modal be completed on a
  keyboard alone, with visible focus at every step?
- Modals: focus trap, `Escape`, return focus on close. `ExpenseForm`, `SettleUpModal`,
  `ItemizedReceiptModal`, `EditHistoryModal`, `TripInviteModal` are the ones that matter.
- Numbers as text: are balances announced with their currency and sign, or is "−$42.17" rendered as
  a colour and a minus glyph a screen reader will skip? **Colour must never be the only carrier of
  owe-vs-owed** — that is both a WCAG failure and a money-comprehension failure.
- Charts: does `SpendingChart` have a text equivalent?

## 9. Email Deliverability / Notifications

**Owns:** `/api/notifications/send-emails`, `src/lib/email`, `NotificationSettings`, preferences.

- Every notification type actually has a template and a send path — **a queued type with no
  handler is silently discarded**, and no user ever learns their reminder didn't go out.
- No placeholder or lorem content on a path that reaches a real inbox.
- Retry has a cap; a permanently failing address is not retried forever.
- Preferences are honored, and there is an unsubscribe path.
- The cron gates on `requireCronSecret` and fails closed when the secret is unset.

## 10. Application Security

**Owns:** auth, authorization, tenancy, tokens, rate limits.

- **Authz matrix:** for each id-addressed route (expense, payment, comment, item, subscription,
  trip), can user X read/edit/delete user Y's object? Cross-tenant access must 404, not 403.
- **Mass assignment:** does a `PATCH` let a client set fields it shouldn't (payer, trip, currency,
  amount)? A mutable `payerId` is a money defect, not just a security one.
- **Tokens:** invite/reset/verification tokens hashed at rest, single-use, expiring; generated with
  a CSPRNG, not `Math.random()`.
- **Rate limits:** present on register/login/reset and on expensive routes (OCR); the key must not
  be client-controllable (`X-Forwarded-For` spoofing), and the store must evict.
- **Cron:** `requireCronSecret` fails closed. Verify, don't assume.
