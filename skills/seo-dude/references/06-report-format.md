# 06 — Report Format

The deliverable template. Load for Phase 7.

**Write to** `docs/reports/seo/seo-audit-YYYYMMDD-HHMMSS.md` — but **check for an
existing report convention first** (`docs/reports/`, `reports/`, `.reports/`) and
match it. If none exists, create `docs/reports/seo/`.

---

## Rules for the report itself

1. **Lead with the verdict.** Never open with methodology. The reader wants the
   score and the one thing that matters.
2. **Every finding carries evidence** — `file:line`, a URL, or command output.
   No evidence, no finding.
3. **Rank by impact, not by checklist order.** A missing meta description does not
   go above a sitewide `noindex` because "metadata" comes first alphabetically.
4. **Name effort honestly.** "Fix the title tags" (2 hours) and "build content
   depth" (2 quarters) are not comparable line items and must not look comparable.
5. **No fabricated numbers.** No invented volumes, difficulty scores, or "+30%
   traffic" projections. If you don't have the data, say the data is unavailable.
6. **Include what you checked and found clean.** A report that only lists problems
   reads as a problem inventory; one that shows coverage reads as an audit.

---

## Template

````markdown
# SEO Audit — <site or repo> — YYYY-MM-DD

**Scope:** <codebase | live URL | both> · **Mode:** <full | diff | scope:X>
**Auditor:** seo-dude v<version>

---

## Verdict

**Score: NN/100** · Gate: **PASS** / **FAIL**

<One paragraph. What is the state of this site's SEO, what is the single
biggest lever, and what should happen first. Be decisive. If the gate failed,
say so here and say that the rest of the score is capped and provisional.>

**The one thing:** <If they do only one thing, this. One sentence.>

---

## Score breakdown

| Category | Weight | Score | Lost points for |
|---|---:|---:|---|
| Content depth & differentiation | 30 | 12 | No indexable long-form surface; 3 competitors average ~40× the content pages |
| Intent coverage & keyword mapping | 15 | 9 | No informational-intent pages; `/pricing` and `/plans` cannibalize |
| Technical foundation | 20 | 18 | Stale `lastmod`; one redirect chain |
| Authority & links | 20 | 8 | 14 referring domains; low source diversity |
| Vertical / local / international | 10 | — | **N/A — redistributed** |
| Page experience | 5 | 4 | INP 240ms on mobile |
| **Total** | **100** | **NN** | |

<If a category was N/A, state it and show the redistribution explicitly.>

---

## Status vs. prior audit

<Only if a prior report exists in the same directory. Read it first.>

| ID | Finding | Prior | Now |
|---|---|---|---|
| SEO-003 | Missing canonical on `/pricing` | HIGH | **FIXED** |
| SEO-007 | Thin content on `/guides/*` | MEDIUM | **STILL PRESENT** |
| SEO-011 | Redirect chain on legacy URLs | — | **NEW** |
| SEO-004 | Missing OG image on `/faq` | LOW | **VERIFIED FALSE POSITIVE** — route inherits from layout |

---

## Findings

### SEO-001 · CRITICAL · Sitewide `noindex` on production

**Evidence**
`app/layout.tsx:34` — `robots: { index: false }`
Confirmed live: `curl -sI https://example.com | grep x-robots-tag` → `noindex`

**Why it matters**
Nothing on this domain can rank. Every other finding in this report is
provisional until this is fixed.

**Fix**
Remove the `index: false` from the root metadata. Verify with URL Inspection,
then request indexing for the top 10 pages.

**Effort:** 15 minutes · **Category:** Technical foundation

---

### SEO-002 · HIGH · <title>

**Evidence** · **Why it matters** · **Fix** · **Effort** · **Category**

<Repeat. Ordered by severity, then by impact within severity.>
````

---

## Required closing sections

### Checked and clean

```markdown
## Checked and clean

- Canonical tags present and self-referential on all 12 public routes
- `robots.txt` valid; does not block CSS or JS
- Structured data validates (Organization, WebSite, FAQPage, BreadcrumbList)
- HTTPS enforced; HSTS present
- No duplicate title tags
- Mobile-friendly on all tested routes
- No manual actions in Search Console
```

**Do not skip this.** It is what separates an audit from a complaint list, and it
prevents the next person re-checking the same things.

### The plan

```markdown
## The plan

**Now — mechanical fixes** (this session, ~3 hours)
1. SEO-001 sitewide noindex
2. SEO-004 stale sitemap lastmod
3. SEO-006 redirect chain
...

**Next — this sprint** (needs a decision or a small project)
1. SEO-002 resolve /pricing vs /plans cannibalization — requires choosing which URL wins
...

**Program — quarters, not sprints**
1. Content depth. Competitors average ~40× the indexable pages. This is the
   highest-weighted category and the one this audit cannot fix.
2. Link authority. 14 referring domains. Needs a linkable-asset program.
```

### What one pass cannot fix

```markdown
## What one pass cannot fix

Be explicit. A user who believes this audit finished the job will stop, and
stopping is the actual failure mode.

**This audit fixed:** every technical blocker, the metadata and structured-data
layer, duplication, the redirect and canonical graph.

**This audit could not fix, and no single pass can:**

| Gap | Weight | Realistic timeline |
|---|---:|---|
| Content depth | 30 | 2–4 quarters of consistent publishing |
| Link authority | 20 | 2+ quarters; requires linkable assets, not outreach volume |
| Domain trust | — | Accrues; cannot be bought or accelerated safely |

Traffic from SEO grows gradually, occasionally in spurts, through accumulated
incremental improvement. Anyone promising otherwise is selling something.
```

### Verification debt

```markdown
## Verification debt

Figures deliberately **not** used in this report because the source is dated
and could not be re-verified in this pass:

- Long-tail volume split (~95% of keywords / ~35% of volume) — direction used, number omitted
- Page-1 click share (~95%) — direction used, number omitted
- FTC per-review penalty — inflation-adjusted annually; not quoted

If any of these need to be stated to a stakeholder, verify against a current
source first.
```

---

## Tone calibration

**Good:**
> Content depth is the problem. You have 12 indexable pages; the three sites
> ranking above you average around 400. Every technical finding below is real and
> worth fixing, and none of them will change your rankings as much as publishing
> would.

**Bad:**
> There are several opportunities to optimize your SEO performance. We've
> identified 23 findings across multiple categories that could improve your
> organic visibility.

The first tells someone what to do. The second bills hours.

**Also good — refusing work:**
> You asked about a disavow project. Don't do it. You have no manual action and
> no history of link buying, and Penguin has discounted rather than penalized bad
> links since 2016. Those 40 junk links are already being ignored. Spend the
> quarter on content instead.

---

## Finding-ID conventions

- `SEO-NNN`, zero-padded to 3, sequential within a report
- **IDs are stable across reports.** If SEO-007 recurs, it stays SEO-007
- New findings continue from the highest ID ever used, not from the count in this
  report
- Keep a `verified-false-positive` list so dismissed findings aren't re-reported
  each run — record the reason, not just the dismissal
