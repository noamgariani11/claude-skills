# 04 — Vertical, Local & International

Image, video, news, Google Business Profile, hreflang. Weight: **8 of 100** —
**conditional. Run only the applicable sections and redistribute the rest of the
weight proportionally.** A B2B SaaS with no storefront should not be marked down
for having no map-pack presence.

⚠️ = 2023-sourced figure. **Re-verify before quoting.** Platform limits in
particular change frequently — **verify any specific number against the platform's
own current docs before it influences a rule or a recommendation.**

---

## 0. Applicability check — run this first

| Section | Run when |
|---|---|
| **Image** (§1) | Almost always — every site has images |
| **Video** (§2) | Site has video, or the category has video-heavy SERPs |
| **News** (§3) | Publisher or heavy PR motion. **Rare** |
| **Local** (§4) | Physical location(s), or service-area business |
| **International** (§5) | More than one language or country targeted |

**The arbitrage worth naming:** competitive density in image and video verticals is
far lower than in web search. A keyword unaffordable in web search may be
**winnable in the image or video vertical for the same intent**. For a small brand
this is the highest-ROI move in this file.

---

## 1. Image search

### Why it pays

1. Direct traffic from image results
2. **Blended placement** — image results pulled into universal SERPs win a second slot
3. **Quiet reputation effect** — real product/facility photos raise purchase
   confidence independent of ranking
4. **CTR lift** on the main result when a thumbnail attaches

⚠️ Google reported ~50% of online shoppers say images inspired a purchase (2019).
Vendor-published; directional only.

### What ranks an image

| Signal | Rule |
|---|---|
| **Filename** | Descriptive. `abe-lincoln.jpg`, not `IMG_4137a-bl2.jpg` |
| **`alt` attribute** | **Always quote it** (see failure mode below) |
| **Nearby text** | Text immediately before/after is the strongest association |
| **Caption** | A real caption below the image is highly beneficial |
| **Position** | Higher on the page ⇒ read as more important |
| **Page relevance** | Relevant images rank better *and* help the page rank |
| **Image sitemap** | Aids discovery, especially under lazy loading |

### Failure modes

- **Unquoted `alt`.** `alt=Abe Lincoln photo` silently loses everything after
  `Abe`. Invisible, common, trivially fixable. **Always grep for this.**
- **CSS background images are never indexed.** Google parses `<img>`; it does not
  index CSS backgrounds. Anything meant to be found must be a real
  `<img>`/`<picture>`
- **Lazy loading can hide images entirely.** Mitigate with image sitemaps and
  `<picture>`/`srcset` responsive patterns
- **Decorative images want `alt=""`.** Both Google and W3C. Marking up spacers is
  noise and an accessibility regression
- **Embedded thumbnails in the file** (Photoshop default) break some compression
  pipelines. Turn off

### Copyright

Buying stock buys a **licence to use**, not copyright. Some licences require
attribution links. **Google tracks copyright removal demands per domain** with
potential ranking consequence. Flag any image with unclear provenance.

---

## 2. Video & YouTube

### 2.1 Hosting decision

⚠️ A 2020 study found >90% of videos in Google's top 7 positions were
YouTube-hosted, ~98% at position 1. Dated, but the mechanism (Google property,
unmatched engagement data) is unchanged.

**If the goal is Google visibility: host on YouTube and embed.** Self-host only for
control, gating, or brand-player requirements.

### 2.2 Two engines, not one

**The most important structural fact in this section:**

| | **YouTube search** | **Recommendation system** |
|---|---|---|
| Surfaces | Search results | Home feed, "Up Next", Shorts feed |
| Optimize for | Query match — title, description, tags | **Satisfaction** — watch time, valued watch time, shares |
| Wins for | **How-to / instructional** | Almost everything else |

**For most channels, recommendations deliver more traffic than search.** Optimizing
titles and descriptions is necessary but insufficient — it addresses the smaller
engine.

**Recommendation inputs:** clicks (weak, early), **watch time**, **valued watch
time** (survey-based 1–5 stars), shares/likes/dislikes. Google's stated "4 Rs":
**Remove** violative, **Reduce** borderline, **Raise** authoritative, **Reward**
trusted creators.

### 2.3 Metadata

| Element | Rule |
|---|---|
| **Thumbnail** | ⚠️ ~90% of top performers use a custom one. **CTR factor, not ranking.** Close-up faces or bright color; rule of thirds |
| **Title** | Up to 100 chars. Keywords early, brand late. **Never clickbait** — the target is watch time, not clicks |
| **Description** | Up to 5,000 chars; **only ~110 chars show in the SERP.** Front-load. Don't repeat the title |
| **Hashtags** | Up to 60; ~4–6 is the working range. **Exceeding 60 makes YouTube ignore all of them.** Render *above* the title, so they affect CTR |
| **Tags** | Disambiguation only (typos/misspellings). Not topic tags |
| **Chapters** | Timestamps in the description → chapters → Google "key moments" deep links in the SERP |
| **Captions** | See below |
| **End screens / cards** | Drive session watch time, which feeds recommendations |

### 2.4 Captions vs. subtitles — distinct things

- **Subtitles** = dialogue as text. For sound-off viewing and translation
- **Captions** = dialogue **+ non-verbal sound**. For deaf/HoH viewers

Specifics:
- **SRT / SubViewer** are text-editable — right starting point. **SCC** gives the
  most precise alignment
- Transcript syntax: `>>` marks a speaker change; `[brackets]` mark non-verbal sound
- **Non-English captions must be UTF-8** or accents and non-Latin scripts corrupt
- Auto-captions work under ~1 hour and are usually faster to *correct* than to author
- **Many platforms mute video by default.** On those surfaces subtitles are the
  difference between comprehension and none — not an accessibility nicety

### 2.5 Length — stop asking

**Do not ask "how long should my video be."** Relative watch time (% viewed)
dominates for short videos; absolute watch time for long ones. YouTube wants both
to succeed and no longer infers a global length preference from viewing history.

**Make it the length the content needs**, then use the audience-retention report to
adjust. **Never give a duration target as an SEO instruction.**

### 2.6 Self-hosted video in web search

For rich-result eligibility:

- **One video per page**, prominently featured. Video title in both `<title>` and a
  top-level heading above it; descriptive text below
- **Stable static URLs** for page and file. CDNs rotating URLs break indexing
- Prefer `<video>` — the only one of `<video>`/`<iframe>`/`<object>`/`<embed>` with
  a native **`poster`** thumbnail attribute
- Declare thumbnails in a **video sitemap** *and* on-page (structured data
  preferred — `VideoObject` supports more attributes)
- Not behind login, paywall, interstitial, or lazy-load gate
- Supported containers include MP4, WebM, MOV, MPEG, AVI, MKV, and others —
  **verify the current list** before asserting

---

## 3. News

**You can no longer apply to Google News.** Google selects automatically.

**Prerequisites:**
- A **dedicated news site** — not a news *section* on a product site
- **Original** content — republishing doesn't qualify
- **Credible, named authors** with subject-matter expertise
- Updated **multiple times per day**

Plus: author bio pages, staff listing, About page with a physical address, visible
bylines and publication dates.

**The consequence: a company blog will not qualify, ever.** That's fine — it means
a launch motion should target *being covered by* news sites, not becoming one.
**Do not build toward Google News eligibility.** If a client asks, say this.

**Two surfaces, different algorithms:** Google News (the property) and **Top
Stories** (in universal results) rank differently and draw from different pools —
Top Stories can include Reddit and other UGC. **Top Stories weights freshness
hardest**; keeping a developing story updated is the dominant lever.

---

## 4. Local

### 4.1 The three inputs

**Relevance, prominence, and proximity.** Proximity has no analogue in web search
and constrains everything else — results are bounded to a radius that tightens with
competitive density. Dense urban district: a few blocks. Rural: miles.

### 4.2 Google Business Profile — ranking vs. engagement

**The table most local-SEO advice gets wrong:**

| Field | Ranking factor? |
|---|---|
| **Primary category** | ✅ **Strongest single lever** |
| **Business name** | ✅ (stuffing it violates guidelines → suspension risk) |
| **Address** (proximity) | ✅ |
| **Additional categories** | ✅ |
| **Website link** | ✅ |
| Phone number | ❌ (call-tracking numbers are fine and are best practice) |
| Hours | ❌ — affects engagement, which is |
| Photos / videos | ❌ — same |
| Description | ❌ **Do not keyword-stuff.** Zero ranking influence |
| Google Posts | ❌ — same |
| Q&A | ❌ — same |

**The pattern:** most fields influence rankings only **through engagement**.
Stuffing them is pure downside — hurts engagement, doesn't help ranking.

**Call tracking done right:** tracking number as **primary**, real number as
**secondary**, both with a local area code.

### 4.3 Myths — dispatched

These are actively sold as services. Name them:

| Myth | Reality |
|---|---|
| Google My Maps driving-direction spam | **No effect.** Real users navigating to you *does* count |
| Embedding your Maps listing on-site | **No ranking effect.** Helps conversion |
| Geotagging image EXIF | **No meaningful effect** |
| Buying Google Ads | **No effect** on organic local rank |
| Call-tracking numbers hurt | **They don't**, configured as above |
| Keywords in review *replies* | **No effect.** Keywords in the reviews themselves do. Stuffing replies **hurts** via engagement |
| **Defining a service area ranks you there** | **False. The biggest and most expensive myth here** |

**The service-area finding, stated plainly:** rankings derive from the **verified
address**, always. Declaring service in three cities does not produce rankings in
three cities. A business at a Dallas address listing Dallas/Houston/Austin ranks
**only near the Dallas address** — roughly 3–5 miles out, competition-dependent.
The only remedy is a physical location with its own verified GBP.

**This also explains a common false alarm:** rank trackers default to the centroid
of the declared service area, so a hidden-address business appears to rank nowhere.
**Scan from the verified address.**

### 4.4 Reviews

- Ask **every** customer; make it one click
- **Respond to every review.** The audience for a reply to a negative review is
  **every future reader**, not the reviewer
- **Stay above 4.0** — below it you're filtered out of qualitative queries
  ("best", "top")
- **Never buy reviews.** ⚠️ FTC penalties reported upwards of $43,000 per review —
  **verify the current figure**, it's inflation-adjusted annually
- Identify yourself by name in responses; **never** reveal a customer's private
  details

### 4.5 Local links and citations

Local links are weighted **differently** — relevance to the *locale* can outweigh
domain authority. A small local site with weak metrics may be worth more than a
strong unrelated one.

Sources: sponsorships (buying a sponsorship that yields a link is fine; buying a
link is not), volunteering, meetups (offer your space), local blogs, clubs staff
belong to, business associations, chambers of commerce.

**Citations** (NAP mentions) matter **less than they used to** as the algorithm
improved. **Get them consistent once; do not run an ongoing citation program.**

### 4.6 Local on-site

- One page per location, each with unique content, address, and phone
- `LocalBusiness` schema on the GBP landing page **only** — not sitewide
- NAP visible on the page GBP links to
- Location in title, top heading, URL, content
- Embed Maps for conversion (not ranking)

### 4.7 Auditing local rank

**A single rank number is meaningless for local** — you rank differently at
different physical points. Use a **grid/geo scan** (BrightLocal, Local Falcon) to
map rank across an area, not a single position.

**Check for fake and obsolete competitors** in the map pack — a zero-sum surface
with only three slots. Signals: "Claim this business", no reviews, no photos, no
signage in Street View, keyword-stuffed names, `business.site` websites,
residential addresses inconsistent with the business type. Reporting these is
legitimate and can move you up immediately.

---

## 5. International

### 5.1 Structure

| Structure | Geotargeting | Authority | Cost |
|---|---|---|---|
| **ccTLD** (`brand.de`) | Automatic, **unchangeable** | **Separate** per domain — build each from zero | Highest |
| **Subdirectory** (`brand.com/de-de/`) | Search Console | **Shared** | **Lowest. Default** |
| **Subdomain** (`de.brand.com`) | Search Console | Case-by-case | Middle |

**Subdirectories win for most sites** — the reason is authority consolidation, not
technique. Exceptions: legal requirements, a market where a local TLD is a trust
signal, or targeting a market with a different dominant engine (e.g. Baidu
generally favors a local ccTLD with a local IP — **verify current guidance**).

⚠️ Some ccTLDs are treated as generic by Google (`.co`, `.io`, `.fm`, `.ad`) and
are **not** auto-geotargeted. Check the current list before assuming.

New gTLDs (`.app`, `.marketing`, `.nyc`) carry **no ranking benefit** — including
geographic-sounding ones.

### 5.2 hreflang

**Requires a complete handshake:** every version references every other version
**and itself**. A missing self-reference or one-way link invalidates the set.

**Placements:** `<head>`; **XML sitemap** (best at scale); HTTP header (PDFs and
non-HTML).

**Format:** `hreflang="en-us"` — ISO 639-1 language + ISO 3166-1 alpha-2 country.

**The two dominant failure modes:**
1. Pointing at **non-indexable URLs** — 4xx/5xx, redirects, `noindex`, or pages
   canonicaling elsewhere
2. **A bare country code with no language** — invalid. Language is always required

`x-default` marks the fallback for unmatched locales.

**Validate:** Merkle's hreflang tester, Screaming Frog, Sitebulb, Ahrefs, Semrush.
**Test in staging before shipping** — hreflang errors are easy to make in bulk.

### 5.3 Rules

- **Never auto-redirect on IP or `Accept-Language`.** It blocks crawling of other
  locales. Use a **dismissible banner** offering the alternate version, and persist
  the choice
- **Translate URLs** into the target language where the script is Latin;
  transliterate rather than using non-Latin characters
- **Translate/localize everything** — metadata, headings, navigation, body. Use
  **native speakers**; machine translation needs human validation
- **Same language, different countries still diverge** — terminology, currency,
  seasonality, product availability. `en-us` and `en-gb` are not interchangeable
- **Cross-link locale versions** with crawlable links
- **Earn local links** in each target market — this is the part that doesn't
  transfer, and it's why each new locale is a marketing project rather than a
  translation project
- **You cannot target a continent or region.** Engines support **language** and
  **country** only. "Targeting Europe" is not a thing — pick countries
