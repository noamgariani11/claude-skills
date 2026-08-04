# Domain Accuracy — ground truth and the citation rule

This is the highest-risk file in the skill.

A platform expert who asserts *"X's limit is 280"* from model memory is **exactly as dangerous as
the app being wrong** — and more dangerous, because a confident wrong correction gets *committed*.
Model recall on platform specifics is stale by construction: char limits, ad objective names, and
algorithm behavior all change, and the model's training data has a cutoff.

Everything below was **verified against official sources on 2026-07-11**. Rows that could not be
verified say so, and **must not be filled in from memory.**

---

## The citation rule (non-negotiable)

Every domain-accuracy finding must cite **one** of:

1. **`research/platforms/<platform>.md` or `research/ads/*`** — this repo's own research corpus.
2. **A `HIGH`-confidence row in the tables below** — with its source URL.
3. **A live `WebFetch`** of the platform's own docs. Cite the URL and the date fetched.

A finding with none of these is **`[UNVERIFIED]`**. It is *named* in the report so the next run can
chase it, but it **cannot be scored as a defect** and **cannot be handed to Phase 5** for a code
change.

> **Never edit `lib/tailoring/platforms.ts` or `lib/ads/formats.ts` on the strength of model recall
> alone.** If you cannot cite it, you do not know it.

### Severity of an accuracy defect

| Finding | Severity |
|---|---|
| Code says a limit/format that would make a real post **fail to publish** (see the hard-fail rows) | `critical` |
| An **invented** ad campaign type / objective that doesn't exist in that ads manager | `high` |
| Code ↔ `research/*.md` drift (definition-of-done #4 violation) | `high` → `RESEARCH-DRIFT` |
| A rule stated as platform **policy** that is actually **folklore** (see below) | `medium` |
| A rule that is outdated but harmless | `medium` |
| Cosmetic wording in a blueprint | `low` |

---

## ⚠ The folklore problem — read this before flagging anything about links or hashtags

The 2026-07-11 verification pass found that **the marketing industry's two most repeated "rules"
are not platform policy anywhere we could check.** This matters enormously, because the app's code
encodes them as if they were.

### Link penalties: FOLKLORE, and officially denied on three platforms

| Platform | What the platform actually says |
|---|---|
| **Threads** | Mosseri, Nov 2024: *"We don't downrank links,"* but they don't weight p(click) highly. In 2025 Meta retuned ranking so URL posts are "ranked properly". [threads.com/@mosseri/post/DCpQG0hz0m8] |
| **Instagram** | Mosseri: *"if you say 'link in bio' it's going to decrease your reach. That is not true… it will not affect your reach one way or another."* |
| **X** | Musk, 2025-04-25: *"there is no explicit rule limiting the reach of links in posts."* The algorithm maximizes user-seconds, so a link that shortens dwell **naturally** gets less exposure — an **emergent effect, not a rule.** |
| **Facebook** | Meta officially demotes **clickbait links** and **links to low-quality page experiences** — *not links as such.* [transparency.meta.com] |
| **LinkedIn** | **No primary source in either direction.** The penalty is unverified; so is its absence. |

> **✅ FIXED as of run #13 (2026-07-16) — do NOT re-flag this.** This file used to say
> `lib/tailoring/platforms.ts` justified X's `links: "first-comment"` with a "cuts reach ~50%"
> claim. **It no longer does, and the number does not exist anywhere in the repo.** The X expert
> grepped `lib/ components/ app/` for `cuts reach|50%|94%|13.5|2-4x` → no link-penalty number.
> What ships now is exactly the right distinction:
> *"Keep the external link out of the main post; put it in the first reply - X favors on-platform
> dwell, **though the exact reach effect isn't officially quantified**"*.
> `research/platforms/twitter-x.md` goes further: it explains the *mechanism* (Phoenix has no
> positive objective for an external link click, so demotion is **learned, not written**), names
> the "94% fewer views" figure as one account's A/B test and refuses to ship it, and grounds the
> one real primary number (the API bills $0.200 for a post with a URL vs $0.015 without —
> docs.x.com/x-api/getting-started/pricing).
> **An expert who "corrects" this from this file's old text is filing a fabricated finding.**

**Where the folklore actually lives now (run #13, `X-BENCH-FOLKLORE`, `high`):** the scrub landed
in `platforms.ts` and missed its sibling. **`lib/tailoring/organic-benchmarks.ts:125`** still ships
`target: "Replies weigh ~13.5× a like; reply-backs and bookmarks are top signals"` — **both halves
are claims `research/platforms/twitter-x.md` §14 explicitly lists under "Never claim"** (weights
multiply *probabilities*, not counts; no sourced bookmark multiplier exists). It contradicts
`platforms.ts:218` **in the same module**, which correctly calls "a reply is worth 13.5 likes"
*"a category error, not a fact."* It renders live at `app/(dashboard)/analytics/page.tsx:281`.
It survived because **no test covers `organic-benchmarks.ts`** — the classic shape of a partial fix.
Route `RESEARCH-DRIFT`. Check this file's sibling modules before declaring any folklore scrub done.

### Hashtags-as-ranking-signal: UNVERIFIED almost everywhere

- **Instagram officially says hashtags do NOT boost reach** (they categorize). Hashtag-following
  was retired ~Dec 2024.
- **TikTok** is the one place it's official: caption/sound/hashtag info is one of three signal
  groups — but there is **no official optimal-count guidance.** "3–5 hashtags" is folklore.
- **X, LinkedIn, Facebook**: no official statement that hashtags are a ranking signal.

Any hashtag-count heuristic in the code should be labeled a **soft convention**, not a platform
rule. Flagging the *convention* is fine; flagging it as a *rule violation* is not.

---

## Organic ground truth (verified 2026-07-11)

`HIGH` = safe to cite. `MED` = cite with the caveat. `UNVERIFIED` = **must** be re-grounded before
use in a finding — the value here is a hint, not evidence.

### Character limits

| Platform | Limit | Conf | Source |
|---|---|---|---|
| X | **280** standard; **25,000** Premium long-post (timeline still truncates at 280) | HIGH / MED | docs.x.com/x-api/posts/creation-of-a-post |
| LinkedIn | **3,000** feed post. Over-length → API `400 FIELD_LENGTH_TOO_LONG` (**hard fail, not truncation**). Article: 125,000 | HIGH | learn.microsoft.com/…/posts-api |
| Instagram | **2,200** caption; ≤30 hashtags (API bound), ≤20 @mentions | HIGH | developers.facebook.com/…/ig-user/media |
| TikTok | **2,200 UTF-16 runes** via API (hashtags/mentions count). In-app 4,000 is unofficial — **2,200 is the enforceable ceiling for an API tool** | HIGH / MED | developers.tiktok.com/…/direct-post |
| Facebook | 63,206 widely cited but **no official Meta doc exists**; Graph API states no limit | UNVERIFIED | — |
| Threads | **500 — counted as UTF-8 BYTES**, not characters. Emoji and URLs consume multiple bytes; a naive JS `.length` check **under-reports and will hard-fail on publish** | HIGH | developers.facebook.com/docs/threads/posts |
| YouTube | Title **100**; description **5,000** | HIGH | support.google.com/youtube/answer/57407 |
| Reddit | Title 300; selftext 40,000; comment 10,000 | MED (Reddit blocks fetchers; secondary only) | — |
| Pinterest | Title 100 (first ~40 show in feed); description **800** per Pinterest's own spec page | HIGH | help.pinterest.com/…/pinterest-product-specs |
| Snapchat | No real text surface. Ad chrome only: brand ≤25, headline ≤34 | HIGH | forbusiness.snapchat.com/advertising/ad-formats |
| Tumblr | **No single post limit.** 4,096 chars **per text block**; 1,000 blocks/post | HIGH | help.tumblr.com/…/writing-posts |
| Hacker News | Title **80** (form-enforced; not in the guidelines text) | MED | news.ycombinator.com |

### Hard publish-fail rules (a violation here is `critical` — the post does not go out)

| Platform | Will hard-fail if… |
|---|---|
| **Threads** | >500 **bytes**; >5 unique URLs (enforced 2025-12-22); **>1 topic tag — exactly ONE per post**; video >300s/>1GB; carousel <2 or >20 |
| **Instagram** | Non-JPEG image; aspect outside **4:5–1.91:1**; >8MB or width outside 320–1440px; Reel <3s or >15min or >300MB; >10 carousel items; caption >2,200 / >30 tags / >20 mentions; container >24h old; **personal (non-professional) account** |
| **LinkedIn** | Post >3,000 chars; multi-image <2 or >20; non-MP4 video or outside 3s–30min |
| **TikTok** | Title >2,200; `privacy_level` not in the creator's allowed options; enabling duet/stitch/comment the creator disabled; video over that **account's** `max_video_post_duration_sec` (must be read from `creator_info`, never assumed); **an unaudited app can only post `SELF_ONLY`** |
| **X** | Poll posts: text must be ≤280 **even for Premium**; max 4 photos OR 1 GIF OR 1 video |
| **Facebook** | Missing Page access token / `pages_manage_posts`; an app may only edit a post **it** created; scheduling window 10 min–30 days |

> **TikTok has a non-optional compliance flow**: call `creator_info/query` first and drive the UI
> from its response (no default privacy — the user must pick; must show Music Usage Confirmation,
> branded-content consent, and a content preview; no added watermark). **If Sheevook's TikTok path
> doesn't do this, it is not a compliant integration** — `high`.

### Media specs

| Platform | Spec | Conf |
|---|---|---|
| Instagram | Image: JPEG only, ≤8MB, width 320–1440, aspect 4:5–1.91:1. Reels: 3s–15min, ≤300MB, 9:16. Carousel ≤10 (all cropped to first item's ratio) | HIGH |
| Threads | Image ≤8MB, width 320–1440, aspect ≤10:1. Video ≤300s, ≤1GB. Carousel 2–20 | HIGH |
| TikTok | MP4/WebM/MOV, 360–4096px, 23–60 FPS, ≤4GB. Photos JPEG/WebP ≤20MB | HIGH |
| LinkedIn | Multi-image 2–20. **No enforced aspect ratio** for organic. Video MP4 only, 3s–30min | HIGH |
| YouTube | **Shorts ≤ 3 minutes** (raised from 60s; applies to uploads on/after 2024-10-15) | HIGH |
| Pinterest | **2:3 (1000×1500)** recommended | HIGH |
| X | Aspect ratios — **UNVERIFIED** (X blocks fetchers). Video ~2:20 free | MED/UNVERIFIED |
| Facebook | Max images, Reels duration — **UNVERIFIED** (Meta docs state no limits) | UNVERIFIED |

### Platform-specific facts worth knowing

- **YouTube:** YouTube's own docs credit **average view duration** as the recommendation signal and
  warn that **clickbait CTR backfires** ("clickbait videos tend to have low AVD and therefore are
  less likely to get recommended"). **Do NOT let an expert claim "high CTR ranks you higher" as
  official** — that is a widely-repeated overreach.
- **Reddit:** the **"9:1 self-promo rule" is NOT official Reddit policy.** It comes from the
  retired reddiquette / self-promotion wiki. It remains a real *community norm* enforced by mods
  per-subreddit — cite it as a norm, never as a rule. (Reddit's own pages 403 to fetchers, so all
  Reddit rows here are secondary.)
- **Pinterest:** officially self-describes as *"a visual search and discovery platform."* Links are
  a first-class Pin field and genuinely work (unlike IG captions). But **"Pins have a months-long
  half-life" has NO official source** — UNVERIFIED, do not ship it as fact.
- **Hacker News** (official guidelines, all HIGH): *"don't editorialize"*; use the original title;
  no uppercase for emphasis; crop gratuitous numbers ("10 Ways To X" → "How To X"); *"don't use HN
  primarily for promotion."* **Show HN** must be something people can **try out** — *"blog posts,
  sign-up pages, newsletters, lists… can't be tried out, so can't be Show HNs."* Title must begin
  `Show HN:`; minimize signup friction; never solicit upvotes.
- **Facebook:** **engagement bait** (explicitly asking for likes/shares/comments/tags/votes) is an
  official **demotion**. If Sheevook generates "Like if you agree!", that's a real, citable defect.

---

## Ads ground truth (verified 2026-07-11)

Structural facts about the repo that experts get wrong (**not** findings):

- The 6 networks are `meta`, `google_ads`, `x_ads`, `linkedin_ads`, `tiktok_ads`, `reddit_ads`.
- **Instagram + Facebook ads run through `meta`. YouTube ads run through `google_ads`.** There is
  deliberately no `youtube_ads` or `instagram_ads`. An expert who "finds" one has misread the
  architecture.
- **The X platform key is `twitter`, not `x`** (research doc: `research/platforms/twitter-x.md`).
  The *ad network* is `x_ads`.

### ⚠ Live defects this table already implies in `lib/ads/formats.ts`

Verified 2026-07-11. **Confirm the id still exists in the file before filing** — but if it does,
these are citable, not speculative:

| Repo id | Reality | Severity |
|---|---|---|
| ~~`meta_advantage_shopping` → `"Advantage+ Shopping"`~~ | ✅ **FIXED — verified run #13. `formats.ts:242` now reads `name: "Advantage+ Sales"`** with a comment dating the Feb 2025 rename. Id kept stable (correct — ids are internal). **Do NOT re-file.** | none |
| *(missing entirely)* | **Advantage+ Leads** — third Advantage+ type, still absent from the Meta block (re-confirmed run #13). | `medium` gap — **still open** |
| ~~`tiktok_shopping` → `"Video Shopping"`~~ | ✅ **FIXED — verified run #13. `formats.ts:571` now reads `name: "GMV Max"`**, with a comment dating the July 2025 retirement. **Do NOT re-file.** | none |
| `google_display` (formats.ts:146) | Still exists **today**. Google is folding Display into Demand Gen as the "GDN" channel; migration tool rolls out **June 2026**. | `low` — a forward risk to note, **not** a defect |
| `linkedin_message` → `name: "Conversation Ads"` (formats.ts:333) | **NOT a defect.** Conversation Ads are current. The *id* is a slight misnomer (the retired format is "Message Ads"), but the user-facing name is right. **Do not "fix" this.** | none |

### Verified objective lists (cite these)

- **Meta (ODAX):** Awareness, Traffic, Engagement, Leads, App promotion, Sales
  (`OUTCOME_*` enums). Legacy objectives (CONVERSIONS, LINK_CLICKS, REACH, …) are deprecated.
  Advantage+ types: **Sales** (ex-Shopping), **App**, **Leads**.
- **Google Ads:** Search, Performance Max, Demand Gen, Display, Video, Shopping, App (+ niche:
  Smart, Hotel, Call). **Retired: Discovery** (→ Demand Gen, Jan 2024), **Smart Shopping + Local**
  (→ PMax, 2022), **Video Action Campaigns** (→ Demand Gen / Video "Drive conversions").
  *"AI Max for Search" is a setting inside Search, NOT a campaign type.*
- **LinkedIn:** 8 objectives — Brand awareness, Website visits, Engagement, Video views, Lead
  generation, Website conversions, Job applicants, Talent leads. **Sponsored Messaging IS allowed
  in the EU** since Oct 2024 (opt-in members only) — a blanket "EU-restricted" flag is **wrong**.
- **TikTok:** Reach, Traffic, Video views, Community interaction, Branded Mission, App promotion,
  Lead generation, Sales. **Spark Ads always require an existing organic post**; a per-post
  authorization code is needed for *third-party creator* posts, but a linked Business Center
  identity works without one — so "always needs an auth code" is an overstatement.
- **X:** Reach, Video views, Pre-roll views, Website traffic, Engagements, Followers, App installs,
  App re-engagements, Website conversions. (business.x.com 402s to fetchers — MED confidence.)
- **Reddit:** Brand Awareness **and Reach** (one combined objective, CPM), Traffic, Conversions,
  App Install, Video Views, + Lead Generation (beta). **There is NO standalone "Engagement"
  objective** — worth checking against Sheevook's `CampaignObjective` mapping.

### X ads copy rules — hard validation, `critical` if violated

| Fact | Value | Conf | Source |
|---|---|---|---|
| **Hashtags BANNED in X Ads** | **TRUE, VERIFIED.** X Ads Quality Policy: *"Ads must not include hashtags or urls in the ad text."* Announced by @XBusiness 2025-06-26, effective **2025-06-27**. The repo's code comment is **CORRECT.** | HIGH | x.com/XBusiness/status/1938425514072621323 |
| **URLs also banned in ad text**; **≤1 emoji** | Same policy. The repo's comment likely omits both. | HIGH | business.x.com quality-policy |
| Scope | Applies to **ad copy only** — organic X posts may still use hashtags. Exceptions: Boosted Posts, and ads targeting **Japan/Korea**. | MED-HIGH | same |

**So: if any X ad-copy path emits a `#`, a URL, or 2+ emoji, that is a `critical` publish-blocking
defect with an official citation.** This is the single most actionable ads check in the skill.

### The Pinterest / Snapchat gap — ⚠️ **CLOSED. Do NOT re-file this.**

Both have **real self-serve ads platforms** (ads.pinterest.com, ads.snapchat.com). Objective sets:
Pinterest — Brand awareness, Video completion, Consideration, Conversions, Catalog sales.
**Snapchat — Awareness & Engagement · Traffic · Leads · App Promotion · Sales** (exactly five;
consolidated from 12 in Aug 2024, [forbusiness.snapchat.com/blog/ads-manager-objectives](https://forbusiness.snapchat.com/blog/ads-manager-objectives),
re-verified 2026-07-16).

**This file used to say both were "absent from `AD_NETWORKS`" — that is FALSE as of run #13.**
`lib/ads/networks.ts:110` ships `pinterest_ads` and `:121` ships `snapchat_ads`, both `live: false`
and correctly surfaced as "planning only" rather than presented as launchable. The gap is **closed**.
An expert trusting the old line files a **fabricated gap** — the exact failure this file exists to
prevent.

**The real, live defect is now INSIDE the Snapchat entry** (run #13, `high`, verified on `/ads`):
`lib/ads/formats.ts:795-850` ships **3 of the 5**, invents a merged **"Sales / Leads"** that no buyer
can select, and **omits Traffic** — while `snap_sales_leads.bestFor` still claims `"traffic"`, routing
traffic buyers into a conversion campaign. Blast radius is capped (`bestFor` feeds only the teaching
surface `CampaignTypeGuide.tsx:193`, not an auto-builder) → `high`, not `critical`.
Root cause is `RESEARCH-DRIFT`: `research/platforms/snapchat.md` §9 documents ad *formats* but never
lists the objectives, so nothing anchors the code.

**Standing lesson: these ground-truth rows go stale in the OPTIMISTIC *and* PESSIMISTIC direction.**
Run #13 had three experts (X, Snapchat, Media Buyer) independently catch this file claiming a defect
the repo had already fixed. **Re-verify the code before filing any gap this file predicts.**

---

## Maintaining this file

One of the skill's compounding assets. Each run:

- When an expert grounds an `UNVERIFIED`/`MED` fact against a live doc, **promote it**: write the
  value, set the date, cite the URL, and log it in `learnings.md` under `ground-truth promoted`.
- When a fact turns out to be wrong, **overwrite it in place.** A stale line here is worse than no
  line, because it will be trusted.
- Never append a diary. This file records what is true *now*.
- **Known-blocked sources** (do not burn a run rediscovering this): Reddit (403), X help/business
  domains (402/403), `facebook.com/business/help/*` (bot-blocked). Route around them via developer
  docs, official accounts, or transparency.meta.com.
