#!/usr/bin/env python3
"""Turn a REJECTED candidate into a permanent precision case.

Why this exists. Triage rejects candidates every round -- the native select
that is correct, the framework half-step that is not drift, the `transition:
all` that is the CSS initial value and not an author's choice. Those rejections
are the most valuable output of a review and the only one that has been
evaporating: the reason lives in a ledger line, the threshold stays as it was,
and the next campaign rediscovers the same false positive and argues it again.

A false positive costs more than a miss. It survives triage, it gets debated,
and it teaches the user to distrust the number. So every rejection should end
up in `fixtures/clean.html`, where `probe-selftest.mjs --precision` asserts
forever that this exact construct produces zero candidates.

    # what still owes a fixture case
    fixture-case.py --from-findings .design/findings-dashboard.json

    # add one (and stamp it back onto the finding)
    fixture-case.py --why "a native select keeping its own chevron is correct" \\
                    --html '<p><label for="s">Status</label><select id="s">...</select></p>' \\
                    --record-in .design/findings-dashboard.json --finding-id P012

Then run, and it must be silent:
    node probe-selftest.mjs --precision
"""

import argparse
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
CLEAN = HERE / "fixtures" / "clean.html"
EXPECTED = HERE / "fixtures" / "EXPECTED.md"


def used_ids():
    """Every case id already claimed, in BOTH files.

    The two can disagree: a case documented in EXPECTED.md but not yet in the
    page still owns its number. Reading only the HTML is how two people editing
    the fixture in the same afternoon both pick C38.
    """
    ids = set()
    for path in (CLEAN, EXPECTED):
        if path.exists():
            ids |= {int(m) for m in re.findall(r"\bC(\d{2,3})\b", path.read_text())}
    return ids


def next_id():
    ids = used_ids()
    return f"C{max(ids) + 1 if ids else 1:02d}"


def add_case(why, snippet, cid=None):
    html = CLEAN.read_text()
    if cid:
        n = int(re.sub(r"\D", "", cid) or 0)
        if n in used_ids():
            sys.exit(f"{cid} is already used. Pick another, or omit --id and take {next_id()}.")
    cid = cid or next_id()
    if "</main>" not in html:
        sys.exit("clean.html has no </main> to insert before - fix the fixture, not this script.")
    wrapped = (
        f"\n  <!-- {cid}: {why} -->\n"
        f"  {snippet.strip()}\n"
    )
    html = html.replace("</main>", wrapped + "</main>", 1)
    CLEAN.write_text(html)

    doc = EXPECTED.read_text().rstrip("\n")
    doc += f"\n- **{cid}** {why}\n"
    EXPECTED.write_text(doc)
    return cid


def owing(path):
    with open(path) as fh:
        doc = json.load(fh)
    findings = doc if isinstance(doc, list) else doc.get("findings", [])
    return [f for f in findings
            if (f.get("status") or "").strip().lower() == "rejected"
            and not f.get("fixtureCase")]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-findings", metavar="JSON",
                    help="list rejected findings that do not yet have a fixture case")
    ap.add_argument("--why", help="one sentence: why this construct is CORRECT")
    ap.add_argument("--html", help="the smallest snippet that reproduces it")
    ap.add_argument("--id", help="case id (default: next free C-number)")
    ap.add_argument("--record-in", metavar="JSON", help="stamp the case id onto a finding")
    ap.add_argument("--finding-id", help="which finding to stamp")
    args = ap.parse_args()

    if args.from_findings:
        owed = owing(args.from_findings)
        if not owed:
            print("Every rejected finding already has a precision case. Nothing owed.")
            return 0
        print(f"{len(owed)} rejected finding(s) with no precision case yet.")
        print("A rejection without a fixture case is a false positive that will come back:\n")
        for f in owed:
            print(f"  {f.get('id','?'):<8} {f.get('pillar','?'):<12} {f.get('summary','')[:80]}")
        print("\nFor each, add the construct that was CORRECT:")
        print("  fixture-case.py --why '<why it is correct>' --html '<snippet>' \\")
        print(f"                  --record-in {args.from_findings} --finding-id <ID>")
        return 1

    if not (args.why and args.html):
        ap.error("--why and --html are both required (or use --from-findings)")

    cid = add_case(args.why, args.html, args.id)
    print(f"added {cid} to {CLEAN}")
    print(f"documented {cid} in {EXPECTED}")

    if args.record_in and args.finding_id:
        with open(args.record_in) as fh:
            doc = json.load(fh)
        findings = doc if isinstance(doc, list) else doc.get("findings", [])
        hit = next((f for f in findings if f.get("id") == args.finding_id), None)
        if hit is None:
            print(f"warning: no finding {args.finding_id} in {args.record_in}", file=sys.stderr)
        else:
            hit["fixtureCase"] = cid
            with open(args.record_in, "w") as fh:
                json.dump(doc, fh, indent=1)
            print(f"stamped {args.finding_id}.fixtureCase = {cid}")

    print("\nNow prove it is silent - this is the whole point:")
    print(f"  node {HERE / 'probe-selftest.mjs'} --precision")
    print("If it now reports a candidate, the THRESHOLD is wrong, not the fixture.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
