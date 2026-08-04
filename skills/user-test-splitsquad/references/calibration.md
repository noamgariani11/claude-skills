# Calibration — measuring the FALSE-NEGATIVE rate

Every run reports what it *found*. No run reports what it **walked straight past** — and that
number is the one that tells you whether to trust a clean report.

A run that finds 12 issues feels productive. If the panel also missed 8 planted ones, then "the
math checks out" means nothing, and a green report is actively misleading. Calibration is how this
skill earns the right to say "these numbers are right."

Run **every 5th run**, or on demand with `--calibrate`.

## ⚠ Overdue calibration is a blocking condition, not a note

If the ledger in `learnings.md` shows calibration overdue, **the run converts to `--calibrate`**
unless the user explicitly declines, and any report from an overdue panel carries this line **in
its verdict**:

> *Calibration overdue by N runs — this panel's false-negative rate is unmeasured, so "no money
> defects found" is not evidence of absence.*

A debt that is only ever *recorded* is not a protocol.

---

## Protocol

1. **Isolate in a worktree, not just a branch:**

   ```bash
   git worktree add ../splitsquad-calib HEAD && cd ../splitsquad-calib
   cp -al /home/drago/splitsqaud/node_modules node_modules   # HARDLINK copy, never a symlink
   ```

   **`cp -al`, never `ln -s`:** Next 16 / Turbopack rejects a symlinked `node_modules` with a fatal
   *"points out of the filesystem root"* panic. The hardlink copy is instant on the same filesystem.

   **Do not create a `.env` in the calibration tree.** No `POSTGRES_URL`, no `STRIPE_SECRET_KEY`,
   no `CRON_SECRET` — the absence is a *safety property*, not a convenience: a planted defect
   physically cannot reach a real database or a real payment rail.

   Confirm all plants compile (`npx tsc --noEmit` → 0 errors) before fielding anyone. A plant the
   compiler catches measures nothing about the panel.

2. **COMMIT the plants.** Uncommitted plants make `git status` list exactly the five planted files,
   and agents *will* run `git diff`. Commit them as one ordinary-looking commit so the tree reads
   clean, and keep the manifest **outside** the worktree.

3. **Plant 5 defects**, one per class, in surfaces the run will actually visit. Keep the manifest
   private:

   | Class | Example plant | Who *should* catch it |
   |---|---|---|
   | **Conservation** | In `resolveShares`, change the `equal`/`shares` branch from `p.weight ?? 1` to `p.weight \|\| 1` — an excluded participant is silently charged | Cent-counter (B) / bookkeeper |
   | **Rounding** | `Math.round(share * 100) / 100` on each share so the parts no longer sum to the total | Bookkeeper (accumulation test) |
   | **FX** | Change the EUR fallback rate from `0.92` to `0.82` | FX expert / traveler (C) |
   | **Settlement sign** | Flip the payment direction in `computeBalances` so a payment doubles the imbalance | Treasurer (D) |
   | **Honesty** | Make the balance card render "All settled up" whenever the *simplified plan* is empty, regardless of net balances | Adversarial / D |

   **Add a sixth plant when itemization is in scope:** make assigned receipt items drop their
   `assignedTo` so every item splits equally — a defect that is invisible on the totals and only
   shows in attribution.

   Plant them **where the personas will actually walk**. A defect on a surface nobody visits
   measures your route coverage, not your panel.

4. **Run the panel normally.** The personas must not know a calibration is running. If they know,
   they hunt, and you have measured hunting rather than testing.

5. **Score it — per lane, not just in aggregate:**

```
CALIBRATION RESULT
Planted: 5
Caught:  N  (which, by whom, at what severity)
Missed:  M  (which, and — the important part — WHY)
False-negative rate: M/5
Per-lane rate:  bookkeeper __/__ · FX __/__ · treasurer __/__ · adversarial __/__ · cent-counter __/__
Cross-catches:  (plants caught ONLY by a lane that didn't own them)
Repo-suite rate: __/5  (how many did `npm test` catch on its own?)
Severity accuracy: did the catcher rate it as high as it deserved?
```

**Report the per-lane rate, because the aggregate hides dead lanes.** A plant caught only by a
cross-catch is a **miss for its owner** — score it that way and say so.

**Also record what the repo's own suite caught.** 85 pure-logic tests over exactly this math ought
to catch the conservation and rounding plants. If it doesn't, that ratio *is* the test-shape
finding from SKILL.md Phase 2D — measured instead of argued, and far more persuasive.

6. **Throw the worktree away.** `git worktree remove ../splitsquad-calib --force`, delete the
   branch, then verify from the **real** tree: `git status` clean, plant files identical to `HEAD`,
   `git log --oneline -3` free of the plant commit.

---

## Reading the number

| FN rate | Verdict |
|---|---|
| 0/5 | The panel is sharp. A clean report from this panel means something. |
| 1/5 | Normal. Note which class leaked and strengthen that lane's checklist. |
| 2/5 | The panel has a blind spot. **Fix the skill before trusting another run.** |
| 3+/5 | The skill is theater. Findings are incidental, not systematic. Rebuild the weak lane. |

**The `WHY` on each miss is the actual product of this exercise**, not the ratio. Misses cluster,
and the cluster names the weakness:

- *Missed the conservation plant* → nobody re-derived a number by hand. The corpus never reached
  the experts, or the capture protocol was skipped in Phase 2A. **This makes the entire Money
  Integrity axis fake** — it is the most serious possible miss.
- *Missed the rounding plant* → the accumulation test wasn't run; someone checked one expense
  instead of twenty.
- *Missed the FX plant* → the expert read the code and trusted the table instead of checking a rate
  against a live source. This is the exact failure `domain-accuracy.md` exists to prevent.
- *Missed the sign plant* → the treasurer looked at the settle-up plan but never applied it on
  paper. Workflow 2 step 2 is not being executed.
- *Missed the honesty plant* → dimension 6 of `money-integrity.md` is being read but not used. The
  fix is to make the judge state each *claim of state* and the data backing it, explicitly, rather
  than render a holistic score.
- *Caught it but under-rated it* → the severity table isn't being applied. Invented money is
  `critical`, not "medium, minor math issue."

Record the result and the misses in `learnings.md`. **A rising FN rate across calibrations means
the skill is decaying** — usually because a reference file grew long enough that agents stopped
reading it to the end. Fix that by cutting, not by adding.
