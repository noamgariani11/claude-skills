# helm — Active Lessons (the skill's self-improving playbook)

Read at the **start of every `/helm` run** (Startup step 1) and curated at the **end of every cycle**
(phase 5). This is how helm compounds: each cycle leaves it sharper. Treat the directives here as
standing amendments to SKILL.md doctrine — apply the highest-impact ones first.

## Maintenance contract (read before editing this file)

- **Guardrails are immutable by this loop.** Lessons may sharpen *technique, routing, briefing,
  sizing, research, and review* — they may **never** relax the review gate, the simplicity bar, the
  evidence requirement, the shipping-authorization rule, or surgical-edit discipline. A "lesson"
  that weakens a guardrail is invalid; delete it. Structural edits to SKILL.md guardrail text are
  human-only (propose here; never auto-apply).
- **Evidence or it didn't happen.** Every lesson cites the cycle(s)/project that produced it. Record
  what *wasted time*, not just wins. An honest "no new lesson this cycle" is a valid outcome — never
  fabricate an improvement to look productive.
- **Falsifiable & bounded.** Each lesson carries a confidence and a supporting/contradicting count.
  Contradicted once → downgrade; contradicted twice → retire to the bottom. Keep **≤ 30 active
  lessons**: merge duplicates, retire stale/low-impact.
- **Ranked.** Highest-expected-impact first, so a run that only reads the top still gets the most.
- **Project facts never live here.** Those go in that project's `.helm/brief.md`. This file is only
  about how to run *helm itself*, across any project. (Per-project failed approaches go in that
  project's `.helm/pitfalls.md`; cross-project anti-patterns become production-rule lessons here.)
- **Habits, not facts.** Claude already knows the *facts* ("knowing-that"); lessons exist to install
  *procedural habits* ("knowing-how"). Write each lesson as a **production rule** that fires
  automatically — trigger (`Apply when`) → action (`Do`) → the default it suppresses (`Don't`) — not
  as soft advice. If a lesson wouldn't change behavior on the next matching cycle, it isn't one.

### Lesson schema (a production rule: if-then-override)

```
### L-NNN · <short imperative title>   [conf: high|med|low] · [area: research/plan/dispatch/review/process]
- **Apply when:** <the trigger — the situation that should make this fire>
- **Do:** <the action to take, automatically — concrete and specific>
- **Don't:** <the default behavior this overrides/suppresses>   (omit if none)
- **Why / evidence:** <what happened; cite project + cycle / log entry>
- **Provenance:** added <date> · supporting: N · contradicting: M
```

---

## Active lessons (apply every cycle, highest-impact first)

### L-001 · Re-anchor from disk before reasoning   [conf: high] · [area: process]
- **Do:** Open every cycle by reading `brief.md` North Star + top of `backlog.md` + last 1–2 `log.md`
  entries. Do not plan or dispatch from conversation memory — it is drifting the moment a run gets long.
- **Why / evidence:** Long-running agents reliably hallucinate state after ~1 hour and contradict their
  own earlier choices (seed lesson from agent-failure-mode research, 2025–2026).
- **Apply when:** Always, phase 0.
- **Provenance:** added 2026-06-05 · supporting: 0 (seed) · contradicting: 0

### L-002 · Brief the why, not just the what   [conf: high] · [area: dispatch]
- **Do:** Every task brief states the user/business value and the definition of success before the
  files. Engineers given the *why* make better local decisions and need fewer round-trips.
- **Why / evidence:** Seed principle — a chunk dispatched as "change X in file Y" with no purpose
  produces literal-but-wrong work that review bounces.
- **Apply when:** Every dispatch.
- **Provenance:** added 2026-06-05 · supporting: 0 (seed) · contradicting: 0

### L-003 · Small chunks, capped concurrency, real review   [conf: high] · [area: dispatch]
- **Do:** Dispatch 1–2 chunks at a time and review each before sending more. Throughput without a
  review gate just ships slop faster.
- **Why / evidence:** Seed — validation theater and cost-explosion failure modes both stem from
  fanning out faster than you can verify.
- **Apply when:** Phase 3, always.
- **Provenance:** added 2026-06-05 · supporting: 0 (seed) · contradicting: 0

### L-004 · Delegate heavy reading; keep helm's context lean   [conf: high] · [area: process]
- **Do:** Send codebase exploration, code writing, and reviews to subagents/skills with fresh
  contexts. Helm holds summaries and decisions, never raw file dumps — that's what lets it run long.
- **Why / evidence:** Seed — the orchestrator's own context is the scarce resource; filling it with
  file contents is the fast path to drift.
- **Apply when:** Always.
- **Provenance:** added 2026-06-05 · supporting: 0 (seed) · contradicting: 0

### L-005 · Demand evidence the code ran   [conf: high] · [area: review]
- **Do:** A chunk is not `done` until a review skill confirms it works with observed output. Reject
  green claims that show no run. Findings go back as a new groomed item, never silently accepted.
- **Why / evidence:** Seed — "validation theater" is the failure mode where reviews pass broken work;
  the only defense is real evidence, not the author's say-so.
- **Apply when:** Phase 4, always.
- **Provenance:** added 2026-06-05 · supporting: 0 (seed) · contradicting: 0

### L-006 · Acceptance starts failing; never weaken a test to pass it   [conf: high] · [area: review]
- **Do:** Track each chunk's acceptance as pass/fail items that begin failing and only flip on an
  *observed* pass. Deleting/skipping/weakening a test to make a criterion green is an automatic fail.
- **Why / evidence:** Anthropic's long-running-agent harness — agents declare work done prematurely;
  the cure is a feature list where items start failing and "it is unacceptable to remove or edit tests."
- **Apply when:** Grooming (write criteria) and phase 4 (verify them).
- **Provenance:** added 2026-06-05 · supporting: 0 (seed) · contradicting: 0

### L-007 · Re-acquire context from git + progress, verify base health, then work one feature   [conf: high] · [area: process]
- **Do:** On resume read `git log` + `.helm/` and run the fast gate to confirm the base is green
  before new work; build features one at a time; commit each accepted chunk as a checkpoint and
  revert to the last green commit when one goes bad.
- **Why / evidence:** Anthropic's harness research — session-startup protocol (read progress/git +
  verify) and incremental single-feature work were "critical"; git commits enable recovery.
- **Apply when:** Phase 0 (resume) and phase 3 (dispatch/recover).
- **Provenance:** added 2026-06-05 · supporting: 0 (seed) · contradicting: 0

### L-009 · MUST call ScheduleWakeup at the end of every --once cycle   [conf: high] · [area: process]
- **Apply when:** Running in `--once` mode (the `/loop /helm --once` pattern).
- **Do:** Before returning, call `ScheduleWakeup(delaySeconds: 60, prompt: "/loop /helm --once", reason: "next helm cycle")`. The prompt MUST include the `/loop` prefix — the harness re-enters the loop skill on wake-up, not helm directly. This is the **only** mechanism that re-fires the loop. A clean return without it ends the loop silently.
- **Don't:** Just return at the end of a cycle and assume the loop re-fires automatically — it does not. Also don't use `"/helm --once"` without the `/loop` prefix; the wake-up fires a raw prompt and `/loop` is needed to re-enter the scheduling harness.
- **Why / evidence:** Helm stopped running after 1–2 cycles because Phase 6 said "return cleanly so the loop re-fires you" — but that's false. The `/loop` harness only re-invokes when ScheduleWakeup is called. Observed 2026-06-05. Prompt format corrected 2026-06-09 (Cycle 218).
- **Provenance:** added 2026-06-05 · supporting: 2 · contradicting: 0

### L-010 · NEVER yield to the user after a Skill() returns — continue immediately   [conf: high] · [area: process]
- **Apply when:** A skill (`/back-end-dude`, `/front-end-dude`, etc.) finishes and returns output in the attended bare-`/helm` run mode.
- **Do:** As soon as a skill returns, **immediately** (in the same response): (1) do Phase 4 review inline — observe each acceptance criterion pass/fail with evidence; (2) update `.helm/backlog.md` and `log.md`; (3) start the next cycle — re-anchor from disk, run research thrust, groom next item, dispatch. Never produce a response that ends without dispatching the next chunk or starting the next cycle.
- **Don't:** Treat a skill's return as the end of your turn. Ending the turn yields control to the user and breaks the perpetual loop. This is the most common failure mode observed.
- **Why / evidence:** User corrected this three separate times (three separate occasions helm stopped after a skill returned). Root cause: Claude naturally ends a turn after the last tool call resolves. The fix is to keep producing tool calls and text until the next dispatch is sent. Observed 2026-06-05 × 3.
- **Provenance:** added 2026-06-05 · supporting: 3 · contradicting: 0

### L-011 · NEVER use Skill() dispatch in --once mode; do work inline or accept loop death   [conf: high] · [area: process]
- **Apply when:** Running in `--once` mode (the `/loop /helm --once` pattern).
- **Do:** Do all execution work **inline** (Read/Edit/Bash tools directly, or via Agent tool which returns results). At the end of every cycle, call ScheduleWakeup as the very last action.
- **Don't:** Call `Skill()` to dispatch to a subskill (back-end-dude, front-end-dude, etc.) in `--once` mode. `Skill()` hands the conversation over to the subskill completely — when the subskill finishes, the turn ends with the subskill's output. Helm never gets control back and never calls ScheduleWakeup. Loop dies silently.
- **Why / evidence:** Two separate failures on BL-005a: (1) Cycle 10 called ScheduleWakeup before Skill() — back-end-dude never ran. (2) Cycle 11 called Skill() without premature ScheduleWakeup — back-end-dude ran and completed, but the loop died because back-end-dude's message was the last in the turn, not helm's. User had to manually restart. Observed 2026-06-05 × 2.
- **`--once` dispatch options that work:** (a) Do work inline with Read/Edit/Bash — helm keeps the turn and calls ScheduleWakeup at the end. (b) Use `Agent()` tool (not `Skill()`) — Agent returns its result as a value, then helm continues in the same turn and calls ScheduleWakeup.
- **Provenance:** added 2026-06-05 · supporting: 2 · contradicting: 0

### L-012 · Run `pnpm db:generate` after pulling if typecheck shows Prisma client errors   [conf: high] · [area: process]
- **Apply when:** After `git pull` / merge, the first typecheck shows `Module '"@prisma/client"' has no exported member` errors or callback parameters typed as implicit `any` in Prisma-result maps.
- **Do:** Run `pnpm db:generate` immediately before retrying typecheck. This regenerates the Prisma client from the current schema, which pulls often fail to trigger automatically.
- **Don't:** Try to fix the TS errors manually or add type annotations — they are a symptom of a stale client.
- **Why / evidence:** Cycle 198: pulled 7 commits; TaxAssessment not exported + implicit-any on all Prisma result callbacks; `pnpm db:generate` fixed all errors instantly. CLAUDE.md already documents this but it isn't yet a procedural habit.
- **Provenance:** added 2026-06-08 · supporting: 1 · contradicting: 0

### L-008 · You are Claude A improving Claude B — refine the brief, not just the backlog   [conf: high] · [area: process]
- **Do:** Treat every dispatched agent's struggle/round-trip as a defect in *your* brief, routing, or
  sizing. Each cycle, turn an observation into a concrete improvement to the task-brief template,
  routing, LESSONS, or an additive fix to a review skill. Use strong language ("MUST") for repeat misses.
- **Why / evidence:** Anthropic's recommended skill-iteration loop: Claude A authors/refines while
  observing Claude B use the skill on real tasks; improvements come from observed behavior, not assumptions.
- **Apply when:** Phase 5, every cycle.
- **Provenance:** added 2026-06-05 · supporting: 0 (seed) · contradicting: 0

### L-013 · Verify each audit finding against the code before fixing; 0-code cycles and deferred migrations are valid   [conf: high] · [area: review]
- **Apply when:** A dispatched audit/review agent returns findings (esp. `--quality` mode), especially ones it hedges ("not obviously guaranteed", "might reject", "could double-insert").
- **Do:** Before fixing ANY finding, open the cited code AND everything that governs its runtime behavior — the functions it calls, AND the CSS cascade (layered vs unlayered rules, base styles, framework precedence) for styling findings — and confirm the failure is real at runtime. Treat a hedged finding as a hypothesis, not a fact. When all findings turn out latent / false-positive / speculative, ship NOTHING and log an honest "0 active bugs, here's the evidence" — that is a correct, valuable quality outcome. For a real-but-latent finding whose fix needs an action you can't verify in-loop (a DB schema migration with prod-deploy risk, anything needing a live DB/TTY), DEFER it: write a full senior backlog brief instead of shipping an unverifiable change in an unattended loop. **If you already dispatched a fix agent and then discover the finding is a false positive, STOP it immediately (TaskStop) and confirm a clean tree before it churns files.**
- **Don't:** Apply an audit's suggested fix on its say-so; manufacture a commit so the cycle "produced something"; ship a Prisma migration you can't observe applying cleanly; or "fix" a class-token/style that a higher-precedence rule already overrides (pure no-op churn that masquerades as a real fix in the diff).
- **Why / evidence:** (1) Q4 (Miskari, 2026-06-22) — worker/jobs audit flagged `void notifyJobFailure(...)` as an unhandled-rejection risk; reading the impl showed it try/catches and always resolves (false positive). (2) Q5 — ~32 form controls flagged for `border-rule` (apparent WCAG 1.4.11 violation); `globals.css` has an UNLAYERED rule already overriding them to `field-border` — no violation; stopped the fix agent before ~20 files of no-op churn. (3) Q9 — audit flagged `comps.length` (unfiltered) as inflating the dashboard protest tier +17 pts; tracing the data flow showed comps only exist with a protest, and `scoreProtestOpportunity` early-returns "filed" when a protest exists, so the count is NEVER consumed → the bug is real-but-dead, MED→latent, no user impact. The audit found wrong code but wrongly claimed impact.
- **Also verify the audit's claimed IMPACT, not just whether the code is wrong:** trace the value to the user-visible output through every guard/early-return/binding. "Wrong code" + "never consumed" = a latent fix, not a user-facing bug — record it honestly and don't overstate it.
- **A CRITICAL severity does NOT license a blind fix — if anything the bar is higher.** The instinct on a CRITICAL ("feature is dead", "data is wrong") is to rush a fix. Resist it when the fix is a multi-file REDESIGN with multiple valid shapes AND a worse failure mode than the bug. Q26 (Miskari, 2026-06-22): the recurring-inspection engine was 100% dead (anchor written `status:completed`, worker required `status:scheduled`) — a real CRITICAL. But the correct fix spanned worker+action+UI, and a partial/wrong choice would mint **duplicate** inspections (silent no-op → active corruption: strictly worse), plus it needed a unique-index migration and a live worker+DB to verify. Shipped NOTHING; wrote a full senior brief (the recommended model + acceptance criteria, incl. "extract a pure planner so the date math is unit-testable without a live worker"). Deferring a well-evidenced CRITICAL with a senior brief beats shipping an unverifiable redesign that could make it worse.
- **For a CONVENTION/unit mismatch between modules, find the source of truth before deciding which side is wrong — the flagged site may be the correct one.** When an audit flags "module X disagrees with module Y about units" (cents vs dollars, ¢/kWh vs $/kWh), don't assume the cited line is the bug. Identify the canonical function the rest of the system trusts (the one the majority of call sites + the formatter + the input form agree with) and fix the OUTLIER to match it. Q27 (Miskari, 2026-06-22): `bill-rate-audit` ×100'd a `per_kwh` rate as dollars, but `estimateMonthlyCostCents` + `formatRate` + `unitRateToDollars` + the rate form all treat per_kwh as ¢/kWh — three-to-one, so the audit was the outlier. "Fixing" the wrong side would have broken the working cost/savings engine. Then centralize the convention in ONE helper (`unitRateToCents`) so it can't drift again.
- **On a high-blast-radius surface (security/privilege/money-movement), independently verify the audit's CLEAN verdict, not just its findings.** A false "clean" on a privilege boundary is as dangerous as a missed bug, and the cost of one own-read is tiny against the blast radius. Don't accept "the surface is locked down" on the audit's say-so — re-read the single load-bearing control yourself. Q28 (Miskari, 2026-06-22): the impersonation audit returned 0 findings ("locked down"); I still read `startImpersonationAction` + `maybeImpersonate` + the cookie crypto myself to confirm the actual escalation gates (super-admin checked first, `actorId` bound to the acting operator not the target, consumption re-gates on super-admin+actorId). Scale your own-verification to the cost of a wrong "clean," not to whether there's a finding to fix. (A clean security cycle with first-hand evidence is a valuable deliverable — log the evidence, ship no code.)
- **Provenance:** added 2026-06-22 · supporting: 5 · contradicting: 0

### L-015 · Don't "fix" intentional product behavior; a behavior change needs a product decision   [conf: high] · [area: review]
- **Apply when:** An audit flags behavior as a bug (duplicate sends, "too many" alerts, an aggressive cadence, a missing step) in `--quality`/autonomous mode where there's no user to confirm intent.
- **Do:** Before fixing, decide whether it's a CORRECTNESS bug (does something unintended/inconsistent -> fix it) or an INTENTIONAL design choice (a deliberate product cadence/policy -> leave it; record it as a noted design item, not a fix). Look for signals of intent: a consistent pattern across siblings, an explanatory comment, a ref/key structure that deliberately re-fires. Only ship a fix when the current behavior is provably unintended.
- **Don't:** Unilaterally change product behavior (e.g. convert "remind daily until resolved" into "remind once") just because an audit labeled it "duplicate"/"excessive". That's a product decision you can't make autonomously; "fixing" it is unwanted scope, not hardening.
- **Why / evidence:** Q13 (Miskari, 2026-06-22) -- scheduler audit flagged 5 "duplicate" daily-nag enqueuers as MED. Tracing them showed range-query + stable ref = deliberate "nag until resolved" design (consistent across due-bill/contract/protest/exemption/switch-window). Only the DST day-flip (an UNINTENDED double-send from a wall-clock bug) was a real correctness fix; the daily-nag cadence was left as a noted design item. Fixing it would have silently changed product behavior.
- **Provenance:** added 2026-06-22 · supporting: 1 · contradicting: 0

### L-014 · After consecutive verified-clean cycles, rotate to the highest-bug-probability surface   [conf: high] · [area: process]
- **Apply when:** Running `--quality` and the last 2+ cycles found 0 real bugs (the audited slices were well-built core logic).
- **Do:** Deliberately pick the next slice by where bugs ACTUALLY hide, not by rote rotation: fragile external-data parsing (scrapers/APIs/file/LLM output), complex multi-branch state machines, unit-conversion boundaries (cents/dollars, %, timezones), and recently-added or least-tested code. These convert a clean streak into real findings.
- **Don't:** Keep auditing the well-built core (money helpers, RLS, queue) just because it's next in the list — a third consecutive "verified-clean" there is low marginal value when fragile surfaces sit unaudited.
- **Why / evidence:** Miskari Q1-Q5 found only tiny/no bugs on coverage/multi-tenancy/money/worker/design-tokens (all well-built). Q6 rotated to CAD/external parsing on this exact instinct and immediately found a CRITICAL silent 100x money-corruption (cents passed where dollars expected, double `dollarsToBigCents`). Highest-value find of the run.
- **Provenance:** added 2026-06-22 · supporting: 1 · contradicting: 0

### L-016 · A query that SELECTS a field it never filters/uses is a smoking gun for a dropped filter   [conf: high] · [area: review]
- **Apply when:** Auditing read/report/aggregation code (`--quality`), especially anything that produces a money/count/status figure from a DB query.
- **Do:** When a query `select`s (or `include`s) a column that the downstream code never reads, treat it as a high-probability DROPPED FILTER — someone intended to gate on it and the gate was lost (or never wired). Trace whether that field SHOULD constrain the result. The canonical correct gate often already exists elsewhere in the codebase (a write-path, a sibling helper) — reuse it, don't reinvent the predicate.
- **Don't:** Wave it off as a harmless over-select. The unused field is the tell, not noise.
- **Why / evidence:** Q23 (Miskari, 2026-06-22) — the Tax Savings report `select`ed protest `status` on both the Excel route and the on-screen section but filtered only on `resultMarketValueCents !== null`, never on `status`. That dropped filter let a `withdrawn`/in-progress protest with a tentative value be reported to owners as realized savings. The correct gate (`informal_done`/`arb_done`) already lived inline in the protest update action; centralizing + reusing it fixed both surfaces. The selected-but-unused `status` was the entire giveaway.
- **Provenance:** added 2026-06-22 · supporting: 1 · contradicting: 0

### L-017 · After confirming a bug, grep the whole codebase for the bug CLASS, not just the cited site   [conf: high] · [area: review]
- **Apply when:** You've verified a real finding in `--quality` mode, especially a mechanical/idiom-level bug (a date-math overflow, a missing `/100`, a bare-prisma call, a missing status filter, an unguarded server action).
- **Do:** Before closing the cycle, `git grep` the underlying primitive/idiom across `src/` to find sibling instances the audit (which read a bounded file set) never saw. Fix the ones that are real with the same shared helper. A single audit pass scopes to the files you pointed it at; the bug class usually isn't that polite.
- **Don't:** Fix only the one file the audit cited and assume the class is contained.
- **Why / evidence:** Q24 (Miskari, 2026-06-22) — the lease audit flagged a `Date.setMonth(getMonth()+n)` month-overflow on the renewal-offer LETTER (cosmetic, MED). Grepping `setMonth(` across the repo found the SAME overflow in `applications/[id]/actions.ts` building a draft lease `endDate` that gets PERSISTED on `lease.create` — a higher-value bug (wrong stored date, not just a printed one) the audit never looked at. Both fixed in one commit via the existing clamping `addMonths()` helper. The grep found the instance that actually mattered.
- **Companion to L-016** (selected-but-unused = dropped filter): L-016 is how you SPOT a class; L-017 is how you make sure you've KILLED all of it.
- **2nd confirmation:** Q25 (Miskari, 2026-06-22) — a self-driven audit of the unauth `/apply` intake found a finite-but-huge-dollar overflow (`1e308 * 100` → Infinity → `BigInt()` throws → 500). Grepping the conversion class (`BigInt(Math.round(` / `dollarsToBigCents`) surfaced the SAME unauth crash in `/api/public/rfq-quote` — a second public endpoint the audit never opened. Both fixed via one shared guarded helper. Sub-pattern worth remembering: a value that passes `Number.isFinite`/`z.number()` can still overflow when SCALED (×100) and crash a downstream `BigInt`/`Math.round` — type-validity ≠ magnitude-safety, especially on unauth inputs.
- **3rd confirmation (grep CONFIRMS containment too):** Q27 (Miskari, 2026-06-22) — after fixing a per_kwh ¢/$ unit mismatch in `bill-rate-audit` + the holdover email, `git grep`'d the `rate * 100` class across the repo. This time the grep found NO other drift site (the rest were flat_monthly dollars / a percent calc / cap rates, all correct). A clean grep is a positive result: it converts "the audit found 2 sites" into "the class is provably 2 sites, now killed" — close the cycle with confidence instead of a nagging "did I get them all?".
- **4th confirmation:** Q37 (Miskari, 2026-06-22) — the dashboard audit found ONE truncated-headline bug (Overdue/Due-30d totals summed a `take:8` display array). Grepping the class (`.length`/`.reduce` count-displays vs their `take`-capped sources) found the SAME bug on the "Renewals" stat (`contractsEnding.length`, `take:6`). 1 audit finding → 2 fixes.
- **5th confirmation — grep the PATTERN, not the FILE SET:** Q46 (Miskari, 2026-06-22) — Q42 fixed a non-atomic protest.update→taxAssessment.update conclusion write-back in `updateProtest`, but its "atomicity sweep" scanned only the highest-WRITE files and called the class contained. Three cycles later, probing an unrelated class (missing-Zod) on `tax/hearing-day/actions.ts` surfaced the IDENTICAL unwrapped write-back in `recordHearingOutcome` — a file Q42 never opened. Lesson sharpening: when you close a class, grep the exact column/idiom pair that defines it (`finalAppraised/MarketValueCents` on a `taxAssessment.update` next to a `protest.update`), NOT "the files most likely to have it." A column-grep is exhaustive and cheap; a file-scoped audit is neither. After the Q46 column-grep, the class is provably 2 sites, both transactional. Corollary: a sibling can hide for many cycles and be found incidentally — so a clean *pattern* grep is the only honest "contained," a clean *file* sweep isn't.
- **Provenance:** added 2026-06-22 · supporting: 5 · contradicting: 0

### L-018 · Code that contradicts its OWN documentation is a high-confidence bug — fix the code to the stated intent   [conf: high] · [area: review]
- **Apply when:** Auditing a module that carries a docstring, a named constant/notes block, or inline comments stating the intended behavior/schedule/spec.
- **Do:** When the code's behavior diverges from what the SAME file documents (a comment says "12% in July" but the branch yields 11%; a docstring says "$/unit" but the math treats cents), treat it as a near-certain bug AND a low-risk fix — the author told you the intent, so aligning the code to it is unlikely to be unwanted. This is one of the highest-confidence finding signals: no external spec lookup needed, the contradiction is self-contained. Quote BOTH the doc and the code in the finding.
- **Don't:** Defer to the code as ground truth when the doc disagrees, or treat such a divergence as "intentional" without a separate signal — self-contradiction is the opposite of intent. (Contrast L-015: an intentional simplification is one the docs CONFIRM, e.g. "advisory only, pro-rated months not captured" — there the docs and code agree on the simplification.)
- **Why / evidence:** Q29 (Miskari, 2026-06-22) — `computePenalty` ramped the TX Sec 33.01 penalty with `monthsLate <= 6`, yielding 11% in July, but the file's own `TEXAS_PENALTY_NOTES` and docstring both said "Jul 1+: 12%". The notes encoded the author's intent; the branch math was the typo. One-char fix (`<= 6` → `< 6`) with full confidence, no statute lookup required (though it also matched the statute). Same shape in Q27: `bill-rate-audit`'s JSDoc said "$/unit, NOT cents" but the whole subsystem treats per_kwh as cents — there the doc was ALSO stale, so cross-check which of {code, doc} the rest of the system agrees with (L-013 convention-source-of-truth) when BOTH might be wrong.
- **2nd confirmation (comments, not just docstrings):** Q34 (Miskari, 2026-06-22) — three comments in `documents.ts` claimed the worker's R2 reconciliation tick "sweeps orphaned R2 objects"; tracing `r2ReconcileTick` showed it's read-only and runs the opposite direction (DB→R2, never enumerates R2). The comments described a data-retention safety property that didn't exist. Here the fix was to the COMMENTS (the tick's behavior was intentional + useful) — the inverse of Q29 where the fix was to the code. Rule of thumb: when code and its own doc disagree, find which side the rest of the system + the component's actual behavior support, then correct the OTHER side. Correcting a false safety-relevant comment is real work, not churn — it stops a future dev from trusting a guarantee that isn't there.
- **Provenance:** added 2026-06-22 · supporting: 2 · contradicting: 0

### L-019 · A brief's proposed APPROACH is a starting point, not a mandate — re-evaluate it against existing patterns at implementation time   [conf: high] · [area: dispatch]
- **Apply when:** Picking up a groomed backlog item (especially one YOU briefed cycles earlier) to implement it.
- **Do:** Before executing the brief's "Approach" section, re-derive the simplest/safest path from the CURRENT codebase: grep for an existing precedent that already solves the same shape. If a simpler pattern exists, take it and note the deviation in the commit + the backlog entry. A brief written at grooming time optimizes for "what would work"; at implementation you also know "what the codebase already does well" — prefer the latter when it's lower-risk.
- **Don't:** Mechanically build what the brief said just because you (or a planner) wrote it. A brief is a hypothesis about HOW, not a contract — re-test it. Especially resist building a NEW security-sensitive surface (an unauth route, a sweeper, a new gate) when an existing, already-audited pattern achieves the same end with less blast radius.
- **Why / evidence:** Q36 (Miskari, 2026-06-22) — BL-Q070 (a broken investor-page hero image) was briefed as "add a new token-scoped unauthenticated image route." At implementation, the tenant portal's existing pattern (presign the R2 object SERVER-SIDE in the RSC, render `<img src={signed}>`) solved it with NO new unauth route, NO middleware change, and inherited the page's already-audited revoke/expiry + orgPrisma scoping. Building the briefed route would have traded a safe-broken-image for a brand-new file-serving attack surface to get perfectly scoped. The simpler precedent was strictly lower-risk.
- **Provenance:** added 2026-06-22 · supporting: 1 · contradicting: 0

### L-020 · A `take:N`-capped query reused as the source of a headline total/count is a truncation bug   [conf: high] · [area: review]
- **Apply when:** Auditing any page/component that shows BOTH a list (paginated / "top N") AND a summary stat (a total, a count, an average) over the same data.
- **Do:** When a `findMany({ ..., take: N })` array is also `.reduce()`d for a money total or read via `.length` for a count, flag it: the display cap silently caps the summary. The summary must come from a separate UNBOUNDED `aggregate({_sum,_count})` / `count()` (with the where clause byte-identical to the list query), while the `take:N` array stays only for the rows. Grep the file for `.reduce(`/`.length`/`.toString()` on every `take:`-limited variable.
- **Don't:** Trust that a headline number is right just because the list below it looks right — the list is intentionally truncated; the number must not be. Don't reuse one query for both.
- **Why / evidence:** Q37 (Miskari, 2026-06-22) — the operator dashboard summed `overdue`/`upcoming` bill arrays (each `take:8`) for the "Overdue $" + count cells, so an org with 20 overdue bills saw "$8,000 · 8 bills" instead of $20k · 20 — the most-watched home-screen number understated ~60%. Same shape on "Renewals" (`contractsEnding.length`, `take:6`). Both fixed with unbounded aggregates; the `take:N` arrays kept for the rows. A `take:` literal next to a summary stat is a high-yield audit tell.
- **Companion to L-016/L-018:** another spotting heuristic — L-016 (selected-but-unused = dropped filter), L-018 (code vs its own doc), L-020 (take-capped array summed for a headline). Once spotted, L-017 (grep the class) kills all instances.
- **2nd confirmation (strong — the class recurs broadly):** Q38 (Miskari, 2026-06-22) — a codebase-wide sweep for this exact pattern (after the 2 dashboard fixes) scanned ~250 `take:` sites and found **8 more** confirmed truncated headlines (schedule "$ unpaid" header even disagreed with its own footer; contracts "est. monthly"; tenant ledger cards; + a take:500 cluster) plus a large correctly-handled remainder. Lesson: this isn't a one-off — when you fix ONE take-capped-headline bug, the same UI idiom has almost certainly been copied across many list pages; sweep them all. The SAFE cases (list rows, form dropdowns, take:1 lookups, "+N more", a separate `count()`/`groupBy` already backing the headline) are easy to distinguish by tracing whether the capped array reaches a displayed total/count.
- **Provenance:** added 2026-06-22 · supporting: 2 · contradicting: 0

### L-021 · Reframe a diffuse quality DIMENSION as a finite set of greppable code-smell patterns, then sweep   [conf: high] · [area: review]
- **Apply when:** Tasked to audit a fuzzy cross-cutting dimension — "error/zero-state handling", accessibility, mobile/responsive, performance — where "does everything handle X?" is un-auditable and a generic page-by-page read is low-yield.
- **Do:** Translate the dimension into a CONCRETE list of failure-mode code patterns that are greppable, then sweep each across the codebase and triage (reachable bug / guarded / guaranteed-safe). Zero-state → `Math.max(...arr)` (empty→±Inf), `arr[0].field` (throws when `noUncheckedIndexedAccess` off — check the tsconfig), `/ x.length`/count/sum (NaN/Inf), `.toFixed`/`Math.round` on NaN, `new Date(null)`, `JSON.parse` of nullable cols. (a11y → `<img>` w/o alt, icon-button w/o aria-label, raw color tokens, `<div onClick>`; perf → N+1 `findMany` in a `.map`, unbounded `findMany` in a request path; mobile → fixed px widths, `overflow` without scroll.) The grep gives finite, verifiable coverage instead of a vague "looked at it".
- **Don't:** Try to audit a diffuse dimension by reading pages and asking "is this okay?" — you'll miss the systematic instances and can't claim real coverage. Don't report a dimension "clean" without a pattern-by-pattern sweep.
- **Why / evidence:** Q41 (Miskari, 2026-06-22) — the "error/zero-state" dimension had never been swept (too diffuse). Reframing it as 6 greppable crash patterns made it tractable: a focused sweep verified DOZENS of sites guarded and found exactly ONE real bug (an `Infinity%` budget alert on a valid 0-budget input, dashboard home screen). Result: a concrete "new users won't hit a crash/garbage" verdict with first-hand evidence — impossible to claim from a generic read. Same engine as L-020 (which reframed "wrong dashboard numbers" as "take:N array reused for a headline").
- **2nd confirmation:** Q42 (Miskari, 2026-06-22) — reframed "data integrity under partial failure" (un-auditable as stated) into the greppable pattern "2+ DEPENDENT writes via separate `orgPrisma` calls NOT in one `withOrg`/`$transaction`". The sweep verified the prime suspects already-transactional and found 2 real bugs (an inconsistent protest↔assessment pair; a duplicate-tenant-on-retry). Confirms the engine generalizes from crash-classes to integrity-classes. **A standing move once a few cycles in:** most remaining bug-yield is in CLASSES (a repeated risky idiom) more than in one-off logic errors — once a class is named + greppable, one sweep finds + kills all instances and earns a real coverage claim.
- **3rd confirmation:** Q43 (Miskari, 2026-06-22) — "cross-tenant data exposure" → the greppable pattern "a user-supplied FK id written to a create/update without `assertRefsInOrg`/an org-scoped findFirst". Found 1 HIGH (reconcile rent-match disclosing another org's tenant/lease) + 1 MED-latent among an otherwise broadly-defended class (124 guard sites). Security classes, integrity classes, crash classes, correctness classes — all yield to the same name-it→grep-it→sweep engine. By this depth in a campaign it's the DEFAULT cycle shape: pick an un-swept risky idiom, sweep it, fix the real tier, queue/decline the rest.
- **Provenance:** added 2026-06-22 · supporting: 3 · contradicting: 0
