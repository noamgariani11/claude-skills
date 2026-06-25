# Stability Patterns

Nygard's "Release It!" plus a few modern additions. Every integration point is a failure point. These are the patterns that stop one failure from becoming an outage.

## Timeout

Every outbound call has an **explicit** timeout — connect + read. Default HTTP client timeouts are either infinite or absurdly long.

- Pick a number; document why. "Downstream p99 is 800ms, so timeout is 2s."
- Log every timeout with the target and elapsed time.
- Propagate the deadline downstream where possible (`X-Deadline` header or tracing baggage) so the callee can give up early.
- **Per-call**, not per-connection-pool. A single slow dependency should not stall unrelated work.

## Circuit breaker

States: **closed** (traffic flows), **open** (fail fast, short-circuit), **half-open** (probe with a single request).

- **Trip on error rate + latency**, not just errors. A consistently slow-but-200 dependency is killing you; catch it.
- **Half-open**: after the open interval, allow one request. Success → close. Failure → reset the open timer.
- **Fallback behavior**: cached value, default, empty list, 503 — explicit and documented.
- Per-dependency, not global. One dead dependency shouldn't trip the breaker for another.

## Bulkhead

Isolate resources by workload so one slow consumer can't starve the rest. "Ship with watertight compartments."

- Separate connection pools per downstream. The flaky upstream's pool fills up; the healthy one still works.
- Separate worker pools per priority (synchronous requests vs background jobs).
- Separate tenants / rate-limit buckets for noisy-neighbor isolation.

## Shed load / backpressure

When you're overwhelmed, reject fast (429) rather than accept-and-die.

- Signals: queue depth, p95 latency, in-flight request count, open file descriptors.
- Shed load from the *cheapest* work first (non-essential endpoints, anonymous users) and protect the money path.
- Backpressure propagates — when you 429 a client, the client should slow down, not retry immediately. `Retry-After` is a contract.

## Fail fast

Validate preconditions cheaply and early. Long operations with late failures waste resources and confuse users.

- Zod parse before any DB call.
- Ownership check before the expensive join.
- Budget check before starting a paid-for operation.

## Steady state

No unbounded anything in production.

- Bounded disk (log rotation, temp cleanup, quota per tenant).
- Bounded memory (LRU caches with size caps).
- Bounded DB growth (retention policies, partitioning, archival).
- Bounded queues (max depth, DLQ on overflow).
- Bounded open connections (pool caps, idle timeouts).

Run the system for weeks in load test. Find what grows.

## Governor (cost cap)

Cap runaway cost. Defense-in-depth against accidental DoS-by-your-own-code.

- Max rows per query (`LIMIT 100` always; 500 at most with a cursor).
- Max tokens per AI call (Kablan: 4096 for chat; set per route).
- Max retries per operation.
- Max message size (body parser limit).
- Max fan-out (one incoming request triggers at most N downstream calls).
- Max per-user spend per minute/hour/day — stop the runaway before you get the bill.

## Graceful shutdown

On SIGTERM:

1. Stop accepting new connections (remove from load balancer, fail health check).
2. Let in-flight requests finish (drain timeout, e.g., 30s).
3. Flush buffered logs / metrics.
4. Close DB connections cleanly.
5. Exit.

On Vercel/Fluid Compute: the platform provides drain signals; use `waitUntil` for tail work. Don't kick off a long task during a request without a strategy for what happens when the instance shuts down.

## Feature flags and kill switches

Every risky feature ships behind a flag. Every integration has a kill switch.

- **Feature flag**: on/off (or gradual rollout %) per feature. Change at runtime, no deploy.
- **Kill switch**: "disable this integration / endpoint / experiment right now." A single boolean you can flip when an incident is in progress.
- Flags are evaluated *cheaply* and cached locally (stale-by-a-few-seconds is fine).
- Feature-flag churn is a code smell — remove flags after rollout completes. Flags should be a migration tool, not a permanent architecture.
- Document who owns each flag and the criteria for removal.

Kablan: no dedicated flag system yet — if you need one, put it in `app_users.flags` JSONB or a `feature_flags` table with a 30s-cached lookup; don't reach for LaunchDarkly until the complexity warrants it.

## Rolling deploys and rollback

- Every deploy is rollback-able in < 1 minute.
- Migration state must be compatible with old + new code (expand/contract — see [database.md](./database.md)).
- Watch error rate and latency for a defined window post-deploy; auto-rollback on regression.
- Canary/progressive rollout for risky changes (10% → 50% → 100%).

## Chaos / failure injection (worth it when the system matters)

- Kill a pod in staging; verify everything recovers.
- Inject a 5s latency on the DB in staging; verify timeouts/circuit breakers fire.
- Black-hole a dependency; verify fallback behavior.

Not for every service. Worth it for anything that pages someone at 3am.
