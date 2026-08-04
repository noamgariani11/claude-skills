# Planted-defect calibration — measuring the FALSE-NEGATIVE rate

## Why

This skill measures false positives obsessively. `known-issues.json` catalogues every phantom finding it
ever produced — the `classForType` misread, the cold-compile "hangs", the combobox that Playwright
couldn't drive. That discipline is why the reports are trustworthy.

It measures false negatives **not at all**.

Nothing in the protocol asks: *what did the personas miss?* The run-3 Critical — a cross-org data leak —
sat latent for **two full runs** because nobody happened to visit `/reports?tab=analytics`. It was found
by luck (a persona wandered in), not by method. How many more are latent right now? The honest answer is
that nobody knows, and with the current protocol nobody can know.

That makes every calibration decision blind. Is a ~700-word persona budget enough to force a real
re-derivation of the math, or does it produce a persona who *glances* at the number and moves on? Are
three personas enough? Does the domain-accuracy check actually happen, or does it get skipped under
budget pressure and reported as "ACCURATE" on vibes? **You cannot answer any of these from the reports,
because a persona who misses a bug and a persona who correctly finds nothing produce identical output.**

The fix is the standard one for any detector: **feed it known defects and see what it catches.** This is
mutation testing, pointed at the test harness instead of the code.

## Protocol

Run **every 5th full run**, or on demand with `--calibrate`.

### 1. Plant, on a throwaway worktree

```bash
git worktree add /tmp/mb-calib -b calib/throwaway-$(date +%s)
```

**Never plant on the working branch.** Never merge a plant. The worktree is discarded at the end — that
is the entire safety model, so do not compromise it for convenience.

Plant exactly **3** defects drawn from the real failure taxonomy — the classes this product actually
produces, not exotic ones. One from each tier:

| Tier | Example plant | Should be caught by |
|---|---|---|
| **Statutory / Critical** | Protest deadline off by one day (break the later-of rule) | The 2A domain gate — this is a hard fail |
| **Financial math** | `$/sqft` divided by month instead of year; or NOI silently including a financing category | The persona who re-derives (Marcus / James / Robert) |
| **Provenance / trust** | Strip the freshness label off a material number (assessed value, comps) | Any persona applying `[UNLABELED]` |

Rotate the specific plants each calibration so the roster cannot overfit to them.

**At least one plant per calibration MUST sit on an alternate code path — a stored value, an override
table, a cache, or a denormalized column — rather than the primary derivation.** This is not a
preference; it is where the only confirmed miss actually lived. On 2026-07-17 Marcus checked the
deadline on three surfaces that all derive it, found them correct and agreeing, then opened
`/properties/1` — whose appeal panel renders a **stored** `protestDeadline` with an "Authoritative"
badge through a path that never calls the derivation — and did not re-check it there. The primary path
is the well-lit one; every persona already walks it. The alternate path is where a real defect survives
a confident-looking three-surface check.

Known alternate paths in this codebase worth rotating through: `storedDeadline` on the property appeal
panel, `appeal-window-overrides.ts`, `ParcelCache` comps, denormalized `property.units`, and any
`*Cents` column written at one site and read at another.

Since 2026-07-19 the cross-surface disagreement check (`crossSurfaceChecks` in `sweep-config.json`) is
**mechanical and runs every sweep**, so a plant that makes two surfaces disagree should now be caught by
the script for free. That raises the bar rather than lowering it: **a plant the script catches does not
count as a persona catch.** Score it separately (`caught_by: "sweep"`), and keep at least one plant that
the script *cannot* see — a value that is wrong identically everywhere, which only domain knowledge can
flag (an implausible rate, a broken statutory rule, a stripped provenance label). The script tests
consistency; only the personas test *correctness*.

#### 1b. VERIFY EVERY PLANT IS OBSERVABLE BEFORE FIELDING ANYONE (mandatory)

**An unobservable plant scores as a miss and silently inflates your miss rate.** On 2026-07-17, **2 of 3
initial plants were duds** and would have reported a false 0/3 catch rate:

- A plant in `appeal-process.ts` (`later_of_fixed_or_offset`) **never renders**, because a stored
  "Authoritative" `protestDeadline` short-circuits the derivation on every surface that shows a deadline.
- A plant in `leases/renewals` `rentPerSqft` **never renders**, because the only seeded lease sits behind
  a "Too few comps" empty state.

So: after planting, **capture the target route and diff the rendered number against the unplanted app**
before fielding a single persona. Cheap and decisive:

```bash
MB_BASE=http://localhost:<calib-port> node tools/user-test-harness/mbcapture.cjs /tmp/plant <route>
MB_BASE=http://localhost:<base-port>  node tools/user-test-harness/mbcapture.cjs /tmp/base  <route>
```

If the plant does not change the rendered output, **relocate it and re-verify** — do not field it.
Prefer planting at the **display site you have actually seen render** (the value the persona reads) over
a deep pure function that a fallback, an override table, or an empty state may shadow.

Beware the capture race: a **first hit can return nav-only text (~335 bytes)**, which looks like a blank
page. Always re-hit warm, or `waitForSelector('table')`, before concluding a plant is invisible.

#### 1c. Plant where the persona will actually walk

Each plant belongs on a route in an assigned persona's own documented workflow, so the catch is honest —
never steer a persona toward it. On 2026-07-17 the plants sat on `/properties/1` (Marcus), `/tenants`
(Terrence) and `/vendors/cycle-time` (Priya), all routes already in their cards. The two that were on a
persona's *primary* surface were caught; the one on a surface Marcus visited for a *different reason* was
missed — which is itself a finding about surface coverage, not about the persona.

### 2. Field blind

Run the **normal** roster, the **normal** protocol, against the planted worktree. The persona agents,
the technical reviewer, and the adversarial agent are **never told** a calibration is running. Telling
them destroys the measurement — you would be testing whether they can find a bug they know exists, which
is not the question.

### 3. Score

- **Catch rate** = planted defects found / planted. Per-tier and overall.
- **Who caught what** — which persona/agent found each, and at which step. Record `caught_by`:
  `"persona"` / `"tech-review"` / `"adversarial"` / `"sweep"`. **A plant the mechanical sweep catches
  does not count toward the persona catch rate** — the script is testing consistency, the personas are
  testing correctness, and blending them would let a script improvement disguise a roster regression.
- **Misses** — for each uncaught plant, the diagnostic question: *why didn't the protocol surface it?*

**Disclose plant contamination in the report.** A planted number does not just sit there waiting to be
found — it *changes the run's qualitative output*. On 2026-07-17 both Priya's and Terrence's
trust-tipping PULSE sentences quoted a **planted** figure, so their narratives described a product that
does not exist. Each also had an independent real finding, so both landed on Conditional either way and
the verdict was unaffected — but that had to be checked, not assumed.

So on any calibration run: (a) mark every persona quote that references a planted value, (b) re-derive
the domain-trust rating **with the planted findings removed** and report both, and (c) if removing them
would change the rating or the verdict, say so explicitly. A calibration run's verdict is only
publishable once it has been shown to survive the plants being taken out.

### 4. Act on a miss — a missed plant is a defect in the METHOD

This is the whole point, and it is where the value is. A miss is never "the persona had a bad day":

| Miss | What it proves | Fix |
|---|---|---|
| Wrong deadline not caught | The 2A domain gate is not actually being executed | Make the deadline hand-derivation a mandatory, quoted step in the agent brief |
| Wrong `$/sqft` not caught | Personas are *reading* numbers, not *re-deriving* them | Force an explicit "show your arithmetic" step; the budget may be too tight to allow real derivation |
| Missing freshness label not caught | The `[UNLABELED]` tag is decorative | Require an explicit provenance verdict per material number, not an optional tag |
| Nobody visited the surface at all | Coverage rotation has a hole | The route belongs in the cluster ledger |

Each fix goes into the SKILL / references immediately. **The plant that got missed becomes a permanent
protocol upgrade** — that is how the loop compounds instead of just repeating.

### 5. Record + destroy

```json
"calibration": {
  "last_run": "2026-07-11",
  "planted": 3,
  "caught": 2,
  "catch_rate": 0.67,
  "by_tier": { "statutory": "caught", "financial_math": "caught", "provenance": "MISSED" },
  "missed": ["freshness label stripped from assessed value - no persona re-checked provenance on /tax/assessments"],
  "protocol_changes": ["2C now requires an explicit provenance verdict per material number"]
}
```

```bash
git worktree remove /tmp/mb-calib --force
git branch -D calib/throwaway-<ts>
```

**Verify the plants are gone before the next real run.** A surviving plant would poison every subsequent
finding — and it would look exactly like a real regression, which is the worst possible failure mode for
this skill. Confirm with `git status` on the working branch and a diff against the last known-good SHA.

## Reading the number

A catch rate below ~0.8 means the reports' "no [WRONG] findings" verdicts are **not evidence of
correctness** — they are evidence of not-looking. Say that plainly in the report. It is more valuable
than any individual bug: it recalibrates how much confidence every past clean verdict deserved.
