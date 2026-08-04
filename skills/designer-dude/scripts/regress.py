#!/usr/bin/env python3
"""
regress.py - did the fixes make anything worse?

Mode D ships changes. Every change is a chance to break something that was
fine, and design regressions are unusually easy to miss: they land on a
viewport you did not screenshot, in the theme you do not develop in, or on
the surface you fixed second.

This diffs two probe payloads of the SAME surface and reports every measured
metric that moved the wrong way. It is deliberately mechanical. It does not
know what you intended; it knows what the page measured before and after.

    python3 regress.py BEFORE.json AFTER.json
    python3 regress.py --before .design/baseline/probe-*.json \
                       --after  .design/probe-*.json
    python3 regress.py ... --json .design/regressions.json
    python3 regress.py --selftest

Exit codes:  0 clean (or advisories only) · 1 a real regression · 2 bad input.

Reading the output
------------------
CRITICAL   an accessibility or correctness metric went backwards. Revert.
MAJOR      something a designer would notice. Explain it or revert it.
MINOR      drift worth a line in the ledger.
ADVISORY   moved, but within noise or plausibly intended. Look, do not panic.

Improvements are printed too, because a diff that only shows bad news is a
diff nobody trusts.
"""

import argparse
import glob as globmod
import json
import os
import sys

CRIT, MAJOR, MINOR, ADVISORY = "critical", "major", "minor", "advisory"
SEV_ORDER = {CRIT: 0, MAJOR: 1, MINOR: 2, ADVISORY: 3}
FAIL_ON = (CRIT, MAJOR)

# --------------------------------------------------------------------------
# The metric table.
#
# path            dotted path inside one run object
# dir             "down" = lower is better, "up" = higher is better
# sev             severity when it moves the wrong way
# tol             absolute change that is treated as noise
# gate            optional (threshold, severity) - crossing it upgrades severity
# --------------------------------------------------------------------------
METRICS = [
    # --- accessibility and contrast: these are never taste calls -----------
    ("color.textContrast.failures",            "down", CRIT,  0, None),
    ("color.nonTextContrast.fieldBorderFailures", "down", CRIT, 0, None),
    ("a11y.imagesMissingAlt.count",            "down", CRIT,  0, None),
    ("a11y.fieldsMissingLabel.count",          "down", CRIT,  0, None),
    ("a11y.fieldsPlaceholderOnly.count",       "down", CRIT,  0, None),
    ("a11y.controlsMissingAccessibleName.count", "down", CRIT, 0, None),
    ("a11y.ariaHiddenContainingFocusable",     "down", CRIT,  0, None),
    ("a11y.duplicateIds.count",                "down", MAJOR, 0, None),
    ("a11y.positiveTabindex",                  "down", MAJOR, 0, None),
    ("interaction.focusRing.invisible",        "down", CRIT,  0, None),
    ("interaction.belowWcagTarget24.count",    "down", CRIT,  0, None),
    ("interaction.belowFittsTarget44.count",   "down", MAJOR, 2, None),
    ("interaction.hoverOnlyContentCount",      "down", CRIT,  0, None),
    ("layout.horizontalOverflow",              "down", CRIT,  0, None),
    ("layout.overflowingElementCount",         "down", MAJOR, 0, None),

    # --- designed states: coverage falling means a fix deleted a state -----
    ("states.hoverCoverage",                   "up",   MAJOR, 5, None),
    ("states.focusVisibleCoverage",            "up",   CRIT,  2, None),
    ("states.withActiveRule",                  "up",   MINOR, 1, None),
    ("states.withDisabledRule",                "up",   MINOR, 1, None),
    ("states.reducedMotionMediaRules",         "up",   MAJOR, 0, None),

    # --- interaction affordances ------------------------------------------
    ("interaction.missingPointerCursor.count", "down", MAJOR, 0, None),
    ("interaction.clickableWithoutTransition", "down", MINOR, 3, None),

    # --- colour and system scales -----------------------------------------
    ("color.accentPixelShare",                 "down", MINOR, 1.0, (10, MAJOR)),
    ("color.pureBlackOrWhiteText",             "down", MINOR, 0, None),
    ("system.radius.distinct",                 "down", MINOR, 0, (5, MAJOR)),
    ("system.shadow.distinct",                 "down", MINOR, 0, (5, MAJOR)),
    ("system.zIndex.distinct",                 "down", MINOR, 0, (7, MAJOR)),

    # --- typography --------------------------------------------------------
    ("typography.distinctSizes",               "down", MINOR, 1, (14, MAJOR)),
    ("typography.distinctFamilies",            "down", MINOR, 0, (4, MAJOR)),
    ("typography.offenders.leadingOutOfBandCount", "down", MINOR, 1, None),
    ("typography.offenders.measureOutOfBandCount", "down", MINOR, 1, None),

    # --- motion -------------------------------------------------------------
    ("motion.infiniteAnimations.count",        "down", MINOR, 0, None),
    ("motion.transitionsOver600msCount",       "down", MINOR, 1, None),

    # --- slop tells ---------------------------------------------------------
    ("slop.purpleOrIndigoGradients",           "down", MAJOR, 0, None),
    ("slop.largeRadialGradients",              "down", MAJOR, 0, None),
    ("slop.threeUpFeatureGrids",               "down", MAJOR, 0, None),
    ("slop.iconsInColouredCircles",            "down", MINOR, 1, None),
    ("slop.gradientClippedText",               "down", MINOR, 0, None),
    ("slop.colouredLeftBorderCards",           "down", MINOR, 1, None),
    ("slop.backdropBlurElements",              "down", MINOR, 3, None),
    ("slop.centredShare",                      "down", MINOR, 5, (30, MAJOR)),
    ("slop.decorativeStepNumbers",             "down", MAJOR, 0, None),
    ("slop.emDashesPer1kChars",                "down", MINOR, 0.5, None),
    ("slop.llmSentenceFrames",                 "down", MAJOR, 0, None),

    # A hover rule that paints nothing, and a fill with nowhere to sit.
    # Tracked separately from hoverCoverage because coverage RISES when
    # somebody adds the rule that turns out to be inert.
    ("states.inertHoverFills",                 "down", MAJOR, 0, None),
    ("states.hueOnlyHoverFills",               "down", MINOR, 0, None),
    ("states.inertHoverBorders",               "down", MINOR, 0, None),
    ("states.hoverFillsCoveringOwnRule",       "down", MINOR, 0, None),
    ("states.hoverFillsWithoutPadding",        "down", MINOR, 0, None),

    # --- browser chrome: the parts the OS draws, which screenshots miss ----
    ("chrome.darkSurfaceWithoutColorScheme",   "down", MAJOR, 0, None),
    ("chrome.hiddenScrollbars",                "down", MAJOR, 0, None),
    ("chrome.unstyledStrippedSelects",         "down", MAJOR, 0, None),
    ("chrome.nativeTitleTooltips",             "down", MAJOR, 0, None),
]

# Page-level metrics live beside `runs`, not inside one.
PAGE_METRICS = [
    ("consoleErrors",                            "down", MAJOR, 0, None),
    ("failedRequests",                           "down", MAJOR, 0, None),
    ("performance.largestContentfulPaint",       "down", MINOR, 400, (2500, MAJOR)),
    ("performance.cumulativeLayoutShift",        "down", MINOR, 0.02, (0.1, MAJOR)),
    ("performance.firstContentfulPaint",         "down", MINOR, 300, None),
]

# Auto-discovery: any numeric leaf whose key names a defect counts, even if
# nobody added it to the table above. This is what keeps the guard honest as
# probe.js grows new checks.
BAD_KEY_HINTS = ("fail", "missing", "invisible", "violat", "overflow",
                 "duplicate", "outofband", "invalid", "broken", "orphan",
                 "straightquote", "tiny", "unlabelled", "unlabeled")
DISCOVERY_IGNORE = ("truncated", "checked", "tested", "scanned", "total")

# Metrics that legitimately move run to run and must never fail a build.
VOLATILE = ("elementsScanned", "documentHeight", "textDensityChars",
            "fontsLoaded", "scrollWidth", "clientWidth", "probedAt")


def get(obj, path, default=None):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def as_number(v):
    """Booleans count as 0/1, lists count as their length, None is absent."""
    if v is None:
        return None
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, list):
        return float(len(v))
    if isinstance(v, dict) and "count" in v and isinstance(v["count"], (int, float)):
        return float(v["count"])
    return None


def fmt(n):
    if n is None:
        return "-"
    return str(int(n)) if float(n).is_integer() else f"{n:.3g}"


def discover(before_run, after_run, known):
    """Walk both run objects and yield (path, dir, sev, tol, gate) for numeric
    leaves that name a defect and are not already in the table."""
    found = {}

    def walk(node, prefix):
        if isinstance(node, dict):
            for k, v in node.items():
                key = f"{prefix}.{k}" if prefix else k
                low = k.lower()
                if any(x in low for x in DISCOVERY_IGNORE):
                    continue
                if isinstance(v, (dict,)):
                    walk(v, key)
                    if "count" in v and any(h in low for h in BAD_KEY_HINTS):
                        found[f"{key}.count"] = True
                elif any(h in low for h in BAD_KEY_HINTS) and as_number(v) is not None:
                    found[key] = True

    walk(before_run, "")
    walk(after_run, "")
    for path in sorted(found):
        if path in known or any(v in path for v in VOLATILE):
            continue
        yield (path, "down", MINOR, 0, None)


def compare(before, after, label):
    """Returns (regressions, improvements)."""
    regressions, improvements = [], []
    known = {m[0] for m in METRICS}

    def check(scope, path, direction, sev, tol, gate, b_obj, a_obj):
        b = as_number(get(b_obj, path))
        a = as_number(get(a_obj, path))
        if b is None or a is None:
            return
        delta = a - b
        if delta == 0:
            return
        worse = delta > 0 if direction == "down" else delta < 0
        row = {"surface": label, "scope": scope, "metric": path,
               "before": b, "after": a, "delta": delta}
        if not worse:
            improvements.append(row)
            return
        level = sev
        if abs(delta) <= tol:
            level = ADVISORY
        if gate:
            threshold, upgraded = gate
            crossed = (a > threshold >= b) if direction == "down" else (a < threshold <= b)
            if crossed and SEV_ORDER[upgraded] < SEV_ORDER[level]:
                level = upgraded
        row["severity"] = level
        regressions.append(row)

    for path, d, s, tol, gate in PAGE_METRICS:
        check("page", path, d, s, tol, gate, before, after)

    b_runs = {r.get("tag"): r for r in before.get("runs", [])}
    a_runs = {r.get("tag"): r for r in after.get("runs", [])}
    shared = [t for t in a_runs if t in b_runs]
    if not shared:
        print(f"  ! {label}: no matching run tags between the two probes. "
              f"Re-probe with the same viewport config before trusting a diff.",
              file=sys.stderr)

    for tag in sorted(shared):
        b_run, a_run = b_runs[tag], a_runs[tag]
        table = list(METRICS) + list(discover(b_run, a_run, known))
        for path, d, s, tol, gate in table:
            check(tag, path, d, s, tol, gate, b_run, a_run)

    only_before = sorted(set(b_runs) - set(a_runs))
    if only_before:
        regressions.append({
            "surface": label, "scope": "coverage", "metric": "runs.missing",
            "before": len(b_runs), "after": len(a_runs), "delta": -len(only_before),
            "severity": MINOR,
            "note": "the after-probe skipped " + ", ".join(only_before),
        })
    return regressions, improvements


def load(path):
    with open(path) as fh:
        payload = json.load(fh)
    if "runs" not in payload:
        raise ValueError(f"{path} is not a probe payload (no `runs` key)")
    return payload


def expand(paths):
    out = []
    for p in paths:
        hits = sorted(globmod.glob(p)) if any(c in p for c in "*?[") else [p]
        if not hits:
            print(f"no such probe payload: {p}", file=sys.stderr)
            sys.exit(2)
        out.extend(hits)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pair", nargs="*", help="BEFORE.json AFTER.json")
    ap.add_argument("--before", nargs="+", default=[], help="prior probe payload(s); globs ok")
    ap.add_argument("--after", nargs="+", default=[], help="current probe payload(s); globs ok")
    ap.add_argument("--json", help="write the machine-readable diff here")
    ap.add_argument("--quiet-improvements", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.pair:
        if len(args.pair) != 2 or args.before or args.after:
            print("Positional form takes exactly BEFORE.json AFTER.json.", file=sys.stderr)
            sys.exit(2)
        befores, afters = [args.pair[0]], [args.pair[1]]
    else:
        befores, afters = expand(args.before), expand(args.after)
    if not befores or not afters:
        print("Nothing to compare. Pass BEFORE.json AFTER.json, or --before/--after.",
              file=sys.stderr)
        sys.exit(2)

    b_by_label, a_by_label = {}, {}
    for p in befores:
        pl = load(p)
        b_by_label[pl.get("label") or os.path.basename(p)] = pl
    for p in afters:
        pl = load(p)
        a_by_label[pl.get("label") or os.path.basename(p)] = pl

    # A positional pair is one surface by definition, even if the labels drift.
    if args.pair and len(b_by_label) == 1 and len(a_by_label) == 1:
        only = list(a_by_label)[0]
        b_by_label = {only: list(b_by_label.values())[0]}

    all_reg, all_imp, unmatched = [], [], []
    for label, after in sorted(a_by_label.items()):
        before = b_by_label.get(label)
        if before is None:
            unmatched.append(label)
            continue
        reg, imp = compare(before, after, label)
        all_reg.extend(reg)
        all_imp.extend(imp)

    all_reg.sort(key=lambda r: (SEV_ORDER[r["severity"]], r["surface"], r["metric"]))

    print("=" * 74)
    print("REGRESSION CHECK")
    print("=" * 74)
    print(f"surfaces compared: {len(a_by_label) - len(unmatched)}"
          f" · regressions: {sum(1 for r in all_reg if r['severity'] in FAIL_ON)}"
          f" blocking, {sum(1 for r in all_reg if r['severity'] not in FAIL_ON)} advisory"
          f" · improvements: {len(all_imp)}")
    if unmatched:
        print(f"no prior probe for: {', '.join(unmatched)} (nothing to compare)")

    if all_reg:
        print()
        print(f"{'sev':<9} {'surface':<14} {'where':<16} {'metric':<44} {'before':>8} {'after':>8}")
        print("-" * 104)
        for r in all_reg:
            print(f"{r['severity']:<9} {r['surface'][:14]:<14} {r['scope'][:16]:<16} "
                  f"{r['metric'][:44]:<44} {fmt(r['before']):>8} {fmt(r['after']):>8}"
                  + (f"\n{'':>9} {r['note']}" if r.get("note") else ""))
    else:
        print("\nNothing measured moved the wrong way.")

    if all_imp and not args.quiet_improvements:
        print(f"\nimproved ({len(all_imp)}):")
        seen = set()
        for r in all_imp:
            key = (r["surface"], r["metric"])
            if key in seen:
                continue
            seen.add(key)
            print(f"  {r['surface']:<14} {r['metric']:<44} "
                  f"{fmt(r['before'])} -> {fmt(r['after'])}")

    blocking = [r for r in all_reg if r["severity"] in FAIL_ON]
    if blocking:
        print("\n" + "=" * 74)
        print(f"{len(blocking)} blocking regression(s). Mode D's rule: any revert is a "
              "stop condition.")
        print("Fix or revert the commit that caused it before continuing the round, and")
        print("record it in the ledger. Do not carry a regression into a re-score.")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"regressions": all_reg, "improvements": all_imp,
                       "unmatched": unmatched}, fh, indent=1)
        print(f"\nwritten: {args.json}")

    sys.exit(1 if blocking else 0)


def selftest():
    def run(tag, extra_before=None, extra_after=None):
        base_run = {"tag": tag, "color": {"textContrast": {"failures": 0},
                                          "accentPixelShare": 6},
                    "a11y": {"imagesMissingAlt": {"count": 0}},
                    "states": {"focusVisibleCoverage": 80, "hoverCoverage": 70},
                    "layout": {"horizontalOverflow": False},
                    "system": {"radius": {"distinct": 3}}}
        b = json.loads(json.dumps(base_run))
        a = json.loads(json.dumps(base_run))
        if extra_before:
            b.update(extra_before)
        if extra_after:
            a.update(extra_after)
        return b, a

    failures = []

    def expect(name, cond):
        if not cond:
            failures.append(name)

    # 1. identical payloads produce nothing
    b, a = run("1440x900")
    reg, imp = compare({"runs": [b]}, {"runs": [a]}, "x")
    expect("identical payloads are clean", reg == [] and imp == [])

    # 2. a new contrast failure is critical
    b, a = run("1440x900", None, {"color": {"textContrast": {"failures": 3},
                                            "accentPixelShare": 6}})
    reg, _ = compare({"runs": [b]}, {"runs": [a]}, "x")
    expect("new contrast failure is critical",
           any(r["metric"] == "color.textContrast.failures" and r["severity"] == CRIT
               for r in reg))

    # 3. fixing one is an improvement, not a regression
    reg, imp = compare({"runs": [a]}, {"runs": [b]}, "x")
    expect("fixed contrast is an improvement",
           not reg and any(r["metric"] == "color.textContrast.failures" for r in imp))

    # 4. focus coverage dropping is critical; a 1-point wobble is advisory
    b, a = run("1440x900", None, {"states": {"focusVisibleCoverage": 40, "hoverCoverage": 70}})
    reg, _ = compare({"runs": [b]}, {"runs": [a]}, "x")
    expect("focus coverage drop is critical",
           any(r["metric"] == "states.focusVisibleCoverage" and r["severity"] == CRIT
               for r in reg))
    b, a = run("1440x900", None, {"states": {"focusVisibleCoverage": 79, "hoverCoverage": 70}})
    reg, _ = compare({"runs": [b]}, {"runs": [a]}, "x")
    expect("1-point focus wobble is advisory",
           any(r["metric"] == "states.focusVisibleCoverage" and r["severity"] == ADVISORY
               for r in reg))

    # 5. a gate upgrades severity when the threshold is crossed
    b, a = run("1440x900", None, {"color": {"textContrast": {"failures": 0},
                                            "accentPixelShare": 14}})
    reg, _ = compare({"runs": [b]}, {"runs": [a]}, "x")
    expect("accent crossing 10% upgrades to major",
           any(r["metric"] == "color.accentPixelShare" and r["severity"] == MAJOR
               for r in reg))
    b, a = run("1440x900", None, {"color": {"textContrast": {"failures": 0},
                                            "accentPixelShare": 8}})
    reg, _ = compare({"runs": [b]}, {"runs": [a]}, "x")
    expect("accent moving inside the budget stays minor or advisory",
           all(r["severity"] in (MINOR, ADVISORY) for r in reg))

    # 6. booleans compare as 0/1
    b, a = run("1440x900", None, {"layout": {"horizontalOverflow": True}})
    reg, _ = compare({"runs": [b]}, {"runs": [a]}, "x")
    expect("horizontal overflow appearing is critical",
           any(r["metric"] == "layout.horizontalOverflow" and r["severity"] == CRIT
               for r in reg))

    # 7. page-level console errors are lists
    reg, _ = compare({"runs": [b], "consoleErrors": []},
                     {"runs": [b], "consoleErrors": ["boom", "bang"]}, "x")
    expect("new console errors are major",
           any(r["metric"] == "consoleErrors" and r["severity"] == MAJOR for r in reg))

    # 8. unmatched run tags do not crash and do not invent regressions
    b, a = run("1440x900")
    b2, _ = run("390x844")
    reg, _ = compare({"runs": [b, b2]}, {"runs": [a]}, "x")
    expect("a skipped viewport is reported once as minor",
           sum(1 for r in reg if r["metric"] == "runs.missing") == 1)

    # 9. auto-discovery catches a metric nobody added to the table
    b, a = run("1440x900", {"newthing": {"widgetsMissingLabel": 0}},
               {"newthing": {"widgetsMissingLabel": 4}})
    reg, _ = compare({"runs": [b]}, {"runs": [a]}, "x")
    expect("auto-discovery catches an untabled defect metric",
           any(r["metric"].endswith("widgetsMissingLabel") for r in reg))

    # 10. volatile metrics never fire
    b, a = run("1440x900", {"meta": {"elementsScanned": 100}},
               {"meta": {"elementsScanned": 4000}})
    reg, _ = compare({"runs": [b]}, {"runs": [a]}, "x")
    expect("volatile metrics are ignored",
           not any("elementsScanned" in r["metric"] for r in reg))

    for name in failures:
        print(f"FAIL  {name}")
    total = 10
    print(f"{total - len(failures)}/{total} regression-guard selftests passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
