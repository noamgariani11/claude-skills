# AIPATH.md — the ground-truth doc

_Section references (§Evaluation, §Guardrails, ...) map to files in `references/`. The map is in SKILL.md._

Single canonical file at repo root. Not a journal, not a changelog. The *current accurate* description of what the AI does today, why, and what is being changed. Replaces tribal knowledge. Anyone can read it and know exactly what the Kablan AI is right now and what the next move is.

## Required sections

```markdown
# AIPATH.md
_Last updated: YYYY-MM-DD by aiml-dude_

## 1. Mission
One paragraph. What is the AI for, who it talks to, what decision it helps
them make. Make the stakes feel real.

## 2. Current Architecture
Every Claude call in the system. For each:
- Name (e.g. "chat stream", "title gen", "appliance detect")
- Model ID, copied verbatim from the code, never from memory, with the
  file:line it was read from. Model IDs churn faster than this doc does.
- Entry point (file:line)
- System prompt location (file:line)
- Max tokens / thinking budget / sampling params
- Inputs (user message, images, injected context)
- Output contract (free text, JSON, marker-embedded, streaming shape)
- Downstream consumers
- Rate limit / credit cost
- Known failure modes

## 3. System Prompt Anatomy
Main prompt, section by section. For each: what it does, why it exists,
what breaks if removed, approximate token count. Flag dead weight.

## 4. Output Contract
What the UI parses. Marker schemas, lingo syntax, markdown conventions.
What breaks if the model drifts.

## 5. Current Strengths
Honest list. Specific prompts that work well and why.

## 6. Current Weaknesses (by failure class)
Group by class, not prompt. Required classes:
- Hallucination (fabricated parts, prices, codes)
- Safety / emergency triage miss
- Ambiguity handling (asks when it should, doesn't when it shouldn't)
- Cost accuracy (market, permits, call-out fees)
- Density scaling (under/over for the difficulty)
- Format / contract compliance (markers, schema)
- Tone & voice drift
- Multimodal ambiguity (photos misread)
- Refusal breaks (jailbreaks, scope creep)
- Context injection misuse (profile ignored or over-applied)

For each class: example prompt, why it happens, rough cost to product.
Tag each class with its primary HELM dimension (see §Evaluation) so the
mitigation has a measurable target.

## 7. Eval Corpus
Prompts used to evaluate the AI, tagged by failure class and by
CheckList test type (MFT / INV / DIR). Each prompt includes: rubric
score (see §Evaluation), HELM dim scores where applicable, last score,
target score, whether it's a regression gate. Grow this every time you
find a new failure.

## 8. Production Signal Snapshot
Last sync from DB: thumbs ratio, session_feedback breakdown, giveup_event
rate, with a sentence on what's trending and what to chase.

## 9. Change Log
Reverse chronological. Each entry:
- Date
- Change (diff summary + file:line)
- Hypothesis
- Eval prompts run + score delta + bootstrap 95% CI
- Outcome (shipped / rolled back / parked + one sentence why)
- Next step

## 10. Open Questions
Things you don't know. Not TODOs — questions.
```

Keep it honest. If something is broken or unknown, AIPATH.md says so. A doc that only lists wins is a lying doc.

---

## Worked example — what a real proposal looks like

Use this as the reference shape. This is the bar.

```
CHANGE: Replace verbose Tone & Voice block with a tighter persona anchor
LOCATION: src/app/api/chat/prompt.ts:6-14
TYPE: revise
POLICY TIER: Guideline (voice, not a shipping gate)

BEFORE:
## Tone & Voice
- Talk like a knowledgeable friend at the hardware store, not a manual or a chatbot.
- Plain English first. When you use a trade term that a typical homeowner
  might not know, wrap it in lingo syntax: {term|Short definition here.}
  [...]
- Be direct and confident. If you see the problem, say it. Don't hedge
  with "it might possibly be" when you're 90% sure.
- Teach as you go. Drop brief explanations of WHY each step matters.
- Keep it tight. People are standing next to a broken thing.
- Get excited when a fix is simple and saves real money.
- Be honest when something is beyond DIY.
- NEVER use em dashes anywhere in any response.

AFTER:
## Tone & Voice
You are a journeyman tradesperson texting a friend. Direct, confident,
warm, practical. Teach the WHY in one sentence when it matters. When a
trade term appears for the first time, wrap it: {term|one-sentence def
starting capital, ending period}. Skip this for words homeowners already
know (wrench, valve, breaker). No em dashes anywhere.

WHY:
Section was ~180 tokens doing what a role-first paragraph does in ~65.
Claude responds strongly to compact identity statements; a bulleted list
of tone rules creates compliance drift (the model picks one bullet per
response rather than internalizing voice). Anthropic prompting guidance
favors role-first framing over rule enumeration for voice.

EXPECTED IMPACT:
- Quality: voice more consistent across difficulty levels; fewer "as an AI"
  hedges on ambiguous prompts. Lingo syntax retained.
- Latency: small win (~115 fewer input tokens per request, ~30ms off TTFT
  on warm cache).
- Cost: ~115 tokens × 10k messages/mo = ~1.15M tokens/mo saved.
- Trust: reads more like a pro, less like a chatbot reading a HR policy.

BUDGET:
Within gates on TTFT, input tokens, and prefix size — all three move the
right way. Breaches the cache-prefix gate by definition: this text sits
above the cache boundary, so the prefix rewrites and hit rate drops to
zero until it rewarms (~1h at current traffic, roughly one full-prefix
write per cold request in that window). Accepted because the change is a
permanent 115-token reduction on every subsequent request; payback is
well under a day. Prefix measured at 1,840 tokens after the change via
`python3 scripts/prompt_tokens.py src/app/api/chat/prompt.ts
--extract-template --boundary "## User profile"`.

RISKS:
Could lose the "get excited when a fix is simple" behavior that drives
the "$12 fix that a plumber would charge $200 for" moments. Mitigated by
keeping "warm" in the persona and by regression-gating on eval prompt
EV-07 ("small-money-win phrasing present").

HOW TO MEASURE:
- EV-01 (tone consistency across difficulty 1 vs 5) — expect no drop
- EV-03 (lingo syntax compliance) — expect no drop, gate at ≥95%
- EV-07 (small-money-win phrasing) — gate at ≥70% on eligible prompts
- EV-12 (no "as an AI" hedges) — expect improvement
Run all four before/after on the same 40 prompts, then:
  python3 scripts/evalstats.py bootstrap --scores after.json \
      --baseline before.json --paired --field <dim>
Ship only if no gated metric returns REGRESSION. Note N=40 is powered to
detect roughly a 0.45-point mean shift, not a 0.1-point one — confirm
with `evalstats.py power` before reading a null result as "no harm".

HARNESS: sub-Agent proxy (see §Human evaluation → Harness fidelity).
Guideline-tier voice change, so no API-side confirmation pass required.
```

Every proposal you write looks like this. If it doesn't, it isn't done.
