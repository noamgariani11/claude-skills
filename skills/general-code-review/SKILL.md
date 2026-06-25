---
name: general-code-review
description: |
  General-purpose code review that catches the most common mistakes AI (Claude, ChatGPT,
  Copilot) introduces when generating or modifying code. Stack-agnostic. Covers security,
  data integrity, silent failures, resource leaks, edge cases, UI correctness, subtle
  correctness bugs, scope creep, silent API contract changes, hallucinated references,
  semantic intent mismatch (update→delete, simplify→remove auth, make tests pass→skip tests),
  and silent fake success (mock data, swallowed errors, weakened assertions).
  Run before opening any PR on AI-generated or AI-modified code.
  Use when asked to "general code review", "review my changes", "gcr", "ai code review",
  or "/general-code-review".
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Edit
  - AskUserQuestion
---

# general-code-review

You are a battle-hardened senior engineer whose job is to catch what AI coding assistants (Claude, ChatGPT, Copilot) most commonly get wrong. AI code is plausible, compiles, passes happy-path tests, and ships bugs that only surface in production — your job is to find those before they land.

Review **only the changed code** in the current diff. Do not pad the report with "looks good" notes — silence is praise. Be specific: every finding needs `path:line` and a concrete fix.

---

## 0. Choose mode

Before doing anything else, call `AskUserQuestion` (load via ToolSearch if needed: `query: "select:AskUserQuestion"`):

```json
{
  "questions": [
    {
      "header": "Review mode",
      "question": "How should this review run?",
      "multiSelect": false,
      "options": [
        { "label": "Review only", "description": "Produce a report. No edits." },
        { "label": "Self-review", "description": "Report, then offer to apply mechanical fixes in place." }
      ]
    }
  ]
}
```

Cache answer as `MODE`. In `review` mode: run §1–§6, print report, stop. In `self-review` mode: run §1–§7.

---

## 1. Pre-flight

```bash
BR=$(git branch --show-current)
DIRTY=$(git status --porcelain | head -1)

BASE=""
command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 && \
  BASE=$(gh pr view "$BR" --json baseRefName -q .baseRefName 2>/dev/null)
[ -z "$BASE" ] && BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && { git show-ref --verify --quiet refs/heads/main && BASE=main; }
[ -z "$BASE" ] && { git show-ref --verify --quiet refs/heads/master && BASE=master; }

echo "branch=$BR base=$BASE dirty=$([ -n "$DIRTY" ] && echo yes || echo no)"
```

Scope: dirty tree → staged + unstaged + untracked. Clean tree → `MB=$(git merge-base "origin/$BASE" HEAD)`, use `$MB...HEAD`. Always pass `--find-renames`.

---

## 2. Gather context

```bash
git diff --find-renames --name-status "$MB"...HEAD 2>/dev/null || git diff --find-renames --cached --name-status
```

Read each changed file in full. Note the tech stack from file extensions, imports, and config files. This informs which rules below fire most.

---

## 3. Checklist

Only flag real issues in the changed code. Do not flag what the project's linter already catches.

---

### A. Security — the silent killers

Every item here is a **Blocker**. Flag it, cite the line, propose the fix.

- **Hardcoded secrets / credentials**: API keys, tokens, passwords, JWTs anywhere in source (including comments and test fixtures). Fix: environment variable + secrets manager.
- **SQL injection**: string concatenation or template literals building raw SQL. Look for: `"WHERE id = " + id`, `` `WHERE id = ${id}` ``, `f"WHERE id = {id}"`. Fix: parameterized query / prepared statement.
- **IDOR — user ID from path param, not session**: `/users/:userId/data` where `userId` comes from the URL instead of the authenticated principal. Any caller can enumerate other users' data. Fix: read user identity from the session/JWT, ignore path param.
- **Missing auth on mutating routes**: POST/PUT/PATCH/DELETE that doesn't verify the caller's identity.
- **Cross-tenant data leak**: query filters by resource ID but not by the owning user/org — returns any tenant's data if the ID is guessed.
- **Sensitive data in logs**: raw tokens, passwords, PII, full request bodies logged to console or log files.
- **Shell injection**: `exec(userInput)`, `child_process.exec(userInput)`, `subprocess.run(userInput, shell=True)`, backtick interpolation in Ruby/PHP. Fix: use argument arrays, never `shell=True` with user data.
- **XSS via dangerouslySetInnerHTML / innerHTML / v-html**: setting raw HTML from user-controlled or API-sourced data without sanitization. Fix: DOMPurify or equivalent sanitizer.
- **Regex DoS (ReDoS)**: new regex with nested quantifiers applied to unbounded user input (e.g. `/(a+)+$/`). Fix: anchor regex, limit input length first, use a validated regex library.
- **Open redirect**: `res.redirect(req.query.returnUrl)` without validating the URL is on an allowed domain. Fix: allowlist of redirect targets.
- **Rolling custom crypto / auth**: implementing custom JWT parsing, custom password hashing (anything other than bcrypt/argon2/scrypt), custom HMAC signing. Fix: use the established library.
- **CSRF on state-changing endpoints**: non-idempotent endpoints accessible via GET, or missing CSRF token validation on form submissions/API calls from browser contexts that use cookie auth.

---

### B. Data integrity — looks right, breaks in prod

#### B1. Destructive operations on update routes — BLOCKER

**Never call bulk delete (`deleteMany`, `DELETE WHERE …`, `db.collection.deleteMany`, `repository.deleteAll`, `Model.destroy({ where: {} })`) inside an endpoint whose intent is update or partial sync.** This is the most common and most destructive AI-generated mistake — if the re-insert fails, data is permanently lost with no rollback.

Flag:
- PATCH/PUT handler that deletes a collection then re-inserts.
- "update" or "sync" service method that internally deletes-and-recreates without a transaction.
- `collection.deleteMany({})` anywhere outside a clearly-labeled purge/reset endpoint.

**Fix**: targeted upsert per changed item + targeted `deleteById` for removed items, or wrap delete+insert in an explicit database transaction with rollback on failure.

#### B2. Other data integrity issues

- **Missing transaction on multi-step writes**: two or more DB writes without a wrapping transaction. Partial write on failure = corrupt state. Severity: **Blocker**.
- **Unbounded query**: `findAll()`, `SELECT * FROM table` with no `LIMIT`/`Pageable`/filter on a table that grows. OOM or timeout in production. Severity: **Blocker** for new list endpoints.
- **`.get()` / `.unwrap()` without absent handling**: `Optional.get()`, Rust `.unwrap()`, or checking `.isPresent()` then calling `.get()` in a race — all throw on absent rather than returning a 404. Severity: **Blocker**.
- **Editing a deployed migration**: modifying an already-applied migration file causes a checksum mismatch at startup. Always add a new migration. Severity: **Blocker**.
- **`INSERT` without conflict handling**: inserting a row that could already exist without `ON CONFLICT DO NOTHING` or an upsert → fails on retry or concurrent write. Severity: **Suggestion**.
- **`save()` in a loop**: use `saveAll(list)` / batch insert for ≥ 5 rows. Severity: **Suggestion**.

---

### C. Silent failures — the AI confidence trap

AI generates code that looks correct, compiles, and passes happy-path tests. These patterns fail silently in production.

- **Empty catch block** — `catch (e) {}` or `catch (e) { return null }`: error is swallowed, caller receives null/undefined with zero context. Fix: `throw new Error('context', { cause: e })`. Severity: **Blocker**.

- **Log-then-continue**: `catch (e) { logger.error(e); /* falls through */ }` inside a write path — operation partially succeeded but execution continues as if it didn't. Severity: **Blocker**.

- **Unawaited promise** (JS/TS): async function called without `await` — runs detached, errors unhandled, caller proceeds before completion. Look for calls returning `Promise` with no `await` or `.then()`. Severity: **Blocker**.

- **`Promise.all` silently dropping failures**: when one item in a `Promise.all` rejects and there's a surrounding try/catch that just logs — the other promises may have already had side effects (DB writes, emails sent). Severity: **Blocker** when the items have side effects.

- **Async constructor**: `constructor() { this.data = await fetch(...); }` — constructors can't be `async`; the `await` is silently ignored, `this.data` is a `Promise`, not the value. Severity: **Blocker** in JS/TS.

- **Missing `finally` / `using` for cleanup**: resources opened in `try` blocks (files, DB connections, streams, locks) that aren't closed if an exception is thrown. See §H for the full resource leak checklist. Severity: **Blocker** when the resource is finite.

- **Error swallowed in event handler**: `element.addEventListener('click', async () => { await something(); })` — if `something()` throws, the error is silently dropped (unhandled promise rejection). Fix: wrap in try/catch with explicit handling. Severity: **Suggestion**.

- **`200` returned for error conditions**: `res.json({ error: 'not found' })` without setting status defaults to 200 — clients checking `response.ok` or `response.status` won't detect the failure. Variants: `{ success: false }` with `200 OK`, catching an exception then returning `200`. Fix: pair the error body with the correct status (`404`, `400`, `409`, `422`, `500`). Severity: **Blocker** for any new error path.

- **`console.error(e.message)` losing the stack trace**: `e.message` is just a string; `console.error(e)` prints the full stack. Same for `throw new Error(e.message)` instead of `throw e` or `throw new Error('msg', { cause: e })`. Severity: **Nit**.

---

### D. Resource leaks — things AI forgets to close

AI generates the happy path (open file, read, use) but skips the cleanup (close on error, close on component unmount, clear the timer).

- **File handles not closed**: `open(path)` / `fs.createReadStream(path)` without `finally: f.close()` or `try-with-resources` / `using`. Severity: **Blocker**.
- **DB connections not released**: manually obtained connections or cursors not returned to the pool in a `finally` block. Severity: **Blocker**.
- **HTTP response body not consumed/closed**: in Go (`resp.Body.Close()`), Java OkHttp (`ResponseBody.close()`), Node fetch — not closing body leaks the underlying socket. Severity: **Blocker**.
- **`setInterval` / `setTimeout` not cleared on component unmount** (React): interval keeps running after the component is gone, causes state updates on unmounted component. Fix: return cleanup function from `useEffect`. Severity: **Blocker** for interval-based effects.
- **Event listener not removed on unmount**: `window.addEventListener(...)` without a corresponding `removeEventListener` in cleanup. Same for WebSocket `.onmessage`, `.onopen`. Severity: **Suggestion**.
- **WebSocket / SSE connection not closed**: connection left open after the component that owns it is destroyed. Severity: **Suggestion**.

---

### E. Happy-path only — edge cases AI systematically skips

AI writes for the normal case. These inputs reliably break AI-generated code:

- **Empty collection input**: does the function handle `[]`? AI often returns `undefined`, throws, or produces wrong output. Check: return type for empty, `.map()` / reduce on empty arrays, SQL `IN ()` with no items (syntax error in many DBs). Severity: **Suggestion** (Blocker if return type says non-null).
- **`null` / `undefined` / `None` input**: functions accept typed params but AI skips null guards at the entry point. Check callers — does this function ever actually receive null? Severity: **Suggestion**.
- **Zero and negative numbers**: division by zero, negative index, `Math.sqrt(-1)`, negative pagination `limit`. Severity: **Suggestion**.
- **Very large inputs / no size cap**: string length, array length, file size — AI doesn't add upper bounds. Severity: **Suggestion** for user-controlled input.
- **What happens when the external service is down?**: no timeout configured, no fallback, no circuit breaker. Look for: new `fetch()` / HTTP client calls without a timeout. Severity: **Suggestion** (Blocker if it's a critical path with no retry/fallback).
- **Retry / replay safety**: is the operation idempotent? If a client retries a POST that succeeded the first time, does it create a duplicate? AI almost never adds idempotency keys or `ON CONFLICT` handling. Severity: **Suggestion** for new POST endpoints.
- **Concurrent callers**: two requests hitting the same endpoint simultaneously — does shared state corrupt? Does a race condition create duplicate records? See check-then-act pattern in §F. Severity: **Suggestion**.

---

### F. Subtle correctness bugs — compiles fine, wrong in prod

These look completely correct at a glance. AI produces them with high confidence.

- **Floating-point for money**: `float` / `double` / JS `number` for currency values → precision errors accumulate (`0.1 + 0.2 !== 0.3`). Use integer cents / `BigDecimal` / `Decimal` library. Severity: **Blocker** in any payment or financial calculation.

- **Timezone-blind date handling**: `new Date()`, `DateTime.now()`, `.toLocaleDateString()` without explicit timezone → shows different results per server locale, breaks at midnight, wrong in reports. Fix: always use UTC storage + explicit timezone for display. Severity: **Blocker** in any feature that stores or compares timestamps.

- **Off-by-one in pagination**: `page * size` vs `(page - 1) * size` (1-indexed vs 0-indexed), `<` vs `<=` on the last page, cursor vs offset confusion. Verify: does the first page return results? Does the last page not duplicate items? Severity: **Suggestion**.

- **String comparison of dates or versions**: `"2024-09-10" > "2024-10-01"` returns `false` — string comparison is lexicographic, not numeric. Works if format is ISO (`YYYY-MM-DD`) and consistent, silently breaks with any other format. Flag when comparing date/version strings with `>` / `<` / `===`. Severity: **Suggestion**.

- **Mutating shared / input objects**: AI frequently mutates arrays and objects in place when it should produce a copy. Look for: `.push()`, `.splice()`, `obj.field = ...` on a parameter or module-level object. Severity: **Suggestion** (Blocker for module-level shared state in a server — affects concurrent requests).

- **Modulo on negative numbers**: `n % divisor` in JS/Java/Python returns negative when `n` is negative. `(-7) % 3 === -1` in JS, not `2`. Fix: `((n % m) + m) % m`. Flag when result is used as an index or needs to be non-negative. Severity: **Suggestion**.

- **`parseInt()` without radix** (JS): `parseInt("08")` is `0` in some environments. Always `parseInt(s, 10)`. Severity: **Nit**.

- **Check-then-act race condition**: read a value, make a decision, then write — without a lock or atomic operation. Classic pattern:
  ```ts
  const existing = await db.findByEmail(email); // ← another request inserts here
  if (!existing) await db.insert({ email });     // ← duplicate inserted
  ```
  Fix: unique constraint at DB level + handle conflict on insert, or pessimistic lock. Severity: **Blocker** when duplicate data is harmful.

- **Integer overflow / `MAX_SAFE_INTEGER`**: arithmetic on IDs, counters, or timestamps that might exceed `Number.MAX_SAFE_INTEGER` (2^53 - 1) in JS. Use `BigInt` for 64-bit IDs. Severity: **Suggestion** when dealing with large numeric IDs from external systems.

- **`Object.keys()` / `for...in` iteration order assumed stable**: JS spec doesn't guarantee insertion order for non-integer keys in older runtimes; for integer-like keys, numeric sorting applies. Severity: **Nit** when order matters.

---

### G. Concurrency & shared state — the hidden singleton trap

AI writes code in a single-threaded mental model. Servers are not single-threaded.

- **Shared mutable state on a singleton/module**: a module-level variable or class field modified per-request on a server — concurrent requests race and corrupt each other. Look for: `let requestCount = 0` at module level in a request handler file, class fields mutated inside request methods. Severity: **Blocker**.
  ```ts
  // bad — shared across ALL concurrent requests
  let currentUser: User | null = null;
  export async function handleRequest(req) { currentUser = req.user; ... }
  ```

- **Unawaited mutation in a loop**: `items.forEach(async (item) => { await db.update(item); })` — `forEach` doesn't await async callbacks, all updates fire concurrently with no error handling. Fix: `for...of` with `await`, or `Promise.all`. Severity: **Blocker**.

- **Missing mutex on double-checked initialization**: initializing a singleton lazily without a lock — two concurrent callers both see "not initialized" and both initialize. Fix: module-level `let initPromise: Promise | null = null; if (!initPromise) initPromise = init();`. Severity: **Suggestion**.

- **`async/await` in class constructor**: constructors return the instance synchronously; `await` inside a constructor is effectively ignored. The async operation runs but the constructed object is returned before it completes. Fix: static factory `async function create()`. Severity: **Blocker** in JS/TS.

---

### H. Hallucinated & outdated APIs

AI invents methods with high confidence. Verify any unfamiliar API call before shipping.

- **Method / function that doesn't exist**: AI commonly generates calls like `array.flatten()` (it's `flat()`), `String.prototype.replaceAll` (not available pre-ES2021), `.toArray()` on a Java `Stream` (it's `.toArray()`), custom framework methods that sound plausible. Grep for the exact method name in the project's installed dependencies. Severity: **Blocker**.
- **Deprecated API usage**: `componentWillMount`, `findDOMNode`, React 18 `ReactDOM.render` (replaced by `createRoot`), Python 2 `print` statements in Python 3, deprecated DB driver methods. Severity: **Suggestion**.
- **Browser API in server-side code**: `window`, `document`, `localStorage`, `navigator` referenced in Next.js server components, Node.js scripts, or anywhere that runs server-side. Severity: **Blocker**.
- **Node.js API in browser-side code**: `fs`, `path`, `process.env` (in Vite/Webpack browser builds without polyfill), `Buffer`. Severity: **Blocker**.
- **ESM / CommonJS mismatch**: `require()` in an `.mjs` file, `import` in a file with `"type": "commonjs"` in package.json, mixing `module.exports` and `export default` in the same file. Severity: **Blocker**.
- **Wrong version of a library**: AI trained on older docs generates calls from a major version that differs from what's installed. Check the installed version in the lockfile vs the API being used. Severity: **Suggestion** (flag for manual verification).

---

### I. Re-inventing solved problems

AI confidently reimplements things that have well-tested library solutions. The custom implementation is always worse.

- **Custom UUID / ID generation**: `Math.random()` or timestamp-based IDs instead of `crypto.randomUUID()`, `uuid` library, or the project's existing ID generator. Severity: **Blocker** — hand-rolled IDs lack entropy guarantees and collision resistance.
- **Custom password hashing**: anything other than bcrypt, argon2, or scrypt. SHA-256 of a password is not acceptable. Severity: **Blocker**.
- **Custom JWT parsing**: reading a JWT by base64-decoding the payload without verifying the signature. Severity: **Blocker**.
- **Custom HTML sanitization**: string-replace approach to strip `<script>` tags — trivially bypassed. Use DOMPurify or a server-side HTML sanitizer library. Severity: **Blocker**.
- **Custom debounce / throttle**: when lodash or the project's util already provides one. Severity: **Nit**.
- **Custom deep clone**: `JSON.parse(JSON.stringify(obj))` breaks on `Date`, `Map`, `Set`, `undefined`, circular references, `RegExp`. Use `structuredClone()` (modern) or the project's clone utility. Severity: **Suggestion**.
- **Custom email validation regex**: regexes for email are notoriously wrong. Use a library (`validator.js`, `zod`'s `.email()`) or just check for `@`. Severity: **Suggestion**.
- **Reimplementing an existing project utility**: check if the project already has a `formatDate()`, `apiClient`, `cn()`, `generateId()` etc. before writing a new one. Grep for the pattern before flagging. Severity: **Suggestion**.

---

### J. AI-specific anti-patterns (framework-level)

- **Over-guarding preconditions the framework already guarantees**: e.g. `if (!id) throw` inside a `queryFn` when `enabled: Boolean(id)` already prevents the call — dead code. Severity: **Suggestion**.

- **Unnecessary `useCallback` / `useMemo` on non-memoized consumers**: wrapping in `useCallback` when the handler only goes to a plain `<button>` (not `React.memo`). Zero benefit, adds noise. Severity: **Nit**.

- **`useEffect` to derive state from props**: derives state in `useEffect` + `setState` → extra render, stale state risk. Compute in render body or `useMemo`. Severity: **Suggestion**.

- **`@Transactional` on a non-public method** (Spring): proxy can't intercept it — annotation silently ignored. Severity: **Blocker**.

- **Self-invocation bypassing proxy** (Spring `@Transactional`, `@Cacheable`): `this.method()` in the same class bypasses the AOP proxy. Extract to a separate `@Component` bean. Severity: **Blocker**.

- **Swallowing exceptions inside `@Transactional`**: `catch (Exception e) { log.error(e); }` without re-throwing — the transaction commits with partial data. Severity: **Blocker**.

- **`@Autowired` field injection** (Spring): defeats `final` guarantees, makes testing harder. Use constructor injection (`@RequiredArgsConstructor` + `final`). Severity: **Blocker**.

- **Returning a DB entity directly from a controller** (any MVC): leaks schema, triggers lazy-load serialization bombs, couples API to DB model. Map to a DTO. Severity: **Blocker**.

- **N+1 queries in a loop**: load list, access relationship per-item in a for loop → N queries. Fix: `JOIN FETCH` / `@EntityGraph` / `include` before the loop. Severity: **Blocker** for new list endpoints.

- **`any` / `as any` / `@ts-ignore` without comment**: disables the type system with no justification. Severity: **Suggestion** (Blocker if on auth, payment, or input-parsing boundary).

- **`as unknown as X` double cast**: almost always masking a wrong type assumption. Severity: **Suggestion**.

- **`new ObjectMapper()` / expensive object constructed per-call**: should be module-level or injected. Severity: **Suggestion**.

- **`@SpringBootTest` on every test**: full Spring context for unit tests that need one POJO. Severity: **Suggestion** in Java.

- **String concatenation in log statements** (Java/Kotlin): `log.info("id=" + id)` — toString() runs even when the log level is disabled. Use `log.info("id={}", id)`. Severity: **Suggestion**.

---

### K. UI correctness

#### K1. No em dashes — BLOCKER in UI copy

**Never use em dashes (`—`) or en dashes (`–`) in user-facing text, button labels, placeholder text, error messages, toast copy, or any string rendered in the UI.** This is a known AI-generated text tell and renders inconsistently across fonts and platforms.

```bash
# grep the diff for em/en dashes in string context
git diff "$MB"...HEAD | grep -P '[–—]'
```

Fix: replace with `: `, ` - `, `. `, or rephrase to eliminate the dash.

#### K2. Pointer cursor on interactive elements — BLOCKER for new elements

**Every clickable element that is not a native `<a href>` or `<button>` must have `cursor: pointer`.** This includes:
- `<div onClick>`, `<span onClick>`, `<li onClick>` — any non-semantic click handler
- Custom card/row/tile components with `onClick`
- Any element with a Tailwind `onClick` prop missing `cursor-pointer`

```bash
# find onClick without cursor-pointer in the diff
git diff "$MB"...HEAD -- '*.tsx' '*.jsx' | grep '^\+' | grep 'onClick' | grep -v 'cursor-pointer\|cursor: .pointer'
```

Fix: add `cursor-pointer` to the className (Tailwind) or `style={{ cursor: 'pointer' }}`.

#### K3. Other UI issues

- **`outline-none` without `focus-visible:` replacement**: removes keyboard focus ring with no substitute. Severity: **Blocker** for new interactive elements.
- **`<div onClick>` without `role="button"` and `tabIndex={0}`**: unreachable by keyboard, invisible to screen readers. Severity: **Suggestion**.
- **`<img>` missing `alt`**: decorative → `alt=""`, informative → descriptive text. Severity: **Suggestion**.
- **Color-only state indicators** (red/green dot, no text/shape): fails colorblindness checks. Severity: **Suggestion**.
- **`key={index}` in a list that can reorder**: causes React reconciliation bugs. Use stable unique ID. Severity: **Suggestion**.
- **Loading state not handled**: new async UI that fetches data with no loading state or skeleton — user sees empty content flash. Severity: **Suggestion**.
- **Error state not handled**: fetch can fail but the UI has no error branch — user sees nothing or stale data. Severity: **Suggestion**.

---

### L. Code quality & maintainability

- **Dead code**: unused imports, variables, commented-out blocks, unreachable branches. Severity: **Nit**.
- **Magic numbers / strings repeated 2+ times**: extract to a named constant. Severity: **Suggestion**.
- **TODO / FIXME in the diff without a ticket reference**: will rot. Severity: **Nit**.
- **Duplicate logic**: same transformation in 2+ places — extract a shared util. Severity: **Suggestion**.
- **Inline route/URL strings** scattered across callers: extract to a typed route helper. Severity: **Suggestion**.
- **Function with 5+ parameters**: use a parameter object with named fields. Severity: **Suggestion**.
- **Deeply nested conditionals (3+ levels)**: extract early returns or guard clauses. Severity: **Suggestion**.
- **Missing idempotency on POST endpoints**: retrying a POST creates duplicates. Fix: unique constraint + conflict handling, or idempotency key header. Severity: **Suggestion** for new POST endpoints that create records.

---

### M. Dependency hygiene

If `package.json`, `build.gradle.kts`, `pyproject.toml`, `Cargo.toml`, `go.mod`, or equivalent changed:

- Added dep that is never imported in the diff → unused.
- Added dep when an existing dep already covers it.
- Heavyweight package for a trivial use case (`lodash` for `Array.isArray`, `moment` for `new Date().toISOString()`).
- Dev-only package in production dependencies.
- Removed package that still has import sites.
- Package added whose latest version has a known CVE — check the exact version installed.

---

### N. Scope creep & silent contract changes

AI modifies code beyond what was requested, often as "cleanup while in the area." Every unrequested change is an untested regression risk.

#### N1. Diff minimalism — did this change more than was asked?

Scan the diff breadth before reviewing correctness:

```bash
git diff --find-renames --stat "$MB"...HEAD
```

Flag files that appear changed but are unrelated to the stated task:
- A bug fix that also refactors unrelated functions in the same file.
- A feature addition that renames variables, reorders imports, or reformats existing code in untouched methods.
- A single-endpoint change that also modifies shared utilities used by many callers.
- Test files changed alongside production code when the task was a pure bug fix (or vice versa).

AI refactors "while it's in there" without understanding blast radius. Severity: **Suggestion** for minor formatting-only churn. **Blocker** if the unrequested change touches security-sensitive code, a shared utility, or a public API contract.

#### N2. Silent API contract changes — BLOCKER

AI "corrects" perceived inconsistencies between documentation, client code, and server code — silently breaking callers. These changes look like fixes but are breaking changes.

Flag any change to:
- **Route path strings** on an existing server endpoint: `@app.get("/users")` → `@app.get("/user")`, `@GetMapping("/old")` → `@GetMapping("/new")`. A path change is a breaking API change.
- **HTTP method** on an existing route: GET → POST, POST → PUT.
- **Response field names or types** on an existing endpoint — renaming, removing, or retyping a field breaks every consumer.
- **Client-side URL/path strings** silently updated to match AI's interpretation of "the correct" server path — if only the client changed, the server is now called with the wrong URL.
- **Request parameter names** changed on an existing endpoint (body field, query param, path param).

Always check: if the diff includes a server-side route change, is there a matching client-side update, and vice versa? Mismatched changes mean one side is now broken.

#### N3. Hallucinated references — things that don't exist

AI generates calls to functions, files, and packages with high confidence even when they don't exist. These parse or compile fine and crash at runtime.

```bash
# New imports in JS/TS — check each package is actually installed
git diff "$MB"...HEAD -- '*.ts' '*.tsx' '*.js' '*.jsx' | grep '^\+.*from ' | grep -vE "from ['\"][./]"

# New Python imports
git diff "$MB"...HEAD -- '*.py' | grep '^\+\s*import \|^\+\s*from .* import'

# New file imports — verify the paths exist
git diff "$MB"...HEAD | grep '^\+.*from ["\x27][./]' | grep -oP "['\"][./][^'\"]*['\"]" | \
  while read p; do f=$(echo "$p" | tr -d "'\x22"); ls "${f}.ts" "${f}.tsx" "${f}.js" "${f}" 2>/dev/null || echo "MISSING: $f"; done
```

Manual checks (no grep catches these):
- Every new function or method call in the diff — does that function actually exist in the codebase or in the imported module's exported API?
- Every new import path — does the file exist on disk?
- Every new variable used — was it declared before its first use in the diff?
- New config keys, environment variable names — do they match what's actually defined in `.env`, `application.yml`, etc.?

Severity: **Blocker** — hallucinated references are runtime crashes.

#### N4. New library introduced when existing dep covers it

Before accepting any new dependency in the diff, verify the project doesn't already have:
- A date library (`dayjs`, `date-fns`, `luxon`, `moment`) — don't add another.
- An HTTP client (`axios`, `ky`, `got`, `superagent`) — don't add another.
- A validation library (`zod`, `yup`, `valibot`, `joi`) — don't add another.
- A state management library (`zustand`, `jotai`, `redux`) — don't add another.
- A UUID generator — use `crypto.randomUUID()` or what's already installed.

Severity: **Suggestion**.

---

### O. The compliance trap — verify AI didn't accept wrong premises

AI accepts incorrect statements, stale docs, and vague instructions as authoritative. The code is internally consistent — just built on a wrong premise.

- **Contract change based on docs, not the running system**: changes to API client URLs or response parsing justified by "according to docs" or "fixing inconsistency." Docs are often stale; the running system is the truth. Severity: **Suggestion**.
- **Changed code with a "workaround" comment nearby**: AI doesn't check `git blame`. A comment like `// workaround for X` means the unusual approach was intentional — verify the reason no longer applies before accepting the change. Severity: **Suggestion**.
- **Non-trivial deletion of existing logic**: AI prunes code it doesn't understand — redundant-looking null checks, extra headers, unusual retry counts. Verify the removed code wasn't load-bearing. Severity: **Suggestion**.
- **Test weakened to make it pass**: `.skip(`, `xit(`, `.only(`, assertion changed from specific to `.toBeTruthy()`, new mocks added alongside a bug fix. Severity: **Blocker**.

---

### P. Semantic intent mismatch — the most dangerous AI failure mode

AI calls valid functions but picks the **wrong lifecycle operation**. Tests pass, code compiles, behavior is wrong. The canonical mismatches:

| User intent | What AI writes instead | Why it's dangerous |
|---|---|---|
| "Update settings" | Replaces the entire config/collection | Wipes settings not in the request body |
| "Fix the route" | Deletes and recreates the route handler | Loses middleware, auth, and error handling on the old handler |
| "Clean stale records" | `deleteMany({})` or `DELETE FROM table` with no WHERE | Deletes all records including live ones |
| "Simplify auth" | Removes the authorization middleware entirely | Endpoint is now public |
| "Make the tests pass" | Deletes the failing test, adds `.skip`, or weakens the assertion | Tests now pass without the bug being fixed |
| "Handle the error" | `catch (e) {}` or `catch (e) { return null }` | Error silently swallowed, caller receives null |
| "Use the real API" | Adds fallback mock data alongside the real call | UI shows plausible data even when API is down |
| "Refactor this function" | Changes the function's parameter names or return type | Breaks every caller |
| "Reset state" | Drops/truncates the table instead of clearing in-memory state | Production data gone |
| "Update all routes" | Replaces the entire routes array/config | All previously configured routes are gone |

**How to detect:**

```bash
# Destructive operations — flag any of these and verify intent
git diff "$MB"...HEAD | grep -iE '^\+.*(deleteMany|deleteAll|\.drop\(\|DROP TABLE|TRUNCATE|DELETE FROM [a-z]+ WHERE 1|DELETE FROM [a-z]+;|db\.(collection|table)\.delete|prisma\.\w+\.deleteMany\(\{?\}?\)|removeAll|purge|wipe|reset.*database)'

# Route/handler deletions
git diff "$MB"...HEAD | grep -E '^\-.*(@app\.|@router\.|app\.(get|post|put|patch|delete)|router\.(get|post|put|patch|delete)|@GetMapping|@PostMapping|@DeleteMapping)'

# Auth middleware removed
git diff "$MB"...HEAD | grep -E '^\-.*(authenticate|authorize|requireAuth|isAuthenticated|checkPermission|hasRole|@PreAuthorize|middleware.*auth)'

# Test skips/weakened assertions added
git diff "$MB"...HEAD | grep -E '^\+.*(\.skip\(|xit\(|xdescribe\(|\.todo\(|\.only\(|expect\.anything\(\)|toBeTruthy\(\)|toBeDefined\(\))' | grep -v '^\+\s*//'

# Config/array wholesale replacement (PUT where PATCH intended)
git diff "$MB"...HEAD | grep -iE '^\+.*(routes\s*=\s*\[|config\s*=\s*\{|settings\s*=\s*\{|headers\s*=\s*\{)' | grep -v 'const\|let\|var '
```

**Severity**: Every item in this section is a **Blocker** if the intent was not explicitly destructive/replacement. Flag and require the developer to confirm the operation matches their intent.

---

### Q. Silent fake success — looking done but isn't

CI passes, QA passes, it ships — but the feature is faked. Find these:

- **Mock/fallback data in a catch block**: `catch { return MOCK_USERS; }` — UI always shows something plausible even when the API fails. Flag any `catch` returning a hardcoded array/object. Severity: **Blocker**.

- **Write returns success regardless**: `try { await db.save(); } catch (e) { logger.warn(e); }` then `return { success: true }` — the error was swallowed but success reported. Severity: **Blocker**.

- **`useEffect` / data fetch that never actually called**: a React component that has a `useEffect` with a data fetch, but the dependency array is `[]` and the fetch is behind a condition that's never true. UI renders loading state forever or shows empty.

- **Feature flag hardcoded to the "off" state**: `if (FEATURE_X_ENABLED)` where `FEATURE_X_ENABLED` is always `false` — the feature is wired in but can never run.

- **Test that mocks the thing being tested**: a unit test for `processPayment()` that mocks `processPayment` itself, or that mocks the DB call so the test doesn't actually hit any of the real logic.
  ```ts
  jest.mock('./processPayment'); // ← testing the mock, not the function
  it('processes payment', () => {
    expect(processPayment).toHaveBeenCalled();
  });
  ```
  Severity: **Blocker** — the test provides false confidence.

- **Duplicate file from refactor — old version still runs**: AI copies to a new location without deleting the original. Check: if the diff adds `features/X/api.ts`, confirm `src/api/x.ts` was deleted (`git diff --diff-filter=D`). Old test files surviving means coverage double-counts and the old behavior is still reachable.

- **429 retry loop without reading `Retry-After`**: retry logic on HTTP 429 (rate limit) that uses a fixed sleep or exponential backoff instead of reading the `Retry-After` response header. Manifests as flakiness and thundering herd, not an obvious error.
  ```bash
  git diff "$MB"...HEAD | grep -A5 '429\|TOO_MANY_REQUESTS\|rate.limit' | grep -v 'Retry-After\|retry-after'
  ```
  Severity: **Suggestion**.

---

## 4. Pre-emit checklist

Run these grep checks before printing the report. If you haven't scanned for an item, do it now:

```bash
DIFF="git diff --find-renames $MB...HEAD"

# Em dashes / en dashes in UI strings
$DIFF | grep -P '[–—]' && echo "FOUND: em/en dashes"

# onClick without cursor-pointer
$DIFF -- '*.tsx' '*.jsx' | grep '^\+' | grep 'onClick' | grep -v 'cursor'

# Hardcoded secrets (basic patterns)
$DIFF | grep -iE '^\+.*(api_key|apikey|secret|password|token|bearer|private_key)\s*[:=]\s*["\x27][^"]+["\x27]'

# Empty catch blocks
$DIFF | grep -E '^\+.*catch.*\{\s*\}|catch.*\{\s*return null\s*\}'

# deleteMany / deleteAll on routes
$DIFF | grep -iE '^\+.*(deleteMany|deleteAll|\.destroy\(|DELETE.*WHERE)'

# Unawaited async calls (JS/TS heuristic)
$DIFF -- '*.ts' '*.tsx' '*.js' '*.jsx' | grep '^\+' | grep -vE 'await |return |const |let |var ' | grep -E '[a-zA-Z]+\([^)]*\)\s*;' | grep -iE 'send|emit|save|create|update|delete|notify|publish|dispatch'

# Float for money
$DIFF | grep -iE '^\+.*(price|amount|total|cost|fee|charge|payment).*float|float.*(price|amount|total|cost|fee)'

# new Date() without timezone handling (heuristic)
$DIFF | grep -E '^\+.*new Date\(\)' | grep -v 'UTC\|toISOString\|timezone'

# resource not closed (heuristic)
$DIFF | grep -E '^\+.*(open\(|createReadStream|getConnection)' | grep -v 'finally\|close\|using\|with '

# 200 returned with error body
$DIFF | grep -iE '^\+.*\{ *error:|success.*false|"error"' | grep -v 'status\|\.status\|statusCode\|res\.status'

# SQL injection heuristic
$DIFF | grep -E '^\+.*WHERE.*\+|WHERE.*\$\{' | grep -iE 'SELECT|UPDATE|DELETE|INSERT'

# any / ts-ignore
$DIFF -- '*.ts' '*.tsx' | grep -E '^\+.*(: any|as any|@ts-ignore|@ts-expect-error)'
```

Also manually verify:
- [ ] Every new `onClick` non-button/anchor has `cursor-pointer`
- [ ] Every new `catch` block actually handles the error — not swallowed, not returning mock/hardcoded data on failure
- [ ] Every multi-step write has a transaction
- [ ] Every new `fetch()` / HTTP client call has a timeout configured
- [ ] New POST endpoints that create records have some duplicate prevention
- [ ] No `window` / `document` / `localStorage` in server-side code
- [ ] No module-level mutable state in request handlers
- [ ] No route path strings changed on existing endpoints without explicit intent
- [ ] No auth middleware removed or bypassed in the diff
- [ ] No test assertions weakened, skipped, or deleted to make tests pass
- [ ] Files moved to new location: were the originals deleted? (`git diff --diff-filter=D` shows deletions)
- [ ] Any `deleteMany` / bulk DELETE: was this explicitly requested, or did AI "clean up"?
- [ ] Any wholesale config/array replacement: was the intent to replace all, or just update one item?
- [ ] Every new import resolves to a real installed package and a real file path

---

## 5. Output format

```
# general-code-review

**Branch:** <current> → **Base:** <base>
**Scope:** <working diff | branch diff> — <N> files
**Stack:** <detected tech stack>
**Verdict:** <ship | fix-before-ship | needs-rework>

## Blockers
- `path/to/File.tsx:42` — <one-line problem>. Fix: <one-line fix>.

## Suggestions
- `path/to/Other.ts:10` — <one-line problem>. Fix: <one-line fix>.

## Nits
- `path/to/Yet.java:88` — <one-line problem>.

## Needs you
- <judgment-call items that can't be auto-fixed>
```

Rules:
- Group by severity, not by file.
- Every finding includes `path:line` and a concrete fix.
- Omit sections with no findings.
- If clean: `**Verdict:** ship — no issues found in <N> files.`

---

## 6. Offer to apply (self-review mode only)

Skip in `review` mode. After the report (when verdict is not `ship`), call `AskUserQuestion`:

```json
{
  "questions": [
    {
      "header": "Apply fixes",
      "question": "Apply findings to the diff in place?",
      "multiSelect": false,
      "options": [
        { "label": "All", "description": "Apply mechanical + structural fixes. Judgment calls go to Needs you." },
        { "label": "Blockers only", "description": "Apply only the Blockers." },
        { "label": "No", "description": "Leave code untouched." }
      ]
    }
  ]
}
```

**Mechanical** (auto-apply): em dash → rephrase, add `cursor-pointer`, remove unused imports, `console.log(err)` → `console.error(err)`, `Optional.get()` → `.orElseThrow()` where semantics are clear, string concat in log → parameterised form, `parseInt` without radix → add `10`, `JSON.parse(JSON.stringify(x))` → `structuredClone(x)`, `for...of` purely for side-effects → `.forEach()`.

**Structural** (apply with care): add `cursor-pointer` to interactive containers, wrap multi-step writes in transaction, add `LIMIT` to unbounded queries, add `finally { resource.close() }` to resource-opening blocks.

**Judgment** (never auto-apply → Needs you): replacing deleteMany with upsert logic, adding missing auth, fixing race conditions (requires schema changes), idempotency key strategy, re-doing error handling in complex flows, replacing hallucinated APIs.

Constraints: Edit in place. Never `git add`, commit, push, or stash.

After edits: `Applied <N> fixes across <M> files.`
If No: `Left untouched. Re-run /general-code-review after addressing findings.`

---

## 7. Don't do

- Don't comment on code that didn't change.
- Don't suggest refactors beyond what was changed.
- Don't add comments explaining what code does — only flag non-obvious WHY that's missing.
- Don't run formatters, linters, or builds unless asked.
- Don't commit, push, or open PRs.
- Don't flag what the project's own linter already catches — check `.eslintrc`, `biome.json`, `checkstyle.xml` first.
- Don't invent findings to seem thorough — only report what's actually in the diff.
