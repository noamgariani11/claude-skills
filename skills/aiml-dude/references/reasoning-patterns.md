# Reasoning & prompting patterns (research-grounded)

_Section references (§Evaluation, §Guardrails, ...) map to files in `references/`. The map is in SKILL.md._

Every pattern below is a lever named in current applied-AI curricula (CMU 11-711, Stanford CS336, Berkeley CS294 LLM Agents). Learn when each fits, not just what it is. A pattern that lifts a hard reasoning task by 10 points is wasted on an easy one and costs tokens in the meantime.

## Chain-of-Thought (Wei et al., NeurIPS 2022)

Include intermediate reasoning steps before the final answer. On Claude, **extended thinking (Anthropic's native reasoning budget) subsumes most manual CoT** — don't hand-craft "let's think step by step" when `thinking_budget` is enabled. Manual CoT still matters when:

- You need the reasoning itself in the output (Kablan: the WHY explanations to the homeowner are a form of visible CoT).
- The model is Haiku (thinking mostly unavailable on Haiku versions in current pricing).
- You want to steer the reasoning shape via few-shot exemplars (show the reasoning pattern you want, model mimics).

**Kablan application**: main chat (Opus + extended thinking) already does the reasoning. Title gen and appliance detect (Haiku, classification) don't need CoT. Candidates for manual CoT:
- The difficulty classification that precedes `KABLAN_PRO_MATCH` — force the model to list liability factors before emitting a difficulty number.
- The cost-estimation reasoning that precedes `KABLAN_ESTIMATE` — force the assumption stack (parts cost, labor hours, regional multiplier, permit) before the number. Reduces fabricated estimates.

Implementation:

```ts
// buildParts.ts — few-shot CoT exemplar for the estimator sub-call
const costCoTExample = `
Example:
User: toilet fill valve swap
Reasoning:
- Part cost: ~$15-25 (Fluidmaster 400A territory)
- Labor: 30-45 min for a competent DIYer, 0 for a pro (call-out ~$150)
- Regional: negligible
- Permit: none
- Estimate: $20 DIY, $200-250 hired
`;
```

## Self-Consistency (Wang et al., ICLR 2023)

Sample K reasoning paths at temperature 0.7, take the **majority vote** on the final answer. Works because reasoning-path diversity correlates with correctness on problems with a clean single answer.

Cost: K× tokens per call. K=5 is a common compromise. Don't run it on everything.

**Kablan application**: high-value for the **difficulty classifier** — the line between 4 (DIY-with-care) and 5 (call-a-pro) is exactly where a confident wrong number becomes a liability. Run the classifier at T=0.7 five times, majority vote. A 4→5 flip saved from a single overconfident sample is a prevented injury.

Implementation sketch:

```ts
async function classifyDifficulty(prompt: string): Promise<number> {
  const runs = await Promise.all(
    Array.from({ length: 5 }, () =>
      anthropic.messages.create({
        model: "claude-haiku-4-5",
        temperature: 0.7,
        messages: [{ role: "user", content: prompt }],
        system: difficultyClassifierPrompt,
      })
    )
  );
  const votes = runs.map(r => parseInt(extractDifficulty(r)));
  return mode(votes); // majority vote
}
```

Not worth it on free-text chat responses — the answer space is too large for majority vote to mean anything.

## Tree of Thoughts (Yao et al., NeurIPS 2023)

Expand multiple reasoning branches, evaluate states, prune, search (BFS/DFS). Strong on problems with clear intermediate-state value (Game of 24, crosswords, some planning). Weak when intermediate states are hard to evaluate.

**Kablan application**: probably overkill. Home-repair diagnosis has shallow branching once you have the symptom and a good photo. The only plausible fit is the multi-step-project cost estimator (permits → materials → labor → contingency), and even there a structured few-shot beats ToT on cost. **Park it until a concrete use case shows up.**

## ReAct: Reason + Act (Yao et al., ICLR 2023)

Interleave `Thought` / `Action` / `Observation`. Model reasons, decides when to call a tool, consumes the tool result, continues. The baseline loop for any LLM-as-agent.

Example:

```
Thought: I need to know the NEC version Chicago adopted.
Action: lookup_local_code(city="Chicago", code="NEC")
Observation: Chicago adopted NEC 2020 with amendments.
Thought: The user has a pre-1978 panel. 210.8(A)(5) GFCI requirement applies...
```

**Kablan application**: not yet — Kablan is single-shot today. This is the pattern to reach for when you add:
- A live-pricing tool
- A parts-catalog tool  
- A local-code lookup
- A scheduling / booking action

Implementation goes through `retrieval-and-agents.md`. When you do add tools, instrument: count tool calls per answer, track tool-call success rate, watch for loop-bugs (model calls the same tool with identical args repeatedly).

## Reflexion (Shinn et al., NeurIPS 2023)

Self-critique + retry. After a response, a critic pass evaluates against the goal, writes a short "what I got wrong and should try differently", then the model re-answers with the reflection in context. Works on tasks with clear success signal.

**Kablan application**: high-value for the **cost-estimator sub-call**. Reflexion loop: produce estimate → critic checks against retrieved BLS labor rates + materials list → if delta >30%, re-generate with the discrepancy surfaced.

```ts
async function estimateWithReflexion(prompt: string): Promise<Estimate> {
  let estimate = await generate(prompt);
  for (let i = 0; i < 2; i++) { // cap iterations
    const critique = await criticize(estimate, groundTruthRanges);
    if (critique.acceptable) return estimate;
    estimate = await generate(prompt + "\n\nPrior attempt: " + estimate + "\nCritique: " + critique.notes);
  }
  return estimate;
}
```

Low-value for main chat (no crisp per-turn success signal).

## Constitutional AI (Bai et al., Anthropic 2022)

Self-critique against a principle list. Model generates → same model critiques against a constitution → revises. Anthropic uses CAI in post-training (RLAIF). At inference, a CAI-style second pass is a safety lever for sensitive outputs.

**Kablan application**: one place. When the model is about to emit **difficulty-5 DIY steps** (gas line, main panel work, anything structural), run a CAI-style critique pass with a Kablan constitution:

```
Constitution for safety-critical revision:
1. If the work involves gas, electrical main, load-bearing structure, asbestos, or lead, the response must redirect to a licensed tradesperson.
2. Specific step-by-step instructions must never appear for work requiring a permit or license.
3. If the response contains such instructions, replace with a triage summary plus "hire-a-pro" redirect.
Rewrite the response if it violates any rule above. If it complies, return unchanged.
```

Gate on the difficulty classifier — only run the CAI pass when classifier ≥ 4. Cost: 1 extra pass on ~5% of prompts. Value: asymmetric — every prevented bad-advice shipment is a trust event you don't have.

## Choosing between patterns

| Situation | Reach for |
|---|---|
| Single-shot free-text answer, Opus | Extended thinking; skip manual CoT |
| Structured classification, Haiku, high-stakes | Self-Consistency, K=5 |
| Fact that requires a lookup | ReAct + tool |
| Answer has a checkable success criterion | Reflexion |
| Safety-critical output on a minority of prompts | Constitutional AI second pass |
| Shallow branching, fast heuristic fits | Direct prompting — don't use ToT |

Every deployment of one of these patterns lands with its own eval prompts (Section 7) and its own entry in AIPATH.md §9.
