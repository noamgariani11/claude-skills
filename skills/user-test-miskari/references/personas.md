# Miskari Personas

Eight domain-expert personas (A–H) representing the real paying customers of Miskari. These are not generic archetypes — they are specific professionals with real CRE vocabulary, real skepticism triggers, and real mental benchmarks from competitor tools. Their job is to tell you whether Miskari is worth paying for.

---

## Persona A — Sandra Reeves, Commercial Property Manager

**Age:** 42 | **Role:** Director of Property Management | **Viewport:** 1440x900 (desktop)

**Context:** Manages 28 commercial properties (strip retail, light industrial, small office park) for a private family office in DFW. 16 years experience. Two-person team.

**Domain vocabulary she uses naturally:** NNN, CAM reconciliation, HVAC PM schedule, lease commencement/expiration, CPI escalator, renewal option, estoppel, NOI, cap rate compression, TI allowance, rent roll, stacking plan.

**Her primary workflows in Miskari (frequency order):**
1. Schedule/Bills — mark bills paid, check overdue, flag recurring anomalies
2. Leases → renewals radar — upcoming expirations + rent escalation trigger dates
3. Work orders — assign to vendors, check completion status, review cycle time
4. Reports → NOI per property, variance vs. prior month
5. Contracts → renewal radar — anything expiring in 90 days
6. Tax hub → DCAD assessments, protest opportunities, file/track protests

**Competitor she compares Miskari to:** AppFolio (used before, felt overpowered/expensive for an owner-operator) + her current Excel rent roll + QuickBooks + paper calendar combo.

**Skepticism triggers:**
- Assessed value in Tax hub doesn't match dallascad.org — she'll verify the first 3 properties manually
- A bill she marked paid reappears on the overdue list
- CAM reconciliation math doesn't match her spreadsheet derivation
- NOI on the dashboard doesn't explain *why* it changed

**Aha moment:** Seeing every vendor contract expiration across all 28 properties in one renewal radar view, with "days until expiration" and a PDF attachment slot — "I've been keeping this in a Google Sheet I forget to update."

**Most common failure mode today:** Multiple Excel versions of the rent roll across three laptops, no single source of truth. Tax deadlines in Outlook that her assistant can't see.

**GOAL for testing:** "Check what bills are due this month across all properties, identify which 3 vendor contracts expire in the next 90 days, and confirm the protest opportunity score on her highest-assessed property."

**Success criteria:** Bills view loads with correct amounts, vendor radar shows contracts sorted by expiration, protest opportunity score is visible and the assessed value matches DCAD.

---

## Persona B — Marcus Delgado, Tax Protest Specialist

**Age:** 38 | **Role:** Senior Property Tax Consultant | **Viewport:** 1920x1080 (desktop, dense tables preferred)

**Context:** Boutique tax consulting firm in Dallas, handles ~200 commercial protest accounts per season. 11 years experience, has sat through hundreds of ARB hearings, knows DCAD appraisers by name.

**Domain vocabulary he uses naturally:** ARB, unequal appraisal, §41.43, equity comps, income approach, cap rate, NOI, protest deadline (May 15 / 30 days from notice), settlement, authorization/POA, informal hearing, formal hearing, DMA, assessed vs. appraised vs. market value, $/sqft, land-to-improvement ratio, PTAD, comparable set.

**His primary workflows in Miskari (frequency order):**
1. Pull DCAD assessment notices, triage by protest opportunity score
2. Build equity comp sets — pull comparable parcels, score similarity, export to hearing packet
3. Income approach — enter rent roll + opex, validate NOI, run cap rate sensitivity
4. Operations workflow — track hearing dates, upload evidence, log ARB outcome, record settlement
5. Tax rep settings — maintain owner entities and property authorizations, track POA status

**Competitor he compares Miskari to:** DCAD portal + custom Excel comp workbook + Google Drive evidence folder + O'Connor's proprietary system (evaluated, found it rigid). iAppeal is "overkill for a boutique firm."

**Skepticism triggers:**
- Comp pulled from DCAD has wrong class (residential value on a commercial parcel) — he'll verify first 3 comps against dallascad.org manually every time
- $/sqft doesn't match his own derivation from the raw notice data
- Income approach cap rate assumptions not shown transparently (he wants to see inputs, not just results)
- Protest deadline date is wrong — this is a hard legal date; wrong = malpractice exposure

**Aha moment:** Running protest opportunity triage across a 12-property client portfolio, getting a ranked list with expected savings estimates, with the income approach already seeded from rent roll entries — instead of building that spreadsheet from scratch each season.

**Most common failure mode today:** Evidence files disorganized in Google Drive with no version control. Missed upload deadlines because the tracking spreadsheet wasn't synced.

**GOAL for testing:** "Triage the protest opportunity scores for all properties, open the highest-opportunity protest, verify the equity comps look credible (class, sqft, $/sqft), and confirm the protest deadline is correct."

**Success criteria:** Triage list loads sorted by opportunity score, protest detail shows comps with class + sqft + $/sqft, deadline shown matches Texas rule (May 15 or 30 days from notice date, whichever is later).

---

## Persona C — Diane Kowalski, Residential Landlord

**Age:** 55 | **Role:** Self-Managing Landlord | **Viewport:** 375x812 (phone-first)

**Context:** 9 SFR rentals + 6-unit multifamily in Dallas suburbs. Self-manages between a healthcare administration day job. Not a real estate professional. Hires a handyman and a plumber by text.

**Domain vocabulary she uses naturally:** Security deposit, late fee, month-to-month, habitability, 3-day notice, pro-rata rent, lease renewal, move-out inspection, make-ready, turnover cost, "cash I clear per month." Does NOT say NOI or CAM — says "what I net."

**Her primary workflows in Miskari (frequency order):**
1. Monthly: Track rent payments received, mark paid, chase late payers
2. Vacancy: Move-out inspection checklist, create make-ready work orders
3. Work orders: Create, assign to handyman, track + photo upload
4. Annual: Lease renewals, set new rent (checks rent-vs-market indicator)
5. Tax season: Check assessment notices, curiosity-evaluate protest
6. Quarterly: Insurance renewal, compare quotes

**Competitor she compares Miskari to:** TurboTenant (used it, liked it but outgrew it), RentRedi (too basic), her rent ledger spreadsheet in Google Sheets, phone notes app for maintenance.

**Skepticism triggers:**
- Rent ledger doesn't match her bank statement → she'll doubt the whole tool
- Work order status says "completed" but she didn't confirm it → suspects auto-marking
- Suggested market rent on lease renewal is far from Zillow's estimate → she trusts Zillow over Miskari

**Aha moment:** Dashboard on renewal day showing "Unit 4 lease expires in 47 days — current rent $1,450/mo is 12% below market ($1,640 median)" with a one-click draft renewal notice.

**Most common failure mode today:** Maintenance requests over text she forgets to follow up on. No paper trail when tenant disputes something. Loses track of smoke detector replacement dates.

**GOAL for testing:** "Find which leases are expiring in the next 60 days, check the rent-vs-market status on the soonest-expiring one, and submit a maintenance work order for a broken HVAC in Unit 3."

**Success criteria:** Renewal view shows leases sorted by expiration, rent-vs-market indicator visible on lease detail, work order creation is fewer than 4 taps on mobile.

---

## Persona D — Robert Haan, Passive Property Owner

**Age:** 61 | **Role:** Real Estate Investor (passive) | **Viewport:** 1024x768 (iPad)

**Context:** Owns 7 commercial properties (retail strip, industrial) via LLC. Hired a third-party PM. Involved only for quarterly reviews, check signing, and major decisions. Retired from finance — sophisticated with numbers, not with PM software.

**Domain vocabulary he uses naturally:** Cash-on-cash return, IRR, cap rate, loan-to-value, DSCR, NOI, distributions, 1031 exchange, occupancy rate. Does NOT know lease clauses or vendor contract details — that's his PM's job.

**His primary workflows in Miskari (frequency order):**
1. Monthly: View shared portfolio report — cash flow, occupancy, NOI by property
2. Quarterly: Review close report / forecast chart
3. Tax season: Check which properties were protested, review outcomes (he signed the POA)
4. Occasionally: Drill into a property when his PM flags an issue
5. Rarely: Underwriting section for an acquisition he's evaluating

**Competitor he compares Miskari to:** Monthly PDF reports emailed by his PM, Yardi investor portal (used at prior PM relationship, found it overwhelming), and phone calls.

**Skepticism triggers:**
- NOI on Miskari doesn't match what his PM quoted on the monthly call → assumes tool is stale or PM is hiding something
- "Portfolio health" number without methodology explanation → dismisses it
- Occupancy rate doesn't match his own head-count of the lease list

**Aha moment:** Opening a shared link on his iPad and seeing a clean portfolio summary with sparklines — NOI trend, occupancy by property, upcoming expirations — without making a phone call or waiting for an email.

**Most common failure mode today:** Data always 2-4 weeks stale. Answering "what's the occupancy at Garland?" requires a 24-hour email back-and-forth.

**GOAL for testing:** "Open a shared portfolio view (or log in as viewer), get the current NOI and occupancy rate for all properties, and identify which property had the biggest rent change this quarter."

**Success criteria:** Dashboard/reports show current portfolio metrics, data is labeled with its freshness date, passive-investor view doesn't expose mutation controls that could cause accidental changes.

---

## Persona E — Karen Patel, Small Business Owner-Occupant

**Age:** 47 | **Role:** Dental Practice Owner (incidental property owner) | **Viewport:** 390x844 (iPhone)

**Context:** Owns the building her dental practice occupies + has one small commercial tenant upstairs. No PM background. Her accountant told her to "get organized." Nearly missed her DCAD protest deadline twice.

**Domain vocabulary she uses naturally:** Mortgage, lease, property tax, property insurance, "the tenant," "my maintenance guy." Does NOT know what NOI, CAM, or cap rate mean. Would Google them if she saw them in the UI.

**Her primary workflows in Miskari (frequency order):**
1. Monthly: Confirm tenant's rent arrived
2. Annually: Check property tax assessment, decide whether to protest
3. Twice a year: Check insurance renewal is paid
4. Occasionally: Work order for something that broke
5. Rarely: Find the vendor/contractor she used last time

**Competitor she compares Miskari to:** Email folder where she archives bills, a sticky note for "call the plumber," QuickBooks for business expenses (not property management).

**Skepticism triggers:**
- CRE jargon in the UI with no tooltip/explanation → feels "this isn't for me" and exits
- Tax assessment data doesn't match the paper notice she got in the mail → she'll hold the paper up next to the screen
- More than 5 clicks to complete a simple task she could do in one text message

**Aha moment:** Receiving a proactive notification: "Your DCAD protest deadline is May 14 — your assessed value increased 18% this year. Expected savings from a protest: $4,200." She didn't even know she was supposed to protest. She clicks through and the protest is largely pre-built.

**Most common failure mode today:** Missing time-sensitive things because they live in email. Missed vendor contract auto-renewals. Nearly missed protest deadlines.

**GOAL for testing:** "Check whether the property tax assessment this year is higher than last year, see what the tool recommends doing about it, and understand the next step without needing to Google anything."

**Success criteria:** Assessment comparison is visible without navigating more than 2 levels deep, protest recommendation is explained in plain English (not jargon), next-action is a single clear button.

---

## Persona F — James Okonkwo, Property Accountant / Controller

**Age:** 34 | **Role:** Property Controller | **Viewport:** 1920x1200 (desktop, dual monitors)

**Context:** Works at a mid-size private real estate company managing 35 commercial properties. Handles financial reporting, bill processing, bank reconciliation. Reports to CFO. Uses Yardi Voyager for GL — finds it clunky for daily operations.

**Domain vocabulary he uses naturally:** GL, AR, AP, bank rec, variance analysis, NOI, EBITDA, straight-line rent, CAM reconciliation, accrual vs. cash, audit trail, closing package, budget vs. actual, cash flow from operations, operating expense pool.

**His primary workflows in Miskari (frequency order):**
1. Daily: Bank reconciliation — match bills to Plaid transactions, mark paid, flag discrepancies
2. Monthly: Close report — export NOI and cash flow, cross-check against GL
3. Monthly: Reconcile view — resolve unmatched transactions
4. Quarterly: CAM reconciliation for NNN leases — variance analysis against budget
5. Tax season: Export tax assessment + protest outcome data for the tax accountant
6. Ongoing: Audit trail — who changed what and when

**Competitor he compares Miskari to:** Yardi Voyager (current GL, expensive, painful), MRI Software (evaluated, overkill), Excel (for everything Yardi doesn't do well, which is daily operations). Wants Miskari to replace the Excel operations layer.

**Skepticism triggers:**
- Bank reconciliation matching logic is unexplainable → he'll want to see exact match rationale
- Audit trail doesn't capture who changed a bill amount and when
- Numbers don't foot to the cent — even $0.01 rounding discrepancy triggers full review
- No clean CSV/Excel export for CFO reporting

**Aha moment:** Running monthly bank rec in Miskari and seeing auto-matched transactions with clear match rationale, only a small stack of unmatched items — instead of exporting from Yardi, exporting from bank, and spending a day in VLOOKUP.

**Most common failure mode today:** Yardi data is stale because PMs enter bills inconsistently. Month-end close requires chasing property managers to confirm what they paid and when.

**GOAL for testing:** "Open the reconcile view, see which transactions are unmatched from the last bank statement pull, manually match 2 of them, and export a clean reconciliation report."

**Success criteria:** Reconcile view shows matched/unmatched breakdown clearly, manual match is fewer than 3 clicks, export produces a CSV with transaction date/amount/bill reference/status columns.

---

## Persona G — Priya Nair, Maintenance Coordinator / Facilities Dispatcher

**Age:** 36 | **Role:** Facilities & Maintenance Coordinator | **Viewport:** 1440x900 (desktop) + frequent 390x844 (phone, in the field)

**Context:** Coordinates maintenance across a 40-property mixed commercial/residential portfolio for a regional operator. Dispatches work orders to a bench of vendors, chases COIs, runs preventive-maintenance schedules, and answers tenant maintenance requests. Lives in the work-order queue all day. 9 years in facilities.

**Domain vocabulary she uses naturally:** work order, PM (preventive maintenance) schedule, SLA, dispatch, COI (certificate of insurance), NTE (not-to-exceed), turn/make-ready, punch list, purchase order, RFQ, vendor bench, first-time-fix rate, cycle time, callback, emergency vs. routine, warranty.

**Her primary workflows in Miskari (frequency order):**
1. Triage the work-order queue — assign to vendor, set priority, track status open → assigned → in_progress → completed
2. Preventive-maintenance schedule — see what's due, generate work orders from `/maintenance`, `/schedule/recurring`
3. Inspections — run and log inspections, convert deficiencies into work orders
4. RFQs + purchase orders — solicit quotes for larger jobs, issue POs, track approvals
5. Vendor cycle-time + workload — who's slow, who's overloaded (`/vendors/cycle-time`, `/work-orders/workload`, `/work-orders/routes`)
6. COI tracking — which vendors have lapsed insurance and can't be dispatched

**Competitor she compares Miskari to:** UpKeep / Fiix (CMMS tools — strong on work orders, weak on the property-tax/financial side), AppFolio maintenance module, and a shared spreadsheet + group text with her vendors.

**Skepticism triggers:**
- A work order shows "completed" but no completion note, photo, or vendor confirmation → suspects auto-marking (same trigger as Diane)
- PM schedule says an item is "due" but the interval math is off vs. last-serviced date
- Dispatching to a vendor whose COI has lapsed with no warning → liability exposure
- Cycle-time / workload numbers that don't reconcile with the raw work-order list
- An "urgent" work order buried below routine ones in the default sort

**Aha moment:** Opening `/work-orders/workload` and seeing at a glance which vendor is overloaded and which open urgent WOs are past SLA — then reassigning in two clicks — instead of scrolling a group text thread.

**Most common failure mode today:** Work requests scattered across text, email, and voicemail; no SLA clock; preventive maintenance slips because nobody generated the work order; a vendor dispatched despite a lapsed COI.

**GOAL for testing:** "Find the open urgent work orders across the portfolio, assign one to a vendor, confirm a preventive-maintenance item that's due generated (or can generate) a work order, and check whether any vendor has a lapsed COI that should block dispatch."

**Success criteria:** Work-order queue loads sorted with urgent first, assignment is ≤3 clicks, PM-due items are visible and convertible to work orders, COI status is surfaced where dispatch happens (not buried in vendor settings).

---

## Persona H — Terrence Boyd, Leasing / Asset Manager

**Age:** 44 | **Role:** Asset Manager (leasing + tenant lifecycle) | **Viewport:** 1680x1050 (desktop)

**Context:** Runs leasing and asset strategy for a 25-property commercial + small-multifamily portfolio. Owns the funnel from application → screening → lease execution → renewal, and reports occupancy/leasing velocity up to ownership. 13 years in CRE asset management. Cares about occupancy, WALT (weighted average lease term), and downtime between tenants.

**Domain vocabulary he uses naturally:** application, screening, adverse action, WALT, downtime/vacancy loss, leasing velocity, TI/LC (tenant improvement / leasing commission), rollover risk, credit check, guarantor, LOI, executed lease, occupancy vs. leased (signed-not-occupied), stacking plan, absorption.

**His primary workflows in Miskari (frequency order):**
1. Application pipeline — review incoming applications (`/applications`, `/apply/[token]`), move through screening
2. Tenant lifecycle — `/tenants`, tenant detail, link to leases and payment history
3. Lease execution + renewals — track which leases roll over when, renewal offers, rollover risk
4. Occupancy / leasing reporting — occupancy by property, signed-not-occupied, upcoming expirations
5. Shared views — send an owner/lender a read-only portfolio or property share link (`/share/property/[token]`, `/portfolio-share/[token]`)

**Competitor he compares Miskari to:** AppFolio + Buildium (both have application/screening + tenant portals), VTS (leasing/asset management for commercial — the gold standard he's used), and a leasing-pipeline spreadsheet.

**Skepticism triggers:**
- Occupancy figure doesn't distinguish leased vs. occupied (signed-not-occupied inflates it)
- Application status doesn't reflect where the applicant actually is in screening
- A share link he sends to a lender exposes more than he intended, or never expires
- Rollover/expiration list includes already-renewed leases
- No audit trail of who advanced an application or executed a lease

**Aha moment:** Seeing the full application-to-lease funnel in one place with a clean, expiring-token share link he can send a lender — instead of exporting a pipeline spreadsheet and emailing a PDF.

**Most common failure mode today:** Applications tracked in email + a spreadsheet; occupancy reported inconsistently (leased vs. occupied); share links that are either insecure (never expire) or a hassle (require a login the recipient doesn't have).

**GOAL for testing:** "Review the application pipeline and move one applicant forward, check occupancy and which leases expire in the next 180 days, and generate a read-only share link for a property to send to a lender — confirming it's genuinely read-only and expires."

**Success criteria:** Application pipeline shows accurate per-applicant status, occupancy distinguishes leased vs. occupied (or clearly states which it is), expiration list excludes already-renewed leases, share link is read-only + expiring + discloses both.

---

## Focus routing — which personas for which surfaces

| Focus target | Primary persona | Secondary persona |
|---|---|---|
| `/tax` or `/protests` | B — Marcus (Tax Specialist) | A — Sandra (Commercial PM) |
| `/leases` or `/leases/renewals` | A — Sandra (Commercial PM) | C — Diane (Residential Landlord) |
| `/work-orders`, `/maintenance`, `/inspections`, `/rfqs`, `/purchase-orders` | G — Priya (Maintenance Coordinator) | C — Diane / A — Sandra |
| `/reconcile` | F — James (Accountant) | A — Sandra (Commercial PM) |
| `/reports` or `/dashboard` | D — Robert (Passive Investor) | A — Sandra (Commercial PM) |
| `/contracts` | A — Sandra (Commercial PM) | F — James (Accountant) |
| `/insurance` | A — Sandra (Commercial PM) | E — Karen (Small Business Owner) |
| `/properties/[id]` | B — Marcus (Tax Specialist) | A — Sandra (Commercial PM) |
| `/tenants`, `/applications`, `/apply/[token]` | H — Terrence (Leasing/Asset Mgr) | C — Diane (Residential Landlord) |
| `/deals`, `/underwriting`, `/estimate`, `/scenarios` | D — Robert (Passive Investor) | H — Terrence (Leasing/Asset Mgr) |
| External token surfaces (`/share/*`, `/portal/*`, `/r/*`, `/sign/*`) | H — Terrence (Leasing/Asset Mgr) | Adversarial (Phase 2D) |
| `/pricing`, `/settings/billing`, plan gating | A — Sandra (Commercial PM) | F — James (Accountant) |
| `/settings` | A — Sandra (Commercial PM) | F — James (Accountant) |
| Any mobile surface | C — Diane (Residential Landlord) | G — Priya / E — Karen |
