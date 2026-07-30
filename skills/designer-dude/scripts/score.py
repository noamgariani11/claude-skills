#!/usr/bin/env python3
"""Deterministic scorer for designer-dude.

Two ways in:

  1. FINDINGS MODE (preferred) — derive every pillar grade from the confirmed
     findings, so a grade is a function of documented evidence:
       score.py --findings .design/findings-dashboard.json --slop B-
     Each pillar starts at A and is demoted by severity. Nothing is decided in
     anyone's head, which means the same evidence scores the same next week and
     a "run it again until it's 90+" campaign measures progress instead of mood.

  2. LETTERS MODE (back-compatible) — pass the twelve letters yourself:
       score.py --typography B- --hierarchy C ... --consistency B-

Both print the arithmetic, the composite, the four sub-scores, and a
ready-to-paste headline. Extras that matter for repeat runs:

  --target 90        exact cheapest path to a target score (which pillar
                     upgrades buy the most points per letter step)
  --provisional a,b  pillars whose evidence was NOT captured this run: they
                     are capped and labelled, never allowed to read as A
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
import datetime
import json
import math
import os
import re
import sys


def normalize(x):
    """Kill binary-float noise before any flooring or band comparison.

    Without this a true 92.00 accumulates as 91.99999999999999, prints as
    (91), and a score sitting exactly on a band floor lands one band low.
    """
    return round(x, 6)


# Letter -> number. ROUND-TRIP STABLE against BANDS: feed any letter's value
# back through to_letter() and you get the same letter. The older table
# (A+=100, A=95, A-=91 ...) was not -- A- came back as A, and a card of
# straight A pillars averaged to 95 and printed A+. That inflation is silent
# and always upward, which is the worst direction for a skill whose whole
# value is not flattering the work. Edit these and you must edit BANDS too:
#   python3 score.py --selftest
GRADE_VALUES = {
    "A+": 97, "A": 92, "A-": 88, "A−": 88,
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
    # Brand Coherence deliberately does not reuse Typography — that is already
    # measured inside Craft. It pairs voice with the cross-page check.
    "Brand Coherence": ["content", "consistency"],
}

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
        "All seven states designed for every interactive element, and Core Web "
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
        "the 2.2 SCs most sites miss (2.4.11, 2.5.7, 2.5.8, 3.3.7, 3.3.8), and "
        "at least one thing done for assistive tech that no checker asked for.",
    ),
    "responsive": (
        "responsive.designed-breakpoints",
        "Each breakpoint is a layout decision with its own reason, tables have a "
        "real small-screen answer rather than a squeeze, and 320px is as "
        "considered as 1440px.",
    ),
    "craft": (
        "craft.decided-details",
        "Every detail visibly answered a question: disciplined radius and shadow "
        "scales, one light source, deterministic sort on ties, aligned decimals, "
        "clean console, correct-DPR assets. Decided, not assembled.",
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
    if not isinstance(surfaces, list) or len(surfaces) < CREDIT_MIN_SURFACES:
        problems.append(f"needs 'surfaces' naming >={CREDIT_MIN_SURFACES} probed surfaces "
                        f"(got {len(surfaces) if isinstance(surfaces, list) else 0}) -- "
                        f"excellence shown on one page scores the page")
    status = (entry.get("status") or "confirmed").strip().lower()
    if status not in {"confirmed", "verified", "fixed"}:
        problems.append(f"status '{status}' is not confirmed")
    return problems


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
    +5 letter-points, so the cheapest route is always the heaviest pillar.
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
    # The lowest uniform grade that clears the target — the honest answer to
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
        return "canon.md has no 'Last verified:' date — the currency layer cannot be trusted."
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
    if all_at("A+") != 97.0:
        failures.append(f"  all-A+ card scores {all_at('A+')}, expected 97.00")
    needed, reached = credit_plan(95.0)
    if reached < 95.0 or len(needed) < 2:
        failures.append(f"  credit_plan(95) returned {len(needed)} credits reaching {reached}")
    if credit_plan(92.0)[0]:
        failures.append("  credit_plan(92) asks for credits to reach the findings ceiling")
    if credit_plan(99.0)[1] < all_at("A+") - 0.001:
        failures.append("  credit_plan(99) did not exhaust every pillar before giving up")

    # A credit must be rejected for each missing element, and accepted only
    # when all of them are present.
    good = {"kind": "credit", "criterion": A_PLUS_CRITERIA["motion"][0],
            "evidence": ".design/probe-dashboard.json", "surfaces": ["a", "b"],
            "status": "confirmed"}
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
    if not credit_problems(good, "craft"):
        failures.append("  motion's criterion was accepted as a credit for craft")

    if failures:
        print("SELFTEST FAILED:")
        print("\n".join(failures))
        return 1
    print(f"selftest ok — {len(seen)} grades round-trip, weights sum to 100, "
          f"WCAG cap -> C+, provisional cap -> B+, perf cap -> A-, demotion maths "
          f"consistent, {len(ids)} A+ criteria, findings ceiling {all_at('A'):.2f}, "
          f"credit gate rejects incomplete claims")
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
    p.add_argument("--slop", help="AI Slop grade (from probe-report.py, or judged by eye)")
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
    if args.findings:
        grades, detail, doc, ignored = grades_from_findings(args.findings)
        if doc.get("slopMeasured", {}).get("grade") and not args.slop:
            args.slop = doc["slopMeasured"]["grade"]
    if args.json_in:
        with open(args.json_in) as fh:
            grades.update(json.load(fh))
    # Explicit letters always win over derived ones — a human overriding the
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
        print(f"  A+ CREDITS ({len(credited_pillars)} of {len(PILLARS)} pillars) — each on a "
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
    if provisional:
        print(f"  PROVISIONAL: {', '.join(provisional)} — evidence not captured this run.")

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
