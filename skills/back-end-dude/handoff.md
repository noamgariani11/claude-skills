# Sibling-skill Handoff

Back-end-dude is for senior server-side work. When another skill is a better fit, hand off rather than grinding through. State explicitly when you're suggesting a handoff and why.

## When to hand off

| Situation | Hand off to | Why |
|---|---|---|
| Deep auth / crypto stress-test, real-attacker mindset | `/security-dude` | Actively attacks the app; covers secrets archaeology, supply chain, real repro steps. Back-end-dude audits at code-review depth; security-dude goes deeper. |
| Infrastructure-wide security audit (CI/CD, LLM, skill supply chain, STRIDE) | `/cso` | Infra-first, broader scope than a code review. |
| API contract from the client's perspective; request/response shape ergonomics | `/front-end-dude` | Owns the consumer side. Pair when designing a new endpoint. |
| Test strategy construction / exhaustive test writing | `/qa-dude` | Runs tests in parallel, treats app as system under test; better at generating edge cases than back-end-dude reviewing existing tests. |
| Systematic bug investigation with root-cause discipline | `/investigate` | The Iron Law — no fix without root cause. Use when the bug is puzzling, not when the fix is obvious. |
| Pre-landing PR diff review against base | `/review` | Specialized for diff-based structural review; catches conditional side effects and trust-boundary bugs. |
| Pre-push production-readiness gate | `/checker` | Five sequential gates (intent, minimalism, quality, functionality, prod readiness). Back-end-dude is not a ship-gate. |
| Design/implementation plan sanity-check from eng-manager POV | `/plan-eng-review` | Lock in architecture, data flow, test coverage before coding. Pair this with back-end-dude's build mode for big features. |
| CEO-mode rethink of the problem space | `/plan-ceo-review` | "Is this even the right problem?" Back-end-dude assumes the problem is settled. |
| Code reuse / dead code / simplification pass | `/simplify` | Back-end-dude focuses on correctness and reliability; simplify focuses on removing unneeded code. |

## Handoff phrasing

Make handoffs explicit so the user can redirect. Examples:

- "This looks like a real security issue — recommend running `/security-dude` to stress-test it before the fix ships."
- "The bug reproduces but I don't yet have a root cause. Recommend `/investigate` to do it properly; I can resume the fix once we have one."
- "The endpoint design is sound from the server side. Before coding, worth pairing with `/front-end-dude` to sanity-check the DTO from the consumer's angle."

## When *not* to hand off

- The user asked *me* for the review / build / debug. Do the work; mention the sibling skill only as a follow-up option.
- The sibling's scope would duplicate mine (another code reviewer for the same PR). Cite findings, don't stack reviewers.
- Under time pressure on a small change. A single good review is usually enough.

## Pairing patterns

Some work benefits from two skills in sequence, not a handoff:

- **Big feature build**: `/plan-eng-review` → back-end-dude Build → `/review` → `/checker` → `/ship`.
- **Security-sensitive change** (auth, billing, PII): back-end-dude review → `/security-dude` stress test → fixes → `/checker`.
- **Puzzling prod incident**: `/investigate` (root cause) → back-end-dude Build (fix) → regression test → postmortem.
