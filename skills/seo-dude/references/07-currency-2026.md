# 07 — Currency Check (verified July 2026)

**Load this on every run.** The rest of the references encode durable mechanics
distilled from a 2023 source. This file is the state of the world, and it is the
only one with an expiry date.

**If today is more than ~3 months after July 2026, re-verify §1 and §2 with
`WebSearch` before relying on them.** Say in the report which items you verified
and which you carried forward unchecked.

**Evidence tiers.** Use these labels in the report:

| Tier | Meaning | May you state it as fact? |
|---|---|---|
| **DOCUMENTED** | Stated by the platform in its own docs/blog | **Yes** |
| **KNOW** | Multiple independent measurement studies agree | Direction yes, number with attribution |
| **BELIEVE** | Practitioner consensus, no primary confirmation | **No** — label it |
| **FOLKLORE** | Repeated with no traceable origin | **Never** |

---

## 1. Corrections to the other reference files

**These override anything in `01`–`06` that contradicts them.**

| Ref | Stale claim | Correction | Tier |
|---|---|---|---|
| `01` §10 | FID ≤ 0.1s | **INP replaced FID 2024-03-12. Target INP ≤ 200ms** | DOCUMENTED |
| `01` §10 | CWV scored per-page, per-metric | **March 2026 core update reportedly moved to a site-wide composite score.** Changes audit method — see §3 | BELIEVE |
| `01` §7, §9 | `FAQPage`/`HowTo` earn rich results | **HowTo desktop retired Sept 2023; FAQ retired 2026-05-07.** Seven more types retired June 2025. **Both remain valid Schema.org types Google still parses** — see §4 | DOCUMENTED |
| `01` §7 | IndexNow — "verify Google's status" | **Resolved: Google has not adopted it and has signalled no plan to.** Bing, Yandex, Seznam, Naver do (~80M sites) | DOCUMENTED |
| `02` §5, `05` §5 | Helpful Content is a standalone update | **Folded into the core algorithm March 2024.** Google no longer ships separate HCU releases. The *mechanics* still apply; the *name* is gone | DOCUMENTED |
| `05` §3 | Prohibited-tactics ledger | **Add site reputation abuse** ("parasite SEO"), in force 2024-05-05 — see §5 | DOCUMENTED |
| `05` §5 | Algorithm ledger ends 2022 | **Three years missing** — see §2 | DOCUMENTED |
| `04` §3 | Google News/Discover guidance | **First standalone Discover core update, Feb 2026** — see §6 | DOCUMENTED |
| all | Zero-click / CTR figures | **Superseded** — see §7 | KNOW |

---

## 2. Post-2023 algorithm timeline

| Date | Update | Effect |
|---|---|---|
| **2024-03-05** | March 2024 core + new spam policies | Largest core update to that point. **HCU absorbed into core.** Targeted ~40% reduction in unhelpful content |
| **2024-03-12** | INP replaces FID | Latency of *all* eligible interactions, worst-case |
| **2024-05-05** | Site reputation abuse policy | "Parasite SEO" |
| **2024-05** | AI Overviews general rollout | The structural change |
| **2025-03 / 06 / 12** | Three core updates | Dec 2025 ran 18 days across holiday trading |
| **2025-06** | Seven structured-data types retired | Book Actions, Course Info, Claim Review, Estimated Salary, Learning Video, Special Announcement, Vehicle Listing |
| **2026-02-05 → 02-27** | **Discover core update** (first standalone) | See §6 |
| **2026-03** | Spam update + core update | Most volatile core to that point; composite CWV reported |
| **2026-05-07** | FAQ rich results retired | Search Console report June; API August |
| **2026-05-21 → 06-02** | May 2026 core update | Reported heavier still |

**Cadence: roughly every 3–4 months, no fixed schedule.**

⚠️ **This table ends July 2026.** When diagnosing a traffic drop, always
`WebSearch` for updates after that date. Never tell a user "no update matches"
based on a static table.

---

## 3. Core Web Vitals — current, and the composite question

**Thresholds** (DOCUMENTED) — 75th percentile of real Chrome users, 28-day window:

| Metric | Threshold |
|---|---|
| **LCP** | ≤ 2.5s |
| **INP** | ≤ 200ms |
| **CLS** | ≤ 0.1 |

⚠️ **INP is the most commonly failed metric** — ~43% of sites reportedly fail it
(KNOW). Hydration-heavy JS frameworks are the usual cause.

### The composite/site-wide claim (BELIEVE)

Multiple independent SEO analyses report the March 2026 core update moved CWV
evaluation from **per-metric to composite** (passing two and failing one no longer
earns full credit) and from **per-page to site-wide aggregation** (slow templates
drag the whole domain). **No Google source confirms either.**

**How to act on an unconfirmed claim — split it:**

- ✅ **Change the method.** **Sample CWV across every page template, not just the
  home page.** Correct either way; costs nothing. **Do this.**
- ❌ **Do not change the pitch.** The controlled study in `01` §10 found the
  original rollout statistically indistinguishable between test and control. One
  unconfirmed consensus does not make speed a major ranking factor.
- **Net:** page experience moves from *negligible* to *small but not ignorable*.
  Rubric weight raised 5 → 7. Relevance and content depth still dominate.

**In the report:** if you flag CWV findings, label the site-wide claim BELIEVE.
Do not tell a user their rankings dropped because of CWV unless you have evidence
specific to their site.

---

## 4. Structured data — the rich-result retreat

Google is **removing** rich-result types faster than it adds them (§2).

**The critical distinction:** `FAQPage` and `HowTo` remain **valid Schema.org
types** and Google **still parses them to understand pages**. What ended is the
**visible SERP feature**.

**Audit consequences:**

1. **Do not flag `FAQPage`/`HowTo` markup as "remove this."** It still aids machine
   comprehension and AI citation.
2. **Do not promise a rich result** from either. If the site's rationale was the
   SERP feature, that rationale is dead — say so.
3. **Never justify structured data by the rich result alone.** Rich results are
   being withdrawn; machine comprehension and AI citation are durable. Frame
   recommendations that way.
4. **Check the current supported-type list before promising any rich result.**
   The set shrinks — `WebSearch` it rather than trusting `01` §9.

---

## 5. Site reputation abuse — added to the prohibited ledger

In force **2024-05-05**. Post-dates the book, so it is absent from `05` §3.

> **Site reputation abuse ("parasite SEO")** — third-party pages published on a
> host domain with **little or no first-party oversight**, whose purpose is to
> exploit the host's ranking signals. Coupon/casino/loan sections bolted onto news
> sites; rented subfolders; unmoderated partner directories.

**Not all third-party content violates it** — only content hosted without close
oversight *and* intended to manipulate rankings.

**The distinguishing factor is editorial oversight, not the commercial
relationship.** A guest post the publisher genuinely edited is fine. A subfolder
they rented out is not.

**Flag it when you see:** a subfolder or subdomain whose content is unrelated to
the host's purpose, has a different author pool, and shows no editorial
involvement — especially in high-CPC verticals (loans, casinos, coupons, CBD).

---

## 6. Google Discover — Feb 2026 update

First-ever **standalone Discover core update**, 2026-02-05 → 02-27.

**Three shifts:** page-level EEAT (not site-level) · topical authority assessed
**topic-by-topic** · a **headline-content misalignment classifier** (the clickbait
detector, made explicit).

**Two hard mechanical gates — check these first, they are independently
disqualifying and cheap to fix:**
- Images **≥1200px wide** with `max-image-preview:large`
- Page load **2–3s**

**Impact:** unique domains in the US Top-1000 Discover placements fell
**172 → 158 (−8.1%)**. Consolidation toward established authority.

**If a site depends on Discover traffic**, check the two gates before offering any
content advice.

---

## 7. AI Overviews — the structural change

**The biggest difference between the book's world and now.** It does not change
*how to rank*. It changes **what ranking is worth**.

| Metric | Value | Tier |
|---|---|---|
| Queries triggering an AIO | **~48%** (Mar 2026) | KNOW |
| Zero-click, all searches | **~65%** | KNOW |
| Zero-click when AIO present | **~83%** | KNOW |
| CTR reduction, top-ranking, AIO present | **~58%** (Ahrefs, Feb 2026) — roughly **double** the ~34.5% eight months earlier | KNOW |
| Conversion rate of surviving clicks | **+23%** | BELIEVE |
| Click lift for brands *cited* in the AIO | **+35%** | BELIEVE |

**Three consequences for the audit:**

1. **The effect is accelerating.** Any AIO figure older than ~2 quarters
   understates it. Re-verify before quoting.
2. **Coverage is uneven by vertical.** Healthcare and B2B tech approach ~90%;
   **ecommerce reportedly fell 29% → 4%** as Google protects transactional revenue
   (BELIEVE — single-source, coherent incentive story). **Check the client's
   vertical before sizing the impact.**
3. **Citation now beats position** on AIO queries. Being referenced *inside* the
   answer outperforms ranking beneath it.

### The measurement consequence — this generates false positives

**The chain `rank → CTR → sessions` is broken.** A page can hold position 1, gain
impressions, and lose half its clicks with nothing wrong with it.

| Symptom | Naive reading | Often actually |
|---|---|---|
| Sessions down, rank flat | "We were penalized" | An AIO now appears on the query |
| Sessions down, impressions **up** | "Something broke" | More eligible, capturing less |
| Sessions down, conversions flat | "Traffic crisis" | **Lost worthless traffic. Do nothing** |
| Rank up, sessions flat | "Rankings don't work" | Position sits beneath an AIO |

**Minimum honest traffic-drop check — all four, together:** conversions ·
impressions · SERP shape · manual actions + recent deploys.

**Never diagnose a traffic drop from sessions alone in 2026.**

---

## 8. AI visibility — the audit dimension the book has no chapter for

Rubric weight **10**. Grounded in the Princeton GEO study (ACM KDD 2024) and
per-engine behaviour.

**What moves AI citation:**

| Tactic | Effect | Tier |
|---|---|---|
| **Cite credible external sources** | **+40%**, up to **+115%** for lower-ranked pages | KNOW (peer-reviewed) |
| **Add statistics** with named sources | **+41%** | KNOW |
| **Add quotations** from named experts | **+28%** | KNOW |
| Authoritative, fluent, non-promotional prose | Positive | KNOW |
| **Keyword stuffing** | **−10%** | KNOW |
| Promotional tone | **−26%** correlation with citation | BELIEVE |
| Adding words without structure | ~0% | KNOW |

**Note the inversion:** citing sources lifted a 5th-ranked page **+115%** while the
top-ranked page *lost* share. **GEO is a leveler — it lets lower-ranked pages punch
up.** For a small site this is the single best-evidenced opportunity available.

**On-page checks:**
- **Answer-first blocks** — open each section with a 40–60 word direct answer
- **Semantic chunking** — 200–400 word sections, one concept each, independently
  extractable. Models read chunks, not pages
- **Stats density** — a cited statistic every ~150–200 words, linked to originals
- **Comparison tables** — lifted cleanly, match commercial intent
- **Entity consistency** — identical brand/product naming everywhere so the model
  resolves you to one entity. ⚠️ Brand mentions correlate **0.664** with AIO
  appearance vs. **0.218** for backlinks (>3× more predictive)
- **Freshness** — ⚠️ content updated within 30 days reportedly gets ~3.2× more
  citations. Perplexity weights recency hardest
- **Structured data** — for machine comprehension, not rich results (§4)

**Engines barely agree.** Only ~11% of domains are cited by both ChatGPT and
Perplexity. **"AI visibility" is not one number** — name which engines you sampled
or the metric is meaningless.

**`llms.txt`:** Google **does not support it and has said so on the record**
(Illyes, July 2025; AI-optimization guide updated 2026-06-15). **Perplexity and
Claude do retrieve it**; Stripe, Cloudflare and Anthropic ship one; adoption
~10.13% of 300k domains surveyed. **Verdict: cheap to ship, real benefit on
non-Google engines. Never claim it helps with Google.**

---

## 9. What did *not* change

State this in reports — the reflex is to declare everything obsolete every
eighteen months.

- **Relevance and content depth dominate.** Every core update since 2024 pushed
  *further* this way
- **Links still function as citations**, weighted by trust and topical relevance
- **Crawlability and indexability remain gates**
- **Canonical, redirect and duplication mechanics are unchanged**
- **Penguin still discounts rather than penalizes**
- **Manual actions still notify; algorithmic adjustments still don't**
- **hreflang mechanics are unchanged**
- **Local still runs on relevance + prominence + proximity**, and a declared
  service area still ranks you nowhere
- **EEAT is still a rater rubric, not a ranking factor**

**The pattern: mechanics are durable, magnitudes are not.** Trust `01`–`06` for
*arguments*; verify their *numbers* here.

---

## 10. Re-verification list

Check quarterly. Ordered by decay rate.

| Item | Why it decays |
|---|---|
| AIO coverage + CTR impact | Doubled in 8 months |
| Latest core/spam update | Every 3–4 months |
| CWV composite claim | **BELIEVE — upgrade or drop** on Google confirmation |
| Supported rich-result types | Net-negative trend |
| `llms.txt` support by engine | Fast-moving, contested |
| Discover eligibility gates | New surface, unstable |
| Ecommerce AIO coverage (29% → 4%) | Single-source BELIEVE |

---

**Sources** (verified July 2026)

- [Google Search Central — March 2024 core update and new spam policies](https://developers.google.com/search/blog/2024/03/core-update-spam-policies)
- [web.dev — INP becomes a Core Web Vital](https://web.dev/blog/inp-cwv-march-12)
- [Google Search Central — Changes to HowTo and FAQ rich results](https://developers.google.com/search/blog/2023/08/howto-faq-changes)
- [Search Engine Journal — Google Drops FAQ Rich Results](https://www.searchenginejournal.com/google-drops-faq-rich-results-from-search/574429/)
- [Search Engine Journal — AI Overviews cut organic clicks (field study)](https://www.searchenginejournal.com/ai-overviews-cut-organic-clicks-38-field-study-finds/573145/)
- [Search Engine Land — Google algorithm updates library](https://searchengineland.com/library/platforms/google/google-algorithm-updates)
- [Search Engine Journal — Google algorithm update history](https://www.searchenginejournal.com/google-algorithm-history/)
- Princeton/Georgia Tech/IIT Delhi/AI2, *GEO: Generative Engine Optimization*, ACM KDD 2024 ([arXiv 2311.09735](https://arxiv.org/html/2311.09735v3))

KNOW/BELIEVE tiers aggregate multiple independent SEO measurement vendors.
**Tier labels reflect source quality, not confidence in direction** — a BELIEVE
item may well be true; it simply has no primary confirmation and must not ship as
fact.
