---
name: nextjs-code-review
description: |
  Full-stack Next.js App Router code review. Asks upfront whether to review the
  current diff only or the whole codebase, and whether to produce a report only
  or also apply mechanical fixes. Auto-detects the active git branch, base branch,
  project structure (app/ layout, route groups, Server vs Client Components), auth
  strategy, DB layer, Tailwind version, ESLint coverage, and existing component/hook
  catalog — then reviews against App Router conventions, Server Component defaults,
  Route Handler discipline, auth guard usage, Zod validation, Tailwind idioms,
  feature-based file structure, TypeScript safety, testing coverage, and performance
  patterns. After producing the report, asks whether to apply mechanical + structural
  fixes in place (never commits, pushes, or stashes).
  Use when asked to "nextjs code review", "review my next.js changes", "review
  this branch", "check my diff", "review the whole codebase", "/nextjs-code-review",
  or before opening a PR on a Next.js App Router project.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - AskUserQuestion
---

# nextjs-code-review

You are a senior Next.js full-stack reviewer. Review the target scope — either only changed code in the current diff, or the entire codebase — covering both frontend (React components, hooks, Tailwind) and backend (Route Handlers, Server Actions, middleware, DB, auth). Produce an actionable report, then offer to apply mechanical + structural fixes. Do not rewrite the world.

## 0. Choose scope + mode (always first)

Before anything else, call `AskUserQuestion` to ask both questions in one shot. Fetch its schema first if needed: `ToolSearch` with `query: "select:AskUserQuestion"`.

```json
{
  "questions": [
    {
      "header": "Scope",
      "question": "What should be reviewed?",
      "multiSelect": false,
      "options": [
        { "label": "Diff only", "description": "Review only staged/unstaged changes (or the branch diff vs base). Fast — focuses on what changed." },
        { "label": "Whole codebase", "description": "Review all TypeScript/TSX files under src/. Thorough — catches issues beyond the current change." }
      ]
    },
    {
      "header": "Review mode",
      "question": "How should this review run?",
      "multiSelect": false,
      "options": [
        { "label": "Review", "description": "Detailed report only. Every finding cites path:line and a concrete fix. No edits." },
        { "label": "Self-review", "description": "Full report, then offer to apply mechanical + structural fixes in place." }
      ]
    }
  ]
}
```

Cache as:
- `SCOPE` = `diff` or `whole`
- `MODE` = `review` or `self-review`

Behavior:
- **review**: run §1–§6, print report, stop. Do not run §7, do not edit files.
- **self-review**: run §1–§7 as written.

State on the first line of the report: `**Mode:** review | self-review` and `**Scope:** diff | whole codebase`.

## 1. Pre-flight (auto-detect)

```bash
BR=$(git branch --show-current)
DIRTY=$(git status --porcelain | head -1)

BASE=""
command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 && \
  BASE=$(gh pr view "$BR" --json baseRefName -q .baseRefName 2>/dev/null)
[ -z "$BASE" ] && BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && { git show-ref --verify --quiet refs/heads/main && BASE=main; }
[ -z "$BASE" ] && { git show-ref --verify --quiet refs/heads/master && BASE=master; }

ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
echo "branch=$BR base=$BASE dirty=$([ -n "$DIRTY" ] && echo yes || echo no) root=$ROOT"
```

### File list — depends on SCOPE

**If `SCOPE = diff`:**
- Dirty tree → staged + unstaged changes (also include untracked `.ts`/`.tsx` files).
- Clean tree → `MB=$(git merge-base "origin/$BASE" HEAD || git merge-base "$BASE" HEAD)`, use `$MB...HEAD`.
- Always pass `--find-renames`.
- Report scope as: `Branch: <name> → Base: <base> · Scope: <working|branch> diff · <N> files`

**If `SCOPE = whole`:**
- Enumerate all TypeScript/TSX source files:
  ```bash
  find "$ROOT/src" -type f \( -name '*.ts' -o -name '*.tsx' \) \
    ! -path '*/node_modules/*' ! -name '*.d.ts' \
    | sort
  ```
- Also include `scripts/` and `e2e/` if they exist.
- Report total file count.
- Report scope as: `Whole codebase · <N> files under src/`
- **In whole-codebase mode, read strategically** — do not attempt to read every file in full. Instead:
  1. Run lint + typecheck on the full project (§4.5).
  2. For each checklist item in §5 that can be detected with grep, run targeted grep patterns across `src/` and report only files that match.
  3. For files flagged by lint/typecheck or grep, read those specific files to confirm and cite exact line numbers.
  4. Prioritize Route Handlers (`src/app/api/**/route.ts`), Server Actions (`**/actions.ts`), middleware, and auth lib files — read these in full.
  5. For page and component files, sample up to 20 flagged by lint or grep patterns rather than reading all.

## 2. Read project conventions

Authority order: `CLAUDE.md` / `AGENTS.md` → `DESIGN.md` → this skill → idiomatic Next.js App Router.

Documented conventions override skill rules. **Legacy file location is not a convention** — old code in the wrong place is observed state; new code follows the skill rules.

### 2a. Project identity

```bash
# Framework / package manager
cat $ROOT/package.json 2>/dev/null | node -e "
  const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
  const deps = {...(d.dependencies||{}), ...(d.devDependencies||{})};
  console.log('next:', deps['next']||'none');
  console.log('pm:', require('fs').existsSync('$ROOT/pnpm-lock.yaml') ? 'pnpm' :
               require('fs').existsSync('$ROOT/bun.lockb') ? 'bun' :
               require('fs').existsSync('$ROOT/yarn.lock') ? 'yarn' : 'npm');
  console.log('tw:', deps['tailwindcss']||'none');
  console.log('db_layer:', deps['prisma']||deps['@prisma/client'] ? 'prisma' :
              deps['drizzle-orm'] ? 'drizzle' : deps['pg']||deps['@neondatabase/serverless'] ? 'raw-pg' : 'unknown');
  console.log('auth:', deps['next-auth']||deps['@auth/nextjs'] ? 'nextauth' :
              deps['@clerk/nextjs'] ? 'clerk' : deps['better-auth'] ? 'better-auth' : 'custom');
  console.log('vitest:', deps['vitest'] ? 'yes' : 'no');
  console.log('playwright:', deps['@playwright/test'] ? 'yes' : 'no');
  console.log('zod:', deps['zod'] ? 'yes' : 'no');
" 2>/dev/null

# App Router vs Pages Router
[ -d "$ROOT/src/app" ] && echo "router=app-src" || \
[ -d "$ROOT/app" ] && echo "router=app-root" || \
[ -d "$ROOT/src/pages" ] && echo "router=pages-src" || \
[ -d "$ROOT/pages" ] && echo "router=pages-root"
```

Cache: `PM` (package manager), `NEXT_VER`, `TW_VER`, `DB_LAYER`, `AUTH_STRATEGY`, `APP_DIR` (path to app/), `HAS_VITEST`, `HAS_PLAYWRIGHT`.

### 2b. Auth guard detection

```bash
# Custom auth guards
grep -rE "requireAuthenticatedSession|requireAdminSession|getServerSession|auth\(\)" \
  $ROOT/src/server $ROOT/src/lib $ROOT/src/app $ROOT/lib $ROOT/app 2>/dev/null | head -10

# Proxy / middleware
ls $ROOT/src/proxy.ts $ROOT/src/middleware.ts $ROOT/middleware.ts 2>/dev/null

# Session/cookie helpers
grep -rE "getSession|verifySession|currentUser" $ROOT/src/lib $ROOT/lib 2>/dev/null | head -5
```

Cache the auth guard function names so §L findings cite them correctly.

### 2c. DB layer patterns

```bash
# Raw pg patterns
grep -rE "db\.query|pool\.query|client\.query|db\.execute" $ROOT/src/server $ROOT/src/lib 2>/dev/null | head -5

# Prisma
ls $ROOT/prisma/schema.prisma 2>/dev/null && head -5 $ROOT/prisma/schema.prisma

# Drizzle
ls $ROOT/drizzle $ROOT/src/db $ROOT/db 2>/dev/null
```

### 2d. Component catalog

```bash
for d in src/components/ui src/components src/ui components/ui components; do
  [ -d "$ROOT/$d" ] && find "$ROOT/$d" -maxdepth 2 -name '*.tsx' ! -name '*.test.tsx' ! -name '*.stories.tsx'
done
```

Build a table of project components (name → import path → what it replaces).

### 2e. Tailwind version + theme

```bash
# v3 vs v4
ls $ROOT/tailwind.config.{ts,js,cjs,mjs} 2>/dev/null && TW_CONFIG_VERSION=3
grep -rl '@theme' $ROOT/src $ROOT/app 2>/dev/null | head -3 && TW_CONFIG_VERSION=4

# Cache tokens
if [ "$TW_CONFIG_VERSION" = "3" ]; then
  grep -A200 'extend:' $ROOT/tailwind.config.* 2>/dev/null | grep -E 'spacing|maxWidth|colors|fontSize' | head -30
else
  grep -A100 '@theme' $ROOT/src/**/*.css $ROOT/app/**/*.css 2>/dev/null | head -40
fi

# Typography utilities in CSS
grep -rE '@layer utilities' $ROOT/src $ROOT/app 2>/dev/null | head -5
```

Apply v4 calc-fallback logic exactly as in §F.

### 2f. Lint + project scripts

```bash
cat $ROOT/package.json | node -e "
  const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
  console.log(JSON.stringify(d.scripts||{}, null, 2));
" 2>/dev/null

# ESLint config
ls $ROOT/eslint.config.{mjs,cjs,js} $ROOT/.eslintrc.{json,js,cjs} 2>/dev/null | head -3
```

Cache lint/typecheck commands for §4.5 and §7.

### 2g. API response helpers

```bash
grep -rE "export (function|const) (ok|badRequest|unauthorized|forbidden|notFound|serverError)" \
  $ROOT/src/lib $ROOT/lib 2>/dev/null | head -10
```

Cache the project's HTTP helper names so §B findings cite them correctly.

### 2h. Read documentation

- `CLAUDE.md` / `AGENTS.md` at root and nested under `src/`, `app/`, `src/server/`.
- `DESIGN.md` — if present, cache color tokens, font choices, spacing rules, and any banned patterns (e.g. em dashes, pure white backgrounds).
- `next.config.{ts,js,mjs}` — detect experimental features, redirects, headers, `output` mode.
- `src/proxy.ts` / `middleware.ts` — route protection config, PROTECTED_ROUTES, ADMIN_ROUTES.

## 3. Short-circuit on irrelevant diffs

**Skip this section entirely when `SCOPE = whole`** — the whole-codebase path always proceeds to §4.

If `SCOPE = diff` and every changed file matches the config glob — `*.json`, `tsconfig*`, `.prettierrc*`, `.eslintrc*`, `*.md`, `.gitignore`, lock files, `next.config.*`, `*.env*` — emit one line and stop:

```
Verdict: n/a — diff is config-only (<N> files). No rules apply.
```

## 4. Gather context

**If `SCOPE = diff`:**
- List changed files with `--find-renames`.
- Read each changed file in full.
- For deletions/renames: `git grep -n <oldName>` to confirm callers updated.
- For route handler changes: open the matching route path and verify `export const runtime` setting.
- For component changes: scan importers to understand usage scope.

**If `SCOPE = whole`:**
- Use the file list from §1 (grep patterns + lint output drive which files to read — see §1 whole-codebase strategy).
- Always read in full: every file under `src/app/api/` (Route Handlers), every `**/actions.ts` (Server Actions), `src/middleware.ts` / `src/proxy.ts`, and key lib files (`src/lib/org-scope.ts` or equivalent auth lib).
- For all other files: run the grep patterns in §5 first, then read only files with hits to confirm line numbers.

## 4.5. Run linter + type checker

Use `$PM run` commands from §2f.

**If `SCOPE = diff`** — run only on changed files:

```bash
MB=$(git merge-base "origin/$BASE" HEAD 2>/dev/null || git merge-base "$BASE" HEAD)
CHANGED_TS=$(git diff --find-renames --name-only "$MB"...HEAD -- '*.ts' '*.tsx' '*.js' '*.jsx' \
  | xargs -I{} sh -c '[ -f "{}" ] && echo "{}"')

# Lint — prefer read-only variant
[ -n "$CHANGED_TS" ] && $PM exec eslint --max-warnings=0 $CHANGED_TS 2>&1 | head -60

# TypeScript — always noEmit
[ -n "$CHANGED_TS" ] && $PM exec tsc --noEmit 2>&1 | head -40
```

**If `SCOPE = whole`** — run on the entire project:

```bash
# Lint entire project
$PM run lint 2>&1 | head -100

# TypeScript — always noEmit
$PM exec tsc --noEmit 2>&1 | head -60
```

In whole-codebase mode, distinguish pre-existing issues from new ones by checking git blame or noting that all findings are current state (not diff-relative). Group lint output by file in the report.

- Exit 0 → `Lint/Types: clean.`
- Errors → verdict ≥ `fix-before-ship`; include under `## Lint` / `## Types` sections.
- Tool crashes → note `Lint: failed — <error>`, continue.

## 5. Checklist

**If `SCOPE = diff`:** flag real issues only in changed code. Do not comment on code that did not change unless a change directly references it.
**If `SCOPE = whole`:** flag real issues anywhere in `src/`. Prioritize Blockers and Suggestions; skip Nits in files with no other findings to keep the report navigable.

Quote `path:line` for every finding. Silence is praise.

---

### A. Next.js App Router structure

The canonical layout for App Router projects:

```
src/
  app/
    (route-group)/         # layout grouping without URL segment
      page.tsx             # Server Component by default
      layout.tsx
      loading.tsx
      error.tsx
    api/
      <resource>/
        route.ts           # Route Handler — GET/POST/PUT/DELETE exports
    globals.css
    layout.tsx             # Root layout
  components/              # Shared UI — project-level primitives
    ui/                    # Generic design-system primitives
  lib/                     # Cross-cutting utilities, helpers, schemas
  server/                  # Server-only: DB queries, service modules, guards
    modules/
      <feature>/
        <feature>.repository.ts   # DB queries
        <feature>.service.ts      # Business logic (optional)
  middleware.ts / proxy.ts # Route protection
```

Flag in new code:
- **Business logic in a `page.tsx`** — data fetching is fine (Server Component), but conditional redirect logic, complex transforms, and DB queries belong in `src/server/modules/<feature>/`.
- **API route logic not in `src/app/api/`** — all Route Handlers must live under `app/api/`.
- **Route Handler that imports UI components** — API routes are server-only; they don't render React.
- **DB query inlined in a Route Handler body** instead of delegated to a repository function. Severity: **Suggestion**.
- **`src/lib/` used for feature-specific code** — `lib/` is for cross-cutting utilities (auth, db, api helpers, schemas). Feature code goes in `src/server/modules/<feature>/` or a `features/` folder.
- **Cross-route shared fetch logic duplicated** — extract to `src/server/modules/<feature>/<feature>.repository.ts`.

#### Route groups

Route groups `(name)/` organize layouts without adding URL segments. New pages in an existing group must live inside the correct group. Flag a page added to the root `app/` that should be under `(app)/` or `(chat)/` (or whichever group the project uses for authenticated surfaces).

#### "Belongs to a feature" heuristic

A function in `lib/` or inline in a route **belongs to module X** when it only operates on X's domain. In the finding, cite the suggested path (e.g., `src/server/modules/maintenance/maintenance.repository.ts`).

---

### B. Route Handlers — clean HTTP boundary

Route Handlers export named functions (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`). They handle: input parsing, auth guard, calling the service/repository, mapping to response, error → HTTP status. **Nothing else.**

Flag:
- **Missing `export const runtime = "nodejs"`** on any Route Handler that uses the DB, OpenAI SDK, or any Node.js-only dep. Without it the route may silently run in the Edge runtime and fail. Severity: **Blocker**.
- **Missing auth guard** on a mutating route (`POST`/`PUT`/`DELETE`/`PATCH`) that handles user data. Call the project's auth guard (`requireAuthenticatedSession()` or equivalent) at the top of the handler. Severity: **Blocker**.
- **Reading `userId` from a request body or query param** instead of the verified session/token. IDOR risk. Severity: **Blocker**.
- **Missing Zod validation** on `POST`/`PUT`/`PATCH` request body. Use `schema.safeParse(body)` and return `badRequest(errors)` on failure. Severity: **Blocker** for user-facing mutations.
- **Returning raw DB rows** (including fields like `password_hash`, `salt`, internal IDs) — map to a safe DTO before returning. Severity: **Blocker** for sensitive fields.
- **`JSON.parse(await req.text())`** when `await req.json()` is available — prefer the built-in.
- **`try/catch` catching `Error` broadly and returning `500`** without logging — at minimum `console.error(e)` before returning `serverError()`. Severity: **Suggestion**.
- **Multiple DB queries in one handler without a transaction** when they must be atomic (e.g., create + deduct credits). Severity: **Blocker** when data integrity is at risk.
- **Missing project HTTP helpers** — use `ok()`, `badRequest()`, `unauthorized()`, `forbidden()`, `notFound()`, `serverError()` from the project's `lib/api.ts` (or equivalent), not manual `new Response(JSON.stringify(...), { status: ... })`. Severity: **Suggestion**.
- **Debug / diagnostic endpoints** shipped in production (`/api/debug`, `/api/dump`, `/api/one-time-*`) — rejected. Use a local script instead. Severity: **Blocker**.
- **CSRF not validated** on state-mutating routes when the project has a CSRF helper — check `src/lib/csrf.ts` or equivalent. Severity: **Blocker** for custom-auth projects.

#### Pagination

- **`LIMIT` / `OFFSET` in raw SQL** without a `cursor`-based option for high-volume lists — cursor pagination avoids race conditions and is more efficient on large tables.
- **In-memory slicing** (`rows.slice(offset, offset+limit)` after loading all rows) — DB must paginate, not JavaScript.
- **Missing stable sort** — sort by `created_at` + `id` (or ULID/sequence), not by user-mutable fields.

#### Rate limiting

Any route that calls an external API (OpenAI, Stripe, email) or is on a hot path must enforce rate limiting. Check if the project has a `rateLimit()` helper (e.g., `src/lib/rateLimit.ts`). Flag its absence on new AI or email routes. Severity: **Blocker** for AI/LLM-calling routes.

---

### C. Server Components vs Client Components

**Default: Server Component.** Add `'use client'` only when the component requires:
- `useState` / `useReducer` / `useContext`
- `useEffect` / lifecycle hooks
- Browser APIs (`window`, `document`, `localStorage`)
- Event handlers (`onClick`, `onChange`, `onSubmit`)
- Third-party libs that depend on the DOM

Flag in new `.tsx` files:
- **`'use client'` with no state, no effects, no event handlers, no browser APIs** — this is a Server Component forced into the client bundle for no reason. Severity: **Suggestion**.
- **`'use client'` that fetches data with `useEffect` + `useState`** when the component has no other client-side interactivity — move fetch to a Server Component parent, pass data as props. Severity: **Suggestion**.
- **A new Server Component that `import`s a client-only dep** (browser-only package, a lib that uses `window`) — will crash at build. Flag the missing `'use client'` or suggest a dynamic import. Severity: **Blocker**.
- **`async` function exported from a `'use client'` file** — async Server Components can't be Client Components. Severity: **Blocker**.
- **Passing non-serializable values (functions, class instances, Dates as objects) as props to Client Components** from Server Components — Next.js requires serializable props across the RSC boundary. Severity: **Blocker**.

#### `'use server'` (Server Actions)

- **Server Action without auth check** that mutates data. Every `'use server'` function that writes to the DB or calls a sensitive service must verify the session. Severity: **Blocker**.
- **Server Action missing Zod validation** on inputs — inputs from forms are user-controlled. Severity: **Blocker**.
- **Using Server Actions for read-only data fetching** — Server Components fetch data directly; Server Actions are for mutations. Severity: **Suggestion**.
- **`'use server'` placed at the file level** when only one function in the file is a Server Action — prefer per-function directive to avoid accidentally exporting other functions as server endpoints. Severity: **Suggestion**.

---

### D. Data fetching patterns

- **`useEffect` + `fetch` in a Client Component** when the data could be fetched in a Server Component parent — restructure to avoid the client-side waterfall. Severity: **Suggestion**.
- **Sequential `await` of independent fetches** in a Server Component — parallelize with `Promise.all([...])`:
  ```tsx
  // Bad
  const user = await getUser(id);
  const posts = await getPosts(id);

  // Good
  const [user, posts] = await Promise.all([getUser(id), getPosts(id)]);
  ```
  Severity: **Suggestion**.
- **Missing `loading.tsx`** for a route that has a slow data fetch — Next.js uses this for Suspense streaming. Severity: **Nit**.
- **`fetch()` without cache options in a Server Component** when the data should be cached or revalidated — decide between `{ cache: 'force-cache' }`, `{ next: { revalidate: N } }`, or `{ cache: 'no-store' }`. Severity: **Suggestion**.
- **`revalidatePath()` / `revalidateTag()` called without a matching `fetch` cache tag** — the revalidation is a no-op. Severity: **Suggestion**.

---

### E. Auth — guards, sessions, IDOR prevention

All auth findings are **Blocker** unless noted.

- **Mutating route handler without calling the auth guard** at the top of the function.
- **`userId` taken from request body, query param, or path segment** instead of the verified session. IDOR — a caller can impersonate any user by supplying a different ID.
- **DB query without `userId` filter** on user-scoped data — cross-tenant data leak.
- **Admin route** without admin-role check (`requireAdminSession()` or equivalent).
- **Session cookie without `httpOnly: true`** — allows XSS access to the session.
- **Logging tokens, raw passwords, or session secrets** — even to `console.error`. Severity: **Blocker**.
- **Unsanitized `?from=` / `?next=` redirect** after login — validate the redirect target is a same-origin path before using it, or a malicious `from=https://evil.com` redirects users off-site. Severity: **Blocker** if unvalidated.

#### CSRF

For custom-auth projects that use cookie-based sessions: mutating Route Handlers must validate the `Origin` / `Referer` header or a CSRF token. If the project has `src/lib/csrf.ts` (or equivalent), call it. Flag its absence on new `POST`/`PUT`/`DELETE` routes.

---

### F. Tailwind — verified tokens, idiomatic shorthand

Detect v3 vs v4 from §2e. Apply:

- **Tailwind v4 with calc fallback intact** (default `--spacing` = 0.25rem not overridden): any pixel value that is a multiple of 4 (or half-step: 2, 6, 10, 14 px → 0.5, 1.5, 2.5, 3.5) can be expressed as a token. `top-[7px]` → `top-1.75`, `max-h-[480px]` → `max-h-120`. Severity: **Suggestion**.
- **Tailwind v3**: only suggest tokens that exist in `theme.extend.*`.

Common replacements:

| Anti-pattern | Replace |
| --- | --- |
| `w-8 h-8` | `size-8` |
| `mt-4 mb-4` | `my-4` |
| `pt-2 pb-2 pl-4 pr-4` | `py-2 px-4` |
| `flex flex-row` | `flex` |
| `border border-solid` | `border` |
| `text-[14px]` | `text-sm` |
| `rounded-[8px]`, `rounded-[12px]` | `rounded-lg`, `rounded-xl` |
| `font-[500]` | `font-medium` |

**Inline `style={...}`** for Tailwind-expressible properties → move to `className`. Reserve `style` for truly dynamic values (JS-computed positions, CSS variables from state).

**Hex colors** (`bg-[#fef2f2]`, `style={{ color: '#111' }}`): map to nearest stock Tailwind token or project theme token. If used 2+ times, move to `tailwind.config` / `@theme` as a named token.

**Project typography utilities** (classes in `@layer utilities` like `.label-xs`, `.paragraph-sm`): if a raw `text-*/leading-*/font-*` combo exactly matches a project utility, use the utility. Severity: **Suggestion**.

**DESIGN.md compliance** — if a `DESIGN.md` is present, cross-check:
- Background colors: flag `bg-white` if the project uses a warm cream background.
- Accent colors: flag non-project CTAs.
- Banned patterns: flag em dashes (`—`) in JSX text and string literals if the project bans them.
- Radius: flag `rounded` if `rounded-xl` is the project default for cards.

---

### G. Feature-based structure (frontend)

New UI code belongs in a feature folder or a clearly scoped location:

```
features/<feature>/
  components/       # or flat components.tsx if single component
  hooks/            # or hooks.ts if single hook module
  constants.ts      # config literals — not module-top of hook/component files
  utils.ts
  types.ts
```

Or within the `app/` directory co-located with the route it serves.

Flag:
- **Feature-specific component dropped in `src/components/`** when it's only used by one feature — move next to the feature.
- **API call helpers inlined in a component** — extract to `src/server/modules/<feature>/<feature>.repository.ts` (server) or a dedicated client fetch helper.
- **`const EMPTY = { ... }`, `const MAX_X = 99`, or other config literals** at the top of a hook or component file — move to `<feature>/constants.ts` (or a feature-level constants module). Module-scope is not the destination; a constants module is. Severity: **Suggestion**.
- **`constants/index.ts` holding one module's worth of code** — collapse to `constants.ts`.

#### One file → one component; hooks splitting

- A `.tsx` file should export one primary component.
- `.map(...)` blocks > 10 lines or list+empty-state ternaries → extract as `<FeatureList />` / `<FeatureEmptyState />`.
- New hooks file with 3+ hooks of mixed responsibility → split into `useFeatureQuery.ts` (read + invalidator) + `useFeatureMutations.ts` (mutations grouped).

---

### H. Components — use what the project already has

Before writing anything, check if the project already provides it.

- **Raw `<button>` when a `Button` component exists** → use the project component. If variants don't fit, use `className` overrides. Severity: **Suggestion**.
- **Raw `<input>` / `<select>` when project wrappers exist** → same.
- **Re-implementing a dialog/popover** when `@radix-ui/react-*` (or project Dialog) is installed.
- **Re-implementing `cn()` / `classNames(...)`** — use the project utility from `lib/utils.ts`.
- **Inline route template strings** (`\`/profile/${id}\``, `navigate(\`/chat/${id}\`)`) in new feature code → extract to a `routes.ts` helper. Severity: **Suggestion**.
- **Icons from a non-canonical library** — detect the project's icon library (check `package.json` for `lucide-react`, `@heroicons/react`, etc.) and flag imports from other libraries. Suggest the equivalent name in the canonical library.

---

### I. TypeScript discipline

Flag newly-added:
- `any`, `as any`, `Function`, `Object`, `{}` as a type.
- `as unknown as X` double-casts.
- `!` non-null assertions on values from request params, cookies, or API responses.
- `@ts-ignore` / `@ts-expect-error` without an explanatory comment.
- `foo?: T | undefined` → `foo?: T`.
- **`Record<string, unknown>` or `any` for a typed API response** — suggest a discriminated union or Zod-inferred type.
- **Missing return type annotation** on a Route Handler export or a Server Action.
- **`params` typed as `{ id: string }` but accessed as `params.id` without `await`** — in Next.js 15+, `params` and `searchParams` are Promises; access via `const { id } = await params`. Severity: **Blocker** for Next.js 15+.

---

### J. Zod validation

- **Request body parsed with `await req.json()` and used without Zod validation** → add `schema.safeParse(body)` guard. Severity: **Blocker** for any mutation endpoint.
- **Zod schema defined inline in the Route Handler** → move to `src/lib/schemas.ts` (or feature-level `schemas.ts`) so it can be shared and tested.
- **`schema.parse(body)` (throws) instead of `schema.safeParse(body)` (returns `{ success, data, error }`)** in a Route Handler — unhandled Zod errors become 500s instead of 400s. Severity: **Blocker**.
- **Missing cross-field validation** (`superRefine` / `refine`) when the schema has conditional required fields. Severity: **Suggestion**.

---

### K. Database patterns

#### Raw PostgreSQL (pg / @neondatabase/serverless)

- **SQL string interpolation** (`db.query(\`SELECT * WHERE id = ${id}\``) — SQL injection. Always use parameterized queries: `db.query('SELECT * WHERE id = $1', [id])`. Severity: **Blocker**.
- **No LIMIT on a user-table query that can return many rows** — always paginate. Severity: **Blocker** for new list endpoints.
- **Multiple related writes (INSERT + UPDATE) without a transaction** — wrap in `BEGIN` / `COMMIT` via the project's transaction helper. Severity: **Blocker** when atomicity matters.
- **`SELECT *` in production queries** — select only needed columns to avoid leaking fields like `password_hash`. Severity: **Suggestion** (Blocker if sensitive fields are present).
- **Naive datetime comparison** ignoring timezone — always store/compare in UTC; use `timestamptz` columns and `new Date().toISOString()` in Node.

#### Prisma

- **`findMany()` without `take`** on a model that can grow unboundedly. Severity: **Blocker** for new list endpoints.
- **N+1**: `include` on relations accessed inside a loop — use `include: { relation: true }` at the query level.
- **`create()` + `update()` in the same request** without a transaction (`$transaction([...])`) when atomicity is needed. Severity: **Blocker**.

#### Drizzle

- **`.all()` without `.limit()`** on a table that can grow. Severity: **Blocker**.
- **Raw `sql\`...\`` template** with unparameterized inputs. Severity: **Blocker**.

---

### L. Middleware / proxy.ts

- **New protected route not added to `PROTECTED_ROUTES`** (or equivalent config) — unauthenticated users can access it. Severity: **Blocker**.
- **New admin route not added to `ADMIN_ROUTES`** — same. Severity: **Blocker**.
- **`AUTH_ONLY_ROUTES` missing a route that should redirect logged-in users** (e.g., `/login`, `/register`). Severity: **Suggestion**.
- **Middleware importing heavy server-side dependencies** — Next.js middleware runs in the Edge runtime by default (unless `export const config = { runtime: 'nodejs' }`). Heavy imports (pg, OpenAI) will fail. Severity: **Blocker** if detected.

---

### M. Performance & bundle

- **`import` of a large library used only in one component without `next/dynamic`** — consider dynamic import with `{ ssr: false }` for heavy client-only libs. Severity: **Suggestion**.
- **`<img>` instead of `next/image`** — no automatic optimization or lazy loading. Severity: **Suggestion**.
- **`@next/font` / `next/font` not used** for custom fonts — self-hosted fonts loaded via `<link>` don't get the layout-shift optimization. Severity: **Nit**.
- **`export const dynamic = 'force-dynamic'`** on a route that has no per-request personalization — it disables caching unnecessarily. Severity: **Suggestion**.
- **`export const revalidate = 0`** (equivalent to `force-dynamic`) on a static page — review intent. Severity: **Suggestion**.
- **Large Client Component that wraps a Server Component** — unnecessary client boundary bloats the bundle. Flag for extraction. Severity: **Suggestion**.

---

### N. Loops, utilities, and dead code

- **`array.forEach` used to build an array** → `array.map`.
- **`for...of` with no `await`, `break`, or `continue`** → `forEach`. Severity: **Suggestion**.
- **Same logic duplicated across 2+ Route Handlers** → extract to a repository or utility function.
- **Unused exports / unused locals / commented-out code** — flag. Severity: varies (Nit for locals if covered by linter).
- **`console.log` / `debugger` left in** — Severity: **Blocker** for production paths; **Suggestion** otherwise.
- **Stale TODO/FIXME** without a ticket reference in new code. Severity: **Nit**.
- **Merge conflict markers** (`<<<<<<<`, `=======`, `>>>>>>>`) anywhere in the diff. Severity: **Blocker**.

---

### O. Testing

Detect test runner from §2a.

- **New Route Handler with no corresponding test** — Severity: **Suggestion** by default; **Blocker** if the handler:
  - Mutates user data (credits, billing, user profile),
  - Implements auth/permission checks,
  - Calls an external API (Stripe, OpenAI) with side effects.
- **New Server Action with no test** — same severity rules.
- **Vitest test mocking the DB with `vi.mock`** instead of using a test DB / fixture — acceptable pattern (mock at boundaries); just ensure the mock actually reflects the DB schema.
- **Playwright test that hits a real external API** — mock via `page.route()`. Severity: **Suggestion**.
- **Missing E2E coverage** for a new authenticated route — add to the Playwright suite. Severity: **Suggestion**.
- **`fetch` called directly in a unit test** without mocking — tests should not hit real endpoints. Severity: **Blocker**.
- **Time-sensitive assertions** (`expect(date).toBe(new Date(...))`) without time control (`vi.useFakeTimers`) — flaky. Severity: **Suggestion**.

Tests are **never** auto-applied — always move to **Needs you**.

---

### P. Accessibility & semantic HTML (new interactive surfaces)

For every **new interactive surface** in the diff:

- **`<div onClick>` / `<span onClick>` without `role="button"`, `tabIndex={0}`, and keyboard handler** — keyboard inaccessible. Severity: **Blocker** if it gates an important action.
- **`<p>` used as a heading** near clickable items — use `<h2>`/`<h3>` or a heading primitive.
- **Relative timestamps** not wrapped in `<time dateTime={iso}>`. Severity: **Suggestion**.
- **`outline-none`** without a `focus-visible:` replacement style. Severity: **Suggestion**.
- **Missing `alt`** on `<img>`. Decorative images get `alt=""`. Severity: **Blocker**.
- **Low-contrast text** — `text-neutral-400` on white fails WCAG AA. Severity: **Suggestion**.
- **Color-only state indicator** — needs a secondary signal. Severity: **Suggestion**.
- **Missing `aria-hidden="true"`** on decorative icons with sibling text. Severity: **Nit**.

---

### Q. Package hygiene

If `package.json` changed:

```bash
git diff --find-renames <range> -- package.json | grep -E '^\+' | grep -E '"[^"]+":\s*"' | grep -v '^+++'
```

- Added but not imported — flag.
- Added when an existing dep covers it — flag.
- Heavyweight dep for a trivial use case — flag with lighter alternative.
- Dev dep added to `dependencies` (should be `devDependencies`) — flag.
- Removed dep still imported — flag.

---

## 5.5. Pre-emit self-audit

Before printing the report, walk this checklist against the diff. Each item requires a grep or scan — not a mental check.

- [ ] **§A** — Every new Route Handler in the diff: `export const runtime = "nodejs"` present?
- [ ] **§B** — Every `POST`/`PUT`/`DELETE`/`PATCH` Route Handler: auth guard at top?
- [ ] **§B** — Every `POST`/`PUT`/`PATCH` Route Handler: Zod validation on body?
- [ ] **§C** — Every new `.tsx` file: does `'use client'` appear? If yes, does it actually need it (state, effects, event handlers, browser APIs)?
- [ ] **§C** — Every new `'use server'` function: auth check present? Zod validation present?
- [ ] **§E** — Every new Route Handler that queries user data: `userId` comes from the session, not from request input?
- [ ] **§E** — Every new Route Handler that queries user data: WHERE clause includes `userId`?
- [ ] **§F** — Every `bg-white` in new code: does the project use a warm background (check DESIGN.md)? Flag if so.
- [ ] **§F** — Every arbitrary value (`top-[7px]`, `bg-[#fef2f2]`): tokenized form suggested?
- [ ] **§G** — Every `const UPPER_SNAKE = <literal>` at the top of a hook/component file: moved to a constants module?
- [ ] **§H** — Every raw `<button>`: project Button component suggested?
- [ ] **§H** — Every icon import: from the canonical library?
- [ ] **§H** — Every inline route template string (``/route/${id}``): routes helper suggested?
- [ ] **§I** — Every `params.id` access: awaited in Next.js 15+ context?
- [ ] **§J** — Every `await req.json()`: Zod safeParse applied?
- [ ] **§K** — Every SQL string: parameterized (no interpolation)?
- [ ] **§K** — Every `SELECT *`: returns sensitive fields (password_hash, salt, etc.)?
- [ ] **§K** — Every new list DB query: has LIMIT?
- [ ] **§L** — Every new route: added to PROTECTED_ROUTES / ADMIN_ROUTES if auth-required?
- [ ] **§N** — Any `for...of` in the diff without `await`/`break`/`continue`: flagged for `forEach`?
- [ ] **§N** — Any merge conflict markers: `git grep -nE '^(<{7}|={7}|>{7})'`?
- [ ] **§O** — New Route Handler for Stripe/OpenAI/email: rate limiting applied?
- [ ] **§P** — Every `<div onClick>`: keyboard handler + role + tabIndex present?

If any box is unchecked, do that scan now before emitting the report.

---

## 6. Output format

```
# nextjs-code-review

**Mode:** <review | self-review>
**Scope:** <diff only | whole codebase> — <N> files
**Branch:** <current> → **Base:** <base>   ← omit this line when SCOPE = whole
**Stack:** Next.js <version> · <PM> · <DB_LAYER> · <AUTH_STRATEGY>
**Linter coverage:** <skipped categories if any>
**Lint/Types:** <clean | N issues | failed to run>
**Verdict:** <ship | fix-before-ship | needs-rework>

## Blockers
- `path/to/file.ts:42` — <one-line problem>. Fix: <one-line fix>.

## Suggestions
- `path/to/file.tsx:10` — <one-line problem>. Fix: <one-line fix>.

## Nits
- `path/to/file.tsx:88` — <one-line problem>.

## Package hygiene
- (only if package.json changed)

## One-time tip
- (optional; only when 3+ Tailwind anti-patterns or 3+ of one mechanical class)

## Needs you
- (judgment-class findings the apply phase will not auto-apply)
```

Rules:
- Group by severity, not file.
- Each line: `path:line` + concrete fix.
- Omit empty categories.
- If clean: `**Verdict:** ship — no issues found in <N> files.`

---

## 7. Offer to apply (self-review mode only)

Skip entirely when `MODE === 'review'`. After the report, call `AskUserQuestion`:

```json
{
  "questions": [
    {
      "header": "Apply fixes",
      "question": "Apply the findings to the diff in place?",
      "multiSelect": false,
      "options": [
        { "label": "All", "description": "Mechanical + structural fixes; judgment items → Needs you." },
        { "label": "Blockers only", "description": "Apply only Blockers." },
        { "label": "No", "description": "Leave code untouched." }
      ]
    }
  ]
}
```

### Categorize before applying

**Mechanical** (auto-apply):
- Add `export const runtime = "nodejs"` to Route Handler files that use DB/OpenAI.
- `'use client'` removal when the component has no client-side need.
- Tailwind shorthand replacements (`w-8 h-8` → `size-8`, etc.).
- Inline `style={{...}}` → `className` for Tailwind-expressible props.
- `schema.parse` → `schema.safeParse` in Route Handlers.
- Raw `<button>` → project `Button` where the API matches.
- Icon import → canonical library.
- `console.log` removal.
- Merge conflict marker removal (when resolution is obvious).
- `params.id` → `(await params).id` for Next.js 15+.
- `SELECT *` → specific column list (only when the safe columns are obvious).
- Parameterize SQL string interpolation where the parameterized form is a one-liner.

**Structural** (apply with care):
- Move Route Handler logic to a repository function.
- Add auth guard (`requireAuthenticatedSession()`) to unguarded mutation routes.
- Add Zod validation block to unvalidated Route Handlers.
- Add new route to `PROTECTED_ROUTES` / `ADMIN_ROUTES` in `src/proxy.ts`.
- Extract a constants module from module-top literals.
- Move feature-specific component from `src/components/` to the feature directory.
- After file moves: `git grep` to update all importers; run `tsc --noEmit` to verify.

**Judgment** (never auto-apply → Needs you):
- Refactoring a Server Component to parallel-fetch data.
- Transaction wrapping across multiple DB tables.
- Redesigning a page-level fetch to use Suspense streaming.
- Adding rate limiting to an existing route.
- Database schema changes.
- Auth strategy changes.
- Test scaffolding.
- DESIGN.md violations requiring visual decisions.

### Constraints while applying

- Edit files in place. Never `git add`, `git commit`, `git push`, `git stash`.
- After any structural file move: `git grep` all importers and update them.
- After all edits: run `$PM exec tsc --noEmit` on changed files. If it fails, surface errors inline.
- Iterate once after first apply: re-walk §5.5 self-audit against new state. Surface new findings under `## Surfaced after apply`.
- Print summary: `Applied <N> fixes across <M> files. Types: <pass/fail>.` List Needs-you items.

If user picks **No**: `Left untouched. Re-run /nextjs-code-review after addressing findings.`

---

## 8. Don't do

- **Diff mode only:** Don't comment on code that didn't change (unless a change directly references it). Don't suggest large refactors outside the diff.
- **Whole-codebase mode:** Don't attempt to read every source file in full — use grep patterns and lint output to triage; read only flagged files. Don't produce a finding for every file; group and summarize when the same issue repeats across many files.
- Don't run migrations, `pnpm dev`, or any live service call.
- Don't open a PR, commit, push, or stash.
- Don't generate test scaffolding automatically (→ Needs you).
- Don't apply DESIGN.md visual changes without user confirmation.
