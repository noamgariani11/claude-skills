# SplitSquad test-harness + environment facts

**This file is EDITED IN PLACE, never appended to.** It is the durable state of the environment —
what is true *now*. Run *history* goes in `learnings.md`. When a fact changes, **overwrite it** —
a stale line here is worse than no line, because it will be trusted.

Seeded 2026-07-21 from a live survey of the repo and from `docs/reports/bugs/` (the `/bug-hunt`
skill's store). **Every item below already cost someone real time.** Do not re-learn them.

---

## The app

- Repo: **`/home/drago/splitsqaud`** — note the **misspelled directory name** (`sqaud`). The
  product is **SplitSquad**; `package.json` still calls itself `expense-manager`. All three names
  are correct in their own place; none of them is a finding.
- Next.js **16** App Router, React **19**, Tailwind v4, `reactCompiler: true`.
- Package manager is **npm** (not pnpm). Gates: `npm test`, `npm run lint`, `npm run build`.
- `npm test` = Vitest, node environment, **`src/**/*.test.ts` only** — 6 files / 85 tests as of
  2026-07-21, all pure logic (balances, currency, debt simplification, password, token helpers).
  **No component tests. No E2E tests.** That is a repo fact, not a discovery.

## ⚠ Route shape changed — CLAUDE.md is stale on this

| Route | What it is |
|---|---|
| `/` | **Marketing landing page** (server component, no `"use client"`). Not the app. |
| `/app` | The dashboard — the thing CLAUDE.md calls "`/` (main app)". |
| `/login` | Sign-in, dedicated route. Redirects to `callbackUrl` (relative-only) or `/app`. |

A persona sent to `/` to test app behavior is testing a landing page. Derive routes from
`find src/app -name page.tsx` every run, not from any prose.

## ⚠ THERE IS NO DATABASE HERE (as of 2026-07-21)

No `.env`, no `.env.local`, so **`POSTGRES_URL` is unset and `hasDb` is false.** Consequences that
look exactly like bugs and are not:

- The app boots on **seed data** and persists to localStorage under `splitsquad-local-state`.
- Seed people: **samira / marco / pilar / aiden** (`@tripsplit.dev`). Seed trips include
  `t-lisbon` ("Lisbon Surf + Work"). These are the identities every persona will meet.
- **Credential sign-in cannot work** — user lookup needs the DB. A persona blocked at `/login` in
  this mode has found a *mode boundary*. What *is* a defect: an unhelpful generic failure that
  reads as "wrong password."
- Every DB-only route (`/api/trips`, `/api/expenses`, subscriptions, comments, items, history) is
  reachable but has no store behind it. Findings about them from this mode are **code reads, not
  runtime observations** — tag them `[INFERRED]` unless you actually exercised them.
- Cron routes additionally need `CRON_SECRET`; `requireCronSecret` **fails closed** (500) when it
  is unset. That is correct, documented behavior — do not file it.

If the user provides a database, record `storage: postgres` in `baseline.json` and say so in the
report. **Never trend Money Integrity across storage modes without flagging it.**

## Never trust the first port that answers

This box runs several apps at once. **On 2026-07-21, `:3000` served an unrelated picoCTF site**
while SplitSquad was not up at all.

```bash
for p in 3000 3001 3002 3003 3005 3007; do
  printf '%s: ' "$p"; curl -s --max-time 2 "http://localhost:$p" | grep -oiE '<title>[^<]*' | head -1
  echo
done
```

**The served `<title>` must contain `SplitSquad`.** Verify before testing anything, and
**re-check during long runs** — a persona that 404s halfway through has probably been pointed at
another product, not found a bug.

## ⚠ Browser work goes through the `browse` skill — non-negotiable

Global CLAUDE.md, and it exists because a Next.js dev server driven by automated browsing once grew
to 15.9GB and tripped the kernel OOM killer, taking down the whole WSL distro mid-session.

- **Never `npm run dev &`.** Start servers with `~/.claude/skills/browse/serve.sh`, which caps the
  Node heap and picks a verified-free port.
- **Never hand-roll Playwright** when `mcp__playwright__*` can do it. **Never** run
  `npx playwright install` — Chromium is already in `~/.cache/ms-playwright`.
- Check `free -g` before a long browser run. Under ~8GB available, say so and stop.
- If a dev server dies mid-run, check `dmesg -T | tail -30` for `Out of memory: Killed process`
  **before** restarting. Silently restarting hides an environment failure that invalidates findings.

## ⚠ THE SHARED-BROWSER TRAP

Playwright MCP is **ONE browser instance at user scope**. Parallel agents do not get their own —
they contend, hijack each other's tabs, and produce findings about the wrong app.

- **Run at most ONE browser-driving agent at a time.** Everyone else drives route handlers with
  `curl` and reads code.
- Tell agents to **write findings as they go**, so an interruption leaves partial output.
- Give each persona **one browser context for its whole session** — separate invocations reset
  `localStorage`, which in this app means **a fresh set of seed trips and the loss of everything
  the persona just entered.** That looks exactly like data loss and is not.

## Money-math entry points (for the experts)

| What | Where |
|---|---|
| Canonical math | `src/utils/balances.ts` — `calculateExpenseTotal`, `resolveShares`, `computeBalances` |
| Debt simplification | `src/utils/debtSimplification.ts` — `simplifyDebts`, `getDebtSummary` |
| FX | `src/utils/currency.ts` — static table + `updateExchangeRates` + `convertCurrency` |
| Rates route | `src/app/api/currency-rates/route.ts` (Frankfurter proxy, 1h cache) |
| State owner | `src/context/AppStateContext.tsx` (~1300 lines) — re-exports the math, owns everything else |
| Tests | `src/utils/__tests__/{balances,currency,debtSimplification}.test.ts` |

`AppStateContext` **re-exports** the canonical helpers for backwards compatibility. That is not a
duplicate implementation. A *view* computing its own shares (`GlobalBalanceCard`,
`CrossTripBalanceView` have both done arithmetic of their own) **is**.

## The neighbouring report stores

| Directory | Owner | This skill |
|---|---|---|
| `docs/reports/user-test-reports/` | **this skill** | read + write |
| `docs/reports/bugs/` | `/bug-hunt` | **read-only lore** |
| `docs/reports/seo/` | `/seo-dude` | ignore |

`docs/reports/bugs/latest.json` already carries a 27-finding static sweep. Use it to avoid
re-discovering known ground — but **re-prove anything you intend to report**, and never carry its
prose as fact.

## Verified false positives — do NOT re-flag

| Finding | Why it isn't a bug |
|---|---|
| SWR hooks return empty shapes on error | Deliberate: the localStorage fallback must keep rendering. Documented in CLAUDE.md. |
| DB layer is "not authoritative for the UI" | By design — additive, client state is primary. |
| Cron routes 500 without `CRON_SECRET` | `requireCronSecret` **fails closed** on purpose. Correct behavior. |
| `/api/settlements` returns a stub | Documented stub. An honest boundary. (A stub returning *fabricated data* would be a defect — check which.) |
| `AppStateContext` "re-implements" the balance math | It **re-exports** `src/utils/balances.ts`. Read the import before filing. |
| No `useMemo`/`useCallback` in components | `reactCompiler: true` handles memoization. Adding them by hand is against repo convention. |
| `package.json` name is `expense-manager` | Historical. The product is SplitSquad. Cosmetic at most. |
| Seed people/trips appear on a fresh context | Intended first-run state with no DB — and also what a fresh browser context looks like (see the shared-browser trap). |
