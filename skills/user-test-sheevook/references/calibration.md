# Calibration — measuring the FALSE-NEGATIVE rate

Every run reports what it *found*. No run reports what it **walked straight past** — and that
number is the one that tells you whether to trust a clean report.

A run that finds 12 bugs feels productive. If the panel also missed 8 planted ones, then "no
critical findings" means nothing, and a green report is actively misleading. Calibration is how
this skill earns the right to say "this looks good."

Run **every 5th run**, or on demand with `--calibrate`.

## ⚠ Overdue calibration is a blocking condition, not a note

Calibration has been skipped for **three consecutive due slots** (#15, #16, #17) while every
report faithfully recorded that it was "owed." A debt that is only ever *recorded* is not a
protocol. **It is now enforced in Phase 0.7:** if the ledger shows calibration overdue, the run
converts to `--calibrate` automatically unless the user explicitly declines, and any report from
an overdue panel must carry this line in its verdict:

> *Calibration overdue by N runs — this panel's false-negative rate is unmeasured, so "no critical
> findings" is not evidence of absence.*

The point of the number is to earn the right to say a clean report is clean. An unmeasured panel
cannot say that, and should not imply it.

---

## Protocol

1. **Isolate in a worktree, not just a branch** — the method that worked at run #14, reuse it
   verbatim:

   ```bash
   git worktree add ../sheevook-calib HEAD && cd ../sheevook-calib
   ln -s /home/drago/sheevook/research research          # gitignored, needed for Job 1
   cp -al /home/drago/sheevook/node_modules node_modules   # HARDLINK copy, not a symlink
   printf 'ANTHROPIC_API_KEY=\n' > .env.local             # NO DATABASE_URL — SQLite only
   ```

   **`cp -al`, never `ln -s`:** Next 16 Turbopack rejects a symlinked `node_modules` with a FATAL
   panic - *"Symlink [project]/node_modules is invalid, it points out of the filesystem root"*. The
   hardlink copy is instant on the same filesystem and Turbopack accepts it. (Broke at run #17.)

   **The missing `DATABASE_URL` is the safety property, not a convenience:** it forces SQLite, so
   a planted defect **physically cannot** reach live Neon Postgres or the **live Stripe keys**
   (`harness.md`). A branch alone does not give you that — the same `.env.local` follows it.
   Confirm all 5 plants compile (`pnpm exec tsc --noEmit` → 0) before fielding anyone; a plant
   that fails to build is caught by the compiler, not by the panel, and measures nothing.

2. **COMMIT the plants.** Run #14's own recorded methodology flaw: the plants were left
   **uncommitted**, so `git status` showed exactly the five planted files and **four of five
   agents used `git diff` / `log -S` to confirm "uncommitted."** They caught them on merits
   first — but a tree that advertises the answer measures the wrong thing. Commit them as one
   ordinary-looking commit so the tree reads clean, and keep the manifest outside the worktree.

3. **Plant 5 defects**, one per class below, in the surfaces the run will actually visit. Keep a
   private manifest (do NOT put it where the personas can read it):

   | Class | Example plant | Which persona *should* catch it |
   |---|---|---|
   | **Domain accuracy** | Change X's `hardLimit` from 280 → 300 in `platforms.ts` | X platform expert (Job 1) |
   | **Fake ad product** | Add a plausible-but-nonexistent campaign type to `formats.ts` (e.g. `meta_reach_plus`) | Media buyer / platform expert (Job 2) |
   | **Output quality** | Force one platform's generator to emit obvious slop ("In today's fast-paced world…") | Virality expert (Job 3) |
   | **Honesty** | Make a publish call return success without a live connection | Adversarial |
   | **Silent data loss** | Make discovery overwrite a user-filled brand field | Brand strategist (overwrite test) |

   Plant them **where the personas will actually walk**. A defect on a surface nobody visits
   measures nothing except your route coverage — which is a separate (also useful) finding.

   **Add a sixth plant when the veracity axis is in scope:** make one generator emit a
   *fabricated first-person anecdote or an invented statistic* (distinct from the slop plant —
   slop is beige, this one is specific, vivid, and false). Run #14 proved the panel scored exactly
   this **4.2/5** and shipped it. It is the class the rubric was blindest to, so it is the class
   most worth measuring now that `output-quality.md` dimension 6 exists.

4. **Run the panel normally.** The personas must not know a calibration is running. If they know,
   they hunt, and you've measured hunting rather than testing.

5. **Score it — per lane, not just in aggregate:**

```
CALIBRATION RESULT
Planted: 5
Caught:  N  (list which, by whom, and at what severity)
Missed:  M  (list which, and — this is the important part — WHY)
False-negative rate: M/5
Per-lane rate:  platform-expert __/__ · adversarial __/__ · virality __/__ · brand __/__
Cross-catches:  (plants caught ONLY by a lane that didn't own them)
Repo-suite rate: __/5  (how many did `pnpm test` catch on its own?)
Severity accuracy: did the catcher rate it at the severity it deserved?
```

**Report the per-lane rate, because the aggregate hides dead lanes.** At run #14 the adversarial
persona caught **4 of 5** — including plants it did not own — so the aggregate read a perfect 0/5
false negatives while the *owning* lanes were largely unresolved. A plant caught only by a
cross-catch means its owner lane missed it: score it as a miss for that lane and say so.

**Also record what the repo's own suite caught.** At #14 that was **1 of 5** — a credit to
`discovery.test.ts:730` and an indictment of the other four lanes. That ratio is the input to the
test-shape audit in `scoring-and-evidence.md`; a suite that catches 1 of 5 planted defects is the
same finding as `TEST-SHAPE-STRUCTURAL`, measured instead of argued.

6. **Throw the worktree away.** `git worktree remove ../sheevook-calib --force` and delete the
   branch. Then verify from the **real** tree that no plant survived: `git status` clean, plant
   files identical to `HEAD`, and `git log --oneline -3` free of the plant commit.

---

## Reading the number

| FN rate | Verdict |
|---|---|
| 0/5 | The panel is sharp. A clean report from this panel means something. |
| 1/5 | Normal. Note which class leaked and strengthen that persona's checklist. |
| 2/5 | The panel has a blind spot. **Fix the skill before trusting another run.** |
| 3+/5 | The skill is theater. Findings are incidental, not systematic. Stop and rebuild the weak lane. |

**The `WHY` on each miss is the actual product of this exercise**, not the ratio. Misses cluster,
and the cluster names the weakness:

- *Missed the domain-accuracy plant* → the expert reviewed the UI and skipped Job 1. The three-jobs
  rule in `platform-experts.md` is not being enforced. Enforce it: reject and re-run the agent.
- *Missed the fake ad product* → the expert accepted `formats.ts` as authoritative instead of
  auditing it against reality. This is the exact failure the skill exists to prevent.
- *Missed the slop plant* → the Virality expert is judging the UI, not the artifact. Check that the
  Phase 2A corpus actually reached them — **a missing corpus is the most likely cause**, and it
  makes the entire Output axis fake.
- *Missed the veracity plant* → dimension 6 of `output-quality.md` is not being applied. This is
  the class that scored 4.2/5 before the axis existed; if it leaks again, the axis is being read
  but not used, and the fix is to make the judge state each claim and its source explicitly rather
  than render a holistic score.
- *Missed the honesty plant* → the Adversarial persona is testing happy paths.
- *Caught it but under-rated the severity* → the severity table isn't being applied. A faked
  publish is `critical`, not "medium, minor UX issue."

Record the result and the misses in `learnings.md`. **A rising FN rate across calibrations means
the skill is decaying** — usually because a reference file grew long enough that agents stopped
reading it to the end. That is a real failure mode; fix it by cutting, not by adding.
