# Review Checklist

Apply in order. P0 blocks merge. P1 must be addressed before the feature sees real users. P2 is cleanup before the area is maintained by someone else.

## Minimum viable (the top-6 under time pressure)

If you have five minutes, these only. Full list below.

1. **Session guard + ownership in `WHERE`** — BOLA is #1 for a reason.
2. **Zod on all inputs** (body, query, params).
3. **SQL parameterized**; dynamic `ORDER BY`/`LIMIT` uses an allowlist.
4. **Atomic writes in one transaction**; isolation chosen deliberately.
5. **Idempotent retry** (unique constraint with `ON CONFLICT`, or `Idempotency-Key`).
6. **Response DTO has no leaked fields** (password hashes, tokens, internal flags).

## Full checklist

### P0 — Correctness & security (blocks merge)

- [ ] `export const runtime = "nodejs"` on routes touching DB / SDK / crypto.
- [ ] Session guard at top of handler (`requireAuthenticatedSession()` or `requireAdminSession()`).
- [ ] AuthZ enforced in the repository — **ownership in `WHERE`**. Every user-scoped query includes `AND user_id = $n`.
- [ ] Admin endpoints re-verify admin role from DB each request (`requireAdminSession()` already does).
- [ ] Zod validation on request body, query, and path params. No `as any` escape hatches.
- [ ] CSRF enforced on state-mutating cookie-auth routes (Kablan: via `src/proxy.ts` Origin/Host check).
- [ ] SQL parameterized. No string concat with user input. Dynamic `ORDER BY`/columns use an allowlist.
- [ ] Atomic writes in a single transaction with the correct isolation level.
- [ ] Idempotent on retry — unique constraint with `ON CONFLICT`, or `Idempotency-Key` protocol.
- [ ] Webhook path: signature verified, event id deduped, processing in a transaction.
- [ ] No leaked fields in response DTO (password hashes, session tokens, reset tokens, internal flags, other-tenant data).
- [ ] Rate limited on cost/abuse-sensitive routes (auth, AI, email, search, signup, password reset).
- [ ] No secrets in logs, error messages, or responses.
- [ ] Outbound user-provided URLs (SSRF vectors) — allowlisted or IP-validated; private/metadata ranges blocked.

### P1 — Reliability & performance (address before real users)

- [ ] Timeout on every outbound call (HTTP, AI, DB session-level).
- [ ] Retry policy with exponential backoff + jitter where retries are appropriate. Terminal errors not retried.
- [ ] Circuit breaker / fallback on critical downstream dependencies (if traffic warrants).
- [ ] Indexes cover the query's filters, joins, and sort. `EXPLAIN ANALYZE` on hot queries; no `Seq Scan` on large tables.
- [ ] No N+1: DB calls inside a loop folded into `IN (...)` or a join.
- [ ] Pagination capped server-side; keyset/cursor for large lists.
- [ ] Payload size capped at the edge; query complexity capped.
- [ ] Governor caps: max rows per query, max tokens per AI call, max retries, max fan-out.
- [ ] Graceful shutdown / request cancellation handled (don't leave jobs half-done).
- [ ] Metrics emitted: request rate, error rate, p95 latency. Structured log with correlation id.
- [ ] Migration is expand/contract if it touches a large table. Backfills are chunked + resumable.
- [ ] Cache invalidation strategy documented if a cache is introduced. Stampede protection considered.
- [ ] Errors: correct status codes, stable error codes, no stack traces or internal details leaked.

### P2 — Hygiene & maintainability (clean up before handoff)

- [ ] Repository / service / route separation maintained (no DB calls in the handler).
- [ ] DTO converters used — no returning raw rows.
- [ ] Naming matches the module convention (`*.repository.ts`, `toXxxDto`, schema suffix).
- [ ] No dead code, no TODO without a ticket.
- [ ] Happy path, unauth, wrong-owner, bad input, and conflict tests exist.
- [ ] Feature flag / kill switch in place if the change is risky and can be rolled back via config.
- [ ] Dependencies reviewed (any new package — active, reasonable, expected).
- [ ] Comments explain *why* for non-obvious decisions, not *what*.
- [ ] Cost-per-request ballparked (DB rows scanned, tokens consumed, external calls) if this is a hot path.

## Category-specific add-ons

### Auth / session endpoint

- [ ] Password hashed with scrypt/argon2id (Kablan: `src/lib/password.ts`).
- [ ] Timing-safe compare on all secret checks (`crypto.timingSafeEqual`).
- [ ] Rate-limited per account + per IP. Lockout + recovery path.
- [ ] Error messages don't leak "user exists vs wrong password."
- [ ] Session rotated on privilege change.
- [ ] Auth event logged (login, logout, password change, role change).

### Webhook handler

- [ ] `export const runtime = "nodejs"`.
- [ ] Raw body read for signature verification before any JSON parse.
- [ ] Signature verified with timing-safe compare.
- [ ] Event id deduped via `processed_events` table or equivalent.
- [ ] Dedupe + processing in the same transaction (or dedupe-then-queue with outbox).
- [ ] Fast 200 on success, 2xx+4xx on terminal failures, 5xx for transient (so provider retries).
- [ ] Out-of-order events handled or documented as not expected.

### AI endpoint

- [ ] Input length cap, output token cap.
- [ ] Per-user rate limit (not just per-IP).
- [ ] Cost accounting — credit decrement / spend meter updated atomically with the call.
- [ ] Timeout on the AI SDK call.
- [ ] System prompt built with validated inputs (no user-injected instructions in the system message).
- [ ] Response streaming handles client disconnect (don't keep billing tokens after the user left).

### Payment / billing endpoint

- [ ] Amounts in integer cents (or smaller unit). Never float.
- [ ] Idempotency-Key required on every create/charge endpoint.
- [ ] Webhook is the source of truth for Stripe state; don't trust the checkout redirect alone.
- [ ] Ledger (credits / invoices) written transactionally with the billing row update.
- [ ] Webhook signature verified; event id deduped.
- [ ] Refund / dispute path considered, not just happy-path purchase.

### Data-export / user-data-deletion endpoint (CCPA / GDPR)

- [ ] Auth'd. Rate-limited. Audit-logged.
- [ ] Export includes *only* the requester's data, confirmed via ownership filters in every query.
- [ ] Deletion is thorough: app_users, profiles, chat history, sessions, push subs, credits, support tickets. Document what's purged vs anonymized.
- [ ] Deletion is atomic where possible; idempotent if not.
