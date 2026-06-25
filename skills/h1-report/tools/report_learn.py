#!/usr/bin/env python3
"""The learning spine for /h1-report: guarantees that every run records and learns.

The skill's Phase 6 promise — "every run, something is learned" — only holds if the
logging is mechanical instead of a thing the model might skip. This tool makes it
mechanical:

  * `log`     appends one structured row to memory/report-log.jsonl (the per-report history)
              and prints the Phase-6 learning checklist so a lesson is never forgotten.
  * `outcome` updates a prior row when a triage verdict lands (resolved / duplicate / n-a /
              informative / severity-changed / bounty) — the strongest learning signal.
  * `stats`   summarises the history for Phase R recall (counts by outcome, most-cited
              lessons, recent rows) so each run opens already knowing what worked.

It never edits LESSONS.md for you (lessons are a judgement call), but it refuses to let a
run end silently: `log` always writes, and always prints the "now update LESSONS.md" gate.

  report_learn.py log --program acme --mode A --class idor \
      --title "IDOR in GET /api/v2/invoices/{id} ..." --severity "High CVSS:3.1/.../ (7.1)" \
      --em-dashes 3 --validator pass --outcome pending --lessons L-002,L-003
  report_learn.py outcome --title "IDOR in GET" --set resolved --bounty 1500 \
      --note "triager liked the per-tenant repro; rewarded fast"
  report_learn.py stats
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"
LOG = MEM / "report-log.jsonl"
LESSONS = MEM / "LESSONS.md"

OUTCOMES = {"pending", "triaged", "resolved", "duplicate", "n-a", "informative",
            "needs-info", "severity-changed", "spam", "self-closed"}
# Reputation deltas (HackerOne, 2024-2026) — surfaced so Phase 6 reasons about the stats cost.
REP_DELTA = {"triaged": +7, "resolved": +7, "n-a": -5, "spam": -10, "informative": 0,
             "duplicate": 0, "self-closed": 0}


def now_iso() -> str:
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_rows() -> list[dict]:
    if not LOG.is_file():
        return []
    rows = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def write_rows(rows: list[dict]) -> None:
    LOG.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def cmd_log(a: argparse.Namespace) -> int:
    row = {
        "ts": now_iso(),
        "mode": a.mode,
        "program": a.program,
        "class": a.cls or "",
        "title": a.title or "",
        "severity": a.severity or "",
        "cvss": a.cvss or "",
        "em_dashes_removed": a.em_dashes,
        "validator": a.validator,
        "outcome": a.outcome,
        "lessons_touched": [s.strip() for s in (a.lessons or "").split(",") if s.strip()],
        "note": a.note or "",
    }
    if a.outcome not in OUTCOMES:
        print(f"warning: unusual outcome '{a.outcome}' (known: {sorted(OUTCOMES)})", file=sys.stderr)
    MEM.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"logged → {LOG}")
    print(json.dumps(row, indent=2, ensure_ascii=False))
    print_phase6_gate(row)
    return 0


def cmd_outcome(a: argparse.Namespace) -> int:
    rows = read_rows()
    if not rows:
        print("no rows to update", file=sys.stderr)
        return 1
    idx = None
    if a.ts:
        idx = next((i for i, r in enumerate(rows) if r.get("ts") == a.ts), None)
    elif a.title:
        matches = [i for i, r in enumerate(rows) if a.title.lower() in r.get("title", "").lower()]
        idx = matches[-1] if matches else None  # most recent match
    if idx is None:
        print("no matching row (use --ts or a --title substring)", file=sys.stderr)
        return 1
    if a.set not in OUTCOMES:
        print(f"warning: unusual outcome '{a.set}'", file=sys.stderr)
    rows[idx]["outcome"] = a.set
    if a.bounty is not None:
        rows[idx]["bounty"] = a.bounty
    if a.note:
        rows[idx]["outcome_note"] = a.note
    rows[idx]["outcome_ts"] = now_iso()
    write_rows(rows)
    delta = REP_DELTA.get(a.set)
    print(f"updated row [{rows[idx]['ts']}] → outcome={a.set}"
          + (f", bounty=${a.bounty}" if a.bounty is not None else "")
          + (f"  (reputation {'+' if delta and delta > 0 else ''}{delta})" if delta is not None else ""))
    print("\nThis verdict is a learning signal. Phase 6 is NOT done until you have:")
    print("  • extracted the lesson this outcome teaches (what would you write differently next time?)")
    print("  • added/sharpened it in LESSONS.md with this report as evidence")
    print("  • written a durable auto-memory if it's a program/triager fact for next session")
    if a.set == "n-a":
        print("  NOTE: a program-initiated N/A is -5 rep. If a future draft is this weak, self-close it (0).")
    return 0


def cmd_stats(a: argparse.Namespace) -> int:
    rows = read_rows()
    if not rows:
        print("report-log.jsonl is empty — no history yet. (First report? That's fine.)")
        print_lessons_index()
        return 0
    by_outcome: dict[str, int] = {}
    by_program: dict[str, int] = {}
    by_class: dict[str, int] = {}
    lesson_cites: dict[str, int] = {}
    bounty_total = 0
    for r in rows:
        by_outcome[r.get("outcome", "?")] = by_outcome.get(r.get("outcome", "?"), 0) + 1
        by_program[r.get("program", "?")] = by_program.get(r.get("program", "?"), 0) + 1
        if r.get("class"):
            by_class[r["class"]] = by_class.get(r["class"], 0) + 1
        for L in r.get("lessons_touched", []):
            lesson_cites[L] = lesson_cites.get(L, 0) + 1
        if isinstance(r.get("bounty"), (int, float)):
            bounty_total += r["bounty"]

    print(f"== report-log: {len(rows)} report(s) ==")
    print("  by outcome: " + ", ".join(f"{k}={v}" for k, v in sorted(by_outcome.items(), key=lambda x: -x[1])))
    print("  by program: " + ", ".join(f"{k}={v}" for k, v in sorted(by_program.items(), key=lambda x: -x[1])))
    if by_class:
        print("  by class:   " + ", ".join(f"{k}={v}" for k, v in sorted(by_class.items(), key=lambda x: -x[1])))
    if bounty_total:
        print(f"  bounties:   ${bounty_total} total")
    resolved = by_outcome.get("resolved", 0) + by_outcome.get("triaged", 0)
    closed = sum(by_outcome.get(k, 0) for k in ("n-a", "informative", "duplicate", "spam"))
    if resolved or closed:
        print(f"  signal:     {resolved} accepted vs {closed} closed-noisy")
    if lesson_cites:
        top = sorted(lesson_cites.items(), key=lambda x: -x[1])[:6]
        print("  most-applied lessons: " + ", ".join(f"{k}×{v}" for k, v in top))
    print("\n  recent:")
    for r in rows[-5:]:
        print(f"   {r.get('ts','?')[:10]} [{r.get('mode','?')}] {r.get('program','?')}: "
              f"{(r.get('title') or r.get('class') or '')[:54]} → {r.get('outcome','?')}")
    print()
    print_lessons_index()
    return 0


def print_lessons_index() -> None:
    """Surface LESSONS.md headings so Phase R recall is mechanical, not from memory."""
    if not LESSONS.is_file():
        return
    heads = re.findall(r"^###\s+(L-\d+.*?)$", LESSONS.read_text(encoding="utf-8"), re.M)
    if heads:
        print(f"== LESSONS.md ({len(heads)} active) — apply top-ranked first ==")
        for h in heads:
            print("  • " + h.strip())


def print_phase6_gate(row: dict) -> None:
    print("\n── Phase 6 gate: every run learns something ───────────────────────────")
    print("  [ ] LESSONS.md updated — add a NEW lesson, OR sharpen an existing one")
    print("      (bump its supporting count / re-rank / add a counter-example). Never a no-op.")
    print("  [ ] If the outcome is known later, run:  report_learn.py outcome --title \"...\" --set <verdict>")
    print("  [ ] Durable program/triager fact? → write it to the user's auto-memory + MEMORY.md")
    if not row.get("lessons_touched"):
        print("  ⚠ no lessons cited on this row — confirm you really applied none, or add --lessons next time")
    print("───────────────────────────────────────────────────────────────────────")


def main() -> int:
    ap = argparse.ArgumentParser(description="Learning spine for /h1-report (log / outcome / stats).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    lg = sub.add_parser("log", help="append a report row + print the Phase-6 learning gate")
    lg.add_argument("--program", required=True)
    lg.add_argument("--mode", default="A", choices=["A", "B", "C"])
    lg.add_argument("--class", dest="cls", default="")
    lg.add_argument("--title", default="")
    lg.add_argument("--severity", default="")
    lg.add_argument("--cvss", default="", help="full CVSS vector string")
    lg.add_argument("--em-dashes", type=int, default=0, dest="em_dashes")
    lg.add_argument("--validator", default="pass", choices=["pass", "warn", "fail"])
    lg.add_argument("--outcome", default="pending")
    lg.add_argument("--lessons", default="", help="comma list, e.g. L-002,L-003")
    lg.add_argument("--note", default="")
    lg.set_defaults(func=cmd_log)

    oc = sub.add_parser("outcome", help="update a prior row when a verdict lands")
    oc.add_argument("--ts", help="exact ts of the row")
    oc.add_argument("--title", help="substring of the row title (most recent match)")
    oc.add_argument("--set", required=True, help="resolved|duplicate|n-a|informative|severity-changed|...")
    oc.add_argument("--bounty", type=float)
    oc.add_argument("--note", default="")
    oc.set_defaults(func=cmd_outcome)

    st = sub.add_parser("stats", help="summarise history + list lessons (Phase R recall)")
    st.set_defaults(func=cmd_stats)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
