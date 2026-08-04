# Miskari Critical Workflow Protocols

Ten core workflows that define whether Miskari is worth paying for. Workflows 1–6 are the original paying-professional flows; 7–10 (maintenance dispatch, tenant/application pipeline, deal underwriting, external token surfaces) cover clusters that were untested through the first four runs and are where latent Criticals hide. Each protocol defines: the step-by-step path a domain professional takes, what data they expect at each step, what would cause them to lose trust, and what "success" means for a paying customer — not just task completion, but professional-grade output quality.

---

## Workflow 1: Tax Protest End-to-End

**Primary persona:** B — Marcus (Tax Specialist)
**Secondary:** A — Sandra (Commercial PM)
**Seasonal priority:** P0 while any seeded property's appeal window is OPEN (per its county rule — see Phase 0.3); P1 otherwise. For a Texas-only seed this is Jan–May, but Miskari is multi-jurisdiction now, so derive it from the properties, not the calendar.

### Steps
1. Navigate to `/tax` (redirects to `/tax/assessments`)
2. Verify the Triage section at top — assessments ranked by opportunity score
3. Identify a flagged assessment with a reason badge ("10%+ increase", "Below acquisition cost", or "Deadline in Nd")
4. Click "Auto-create protest" → confirm protest is created and pre-populated with property/assessment data
5. Navigate to the protest at `/protests/[id]`
6. Open operations panel → verify equity comps loaded (class, sqft, $/sqft, median highlighted)
7. Enter rent roll + opex in the income approach panel → verify NOI and cap rate compute correctly
8. Upload a piece of evidence (PDF) → check file type/size enforcement (PDF/JPG/XLS, 8 MB limit)
9. Verify the filing gate checklist shows which conditions are met/missing (comps loaded, evidence attached, authorization on file)
10. Check the protest deadline is correct (May 15 OR 30 days from notice date, whichever is later)
11. Print/download the hearing packet → verify it shows equity comps table with property value vs. median $/sqft gap

### Domain accuracy checks
- Protest/appeal deadline: must exactly follow **that property's county rule**. Texas (Dallas/DCAD etc.): later of May 15 or 30 days after notice date. Non-TX counties (Clark NV, Alameda CA, …): the county's own appeal-window rule (`appeal-window-overrides.ts` / `/settings/appeal-windows`). A May-15 date shown on a non-Texas property is WRONG. Wrong by even one day = professional distrust

  **Enumerate the deadline surfaces from the ROUTE LIST, not from habit — and check EVERY one.** The
  2026-07-17 calibration planted a deadline one day wrong and the tax specialist **missed it**: he
  verified the deadline on `/tax/assessments`, `/tax/opportunities` and `/protests/[id]` (all correct,
  all agreeing), then opened `/properties/[id]` for other fields and never re-checked the deadline
  rendered there. Three surfaces agreeing is not proof — **agreement across surfaces that share a code
  path proves nothing about the surface that does not.**

  The known deadline surfaces, and why they can disagree:

  | Surface | Source |
  |---|---|
  | `/tax/assessments`, `/tax/opportunities`, `/protests/[id]` | the assessment's stored `protestDeadline` |
  | **`/properties/[id]` appeal panel** | **`storedDeadline` short-circuits the derivation entirely** and renders an "Authoritative" badge — a *different* code path |
  | `/settings/appeal-windows`, `/tax/preflight`, `/leases/[id]`, the iCal feed (`calendar-events.ts`) | derived via `appeal-process.ts` / `appeal-window-overrides.ts` |

  A deadline check that has not compared the **stored** value against the **derived** value has not
  actually tested the later-of rule.
- Equity comps: each shows $/sqft with source date; median is labeled "§41.43(b)(3) median" or equivalent; property's $/sqft is highlighted vs. median
- Cap rate inputs visible: the income approach panel must show the cap rate assumption, not just the final value. Professionals want to verify the input
- Evidence enforcement: DCAD rules are PDF/JPG/XLS only, 8 MB max — the UI must display these limits and enforce them
- Auto-create: must pre-populate the property account number, tax year, and assessed value from the linked assessment record

### Trust-breakers (any of these = Critical finding)
- Protest deadline shown for a Texas property is wrong
- Estimated savings is $0 or blank when equity comps show clear gap
- Auto-create creates an empty protest that must be manually populated
- Income approach NOI calculation doesn't explain its formula (revenue sources - expense categories)
- Comps show wrong class (e.g., residential value on a commercial parcel) — this is the most common DCAD integration failure
- Filing gate shows "Ready to file" when no evidence is attached

### Success for a professional
- Protest created in one click, pre-populated, with comps already loaded from ParcelCache or discovery
- Hearing packet PDF downloadable with equity comps table, income approach summary, and property account number
- Status path is clearly visible: draft → filed → informal_scheduled → informal_done → arb_scheduled → settled
- Protest settlement saves actual reduction amount and shows it on the assessment list as "saved $X"

### Edge cases to probe
- Property has no equity comps (ParcelCache empty) → show "Comps not yet loaded — trigger discovery?" with a button, not a blank table
- Assessment has no noticed value → flag should still appear if deadline is near
- Protest submitted after deadline → warn, do not silently allow
- Non-Dallas county → "Comps discovery available in Dallas only" message (not a crash or blank)

---

## Workflow 2: New Property Onboarding

**Primary persona:** A — Sandra (Commercial PM)
**Secondary:** B — Marcus (Tax Specialist)

### Steps
1. Navigate to `/properties/new`
2. Enter an address in the CAD auto-fill field → watch autocomplete fire via `/api/properties/geocode`
3. If single parcel match: verify auto-applied fields: sqft, year built, property type, appraised value, acquisition year
4. If multiple parcels: confirm the picker appears (not silent selection)
5. Verify the appraised value label says "acquisition-year value" with Texas non-disclosure caveat visible
6. Submit the form
7. On the property detail page: check the CAD record section shows property class, account number, legal description
8. Watch for enrichment job status banner — public records fan-out in progress
9. After enrichment completes: verify at least USGS elevation, Census ACS, FEMA flood zone populated
10. Trigger comps discovery (if Dallas property): verify comps panel loads with ≥3 parcels showing $/sqft
11. Attach a document → confirm it uploads and appears in the documents list

### Domain accuracy checks
- County selector shows only verified counties (from `SUPPORTED_COUNTIES`) — no unverified counties in the dropdown
- Appraised value is labeled as acquisition-year value (not current-year) — per DESIGN.md, drawn from CAD market value in the acquisition year
- Property type defaults correctly: commercial sub-types (office/retail/industrial/mixed-use/hospitality/land) for commercial; residential sub-types (single-family/condo/townhouse/multifamily/apartment/manufactured) for residential
- State field automatically updates when county selected (same-named counties Orange NY ≠ Orange FL)
- Document upload enforces 20 MB cap and magic-byte MIME sniff (browser Content-Type is untrusted)

### Trust-breakers
- Appraised value shown is current-year (not acquisition-year) — misleads on acquisition cost basis
- Supported county in dropdown but CAD scrape fails silently, leaving fields blank with no error
- Address auto-fill returns residential parcel data for a commercial address
- State field doesn't update when county changes (Orange NY + FL same-name ambiguity)
- After submit, user lands on a blank property page with no confirmation that enrichment is running

### Success for a professional
- Single-address lookup auto-fills 5+ fields with visible "from CAD [date]" badge
- Public records section shows data from at least USGS, Census, and FEMA flood zone after enrichment
- Comps panel (Dallas): ≥3 comparable parcels, each with class, address, $/sqft, appraised value
- Document upload succeeds and appears immediately in the documents list with filename and size

### Edge cases to probe
- Address not in any verified county → form still works with fully manual entry (no CAD features, no crash)
- Parcel has mixed classes (residential + commercial improvements) → picker must appear, not silent auto-select
- DCAD hosts timeout → fallback to `dallascad.org` (not `dcad.org`) or show retry prompt, never 500

---

## Workflow 3: Lease Renewal & Rent-vs-Market

**Primary persona:** A — Sandra (Commercial PM)
**Secondary:** C — Diane (Residential Landlord)

### Steps
1. Navigate to `/leases` → look for "Renewal action required" banner (leases with endDate ≤ 90d)
2. Verify banner shows urgency color coding: red ≤30d, amber ≤60d, accent ≤90d
3. Click a lease → open `/leases/[id]`
4. Check the "Rent vs. Market" callout: Above/At/Below + $/sqft/yr vs. county median + comparable count
5. If "too few comparables" (< 2 in zip), confirm the muted hint appears instead of a hard number
6. Navigate to `/leases/renewals` → verify market rent suggestion (computed as `zipMedian * buildingSqft`)
7. Click "Suggested market rent" to auto-fill the new-rent input
8. Submit the renewal offer → verify `renewalStatus = offered` and lease drops off the action-required banner

### Domain accuracy checks
- Rent-vs-market math: $/sqft/yr = (monthly rent × 12) ÷ building sqft. NOT $/sqft/mo. Professionals quote annual sqft rates in CRE
- Market rent suggestion on renewals page: labeled "Suggested market rent: $X/mo" — clicking must fill the monthly rent input field
- `scoreLeaseRenewal()` risk badge: "At risk" only if payment history is irregular OR relationship is very new (≤3 months), not just because the lease is expiring soon
- Comparable count shown: "Based on N active leases in [zip]" — transparency about the data set

### Trust-breakers
- $/sqft/yr computation wrong (divides by month instead of year, or uses leaseable sqft instead of building sqft)
- Market rent hint shows for zip with only 1 comparable (minimum should be 2 per the code notes)
- "At risk" badge on a lease with 3 years of perfect on-time payments and 60 days remaining
- "Send offer" action changes status but doesn't create an email record or note — gives false impression a notification was sent to the tenant

### Success for a professional
- Renewal pipeline sorts by soonest expiry, color-coded correctly
- Clicking the market rent suggestion correctly fills the monthly rent field
- After "Send offer": renewalStatus = offered, lease drops off the "action required" banner immediately, audit trail shows the action

### Edge cases
- Lease on a property with no `buildingSqft` → rent-vs-market shows "Building sqft missing — add in property settings" (not a crash or $0/sqft)
- Expired lease (endDate in past, status still active) → show "Xd overdue" in red in the banner, still appear in the renewal pipeline
- Multiple leases on same property, different zips → each benchmarks independently against its own zip

---

## Workflow 4: Vendor Contract Renewal Radar

**Primary persona:** A — Sandra (Commercial PM)
**Secondary:** F — James (Accountant, COI tracking)

### Steps
1. Navigate to `/contracts`
2. Look for "Contracts ending soon" section (horizon: 120 days)
3. Verify contracts sorted by end date ascending with urgency indicators
4. For each expiring contract: check `noticeRequiredDays` is translated into an actual calendar date ("Notice required by [date]")
5. Check if notice deadline has already passed → expect red "Past notice deadline" indicator
6. Click a contract → open detail
7. Use "Quick extend" button → verify end date moves by exactly 1 calendar year (not 365 days) and status stays "active"
8. Upload a new signed contract document → confirm it appears in the contract's documents list
9. For a utility contract: verify link to `/utilities/compare` is present on the contract detail

### Domain accuracy checks
- Notice deadline: `endDate - noticeRequiredDays` as a calendar date, displayed as "Notice by [MM/DD/YYYY]" — not just the raw `noticeRequiredDays` number
- 1 calendar year extension: Feb 28 → Feb 28 next year (not +365 days, which would be Feb 27 in non-leap years)
- Service type vocabulary: "landscaping", "HVAC maintenance", "security", "elevator", "pest_control" — CRE industry standard terms
- Monthly estimate column: dollars if populated, clear dash if not (no $0 which implies the contract is free)

### Trust-breakers
- Notice deadline computed without accounting for timezone offset (off by 1 day vs. the contract notice date)
- Quick extend adds 365 days, not 1 calendar year — catches experts on Feb/March contracts
- "Active" filter includes expired contracts that were never manually closed
- Contract expiring in exactly 121 days appears in the 120-day radar (off-by-one at boundary)

### Success for a professional
- All contracts expiring ≤120 days visible, sorted by urgency, with explicit notice deadline dates
- After Quick extend: end date updated, status unchanged, success toast appears
- Document upload appears immediately and is labeled with contract name + date

### Edge cases
- Contract with `noticeRequiredDays = 0` → no "Notice by" date shown (don't show "Notice by [endDate]")
- Vendor has no COI on file → separate vendor COI alert appears independently of contract expiry
- Contract has neither `endDate` nor `noticeRequiredDays` → appears in contracts list but NOT in renewal radar

---

## Workflow 5: Bank Reconciliation

**Primary persona:** F — James (Property Accountant)
**Secondary:** A — Sandra (Commercial PM)

### Steps
1. Navigate to `/reconcile`
2. See the Plaid transactions section or CSV upload option
3. Pull recent bank transactions (or upload CSV)
4. Review auto-match proposals from `proposedMatches()`: transaction ↔ bill pairings with match confidence
5. Confirm correct matches
6. For unmatched transactions: see full bank description, amount, date — not truncated
7. Manually match 2 unmatched transactions to bills using the match interface
8. Mark truly unrelated transactions as "Ignored" (e.g., ATM withdrawal)
9. Verify "N unmatched transactions" count on the dashboard decrements correctly
10. Export/print reconciliation report in CSV with columns: date, amount, description, matched bill, status

### Domain accuracy checks
- Match must be amount-exact to the cent for accounting purposes — not "within tolerance" unless explicitly disclosed
- Vendor name normalization: "RELIANT ENERGY 0023847" should match vendor "Reliant Energy" via normalized string match
- Date: bank transaction dates should display in local time, not UTC (a $5k mortgage paid 11:30 PM UTC on Jan 31 is Jan 31 in CT, not Feb 1)
- Rent matches (income transactions from tenants) must be segregated from expense matches — mixing them is a bookkeeping error
- After confirming a match: the linked bill's `paidDate` or status should update, not just the bank record

### Trust-breakers
- Amount mismatch still marked as "matched" (accountants notice cent discrepancies immediately)
- Ignoring a transaction doesn't decrement the "N unmatched" dashboard count
- Bank descriptions shown as raw Plaid merchant codes without normalization (e.g., "ACH DEBIT 291847019" gives no information)
- CSV upload fails silently when column headers don't match — no error, just empty import
- Export CSV is missing one of the required columns (date / amount / description / bill reference / status)

### Success for a professional
- ≥80% of bank transactions auto-matched to bills
- Unmatched transactions section clearly shows: full description, amount, date, "Ignore" and "Match to bill" CTAs
- Dashboard "Bank Feed" stat drops to 0 (or disappears entirely) after all transactions are matched or ignored
- Exported CSV opens cleanly in Excel with all expected columns, amounts formatted as numbers not strings

### Edge cases
- Two bills same vendor, same amount, same month → match algorithm must not double-assign one transaction
- Foreign currency transaction in bank statement → system warns, does not silently convert
- Plaid connection expired → reconnect prompt shown immediately on the reconcile page, not an empty table

---

## Workflow 6: Portfolio Health Dashboard

**Primary persona:** D — Robert (Passive Investor)
**Secondary:** A — Sandra (Commercial PM)

### Steps
1. Log in → land on `/dashboard`
2. Check headline stat grid: Overdue bills, Due 30d, Contract renewals 120d, Active protests, Maintenance, Rent Roll, Occupancy, Work Orders, Insurance, Leases 180d, NOI, Bank Feed
3. Review Portfolio Health score (0–100) with issue breakdown (critical/warning/info items)
4. Review Cash Flow Forecast card (3 months forward)
5. Check NOI by property table (last month vs. prior month delta)
6. Click an overdue-bills stat → verify navigation to `/schedule?view=bills` (filtered correctly)
7. Navigate to `/reports` → check portfolio benchmarks section and forecast chart

### Domain accuracy checks
- NOI formula: income collected (rent payments received) minus paid bills for the period — NOT accrued/scheduled amounts
- NOI delta labeled by month: "NOI · May" with "+$X / -$X vs prior mo" (not just a number)
- Occupancy: leased sqft ÷ total portfolio sqft (not unit count) — real estate professionals always use sqft-based occupancy
- Cash Flow Forecast labeled as "projected" (uses rent roll base rent, not actual collected) — this distinction must be visible
- Portfolio Health score: green ≥80, yellow 60–79, red <60; penalizes data completeness gaps (properties with no sqft, no assessments)
- Tax season card (visible March–July only): shows estimated savings tiers — "urgent" / "strong" / "moderate"

### Trust-breakers
- NOI shows positive when portfolio has more bill spend than rent collected (suggests bills not all categorized as expenses)
- Occupancy shows 100% when any property has no active leases (buildings with sqft=0 should be excluded from denominator)
- Cash flow forecast shows identical income and expense bars 3 months in a row with no variation — looks like a placeholder
- Portfolio Health score is 100 with obvious data gaps (missing sqft, no assessments loaded, no vendors) — data completeness must factor in
- "Overdue" bills stat includes bills manually marked paid but not yet reflected in the aggregate
- "Leases 180d" stat includes already-renewed leases (renewalStatus = accepted or offered) — should exclude these

### Success for a professional
- Dashboard loads in < 2s with all stat cards populated (no loading spinners that persist)
- Clicking any stat card navigates to the filtered list with the filter applied correctly
- NOI by property table sorted by highest NOI descending, color-coded (green positive / red negative)
- Portfolio Health issues link to `/settings/data-quality` with specific actionable items listed
- Forecast chart shows a meaningful curve (not a flat line) based on known bill schedules

### Edge cases
- Portfolio with 0 properties → "Getting Started" card with 3 setup steps, stat grid hidden (not showing 0s)
- All leases paid this month → Rent collection shows "All N leases paid this month" (green, not empty/missing)
- Tax season card outside March–July → no card shown even if protests are in progress
- `unmatchedBankTxnCount = 0` → Bank Feed stat cell absent from the grid entirely (conditional render, not showing "0")

---

## Workflow 7: Maintenance Dispatch & Preventive Maintenance

**Primary persona:** G — Priya (Maintenance Coordinator)
**Secondary:** C — Diane (Residential Landlord) / A — Sandra (Commercial PM)

### Steps
1. Navigate to `/work-orders` → confirm the queue sorts urgent/emergency first, not by creation date
2. Open an urgent open work order → assign it to a vendor; verify status advances open → assigned and the vendor sees it
3. Navigate to `/maintenance` → find a preventive-maintenance item that's due (nextDueAt in the past) → generate a work order from it (or confirm one exists)
4. Navigate to `/work-orders/workload` and `/vendors/cycle-time` → check the numbers reconcile with the raw work-order list
5. Navigate to `/inspections` → confirm an inspection can log a deficiency and convert it to a work order
6. Check COI/insurance status where dispatch happens → a vendor with a lapsed COI should be flagged before assignment
7. Optionally: `/rfqs` + `/purchase-orders` → solicit a quote and issue a PO for a larger job; verify approval routing

### Domain accuracy checks
- PM due-date math: nextDueAt = lastServicedAt + intervalDays. An item marked "due" must actually be past that date
- Work-order status is the real lifecycle: open → assigned → in_progress → on_hold → completed (not "todo/doing/done")
- Cycle-time = completed_at − created_at across completed WOs; workload = open WOs per vendor. Both must foot to the underlying list
- "Completed" requires a completion note/photo/vendor confirmation — never auto-marked
- Urgent/emergency priority actually reorders the default queue

### Trust-breakers
- A work order shows "completed" with no evidence of completion (auto-marked) — same distrust as a lying status badge
- PM item flagged "due" whose interval math says it isn't (or vice versa) — the schedule can't be trusted, so PM slips
- A vendor with a lapsed COI is dispatchable with no warning (liability exposure)
- Cycle-time/workload aggregates that don't reconcile with the work-order list (aggregation trust — same family as the analytics leak)
- Urgent WOs buried below routine ones in the default sort

### Success for a professional
- Queue triage-ready: urgent first, assignment ≤3 clicks, status advances visibly
- PM schedule surfaces what's due and converts to work orders without re-keying
- COI status appears at the point of dispatch, not buried in vendor settings
- Workload/cycle-time views reconcile with the raw list and help rebalance vendors

### Edge cases to probe
- Work order with no vendor assigned → clear "unassigned" state, still counts in the queue
- PM item with no lastServicedAt → shows "never serviced", not a bogus due date
- Emergency work order created after hours → still surfaces at top; no silent drop
- Vendor with no COI on file at all (vs. lapsed) → both block/flag dispatch distinctly

---

## Workflow 8: Tenant Application & Screening Pipeline

**Primary persona:** H — Terrence (Leasing/Asset Manager)
**Secondary:** C — Diane (Residential Landlord)

### Steps
1. Navigate to `/applications` → review the incoming application pipeline; confirm each row's status reflects where the applicant actually is
2. Open an application (`/applications/[id]`) → advance it one step in screening; verify the status change persists and is audited
3. Follow the applicant → `/tenants` / tenant detail → confirm the link to lease + payment history is intact
4. Inspect the public application intake `/apply/[token]` → confirm it's a clean, scoped form (unauthenticated) that doesn't leak org data
5. From a tenant/lease, check occupancy reporting distinguishes leased vs. occupied (signed-not-occupied)

### Domain accuracy checks
- Application status is the real pipeline stage (received → screening → approved/adverse-action), not a generic flag
- Advancing an application writes an audit-trail entry (who moved it, when)
- Occupancy distinguishes leased vs. occupied, or states clearly which metric it is
- The public `/apply/[token]` intake exposes only the intake form — no portfolio/tenant data inferable from the token or URL params

### Trust-breakers
- Application status doesn't match the applicant's real screening stage (pipeline lies)
- Advancing/executing has no audit trail (a controller/asset manager can't trace decisions)
- `/apply/[token]` leaks org or other-applicant data, or a guessed/expired token still renders
- Occupancy conflates leased and occupied, inflating the number

### Success for a professional
- The full application → screening → lease funnel is visible in one place with accurate per-applicant status
- Advancing an applicant is auditable
- Public intake is scoped and safe; occupancy reporting is unambiguous

### Edge cases to probe
- Malformed/guessed `/apply/[token]` → fails closed (404), does not leak
- Expired application-request token → clear expired state, not a live form
- Applicant with no linked property yet → pipeline still coherent
- Adverse-action / rejected applicant → handled distinctly, not silently deleted

---

## Workflow 9: Deal Underwriting & Acquisition Scenarios

**Primary persona:** D — Robert (Passive Investor)
**Secondary:** H — Terrence (Leasing/Asset Manager)

### Steps
1. Navigate to `/deals` → review the pipeline; open a deal (`/deals/[id]`)
2. Navigate to `/underwriting` → enter/confirm the assumptions (purchase price, NOI, cap rate, financing)
3. Verify the returns math: cap rate = NOI ÷ price; cash-on-cash and DSCR if shown
4. Navigate to `/scenarios` → run a sensitivity (change cap rate or rent) and confirm outputs move correctly
5. Use `/estimate` if present → sanity-check a quick valuation against the underwriting

### Domain accuracy checks
- Cap rate = NOI ÷ purchase price, shown with both inputs visible (not just the result)
- Cash-on-cash = pre-tax cash flow ÷ equity invested; DSCR = NOI ÷ debt service — each traceable to inputs
- Boundary handling: price = 0 must not divide-by-zero / NaN; absurd inputs handled gracefully (this is also a Phase 2D probe)
- Scenario outputs change monotonically and correctly when an input moves

### Trust-breakers
- Returns math that doesn't tie to the stated inputs (a finance-literate investor re-derives it in his head)
- A "portfolio health" or valuation number with no methodology
- Divide-by-zero / NaN on boundary inputs
- Scenario sliders that don't move the output, or move it the wrong way

### Success for a professional
- Underwriting shows inputs AND derived returns, each auditable
- Scenarios produce a believable sensitivity, not a flat line
- Boundary inputs are handled without a crash

### Edge cases to probe
- Deal with no financials yet → empty-but-coherent underwriting, not 0s presented as real
- Price = 0 or NOI = 0 → graceful, no NaN
- Scenario with an extreme cap rate (0.5% / 50%) → still renders a sane (if unrealistic) number

---

## Workflow 10: External Token Surfaces (shares, portals, request links)

**Primary persona:** H — Terrence (Leasing/Asset Manager) for the happy path; **Adversarial (Phase 2D)** for the attack path
**Secondary:** D — Robert (Passive Investor, the recipient of a share)

This workflow is BOTH a first-impression UX surface (what a tenant/vendor/lender sees, unauthenticated) AND the highest-stakes adversarial surface. Test both faces every run once a token exists in the seed.

### Steps (happy path)
1. From a property/portfolio, generate a read-only share link (`/share/property/[token]`, `/portfolio-share/[token]`)
2. Open the link in a clean/incognito context (no auth) → confirm it renders read-only, discloses read-only + expiry, exposes no mutation controls
3. Open a tenant/vendor-facing link (`/portal/[token]`, `/r/[token]/maintenance`, `/r/[token]/quote`, `/r/[token]/survey`, `/sign/[token]`, `/documents/request/[token]`) → confirm the recipient sees only what they should

### Domain accuracy checks
- The shared payload exposes only owner-configured fields — no other-org data inferable from the token or URL params
- Expiry and read-only status are disclosed to the recipient
- The unauthenticated view is a clean, professional first impression (this is what a lender's first taste of the operator's tooling looks like)

### Trust-breakers (attack path — Phase 2D probes these)
- A malformed or guessed token renders data instead of failing closed (404/expired)
- An EXPIRED or revoked token still renders
- A share leaks fields the owner didn't configure, or lets a recipient infer another org's data via URL params
- A "read-only" share exposes a mutation control that actually works
- The `org/<orgId>/` document-key guard can be bypassed from a token surface

### Success for a professional
- Send-a-link is one action; the recipient needs no login; the link is genuinely read-only and expires
- Both the sender (Terrence) and the recipient (Robert) trust it — Robert loved the disclosed read-only/no-login/30-day-expiry in prior runs

### Edge cases to probe
- Token for a since-deleted/soft-deleted parent → clean gone state, not a stale render
- Two different token types with a swapped token → each fails closed
- Very old token (past expiry window) → expired, re-issue prompt to the owner only
