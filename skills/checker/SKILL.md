---
name: checker
description: |
  Pre-push production readiness check. Runs five sequential gates: intent
  verification, diff minimalism audit, code quality review, functionality
  verification, and prod readiness sign-off. Use when a feature is done and
  needs thorough review before pushing to prod. Use when asked to "checker",
  "check this before pushing", "pre-push review", or "is this ready for prod".
---

# Checker — Production Readiness Review

A five-gate sequential review of your current changes. Each gate must pass before the next runs. A single FAIL blocks the push.

---

## Setup

Run this first to gather context. Capture **both** committed and uncommitted changes:

```bash
_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
_BASE=$(git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main 2>/dev/null || echo "HEAD~1")
_BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "unknown")

# Committed changes since branching from main
_COMMITTED_FILES=$(git diff --name-only "$_BASE"...HEAD 2>/dev/null)
_COMMITTED_DIFF=$(git diff "$_BASE"...HEAD 2>/dev/null)
_STAT=$(git diff --stat "$_BASE"...HEAD 2>/dev/null)
_LOG=$(git log "$_BASE"...HEAD --oneline 2>/dev/null)

# Uncommitted changes (staged + unstaged)
_UNCOMMITTED_FILES=$(git diff --name-only HEAD 2>/dev/null; git diff --name-only --cached HEAD 2>/dev/null)
_UNCOMMITTED_DIFF=$(git diff HEAD 2>/dev/null; git diff --cached HEAD 2>/dev/null)

# All files touched (deduplicated)
_ALL_FILES=$(echo "$_COMMITTED_FILES"$'\n'"$_UNCOMMITTED_FILES" | sort -u | grep -v '^$')
_ALL_DIFF="$_COMMITTED_DIFF"$'\n'"$_UNCOMMITTED_DIFF"
```

Print this header:

```
# Checker — <branch name>
<N> commits behind origin/main  |  <X files changed>
```

If `_BEHIND` is 10 or more, add: `> **Stale branch** — consider rebasing before pushing.`

If `_UNCOMMITTED_FILES` is non-empty, note: `> **Uncommitted changes included** — staged and unstaged changes are part of this review.`

If `_ALL_FILES` is empty, stop and tell the user there are no changes to review.

If the intent is not clear from `_LOG`, use AskUserQuestion to ask: "What is this change supposed to do?"

---

## Gate 1 — Intent Verification

**Purpose:** Confirm the diff matches the stated intent. Catch scope creep and accidental modifications.

Read every file in `_ALL_FILES` using the Read tool. For each file, categorize its changes:

| Category | Meaning |
|----------|---------|
| `CORE` | Directly implements the feature/fix |
| `INCIDENTAL` | Cleanup or refactor that came along for the ride |
| `UNRELATED` | Touches something the feature doesn't need |
| `RISKY` | Changes shared/foundational code (utils, hooks, middleware, DB models, base components) |

Output a table:

---

### Gate 1 — Intent Verification

**Feature intent:** _one sentence_

| File | Category | Notes |
|------|----------|-------|
| `src/foo/Bar.tsx` | CORE | implements X |
| `src/utils/helpers.ts` | INCIDENTAL | minor cleanup |
| `src/pages/Other.tsx` | UNRELATED | unrelated to feature |
| `src/hooks/useAuth.ts` | RISKY | shared hook modified |

**Verdict:** PASS / WARN / FAIL
> Reason if not PASS

---

- **PASS** = only CORE and INCIDENTAL
- **WARN** = INCIDENTAL changes are substantive but defensible
- **FAIL** = UNRELATED changes present, or RISKY without justification — recommend splitting to a separate branch

---

## Gate 2 — Diff Minimalism

**Purpose:** Ensure the diff is as lean as possible. No bloat, duplication, or dead code.

Scan `_ALL_DIFF` for:
- **Duplication** — logic that already exists elsewhere (use Grep to verify before flagging)
- **Dead code** — stale imports, unused vars, orphaned types, commented-out blocks
- **Over-engineering** — abstractions not required by the current task
- **Redundant state** — derived values stored in state instead of computed
- **Copy-paste** — 3+ near-identical blocks that should be a loop or helper

Output:

---

### Gate 2 — Diff Minimalism

**Lines:** +X / -Y (net: Z)

| File | Line | Type | Issue | Fix |
|------|------|------|-------|-----|
| `src/foo/Bar.tsx` | 42 | DUPLICATION | `useDebounce` reimplemented | Use `src/hooks/useDebounce.ts` |
| `src/foo/Bar.tsx` | 88 | DEAD CODE | `useState` imported but unused | Remove import |
| `src/utils/api.ts` | 15 | REDUNDANT | `isLoading` stored in state | Derive from `status === "loading"` |

**Verdict:** PASS / WARN / FAIL

---

- **PASS** = no issues, or trivially minor
- **WARN** = issues present but non-blocking
- **FAIL** = meaningful duplication, or dead code that will confuse future readers

---

## Gate 3 — Code Quality

**Purpose:** Catch things that will cause bugs, maintenance pain, or security issues. Not style-policing.

Check `_ALL_DIFF` against this checklist. Only list items that are **violated**:

---

### Gate 3 — Code Quality

**Correctness**

| Check | Status | Location |
|-------|--------|----------|
| No `any` type casts hiding real errors | | |
| No silenced errors (`catch (e) {}`) | | |
| Async/await correct — no floating promises | | |
| No unsafe array/object mutations | | |
| No off-by-one errors in loops/slices | | |

**Security**

| Check | Status | Location |
|-------|--------|----------|
| No secrets/tokens/credentials in code or comments | | |
| No `dangerouslySetInnerHTML` without sanitization | | |
| No string interpolation into SQL/shell commands | | |
| User input validated at system boundaries | | |

**Reliability**

| Check | Status | Location |
|-------|--------|----------|
| Error states handled (network, async, null) | | |
| No infinite loop risk (useEffect deps, while loops) | | |
| useEffect subscriptions/timers have cleanup returns | | |
| No race conditions in concurrent async ops | | |
| Loading/error states surfaced to the user | | |
| No hardcoded env-specific values (localhost, test IDs) | | |

**Maintainability**

| Check | Status | Location |
|-------|--------|----------|
| Names describe what, not how | | |
| Complex logic has a "why" comment | | |
| No magic numbers/strings without a named constant | | |
| Component/function has single responsibility | | |

Fill Status with `ok` or a short problem description. Omit rows where the check clearly doesn't apply (e.g. SQL checks on a pure UI file).

**Verdict:** PASS / WARN / FAIL
> List each violation as: `` `file:line` — CATEGORY — description — fix ``

---

- **PASS** = no violations
- **WARN** = non-blocking issues
- **FAIL** = security issue, correctness bug, or reliability gap that will cause prod incidents

---

## Gate 4 — Functionality

**Purpose:** Trace the feature end-to-end to confirm it actually does what it's supposed to do.

Steps:
1. Identify entry points (route handler, component mount, user action, API endpoint, cron job).
2. Trace the happy path from entry to output/side-effect, reading each function called.
3. Identify the 3 most likely failure scenarios and trace those too.
4. Check if each failure fails gracefully or crashes.
5. Verify tests exist for the happy path and at least one failure case.

Run to find test files:
```bash
echo "$_ALL_FILES" | grep -E "\.[tj]sx?$" | grep -v -E "(test|spec)" | while read f; do
  base="${f%.*}"; ext="${f##*.}"
  ls "${base}.test.${ext}" "${base}.spec.${ext}" 2>/dev/null
done
```

Output:

---

### Gate 4 — Functionality

**Entry point:** `src/pages/Foo.tsx:42`
**Happy path:** user clicks → POST /api/foo → DB write → toast shown

**Failure scenarios:**

| # | Scenario | Outcome | Status |
|---|----------|---------|--------|
| 1 | Network error on POST | Shows error toast | HANDLED |
| 2 | Empty response body | Crashes with TypeError | **UNHANDLED** |
| 3 | Auth token expired | Redirects to login | HANDLED |

**Test coverage:**

| File | Covers |
|------|--------|
| `src/pages/Foo.test.tsx` | Happy path |
| _(none)_ | Failure scenario 2 — missing |

**Verdict:** PASS / WARN / FAIL

---

- **PASS** = happy path verified, failures handled, tests present
- **WARN** = missing test coverage or one minor unhandled edge case
- **FAIL** = unhandled failure that will cause a prod incident, or happy path broken

---

## Gate 5 — Prod Readiness

**Purpose:** Catch the things developers forget when they're excited a feature works locally.

Run these automated checks against `_ALL_DIFF`:

```bash
# Leftover debug logs
echo "$_ALL_DIFF" | grep "^+" | grep -v "^+++" | grep -E "console\.(log|debug|warn)"

# Blocking TODOs introduced in this diff
echo "$_ALL_DIFF" | grep "^+" | grep -v "^+++" | grep -E "\b(TODO|FIXME|HACK|XXX)\b"

# Hardcoded localhost URLs (excluding test files)
echo "$_ALL_DIFF" | grep "^+" | grep -v "^+++" | grep "localhost" | grep -v -E "(test|spec|mock|example)"

# Removed accessibility attributes
echo "$_ALL_DIFF" | grep "^-" | grep -v "^---" | grep -E "(aria-label|aria-labelledby|role=|alt=)"
```

Output:

---

### Gate 5 — Prod Readiness

**Environment**

| Check | Result |
|-------|--------|
| No `console.log` / `console.debug` left | `src/pages/Foo.tsx:23` — FAIL |
| No blocking TODOs/FIXMEs introduced | none |
| No hardcoded env values / localhost URLs | none |
| Feature flag in place for risky rollout | n/a |

**Data & Migration**

| Check | Result |
|-------|--------|
| DB schema change has migration file | n/a |
| API contract change — consumers updated | no breaking changes |
| No shared type breakage without versioning | ok |

**Observability**

| Check | Result |
|-------|--------|
| Key operations have meaningful log statements | ok |
| Errors logged with enough context to diagnose | ok |

**Regression**

| Check | Result |
|-------|--------|
| Existing tests that import changed modules | `src/pages/Foo.test.tsx` — check passes |
| Auth / payments / data deletion touched | no — standard scrutiny applies |

**Dependencies** _(skip if `package.json` not changed)_

| Check | Result |
|-------|--------|
| Lock file also updated | ok |
| No devDep in dependencies | ok |
| New dep has justification | ok |

**Accessibility** _(skip if no UI files changed)_

| Check | Result |
|-------|--------|
| No aria-label / role / alt attrs removed | ok |
| Interactive elements still have accessible labels | ok |

**Branch**

| Check | Result |
|-------|--------|
| Commits behind origin/main | 2 — ok |
| Uncommitted changes included in review | yes |

**Verdict:** PASS / WARN / FAIL

---

- **PASS** = all clear
- **WARN** = non-blocking (non-blocking TODO, minor logging gap)
- **FAIL** = console.log in prod path, hardcoded env value, missing migration, breaking change without update

---

## Final Report

Print this summary after all five gates:

---

## Checker Report — `<branch>`

| Gate | Name | Result |
|------|------|--------|
| 1 | Intent Verification | PASS / WARN / FAIL |
| 2 | Diff Minimalism | PASS / WARN / FAIL |
| 3 | Code Quality | PASS / WARN / FAIL |
| 4 | Functionality | PASS / WARN / FAIL |
| 5 | Prod Readiness | PASS / WARN / FAIL |

---

**READY TO PUSH** — all gates PASS. Safe to push.

**NEEDS FIXES** — one or more WARNs. Use AskUserQuestion to ask:
> "There are warnings above. Acknowledge and push anyway, or fix first?"
If the user acknowledges, update status to READY TO PUSH and note which warnings were accepted.

**BLOCKED** — any FAIL. Do NOT suggest pushing. Print:

### To unblock:

1. **[Gate X]** `file:line` — one-sentence fix
2. **[Gate Y]** `file:line` — one-sentence fix

Each item must be actionable enough to fix without re-reading the full report.

---

_This skill is read-only — it never edits files, commits, or pushes. Re-run checker after fixes to confirm all gates pass._
