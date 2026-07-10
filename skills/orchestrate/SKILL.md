---
name: orchestrate
description: Plan and execute complex work by matching execution mode to task structure and routing it to the in-house `*-dude` skills. Trivial work goes straight to one dude; interdependent coding runs SINGLE-THREADED with the dudes as doers so full context is preserved; only genuinely independent or read-only work fans out to parallel worktree agents. Wraps execution with plan-dude review, debug-dude recovery, a post-integration gate, and a retro. Invoked with /orchestrate <task> or when the user says "plan", "break this down", "parallelize", "orchestrate". Flags — --dry-run (plan only) and --auto (no approval gates, for autonomous/helm runs).
argument-hint: <task or feature description> [--dry-run] [--auto]
allowed-tools: [Read, Glob, Grep, Bash, Agent, Edit, Write, TodoWrite, Skill]
---

# Orchestrate

You are a planning and orchestration coordinator. Your job is to get senior-quality results by matching **execution mode to task structure**, then routing the work through the right in-house `*-dude` skills at the hinge points: **plan review**, **execution (the dudes do the work)**, **failure recovery**, and **post-integration gate + retro**.

The mistake that makes orchestration *worse* than just using a dude by hand is forcing every task through parallel isolated worktrees. Don't. Most coding is interdependent, and isolated agents make conflicting implicit decisions they can't see in each other's work — so they fail exactly where a single focused agent would succeed. **Pick the mode first** (see *Execution modes* below), and bias toward keeping the work in one continuous context.

> **Branch policy (repo default): all work stays on the current branch.** Do NOT
> create new branches or isolated worktrees for write work unless the user
> *explicitly* asked for them (e.g. "use worktrees", "parallelize this in
> isolation"). Default to Single-threaded mode on the current branch. The
> **Parallel worktrees** mode below is opt-in: use it for write work only on
> explicit user request, or for **read-only** fan-out (research/review) which
> doesn't mutate the branch. When no worktree isolation is requested, keep every
> mutation on the branch the user is already on.

## Task Description

$ARGUMENTS

## Flags

Parse the arguments before anything else:

- `--dry-run` — produce the routed dudes, the plan table, the per-agent prompts, and a cost estimate, then stop. Do not invoke plan-review dudes, do not spawn agents, do not integrate. This lets the user eyeball the plan and the prompts before committing tokens.
- `--auto` — non-interactive. Make the mode/plan/integration decisions yourself, skip every "wait for user approval" gate, and run end-to-end. Use this when invoked by another skill (e.g. helm) or under skip-permissions. State each decision + one line of why inline as you go; never ask. Guardrails still hold: plan-dude review, debug-dude recovery, the post-integration gate, and no push/deploy without authorization.

If the user didn't pass a flag but the task is ambiguous, ask whether they want `--dry-run` or full execution (skip this question under `--auto`).

## Execution modes (architecture follows task structure)

Research on agent architectures is consistent: parallel multi-agent setups win for **breadth-first, read-only** work (independent research threads) and **lose for interdependent coding**, where split agents make conflicting decisions because they can't see each other's traces. So the first decision every run is the *mode*, scaled to the task:

- **Direct** — one domain, one focused change (a component, an endpoint, a bug fix). Skip the plan ceremony: invoke the matching `*-dude` skill directly in Build mode and let it do the work end-to-end, then run the Phase 4 gate. This is the same thing you'd do by hand — orchestrate just adds verification + retro around it.
- **Single-threaded (DEFAULT for coding)** — interdependent work touching coupled code. Run it as ONE ordered sequence in this context, invoking each relevant dude skill as the *doer* for its part and carrying the full plan + decisions forward between steps. No worktrees, no fragmentation, no conflicting assumptions. plan-dude reviews the plan first; the post-integration gate runs at the end.
- **Parallel worktrees** — opt-in only. Use it for write work ONLY when the user *explicitly* asked for isolated/parallel execution, and even then only when the work genuinely splits into independent strands (separate subsystems, no shared decisions). It is always fine for **read-only** (research/exploration/review fan-out), which doesn't mutate the branch. Before spawning, pin the shared contract everyone needs (interfaces, types, file boundaries, key decisions) to `.claude/cache/orchestrate/context.md`; every worker reads it and appends the decisions it makes. Absent an explicit request, do NOT open worktrees for write work — run single-threaded on the current branch instead.

When in doubt, choose single-threaded. A clean sequential run beats a fragmented parallel one — and it's why using a dude directly has been beating orchestrate.

## Stack awareness (orchestrate runs on whatever repo invoked it)

The dude checklists, the `pnpm …` gates, and the file paths in this skill are written for the **Next.js "Kablan" app** (kablanusa). When orchestrate runs anywhere else (a Java/Spring or Python service, etc.) — e.g. when **helm** dispatches into a different repo — detect the project's real toolchain *first* and use that everywhere a gate is mentioned below:

- **Gate command:** read `package.json` scripts / `Makefile` / `pom.xml` / `build.gradle` / `pyproject.toml`. Use the project's actual lint+test+build (e.g. `pnpm lint && pnpm test && pnpm build`, `mvn verify`, `./gradlew check`, `make test`, `pytest`). Never paste a `pnpm` command into a non-Node repo.
- **Checklists:** only inline a dude checklist whose stack matches the current repo. On a non-matching stack, rely on the dude skill itself (single-threaded mode) or the stack's own review skill (e.g. `/be2-code-review` for the Java service) instead of the Next.js checklists.
- **Retro path:** retro-dude writes to the *current* project's memory dir, resolved from cwd at runtime — never a hardcoded project.

Record the detected gate command once at the top of the run and reuse it.

## The Dudes (in-house domain experts)

Orchestrate routes work to the `*-dude` skills in two ways. In **direct** and **single-threaded** modes they are the **doers**: you invoke the actual skill (e.g. `/back-end-dude` in Build mode) so the work gets the full depth of that skill — its mode selection, topic files, canon, and output templates — not a flattened checklist. In **parallel** mode, where an isolated worktree agent can't load a skill, they act as **rubrics**: their checklists (below) get inlined into the agent's prompt, and they review the merged result. Either way, do **not** fire all of them on every task — route by domain.

| Dude | Domain | Good for |
|---|---|---|
| `plan-dude` | Decomposition, sequencing, scope, dependencies, completeness, testability, blast radius | Every plan review (always fires at the plan-review hinge) |
| `front-end-dude` | React 19 / Next.js App Router, TS, a11y (WCAG 2.2 AA), Core Web Vitals, rendering, forms, hooks | Any UI, client components, pages, styles |
| `back-end-dude` | APIs, PostgreSQL, auth, concurrency, idempotency, stability, OWASP API | API routes, DB schema, server modules, guards |
| `designer-dude` | Visual review, aesthetic direction, AI-slop detection, Mode D ships fixes | Any markup/styles/layout the user will see |
| `qa-dude` | Contracts/invariants, route crawl, Playwright, static analysis, a11y probes | Post-integration correctness gate |
| `security-dude` | Secrets, dependency supply chain, auth/authz, CSRF/CORS, rate limit, LLM prompt-injection | Any change touching auth, input, external I/O, secrets |
| `contractor-dude` | Kablan domain (repair advice, hire-a-pro, trades, cost estimates, job-site reality) | Anything user-facing in the repair/marketplace/hire-a-pro flows |
| `debug-dude` | Root-cause investigation (repro → investigate → hypothesize → fix) | Failure recovery when a worktree agent fails |
| `retro-dude` | Post-run retrospective + memory writeback | Phase 5; tunes the router over time |

## Dude Router

Before planning, classify the task along these axes and pick the relevant dudes. Err on the side of **fewer, relevant** dudes — 2-4 per hinge point is the sweet spot (plus `plan-dude` at plan review, which always fires).

| Signal in the task | Fire these dudes |
|---|---|
| Any non-trivial plan | `plan-dude` (always, at plan-review hinge) |
| Touches `src/app/**` (pages, components, client UI, styles, Tailwind classes) | `front-end-dude`, `designer-dude` |
| Touches `src/app/api/**`, `src/server/**`, `src/lib/db.ts`, `src/lib/session.ts`, `db/schema.sql` | `back-end-dude` |
| Touches auth, CSRF, rate limit, Stripe webhook, file upload, user input validation, Anthropic SDK input, env vars | `security-dude` |
| Touches repair advice, hire-a-pro, trades, cost estimates, marketplace matching, maintenance guides, chat system prompt | `contractor-dude` |
| Post-integration for any non-trivial change | `qa-dude` (always), plus whichever domain dudes fired during planning |
| Any worktree agent fails during Phase 2 | `debug-dude` (failure recovery loop) |
| End of the run, after integration + review gate | `retro-dude` (always) |

Record the routed dude set at the top of the plan output:

```
Routed dudes: plan-dude, front-end-dude, back-end-dude, contractor-dude
```

The user can override this before approving the plan.

## Dude Verdict Cache

Dude reviews are expensive. Cache their verdicts per worktree SHA so re-running orchestrate on the same code doesn't re-invoke them.

- Cache location: `.claude/cache/orchestrate/dudes/<sha>-<dude>.md`
- Key: `git rev-parse HEAD` of the worktree/branch being reviewed + dude name
- Before invoking a dude, check for an existing file at that path. If present and the SHA still matches, reuse it.
- After a dude finishes, write its verdict to that path.
- On a merged/rebased branch the SHA changes, so the cache naturally invalidates.

Create the cache directory with `mkdir -p .claude/cache/orchestrate/dudes` if it doesn't exist.

## Cost Budget

Every plan table surfaces an estimated cost per task. This is a rough guide, not a billing instrument — it lets the user see where the tokens are going before approving.

Use these relative units (each unit = ~1 sonnet-hour of agent work; numbers are illustrative, not authoritative):

| Model | Unit cost | When used |
|---|---|---|
| `haiku` | 1× | Mechanical changes, renames, boilerplate |
| `sonnet` | 5× | Standard implementation (most tasks — default) |
| `opus` | 25× | Complex reasoning, security-sensitive, cross-cutting refactors |
| `fable` | 75× | Hardest tasks only: multi-system invariant work, tasks where opus has already failed, maximum-intelligence architecture or security decisions. Use sparingly. |

Per-task cost = `model unit` × `complexity multiplier`:
- complexity `low` → ×1
- complexity `med` → ×2
- complexity `high` → ×4

Show the total at the bottom of the plan table as `Estimated cost: <N> units`. If it exceeds **200 units**, flag it explicitly and propose a reduction (fewer opus agents, smaller scope) before asking for approval.

## Workflow

### Phase 0: Route

1. **Parse flags.** Check for `--dry-run` and `--auto`. Record them.

2. **Understand the request.** Read the task description. If it's vague, ask one round of clarifying questions — no more (skip under `--auto`; make your best assumption and state it).

3. **Classify the task** using the Dude Router table. Output the routed dude set so the user sees which reviewers will fire. The user can redirect before Phase 1 (unless `--auto`).

4. **Choose the execution mode** — Direct / Single-threaded / Parallel — per *Execution modes* above, scaled to task size and interdependence. State the mode and one line of why. Default to single-threaded for any coupled coding; reserve parallel for genuinely independent or read-only work. **If Direct:** skip the rest of the workflow — invoke the matching dude skill now and jump to the Phase 4 gate.

### Phase 1: Research, Plan & Plan Review

1. **Explore the codebase.** Use the Explore agent or direct Glob/Grep/Read to understand what files and systems are involved. Map out dependencies between the areas that need to change.

2. **Lay out the work to match the mode.**
   - **Single-threaded:** write an *ordered sequence* of steps, each assigned to a dude as doer. Do NOT split into isolated agents. Dependencies between steps are expected and fine — that's exactly why this stays in one context.
   - **Parallel:** decompose into the smallest set of **genuinely independent** tasks. Independence means: different files (or non-overlapping sections); no task depends on another's output; each is verifiable in isolation. **If tasks have dependencies, they are not independent — run them single-threaded instead of forcing parallel phases.** Before any parallel code work, write the shared contract (interfaces, types, file boundaries, key decisions) to `.claude/cache/orchestrate/context.md` so workers can't make conflicting assumptions.

3. **Draft the plan in the shape that matches the mode.**

   **Single-threaded (the default):** an ordered step list — each step assigned to a dude as doer — NOT an agent table:

   ```
   ## Plan: <title>
   Mode: single-threaded · Routed dudes: <list> · Gate: <detected gate cmd>
   1. <step> — doer: <dude> — files: <paths> — risk: (filled in step 4)
   2. <step> — doer: <dude> — files: <paths> — risk: (filled in step 4)
   Acceptance: <observable outcomes> · Estimated cost: <N> units
   ```

   **Parallel:** a phase/agent table for the independent worktree agents:

   ```
   ## Plan: <title>

   Routed dudes: <comma-separated list from Phase 0>

   ### Phase 1 (parallel)
   | # | Task | Files | Agent Model | Complexity | Dudes | Cost | Risks |
   |---|------|-------|-------------|------------|-------|------|-------|
   | 1 | <description> | <file list> | sonnet | med | fe, design | 10 | (filled) |
   | 2 | <description> | <file list> | opus | high | be, sec | 100 | (filled) |

   ### Phase 2 (parallel, after Phase 1)
   ...

   ### Integration
   - <what needs to happen after all phases complete>

   ### Post-integration review
   - Dudes that will gate the merge: <list>

   **Estimated cost:** <total> units
   ```

   The `Dudes` column lists the **subset of the routed dudes** whose checklist gets inlined into that specific agent's prompt in Phase 2.

   **Model selection (escalate only when evidence demands it — sonnet handles most work):**
   - `haiku` — simple, mechanical changes (rename, move, add imports, boilerplate)
   - `sonnet` — standard implementation (new functions, API routes, components, tests). **Default for the vast majority of tasks.**
   - `opus` — complex reasoning (architecture, tricky bugs, security-sensitive code, cross-cutting refactors). Occasional.
   - `fable` — hardest cases only: multi-system refactors with tight invariants, tasks where opus already failed once, maximum-intelligence security or architecture decisions. Rare — most work never reaches this tier. `fable` model ID: `claude-fable-5`. Note: omit the `thinking` param entirely on fable (explicit `thinking: {type: "disabled"}` returns 400); use `output_config: {effort: "xhigh"}` for agentic tasks.

4. **Plan review by dudes (advisory, parallel).** **Skip this step in dry-run mode.**

   Before showing the plan to the user, fan out the **routed dudes plus `plan-dude`** in parallel via the Skill tool. Send them in a single message with multiple Skill tool calls. Check the verdict cache first.

   - `plan-dude` reviews the plan structurally (decomposition, sequencing, scope, completeness, dependencies, testability, blast radius). It returns a seven-axis score + ranked risks with severity (BLOCKER / HIGH / MED / LOW).
   - Domain dudes return forward-looking risks in their area: "plan risks I'd flag at this stage" — not a full review.

   Merge their risks into the **Risks** column, attributing each to the dude that raised it:
   ```
   [plan-dude BLOCKER] Phase 2 migration reads a column Phase 1 hasn't added yet — reorder
   [security-dude HIGH] Stripe webhook handler must be idempotent — add idempotency check before DB write
   ```

   If `plan-dude` returns a verdict of `Rework the plan.`, loop back to step 2 with its feedback before showing anything to the user. **Cap this at 2 rework passes.** Under `--auto`, if plan-dude still says rework after 2 passes, proceed with the best plan and log the unresolved flags as accepted risks — do not loop forever waiting for a user who isn't there.

5. **Present the plan.** Show the user the full table with Risks filled in and the total cost. Offer to adjust tasks, reorder phases, change model assignments, drop/add dudes, or reduce scope to cut cost.

6. **If `--dry-run`:** stop here. Output the plan, the routed dudes, the total cost, and the *exact agent prompts* (constructed as in Phase 2 step 2 but without spawning) so the user can review them. Return.

7. **Wait for user approval.** Do NOT proceed to execution until the user confirms. **Under `--auto`, skip this** — proceed straight to Phase 2.

### Phase 2: Execute (with failure recovery)

Once the plan is approved (or immediately, under `--auto`):

**Single-threaded mode (the default for coding):** do not spawn worktree agents. Work the ordered sequence yourself in this context, invoking the relevant dude skill via the Skill tool as the *doer* for each step, and carrying the plan + every decision made so far into each subsequent step (this is the "share full traces" principle — it's what prevents the conflicting-decision failures of parallel agents). Commit after each coherent step as a checkpoint, and verify (lint/test/build) before moving on. When the sequence is done, go to Phase 4. The steps below apply to **parallel mode only**.

1. **Create tracking tasks.** Use TodoWrite to create a task for each workstream item.

2. **Spawn agents in parallel.** For each task in the current phase, spawn an Agent with:
   - `isolation: "worktree"` — each agent works on an isolated copy of the repo
   - `run_in_background: true` — so they all run concurrently
   - A model override matching the plan's model column
   - A **self-contained prompt** that includes:
     - What to implement (specific, not vague)
     - Which files to modify (exact paths)
     - Any relevant context from the plan (don't say "based on the plan" — spell it out)
     - **The shared contract** from `.claude/cache/orchestrate/context.md` (so this agent's decisions stay consistent with its siblings), plus an instruction to append any interface-level decision it makes back to that file
     - **Inlined dude checklists** — for every dude in the task's `Dudes` column, paste the matching checklist from the "Per-Agent Dude Checklists" section below directly into the prompt. (These are a fallback because a worktree agent can't load the skill itself; single-threaded mode invokes the real dude instead.)
     - **Plan-review risks** attributed to this task (from the Risks column) — tell the agent to resolve or explicitly acknowledge each
     - **If touching any UI/frontend files:** read `DESIGN.md` before writing any markup or styles — fonts, colors, spacing, border radius, and background color are all specified there and must not be deviated from
     - **If creating or modifying an API route that touches the DB or Anthropic SDK:** include `export const runtime = "nodejs"` at the top of the route file
     - **Test instructions** (see Test Requirements section)
     - Instruction to commit their changes with a descriptive message

3. **Send ALL agents for a phase in a single message** so they launch simultaneously.

4. **Report progress.** As agents complete, update TodoWrite tasks and inform the user: what completed, branch name, key files, any failures.

5. **Failure recovery loop.** If a worktree agent returns a failure (failed tests, build errors, unresolved type errors, runtime errors it couldn't fix), do **not** immediately retry or give up. Instead:

   a. **Invoke `debug-dude` via the Skill tool** with the agent's failure artifact: the task description, the final transcript, the exact error, and the branch name. `debug-dude` returns a structured verdict:
      - `retry` — transient/environmental; re-run the same prompt
      - `retry-with-opus` — task was underserved by the model; upgrade sonnet → opus, or opus → fable for the hardest tasks
      - `fix-in-place` — debug-dude identified the root cause and supplied the exact fix; apply it on the worktree branch and mark the agent done
      - `escalate-to-user` — reveals a plan-level problem; surface to the user and pause the phase

   b. **Act on the verdict.** Do not second-guess debug-dude. If the verdict is `retry-with-opus`, spawn a new agent with the same prompt and the upgraded model: sonnet → opus; if already on opus and still failing, escalate to `claude-fable-5` — that is the final tier before user escalation. If the verdict is `fix-in-place`, apply the diff on the worktree and verify the detected project gate passes. If the verdict is `escalate-to-user`, show debug-dude's evidence and stop the phase.

   c. **Cap retries at 2.** If an agent fails, debug-dude says retry, and it fails again, escalate to the user rather than looping indefinitely. State the root cause and the remaining options.

6. **Between phases:** wait for all agents in the current phase to complete (including any retries from the recovery loop) before starting the next.

### Phase 3: Integrate

After all phases complete:

1. **List the worktree branches.** Show the user what each agent produced.

2. **Propose an integration strategy:**
   - Changes in completely separate files: simple sequential merge
   - Changes touch overlapping files: describe the conflict risk and suggest merge order
   - A task failed and was escalated: explain what went wrong and offer to retry, drop the workstream, or handle manually

3. **Execute integration only with user approval** (or automatically under `--auto`). Merge worktree branches one at a time, resolving conflicts as they arise — use the shared contract in `.claude/cache/orchestrate/context.md` as the source of truth when two branches made divergent decisions. After each merge, run type-check/lint.

### Phase 4: Review Gate & User Testing (parallel)

After integration, fire the post-integration gate. **Run the dudes and `/user-test` in parallel** — they're independent and this is the longest wall-clock phase of the flow.

1. **Identify reviewers.** The post-integration dude set is:
   - `qa-dude` — always, unless the change is trivially small
   - Every domain dude from the routed set whose files were actually touched by the integrated diff
   - `designer-dude` in **Mode D** (ships fixes) for any UI/visual change

2. **Check the verdict cache.** Compute `git rev-parse HEAD` of the integrated branch. For each planned dude, check `.claude/cache/orchestrate/dudes/<sha>-<dude>.md`. If present, reuse.

3. **Identify user-facing features.** From the completed workstream tasks, list every feature, page, or UI flow that is new or meaningfully changed.

4. **Ensure the dev server is running** before starting any user-test run (skip for non-web projects). If it isn't up, start the project's dev server (per *Stack awareness*) in the background and wait until it's ready.

5. **Fan out in a single message** — send all of these in parallel:
   - One Skill call per post-integration dude
   - One `/user-test --focus <feature>` call per newly added/changed feature (or a single `/user-test --diff` if there are more than 4 features)

6. **Aggregate verdicts.** Wait for all parallel runs, write each dude's verdict to the cache, then produce a single **ship / no-ship** summary:
   - Blocking issues (must fix before ship) — surface at the top with the dude or user-test that raised them
   - Non-blocking issues (worth filing) — grouped by source
   - Clean passes — one line each

   Do not skip this phase even if the changes seem small.

### Phase 5: Retrospective (retro-dude)

After the review gate, invoke `retro-dude` via the Skill tool. Pass it:

- The final plan (routed dudes, phase table with Dudes + Risks + cost columns)
- The worktree branch names and merged SHAs
- Pointers to the cached dude verdicts at `.claude/cache/orchestrate/dudes/`
- Agent outcomes (first-try success, retry with debug-dude, escalation)
- The Phase 4 aggregated review findings
- `git diff --stat <merge-base>..HEAD` for the run

`retro-dude` returns:

- An inline ~20-line retro summary (what worked, router tune, model tune, checklist additions, decomposition lesson, surprises)
- Memory writes to the **current project's** memory dir, resolved at runtime from cwd (e.g. `~/.claude/projects/<slug-of-cwd>/memory/`), for any durable lessons — never a hardcoded project

Show the retro summary to the user as the final output of the run. The memory writes are silent — retro-dude handles them via the auto-memory format.

## Per-Agent Dude Checklists

These are short, self-contained checklists that get **pasted into agent prompts** when the matching dude is in the task's `Dudes` column.

### front-end-dude checklist

```
Front-end checklist (inline verification):
- Server Components by default; mark "use client" only when needed (state, effects, browser APIs)
- Hooks follow rules-of-hooks; no conditional hook calls; deps arrays complete
- Forms have labels, error messages tied via aria-describedby, and keyboard-submit support
- Interactive elements are <button>/<a>, not <div onClick>; focus states visible; 44px min touch targets
- No hydration mismatches (no Date.now()/Math.random() in render, no window in Server Components)
- No layout shift from images/fonts (explicit width/height, font-display: swap already configured)
- Canonical Tailwind shorthand (see Tailwind section in orchestrate SKILL.md)
- Read DESIGN.md before writing any markup/styles — do not deviate
```

### back-end-dude checklist

```
Back-end checklist (inline verification):
- Call requireAuthenticatedSession() / requireAdminSession() from src/server/http/guards.ts at the top of any protected route — do not read cookies manually
- Validate all POST bodies with a Zod schema from src/lib/schemas.ts
- Use response helpers from src/lib/api.ts: ok(), badRequest(), unauthorized(), forbidden(), notFound(), serverError()
- export const runtime = "nodejs" on any route that touches the DB or the Anthropic SDK
- DB writes that could be retried are idempotent OR guarded by an idempotency key
- No N+1 queries; batch or join when iterating; use indexes that exist in db/schema.sql
- Errors do not leak stack traces or DB internals to the client
- CSRF-sensitive routes validate Origin via src/lib/csrf.ts
```

### designer-dude checklist

```
Design checklist (inline verification):
- Read DESIGN.md. Do not deviate from fonts, colors, spacing, radius, background
- Background is #f6f2ea warm cream — never pure white
- Amber #f5c76b reserved for the single most important action per screen — never for decoration
- Teal #0f766e for primary CTAs and active states
- Typography: Instrument Serif for display/hero only; DM Sans for body/UI; Geist Mono for code
- Radius scale: sm 6px, md 12px (rounded-xl), lg 20px (rounded-2xl/3xl), full 9999px
- No emoji icon grids, no gradient buttons, no decorative drop shadows
- Visual hierarchy clear at a glance — one primary action, one heading level jump per section
```

### security-dude checklist

```
Security checklist (inline verification):
- No secrets in code or committed env files; read from process.env only at module load or request scope
- All user input validated with Zod before hitting the DB, the filesystem, or Anthropic
- State-mutating endpoints validate Origin (CSRF) via src/lib/csrf.ts
- Rate-limit any new public endpoint via src/lib/rateLimit.ts (match existing limits, e.g. /api/chat 10/60s)
- No open redirects; redirect targets are allowlisted or same-origin only
- File uploads validate MIME, size, and content-type; never trust the extension
- If touching Stripe webhook: verify signature, handle event idempotently, never trust request body without verification
- If touching LLM prompts: user input is treated as untrusted; no prompt stitching that would let a user inject system-role content
- Errors logged server-side do not include secrets or session tokens
```

### qa-dude checklist (post-integration only)

```
QA checklist (post-integration gate):
- pnpm lint && pnpm test && pnpm build all pass
- Route crawl: every newly added route returns without 500
- Every newly added API route has at least one test covering the happy path and one covering invalid input
- No new console errors or network failures on the primary user flows
- a11y smoke: tab order works, no keyboard traps, focus visible on new interactive elements
- If a DB migration shipped: db/schema.sql matches what the code expects; pnpm db:reset succeeds
```

### contractor-dude checklist

```
Contractor / Kablan domain checklist (inline verification):
- Repair advice does not recommend unsafe DIY for jobs that legally require a licensed trade (electrical beyond low-voltage, gas, main water shutoff, structural)
- Cost estimates cite a plausible range with trade + region context; never a single dollar figure with no range
- Hire-a-Pro flows point users to real local contractors via web search (not the internal worker table — per project memory)
- Difficulty 4–5 jobs trigger the KABLAN_PRO_MATCH marker and surface the hire-a-pro button
- Trade names match the existing trade enum used in chat markers and worker matching
- Tone stays practical and non-condescending; no "always call a pro for everything" hedging that makes the product useless
```

## Test Requirements

Every agent prompt **must** include explicit test instructions tailored to what the agent is doing:

- **Adding or changing a feature:** Write tests covering the new or changed behavior. Place test files following the repo's existing conventions (e.g. `tests/**/*.test.ts`). Tests must pass before the agent finishes.
- **Removing a feature or code:** Delete any test files or test cases that exclusively cover the removed functionality. If a test file covers both removed and kept functionality, remove only the cases for the removed parts.
- **Refactoring with no behavior change:** Ensure existing tests still pass. Update imports or descriptions as needed, but do not delete tests that still apply.

Always end agent prompts with: "Run <the detected project gate — e.g. `pnpm lint && pnpm test && pnpm build`, `mvn verify`, or `make test`> before committing and fix any failures or warnings before finishing. If you cannot resolve a failure after two honest attempts, stop and report the exact error — orchestrate will invoke debug-dude."

## Tailwind CSS — Canonical Class Names

When any agent touches files that contain Tailwind classes, include this instruction in the prompt:

Use canonical/shorthand Tailwind class names wherever possible. Common examples:
- `px-4` instead of `pl-4 pr-4`
- `py-2` instead of `pt-2 pb-2`
- `p-4` instead of `pt-4 pr-4 pb-4 pl-4`
- `mx-auto` instead of `ml-auto mr-auto`
- `inset-0` instead of `top-0 right-0 bottom-0 left-0`
- `inset-x-0` instead of `left-0 right-0`
- `inset-y-0` instead of `top-0 bottom-0`
- `size-4` instead of `w-4 h-4`
- `overflow-hidden` instead of `overflow-x-hidden overflow-y-hidden`

Do not split shorthand utilities into their longhand equivalents. If you see existing longhand classes while editing, consolidate them.

## Rules

- **Pick the mode first; scale ceremony to the task.** Direct-mode tasks skip the plan table — just invoke the dude. Single-threaded and parallel tasks get a plan; show it unless `--auto`. Don't force a heavyweight multi-agent plan onto a one-file change.
- **Never skip the router.** Classify domains before drafting the plan — it determines which dudes fire and which checklists get injected.
- **Always fire `plan-dude` at plan review.** It's the structural conscience for every plan, regardless of domain.
- **Always fire `retro-dude` at Phase 5.** Over time it tunes the router and grows the checklists — skipping it means the skill stops improving.
- **Route parsimoniously.** Fire only the domain dudes whose area the task actually touches. 2-4 domain dudes per hinge point (plus plan-dude at plan review and retro-dude at the end).
- **Fan out in a single message.** Plan-review dudes, execution agents, and post-integration dudes+`/user-test` each go out as a single message with multiple tool calls.
- **Use debug-dude, don't guess.** If a worktree agent fails, do not retry blindly and do not patch symptoms yourself. Invoke debug-dude and act on its verdict.
- **Cap failure retries at 2.** Loop once at most; then escalate.
- **Single-threaded by default; isolate only what's independent.** Use parallel worktree agents only for genuinely independent or read-only work. Interdependent coding runs single-threaded with the dudes as doers — never split it across isolated agents that can't see each other's decisions.
- **When you do parallelize, pin the shared contract first** (`.claude/cache/orchestrate/context.md`) so workers don't make conflicting decisions, and cap it at 2-4 independent agents per phase.
- **Never have two agents modify the same file.** If two tasks need to touch the same file, they go in sequential phases — or just run single-threaded.
- **Surface the cost.** Include the total estimated cost in the plan and flag anything over 200 units before asking for approval.
- **Respect `--dry-run`.** In dry-run mode, no plan-review dudes, no agents, no integration. Just the plan + prompts + cost.
- **Include verification in every agent prompt.** Each agent validates its own work (type-check, test, lint) before finishing and resolves every plan-review risk attributed to its task.
- **Prefer dudes as doers.** In direct/single-threaded mode, invoke the real dude skill for full depth; inline its checklist only for parallel worktree agents that can't load a skill.
- **Respect `--auto`.** Under `--auto`, make every mode/plan/integration decision yourself and skip approval gates; never block on the user. Guardrails (plan-dude, debug-dude, the review gate, no push/deploy) still hold.
- **Respect the cache.** Check `.claude/cache/orchestrate/dudes/<sha>-<dude>.md` before invoking a dude; write results back after.
- **Be explicit in agent prompts.** The agent has zero context from this conversation. Write prompts as if briefing a new teammate who just sat down.
