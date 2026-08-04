#!/usr/bin/env python3
"""Deterministic scorer for designer-dude.

Two ways in:

  1. FINDINGS MODE (preferred) - derive every pillar grade from the confirmed
     findings, so a grade is a function of documented evidence:
       score.py --findings .design/findings-dashboard.json --slop B-
     Each pillar starts at A and is demoted by severity. Nothing is decided in
     anyone's head, which means the same evidence scores the same next week and
     a "run it again until it's 90+" campaign measures progress instead of mood.

  2. LETTERS MODE (back-compatible) - pass the twelve letters yourself:
       score.py --typography B- --hierarchy C ... --consistency B-

Both print the arithmetic, the composite, the four sub-scores, and a
ready-to-paste headline. Extras that matter for repeat runs:

  --target 90        exact cheapest path to a target score (which pillar
                     upgrades buy the most points per letter step)
  --provisional a,b  pillars whose evidence was NOT captured this run: they
                     are capped and labelled, never allowed to read as A
  --slop A           measured AI-slop grade; anything below A caps Overall at 97
  --wcag-fail        an unresolved WCAG 2.2 AA failure: caps Overall at C+
  --perf-unmeasured  Core Web Vitals were never measured on a production
                     build: caps Interaction & Performance at A-
  --baseline 78.5    prior overall; prints the delta and shouts on regression
  --json out.json    machine-readable scorecard for design-baseline.json
  --selftest         verify the grade tables and demotion maths are consistent

Findings can also carry CREDITS ("kind": "credit"), which is how a pillar
reaches A+. Demotion alone bounds a straight-A card at 92.00, so without
credits the top eight points of the scale are unreachable by construction and
"get this to 95" is a target no amount of work can satisfy. A credit is not a
compliment: it names an A+ criterion from scoring.md, carries evidence, cites
two or more surfaces, and only promotes a pillar that is otherwise defect-free.
"""

import argparse
import collections
import datetime
import hashlib
import json
import math
import os
import pathlib
import re
import sys
import tempfile


def normalize(x):
    """Kill binary-float noise before any flooring or band comparison.

    Without this a true 92.00 accumulates as 91.99999999999999, prints as
    (91), and a score sitting exactly on a band floor lands one band low.
    """
    return round(x, 6)


# Letter -> number. ROUND-TRIP STABLE against BANDS: feed any letter's value
# back through to_letter() and you get the same letter. An older table
# (A+=100, A=95, A-=91 ...) was not -- A- came back as A, and a card of
# straight A pillars averaged to 95 and printed A+. That inflation is silent
# and always upward, which is the worst direction for a skill whose whole
# value is not flattering the work. Edit these and you must edit BANDS too:
#   python3 score.py --selftest
#
# A+ = 100, not 97. A 0-100 scale whose maximum is 97 is a broken instrument:
# "get this to 98" is then unsatisfiable by any amount of real work, which
# teaches the user to ignore the number. 100 is reachable and deliberately
# brutal -- it needs an evidence-backed A+ credit on ALL ELEVEN pillars AND a
# measured slop grade of A or better (SLOP_GATE below), plus a current human
# certification whose artifacts exist and match their SHA-256 manifest. A=92
# still sits inside the A band, so the round-trip property holds.
GRADE_VALUES = {
    "A+": 100, "A": 92, "A-": 88, "A−": 88,
    "B+": 85, "B": 81, "B-": 78, "B−": 78,
    "C+": 75, "C": 71, "C-": 68, "C−": 68,
    "D": 63, "F": 50,
}

BANDS = [
    (95, "A+"), (90, "A"), (87, "A-"), (84, "B+"), (80, "B"), (77, "B-"),
    (74, "C+"), (70, "C"), (67, "C-"), (60, "D"), (0, "F"),
]

# Demotion in points on the same 0-100 scale the letters live on, so the
# arithmetic in scoring.md ("critical = a full letter, major = half, minor = a
# quarter") is executable rather than done in your head. A full letter is
# A(92) -> B(81) = 11 points.
FULL_LETTER = 11.0
SEVERITY_COST = {
    "critical": FULL_LETTER,
    "major": FULL_LETTER / 2,
    "minor": FULL_LETTER / 4,
    "petty": 0.0,
}
# Findings in these states are UNRESOLVED and still count against the grade.
# "deferred" counts: a defect nobody can fix from here is still a defect the
# user is shipping. Only "fixed" and "rejected" stop counting.
COUNTS_AGAINST = {"candidate", "confirmed", "open", "deferred", "best-effort"}
DOES_NOT_COUNT = {"fixed", "verified", "rejected", "false-positive", "no_change_needed"}

# Confirmed AA criteria produced by probe-report.py. Keeping the cap derivable
# from the findings ledger closes a dangerous workflow gap: a reviewer could
# confirm a critical WCAG row, forget the separate --wcag-fail switch, and
# still print an uncapped score. Candidates do not auto-cap because the probe's
# contract requires confirmation; confirmed/open/deferred defects do.
WCAG_AA_CRITERIA = {
    "1.1.1", "1.3.1", "1.3.5", "1.4.1", "1.4.3", "1.4.4", "1.4.11", "1.4.12",
    "1.4.13", "2.1.1", "2.4.1", "2.4.3", "2.4.7", "2.4.11", "2.5.3", "2.5.7", "2.5.8",
    "3.1.1", "3.1.2", "3.3.2", "3.3.7", "3.3.8", "4.1.2", "4.1.3",
}

PILLARS = [
    ("typography", "Typography", 15),
    ("hierarchy", "Visual Hierarchy", 15),
    ("spacing", "Spacing & Layout", 12),
    ("color", "Color & Contrast", 10),
    ("interaction", "Interaction & Performance", 10),
    ("content", "Content & Voice", 10),
    ("a11y", "Accessibility", 8),
    ("responsive", "Responsiveness", 7),
    ("craft", "Craft & Considered Details", 5),
    ("ia", "Information Architecture", 4),
    ("motion", "Motion", 4),
]
PILLAR_KEYS = [p[0] for p in PILLARS]
PILLAR_WEIGHT = {k: w for k, _, w in PILLARS}

# Pillars the probe cannot measure. In findings mode, "no findings" here means
# "nobody looked", not "it is perfect" -- so the script refuses to award them a
# silent A and demands an explicit letter. This is the single most important
# guard against a scorecard drifting upward across a long campaign.
EYE_ONLY = ["hierarchy", "ia", "content", "consistency"]

SUBSCORES = {
    "Craft": ["typography", "spacing", "color", "motion", "craft"],
    "Clarity": ["hierarchy", "interaction", "ia", "a11y"],
    # Brand Coherence deliberately does not reuse Typography - that is already
    # measured inside Craft. It pairs voice with the cross-page check.
    "Brand Coherence": ["content", "consistency"],
}

# The top three points of the scale are gated on MEASURED slop, not on
# credits alone. Credits are argued; the slop grade is computed by
# probe-report.py from the page itself, so it is the one input to the top band
# that a reviewer cannot talk itself into. Without a slop grade of A or better
# the composite stops at 97.00 -- an excellent card, but not a perfect one.
# Pass --slop <grade> from `probe-report.py ... | grep "AI Slop"`. Omitting it
# is not neutral: an unmeasured slop grade caps here too, because "grade only
# what you measured" applies hardest at the top of the scale.
SLOP_GATE_CAP = 97.0
SLOP_GATE_MIN = "A"

WCAG_CAP = 75          # C+, and it maps back to the C+ band
PROVISIONAL_CAP = 85   # B+: you cannot claim an A on evidence you did not capture
PERF_UNMEASURED_CAP = 88   # A-: half of Interaction is perf, and you did not measure it
CURRENCY_MAX_DAYS = 200

# ---------------- A+ criteria ----------------
#
# Why this table exists. Findings mode starts every pillar at A and only ever
# demotes, so the best a real product can score is a straight-A card = 92.00.
# That made the top eight points of the scale unreachable by construction: a
# team could build a bespoke type system with a genuine point of view and the
# scorer had no way to say so, while "get this to 95" was a target no amount of
# work could satisfy. The fix is NOT to hand out A+ when a gap needs closing --
# that is grading your own homework, and --target still refuses to schedule it.
# The fix is to make A+ falsifiable: a claim, against a named criterion, with
# evidence, on more than one surface, on a pillar carrying zero open defects.
#
# One criterion per pillar, deliberately. Each is a CONJUNCTION -- every clause
# must hold -- because a menu of alternatives is a menu of the easiest one.
# These are the source of truth; scoring.md quotes them at greater length.
A_PLUS_CRITERIA = {
    "typography": (
        "typography.voice-and-ratio",
        "A face chosen and self-hosted for its voice (never Inter/Roboto/Arial/"
        "system as the default that nobody picked), the scale on ONE ratio with "
        "no near-duplicate steps, and tabular numerals everywhere numbers align.",
    ),
    "hierarchy": (
        "hierarchy.singular-primary",
        "One primary action per surface, argued against what users come to that "
        "surface to do -- not merely tidy. The eye lands on the same element at "
        "every probed viewport, and the second and third stops are also intended.",
    ),
    "spacing": (
        "spacing.composed-grid",
        "A grid that is felt, not just obeyed: one base unit, 6-8 named steps, "
        "zero off-base values, and vertical rhythm that survives a long page and "
        "a dense table on the same screen.",
    ),
    "color": (
        "color.designed-dark-and-range",
        "Semantic roles in a perceptual space (oklch), a dark theme designed "
        "rather than inverted, accent under 10% of pixels, and no state that "
        "relies on colour alone. AAA on body text where the palette allows.",
    ),
    "interaction": (
        "interaction.states-and-vitals",
        "All seven states designed for every interactive element, configured "
        "status actions and custom widgets pass their behavioral contracts, and Core Web "
        "Vitals MEASURED inside budget on a production build (LCP <=2.5s, "
        "INP <=200ms, CLS <0.1). Observation is not a measurement.",
    ),
    "content": (
        "content.voice-with-a-point-of-view",
        "Copy that could only belong to this product: domain nouns in the user's "
        "vocabulary, empty states that name the next action, errors that name the "
        "field and the fix, and a voice a reader could recognise unlabelled.",
    ),
    "a11y": (
        "a11y.beyond-aa",
        "Zero AA failures, a clean manual keyboard pass including focus return, "
        "browser-confirmed Label in Name, no completely obscured focus, the 2.2 "
        "SCs most sites miss (2.4.11, 2.5.7, 2.5.8, 3.3.7, 3.3.8), and "
        "at least one thing done for assistive tech that no checker asked for.",
    ),
    "responsive": (
        "responsive.designed-breakpoints",
        "Each breakpoint is a layout decision with its own reason, tables have a "
        "real small-screen answer rather than a squeeze, 320px is as considered "
        "as 1440px, and applicable text-expansion/RTL stress adds no clipping or overflow.",
    ),
    "craft": (
        "craft.decided-details",
        "Every detail visibly answered a question: disciplined radius and shadow "
        "scales, one light source, deterministic sort on ties, aligned decimals, "
        "clean console, correct-DPR assets, stable visual/ARIA baselines, and no "
        "critical target-engine regression. Decided, not assembled.",
    ),
    "ia": (
        "ia.predictable-object-model",
        "A user can predict where a record lives before navigating there. Labels "
        "are the user's words, deep links survive a refresh, and depth beyond two "
        "levels is served by search.",
    ),
    "motion": (
        "motion.signature-moment",
        "Motion carries continuity or feedback throughout, honours "
        "prefers-reduced-motion completely, and the product has one moment "
        "someone would remember -- without animating a 200-row list.",
    ),
}
CREDIT_MIN_SURFACES = 2   # excellence claimed from a single page scores the page


def to_number(grade, where):
    key = str(grade).strip().upper().replace("−", "-")
    if key not in GRADE_VALUES:
        sys.exit(f"error: '{grade}' is not a valid grade for {where}. "
                 f"Valid: {', '.join(sorted(GRADE_VALUES))}")
    return GRADE_VALUES[key]


def to_letter(number):
    number = normalize(number)
    for floor, letter in BANDS:
        if number >= floor:
            return letter
    return "F"


def next_letter_up(letter):
    ladder = ["F", "D", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]
    key = letter.replace("−", "-")
    i = ladder.index(key) if key in ladder else 0
    return ladder[min(i + 1, len(ladder) - 1)]


# ---------------- findings mode ----------------

def credit_problems(entry, pillar):
    """Every reason this credit does not count. Empty list = it counts.

    Deliberately strict and deliberately mechanical. A credit is the only way
    the number goes UP on its own, so it is the one place where a generous
    reading turns the whole scorecard into a mirror.
    """
    problems = []
    criterion = (entry.get("criterion") or "").strip()
    expected = A_PLUS_CRITERIA.get(pillar, ("", ""))[0]
    if not criterion:
        problems.append(f"no 'criterion' (expected '{expected}')")
    elif criterion != expected:
        problems.append(f"criterion '{criterion}' is not {pillar}'s A+ criterion "
                        f"('{expected}')")
    if not str(entry.get("evidence") or "").strip():
        problems.append("no 'evidence' (probe path, measurement or screenshot)")
    surfaces = entry.get("surfaces") or []
    distinct_surfaces = ({str(s).strip() for s in surfaces if str(s).strip()}
                         if isinstance(surfaces, list) else set())
    if not isinstance(surfaces, list) or len(distinct_surfaces) < CREDIT_MIN_SURFACES:
        problems.append(f"needs 'surfaces' naming >={CREDIT_MIN_SURFACES} probed surfaces "
                        f"(got {len(distinct_surfaces)} distinct) -- "
                        f"excellence shown on one page scores the page")
    status = (entry.get("status") or "").strip().lower()
    if status != "verified":
        problems.append(f"status '{status or '(missing)'}' is not 'verified'")
    return problems


def credit_evidence_problems(entry, pillar, ledger_path):
    """Validate the bytes behind a verified A+ claim at every high score."""
    if str(entry.get("status") or "").strip().lower() != "verified":
        return []
    problems = []
    artifact = str(entry.get("evidence") or "").strip()
    pure = pathlib.PurePosixPath(artifact)
    if not artifact or pure.is_absolute() or ".." in pure.parts:
        return ["evidence must be a contained relative credit-evidence JSON path"]
    base = os.path.dirname(os.path.abspath(ledger_path))
    full = os.path.join(base, artifact)
    try:
        if os.path.commonpath([base, os.path.realpath(full)]) != base:
            return ["credit evidence resolves outside the findings bundle"]
        with open(full, encoding="utf8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        return [f"credit evidence is not readable JSON: {exc}"]
    expected = A_PLUS_CRITERIA.get(pillar, (None,))[0]
    if (not isinstance(doc, dict) or doc.get("schema") != "designer-dude-credit-evidence/v1" or
            doc.get("status") != "pass" or str(doc.get("pillar") or "") != pillar or
            str(doc.get("criterion") or "") != str(expected or "")):
        problems.append("credit evidence schema, pillar, criterion, or status does not match")
    if not str(doc.get("reviewer") or "").strip():
        problems.append("credit evidence reviewer is missing")
    try:
        stamp = datetime.datetime.fromisoformat(str(doc.get("reviewedAt") or "").replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=datetime.timezone.utc)
        age = (datetime.datetime.now(datetime.timezone.utc) - stamp.astimezone(datetime.timezone.utc)).days
        if age < -1 or age > 90:
            problems.append("credit evidence is stale or future-dated")
    except ValueError:
        problems.append("credit evidence reviewedAt is invalid")
    doc_surfaces = {str(x).strip() for x in doc.get("surfaces", []) if str(x).strip()}
    entry_surfaces = {str(x).strip() for x in entry.get("surfaces", []) if str(x).strip()}
    if len(doc_surfaces) < 2 or doc_surfaces != entry_surfaces:
        problems.append("credit evidence surfaces do not match the credit")
    observations = doc.get("observations")
    if not isinstance(observations, list) or not observations or any(not str(x).strip() for x in observations):
        problems.append("credit evidence observations are missing")
    records = doc.get("artifacts")
    if not isinstance(records, list) or not records:
        problems.append("credit evidence nested artifacts are missing")
    else:
        seen = set()
        for record in records:
            if not isinstance(record, dict):
                problems.append("credit evidence contains a non-object nested artifact")
                continue
            path = str(record.get("path") or "").strip()
            digest = str(record.get("sha256") or "").strip().lower()
            path_pure = pathlib.PurePosixPath(path)
            if (not path or path in seen or path_pure.is_absolute() or ".." in path_pure.parts or
                    not re.fullmatch(r"[0-9a-f]{64}", digest)):
                problems.append(f"credit evidence has an invalid nested artifact: {path or '(blank)'}")
                continue
            seen.add(path)
            nested = os.path.join(base, path)
            try:
                if os.path.commonpath([base, os.path.realpath(nested)]) != base or not os.path.isfile(nested):
                    problems.append(f"credit nested artifact is absent or outside the bundle: {path}")
                    continue
                actual = hashlib.sha256()
                with open(nested, "rb") as fh:
                    for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                        actual.update(chunk)
                if actual.hexdigest() != digest:
                    problems.append(f"credit nested artifact sha256 mismatch: {path}")
            except (OSError, ValueError) as exc:
                problems.append(f"credit nested artifact could not be verified: {path} ({exc})")
    return problems


PERFECTION_STATES = {
    "hover", "focus-visible", "active", "disabled", "loading", "empty", "error"
}


def perfection_certification_problems(doc, ledger_path=None, verify_artifacts=False):
    """Validate the human evidence automation cannot manufacture.

    Eleven credits prove that each pillar cleared its named conjunction. They
    do not prove that anybody reviewed the product as a whole, traversed more
    than a showcase route, or exercised the states a rest-state DOM probe
    cannot reach. The literal maximum therefore needs one deliberately
    inconvenient, current certification record in the SAME ledger. This is a
    schema check, not an assertion that the reviewer told the truth; its value
    is making the remaining human claim explicit, attributable and auditable.
    """
    cert = doc.get("perfectionCertification") if isinstance(doc, dict) else None
    if not isinstance(cert, dict):
        return ["missing perfectionCertification object"]
    problems = []
    if str(cert.get("status") or "").strip().lower() != "verified":
        problems.append("certification status is not 'verified'")
    if not str(cert.get("reviewer") or "").strip():
        problems.append("reviewer is missing")

    reviewed = str(cert.get("reviewedAt") or "").strip()
    if not reviewed:
        problems.append("reviewedAt is missing")
    else:
        try:
            stamp = datetime.datetime.fromisoformat(reviewed.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.timezone.utc)
            age = (now - stamp.astimezone(datetime.timezone.utc)).days
            if age > CURRENCY_MAX_DAYS:
                problems.append(f"reviewedAt is stale ({age} days; max {CURRENCY_MAX_DAYS})")
            if age < -1:
                problems.append("reviewedAt is in the future")
        except ValueError:
            problems.append("reviewedAt is not an ISO-8601 date")

    surfaces = cert.get("surfaces") or []
    distinct_surfaces = ({str(s).strip() for s in surfaces if str(s).strip()}
                         if isinstance(surfaces, list) else set())
    if len(distinct_surfaces) < 3:
        problems.append(f"needs >=3 distinct reviewed surfaces (got {len(distinct_surfaces)})")

    viewports = cert.get("viewports") or []
    distinct_viewports = ({str(v).strip() for v in viewports if str(v).strip()}
                          if isinstance(viewports, list) else set())
    widths = []
    for value in distinct_viewports:
        match = re.search(r"(?<!\d)(\d{3,4})\s*[x×]", value.lower())
        if match:
            widths.append(int(match.group(1)))
    if len(distinct_viewports) < 3 or not widths or min(widths) > 390 or max(widths) < 1280:
        problems.append("viewports need >=3 distinct captures spanning <=390px through >=1280px")

    states = cert.get("states") or []
    got_states = ({str(s).strip().lower() for s in states if str(s).strip()}
                  if isinstance(states, list) else set())
    missing_states = sorted(PERFECTION_STATES - got_states)
    if missing_states:
        problems.append("states not verified: " + ", ".join(missing_states))

    evidence = cert.get("evidence") or []
    distinct_evidence = ({str(e).strip() for e in evidence if str(e).strip()}
                         if isinstance(evidence, list) else set())
    if len(distinct_evidence) < 3:
        problems.append(f"needs >=3 distinct visual evidence artifacts (got {len(distinct_evidence)})")

    aria_evidence = cert.get("ariaSnapshotEvidence") or []
    distinct_aria = ({str(e).strip() for e in aria_evidence if str(e).strip()}
                     if isinstance(aria_evidence, list) else set())
    if len(distinct_aria) < 3:
        problems.append(f"needs >=3 distinct accessibility-tree artifacts (got {len(distinct_aria)})")

    processes = cert.get("completeProcesses") or []
    valid_processes = 0
    if isinstance(processes, list):
        for process in processes:
            if not isinstance(process, dict):
                continue
            steps = process.get("steps") or []
            if (str(process.get("status") or "").strip().lower() == "verified" and
                    str(process.get("name") or "").strip() and
                    isinstance(steps, list) and len({str(s).strip() for s in steps if str(s).strip()}) >= 2 and
                    str(process.get("evidence") or "").strip()):
                valid_processes += 1
    if valid_processes < 1:
        problems.append("needs >=1 verified complete process with 2+ steps and evidence")

    for key, label in (("keyboardReview", "keyboard review"),
                       ("assistiveTechReview", "assistive-technology review")):
        review = cert.get(key)
        if not isinstance(review, dict):
            problems.append(f"{label} is missing")
            continue
        if str(review.get("status") or "").strip().lower() != "verified":
            problems.append(f"{label} status is not 'verified'")
        if not str(review.get("evidence") or "").strip():
            problems.append(f"{label} evidence is missing")

    # The last two points cannot rest on a human sentence that the page was
    # "thoroughly checked". Require the executable layers added by the skill:
    # detector validation, configured behavior, i18n stress, target-engine
    # coverage, and stable visual/ARIA regression evidence. Applicability is
    # explicit: a product may genuinely have no RTL locale or custom widgets,
    # but "not-applicable" costs a reason and evidence of the declared scope.
    validation = cert.get("validationEvidence")
    if not isinstance(validation, dict):
        problems.append("validationEvidence is missing")
    else:
        if str(validation.get("status") or "").lower() != "verified":
            problems.append("validationEvidence status is not 'verified'")
        for key in ("recall", "precision", "mutations", "pipeline"):
            value = str(validation.get(key) or "")
            match = re.fullmatch(r"(\d+)\s*/\s*(\d+)", value)
            if not match or int(match.group(2)) < 1 or match.group(1) != match.group(2):
                problems.append(f"validationEvidence.{key} must be a complete non-zero pass ratio")
        if not str(validation.get("evidence") or "").strip():
            problems.append("validationEvidence evidence is missing")

    def evidence_review(key, label, checks=()):
        review = cert.get(key)
        if not isinstance(review, dict):
            problems.append(f"{label} is missing")
            return
        if str(review.get("status") or "").strip().lower() != "verified":
            problems.append(f"{label} status is not 'verified'")
        if not str(review.get("evidence") or "").strip():
            problems.append(f"{label} evidence is missing")
        for check in checks:
            item = review.get(check)
            if not isinstance(item, dict):
                problems.append(f"{label}.{check} is missing")
                continue
            state = str(item.get("status") or "").strip().lower()
            if state not in {"verified", "not-applicable"}:
                problems.append(f"{label}.{check} status must be verified or not-applicable")
            if state == "not-applicable" and not str(item.get("reason") or "").strip():
                problems.append(f"{label}.{check} needs a reason when not-applicable")

    evidence_review("behavioralReview", "behavioral review",
                    ("focusSweep", "accessibleNames", "labelInName", "statusAnnouncements", "widgetContracts",
                     "accessibleAuthentication", "dragAlternatives", "redundantEntry"))
    evidence_review("internationalizationReview", "internationalization review",
                    ("textExpansion", "rtl", "localeProfiles"))
    evidence_review("artifactRegression", "artifact regression",
                    ("visual", "aria"))
    evidence_review("representativeSampling", "representative sampling")
    evidence_review("usabilityReview", "usability review")
    evidence_review("performanceReview", "performance review")
    evidence_review("calibrationSnapshot", "calibration snapshot")

    method = cert.get("methodValidation")
    if not isinstance(method, dict):
        problems.append("method validation is missing")
    else:
        if str(method.get("status") or "").strip().lower() != "verified":
            problems.append("method validation status is not 'verified'")
        for key, label in (("detectorBenchmark", "detector benchmark"),
                           ("actBenchmark", "W3C ACT benchmark"),
                           ("expertCorrelation", "expert-score correlation")):
            item = method.get(key)
            if not isinstance(item, dict):
                problems.append(f"method validation.{key} is missing")
            else:
                if str(item.get("status") or "").strip().lower() != "verified":
                    problems.append(f"{label} status is not 'verified'")
                if not str(item.get("evidence") or "").strip():
                    problems.append(f"{label} evidence is missing")

    cross_engine = cert.get("crossEngineReview")
    if not isinstance(cross_engine, dict):
        problems.append("cross-engine review is missing")
    else:
        cross_status = str(cross_engine.get("status") or "").strip().lower()
        if cross_status != "verified":
            problems.append("cross-engine review status must be verified for perfection")
        if cross_status == "verified":
            engines = {str(x).strip().lower() for x in (cross_engine.get("engines") or [])}
            if not {"chromium", "firefox", "webkit"}.issubset(engines):
                problems.append("cross-engine review needs Chromium, Firefox and WebKit")
        if not str(cross_engine.get("evidence") or "").strip():
            problems.append("cross-engine review evidence is missing")

    # Every evidence reference must be content-addressed. Merely naming
    # "dashboard.png" proves nothing: the file can be absent, replaced after
    # review, or point at a different run. Hashes make the certification
    # reproducible and let a later scorer detect stale evidence rather than
    # trusting the ledger's prose.
    referenced = set(distinct_evidence) | set(distinct_aria)
    credit_records = []
    findings = doc.get("findings") if isinstance(doc, dict) else []
    for finding in findings if isinstance(findings, list) else []:
        if not isinstance(finding, dict):
            continue
        is_credit = (str(finding.get("kind") or "").strip().lower() == "credit" or
                     str(finding.get("severity") or "").strip().lower() == "credit")
        if is_credit and str(finding.get("status") or "").strip().lower() == "verified":
            credit_records.append(finding)
            if str(finding.get("evidence") or "").strip():
                referenced.add(str(finding["evidence"]).strip())
    for key in ("keyboardReview", "assistiveTechReview"):
        review = cert.get(key)
        if isinstance(review, dict) and str(review.get("evidence") or "").strip():
            referenced.add(str(review["evidence"]).strip())
    if isinstance(processes, list):
        for process in processes:
            if isinstance(process, dict) and str(process.get("evidence") or "").strip():
                referenced.add(str(process["evidence"]).strip())
    for key in ("validationEvidence", "behavioralReview", "internationalizationReview",
                "crossEngineReview", "artifactRegression", "representativeSampling",
                "usabilityReview", "performanceReview", "calibrationSnapshot"):
        review = cert.get(key)
        if isinstance(review, dict) and str(review.get("evidence") or "").strip():
            referenced.add(str(review["evidence"]).strip())
    if isinstance(method, dict):
        for key in ("detectorBenchmark", "actBenchmark", "expertCorrelation"):
            item = method.get(key)
            if isinstance(item, dict) and str(item.get("evidence") or "").strip():
                referenced.add(str(item["evidence"]).strip())

    manifest = cert.get("artifactManifest") or []
    indexed = {}
    if not isinstance(manifest, list):
        problems.append("artifactManifest is not a list")
    else:
        for entry in manifest:
            if not isinstance(entry, dict):
                problems.append("artifactManifest contains a non-object entry")
                continue
            artifact = str(entry.get("path") or "").strip()
            digest = str(entry.get("sha256") or "").strip().lower()
            if not artifact:
                problems.append("artifactManifest entry has no path")
                continue
            pure = pathlib.PurePosixPath(artifact)
            if pure.is_absolute() or ".." in pure.parts:
                problems.append(f"artifactManifest path is not portable or contained: '{artifact}'")
                continue
            if artifact in indexed:
                problems.append(f"artifactManifest repeats '{artifact}'")
                continue
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                problems.append(f"artifactManifest has invalid sha256 for '{artifact}'")
                continue
            indexed[artifact] = digest
    missing_manifest = sorted(referenced - set(indexed))
    if missing_manifest:
        problems.append("evidence missing from artifactManifest: " + ", ".join(missing_manifest))

    if verify_artifacts:
        if not ledger_path:
            problems.append("cannot verify artifacts without the findings-ledger path")
        else:
            base = os.path.dirname(os.path.abspath(ledger_path))
            for artifact in sorted(referenced & set(indexed)):
                full = os.path.join(base, artifact)
                try:
                    if os.path.commonpath([base, os.path.realpath(full)]) != base:
                        problems.append(f"artifact resolves outside evidence bundle: {artifact}")
                        continue
                except ValueError:
                    problems.append(f"artifact resolves outside evidence bundle: {artifact}")
                    continue
                if not os.path.isfile(full):
                    problems.append(f"artifact does not exist: {artifact}")
                    continue
                try:
                    actual = hashlib.sha256()
                    with open(full, "rb") as fh:
                        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                            actual.update(chunk)
                    if actual.hexdigest() != indexed[artifact]:
                        problems.append(f"artifact sha256 mismatch: {artifact}")
                except OSError as exc:
                    problems.append(f"artifact could not be read: {artifact} ({exc})")

            def load_artifact_json(artifact, label):
                artifact = str(artifact or "").strip()
                if not artifact:
                    return None
                pure = pathlib.PurePosixPath(artifact)
                if pure.is_absolute() or ".." in pure.parts:
                    problems.append(f"{label} evidence path is not portable or contained: {artifact}")
                    return None
                full = os.path.join(base, artifact)
                try:
                    if os.path.commonpath([base, os.path.realpath(full)]) != base:
                        problems.append(f"{label} evidence resolves outside evidence bundle: {artifact}")
                        return None
                except ValueError:
                    problems.append(f"{label} evidence resolves outside evidence bundle: {artifact}")
                    return None
                try:
                    with open(full) as fh:
                        return json.load(fh)
                except (OSError, ValueError) as exc:
                    problems.append(f"{label} evidence is not readable JSON: {artifact} ({exc})")
                    return None

            def load_evidence_json(section, label):
                ref = cert.get(section) if isinstance(cert.get(section), dict) else {}
                return load_artifact_json(ref.get("evidence"), label)

            def dig(doc, *path, default=None):
                cur = doc
                for part in path:
                    if not isinstance(cur, dict) or part not in cur:
                        return default
                    cur = cur[part]
                return cur

            def check_source_freshness(payload, thresholds, label):
                max_age = thresholds.get("maxAgeDays")
                if not isinstance(max_age, (int, float)) or not 0 <= max_age <= 90:
                    problems.append(f"{label} evidence weakens or omits the source-age threshold")
                    return
                try:
                    stamp = datetime.datetime.fromisoformat(
                        str(payload.get("observedAt") or "").replace("Z", "+00:00"))
                    if stamp.tzinfo is None:
                        stamp = stamp.replace(tzinfo=datetime.timezone.utc)
                    actual_age = (datetime.datetime.now(datetime.timezone.utc) -
                                  stamp.astimezone(datetime.timezone.utc)).days
                    if actual_age < -1 or actual_age > max_age or payload.get("ageDays") != actual_age:
                        problems.append(f"{label} evidence source date is stale, future, or inconsistent")
                except ValueError:
                    problems.append(f"{label} evidence has no valid source observation date")

            def verify_nested_artifacts(payload, label, field="artifacts"):
                records = payload.get(field) if isinstance(payload, dict) else None
                if not isinstance(records, list) or not records:
                    problems.append(f"{label} evidence has no {field} bundle")
                    return {}
                seen_nested = set()
                bundled = {}
                for record in records:
                    if not isinstance(record, dict):
                        problems.append(f"{label} nested artifact bundle contains a non-object")
                        continue
                    artifact = str(record.get("path") or "").strip()
                    digest = str(record.get("sha256") or "").strip().lower()
                    if field == "inputArtifacts" and not str(record.get("kind") or "").startswith("raw-"):
                        problems.append(f"{label} raw input artifact has no input role")
                    pure = pathlib.PurePosixPath(artifact)
                    if (not artifact or pure.is_absolute() or ".." in pure.parts or
                            not re.fullmatch(r"[0-9a-f]{64}", digest)):
                        problems.append(f"{label} has an unsafe or invalid nested artifact: {artifact or '(blank)'}")
                        continue
                    if artifact in seen_nested:
                        problems.append(f"{label} repeats nested artifact: {artifact}")
                        continue
                    seen_nested.add(artifact)
                    bundled[artifact] = digest
                    if indexed.get(artifact) != digest:
                        problems.append(f"{label} nested artifact is absent or mismatched in artifactManifest: {artifact}")
                        continue
                    full = os.path.join(base, artifact)
                    try:
                        if os.path.commonpath([base, os.path.realpath(full)]) != base:
                            problems.append(f"{label} nested artifact resolves outside evidence bundle: {artifact}")
                            continue
                    except ValueError:
                        problems.append(f"{label} nested artifact resolves outside evidence bundle: {artifact}")
                        continue
                    if not os.path.isfile(full):
                        problems.append(f"{label} nested artifact does not exist: {artifact}")
                        continue
                    try:
                        actual = hashlib.sha256()
                        with open(full, "rb") as fh:
                            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                                actual.update(chunk)
                        if actual.hexdigest() != digest:
                            problems.append(f"{label} nested artifact sha256 mismatch: {artifact}")
                    except OSError as exc:
                        problems.append(f"{label} nested artifact could not be read: {artifact} ({exc})")
                return bundled

            validation_doc = load_evidence_json("validationEvidence", "validation")
            if validation_doc is not None:
                if validation_doc.get("status") != "pass":
                    problems.append("validation evidence status is not pass")
                ratios = validation_doc.get("ratios") or {}
                for key in ("recall", "precision", "mutations", "pipeline"):
                    if str(ratios.get(key)) != str(validation.get(key)):
                        problems.append(f"validation evidence ratio mismatch for {key}")

            artifact_doc = load_evidence_json("artifactRegression", "artifact regression")
            if artifact_doc is not None and artifact_doc.get("status") != "pass":
                problems.append("artifact regression evidence status is not pass")

            cross_doc = load_evidence_json("crossEngineReview", "cross-engine")
            if cross_doc is not None and isinstance(cross_engine, dict) and cross_status == "verified":
                requested = {str(x).lower() for x in cross_doc.get("enginesRequested", [])}
                required = {"chromium", "firefox", "webkit"}
                if not required.issubset(requested):
                    problems.append("cross-engine evidence did not request all three engines")
                if cross_doc.get("regressions"):
                    problems.append("cross-engine evidence contains invariant regressions")
                surfaces_e = cross_doc.get("surfacesRequested") or []
                viewports_e = cross_doc.get("viewportsRequested") or []
                ran = {(x.get("engine"), x.get("surface"), x.get("viewport"))
                       for x in cross_doc.get("results", []) if x.get("status") == "ran"}
                missing_runs = [(e, s, v) for e in required for s in surfaces_e for v in viewports_e
                                if (e, s, v) not in ran]
                if missing_runs:
                    problems.append(f"cross-engine evidence misses {len(missing_runs)} requested runs")

            behavior_doc = load_evidence_json("behavioralReview", "behavioral")
            if behavior_doc is not None:
                behavior_payload = behavior_doc.get("behavioralEvidence") or {}
                check_to_payload = {
                    "statusAnnouncements": "announcements", "widgetContracts": "widgets",
                    "accessibleAuthentication": "authentication", "dragAlternatives": "dragAlternatives",
                    "redundantEntry": "redundantEntries",
                }
                behavior_review = cert.get("behavioralReview") or {}
                for check, payload_key in check_to_payload.items():
                    state = str((behavior_review.get(check) or {}).get("status") or "").lower()
                    if state != "verified":
                        continue
                    entries = behavior_payload.get(payload_key) or []
                    if not entries or any(x.get("status") != "verified" for x in entries):
                        problems.append(f"behavioral evidence does not verify {check}")
                runs = behavior_doc.get("runs") or []
                if str((behavior_review.get("focusSweep") or {}).get("status") or "").lower() == "verified":
                    focus = [dig(r, "interaction", "focusRing", default={}) or {} for r in runs]
                    if not focus or any(x.get("completelyObscured", 0) or not x.get("tested", 0) for x in focus):
                        problems.append("behavioral evidence does not verify the focus sweep")
                if str((behavior_review.get("labelInName") or {}).get("status") or "").lower() == "verified":
                    names = [dig(r, "a11y", "browserLabelInName", default=None) for r in runs]
                    if not names or any(x is None or x.get("failures", 0) for x in names):
                        problems.append("behavioral evidence does not verify browser Label in Name")
                if str((behavior_review.get("accessibleNames") or {}).get("status") or "").lower() == "verified":
                    names = [dig(r, "a11y", "browserMissingAccessibleName", default=None) for r in runs]
                    if not names or any(x is None or x.get("failures", 0) or x.get("inconclusive") for x in names):
                        problems.append("behavioral evidence does not verify browser accessible names")

            i18n_doc = load_evidence_json("internationalizationReview", "internationalization")
            if i18n_doc is not None:
                review = cert.get("internationalizationReview") or {}
                runs = i18n_doc.get("runs") or []
                baseline_run = next((x for x in runs if x.get("tag") == "1440x900"), None)
                base_over = bool(dig(baseline_run, "layout", "horizontalOverflow", default=False)) if baseline_run else False
                base_clip = dig(baseline_run, "layout", "clippedContent", "count", default=0) if baseline_run else 0
                for check, tag in (("textExpansion", "text-expansion"), ("rtl", "rtl")):
                    if str((review.get(check) or {}).get("status") or "").lower() != "verified":
                        continue
                    run = next((x for x in runs if x.get("tag") == tag), None)
                    if run is None or baseline_run is None:
                        problems.append(f"internationalization evidence misses {tag}")
                        continue
                    new_over = bool(dig(run, "layout", "horizontalOverflow", default=False))
                    new_clip = dig(run, "layout", "clippedContent", "count", default=0)
                    if (new_over and not base_over) or new_clip > base_clip:
                        problems.append(f"internationalization evidence contains a {tag} layout regression")

                locale_state = str((review.get("localeProfiles") or {}).get("status") or "").lower()
                if locale_state == "verified":
                    if baseline_run is None:
                        problems.append("internationalization evidence misses the 1440x900 locale baseline")
                    locale_attempts = [x for x in i18n_doc.get("overridePasses", [])
                                       if str(x.get("pass") or "").startswith("locale-")]
                    if not locale_attempts or any(x.get("status") != "ran" for x in locale_attempts):
                        problems.append("internationalization evidence does not verify complete locale profiles")
                    for attempt in locale_attempts:
                        run = next((x for x in runs if x.get("tag") == attempt.get("pass")), None)
                        if run is None:
                            problems.append(f"internationalization evidence misses {attempt.get('pass')}")
                            continue
                        new_over = bool(dig(run, "layout", "horizontalOverflow", default=False))
                        new_clip = dig(run, "layout", "clippedContent", "count", default=0)
                        if (new_over and not base_over) or new_clip > base_clip:
                            problems.append(f"internationalization evidence contains a {attempt.get('pass')} layout regression")

            for section, label, mode in (("representativeSampling", "representative sampling", "sampling"),
                                         ("usabilityReview", "usability", "usability"),
                                         ("assistiveTechReview", "assistive technology", "assistive-tech"),
                                         ("performanceReview", "production performance", "performance")):
                evidence_doc = load_evidence_json(section, label)
                if evidence_doc is not None and (evidence_doc.get("status") != "pass" or
                                                 evidence_doc.get("mode") != mode or
                                                 evidence_doc.get("schema") != "designer-dude-evidence-gate/v1"):
                    problems.append(f"{label} evidence is not a passing {mode} gate")
                if evidence_doc is None or evidence_doc.get("status") != "pass":
                    continue
                thresholds = evidence_doc.get("thresholds") or {}
                payload = evidence_doc.get("evidence") or {}
                check_source_freshness(payload, thresholds, label)
                nested = verify_nested_artifacts(payload, label)
                raw_inputs = verify_nested_artifacts(payload, label, "inputArtifacts")
                if len(raw_inputs) != 1:
                    problems.append(f"{label} evidence must bind exactly one raw input document")
                digests = (payload.get("inputDigests") or {}).values()
                if not digests or any(not re.fullmatch(r"[0-9a-f]{64}", str(x or ""))
                                      for x in digests):
                    problems.append(f"{label} evidence does not bind its raw input")
                if mode == "sampling":
                    if (thresholds.get("minStructured", 0) < 3 or
                            thresholds.get("minRandom", 0) < 2 or
                            thresholds.get("minProcesses", 0) < 1):
                        problems.append("representative sampling evidence weakens perfection thresholds")
                    if payload.get("completeProcesses", 0) < thresholds.get("minProcesses", 1):
                        problems.append("representative sampling evidence lacks a complete process")
                    if payload.get("exhaustive"):
                        if payload.get("inventory", 0) < 1:
                            problems.append("exhaustive sampling evidence lacks a pinned inventory")
                    elif (payload.get("structured", 0) < thresholds.get("minStructured", 3) or
                          payload.get("random", 0) < thresholds.get("minRandom", 2) or
                          payload.get("randomSelectionVerified") is not True):
                        problems.append("representative sampling evidence lacks required samples")
                elif mode == "usability":
                    if (thresholds.get("minParticipants", 0) < 10 or
                            thresholds.get("minTasks", 0) < 3 or
                            thresholds.get("minAttemptsPerTask", 0) < 10 or
                            thresholds.get("minSuccessLower95", 0) < .7):
                        problems.append("usability evidence weakens perfection thresholds")
                    tasks = payload.get("tasks") or []
                    if payload.get("participants", 0) < thresholds.get("minParticipants", 10) or \
                            len(tasks) < thresholds.get("minTasks", 3) or any(
                                task.get("status") != "pass" or
                                task.get("attempts", 0) < thresholds.get("minAttemptsPerTask", 10) or
                                task.get("criticalErrors", 0) or
                                not str(task.get("essentialFunction") or "").strip() or
                                not re.fullmatch(r"[0-9a-f]{64}",
                                                 str(task.get("protocolTaskSha256") or "")) or
                                nested.get(str(task.get("protocolTaskArtifact") or "")) !=
                                str(task.get("protocolTaskSha256") or "").lower() or
                                not task.get("successCi95Wilson") or
                                task["successCi95Wilson"][0] < thresholds.get("minSuccessLower95", .7)
                                for task in tasks):
                        problems.append("usability evidence does not contain sufficient passing tasks")
                elif mode == "assistive-tech":
                    if (thresholds.get("minCombinations", 0) < 2 or
                            thresholds.get("minTasks", 0) < 3):
                        problems.append("assistive technology evidence weakens perfection thresholds")
                    combinations = payload.get("combinations") or []
                    stacks = payload.get("stacks") or []
                    tasks = payload.get("tasks") or []
                    observations = payload.get("observations") or []
                    if (len(stacks) < thresholds.get("minCombinations", 2) or
                            len(combinations) < len(stacks) or
                            len(tasks) < thresholds.get("minTasks", 3) or
                            len(observations) < len(combinations) * len(tasks) or
                            any(x.get("outcome") != "pass" or not re.fullmatch(
                                r"[0-9a-f]{64}", str(x.get("artifactSha256") or "")) or
                                not re.fullmatch(r"[0-9a-f]{64}",
                                                 str(x.get("taskProtocolSha256") or "")) or
                                nested.get(str(x.get("artifact") or "")) !=
                                str(x.get("artifactSha256") or "").lower() or
                                nested.get(str(x.get("taskProtocolArtifact") or "")) !=
                                str(x.get("taskProtocolSha256") or "").lower()
                                for x in observations)):
                        problems.append("assistive technology evidence has an incomplete or failing matrix")
                else:
                    if (thresholds.get("minSurfaces", 0) < 3 or
                            thresholds.get("minObservationsPerDevice", 0) < 100 or
                            thresholds.get("minWindowDays", 0) < 28 or
                            thresholds.get("maxLcpMsP75", 999999) > 2500 or
                            thresholds.get("maxInpMsP75", 999999) > 200 or
                            thresholds.get("maxClsP75", 999999) > .1):
                        problems.append("production performance evidence weakens Core Web Vitals thresholds")
                    surfaces = payload.get("surfaces") or []
                    if (payload.get("productionBuild") is not True or
                            payload.get("realUserMonitoring") is not True or
                            payload.get("windowDays", 0) < thresholds.get("minWindowDays", 28) or
                            len(surfaces) < thresholds.get("minSurfaces", 3)):
                        problems.append("production performance evidence lacks production RUM scope")
                    for surface in surfaces:
                        if not isinstance(surface, dict):
                            problems.append("production performance evidence contains an invalid surface")
                            continue
                        if nested.get(str(surface.get("artifact") or "")) != \
                                str(surface.get("artifactSha256") or "").lower():
                            problems.append("production performance surface lacks its pinned RUM export")
                        devices = surface.get("devices") if isinstance(surface.get("devices"), dict) else {}
                        for device in ("mobile", "desktop"):
                            item = devices.get(device) if isinstance(devices.get(device), dict) else {}
                            p75 = item.get("p75") if isinstance(item.get("p75"), dict) else {}
                            if (item.get("status") != "pass" or
                                    item.get("observations", 0) < thresholds.get("minObservationsPerDevice", 100) or
                                    p75.get("lcpMs", 999999) > thresholds.get("maxLcpMsP75", 2500) or
                                    p75.get("inpMs", 999999) > thresholds.get("maxInpMsP75", 200) or
                                    p75.get("cls", 999999) > thresholds.get("maxClsP75", .1)):
                                problems.append(f"production performance evidence fails {surface.get('id')}/{device}")

            calibration_doc = load_evidence_json("calibrationSnapshot", "calibration snapshot")
            if calibration_doc is not None and (calibration_doc.get("status") != "pass" or
                                                calibration_doc.get("schema") != "designer-dude-calibration-verification/v1"):
                problems.append("calibration snapshot evidence is not a passing verification")
            if calibration_doc is not None and calibration_doc.get("status") == "pass" and (
                    calibration_doc.get("artifactCount", 0) < 1 or
                    calibration_doc.get("ageDays", 91) > 90 or
                    (calibration_doc.get("thresholds") or {}).get("maxAgeDays", 91) > 90 or
                    not re.fullmatch(r"[0-9a-f]{64}",
                                     str(calibration_doc.get("manifestSha256") or "")) or
                    calibration_doc.get("errors")):
                problems.append("calibration snapshot evidence is empty, stale, or contains errors")
            if calibration_doc is not None and calibration_doc.get("status") == "pass":
                calibration_nested = verify_nested_artifacts(calibration_doc, "calibration snapshot")
                snapshot_hash = str(calibration_doc.get("manifestSha256") or "").lower()
                if (snapshot_hash not in calibration_nested.values() or
                        len(calibration_nested) < calibration_doc.get("artifactCount", 0) + 1):
                    problems.append("calibration snapshot bundle omits its manifest or frozen artifacts")
                matches = [path for path, digest in indexed.items() if digest == snapshot_hash]
                if not matches:
                    problems.append("calibration snapshot manifest bytes are absent from artifactManifest")
                else:
                    verified_snapshot = False
                    for path in matches:
                        pure = pathlib.PurePosixPath(path)
                        if pure.is_absolute() or ".." in pure.parts:
                            continue
                        full = os.path.join(base, path)
                        if not os.path.isfile(full):
                            continue
                        try:
                            actual = hashlib.sha256()
                            with open(full, "rb") as fh:
                                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                                    actual.update(chunk)
                            verified_snapshot = verified_snapshot or actual.hexdigest() == snapshot_hash
                        except OSError:
                            continue
                    if not verified_snapshot:
                        problems.append("calibration snapshot manifest artifact is absent or hash-mismatched")

            if isinstance(method, dict):
                for key, label, mode, schema in (
                    ("detectorBenchmark", "detector benchmark", "detectors", "designer-dude-evidence-gate/v1"),
                    ("actBenchmark", "W3C ACT benchmark", "detectors", "designer-dude-act-benchmark/v1"),
                    ("expertCorrelation", "expert-score correlation", "ratings", "designer-dude-evidence-gate/v1")):
                    item = method.get(key) if isinstance(method.get(key), dict) else {}
                    evidence_doc = load_artifact_json(item.get("evidence"), label)
                    if evidence_doc is not None and (evidence_doc.get("status") != "pass" or
                                                     evidence_doc.get("mode") != mode or
                                                     evidence_doc.get("schema") != schema):
                        problems.append(f"{label} evidence is not a passing {mode} gate")
                        continue
                    if evidence_doc is None:
                        continue
                    thresholds = evidence_doc.get("thresholds") or {}
                    payload = evidence_doc.get("evidence") or {}
                    if key != "actBenchmark":
                        check_source_freshness(payload, thresholds, label)
                        nested = verify_nested_artifacts(payload, label)
                        raw_inputs = verify_nested_artifacts(payload, label, "inputArtifacts")
                        expected_inputs = 2 if key == "detectorBenchmark" else 1
                        if len(raw_inputs) != expected_inputs:
                            problems.append(f"{label} evidence must bind exactly {expected_inputs} raw input document(s)")
                    if key != "actBenchmark":
                        digests = (payload.get("inputDigests") or {}).values()
                        if not digests or any(not re.fullmatch(r"[0-9a-f]{64}", str(x or ""))
                                              for x in digests):
                            problems.append(f"{label} evidence does not bind its raw input")
                    if key == "detectorBenchmark":
                        if (thresholds.get("minCases", 0) < 100 or
                                thresholds.get("minPositive", 0) < 50 or
                                thresholds.get("minNegative", 0) < 40 or
                                thresholds.get("minLabelers", 0) < 2 or
                                thresholds.get("minPrecisionLower95", 0) < .94 or
                                thresholds.get("minRecallLower95", 0) < .94 or
                                thresholds.get("maxCannotTellRatio", 1) > .05):
                            problems.append("detector benchmark evidence weakens perfection thresholds")
                        confusion = payload.get("confusion") or {}
                        cases = payload.get("cases", 0)
                        if (cases < thresholds.get("minCases", 100) or confusion.get("fp", 0) or
                                confusion.get("fn", 0) or
                                confusion.get("tp", 0) < thresholds.get("minPositive", 50) or
                                confusion.get("tn", 0) < thresholds.get("minNegative", 40) or
                                (cases and confusion.get("cannotTell", 0) / cases >
                                 thresholds.get("maxCannotTellRatio", .05))):
                            problems.append("detector benchmark evidence does not meet its confusion thresholds")
                        for rule, counts in (payload.get("perRule") or {}).items():
                            if not counts.get("tp", 0) + counts.get("fn", 0) or \
                                    not counts.get("tn", 0) + counts.get("fp", 0):
                                problems.append(f"detector benchmark rule {rule} lacks two-sided coverage")
                    elif key == "expertCorrelation":
                        if (thresholds.get("minProducts", 0) < 12 or
                                thresholds.get("minReviewers", 0) < 3 or
                                thresholds.get("minAgreementAlpha", 0) < .8 or
                                thresholds.get("minSpearmanLower95", 0) < .7 or
                                thresholds.get("minLinConcordance", 0) < .9 or
                                thresholds.get("maxMeanAbsoluteError", 999) > 5 or
                                thresholds.get("maxAbsoluteBias", 999) > 3 or
                                thresholds.get("maxProductError", 999) > 10 or
                                thresholds.get("minExpertScoreSpan", 0) < 80 or
                                thresholds.get("minHighProducts", 0) < 2 or
                                thresholds.get("minLowProducts", 0) < 2 or
                                thresholds.get("minHighExpertScore", 0) < 90 or
                                thresholds.get("maxLowExpertScore", 999) > 20 or
                                thresholds.get("bootstrapIterations", 0) < 1000):
                            problems.append("expert-score correlation evidence weakens perfection thresholds")
                        ci = payload.get("spearmanBootstrap95") or []
                        coverage = payload.get("strataCoverage") or {}
                        panel = payload.get("reviewerPanel") or {}
                        products = payload.get("products") or []
                        expert_values = [x.get("expertMedian") for x in products
                                         if isinstance(x, dict) and isinstance(x.get("expertMedian"), (int, float))]
                        bands = collections.Counter(str((x.get("strata") or {}).get("qualityBand") or "").lower()
                                                    for x in products if isinstance(x, dict))
                        if (payload.get("count", 0) < thresholds.get("minProducts", 12) or
                                payload.get("krippendorffAlphaInterval", -1) <
                                thresholds.get("minAgreementAlpha", .8) or len(ci) != 2 or
                                ci[0] < thresholds.get("minSpearmanLower95", .7) or
                                payload.get("linConcordance", -1) < thresholds.get("minLinConcordance", .9) or
                                payload.get("meanAbsoluteError", 999) >
                                thresholds.get("maxMeanAbsoluteError", 5) or
                                abs(payload.get("meanBias", 999)) > thresholds.get("maxAbsoluteBias", 3) or
                                payload.get("maxProductError", 999) > thresholds.get("maxProductError", 10) or
                                payload.get("expertScoreSpan", 0) < thresholds.get("minExpertScoreSpan", 80) or
                                payload.get("highProducts", 0) < thresholds.get("minHighProducts", 2) or
                                payload.get("lowProducts", 0) < thresholds.get("minLowProducts", 2) or
                                panel.get("profiled", 0) < thresholds.get("minReviewers", 3) or
                                panel.get("affiliations", 0) < 2 or
                                not {"product-design", "accessibility"}.issubset(
                                    {str(x).lower() for x in panel.get("expertise") or []}) or
                                len(expert_values) != payload.get("count", 0) or
                                (expert_values and max(expert_values) - min(expert_values) <
                                 thresholds.get("minExpertScoreSpan", 80)) or
                                sum(x >= thresholds.get("minHighExpertScore", 90) for x in expert_values) <
                                thresholds.get("minHighProducts", 2) or
                                sum(x <= thresholds.get("maxLowExpertScore", 20) for x in expert_values) <
                                thresholds.get("minLowProducts", 2) or
                                len(coverage.get("productCategory") or []) < 3 or
                                len(coverage.get("surfaceType") or []) < 3 or
                                not {"low", "mid", "high"}.issubset(
                                    {str(x).lower() for x in coverage.get("qualityBand") or []}) or
                                not {"mobile", "desktop"}.issubset(
                                    {str(x).lower() for x in coverage.get("viewportClass") or []}) or
                                any(bands[x] < 3 for x in ("low", "mid", "high")) or
                                any(nested.get(str(x.get("artifact") or "")) !=
                                    str(x.get("artifactSha256") or "").lower()
                                    for x in products if isinstance(x, dict))):
                            problems.append("expert-score correlation evidence misses reliability thresholds")
                    else:
                        confusion = evidence_doc.get("confusion") or {}
                        total = sum(confusion.get(x, 0) for x in ("tp", "fp", "tn", "fn", "cannotTell"))
                        source = evidence_doc.get("source") or {}
                        cases = evidence_doc.get("items") or []
                        try:
                            act_stamp = datetime.datetime.fromisoformat(
                                str(evidence_doc.get("generatedAt") or "").replace("Z", "+00:00"))
                            if act_stamp.tzinfo is None:
                                act_stamp = act_stamp.replace(tzinfo=datetime.timezone.utc)
                            act_age = (datetime.datetime.now(datetime.timezone.utc) -
                                       act_stamp.astimezone(datetime.timezone.utc)).days
                        except ValueError:
                            act_age = 91
                        if (total < 80 or confusion.get("fp", 0) or confusion.get("fn", 0) or
                                (total and confusion.get("cannotTell", 0) / total > .05) or
                                act_age < -1 or act_age > 90 or
                                not re.fullmatch(r"[0-9a-f]{64}", str(source.get("manifestSha256") or "")) or
                                len(cases) != total or any(not re.fullmatch(
                                    r"[0-9a-f]{64}", str(case.get("sourceSha256") or ""))
                                    for case in cases if isinstance(case, dict)) or
                                any(not isinstance(case, dict) for case in cases)):
                            problems.append("W3C ACT benchmark evidence lacks a clean pinned corpus result")

            for credit in credit_records:
                pillar = str(credit.get("pillar") or "").strip()
                path = str(credit.get("evidence") or "").strip()
                credit_doc = load_artifact_json(path, f"{pillar or 'unknown'} A+ credit")
                if credit_doc is None:
                    continue
                expected_criterion = A_PLUS_CRITERIA.get(pillar, (None,))[0]
                if (credit_doc.get("schema") != "designer-dude-credit-evidence/v1" or
                        credit_doc.get("status") != "pass" or
                        str(credit_doc.get("pillar") or "") != pillar or
                        str(credit_doc.get("criterion") or "") != str(expected_criterion or "") or
                        str(credit.get("criterion") or "") != str(expected_criterion or "")):
                    problems.append(f"{pillar or 'unknown'} A+ credit evidence does not match its criterion")
                if not str(credit_doc.get("reviewer") or "").strip():
                    problems.append(f"{pillar or 'unknown'} A+ credit evidence has no reviewer")
                try:
                    stamp = datetime.datetime.fromisoformat(
                        str(credit_doc.get("reviewedAt") or "").replace("Z", "+00:00"))
                    if stamp.tzinfo is None:
                        stamp = stamp.replace(tzinfo=datetime.timezone.utc)
                    age = (datetime.datetime.now(datetime.timezone.utc) -
                           stamp.astimezone(datetime.timezone.utc)).days
                    if age < -1 or age > 90:
                        problems.append(f"{pillar or 'unknown'} A+ credit evidence is stale or future-dated")
                except ValueError:
                    problems.append(f"{pillar or 'unknown'} A+ credit evidence has no valid review date")
                declared_surfaces = {str(x).strip() for x in credit_doc.get("surfaces", []) if str(x).strip()}
                record_surfaces = {str(x).strip() for x in credit.get("surfaces", []) if str(x).strip()}
                if len(declared_surfaces) < 2 or declared_surfaces != record_surfaces:
                    problems.append(f"{pillar or 'unknown'} A+ credit evidence does not match its surfaces")
                observations = credit_doc.get("observations")
                if not isinstance(observations, list) or not observations or any(
                        not str(x).strip() for x in observations):
                    problems.append(f"{pillar or 'unknown'} A+ credit evidence has no observations")
                verify_nested_artifacts(credit_doc, f"{pillar or 'unknown'} A+ credit")
    return problems


def perfection_eligible(findings_mode, credited_count, slop_measured, certification_ok):
    """The literal maximum needs the complete machine and human evidence path."""
    return (bool(findings_mode) and credited_count == len(PILLARS) and
            bool(slop_measured) and bool(certification_ok))


def grades_from_findings(path, verbose=True):
    with open(path) as fh:
        doc = json.load(fh)
    findings = doc if isinstance(doc, list) else doc.get("findings", [])

    per = {k: [] for k in PILLAR_KEYS}
    credits = {k: [] for k in PILLAR_KEYS}
    rejected_credits = []
    unknown, ignored, candidates = [], 0, 0
    for f in findings:
        pillar = (f.get("pillar") or "").strip()
        status = (f.get("status") or "confirmed").strip().lower()
        sev = (f.get("severity") or "").strip().lower()
        if pillar not in per:
            unknown.append(pillar or "(none)")
            continue
        if (f.get("kind") or "").strip().lower() == "credit" or sev == "credit":
            problems = credit_problems(f, pillar)
            if not problems:
                problems.extend(credit_evidence_problems(f, pillar, path))
            if problems:
                rejected_credits.append((pillar, f.get("id") or "(no id)", problems))
            else:
                credits[pillar].append(f)
            continue
        if status in DOES_NOT_COUNT:
            ignored += 1
            continue
        if status not in COUNTS_AGAINST:
            unknown.append(f"status:{status}")
            continue
        if status == "candidate":
            candidates += 1
        if sev not in SEVERITY_COST:
            unknown.append(f"severity:{sev}")
            continue
        per[pillar].append(f)

    if unknown and verbose:
        print("warning: entries the scorer could not use: " +
              ", ".join(sorted(set(unknown))[:8]))
    if candidates and verbose:
        print(f"WARNING: {candidates} findings still have status 'candidate'. A candidate is")
        print("         a grep or a threshold breach, NOT a confirmed defect. Confirm or")
        print("         reject each one before quoting this score anywhere.")
    if rejected_credits and verbose:
        print("CREDITS NOT COUNTED (a credit that does not meet the bar is not a grade):")
        for pillar, ident, problems in rejected_credits:
            print(f"  {pillar}/{ident}: " + "; ".join(problems))

    grades, detail = {}, {}
    for key in PILLAR_KEYS:
        items = per[key]
        cost = sum(SEVERITY_COST[(f.get("severity") or "").lower()] for f in items)
        value = max(40.0, GRADE_VALUES["A"] - cost)
        # A credit promotes A -> A+, and ONLY from a clean A. A pillar carrying
        # an open defect cannot be "considered and delightful" at the same time,
        # so a credit never cancels a demotion -- it cannot be used to buy back
        # points, only to record that a defect-free pillar went further.
        credited = None
        if credits[key]:
            if cost == 0:
                credited = credits[key][0]
                value = float(GRADE_VALUES["A+"])
            else:
                credited = False   # claimed, blocked by open findings
        grades[key] = to_letter(value)
        detail[key] = {
            "raw": normalize(value), "cost": normalize(cost), "count": len(items),
            "bySeverity": {s: sum(1 for f in items if (f.get("severity") or "").lower() == s)
                           for s in SEVERITY_COST},
            "credit": (credited.get("id") or credited.get("criterion")) if credited else None,
            "creditBlocked": credited is False,
        }
    return grades, detail, doc, ignored


# ---------------- target / gap analysis ----------------

def path_to_target(grades, target, ceiling_letter="A"):
    """Cheapest route to a target composite, aggregated per pillar.

    This is what makes 'keep running it until it scores 90+' a plan rather than
    a grind: it names which pillars actually move the number, with the points
    each buys. Typography and Hierarchy carry 30 of the 100 points between
    them, so a run spent polishing Motion and Craft can move the composite by
    less than a point no matter how good the work was.

    Aggregated by pillar because 'Typography C -> A-' is a plan and forty rows
    of 'B+ -> A-' is a treadmill. Stops at A by default: A+ is reserved for
    'considered and delightful, rare', which is not something you schedule.
    """
    cur = {k: grades[k].replace("−", "-") for k in PILLAR_KEYS}
    start = dict(cur)
    total = sum(GRADE_VALUES[cur[k]] * w / 100 for k, _, w in PILLARS)
    ceiling = GRADE_VALUES[ceiling_letter]
    guard = 0
    while total < target and guard < 120:
        guard += 1
        best = None
        for key, name, weight in PILLARS:
            nxt = next_letter_up(cur[key])
            if nxt == cur[key] or GRADE_VALUES[nxt] > ceiling:
                continue
            gain = (GRADE_VALUES[nxt] - GRADE_VALUES[cur[key]]) * weight / 100
            if gain <= 0:
                continue
            if best is None or gain > best[0]:
                best = (gain, key, nxt)
        if best is None:
            break
        _, key, nxt = best
        gain = (GRADE_VALUES[nxt] - GRADE_VALUES[cur[key]]) * PILLAR_WEIGHT[key] / 100
        cur[key] = nxt
        total = normalize(total + gain)

    moves = []
    for key, name, weight in PILLARS:
        if cur[key] != start[key]:
            gain = (GRADE_VALUES[cur[key]] - GRADE_VALUES[start[key]]) * weight / 100
            moves.append((name, start[key], cur[key], gain, weight))
    moves.sort(key=lambda m: -m[3])
    return moves, total


def all_at(letter):
    """Composite of a card where every pillar is `letter`."""
    return normalize(sum(GRADE_VALUES[letter] * w / 100 for _, _, w in PILLARS))


def credit_plan(target, grades=None):
    """How many pillars must earn an A+ credit to reach a target above 92.

    The findings ceiling is a straight-A card = 92.00, so any target above that
    is a claim about excellence, not a backlog of fixes. This prints exactly
    which pillars would have to clear their A+ criterion -- the arithmetic that
    otherwise gets hand-derived once per campaign and then argued about.

    Greedy by weight, which is optimal here: every promotion is the same
    +8 letter-points (A=92 -> A+=100), so the cheapest route is always the
    heaviest pillar.
    """
    base = {k: "A" for k in PILLAR_KEYS}
    if grades:
        for k in PILLAR_KEYS:
            cur = grades.get(k, "A").replace("−", "-")
            # Assume the pillar reaches A first; credits sit on top of that.
            base[k] = "A+" if cur == "A+" else "A"
    total = normalize(sum(GRADE_VALUES[base[k]] * w / 100 for k, _, w in PILLARS))
    order = sorted((p for p in PILLARS if base[p[0]] != "A+"),
                   key=lambda p: -p[2])
    needed = []
    for key, name, weight in order:
        if total >= target:
            break
        total = normalize(total + (GRADE_VALUES["A+"] - GRADE_VALUES["A"]) * weight / 100)
        needed.append((name, weight, total))
    return needed, total


def feasibility(target):
    """What grade average does the target actually demand? Print it up front.

    Because the composite is a weighted mean of the letter values, an all-A-
    minus card scores exactly 88 -- so a 90 target is unreachable without real
    A grades, no matter how many small fixes land. Users chasing 90+ deserve to
    know that before spending a run on it.
    """
    ladder = ["B", "B+", "A-", "A", "A+"]
    scores = {l: sum(GRADE_VALUES[l] * w / 100 for _, _, w in PILLARS) for l in ladder}
    # The lowest uniform grade that clears the target - the honest answer to
    # "how good does this have to be", rather than marking every row above it.
    minimum = next((l for l in ladder if scores[l] >= target), None)
    lines = []
    for letter in reversed(ladder):
        mark = "   <- the target needs at least this, everywhere" if letter == minimum else ""
        lines.append(f"    every pillar at {letter:<2} = {scores[letter]:6.2f}{mark}")
    if minimum is None:
        lines.append("    even an all-A+ card does not reach this target. Pick a real number.")
    return lines


# ---------------- currency ----------------

def currency_warning():
    canon = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "references", "canon.md")
    try:
        with open(canon) as fh:
            head = fh.read(4000)
    except OSError:
        return None
    m = re.search(r"Last verified:\s*(\d{4})-(\d{2})-(\d{2})", head)
    if not m:
        return "canon.md has no 'Last verified:' date - the currency layer cannot be trusted."
    verified = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    age = (datetime.date.today() - verified).days
    if age > CURRENCY_MAX_DAYS:
        return (f"canon.md was last verified {age} days ago ({verified}). Re-verify the dated "
                f"claims (trend calls, WCAG/CWV status, benchmark palettes) with WebSearch "
                f"before asserting any of them.")
    return None


# ---------------- selftest ----------------

def selftest():
    failures = []
    seen = set()
    for letter, value in GRADE_VALUES.items():
        canonical = letter.replace("−", "-")
        if canonical in seen:
            continue
        seen.add(canonical)
        got = to_letter(value)
        if got != canonical:
            failures.append(f"  {canonical} = {value} -> reads back as {got}")

    weight_total = sum(w for _, _, w in PILLARS)
    if weight_total != 100:
        failures.append(f"  pillar weights sum to {weight_total}, not 100")
    if to_letter(WCAG_CAP) != "C+":
        failures.append(f"  WCAG_CAP {WCAG_CAP} maps to {to_letter(WCAG_CAP)}, expected C+")
    if to_letter(PROVISIONAL_CAP) != "B+":
        failures.append(f"  PROVISIONAL_CAP {PROVISIONAL_CAP} maps to {to_letter(PROVISIONAL_CAP)}, expected B+")

    # Demotion maths: one critical from A must land exactly on B, two minors
    # must equal one major, and four minors must equal one critical.
    if to_letter(GRADE_VALUES["A"] - SEVERITY_COST["critical"]) != "B":
        failures.append("  A minus one critical does not land on B")
    if SEVERITY_COST["minor"] * 2 != SEVERITY_COST["major"]:
        failures.append("  two minors != one major")
    if SEVERITY_COST["minor"] * 4 != SEVERITY_COST["critical"]:
        failures.append("  four minors != one critical")

    # Every ladder rung must round-trip and strictly ascend.
    ladder = ["F", "D", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]
    vals = [GRADE_VALUES[x] for x in ladder]
    if vals != sorted(vals):
        failures.append("  ladder is not monotonically increasing")
    for key in EYE_ONLY:
        if key != "consistency" and key not in PILLAR_KEYS:
            failures.append(f"  EYE_ONLY names '{key}', which is not a pillar")

    # A perfect card must actually print A+, and an all-F card must print F.
    perfect = sum(GRADE_VALUES["A+"] * w / 100 for _, _, w in PILLARS)
    worst = sum(GRADE_VALUES["F"] * w / 100 for _, _, w in PILLARS)
    if to_letter(perfect) != "A+":
        failures.append(f"  all-A+ card scores {perfect} -> {to_letter(perfect)}")
    if to_letter(worst) != "F":
        failures.append(f"  all-F card scores {worst} -> {to_letter(worst)}")

    if to_letter(PERF_UNMEASURED_CAP) != "A-":
        failures.append(f"  PERF_UNMEASURED_CAP {PERF_UNMEASURED_CAP} maps to "
                        f"{to_letter(PERF_UNMEASURED_CAP)}, expected A-")

    # Every pillar must have exactly one A+ criterion, and the ids must be
    # unique and namespaced to their pillar -- a credit naming another pillar's
    # criterion is the obvious way to game this.
    for key, _, _ in PILLARS:
        if key not in A_PLUS_CRITERIA:
            failures.append(f"  no A+ criterion defined for pillar '{key}'")
    for key, (cid, text) in A_PLUS_CRITERIA.items():
        if key not in PILLAR_KEYS:
            failures.append(f"  A+ criterion '{cid}' names non-pillar '{key}'")
        elif not cid.startswith(key + "."):
            failures.append(f"  criterion id '{cid}' is not namespaced to '{key}'")
        if len(text) < 40:
            failures.append(f"  criterion '{cid}' has no substantive definition")
    ids = [c for c, _ in A_PLUS_CRITERIA.values()]
    if len(set(ids)) != len(ids):
        failures.append("  duplicate A+ criterion ids")

    # The ceiling arithmetic that Mode F quotes must come from here, not from
    # anyone's head: a straight-A card is 92.00 and only credits go above it.
    if all_at("A") != 92.0:
        failures.append(f"  straight-A card scores {all_at('A')}, expected 92.00")
    if all_at("A+") != 100.0:
        failures.append(f"  all-A+ card scores {all_at('A+')}, expected 100.00")
    needed, reached = credit_plan(95.0)
    if reached < 95.0 or len(needed) < 2:
        failures.append(f"  credit_plan(95) returned {len(needed)} credits reaching {reached}")
    if credit_plan(92.0)[0]:
        failures.append("  credit_plan(92) asks for credits to reach the findings ceiling")
    if credit_plan(101.0)[1] < all_at("A+") - 0.001:
        failures.append("  credit_plan(101) did not exhaust every pillar before giving up")
    # 100 must be REACHABLE -- that is the whole point of A+ = 100 -- and it
    # must cost every pillar. A scale whose maximum no work can reach is a
    # broken instrument; one whose maximum is cheap is a flattering one.
    plan_100, reached_100 = credit_plan(100.0)
    if reached_100 < 100.0 or len(plan_100) != len(PILLARS):
        failures.append(f"  credit_plan(100) reached {reached_100} with "
                        f"{len(plan_100)} of {len(PILLARS)} pillars credited")

    # A credit must be rejected for each missing element, and accepted only
    # when all of them are present.
    good = {"kind": "credit", "criterion": A_PLUS_CRITERIA["motion"][0],
            "evidence": ".design/probe-dashboard.json", "surfaces": ["a", "b"],
            "status": "verified"}
    if credit_problems(good, "motion"):
        failures.append("  a complete credit was rejected: " +
                        "; ".join(credit_problems(good, "motion")))
    for drop, why in [("criterion", "missing criterion"), ("evidence", "missing evidence"),
                      ("surfaces", "missing surfaces")]:
        bad = {k: v for k, v in good.items() if k != drop}
        if not credit_problems(bad, "motion"):
            failures.append(f"  credit accepted despite {why}")
    if not credit_problems({**good, "surfaces": ["only-one"]}, "motion"):
        failures.append("  credit accepted from a single surface")
    if not credit_problems({**good, "surfaces": ["same", "same"]}, "motion"):
        failures.append("  credit accepted from the same surface listed twice")
    if not credit_problems({k: v for k, v in good.items() if k != "status"}, "motion"):
        failures.append("  credit accepted without explicit verified status")
    if not credit_problems(good, "craft"):
        failures.append("  motion's criterion was accepted as a credit for craft")
    with tempfile.TemporaryDirectory(prefix="designer-dude-credit-") as tmp:
        nested_name = "motion-proof.txt"
        nested_bytes = b"reviewed motion evidence"
        nested_digest = hashlib.sha256(nested_bytes).hexdigest()
        with open(os.path.join(tmp, nested_name), "wb") as fh:
            fh.write(nested_bytes)
        credit_name = "credit-motion.json"
        credit_record = {**good, "pillar": "motion", "evidence": credit_name}
        credit_doc = {
            "schema": "designer-dude-credit-evidence/v1", "status": "pass",
            "pillar": "motion", "criterion": A_PLUS_CRITERIA["motion"][0],
            "reviewer": "reviewer@example.test",
            "reviewedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "surfaces": ["a", "b"], "observations": ["motion is purposeful and bounded"],
            "artifacts": [{"path": nested_name, "sha256": nested_digest}],
        }
        with open(os.path.join(tmp, credit_name), "w") as fh:
            json.dump(credit_doc, fh)
        credit_ledger = os.path.join(tmp, "findings.json")
        with open(credit_ledger, "w") as fh:
            json.dump({"findings": [credit_record]}, fh)
        credit_grades, _, _, _ = grades_from_findings(credit_ledger, verbose=False)
        if credit_grades.get("motion") != "A+":
            failures.append("  valid reviewed A+ credit evidence was rejected")
        credit_doc["pillar"] = "craft"
        with open(os.path.join(tmp, credit_name), "w") as fh:
            json.dump(credit_doc, fh)
        bad_credit_grades, _, _, _ = grades_from_findings(credit_ledger, verbose=False)
        if bad_credit_grades.get("motion") == "A+":
            failures.append("  wrong-pillar A+ evidence raised a high score")
    good_cert = {
        "perfectionCertification": {
            "status": "verified", "reviewer": "reviewer@example.test",
            "reviewedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "surfaces": ["dashboard", "settings", "detail"],
            "viewports": ["320x568", "768x1024", "1440x900"],
            "states": sorted(PERFECTION_STATES),
            "evidence": ["dashboard.png", "settings.png", "detail.png"],
            "ariaSnapshotEvidence": ["dashboard.aria.yml", "settings.aria.yml", "detail.aria.yml"],
            "completeProcesses": [{"name": "approve invoice", "status": "verified",
                                   "steps": ["open record", "approve", "see confirmation"],
                                   "evidence": "approve-process.md"}],
            "keyboardReview": {"status": "verified", "evidence": "keyboard-pass.md"},
            "assistiveTechReview": {"status": "verified", "evidence": "at.json"},
            "validationEvidence": {"status": "verified", "recall": "68/68",
                                   "precision": "52/52", "mutations": "18/18",
                                   "pipeline": "16/16", "evidence": "validation.json"},
            "behavioralReview": {
                "status": "verified", "evidence": "behavior.json",
                "focusSweep": {"status": "verified"},
                "accessibleNames": {"status": "verified"},
                "labelInName": {"status": "verified"},
                "statusAnnouncements": {"status": "verified"},
                "widgetContracts": {"status": "not-applicable", "reason": "native controls only"},
                "accessibleAuthentication": {"status": "not-applicable", "reason": "no authentication surface"},
                "dragAlternatives": {"status": "not-applicable", "reason": "no dragging interactions"},
                "redundantEntry": {"status": "not-applicable", "reason": "no repeated multi-step inputs"},
            },
            "internationalizationReview": {
                "status": "verified", "evidence": "i18n.json",
                "textExpansion": {"status": "verified"},
                "rtl": {"status": "not-applicable", "reason": "English-only declared scope"},
                "localeProfiles": {"status": "verified"},
            },
            "representativeSampling": {"status": "verified", "evidence": "sampling.json"},
            "usabilityReview": {"status": "verified", "evidence": "usability.json"},
            "performanceReview": {"status": "verified", "evidence": "performance.json"},
            "methodValidation": {"status": "verified",
                "detectorBenchmark": {"status": "verified", "evidence": "detector-benchmark.json"},
                "actBenchmark": {"status": "verified", "evidence": "act-benchmark.json"},
                "expertCorrelation": {"status": "verified", "evidence": "expert-correlation.json"}},
            "calibrationSnapshot": {"status": "verified", "evidence": "calibration-verification.json"},
            "crossEngineReview": {"status": "verified", "engines": ["chromium", "firefox", "webkit"],
                                  "evidence": "cross-engine.json"},
            "artifactRegression": {"status": "verified", "evidence": "artifact-regression.json",
                                   "visual": {"status": "verified"}, "aria": {"status": "verified"}},
            "artifactManifest": [
                {"path": p, "sha256": "0" * 64} for p in (
                    "dashboard.png", "settings.png", "detail.png",
                    "dashboard.aria.yml", "settings.aria.yml", "detail.aria.yml",
                    "approve-process.md", "keyboard-pass.md", "at.json",
                    "validation.json", "behavior.json", "i18n.json", "cross-engine.json",
                    "artifact-regression.json", "sampling.json", "usability.json",
                    "performance.json",
                    "detector-benchmark.json", "expert-correlation.json",
                    "act-benchmark.json",
                    "calibration-verification.json")
            ],
        }
    }
    good_cert["findings"] = []
    for pillar in PILLAR_KEYS:
        credit_path = f"credit-{pillar}.json"
        good_cert["findings"].append({
            "id": f"credit-{pillar}", "kind": "credit", "severity": "credit",
            "pillar": pillar, "criterion": A_PLUS_CRITERIA[pillar][0],
            "evidence": credit_path, "surfaces": ["dashboard", "detail"],
            "status": "verified",
        })
        good_cert["perfectionCertification"]["artifactManifest"].append(
            {"path": credit_path, "sha256": "0" * 64})
    cert_ok = not perfection_certification_problems(good_cert)
    if not cert_ok:
        failures.append("  complete perfection certification was rejected: " +
                        "; ".join(perfection_certification_problems(good_cert)))
    for missing in ("reviewer", "reviewedAt", "surfaces", "viewports", "states",
                    "evidence", "ariaSnapshotEvidence", "completeProcesses",
                    "keyboardReview", "assistiveTechReview", "validationEvidence",
                    "behavioralReview", "internationalizationReview", "crossEngineReview",
                    "artifactRegression", "representativeSampling", "usabilityReview",
                    "performanceReview", "methodValidation", "calibrationSnapshot", "artifactManifest"):
        bad_cert = json.loads(json.dumps(good_cert))
        del bad_cert["perfectionCertification"][missing]
        if not perfection_certification_problems(bad_cert):
            failures.append(f"  perfection certification accepted without {missing}")
    bad_hash = json.loads(json.dumps(good_cert))
    bad_hash["perfectionCertification"]["artifactManifest"][0]["sha256"] = "not-a-hash"
    if not perfection_certification_problems(bad_hash):
        failures.append("  perfection certification accepted an invalid artifact hash")
    bad_path = json.loads(json.dumps(good_cert))
    bad_path["perfectionCertification"]["artifactManifest"][0]["path"] = "../outside.png"
    if not perfection_certification_problems(bad_path):
        failures.append("  perfection certification accepted an escaping artifact path")
    bad_ratio = json.loads(json.dumps(good_cert))
    bad_ratio["perfectionCertification"]["validationEvidence"]["pipeline"] = "7/8"
    if not perfection_certification_problems(bad_ratio):
        failures.append("  perfection certification accepted an incomplete pipeline benchmark")
    bad_na = json.loads(json.dumps(good_cert))
    del bad_na["perfectionCertification"]["internationalizationReview"]["rtl"]["reason"]
    if not perfection_certification_problems(bad_na):
        failures.append("  perfection certification accepted not-applicable without a reason")
    bad_engines = json.loads(json.dumps(good_cert))
    bad_engines["perfectionCertification"]["crossEngineReview"]["engines"] = ["chromium", "firefox"]
    if not perfection_certification_problems(bad_engines):
        failures.append("  perfection certification accepted incomplete browser-engine coverage")
    with tempfile.TemporaryDirectory(prefix="designer-dude-score-") as tmp:
        verified_cert = json.loads(json.dumps(good_cert))
        manifest = verified_cert["perfectionCertification"]["artifactManifest"]
        nested_path = "nested-evidence.bin"
        snapshot_path = "calibration-snapshot.json"
        raw_input_path = "raw-input.json"
        raw_predictions_path = "raw-predictions.json"
        nested_hash = hashlib.sha256(("evidence:" + nested_path).encode("utf8")).hexdigest()
        snapshot_hash = hashlib.sha256(("evidence:" + snapshot_path).encode("utf8")).hexdigest()
        raw_input_hash = hashlib.sha256(("evidence:" + raw_input_path).encode("utf8")).hexdigest()
        raw_predictions_hash = hashlib.sha256(("evidence:" + raw_predictions_path).encode("utf8")).hexdigest()
        manifest.extend([{"path": nested_path, "sha256": nested_hash},
                         {"path": snapshot_path, "sha256": snapshot_hash},
                         {"path": raw_input_path, "sha256": raw_input_hash},
                         {"path": raw_predictions_path, "sha256": raw_predictions_hash}])
        fresh_stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        semantic_docs = {
            "validation.json": {"status": "pass", "ratios": {"recall": "68/68",
                "precision": "52/52", "mutations": "18/18", "pipeline": "16/16"}},
            "behavior.json": {"behavioralEvidence": {
                "announcements": [{"status": "verified"}], "widgets": [],
                "authentication": [], "dragAlternatives": [], "redundantEntries": []},
                "runs": [{"interaction": {"focusRing": {"tested": 3, "completelyObscured": 0}},
                          "a11y": {"browserLabelInName": {"failures": 0},
                                    "browserMissingAccessibleName": {"failures": 0, "inconclusive": []}}}]},
            "i18n.json": {"runs": [
                {"tag": "1440x900", "layout": {"horizontalOverflow": False,
                 "clippedContent": {"count": 0}}},
                {"tag": "text-expansion", "layout": {"horizontalOverflow": False,
                 "clippedContent": {"count": 0}}},
                {"tag": "locale-ja-jp", "layout": {"horizontalOverflow": False,
                 "clippedContent": {"count": 0}}}],
                "overridePasses": [{"pass": "locale-ja-jp", "status": "ran"}]},
            "cross-engine.json": {"enginesRequested": ["chromium", "firefox", "webkit"],
                "surfacesRequested": ["dashboard"], "viewportsRequested": ["1440x900"],
                "regressions": [], "results": [
                    {"engine": e, "surface": "dashboard", "viewport": "1440x900", "status": "ran"}
                    for e in ("chromium", "firefox", "webkit")]},
            "artifact-regression.json": {"status": "pass"},
            "sampling.json": {"schema": "designer-dude-evidence-gate/v1",
                "mode": "sampling", "status": "pass",
                "thresholds": {"minStructured": 3, "minRandom": 2, "minProcesses": 1,
                               "maxAgeDays": 90},
                "evidence": {"inputDigests": {"plan": "a" * 64},
                             "inputArtifacts": [{"path": raw_input_path,
                                                 "sha256": raw_input_hash,
                                                 "kind": "raw-sampling-input"}],
                             "artifacts": [{"path": nested_path, "sha256": nested_hash}],
                             "observedAt": fresh_stamp, "ageDays": 0,
                             "exhaustive": False, "samples": 5, "structured": 3,
                             "random": 2, "randomSelectionVerified": True,
                             "completeProcesses": 1}},
            "usability.json": {"schema": "designer-dude-evidence-gate/v1",
                "mode": "usability", "status": "pass",
                "thresholds": {"minParticipants": 10, "minTasks": 3,
                               "minAttemptsPerTask": 10, "minSuccessLower95": .7,
                               "maxAgeDays": 90},
                "evidence": {"inputDigests": {"observations": "a" * 64},
                             "inputArtifacts": [{"path": raw_input_path,
                                                 "sha256": raw_input_hash,
                                                 "kind": "raw-usability-input"}],
                             "artifacts": [{"path": nested_path, "sha256": nested_hash}],
                             "observedAt": fresh_stamp, "ageDays": 0,
                             "participants": 10, "tasks": [
                    {"id": f"task-{i}", "attempts": 10, "successes": 10,
                     "essentialFunction": f"function-{i}", "protocolTaskSha256": nested_hash,
                     "protocolTaskArtifact": nested_path,
                     "criticalErrors": 0, "successCi95Wilson": [.722467, 1], "status": "pass"}
                    for i in range(3)]}},
            "at.json": {"schema": "designer-dude-evidence-gate/v1",
                "mode": "assistive-tech", "status": "pass",
                "thresholds": {"minCombinations": 2, "minTasks": 3, "maxAgeDays": 90},
                "evidence": {"inputDigests": {"observations": "a" * 64},
                             "inputArtifacts": [{"path": raw_input_path,
                                                 "sha256": raw_input_hash,
                                                 "kind": "raw-assistive-tech-input"}],
                             "artifacts": [{"path": nested_path, "sha256": nested_hash}],
                             "observedAt": fresh_stamp, "ageDays": 0,
                             "stacks": [["nvda", "firefox", "windows"],
                                        ["voiceover", "safari", "macos"]],
                             "combinations": [["nvda", "1", "firefox", "1", "windows"],
                                                ["voiceover", "1", "safari", "1", "macos"]],
                             "tasks": ["one", "two", "three"],
                             "observations": [{"outcome": "pass", "artifact": nested_path,
                                               "artifactSha256": nested_hash,
                                               "taskProtocolArtifact": nested_path,
                                               "taskProtocolSha256": nested_hash}
                                              for _ in range(6)]}},
            "performance.json": {"schema": "designer-dude-evidence-gate/v1",
                "mode": "performance", "status": "pass",
                "thresholds": {"minSurfaces": 3, "minObservationsPerDevice": 100,
                               "minWindowDays": 28, "maxLcpMsP75": 2500,
                               "maxInpMsP75": 200, "maxClsP75": .1, "maxAgeDays": 90},
                "evidence": {"inputDigests": {"observations": "a" * 64},
                             "inputArtifacts": [{"path": raw_input_path,
                                                 "sha256": raw_input_hash,
                                                 "kind": "raw-performance-input"}],
                             "artifacts": [{"path": nested_path, "sha256": nested_hash}],
                             "observedAt": fresh_stamp, "ageDays": 0,
                             "windowDays": 28, "productionBuild": True,
                             "realUserMonitoring": True,
                             "surfaces": [{"id": f"surface-{i}", "artifact": nested_path,
                                 "artifactSha256": nested_hash, "devices": {
                                     device: {"observations": 100, "status": "pass",
                                              "p75": {"lcpMs": 1800, "inpMs": 120, "cls": .05}}
                                     for device in ("mobile", "desktop")}}
                                 for i in range(3)]}},
            "detector-benchmark.json": {"schema": "designer-dude-evidence-gate/v1",
                "mode": "detectors", "status": "pass", "thresholds": {
                    "minCases": 100, "minPositive": 50, "minNegative": 40,
                    "minLabelers": 2, "minPrecisionLower95": .94,
                    "minRecallLower95": .94, "maxCannotTellRatio": .05,
                    "maxAgeDays": 90},
                "evidence": {"inputDigests": {"labels": "a" * 64, "predictions": "b" * 64},
                    "inputArtifacts": [{"path": raw_input_path, "sha256": raw_input_hash,
                                        "kind": "raw-labels-input"},
                                       {"path": raw_predictions_path, "sha256": raw_predictions_hash,
                                        "kind": "raw-predictions-input"}],
                    "artifacts": [{"path": nested_path, "sha256": nested_hash}],
                    "observedAt": fresh_stamp, "ageDays": 0,
                    "cases": 110,
                    "confusion": {"tp": 70, "fp": 0, "tn": 40, "fn": 0, "cannotTell": 0},
                    "perRule": {"fixture": {"tp": 70, "tn": 40, "fp": 0, "fn": 0}}}},
            "act-benchmark.json": {"schema": "designer-dude-act-benchmark/v1",
                "mode": "detectors", "status": "pass",
                "generatedAt": fresh_stamp,
                "source": {"manifestSha256": "a" * 64},
                "confusion": {"tp": 54, "fp": 0, "tn": 84, "fn": 0, "cannotTell": 0},
                "items": [{"sourceSha256": "a" * 64} for _ in range(138)]},
            "expert-correlation.json": {"schema": "designer-dude-evidence-gate/v1",
                "mode": "ratings", "status": "pass", "thresholds": {
                    "minProducts": 12, "minReviewers": 3, "minAgreementAlpha": .8,
                    "minSpearmanLower95": .7, "bootstrapIterations": 4000,
                    "minLinConcordance": .9, "maxMeanAbsoluteError": 5,
                    "maxAbsoluteBias": 3, "maxProductError": 10,
                    "minExpertScoreSpan": 80, "minHighProducts": 2,
                    "minLowProducts": 2, "minHighExpertScore": 90,
                    "maxLowExpertScore": 20,
                    "maxAgeDays": 90},
                "evidence": {"inputDigests": {"ratings": "a" * 64},
                             "inputArtifacts": [{"path": raw_input_path,
                                                 "sha256": raw_input_hash,
                                                 "kind": "raw-ratings-input"}],
                             "artifacts": [{"path": nested_path, "sha256": nested_hash}],
                             "observedAt": fresh_stamp, "ageDays": 0,
                             "count": 12, "krippendorffAlphaInterval": .95,
                             "strataCoverage": {
                                 "productCategory": ["commerce", "content", "enterprise"],
                                 "surfaceType": ["marketing", "workflow", "settings"],
                                 "qualityBand": ["low", "mid", "high"],
                                 "viewportClass": ["mobile", "desktop"]},
                             "reviewerPanel": {"profiled": 3, "affiliations": 3,
                                               "expertise": ["product-design", "accessibility"]},
                             "products": [{"artifact": nested_path, "artifactSha256": nested_hash,
                                 "expertMedian": i * 9,
                                 "strata": {"qualityBand":
                                 "low" if i < 4 else "mid" if i < 8 else "high"}}
                                 for i in range(12)],
                             "linConcordance": .99, "meanAbsoluteError": 1,
                             "meanBias": -1, "maxProductError": 1,
                             "expertScoreSpan": 99, "highProducts": 2, "lowProducts": 3,
                             "spearmanBootstrap95": [.85, 1]}},
            "calibration-verification.json": {
                "schema": "designer-dude-calibration-verification/v1", "status": "pass",
                "ageDays": 0, "artifactCount": 1, "errors": [],
                "artifacts": [{"path": snapshot_path, "sha256": snapshot_hash},
                              {"path": nested_path, "sha256": nested_hash}],
                "manifestSha256": snapshot_hash, "thresholds": {"maxAgeDays": 90}},
        }
        for credit in verified_cert["findings"]:
            semantic_docs[credit["evidence"]] = {
                "schema": "designer-dude-credit-evidence/v1", "status": "pass",
                "pillar": credit["pillar"], "criterion": credit["criterion"],
                "reviewer": "reviewer@example.test", "reviewedAt": fresh_stamp,
                "surfaces": credit["surfaces"],
                "observations": ["criterion verified on both pinned surfaces"],
                "artifacts": [{"path": nested_path, "sha256": nested_hash}],
            }
        for entry in manifest:
            full = os.path.join(tmp, entry["path"])
            if entry["path"] in semantic_docs:
                with open(full, "w") as fh:
                    json.dump(semantic_docs[entry["path"]], fh)
            else:
                with open(full, "wb") as fh:
                    fh.write(("evidence:" + entry["path"]).encode("utf8"))
            with open(full, "rb") as fh:
                entry["sha256"] = hashlib.sha256(fh.read()).hexdigest()
        ledger = os.path.join(tmp, "findings.json")
        if perfection_certification_problems(verified_cert, ledger, verify_artifacts=True):
            failures.append("  present hash-matched certification artifacts were rejected")
        missing_nested = json.loads(json.dumps(verified_cert))
        missing_nested["perfectionCertification"]["artifactManifest"] = [
            x for x in missing_nested["perfectionCertification"]["artifactManifest"]
            if x["path"] != nested_path]
        nested_errors = perfection_certification_problems(
            missing_nested, ledger, verify_artifacts=True)
        if not any("nested artifact is absent" in p for p in nested_errors):
            failures.append("  nested study artifacts could be omitted from artifactManifest")
        missing_raw = json.loads(json.dumps(verified_cert))
        missing_raw["perfectionCertification"]["artifactManifest"] = [
            x for x in missing_raw["perfectionCertification"]["artifactManifest"]
            if x["path"] != raw_input_path]
        raw_errors = perfection_certification_problems(
            missing_raw, ledger, verify_artifacts=True)
        if not any(raw_input_path in p and "absent" in p for p in raw_errors):
            failures.append("  raw external-study inputs could be omitted from artifactManifest")
        missing_snapshot = json.loads(json.dumps(verified_cert))
        missing_snapshot["perfectionCertification"]["artifactManifest"] = [
            x for x in missing_snapshot["perfectionCertification"]["artifactManifest"]
            if x["path"] != snapshot_path]
        snapshot_errors = perfection_certification_problems(
            missing_snapshot, ledger, verify_artifacts=True)
        if not any("snapshot manifest bytes are absent" in p for p in snapshot_errors):
            failures.append("  calibration snapshot bytes could be omitted from artifactManifest")
        with open(os.path.join(tmp, manifest[0]["path"]), "ab") as fh:
            fh.write(b"changed after review")
        artifact_errors = perfection_certification_problems(
            verified_cert, ledger, verify_artifacts=True)
        if not any("sha256 mismatch" in p for p in artifact_errors):
            failures.append("  changed certification artifact did not invalidate perfection")
        semantic_entry = next(x for x in manifest if x["path"] == "artifact-regression.json")
        semantic_path = os.path.join(tmp, semantic_entry["path"])
        with open(semantic_path, "w") as fh:
            json.dump({"status": "fail", "failures": ["visual regression"]}, fh)
        with open(semantic_path, "rb") as fh:
            semantic_entry["sha256"] = hashlib.sha256(fh.read()).hexdigest()
        semantic_errors = perfection_certification_problems(
            verified_cert, ledger, verify_artifacts=True)
        if not any("artifact regression evidence status" in p for p in semantic_errors):
            failures.append("  hash-valid failing artifact regression evidence was accepted")
        expert_entry = next(x for x in manifest if x["path"] == "expert-correlation.json")
        expert_path = os.path.join(tmp, expert_entry["path"])
        with open(expert_path, "w") as fh:
            json.dump({"schema": "designer-dude-evidence-gate/v1", "mode": "ratings",
                       "status": "fail", "reasons": ["rank correlation below threshold"]}, fh)
        with open(expert_path, "rb") as fh:
            expert_entry["sha256"] = hashlib.sha256(fh.read()).hexdigest()
        expert_errors = perfection_certification_problems(
            verified_cert, ledger, verify_artifacts=True)
        if not any("expert-score correlation evidence" in p for p in expert_errors):
            failures.append("  hash-valid failing expert-correlation evidence was accepted")
        weak_expert = json.loads(json.dumps(semantic_docs["expert-correlation.json"]))
        weak_expert["thresholds"]["minProducts"] = 1
        with open(expert_path, "w") as fh:
            json.dump(weak_expert, fh)
        with open(expert_path, "rb") as fh:
            expert_entry["sha256"] = hashlib.sha256(fh.read()).hexdigest()
        weak_errors = perfection_certification_problems(
            verified_cert, ledger, verify_artifacts=True)
        if not any("expert-score correlation evidence weakens" in p for p in weak_errors):
            failures.append("  hash-valid weakened expert-correlation policy was accepted")
        performance_entry = next(x for x in manifest if x["path"] == "performance.json")
        performance_path = os.path.join(tmp, performance_entry["path"])
        weak_performance = json.loads(json.dumps(semantic_docs["performance.json"]))
        weak_performance["thresholds"]["maxLcpMsP75"] = 9999
        with open(performance_path, "w") as fh:
            json.dump(weak_performance, fh)
        with open(performance_path, "rb") as fh:
            performance_entry["sha256"] = hashlib.sha256(fh.read()).hexdigest()
        performance_errors = perfection_certification_problems(
            verified_cert, ledger, verify_artifacts=True)
        if not any("performance evidence weakens" in p for p in performance_errors):
            failures.append("  hash-valid weakened Core Web Vitals policy was accepted")
        first_credit = verified_cert["findings"][0]
        credit_entry = next(x for x in manifest if x["path"] == first_credit["evidence"])
        credit_path = os.path.join(tmp, first_credit["evidence"])
        wrong_credit = json.loads(json.dumps(semantic_docs[first_credit["evidence"]]))
        wrong_credit["pillar"] = "not-the-claimed-pillar"
        with open(credit_path, "w") as fh:
            json.dump(wrong_credit, fh)
        with open(credit_path, "rb") as fh:
            credit_entry["sha256"] = hashlib.sha256(fh.read()).hexdigest()
        credit_errors = perfection_certification_problems(
            verified_cert, ledger, verify_artifacts=True)
        if not any("A+ credit evidence does not match its criterion" in p for p in credit_errors):
            failures.append("  hash-valid A+ evidence could certify the wrong pillar")
    if perfection_eligible(False, len(PILLARS), True, cert_ok):
        failures.append("  letter mode can certify a perfect score")
    if perfection_eligible(True, len(PILLARS) - 1, True, cert_ok):
        failures.append("  ten of eleven credits can certify a perfect score")
    if perfection_eligible(True, len(PILLARS), False, cert_ok):
        failures.append("  a manually supplied slop grade can certify a perfect score")
    if perfection_eligible(True, len(PILLARS), True, False):
        failures.append("  missing human certification can certify a perfect score")
    if not perfection_eligible(True, len(PILLARS), True, cert_ok):
        failures.append("  complete machine and human evidence cannot certify perfection")

    if failures:
        print("SELFTEST FAILED:")
        print("\n".join(failures))
        return 1
    print(f"selftest ok - {len(seen)} grades round-trip, weights sum to 100, "
          f"WCAG cap -> C+, provisional cap -> B+, perf cap -> A-, demotion maths "
          f"consistent, {len(ids)} A+ criteria, findings ceiling {all_at('A'):.2f}, "
          f"credit gate rejects incomplete claims, perfection artifacts hash- and semantics-verified")
    warn = currency_warning()
    if warn:
        print("note: " + warn)
    return 0


# ---------------- main ----------------

def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())

    p = argparse.ArgumentParser(add_help=True)
    for flag, name, weight in PILLARS:
        p.add_argument(f"--{flag}", help=f"{name} (weight {weight})")
    p.add_argument("--consistency", help="Cross-page consistency grade, feeds Brand Coherence")
    p.add_argument("--findings", help="Derive pillar grades from a findings JSON")
    p.add_argument("--json", dest="json_in", help="Read pillar letters from a JSON object")
    p.add_argument("--slop", help="AI Slop grade from probe-report.py. Required to score above %.0f: the top band is gated on measured slop, not on credits." % SLOP_GATE_CAP)
    p.add_argument("--wcag-fail", action="store_true",
                   help="Unresolved WCAG AA failure: caps Overall at C+")
    p.add_argument("--perf-unmeasured", action="store_true",
                   help="Core Web Vitals not measured on a production build: "
                        "caps Interaction & Performance at A-")
    p.add_argument("--provisional", default="",
                   help="Comma-separated pillars whose evidence was NOT captured; capped at B+")
    p.add_argument("--baseline", type=float, help="Prior overall score, to report a delta")
    p.add_argument("--target", type=float, help="Print the cheapest path to this composite")
    p.add_argument("--out-json", help="Write the scorecard as JSON for design-baseline.json")
    args = p.parse_args()

    grades, detail, doc, ignored = {}, {}, {}, 0
    slop_from_findings = False
    if args.findings:
        grades, detail, doc, ignored = grades_from_findings(args.findings)
        unresolved_wcag = [f for f in (doc if isinstance(doc, list) else doc.get("findings", []))
                           if str(f.get("status") or "confirmed").strip().lower() in
                           (COUNTS_AGAINST - {"candidate"}) and
                           str(f.get("wcag") or "").strip() in WCAG_AA_CRITERIA]
        if unresolved_wcag:
            args.wcag_fail = True
            print("WCAG cap derived from confirmed findings: " +
                  ", ".join(sorted({str(f.get('wcag')) for f in unresolved_wcag})))
        measured_slop = doc.get("slopMeasured", {}).get("grade")
        if measured_slop:
            slop_from_findings = True
            if args.slop and args.slop.strip().upper().replace("−", "-") != measured_slop.upper().replace("−", "-"):
                print(f"warning: --slop {args.slop} ignored; findings ledger measured {measured_slop}")
            args.slop = measured_slop
    if args.json_in:
        with open(args.json_in) as fh:
            grades.update(json.load(fh))
    # Explicit letters always win over derived ones - a human overriding the
    # arithmetic is legitimate, but it is printed loudly below.
    overrides = {}
    for flag, _, _ in PILLARS:
        v = getattr(args, flag.replace("-", "_"))
        if v is not None:
            # Supplying an eye-only pillar's letter is REQUIRED, not an
            # override -- the probe cannot see hierarchy or IA, so a derived A
            # there means "nobody looked" and there is nothing to override.
            derived_from_evidence = detail.get(flag, {}).get("count", 0) > 0
            if flag in grades and grades[flag] != v and derived_from_evidence:
                overrides[flag] = (grades[flag], v)
            grades[flag] = v
    if args.consistency is not None:
        grades["consistency"] = args.consistency

    missing = [name for flag, name, _ in PILLARS if flag not in grades]
    if missing:
        sys.exit("error: missing grades for: " + ", ".join(missing) +
                 "\nScore every pillar. A skipped pillar is a silent A.")

    if args.findings:
        blind = [k for k in EYE_ONLY
                 if k in PILLAR_KEYS and detail.get(k, {}).get("count", 0) == 0
                 and k not in [f.replace("-", "_") for f in overrides]
                 and getattr(args, k, None) is None]
        if blind:
            sys.exit(
                "error: these pillars cannot be measured by the probe, and no findings were\n"
                "       recorded against them: " + ", ".join(blind) + "\n"
                "       'No findings' here means nobody looked, not that they are perfect.\n"
                "       Look at the page and pass an explicit letter, e.g. --hierarchy B+.\n"
                "       (Refusing to auto-award A on eye-only pillars is deliberate: it is\n"
                "       what stops a repeat-run campaign from inflating its own score.)")

    for flag, name, _ in PILLARS:
        to_number(grades[flag], name)
    if "consistency" in grades:
        to_number(grades["consistency"], "cross-page consistency")

    provisional = [x.strip() for x in args.provisional.split(",") if x.strip()]
    bad_prov = [x for x in provisional if x not in PILLAR_KEYS]
    if bad_prov:
        sys.exit(f"error: --provisional names non-pillars: {', '.join(bad_prov)}")

    print("Weighted composite")
    print("-" * 66)
    total = 0.0
    credited_pillars, blocked_credits = [], []
    for flag, name, weight in PILLARS:
        value = to_number(grades[flag], name)
        note = ""
        if detail.get(flag, {}).get("credit"):
            credited_pillars.append((flag, detail[flag]["credit"]))
            note += f"  [credit {detail[flag]['credit']}]"
        if detail.get(flag, {}).get("creditBlocked"):
            blocked_credits.append(flag)
        # Perf is half of Interaction & Performance. Grading it on observation
        # and then printing a letter is exactly the fabricated certainty this
        # skill exists to avoid, so an unmeasured pillar cannot read A or A+.
        if flag == "interaction" and args.perf_unmeasured and value > PERF_UNMEASURED_CAP:
            note += f"  (Core Web Vitals unmeasured: capped from {grades[flag]})"
            value = PERF_UNMEASURED_CAP
            grades[flag] = to_letter(value)
        if flag in provisional and value > PROVISIONAL_CAP:
            note += f"  (provisional: capped from {grades[flag]})"
            value = PROVISIONAL_CAP
            grades[flag] = to_letter(value)
        if flag in detail and detail[flag]["count"]:
            d = detail[flag]
            bits = ", ".join(f"{n}x{s[:4]}" for s, n in d["bySeverity"].items() if n)
            note += f"  [{bits} = -{d['cost']:.2f}]"
        contribution = value * weight / 100
        total += contribution
        print(f"  {name:<28} {grades[flag]:>3}  {value:>3} x {weight:>2} / 100 = "
              f"{contribution:6.2f}{note}")
    print("-" * 66)
    total = normalize(total)

    if credited_pillars:
        print(f"  A+ CREDITS ({len(credited_pillars)} of {len(PILLARS)} pillars) - each on a "
              f"named criterion, with evidence, on 2+ surfaces:")
        for flag, ident in credited_pillars:
            print(f"    {flag}: {ident}")
        if len(credited_pillars) > 4:
            print("    ** A+ is 'considered and delightful, rare'. More than four pillars")
            print("       claiming it is the shape of a scorecard that has stopped")
            print("       measuring. Re-read the criteria in scoring.md before quoting this. **")
    if blocked_credits:
        print("  CREDITS CLAIMED BUT BLOCKED by open findings on the same pillar: " +
              ", ".join(blocked_credits))
        print("    A credit records that a defect-free pillar went further. It never")
        print("    buys back points from a defect. Fix those findings first.")
    if args.perf_unmeasured:
        print("  PERF UNMEASURED: Core Web Vitals were not measured on a production build.")
        print("    Say so in the report; do not quote observed smoothness as a vitals result.")

    if overrides:
        print("  MANUAL OVERRIDES (derived -> yours):")
        for k, (was, now) in overrides.items():
            print(f"    {k}: {was} -> {now}   <- say why in the report; an unexplained")
            print(f"       override is how a scorecard stops measuring anything")

    slop_capped = False
    if total > SLOP_GATE_CAP:
        slop = (args.slop or "").strip().replace("−", "-").upper()
        have = GRADE_VALUES.get(slop)
        if have is None or have < GRADE_VALUES[SLOP_GATE_MIN]:
            print(f"  raw weighted sum                       {total:6.2f}")
            shown = slop if slop else "not measured"
            print(f"  slop gate ({shown}, needs {SLOP_GATE_MIN}) -> capped at   "
                  f"{SLOP_GATE_CAP:6.2f}")
            total = float(SLOP_GATE_CAP)
            slop_capped = True

    # 100 is a certification, not merely the top arithmetic result. Letter
    # mode has no findings ledger and cannot prove eleven A+ conjunctions.
    # Fewer than eleven credits can be exceptional, but cannot be perfect.
    perfection_capped = False
    certification_problems = (perfection_certification_problems(
                                  doc, ledger_path=args.findings, verify_artifacts=True)
                              if args.findings else ["findings mode is required"])
    certification_ok = not certification_problems
    if total >= 100 and not perfection_eligible(args.findings, len(credited_pillars),
                                                 slop_from_findings, certification_ok):
        print(f"  raw weighted sum                       {total:6.2f}")
        print(f"  perfection gate ({len(credited_pillars)}/{len(PILLARS)} verified credits, "
              f"findings mode={'yes' if args.findings else 'no'}, "
              f"measured slop={'yes' if slop_from_findings else 'no'}, "
              f"human certification={'yes' if certification_ok else 'no'}) -> capped at    99.00")
        if args.findings and certification_problems:
            print("  certification not accepted:")
            for problem in certification_problems:
                print(f"    - {problem}")
        total = 99.0
        perfection_capped = True

    capped = False
    if args.wcag_fail and total > WCAG_CAP:
        print(f"  raw weighted sum                       {total:6.2f}")
        print(f"  WCAG AA failure unresolved -> capped at {WCAG_CAP:6.2f}")
        total = float(WCAG_CAP)
        capped = True

    letter = to_letter(total)
    print(f"  OVERALL                                {total:6.2f}  ->  {letter}")
    if capped:
        print("  NOTE: cap applied. Fix the accessibility failure and rescore before")
        print("        quoting a higher grade. The cap is not a rounding rule.")
    if slop_capped:
        print(f"  NOTE: above {SLOP_GATE_CAP:.0f} the number is a claim of perfection, and")
        print(f"        perfection is gated on a MEASURED slop grade of {SLOP_GATE_MIN}.")
        print("        Remove the patterns probe-report.py is counting; do not argue them.")
    if perfection_capped:
        print("  NOTE: 100 requires findings mode, its embedded measured slop result,")
        print("        a verified A+ credit on every pillar, and a current attributable")
        print("        human certification across routes, viewports, states and keyboard/AT.")
        print("        A manual all-A+ card is an opinion; it is not a perfect-design certificate.")
    if provisional:
        print(f"  PROVISIONAL: {', '.join(provisional)} - evidence not captured this run.")

    print()
    print("Sub-scores")
    print("-" * 66)
    parts = []
    for label, flags in SUBSCORES.items():
        available = [f for f in flags if f in grades]
        if len(available) < len(flags):
            skipped = set(flags) - set(available)
            print(f"  {label:<18} incomplete (missing: {', '.join(sorted(skipped))})")
            continue
        avg = sum(to_number(grades[f], f) for f in available) / len(available)
        sub_letter = to_letter(avg)
        parts.append((label, sub_letter))
        print(f"  {label:<18} {avg:6.2f}  ->  {sub_letter}   "
              f"({', '.join(f'{f}={grades[f]}' for f in available)})")

    print()
    headline = f"Overall: {letter} ({math.floor(total)})"
    for label, sub_letter in parts:
        headline += f" · {label}: {sub_letter}"
    headline += f" · Slop: {args.slop}" if args.slop else " · Slop: <grade slop separately>"
    print("Headline line (paste inline):")
    print(f"  {headline}")

    if args.baseline is not None:
        delta = total - args.baseline
        print()
        if delta < -0.005:
            print(f"  *** REGRESSION: {args.baseline:.2f} -> {total:.2f} ({delta:+.2f}). "
                  f"Something went sideways. Say so loudly, at the top of the report. ***")
        elif delta > 0.005:
            print(f"  Improved: {args.baseline:.2f} -> {total:.2f} ({delta:+.2f})")
        else:
            print(f"  No change: {total:.2f}")

    if args.target:
        print()
        print(f"Path to {args.target:g}")
        print("-" * 66)
        print("  What the target costs, before choosing where to work:")
        for line in feasibility(args.target):
            print(line)
        findings_ceiling = all_at("A")
        if args.target > findings_ceiling:
            print()
            print(f"  ** {args.target:g} IS ABOVE THE FINDINGS CEILING OF {findings_ceiling:.2f}. **")
            print("     Fixing every defect on every pillar lands on a straight-A card and")
            print("     stops there. Above it, the number is a claim about excellence, and")
            print("     the only way up is an A+ credit per scoring.md: a named criterion,")
            print("     evidence, two or more surfaces, zero open findings on that pillar.")
            needed, reached = credit_plan(args.target, grades)
            if not needed and reached >= args.target:
                print(f"     Already there at {reached:.2f}.")
            elif not needed:
                print(f"     Even an all-A+ card reaches only {all_at('A+'):.2f}. Pick a real number.")
            else:
                print(f"     Cheapest route: {len(needed)} credit(s), heaviest pillars first.")
                for name, weight, running in needed:
                    print(f"       + {name:<28} (w{weight:>3})  -> {running:6.2f}")
                if reached < args.target:
                    print(f"     Every pillar at A+ still reaches only {reached:.2f}.")
                else:
                    print(f"     That is {len(needed)} of {len(PILLARS)} dimensions you would be "
                          f"declaring 'considered and")
                    print("     delightful, rare'. If that is not true of the product, the honest")
                    print("     move is to report the ceiling and hand back a design brief")
                    print("     (mode-f-campaign.md, 'When the ceiling is arithmetic') rather")
                    print("     than award the credits.")
        print()
        if capped:
            print("  ** Overall is CAPPED at C+ by an unresolved WCAG failure. No amount")
            print("     of typographic work moves the number until that is fixed. **")
            print()
        moves, reached = path_to_target(grades, args.target)
        if not moves and reached >= args.target:
            print(f"  Already at {reached:.2f}.")
        elif not moves:
            print(f"  Nothing left to move below A: findings ceiling reached at {reached:.2f}.")
            print("  Every further point is an A+ credit, and a credit is earned by the")
            print("  product being better, not by the review being run again.")
        else:
            print(f"  {'Pillar':<28} {'now':>3} -> {'to':<3} {'points':>7}  weight")
            for name, frm, to, gain, weight in moves:
                print(f"  {name:<28} {frm:>3} -> {to:<3} {gain:+7.2f}  {weight:>3}")
            if reached >= args.target:
                print(f"  → lands at {reached:.2f}. Ordered by points bought, so the top row is")
                print("    where the next run's effort belongs.")
            else:
                print(f"  → only reaches {reached:.2f} with every listed pillar at A.")
                print(f"    {args.target:g} is NOT reachable from here without an A+ credit:")
                print("    say that plainly instead of grinding another run for 0.4 points.")
            if capped:
                print("  (all of it is moot until the WCAG failure is resolved)")

    warn = currency_warning()
    if warn:
        print()
        print("CURRENCY: " + warn)

    if args.out_json:
        with open(args.out_json, "w") as fh:
            json.dump({
                "overall": normalize(total), "letter": letter,
                "cappedByWcag": capped, "provisional": provisional,
                "perfUnmeasured": bool(args.perf_unmeasured),
                "credits": {flag: ident for flag, ident in credited_pillars},
                "findingsCeiling": all_at("A"),
                "perfectionCertified": bool(total >= 100 and certification_ok),
                "perfectionCertificationProblems": certification_problems,
                "pillars": {k: grades[k] for k in PILLAR_KEYS},
                "consistency": grades.get("consistency"),
                "subScores": {label: g for label, g in parts},
                "slop": args.slop,
                "headline": headline,
                "derivation": detail or None,
            }, fh, indent=1)
        print(f"\nwrote {args.out_json}")


if __name__ == "__main__":
    main()
