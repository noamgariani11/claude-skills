# Critical Workflow Protocols

The journeys that decide whether SplitSquad is a product. Each has a protocol, a set of accuracy
checks, and a definition of failure. Run the ones your persona owns.

---

## Workflow 1 — The core loop (the trunk)

**create trip → add members → add expenses → see balances → settle up.** If this doesn't work
end-to-end, nothing else matters. **Persona A owns it and gates the run on it.**

1. **Trip exists?** Create one: name, dates, currency, members. How many steps before an expense
   can be entered? Count them.
2. **Add an expense.** Note what is *required* before the number can be saved. A form that demands
   a category before an amount has its priorities inverted for the actual use case (standing at a
   till).
3. **Split it** — exercise all four types (`equal`, `shares`, `percentage`, `exact`) plus one with
   tax and tip and one with an excluded participant (weight `0`). **Capture inputs and outputs
   together** (`money-integrity.md` capture protocol).
4. **Balances.** Do they update immediately? Does `BalanceCard` agree with `CrossTripBalanceView`
   and `GlobalBalanceCard`? **Three surfaces disagreeing about one debt is the bug the user
   experiences as "this app can't decide what I owe" — `high`.**
5. **Settle up** → Workflow 2.

**Failure = any step where the user cannot proceed for a reason that isn't an honest mode boundary
(no DB, no Stripe key, no Vision credentials).**

---

## Workflow 2 — Settle up (Persona D + bookkeeper)

1. Open the settle-up plan. Record it verbatim: every transfer, from, to, amount.
2. **Apply it on paper.** Every member must land at zero (I9). If anyone doesn't, that is the
   finding of the run.
3. **Count the transfers.** ≤ n−1 for n non-zero members.
4. **Reload and re-derive.** Same plan? A non-deterministic plan (ties with no tie-break) is a
   trust defect even when both versions are valid.
5. **Record a payment** and re-check every balance. Sign convention per I8 — a flipped sign
   *doubles* the imbalance and still looks plausible.
6. **Edge cases, in order:** overpay a debt (does the surplus flip direction by the right amount?);
   pay yourself; pay a negative amount; pay in a currency other than the debt's.
7. **The honesty pass:** after settling, does anything claim *settled* while the ledger nets
   non-zero? Does a `pending` Stripe payment render as paid? Does the Venmo/Zelle handoff imply the
   app *sent* money it can only *record*?
8. `/api/settlements` is a **documented stub**. An honest "not available" is a mode boundary and
   **not** a defect. A stub returning a fabricated success shape is `critical`.

---

## Workflow 3 — Multi-currency (Persona C + FX expert)

1. Set a trip currency different from the base. Add expenses in a **third** currency.
2. Check the layering (I12): expense currency → trip currency → base. Once per hop, exactly.
3. **The unsupported-currency test.** Get a code outside the six-code table into the math — via the
   API, via persisted state, or via any path the picker doesn't guard. If it converts **1:1
   against USD**, that is money invented from nothing: `critical`, and silent.
4. **Provenance:** can a user tell whether a number used a live rate or the 2024 static fallback,
   and as of when? Check what `/api/currency-rates` actually returned this session (it caches for
   an hour and falls back silently).
5. **Historicity:** note a finished trip's total, force a rate refresh, re-read it. If it moved
   with no new expenses, decide whether the app ever claimed otherwise — and hold it to its claim.
6. **Round-trip** A→B→A within a cent (I10).

---

## Workflow 4 — Invite, preview, and joining (Persona E + privacy expert)

1. Issue an invite (`/api/trips/[id]/invite`), open `/invite/[token]` **signed out, on mobile**.
2. Open `/trip-preview/[token]` the same way. **Diff the API response against what the page
   renders** — the leak is usually in the payload, not the UI. Other members' emails, unrelated
   trips, or ids that address other endpoints are `high`.
3. **Lifecycle:** accept twice; accept expired; accept after removal from the trip. Each must fail
   **specifically**. A generic error here reads as "the app is broken."
4. Accept, and check the new member appears in balances **without retroactively changing anyone's
   share of expenses entered before they joined** — unless the app explicitly says it does.
5. In localStorage mode, credential sign-in cannot work (no DB). Report the *experience*: does the
   app say so honestly, or fail generically so the user thinks they mistyped their password?

---

## Workflow 5 — Recurring expenses & subscriptions (Persona F)

1. Create a recurring expense at each frequency: `weekly`, `monthly`, `yearly`. Create a shared
   subscription.
2. Drive `/api/expenses/recurring/process` and `/api/subscriptions/process` (they need
   `CRON_SECRET`; `requireCronSecret` **fails closed** if it's unset — that's correct behavior).
3. **Does each frequency actually fire?** A frequency that silently never generates a charge is
   `high` and invisible by construction — nothing appears, so nobody notices.
4. **Idempotency:** run the processor twice for the same period. Two charges for one month of rent
   is a money defect; a failed insert that permanently skips the period is the same defect wearing
   the opposite sign.
5. **Dates:** month-end in a 30-day month, leap day, a user outside UTC. A bill dated "the 1st"
   must fire on the 1st for them too — or the app must say which clock it uses.
6. **Backfill:** an overdue recurring expense — does it generate every missed occurrence, or one
   per run with a drifting date?
7. **Notification:** does anything tell her it happened? A queued notification with no handler is
   silently discarded and no user ever learns their reminder didn't send.

---

## Workflow 6 — Receipts and itemization (persona A/B + OCR skeptic)

1. Scan a clean receipt via `ReceiptScanner` → `/api/scan-receipt` (Google Vision; without
   credentials the failure must be honest, not a zeroed receipt).
2. **The confirmation question:** does the extracted total arrive as a *fact* or a *proposal*? A
   scanned number that silently becomes the subtotal is `high` — nobody re-reads a number that
   already looks right.
3. Itemize (`ItemizedReceiptModal`, `/api/expenses/[id]/items`): assign items to specific people.
   **Shares must still sum to the expense total, including tax and tip** (I2).
4. **Unassigned items:** who pays? An item assigned to nobody that quietly leaves the total is
   `high`.
5. Adversarial inputs: a non-receipt, a foreign-currency receipt, an image with two totals.

---

## Workflow 7 — Editing and audit trail (Persona B)

1. Edit an expense **after** balances have been read and a settle-up plan produced.
2. Every downstream balance must rewrite correctly, and any prior "settled" state must re-open
   honestly. Silently keeping a settled badge over changed numbers is `critical` (dimension 6).
3. `EditHistoryModal` / `/api/expenses/[id]/history`: does the trail say what actually changed, or
   just that something did? Can B trace a balance delta to the edit that caused it?
4. Delete an expense that a payment was made against. What happens to the payment?

---

## Workflow 8 — Persistence and the two-tab problem (durability expert)

1. Enter an expense; close the tab **inside the debounce window**. Measure the window; state what
   is lost.
2. Fill localStorage toward its ~5MB ceiling with receipt images. When the write fails, does the
   app notice? **A "saved" UI over a failed write is `critical`** — the user's state and the app's
   state have diverged and only one survives a reload.
3. Hand-edit persisted state into an older/broken shape (trip with no `expenses`, expense with no
   `participants`). Degrade or crash?
4. An intentionally **empty** trips array on reload — is it ever mistaken for "no data" and
   replaced with seed data? Restoring demo trips over a user's cleared state destroys real work.
5. Two tabs, both editing. Last-write-wins over a whole state blob loses one tab's work.
   **Reproduce it before flagging it.**

---

## Workflow 9 — Export and reporting (Persona B)

1. Export CSV and PDF; run `/api/trips/[id]/report`.
2. **Does the export reconcile with the screen?** Same totals, same shares, same balances, to the
   cent. An export that disagrees with the UI is the version that gets forwarded to the group —
   `high`.
3. Are currencies labeled in the export, or are numbers bare?
4. Does the export leak other members' data beyond what the recipient should hold (privacy expert
   overlaps here)?

---

## Workflow 10 — The adversarial money pass (Phase 2E, last)

Ordered by expected value:

1. Unknown-currency expense (`JPY`, `THB`, `CHF`) → is it 1:1'd against USD?
2. Weight `0` in each split type → charged exactly zero?
3. `exact` weights that don't sum to the total → who absorbs the delta, and is it visible?
4. `percentage` weights summing to 250 → normalized, or is money created?
5. $0.01 split three ways; $100 split three ways ×20 → does the error accumulate?
6. Payment larger than the debt; to yourself; negative; in another currency.
7. Add a second trip, reorder trips → do cross-trip balances change? (Order-dependence invents
   mutual debts.)
8. Settle, then edit the underlying expense → does "settled" re-open?
9. Invite token replay / expiry / post-removal.
10. Mass-assignment probes on `PATCH` routes (payer, trip, currency, amount).
11. **Rate-limit and auth chaos LAST** — the limiter is in-memory and per-instance, and shared with
    the personas' own traffic.
