---
name: push-dude
version: 1.0.0
description: |
  Smart commit grouper and pusher. Runs the project's gates first (linter,
  typecheck, tests), fixes what they flag, then analyzes all unstaged and staged
  changes, groups them into logical, well-named commits where things that belong
  together stay together, commits them in a clean sequence, and pushes. Handles
  merge conflicts during push automatically. Never adds AI co-author attribution.
  Use when asked to "push-dude", "group my commits", "smart push",
  "commit and push everything", or "push my changes smartly".
allowed-tools:
  - Bash
  - Read
  - Edit
  - AskUserQuestion
triggers:
  - push dude
  - group my commits
  - smart push
  - push my changes
  - commit and push
---

# /push-dude - Smart Commit Grouper and Pusher

You are running the `/push-dude` workflow. Your job: verify the working tree
passes the project's gates (fixing whatever they flag), then look at every
changed file, group them into logical, small commits where related things stay
together, write clear human-readable messages, make the commits in order, and
push. Handle any conflicts on the way.

**Do not commit or push code that fails the gates.** Green linter, typecheck,
and tests come first; grouping and pushing come after.

---

## HARD RULES (never violate these)

- **NEVER** add `Co-Authored-By:`, `Co-authored-by:`, or any AI/Claude attribution to any commit.
- **NEVER** use em dashes (`-` is fine; `--` in text is not; `—` is never fine) in subject lines or bodies.
- **NEVER** use `git add -A` or `git add .` when staging a mixed-concern commit. Always name specific files.
- **NEVER** force-push without the user explicitly asking for it.
- **NEVER** commit `.env`, credentials, or secret files.
- **NEVER** commit or push code that fails the linter, typecheck, or tests. Run the gates (Step 2) and get them green first. The only exception is a pre-existing failure you did not introduce and cannot fix in scope, which you must surface to the user before proceeding.
- **NEVER** silence a linter or type error with a blanket `eslint-disable`, `@ts-ignore`/`@ts-expect-error`, `any`, or `--no-verify` just to get green. Fix the underlying cause. A targeted, justified suppression is allowed only when the rule is genuinely wrong for that line, and you must say so in the report.

---

## Step 1: Read the full working tree state

Run these to understand everything that is changed:

```bash
git status
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "NO_UPSTREAM"
git log --oneline -5
git diff --stat HEAD
```

Then read the full diff so you understand what each change actually does:

```bash
git diff HEAD
```

Also check for any already-staged files (these get included too):

```bash
git diff --cached --stat
git diff --cached
```

---

## Step 2: Run the gates and fix what they flag

Before grouping anything, get the working tree to a green state. The whole tree
ships together, so the gates run once over everything (not per planned commit).

**Speed note for this repo:** ESLint is the slow gate (~6 min cold, ~7s warm with
cache). Every unnecessary re-run costs minutes. Follow the rules below to minimize
gate runs: run all three in parallel on the first pass, then only re-run the gate
that failed when you fix something.

**2a. Discover the project's gate commands.** Read `package.json` `scripts` (and
honor `CLAUDE.md`/`README` if they name the gates). Pick the package manager from
the lockfile: `pnpm-lock.yaml` -> `pnpm`, `yarn.lock` -> `yarn`, `package-lock.json`
-> `npm run`, `bun.lockb` -> `bun run`. For this repo the gates are:

```bash
pnpm format:check  # Prettier format check (fast ~5s) - run this first, alone
pnpm lint          # ESLint strict (~6 min cold, ~7s warm with cache)
pnpm typecheck     # tsc --noEmit (~10s)
pnpm test          # Vitest unit tests (~15s)
```

If a Prisma schema change is part of the diff, run `pnpm db:generate` first so
typecheck sees the regenerated client. If there is no test script, skip tests and
say so in the report. Never invent a gate the project does not define.

**2b. Run format:check first (alone, fast).** This gate is cheap and if it fails
the push hook will fail immediately without running the slow gates - so catch it
now before wasting time:

```bash
pnpm format:check
```

If it fails, run `pnpm format` to auto-fix, then continue. Do NOT re-run
format:check - prettier is deterministic, format always fixes what check found.
The formatted files will be included in the commit plan later.

**2c. Run lint, typecheck, and test IN PARALLEL.** All three are independent and
can run simultaneously. Launch them together, wait for all three to finish, then
read each result:

```bash
pnpm lint 2>&1 | tee /tmp/_push_lint.txt; echo $? > /tmp/_push_lint_exit.txt &
pnpm typecheck 2>&1 | tee /tmp/_push_tc.txt; echo $? > /tmp/_push_tc_exit.txt &
pnpm test 2>&1 | tee /tmp/_push_test.txt; echo $? > /tmp/_push_test_exit.txt &
wait
```

Read `/tmp/_push_lint.txt`, `/tmp/_push_tc.txt`, and `/tmp/_push_test.txt` to
see each gate's output. Read the `_exit.txt` files to see which ones failed.

**2d. Fix each failing gate independently. Re-run ONLY the gate you fixed.**

This is the critical rule for speed. After fixing lint errors: re-run `pnpm lint`
only. Do not re-run typecheck or test - they already completed in 2c and their
result is still valid unless you changed something that affects them.

- **Lint failures:** Fix each error in the flagged files. If lint reports
  auto-fixable problems, run `pnpm lint:fix` first, then `pnpm lint` to confirm.
  Re-run `pnpm lint` after each fix batch until it exits clean.
  Do not re-run typecheck or test just because you re-ran lint.

- **Typecheck failures:** Fix type errors. Re-run `pnpm typecheck` only. Do not
  re-run lint or test unless your fix also changes imports/types that lint checks.

- **Test failures:** Fix or update tests. Re-run `pnpm test` only. Do not re-run
  lint or typecheck unless your fix changed non-test source files.

When a fix could plausibly affect a gate that already passed (e.g. you rewrote a
function that tests cover), re-run that gate too. Use judgment.

**2e. When you cannot get green:**

- If the only remaining failure is **pre-existing** (present on `HEAD` before your
  changes, unrelated to this diff) and out of scope to fix here: verify by stashing
  your changes (`git stash`) and running the failing gate on the base HEAD. If it
  fails there too, note it and proceed - but tell the user clearly in the final
  report. Then `git stash pop`.
- If a failure is **caused by the changes being pushed** and you cannot
  confidently fix it, STOP. Do not commit or push. Use AskUserQuestion to show
  the failing output and ask how they want to handle it.

Only once the gates are green (or the sole failures are acknowledged pre-existing
ones) do you move on to grouping.

---

## Step 3: Analyze and form commit groups

Study the diff carefully. Understand the purpose of each change, not just which
file it touched. Then cluster files by logical concern.

**Good grouping heuristics:**

| Theme | What belongs together |
|---|---|
| Schema / DB | Prisma schema, migrations, seed data - always its own commit |
| Domain lib | `src/lib/*.ts` business logic, algorithms, calculations |
| Server actions / API | `actions.ts` files, `route.ts` handlers, server-side mutations |
| UI components | React components, forms, layouts, Tailwind styling |
| Auth / permissions | Middleware, role guards, org-scope logic |
| Config / tooling | ESLint, tsconfig, package.json, CI config |
| Tests | Unit tests, integration tests, fixtures |
| Scripts / workers | CLI scripts, background workers, one-off tools |
| Docs | README, CHANGELOG, TODOS, markdown files |
| Deletions | Files removed as part of a refactor go with the refactor commit; pure removals get their own commit |

**Splitting rules:**
- A commit that spans multiple unrelated concerns is too big - split it.
- A commit that would leave the codebase broken on its own is too small - merge it with what it depends on.
- Ask: if a developer reads this commit message 6 months from now while `git blame`-ing a file, does it instantly tell them what changed and why?

**Think hard about deleted files:** A deleted component that was replaced by a
new one belongs in the same commit as the replacement. A deleted file with no
replacement gets its own `chore: remove X` or `refactor: remove X` commit.

---

## Step 4: Output your commit plan

With the gates green, print the full plan before making any commits. Format:

```
COMMIT PLAN
====================================================

COMMIT 1: feat(billing): add Stripe checkout session endpoint
Files:
  src/app/api/billing/checkout/route.ts (modified)
  src/lib/stripe.ts (modified)
Reason: Wires up the checkout route to mint Stripe sessions with org context
        and rate limiting; adds the verifyWebhook helper to the shared lib.

COMMIT 2: chore(schema): add subscription and plan billing tables
Files:
  prisma/schema.prisma (modified)
  prisma/seed.ts (modified)
Reason: Seeds the four plan tiers (free/starter/pro/enterprise) and adds
        Subscription, UsageCounter, StripeEvent tables with RLS protection.

...

====================================================
```

Be concrete about the reason. "Updated X" is bad. "Adds Y so that users can Z"
is good.

---

## Step 5: Execute the commits

Work through the plan in order. For each commit:

**5a. Stage only the relevant files:**

```bash
git add path/to/file1 path/to/file2
```

Never `git add -A` or `git add .` for a commit that covers a subset of changes.

**5b. Verify the staged content looks right:**

```bash
git diff --cached --stat
```

If something unexpected is staged, unstage it: `git restore --staged <file>`

**5c. Commit with a proper multi-line message using a HEREDOC:**

```bash
git commit -m "$(cat <<'EOF'
type(scope): subject line in imperative present tense

Body that explains what changed and why. What was the motivation?
What problem does this solve? What should a future developer know?
Keep lines under 80 chars. No em dashes. No AI attribution.
EOF
)"
```

Subject line rules:
- Format: `type(scope): description` (e.g. `feat(billing): add checkout route`)
- Max 72 characters total
- All lowercase after the colon
- Imperative present tense: "add", "fix", "remove" - not "added", "fixes"
- No period at the end
- Types: `feat`, `fix`, `refactor`, `chore`, `style`, `docs`, `test`, `perf`

Body rules:
- Blank line between subject and body (HEREDOC handles this)
- Answer "what changed" and "why" - the diff answers "how"
- Specific: name the files, concepts, and user-facing effects that matter
- No `Co-Authored-By`, no `Co-authored-by`, no mention of Claude or AI

**5d. Confirm it landed:**

```bash
git log --oneline -1
```

**5e. If a file is partially relevant to two commits:**

Some files legitimately touch two concerns (e.g. a shared lib that got a feature
and a bug fix). If splitting the file at the line level is needed, use AskUserQuestion
to ask the user whether to put the whole file in the more-relevant commit, or
whether they want to handle it manually. Never silently misfile it.

---

## Step 6: Push and handle conflicts

After all commits are made, push:

```bash
git push
```

**If push is rejected (non-fast-forward / remote has new commits):**

Pull with rebase to replay our commits on top of remote state:

```bash
git pull --rebase
```

**If rebase encounters merge conflicts:**

For each conflicted file:

1. See what is conflicted:
   ```bash
   git diff --diff-filter=U --name-only
   ```
2. Read the conflicted file (look for `<<<<<<<`, `=======`, `>>>>>>>` markers).
3. Resolve it:
   - Keep our change if we added new functionality and their change was independent.
   - Keep their change if they fixed something we didn't touch.
   - Merge both if they are additive (e.g. both added imports, both added fields).
   - If ambiguous, use AskUserQuestion to show both versions and ask the user which to keep.
4. Stage the resolved file:
   ```bash
   git add <resolved-file>
   ```
5. Continue:
   ```bash
   git rebase --continue
   ```

Repeat until rebase completes, then push:

```bash
git push
```

**If the push is rejected again after rebase:** STOP. Show the error. Do not
force-push. Tell the user what happened and ask what they want to do.

**If there is no upstream set yet:**

```bash
git push --set-upstream origin $(git branch --show-current)
```

---

## Step 7: Final report

Print a clean summary:

```
DONE
====================================================
Branch:  <branch-name>
Gates:   lint OK | typecheck OK | tests OK (12 passed)
Pushed:  <N> commits to <remote/branch>

COMMITS:
  <short-hash>  type(scope): subject
  <short-hash>  type(scope): subject
  ...
====================================================
```

In the `Gates` line, report what actually ran. If you fixed something to get
green, say what (e.g. `lint OK (auto-fixed 3, hand-fixed 1)`). If a gate was
skipped (no script) or a pre-existing failure was knowingly left, call it out
explicitly rather than implying everything was clean.

Run `git log --oneline origin/<base>..HEAD 2>/dev/null || git log --oneline -10`
to get the hashes for the summary.

If any files were left uncommitted (e.g. the user explicitly has untracked files
that look intentionally untracked, like `.env.local`), note them:

```
Left uncommitted (likely intentional):
  .env.local
  node_modules/ (gitignored)
```

Do not commit files that are gitignored or look like local config the user
intentionally keeps out of version control.
