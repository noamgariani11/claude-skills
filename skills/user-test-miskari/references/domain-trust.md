# Miskari Domain Trust Signals

This reference defines the specific trust signals, skepticism triggers, and competitor benchmarks that real estate professionals use to evaluate whether Miskari is worth their money. These are NOT generic UX heuristics — they are domain-specific checkpoints that only someone who has worked in commercial real estate would apply.

---

## What "trust" means in CRE software

Commercial real estate professionals are professional skeptics. They make financial decisions based on the data in their tools. A wrong number doesn't just mean a bad UX experience — it means a missed protest deadline, a bad lease renewal price, or an incorrect financial report that the CFO questions. These professionals have been burned by bad tools before. They will actively look for reasons NOT to trust Miskari.

Trust in Miskari is earned on three axes:

1. **Data accuracy** — the numbers match what the professional would verify from primary sources
2. **Provenance** — the data shows where it came from and how fresh it is
3. **Professional fluency** — the app speaks their vocabulary and respects their expertise

All three must hold simultaneously. A beautifully designed app with wrong math loses faster than an ugly app with accurate data.

---

## Critical trust signals (presence = trust; absence or violation = distrust)

### Financial math integrity
- NOI computation is visible and auditable: income sources listed, expense categories listed, derived NOI matches manual calculation
- Cap rate shown with both the NOI and the value used in the denominator
- Rent-vs-market shows $/sqft/yr (annual per square foot), not $/sqft/mo — CRE industry standard is annual
- Money values toe to the cent in the reconciliation view — even a $0.01 discrepancy triggers a full review from an accountant
- CAM reconciliation variance column shows the delta, not just the totals — professionals want to see what moved

### Data provenance
- Every CAD-sourced number is labeled: "Source: DCAD · [date]" or "As of 2025 tax roll"
- Comps show their pull date — a comp from 2022 is not useful for a 2025 protest
- Market rent comparables show the count and zip: "Based on 8 active leases in 75234"
- Cash flow forecast is labeled "projected" (uses scheduled amounts, not actuals)
- Portfolio Health score links to its methodology (what's counted as critical vs. warning)
- Public records enrichment shows which sources loaded vs. failed

### Deadline precision
- Protest/appeal deadline is the exact date **for that property's county**: in Texas, later of May 15 OR 30 days after notice date; in other supported jurisdictions (Clark NV, Alameda CA, …), that county's own appeal-window rule (`appeal-window-overrides.ts`). A hardcoded "May 15" on every property — or a May-15 date on a non-Texas property — is a trust failure
- Contract notice deadline is a calendar date, not "you have N days" — professionals need to put it on a calendar
- Lease expiration shows days remaining, not just the end date
- "Action required" banners disappear immediately when the action is taken — stale banners train users to ignore them

### Professional vocabulary
- Property type uses CRE terms: office, retail, industrial, mixed-use, hospitality, land (not "commercial building 1")
- Lease terms: commencement date, expiration date, rent escalator, CAM, renewal option — not generic "start/end"
- Work order statuses: open, assigned, in_progress, on_hold, completed — not "todo, doing, done"
- Vendor contracts: service type labels match industry vocabulary (landscaping, HVAC maintenance, elevator, pest_control)
- Assessment notices: appraised value, assessed value, land value, improvement value — distinct concepts displayed distinctly
- Protest outcomes: reduction, withdrawal, no_change, dismissed — not "won/lost"

### Multi-tenant integrity (non-negotiable)
- No property, tenant, lease, bill, or document from org A is visible when logged in as org B
- Shared report token only exposes fields the owner configured — no ability to infer other org data from URL parameters
- Audit trail shows who changed what and when — a controller expects to be able to trace any number change to a user action

---

## Skepticism triggers by persona

### Sandra (Commercial PM) — what makes her check her spreadsheet
1. Assessed value in Tax hub doesn't match dallascad.org (she'll open DCAD in a second tab)
2. A bill she marked paid appears on the Overdue stat on the dashboard
3. NOI changes month-over-month without any explanation (she'll look for a categorization error)
4. Vendor contract end date is off by even one day from her paper contract
5. A work order she created is missing from the vendor's assigned work list

### Marcus (Tax Specialist) — what makes him hand-verify every comp
1. Comp pulled from DCAD shows the wrong class (residential value for a commercial parcel)
2. $/sqft median differs from his own VLOOKUP on the same dataset by more than $1
3. Income approach NOI can't be traced to its inputs (he'll want to see each rent line and each expense)
4. Protest deadline doesn't account for notice date — he knows some clients get notices after April 15
5. Filing gate says "ready" when he hasn't attached evidence — he knows DCAD rejects incomplete packages

### Diane (Residential Landlord) — what makes her go back to her phone notes
1. Rent payment ledger doesn't match her Wells Fargo statement (she'll check immediately)
2. Work order says "completed" — she'll text the handyman to confirm before trusting the status
3. Suggested market rent is >15% different from Zillow's Zestimate for the zip (she trusts Zillow as her reference)
4. Mobile interface requires more than 5 taps to log a maintenance request
5. Notification arrives but she can't tell which property or tenant it's about without clicking through

### Robert (Passive Investor) — what makes him call his PM
1. NOI on Miskari doesn't match the number his PM mentioned on the quarterly call
2. Portfolio Health score is high but one of his properties is obviously empty (he checks occupancy)
3. "Portfolio health" or "NOI" shown without methodology — he'll assume someone made a number up
4. Shared report link expires or requires a login he can't remember
5. Occupancy rate differs from what he'd count manually from the lease list

### Karen (Small Business Owner) — what makes her close the tab
1. Terminology she doesn't understand with no tooltip: "ARB", "CAM reconciliation", "§41.43"
2. Tax assessment data doesn't match the paper notice she received (she has the physical paper)
3. More than 5 clicks to do something she expected to be simple
4. A screen that looks like a spreadsheet with 20 columns — she's not an accountant
5. No feedback that something was submitted ("did that go through or not?")

### James (Property Accountant) — what makes him rebuild it in Excel
1. Bank reconciliation matching logic can't be explained — he needs to know the match algorithm
2. Audit trail doesn't capture who changed a bill amount and when (he'll need this for audit purposes)
3. Numbers don't foot to the cent — $0.01 discrepancy triggers full review
4. Export CSV has amounts stored as strings not numbers (Excel can't sum them without manual correction)
5. Two bills with same vendor/amount in same month auto-matched to the same bank transaction (double-booking)

### Priya (Maintenance Coordinator) — what makes her go back to her group text
1. A work order shows "completed" with no note, photo, or vendor confirmation (auto-marked)
2. A PM item flagged "due" whose interval math (lastServiced + interval) says it isn't — the schedule can't be trusted
3. A vendor with a lapsed COI is dispatchable with no warning
4. Cycle-time / workload aggregates that don't reconcile with the raw work-order list
5. Urgent/emergency work orders buried below routine ones in the default sort

### Terrence (Leasing/Asset Manager) — what makes him fall back to his pipeline spreadsheet
1. Occupancy that conflates leased and occupied (signed-not-occupied inflates the number)
2. Application status that doesn't match the applicant's real screening stage
3. A share link he sends a lender exposes more than configured, or never expires
4. Rollover/expiration list that includes already-renewed leases
5. No audit trail of who advanced an application or executed a lease

---

## Competitor benchmarks

Professionals don't evaluate Miskari in isolation — they compare it to what they've used before or what they know exists. When a persona hits a "competitor comparison moment," classify the outcome using these benchmarks:

### AppFolio (main competitor for commercial PM)
- **AppFolio advantage Miskari must beat:** Unified lease + maintenance + billing in one place, owner portal, mobile app
- **AppFolio weakness Miskari can win on:** $250+/month minimum, pricing by unit (penalizes small portfolios), no property tax protest module, no utility rate comparison
- **Parity check:** Vendor contact management, document storage, basic financial reporting

### Buildium (residential-focused)
- **Buildium advantage:** Tenant portal, online rent collection, stronger residential lease management
- **Buildium weakness Miskari can win on:** No commercial support, no tax protest, weak vendor/contract management, no CAD integration
- **Parity check:** Maintenance work orders, basic lease tracking, owner reporting

### Yardi Voyager (enterprise CRE)
- **Yardi advantage:** Full GL, true accounting, deep CRE analytics, strong market data integrations
- **Yardi weakness Miskari can win on:** $$$$ enterprise pricing, 6-month implementation, requires a consultant, overkill for 5–50 property portfolios
- **Parity check:** Portfolio health analytics, multi-user access control, document management

### Excel / Google Sheets (the real incumbent)
- **Excel advantage:** Infinite flexibility, zero learning curve for the person who built the model, free
- **Excel weakness Miskari can win on:** No auto-refresh from DCAD, no protest workflow, no work order tracking, no document storage, no audit trail, no sharing without email, no mobile
- **Win signal:** Any Miskari feature that would require a new spreadsheet tab, a formula lookup, or a manual update is a win against Excel
- **Loss signal:** If a professional says "I'll just do it in Excel" after seeing a Miskari flow, Miskari lost that comparison

### TurboTenant / RentRedi (residential DIY)
- **TurboTenant advantage:** Free tier, online applications, e-lease signing, tenant portal
- **TurboTenant weakness Miskari can win on:** No commercial support, no tax protest, no vendor/contract management, no CAD integration, no financial analytics
- **Parity check:** Basic lease tracking, maintenance requests, rent reminders

### UpKeep / Fiix (CMMS — Priya's maintenance benchmark)
- **CMMS advantage:** Deep work-order + PM-schedule tooling, mobile-first for field techs, asset histories, SLA clocks
- **CMMS weakness Miskari can win on:** No property-tax/protest side, no financial/NOI reporting, no lease/tenant lifecycle — a maintenance silo, not a property platform
- **Parity check:** Work-order queue, preventive-maintenance schedules, vendor dispatch, cycle-time reporting. If Miskari's work-order flow is materially worse than UpKeep's, Priya notices immediately

### VTS (Terrence's leasing/asset-management benchmark)
- **VTS advantage:** Best-in-class commercial leasing pipeline, stacking plans, deal/tenant funnel, portfolio analytics for institutional CRE
- **VTS weakness Miskari can win on:** Enterprise pricing + complexity, overkill for 5–50 property operators, no tax-protest module, no day-to-day maintenance/billing ops
- **Parity check:** Application → screening → lease funnel, occupancy (leased vs. occupied), rollover/expiration tracking, shareable read-only views for owners/lenders

---

## The "phone call test"

The ultimate benchmark for any Miskari feature: **would this information require a phone call or email to get without Miskari?**

- "What vendor do we use for HVAC at the Plano property?" → one question to the PM or a folder dive
- "When does the security contract renew?" → one email to the operations manager
- "What's the protest deadline for the Garland warehouse?" → a 20-minute DCAD portal session
- "Are any of my leases expiring in the next 90 days?" → 30 minutes of Excel VLOOKUP

If Miskari answers any of these in < 10 seconds, that's a professional win. If Miskari requires more steps than the phone call, it loses to the phone call.

---

## Data freshness standards (by domain)

| Data type | Max acceptable staleness | What to show if stale |
|---|---|---|
| DCAD assessed value | 1 tax roll year | "2024 roll — 2025 not yet loaded" |
| Equity comps ($/sqft) | 60 days | "Comps as of [date] — re-run discovery?" |
| Utility rate comparison | 30 days | "Rates as of [date] — market changes weekly" |
| Market rent (portfolio median) | 30 days | "Based on leases as of [date]" |
| Bank transactions (Plaid) | 24 hours | "Last synced [time] — sync now?" |
| Public records (Census, FEMA, etc.) | 6 months | "Enrichment last updated [date]" |
| Insurance premium | 1 year (renewal cycle) | "Policy expires [date]" |
| Property info (sqft, year built) | Always show source and date | "From DCAD scrape [date]" |

Any number shown without a freshness label when it has a meaningful staleness risk = [UNLABELED] finding.
