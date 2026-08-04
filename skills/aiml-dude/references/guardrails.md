# Guardrails

_Section references (§Evaluation, §Guardrails, ...) map to files in `references/`. The map is in SKILL.md._

## Guardrails & defense in depth

Safety that lives only in the system prompt is a single point of failure. A jailbreak, a model update, a prompt edit — any one can break the guarantees you thought you had. Defense in depth puts independent classifiers on both sides of the main model call.

### Three-layer architecture

```
[User input]
    ↓
[Layer 1: Input classifier]   ← block unsafe asks before inference
    ↓
[Main model]                  ← system prompt + extended thinking + CAI pass
    ↓
[Layer 2: Output classifier]  ← block unsafe output before render
    ↓
[Layer 3: Logging boundary]   ← PII-redacted, tagged for review
```

Each layer is cheap, independent, has a different failure mode. A system prompt that fails once every 1000 requests + a classifier catching 95% of what the main model let through ≈ 1-in-20000 failures shipped to a user.

### Layer 1: input classifier

Fires before the main call. Decisions: allow / warn / block / escalate.

**Model options** (pick one, measure):
- **Llama Guard 3-8B or 4-12B** (Meta, open-weights): fast, trained on a documented safety taxonomy. Self-host or hosted variant.
- **OpenAI moderation** (`omni-moderation-latest`): free at the API layer. Good baseline for obvious abuse.
- **Haiku-as-classifier**: your own rubric. Wins when the taxonomy is domain-specific (Kablan: "out-of-scope", "difficulty-5 DIY ask", "emergency triage").

**Kablan-specific taxonomy**:

```ts
type InputClassification = {
  allow: boolean;
  category:
    | "safe"
    | "emergency"          // gas, fire, CO, live electrical
    | "scope_violation"    // legal/medical/financial
    | "difficulty_5_diy"   // user pushing DIY on pro-only work
    | "jailbreak_attempt"
    | "pii_heavy";         // user dumped too much personal info
  confidence: number;        // 0-1
  action: "pass" | "warn_in_prompt" | "hard_refuse" | "route_to_emergency_template";
};
```

**Wiring rules**:
- `safe` → straight to main model.
- `emergency` → bypass main model. Emit a hard-coded triage template (911 / gas utility / electrical emergency). Never let the LLM improvise here.
- `scope_violation` → redirect template ("I handle home repair; for this, here's where to look").
- `difficulty_5_diy` → pass through, but inject a context note into the main prompt ("user may push for DIY on pro-only work") and *force* the CAI pass on output.
- `jailbreak_attempt` → clean refusal + log to the red-team review stream.

### Layer 2: output classifier

Fires between generation and render. Catches:
- Step-by-step instructions for permit-required work the main model emitted anyway.
- Code section or part-number citations that fail citation-verification (§Hallucination playbook).
- Sycophantic "go ahead and DIY" when the input classifier said difficulty-5.
- PII in the generated response (address, phone, named location).

```ts
type OutputClassification = {
  pass: boolean;
  violations: Array<
    | "unlicensed_work_steps"
    | "unverified_code_cite"
    | "fabricated_part_number"
    | "yielded_to_user_framing"
    | "pii_emitted"
  >;
  action: "pass" | "redact_and_pass" | "regenerate" | "replace_with_triage";
};
```

- `pass` → render.
- `redact_and_pass` → strip violating segments (fabricated part number → "the cartridge specific to your unit") and render the redacted version.
- `regenerate` → one more main-model pass with the violation surfaced in context. Cap at one retry.
- `replace_with_triage` → drop the generation, emit the hire-a-pro template.

### Layer 3: PII redaction at the logging boundary

Everything leaving the process gets PII-redacted at log write, not at query time. Kablan users post photos of their homes — receipts on counters, faces in reflections, street signs through windows. Logs are one breach away from a privacy incident.

Redaction rules:
- Regex: US phone, SSN, email, street address, credit card.
- NER (spaCy or a small model) for names + locations.
- Images: log the file hash and the sub-Agent's one-sentence description. Never log base64.
- User IDs: hashed with a session-scoped salt. Never log plaintext account IDs.

### Latency / cost budget for all layers

Every guardrail taxes latency and cost. Budget it in the §Change proposal template's LATENCY / COST BUDGET block.

April 2026 rough targets:
- Haiku-class input classifier: ~80-150ms p95, ~200 input + 50 output tokens.
- Llama Guard 7B hosted: ~100ms p95.
- Output classifier: same shape, fires on a fraction of prompts by risk.
- PII redaction: 20-40ms regex-only; 100-200ms NER-backed.

Ceiling for all guardrails combined: **+300ms p95 TTFT**. Above that, the architecture needs rethinking.

### Fire-rate matrix

| Prompt class | Input classifier | Output classifier | PII redaction |
|---|---|---|---|
| Easy DIY (diff 1-2) | Always | 10% sample | Always |
| Moderate (diff 3) | Always | 20% sample | Always |
| High-stakes (diff 4-5) | Always | Always | Always |
| Emergency-flagged | Always + template route | N/A | Always |
| Adversarial corpus | Always | Always | Always |

### Incident wiring

Every classifier block logs: `{input_hash, input_category, output_category, user_id_hash, classifier_model, classifier_version, ts}`. That log is the audit trail for post-incident review.

Hand off to `security-dude` / `cso` for SIEM rules, alert routing, access control on the log store. `aiml-dude` owns the classifier choice, rubric, and thresholds.
