# Miskari test-harness + environment facts

**This file is EDITED IN PLACE, never appended to.** It is the durable state of the environment — the
facts that are true *now*. It is not a diary.

Everything here was previously buried in `learnings.md`, which grew to 51 KB of interleaved run-narrative
and protocol-lessons that every run re-read in full and half-re-derived anyway. Run *history* stays in
`learnings.md` (rolling 5-run window). Run *knowledge* lives here. When a fact changes, **overwrite it**
— a stale line here is worse than no line, because it will be trusted.

---

## The harness is committed. Do not rebuild it.

`tools/user-test-harness/` in the repo. Not `scripts/` — `.cjs` files there break `pnpm lint`
("not found by the project service"), which is why prior runs kept exiling the harness to a scratchpad
and then losing it to a `/compact`. `tools/**` is excluded from lint and knip.

| Script | Purpose |
|---|---|
| `mblib.cjs` | `launch`, `newContext`, `brandCheck`, `login`, `go`, `text`, `shot`, `selectCombobox` |
| `mbcapture.cjs` | `<outdir> <route…>` → text + console + ≥400s + screenshot + `_summary.json` |
| `mbprobe.cjs` | `[--no-auth] <route…>` → fast HTTP status/redirect/body sweep, no browser |
| `mbsweep.cjs` | Deterministic isolation + token tripwire + **cross-surface consistency**. Exit 1 = anomaly |
| `validate-artifacts.mjs` | Schema + self-consistency check on `baseline.json` / `known-issues.json` |

```bash
export MB_BASE="http://localhost:3002"    # REQUIRED - the brand-verified port
pnpm ut:login                              # ~15-30s against Neon
pnpm ut:sweep                              # or ut:sweep:full
pnpm ut:validate
```

`MB_AUTH` defaults to `~/.cache/miskari-user-test/auth-state.json` — under `~/.cache` deliberately, so it
survives a `/compact` wiping `/tmp` (this has bitten a run).

**The sweep also runs cross-surface consistency checks** (`crossSurfaceChecks` in `sweep-config.json`):
the same fact extracted from every surface that renders it, asserted to have exactly one value. Added
2026-07-19 because this is the class that beat the 2026-07-17 calibration — a planted deadline checked
on three surfaces that all *derive* it, missed on `/properties/[id]`, which renders a **stored**
`protestDeadline` through a path that never calls the derivation. Two rules when you touch it:
`INCONCLUSIVE` (<2 surfaces matched) is a **failure, not a pass** — the extractor has rotted with the
markup, so fix it or delete the check; and add a new check whenever a run finds a material fact on 2+
surfaces, enumerating those surfaces from the **route list**, not from where you happened to look.
Full field reference in `tools/user-test-harness/README.md`.

---

## Seven gotchas, each of which cost a prior run real time

0. **`button[type="submit"]` clicks SIGN OUT, not your form.** The app chrome renders a "Sign out" form
   whose button is `type=submit` and precedes the page form in the DOM. A bare `button[type="submit"]`
   selector therefore logs you out: the server log reads `POST /<route> 303` → `logoutAction()`, the
   browser lands on `/login`, and **no record is created — with no error and no console error.** This
   produced a **CRITICAL false positive** on 2026-07-16 ("/work-orders/new silently discards the COI
   block"), complete with a confident but wrong code-level root cause. **Always target the form button by
   its accessible name:** `page.getByRole("button", { name: /Create work order/i })`. If a submit
   "silently does nothing", check `page.url()` for `/login` before filing anything.

0b. **Drive the custom combobox by role, not by text.** `mb.selectCombobox(page, triggerSelector, optionText)`
   takes a **CSS selector** first, not a label. The reliable pattern: find the trigger next to the
   aria-hidden native select, click it, then click the option **by role** —
   `page.locator('select[name="vendorId"]').locator('xpath=..').locator('button[role="combobox"]').first()`
   then `page.getByRole('option', { name: /Metro HVAC/i }).click()`. `getByText()` resolves to the
   aria-hidden `<option>` and fails with "element is not visible".

1. **Never `waitUntil: "networkidle"`.** Miskari streams — all token surfaces, `/tax/preflight`, every
   Suspense route. networkidle never fires, you get a false 30–45s "hang", and it gets misfiled as a
   reliability bug (a persona did exactly this to `/tax/preflight`). `go()` uses `domcontentloaded`.
   **A route is only slow if a WARM second hit is still slow.**

2. **Warm every route before a stress test.** A cold concurrent round shows non-200s that are Turbopack
   compile timeouts, not 500s. One run filed 9/18 cold-compile non-200s as a reliability Critical; warm,
   it was 18/18 green. `mbsweep.cjs` warms automatically.

3. **`selectOption` cannot drive the app's `SelectInput`.** It is a custom combobox with an aria-hidden
   native `<select>`. Playwright's `selectOption` silently fails on it — this produced a false-positive
   "form can't submit" finding in run 4. Use `mb.selectCombobox(page, trigger, optionText)` (click the
   trigger, then the option). **A select is only broken if a HUMAN click-through also fails.**

4. **Don't read seed reality from the database.** Direct `pg`/CLI queries against Neon hang from bash in
   this environment (`DatabaseNotReachable` via the adapter, three different ways), and a standalone DB
   script was declined by the user mid-run. Use **`GET /api/diagnostics/seed-check`** instead — own-org
   counts, workflow prerequisites, and fixture-invariant warnings, straight from the app.

5. **Agent liveness ≠ file mtime.** Persona agents block on slow `mbcapture` calls, so an idle transcript
   mtime does NOT mean the agent finished. Wait on a "final report" content marker in its output.

6. **A bare `fetch()` gets 403'd by every `/api/*` route.** The `Sec-Fetch-Site` same-origin guard fails
   **closed** when both `Sec-Fetch-Site` and `Origin` are absent — and `fetch()` sends neither (a browser
   sends them automatically). Send `Sec-Fetch-Site: same-origin` + `Origin: $MB_BASE` (`mbsweep.cjs` does).
   **This is the guard working correctly. Never weaken it to make a test pass.**

7. **Server-action FORM writes MAY bounce to `/login` under the Playwright harness — but this is NOT reliable
   and must be re-tested, not assumed.** Originally observed 2026-07-15-1415: a `<form action={serverAction}>`
   submit driven through `mb.run` redirected to `/login` even though the context was authed — a cookie-on-the-wire
   limitation of the harness, NOT a product auth bug (curl with the same session cookie → HTTP 500 on a bad body,
   *not* `/login`, so the app authenticates writes correctly).

   **CONTRADICTED 2026-07-19.** The adversarial agent drove a two-step `ConfirmDeleteButton` (a server-action form
   write) to completion in a real browser and it worked normally, redirecting to `/work-orders?trashed=14`. Several
   personas the same run completed server-action writes live: contract create/delete, work-order create + complete,
   inspection create, RFQ create + award, PO create + approve, and an org settings update.

   **So: do NOT cite this gotcha as a reason to skip a live verification.** It has been the standing excuse for
   leaving the optimistic-lock race (probe 2) and mark-paid freshness (probe 4) un-verified live *every run* — and
   that excuse is now known to be at least sometimes false. Attempt the live drive first; only fall back to
   code+curl if it actually bounces, and record which happened. API-route POSTs (e.g. the reconcile match CTA)
   have always gone through. Do NOT file a bounce as a Critical if you do hit one. To force a server-action write
   end-to-end via curl, carry `Sec-Fetch-Site: same-origin` + `Origin: $MB_BASE` + the storageState cookies.

Two more the harness now handles for you, but that you should know about:

- **`LD_LIBRARY_PATH` is set by `mblib.cjs` itself** (`ensureBrowserLibs()`). Chromium's OS libs live in a
  user-space sysroot; the old harness needed a wrapper script to export this, and forgetting it produced a
  bare `libnspr4.so: cannot open shared object file` that reads like a broken harness rather than a missing
  env var.
- **Cold compiles routinely take 30–45s and will drop the connection.** `mbsweep.cjs` retries (2×, 120s
  timeout) and warms first. A dropped cold-compile connection is **not** a product finding — a prior run
  filed one as a reliability Critical.

---

## Ports: never trust the first one that answers

Miskari has been found on **3000, 3001, and 3002** across runs, and unrelated apps squat those ports —
`:3000` has been "Sheevook"/pegazosdetailing, `:3001` "marketing-helper". Their login pages match a naive
`grep "Sign in"`. `brandCheck()` refuses known impostor markers and requires a Miskari brand/login marker;
every agent calls it as a double-confirm. If no port is Miskari, start it: `PORT=3002 pnpm dev` (~3s).

## Login

`dev@example.com` / `devpassword` (org "dev"). Login is a **server action against Neon and is slow
(~15–30s, not 2s)**. `login()` polls until the URL leaves `/login` before saving `storageState`.
**Do not shorten this wait** — it is the single most common way a run breaks itself.

## Chromium in this WSL box

No passwordless sudo. Chromium's OS libs are extracted into a user-space sysroot:
`~/.cache/miskari-browser-sysroot/root/usr/lib/x86_64-linux-gnu` on `LD_LIBRARY_PATH`, with the cached
browser under `~/.cache/ms-playwright/`. If missing on a fresh box: `apt-get download` + `dpkg-deb -x`
libnss3 / libnspr4 / libasound2t64 into that sysroot. It usually already exists. MCP Playwright may be
unconnected in a given session — the node harness is the always-available fallback.

## Memory: the box will SIGKILL your dev servers

**~20 GB total.** Two Next dev servers (e.g. a baseline on :3002 plus a calibration build on :3003) plus
three concurrent Playwright persona agents will OOM the box: servers die with **exit 143/144** mid-run,
and the browser sees `ERR_CONNECTION_REFUSED` / "Execution context was destroyed". This happened twice on
2026-07-17. The same load also starves Neon connections and produces **`ETIMEDOUT` 500s that look exactly
like a product reliability bug** (a persona filed one; the prior run had already disproven the same
signature as a "pool artifact"). Budget ~10 GB headroom: run a calibration build serially, or kill the
baseline server while the calibration one is up. Check `free -m` before blaming the app.

## Neon cold starts

The Neon instance **suspends when idle**. The first one or two commands of a run (`prisma migrate status`,
`pnpm seed:user-test`) routinely fail with `P1001 Can't reach database server` or `ETIMEDOUT` and then
**succeed verbatim on retry**. Always retry once before treating it as an environment failure.

Direct `pg`/`tsx` probes are possible but fiddly, and the schema is mixed-convention: table names are
**snake_case** (`@@map("property")`, `lease`, `unit`) while columns are **camelCase and must be quoted**
(`"organizationId"`, `"buildingSqft"`, `"leasedSqft"`). A bare script also needs `import "dotenv/config"`
or it silently targets `127.0.0.1:5432`. Prefer `/api/diagnostics/seed-check` for fixture facts.

## Database / migrations

- **Always `pnpm exec prisma migrate status` in Phase 0.** Migration drift has contaminated two runs: the
  app ran ahead of the DB, the regenerated Prisma client selected columns the DB lacked, and every
  affected route hard-500'd. Run 2's dominant "Critical" was entirely this.
- After applying migrations you **must restart the dev server** — the Prisma client is cached in-process
  and HMR does not reload it. Then warm every route (the first hit after a restart cold-compiles).
- `prisma migrate dev` **hangs on Neon** (shadow DB). Author migration SQL by hand + `prisma migrate deploy`.
- The `.env` DB is a **shared Neon instance with ~6 orgs / 41 properties**. Dev Org is id **1** (properties
  1–3). Confine every write to Dev Org; keep all cross-org probing read-only.
- Runtime role has historically been `neondb_owner` with `rolbypassrls=true`, which makes FORCE RLS a
  silent no-op — isolation then rests entirely on the app-layer `WHERE organizationId`. **The NOBYPASSRLS
  role switch is a deployment action, not code.** It has been open for 5+ runs; it belongs in `DEPLOY.md`,
  not in another run report. The `normalize_rls_bypass_policies` migration already fixed the policies
  themselves, so the switch is now safe to flip.

## Fixtures

`pnpm seed:user-test` (additive, idempotent, Dev-Org-only) provisions the chronically-missing fixtures:
a Plaid item + 6 bank transactions, a residential lease expiring in 45d, 5 ParcelCache office comps, and
Unit rows. Run it before every session. Then read `GET /api/diagnostics/seed-check` for the actual state.

**Known fixture artifacts — do NOT file these as product bugs** (the diagnostics endpoint warns on each):
- Seeded leases with `unitId = NULL` → every suite renders Vacant under an "Occupied 1" tile.
- `property.units` scalar disagreeing with the actual `Unit` row count.
- Legacy triplicate bills in the shared dev DB (a since-fixed seed non-idempotency; the old rows persist
  and 3x-inflate expense/NOI aggregates until a clean reseed).
- 0 documents in the entire DB → document-boundary probing stays code-level.
