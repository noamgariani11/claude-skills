# Training pipeline: DSPy, fine-tuning, and the feedback flywheel

_Section references (§Evaluation, §Guardrails, ...) map to files in `references/`. The map is in SKILL.md._

## Programmatic prompt optimization (DSPy)

Hand-tuning a prompt is a craft. When you have a clear metric and a corpus, treat the prompt as a parameter and let an optimizer tune it. DSPy (Khattab et al., Stanford, 2023) is the reference framework: declare a program (inputs → outputs), declare a metric, let a **teleprompter** search over few-shot examples, instruction phrasing, and chain structure to maximize the metric.

### When DSPy fits Kablan

- **Clear metric** (rubric score, FactScore, exact-match pass-rate, `KABLAN_ESTIMATE` deviation) that can be computed automatically.
- **Sub-call with bounded scope**: difficulty classifier, cost-estimator structurer, appliance detector, marker extractor. Not the full conversational main prompt.
- **Training corpus ≥ 50 prompts** with labels or rated responses, so the optimizer separates signal from noise.
- **You've hand-tuned and hit a plateau**. Optimizer gains are typically 2-15 rubric points above a decent baseline, rarely more. If hand-tuning still has headroom, close that first.

### When it doesn't fit

- Free-text conversational responses with fuzzy "good" / "bad" judgment. No clean metric → no signal to optimize.
- Any call where the response is the user-facing product (main chat). Opaque-optimized prompts drift from the designed voice; you lose the Tone & Voice compliance you paid for in the persona anchor.
- Safety-critical calls (difficulty-5 refusal, emergency triage). You want to hand-own every line — no optimizer.
- Corpus < 30 items. The optimizer overfits; "gains" disappear on holdout.

### Workflow

```python
# pip install dspy-ai
import dspy
from dspy import InputField, OutputField, ChainOfThought, Signature

# 1. Declare the program
class DifficultyClassifier(Signature):
    """Classify home-repair tasks by difficulty 1-5. 5 = licensed pro required."""
    user_message = InputField()
    photo_summary = InputField(desc="one-sentence photo description, empty if no photo")
    difficulty   = OutputField(desc="integer 1-5")
    reasoning    = OutputField(desc="one sentence naming liability factors")

program = ChainOfThought(DifficultyClassifier)

# 2. Declare the metric
def metric(example, pred, trace=None):
    # exact-match on integer; partial credit for off-by-one below 5
    try:
        got = int(pred.difficulty)
    except Exception:
        return 0.0
    if got == example.difficulty: return 1.0
    if example.difficulty == 5 and got != 5: return 0.0     # safety floor
    if abs(got - example.difficulty) == 1: return 0.5
    return 0.0

# 3. Split data (80/10/10)
train, dev, test = split_stratified(examples, by="difficulty", ratios=(0.8, 0.1, 0.1))

# 4. Wire in the execution backend (Claude)
dspy.configure(lm=dspy.Claude(model="claude-haiku-4-5"))

# 5. Optimize
optimizer = dspy.BootstrapFewShotWithRandomSearch(
    metric=metric,
    max_bootstrapped_demos=4,
    num_candidate_programs=16,
)
optimized = optimizer.compile(program, trainset=train, valset=dev)

# 6. Ship-gate: compare on held-out test with bootstrap CI
baseline_scores = [metric(e, program(user_message=e.user_message, photo_summary=e.photo_summary)) for e in test]
optimized_scores = [metric(e, optimized(user_message=e.user_message, photo_summary=e.photo_summary)) for e in test]
from scipy.stats import bootstrap
delta_ci = bootstrap((optimized_scores, baseline_scores), lambda o, b: sum(o)/len(o) - sum(b)/len(b), n_resamples=1000).confidence_interval
assert delta_ci.low > 0, "optimizer win not significant, do not ship"

# 7. Extract artifacts
print(optimized.predict.signature.instructions)  # tuned instruction
print(optimized.predict.demos)                   # selected few-shot demos
```

Output: a prompt string plus a small set of few-shot demos. **Audit both by hand before shipping.** Read every demo — the optimizer will happily select demos that game the metric but embarrass you in production.

### Kablan applications (highest value first)

1. **Difficulty classifier** (precedes `KABLAN_PRO_MATCH`). Clean metric (matches hand-labeled difficulty), tight scope, safety-relevant. Expect 5-10 pp accuracy lift over hand-tuned baseline. Pair with Self-Consistency (§Reasoning patterns) for the 4-vs-5 boundary.
2. **Cost-estimate marker extractor**. Metric: valid JSON `KABLAN_ESTIMATE` + cost range within ±30% of hand-labeled ground truth. DSPy helps force the schema compliance even on weaker models.
3. **Appliance detector from photo + text** (`/api/profile/appliances/detect`). Metric: multi-label F1 against hand-labeled appliance list. Good DSPy candidate because the output schema is structured.

### Rules

- Lock in baseline evals **before** optimization. Compare baseline vs optimized with paired bootstrap CI (§Evaluation). No ship if CI overlap.
- **Re-optimize on model version bumps.** An optimal prompt for Haiku 4-5 is not optimal for Haiku 4-6. Budget the optimization cost into every model pin bump.
- Commit the training set, metric function, and teleprompter config alongside the optimized prompt in `evals/dspy/`. Reproducibility is non-negotiable — the optimizer is stochastic, and "the prompt that used to work" has to be re-generatable.
- Keep the hand-tuned baseline committed as `prompt_hand.ts`. If the optimized version regresses in production, swap back in one commit.
- Treat DSPy-generated demos as part of the prompt surface for cache purposes (§Prompt caching): byte-stable means they can live inside the cached prefix.
---

## Fine-tuning, distillation & synthetic data

Prompt engineering is free and infinitely reversible. Fine-tuning is a commitment — weights, eval overhead, re-tuning on every base-model bump. At a certain scale and narrowness, a fine-tuned sub-call beats any prompt. Know when to cross the threshold.

### Decision tree: prompt vs fine-tune

```
                  Prompt-engineering first
                           │
      ┌────────────────────┼────────────────────┐
      ▼                    ▼                    ▼
 Metric plateaued     Clear metric         Cost or latency
 after 3+ hand       + corpus ≥ 500       hurt, the call is
 iterations?         labels?               narrow & repeated?
      │                    │                    │
     Yes                  Yes                  Yes
      ▼                    ▼                    ▼
 DSPy first         DSPy → SFT             Distillation
 (§Programmatic)    (this section)         (this section)
```

**Kablan hard thresholds** (April 2026):
- **Main conversational chat: never fine-tune.** The conversation is the product; opaque weights risk every voice dimension we designed.
- **Sub-calls** (difficulty classifier, appliance detector, cost-marker extractor, title gen): **fine-tune when corpus ≥ 500 labels AND hand-tuned prompt plateaued at <90% of ceiling target**.
- **Structured extractors** (JSON-only outputs): **fine-tune earlier, ≥ 300 labels**. Schema compliance is the highest-value thing you can fine-tune into a smaller model.

### Supervised Fine-Tuning (SFT)

Label a corpus of `(input, desired_output)` pairs. Train the model to produce the output given the input. Baseline option.

```python
# difficulty-classifier SFT dataset
dataset = [
    {"messages": [
        {"role": "system", "content": classifier_system_prompt},
        {"role": "user", "content": f"{user_message}\n\nPhoto: {photo_summary}"},
        {"role": "assistant", "content": f"difficulty: {gold.difficulty}\nreasoning: {gold.reasoning}"},
    ]}
    for gold in labels
]

# training: provider-specific.
# Anthropic: via Files + Batch APIs (check current docs for pinned model compatibility).
# OpenAI: client.fine_tuning.jobs.create(model="gpt-4.1-mini", training_file=...)
# Open-weights (Llama 3.1-8B baseline): Axolotl / Unsloth / torchtune.
```

**Gotchas**:
- Split 80/10/10 for train/dev/test; report bootstrap CI on *test*, never dev.
- Validate schema compliance on 100% of outputs — SFT'd models still drift.
- Hash the training set; tie the artifact to the hash. Reproducibility is non-negotiable.

### Direct Preference Optimization (DPO) (Rafailov et al., 2023)

When you have paired preferences (A preferred to B on the same prompt), DPO aligns the model toward the preferred answer without a separate reward model. Cheaper than RLHF, often just as good.

**Kablan recipe**: pairwise preference data from §Pairwise preference evaluation **is** DPO training data. Every human-judged "Response A better than B" becomes `{chosen: A, rejected: B}`. Collect 500+ pairs before training.

DPO over SFT when:
- You have paired preferences, not absolute labels.
- The failure mode is "right content, wrong phrasing" — SFT labels right phrasing in isolation; DPO uses both good and bad in context.

### Distillation (teacher-student)

Train a small model to mimic a large model's outputs on a specific task. Cost savings are huge: a distilled Haiku-sized classifier runs at ~10× lower cost than Opus with comparable narrow-task accuracy.

**When Kablan should distill**:
- Difficulty classifier — narrow output space, currently Opus, clear target.
- Cost-range extractor — JSON schema, currently over-budgeted on Opus.
- Appliance detector — classification + structured output.

**Recipe**:
1. Generate 5k-20k `(input, teacher_output)` pairs using Opus as the teacher (synthetic data generation — see next subsection).
2. SFT a Haiku-sized student on those pairs.
3. Eval student on the same test set as the teacher. Target: **≥95% of teacher accuracy at ≤10% of cost**.
4. Ship the student as a sub-call replacement. Monitor for drift.

### Synthetic data generation

"Not enough labels to fine-tune" is almost never true. It means "not enough *human* labels". LLMs are excellent label generators for narrow tasks.

**Kablan pipeline** for the difficulty classifier:

```python
# Step 1: seed corpus — real production user messages
seed_prompts = load_production_messages(n=500)

# Step 2: augment via paraphrase (cheap Haiku)
def paraphrase(prompt):
    return haiku.generate(f"""
    Rewrite this home-repair user message in 5 ways a real homeowner might phrase it.
    Keep the same trade, same difficulty, same implied tools.
    Original: {prompt}
    """)
augmented = [p for seed in seed_prompts for p in paraphrase(seed)]  # ~2500 variants

# Step 3: label with the teacher (Opus)
def label(prompt):
    return opus.classify(prompt, schema=DifficultySchema)
labels = [label(p) for p in augmented]

# Step 4: self-consistency filter — discard where K=5 teacher calls disagreed
filtered = [l for l in labels if self_consistency_vote(l) == l.difficulty]

# Step 5: human review of 5% random sample + ALL boundary cases (4 vs 5)
#   Boundary cases matter most — they're where sycophancy and liability collide.
gold_test = human_review_subset(
    filtered,
    sample_rate=0.05,
    must_review=lambda l: l.difficulty in [4, 5]
)

# Step 6: SFT Haiku on (augmented minus gold_test)
train(haiku, augmented - gold_test, eval_on=gold_test)
```

**Synthetic data traps**:
- **Mode collapse**: teacher regurgitates a narrow style. Paraphrase step mitigates; measure with Distinct-n or Self-BLEU on augmented.
- **Teacher bias**: student inherits teacher blind spots. Ground the test set in *real* production data, not synthetic.
- **Label noise**: teachers are 90% accurate at best. Self-consistency filter + boundary-case human review is non-negotiable.
- **Distribution shift**: augmentation drifts toward cleaner/more formal language than real users type. Compare n-gram distributions between real and synthetic to check.

### Use the Batches API for bulk labeling

Synthetic data generation is embarrassingly parallel and not latency-sensitive. Anthropic's Message Batches API processes batches asynchronously at **50% off standard input + output pricing**, with up to 24-hour SLA (usually minutes). For the worked example above (5000 synthetic pairs × $0.006/pair = $30), batch pricing cuts that to $15. Every 1000 items of distillation labeling saves real money.

```python
batch = anthropic.messages.batches.create(
    requests=[
        {"custom_id": f"label-{i}", "params": {
            "model": "claude-opus-4-7",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}],
        }}
        for i, prompt in enumerate(augmented)
    ]
)
# poll batch.id until status == "ended", then read results by custom_id
```

**When to reach for batch mode**:
- Distillation labeling jobs ≥500 items → always.
- Canary corpus backfills on a new pinned model → always.
- Full eval corpus re-runs not attached to a PR → yes.
- Per-PR canary runs → no, SLA too loose.
- Anything interactive (human eval protocol, ad-hoc) → no, user is waiting.

Batch mode preserves prompt caching, so the combined discount compounds: 50% off inputs × 90% off cached tokens = ~95% cost reduction on the cached portion of each batched call. Worth structuring your labeling prompts to maximize cached-prefix share.

### Cost math: when distillation pays

Rough model (confirm current pricing before committing):

```
Opus per classifier call:   ~$0.006  (1500 input + 100 output tokens)
Haiku per classifier call:  ~$0.0004

One-time distillation cost:
  5k synthetic pairs × $0.006 (teacher labels)   = $30
  SFT training job                                = ~$50
  Eval sweep                                      = ~$20
  Total one-time                                  ≈ $100

Break-even:
  Opus calls needed to save $100
  = $100 / ($0.006 − $0.0004) = ~18000 calls

At 500 classifier calls/day ⇒ 36 days to payback.
```

If the sub-call is invoked >500 times/day, distillation pays back in ~6 weeks. Below that, prompt engineering is still cheaper.

### Ship rules

- Always keep the prompt-engineered baseline committed as `prompt_hand.ts`. Fine-tunes regress when base models update; you need instant rollback.
- Re-run the full eval corpus on every base-model bump. SFT on `claude-haiku-4-5` does not transfer cleanly to `claude-haiku-4-6`.
- Commit training set hash + eval set hash + model ID + hyperparameters at `evals/finetunes/<name>/metadata.json`. Treat fine-tuned weights like a database migration: versioned, reversible, documented.
- Every fine-tune lands with an AIPATH.md §9 entry including baseline vs fine-tuned bootstrap CI per rubric dim, cost delta, latency delta.
- Never SFT on data containing raw user PII. Run the redaction layer first.
---

## Feedback flywheel: human eval → SFT / DPO data

Every rated response is training signal. A §Human evaluation protocol session produces 20-100 `(prompt, response, rubric, note)` tuples. Treat them as raw material, not a one-off report. Over quarters they become the SFT/DPO corpus that shifts Kablan from "prompt-engineered" to "trained on our users" — a moat no competitor starting fresh can replicate.

### Pipeline

```
 Session artifact (evals/sessions/*.json)
           │
           ▼
 1. Auto-cluster free-text notes into themes      ← Haiku sub-Agent, Claude Code credits
           │
           ▼
 2. Aggregate themes across sessions; rank by
    count and severity                            ← weekly roll-up (loop or CI cron)
           │
           ▼
 3. Triage each theme:                            ← operator decision
       - Prompt fix
       - Guardrail rule
       - SFT candidate
       - DPO candidate
       - Eval gap
       - Unactionable noise
           │
           ▼
 4. Materialize SFT / DPO training data from
    rated tuples or pairwise comparisons
           │
           ▼
 5. Periodic fine-tune pass                       ← every 2-4 weeks or N≥500, first to hit
```

### Step 1: auto-cluster free-text notes

After each session, spawn a Haiku-equivalent sub-Agent (Claude Code credits) to cluster the notes:

```
Sub-Agent prompt:
  Below are free-text rater notes from one eval session. Group them
  into themes. For each theme return:
    - Theme name (≤5 words)
    - Example note IDs
    - One-sentence summary of the common complaint or praise
  JSON only.
```

Output appends to the session artifact at `aggregate.free_text_themes` (already in the schema in §Human evaluation protocol).

### Step 2: aggregate themes across sessions

`evals/sessions/*.json` accumulates over weeks. Weekly roll-up script (can run via the `loop` skill or CI cron) merges themes by fuzzy string match and counts occurrences:

```python
themes = []
for session in glob("evals/sessions/*.json"):
    for t in session["aggregate"]["free_text_themes"]:
        existing = find_match(themes, t.name, threshold=0.8)
        if existing:
            existing.count += t.count
            existing.example_ids.extend(t.example_ids)
        else:
            themes.append(Theme(**t))

write("evals/themes/weekly.json", sorted(themes, key=lambda t: -t.count))
```

The weekly roll-up lands in AIPATH.md §8 Production Signal Snapshot.

### Step 3: theme triage (the decision step)

For each ranked theme, the operator picks a triage path:

| Triage | When | Action |
|---|---|---|
| **Prompt fix** | Theme names a discrete, prompt-fixable behavior ("too long on easy prompts", "skipped asking for photo") | §Change proposal template → update `prompt.ts` → canary → ship |
| **Guardrail rule** | Theme names a behavior that should be hard-enforced, not prompt-requested ("emitted steps for gas-line work") | Add rule to Layer 2 output classifier (§Guardrails) |
| **SFT candidate** | Theme needs a consistent, non-prompt-fixable pattern shift (tone calibration, domain-specific language) | Accumulate labeled examples; fine-tune sub-call when count ≥ 500 |
| **DPO candidate** | Theme surfaces in pairwise evals where both responses were rubric-fine but one was clearly preferred | Accumulate preference pairs; DPO when count ≥ 500 |
| **Eval gap** | Theme reveals a capability the corpus doesn't cover | Add to CheckList coverage, then pick a triage |
| **Unactionable noise** | "I didn't like the vibe" | Ignore, don't suppress — keep the signal, just don't act on it |

Most themes are prompt fixes. A 5-15% minority are SFT/DPO candidates. Misrouting SFT candidates to prompt fixes causes prompt bloat; misrouting prompt fixes to SFT wastes weeks.

### Step 4: materialize training data

**SFT candidate shape**:

```json
{
  "candidate_id": "SFT-2026-04-18-EV-07",
  "source_session": "2026-04-20T14-32-00",
  "input":  { "system": "...", "messages": [...] },
  "original_response":  "<what Kablan said>",
  "corrected_response": "<what the rater said it should have said>",
  "rubric_before": { "correctness": 4, "density": 2, ... },
  "rubric_target": { "density": 4, ... },
  "theme": "too_long_on_easy_prompts",
  "triaged_as": "sft"
}
```

The operator writes the corrected response. Raw rater notes are not labels — "make it shorter" is not an SFT label; the rewritten response that *is* the correct length is the SFT label.

**DPO candidate shape** (from §Pairwise preference):

```json
{
  "candidate_id": "DPO-2026-04-19-PAIR-12",
  "chosen":   "<winning response>",
  "rejected": "<losing response>",
  "user_message": "...",
  "preference_strength": "strong" | "weak" | "tie_broken",
  "rater_note": "..."
}
```

Store at `evals/training/sft/*.json` and `evals/training/dpo/*.json`. Versioned, hashed, committed.

### Step 5: periodic fine-tune

Trigger when any of these fire first:
- 500 new SFT or DPO candidates accumulated.
- 4 weeks since last fine-tune on this sub-call.
- Regression in the main eval corpus attributable to prompt bloat from too many fixes.

Run the §Fine-tuning, distillation & synthetic data recipe. New artifact lands at `evals/finetunes/<YYYY-MM>/`. AIPATH.md §9 entry with before/after CIs, cost delta, latency delta.

### Flywheel economics (6 months running)

- 20-30 SFT candidates/session × 100 sessions = 2000-3000 raw candidates.
- ~500 high-quality after triage filtering.
- One SFT pass per quarter on each fine-tuneable sub-call.
- Typical lift: difficulty classifier accuracy +2-5pp per pass, 10-30% cost reduction on that sub-call.

No single change is dramatic. Run it for four quarters and Kablan has a trained-on-our-users AI a competitor can't replicate by prompting harder.

### What NOT to do in the flywheel

- **Never SFT the main chat response.** Voice is the product; opaque weights destroy design control. Flywheel targets narrow sub-calls only.
- **Don't auto-promote rater notes to SFT data.** Every SFT candidate goes through operator triage. Raw notes are noisy and rater-biased.
- **Don't skip the human-corrected response step.** "Be more concise" is not a label. "Here is the rewritten response that is concise" is.
- **Don't let the corpus become a monoculture.** If 80% of candidates come from 5 raters, the fine-tune inherits their biases. Rotate raters; flag when diversity drops.
