# 02 — Content & Keywords

Intent coverage, keyword mapping, content depth, EEAT, on-page optimization.
**This carries the two highest-weighted rubric categories (28 + 12 = 40 of 100).**
Load for Phase 3 or `--scope content`.

⚠️ = 2023-sourced figure. **Re-verify before quoting.**

---

## 1. Intent taxonomy — audit for coverage

| Type | User wants | Typical page | Converts |
|---|---|---|---|
| **Navigational** | A specific site they already have in mind | Home, brand pages | Very high (own brand) |
| **Informational** | To learn or research | Guides, articles, docs | Rarely now |
| **Transactional** | To buy/sign up/book/download | Product, pricing, signup | Highest |
| **Local** | Something near them | Location pages, GBP | High, often offline |

**Local is a cross-cutting axis, not a fourth bucket.** A query can be local *and*
informational. Modelling it as a bucket produces wrong logic.

### The audit

1. **Map every page to an intent.** Pages that map to none are candidates for
   removal or merging.
2. **Find the gaps.** Most B2B/SaaS sites are transactional-heavy and
   informational-poor — they only have pages for people already deciding.
3. **Own your branded SERP.** ⚠️ ~70% of clicks on branded queries go to the first
   result. Check: does the brand's own site rank #1 for its own name, and does it
   own `[brand] + pricing / reviews / alternatives / support / vs competitor`?
   If a comparison site owns `[brand] alternatives`, that's a HIGH finding.
4. **Check negative-modifier terms** — `[brand] sucks / scam / complaints`. If
   people search it, you want to be the result.

**The case for informational content:** ⚠️ Conductor reported users finding useful
informational content are ~131% more likely to buy later. **This is
vendor-published and self-sampled — directionally sound, numerically unusable.**
Don't quote the number; make the argument.

---

## 2. Topic map and supersets

Build bottom-up:

1. Name entities and concepts — products, services, category
2. Go up a level to the parent domain(s)
3. Ask **why people buy** — problems, fears, alternatives, adjacent concerns
4. Find the **supersets**: dimensions with high cardinality where exactly one
   value applies to every keyword. These become spreadsheet *columns*, not rows

**The taxonomy warning — the most transferable idea here:**

> Your internal product taxonomy is not your keyword taxonomy, because the latter
> is governed by search intent.

One SKU internally may need one page per compatible model, because that's how
people search. Three SKUs internally may be one page, because nobody distinguishes
them in a query.

**Audit for divergence:** does the site's navigation reflect how the company
organizes things, or how buyers search? A "you call it X, buyers search for Y"
finding is high-value and cheap to produce.

---

## 3. Keyword cannibalization

Two or more pages targeting the same term forces the engine to pick — splitting
internal anchor text, external links, and relevance across both.

**Detection:**
```
Grep for duplicate/near-duplicate <title> values
```
Then, per suspected term:
```
site:example.com "target phrase"
```
More than one page competing? Cannibalization.

**Also check** Search Console: one query where the "top page" **flips between
URLs** across weeks is the clearest signal.

**Fixes:**
1. **Consolidate** — merge into the stronger page, 301 the weaker
2. **Differentiate** — retarget one page to a genuinely different intent
3. **Internally link** the narrower page → broader page using the broad term as
   anchor (e.g. a `low-interest mortgages` page linking "mortgages" to the
   `mortgages` page). This resolves the ambiguity explicitly

---

## 4. Content depth — the highest-weighted category

**The argument:** sites that win a category win on **breadth and depth around one
topic**, not on technical polish.

⚠️ The book's worked comparisons: **WebMD vs. Mayo Clinic** — a 1996 site matching
a ~1889 institution on organic traffic, on the strength of ~397 pages about
*diabetes alone*. **NerdWallet vs. Fidelity** — a 2009 startup out-trafficking a
1946 incumbent with ~24,000 informational pages vs. ~1,460.

⚠️ Long tail: ~95% of all keywords, ~35% of all search volume. Individually tiny,
collectively decisive, and higher-converting because more specific.

### The audit

1. **Count indexable content pages** on the site vs. the top 3 organic competitors
   (`site:` queries give a rough order of magnitude — say "order of magnitude,"
   not a precise count, since `site:` is unreliable).
2. **Build a user-needs pyramid** for the core topic. What questions exist around
   it? How many does the site answer?
3. **Identify the depth gap** — name the specific subtopics with no page.
4. **Check for a blog/resources surface at all.** Zero indexable long-form content
   is a HIGH finding in any competitive category.

### The thin-slicing counter-check

**Before recommending "make more pages," verify each would answer a question the
others don't.** 50 pages differing only by a swapped noun is thin slicing — it
gets filtered, and at volume it can trigger a sitewide Helpful Content demotion.

**Better axis for programmatic content:** cross two real dimensions (topic ×
job-to-be-done, product × use-case) so each page has genuinely distinct substance.

---

## 5. Helpful Content — the sitewide risk

Two properties that invert normal remediation logic:

1. **It is sitewide.** A section of engine-first content demotes the *entire*
   domain, including good pages.
2. **Recovery takes many months** after removal.

### Diagnostic questions

- Is the content primarily for people, or to rank?
- Does the site have a clear focus, or does it produce content on whatever's
  trending?
- Is it written by someone with genuine expertise?
- Does it add value beyond what already exists on the web?
- Was it created just because a topic was trending?
- Does it leave the reader feeling they need to search again?

**Remediation:** `noindex` is a **patch**. Google's John Mueller has said the real
fix is **removing the content**. Pages built to rank rather than help aren't
helping reputation with users either.

**AI-generated content:** acceptable when a subject-matter expert owns and reviews
it. Problematic as an entire strategy. Google's stated objection is specifically
that such content "can really only put together summaries of what others have
published" — i.e. it fails the **Experience** limb of EEAT structurally.

---

## 6. EEAT

**Experience, Expertise, Authoritativeness, Trustworthiness.** (E-A-T from 2018;
the leading **E** for Experience added December 2022.)

**EEAT is not a ranking factor.** It is a rubric for human **Search Quality
Raters**, whose scores never touch live rankings — they feed engineers as test
cases. Google's Danny Sullivan has said so directly. What's true: Google builds
**proxy signals** it *can* measure to approximate it.

**YMYL** ("Your Money or Your Life") — content materially affecting health,
finances, safety, or wellbeing. **Held to a higher standard.** Quality algorithms
hit hardest here. If the site is YMYL, weight every EEAT finding up one severity.

### Audit checklist

| Signal | Check |
|---|---|
| **Named authors** | Bylines on advisory content? Real names? |
| **Author bios** | Dedicated bio pages with verifiable credentials? |
| **Author citations elsewhere** | Published on other credible sites? |
| **Sources cited** | Third-party claims linked to originals? |
| **Ad/affiliate disclosure** | Fully disclosed, even without editorial influence? |
| **UGC moderation** | Unmoderated comments/forums = standing liability |
| **Outbound link quality** | You inherit some of what you point at |
| **Content freshness** | Accurate at publish is insufficient; is it maintained? |
| **Contact/About** | Real address, real contact path |
| **First-hand experience** | Does content claiming testing/visiting/using actually reflect it? |

**The Experience gap is the one worth flagging hardest** in AI-assisted content:
claims like "we tested," "in our experience," "I visited" that no one actually did
are both an EEAT failure and a potential FTC issue.

---

## 7. Title tags

The most important on-page element. ⚠️ Google uses the supplied `<title>` about
87% of the time; ⚠️ ~7.4% of top-ranking pages have none at all.

| Rule | Detail |
|---|---|
| **Write for humans first** | It's the headline in the results |
| **Keywords early, brand last** | Users need to know what they'll get |
| **~60–65 characters** | Beyond that, truncation. Actual limit is pixel width |
| **Unique per page** | Duplicates are a cannibalization signal |
| **Match searcher intent** | Browsing → descriptive. Buying → make the action clear |
| **Don't cannibalize** | Don't put page B's target term in page A's title |
| **Dividers** | `|`, `-`, `:` — readability only, no SEO value |

**If Google rewrites your title,** it's usually because the supplied one doesn't
match the query, doesn't describe the page, or is missing. Diagnose before
"fixing" — the rewrite may be better for secondary intents while yours is right
for the primary one.

---

## 8. Meta descriptions

**Not a ranking factor. A CTR lever.** Write it as ad copy.

- **~155–160 characters.** Actual cap is pixel width
- Include the target keyword — matched query terms get **bolded** in the SERP,
  which drives the CTR gain
- Soft sell, not hard sell. Organic clickers are often researching, not buying —
  successful PPC copy often does *not* transfer
- **Omitting it is legitimate at scale.** For a large catalog or long-tail archive,
  Google's auto-generated description contains the user's actual query terms.
  Machine-generated descriptions are often *worse* than none

---

## 9. Headings, body, and on-page structure

- **Heading hierarchy is what matters, not the specific tag.** The highest-level
  heading on the page carries the weight — an `<h3>` used as the top heading with
  only lower levels beneath behaves like an `<h1>`. Styling ≠ signal
- **One top-level heading** functioning as the page label; sub-headings label
  sections
- **Semantic richness over repetition.** Repeating an exact phrase reads as
  unnatural. Use synonyms and related concepts — the engine understands them
- **Page segmentation is real.** Google reads CSS and understands layout. Keywords
  in sidebars and footers carry less weight than main content. Use semantic HTML
  (`<main>`, `<article>`) to mark the primary content
- **Co-occurrence:** a comprehensive page on a topic naturally contains related
  subtopics. Their *absence* is a quality signal. A diabetes page with no mention
  of symptoms, causes, or treatment reads as thin regardless of word count
- **Bold/italic carry slight emphasis** — confirmed by Google's John Mueller. Only
  works when used sparingly; bolding everything means bolding nothing
- **No universal ideal word count.** Depends entirely on the topic and query. Never
  give a writer a word-count target as an SEO instruction

---

## 10. Images (on-page; see `04-` for image search)

- **Descriptive filenames** — `abe-lincoln.jpg`, not `IMG_4137a-bl2.jpg`
- **`alt` attributes — always quoted.** Unquoted multi-word alt text silently
  loses everything after the first word. This is a real, common, invisible bug
- **`alt=""` for decorative images.** Both Google and W3C say so; marking up
  spacers is noise and an accessibility regression
- **Nearby text and captions** are the strongest association signals
- **CSS background images are never indexed.** Anything meant to be found must be
  a real `<img>`/`<picture>`
- **Copyright:** buying stock buys a *licence*, not copyright. Google tracks
  copyright removal demands per domain

---

## 11. Internal linking

- **Contextual in-body links** outweigh navigation links
- **Descriptive anchor text.** "Click here" wastes the strongest internal signal
  you control
- **Cross-link related content** — this is also the cannibalization fix (§3)
- **Link depth ≤4 clicks** from home for anything important
- **Surface deep pages** by linking them from higher-authority pages

---

## 12. Striking-distance opportunities

**The fastest visible win available, which makes it the right first move for
internal credibility.**

Pages ranking **top 20 but not #1**. Often a title-tag and content edit, not a
project.

**Rank thresholds — why this band and not others:**

| Band | Meaning |
|---|---|
| Unindexed | Nothing to measure. Fix indexation first |
| Top 100 | Measurable (most tools report top 100). **Analytics threshold, not traffic** |
| Top 20 | ⚠️ ~5% of clicks land past page 1. "Striking distance" starts here |
| **Top 10** | ⚠️ ~95% of clicks. **The only commercially meaningful band** |
| #1 | Disproportionate share |

At rank 90 on a hard term, moving to 60 is worth nothing. Spend elsewhere until
near 20.

**Workflow:** pull Search Console queries with position 4–20 and impressions but
low CTR → check title/meta relevance to the query → check content actually answers
it → add depth or internal links.

**Check the SERP shape first.** A rich result or map pack can push you off page 1
while you're technically in the top 10.

---

## 13. SERP features and the deoptimization paradox

Organic results compete with OneBox answers, knowledge panels, featured snippets,
map packs, rich/enriched results, carousels, video key moments, and sitelinks
search boxes.

If Google lifts content into a featured snippet, users may get the answer without
clicking. Some practitioners deliberately *deoptimize* to drop out and recover the
click.

**Never make this call on traffic alone.** If conversions haven't decreased, the
traffic lost was worthless. **Check conversions, not sessions.** Any traffic-drop
alarm without a conversion check is a vanity alert.

---

## 14. Content freshness

- **Update, don't republish.** Refreshing an established URL retains its accrued
  authority; a new URL starts from zero
- **Prioritize by traffic decay** — pages that ranked and are sliding
- **Watch for term inflection.** The book's example: `hdmi to displayport adapter`
  vs. `displayport to hdmi adapter` — same product, but volume **flips** as the
  installed base turns over. Miss it and you optimize for a dying query for a year
- **Seasonality is not just holidays.** Start next cycle's work right after the
  current one ends, when competition has collapsed
