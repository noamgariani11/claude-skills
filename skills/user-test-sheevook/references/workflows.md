# Critical Workflow Protocols

The journeys that decide whether Sheevook is a product. Each has a protocol, a set of accuracy
checks, and a definition of failure. Run the ones your persona owns.

---

## Workflow 1 — The core loop (the trunk)

**create → tailor → approve → schedule → publish → analyze.** This is CLAUDE.md's stated core
loop. If it doesn't work end-to-end, nothing else matters. **Persona A owns it and gates the run
on it.**

1. **Brand exists?** No brand = no `brandContext` = generic output. Setting up the brand is step
   zero, and how painful it is *is* a finding (a marketer will not fill in 40 fields).
2. **Create** at `/content/new`. Note: what does it ask for? Does it ask for the *idea* or make
   you write the post? (A tool that makes you write the post has not saved you anything.)
3. **Tailor** → per-platform variants. **Capture every artifact verbatim** (`output-quality.md`).
4. **Approve** → is the approval gate real? Try to skip it (that's the Adversarial's job, but note
   if it looks skippable).
5. **Schedule** → does it land on `/calendar` in the right slot? Are `postingWindows` and
   `minGapHours` from `platforms.ts` respected? Schedule into the past — what happens?
6. **Publish** → **without a live OAuth connection this MUST fail honestly.** A fake "posted!" is
   a `critical` defect (CLAUDE.md forbids it). An honest, clear failure is correct behavior and is
   **not** a bug — do not score it as one.
7. **Analyze** → see Workflow 3.

**Failure = any step where the user cannot proceed for a reason that isn't an honest external
prerequisite.**

---

## Workflow 2 — Build an ad campaign (Persona C + ad-capable platform experts)

1. `/campaigns` → create a campaign. Pick an **objective** (`awareness | traffic | engagement |
   leads | launch | retention` — `lib/types.ts`).
2. `/ads` → pick a network (`lib/ads/networks.ts`), a **campaign type / ad format**
   (`lib/ads/formats.ts`), attach creative.
3. **Accuracy checks (the ones that decide C's trust):**
   - Is every campaign type in `formats.ts` one you would actually see in that ads manager?
     An invented one is a `high` trust defect. Ground it — `domain-accuracy.md`, and note most ad
     rows are `VOLATILE` and must be re-verified before you flag them.
   - Does the objective→campaign-type mapping make sense, and is it stated anywhere?
   - Budgets in **integer cents** (CLAUDE.md).
   - Does the creative meet the real format spec (ratio, duration, headline char limits)?
4. **Structure check:** objective → campaign type → ad set → creative → measurement. Name the
   missing link if there is one.
5. Meta is the live adapter (`lib/ads/meta.ts`); others may be honest "coming soon" — that's a
   product boundary, not a bug. But an *un-honest* one (pretends to work) is `critical`.

---

## Workflow 3 — The analytics learning loop (Persona E)

CLAUDE.md and the repo claim a closed loop:

> connect GA4/Meta/X analytics → append-only `performance_snapshots` → pure `lib/performance`
> distills → **grounds generation / ideation / ad-optimize**

**Test whether the loop actually closes.** This is E's signature move and the finding is big
either way.

1. `/platforms` → connect an analytics source (`ConnectionsSetup`, credential families — one Meta
   app key powers FB/IG/Insights/Ads). Drive as far as the OAuth wall honestly allows.
2. Are snapshots captured? Is the table genuinely append-only?
3. Does `lib/performance` distill them into something a human can read?
4. **The closing question: does anything in the generated output demonstrably change because of
   performance data?** Generate before, generate after, diff. If nothing changes, the "learning
   loop" is a dashboard, and the claim is marketing. `high`.
5. **The honesty check:** does any displayed metric appear that the platform API never returned?
   An invented metric is `critical` (CLAUDE.md: "never invent metrics for a real post").
6. Shortlinks (`/l/[slug]`) and `/api/attribution` — does click → attribution actually work?
   (Known: a bad slug 302s to `/` **intentionally**. Verified false positive. Don't re-flag.)

---

## Workflow 4 — The community reply queue (Persona F)

1. `/community` → reply drafts for replies-to-others (the `EngagementProvider` boundary).
2. `/approvals` → is approval a real gate? Can a draft reach a platform unreviewed?
3. **The mod test** on every draft: would a moderator remove this? would it get downvoted? would
   it get the account banned?
4. Check CTA modes (off / soft). Does a "soft" CTA still read as marketing to a native? On Reddit
   and HN, *any* CTA usually does.
5. **Reddit is a live OAuth publisher** — the app can genuinely post. That means it can genuinely
   get the user banned. A generated self-promo Reddit comment is `critical`, not `medium`.

---

## Workflow 5 — Connections & setup (Persona E)

1. `/platforms` → `ConnectionsSetup` groups one-time app registration by **credential family**
   (Meta → Facebook/Instagram/Insights/Ads from one app key).
2. Can a non-developer marketer get through this? Registering a Meta developer app is a genuinely
   hard ask. Does the app acknowledge that, and guide?
3. Honest failure: platforms without a live connection must return a clear error, never a fake
   success.
4. If `MANAGED_CREDENTIALS=1`, the dev-app UI is hidden and the user just clicks Connect. Note
   which mode you observed — the UX verdict is completely different between them.
5. Tokens are server-only. A token reaching a client component is `critical`
   (use `PublicConnection`).

---

## Workflow 6 — Brand voice propagation (Persona D)

1. `/settings` → set a **deliberately sharp** brand: strong POV, high edge, specific customer
   voice (`lib/voice`, `lib/positioning`, `lib/strategy`).
2. Generate across ≥3 platforms.
3. **Does the voice survive tailoring?** If LinkedIn sands the edges off until the post is
   indistinguishable from every other LinkedIn post, the edge dial is decorative. `high`.
4. **The decoration test:** for each brand field, does changing it produce an *observable* change
   in output? Fill, regenerate, diff. A field with no observable effect is decoration — flag it by
   name.
5. `/compare` → does it actually help you see the difference between variants?

---

## Workflow 7 — YouTube packaging (the YouTube expert)

1. Generate a YouTube variant. **The variant table has NO title column — the title is a `Title:`
   line inside `content`.** (Repo fact.)
2. Verify the packaging assist produces: title angles, chapters, thumbnail brief, benchmarks.
3. Round-trip it: does the `Title:` line survive an edit → save → reload without corrupting the
   body? This parsing scheme is fragile by construction — probe it.
4. A YouTube "post" with no title is not a YouTube post. `high`.

---

## Workflow 8 — Workspace discovery: the hallucination test (Persona A + Adversarial + D)

**The highest-stakes workflow in the product, and the easiest to get catastrophically wrong.**

`lib/discovery` reads the user's real public website once at workspace creation and derives the
brand profile, local market, category playbook, platform norms, and competitive set. That distilled
result is serialized into `brandContext()` and lands in **EVERY AI call at once**.

CLAUDE.md states two **non-negotiables**. Both are directly testable, and both are `critical` if
violated — because a fabricated fact here doesn't just appear once, it **propagates into every
piece of content the tool ever generates for that brand**:

1. **"It never invents a fact, price, quote, or competitor"** — facts with numbers absent from the
   source are dropped.
2. **"It never overwrites a brand field the user filled in"** — it *proposes*, the user *applies*.

### The protocol (do this properly — it is the single best test in this skill)

1. Point discovery at a **real, small, known site** whose content you can read in full yourself.
   Read the source page first, so you know exactly what facts genuinely exist on it.
2. Run discovery. Then **diff the derived profile against the source page, fact by fact.**
   - Any **price** not literally on the page → `critical`.
   - Any **quote** not literally on the page → `critical`.
   - Any **competitor** not named on the page and not otherwise grounded → `critical`.
   - Any **number** (headcount, founding year, customer count, % claim) that isn't on the page →
     `critical`. CLAUDE.md says numbered facts absent from the source are *dropped* — so any that
     survive are a direct violation.
3. **The adversarial version:** point it at a **sparse or near-empty page** (a one-line landing
   page, a parked domain, a 404). A hallucinating extractor fills the vacuum — this is where
   invention shows up if it's going to. A confident, detailed brand profile derived from a page
   with nothing on it is the finding of the run.
4. **The overwrite test (D owns this):** fill in brand fields *by hand first*, then run discovery.
   Every hand-filled field must survive untouched. Discovery may only *propose*. If it silently
   overwrites a user's positioning statement, that is `critical` — it destroys user work.
5. Check the deterministic-first claim: the crawl/extract/classifier/local/norms are supposed to be
   **pure and free**, with at most **two** AI calls that only *refine*. Does it still produce a
   usable profile with `ANTHROPIC_API_KEY` unset? It must.
6. Never wire discovery into a surface by hand — it lands via `brandContext()`. A surface that
   reads discovery directly is an architecture finding.

Also test the plain UX: a marketer types their domain and waits. How long? Is there honest
progress? What happens on a site that won't crawl (JS-only, robots.txt block, timeout)? A silent
failure that yields an empty brand is worse than a loud one.

---

## Workflow 9 — The five content lenses (Persona B)

The app now ships five independent, pure, zero-AI-cost linters. B should test each **by feeding it
content it should catch**, not by admiring the UI:

| Lens | Lib | Feed it |
|---|---|---|
| Stress-test (adversarial review) | `lib/stress-test` | a draft with an obvious unsupported claim |
| Boring / POV | `lib/voice` (boringScore) | deliberately beige, agreeable copy |
| GEO / citation-readiness | `lib/geo` | copy with no citable facts or structure |
| Conversion | `lib/conversion` | high reading-level copy, a "scarecrow" CTA, ableist phrasing, brand-in-text |
| Tailoring validate | `lib/tailoring/validate` | copy that breaks a platform's own rules |

**A lens that passes content it was built to catch is a `high` finding** — a linter that doesn't
fire is worse than no linter, because it grants false confidence. Conversely, check the false-
positive direction: does the conversion linter flag *good* punchy copy as too-low-reading-level?
Does boringScore punish a genuinely sharp, short post? An inverted lens (punishes good, passes bad)
would be the finding of the run.

---

## Workflow 10 — Studio / stress-test / rewrite (Persona B)

1. Write a **deliberately beige** draft. Feed it to the stress-test panel (`lib/stress-test`,
   `/api/stress-test`).
2. Does the resilience score reflect reality? Are the fixes actionable, or generic advice?
3. Does the `lib/voice` boringScore fire the "reads generic" warning?
4. Then write a **genuinely sharp, edgy** draft. Does the app try to sand it down? A tool that
   punishes the good draft and passes the beige one is inverted — and that would be the finding of
   the run.
5. Does the GEO linter (`lib/geo`) give real citation-readiness advice or boilerplate?
