# 01 — Technical Audit

Crawl, index, render, duplication, redirects, architecture, structured data,
page experience. Load for Phases 1–2, or `--scope technical` / `--scope speed`.

⚠️ = figure from a 2023 source. **Re-verify before quoting.**

---

## 1. The gate procedure

Run in this order. **Stop at the first failure and report it** — everything
downstream is invalid on a page that cannot be indexed.

### 1.1 Does it serve 200?

```bash
# Status + redirect chain in one shot
curl -sIL -o /dev/null -w '%{http_code} %{num_redirects} %{url_effective}\n' "$URL"
# Full chain with each hop
curl -sIL "$URL" | grep -iE '^(HTTP/|location:)'
```

Fail conditions: any 4xx/5xx; a redirect chain ≥3 hops; a **soft 404** (200 status
with "not found" content — check the body, not just the code).

### 1.2 Is it indexable?

Three independent blockers. Check all three — they interact.

```bash
curl -s "$ORIGIN/robots.txt"
curl -sI "$URL" | grep -i 'x-robots-tag'
```
```
Grep: '<meta[^>]*name=["'\'']robots'   # meta robots
Grep: 'noindex'                         # anywhere — framework configs included
```

**The mutually-cancelling bug** — the single most common self-inflicted SEO wound:
a URL that is **both** `Disallow`ed in `robots.txt` **and** marked `noindex`. The
crawler never fetches the page, so it never reads the `noindex`, so the page can
still appear in results (URL-only, no snippet) and can never be removed.

- To keep a page **out of the index**: `noindex` it and **allow crawling**.
- To save **crawl budget** on pages already out of the index: `Disallow` only.
- **Never both.**

### 1.3 Does the content render server-side?

The modern #1 blocker. Content that requires a *user action* to load is invisible
— Googlebot does not click.

```bash
# What a fetch sees (pre-JS)
curl -s "$URL" | grep -c 'DISTINCTIVE_PHRASE_FROM_PAGE'
```

Then compare against the post-JS DOM. Options, best first:
- Google's **Rich Results Test** or **URL Inspection** → "View crawled page"
- Chrome DevTools **Elements** panel (not "View source" — that shows pre-execution JS)
- A headless browser (Playwright/Puppeteer) capturing `page.content()`

**If the phrase is in the DOM but not the fetch, and no JS error occurred, it's
probably fine** (Googlebot has run evergreen Chromium since May 2019). **If it
only appears after a click, tab, or accordion open — it's invisible.**

⚠️ Deferred-render latency was reported as median ~5s / p90 "minutes" (2019).
Direction durable, magnitude stale.

### 1.4 Canonical resolves

```
Grep: 'rel=["'\'']canonical'
Grep: 'canonical'  # framework metadata APIs
```

Fail conditions:
- **No canonical** on an indexable page
- **Two canonicals** on one page pointing to different URLs → Google ignores both
- **Circular**: A→B and B→A → ignored
- Canonical → a `noindex`, redirecting, or 404 URL
- Canonical → HTTP from an HTTPS page (or vice versa)

Canonical is a **hint, not a directive**. Contradictory signals get it discarded
silently. A 301 is the strong version.

### 1.5 Reachable

Orphan pages — in the sitemap or analytics but with zero internal links. Detect
by diffing:
- sitemap URLs vs. crawl-discovered URLs
- analytics-visited URLs vs. crawl-discovered URLs
- server-log URLs vs. crawl-discovered URLs

### 1.6 Manual action

Google Search Console → **Manual actions**. If present, you know the cause; go
straight to `05-penalties-and-recovery.md`. Also read **Pages → "Crawled —
currently not indexed"** — this is where index-budget problems surface.

---

## 2. Crawl blockers — the full list

| Blocker | Real in 2026? | Detection |
|---|---|---|
| Content behind a form/login | **Yes** | Any content requiring POST |
| Content loaded on user interaction | **Yes — #1 modern trap** | DOM-vs-fetch diff after interaction |
| `robots.txt` disallow | Yes | Fetch and read it |
| `noindex` / `nofollow` | Yes | Grep |
| Session IDs in URLs | Where they survive | `Grep: 'sessionid\|sid=\|PHPSESSID'` |
| iframes | Yes | Content attributed to the iframe's URL, not the page |
| 200+ links on a page | Directionally | Count `<a href` per template |
| Infinite scroll with no paginated URLs | **Yes** | Check for `?page=` equivalents |
| Faceted navigation explosion | Yes | Count crawlable filter permutations |

**Spider traps** to check for: recursive redirect loops, infinite calendar
pagination, and sort/filter combinations generating unbounded URL space.

---

## 3. Rendering mode

| Mode | SEO risk | Recommendation |
|---|---|---|
| **SSR** | Lowest | Default-correct |
| **CSR** | Highest | Migrate or add SSR for above-fold |
| **Dynamic rendering** (SSR to bots, CSR to users) | Medium | Google calls this a **workaround**, not a solution. Bridge only |
| **Hybrid / SSR-with-hydration** | Low | **The modern default.** Above-fold server, rest hydrated |

**Framework-specific checks:**

- **Next.js App Router** — Server Components are SSR by default (good). Grep for
  `"use client"` at the top of route-level page files; primary content in a
  Client Component is a regression. Check `generateMetadata` exists on dynamic
  routes.
- **Next.js Pages Router** — `getServerSideProps` / `getStaticProps` present?
  Pure client fetching in `useEffect` is a risk.
- **React SPA (CRA/Vite)** — likely fully CSR. This is usually the finding.
- **Nuxt / SvelteKit / Astro** — check SSR is enabled, not `ssr: false`.
- **Gatsby / static generators** — usually fine for rendering; check the
  templates expose editable `<title>` and meta.

**Universal framework failure modes:** soft-404s on missing dynamic routes;
inability to set per-route `<title>`/meta; `robots.txt` not served; bundle size
harming LCP.

---

## 4. Duplication, thin content, thin slicing

Three distinct problems Google treats differently. **Do not conflate them.**

### 4.1 Duplication

Exact, near (sort orders, tracking params, print views), and cross-domain
(syndication, scraping).

**What it costs** — the mechanism, not the myth:
- Crawl budget burned on pages that get filtered
- Link authority split across URLs that can't rank
- **The engine picks the canonical and may pick wrong**

**There is no duplicate-content penalty in ordinary cases.** Filtering ≠ penalty.
Say "filtered," not "penalized." Penalties arrive for large-scale aggregation
with no added value or thin-affiliate patterns.

**Common sources to check:**
```
HTTP and HTTPS both serving      → 301 + HSTS
www and non-www both serving     → pick one, 301 the other
Trailing-slash variants          → normalize
Uppercase URL variants           → Unix servers are case-sensitive; force lowercase
Tracking params (?utm_, ?source) → canonical to the clean URL
Print/AMP/mobile variants        → canonical
Pagination                       → self-canonical each page; don't canonical to page 1
Faceted/sort URLs                → canonical or noindex
```

**Fix ladder (in order):** eliminate + 301 → `rel="canonical"` → `noindex` →
`robots.txt` disallow.

### 4.2 Thin content

Floor: ⚠️ ≥30–50 unique words forming parsable sentences, unique `<title>`,
unique meta description, unique media. **A floor, not a target.**

Other forms: pages with content only behind a form; pages that exist to hold an
affiliate link; auto-generated pages with no editorial pass.

### 4.3 Thin slicing

Many pages differing only trivially. **This is the trap for programmatic content
strategies.** The tests:
- One page per size/color/variant with no distinct content
- One page per city for a service with **no genuine local component**
- Templated pages where only a noun is swapped

If you're generating pages from a data source, ask: *does each page answer a
question the others don't?* If not, consolidate.

---

## 5. Redirects

| Code | Use | Authority | Index behavior |
|---|---|---|---|
| **301** | Permanent | Passes | Old URL swapped. **Default.** |
| **308** | Permanent, method-preserving | Passes | Same as 301 for SEO |
| **302 / 307** | Genuinely temporary | Passes | **Old URL may stay indexed** |
| `meta refresh` >0s | Never for permanent | Unpredictable | Avoid |
| **303** | Never for SEO | Unpredictable | Avoid |

All `30x` types pass PageRank. The difference is **which URL stays in the index** —
that is the whole game. "302 is safer because it's reversible" is wrong reasoning.

**Check for:**
- Chains (each hop bleeds crawl budget) → collapse to one hop
- **Loops** (fatal). Classic case: 301 `/index.html` → `/` on a server whose
  `DirectoryIndex` *is* `index.html`
- Redirects to the home page instead of the nearest relevant page (lazy and lossy)
- 302s used for permanent moves

---

## 6. Site architecture

- **Link depth**: for sites under ~10k pages, everything reachable in **≤4 clicks**
  from home. Deeper = read as less important.
- **Don't over-flatten**: 200+ links on a page dilutes each link's share to near
  zero. Balance.
- **Breadcrumbs**: best structure for showing hierarchy + keyword-rich internal
  anchors. Add `BreadcrumbList` schema.
- **Descriptive anchor text** on internal links. "Click here" / "Read more" wastes
  the strongest internal signal you control.
- **Contextual in-body links** matter more than navigation links — ⚠️ >75% of
  on-site time is reportedly spent in browse/search discovery mode.
- **Taxonomy**: as few categories as possible without becoming useless. Cross-link
  items that legitimately belong to multiple categories.

**Pagination:** `rel="next"/"prev"` is **dead** — Google confirmed in March 2019 it
no longer uses them. Use plain crawlable `<a href>` links between pages. Optionally
a `view-all` page with paginated pages canonicaling to it — **only if it loads
fast**. Never canonical page 2+ to page 1.

---

## 7. XML sitemaps

**Include only:** canonical, indexable, 200-returning URLs.

**Exclude:** URLs with tracking params; redirecting URLs; non-200 URLs;
`noindex` URLs; canonicalized-away duplicates.

**Target: <1% of sitemap URLs having any of the above errors.** Above that,
engines may distrust the file.

- 50MB / 50,000 URL cap per file → use a sitemap index above that
- Reference it from `robots.txt`: `Sitemap: https://example.com/sitemap.xml`
- `<lastmod>` is used **when consistently and verifiably accurate**. Google has
  said it ignores `<changefreq>` and `<priority>` entirely.
- **A hardcoded `lastmod` is worse than none** — it will go stale silently. Derive
  from git, CMS timestamp, or build time.
- Specialized sitemaps: **image** (aids discovery under lazy-loading), **video**,
  **news** (only content from the last 2 days; keep it pruned).
- Use separate sitemaps per content type/section — it makes Search Console's
  indexation reporting diagnostic instead of a single opaque number.

**IndexNow** (Bing + Yandex, 2021) pings on create/modify/delete. ⚠️ Verify
Google's current adoption status before recommending it. Complements, never
replaces, XML sitemaps.

---

## 8. robots.txt

```
User-agent: *
Disallow: /admin/
Allow: /admin/public-thing
Sitemap: https://example.com/sitemap.xml
```

- Must be at the **root**, lowercase filename, plain text
- Order of rules is **irrelevant**; matching is by **most specific user-agent**
- Directives are **case-sensitive** for paths
- Pattern matching: `*` wildcard, `$` end-anchor
- `Crawl-delay` — supported by Bing, **not Google**
- **`Noindex:` in robots.txt is dead** — Google dropped support September 2019.
  If you find it, it's doing nothing.
- **Never block CSS or JS.** Google explicitly needs them to understand layout.
  This is a common and damaging misconfiguration.
- Subdomains and HTTP/HTTPS each need their **own** `robots.txt`

---

## 9. Structured data

**JSON-LD is Google's recommended format.** ⚠️ A 2020 SearchPilot test found no
measurable organic difference vs. microdata — the recommendation is about
authoring ergonomics.

**Not a ranking factor.** Value = rich results → CTR. Manual actions exist for
abuse, so over-marking carries real downside.

**Rules:**
- Choose the **most specific type** (`Restaurant` > `LocalBusiness`)
- **Only mark up what is visible on the page.** Narrow exception: context a human
  infers visually but a parser cannot (`bestRating`/`worstRating` on a star scale)
- **Never fabricate `aggregateRating`.** Common manual-action trigger
- Generate schema from the same source that renders the copy — makes drift
  structurally impossible rather than a discipline problem
- Validate: Google **Rich Results Test**, **Schema Markup Validator**, and Search
  Console's structured-data reports

**High-value types:** `Organization`, `WebSite`, `BreadcrumbList`, `FAQPage`,
`HowTo`, `Article`/`NewsArticle`, `Product`, `LocalBusiness`, `VideoObject`,
`Event`, `JobPosting`, `Recipe`.

> ⚠️ **Rich-result availability has changed — see `07-currency-2026.md` §4.**
> `HowTo` (desktop) retired Sept 2023; **`FAQPage` retired 2026-05-07**; seven
> more types retired June 2025. **Both remain valid Schema.org types Google still
> parses** — so **do not flag them for removal**, and **do not promise a rich
> result** from either. **Check the current supported-type list with `WebSearch`
> before promising any rich result at all.** The durable justification for
> structured data is machine comprehension and AI citation, not the SERP feature.

---

## 10. Page experience & Core Web Vitals

| Metric | Threshold (75th pct) |
|---|---|
| **LCP** — Largest Contentful Paint | ≤ 2.5s |
| **INP** — Interaction to Next Paint | ≤ 200ms |
| **CLS** — Cumulative Layout Shift | ≤ 0.1 |

⚠️ **INP replaced FID in March 2024.** Any source still saying "FID ≤ 0.1s" is
pre-2024. Target INP.

Plus: mobile-friendliness, HTTPS, no intrusive interstitials.

### Size this honestly

A controlled study over the page-experience rollout (1,188 keywords, 7,623
fixed-position control URLs) found CWV improvement per ranking position
**statistically indistinguishable between test and control** — sites improved
scores everywhere, they weren't reranked for it. Google's own framing: "quite a
subtle update... relevance is still, by far, much more important."

**Fix CWV for conversion and UX** — where the effect is large and direct. **Do not
sell it as a ranking lever.** Any copy implying "faster = higher rankings"
overclaims.

### LCP decomposition

1. **TTFB** — server/hosting/CDN
2. **Resource load delay** — discovery of the LCP resource (preload it)
3. **Resource load time** — image size/format (WebP/AVIF), compression
4. **Element render delay** — render-blocking CSS/JS

### CLS

- Always set `width`/`height` (or `aspect-ratio`) on images and video
- Reserve space for ads, embeds, and injected banners
- Never insert content above existing content post-load
- Use `transform` animations, not layout-triggering properties
- **Beware**: aggressively removing render-blocking CSS (a common PageSpeed
  recommendation) can *worsen* CLS. These optimizations trade against each other

### Tools

CrUX (**field data — the actual signal**), PageSpeed Insights, Lighthouse (**lab
data**), Search Console Core Web Vitals report, WebPageTest, GTmetrix.

**Field data beats lab data.** Lighthouse scores a synthetic run on your machine;
CrUX reports what real users experienced.

> **Sample every page template, not just the home page.** Reports of the March
> 2026 core update moving CWV to a **site-wide composite** score are unconfirmed
> by Google (tier BELIEVE — `07-currency-2026.md` §3), but template-level sampling
> is the correct method either way and costs nothing. A home-page-only CWV reading
> was always weak evidence; if site-wide aggregation is real, it is actively
> misleading.

---

## 11. Interstitials

Penalized: overlays covering primary content **on initial load from search**.
Fine: banners, in-app-install prompts, and — per Google — whatever happens *after*
the user interacts with the page. Exempt: legally required (cookie consent, age
verification).

---

## 12. International (see also `04-` for full treatment)

| Structure | Geotargeting | Authority | Recommendation |
|---|---|---|---|
| **ccTLD** (`brand.de`) | Automatic, unchangeable | **Separate** per domain | Highest cost |
| **Subdirectory** (`brand.com/de-de/`) | Search Console | **Shared** | **Default choice** |
| **Subdomain** (`de.brand.com`) | Search Console | Case-by-case | Middle |

- New gTLDs (`.app`, `.nyc`) carry **no ranking benefit** — including
  geographic-sounding ones
- **hreflang needs a complete handshake**: every version references every other
  version **and itself**. Missing self-reference invalidates the set
- Placements: `<head>`, **XML sitemap** (best at scale), HTTP header (PDFs)
- Format: `hreflang="en-us"` — ISO 639-1 language + ISO 3166-1 alpha-2 country.
  **A bare country code without a language is invalid**
- `x-default` for the fallback version
- **Never auto-redirect on IP or `Accept-Language`** — it blocks crawling of the
  other locales. Use a dismissible banner

**Validate:** Merkle's hreflang tester, Screaming Frog, Ahrefs, Semrush.
