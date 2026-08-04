# 05 — Penalties, Algorithm Updates & Recovery

Diagnosing traffic loss, and the enforceable list of tactics never to recommend.
Load for Phase 6, or any "why did my traffic drop" question.

⚠️ = 2023-sourced. **Re-verify before quoting.**

---

## 1. The three failure modes — do not conflate

Getting this wrong sends people down months-long wrong paths. It is the single
most common diagnostic error in SEO.

| | **Manual action** | **Algorithmic adjustment** | **Filtering** |
|---|---|---|---|
| **Trigger** | A human reviewer | An algorithm | Normal dedup/diversity |
| **Notified?** | **Yes** — Search Console message | **No** | **No** |
| **Is it a penalty?** | Yes | No — a re-scoring | **No** — normal operation |
| **Remedy** | Fix → **reconsideration request** | Fix → wait for re-crawl + re-process | Usually nothing to fix |
| **Timeline** | Response typically **2–3 weeks** | Weeks to months | N/A |

**Filtering is not punishment.** When duplicate pages get collapsed or one result
per domain is shown, that is the system working. **Say "filtered," not
"penalized"** — in reports and in client conversation. The words imply different
remedies.

---

## 2. Diagnostic order — follow strictly

**Most misdiagnosis comes from skipping step 1.**

### Step 1 — Confirm it's actually organic search traffic

Check analytics and **isolate organic**. Ruling out first:
- A tracking-code regression (a broken analytics tag looks exactly like a traffic
  collapse)
- Sitewide changes affecting all channels
- Seasonality — **compare year-over-year, not month-over-month**
- A paid campaign ending
- A referral source disappearing

**A shocking share of "SEO emergencies" are a removed analytics tag.** Check it
before anything else.

### Step 2 — Check Search Console for a manual action

If present, you know the cause and the remedy. Go to §4.

### Step 3 — Pin the exact date, correlate with known updates

Get the precise day the drop began. Then check:
- Google Search Status Dashboard (official confirmed updates)
- Moz's algorithm history, Search Engine Roundtable, Search Engine Land
- Volatility trackers: MozCast, Semrush Sensor, Algoroo, Rank Ranger

**If it lines up with a confirmed update, read what that update targeted** and
audit against it specifically.

### Step 4 — If no update matches, audit your own changes

Google makes **thousands of changes per year**, most unannounced. But before
assuming an unannounced update:

- **What did the dev team ship near that date?** Deploys are a far more common
  cause than algorithm updates
- Check for: accidental `noindex`, `robots.txt` regression, a staging config
  promoted to production, a CMS/framework migration, URL structure changes without
  redirects, a redesign that removed content or internal links
- **Check `robots.txt` and meta robots first.** A staging `Disallow: /` reaching
  production is the classic catastrophic self-inflicted wound

### Step 5 — Check for lost links

Link-analysis tools have latency; verify important lost links manually.

### Step 6 — Scope it

- **Sitewide** drop ⇒ sitewide cause (manual action, Helpful Content, technical
  regression, migration)
- **One section** ⇒ something specific to that section
- **One page** ⇒ competitor movement, content staleness, lost links, or a SERP
  feature change on that query

**Also check whether the SERP itself changed.** If a map pack or AI overview
appeared on your top query, you may have lost traffic without losing rank. That is
a different problem with a different response.

---

## 3. The prohibited ledger — never recommend these

**Enforceable list.** These must never be recommended, **including when the user
explicitly asks for them**. Explain why instead.

### Hard prohibitions

| Tactic | Why it fails |
|---|---|
| **Keyword stuffing** | Trivially detected. Also **−10% on AI citation** per the Princeton GEO study |
| **Hidden text / links** | White-on-white, `display:none`, off-screen positioning, single-character anchors |
| **Cloaking** | Different content to bots vs. users |
| **Sneaky redirects** | Users redirected somewhere other than what was indexed |
| **Buying links** | Including **paid guest posts** |
| **Reciprocal link trading** | Reads as a scheme |
| **Private blog networks** | Google detects them well |
| **Buying expired domains for links** | Same |
| **Content scraping / spinning** | Copyright exposure plus a quality signal |
| **Doorway pages** | Built solely to capture a query and funnel elsewhere |
| **Thin slicing** | Near-identical pages per size/city/variant |
| **Comment / forum spam** | |
| **Requesting specific anchor text** | Explicitly against engine guidelines |
| **Automated queries to Google** | Grey area; scaled rank-tracking especially |
| **Fabricated structured data** | Especially `aggregateRating`. Common manual-action trigger |
| **Fake or incentivized reviews** | FTC liability on top of platform penalties |
| **Site reputation abuse ("parasite SEO")** | **⚠️ Post-dates the 2023 source — policy in force 2024-05-05.** Third-party pages on a host domain with little or no first-party oversight, exploiting the host's ranking signals. **The distinguishing factor is editorial oversight, not the commercial relationship.** See `07-currency-2026.md` §5 |

### Sanctioned exceptions worth knowing

- **Dynamic rendering** (SSR to bots, CSR to users) is technically cloaking but
  tolerated as a **workaround** — same content both ways. Not a long-term solution
- **Flexible sampling** — Google's sanctioned paywall program. Googlebot crawls
  gated content; users arriving from search get the full article, capped per month

### Discouraged — abused into worthlessness

Infographic link campaigns · widget/badge links · mass press-release links ·
article directories · low-quality paid directories · mass unrelated guest posting.

### Explicitly fine — say so, people assume otherwise

- **Guest posting for readership** (not for links)
- **Being an affiliate** — Google's Gary Illyes has praised affiliate sites with
  genuine added value. *Thin* affiliate content is the problem
- **Content syndication** — with cross-domain canonical, `noindex` on the copy, or
  a link back to the original
- **AI-assisted content** — with SME ownership and review
- **Paid links** — as advertising, with `rel="sponsored"`
- **Local business directories** — categorically different from cheap link directories
- **Buying a sponsorship that yields a link** — you're buying the sponsorship

---

## 4. Manual action types and remedies

| Type | Remedy |
|---|---|
| **Thin content** | Improve, `noindex`, or remove. Identify the pattern — usually autogenerated, doorway, or too-similar pages |
| **Unnatural links (partial)** | One or few pages affected. Find the over-linked pages, clean/disavow |
| **Unnatural links (sitewide)** | Broad cleanup. Highest traffic impact |
| **Cloaking / sneaky redirects** | Compare rendered vs. served content; check conditional redirects |
| **Hidden text / keyword stuffing** | Grep for `display:none`, matching text/background colors, off-screen positioning |
| **User-generated spam** | Remove spam, then implement moderation. Root cause is process, not content |
| **Unnatural outbound links** | Add `rel="sponsored"`/`nofollow`, or remove |
| **Pure spam** | Aggressive tactics. Often faster to start over on a new domain |
| **Spammy free host** | Your site is clean but the host isn't. Move hosts |
| **Structured data abuse** | Remove fabricated/inappropriate markup |

### Reconsideration requests

Only available **when a manual action exists**. There is no reconsideration path
for an algorithmic drop.

**Format — short and factual. A reviewer reads these all day:**

1. Briefly state the problem, with a statistic or two
2. Explain what went wrong — ignorance of the rules or a rogue agency are both
   acceptable answers; be honest
3. Explain what you did, **with counts** ("contacted 340 domains, 112 links
   removed, 890 disavowed at domain level")
4. State that you intend to follow the guidelines going forward

**Do not** complain, argue, or plead. **Be aggressive in the cleanup** — trying to
preserve marginal links usually means a second rejection, and a second round costs
another 2–3 weeks. Response typically arrives in 2–3 weeks.

---

## 5. Algorithm ledger

| Update | Year | What it targets |
|---|---|---|
| **Panda** → **Coati** | 2011 → 2022 | Content quality. Core since 2016; **superseded by Coati Nov 2022** |
| **Penguin** | 2012 | Link quality. **Penguin 4.0 (2016) stopped penalizing — now discounts bad links to zero** |
| **Hummingbird** | 2013 | First ML pass at whole-query meaning |
| **RankBrain** | 2015 | Novel queries matched to similar past ones. Aimed at the ~15% of daily queries never seen before |
| **BERT** | 2019 | **Bidirectional** context — could finally read words before *and* after a term |
| **Subtopics** | 2020 | Splits a broad SERP into subtopic clusters |
| **Passages** | 2021 | Ranks a *passage* within a long page independently |
| **Page experience** | 2021 mobile / 2022 desktop | CWV + mobile + HTTPS + interstitials. **Small effect** |
| **MUM** | 2021 | Multimodal, cross-language (75 languages) |
| **Helpful Content** | Aug 2022 | **Sitewide** demotion for engine-first content. **⚠️ Folded into the core algorithm March 2024 — no longer a standalone update. Mechanics still apply; the name is gone** |
| **Link spam + SpamBrain** | Dec 2022 | AI neutralization of unnatural links |
| **Broad core updates** | Several/year | Ongoing re-scoring. Google publishes dates, not mechanics |

> ⚠️ **This table ends at the 2023 source cutoff and is missing three years.**
> The post-2023 timeline — March 2024 core (HCU absorption), site reputation
> abuse, INP, AI Overviews, and the 2025–2026 core updates — is in
> `07-currency-2026.md` §2. **Never tell a user "no update matches your drop
> date" based on this table alone.** `WebSearch` for updates around their date.

### Two Helpful Content properties that invert normal logic

1. **Sitewide.** A section of engine-first content demotes the *entire* domain
2. **Recovery takes many months** after removal

**Remediation:** `noindex` is a **patch**. Google's John Mueller has said the real
fix is **removing the content**.

---

## 6. Recovery expectations — set these explicitly

**Understating the timeline is the most common way an SEO engagement fails.**

| Scenario | Realistic timeline |
|---|---|
| Technical fix (indexation, canonical, redirect) | Days to weeks after re-crawl |
| Manual action reconsideration | **2–3 weeks** per round, plus fix time |
| Domain migration dip | ⚠️ **Should rarely exceed 60–90 days** if executed well |
| Algorithmic (Helpful Content) recovery | **Many months.** Often the next update cycle |
| Content depth building | **Quarters.** Not a fix — a program |
| Link authority building | **Quarters to years** |

**Crawl rate is responsive to server health.** Google's Gary Illyes: "if the site
responds really quickly for a while, the limit goes up... if the site slows down or
responds with server errors, the limit goes down."

**To accelerate re-crawl after large changes:**
- Fix 4xx/5xx and soft-404s
- Remove/`noindex` duplicates; block crawling of internal search results
- Cut faceted-navigation bloat
- **Improve internal linking** to pages you want re-crawled — link higher in the
  hierarchy, link more often
- Improve server response time
- Submit updated sitemaps; use URL Inspection for individual priority pages
- Keep both old and new sitemaps live during a migration

**Index budget is the under-discussed twin of crawl budget.** Google may index only
a fraction of a large site. Blocking in `robots.txt` (crawl) is **not** the same as
keeping out of the index. To *remove* from the index, `noindex` it and **let it be
crawled**. Review "Crawled — currently not indexed" in Search Console regularly.

---

## 7. Site moves — the checklist that prevents the 90-day hole

1. **Inventory every URL first** — crawl, sitemaps, Search Console, server logs,
   and a backlink export from **multiple vendors** (each crawls a slice; the union
   is materially larger)
2. **Build an old→new mapping.** Wildcard rules where structure is preserved;
   individual rows for exceptions and retired pages
3. **301 everything**, including retired pages → the nearest genuinely relevant
   parent. **Not the home page by default**
4. **Keep both sitemaps live** for a period so the crawler pairs them faster
5. **Contact the top ~100 referring domains** to update links. Everyone skips
   this; it's the step that most shortens the dip
6. **Search Console Change of Address** (verify both properties first)
7. **Monitor** 404s, 5xx, crawl rate, and redirect handling for at least a quarter

**Do not change domain, URL structure, CMS, and design in one release.** When
traffic drops, nothing is attributable — and something always drops.

**Consider phasing** a large URL migration in tranches. Three 10% dips are easier
to absorb, and easier to diagnose, than one 35% dip.
