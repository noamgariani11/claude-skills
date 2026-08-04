# Sheevook test-harness + environment facts

**This file is EDITED IN PLACE, never appended to.** It is the durable state of the environment —
what is true *now*. Run *history* goes in `learnings.md`. When a fact changes, **overwrite it** —
a stale line here is worse than no line, because it will be trusted.

Seeded on 2026-07-11 from `docs/reports/user-test-reports/learnings.md`, the generic `/user-test`
skill's history. **Every item below already cost a prior run real time.** Do not re-learn them.

---

## The app

- Repo: **`/home/drago/sheevook`**. Product name: **Sheevook**.
  (Corrected run #13 — this file said `marketing-helper` for 12 runs. That path does not exist.)
- `pnpm dev` → http://localhost:3000. Next.js 16 App Router, React 19.
- Package manager is **pnpm**. Gates: `pnpm build`, `pnpm lint`, `pnpm test`.

## ⚠ THE DB IS NEON POSTGRES, AND `.data/marketing.db` IS A DECOY (run #13)

`.env.local` sets a live **`DATABASE_URL`** pointing at Neon Postgres. The repo supports both
engines, and CLAUDE.md's "SQLite locally" framing plus this file's own old text sent **five
personas in run #13 toward the wrong database.**

- **`.data/marketing.db` still exists and is an EMPTY, STALE SQLite file.** Reading it returns
  0 brands / 0 content / no `auth_user` and looks exactly like "the app is broken / was reseeded."
  **It is not the app's database.** The coordinator lost ~20 minutes to this before persona A
  caught it.
- Postgres has tables SQLite lacks (`ai_usage`, `subscription`, `engagement_mentions`,
  `media_blobs`) — proof the live server applied the schema *there*.
- Read it like this. **Two corrections from run #16 — the previous version of this snippet hung:**
  ```bash
  set -a; source .env.local; set +a
  node -e 'const {Client}=require("pg");
    const c=new Client({connectionString:process.env.DATABASE_URL, statement_timeout:90000});
    c.connect().then(()=>c.query("select id,name from brand")).then(r=>{console.log(r.rows);c.end()})'
  ```
  1. **Do NOT pass `ssl:{rejectUnauthorized:false}` — it HANGS on this Neon endpoint.** Use the
     connection string bare; `sslmode` is already in it. (This file previously prescribed the
     `ssl` option; that was the hang.)
  2. **Neon cold-starts slowly.** Pass `statement_timeout: 90000`. Run #16 lost time to queries
     hanging at the 60s default during a cold start that was not a failure.
- **Postgres folds unquoted identifiers to LOWERCASE.** Columns come back as `aiassisted`,
  `createdat`, `anchorcompetitor` — **not** the camelCase in `lib/types.ts`. Three agents hit this
  in one run. A `SELECT` that reads `row.aiAssisted` gets `undefined` and looks like "the AI never
  ran," which is a false finding waiting to happen.
- `sqlite3` CLI is **not installed**. Tables are SINGULAR (`brand`, `content`, `variants`).
  `content` HAS `createdAt`; `brand` does NOT.
- **`GET /api/brand` is 405 by design** (PUT/POST only). Reading the brand that way returns
  nothing and looks exactly like an empty brand — it cost a coordinator a false reading. Read the
  brand from Postgres or a Server Component surface instead.

## ⚠ LIVE STRIPE KEYS — never touch checkout (run #13)

`.env.local` carries **LIVE** Stripe price IDs on `acct_1TtuGe7lSjvFzfP4`, and warns in its own
comment that a completed checkout **bills a REAL card — including from `pnpm dev` on localhost.**
`/api/billing` reports `stripeConfigured: true`.

**No persona may POST `/api/billing/checkout`.** Brief every agent explicitly. Reading
`/api/billing`, `lib/billing/*`, and `/pricing` is fine.

## The 45s CLI timeout is TOO TIGHT for the tailor tier (run #13)

This blocked runs #11 and #12 from certifying live-AI quality, and both misdiagnosed it as box load.

- **Measured:** a tailor call with a full `brandContext` genuinely needs **~68s**. The default
  ceiling is **45s** (`lib/ai/claude-cli.ts:27`), so it dies mid-generation and falls back.
- Not load (box quiet, load 1.15), not the CLI (raw Haiku probe 3.1s), not dev compilation
  (warm retry 46.9s). The `claude-cli.ts` comment claiming "healthy local completions land in
  ~16-31s" is **not true of the tailor tier.**
- **Fix: `CLAUDE_CLI_TIMEOUT_MS=180000` in `.env.local`.** With it, all 5 platforms returned
  `aiAssisted:true` first try. Run #13 appended this; keep it.
- Contributing cause: `spawn` passes no `cwd`, so the CLI inherits the server's cwd and loads the
  repo's 19KB CLAUDE.md into **every** call — measured **15.8s vs 10.6s** from `/tmp`.
- `CLAUDE_CLI_PATH` in `.env.local` is **dead config** — zero code references; `claude-cli.ts:65`
  spawns `"claude"` via PATH deliberately.

## Test-brand domains

- **`cadence.dev` DOES NOT RESOLVE** (`curl: (6) Could not resolve host`). The baseline brand used
  for runs #1-#12 never had a real site, so "discovery cold" was never truly exercised on it.
- **`qovery.com` works** and is a genuinely hard discovery test: the company has *pivoted* to
  AI-agent infrastructure, so stale model priors ("Heroku alternative / preview envs") are wrong
  and reading the site is the only way to get it right. Run #13 used it. Discovery passed.

## Never trust the first port that answers

This box runs several apps at once — a prior run tested an unrelated app ("Pegazos") on :3001 for
a while before noticing, and miskari commonly holds :3007.

```bash
for p in 3000 3001 3002 3003 3005 3007; do
  printf '%s: ' "$p"; curl -s --max-time 2 "http://localhost:$p" | grep -oiE '<title>[^<]*' | head -1
done
```

**The served `<title>` must read Sheevook.** Verify before testing anything.

**Ports churn violently on this box and Sheevook moves mid-run.** Across recent runs it has served
on **3000, 3001, and 3005** at different moments, while Miskari, Pegazos, and a realtor app take
whichever port is free. Re-detect the port **during** a long run, not only at the start — a
persona that 404s halfway through has probably been pointed at another product, not found a bug.
**This scan list is the canonical one; SKILL.md defers to it rather than repeating it.**

## First-run state: the app is EMPTY

No demo data, by design. A fresh workspace opens on onboarding (welcome + checklist + tour).
**The core loop cannot be tested without creating an account at `/setup`.**

- `pnpm seed` resets to a clean, EMPTY state — and **destroys the existing account.**
- **Never run `pnpm seed` without asking the user.** A sibling session reseeded mid-run once and
  invalidated the personas' login, killing the verification pass.
- There is no in-app account reset. Test accounts are run residue; name them in the report.

## Auth

- Single account, login-gated. `proxy.ts` (the Edge proxy — renamed from `middleware.ts` for
  Next 16) does an optimistic cookie-*presence* check; the authoritative check is server-side:
  `requireAuth()` for pages, `handler()` for API routes.
- **Login selector trap:** the text "Sign in" matches the AuthShell **heading**, not the submit
  button. Use `{"role":"button","name":"Sign in"}`. (The duplicate accessible name is itself a
  real low-severity finding — already known.)

### ⚠ THE HYDRATION TRAP — this looks exactly like bad credentials (cost run #14 ~20 min)

**Filling a login field right after `domcontentloaded` beats React hydration.** The `onChange`
never fires, component state stays empty, and the API returns **"Validation failed"** — which is
indistinguishable from wrong credentials, so the natural next move (re-check the password, reseed,
mint a new account) is the wrong one and burns the run.

- Wait for `networkidle` **plus ~1.5s**, then use `type()` (not `fill()`) on
  `#login-username` / `#login-password`.
- **Log in ONCE, save `storageState`, and reuse it everywhere.** This is also the documented fix
  for the shared-bucket rate-limit self-DoS below, and for the tour false positive above.

### ⚠ THE SHARED-BROWSER TRAP — cost run #17 a full re-field of the gate persona

**Playwright MCP is ONE browser instance at user scope.** Parallel agents do not get their own.
At run #17, seven concurrent agents contended for it: the gate persona stalled with a 126-byte
output file, and persona D reported her browser navigating to another agent's port mid-test
("the shared Playwright browser was hijacked").

- **Run at most ONE browser-driving agent at a time.** Everyone else drives the API with `curl`.
- Better default: tell every agent to **prefer `curl` against the route handlers** (same code path,
  same validation, same repository writes) and reserve the browser for genuine UI judgment.
- Tell agents to **write findings as they go**, so an interruption leaves partial output.

### Session-minting field names (each of these silently 307s or 400s if wrong)

- The payload field is **`uid`**, NOT `userId`, and **`exp` is REQUIRED** - see `SessionPayload`
  in `lib/auth/crypto.ts:66-80`. A payload missing `exp` produces a cookie the app rejects.
- `sessionversion` comes back from Postgres as a **STRING**; cast `Number(...)`.
- The DB table is **`brand`**, not `brands`.
- `POST /api/projects` needs a discriminator: `{"action":"create","name":...,"url":...}`.
- `/api/brand` is **PUT only** (GET/POST return 405 by design).

### Minting a session directly (when a sibling owns the account)

If a sibling session owns the live account, **do not reseed**. HMAC-sign a session per
`lib/auth/crypto.ts` using the `session_secret` from the `auth_meta` table; cookies are
`mh_session` **plus** `active_project`.

> **Gotcha that fails silently:** `sessionversion` comes back from Postgres as a **STRING**. A
> payload signed with `sv: "0"` produces a cookie the app accepts and then **307s the dashboard**
> with no error. Cast it: `Number(o.sessionversion || 0)`.

## The rate-limit self-DoS (this has bitten twice)

`lib/rate-limit.ts` keys **all of localhost** to `clientKey="local"` (no XFF header), so
adversarial auth curls share the **same 60s fixed-window bucket** as the personas' browser logins
and will 400/429 them.

- **Run auth/rate-limit chaos LAST**, after every browser persona has finished.
- Or reuse a saved `storageState` cookie instead of re-logging-in.
- The window is 60s aligned to the minute boundary — it self-clears.

## The tour false positive

`close()` persists `TOUR_SEEN_KEY` to `localStorage` and the tour **does** stay closed within a
real session. It only *appears* to re-open because separate driver invocations create fresh browser
contexts, resetting `localStorage`.

- **Give each persona ONE browser context for its whole session**, or seed `TOUR_SEEN_KEY`.
- The tour's close button is `aria-label="Close tour"`, **not** "Close" — a
  `button[aria-label='Close']` selector will time out. That is not a bug.

## Which brain is running

With `ANTHROPIC_API_KEY` unset, all AI output is **deterministic rule-based fallback** — by design
(the app must work with no key). This completely changes how output is judged; see
`output-quality.md`. Record it as `ai_layer` in `baseline.json` and never compare Output scores
across modes.

**CONFIRM THE BRAIN BY BEHAVIOR, NOT GREP — this has now misfired twice (runs #1 and #2).** The
static check (`echo $ANTHROPIC_API_KEY`, grepping `.env`) said *deterministic* both runs, yet the
app ran **live Anthropic** both times: the key/CLI is inherited from the Claude Code parent env into
`pnpm dev` and doesn't show cleanly. Tells of a LIVE layer: tailoring latency **>20s** (run #2 saw
102s for 4 platforms), `aiAssisted=1` on variants, and **master↔variant word-overlap <70%** (run #2:
41–60% where AI ran; a deterministic paste sits ~90%). Judge the layer from these, then set
`ai_layer`.

## Browser: YES. A browser is always available — `browser: NO` was wrong for four runs

Run #14 settled this after four runs of visual findings being tagged `[INFERRED]` for no reason:
**Playwright 1.61.1 + Chromium are installed** (`~/.cache/ms-playwright`). The Playwright **MCP**
may or may not be in the session; **the library is not the MCP** and its absence proves nothing.
Run #14 took 36 screenshots and certified visual craft, answering a question that had been "owed"
for five runs.

Order of preference:

1. **Playwright MCP tools / the `browse` skill**, if present in the session.
2. **The library, driven directly from node** — always available:
   - **The script must live INSIDE the repo** (`.data/_probe/`, which is gitignored). Node
     resolves `node_modules` from the **script's own directory**, so a script in the scratchpad
     **cannot** import `playwright` or `pg`. This has cost time more than once.
   - Chromium runs without root via `LD_LIBRARY_PATH` pointing at the no-root sysroot at
     `~/.local/pw-libs/root` (`usr/lib/x86_64-linux-gnu:...`).

Only if **both** fail may you fall back to HTTP + source reading — and then tag every
layout/visual finding `[INFERRED]` and say so loudly. **Do not record `browser: NO` in
`baseline.json` without having actually tried path 2.**

## ⚠ `research/` IS GITIGNORED — and it breaks worktrees

`research/` exists in the working tree but **not at HEAD**, so **any `git worktree` lacks it
entirely.** Two consequences that have both cost a run:

- **DoD #4 (keep `platforms.ts` and `research/platforms/*.md` in sync) is structurally impossible
  in a worktree** — the file you must sync is not there. Phase 5 fixes for drift findings cannot
  ship from a worktree without the symlink.
- `platform-research-brief.test.ts` fails there for the same reason.

**Fix, needed in every worktree** (calibration runs included — see `calibration.md`):

```bash
ln -s /home/drago/sheevook/research research
ln -s /home/drago/sheevook/node_modules node_modules   # same problem, same fix
```

## Concurrent sibling sessions (severe, recurring)

Several `claude` sessions run in this repo at once. One has: reseeded the DB mid-run, live-edited
`Composer.tsx` during another session's edit, and left a dangling import.

```bash
for pid in $(pgrep -x claude); do printf '%s -> ' "$pid"; readlink /proc/$pid/cwd; done
stat -c '%y %n' .data/marketing.db
```

- If a sibling owns this tree: run **read-only on code**, decline Phase 5, note it in the report.
- **Never blind-kill a `claude` PID.**
- New tables require a **dev-server restart** — `getDb` caches the connection.

## Verified false positives — do NOT re-flag

| Finding | Why it isn't a bug |
|---|---|
| OAuth tokens stored plaintext in SQLite | Accepted design trade-off, stated in CLAUDE.md. At-rest encryption is an enhancement, not a defect. |
| `/l/<bad-slug>` → 302 to `/` | Intentional per the route comment ("somewhere sensible rather than a dead end"). |
| Composer preselects all platforms | Intentional (`Composer.tsx` comment). |
| Tour "reappears" on every page | Harness artifact — fresh browser context per invocation. See above. |
| Login has no autocomplete | False — `LoginForm.tsx` sets it. A prior grep missed it during a transient 500. |
| Publishing requires a real OAuth connection | Honest product boundary. The app never fakes success. Not brokenness. |
| A competitor's price on `/compare` looks wrong from memory | **Never flag a competitor price from recall — WebFetch the cited source.** Run #12 nearly false-flagged "Sprout Essentials $79/seat/mo" and "Buffer $5/channel/mo"; both were CORRECT. `lib/competitors.ts` dates every claim and cites first-party URLs. |
| `draftEngagementReply` passes no `cache` (ENGAGE-NOCACHE) | By design. The short reply prompt carries no `brandContext`; the `brandContext(brand)` nearby is only a cache-KEY discriminator and is never sent to the model. Nothing to cache. |
| AI "invented" a product number in a variant (e.g. Cadence 40s / 72h / $0.04-env-hour) | Check `brand.facts` AND `brand.valueProps` FIRST — they are injected into every prompt via `brandContext()`, so a number absent from the *master* but present in *brand facts* is grounded, not fabricated. Run #2's IG+FB experts flagged this as "invented specs"; the adversarial pass overruled them (Rule 4). The real defect is subtler: master↔brand-fact *contradiction* (master 48h vs facts 72h), with the AI silently + inconsistently choosing a winner. |

## Report store

This skill writes to **`docs/reports/marketing-test-reports/`** — its own `baseline.json` and
`learnings.md`. The generic `/user-test` skill owns `docs/reports/user-test-reports/`.
**Read that one for lore; never write to it.**
