#!/usr/bin/env python3
"""Run every designer-dude validation layer and write machine evidence.

  python3 validate-rig.py --out .design/designer-dude-validation.json

The output is the `validationEvidence.evidence` artifact required for a literal
100. A partial run is never serialized as passing evidence.
"""

import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


def run(name, command, pattern=None):
    proc = subprocess.run(command, cwd=HERE.parent.parent, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = proc.stdout or ""
    ratio = None
    if pattern:
        match = re.search(pattern, output)
        if match:
            ratio = f"{match.group(1)}/{match.group(2)}"
    passed = proc.returncode == 0 and (not pattern or ratio is not None)
    return {"name": name, "status": "pass" if passed else "fail",
            "exitCode": proc.returncode, "ratio": ratio,
            "output": output[-12000:]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    node = str(HERE / "probe-selftest.mjs")
    checks = [
        run("recall", ["node", node], r"probe-selftest:\s*(\d+)/(\d+) planted"),
        run("precision", ["node", node, "--precision"], r"--precision:\s*(\d+)/(\d+)"),
        run("mutations", ["node", node, "--mutations"], r"--mutations:\s*(\d+)/(\d+)"),
        run("pipeline", ["node", node, "--pipeline"], r"--pipeline:\s*(\d+)/(\d+)"),
        run("runner", ["node", node, "--runner"]),
        run("score", ["python3", str(HERE / "score.py"), "--selftest"]),
        run("evidence", ["python3", str(HERE / "evidence-gates.py"), "--selftest"]),
        run("calibration", ["python3", str(HERE / "calibration-snapshot.py"), "--selftest"]),
        run("resolver", ["node", str(HERE / "cross-engine.mjs"), "--selftest-resolver"]),
    ]
    # Exit zero alone is not enough for the two prose-output integrations.
    for check in checks:
        if check["name"] == "runner" and "runner check ok" not in check["output"]:
            check["status"] = "fail"
        if check["name"] == "score" and "selftest ok" not in check["output"]:
            check["status"] = "fail"
        if check["name"] == "evidence" and "evidence-gates selftest ok" not in check["output"]:
            check["status"] = "fail"
        if check["name"] == "calibration" and "calibration-snapshot selftest ok" not in check["output"]:
            check["status"] = "fail"
        if check["name"] == "resolver" and "cross-engine resolver selftest ok" not in check["output"]:
            check["status"] = "fail"
    status = "pass" if all(c["status"] == "pass" for c in checks) else "fail"
    ratios = {c["name"]: c["ratio"] for c in checks if c["ratio"]}
    doc = {"schema": "designer-dude-validation/v1", "generatedAt":
           datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "status": status, "ratios": ratios, "checks": checks}
    path = pathlib.Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"designer-dude validation: {status} -> {path}")
    for check in checks:
        suffix = f" {check['ratio']}" if check["ratio"] else ""
        print(f"  {check['name']:<10} {check['status']}{suffix}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
