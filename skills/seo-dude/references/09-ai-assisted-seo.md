# 09 — AI-Assisted SEO: production risks to flag, and safe use in the fix loop

Two jobs. **First**, this is a detection reference: when a site's content shows
signs of unreviewed AI generation, this tells you what to flag and how severe it
is. **Second**, it governs how *you* may use AI inside your own audit and fix loop.

It does **not** cover getting cited by AI answer engines (AI Overviews, ChatGPT,
Perplexity) — that is `references/07-currency-2026.md` §7–8, scored under "AI
visibility & citation." This file is about *content produced with AI*, not content
*consumed by* AI. Keep the two straight in the report.

**Source:** Enge, *Using Generative AI for SEO* (O'Reilly, 2025), reconciled with
`07-currency-2026.md` and `08-obsolescence-and-claims.md`. Where a number here and
in `07` disagree, `07` wins.

---

## 1. The governing rule (repeat of iron rule 10, sharpened)

AI is a first-drafter and a legman; a subject-matter expert owns the result. This
is not compliance decoration — it is *why* the leverage exists. An LLM recombines
what is already on the web, so unattended it cannot produce the one thing that
ranks: **new information or a unique perspective.** Strip the human and you get a
fast regurgitation engine, which is exactly what gets demoted at scale (§2).

Consequence for this skill: **content findings stay advisory, never auto-fixed**
(iron rule 10). You may flag AI-slop signals, thin regurgitation, and errors by
omission. You may **not** rewrite the content unattended.

---

## 2. The master risk to flag: low-quality AI content at scale

The single most expensive finding you can surface, because recovery runs **months
to never.** Google's posture is *quality regardless of production method*; Helpful
Content signals (folded into core, March 2024 — see `07` §1) demote unhelpful
content whether or not AI made it. The low-quality *fraction rises with volume*, so
bulk AI publishing is the high-risk pattern.

**Signals a site is publishing unreviewed AI content at scale:**

- A publishing-cadence step-change (a few posts/week → dozens/hundreds) visible in
  sitemap `lastmod` clustering or dated URLs. The ramp itself is a low-quality
  signal, independent of the content.
- Large sets of near-template pages with low sentence-length variation
  ("burstiness"), superlative pile-ups, and the over-used-adjective tell
  (*commendable, meticulous, intricate, seamless*).
- Thin regurgitation: pages that restate consensus with no new data, quote, or
  first-hand angle — nothing an AI engine or Google would prefer over the source.

**Severity:** sitewide unreviewed AI content in a competitive or YMYL category is
**CRITICAL/HIGH** (it maps to the Helpful-Content demotion row in the gate/severity
table). A handful of thin AI pages on secondary URLs is **MEDIUM**.

**How to report it.** Describe the pattern and the risk; recommend *review and
consolidation*, not deletion-by-default. Do not claim you can prove AI authorship
(see §4). Frame as: "these pages show the pattern of unreviewed AI generation and
carry demotion risk; they need SME review or consolidation."

### 2.1 Errors by omission — the sneaky content finding

The text is *technically accurate* but omits the decisive fact: the site's actual
differentiator, or that a competitor's claimed advantage is in fact matched.
Accurate-but-incomplete reads as authoritative and survives a casual review, so it
is worse than an obvious error. You can only *flag the risk category* — verifying a
specific omission needs the SME. Note it under content depth, advisory.

---

## 3. Reference-type currency — do not let AI codegen promise a dead rich result

The book still treats `FAQPage` and `HowTo` schema as earning rich results. **They
do not** — HowTo desktop retired Sept 2023; FAQ rich results retired **2026-05-07**
(`07` §5). When you draft or review schema in the fix loop:

- You may still emit `FAQPage`/`HowTo` for machine understanding, but **never write
  a finding or code comment promising a rich result from a retired type.** That is a
  rule-5 obsolescence violation.
- Mark up **only data already visible on the page** (iron rule / Phase 9). AI will
  happily generate schema for data that isn't shown — that is spam.

Same caution applies to any AI-drafted `hreflang`, `.htaccess`, or redirect code:
AI output is a *draft to review*, and redirect/`.htaccess` rules are
order-sensitive. Validate before it ships.

---

## 4. AI-detection tools are directional, never a verdict

If asked "is this content AI-written," or tempted to run a detector:

- Detectors (GPTZero, Originality.ai, Copyleaks, ZeroGPT, …) key on the same tells
  in §2 and are **unreliable** — they flag the US Constitution as AI-written. Use
  them to *flag for human review*, never as a publish/kill gate, and expect false
  positives on genuine human writing.
- **Never assert a page was AI-generated as fact.** Report the *pattern* and its
  *risk*, tiered as BELIEVE at most (`07` evidence tiers). "This shows the
  signature of unreviewed AI content" is defensible; "this is AI-written" is not.
- "Make it undetectable" is an evasion goal — refuse it the way you refuse any
  black-hat request (iron rule 4). The honest fix is to make the content genuinely
  good, which is a content program, not a patch.

This dovetails with `08` §2: some things are unresolvable, and authorship of a given
page is usually one of them. Say what the pattern suggests and stop.

---

## 5. Using AI safely inside *your own* fix loop

You may use AI to draft mechanical fixes. The constraints:

- **Anything AI drafts, you verify against the page and the project's gates before
  it ships** — same standard as any Phase 9 fix. AI schema/redirect/hreflang drafts
  are *drafts*.
- **Constrain the input to cut hallucination.** Feed the model the exact page data;
  never let it invent titles, stats, or markup for data not present. Database- or
  page-constrained generation is low-risk; open-ended generation is not.
- **Cross-check numbers.** If AI surfaces a statistic for a finding, it must carry a
  real, checkable source — LLMs fabricate stats to fill gaps. Unsourced number →
  drop it (iron rule 2).
- **Currency-check anything the model asserts about search.** Models are trained on
  a corpus that peaked in the 2008–2014 SEO-content era, so they will confidently
  repeat dead rules (character caps, "301s leak juice", FAQ rich results). Route
  every such claim through `07` and `08` before it enters the report.
- **Cap and log.** Same self-regulation as Phase 9 — ≤20 mechanical fixes/run; if AI
  wants to touch >5 files it is a migration, escalate to a plan.

---

## 6. What to write in the report

- If unreviewed-AI-at-scale is present: a dedicated finding at CRITICAL/HIGH with
  the pattern evidence (cadence, template similarity, tells), the demotion risk, and
  a *review/consolidate* recommendation — not mass deletion.
- If AI content is present but reviewed and deep: **no finding.** Google rewards
  quality regardless of production method; do not flag AI use per se. The target is
  slop, not tooling.
- Keep every AI-authorship claim at BELIEVE and framed as pattern+risk.
- Realistic gains, if the user asks what AI can do for their SEO throughput: the
  book's targets are ~-20–30% cost, +20–30% throughput, +~20% quality — *with* SME
  review. Present as targets, never guarantees, and never as a reason to drop review.
