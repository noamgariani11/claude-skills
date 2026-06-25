# Concurrency & Idempotency

Every endpoint will be retried — by clients, by load balancers, by network hiccups, by users mashing buttons. Design for it.

## Idempotency keys (Stripe model)

Protocol:
1. Client generates a UUIDv4 per logical operation, sends `Idempotency-Key: <uuid>` header.
2. Server stores `(key, user_id, request_fingerprint, response_json, response_status, created_at)` in a dedicated table. Unique index on `(user_id, key)`. TTL ≥ 24h (some systems keep 7d).
3. On a repeat with the same key:
   - **Same fingerprint** (hash of body + path + method): return the cached response and status, byte-for-byte.
   - **Different fingerprint**: 409 Conflict. Key was reused with a different request.
4. Scope keys per user (or per tenant) — prevents cross-tenant collisions, and keeps the lookup index small.
5. Only `2xx` and `4xx` responses should be cached. Don't cache 5xx — the client should retry and hopefully succeed.

**Important**: the fingerprint must hash the *actual* request the user intended, not the server-augmented version. Strip server-injected fields (timestamps, session ids) before hashing.

**Alternative for creates**: a unique constraint on a natural key + `INSERT ... ON CONFLICT DO NOTHING RETURNING ...`. If `RETURNING` is empty, you know it was a duplicate; look up and return the existing row. Simpler than the full key protocol for single-table creates.

## Webhook idempotency

Webhook providers are at-least-once. You **will** get duplicates. You **will** get out-of-order events.

1. **Verify signature first.** No processing, no DB touch, until the signature passes. HMAC with a raw-body read — don't JSON-parse before verifying.
2. **Dedupe by the provider's event id** in a `processed_events(provider TEXT, event_id TEXT, processed_at timestamptz, PRIMARY KEY (provider, event_id))` table.
3. `INSERT ... ON CONFLICT DO NOTHING` before processing; if 0 rows inserted, ack (200) and skip.
4. When possible, do the event processing *and* the dedupe insert in the **same transaction** — so a mid-transaction crash doesn't leave a "processed" marker for a never-processed event.
5. **Out-of-order handling**: if event B depends on event A having arrived first, either check for A's effect in state or buffer B until A is processed. Providers like Stripe guarantee ordering within a resource but not globally.
6. **Timeouts**: return 200 fast. If work is slow, queue it and respond — but then the queued work must be independently idempotent.

Kablan: `src/app/api/stripe/webhook/route.ts` should follow this pattern. If it doesn't, that's a P1 finding.

## Retries

- **Exponential backoff with full jitter** — `sleep = random(0, min(cap, base * 2^attempt))`. Prevents thundering-herd retries from synchronized clients.
- Retry **only** idempotent operations, or operations protected by an idempotency key.
- **Classify errors**:
  - *Transient* (retry): network timeout, 502/503/504, connection reset, `serialization_failure`.
  - *Terminal* (don't retry — it'll just fail again): 400, 401, 403, 404, 409, 422.
  - *Rate limited* (retry with server hint): 429 + `Retry-After`.
- **Cap retries** (typically 3–5). After the cap, push to a dead-letter queue with full context for replay.
- **Client-side retries** for outbound calls; **server-side** idempotency to tolerate them.

## Concurrency primitives

- **Optimistic concurrency**: `UPDATE t SET col=..., version=version+1 WHERE id=? AND version=?`. Zero rows updated = conflict; return 409. Cheap, scales well, wrong only when contention is heavy.
- **Pessimistic**: `SELECT ... FOR UPDATE` inside a short transaction. Read-modify-write without races. Don't hold the lock long.
- **Advisory locks**: `pg_advisory_xact_lock(hash_key)` for cross-row critical sections that don't map cleanly to a single row. Auto-released at transaction end. Use the `_xact_` variant, not the session variant, unless you really mean it (session locks leak on connection reuse behind pgbouncer in transaction mode).
- **Queue workers**: `SELECT id FROM jobs WHERE status='pending' ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1`. Perfect for Postgres-backed queues — no blocking, no duplicate pickup.

## Transactional outbox (reliable async messaging)

The problem: you need to both (a) write to the DB and (b) publish an event. If you do (a) then (b) and (b) fails, you've got inconsistent state. 2PC across a DB and a message bus is fragile and slow.

Solution — **outbox pattern**:

```sql
CREATE TABLE outbox (
  id BIGSERIAL PRIMARY KEY,
  aggregate_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz,
  attempts INT NOT NULL DEFAULT 0
);
CREATE INDEX ON outbox (published_at) WHERE published_at IS NULL;
```

1. In the same transaction as your business write, `INSERT INTO outbox (...)`. Now the "I promised to publish this" record is atomic with the state change.
2. A separate worker polls `SELECT ... FROM outbox WHERE published_at IS NULL ORDER BY id FOR UPDATE SKIP LOCKED LIMIT N`, publishes to the downstream (bus / queue / webhook), then `UPDATE outbox SET published_at = now() WHERE id = ?`.
3. The downstream must tolerate duplicates (the worker can crash after publishing, before updating). Downstream consumers dedupe by `outbox.id` or a business key.
4. Add `attempts` and a max-attempts cap; after that, move to a `outbox_dead` table with the error for inspection.
5. For Postgres specifically, you can use `LISTEN/NOTIFY` or logical replication (Debezium-style CDC) to avoid polling.

When to use it: any time a DB write implies a downstream side effect (send email, publish to queue, call webhook) and you need "at-least-once, no lost events." Don't enable webhooks directly from a post-commit callback unless you've thought hard about crash recovery.

## Sagas (long-running multi-service workflows)

2PC across services is almost always the wrong answer. Instead:
- Break the workflow into **steps**, each a local transaction.
- Each step has a **compensating action** that undoes it.
- On failure at step N, run compensations for steps N-1 ... 1 in reverse.
- Orchestrated (central coordinator) or choreographed (each service emits events the next listens for). Orchestration is easier to reason about; choreography scales better.

Saga state lives in a DB table. The orchestrator is durable — it can resume after a crash and knows which step to retry.

Cross-reference: the outbox is often how saga steps communicate reliably.

## Cache stampede / thundering herd

- **Request coalescing / singleflight**: on cache miss, one worker computes; others wait and share the result.
- **Probabilistic early refresh**: refresh the cache before it expires with probability increasing as TTL nears zero. Smooths load.
- **Negative caching**: cache "not found" for short TTL (30s) — prevents repeated DB lookups for popular missing keys.
- **Jittered TTLs**: avoid whole-cohort simultaneous expiry. Add ±10% to every TTL.
