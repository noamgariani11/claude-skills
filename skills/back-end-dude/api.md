# API Design

Contracts first. The URL, the method, the status code, the request shape, the response shape, the error shape — settle those before writing code.

## The DTO / schema boundary

- Define the DTO (what goes in, what comes out) with Zod. Derive the TS type from the schema, never the other way around.
- Validate at the edge. Post-validation, `parse()` output is truth; no second-guessing inside the service layer.
- Request DTO ≠ DB row. Response DTO ≠ DB row. Convert explicitly (`toOrderDto(row)`). This is where BOPLA (OWASP #3) is enforced — an allowlist of fields, never a blanket serialize.

In Kablan: Zod schemas live in `src/lib/schemas.ts`. DTO converters live beside the repository in `src/server/modules/<module>/`.

## Status codes mean something

| Code | Meaning | Common confusion |
|---|---|---|
| 200 | Success with a body | Don't return 200 + `{ error: ... }` for failures — breaks every client |
| 201 | Created; include a `Location` header or the created resource | Use for POSTs that create |
| 202 | Accepted; async processing queued | Include a status URL |
| 204 | Success, no body (DELETE, some PATCHes) | Don't include a body |
| 400 | Malformed request (bad JSON, bad types) | Not for business-rule violations |
| 401 | Not authenticated | Don't leak "user exists" via auth errors |
| 403 | Authenticated but not allowed | BFLA / BOLA responses |
| 404 | Not found (or hide existence — be deliberate) | If leaking existence is a risk, return 404 instead of 403 |
| 409 | Conflict — unique violation, version mismatch, idempotency-key reuse with different body | |
| 410 | Gone — resource permanently removed | For deprecated endpoints |
| 422 | Semantically invalid (fields well-typed but violate business rule) | Many APIs conflate 400/422; pick one rule and stick with it |
| 429 | Rate limited | Always include `Retry-After` |
| 5xx | Our fault | Log it, page on it, don't leak internals in body |

## Error shape

Adopt RFC 7807 Problem Details or a consistent internal shape:

```json
{
  "code": "auth.invalid_credentials",
  "message": "Email or password is incorrect.",
  "details": { "field": "email" }
}
```

- **`code`** is a stable machine-readable string (`auth.invalid_credentials`, `billing.card_declined`). Never break this.
- **`message`** is human-readable and may change.
- **`details`** is structured and optional.
- Kablan's `src/lib/api.ts` helpers (`badRequest()`, `unauthorized()`, etc.) already produce a consistent shape — use them.

## Pagination

- **Cursor / keyset** for anything > ~10k rows: `SELECT ... WHERE (created_at, id) < ($cursor_ts, $cursor_id) ORDER BY created_at DESC, id DESC LIMIT 50`.
- **Offset** is a foot-gun at scale — inconsistent under concurrent writes, slow at large offsets. OK for small, slow-changing lists.
- Cap `limit` server-side (hard max, e.g. 100). Never trust client-provided limits.
- Response includes `next_cursor` (opaque string) and optionally `has_more`. Don't leak the cursor shape.

## Filtering / sorting

- **Allowlist the columns.** Map client names to column names server-side. Never interpolate user-provided sort keys into SQL.
- Compound indexes must cover the sort + filter combinations you advertise.

```ts
const SORT_ALLOWLIST = { createdAt: "created_at", updatedAt: "updated_at" } as const;
const column = SORT_ALLOWLIST[input.sortBy] ?? "created_at";
```

## Idempotency on writes

- Accept an `Idempotency-Key` header on every POST that creates/charges/emails.
- Server stores `(key, user_id, request_fingerprint, response_json, created_at)` with TTL ≥ 24h.
- See [concurrency.md](./concurrency.md) for the full protocol.

## Versioning

- **Evolve additively** — new optional fields, new endpoints.
- **Breaking change = new version** (`/v2/...` or `Accept: application/vnd.app.v2+json`). Don't break v1.
- **Deprecate** with a `Sunset` header (RFC 8594) and a `Deprecation` header. Log deprecated usage per client and reach out.
- Publish a changelog. Don't expect clients to notice.

## Rate limits

- **Per user + per IP**, with `Retry-After` on 429. Sliding window > fixed window for fairness under bursty load.
- **Business-flow limits** (OWASP API #6): cap by operation (password reset, signup, code redemption) not just by URL. One user can exhaust `/auth/reset` from many URLs if you rate-limit by URL alone.
- Kablan: `src/lib/rateLimit.ts` — use it; don't roll your own.
- Include limit state in response headers: `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`.

## Payload, query, and query-complexity caps

- Body size limit at the edge (Kablan: Next.js default ~1MB; tune per-route). Oversize → 413.
- Max query params, max array length inside JSON, max depth. Zod can enforce.
- For search/list endpoints: cap `limit`, cap filter cardinality, cap date range.

## CORS

- On authenticated APIs: **never** `Access-Control-Allow-Origin: *`. Echo a specific origin from an allowlist.
- `Access-Control-Allow-Credentials: true` requires a specific origin.
- Preflight cache: `Access-Control-Max-Age: 86400`.

## Example — Kablan-shaped route

```ts
// src/app/api/orders/[id]/route.ts
import { requireAuthenticatedSession } from "@/server/http/guards";
import { ok, badRequest, notFound } from "@/lib/api";
import { IdSchema } from "@/lib/schemas";
import { getOrderForUser, toOrderDto } from "@/server/modules/orders/orders.repository";

export const runtime = "nodejs";

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const session = await requireAuthenticatedSession();
  const parsed = IdSchema.safeParse((await ctx.params).id);
  if (!parsed.success) return badRequest("orders.invalid_id");

  const row = await getOrderForUser(parsed.data, session.userId);
  return row ? ok(toOrderDto(row)) : notFound("orders.not_found");
}
```

Keep the handler boring: guard → validate → service → response helper. ~10 lines.
