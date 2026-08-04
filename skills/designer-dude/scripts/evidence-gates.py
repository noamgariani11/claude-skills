#!/usr/bin/env python3
"""Evaluate evidence automation cannot honestly create for itself.

Six independent modes turn external observations into reproducible gates:

  evidence-gates.py detectors --labels labels.json --predictions predictions.json
  evidence-gates.py ratings --input expert-ratings.json
  evidence-gates.py usability --input usability-observations.json
  evidence-gates.py assistive-tech --input at-observations.json
  evidence-gates.py sampling --input sampling-plan.json
  evidence-gates.py performance --input performance-observations.json

Every mode writes JSON with status pass/fail/insufficient. `insufficient` is
deliberately non-passing: absence of participants, reviewers, held-out cases,
or an AT/browser pairing is an evidence gap, not a clean result.
"""

import argparse
import collections
import datetime
import hashlib
import json
import math
import pathlib
import random
import statistics
import sys
import urllib.parse

SCHEMAS = {
    "detector-labels": "designer-dude-detector-labels/v1",
    "detector-predictions": "designer-dude-detector-predictions/v1",
    "ratings": "designer-dude-expert-ratings/v1",
    "usability": "designer-dude-usability-observations/v1",
    "assistive-tech": "designer-dude-at-observations/v1",
    "sampling": "designer-dude-sampling-plan/v1",
    "performance": "designer-dude-performance-observations/v1",
}
OUTCOMES = {"positive", "negative", "inapplicable"}
SHA256 = set("0123456789abcdef")
MAX_EVIDENCE_AGE_DAYS = 90

# CLI options may make a study stricter for a particular product, but they
# must not silently weaken the policy used by the perfection certificate.
POLICY = {
    "detectors": {"min_cases": 100, "min_positive": 50, "min_negative": 40,
                  "min_labelers": 2, "min_precision_lower": .94,
                  "min_recall_lower": .94, "max_cannot_tell": .05},
    "ratings": {"min_products": 12, "min_reviewers": 3, "min_alpha": .8,
                "min_spearman_lower": .7, "min_concordance": .9,
                "max_mae": 5, "max_abs_bias": 3, "max_error": 10,
                "min_score_span": 80, "min_high_products": 2,
                "min_low_products": 2, "min_high_score": 90,
                "max_low_score": 20,
                "bootstrap": 1000},
    "usability": {"min_participants": 10, "min_tasks": 3,
                  "min_attempts": 10, "min_success_lower": .7},
    "assistive-tech": {"min_combinations": 2, "min_tasks": 3},
    "sampling": {"min_structured": 3, "min_random": 2, "min_processes": 1},
    "performance": {"min_surfaces": 3, "min_observations": 100,
                    "min_window_days": 28, "max_lcp_ms": 2500,
                    "max_inp_ms": 200, "max_cls": .1},
}


def policy_errors(mode, args):
    """Reject options that make the named perfection policy easier to pass."""
    errors = []
    for key, floor in POLICY[mode].items():
        value = getattr(args, key)
        if key.startswith("max_"):
            weakened = not 0 <= value <= floor
        elif key in {"min_precision_lower", "min_recall_lower", "min_alpha",
                     "min_spearman_lower", "min_success_lower"}:
            weakened = not floor <= value <= 1
        else:
            weakened = value < floor
        if weakened:
            relation = "<=" if key.startswith("max_") else ">="
            errors.append(f"{key} must be {relation} {floor} for perfection evidence")
    return errors


def load(path):
    try:
        with open(path, encoding="utf8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return doc


def is_hash(value):
    value = str(value or "").lower()
    return len(value) == 64 and set(value) <= SHA256


def document_hash(doc):
    """Hash parsed evidence deterministically, independent of JSON whitespace."""
    encoded = json.dumps(doc, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf8")
    return hashlib.sha256(encoded).hexdigest()


def file_hash(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_claims(records, errors):
    """Normalize portable nested evidence references and reject ambiguity."""
    unique = {}
    for record in records:
        path = str(record.get("path") or "").strip()
        digest = str(record.get("sha256") or "").strip().lower()
        pure = pathlib.PurePosixPath(path)
        if not path or pure.is_absolute() or ".." in pure.parts or not is_hash(digest):
            errors.append(f"invalid nested evidence artifact: {path or '(blank)'}")
            continue
        if path in unique and unique[path]["sha256"] != digest:
            errors.append(f"nested evidence artifact has conflicting hashes: {path}")
            continue
        unique[path] = {"path": path, "sha256": digest,
                        "kind": str(record.get("kind") or "evidence")}
    return [unique[path] for path in sorted(unique)]


def parse_stamp(value):
    try:
        stamp = datetime.datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return stamp if stamp.tzinfo else stamp.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def evidence_age(value, label, errors):
    """Validate the date of the underlying observation, not this result file."""
    stamp = parse_stamp(value)
    if stamp is None:
        errors.append(f"{label} must be an ISO-8601 timestamp")
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    age = (now - stamp.astimezone(datetime.timezone.utc)).days
    if age < -1:
        errors.append(f"{label} is in the future")
    if age > MAX_EVIDENCE_AGE_DAYS:
        errors.append(f"{label} is stale ({age} days; max {MAX_EVIDENCE_AGE_DAYS})")
    return age


def wilson(successes, total, z=1.959963984540054):
    if total <= 0:
        return [0.0, 0.0]
    p = successes / total
    den = 1 + z * z / total
    center = (p + z * z / (2 * total)) / den
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / den
    return [round(max(0, center - spread), 6), round(min(1, center + spread), 6)]


def metric(num, den):
    return {"value": round(num / den, 6) if den else None,
            "numerator": num, "denominator": den,
            "ci95Wilson": wilson(num, den) if den else None}


def percentile(values, quantile):
    """Nearest-rank percentile, matching threshold classification semantics."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


def rank(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    at = 0
    while at < len(order):
        end = at + 1
        while end < len(order) and values[order[end]] == values[order[at]]:
            end += 1
        average = (at + 1 + end) / 2
        for pos in range(at, end):
            ranks[order[pos]] = average
        at = end
    return ranks


def pearson(xs, ys):
    if len(xs) < 2:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    dx, dy = [x - mx for x in xs], [y - my for y in ys]
    den = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    return sum(x * y for x, y in zip(dx, dy)) / den if den else None


def spearman(xs, ys):
    return pearson(rank(xs), rank(ys))


def lin_concordance(xs, ys):
    """Lin's CCC: correlation penalized for location and scale disagreement."""
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    vx = statistics.fmean((x - mx) ** 2 for x in xs)
    vy = statistics.fmean((y - my) ** 2 for y in ys)
    cov = statistics.fmean((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = vx + vy + (mx - my) ** 2
    return 2 * cov / den if den else None


def bootstrap_spearman(xs, ys, iterations=4000, seed=1729):
    if len(xs) < 4:
        return None
    rng = random.Random(seed)
    samples = []
    n = len(xs)
    for _ in range(iterations):
        idx = [rng.randrange(n) for _ in range(n)]
        value = spearman([xs[i] for i in idx], [ys[i] for i in idx])
        if value is not None:
            samples.append(value)
    if not samples:
        return None
    samples.sort()
    return [round(samples[int(0.025 * (len(samples) - 1))], 6),
            round(samples[int(0.975 * (len(samples) - 1))], 6)]


def krippendorff_interval(units):
    """Krippendorff alpha with squared interval distance and missing values."""
    usable = [list(v) for v in units if len(v) >= 2]
    all_values = [v for unit in usable for v in unit]
    if not usable or len(set(all_values)) < 2:
        return None
    # Krippendorff's coincidence weighting gives each value, not each raw
    # pair, equal influence when units have different reviewer counts.
    observed_num = 0.0
    for values in usable:
        n = len(values)
        ordered_distance = sum((a - b) ** 2 for i, a in enumerate(values)
                               for b in values[i + 1:]) * 2
        observed_num += ordered_distance / (n - 1)
    n = len(all_values)
    do = observed_num / n
    expected_num = sum((a - b) ** 2 for i, a in enumerate(all_values)
                       for b in all_values[i + 1:]) * 2
    de = expected_num / (n * (n - 1))
    return 1 - do / de if de else None


def finish(mode, status, errors, warnings, evidence, thresholds):
    return {
        "schema": "designer-dude-evidence-gate/v1",
        "mode": mode,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "thresholds": thresholds,
        "evidence": evidence,
    }


def detector_gate(labels, predictions, args):
    errors, warnings = policy_errors("detectors", args), []
    if labels.get("schema") != SCHEMAS["detector-labels"]:
        errors.append("unsupported detector-labels schema")
    if predictions.get("schema") != SCHEMAS["detector-predictions"]:
        errors.append("unsupported detector-predictions schema")
    if labels.get("datasetId") != predictions.get("datasetId"):
        errors.append("datasetId mismatch")
    if not labels.get("labelsFrozenBeforePredictions"):
        errors.append("labelsFrozenBeforePredictions must be true")
    frozen, generated = parse_stamp(labels.get("frozenAt")), parse_stamp(predictions.get("generatedAt"))
    if frozen is None or generated is None:
        errors.append("labels.frozenAt and predictions.generatedAt must be ISO-8601 timestamps")
    elif frozen > generated:
        errors.append("labels were frozen after predictions were generated")
    generated_age = evidence_age(predictions.get("generatedAt"), "predictions.generatedAt", errors)
    labelers = {str(x).strip() for x in labels.get("labelers", []) if str(x).strip()}
    if len(labelers) < args.min_labelers:
        errors.append(f"needs >={args.min_labelers} independent labelers")
    profiles = labels.get("labelerProfiles") if isinstance(labels.get("labelerProfiles"), list) else []
    profiled, affiliations, expertise = set(), set(), set()
    for profile in profiles:
        if not isinstance(profile, dict):
            errors.append("labelerProfiles contains a non-object"); continue
        ident = str(profile.get("id") or "").strip()
        affiliation = str(profile.get("affiliation") or "").strip()
        years = profile.get("yearsExperience")
        skills = {str(x).strip().lower() for x in profile.get("expertise", []) if str(x).strip()}
        if ident not in labelers or ident in profiled:
            errors.append(f"invalid or duplicate labeler profile: {ident or '(blank)'}"); continue
        profiled.add(ident)
        if not affiliation: errors.append(f"{ident} labeler affiliation is missing")
        else: affiliations.add(affiliation.lower())
        if not isinstance(years, (int, float)) or years < 3:
            errors.append(f"{ident} needs >=3 years relevant labeling experience")
        if not skills: errors.append(f"{ident} labeler expertise is missing")
        expertise.update(skills)
    if profiled != labelers:
        errors.append("every labeler needs exactly one labelerProfiles entry")
    if len(affiliations) < 2:
        errors.append("labelers need at least two independent affiliations")
    if not {"visual-design", "accessibility"}.issubset(expertise):
        errors.append("labeler panel must collectively cover visual-design and accessibility")
    producer = str(predictions.get("producer") or "").strip()
    if producer and producer in labelers:
        errors.append("prediction producer must not be a labeler")
    items, expected, nested_artifacts = labels.get("items"), {}, []
    if not isinstance(items, list):
        errors.append("labels.items must be a list")
        items = []
    rule_counts = collections.defaultdict(lambda: collections.Counter())
    for item in items:
        if not isinstance(item, dict):
            errors.append("labels contains a non-object item")
            continue
        ident = str(item.get("id") or "").strip()
        outcome = str(item.get("expected") or "").lower()
        rule = str(item.get("rule") or "").strip()
        if not ident or ident in expected:
            errors.append(f"missing or duplicate label id: {ident or '(blank)'}")
            continue
        if outcome not in OUTCOMES or not rule:
            errors.append(f"invalid expected outcome/rule for {ident}")
            continue
        if item.get("split") != "holdout":
            errors.append(f"{ident} is not in the holdout split")
        if not is_hash(item.get("sourceSha256")):
            errors.append(f"{ident} has no valid sourceSha256")
        if not str(item.get("sourceArtifact") or "").strip():
            errors.append(f"{ident} has no sourceArtifact")
        else:
            nested_artifacts.append({"path": item.get("sourceArtifact"),
                                     "sha256": item.get("sourceSha256"),
                                     "kind": "detector-case"})
        votes = item.get("labels") or []
        voters = {str(x.get("reviewer") or "").strip() for x in votes if isinstance(x, dict)}
        if len(voters) < args.min_labelers or not voters.issubset(labelers):
            errors.append(f"{ident} lacks independent label votes")
        vote_outcomes = [str(x.get("outcome") or "").lower() for x in votes if isinstance(x, dict)]
        if len(vote_outcomes) != len(voters) or any(x != outcome for x in vote_outcomes):
            errors.append(f"{ident} consensus does not match its independent label votes")
        expected[ident] = (outcome, rule)
        rule_counts[rule][outcome] += 1
    predicted = {}
    for item in predictions.get("items", []) if isinstance(predictions.get("items"), list) else []:
        if not isinstance(item, dict):
            continue
        ident = str(item.get("id") or "").strip()
        outcome = str(item.get("outcome") or "").lower()
        if ident in predicted:
            errors.append(f"duplicate prediction id: {ident}")
        elif outcome not in OUTCOMES | {"cannot-tell"}:
            errors.append(f"invalid prediction outcome for {ident}")
        else:
            predicted[ident] = outcome
    unknown = sorted(set(predicted) - set(expected))
    missing = sorted(set(expected) - set(predicted))
    if unknown:
        errors.append(f"{len(unknown)} predictions have no held-out label")
    if missing:
        errors.append(f"{len(missing)} held-out labels have no prediction")

    tp = fp = tn = fn = cannot = 0
    per_rule = collections.defaultdict(lambda: collections.Counter())
    for ident, (truth, rule) in expected.items():
        got = predicted.get(ident)
        if got == "cannot-tell" or got is None:
            cannot += 1; per_rule[rule]["cannotTell"] += 1; continue
        # Inapplicable is a negative case: ACT consistency does not permit a
        # passed/inapplicable example to be failed by the implementation.
        truth_pos, got_pos = truth == "positive", got == "positive"
        key = "tp" if truth_pos and got_pos else "fn" if truth_pos else "fp" if got_pos else "tn"
        if key == "tp": tp += 1
        elif key == "fp": fp += 1
        elif key == "tn": tn += 1
        else: fn += 1
        per_rule[rule][key] += 1
    precision = metric(tp, tp + fp)
    recall = metric(tp, tp + fn)
    specificity = metric(tn, tn + fp)
    coverage = metric(len(expected) - cannot, len(expected))
    thresholds = {"minCases": args.min_cases, "minPositive": args.min_positive,
                  "minNegative": args.min_negative, "minLabelers": args.min_labelers,
                  "minPrecisionLower95": args.min_precision_lower,
                  "minRecallLower95": args.min_recall_lower,
                  "maxCannotTellRatio": args.max_cannot_tell,
                  "maxAgeDays": MAX_EVIDENCE_AGE_DAYS}
    insufficient = []
    if len(expected) < args.min_cases: insufficient.append("too few held-out cases")
    if tp + fn < args.min_positive: insufficient.append("too few positive cases")
    if tn + fp < args.min_negative: insufficient.append("too few negative/inapplicable cases")
    if precision["ci95Wilson"] is None or precision["ci95Wilson"][0] < args.min_precision_lower:
        insufficient.append("precision confidence bound below threshold")
    if recall["ci95Wilson"] is None or recall["ci95Wilson"][0] < args.min_recall_lower:
        insufficient.append("recall confidence bound below threshold")
    if len(expected) and cannot / len(expected) > args.max_cannot_tell:
        insufficient.append("cannot-tell ratio above threshold")
    for rule, counts in rule_counts.items():
        if counts["positive"] == 0 or counts["negative"] + counts["inapplicable"] == 0:
            insufficient.append(f"rule {rule} lacks both positive and negative coverage")
    status = "fail" if errors or fp or fn else "insufficient" if insufficient else "pass"
    errors.extend(insufficient)
    nested_artifacts = artifact_claims(nested_artifacts, errors)
    if errors and status == "pass": status = "fail"
    detail = {rule: dict(counts) for rule, counts in sorted(per_rule.items())}
    return finish("detectors", status, errors, warnings,
                  {"datasetId": labels.get("datasetId"), "cases": len(expected),
                   "labelerPanel": {"profiled": len(profiled), "affiliations": len(affiliations),
                                    "expertise": sorted(expertise)},
                   "observedAt": predictions.get("generatedAt"), "ageDays": generated_age,
                   "inputDigests": {"labels": document_hash(labels),
                                    "predictions": document_hash(predictions)},
                   "artifacts": nested_artifacts,
                   "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
                                 "cannotTell": cannot},
                   "precision": precision, "recall": recall, "specificity": specificity,
                   "coverage": coverage, "perRule": detail}, thresholds)


def ratings_gate(doc, args):
    errors, warnings, products = policy_errors("ratings", args), [], []
    if doc.get("schema") != SCHEMAS["ratings"]:
        errors.append("unsupported expert-ratings schema")
    if doc.get("ratingsBlindToToolScore") is not True:
        errors.append("ratingsBlindToToolScore must be true")
    study = doc.get("study") if isinstance(doc.get("study"), dict) else {}
    if not str(study.get("coordinator") or "").strip(): errors.append("study.coordinator is missing")
    if not str(study.get("toolVersion") or "").strip(): errors.append("study.toolVersion is missing")
    if not is_hash(study.get("protocolSha256")): errors.append("study.protocolSha256 is invalid")
    study_age = evidence_age(study.get("conductedAt"), "study.conductedAt", errors)
    reviewers = {str(x).strip() for x in doc.get("reviewers", []) if str(x).strip()}
    if len(reviewers) < args.min_reviewers:
        errors.append(f"needs >={args.min_reviewers} reviewers")
    profiles = doc.get("reviewerProfiles") if isinstance(doc.get("reviewerProfiles"), list) else []
    profiled, affiliations, expertise = set(), set(), set()
    for profile in profiles:
        if not isinstance(profile, dict):
            errors.append("reviewerProfiles contains a non-object"); continue
        ident = str(profile.get("id") or "").strip()
        affiliation = str(profile.get("affiliation") or "").strip()
        years = profile.get("yearsExperience")
        skills = {str(x).strip().lower() for x in profile.get("expertise", []) if str(x).strip()}
        if ident not in reviewers or ident in profiled:
            errors.append(f"invalid or duplicate reviewer profile: {ident or '(blank)'}"); continue
        profiled.add(ident)
        if not affiliation: errors.append(f"{ident} reviewer affiliation is missing")
        else: affiliations.add(affiliation.lower())
        if not isinstance(years, (int, float)) or years < 3:
            errors.append(f"{ident} needs >=3 years relevant review experience")
        if not skills: errors.append(f"{ident} reviewer expertise is missing")
        expertise.update(skills)
    if profiled != reviewers:
        errors.append("every reviewer needs exactly one reviewerProfiles entry")
    if len(affiliations) < 2:
        errors.append("reviewers need at least two independent affiliations")
    if str(study.get("coordinator") or "").strip() in reviewers:
        errors.append("study coordinator must not be an expert rater")
    if not {"product-design", "accessibility"}.issubset(expertise):
        errors.append("reviewer panel must collectively cover product-design and accessibility")
    strata_doc = doc.get("strata") if isinstance(doc.get("strata"), dict) else {}
    strata_spec = {
        "productCategory": ("productCategories", 3),
        "surfaceType": ("surfaceTypes", 3),
        "qualityBand": ("qualityBands", 3),
        "viewportClass": ("viewportClasses", 2),
    }
    declared, covered = {}, {key: set() for key in strata_spec}
    for item_key, (declared_key, minimum) in strata_spec.items():
        values = {str(x).strip().lower() for x in strata_doc.get(declared_key, []) if str(x).strip()}
        declared[item_key] = values
        if len(values) < minimum:
            errors.append(f"strata.{declared_key} needs >={minimum} declared values")
    if not {"low", "mid", "high"}.issubset(declared["qualityBand"]):
        errors.append("strata.qualityBands must include low, mid and high")
    if not {"mobile", "desktop"}.issubset(declared["viewportClass"]):
        errors.append("strata.viewportClasses must include mobile and desktop")
    tool, consensus, units, nested_artifacts = [], [], [], []
    seen = set()
    for item in doc.get("products", []) if isinstance(doc.get("products"), list) else []:
        ident = str(item.get("id") or "").strip()
        if not ident or ident in seen:
            errors.append(f"missing or duplicate product id: {ident or '(blank)'}"); continue
        seen.add(ident)
        if not is_hash(item.get("artifactSha256")):
            errors.append(f"{ident} has no valid artifactSha256")
        if not str(item.get("artifact") or "").strip():
            errors.append(f"{ident} has no pinned artifact path")
        else:
            nested_artifacts.append({"path": item.get("artifact"),
                                     "sha256": item.get("artifactSha256"),
                                     "kind": "expert-rated-product"})
        item_strata = item.get("strata") if isinstance(item.get("strata"), dict) else {}
        valid_strata = True
        for key in strata_spec:
            value = str(item_strata.get(key) or "").strip().lower()
            if not value or value not in declared[key]:
                errors.append(f"{ident} has invalid or undeclared strata.{key}")
                valid_strata = False
            else:
                covered[key].add(value)
        ratings = item.get("ratings") or []
        values, voters = [], set()
        for rating in ratings:
            who = str(rating.get("reviewer") or "").strip()
            value = rating.get("score")
            if who in reviewers and who not in voters and isinstance(value, (int, float)) and 0 <= value <= 100:
                values.append(float(value)); voters.add(who)
        if len(values) < args.min_reviewers:
            errors.append(f"{ident} lacks {args.min_reviewers} valid independent ratings"); continue
        score = item.get("toolScore")
        if not isinstance(score, (int, float)) or not 0 <= score <= 100:
            errors.append(f"{ident} has invalid toolScore"); continue
        tool.append(float(score)); consensus.append(statistics.median(values)); units.append(values)
        products.append({"id": ident, "toolScore": score,
                         "expertMedian": statistics.median(values), "ratings": len(values),
                         "strata": item_strata if valid_strata else {},
                         "artifact": item.get("artifact"),
                         "artifactSha256": str(item.get("artifactSha256") or "").lower()})
    for key, (declared_key, _) in strata_spec.items():
        missing = sorted(declared[key] - covered[key])
        if missing:
            errors.append(f"uncovered strata.{declared_key}: " + ", ".join(missing))
    band_counts = collections.Counter(
        str(product.get("strata", {}).get("qualityBand") or "").lower() for product in products)
    if any(band_counts[band] < 3 for band in ("low", "mid", "high")):
        errors.append("low, mid and high quality bands each need >=3 products")
    rho = spearman(tool, consensus)
    ci = bootstrap_spearman(tool, consensus, args.bootstrap, args.seed)
    alpha = krippendorff_interval(units)
    errors_by_product = [x - y for x, y in zip(tool, consensus)]
    mae = statistics.fmean(abs(x) for x in errors_by_product) if errors_by_product else None
    bias = statistics.fmean(errors_by_product) if errors_by_product else None
    max_error = max((abs(x) for x in errors_by_product), default=None)
    concordance = lin_concordance(tool, consensus)
    thresholds = {"minProducts": args.min_products, "minReviewers": args.min_reviewers,
                  "minAgreementAlpha": args.min_alpha,
                  "minSpearmanLower95": args.min_spearman_lower,
                  "minLinConcordance": args.min_concordance,
                  "maxMeanAbsoluteError": args.max_mae,
                  "maxAbsoluteBias": args.max_abs_bias,
                  "maxProductError": args.max_error,
                  "minExpertScoreSpan": args.min_score_span,
                  "minHighProducts": args.min_high_products,
                  "minLowProducts": args.min_low_products,
                  "minHighExpertScore": args.min_high_score,
                  "maxLowExpertScore": args.max_low_score,
                  "bootstrapIterations": args.bootstrap, "seed": args.seed,
                  "maxAgeDays": MAX_EVIDENCE_AGE_DAYS}
    insufficient = []
    if len(products) < args.min_products: insufficient.append("too few independently rated products")
    if alpha is None or alpha < args.min_alpha: insufficient.append("reviewer agreement below threshold")
    if ci is None or ci[0] < args.min_spearman_lower: insufficient.append("score correlation confidence bound below threshold")
    if concordance is None or concordance < args.min_concordance:
        insufficient.append("score concordance below threshold")
    if mae is None or mae > args.max_mae: insufficient.append("mean absolute score error above threshold")
    if bias is None or abs(bias) > args.max_abs_bias: insufficient.append("systematic score bias above threshold")
    if max_error is None or max_error > args.max_error: insufficient.append("worst product score error above threshold")
    score_span = max(consensus) - min(consensus) if consensus else None
    high_products = sum(value >= args.min_high_score for value in consensus)
    low_products = sum(value <= args.max_low_score for value in consensus)
    if score_span is None or score_span < args.min_score_span:
        insufficient.append("expert-rated product set does not span enough of the score scale")
    if high_products < args.min_high_products:
        insufficient.append("too few expert-rated high-end products")
    if low_products < args.min_low_products:
        insufficient.append("too few expert-rated low-end products")
    nested_artifacts = artifact_claims(nested_artifacts, errors)
    status = "fail" if errors else "insufficient" if insufficient else "pass"
    errors.extend(insufficient)
    return finish("ratings", status, errors, warnings,
                  {"products": products, "count": len(products),
                   "reviewerPanel": {"profiled": len(profiled),
                                     "affiliations": len(affiliations),
                                     "expertise": sorted(expertise)},
                   "observedAt": study.get("conductedAt"), "ageDays": study_age,
                   "inputDigests": {"ratings": document_hash(doc)},
                   "artifacts": nested_artifacts,
                   "krippendorffAlphaInterval": round(alpha, 6) if alpha is not None else None,
                   "strataCoverage": {key: sorted(values) for key, values in covered.items()},
                   "spearman": round(rho, 6) if rho is not None else None,
                   "spearmanBootstrap95": ci,
                   "linConcordance": round(concordance, 6) if concordance is not None else None,
                   "meanAbsoluteError": round(mae, 6) if mae is not None else None,
                   "meanBias": round(bias, 6) if bias is not None else None,
                   "maxProductError": round(max_error, 6) if max_error is not None else None,
                   "expertScoreSpan": round(score_span, 6) if score_span is not None else None,
                   "highProducts": high_products, "lowProducts": low_products}, thresholds)


def usability_gate(doc, args):
    errors, warnings = policy_errors("usability", args), []
    if doc.get("schema") != SCHEMAS["usability"]:
        errors.append("unsupported usability-observations schema")
    study = doc.get("study") if isinstance(doc.get("study"), dict) else {}
    for key in ("facilitator", "productVersion", "recruitmentScope"):
        if not str(study.get(key) or "").strip(): errors.append(f"study.{key} is missing")
    study_age = evidence_age(study.get("conductedAt"), "study.conductedAt", errors)
    for key in ("protocolSha256", "productArtifactSha256"):
        if not is_hash(study.get(key)): errors.append(f"study.{key} is invalid")
    if not is_hash(study.get("samplingPlanSha256")):
        errors.append("study.samplingPlanSha256 is invalid")
    nested_artifacts = []
    for path_key, hash_key, kind in (
            ("protocolArtifact", "protocolSha256", "usability-protocol"),
            ("productArtifact", "productArtifactSha256", "reviewed-product"),
            ("samplingPlanArtifact", "samplingPlanSha256", "sampling-plan")):
        if not str(study.get(path_key) or "").strip():
            errors.append(f"study.{path_key} is missing")
        else:
            nested_artifacts.append({"path": study.get(path_key),
                                     "sha256": study.get(hash_key), "kind": kind})
    participants = {str(x).strip() for x in doc.get("participants", []) if str(x).strip()}
    if len(participants) < args.min_participants:
        errors.append(f"needs >={args.min_participants} pseudonymous participants")
    tasks_out, all_pass, seen_tasks = [], True, set()
    for task in doc.get("tasks", []) if isinstance(doc.get("tasks"), list) else []:
        ident = str(task.get("id") or "").strip()
        if not ident or ident in seen_tasks:
            errors.append(f"missing or duplicate task id: {ident or '(blank)'}")
            continue
        seen_tasks.add(ident)
        if not str(task.get("essentialFunction") or "").strip() or not is_hash(task.get("protocolTaskSha256")):
            errors.append(f"{ident} lacks an essential function or pinned task protocol")
        if not str(task.get("protocolTaskArtifact") or "").strip():
            errors.append(f"{ident} lacks a task protocol artifact")
        else:
            nested_artifacts.append({"path": task.get("protocolTaskArtifact"),
                                     "sha256": task.get("protocolTaskSha256"),
                                     "kind": "usability-task-protocol"})
        attempts = task.get("attempts") or []
        valid, success, critical = [], 0, 0
        for attempt in attempts:
            who = str(attempt.get("participant") or "").strip()
            if who not in participants or any(x[0] == who for x in valid):
                continue
            completed = attempt.get("completed") is True
            critical_error = attempt.get("criticalError") is True
            valid.append((who, completed, critical_error))
            success += int(completed and not critical_error)
            critical += int(critical_error)
        ci = wilson(success, len(valid)) if valid else None
        passed = (len(valid) >= args.min_attempts and critical == 0 and ci and
                  ci[0] >= args.min_success_lower)
        all_pass = all_pass and bool(passed)
        tasks_out.append({"id": ident, "attempts": len(valid), "successes": success,
                          "essentialFunction": task.get("essentialFunction"),
                          "protocolTaskSha256": task.get("protocolTaskSha256"),
                          "protocolTaskArtifact": task.get("protocolTaskArtifact"),
                          "criticalErrors": critical, "successCi95Wilson": ci,
                          "status": "pass" if passed else "insufficient" if not critical else "fail"})
    if len(tasks_out) < args.min_tasks:
        errors.append(f"needs >={args.min_tasks} representative tasks")
    if any(t["status"] == "fail" for t in tasks_out):
        errors.append("one or more tasks contains a critical error")
    elif not all_pass:
        errors.append("one or more tasks lacks sufficient successful observations")
    thresholds = {"minParticipants": args.min_participants, "minTasks": args.min_tasks,
                  "minAttemptsPerTask": args.min_attempts,
                  "minSuccessLower95": args.min_success_lower,
                  "maxAgeDays": MAX_EVIDENCE_AGE_DAYS}
    nested_artifacts = artifact_claims(nested_artifacts, errors)
    status = "fail" if any(t["status"] == "fail" for t in tasks_out) else \
             "insufficient" if errors else "pass"
    return finish("usability", status, errors, warnings,
                  {"inputDigests": {"observations": document_hash(doc)},
                   "artifacts": nested_artifacts,
                   "observedAt": study.get("conductedAt"), "ageDays": study_age,
                   "participants": len(participants), "tasks": tasks_out}, thresholds)


def at_gate(doc, args):
    errors, warnings, observations = policy_errors("assistive-tech", args), [], []
    if doc.get("schema") != SCHEMAS["assistive-tech"]:
        errors.append("unsupported at-observations schema")
    tester = str(doc.get("tester") or "").strip()
    if not tester: errors.append("tester is missing")
    review_age = evidence_age(doc.get("reviewedAt"), "reviewedAt", errors)
    if not is_hash(doc.get("productArtifactSha256")): errors.append("productArtifactSha256 is invalid")
    if not is_hash(doc.get("protocolSha256")): errors.append("protocolSha256 is invalid")
    if not is_hash(doc.get("samplingPlanSha256")): errors.append("samplingPlanSha256 is invalid")
    nested_artifacts = []
    for path_key, hash_key, kind in (
            ("protocolArtifact", "protocolSha256", "at-protocol"),
            ("productArtifact", "productArtifactSha256", "reviewed-product"),
            ("samplingPlanArtifact", "samplingPlanSha256", "sampling-plan")):
        if not str(doc.get(path_key) or "").strip():
            errors.append(f"{path_key} is missing")
        else:
            nested_artifacts.append({"path": doc.get(path_key), "sha256": doc.get(hash_key),
                                     "kind": kind})
    combos, stacks, tasks, observed_pairs = set(), set(), set(), set()
    for obs in doc.get("observations", []) if isinstance(doc.get("observations"), list) else []:
        required = ("task", "taskProtocolArtifact", "taskProtocolSha256", "at", "atVersion", "browser", "browserVersion", "platform",
                    "expected", "observed", "artifact", "artifactSha256")
        missing = [key for key in required if not str(obs.get(key) or "").strip()]
        if missing or not is_hash(obs.get("artifactSha256")) or not is_hash(obs.get("taskProtocolSha256")):
            errors.append("AT observation missing required versioned evidence: " + ", ".join(missing)); continue
        combo = (str(obs["at"]).lower(), str(obs["atVersion"]).lower(),
                 str(obs["browser"]).lower(), str(obs["browserVersion"]).lower(),
                 str(obs["platform"]).lower())
        stack = (str(obs["at"]).lower(), str(obs["browser"]).lower(),
                 str(obs["platform"]).lower())
        task = str(obs["task"])
        pair = (combo, task)
        if pair in observed_pairs:
            errors.append(f"duplicate AT observation for {task} on {'/'.join(combo)}"); continue
        observed_pairs.add(pair); combos.add(combo); stacks.add(stack); tasks.add(task)
        outcome = str(obs.get("outcome") or "").lower()
        if outcome not in {"pass", "fail"}:
            errors.append(f"AT observation for {obs['task']} has invalid outcome")
        observations.append({"task": obs["task"], "combination": list(combo), "outcome": outcome,
                             "taskProtocolArtifact": obs["taskProtocolArtifact"],
                             "taskProtocolSha256": str(obs["taskProtocolSha256"]).lower(),
                             "artifact": obs["artifact"],
                             "artifactSha256": str(obs["artifactSha256"]).lower()})
        nested_artifacts.extend([
            {"path": obs["taskProtocolArtifact"], "sha256": obs["taskProtocolSha256"],
             "kind": "at-task-protocol"},
            {"path": obs["artifact"], "sha256": obs["artifactSha256"],
             "kind": "at-observation"},
        ])
    failed = [x for x in observations if x["outcome"] == "fail"]
    if len(stacks) < args.min_combinations:
        errors.append(f"needs >={args.min_combinations} distinct AT/browser/platform stacks")
    if len(tasks) < args.min_tasks:
        errors.append(f"needs >={args.min_tasks} complete tasks")
    missing_pairs = [(combo, task) for combo in combos for task in tasks if (combo, task) not in observed_pairs]
    if missing_pairs:
        errors.append(f"AT matrix misses {len(missing_pairs)} task/combination observations")
    if failed: errors.append(f"{len(failed)} assistive-technology observations failed")
    thresholds = {"minCombinations": args.min_combinations, "minTasks": args.min_tasks,
                  "maxAgeDays": MAX_EVIDENCE_AGE_DAYS}
    nested_artifacts = artifact_claims(nested_artifacts, errors)
    status = "fail" if failed else "insufficient" if errors else "pass"
    return finish("assistive-tech", status, errors, warnings,
                  {"inputDigests": {"observations": document_hash(doc)},
                   "artifacts": nested_artifacts,
                   "observedAt": doc.get("reviewedAt"), "ageDays": review_age,
                   "tester": tester, "stacks": [list(x) for x in sorted(stacks)],
                   "combinations": [list(x) for x in sorted(combos)],
                   "tasks": sorted(tasks), "observations": observations}, thresholds)


def sampling_gate(doc, args):
    """Validate a WCAG-EM-shaped representative surface/process sample."""
    errors, warnings = policy_errors("sampling", args), []
    if doc.get("schema") != SCHEMAS["sampling"]:
        errors.append("unsupported sampling-plan schema")
    if not str(doc.get("author") or "").strip(): errors.append("author is missing")
    plan_age = evidence_age(doc.get("createdAt"), "createdAt", errors)
    scope = doc.get("scope") if isinstance(doc.get("scope"), dict) else {}
    for key in ("product", "version", "baseUrl", "conformanceTarget"):
        if not str(scope.get(key) or "").strip(): errors.append(f"scope.{key} is missing")
    page_types = {str(x).strip() for x in doc.get("pageTypes", []) if str(x).strip()}
    functions = {str(x).strip() for x in doc.get("essentialFunctions", []) if str(x).strip()}
    technologies = {str(x).strip() for x in doc.get("technologies", []) if str(x).strip()}
    if not page_types: errors.append("pageTypes is empty")
    if not functions: errors.append("essentialFunctions is empty")
    if not technologies: errors.append("technologies is empty")
    samples = doc.get("samples") if isinstance(doc.get("samples"), list) else []
    seen, covered_types, covered_functions, nested_artifacts = set(), set(), set(), []
    structured = random_count = 0
    for sample in samples:
        ident = str(sample.get("id") or "").strip() if isinstance(sample, dict) else ""
        if not ident or ident in seen:
            errors.append(f"missing or duplicate sample id: {ident or '(blank)'}"); continue
        seen.add(ident)
        kind = str(sample.get("selection") or "").lower()
        if kind == "structured":
            structured += 1
            if not str(sample.get("rationale") or "").strip():
                errors.append(f"{ident} structured sample has no selection rationale")
        elif kind == "random": random_count += 1
        else: errors.append(f"{ident} selection must be structured or random")
        if not str(sample.get("url") or "").strip() or not is_hash(sample.get("artifactSha256")):
            errors.append(f"{ident} lacks URL or content-addressed evidence")
        if not str(sample.get("artifact") or "").strip():
            errors.append(f"{ident} lacks a sampled artifact path")
        else:
            nested_artifacts.append({"path": sample.get("artifact"),
                                     "sha256": sample.get("artifactSha256"),
                                     "kind": "sampled-surface"})
        covered_types.update(str(x).strip() for x in sample.get("pageTypes", []) if str(x).strip())
        covered_functions.update(str(x).strip() for x in sample.get("functions", []) if str(x).strip())
    missing_types = sorted(page_types - covered_types)
    missing_functions = sorted(functions - covered_functions)
    if missing_types: errors.append("uncovered page types: " + ", ".join(missing_types))
    if missing_functions: errors.append("uncovered essential functions: " + ", ".join(missing_functions))
    exhaustive = doc.get("exhaustive") is True
    random_verified = False
    if not exhaustive:
        random_plan = doc.get("randomSelection") if isinstance(doc.get("randomSelection"), dict) else {}
        method = str(random_plan.get("method") or "").strip().lower()
        seed = str(random_plan.get("seed") or "").strip()
        population = random_plan.get("populationSize")
        selected = [str(x).strip() for x in random_plan.get("selectedIds", []) if str(x).strip()]
        actual_random = sorted(str(sample.get("id") or "").strip() for sample in samples
                               if isinstance(sample, dict) and
                               str(sample.get("selection") or "").lower() == "random")
        if method not in {"simple-random", "systematic-random"}:
            errors.append("randomSelection.method must be simple-random or systematic-random")
        if not seed:
            errors.append("randomSelection.seed is missing")
        if not isinstance(population, int) or population < len(actual_random):
            errors.append("randomSelection.populationSize is invalid")
        if len(selected) != len(set(selected)) or sorted(selected) != actual_random:
            errors.append("randomSelection.selectedIds does not match random samples")
        random_verified = not any(message.startswith("randomSelection.") for message in errors)
    inventory = doc.get("inventory") if isinstance(doc.get("inventory"), list) else []
    inventory_by_id = {}
    if exhaustive:
        for entry in inventory:
            ident = str(entry.get("id") or "").strip() if isinstance(entry, dict) else ""
            if (not ident or ident in inventory_by_id or
                    not str(entry.get("url") or "").strip() or
                    not is_hash(entry.get("artifactSha256"))):
                errors.append(f"invalid or duplicate exhaustive inventory entry: {ident or '(blank)'}")
                continue
            inventory_by_id[ident] = entry
        if not inventory_by_id:
            errors.append("exhaustive sampling requires a non-empty content-addressed inventory")
        mapped = set()
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            inventory_id = str(sample.get("inventoryId") or "").strip()
            entry = inventory_by_id.get(inventory_id)
            if entry is None:
                errors.append(f"{sample.get('id') or '(blank)'} has no matching exhaustive inventoryId")
                continue
            mapped.add(inventory_id)
            if (str(sample.get("url") or "").strip() != str(entry.get("url") or "").strip() or
                    str(sample.get("artifactSha256") or "").lower() !=
                    str(entry.get("artifactSha256") or "").lower()):
                errors.append(f"{sample.get('id')} does not match its exhaustive inventory evidence")
        missing_inventory = sorted(set(inventory_by_id) - mapped)
        if missing_inventory:
            errors.append("unsampled exhaustive inventory entries: " + ", ".join(missing_inventory))
    if not exhaustive and structured < args.min_structured:
        errors.append(f"needs >={args.min_structured} structured samples")
    if not exhaustive and random_count < args.min_random:
        errors.append(f"needs >={args.min_random} random samples")
    processes = doc.get("completeProcesses") if isinstance(doc.get("completeProcesses"), list) else []
    valid_processes = 0
    for process in processes:
        if not isinstance(process, dict): continue
        steps = process.get("steps") or []
        if (str(process.get("name") or "").strip() and len(steps) >= 2 and
                all(str(step.get("sampleId") or "") in seen and str(step.get("action") or "").strip()
                    for step in steps if isinstance(step, dict)) and
                len([x for x in steps if isinstance(x, dict)]) == len(steps)):
            valid_processes += 1
    if valid_processes < args.min_processes:
        errors.append(f"needs >={args.min_processes} complete processes mapped to sampled steps")
    nested_artifacts = artifact_claims(nested_artifacts, errors)
    thresholds = {"minStructured": args.min_structured, "minRandom": args.min_random,
                  "minProcesses": args.min_processes, "maxAgeDays": MAX_EVIDENCE_AGE_DAYS}
    return finish("sampling", "pass" if not errors else "insufficient", errors, warnings,
                  {"inputDigests": {"plan": document_hash(doc)},
                   "artifacts": nested_artifacts,
                   "observedAt": doc.get("createdAt"), "ageDays": plan_age,
                   "exhaustive": exhaustive, "inventory": len(inventory_by_id),
                   "randomSelectionVerified": random_verified if not exhaustive else None,
                   "samples": len(seen), "structured": structured,
                   "random": random_count, "coveredPageTypes": sorted(covered_types),
                   "coveredFunctions": sorted(covered_functions), "completeProcesses": valid_processes}, thresholds)


def performance_gate(doc, args):
    """Validate production field Core Web Vitals at p75 by surface/device."""
    errors, warnings = policy_errors("performance", args), []
    if doc.get("schema") != SCHEMAS["performance"]:
        errors.append("unsupported performance-observations schema")
    study = doc.get("study") if isinstance(doc.get("study"), dict) else {}
    for key in ("collector", "productVersion"):
        if not str(study.get(key) or "").strip(): errors.append(f"study.{key} is missing")
    study_age = evidence_age(study.get("conductedAt"), "study.conductedAt", errors)
    if study.get("productionBuild") is not True: errors.append("study.productionBuild must be true")
    if study.get("realUserMonitoring") is not True: errors.append("study.realUserMonitoring must be true")
    if not isinstance(study.get("windowDays"), (int, float)) or study.get("windowDays", 0) < args.min_window_days:
        errors.append(f"study.windowDays must be >={args.min_window_days}")
    nested_artifacts = []
    for path_key, hash_key, kind in (
            ("samplingPlanArtifact", "samplingPlanSha256", "sampling-plan"),
            ("environmentArtifact", "environmentSha256", "performance-environment")):
        if not str(study.get(path_key) or "").strip() or not is_hash(study.get(hash_key)):
            errors.append(f"study.{path_key}/{hash_key} is invalid")
        else:
            nested_artifacts.append({"path": study[path_key], "sha256": study[hash_key], "kind": kind})
    surfaces_out, seen = [], set()
    threshold_failures = 0
    for surface in doc.get("surfaces", []) if isinstance(doc.get("surfaces"), list) else []:
        if not isinstance(surface, dict):
            errors.append("performance surfaces contains a non-object"); continue
        ident = str(surface.get("id") or "").strip()
        url = str(surface.get("url") or "").strip()
        parsed = urllib.parse.urlparse(url)
        if not ident or ident in seen:
            errors.append(f"missing or duplicate performance surface id: {ident or '(blank)'}"); continue
        seen.add(ident)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"{ident} has no absolute HTTP(S) URL")
        if not str(surface.get("artifact") or "").strip() or not is_hash(surface.get("artifactSha256")):
            errors.append(f"{ident} has no pinned RUM export")
        else:
            nested_artifacts.append({"path": surface["artifact"], "sha256": surface["artifactSha256"],
                                     "kind": "rum-export"})
        observations = surface.get("observations") if isinstance(surface.get("observations"), list) else []
        devices = {}
        for device in ("mobile", "desktop"):
            rows = [row for row in observations if isinstance(row, dict) and
                    str(row.get("device") or "").lower() == device]
            valid = []
            for row in rows:
                values = (row.get("lcpMs"), row.get("inpMs"), row.get("cls"))
                if all(isinstance(value, (int, float)) and value >= 0 for value in values):
                    valid.append(values)
            if len(valid) < args.min_observations:
                errors.append(f"{ident}/{device} needs >={args.min_observations} complete field observations")
            lcp = percentile([x[0] for x in valid], .75)
            inp = percentile([x[1] for x in valid], .75)
            cls = percentile([x[2] for x in valid], .75)
            passed = (lcp is not None and inp is not None and cls is not None and
                      lcp <= args.max_lcp_ms and inp <= args.max_inp_ms and cls <= args.max_cls)
            if valid and not passed: threshold_failures += 1
            devices[device] = {"observations": len(valid), "p75": {
                "lcpMs": lcp, "inpMs": inp, "cls": cls}, "status": "pass" if passed else "fail"}
        surfaces_out.append({"id": ident, "url": url, "artifact": surface.get("artifact"),
                             "artifactSha256": str(surface.get("artifactSha256") or "").lower(),
                             "devices": devices})
    if len(surfaces_out) < args.min_surfaces:
        errors.append(f"needs >={args.min_surfaces} critical performance surfaces")
    nested_artifacts = artifact_claims(nested_artifacts, errors)
    thresholds = {"minSurfaces": args.min_surfaces, "minObservationsPerDevice": args.min_observations,
                  "minWindowDays": args.min_window_days, "maxLcpMsP75": args.max_lcp_ms,
                  "maxInpMsP75": args.max_inp_ms, "maxClsP75": args.max_cls,
                  "maxAgeDays": MAX_EVIDENCE_AGE_DAYS}
    status = "fail" if threshold_failures else "insufficient" if errors else "pass"
    if threshold_failures: errors.append(f"{threshold_failures} surface/device Core Web Vitals sets exceed good thresholds")
    return finish("performance", status, errors, warnings, {
        "inputDigests": {"observations": document_hash(doc)}, "artifacts": nested_artifacts,
        "observedAt": study.get("conductedAt"), "ageDays": study_age,
        "windowDays": study.get("windowDays"), "productionBuild": study.get("productionBuild"),
        "realUserMonitoring": study.get("realUserMonitoring"), "surfaces": surfaces_out}, thresholds)


def add_output(parser):
    parser.add_argument("--out", help="write JSON evidence (stdout when omitted)")


def bind_raw_inputs(result, raw_inputs, output_base):
    """Bind exact source JSON bytes to the portable output evidence bundle."""
    output_base = pathlib.Path(output_base).resolve()
    input_artifacts = []
    for role, source_path in raw_inputs:
        resolved = pathlib.Path(source_path).resolve()
        try:
            relative = resolved.relative_to(output_base).as_posix()
        except ValueError:
            result["errors"].append(
                f"raw {role} input must be contained by the output evidence directory")
            continue
        input_artifacts.append({"path": relative, "sha256": file_hash(resolved),
                                "kind": f"raw-{role}-input"})
    result["evidence"]["inputArtifacts"] = input_artifacts
    if len(input_artifacts) != len(raw_inputs) and result["status"] == "pass":
        result["status"] = "insufficient"
    return result


def selftest():
    class Args:
        min_cases = 100; min_positive = 50; min_negative = 40; min_labelers = 2
        min_precision_lower = .94; min_recall_lower = .94; max_cannot_tell = .05
        min_products = 12; min_reviewers = 3; min_alpha = .8; min_spearman_lower = .7
        min_concordance = .9; max_mae = 5; max_abs_bias = 3; max_error = 10
        min_score_span = 80; min_high_products = 2; min_low_products = 2
        min_high_score = 90; max_low_score = 20
        bootstrap = 1000; seed = 1729
        min_participants = 10; min_tasks = 3; min_attempts = 10; min_success_lower = .7
        min_combinations = 2
        min_structured = 3; min_random = 2; min_processes = 1
        min_surfaces = 3; min_observations = 100; min_window_days = 28
        max_lcp_ms = 2500; max_inp_ms = 200; max_cls = .1
    args = Args()
    digest = "a" * 64
    now = datetime.datetime.now(datetime.timezone.utc)
    now_stamp = now.isoformat()
    yesterday_stamp = (now - datetime.timedelta(days=1)).isoformat()
    labels = {"schema": SCHEMAS["detector-labels"], "datasetId": "heldout-v1",
              "labelsFrozenBeforePredictions": True, "frozenAt": yesterday_stamp,
              "labelers": ["r1", "r2"], "labelerProfiles": [
                  {"id": "r1", "affiliation": "studio-a", "yearsExperience": 6,
                   "expertise": ["visual-design"]},
                  {"id": "r2", "affiliation": "accessibility-lab", "yearsExperience": 5,
                   "expertise": ["accessibility"]}], "items": []}
    predictions = {"schema": SCHEMAS["detector-predictions"], "datasetId": "heldout-v1",
                   "producer": "rig", "generatedAt": now_stamp, "items": []}
    for i in range(110):
        expected = "positive" if i < 70 else "negative"
        labels["items"].append({"id": f"case-{i}", "rule": f"rule-{i % 5}",
            "expected": expected, "split": "holdout", "sourceSha256": digest,
            "sourceArtifact": f"detector-cases/case-{i}.html",
            "labels": [{"reviewer": "r1", "outcome": expected},
                       {"reviewer": "r2", "outcome": expected}]})
        predictions["items"].append({"id": f"case-{i}", "outcome": expected})
    detector = detector_gate(labels, predictions, args)
    ratings = {"schema": SCHEMAS["ratings"], "ratingsBlindToToolScore": True,
               "study": {"coordinator": "researcher", "toolVersion": "fixture-1",
                         "protocolSha256": digest, "conductedAt": now_stamp},
               "reviewers": ["r1", "r2", "r3"],
               "reviewerProfiles": [
                   {"id": "r1", "affiliation": "studio-a", "yearsExperience": 8,
                    "expertise": ["product-design"]},
                   {"id": "r2", "affiliation": "studio-b", "yearsExperience": 6,
                    "expertise": ["accessibility"]},
                   {"id": "r3", "affiliation": "studio-c", "yearsExperience": 5,
                    "expertise": ["product-design", "accessibility"]}],
               "strata": {"productCategories": ["commerce", "content", "enterprise"],
                           "surfaceTypes": ["marketing", "workflow", "settings"],
                           "qualityBands": ["low", "mid", "high"],
                           "viewportClasses": ["mobile", "desktop"]},
               "products": [{"id": f"p{i}", "artifact": f"expert-products/p{i}.png",
                 "artifactSha256": digest, "toolScore": i * 9,
                 "strata": {"productCategory": ["commerce", "content", "enterprise"][i % 3],
                            "surfaceType": ["marketing", "workflow", "settings"][i % 3],
                            "qualityBand": "low" if i < 4 else "mid" if i < 8 else "high",
                            "viewportClass": "mobile" if i % 2 else "desktop"},
                 "ratings": [{"reviewer": "r1", "score": max(0, i * 9 - 1)},
                             {"reviewer": "r2", "score": i * 9},
                             {"reviewer": "r3", "score": min(100, i * 9 + 1)}]}
                            for i in range(12)]}
    rating = ratings_gate(ratings, args)
    participants = [f"u{i}" for i in range(10)]
    usability = {"schema": SCHEMAS["usability"],
                 "study": {"facilitator": "researcher", "productVersion": "fixture-1",
                    "recruitmentScope": "representative target users", "conductedAt": now_stamp,
                    "protocolSha256": digest, "productArtifactSha256": digest,
                    "samplingPlanSha256": digest,
                    "protocolArtifact": "usability/protocol.md",
                    "productArtifact": "products/fixture.html",
                    "samplingPlanArtifact": "sampling/plan.json"},
                 "participants": participants,
                 "tasks": [{"id": f"task-{t}", "essentialFunction": f"function-{t}",
                     "protocolTaskSha256": digest,
                     "protocolTaskArtifact": f"usability/task-{t}.md", "attempts": [
                     {"participant": p, "completed": True, "criticalError": False}
                     for p in participants]} for t in range(3)]}
    usability_result = usability_gate(usability, args)
    at_doc = {"schema": SCHEMAS["assistive-tech"], "tester": "qualified-tester",
              "reviewedAt": now_stamp, "productArtifactSha256": digest,
              "protocolSha256": digest, "samplingPlanSha256": digest,
              "protocolArtifact": "at/protocol.md", "productArtifact": "products/fixture.html",
              "samplingPlanArtifact": "sampling/plan.json",
              "observations": []}
    for task in range(3):
        for tech, browser, platform in (("NVDA", "Firefox", "Windows"),
                                        ("VoiceOver", "Safari", "macOS")):
            at_doc["observations"].append({"task": f"task-{task}", "at": tech,
                "taskProtocolSha256": digest,
                "taskProtocolArtifact": f"at/task-{task}.md",
                "atVersion": "test", "browser": browser, "browserVersion": "test",
                "platform": platform, "expected": "named control", "observed": "named control",
                "outcome": "pass", "artifact": f"{tech}-{task}.md", "artifactSha256": digest})
    at_result = at_gate(at_doc, args)
    sampling = {"schema": SCHEMAS["sampling"], "author": "evaluator",
        "createdAt": now_stamp,
        "scope": {"product": "fixture", "version": "1", "baseUrl": "https://example.test",
                  "conformanceTarget": "WCAG 2.2 AA"},
        "pageTypes": ["dashboard", "form"], "essentialFunctions": ["review", "submit"],
        "technologies": ["HTML", "CSS", "JavaScript"],
        "randomSelection": {"method": "simple-random", "seed": "fixture-seed",
                            "populationSize": 20, "selectedIds": ["random-1", "random-2"]},
        "samples": [
            {"id": "dashboard", "selection": "structured", "url": "/dashboard",
             "artifact": "samples/dashboard.html", "artifactSha256": digest,
             "rationale": "primary review function",
             "pageTypes": ["dashboard"], "functions": ["review"]},
            {"id": "form", "selection": "structured", "url": "/form",
             "artifact": "samples/form.html", "artifactSha256": digest,
             "rationale": "primary submission function",
             "pageTypes": ["form"], "functions": ["submit"]},
            {"id": "state", "selection": "structured", "url": "/dashboard?state=empty",
             "artifact": "samples/state.html", "artifactSha256": digest,
             "rationale": "representative empty state",
             "pageTypes": ["dashboard"], "functions": ["review"]},
            {"id": "random-1", "selection": "random", "url": "/one",
             "artifact": "samples/random-1.html", "artifactSha256": digest,
             "pageTypes": [], "functions": []},
            {"id": "random-2", "selection": "random", "url": "/two",
             "artifact": "samples/random-2.html", "artifactSha256": digest,
             "pageTypes": [], "functions": []}],
        "completeProcesses": [{"name": "review and submit", "steps": [
            {"sampleId": "dashboard", "action": "review"},
            {"sampleId": "form", "action": "submit"}]}]}
    sampling_result = sampling_gate(sampling, args)
    performance = {"schema": SCHEMAS["performance"], "study": {
        "collector": "rum-pipeline", "productVersion": "fixture-1", "conductedAt": now_stamp,
        "productionBuild": True, "realUserMonitoring": True, "windowDays": 28,
        "samplingPlanArtifact": "sampling/plan.json", "samplingPlanSha256": digest,
        "environmentArtifact": "performance/environment.json", "environmentSha256": digest},
        "surfaces": [{"id": f"surface-{surface}", "url": f"https://example.test/{surface}",
            "artifact": f"performance/surface-{surface}.json", "artifactSha256": digest,
            "observations": [{"device": device, "lcpMs": 1800, "inpMs": 120, "cls": .05}
                for device in ("mobile", "desktop") for _ in range(100)]}
            for surface in range(3)]}
    performance_result = performance_gate(performance, args)
    failures = []
    for name, result in (("detectors", detector), ("ratings", rating),
                         ("usability", usability_result), ("assistive-tech", at_result),
                         ("sampling", sampling_result), ("performance", performance_result)):
        if result["status"] != "pass": failures.append(f"valid {name} rejected: {result['errors']}")
    bad_predictions = json.loads(json.dumps(predictions)); bad_predictions["items"][99]["outcome"] = "positive"
    if detector_gate(labels, bad_predictions, args)["status"] != "fail":
        failures.append("detector false positive was accepted")
    leaked = json.loads(json.dumps(predictions)); leaked["producer"] = "r1"
    if detector_gate(labels, leaked, args)["status"] != "fail":
        failures.append("labeler-produced predictions were accepted")
    same_labeler_team = json.loads(json.dumps(labels))
    for profile in same_labeler_team["labelerProfiles"]: profile["affiliation"] = "same-team"
    if detector_gate(same_labeler_team, predictions, args)["status"] == "pass":
        failures.append("single-affiliation labeler panel was accepted as independent")
    disputed = json.loads(json.dumps(labels)); disputed["items"][0]["labels"][1]["outcome"] = "negative"
    if detector_gate(disputed, predictions, args)["status"] != "fail":
        failures.append("disputed detector consensus was accepted")
    one_sided = json.loads(json.dumps(labels))
    for item in one_sided["items"]:
        if item["rule"] == "rule-0" and item["expected"] != "positive":
            item["rule"] = "negative-only-rule"
    if detector_gate(one_sided, predictions, args)["status"] == "pass":
        failures.append("detector rules without positive and negative coverage were accepted")
    weak_detector = Args(); weak_detector.min_cases = 1
    if detector_gate(labels, predictions, weak_detector)["status"] == "pass":
        failures.append("weakened detector policy was accepted")
    unblinded = json.loads(json.dumps(ratings)); unblinded["ratingsBlindToToolScore"] = False
    if ratings_gate(unblinded, args)["status"] != "fail":
        failures.append("unblinded expert ratings were accepted")
    one_affiliation = json.loads(json.dumps(ratings))
    for profile in one_affiliation["reviewerProfiles"]: profile["affiliation"] = "same-team"
    if ratings_gate(one_affiliation, args)["status"] == "pass":
        failures.append("single-affiliation expert panel was accepted as independent")
    uncorrelated = json.loads(json.dumps(ratings))
    for i, product in enumerate(uncorrelated["products"]): product["toolScore"] = (i * 37) % 101
    if ratings_gate(uncorrelated, args)["status"] == "pass":
        failures.append("uncorrelated expert/tool scores were accepted")
    inflated = json.loads(json.dumps(ratings))
    for product in inflated["products"]:
        product["toolScore"] = min(100, product["toolScore"] + 15)
    if ratings_gate(inflated, args)["status"] == "pass":
        failures.append("systematically inflated but correlated scores were accepted")
    homogeneous = json.loads(json.dumps(ratings))
    for product in homogeneous["products"]:
        product["strata"] = {"productCategory": "commerce", "surfaceType": "marketing",
                             "qualityBand": "mid", "viewportClass": "desktop"}
    if ratings_gate(homogeneous, args)["status"] == "pass":
        failures.append("homogeneous expert-rating product sets were accepted")
    bad_usability = json.loads(json.dumps(usability)); bad_usability["tasks"][0]["attempts"][0]["criticalError"] = True
    if usability_gate(bad_usability, args)["status"] != "fail":
        failures.append("critical usability error was accepted")
    duplicate_task = json.loads(json.dumps(usability)); duplicate_task["tasks"].append(duplicate_task["tasks"][0])
    if usability_gate(duplicate_task, args)["status"] == "pass":
        failures.append("duplicate usability task ids were accepted")
    stale_usability = json.loads(json.dumps(usability))
    stale_usability["study"]["conductedAt"] = "2000-01-01T00:00:00Z"
    if usability_gate(stale_usability, args)["status"] == "pass":
        failures.append("stale usability observations were accepted")
    bad_at = json.loads(json.dumps(at_doc)); bad_at["observations"][0]["outcome"] = "fail"
    if at_gate(bad_at, args)["status"] != "fail":
        failures.append("failed AT observation was accepted")
    escaping_at = json.loads(json.dumps(at_doc)); escaping_at["observations"][0]["artifact"] = "../outside.md"
    if at_gate(escaping_at, args)["status"] == "pass":
        failures.append("escaping nested AT artifact path was accepted")
    one_stack = json.loads(json.dumps(at_doc))
    for obs in one_stack["observations"]:
        if obs["at"] == "VoiceOver":
            obs.update({"at": "NVDA", "atVersion": "other", "browser": "Firefox",
                        "browserVersion": "other", "platform": "Windows"})
    if at_gate(one_stack, args)["status"] == "pass":
        failures.append("two versions of one AT stack were accepted as breadth")
    bad_sampling = json.loads(json.dumps(sampling)); bad_sampling["samples"] = bad_sampling["samples"][:2]
    if sampling_gate(bad_sampling, args)["status"] == "pass":
        failures.append("unrepresentative surface sample was accepted")
    fake_exhaustive = json.loads(json.dumps(sampling)); fake_exhaustive["exhaustive"] = True
    if sampling_gate(fake_exhaustive, args)["status"] == "pass":
        failures.append("exhaustive sampling without a pinned inventory was accepted")
    fake_random = json.loads(json.dumps(sampling)); del fake_random["randomSelection"]
    if sampling_gate(fake_random, args)["status"] == "pass":
        failures.append("unreproducible random sampling was accepted")
    slow_performance = json.loads(json.dumps(performance))
    for row in slow_performance["surfaces"][0]["observations"]:
        if row["device"] == "mobile": row["lcpMs"] = 3000
    if performance_gate(slow_performance, args)["status"] != "fail":
        failures.append("failing production field performance was accepted")
    import tempfile
    with tempfile.TemporaryDirectory(prefix="dd-evidence-input-") as tmp:
        root = pathlib.Path(tmp); bundle = root / "bundle"; bundle.mkdir()
        inside = bundle / "ratings.json"; inside.write_text("{}")
        outside = root / "outside.json"; outside.write_text("{}")
        template = finish("ratings", "pass", [], [], {}, {})
        if bind_raw_inputs(template, [("ratings", inside)], bundle)["status"] != "pass":
            failures.append("contained raw evidence input was rejected")
        template = finish("ratings", "pass", [], [], {}, {})
        if bind_raw_inputs(template, [("ratings", outside)], bundle)["status"] == "pass":
            failures.append("raw evidence input outside the output bundle was accepted")
    if failures:
        print("evidence-gates selftest FAILED:\n  " + "\n  ".join(failures)); return 1
    print("evidence-gates selftest ok - six valid evidence types pass; weakened policy, stale evidence, leakage, one-sided rules, homogeneous or biased ratings, duplicate tasks, unbundled raw inputs, unpinned or escaping artifacts, critical usability/AT failures and poor field vitals are rejected")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)
    det = sub.add_parser("detectors")
    det.add_argument("--labels", required=True); det.add_argument("--predictions", required=True)
    det.add_argument("--min-cases", type=int, default=100)
    det.add_argument("--min-positive", type=int, default=50); det.add_argument("--min-negative", type=int, default=40)
    det.add_argument("--min-labelers", type=int, default=2)
    det.add_argument("--min-precision-lower", type=float, default=.94)
    det.add_argument("--min-recall-lower", type=float, default=.94)
    det.add_argument("--max-cannot-tell", type=float, default=.05); add_output(det)
    rat = sub.add_parser("ratings"); rat.add_argument("--input", required=True)
    rat.add_argument("--min-products", type=int, default=12); rat.add_argument("--min-reviewers", type=int, default=3)
    rat.add_argument("--min-alpha", type=float, default=.8); rat.add_argument("--min-spearman-lower", type=float, default=.7)
    rat.add_argument("--min-concordance", type=float, default=.9)
    rat.add_argument("--max-mae", type=float, default=5)
    rat.add_argument("--max-abs-bias", type=float, default=3)
    rat.add_argument("--max-error", type=float, default=10)
    rat.add_argument("--min-score-span", type=float, default=80)
    rat.add_argument("--min-high-products", type=int, default=2)
    rat.add_argument("--min-low-products", type=int, default=2)
    rat.add_argument("--min-high-score", type=float, default=90)
    rat.add_argument("--max-low-score", type=float, default=20)
    rat.add_argument("--bootstrap", type=int, default=4000); rat.add_argument("--seed", type=int, default=1729); add_output(rat)
    usa = sub.add_parser("usability"); usa.add_argument("--input", required=True)
    usa.add_argument("--min-participants", type=int, default=10); usa.add_argument("--min-tasks", type=int, default=3)
    usa.add_argument("--min-attempts", type=int, default=10); usa.add_argument("--min-success-lower", type=float, default=.7); add_output(usa)
    at = sub.add_parser("assistive-tech"); at.add_argument("--input", required=True)
    at.add_argument("--min-combinations", type=int, default=2); at.add_argument("--min-tasks", type=int, default=3); add_output(at)
    sam = sub.add_parser("sampling"); sam.add_argument("--input", required=True)
    sam.add_argument("--min-structured", type=int, default=3); sam.add_argument("--min-random", type=int, default=2)
    sam.add_argument("--min-processes", type=int, default=1); add_output(sam)
    perf = sub.add_parser("performance"); perf.add_argument("--input", required=True)
    perf.add_argument("--min-surfaces", type=int, default=3)
    perf.add_argument("--min-observations", type=int, default=100)
    perf.add_argument("--min-window-days", type=int, default=28)
    perf.add_argument("--max-lcp-ms", type=float, default=2500)
    perf.add_argument("--max-inp-ms", type=float, default=200)
    perf.add_argument("--max-cls", type=float, default=.1); add_output(perf)
    args = ap.parse_args()
    try:
        if args.mode == "detectors":
            result = detector_gate(load(args.labels), load(args.predictions), args)
            raw_inputs = [("labels", args.labels), ("predictions", args.predictions)]
        else:
            source = load(args.input)
            if args.mode == "ratings": result = ratings_gate(source, args)
            elif args.mode == "usability": result = usability_gate(source, args)
            elif args.mode == "assistive-tech": result = at_gate(source, args)
            elif args.mode == "sampling": result = sampling_gate(source, args)
            else: result = performance_gate(source, args)
            raw_inputs = [(args.mode, args.input)]
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr); return 2
    output_base = pathlib.Path(args.out).resolve().parent if args.out else pathlib.Path.cwd().resolve()
    bind_raw_inputs(result, raw_inputs, output_base)
    payload = json.dumps(result, indent=2) + "\n"
    if args.out:
        path = pathlib.Path(args.out); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(payload)
        print(f"{args.mode} evidence: {result['status']} -> {path}")
    else:
        print(payload, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
