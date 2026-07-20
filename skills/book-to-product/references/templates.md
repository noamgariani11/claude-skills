# Templates, tables, and vocabularies

Use these exactly so IDs and columns stay uniform across sessions and books.
IDs are stable and never reused: claims `BK-001`, opportunities `OPP-001`,
tasks `TASK-001`, numbered in order of creation within the run.

## claims/INDEX.md

One row per batch. This is the only file you need to read to know what the
ledger contains.

| Batch | File | Source range | Chapters/sections | Claim IDs | State |
|---|---|---|---|---|---|

`Source range` is lines or pages depending on the unit chosen for the run
(passes.md, Pass 0). `synthesis.md` gets a row too, with `-` for batch and
source range, holding the Pass 3 claims that belong to no single batch.

State: `complete` | `in-progress` | `skimmed-out-of-focus` | `not started`.

These are batch states. The reading map tracks *chapters*, which additionally
use `not substantive` and `unread` - a chapter can be non-substantive while the
batch containing it is `complete`. Two vocabularies, two units, deliberately;
the coverage audit checks the chapter-level one.

## claims/batch-NN.md

One record per claim, not a table row. Records append cleanly to a file's end,
survive a bad edit without taking their neighbors with them, and stay readable
when a mechanism needs four lines to describe. Keep the field order fixed.

```markdown
### BK-### - <short claim label>

- Location: <chapter/section, plus the source line or page range>
- Claim: <what the author asserts, in your words>
- Mechanism: <inputs, decisions, sequence, thresholds, failure modes, outputs>
- Evidence type: <causal study | correlation | case study | expert judgment |
  metaphor | speculation | none>
- Evidence detail: <what the book actually presents, including sample/context>
- Scope/assumptions: <company size, channel, geography, maturity, data volume>
- Counterpoint/limitation:
- Sheevook relevance: <your inference - kept distinct from the claim above>
- Confidence: high | medium | low | unverified
- Status: new | confirmed | refined | contradicted | duplicate |
  not-applicable | verify-live
```

- `Location`: page plus chapter/section when pagination is reliable, otherwise
  chapter/section plus the source marker in the run's chosen unit. A Pass 3
  synthesis claim lists every section it draws on.
- `Mechanism` is the field that makes a claim implementable later. A topic
  label is not a mechanism. If you cannot fill it, say so explicitly rather
  than restating the claim - a claim with no mechanism is a candidate for
  `research-only`, and knowing that early saves inventing one in Pass 7.
- Duplicates found in Pass 3 keep their original record, set
  `Status: duplicate`, and gain a `Duplicate of: BK-###` line naming the
  surviving claim. Never delete an ID and never renumber - later files cite
  these, and a dangling `BK-###` reference is worse than a redundant record.
  Merge any detail the duplicate had that the survivor lacks before marking it.

## 02-SHEEVOOK-DELTA.md

| Claim ID(s) | Book insight | Existing research | Current implementation | Delta | Decision | Affected files | Verification needed |
|---|---|---|---|---|---|---|---|

Delta classes:

- `CONFIRMS`: strengthens an existing doctrine or implementation.
- `REFINES`: adds useful nuance, scope, sequence, or safeguards.
- `CONTRADICTS`: conflicts with existing research or product behavior.
- `NEW`: materially useful and not represented.
- `ALREADY-SHIPPED`: useful but already encoded; no new task.
- `OBSOLETE/STALE`: the book reflects an outdated environment.
- `INAPPLICABLE`: unsuitable for Sheevook's audience, architecture, data, or
  ethical constraints.
- `REQUIRES-EVIDENCE`: plausible, but insufficiently supported for product use.

## 03-OPPORTUNITY-MAP.md

| Opportunity ID | Claim IDs | User problem | Proposed leverage | Expected outcome | Evidence/confidence | Dependencies | Risks | Candidate touchpoints | Disposition |
|---|---|---|---|---|---|---|---|---|---|

Disposition: `candidate` | `experiment` | `research-only` | `reject` |
`already-covered`.

## 04-IMPLEMENTATION-BACKLOG.md task templates

Two forms. XS/S tasks use the short form; M/L/XL use the full form.

### Short form (XS/S)

```markdown
## TASK-### - <imperative title>

- Status: proposed | blocked | duplicate | rejected
- Priority: P0 | P1 | P2 | P3
- Opportunity: OPP-###
- Evidence: BK-###
- Confidence: high | medium | low | unverified
- Effort: XS | S
- Current behavior (with file references):
- Proposed behavior:
- Likely code touchpoints:
- Acceptance criteria:
```

Any short-form task that is `P0`, touches SQL or schema, changes an AI call, or
alters a user-facing claim uses the full form instead regardless of effort -
those carry risks the short form has nowhere to record.

### Full form (M/L/XL)

```markdown
## TASK-### - <imperative title>

- Status: proposed | blocked | duplicate | rejected
- Priority: P0 | P1 | P2 | P3
- Opportunity: OPP-###
- Evidence: BK-###, BK-###
- Confidence: high | medium | low | unverified
- User problem:
- Product outcome:
- Why this belongs in Sheevook:
- Current behavior (with file references):
- Proposed behavior:
- In scope:
- Out of scope:
- Dependencies/prerequisites:
- Risks and failure modes:
- Privacy/security/legal considerations:
- Data and migration impact:
- Deterministic fallback / no-AI behavior:
- AI gate, cache, tier, and evaluation impact (if any):
- Research files to add/update:
- Likely code touchpoints:
- Test plan:
- Acceptance criteria:
- Rollout/observability:
- Effort: M | L | XL
- Value: low | medium | high
- Recommended sequence:
```

Priority meanings:

- `P0`: current behavior is unsafe, legally risky, dishonest, data-leaking,
  or materially incorrect.
- `P1`: strengthens the core loop or fixes a serious quality/reliability gap.
- `P2`: useful expansion with good evidence and bounded complexity.
- `P3`: optional polish, speculative value, or horizon work.

## How the pass vocabularies connect

Each pass labels findings in its own vocabulary, and a finding has to survive
the handoffs without changing meaning or quietly disappearing. The mapping is
fixed:

| Pass 4 delta | Pass 5 decision | Pass 6 disposition | Pass 7 outcome |
|---|---|---|---|
| `NEW`, `REFINES`, `CONTRADICTS` | `keep` | `candidate` | a task, priority by risk and value |
| `NEW`, `REFINES` | `narrow` | `candidate`, reduced scope | a task whose "Out of scope" records what was cut |
| any | `defer` | `research-only` | no task; deferred section, with the reason |
| any | `reject` | `reject` | no task; rejected section, with the reason |
| `OBSOLETE/STALE`, `REQUIRES-EVIDENCE` | `blocked-pending-verification` | `candidate` or `experiment` | a task with `Status: blocked`, naming what would unblock it |
| `CONFIRMS`, `ALREADY-SHIPPED` | not reviewed | `already-covered` | no task; noted in the synthesis as confirmation |
| `INAPPLICABLE` | not reviewed | not carried forward | no task; the delta row is the record |

Three rows leak in practice. `blocked-pending-verification` must still be
written as a task - deleting it loses the finding and the next run rediscovers
it from scratch. `narrow` must record what was cut, or the next reader restores
the original scope believing it was an oversight. And `CONFIRMS` deserves its
line in the synthesis even though it generates no work: knowing an outside
author independently reached the same conclusion is worth something the next
time that doctrine is questioned.

## CONTINUE-HERE.md

Overwrite at every stable checkpoint. Keep it short.

```markdown
# Continue Here - <Book Title>

- Source identity/hash:
- Mode and focus:
- Current pass:
- Last completed batch and location:
- Coverage completed:
- Coverage remaining:
- Claim IDs issued through: BK-###        <- authoritative, issue the next from here
- Opportunity IDs issued through: OPP-### <- authoritative
- Task IDs issued through: TASK-###       <- authoritative
- Key unresolved questions:
- Live-verification debt:
- Files created/modified:
- Checks already performed:
- Exact next five actions:
```

The three ID counters are authoritative: a resumed session issues the next ID
from them without reading ledger tails to reconstruct the position. That only
holds if they are updated in the same checkpoint that writes the IDs they
count. Update the counter and the records together, never records first.

When the stopping conditions hold, replace the body with `COMPLETE` plus a
one-line pointer to `06-FINAL-SYNTHESIS.md`.
