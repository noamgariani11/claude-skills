# 08 — Obsolescence & Claim Governance

**Load this in Phase 0 and keep it loaded.** It is not a phase-specific reference.
It governs what you are allowed to *say* in every other phase.

The other reference files tell you what to check. This one tells you what you may
assert while checking, and it exists because of a specific failure mode:

> The other files guard against recommending something **malicious**. This one
> guards against recommending something **stale** — advice that was genuine,
> mainstream, white-hat best practice when most of the internet's SEO writing was
> produced, and is now simply wrong.

Staleness is the likelier failure. Three reasons:

1. **The corpus is skewed old.** SEO blogging peaked as a volume phenomenon around
   2008–2014. That window is wildly overrepresented relative to its accuracy.
2. **The dead rule is the more quotable one.** "Keep titles under 70 characters" is
   crisp and actionable. "Truncation is pixel-bounded and Google rewrites a large
   share of titles anyway" is not. The wrong answer is the more fluent one.
3. **It arrives with no warning signal.** A black-hat suggestion feels wrong to
   write. A dead rule feels like competence.

---

## 1. The obsolescence ledger

Every row was legitimate advice at the time. Every row is now wrong. If you catch
yourself writing anything in the left column, stop.

**Status key:** **DEAD** = the mechanism no longer exists · **INVERTED** = the
correct action is now the opposite · **UNRESOLVABLE** = assert nothing.

### Metrics and tools that no longer exist

| Never say | Status | Say instead |
|---|---|---|
| "Your PageRank is…" / toolbar PageRank | DEAD (retired 2016) | No public per-page Google authority number exists. Third-party scores (Moz DA/PA, Ahrefs DR) are **vendor models, not Google signals** — label them as such |
| mozRank · mozTrust · Linkscape · Open Site Explorer | DEAD (renamed/retired) | Moz Link Explorer, DA/PA. Use current tool names |
| Yahoo! Site Explorer | DEAD (closed 2011) | Google Search Console · Bing Webmaster Tools |
| "Google Webmaster Tools" | RENAMED (GSC since 2015) | Google Search Console. **Never instruct a user to click a control that was removed** |
| Keyword density targets ("aim for 2–3%") | DEAD | Topical and entity coverage, intent match. There is no density number. Density-driven writing actively costs you: stuffing is **−10% on AI citation** |
| "Check Google's cached / Text-only version to see what the crawler indexed" | DEAD (`cache:` operator + cached links removed early 2024) | **URL Inspection** in Search Console, or compare the rendered DOM against a raw fetch. A model trained on older SEO writing will confidently send a user to a cached-page button that no longer exists |

### On-page rules whose mechanism changed

| Never say | Status | Say instead |
|---|---|---|
| "Titles must be under 65–70 characters" | DEAD as stated | Truncation is **pixel-bounded** (~580px desktop), and since Aug 2021 Google **rewrites** displayed titles on a large share of results. Front-load meaning; treat the rendered title as influenced, not controlled |
| "Write the meta description to ~155 chars as ad copy" | HALF-SURVIVED | Still not a ranking factor, still worth writing — but Google rewrites the snippet most of the time. Sell it as CTR *influence*, never a controllable ad slot |
| `noodp` / `noydir` meta tags | DEAD | DMOZ closed 2017; Yahoo Directory closed 2014. These reference directories that no longer exist |
| Meta keywords as an external lever | DEAD | Unused by Google and Bing. Narrow survival: some **internal site-search** products read it |
| "Get the keyword in the domain" (EMD) | INVERTED (2012 EMD update) | Pick a brandable name |
| "Keep links under 100 (or 150) per page" | DEAD — guideline withdrawn | Authority per link still dilutes with count (200+ is a real risk), but **cite no cap** |

### Link and redirect mechanics

| Never say | Status | Say instead |
|---|---|---|
| "301s leak 1–10% of link juice" | DEAD (Illyes, 2016: **no PageRank lost**) | Redirects do not cost authority. **Chains cost crawl budget** — a different, smaller problem |
| "302s pass no value" | DEAD — all `30x` pass authority | The only real difference is **which URL stays indexed** |
| PageRank sculpting with `nofollow` | DEAD TWICE (broken 2009; `nofollow` became a **hint** March 2020) | Also exists now: `rel="ugc"`, `rel="sponsored"`. Advice naming only `nofollow` is pre-2020 |
| Directory submission · article directories · paid directory links | INVERTED | These are now unambiguous **link schemes** → `05-penalties-and-recovery.md` §3 |
| Paying influencers to vote content onto a homepage | INVERTED | Link scheme, plus an undisclosed paid endorsement in most jurisdictions |
| "Submit your site to the search engines" | DEAD | Discovery is crawl, sitemap, internal link |

### Technologies the advice was written about

| Never say | Status | Say instead |
|---|---|---|
| "Avoid Flash" / use SWFObject | MOOT (Flash EOL Dec 2020) | The **principle** generalises: content needing a plugin or a user interaction to appear is content the crawler does not see. That is now a **JavaScript** problem |
| "Avoid framesets" | MOOT (dropped in HTML5) | The `iframe` caveat survives: iframed content is attributed to the iframe's URL |
| "Engines can't execute JavaScript" | LARGELY INVERTED (evergreen Chromium since May 2019) | Standard `<a href>` is still the only reliable link form, but blanket "engines can't do JS" is years stale → `01-technical-audit.md` |
| Optimizing for Google Instant | MOOT (discontinued 2017) | — |
| `&pws=0` to de-personalize a SERP | DEAD | No URL trick yields a neutral SERP. Use a tracker that **states its locale and device assumptions**, and treat output as a sample |

### Platform advice overtaken by the platforms

The **thesis** — optimize for the engines your buyers actually use, not just
Google — is durable and correct. Every *enumeration* of those engines decays in
about five years.

- **Dead or irrelevant as SEO surfaces:** Delicious, Digg, StumbleUpon, Myspace,
  Flickr, Facebook search.
- **Survived and grew:** Amazon (product search), YouTube.
- **Not in any pre-2020 list, and now central:** TikTok search, Reddit
  (structurally more visible in Google since the 2024 content deal), app stores,
  and above all **AI assistants and AI Overviews**.

---

## 2. Unresolvable — assert nothing in either direction

| Claim | Why you must not take a side |
|---|---|
| **"User behaviour / traffic does not affect rankings"** | No longer safe to assert. The 2023 US v. Google antitrust testimony and the 2024 Content Warehouse documentation both surfaced click/interaction systems (Navboost) in ranking. **But the opposite — "get traffic and you'll rank" — is equally unsupported and is the premise of every traffic-bot scam.** Correct posture: user-interaction signals appear to participate in ways Google has not documented. Do not sell traffic as a ranking lever; do not deny the mechanism exists. Say what is known and stop |
| **"Image search referrals are worthless — consider blocking them"** | INVERTED for commerce. Visual search is a real acquisition surface → `04-vertical-local-international.md`. The *accessibility* case for `alt` text was always the durable half |

---

## 3. What survived — safe to state with confidence

Shorter than the ledger, and that is the point. These have now survived a full
platform generation.

- Relevance and authority are the two axes.
- Links are editorial votes; anchor text carries meaning.
- Information hierarchy and click depth matter; minimize clicks from home to money page.
- Internal anchor text should be descriptive, never "click here".
- Short, descriptive, hyphen-separated URLs (hyphens over underscores).
- One resource, one URL.
- **`noindex, follow` beats a `robots.txt` disallow for de-indexing.**
- **Never combine a `robots.txt` disallow with `noindex`** — a blocked page is never
  crawled, so the `noindex` is never read. Still the most common self-inflicted wound.
- The title tag is the highest-leverage single on-page element (the *character rule*
  died; the *importance* did not).
- `alt` text, for accessibility first.
- Optimize for people, not engines — now actually enforced via Helpful Content and EEAT.
- **The link-worthiness gate:** if you cannot name who would link to a page and why,
  creating it spends authority without returning any. This is the cleanest available
  statement of the thin-slicing guard — apply it **per generated page**, not per template.

---

## 4. Attribution discipline — what counts as evidence

The rules above became folklore through bad measurement. Do not repeat the method.

**A single-URL before/after observation is not evidence.** It is the single most
common way SEO folklore is manufactured, and it is how most of §1 was originally
"proven."

Modern confounders make the naive test worse than useless:

| Confounder | Effect on a naive before/after |
|---|---|
| Continuous algorithm updates | No stable baseline period exists |
| Personalization and localization | No neutral SERP; `&pws=0` no longer produces one |
| SERP features and AI Overviews | The same rank can lose clicks with **no ranking change at all** |
| Seasonality and demand shift | Routinely larger than the effect being measured |

**The standard:** a controlled split test across statistically matched **groups** of
pages, with a held-out control measured over the same window.

**Why this matters concretely:** a naive before/after during the page-experience
rollout would have "shown" that Core Web Vitals improvements raised rankings,
because scores were improving everywhere at once. The controlled study
(1,188 keywords / 7,623 control URLs) found test and control **statistically
indistinguishable**. The control group is the only thing that caught it.

**So in a report:**

- Never write "this change caused the ranking improvement" from one URL and one
  metric. Write what changed, what moved, and that **attribution requires a control**.
- If asked "did my SEO work," and the evidence is one page with no control, the
  honest answer is **"this cannot be attributed"** plus what would be needed. Per
  iron rule 2, a refusal is a shippable answer.

---

## 5. Self-check before writing any recommendation

1. Does this reference a **tool, metric, tag, or product** — is it still current
   under its current name? (§1)
2. Am I citing a **number as a rule** (character counts, link caps, percentage of
   juice lost)? Nearly every hard number in classic SEO advice is dead. (§1)
3. Am I asserting a **causal claim** without a control group? (§4)
4. Am I taking a side on something **unresolvable**? (§2)
5. Would this advice have looked equally confident in 2011? If yes, verify before
   shipping it.

When a dated claim matters to the finding and you cannot verify it,
**keep the direction and drop the number** — and log it under Verification debt.
