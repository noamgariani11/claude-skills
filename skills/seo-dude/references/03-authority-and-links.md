# 03 — Authority & Links

Backlink profile, internal architecture, anchor text, toxic links, earned-link
strategy. Weight: **17 of 100**. Load for Phase 4 or `--scope links`.

⚠️ = 2023-sourced figure. **Re-verify before quoting.**

---

## 1. The model — links as citations

Links work like academic citations. The founding insight (Page & Brin, 1998):

> "The citation (link) graph of the web is an important resource that has largely
> gone unused in existing web search engines."

**Why a link carries information at all:** a site linking out is *inviting users to
leave*. Publishers work hard to keep people. So the act of linking anyway signals
genuine belief that the destination is worth it. That is the whole mechanism, and
everything about link quality follows from it.

**The corollary that kills most link-building schemes:** any link the destination
site *asked for*, *paid for*, or *traded for* carries no such signal — which is
exactly why engines discount them.

---

## 2. The trust model

Engines start from a **seed set of trusted sites** and propagate outward,
**decaying with each hop**. One click from a highly trusted source inherits a lot;
three clicks inherits little.

**Practical consequence:** a small number of links from genuinely trusted,
topically-adjacent sites beats a large number of distant ones — and the gap is
**not linear**. This is the mechanical justification for quality-over-quantity, and
it's why "we got 400 links this quarter" is not an answer to "did authority
improve."

---

## 3. What makes a link count

| Factor | Detail |
|---|---|
| **Topical relevance** | Of the linking page *and* the whole linking site. A site with hundreds of relevant pages linking from a relevant page ≫ a one-off |
| **Placement** | Main body ≫ footer/sidebar. Google's "reasonable surfer" patent: links likelier to be *clicked* carry more weight |
| **Proximity** | Surrounding text and nearest heading provide context |
| **Anchor text** | Descriptive metadata about the destination |
| **Source authority** | Trust and topical authority of the linking domain |
| **Timing & tenure** | When first seen, how long it persisted. Disappearing right after a site change is a negative signal |
| **Source diversity** | Links from only one *class* of site reads as a scheme |
| **Link count on the page** | 200+ outbound links ⇒ each share approaches zero |

**Source diversity, concretely.** If every link comes from blogs, that's poor
diversity. Healthy profiles mix: national and local media, industry publications,
universities with related programs, government/nonprofit, podcasts, conference
sites, adjacent-industry sites, and forums/communities.

---

## 4. Auditing a backlink profile

### 4.1 Data sources — use more than one

**No single tool sees the whole web.** Each vendor crawls a slice. Combining
multiple sources and deduplicating yields a materially larger set than any one
tool.

- **Google Search Console** → Links report (free; heavily filtered, incomplete)
- **Bing Webmaster Tools** → different crawl, genuinely different data
- Commercial: Ahrefs, Semrush, Majestic, Moz Link Explorer, LinkResearchTools

**If none are available, say so.** Report the profile as unassessed rather than
inferring it from GSC's filtered sample.

### 4.2 What to look at

1. **Referring domains, not total links.** 10,000 links from 3 domains is 3 votes
2. **Topical relevance distribution** — what share is actually in-category?
3. **Source-type diversity** (§3)
4. **Anchor-text distribution** (§5)
5. **Growth curve** — steady accumulation vs. a spike. Spikes read as campaigns
6. **Lost links** — recently dropped links that used to help. Note vendor latency:
   a link can be gone for weeks before a tool reports it. **Verify important ones
   manually**
7. **Top linked pages** — which content actually earns links? That's your proven
   asset type

### 4.3 The competitor gap

The most actionable output of a link audit:

1. Pull backlinks for the top 3 organic competitors
2. Find domains linking to **≥2 competitors but not you** — these are demonstrably
   willing to link in your category
3. Find the **pages** on their sites that earn the most links — that's the content
   format that works in this market
4. **Copying their link sources only achieves parity.** To outrank, you need
   sources they don't have. Say this explicitly rather than shipping a "get these
   50 links" list that caps at second place

---

## 5. Anchor text

**Over-optimization is a negative signal.** ⚠️ If 19 of 20 external links use the
exact target keyword, that reads as unnatural and the links get discounted.

**A healthy natural distribution skews toward:**
- Brand name (`Acme`, `Acme Corp`)
- Bare URL (`acme.com`)
- Generic (`this article`, `here`, `their guide`)
- Natural phrases containing the topic
- Exact-match keyword — **a minority**

**Never request specific anchor text.** Explicitly against engine guidelines.
Exception: asking someone to fix a **broken** link, or to update an unlinked brand
mention to a link — you're correcting, not directing.

**Internal anchor text is different** — you control it, it's expected to be
descriptive, and it isn't scored for naturalness the same way. Use it well.

---

## 6. Toxic links — proportion first

**Before starting a cleanup project, establish it's warranted.**

**Penguin 4.0 (2016) stopped penalizing and now discounts bad links to zero.** Most
link-cleanup advice predates this and is obsolete. For most sites with a handful of
junk links, **Google already ignores them and cleanup is wasted effort.**

**Cleanup is warranted only when:**
- There is a **manual action** for unnatural links (Search Console will say so), **or**
- The organization has a **known history** of buying links, large-scale guest
  posting, or link schemes

**Otherwise: don't.** Say so in the report — talking a client out of a
three-month disavow project is a real deliverable.

### If warranted — patterns to look for

| Pattern | Signal |
|---|---|
| **Over-optimized anchors on deep pages** | Ecommerce product pages with many keyword-rich external links is not natural |
| **Country mismatch** | Volume of links from countries you don't operate in |
| **Language mismatch** | An English anchor in otherwise-Chinese page text |
| **Guest-post footprints** | `/blog/` URLs, `?q=` params, blog-host domains, keyword-rich in-body links |
| **Link lists with unrelated neighbors** | Your travel site beside a casino and a payday-loan site |
| **Sitewide footer links** | Especially across unrelated sites |
| **Article directories / cheap directories** | Little or no editorial review |
| **Comment/forum spam** | Automated placement |

**Note:** local business directories are a **different thing** and are fine.

### The disavow tool

- Use **only** with a manual action or a known scheme history
- **Disavow at domain level**, not URL — your data is incomplete, and one bad link
  from a domain implies others you can't see
- Google **discards** disavowed link value; it does not redistribute it
- Effect requires Google to **re-crawl each linking page** — months
- **Attempt actual removal first.** Reviewers want to see the effort, and low
  compliance is expected and understood

**Never disavow speculatively.** You will remove links that were helping.

---

## 7. Earning links — what actually works

**Reframe:** you are not building links. You are producing something worth citing
and making sure the right people see it.

### Asset types that earn links

| Type | Why it works |
|---|---|
| **Original research/data** | Press and bloggers need statistics to cite. **The highest-yield format** |
| **Surveys** | Same, cheaper. Ask questions your industry argues about |
| **Comprehensive guides** | Becomes the canonical reference others link to instead of re-explaining |
| **Free tools/calculators** | Only if genuinely new — the 17th mortgage calculator earns nothing |
| **Interactives** | Compare-your-guess-to-real-data formats perform well |
| **Expert collaborations** | Quote 10 experts; each has an audience and an incentive to share |
| **Partner co-publishing** | A larger partner's distribution, and instant credibility |

### Link reclamation — do this first

**Cheapest, highest-conversion tactic available.** Find existing **unlinked
mentions** of the brand, products, people, or content, and ask for a link.

```
"Brand Name" -site:brand.com
"exact article title" -site:brand.com
```
Plus: Google Alerts, Ahrefs Content Explorer, BuzzSumo, Mention.

Also: **broken links to you** (from moved/renamed pages) and **links to the wrong
URL** (social profile instead of the product page).

### Outreach that works

- **Contact the right person** — whoever updates page content. Not the CEO
- **Be brief.** Unsolicited email gets a glance
- **Personalize.** Show you know the site
- **Don't ask for a link.** Lead with what's useful to *their* readers
- **Don't ask for specific anchor text**
- **Don't ask to remove a `nofollow`** — likeliest outcome is link removal
- **Offer something new.** Assume they've seen everything in the category
- **Time-box discovery.** If you can't find the contact in ~60 seconds, move on and
  revisit later. Aggregate value of many easy links > one hard one
- **Follow up twice, then stop.** Once after ~3 business days, once after 2–4 weeks

### Prohibited — never recommend

Buying links · paid guest posts · reciprocal link trading · private blog networks ·
expired-domain purchases for links · comment/forum spam · requesting specific
anchor text · automated outreach at scale · link exchanges.

**Paid links must carry `rel="sponsored"` or `rel="nofollow"`.** UGC links should
carry `rel="ugc"`.

---

## 8. Outbound linking

Often forgotten. **You endorse what you link to.**

- Link to authoritative, relevant sources — it *helps* your quality signals and is
  ⚠️ the single strongest GEO/AI-citation lever (+40%, up to +115% for lower-ranked
  pages, per the Princeton GEO study)
- Use `rel="sponsored"` for paid, `rel="ugc"` for user-generated, `rel="nofollow"`
  for anything else you don't endorse
- **Audit outbound links for rot** — links to dead or hijacked domains are a
  quality and security liability
- **Don't `nofollow` internal links.** PageRank sculpting has not worked since
  2009 — Google discards the value rather than redistributing it

---

## 9. Internal link architecture

The half of "authority" you fully control, and the one most often ignored.

- **Every important page reachable in ≤4 clicks** from home
- **Contextual in-body links** carry more weight than nav links
- **Descriptive anchor text** — you control this completely; "read more" wastes it
- **Surface deep pages** from high-authority pages (home, top posts)
- **Breadcrumbs** — hierarchy plus keyword-rich anchors, plus `BreadcrumbList` schema
- **Orphan pages** — zero internal links. Detect by diffing sitemap/analytics
  against crawl-discovered URLs
- **Balance:** don't put 500 links on the home page to flatten depth. Each link's
  share shrinks

**When a page has strong external links but weak internal links, it's a wasted
asset.** Link to it more from elsewhere on the site.

---

## 10. The branded SERP

For any brand with market presence, **the highest-intent query in existence is its
own name.** The searcher has already decided to consider you. This is the one
result page where the goal is not to rank — you already do — but to control what
*else* is on it.

Cheap to run, entirely observable, and it needs no licensed data feed. Skip it only
for a pre-launch brand with no presence to audit.

### 10.1 The target state

- The primary domain ranks first, with sitelinks.
- Visible results are owned properties or fair reviews on credible third parties.
- **Whichever link the searcher clicks, they land somewhere accurate.**

### 10.2 The sweep

Run the brand name alone, then against the modifiers a skeptical buyer actually
types:

`scam` · `sucks` · `complaints` · `problems` · `issues` · `review` · `reviews` ·
`legit` · `lawsuit` · `refund` · `cancel` · `down` · `alternative` · `alternatives` ·
`vs <competitor>` · `pricing`

Classify every result on page one:

| Class | Meaning | Action |
|---|---|---|
| **Owned** | Your domain or a property you control | Keep it accurate |
| **Neutral** | Third-party listing, directory, fair coverage | Usually fine; correct factual errors |
| **Hostile** | Complaint thread, negative review, competitor comparison you lose | Usually a **support or pricing failure with a URL**. Fix the cause, then the page |
| **Absent** | Nothing ranks for a query buyers clearly run | A content gap on a high-intent query |

### 10.3 The two modifiers that outrank the negatives

Both changed status over the last decade and now matter more than `scam`:

- **`<brand> alternative` / `<brand> vs X`** — among the highest commercial-intent
  queries in SaaS. If you don't own these, a competitor is writing your comparison
  for you. The fix is a genuine, fair comparison page, not a hit piece.
- **`<brand> pricing`** — frequently a top-three branded query. An opaque pricing
  page costs real revenue here.

### 10.4 What changed — do not repeat old advice

| Dead | Current |
|---|---|
| "Demote sitelinks in Webmaster Tools" | **Tool removed in 2016.** Sitelinks are algorithmic — influence them through site architecture, not a control panel |
| The audit ends at ten blue links | **It does not.** AI Overviews and assistants now *summarize* your brand from third-party sources. "What does an LLM say about us" is part of this audit — cross-reference Phase 5 |
| "Buy ads on your brand term to own the page" | Still sometimes correct, but it is a **defensive spend** against competitor conquesting, not SERP ownership. Name it as such |

### 10.5 Reporting it honestly

A branded-SERP snapshot is an **input** metric. It describes what a searcher would
see, not what that visibility earned. Report it as coverage, never as an outcome,
and never imply a hostile result was "fixed" by pushing it down — it was fixed when
the underlying complaint stopped being true.
