---
name: code-quality
version: 0.1.0
description: |
  Whole-codebase code-quality audit. Finds dead code, duplication, trimmable code,
  readability issues, deviations from repo standards, and import-order problems —
  produces a triage report with severity + confidence, then fixes confirmed items
  atomically and verifies with the project's own gates. Use when asked to
  "audit code quality", "find dead code", "clean up the codebase",
  "remove duplication", "code quality scan", "tidy up", or "trim dead weight".
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
triggers:
  - audit code quality
  - find dead code
  - code quality scan
  - clean up the codebase
  - remove duplication
  - trim dead weight
---

# /code-quality — Whole-Codebase Audit + Fix Loop

Systematic, evidence-based pass for finding and removing dead code, duplication,
and readability rot — then fixing what the user confirms, verified by the
project's existing quality gates (lint + typecheck + tests).

**Iron rules**
1. **Detect, don't prescribe.** Use the project's own tooling first (`pnpm lint`,
   `tsc --noEmit`, `knip`, `jscpd` if present). Heuristics are fallbacks.
2. **Confirmed-only fixes.** Never refactor speculatively. Show evidence, get a
   yes, then change one thing.
3. **Atomic changes.** One concern per edit. Re-run gates after each fix group.
4. **Respect repo voice.** Read `CLAUDE.md`, `eslint.config.*`, `.editorconfig`,
   `tsconfig.json` first — match what's already enforced; do not invent new style.
5. **Never commit or push.** Even when the user says "fix everything." Commits
   are an explicit step the user takes.

---

## Phase 0 — Detect tooling and conventions

Run these reads/checks in parallel and remember the results for later phases.

```bash
# Project root + manager
git rev-parse --show-toplevel 2>/dev/null
test -f pnpm-lock.yaml && echo "pm=pnpm" || (test -f bun.lock && echo "pm=bun" || (test -f yarn.lock && echo "pm=yarn" || echo "pm=npm"))

# Available quality tools — anything that returns a path means it's installed
for tool in knip jscpd ts-prune ts-unused-exports depcheck madge biome prettier eslint tsc oxlint; do
  command -v "$tool" >/dev/null 2>&1 && echo "have:$tool"
done
# Also check node_modules/.bin
for tool in knip jscpd ts-prune ts-unused-exports depcheck madge biome prettier eslint oxlint; do
  test -x "node_modules/.bin/$tool" && echo "have-local:$tool"
done

# Standard project files to read for conventions
ls CLAUDE.md AGENTS.md eslint.config.* .eslintrc* .prettierrc* .editorconfig tsconfig.json knip.json knip.ts biome.json 2>/dev/null
```

Read every config file that exists. Pull from `CLAUDE.md`:
- Banned syntax / lint-enforced rules
- Project-specific anti-patterns (the human-curated list of things lint can't catch)
- Quality-gate commands (the exact lint / typecheck / test invocations)
- File-path conventions
- Helper utilities people are supposed to reuse instead of rolling their own

If `CLAUDE.md` has an "Anti-patterns" section, **promote those checks to CRITICAL**
in the report — they reflect bugs that have already happened in this codebase.

---

## Phase 1 — Scope

Use `AskUserQuestion` once. Default to the smallest useful scope.

**Question:** "What scope should I audit?"
- A) Whole repository (full audit, slowest, most thorough)
- B) Files changed vs `main` / `master` (PR-style)
- C) A specific path (you'll provide it)
- D) Currently-staged files only

If C, ask a follow-up text question for the path. Resolve to absolute, verify it
exists, fail fast if not.

For B, compute `git diff --name-only --diff-filter=ACMR <base>...HEAD` where
`<base>` is `main` if it exists else `master`. Filter to files that still exist.

Save scope to a session variable `SCOPE_FILES` — a newline-separated list of
absolute paths. All discovery in Phase 2 reads from this list.

---

## Phase 2 — Discovery (parallel where possible)

Run these as a batch. Each produces a list of `{file, line, kind, evidence,
severity, confidence, suggested_fix}` findings. Keep the output structured so
Phase 3 can group and de-dupe.

### A. Dead code

Order of preference:
1. **`knip`** if installed — `knip --reporter json --no-progress` (best signal).
   Categorizes unused files, exports, deps, types, enum members.
2. **`ts-unused-exports tsconfig.json`** — second-best for TS-only.
3. **`ts-prune`** — legacy but still works on TS.
4. **Heuristic fallback** for any language: for each exported symbol, grep the
   rest of the repo for an import of that symbol's source path or named export.
   No hits → candidate. Confidence: medium (false positives on dynamic imports,
   reflection, framework conventions like Next.js route files / `page.tsx` /
   `route.ts` / `layout.tsx` / `not-found.tsx`).

**Skip rules** — do NOT flag as dead:
- Next.js convention files: `page.*`, `layout.*`, `route.*`, `not-found.*`,
  `loading.*`, `error.*`, `default.*`, `template.*`, `middleware.*`,
  `global-error.*`, `opengraph-image.*`, `icon.*`, `apple-icon.*`, `sitemap.*`,
  `robots.*`, `manifest.*`
- Test files — `*.test.*`, `*.spec.*`, files under `tests/`, `__tests__/`, `e2e/`
- Storybook: `*.stories.*`
- Type-only files re-exported by an `index.ts` barrel
- Anything imported by a string template (search for the basename as a literal
  before flagging)
- Files declared in `package.json` `exports` / `bin` / `main`

### B. Duplication

1. **`jscpd`** if installed — `jscpd --min-lines 6 --min-tokens 50 --reporters json --output .jscpd-report --silent <SCOPE_FILES>`.
   Filter out test fixtures and snapshots.
2. **Fallback heuristic** — for each function ≥ 8 lines, normalize whitespace
   and identifiers to placeholders, hash, and group by hash. Report groups
   with count ≥ 2. Cap at top 30 groups by total LOC saved.

For each duplication group, report **lines saved if extracted** so the user
can prioritize.

### C. Trimmable code (same behavior, less code)

Run lint with these specific rules surfaced (don't auto-fix yet):
- `no-useless-return`, `no-useless-concat`, `no-useless-rename`, `no-useless-catch`
- `prefer-const`, `prefer-template`, `prefer-arrow-callback`,
  `prefer-object-spread`, `prefer-spread`, `prefer-rest-params`
- `no-redundant-await`, `no-await-in-return` (judgment: sometimes intentional)
- `no-else-return`, `no-lonely-if`, `no-negated-condition`
- `no-empty`, `no-empty-function`, `no-empty-pattern`
- Dead branches: `no-constant-condition`, `no-unreachable`
- Wrappers around stdlib: `prefer-includes`, `prefer-string-starts-ends-with`
- Useless type assertions (TS): `@typescript-eslint/no-unnecessary-type-assertion`,
  `no-unnecessary-condition`, `no-unnecessary-type-arguments`

Heuristics:
- Functions that just delegate to another function with the same args — flag
  for inlining unless they're a public API boundary.
- `if (x) return true; else return false;` patterns.
- Variables used exactly once, declared > 3 lines from use.
- Try/catch blocks that just rethrow.

### D. Readability

Pure heuristics — surface, don't auto-fix. Each is a *suggestion*.

| Signal | Threshold |
|---|---|
| File length | > 400 LOC (warn), > 700 (high) |
| Function length | > 60 LOC (warn), > 120 (high) |
| Cyclomatic complexity | > 10 (warn), > 20 (high) — use eslint `complexity` rule |
| Nesting depth | > 4 (warn), > 6 (high) — use eslint `max-depth` |
| Parameter count | > 4 (warn), > 7 (high) — use eslint `max-params` |
| Single-letter identifier outside `(i, j, k, x, y, z, e, t)` in loops/lambdas | warn |
| Magic number not 0/1/-1/2 in non-test code | warn |
| Comment block > 5 lines describing WHAT (not WHY) | suggest delete |
| TODO / FIXME / XXX older than 6 months (git blame) | surface |

Run a quick eslint pass with these rules enabled inline if not in the project
config:

```bash
pnpm exec eslint --no-eslintrc --rule '{"complexity":["warn",10],"max-depth":["warn",4],"max-params":["warn",4],"max-lines-per-function":["warn",60],"max-lines":["warn",400]}' --format json <SCOPE_FILES>
```

(Use the project's resolver if possible; this `--no-eslintrc` form is a fallback
when the project doesn't enforce these.)

### E. Standards / lint / format / types

Authoritative gates — run them as the project defines them.

```bash
# Use exact commands from CLAUDE.md if present, else infer:
pnpm lint
pnpm exec tsc --noEmit
test -f .prettierrc && pnpm exec prettier --check .
```

Every error here is **CRITICAL** — these are already-enforced rules. Group by
rule and file count.

### F. Imports — ordering, top-of-file, unused

The user explicitly cares about this category.

1. **Top-of-file check** — for each source file, find the first non-import,
   non-comment, non-`"use strict"`, non-`"use client"`, non-`"use server"`,
   non-shebang line. Any `import` or top-level `require(...)` after that line
   is a finding. (Inline `await import(...)` for code-splitting is allowed —
   distinguish lazy/dynamic imports from misplaced static ones.)

   Quick grep:
   ```bash
   pnpm exec eslint --no-eslintrc --rule '{"import/first":"error"}' --plugin import <SCOPE_FILES> 2>/dev/null
   # Fallback if no import plugin:
   awk '/^import |^const .* = require\(/ {if (seen_code) print FILENAME":"NR": "$0} /^[^[:space:]/]/ && !/^import / && !/^const .* = require\(/ && !/^"use / && !/^#!/ {seen_code=1}' <files>
   ```

2. **Unused imports** — eslint `no-unused-vars` / `@typescript-eslint/no-unused-vars`
   with `args: "all"`, `varsIgnorePattern: "^_"`.

3. **Import order** — `import/order` (groups: builtin, external, internal,
   parent, sibling, index). Surface if the project doesn't already enforce it;
   ask the user before turning it on.

4. **Duplicate imports** — `import/no-duplicates`.

5. **Side-effect imports without comment** — `import "./foo"` with no neighbor
   explaining why. Surface, don't auto-fix.

### G. Project-specific anti-patterns

For each item in `CLAUDE.md`'s anti-patterns / helpers section, write a
targeted grep. Report matches as **HIGH** (these are documented bug sources).

Example for the kablan repo (read CLAUDE.md and adapt — don't hardcode):
```bash
# key={index} on a dynamic list
rg -n 'key=\{(i|idx|index|n|k)\}' src/

# setTimeout without cleanup hint nearby
rg -n -A3 '\bsetTimeout\(' src/ | rg -B1 -v 'clearTimeout|useDelayedAction|return ?\(\) =>'

# Unsanitized return-to params
rg -n '(searchParams\.get\(.(from|next|returnTo).\)|[?]from=|[?]next=|[?]returnTo=)' src/ | rg -v 'sanitizeReturnTo'

# Manual SQL transaction against pooled proxy
rg -n 'db\.query\("BEGIN"\)' src/

# Banned syntax (em dash here, but generally read CLAUDE.md)
rg -n '—' src/
```

### H. Dependencies (bonus)

If `depcheck` is installed: run it for unused deps. Otherwise skip — easy to
get wrong.

```bash
test -x node_modules/.bin/depcheck && pnpm exec depcheck --json
```

If `madge` is installed: check circular deps.

```bash
test -x node_modules/.bin/madge && pnpm exec madge --circular --extensions ts,tsx src
```

---

## Phase 3 — Triage report

Write a structured report to `.claude/code-quality-report.md` (relative to repo
root). Format:

```markdown
# Code Quality Report — <ISO date> — scope: <A/B/C/D>

**Gates** — lint: <pass|N errors>, tsc: <pass|N errors>, tests: <pass|N failing>

## CRITICAL (n)
Lint/type/test failures + project-specific anti-patterns from CLAUDE.md.
Listed individually with file:line.

## HIGH (n)
Dead exports + dead files (high-confidence). Heavy duplication groups
(≥ 30 LOC saved). Functions over the high-tier readability thresholds.

## MEDIUM (n)
Trimmable code, lower-confidence dead exports, smaller duplication, readability
warnings, import-order issues.

## LOW (n)
Stylistic/nitpick — magic numbers, single-letter names, stale TODOs.

## Findings (one per line, grep-friendly)
<file>:<line>  <severity>  <kind>  <one-line description>  conf=<H|M|L>
```

Print a one-screen summary to chat:
- Total findings by severity
- Top 5 highest-impact items (by LOC saved or bug-risk)
- Path to the full report
- Then ask the user how to proceed (Phase 4).

---

## Phase 4 — Fix loop

Use `AskUserQuestion`:

**Question:** "How should I proceed?"
- A) Fix all CRITICAL + high-confidence HIGH (recommended)
- B) Fix everything ≥ MEDIUM
- F) Fix everything (all severities — CRITICAL + HIGH + MEDIUM + LOW)
- C) Walk through findings one by one
- D) Just fix category X (then ask which)
- E) Stop here — report only

For option F, apply all findings in order of severity (CRITICAL first, then HIGH,
MEDIUM, LOW). Batch trivial edits of the same kind (e.g. all Readonly<> wraps,
all eslint-disable removals) and summarize each batch before applying.

For each fix:
1. **Show the diff first.** Read the file, show the user the planned change in
   plain text (file:line + before/after) before applying. For batches of ≥ 5
   trivial edits in the same category, summarize the batch instead of each one.
2. **Apply via `Edit`.** Never `Write` whole files for a fix — too easy to lose
   adjacent edits.
3. **Verify per-file.** After edits to a file, run lint + tsc on that file (or
   on the project if per-file isn't possible).
4. **Bail on red.** If a fix breaks the gates, revert with `git restore <file>`,
   mark the finding `failed-fix` in the report, and continue.

**Dead code removal — extra caution:**
- Before deleting a file/export, do one more grep for the basename as a string
  literal (catches dynamic require, route registration, env-driven imports).
- For removed files in `src/app/**`, double-check it's not a Next.js route
  convention.
- Show the user every file you're about to delete in a single batch and ask
  for confirmation.

**Duplication extraction:**
- Don't extract automatically unless the duplicated block is mechanically
  identical and the call sites are in the same module / closely-related modules.
- Cross-module extraction needs a name and a home — ask the user before
  creating new files.

---

## Phase 5 — Verify

Run the full project gates one more time:

```bash
pnpm lint && pnpm exec tsc --noEmit && pnpm test
```

If anything fails: report what's red, leave it red, do not bypass.

If all green: print a delta summary —
- Files touched: N
- Lines removed: -N (this is the headline metric for this skill)
- Lines added: +N
- Findings resolved: N / total
- Findings remaining: N (link to updated report)

---

## Phase 6 — Hand back

**Do not commit.** Per repo policy in CLAUDE.md (and as a general default for
this skill), end with:

> "All edits applied and verified. Nothing has been committed. Review with
> `git diff` and commit when you're ready — or tell me to."

If the user says commit, group fixes into logical commits by category (one
commit per: dead code removal, duplication extraction, trim, readability,
import order, anti-pattern fixes). Use the repo's commit-message style (read
recent `git log`).

---

## Notes / pitfalls to avoid

- **TypeScript declaration merging** can hide "unused" exports — types may be
  referenced only in `.d.ts` files or via JSDoc `@type` tags. Search those too.
- **Next.js App Router** registers files by convention, not by import. Always
  apply the skip-list in Phase 2A.
- **Barrel files** (`index.ts` re-exports) confuse some dead-code tools.
  `knip` handles them; older tools don't.
- **i18n keys** loaded from JSON look unused to static analyzers — never
  delete a `.json` file flagged by knip without reading it first.
- **Stripe / webhook handlers / cron handlers** are entered by external
  callers, not by import. Trust the file-name skip list and the user's nod.
- **Test fixtures** — duplication detectors will scream about them. Filter
  out `**/fixtures/**`, `**/__fixtures__/**`, `**/snapshots/**`,
  `**/__snapshots__/**`, `e2e/**/mocks*`.
- **Generated files** — `.next/`, `dist/`, `build/`, `coverage/`, `*.d.ts`
  in `node_modules/.next/types/` should never appear in findings.
- **Don't fight Prettier.** If formatting is enforced by prettier, never
  hand-format; let prettier own it.
- **Readability warnings are suggestions, not orders.** A 200-line function
  in a parser or state machine may be the right shape. Surface it; let the
  user judge.

---

## When NOT to use this skill

- A diff-scoped pre-merge check → use `/review` instead.
- A metrics dashboard / trend tracking → use `/health`.
- Single-file simplification of code you just wrote → use `/simplify`.
- Bug hunting → use `/bug-finder-dude` or `/investigate`.
- Architecture / design rot → use `/plan-eng-review`.

This skill is for **periodic tidying of the whole repo** — pulling out dead
weight that has accumulated and lint can't catch on its own.
