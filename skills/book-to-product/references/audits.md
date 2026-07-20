# Audits, stopping condition, and final report

Run every audit before declaring the research phase complete, and record the
results in `06-FINAL-SYNTHESIS.md`. The audits exist because the most common
failure of a long book run is quiet incompleteness: a chapter represented
only by its summary, a "gap" that was never actually searched for in the
repo, a stale claim shipped into a constant.

## Book coverage audit

- Every chapter/appendix is `complete`, `not substantive`,
  `skimmed-out-of-focus`, or `unread` - the last two with a reason.
- `skimmed-out-of-focus` appears only under a narrow focus the user chose, and
  only for material genuinely outside it. It is not a shortcut for a long
  chapter, and a run with the default focus must have none.
- Every important figure/table has been examined, including figures that had to
  be looked at as rendered pages rather than extracted text.
- Central claims have precise source locations.
- No chapter was represented only by an introduction or summary.
- `claims/INDEX.md` accounts for every batch in the reading map's plan, plus
  `synthesis.md` if Pass 3 issued any claims. Every ID from `BK-001` to the
  counter in `CONTINUE-HERE.md` lands in exactly one file - no gaps, no reuse.
  A gap means a claim was issued an ID and then lost.

## Relevance audit

- Each relevant claim appears in the delta analysis.
- Each irrelevant claim has enough rationale to show it was considered rather
  than missed.
- Both feature opportunities and negative knowledge were considered.

## Repository audit

- Proposed gaps were checked against actual code and current research.
- Gaps reported by a subagent that became a P0 or P1 task were spot-checked
  against the files themselves. A delegated "this does not exist" is a claim
  you are putting in front of the user under your own name.
- Canonical/mirrored files and existing tests are named.
- No task duplicates shipped or already-planned work without saying so.
- Findings were reconciled against prior COMPLETE book runs, and any
  disagreement with a previously accepted claim is surfaced rather than
  silently resolved.
- Architectural and product non-negotiables are preserved or explicitly
  challenged through a doctrine-change proposal.

## Evidence audit

- Author claim, evidence, inference, and recommendation remain distinct.
- Time-sensitive claims are currently verified or implementation-blocked. None
  were kept on the grounds that verification was unavailable.
- Counterevidence and limitations are visible.
- Confidence labels match evidence quality.
- Quotations are short, necessary, accurate, and located.

## Task-quality audit

- Every proposed task traces to evidence and a user/product outcome, and every
  surviving Pass 5 decision reached its mapped Pass 7 outcome (templates.md).
  No `blocked-pending-verification` finding was dropped instead of written as a
  blocked task; no `narrow` decision lost the record of what was cut.
- Acceptance criteria are testable.
- Each task uses the template matching its effort, and no full-form task is
  padded with "n/a" fields that should have made it short-form.
- Dependencies, risks, affected files, fallbacks, and test plans are present
  on every full-form task.
- Priorities reflect Sheevook value and risk rather than novelty.
- The recommended order is dependency-aware.

## Stopping condition

The research-and-backlog phase is complete only when all are true:

- The source-integrity check and project baseline are complete.
- Every substantive book section has been closely read or explicitly marked
  unread with a reason.
- The claim ledger has survived a cross-book second pass.
- Every Sheevook-relevant claim has a repository delta classification.
- High-impact and time-sensitive claims have survived adversarial review and
  current verification, or their tasks are explicitly blocked.
- Durable research has been integrated without overwriting useful existing
  nuance.
- Opportunities include improvements, experiments, and reasoned rejections,
  not only new features.
- Every surviving opportunity is converted into an implementation-ready task,
  marked research-only, or rejected with a reason.
- All five audits pass.
- `CONTINUE-HERE.md` says `COMPLETE` and names no unattempted work.

A run that ends because the session got long, the context filled, or the
backlog looked long enough is not complete - it is paused, and the honest move
is to checkpoint and say so. "Complete" is a claim about the stopping
conditions above, nothing else.

## Final report to the user

Be concise; the artifacts contain the detail. Report:

- the book and edition actually analyzed;
- coverage and any unread/uncertain material;
- the 3-7 most consequential lessons for Sheevook;
- the files created or updated, distinguishing the tracked run directory from
  the gitignored `research/` write that lives on disk only;
- the number of claims, opportunities, and proposed tasks by priority;
- the strongest contradiction or rejected idea;
- the recommended first task/slice and why;
- verification debt or blockers;
- checks run.

Then close with the four-option decision in SKILL.md's "Finishing" section -
recommended first slice, quick wins only, pick specific IDs, or stop here.
Reporting the sequence you computed and then asking an open "which IDs?" throws
away the prioritization work; make the recommendation the default and let the
user override it.
