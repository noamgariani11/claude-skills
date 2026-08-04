#!/usr/bin/env python3
"""Deterministic eval statistics for aiml-dude.

Every number this skill uses to gate a ship decision comes from here:
bootstrap confidence intervals, expected calibration error, judge
agreement (Cohen's kappa), and the power analysis that picks corpus size.

Exists for three reasons:

1. The skill's whole premise is "evals beat vibes". A confidence interval
   computed in a model's head, or by throwaway code written fresh each
   session, is a vibe wearing a lab coat.
2. numpy and sklearn are NOT installed in this environment. The reference
   snippets in references/evaluation-core.md used to assume both. This is
   stdlib-only and actually runs.
3. Bootstrap is randomized. Randomized ship gates that give a different
   answer on rerun are not gates. Every resample here is seeded, so the
   same inputs always produce the same verdict, and the seed is printed
   with the result so anyone can reproduce it.

Usage:
  evalstats.py bootstrap --scores new.json --baseline old.json --paired
  evalstats.py bootstrap --scores 3,4,2,4,3,4
  evalstats.py ece --data session.json
  evalstats.py kappa --human h.json --judge j.json
  evalstats.py power --baseline-rate 0.75 --mde 0.05
  evalstats.py --selftest

Input formats. Anywhere a numeric list is expected you may pass:
  - an inline comma list          --scores 3,4,2,4
  - a path to a JSON array        --scores scores.json
  - a path to a JSON array of objects, with --field
                                  --scores session.json --field correctness

All output is human-readable by default; add --json for a machine-readable
object suitable for writing into an AIPATH.md Change Log entry.
"""

import argparse
import json
import math
import os
import random
import sys

DEFAULT_SEED = 20260720
DEFAULT_B = 1000


# ---------------------------------------------------------------- loading


def load_numbers(spec, field=None):
    """Accept an inline comma list, a JSON array file, or a JSON records file."""
    if spec is None:
        return None
    if os.path.exists(spec):
        with open(spec) as fh:
            data = json.load(fh)
        # Allow a wrapper object: {"scores": [...]} or {"results": [...]}
        if isinstance(data, dict):
            for key in ("scores", "results", "items", "prompts", "data"):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                raise SystemExit(
                    f"{spec}: JSON object has no scores/results/items/prompts/data array"
                )
        if not isinstance(data, list):
            raise SystemExit(f"{spec}: expected a JSON array")
        if data and isinstance(data[0], dict):
            if field is None:
                keys = sorted(data[0].keys())
                raise SystemExit(
                    f"{spec}: array of objects needs --field. Available: {', '.join(keys)}"
                )
            try:
                return [float(row[field]) for row in data]
            except KeyError:
                raise SystemExit(f"{spec}: records are missing field '{field}'")
        return [float(x) for x in data]
    try:
        return [float(x) for x in spec.replace(" ", "").split(",") if x != ""]
    except ValueError:
        raise SystemExit(f"could not parse '{spec}' as numbers or find it as a file")


# ------------------------------------------------------------- primitives


def percentile(values, q):
    """Linear-interpolated percentile, matching numpy.percentile's default.

    Hand-rolled because numpy is not available. Interpolates rather than
    picking a nearest rank so a B=1000 bootstrap does not quantize the CI
    bounds to whole resample values.
    """
    if not values:
        raise ValueError("percentile of empty sequence")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * (q / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return ordered[int(k)]
    return ordered[lo] * (hi - k) + ordered[hi] * (k - lo)


def mean(values):
    return sum(values) / len(values) if values else float("nan")


def bootstrap_means(values, B, rng):
    """B resample means, drawn with replacement."""
    n = len(values)
    out = []
    for _ in range(B):
        out.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    return out


def bootstrap_paired_deltas(new, base, B, rng):
    """B resample means of the per-item delta (new - base).

    Resamples ITEM INDICES, not the two arrays independently. Per-prompt
    variance is shared between arms and cancels, which is why the paired
    CI is tighter than comparing two independent CIs — and why comparing
    two independent CIs on the same corpus is the wrong test.
    """
    if len(new) != len(base):
        raise SystemExit(
            f"paired bootstrap needs equal lengths, got {len(new)} and {len(base)}"
        )
    deltas = [n - b for n, b in zip(new, base)]
    return bootstrap_means(deltas, B, rng)


# ------------------------------------------------------------- subcommands


def cmd_bootstrap(args):
    new = load_numbers(args.scores, args.field)
    base = load_numbers(args.baseline, args.baseline_field or args.field)
    rng = random.Random(args.seed)

    result = {
        "test": None,
        "seed": args.seed,
        "B": args.B,
        "n": len(new),
    }

    if base is None:
        samples = bootstrap_means(new, args.B, rng)
        lo, hi = percentile(samples, 2.5), percentile(samples, 97.5)
        result.update(
            test="single-arm",
            mean=mean(new),
            ci95=[lo, hi],
            verdict=None,
        )
        print(f"n={len(new)}  mean={mean(new):.3f}  95% CI [{lo:.3f}, {hi:.3f}]")
        print(f"(B={args.B}, seed={args.seed})")
        print("\nNo baseline given, so no ship verdict. Pass --baseline to gate a change.")

    elif args.paired:
        samples = bootstrap_paired_deltas(new, base, args.B, rng)
        lo, hi = percentile(samples, 2.5), percentile(samples, 97.5)
        delta = mean(new) - mean(base)
        # Ship rule for the paired test: the delta CI must exclude zero.
        ships = lo > 0
        regresses = hi < 0
        result.update(
            test="paired",
            baseline_mean=mean(base),
            new_mean=mean(new),
            delta=delta,
            delta_ci95=[lo, hi],
            verdict="SHIP" if ships else ("REGRESSION" if regresses else "INCONCLUSIVE"),
        )
        print(f"n={len(new)} paired items")
        print(f"baseline mean = {mean(base):.3f}")
        print(f"new mean      = {mean(new):.3f}")
        print(f"delta         = {delta:+.3f}   95% CI [{lo:+.3f}, {hi:+.3f}]")
        print(f"(B={args.B}, seed={args.seed})")
        print()
        if ships:
            print("VERDICT: SHIP. Delta CI excludes zero on the improving side.")
        elif regresses:
            print("VERDICT: REGRESSION. Delta CI excludes zero on the losing side.")
            print("Do not ship. This is the gate doing its job.")
        else:
            print("VERDICT: INCONCLUSIVE. Delta CI spans zero.")
            print("The improvement is not distinguishable from noise at this N.")
            print("Grow the corpus (see `evalstats.py power`) or widen the MDE.")
            print("Do NOT report this as a win.")

    else:
        s_new = bootstrap_means(new, args.B, rng)
        s_base = bootstrap_means(base, args.B, rng)
        n_lo, n_hi = percentile(s_new, 2.5), percentile(s_new, 97.5)
        b_lo, b_hi = percentile(s_base, 2.5), percentile(s_base, 97.5)
        overlap = not (n_lo > b_hi or b_lo > n_hi)
        result.update(
            test="unpaired",
            baseline_mean=mean(base),
            baseline_ci95=[b_lo, b_hi],
            new_mean=mean(new),
            new_ci95=[n_lo, n_hi],
            overlap=overlap,
            verdict="INCONCLUSIVE" if overlap else ("SHIP" if mean(new) > mean(base) else "REGRESSION"),
        )
        print(f"baseline  n={len(base)}  mean={mean(base):.3f}  95% CI [{b_lo:.3f}, {b_hi:.3f}]")
        print(f"new       n={len(new)}  mean={mean(new):.3f}  95% CI [{n_lo:.3f}, {n_hi:.3f}]")
        print(f"(B={args.B}, seed={args.seed})")
        print()
        if overlap:
            print("VERDICT: INCONCLUSIVE. The CIs overlap.")
            print("Either the improvement is noise or the corpus is too small.")
        else:
            print(f"VERDICT: {result['verdict']}. The CIs are disjoint.")
        print()
        print("NOTE: if both arms ran on the SAME prompts, rerun with --paired.")
        print("The unpaired test is strictly weaker and will call real wins inconclusive.")

    if args.json:
        print(json.dumps(result, indent=2))
    return result


def cmd_ece(args):
    """Expected Calibration Error over M equal-width confidence bins."""
    if args.data:
        with open(args.data) as fh:
            rows = json.load(fh)
        if isinstance(rows, dict):
            rows = rows.get("results") or rows.get("scores") or rows.get("items")
        confidences = [float(r[args.confidence_field]) for r in rows]
        correct = [float(r[args.correct_field]) for r in rows]
    else:
        confidences = load_numbers(args.confidences)
        correct = load_numbers(args.correct)

    if len(confidences) != len(correct):
        raise SystemExit("confidence and correctness lists must be the same length")

    # Correctness may arrive as a 0-4 rubric score rather than a 0/1 flag.
    # The rubric's own pass bar is >=3, so binarize on that rather than
    # silently averaging rubric points against probabilities.
    if any(c > 1 for c in correct):
        correct = [1.0 if c >= args.pass_bar else 0.0 for c in correct]

    M = args.bins
    n = len(confidences)
    total = 0.0
    table = []
    for i in range(M):
        lo = i / M
        hi = (i + 1) / M
        # The last bin is closed on the right. The obvious `>= lo and < hi`
        # silently drops every confidence of exactly 1.0, which is both the
        # most common value in practice and the one that matters most for
        # detecting overconfidence.
        if i == M - 1:
            idx = [j for j, c in enumerate(confidences) if lo <= c <= hi]
        else:
            idx = [j for j, c in enumerate(confidences) if lo <= c < hi]
        if not idx:
            table.append((lo, hi, 0, None, None, None))
            continue
        acc_b = sum(correct[j] for j in idx) / len(idx)
        conf_b = sum(confidences[j] for j in idx) / len(idx)
        gap = abs(acc_b - conf_b)
        total += (len(idx) / n) * gap
        table.append((lo, hi, len(idx), conf_b, acc_b, acc_b - conf_b))

    print(f"ECE = {total:.4f}   (N={n}, {M} bins, target <= 0.10)")
    print()
    print(f"{'bin':>12} {'count':>6} {'conf':>7} {'acc':>7} {'signed gap':>11}")
    for lo, hi, count, conf_b, acc_b, signed in table:
        if count == 0:
            print(f"{lo:.1f}-{hi:.1f}".rjust(12) + f"{0:>7}" + "        -       -           -")
            continue
        flag = "  overconfident" if signed < -0.05 else ("  underconfident" if signed > 0.05 else "")
        print(
            f"{lo:.1f}-{hi:.1f}".rjust(12)
            + f"{count:>7}{conf_b:>8.3f}{acc_b:>8.3f}{signed:>+12.3f}{flag}"
        )
    print()
    if total > 0.10:
        print("ECE is above target. Chase OVERCONFIDENT bins first (negative gap):")
        print("an overconfident wrong answer on a safety-critical prompt is a trust")
        print("event and a latent safety event. Underconfidence only loses the user.")
    if args.json:
        print(json.dumps({"ece": total, "n": n, "bins": M}, indent=2))
    return total


def cmd_kappa(args):
    """Cohen's kappa, optionally weighted, for judge-vs-human agreement."""
    human = [int(round(x)) for x in load_numbers(args.human, args.field)]
    judge = [int(round(x)) for x in load_numbers(args.judge, args.field)]
    if len(human) != len(judge):
        raise SystemExit("human and judge score lists must be the same length")

    categories = sorted(set(human) | set(judge))
    k = len(categories)
    index = {c: i for i, c in enumerate(categories)}
    n = len(human)

    if k == 1:
        print("kappa = undefined: every rating is the same category.")
        print("With zero variance there is no agreement beyond chance to measure.")
        print("Score a gold set with real spread before trusting the judge.")
        return None

    observed = [[0.0] * k for _ in range(k)]
    for h, j in zip(human, judge):
        observed[index[h]][index[j]] += 1.0 / n

    h_marg = [sum(observed[i]) for i in range(k)]
    j_marg = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    expected = [[h_marg[i] * j_marg[j] for j in range(k)] for i in range(k)]

    if args.weights == "none":
        w = [[0.0 if i == j else 1.0 for j in range(k)] for i in range(k)]
    elif args.weights == "linear":
        w = [[abs(i - j) / (k - 1) for j in range(k)] for i in range(k)]
    else:  # quadratic
        w = [[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]

    num = sum(w[i][j] * observed[i][j] for i in range(k) for j in range(k))
    den = sum(w[i][j] * expected[i][j] for i in range(k) for j in range(k))
    if den == 0:
        print("kappa = undefined: expected disagreement is zero.")
        return None
    kappa = 1.0 - num / den

    if kappa < 0.2:
        band = "poor"
    elif kappa < 0.4:
        band = "fair"
    elif kappa < 0.6:
        band = "moderate"
    elif kappa < 0.8:
        band = "substantial"
    else:
        band = "near-perfect"

    agree = sum(1 for h, j in zip(human, judge) if h == j) / n
    print(f"kappa ({args.weights}-weighted) = {kappa:.3f}   [{band}]")
    print(f"raw agreement = {agree:.1%}   (N={n}, {k} categories)")
    print()
    if kappa >= 0.6:
        print("At or above the 0.6 bar. The judge can be trusted at scale,")
        print("with the usual 10% sample-audit each run — judges drift.")
    else:
        print("BELOW the 0.6 bar. Do not run this judge at scale.")
        print("The fix is not more judge tokens. Sharpen the rubric boundaries,")
        print("add 2-3 disambiguation examples to the judge prompt, re-run.")
        print("Do not lower the target to match the judge.")
    if n < 20:
        print()
        print(f"WARNING: gold set is only {n} items. 20 is the minimum viable, 50 is better.")
    if args.json:
        print(json.dumps({"kappa": kappa, "weights": args.weights, "n": n, "band": band}, indent=2))
    return kappa


def cmd_power(args):
    """Required N for a target minimum detectable effect."""
    # Two-sided normal approximation. z for alpha=0.05 -> 1.96, power 0.8 -> 0.84.
    z_alpha = inverse_normal_cdf(1 - args.alpha / 2)
    z_beta = inverse_normal_cdf(args.power)
    p = args.baseline_rate
    d = args.mde
    n = ((z_alpha + z_beta) ** 2) * p * (1 - p) / (d ** 2)
    n_ceil = math.ceil(n)

    print(f"baseline pass rate = {p:.0%}")
    print(f"minimum detectable effect = {d:.0%}")
    print(f"alpha = {args.alpha}  (z = {z_alpha:.2f})")
    print(f"power = {args.power}  (z = {z_beta:.2f})")
    print()
    print(f"required N ~= {n_ceil} prompts")
    print()
    print("This is the two-proportion normal approximation. It is a planning")
    print("number, not a guarantee. For ordinal rubric means rather than a")
    print("pass/fail rate, the rule of thumb is ~100 prompts per dimension per")
    print("arm to detect a 0.3-point shift at 80% power with sigma ~= 1.")
    print()
    print("If the corpus cannot reach this N, widen the MDE BEFORE running.")
    print("An underpowered eval that returns null is not evidence of no effect.")
    if args.json:
        print(json.dumps({"required_n": n_ceil, "baseline_rate": p, "mde": d}, indent=2))
    return n_ceil


def inverse_normal_cdf(p):
    """Acklam's rational approximation to the normal quantile function.

    Accurate to ~1e-9 across the range, which is far more than a power
    calculation needs. Hand-rolled because scipy is not available.
    """
    if not 0 < p < 1:
        raise ValueError("p must be in (0, 1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow = 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > 1 - plow:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


# ---------------------------------------------------------------- selftest


def selftest():
    failures = []

    def check(name, got, want, tol=1e-6):
        ok = abs(got - want) <= tol if isinstance(want, float) else got == want
        if not ok:
            failures.append(f"{name}: got {got!r}, want {want!r}")
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")

    print("percentile")
    check("median of 1..5", percentile([1, 2, 3, 4, 5], 50), 3.0)
    check("p25 of 1..5", percentile([1, 2, 3, 4, 5], 25), 2.0)
    check("p97.5 interpolates", percentile([1, 2, 3, 4], 97.5), 3.925, tol=1e-9)

    print("bootstrap")
    rng = random.Random(DEFAULT_SEED)
    const = bootstrap_means([3, 3, 3, 3], 200, rng)
    check("constant array has zero-width CI", percentile(const, 2.5), 3.0)
    a = bootstrap_means([1, 2, 3, 4, 5], 200, random.Random(7))
    b = bootstrap_means([1, 2, 3, 4, 5], 200, random.Random(7))
    check("same seed is reproducible", a == b, True)
    c = bootstrap_means([1, 2, 3, 4, 5], 200, random.Random(8))
    check("different seed differs", a != c, True)
    paired = bootstrap_paired_deltas([4, 4, 4], [3, 3, 3], 100, random.Random(1))
    check("paired delta of constant +1", percentile(paired, 50), 1.0)

    print("ece")
    # Half correct at confidence 0.5 -> perfectly calibrated -> ECE 0.
    args = argparse.Namespace(
        data=None, confidences="0.5,0.5,0.5,0.5", correct="1,0,1,0",
        bins=10, json=False, confidence_field="c", correct_field="k", pass_bar=3,
    )
    ece_val = cmd_ece(args)
    check("perfectly calibrated -> 0", ece_val, 0.0, tol=1e-9)
    # Confidence 1.0 must land in the last bin, not vanish.
    args = argparse.Namespace(
        data=None, confidences="1.0,1.0", correct="0,0",
        bins=10, json=False, confidence_field="c", correct_field="k", pass_bar=3,
    )
    ece_val = cmd_ece(args)
    check("conf=1.0 counted (not dropped)", ece_val, 1.0, tol=1e-9)

    print("kappa")
    args = argparse.Namespace(human="0,1,2,3,4", judge="0,1,2,3,4",
                             weights="quadratic", field=None, json=False)
    check("perfect agreement -> 1.0", cmd_kappa(args), 1.0, tol=1e-9)
    args = argparse.Namespace(human="0,0,1,1", judge="0,1,0,1",
                             weights="none", field=None, json=False)
    check("chance agreement -> 0.0", cmd_kappa(args), 0.0, tol=1e-9)

    print("power")
    args = argparse.Namespace(baseline_rate=0.75, mde=0.05, alpha=0.05,
                             power=0.8, json=False)
    n = cmd_power(args)
    # The worked example in references/evaluation-core.md gives ~588.
    check("worked example ~= 588", abs(n - 588) <= 2, True)

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  {f}")
        return 1
    print("all selftests passed")
    return 0


# -------------------------------------------------------------------- cli


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic eval statistics for aiml-dude.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--selftest", action="store_true", help="run known-answer tests and exit")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("bootstrap", help="confidence intervals and the ship verdict")
    p.add_argument("--scores", required=True, help="new-arm scores (inline list or JSON file)")
    p.add_argument("--baseline", help="baseline-arm scores; omit for a single-arm CI")
    p.add_argument("--paired", action="store_true",
                   help="both arms ran the SAME prompts in the same order (use this whenever true)")
    p.add_argument("--field", help="field name when the JSON is an array of objects")
    p.add_argument("--baseline-field", help="field name for the baseline file, if different")
    p.add_argument("-B", type=int, default=DEFAULT_B, help=f"resamples (default {DEFAULT_B})")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="RNG seed; printed with results")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("ece", help="expected calibration error")
    p.add_argument("--data", help="JSON records file with confidence + correctness fields")
    p.add_argument("--confidences", help="inline list or JSON array file")
    p.add_argument("--correct", help="inline list or JSON array file (0/1, or 0-4 rubric)")
    p.add_argument("--confidence-field", default="confidence")
    p.add_argument("--correct-field", default="correctness")
    p.add_argument("--pass-bar", type=float, default=3,
                   help="rubric score counted as correct when correctness is 0-4 (default 3)")
    p.add_argument("--bins", type=int, default=10)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_ece)

    p = sub.add_parser("kappa", help="judge-vs-human agreement")
    p.add_argument("--human", required=True)
    p.add_argument("--judge", required=True)
    p.add_argument("--weights", choices=["quadratic", "linear", "none"], default="quadratic",
                   help="quadratic for ordinal rubric scores (default)")
    p.add_argument("--field")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_kappa)

    p = sub.add_parser("power", help="required corpus size for a target effect")
    p.add_argument("--baseline-rate", type=float, required=True, help="current pass rate, 0-1")
    p.add_argument("--mde", type=float, required=True, help="minimum detectable effect, 0-1")
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--power", type=float, default=0.8)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_power)

    args = parser.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
