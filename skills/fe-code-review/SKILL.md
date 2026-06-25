---
name: fe-code-review
description: |
  Front-end code review focused on the current diff. Auto-detects the active git
  branch, base branch, monorepo layout, project Tailwind scale, ESLint coverage,
  and the project's existing UI components — then reviews the diff against
  feature-based structure, project-component reuse, lucide-react icons, idiomatic
  Tailwind tokens (verified to exist in the project's config), one-file-one-component,
  hook-file splitting, generic-primitive extraction, dead code, duplication, unused
  packages, and TypeScript escape hatches. After producing the report, the skill asks
  the user whether to apply the fixes; on confirmation it applies the mechanical and
  structural fixes in-place (never commits, pushes, or stashes).
  Use when asked to "fe code review", "review my frontend changes", "review this branch",
  "check my diff", "/fe-code-review", or before opening a frontend PR.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - AskUserQuestion
---

# fe-code-review

You are a senior front-end reviewer. Review **only the changed code** in the current diff, produce an actionable report, then — depending on the mode chosen up front — either stop at the report or offer to apply the fixes. Do not rewrite the world. Do not comment on code that did not change unless a change directly references it.

## 0. Choose mode (always first, before any analysis)

Before doing anything else — before the pre-flight, before reading files, before running the linter — call `AskUserQuestion` to pick the run mode. If `AskUserQuestion` isn't loaded, fetch its schema via `ToolSearch` with `query: "select:AskUserQuestion"` first.

Tool call shape:

```json
{
  "questions": [
    {
      "header": "Review mode",
      "question": "How should this review run?",
      "multiSelect": false,
      "options": [
        { "label": "Review", "description": "Produce a detailed report only. Each finding includes file/line and a concrete fix. No implementation, no apply prompt at the end." },
        { "label": "Self-review", "description": "Produce the report, then ask whether to apply mechanical + structural fixes in place." }
      ]
    }
  ]
}
```

Cache the answer as `MODE` (`review` or `self-review`) and let it gate the rest of the run:

- **`review` mode**: run §1–§6 normally. The report in §6 is the deliverable — make sure every Blocker / Suggestion / Nit cites `path:line` **and** carries a one-line concrete fix (the existing §6 format already requires this; in `review` mode it's non-negotiable). After printing the report, **stop**. Do **not** run §7. Do not call `AskUserQuestion` again. Do not edit any files.
- **`self-review` mode**: run §1–§7 as written. After the report, call `AskUserQuestion` per §7 to offer applying the fixes.

State the chosen mode on the first line of the report: `**Mode:** review` or `**Mode:** self-review`.

If the diff is config-only (§3 short-circuit) or the verdict is `ship — no issues found`, skip §7 regardless of mode — same behavior as before.

## 1. Pre-flight (no arguments — always auto-detect)

```bash
# git state
BR=$(git branch --show-current)
DIRTY=$(git status --porcelain | head -1)

# base branch — try gh, fall back chain; skip gh entirely if not installed/auth'd
BASE=""
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  BASE=$(gh pr view "$BR" --json baseRefName -q .baseRefName 2>/dev/null)
fi
[ -z "$BASE" ] && BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && { git show-ref --verify --quiet refs/heads/main && BASE=main; }
[ -z "$BASE" ] && { git show-ref --verify --quiet refs/heads/master && BASE=master; }

# repo identity — gates the FFRS-ui-specific overrides in §2.5
ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
IS_FFRS_UI=false
if [ -n "$ROOT" ] && [ -f "$ROOT/package.json" ]; then
  PKG_NAME=$(node -e "try{process.stdout.write(require('$ROOT/package.json').name||'')}catch(e){}" 2>/dev/null)
  if [ "$PKG_NAME" = "ffrs-ui" ] \
     || grep -q '"@finch-ai/finch-ui-components"' "$ROOT/package.json" 2>/dev/null \
     || [ "$(basename "$ROOT")" = "ffrs-ui" ]; then
    IS_FFRS_UI=true
  fi
fi

echo "branch=$BR base=$BASE dirty=$([ -n "$DIRTY" ] && echo yes || echo no) ffrs_ui=$IS_FFRS_UI"
```

`IS_FFRS_UI` controls whether §2.5 and any other FFRS-flagged guidance below fires. When `false`, treat every FFRS-tagged block as if it weren't there — don't fabricate `@finch-ai/finch-ui-components` imports or other ffrs-specific names.

Pick the scope automatically:
- **Dirty working tree** → review staged + unstaged + untracked.
- **Clean working tree** → review the branch diff: `git merge-base "origin/$BASE" HEAD || git merge-base "$BASE" HEAD` and use `<merge-base>...HEAD`.

Always pass `--find-renames` to diff commands so file moves don't masquerade as new files in forbidden locations:

```bash
git diff --find-renames --name-status "$MB"...HEAD
git diff --find-renames "$MB"...HEAD
```

State the chosen scope as a one-line header in the report (e.g. `Branch: enrichement-app-notifications → main · Scope: branch diff · 9 files`).

## 2. Read project conventions before reviewing

These reads override the generic rules below — but **distinguish documented conventions from legacy state**:

- **Documented conventions override skill rules**: explicit choices in `CLAUDE.md` / `AGENTS.md`, lint configuration, formatter configuration, package scripts, an `index.ts` defining a feature's public surface.
- **Legacy file location is NOT a convention**: "all existing API files live in `src/api/`" is observed state, not a stated rule. New code follows the skill's feature-based structure (§A) even when existing peers live in legacy locations. Cite the migration intent in the report ("place new API in `features/<X>/api/` even though `src/api/` still hosts pre-feature-folder files — the project is mid-migration") so the user sees the choice was deliberate.

If you can't tell whether something is a convention or legacy, treat it as legacy.

- **CLAUDE.md / AGENTS.md** at repo root and any nested ones under `src/`, `apps/*/`, `packages/*/`. Read them all.
- **Peer-feature shape — detect before recommending folder vs. file layout**. Before suggesting `features/<X>/constants/index.ts` (folder) vs. `features/<X>/constants.ts` (flat file), grep what existing features actually use:

  ```bash
  ls -d src/features/*/constants 2>/dev/null  # folders
  ls   src/features/*/constants.ts 2>/dev/null  # flat files
  ls -d src/features/*/utils 2>/dev/null
  ls   src/features/*/utils.ts 2>/dev/null
  ls -d src/features/*/hooks 2>/dev/null
  ls   src/features/*/hooks.ts 2>/dev/null
  ```

  Whichever shape dominates among existing features is the project convention — match it. **Default to flat file** (`constants.ts`, `utils.ts`) when a feature has a single module's worth of code; only recommend a folder when the feature ships multiple sibling files (e.g. `constants/status.ts` + `constants/keys.ts`). A single-file `constants/index.ts` is wrong by default — flag it and recommend collapsing to `constants.ts`. Same rule for `utils/index.ts`, `hooks/index.ts`.
- **Tailwind config — detect v3 vs v4 first**:
  - **Tailwind v3**: `tailwind.config.{ts,js,cjs,mjs}`. Cache `theme.extend.spacing`, `maxWidth`/`maxHeight`/`width`/`height`, `fontSize`, `colors`.
  - **Tailwind v4**: there is no JS config — theme lives in CSS via `@theme { … }` blocks. Search `src/**/*.css` for `@theme` blocks and read them all. Cache the same axes (any `--spacing-N`, `--color-*`, `--radius-*`, `--font-*`).
  - **Tailwind v4 calc fallback — IMPORTANT**: if v4 is detected and `@theme` does NOT redeclare the base `--spacing` variable, **all** spacing multiples are valid via `calc(var(--spacing) * N)`. So `top-1.75`, `mt-1.5`, `px-0.75`, `max-h-120`, `max-w-72`, `w-100` resolve correctly even if `--spacing-1.75` etc. aren't explicitly listed. Default base in v4 is `0.25rem` (= 4px per unit). Verify by computing: `top-1.75` = `0.25rem * 1.75` = 7px.
  - When suggesting tokens: in v4 with calc fallback intact, **suggest the tokenized form unconditionally** for any pixel value that is a clean multiple of 4 (or half-step thereof: 2, 6, 10, 14 px → 0.5, 1.5, 2.5, 3.5). Don't downgrade to "judgment call" because a key isn't explicitly listed.
  - In v3 (or v4 with overridden base `--spacing`): only suggest tokens that exist in the cached scale; otherwise fall back to closest stock or leave arbitrary.
- **ESLint config**: `.eslintrc*`, `eslint.config.*`, or `package.json#eslintConfig`. Cache which plugins/rules are active. The skill's lint-aware skipping below depends on this.
- **package.json**: detect `react-query`/`@tanstack/react-query`, `clsx`/`classnames`, lucide-react, the test runner, and any UI library.

### Catalog the project's existing components

Before recommending "use the project's `<Button>`", enumerate **all** primitive components the project ships, not just Button:

```bash
# Components live under one of these — adjust if the repo uses a different layout
for d in src/components/ui src/components src/ui apps/*/src/components/ui apps/*/src/components packages/*/src/components/ui packages/*/src/components; do
  [ -d "$d" ] && find "$d" -maxdepth 2 -name '*.tsx' -not -name '*.test.tsx' -not -name '*.stories.tsx'
done
```

For each component file found, note: name, import path, primary props (read the file's exported type / interface). Build a quick mental table:

| Project component | Import | Replaces raw |
| --- | --- | --- |
| `Button` | `@/components/ui/button` | `<button>` |
| `Input` | `@/components/ui/input` | `<input>` |
| `Dialog`, `Popover`, … | … | radix primitives, raw popovers |

Also look for **utility wrappers** the project already ships: `cn()` from `@/lib/utils`, `formatDate()`, `apiClient`, etc. If the diff re-implements any of these, flag it.

### Catalog shared / sibling component libraries

Some projects depend on a **shared component library** maintained as a sibling repo or org-scoped package. New primitives belong there, not in the consuming app — and the diff should consume what's already published rather than re-implementing it locally. (If `IS_FFRS_UI=true`, §2.5 pins the concrete library name for this repo; otherwise auto-detect as below.)

Detect the shared library:

1. **`package.json`** — scan `dependencies` / `devDependencies` for org-scoped packages that look like component libs: `@<org>/*-ui-components`, `@<org>/design-system`, `@<org>/ui`, `@<org>/components`. If multiple, pick the one with the most imports in `src/`.
2. **Sibling repo on disk** — if the consuming repo lives at `<workspace>/<app>`, check for siblings like `<workspace>/<org>-ui-components`, `<workspace>/design-system`, `<workspace>/ui` that have their own `package.json`. The published name is in their `package.json#name`.
3. **`CLAUDE.md` / `AGENTS.md`** — explicit mention of the shared library, where new primitives go, and the publish flow.

Once located, enumerate its exports. Two cheap ways:

```bash
# From the consuming app — read the installed package's entry
LIB="@<org>/<name>"  # the detected shared library, e.g. @<org>/<ui-components>
node -e "console.log(Object.keys(require('$LIB')))" 2>/dev/null
# Or read the source tree if the sibling repo is on disk:
ls <sibling-path>/src/components 2>/dev/null
sed -n '1,200p' <sibling-path>/src/index.ts 2>/dev/null
```

Cache the export list (component names + import path) alongside the project's local component catalog. Note which are **primitives** (`Button`, `Input`, `Badge`, `Avatar`, `Checkbox`, `Loader`, `Table`, `Pagination`, etc. — generic, app-agnostic) versus **app-specific** wrappers in `src/components/`. The shared library is reserved for primitives.

If you cannot resolve the shared library (not installed, sibling repo not on disk, network-only registry), note once at the top of the report: "Could not enumerate `<lib>` exports — shared-library reuse / promotion checks skipped." Don't fabricate exports.

### Detect monorepo layout

Look for `features/` under `src/`, `apps/*/src/`, `packages/*/src/`. The "feature-based structure" rule applies under whichever one the project uses. If multiple are present, the feature folder must live next to other features in that workspace, not in a different one.

### Lint-aware skipping

If the project ESLint config includes:

- `eslint-plugin-tailwindcss` → **skip the Tailwind shorthand section**. Note once at the top of the report: "Skipped Tailwind tokens — covered by `eslint-plugin-tailwindcss`."
- `eslint-plugin-unused-imports` OR `no-unused-vars` / `@typescript-eslint/no-unused-vars` set to `error` → **skip the unused-imports / unused-locals sub-bullets** of the dead-code rule. Note: "Skipped unused-imports — covered by your linter."
- `eslint-plugin-react-hooks` (almost always on) → still flag dep-array bugs the rule misses (e.g., conditional `useEffect`).

This keeps the report focused on what humans actually need to add on top of automation.

### Severity discipline — don't silently downgrade

When a rule below states a severity (Blocker / Suggestion / Nit), respect it. Common ways the report gets silently diluted:

- **Demoting a Suggestion to Nit because you're "not sure"**: uncertainty about a token, an API, or a project pattern is a research task, not a justification for silence. Read the file, grep the codebase, run the linter — then flag at the stated severity.
- **Skipping a rule because its example "doesn't quite fit"**: if §I literally uses `const EMPTY = { items: [], unreadCount: 0 }` as the example and the diff has the same shape, it's a finding. Examples in rules are matches, not illustrations.
- **Pre-judging that the project's component "doesn't fit" a use case**: §E flags raw `<button>` when `Button` exists. Don't pre-emptively decide the variants don't cover this case — flag it, suggest `className` override or a new variant, and let the team choose (see §E).
- **Treating "existing files do it differently" as a project convention**: see top of §2 — legacy state is not a convention. New code follows the rules.

If you find yourself writing "judgment call" or "leave as-is because the project doesn't do X yet" in a Nit, stop and reconsider whether the rule's stated severity actually applies. When in doubt, flag at the higher severity — the user can always demote in review.

## 2.5. FFRS-ui specific overrides — only when `IS_FFRS_UI=true`

**Skip this whole section when `IS_FFRS_UI=false`.** These pins exist because they're knowledge that can't be derived purely from auto-detection — naming, ownership boundaries, and historical decisions specific to the ffrs-ui codebase. In any other repo they don't apply; rely on the generic detection in §2 instead.

When `IS_FFRS_UI=true`:

- **Shared component library is pinned to `@finch-ai/finch-ui-components`.** When §2's detection runs, prefer this exact name over any auto-detected alternative. Use it as the import path in every shared-library reuse / promotion finding below (§E §0, §5.5 self-audit). Suggested import in findings: `import { Button } from '@finch-ai/finch-ui-components'`.
- **Sibling repo path**: typically `<workspace>/finch-ui-components` on disk. If present, enumerate exports from its `src/index.ts` per §2.
- Anywhere a finding below would say "the shared library detected in §2", substitute `@finch-ai/finch-ui-components` for clarity.

If you learn additional ffrs-specific conventions during the run (e.g. a repo-local rule in `CLAUDE.md`/`AGENTS.md`), apply them in addition to — not in place of — the generic rules.

## 3. Short-circuit on irrelevant diffs

If every changed file matches the config glob — `*.json`, `tsconfig*`, `.prettierrc*`, `.eslintrc*`, `*.md`, `.gitignore`, lock files (`bun.lockb`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`) — emit one line and stop:

```
Verdict: n/a — diff is config-only (<N> files). No FE rules apply.
```

Then skip the implementation question.

## 4. Gather context

- List changed files with `--find-renames`.
- Read each changed file in full so you see imports, surrounding components, and unchanged usages of changed exports.
- For deletions / renames: `git grep -n <oldName>` to confirm callers were updated.

## 4.5. Run the project's linter

Run the project linter against the changed files. Findings go into a dedicated `## Lint` section of the report; they're complementary to the skill's checklist (the linter catches the mechanical, the skill catches the structural).

### Detect the lint command

Look at `package.json#scripts` in this priority order:
1. `lint` — the canonical entry point.
2. `lint:check` / `lint:ci` — read-only variants (preferred over plain `lint` if it auto-fixes).
3. `eslint` / `biome` — direct binary invocation script.

Avoid scripts that include `--fix` or `--write` — the review is read-only.

If no lint script exists, look for a config file (`eslint.config.*`, `.eslintrc*`, `biome.json`) and run the binary directly with the project package manager:
- `bun x eslint <files>` / `pnpm exec eslint <files>` / `yarn eslint <files>` / `npx eslint <files>`
- `bun x biome check <files>` / `npx @biomejs/biome check <files>`

### Scope to changed files

Pass only the changed `.ts/.tsx/.js/.jsx/.css` files to the linter — don't lint the whole repo on every review (slow and noisy):

```bash
CHANGED=$(git diff --find-renames --name-only "$MB"...HEAD -- '*.ts' '*.tsx' '*.js' '*.jsx' '*.css' '*.scss' \
  | xargs -I{} sh -c '[ -f "{}" ] && echo "{}"')
[ -n "$CHANGED" ] && <package-manager> <lint-binary> $CHANGED 2>&1 | tee /tmp/fe-code-review-lint.txt
```

For working diff, also include unstaged + untracked file paths.

### Handle the output

- **Exit 0, no warnings**: report `Lint: clean.` once, no Lint section.
- **Warnings only**: include them under `## Lint` as a compact list — don't reformat or summarize, paste the linter's actual lines (one per line, prefixed with `path:line:col`). Cap at 30 lines; if more, add `…and N more` and offer to print full output on request.
- **Errors**: same as warnings, but the verdict cannot be `ship` regardless of other findings — at minimum `fix-before-ship`.
- **Lint command not found / project has no linter**: skip silently. Don't fabricate findings.
- **Lint command crashes** (config error, missing dep): note `Lint: failed to run — <error>` and continue with the rest of the review.

### Apply phase

If the user picks "All" or "Blockers only" in §7 and the linter has a `--fix`-safe variant available (`lint:fix`, `eslint --fix`, `biome check --write`), offer to run it after the manual edits — but only on the changed files. Don't run it without explicit confirmation, since `--fix` can rewrite untouched parts of files in ways the user may not expect.

## 5. Checklist

Only flag real issues found in the changed code. Quote `path:line`. Do not pad the report with "looks good" notes — silence is praise.

### A. Feature-based structure

New code must live under a feature folder:

```
features/<feature-name>/
  api.ts           # or api/ folder when there are multiple modules
  components/
  hooks/           # or hooks.ts if the feature has a single hook module
  constants.ts     # or constants/ folder when split across multiple files
  utils.ts         # or utils/ folder when split across multiple files
  types.ts
  index.ts         # only if the feature has a public surface
```

**Folder vs. flat file**: prefer a flat file (`constants.ts`, `utils.ts`, `api.ts`) when the feature has a single module's worth of code. Promote to a folder only when the module splits into multiple sibling files (e.g. `constants/status.ts` + `constants/keys.ts`). Always match peer-feature shape — see §2 "Peer-feature shape". A `constants/index.ts` containing only one file is a finding: collapse to `constants.ts`.

Flag (apply to **new** code in the diff regardless of where existing peers live — see §2 "Documented vs legacy"):
- API calls placed in a global `src/api/` directory when they belong to a single feature → move to `features/<feature>/api/`. Even if the project has 10 existing files in `src/api/`, a new file goes in the feature folder. Cite the legacy peers in the report so the reviewer sees the migration choice was deliberate.
- Components dropped into a generic `components/` root when they belong to a feature.
- Hooks placed next to components instead of `hooks/`.
- Utility/helper functions related to a feature placed in a generic `src/utils/` or inside an unrelated page component → move to `features/<feature>/utils/`.
- Constants related to a feature inlined in a component file or in a generic location → `features/<feature>/constants.ts` (or peer-matched shape).
- A `constants/index.ts` (or `utils/index.ts`, `hooks/index.ts`) holding a **single module's worth** of code → flag and recommend collapsing to `constants.ts` / `utils.ts` / `hooks.ts`. The folder form is only justified when there are multiple sibling files inside it.
- Cross-feature imports that suggest a util/hook should be hoisted to a shared location (`shared/`, `lib/`, or a cross-cutting feature folder like `features/react-query/`).
- **Inline data-fetch + render glue** in a generic page or sibling component:
  ```tsx
  const { data, isFetching } = useFeatureCheck(id);
  if (isFetching) return <Skeleton />;
  if (data) return <FeatureBadge result={data} compact />;
  return null;
  ```
  This whole block is a feature concern — extract it as `features/<feature>/components/<Feature>Indicator.tsx` and have the parent render `<FeatureIndicator id={id} />`. The parent shouldn't know about the loading/empty states of a feature it doesn't own.

#### "Belongs to a feature" — concrete heuristic

A component currently in `src/components/` (or a generic location) **belongs to feature `X`** when, after the diff:

```bash
git grep -lE "from ['\"][^'\"]*<ComponentName>['\"]" -- '*.ts' '*.tsx' \
  | grep -v '\.test\.' | grep -v '\.stories\.'
```

…returns only files under `features/X/`. In the finding, cite those importers so the suggestion is specific (e.g. `Only imported by features/notifications/components/* — move under features/notifications/components/`).

### B. One file → one component, one hook → one file

Components:
- A `.tsx` file should default-export (or named-export) **one** React component.
- Small private subcomponents are OK if truly private and < ~15 lines AND they don't own their own hook (state, mutations, queries).
- `.map(...)` blocks longer than ~10 lines, or with more than 2 props worth of logic per item, must be a separate component in their own file.
- Inline-only blocks like a "delete all" header action, "empty state" branch, or list rendering **must** be extracted (`<NotificationListHeader />`, `<NotificationsList />`, `<NotificationEmptyState />`). Severity: **Suggestion**, regardless of line count. Size of the block is irrelevant — what matters is whether it has a clear single responsibility (header action, list+empty, delete confirmation flow).
- An inline block that **owns its own mutation hook** (e.g. the "Delete all" button calling `useDeleteAllNotifications`) **always** gets extracted into its own component, and the extracted component owns the hook. The trigger UI must colocate with the mutation it triggers.
- A `items.length === 0 ? <Empty/> : <ul>...map...</ul>` ternary inside a parent's render body should be extracted as `<List items={items}/>` that handles both branches internally. Keeps the parent focused on layout, not data shape.

Hooks files:
- Don't ship a single hooks file with **3+ hooks of mixed responsibility class**. Classes: read query, mutation, invalidator, generic primitive. Split by responsibility:
  - **Read hooks + their invalidator** in one file (e.g. `useNotifications.ts` exports `useNotifications` + `useInvalidateNotifications`).
  - **Related mutations grouped in one file** named `use<Feature>Mutations.ts` (e.g. `useNotificationMutations.ts` exports `useMarkNotificationRead` + `useDeleteAllNotifications`). **Default to grouping**, not per-mutation files. Only split a mutation into its own file when (a) it owns substantial helpers/types of its own, (b) its lifecycle/concerns are unrelated to the other mutations (different cache, different invalidation, different domain), or (c) the grouped file would exceed ~150 lines. Two or three related mutations sharing a key + an optimistic-update primitive belong together.
  - **Generic primitives** (anything that takes `mutationFn`, `queryKey`, `apply`/`onOptimisticUpdate` as parameters and is not domain-specific) belong in a cross-cutting folder like `features/react-query/hooks/`. If the repo already has a generic primitive, recommend its existing name. Otherwise use these names **verbatim**, don't paraphrase:
    - `useOptimisticMutationFlat` — for flat-query mutations (the "Flat" suffix distinguishes from infinite-query). Argument shape: `{ key, mutationFn, onOptimisticUpdate }` (object, not positional). Param name is `onOptimisticUpdate`, not `apply`.
    - `useOptimisticMutationInfinite` — same idea for infinite queries.
- Worked example — a notifications hooks file shipping `useNotifications` (read), `useMarkNotificationRead` (mut), `useDeleteAllNotifications` (mut), `useInvalidateNotifications` (invalidator), and `useOptimisticNotificationsMutation` (private generic) splits into **3 files**: `useNotifications.ts` (read + invalidator), `useNotificationMutations.ts` (both mutations grouped), and `features/react-query/hooks/use-optimistic-mutation-flat.ts` (hoisted generic). Severity: **Suggestion**.

Tests for new feature code:
- If the diff creates a new feature folder (`features/<X>/components/`, `features/<X>/hooks/`) and ships **zero `*.test.tsx` / `*.test.ts` files**, flag it. Detect the project's test runner (`vitest`, `jest`, `playwright`) from `package.json` and surface the framework name in the finding so the suggestion is concrete.
- Severity: **Suggestion** by default, **Blocker** if the new code includes:
  - **Optimistic mutations with rollback** (the `onMutate` → `onError` rollback path is exactly the kind of code that breaks silently without integration tests),
  - **Reducers / parsers / state machines** with branchy logic,
  - **Logic that gates user data** (auth, permissions, data filtering).
- For a fresh feature, the minimum bar is: one render test per component (`getByTestId`/`getByRole` smoke), one integration test per mutation hook (mock the API, assert optimistic + rollback). Cite the project's existing test patterns (`msw`, `@testing-library/react`) so the finding shows the user the tools are already there.
- This rule is **never** auto-applied — moves to **Needs you**. Auto-generating tests produces false confidence.

Types vs. logic:
- A `.ts` file should be either **types** (interfaces, type aliases, schemas) or **logic** (functions, parsers, transformers) — not both. If a file declares 3+ types AND exports parser/transformer/validator functions, split into `<name>-types.ts` and `<name>-parser.ts` (or `-utils.ts`, `-mappers.ts`). Discriminated unions especially benefit from this split: types live in `types.ts`, the switch-on-discriminant parser lives in `parser.ts`.

### C. Imports

- All imports at the top of the file. No `require()` or dynamic `import()` mid-file unless lazy-loading is intentional.
- Order: external → absolute/aliased → relative → styles/types last.
- No unused imports. *(Skip if covered by linter — see §2.)*
- No duplicate imports from the same module.

### D. Icons — one library, no exceptions

The project picks one icon library; everything in the diff must use it. Detect the canonical library this way:

1. Read `CLAUDE.md` / `AGENTS.md` for an explicit choice.
2. Else, scan `package.json` and the most-used icon import in `src/` (`git grep -hE "from ['\"]([^'\"]*icons?[^'\"]*)['\"]"` and tally).
3. Else, default to `lucide-react`.

Once the canonical library is known, flag in the diff every icon imported from anything else, **and** flag mixing two icon libraries even if both are "icon libraries":

- `react-icons`, `@heroicons/react`, `@radix-ui/react-icons`
- `@fortawesome/*` (any FA package: `pro-regular-svg-icons`, `pro-solid-svg-icons`, `free-solid-svg-icons`, `react-fontawesome`, etc.)
- `@mui/icons-material`, `@iconify/react`, `boxicons`, `feather-icons`, `phosphor-react`, `react-feather`
- raw inline `<svg>` used as a UI icon (allowed only for logos / illustrations / decorative art)
- emoji-as-icon (`<span>✓</span>`, `<span>×</span>`)

For each finding, suggest the equivalent name in the canonical library (e.g. for lucide: `faCircleExclamation` → `CircleAlert`, `faCircleCheck` → `CircleCheck`, `faXmark` → `X`, `faUser` → `User`, `faFile` → `File`). If the team has historically left existing FA icons untouched while migrating, scope findings to **icons added or changed in this diff** — don't demand the whole file be rewritten.

### E. Use what the project already has — components, utilities, and packages

The general rule: **before writing anything, check if the project already provides it.** Four categories to scan:

0. **Shared / sibling component library** (your catalog from §2; when `IS_FFRS_UI=true`, §2.5 pins this to `@finch-ai/finch-ui-components`). This category takes **priority over the local component catalog** when the shared library ships a matching primitive — the whole point of the shared library is that all apps consume the same primitive. Two checks, both directions:

   **Reuse — flag in the diff:**
   - A raw HTML element (`<button>`, `<input>`, `<select>`, `<table>`, etc.) when the shared library exports a matching primitive. Severity: **Suggestion**. Same logic as the local-component case below: if the shared variants don't cover the shape, use `className` overrides, propose a new variant upstream, or document why a raw element is required — but don't pre-judge.
   - A **local re-implementation** in `src/components/` (or anywhere in the consuming app) that duplicates a primitive already exported by the shared library — e.g. a hand-rolled `Badge`, `Avatar`, `Loader`, `Pagination` when the shared lib exports one. Severity: **Suggestion** (or **Blocker** if the diff is *adding* the duplicate from scratch — net-new duplication of a shared primitive is a hard no).
   - A local wrapper around a shared component that only forwards props with no added behavior (`const MyButton = (p) => <Button {...p} />`) — drop the wrapper, import directly.
   - Suggest the exact import path you observed in the project (e.g. `import { Button } from '@<org>/<ui-components>'`, or `'@finch-ai/finch-ui-components'` when `IS_FFRS_UI=true`), not a guess.

   **Promotion — flag in the diff when a new component being added to the consuming app belongs in the shared library instead:**

   A new component in `src/components/` (or `features/<X>/components/` if generic-leaning) **belongs in the shared library** when **all** of these hold:
   - It's a **generic primitive**, not feature-specific: no domain props (`workflowId`, `enrichmentStatus`, `riskScore`), no feature-scoped data fetching, no calls into feature hooks. Naming test: would the component make sense in a different app (admin, marketing site, another product) with the same prop API?
   - It has **no imports from feature folders** (`features/<X>/...`), no imports from app-specific clients (`@/api`, `@/lib/auth`), no imports of app-specific tokens that aren't in the shared library's theme.
   - It's the kind of thing the shared library already hosts (UI primitives — buttons, inputs, badges, dialogs, tooltips, tables, loaders, layout primitives). Cross-reference the shared library's existing exports for shape.
   - It's reasonably stable in API — promoting churny experimental UI to a shared package creates breakage across consumers.

   For a finding, cite **why** it qualifies (no domain props, no feature imports, matches the shared lib's other primitives) and the suggested name + import path it would have after promotion. Severity: **Suggestion**. **Do not auto-apply** — promoting to a shared library requires a publish + version bump in the sibling repo, which is the team's call. Move every promotion finding to **`Needs you`** in §7.

   Edge cases:
   - **Domain-flavored primitive** (`RiskBadge`, `WorkflowStatusBadge`) where the *Badge* itself is generic but the variants/colors are domain-tagged → propose splitting: keep a generic `Badge` in the shared library (with `variant` / `tone` props), and build the domain wrapper (`<RiskBadge>` → `<Badge tone="warning">`) in the consuming app.
   - **Component already exists in shared lib with a slightly different API** → don't propose a duplicate "v2" upstream. Either extend the existing one (new variant / prop) or use it as-is with className.
   - **Storybook / a11y story missing** for an existing local primitive that the diff modifies → not a promotion finding; just note that if the team eventually promotes it, the shared library expects a `.stories.tsx`.

1. **Project-wrapped UI components** (your catalog from §2). Flag in the diff:
   - the **raw HTML element** the project component wraps (`<button>` when `Button` exists, `<input>` when `Input` exists). **Always flag — do not pre-judge that the variants "don't fit"**. If the existing variants don't cover the shape (circular icon button, full-width row, link-style action), the right action is one of: (a) use the project component with `className` overrides for the shape (`<Button className="size-9 rounded-full p-0" variant="…" />`), (b) propose a new variant on the project component, or (c) explicitly document why a raw element is required (e.g. `Radix.Trigger asChild` requires a child that forwards refs — note inline). Choosing between (a)/(b)/(c) is the team's call; flagging the raw element is yours. Severity: **Suggestion**.
   - a **re-implementation** of an existing component (new `ConfirmDialog` when `Dialog` exists; custom tooltip when a project tooltip exists),
   - a **re-implementation** of an existing utility (`classNames(...)` when `cn()` exists; inline `fetch` when `apiClient` exists; inline retry/auth handling that the project's HTTP client already does).

2. **Already-installed third-party primitives.** Some primitive packages are in `package.json` but not yet wrapped by the project. Reading the diff with `package.json` open: if the diff hand-rolls something a listed dep already provides, flag it. Common cases:
   - building a custom tooltip / popover / dialog / dropdown when `@radix-ui/react-*` (or `@headlessui/react`, `react-aria-components`, `@floating-ui/react`) is installed,
   - hand-rolled focus-trap when `focus-trap-react` is installed,
   - manual virtualization when `@tanstack/react-virtual` is installed,
   - manual form state when `react-hook-form` is installed,
   - manual schema validation when `zod` / `valibot` / `yup` is installed.
   In the finding, name the installed package and the equivalent primitive.

3. **Utility libraries the project depends on.** If a library is in `package.json`, prefer it over platform defaults for non-trivial cases:
   - **Dates**: if `dayjs` / `date-fns` / `luxon` is installed, don't write `new Date(...).toLocaleDateString('en-US', { month: 'long', ... })` or `Intl.DateTimeFormat(...)` ad-hoc — use the project library so formats are consistent across the codebase.
   - **HTTP**: don't write raw `fetch(...)` when `apiClient` / `axios` instance / `ofetch` wrapper exists.
   - **Schema/validation**: don't write hand-rolled `if (typeof x === 'string')` chains when `zod` / `valibot` is installed.
   - **Class merging**: don't write inline `classNames(...)`/`Object.entries(...).filter(...).join(' ')` when `cn` (`clsx` + `tailwind-merge`) is exported from `lib/utils`.
   - **i18n**: don't hardcode user-visible strings if `react-i18next` / `next-intl` is wired up.
   - **Route helpers**: don't inline `${id}` template strings inline in JSX (`navigate(\`/profile/person/${id}\`)`, `<Link to={\`/workflows/${workflowId}\`}>`). Suggest extracting to a typed `routes.ts` (or `features/<X>/routes.ts`) — e.g. `routes.profile.person(id)`. Even a single inline template in fresh feature code deserves a route helper, because: (a) the URL shape is now duplicated (string in JSX, route definition in the router), (b) typos won't be caught at compile time, (c) future URL refactors require grep instead of an LSP rename. Flag every inline route template in **new** feature code; for legacy in-place edits, flag if the same path appears 2+ times.

Suggest the import path you observed in the project, not a guess. Exception: a `<button type="submit">` wired directly to a native form when the design-system button can't take that role — note inline. Allow ad-hoc native APIs when the use is trivial and one-off (formatting a single ISO date in a debug surface) — judgment call.

### F. Tailwind shorthand & idioms (verified against the project's config)

For every arbitrary value in the diff:

1. **Tailwind v4 with calc fallback intact** (default base `--spacing` = 0.25rem, no override): suggest the tokenized form for any pixel value that is a clean multiple of 4 (or a half-step of 4: 2, 6, 10, 14 px → 0.5, 1.5, 2.5, 3.5). `top-[7px]` → `top-1.75`, `mt-[6px]` → `mt-1.5`, `px-[3px]` → `px-0.75`, `max-h-[480px]` → `max-h-120`, `max-w-[288px]` → `max-w-72`, `w-[400px]` → `w-100`. **Do not require the key to be explicitly listed in `@theme`.** Severity: **Suggestion** (not Nit).
2. **Tailwind v3 with explicit `theme.extend.spacing`**: only suggest tokens that exist in the cached scale.
3. If the project doesn't extend the relevant scale and is on v3 (or has overridden base `--spacing` in v4) → suggest the closest stock Tailwind token, or leave arbitrary if no stock token is within ~2px.

Common replacements (in v4 with calc fallback intact, all rows apply unconditionally; in v3, rows marked *(scale extension required)* need the theme to define the key):

| Anti-pattern | Replace with (if token exists) |
| --- | --- |
| `text-[20px]`, `text-[14px]` | `text-xl`, `text-sm` |
| `w-8 h-8`, `w-10 h-10` | `size-8`, `size-10` |
| `min-w-8 min-h-8` | `size-8` + `shrink-0` if needed |
| `mt-4 mb-4` / `ml-2 mr-2` | `my-4` / `mx-2` |
| `pt-2 pb-2 pl-4 pr-4` | `py-2 px-4` |
| `flex flex-row` | `flex` |
| `grid grid-cols-1` (no responsive variants) | drop `grid-cols-1` |
| `border border-solid` | `border` |
| `font-[500]`, `text-[#111]` | `font-medium`, theme token |
| `rounded-[8px]`, `rounded-[12px]` | `rounded-lg`, `rounded-xl` |
| `top-[7px]`, `bottom-[3px]` | `top-1.75`, `bottom-0.75` *(only if `theme.extend.spacing` defines them)* |
| `px-[3px]`, `py-[5px]` | `px-0.75`, `py-1.25` *(spacing extension required)* |
| `mt-[6px]`, `mb-[10px]` | `mt-1.5`, `mb-2.5` |
| `max-h-[480px]` | `max-h-120` *(only if `theme.extend.maxHeight`)* |
| `max-w-[288px]` | `max-w-72` |
| `w-[400px]`, `w-[320px]` | `w-100`, `w-80` *(only if `theme.extend.width`)* |
| `h-[44px]`, `h-[56px]` | `h-11`, `h-14` |
| `gap-[12px]` | `gap-3` |
| `leading-[30px]`, `leading-[24px]` | `leading-7.5`, `leading-6` |
| `min-w-[340px]`, `max-w-[500px]` | `min-w-85`, `max-w-125` *(only if extended scale defines them)* |

#### Inline `style={...}` for tailwind-expressible properties

Any inline `style={{...}}` whose property has a Tailwind-class equivalent should be moved into `className`, especially when the surrounding code already uses Tailwind. Common ones:

| Inline style | Tailwind class |
| --- | --- |
| `style={{ transform: 'translateX(-50%)' }}` | `-translate-x-1/2` (also need `transform`-related context if not implicit) |
| `style={{ background: '#0f172a' }}` | `bg-slate-900` (verify hex matches the project palette) |
| `style={{ backgroundColor: '#fef2f2' }}` | `bg-red-50` (or the project token) |
| `style={{ visibility: position ? 'visible' : 'hidden' }}` | `cn(position ? 'visible' : 'invisible')` in `className` |
| `style={{ color: '#111' }}` | `text-neutral-900` / theme token |
| `style={{ display: 'flex', flexDirection: 'column' }}` | `flex flex-col` |

Reserve `style={{...}}` for **truly dynamic** values that can't be class-based: a computed `top: pxFromRef`, an inline `--custom-prop` CSS variable, animation keyframes derived from JS state. Don't use it for static styling that exists as a class.

#### Hex colors → semantic tokens

When the diff introduces an arbitrary hex (`bg-[#fef2f2]`, `text-[#ae9df5]`, `style={{ background: '#0f172a' }}`):

1. If the hex matches a stock Tailwind palette color (`#fef2f2` ≈ `red-50`, `#0f172a` = `slate-900`) → replace.
2. Else if the project's `tailwind.config` defines it as a named token → use the token.
3. Else, **before** approving the arbitrary hex, suggest moving it into `tailwind.config` as a named token if it's used 2+ times in the diff or already exists elsewhere — design tokens belong in config, not scattered in classNames.

If you flagged 3+ Tailwind anti-patterns in this run, add a one-time tip at the bottom: "install the Tailwind CSS IntelliSense VS Code plugin — it highlights every arbitrary value with a token equivalent."

#### Project typography utilities defined in CSS

Some projects define semantic typography utilities in `@layer utilities` (or in a Tailwind v3 plugin) — names like `.label-xs`, `.label-sm`, `.paragraph-sm`, `.heading-3`. These are easy to miss because they live in CSS, not in `tailwind.config.*` and not in `@theme`. **Always grep the project's CSS for `@layer utilities` and cache the class names alongside the spacing/color tokens.**

When the diff uses a raw `text-*` / `leading-*` / `font-*` combo that exactly matches a project utility (e.g. `text-sm leading-6` matches `.paragraph-xs`), suggest the project utility — it's the project's stated typography system, and bypassing it scatters typography decisions across components. Severity: **Suggestion**.

Be calibrated: if the raw combo doesn't exactly match any project utility, leave it. The point is to consume the system, not to force-fit.

### G. Defaults over manual config

- Don't pass props that match the component's default. Exception: `type="button"` inside forms.
- Don't re-implement what the framework gives you (`useEffect` to derive state; manual fetch + manual loading flags when react-query is already a dep — flag with the concrete pattern: `useEffect(() => { setLoading(true); fetch(...) })` → `useQuery(...)`).
- Don't configure things to their default value in config files.
- **Don't change framework defaults without a written reason.** `retry: 1` (default 3), `staleTime: 0` (default 0 — already default), `gcTime: 60_000`, `refetchOnWindowFocus: false`, etc. — if the diff alters a default, require either (a) a comment on the same line explaining why, or (b) a project-wide convention captured in a wrapper. Otherwise drop the override and inherit the default.
- **Don't add a guard for a precondition the framework already guarantees.** Common pattern:
  ```ts
  return useQuery({
    queryKey: ['x', id],
    queryFn: () => {
      if (!id) throw new Error('id required'); // ← dead — `enabled` already prevents this
      return fetchX(id);
    },
    enabled: Boolean(id),
  });
  ```
  The `enabled: Boolean(id)` already prevents the call when `id` is falsy, so the throw is unreachable. Drop the guard. Same shape for: manual loading state alongside `isPending`, `try/catch` around code the framework will catch and surface via `error`, manual revalidation when a tag-based cache invalidation already covers it.

### H. Loops & utilities

- `array.forEach(...)` for **side-effects only**.
- `array.map(...)` when building a new array (including JSX).
- `for...of` **only** when you need `await` inside the loop or early `break`/`continue`. Otherwise prefer `forEach`.
- Flag `forEach` used to build an array, and `map` used purely for side effects.
- **Flag `for...of` used purely for side-effects with no `await` / `break` / `continue`** — replace with `.forEach()`. Project convention: prefer array methods (`forEach`, `map`, `filter`, `reduce`, `some`, `every`) over `for...of` whenever the body is `await`-free and doesn't short-circuit. Examples that **must** be flagged:
  ```ts
  for (const [key, prev] of snapshot) queryClient.setQueryData(key, prev);
  // → snapshot.forEach(([key, prev]) => queryClient.setQueryData(key, prev));

  for (const key of keys) queryClient.invalidateQueries({ queryKey: key });
  // → keys.forEach((key) => queryClient.invalidateQueries({ queryKey: key }));
  ```
  Severity: **Suggestion**.
- **Extract dense single-use transforms for readability.** A nested data-transform block inside a hook callback or component body deserves to be a named util **even when called only once** if any of these apply:
  - 10+ lines of nested object/array spreading (`{ ...x, pages: x.pages.map(p => ({ ...p, items: p.items.map(...) })) }`),
  - branchy logic interleaved with side-effects (mutating a flag like `wasUnread = true` inside a `.map`),
  - the block obscures the surrounding control flow (you have to read the transform to understand what the outer function does).

  Place it in `features/<feature>/utils/` (or `utils.ts` if the project uses flat files — see §2). The optimistic-update transform inside `onOptimisticUpdate` is the canonical case: extract `markNotificationReadInList(list, id): { list: ListCache; wasUnread: boolean }` so the hook reads as data → transform → write. Severity: **Suggestion**. Easier to read at the call site, easier to test in isolation, and the side-effect flag (`wasUnread`) becomes an explicit return value instead of a let-binding.

- **Extract repeated expressions, not just multi-line blocks.** Any non-trivial **expression** repeated in 2+ places deserves a util — it doesn't need to be a 3+ line block. Examples that qualify even though they fit on one line:
  - composite key derivation: `${a.entity_name}|${a.timeframe}` and `${item.entity_name}|${item.timeframe}` → `affiliationKey(x)`
  - URL builders: `\`/api/v1/resource/check/${id}\`` repeated in 2 callers → `resourceCheckUrl(id)`
  - non-trivial predicates: `x.status === 'pending' || x.status === 'running'` → `isInFlight(x)`
  - shape destructuring chains repeated across functions
  Place the util in `features/<feature>/utils/` if feature-local; `lib/` or `shared/utils/` if cross-feature. Don't extract a util used only once. Trivial repeated expressions (`x?.id`, `arr.length === 0`) don't qualify — judgment call on "non-trivial".

### I. Constants, query keys & stable refs

- Module-level literals describing config (`const EMPTY = { items: [], unreadCount: 0 }`, default page sizes, polling intervals, role names, **UI thresholds / magic numbers** like `MAX_BADGE_COUNT = 99`, `DEBOUNCE_MS = 300`, `MAX_RETRIES = 3`) belong in `features/<X>/constants.ts` (or `constants/` — match peer-feature shape per §2), not at the top of a hook file **or component file**. **Module-scope is not "good enough"** — if the feature has (or could have) a constants module, that's where the literal lives. Promote actively: `EMPTY` declared at the top of `useNotifications.ts` is a finding; `MAX_BADGE_COUNT = 99` declared at the top of `NotificationBellTrigger.tsx` is the same finding. **The file extension doesn't matter** — `.ts`, `.tsx`, hook, component, util — all are subject to this rule. Don't praise module-scope as if it were the destination, and don't pre-judge a literal as "component-local" because it sits in a `.tsx` file.
- **Inline empty defaults inside a component or hook body** that get passed to `useQuery`, `useMemo`, etc. — `useQuery({ ..., initialData: { items: [], count: 0 } })` — change identity every render. Hoist them to a `constants/` file (preferred) or at minimum module scope so consumers' deps stay stable.
- **For new features, do NOT extend a global `queryKeys` client.** Even if `src/lib/queryKeys.ts` already hosts entries for older features, a new feature's keys live in `features/<X>/constants/` as a **bare string constant**, used inside an array at the call site. Use this exact shape — don't substitute `as const` tuples or builder functions:
  ```ts
  // features/notifications/constants/index.ts
  export const NOTIFICATIONS_QUERY = 'notifications';

  // call site
  useQuery({ queryKey: [NOTIFICATIONS_QUERY], queryFn: ... });
  // or scoped: useQuery({ queryKey: [NOTIFICATIONS_QUERY, { id }], ... });
  ```
  **Do not** suggest `export const NOTIFICATIONS_QUERY_KEY = ['notifications'] as const;` — the bare string + array-at-call-site is the convention. The string is the canonical handle; the array is the queryKey shape react-query expects.
  **Do not** "collapse in place" by trimming `list()` off the global registry — relocate to feature constants.
- For features that already live in the global registry and the diff only modifies their entries, you may collapse in place — but call out in the report that long-term these belong in `features/<X>/constants/`.
- Flag duplicate-shape entries in a query-key client (`all: ['x']` and `list: ['x']` doing the same job).
- **Don't over-segment query keys.** A 3-segment key like `['x', 'check', id]` should usually collapse to either `['x-check', id]` or `['x', id]`. The general rule: every additional string segment is a partial-match boundary — only add one if you actually plan to invalidate at that boundary. If there's no `invalidateQueries({ queryKey: ['x'] })` (without `'check'`) and no `['x', 'list']` peer, the segmentation is dead and the key should be flat.
- Magic strings used as query keys / event names / role names in 2+ places → constant.

#### Typed constants for repeated literal shapes

Whenever the **same literal pattern** appears in 2+ places in the diff (or once in the diff and elsewhere in the repo), name it. This applies broadly:

- **String literal unions** repeated in 2+ type annotations: `'success' | 'partial'`, `'pending' | 'running' | 'completed' | 'cancelled' | 'failed'`, `'info' | 'success' | 'warning' | 'error'`. Extract to `type CompletionType = 'success' | 'partial';` (in `constants/types.ts` or `features/<X>/constants/types.ts`) and replace every inline copy.
- **Numeric literal unions**: `1 | 2 | 3` → `type Step = 1 | 2 | 3`.
- **Object-shape literals** repeated in 2+ signatures: `{ id: string; name: string }` appearing in five props/returns → extract a named type.
- **Status discriminants compared with `===`**: when `status === 'loading'`, `status === 'success'`, etc. appear across files, the literal lives in too many places. Pair the named type with **typed constants**:
  ```ts
  // features/<X>/constants/status.ts
  export const TASK_STATUS = {
    Idle: 'idle',
    Loading: 'loading',
    Success: 'success',
    Partial: 'partial',
    Failed: 'failed',
  } as const;
  export type TaskStatus = (typeof TASK_STATUS)[keyof typeof TASK_STATUS];
  ```
  Then `status === TASK_STATUS.Loading` at every call site. (Recommend `as const` map + derived type by default. If the project already uses TS `enum` consistently — check existing code and CLAUDE.md — match that convention instead of fighting it.)
- **Sweep rule**: when you flag this pattern in one place, search the whole diff for the same literal union (`grep -E "'success'\\s*\\|\\s*'partial'"` etc.) and list every other occurrence in the same finding so the user fixes them all at once.

This extraction is a **Suggestion**, not a Blocker, unless the same literal union is inlined in 4+ places — then it's a Blocker.

### J. Composition, readability & memoization

- Prefer early-return over a top-level ternary when one branch is dominant. **Either direction is acceptable** — what matters is killing the ternary, not which branch comes first. When the component represents a "list with an empty fallback", prefer the truthy-guard direction (it reads as "if we have items, render them; otherwise empty"):
  ```tsx
  // Avoid:
  return items.length === 0 ? <EmptyState /> : <List items={items} />;

  // Prefer (truthy-guard — reads as "show the list when we have data"):
  if (items.length) return <List items={items} />;
  return <EmptyState />;

  // Also fine (negative-guard — reads as "bail out on empty"):
  if (!items.length) return <EmptyState />;
  return <List items={items} />;
  ```
  Cosmetic — flag as Nit, never Blocker. When extracting a list-with-empty-state component, explicitly recommend the truthy-guard shape in the suggestion.
- Handlers used in only one child should live in that child, not be lifted to the parent and threaded through props.
- If the handler also touches **parent UI-shell state** (open/close, focus, hover, selection), don't keep the whole handler in the parent — pass a **one-line shell callback** as a prop (`onClose: () => setOpen(false)`) and lift the rest into the child. Domain logic (mutations, navigation, derived data) belongs in the component that owns it.
- Mutation hooks (`useMarkNotificationRead`, `useDeleteAllNotifications`) should colocate with the component that calls them. A parent threading `markRead.mutate(id)` through an `onClick` prop is a smell — move the hook into the child.
- **`useCallback` — use when:** the handler is passed to a memoized child (`React.memo`-wrapped row), or appears in another hook's dep array. Flag handlers passed to `<Memoized*>` children that are not wrapped.
- **`useCallback` — flag over-use:** a handler used only by a non-memoized native element (`<button onClick={fn}>`) wrapped in `useCallback` for no reason. Same for `useMemo` over a cheap computation with no memoized consumer / dep-array reader. Strip them.

### K. Dead code

In the changed files, flag (skip subitems already covered by linter — see §2):
- Unused exports (no consumer in the repo).
- Unused locals: variables, params (use `_` prefix only if intentionally ignored), imports, types.
- Commented-out code blocks.
- `console.log` / `debugger` left in.
- Unreachable branches.
- **Dead-on-conditional-render branches.** A value computed unconditionally where a branch only ever runs under a guard that's already wrapped at the consumer:
  ```tsx
  const badge = unreadCount <= 0 ? '' : unreadCount > 99 ? '99+' : String(unreadCount);
  // ...
  {unreadCount > 0 && <span>{badge}</span>}  // ← unreadCount <= 0 branch is dead
  ```
  The `unreadCount <= 0 → ''` branch is unreachable because the consumer's `unreadCount > 0 &&` guard prevents the `<span>` from rendering at all. Either fold the computation into the conditional render, or drop the dead branch. Severity: **Suggestion**.
- Stale TODO/FIXME added in this diff with no ticket reference.

### L. Duplication & pointless indirection

- Same JSX skeleton differing only by data → extract.
- Two hooks doing the same thing under different names → consolidate.
- Hooks copying the same react-query optimistic-update boilerplate but with different mutation functions → extract a generic primitive.
- Inline strings/styles repeated 3+ times → constant or class.
- Type definitions duplicating an existing exported type → reuse.
- **Pass-through re-export**: `import { X } from './x'; export { X };` (or `export type { X };`) from a file that isn't a barrel (`index.ts`) is dead indirection — drop the re-export and import `X` directly at the call sites. Same for value-level: `export const helper = original;`.
- **Pointless type alias**: `type Y = X;` where `Y` is never extended, narrowed, or used to attach documentation, and `X` is already exported — delete `Y`, use `X`. Domain-flavored aliases (`type WorkflowCompletionType = CompletionType;`) without semantic narrowing are noise.
- **Pointless function wrapper**: `const wrap = (x) => inner(x);` — drop, use `inner` directly.

### M. Package hygiene

If `package.json` changed:

```bash
git diff --find-renames <range> -- package.json | grep -E '^\+' | grep -E '"[^"]+":\s*"' | grep -v '^+++'
```

For every newly added dependency, confirm it is actually imported (`git grep -l "from ['\"]<pkg>"`). Flag:
- Added but unused.
- Added when an existing dep already covers it.
- Heavyweight deps for a tiny use case (suggest the lighter alternative or native API).
- Removed deps that still have imports somewhere.
- Lockfile changed but `package.json` didn't (and vice versa).

### N. TypeScript escape hatches & noise

In the diff, flag newly-added:
- `any`, `as any`, `Function`, `Object`, `{}` as a type.
- `as unknown as X` double-casts.
- `!` non-null assertions (especially on values from unsafe sources: `params.id!`, `data!.user`).
- `@ts-ignore` and `@ts-expect-error` without an explanatory comment on the next-but-one line.

**Defaultable casts.** `fn(x as string)` where `x: string | null | undefined` and the receiver tolerates the empty value → drop the cast and default the arg: `fn(x ?? '')` or `fn(x || '')`. Same pattern for `(value as Foo[])` when `value ?? []` works. Generalize: any cast applied to silence "possibly undefined" that could be replaced by `??` / `||` / a type guard.

**Redundant TS notation.** TS already implies certain things — re-stating them is noise:
- `foo?: T | undefined` → `foo?: T` (the `?` already includes `undefined`). Exception: `exactOptionalPropertyTypes` is on in `tsconfig` and the `| undefined` is intentionally distinguishing "absent" from "explicitly undefined" — note inline.
- `Readonly<readonly T[]>` → `readonly T[]`.
- Same array notation mixed in one file (`Array<T>` and `T[]`) → pick one.
- Type assertions to the value's existing type (`(x as string)` when `x` is already `string`) → drop.

**Weak types from API responses.** Backend payloads typed as `Record<string, unknown>`, `unknown[]`, or `any` when the contract is actually known are a smell — the parser then has to runtime-check what the type system should have proven. If the diff introduces such a payload, suggest:
- a **discriminated union** keyed on a server-provided field (`type Section = | { kind: 'a'; ... } | { kind: 'b'; ... }`),
- or, if the team has a generated-types pipeline (OpenAPI → TS, GraphQL codegen, Zod schemas), the generated type from there.
Exception: a payload truly is freeform (telemetry blob, vendor webhook) — note inline.

For each escape hatch, suggest the narrowing the type system would have given for free (e.g. `params: { id: string }` from the route schema; a type guard for `data`).

**Unsafe rest-spread.** `...props` spread *after* safety attributes lets a consumer override them silently:

```tsx
<button
  type="button"
  aria-label="Notifications"
  data-testid="bell"
  className="relative ..."
  {...props}  // ← consumer can override type, aria-label, etc.
>
```

Two failure modes:
1. **Override hole**: a parent passes `type="submit"` and the bell breaks the popover. Or passes `onClick` that runs *after* the trigger's own handler unexpectedly.
2. **Untyped rest**: when the props interface declares only specific fields (`{ unreadCount: number; ref?: Ref<...> }`) and the function destructures `...props` anyway, the rest is implicitly `unknown` / a TS error depending on `noImplicitAny`.

Fix: either move `{...props}` *before* the safety attributes (so explicit attrs win), or — preferred — narrow the props type to declare exactly what the wrapper accepts and stop spreading. Severity: **Suggestion**, **Blocker** if the spread can override `type` on a button inside a form, `role`, `aria-modal`, or any prop that affects accessibility/security.

### O. General quality (light pass on changed lines only)

- New `useEffect` that syncs derived state, fetches data that should live in react-query / RSC, or runs on every render with a missing dep array.
- New client component (`"use client"`) that doesn't need to be — no state, no effects, no event handlers, no browser APIs.
- New `key={index}` in a `.map` over a list that can reorder.

#### Accessibility & semantic HTML — sharper pass on new interactive surfaces

For every **new interactive surface** in the diff (popover, dialog, menu, list, form, card with click handler), walk this checklist:

- **Headings**: a `<p>` whose text reads like a heading and sits next to clickable items belongs as `<h2>` / `<h3>` (or the design-system's heading primitive, or `Popover.Title` / `Dialog.Title` from Radix). Screen readers navigate by heading; lists named with `<p>` are invisible to that flow.
- **Time / dates**: relative timestamps (`dayjs(x).fromNow()`, `formatDistanceToNow(x)`) belong inside `<time dateTime={isoString}>{relativeText}</time>`. The `dateTime` attribute carries the machine-readable ISO form.
- **Color contrast** — spot-check text colors used in the diff against the background they sit on:
  - `text-neutral-400` (#94a3b8) on white = ~3.28:1 — **fails WCAG AA** for normal text (needs 4.5:1).
  - `text-neutral-500` (#64748b) on white = ~4.78:1 — passes.
  - When a low-contrast color is used for "secondary" content (timestamps, captions), suggest a darker neutral or a larger font size (`>=18px` allows 3:1 ratio).
- **Click handlers on non-buttons**: `<div onClick>` / `<span onClick>` without `role="button"`, `tabIndex={0}`, and a keyboard handler is unreachable by keyboard.
- **Missing `htmlFor`** on labels.
- **Missing `alt`** on `<img>`. Decorative images get `alt=""`; informative images need text.
- **Missing `aria-hidden="true"`** on decorative icons that have a sibling text label.
- **Color-only state**: a status indicator that uses only color (red / green dot) needs a secondary signal (text, icon shape, `aria-label`).
- **Outline removal without a focus replacement**: `outline-none` must be paired with a `focus-visible:` style.
- **Missing landmarks / labels** on Radix primitives: `Popover.Content` / `Dialog.Content` should have a `Title` and ideally a `Description`. If hidden visually, use `VisuallyHidden`.

Severity: **Suggestion** for each individual finding. **Blocker** if the diff introduces a fully unreachable surface (e.g. `<div onClick>` with no keyboard handler that gates an important action).

## 5.5. Pre-emit self-audit

**Before** printing the report in §6, walk this literal checklist against the diff. For each item, do not interpret — grep / scan / verify. The point is to catch the rules where the example *literally matches* the diff and you missed it on the first pass.

For each rule, ask: "Did I scan the diff for this rule's example pattern?"

- [ ] **§A** — Every new file under `src/api/`, `src/components/`, `src/utils/`, `src/hooks/` that belongs to a single feature → did I propose moving it under `features/<X>/`?
- [ ] **§B** — Every new `*.tsx` with a `.map(...)` or `items.length === 0 ?` ternary in render body — did I propose extraction?
- [ ] **§B** — Every new hooks file: did I count hooks (read / mutation / invalidator / generic)? If ≥3 mixed-class, did I propose split?
- [ ] **§B** — New feature folder without `*.test.tsx` siblings — did I flag missing tests?
- [ ] **§D** — Every icon import in the diff: from the canonical library?
- [ ] **§E** — Every raw `<button>` / `<input>` / `<form>` in the diff: did I propose the project component (with className override if shape doesn't match)?
- [ ] **§E (shared lib — reuse)** — For each primitive used in the diff (button, input, badge, avatar, loader, pagination, table, checkbox, select, toggle, textarea, label, progress, notification…): is there a matching export in the shared component library (the one cataloged in §2; pinned by §2.5 when `IS_FFRS_UI=true`)? If yes and the diff imports from elsewhere — or hand-rolls it locally — flag it.
- [ ] **§E (shared lib — promotion)** — For each **new** component added in `src/components/` (or a generic-looking component under `features/<X>/components/`): is it a generic primitive with no domain props, no feature imports, and shape-similar to the shared library's existing exports? If yes, flag for promotion to the shared library and move to `Needs you`.
- [ ] **§E (shared lib — duplicate)** — Did I grep the diff's new `.tsx` component names against the shared library's export list? A new `Badge.tsx` / `Avatar.tsx` / `Loader.tsx` / `Pagination.tsx` in the consuming app, when the shared library already exports the same name, is a Blocker.
- [ ] **§E** — Every `${id}` template inlined in JSX/`navigate()` — did I propose a `routes.ts` helper?
- [ ] **§F** — Every arbitrary Tailwind value (`top-[7px]`, `max-h-[480px]`, `w-[400px]`): in v4 with calc fallback, did I suggest the tokenized form?
- [ ] **§F** — Every `text-* leading-* font-*` combo: matches a project typography utility (`.label-xs`, `.paragraph-sm`)?
- [ ] **§G** — Every non-default react-query option (`staleTime`, `gcTime`, `retry`, `refetchOnWindowFocus`): does the diff have a comment explaining why?
- [ ] **§I** — Every module-level config literal (`const EMPTY = …`, `const DEFAULT_PAGE_SIZE = …`, `const MAX_BADGE_COUNT = …`, any `UPPER_SNAKE_CASE = <literal>`) in **any** changed file (`.ts`, `.tsx`, hook, component, util): **is it in the feature's constants module** (not just at module scope)? Module-scope is not the destination. UI thresholds / magic numbers in component files count too — don't pre-judge them as "component-local". Run `git diff <range> | grep -E '^\+const [A-Z][A-Z0-9_]+ ='` against the diff and scan every match.
- [ ] **§A / §2** — Did I detect peer-feature shape (`ls -d src/features/*/constants` vs `ls src/features/*/constants.ts`) before recommending folder vs. flat file? A new feature with a single constants module + sibling features using flat `constants.ts` → suggest `constants.ts`, not `constants/index.ts`.
- [ ] **§H** — Every `for...of` loop in the diff: does the body actually use `await`, `break`, or `continue`? If not, suggest `.forEach()`. Run `git diff <range> | grep -E '^\+\s*for \(const'` and check each.
- [ ] **§H** — Every dense transform inside `onMutate` / `onOptimisticUpdate` / `useMemo` / hook callback (10+ lines of nested spread + `.map`, or branchy logic with side-effect flags): proposed extraction to `features/<X>/utils.ts` even if called only once?
- [ ] **§I** — Any new `queryKeys` entry: relocated to `features/<X>/constants/` as a **bare string** (`NOTIFICATIONS_QUERY = 'notifications'`), used as `[NOTIFICATIONS_QUERY]` at call site? Did I avoid the trap of suggesting `['notifications'] as const` instead of the string?
- [ ] **§B** — Generic primitive extracted to `features/react-query/hooks/`: did I name it `useOptimisticMutationFlat` (not `useOptimisticMutation`), with object args `{ key, mutationFn, onOptimisticUpdate }` (not positional, not `apply`)?
- [ ] **§B** — Multiple mutations in one feature: did I propose **grouping in one `use<Feature>Mutations.ts`** rather than per-mutation files? (Per-mutation only when ~150 lines or unrelated lifecycles — see §B.)
- [ ] **§I** — Repeated literal unions (`'success' | 'partial'`, status discriminants): named type extracted?
- [ ] **§J** — Handlers in parent that touch only child state: lifted into the child?
- [ ] **§K** — Computed values consumed only under a guard: dead branches?
- [ ] **§N** — `...props` spread after safety attributes: flagged?
- [ ] **§O** — Every new `<p>` near clickable items: should it be `<h2>` / heading primitive?
- [ ] **§O** — Every relative timestamp: wrapped in `<time dateTime>`?
- [ ] **§O** — Every `text-neutral-300` / `text-neutral-400` (or similar low-contrast color) on white: contrast ratio acceptable for the text size?
- [ ] **§O** — Every `outline-none`: paired with `focus-visible:` style?

If any box is unchecked, do that scan now. Then emit the report.

The point of this self-audit is not "more rules" — it's making sure the rules you already have actually fire. The most common failure mode is reading a rule, agreeing with it abstractly, and then not pattern-matching it against the literal diff.

### Calibration patterns — drawn from past misses

These are the specific places where prior reviews silently drifted from the rules above. When you encounter them, slow down and double-check:

- **"Module-scope is good enough"** — No, it's not. If §I says constants belong in `constants.ts`, then a `const EMPTY = …` at the top of `useNotifications.ts` is a finding even though it's already module-scoped. Don't praise the half-step as if it were the destination. The same applies to **component files** — `const MAX_BADGE_COUNT = 99` at the top of `NotificationBellTrigger.tsx` is identical to the same literal in a hook file. The file extension (`.ts` vs `.tsx`) and the file's role (hook vs. component vs. util) **do not exempt** the literal from §I. UI thresholds, magic numbers, badge caps, debounce durations, retry counts — all promote.
- **"This `for...of` looks fine"** — If the body has no `await`, no `break`, no `continue`, it's a `forEach` in disguise. Project convention prefers array methods. Don't leave it unflagged because the loop "works" — flag it as a Suggestion.
- **"This transform is only called once, so no extraction needed"** — Single-use is not a justification when the block is 10+ lines of nested spreading or has interleaved side-effect flags (`let wasUnread = false` mutated inside a `.map`). §H's readability-extraction rule applies to *legibility*, not *duplication*. Extract to `features/<X>/utils.ts` and let the hook read top-to-bottom.
- **"Recommend the canonical `constants/` folder"** — Only if peer features in this repo actually use that shape. If the rest of the codebase uses flat `constants.ts`, the new feature does too. And a `constants/index.ts` with one file inside is always wrong — collapse it.
- **"Each mutation in its own file" applied dogmatically** — The rule is a *ceiling* (don't bury 5 mutations in one file), not a *floor*. Two related mutations (same query key, same domain) belong together in `use<Feature>Mutations.ts`. Splitting them produces tiny per-file footprints and pointless import noise.
- **Substituting your preferred shape for the rule's stated example** — When §I shows `export const NOTIFICATIONS_QUERY = 'notifications';` and `[NOTIFICATIONS_QUERY]` at the call site, don't "improve" it to `['notifications'] as const`. The example *is* the rule. Same for `useOptimisticMutationFlat` (don't drop the `Flat`) and the object-args shape `{ key, mutationFn, onOptimisticUpdate }` (don't switch to positional, don't rename `onOptimisticUpdate` to `apply`). When the skill names something, use that name verbatim.
- **Not flagging in a category because "the variants don't quite fit"** — §E covers this explicitly. Flag the raw element; let the team choose between className override / new variant / documented exception. Don't pre-decide.
- **Treating "existing peers in legacy locations" as cover for new code** — §2 covers this. Existing `src/api/*.ts` files are not a convention; new feature API goes in `features/<X>/api.ts` (or `api/`). Cite the legacy peers in the finding so the user sees the migration intent was deliberate.

## 6. Output format

```
# fe-code-review

**Mode:** <review | self-review>
**Branch:** <current> → **Base:** <base>
**Scope:** <working diff | branch diff> — <N> files
**Linter coverage:** <skipped categories, if any>
**Lint:** <clean | N issues | failed to run | n/a — no linter>
**Verdict:** <ship | fix-before-ship | needs-rework>

## Blockers
- `path/to/File.tsx:42` — <one-line problem>. Fix: <one-line fix>.

## Suggestions
- `path/to/Other.tsx:10` — <one-line problem>. Fix: <one-line fix>.

## Nits
- `path/to/Yet.tsx:88` — <one-line problem>.

## Package hygiene
- (only if package.json changed)

## One-time tip
- (optional, only when 3+ Tailwind anti-patterns flagged)
```

Rules:
- Group by severity, not file. **Blockers**: explicit-rule violations. **Suggestions**: idiomatic improvements. **Nits**: subjective polish.
- Each line includes `path:line` and a concrete fix.
- Omit categories with no findings.
- If everything is clean: one line — `**Verdict:** ship — no issues found in <N> files.`

## 7. Offer to apply the fixes (self-review mode only)

**Skip this entire section when `MODE === 'review'`.** In review mode, the report is the deliverable: stop after §6, do not call `AskUserQuestion`, do not edit files. End with the report.

In `self-review` mode, after printing the report (and only when the verdict is not `n/a` / `ship — no issues`), call the **`AskUserQuestion`** tool — do **not** print the question as prose. If `AskUserQuestion` isn't loaded, fetch its schema via `ToolSearch` with `query: "select:AskUserQuestion"` first.

Tool call shape (concrete invocation, not pseudo-code):

```json
{
  "questions": [
    {
      "header": "Apply fixes",
      "question": "Apply the findings to the diff in place?",
      "multiSelect": false,
      "options": [
        { "label": "All", "description": "Apply mechanical + structural findings; leave judgment-call items as `Needs you`." },
        { "label": "Blockers only", "description": "Apply only the Blockers section." },
        { "label": "No", "description": "Leave the code untouched." }
      ]
    }
  ]
}
```

Anywhere else in the run where you need a decision from the user (e.g. clarifying scope before a structural file move, choosing between two valid file layouts), use `AskUserQuestion` — never inline prose questions.

### How to apply

Categorize each finding before applying:

- **Mechanical** (auto-apply): Tailwind shorthand replacement, default-prop removal, `useCallback`/`useMemo` strip, raw `<button>` → project `Button` or shared-library `Button` (read the prop API; if a stock variant fits, use it; otherwise pass `className` for shape overrides — `<Button className="size-9 rounded-full p-0" variant="…" />`), local re-implementation → shared-library import (drop the local file, rewrite importers to the shared package — only when the API matches 1:1; otherwise move to Needs you), unused imports removal, hoist module-level config literals to a feature `constants/` file (don't leave them inline at top of a hook), inline magic strings → typed constant, raw inline SVG icon → lucide. If the project component genuinely cannot carry a needed prop (e.g. `Radix.Trigger asChild` requires native ref forwarding the wrapper doesn't expose), move the item to **Needs you** rather than skipping silently.
- **Structural** (apply with care): file moves under feature folder, hook-file split, query-keys client → flat constant, `src/api/...` → `features/<X>/api/...`. Use `git mv` via Bash, then update every importer in the repo with `git grep`-driven Edits.
- **Judgment** (do NOT auto-apply): generic-primitive extraction with a new name, "split this giant component", API redesign, **shared-library promotion** (a new local component that belongs in `@<org>/<ui-lib>`) — this requires a publish + version bump in the sibling repo, which is not in scope here, anything where a Suggestion phrasing said "from my point of view" or "if it makes sense". Leave these in the report under a new `## Needs you` heading.

Constraints while applying:
- Edit files in place. Never `git add`, `git commit`, `git push`, `git stash`, or `--amend`.
- Don't run formatters or builds unless the user asks.
- After each Structural change (file moves, import-rewrites, hook splits), re-grep to confirm all importers were updated.
- **Auto-verify Structural changes**. After applying any Structural fix that touches imports or moves files, run the project's TypeScript check against the changed files: `<package-manager> exec tsc --noEmit` (scoped to changed paths if the project supports it). If it fails, surface the errors back inline — don't rely on the user to discover them post-hoc. Lint runs only if the user opted into them or if there are auto-fixable lint errors blocking otherwise-clean apply (see §4.5).
- **Iterate once after first apply.** After mechanical+structural edits land, re-walk the §5.5 self-audit checklist against the new state. Common new findings: a moved file's relative imports are now wrong (auto-verify catches), a hoisted constant is now duplicated elsewhere, a renamed symbol is missing from a barrel `index.ts`. If any new findings surface, list them under a new `## Surfaced after apply` section in the summary.
- After all edits + iteration, print one summary line: `Applied <N> fixes across <M> files. Type-check: <pass/fail>.` List any items that moved to **Needs you**.

If the user picks **No**, end with: `Left untouched. Re-run /fe-code-review after addressing the findings to verify.`

## 8. Don't do

- Don't comment on style issues outside the diff.
- Don't suggest large refactors of unchanged code.
- Don't run formatters, linters, or builds unless the user asks.
- Don't open a PR, commit, push, or stash — even after applying fixes.
