# Security

OWASP API Security Top 10 (2023) mapped to what you actually do, plus general rules.

## OWASP API Top 10 (2023)

### 1. BOLA — Broken Object Level Authorization (the #1 real bug)

Fix: **ownership in the `WHERE` clause**. The repository is where auth lives.

```sql
SELECT * FROM orders WHERE id = $1 AND user_id = $2
```

Not:
```sql
SELECT * FROM orders WHERE id = $1  -- then check ownership in app code
```

The DB enforces it. Code forgets. Kablan: every repository function under `src/server/modules/<m>/<m>.repository.ts` must scope to the session user.

### 2. Broken Authentication

- **Password hashing**: scrypt or argon2id with adequate cost. Never SHA-256. Never bcrypt cost < 12. Kablan uses scrypt via `src/lib/password.ts` — use it.
- **Rate-limit login** per user + per IP. Lock after N failures with an unlock path (email link, not CAPTCHA alone).
- **Timing-safe compare** for all secret comparison (`crypto.timingSafeEqual`). Naive `===` leaks length info.
- **Session tokens**: sufficient entropy (≥ 128 bits), httpOnly, Secure in prod, SameSite=Lax minimum.
- **Rotate on privilege change**: new session on password change, admin grant, etc.
- **Don't leak existence** via auth errors: "email or password incorrect" is one message, not two.

### 3. BOPLA — Broken Object Property Level Authorization

Fix: **explicit allowlist of fields** in request and response DTOs.

- Request: `OrderCreateSchema = z.object({ items: z.array(...), notes: z.string().optional() })` — unknown fields are stripped.
- Response: `toOrderDto(row)` picks only public fields. Never `return row` where `row` came from the DB.
- **Never** `Object.assign(user, req.body)` or spread unvalidated input into a persistence call.
- **Never** return `password_hash`, `session_token`, `reset_token`, internal flags, soft-delete markers, other tenants' data.

### 4. Unrestricted Resource Consumption

- Rate limits (per-user + per-IP).
- Pagination caps (server-enforced max `limit`).
- Payload size limits at the edge.
- Query complexity caps (GraphQL depth, list expansion).
- AI token caps (max input tokens, max output tokens, max tool calls).
- File upload caps (size, count, MIME allowlist).
- Per-user spend caps over time (see governor in [stability.md](./stability.md)).

### 5. BFLA — Broken Function Level Authorization

- Admin endpoints **re-verify the role every request** (not just in middleware). Kablan: `requireAdminSession()` DB-checks the role — use it; don't roll your own.
- Don't rely on the UI hiding a button. Clients can call any endpoint.
- Keep admin endpoints behind separate route trees (`/api/admin/...`) so you can't accidentally miss one.

### 6. Unrestricted Access to Sensitive Business Flows

Rate limit by **business operation**, not just URL:
- Password reset: max N per hour per account and per IP.
- Signup: max N per IP per hour (anti-automation).
- Code redemption / gift claim / invite accept: per-operation limits.
- Expensive AI operations: per-user concurrency cap.

CAPTCHA / proof-of-work when automation cost is low and abuse cost is high (new-account creation is the classic).

### 7. Security Misconfiguration

- **Security headers** at the edge: `Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`.
- Debug endpoints disabled in prod (no `/debug`, no stack-trace error pages).
- TLS everywhere — including internal service-to-service. Hard to get wrong; very bad when you do.
- Least-privilege IAM: the app's DB user is not a superuser. S3 bucket policies allow only what's needed.
- No default credentials. No credentials in URLs. No credentials in client code.

### 8. SSRF — Server-Side Request Forgery

**Never fetch a user-provided URL without an allowlist.** If you must:
1. Resolve the hostname yourself (don't let the HTTP client do it).
2. Validate the resolved IP against a **blocklist**: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`, IPv6 `::1`, `fc00::/7`, `fe80::/10`. Also cloud metadata endpoints (`169.254.169.254`).
3. Connect using the resolved IP and set `Host` header manually, OR re-resolve and validate each redirect hop. Many SSRF bugs come from redirect-to-localhost.
4. Disable redirects when you can; cap them and re-validate otherwise.
5. Timeout aggressively.

### 9. Improper Inventory Management

- Live catalog of endpoints, their versions, and their auth requirements. Regenerate from code if you can.
- Decommission old API versions with a sunset plan.
- Know what's public vs internal; internal endpoints should 404 externally.

### 10. Unsafe API Consumption

Third-party responses are **adversarial input**. Validate with the same rigor:
- Zod-parse every external API response before trusting a single field.
- Treat webhook payloads as untrusted until signature + schema verify.
- If an external API can inject URLs, HTML, or structured data you render, sanitize them.
- Version lock where possible; third-party contract changes are a failure mode.

## General rules

### Secrets

- **Env vars** (in a secret manager for prod). Never in code, never in logs, never in error messages.
- **Rotate** on any suspected leak. Assume public exposure = leaked — don't debate it.
- **Separate** per-env (prod secrets never in dev .env), per-service (no shared "god" key).
- **Scope** to minimum permissions; a webhook-signer key does not need DB write.

### CSRF

Cookie-auth'd state-mutating routes must enforce CSRF. Kablan does this via the Origin-vs-Host check in `src/proxy.ts`.

- Origin check + SameSite cookie is the baseline.
- For defense in depth, add a double-submit token or synchronized token.
- API clients using bearer tokens (not cookies) don't need CSRF — the browser won't attach the header automatically.

### Cryptographic hygiene

- `crypto.randomBytes(n)` / `crypto.randomUUID()` for tokens. Never `Math.random()`.
- `crypto.timingSafeEqual()` for any comparison of secrets (session ids, tokens, signatures, password hashes).
- HMAC for integrity (sessions, webhook signatures). Use SHA-256; rotate keys via a versioned key id.
- Don't invent crypto. Don't roll encryption. Use libsodium / Web Crypto / well-reviewed primitives.

### PII and logging

- **Redact before logging.** Allowlist what's safe to log, not denylist.
- Never log: passwords, tokens, session ids, full card numbers, SSNs, API keys, request bodies (without filtering), large JSON blobs verbatim.
- Always log: request id / correlation id, user id, route, status, duration.
- Structured JSON, one event per line. Let the log system search, don't grep.

### Logging auth events

Log and alert on:
- Login success / failure (with IP and user agent).
- Password change / reset.
- Session creation / destruction.
- Role change (user → admin is especially sensitive).
- Admin actions (creating users, deleting data, changing billing).
- 2FA enable / disable.

These are your forensics when something goes wrong.

### Supply chain (dependencies)

- **Pin** production dependencies (`package-lock.json` / `pnpm-lock.yaml` committed).
- **Audit** regularly (`pnpm audit`, `npm audit`, `osv-scanner`). Don't ignore; fix or document why.
- **Review** new deps: active maintenance, reasonable author, reasonable code size, known name. Typosquats are real.
- **Minimize**. Every dep is a liability. Prefer stdlib.
- **SBOM** for production (CycloneDX or SPDX) if your environment requires it.
- Dependabot / Renovate on a reasonable cadence (weekly, not daily; don't drown in noise).

### CORS

On authenticated APIs:
- Echo a specific origin from an allowlist. Never `*` with credentials.
- `Access-Control-Allow-Credentials: true` requires specific origin.
- Preflight cache: `Access-Control-Max-Age: 86400`.
- If your API is for your own front-end only, block cross-origin entirely.

### "Stop and surface" live security issues

If during any work you find:
- A secret in code / logs / git history.
- A missing ownership check on user data.
- A missing signature verification on webhooks.
- An SSRF-reachable fetch with user input.
- An admin endpoint without auth.

**Stop. Tell the user immediately.** Don't silently fix it; they need to know what existed in prod and for how long. Rotate credentials if exposed. Write an incident note.
