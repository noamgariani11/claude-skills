# Observability

If you can't see it in production, it doesn't exist. Build observability as you build features, not after an incident.

## Three pillars

### Logs

- **Structured JSON, one event per line.** One line = one event; no multi-line stack traces spread across lines.
- **Correlation id** propagated through every log, emitted at request boundary, carried into downstream calls (`X-Request-Id` or OpenTelemetry trace id).
- **Log levels**:
  - `DEBUG` — developer signal only; off in prod by default.
  - `INFO` — lifecycle events (request start/end, job complete, significant state transition). This is the default.
  - `WARN` — recoverable anomaly (retry fired, fallback used, degraded mode). Someone should look at these weekly.
  - `ERROR` — something failed that shouldn't; candidate for paging. Must include enough context to act.
- **Redact** — see [security.md](./security.md). Never log passwords, tokens, full card numbers, unbounded request bodies.
- **Context fields**: `request_id`, `user_id`, `route`, `method`, `status`, `duration_ms`, `version` (deploy sha). Omit noise.

### Metrics

Emit numbers, not messages, for things you monitor continuously.

- **RED** for services: **R**ate (req/s), **E**rrors (err/s or error ratio), **D**uration (p50, p95, p99, p999). Not averages — averages hide tail latency.
- **USE** for resources: **U**tilization (CPU, memory), **S**aturation (queue depth, pool waits), **E**rrors (disk errors, pool timeouts).
- **Per-route**, **per-tenant**, **per-downstream** breakdowns. Aggregate metrics hide the worst offenders.
- **Business metrics**: signups/min, payments/min, AI messages/min. An outage that drops signups to zero shows up here first.

### Traces

Distributed traces connect the dots that logs can't.

- **OpenTelemetry** is the standard; use the SDK for your runtime.
- Span every external call (DB query if > 10ms, HTTP call, AI call, cache roundtrip if interesting).
- Span the boundary of every request handler.
- Trace id in every log line — lets you jump from a log to the full trace.
- Sample — 100% traces are too expensive. 1-10% random sampling + 100% for errors is a good default.
- Propagate `traceparent` (W3C) through outbound headers so downstream services join the same trace.

## SLO / SLI — what do we actually promise?

- **SLI** (indicator): the metric you measure (API success rate, p95 latency, queue lag).
- **SLO** (objective): the target (99.9% success, p95 < 300ms).
- **Error budget** = 1 - SLO. If SLO is 99.9%, budget is 0.1% (~43 min/month). Burn rate drives whether you ship features or fix reliability this week.
- **1–3 SLIs per service**. More than that and you're drowning in green-yellow-red.
- **User-centric**: measure what the user cares about, not what's easy to instrument. "Did the order actually go through?" beats "was the DB up?".

## Alerting

- **Alert on symptoms, not causes.** "Users getting 5xx" pages someone; "CPU at 80%" is noise. The symptom is the SLO breach; the cause is what you investigate.
- **Alert only on actionable signals.** If no one knows what to do, it's not an alert — it's a dashboard.
- **Page only for the SLO burn** (multi-window, multi-burn-rate — see SRE Workbook Ch. 5). Avoid single-threshold alerts that flap.
- **Runbook every alert.** "Here's what this means, here's what to check first, here's what to roll back." Written once, used at 3am.

## What to log on a request

At minimum, for every request:
```
{
  "ts": "2026-04-18T15:23:01.123Z",
  "level": "INFO",
  "request_id": "...",
  "trace_id": "...",
  "user_id": "...",
  "route": "GET /api/orders/:id",
  "status": 200,
  "duration_ms": 42,
  "db_queries": 2,
  "db_time_ms": 18,
  "deploy_sha": "abc123"
}
```

One line, parseable, useful. Anything more (request body, headers) goes to a separate debug log with retention/redaction considered.

## Cost-per-request lens

For any endpoint, answer: what does one request cost?

- DB queries × average query cost (rows scanned, bytes returned).
- External API calls × their cost (AI tokens × model price, SaaS pricing per call).
- CPU time (function duration × platform cost).
- Bytes in/out of the edge.

Revisit after any endpoint gets popular. A 2 ms endpoint called 1000/s is 2 seconds of CPU/s — that's a core. A $0.01 AI call × 10k invocations/day is $100/day.

Flag cost regressions the same way you flag latency regressions. Endpoints that cost $X with no matching revenue are a problem.

## Debug runbook (how to use observability under fire)

1. **Find the request.** Use correlation id from user report, or filter logs by user/route/time.
2. **Read the trace.** Where was the time? DB, downstream, cache, CPU, network?
3. **Check metrics.** Is this a single bad request or a spike? p99 latency, error rate.
4. **Check deploys.** What changed recently? (Correlating incidents with deploy times is the #1 shortcut.)
5. **Check dependencies.** Upstream status pages. Our downstream health.
6. **Hypothesize, test, fix.** See `/investigate` skill for the full workflow.
