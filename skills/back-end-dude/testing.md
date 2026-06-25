# Testing

The goal is not "coverage percentage." The goal is confidence that the system behaves correctly under the conditions it'll actually see.

## Pyramid

Lots of fast, narrow tests at the bottom. Fewer, slower, broader tests at the top.

| Layer | Scope | Speed | Count |
|---|---|---|---|
| **Unit** | Pure functions, small classes, validators | ms | many |
| **Integration** | Route + service + real DB; one module at a time | 10–100ms | many |
| **Contract** | Boundary with a third party (Stripe, Anthropic, etc.) | ms, offline | few |
| **End-to-end** | Full stack: HTTP → DB → side-effects | seconds | few, critical paths |
| **Load / chaos** | Performance, failure injection | minutes | targeted, not every PR |

Invert the classic mistake: don't mock-test your way to 100% unit coverage and then discover the real system doesn't work. Integration tests against a real DB catch what unit tests never will.

## Unit tests

- Pure functions. Zod schemas. Parsers (e.g., Kablan's `src/lib/parseAiMarkers.ts`, maintenance health score logic). Validators, formatters, calculators.
- No DB, no network, no file system. If you reach for a mock of the DB, you're probably at the wrong layer.
- Test the behavior, not the implementation. "Given input X, produce output Y." Not "calls `repo.foo` then `repo.bar`."

## Integration tests — the meat

For anything that touches the DB, test against a real Postgres. Two strategies:

### Option A — Testcontainers (or equivalent)

Spin up a throwaway Postgres in a Docker container per test suite. Apply migrations. Run tests. Tear down.

- Pros: 100% realistic, isolated per run, safe for CI.
- Cons: startup cost (~5-10s), needs Docker.

### Option B — Transaction rollback

One shared DB, each test runs inside a transaction that rolls back at the end.

```ts
beforeEach(async () => { await db.query("BEGIN"); });
afterEach(async () => { await db.query("ROLLBACK"); });
```

- Pros: fast (no container startup), easy.
- Cons: doesn't work for code that uses transactions internally (nested tx via savepoints requires care); can't test concurrent access; breaks on pooled connections that span tests.

**Pick one and stick with it.** Kablan with `src/lib/db.ts` + vitest — Testcontainers is the cleanest fit if you're willing to take the startup cost; rollback works if tests are strictly sequential and don't need their own transactions. For repo tests that need `SELECT ... FOR UPDATE` behavior verified, use Testcontainers.

### What to cover

For each route / service / repo:
- **Happy path** — the normal case.
- **Auth failures** — no session (401), wrong user owns the row (403 or 404 depending on policy).
- **Validation failures** — malformed body, missing field, wrong type.
- **Conflict** — unique violation, version mismatch, idempotency-key collision.
- **Retry / idempotency** — same request twice returns the same response, no duplicate side effects.
- **Boundary data** — empty list, max-size list, unicode, null-where-allowed.

## Fakes, not mocks (where possible)

A **fake** is a working but simplified implementation. A **mock** asserts on calls.

- In-memory repository for a unit test of a service? Fine — the fake obeys the same contract.
- Fake clock, fake UUID generator, fake external API (response-replay from fixtures).
- Prefer fakes to mocks because mocks couple tests to implementation. "Called foo with arg x" breaks when you rename `foo`; a fake doesn't care.

Mocks are fine when there's no alternative (third-party SDK, system call). Keep them at the edge of the system.

## Contract tests for third parties

You don't own Stripe, Anthropic, Resend. But the contract with them is critical.

- **Record/replay**: capture real responses in CI once, play them back in tests. Prettier test diffs when contracts change.
- **Schema pinning**: parse every external response through Zod; test that your Zod schema matches recent real payloads. When the provider changes, the test fails loudly.
- **Webhook signature verification** — test with a real signed payload and a tampered one.

## Testing dangerous things

- **Migrations** — run them forward and back (if reversible) on a fresh and a loaded DB in CI.
- **Backfills** — test that they're resumable: run, interrupt, resume, assert the end state is the same as running to completion.
- **Scheduled jobs** — unit test the handler logic; integration test the scheduling (ran at the right time? dedupes across instances?).
- **Webhooks** — send the same payload twice; assert no duplicate effect. Send with bad signature; assert rejection.
- **Concurrent writes** — integration test with two connections, verify the losing writer gets a conflict, not silent corruption.

## Performance testing

- **Per-query**: `EXPLAIN ANALYZE` on hot queries; fail the test if the plan regresses (seq scan where index scan was expected).
- **Per-endpoint**: benchmark the happy path before and after changes. A 50ms endpoint becoming 500ms is a regression even if the tests pass.
- **Load**: for critical endpoints, a k6 or autocannon script that runs at 1x normal load and verifies p95/p99 stay under SLO.

Not every endpoint, not every PR. For the money-path and hot paths.

## What not to test

- Framework code (Next.js routes its own requests; don't re-test routing).
- Zod schemas themselves (Zod is tested; test your schema *composition* if it's non-trivial).
- Private implementation details — test the public contract.
- Anything trivial enough that the test is as complex as the code (getter/setter, straight-through mapper).

## Kablan conventions

- Vitest, tests in `tests/**/*.test.ts`.
- Services at `src/server/modules/<module>/`; repos at `.repository.ts`.
- DB access via the proxy in `src/lib/db.ts` — for integration tests, point at a test DB via `DATABASE_URL`.
- Fixture data via `db/seed.sql` for dev; for tests, construct explicitly in `beforeAll` — don't rely on seed.
