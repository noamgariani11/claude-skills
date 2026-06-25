# Output Templates

Every mode produces a consistent, scannable output. Pick the template that matches the classified mode from [SKILL.md](./SKILL.md).

---

## Review mode

Use when asked to review an API / PR / endpoint / migration.

```markdown
# Back-end review: <what was reviewed>

**Mode:** Review
**Scope:** <file paths or PR #>
**Verdict:** [ Block / Request changes / Approve with nits ]

## Summary
<2-3 sentences: what this change does and the highest-severity concern.>

## P0 — Block merge (correctness / security)
- **<path/to/file.ts:42>** — <what's wrong>
  - Why: <the invariant / threat it violates — cite BOLA, SQLi, etc.>
  - Fix:
    ```ts
    // before → after diff or concrete change
    ```

## P1 — Address before real users (reliability / performance)
- **<path:line>** — <issue>
  - Why: <consequence under load / partial failure>
  - Fix: <one-line or short diff>

## P2 — Cleanup / hygiene
- **<path:line>** — <nit> — <one-line fix>

## What's good
- <1-3 things the author got right — reinforcing good patterns matters>

## Follow-ups (not blocking this PR)
- <separate issues worth filing, if any>
```

Rules:
- Every finding cites `file:line`.
- Every finding has a **one-sentence "Why"** (the invariant, not just "this is wrong").
- P0 findings get a concrete fix (diff or replacement code).
- If nothing is P0, say so explicitly — "No correctness or security blockers."
- Keep "What's good" honest and specific. No boilerplate praise.

---

## Build mode

Use when building a new endpoint / service / module.

```markdown
# Build: <feature name>

**Mode:** Build
**Route(s):** <METHOD /path>
**Owner entity:** <which table(s) / module>

## Contract
### Request
- Method + path: `POST /api/...`
- Body (Zod): <schema name from src/lib/schemas.ts>
- Auth: <required session? admin? anon?>
- Rate limit: <per-user / per-IP / per-operation>
- Idempotency: <Idempotency-Key required? unique-constraint-based? not needed?>

### Response
- 200: `<DTO shape>`
- 4xx error codes: `<stable code strings>` (e.g. `orders.not_found`)
- 5xx: generic; internal error logged with correlation id.

## Invariants
- <each must-hold property: "no two rows for same (user, external_id)", "amount_cents >= 0", etc.>

## Files changed
- `src/app/api/<path>/route.ts` — handler (guard → validate → service → response).
- `src/server/modules/<m>/<m>.repository.ts` — DB access (ownership in `WHERE`).
- `src/server/modules/<m>/<m>.service.ts` — orchestration (if non-trivial).
- `src/lib/schemas.ts` — Zod schemas for request + response.
- `db/schema.sql` — <new columns / indexes / constraints, if any>
- `tests/<m>.test.ts` — happy + unauth + wrong-owner + bad-input + conflict.

## Code
### Handler
```ts
<10-20 lines, boring>
```

### Repository
```ts
<parameterized SQL with ownership>
```

### Tests
```ts
<happy + one failure case>
```

## Follow-ups
- <anything intentionally deferred; e.g., "add rate-limit by IP in a follow-up PR">
```

Rules:
- Contract first; code after.
- Handler is ≤20 lines. If longer, the logic belongs in the service.
- Tests cover at least: happy, unauth, wrong-owner, bad-input, conflict.
- Explicitly list what's deferred vs shipped.

---

## Debug mode

Use when asked "why is X broken / slow / intermittent."

```markdown
# Debug: <short problem statement>

**Mode:** Debug
**Symptom:** <exact observed behavior>
**Impact:** <users affected, paths affected, severity>

## Repro
1. <step>
2. <step>
3. Expected: <...>; Actual: <...>
- Request id / trace id / timestamp: <...>

## Investigation
- Logs: <key findings, with correlation id and what they show>
- Metrics: <relevant RED / USE metrics around the event>
- Traces: <where the time went / where the error came from>
- Code path: <which route → service → repo was involved>
- Recent changes: <deploys, config flips, migrations in the window>

## Hypothesis (ranked)
1. **<most likely>** — supported by: <evidence>. Disproven by: <test>.
2. **<next>** — ...

## Root cause
<what it actually is, with file:line or query and the mechanism>

## Fix
```diff
- <broken code>
+ <fixed code>
```
- Why this is the root cause, not a symptom: <one sentence>
- Regression test: <path to new test>

## Follow-ups
- <monitoring / alerting gaps exposed>
- <other code with the same bug>
- <postmortem needed? yes/no + why>
```

Rules (Iron Law of investigate):
- No fix without a root cause. If root cause is unknown, say so and propose the next diagnostic step, don't paper over.
- Every fix ships with a regression test that would have caught the bug.

---

## Design mode

Use when asked "how should we build X" / "should we...".

```markdown
# Design: <system / capability>

**Mode:** Design
**Problem:** <one-sentence problem statement>
**Constraints:** <SLO, throughput, budget, team size, timeline>

## Current state
<what exists; what's broken or missing>

## Options
### Option A — <name>
- How it works (2-4 sentences):
- Pros: <...>
- Cons: <...>
- Failure modes: <slow dep, downed dep, partial failure, replay, etc.>
- Cost: <DB load / $/request / operational complexity>
- When this wins: <...>

### Option B — <name>
<...>

### Option C — do nothing / defer
- What breaks if we don't solve this now?
- What's the hold-until trigger?

## Recommendation
**<A / B / C>**, because: <the 1-2 deciding factors>.

## Plan of record (if recommendation is accepted)
1. <step> — owner, rough size
2. <step>
3. <step>

## Risks & mitigations
- <risk> → <mitigation>

## What we're not solving
- <explicitly out of scope, to prevent scope creep>
```

Rules:
- Always present at least two options plus "do nothing." Optionality shows you understood the problem, not just picked a favorite.
- Enumerate failure modes per option ([database.md](./database.md) and [stability.md](./stability.md) have the canonical list).
- Recommendation is a recommendation, not a decree. The user decides.

---

## Short-answer mode

For small asks ("is this index right?", "is this status code correct?"), skip templates. Direct answer + `file:line` + one-line reason. Under 150 words.
