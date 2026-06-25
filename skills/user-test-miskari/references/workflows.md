# Miskari Critical Workflow Protocols

Six core workflows that define whether Miskari is worth paying for. Each protocol defines: the step-by-step path a domain professional takes, what data they expect at each step, what would cause them to lose trust, and what "success" means for a paying customer — not just task completion, but professional-grade output quality.

---

## Workflow 1: Tax Protest End-to-End

**Primary persona:** B — Marcus (Tax Specialist)
**Secondary:** A — Sandra (Commercial PM)
**Seasonal priority:** P0 during Jan–May; P1 rest of year

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
- Protest deadline: must exactly follow Texas rule — later of May 15 or 30 days after notice date. Wrong by even one day = professional distrust
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
