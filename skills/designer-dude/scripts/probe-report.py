#!/usr/bin/env python3
"""probe-report — turn probe.js measurements into severity-tagged candidates.

The probe measures. This judges, with thresholds that live in source rather
than in the model's head, so two runs a week apart grade the same page the
same way. That is the whole point: a score you can move by re-reading the
rubric in a better mood is not a score.

    python3 probe-report.py .design/probe-dashboard.json
    python3 probe-report.py .design/probe-dashboard.json --emit-findings .design/findings-dashboard.json
    python3 probe-report.py .design/probe-fixture.json --expect-fixture

Every row is a CANDIDATE. The model confirms, rejects, or reclassifies each
one, adds the findings only a human eye can see (hierarchy, voice, IA, taste),
and feeds the merged file to score.py. Nothing here is allowed to become a
finding on its own -- see the confirmation rules in mode-d-review.md.
"""

import argparse
import json
import sys

# Severity vocabulary shared with scoring.md and score.py.
CRIT, MAJOR, MINOR, PETTY = "critical", "major", "minor", "petty"

# WCAG success criteria that trigger the hard cap when CONFIRMED.
WCAG_TRIGGERS = {"1.4.3", "1.4.11", "2.4.7", "1.1.1", "3.3.2", "2.5.8", "4.1.2", "1.3.1"}


class Report:
    def __init__(self):
        self.rows = []
        self.n = 0

    def add(self, pillar, severity, measured, threshold, summary, evidence=None,
            sc=None, kind="rule", fix=None):
        """kind: 'rule' (measurable, defensible) or 'taste' (period fashion)."""
        self.n += 1
        self.rows.append({
            "id": f"P{self.n:03d}",
            "pillar": pillar, "severity": severity, "kind": kind,
            "measured": measured, "threshold": threshold,
            "summary": summary, "wcag": sc,
            "evidence": (evidence or [])[:4], "fix": fix,
            "source": "probe", "status": "candidate",
        })


def get(d, *path, default=None):
    cur = d
    for p in path:
        if cur is None:
            return default
        cur = cur.get(p) if isinstance(cur, dict) else None
    return default if cur is None else cur


def sel_list(items, key="sel", extra=None):
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            out.append(str(it))
            continue
        s = it.get(key, "?")
        if extra:
            bits = " ".join(f"{k}={it.get(k)}" for k in extra if it.get(k) is not None)
            s = f"{s} [{bits}]"
        out.append(s)
    return out


def analyse(payload):
    r = Report()
    runs = payload.get("runs", [])
    if not runs:
        print("No probe runs in the payload.", file=sys.stderr)
        sys.exit(2)

    def by_tag(pred):
        return [x for x in runs if pred(x.get("tag", ""))]

    light = [x for x in runs if not x.get("tag", "").startswith(("dark", "reduced"))]
    primary = max(light or runs, key=lambda x: get(x, "meta", "viewport", "w", default=0))
    dark = next((x for x in runs if x.get("tag", "").startswith("dark")), None)
    reduced = next((x for x in runs if x.get("tag", "").startswith("reduced")), None)

    # ---------------- Colour & contrast ----------------
    for run in light:
        tag = run.get("tag", "?")
        tc = get(run, "color", "textContrast", default={})
        fails = tc.get("failures", 0)
        if fails:
            worst = sorted(tc.get("failureList", []), key=lambda f: f.get("ratio", 99))[:4]
            r.add("color", CRIT, f"{fails} of {tc.get('checked', 0)} text nodes below AA @{tag}",
                  "0 failures", sc="1.4.3",
                  summary=f"{fails} text elements fail WCAG AA contrast at {tag}; "
                          f"worst {worst[0].get('ratio')}:1 needs {worst[0].get('required')}:1",
                  evidence=[f"{f['sel']} — {f['ratio']}:1 (needs {f['required']}, Lc{f.get('apcaLc')}) "
                            f"{f['fg']} @{f['fontSize']}px w{f['weight']} '{f.get('text','')[:24]}'"
                            for f in worst],
                  fix="Darken the token or raise size/weight; recheck with contrast.py before committing.")
            break   # one finding per page, not one per viewport

    nt = get(primary, "color", "nonTextContrast", default={})
    if nt.get("fieldBorderFailures"):
        r.add("color", CRIT, f"{nt['fieldBorderFailures']} field borders below 3:1", "3:1 minimum",
              sc="1.4.11", summary="Form-field borders fail WCAG 1.4.11 non-text contrast (3:1)",
              evidence=sel_list(nt.get("list"), extra=["ratio", "borderColor"]),
              fix="Use a dedicated field-border token at >=3:1 against the field's backdrop.")

    accent = get(primary, "color", "accentPixelShare", default=0)
    if accent > 25:
        r.add("color", CRIT, f"accent covers {accent}% of the viewport", "<=10%",
              summary=f"Chromatic fills cover {accent}% of the viewport; the accent has stopped "
                      f"being an accent, so nothing reads as primary",
              evidence=sel_list(get(primary, "color", "chromaticFills", default=[]), key="value", extra=["count"]),
              fix="Cut accent to a single primary action per screen; move the rest to surface tokens.")
    elif accent > 10:
        r.add("color", MAJOR, f"accent covers {accent}% of the viewport", "<=10%",
              summary=f"Accent covers {accent}% of the viewport (Refactoring UI: keep it under ~10%)",
              evidence=sel_list(get(primary, "color", "chromaticFills", default=[]), key="value", extra=["count"]))

    if get(primary, "color", "pureBlackOrWhiteText", default=0) > 0:
        r.add("color", MINOR, f"{get(primary,'color','pureBlackOrWhiteText')} elements use pure #000/#fff text",
              "0", kind="taste",
              summary="Pure black or white text (Refactoring UI: tint both toward the surface hue)",
              fix="Swap for a near-black/near-white token with the surface's undertone.")

    dtc = get(primary, "color", "distinctTextColors", default=0)
    if dtc > 8:
        r.add("color", MINOR, f"{dtc} distinct text colours", "<=6",
              summary=f"{dtc} distinct text colours in play; a semantic set is ink/body/muted/inverse "
                      f"plus semantic states",
              evidence=sel_list(get(primary, "color", "textColors", default=[]), key="value", extra=["count"]))

    # Dark mode: designed, or inverted?
    if dark:
        dfails = get(dark, "color", "textContrast", "failures", default=0)
        lfails = get(primary, "color", "textContrast", "failures", default=0)
        if dfails > max(lfails, 0):
            r.add("color", CRIT if dfails else MAJOR,
                  f"dark mode has {dfails} contrast failures vs {lfails} in light", "parity with light",
                  sc="1.4.3", summary="Dark mode fails contrast where light mode passes — inverted, not designed",
                  evidence=[f"{f['sel']} — {f['ratio']}:1 {f['fg']}"
                            for f in get(dark, "color", "textContrast", "failureList", default=[])[:4]],
                  fix="Give dark its own palette: lower accent saturation, warm the neutrals, re-check every pairing.")

    # ---------------- Typography ----------------
    ty = get(primary, "typography", default={})
    fams = ty.get("distinctFamilies", 0)
    if fams > 3:
        r.add("typography", MAJOR, f"{fams} font families rendered", "<=3 (display + UI + mono)",
              summary=f"{fams} distinct font families on one page reads as assembled, not decided",
              evidence=sel_list(ty.get("families", []), key="value", extra=["count"]))

    used = ty.get("sizesUsedTwicePlus", []) or []
    if len(used) > 9:
        r.add("typography", MAJOR, f"{len(used)} font sizes each used 2+ times", "6-8 steps",
              summary=f"{len(used)} type sizes in real use — that is a pile, not a scale",
              evidence=[f"sizes: {used}"],
              fix="Collapse to a ratio scale (1.2/1.25/1.333) and map every use to a named step.")
    near = [x for x in (ty.get("adjacentRatios") or []) if x < 1.07]
    if len(near) >= 2:
        r.add("typography", MINOR, f"{len(near)} adjacent size steps under 1.07x", ">=1.125x between steps",
              summary="Adjacent type sizes are near-duplicates (e.g. 13/14px), so the scale does not read as intentional",
              evidence=[f"ratios: {ty.get('adjacentRatios')}"])

    m = ty.get("measureCh") or {}
    if m.get("median"):
        med = m["median"]
        if med > 78 or med < 45:
            r.add("typography", MAJOR, f"median measure {med}ch (min {m.get('min')}, max {m.get('max')})",
                  "45-75ch (Lupton)",
                  summary=f"Body measure runs at {med}ch; comfortable reading is 45-75ch",
                  evidence=sel_list(get(ty, "offenders", "measureOutOfBand", default=[]), extra=["measureCh"]),
                  fix="Cap the reading column with a max-width in ch, not px.")

    lead = get(ty, "offenders", "leadingOutOfBand", default=[])
    if lead:
        r.add("typography", MINOR, f"{len(lead)} long-copy blocks outside 1.35-1.75 leading", "1.4-1.6 body",
              summary="Body leading sits outside the comfortable band",
              evidence=sel_list(lead, extra=["size", "leading"]))

    q = ty.get("straightQuotes") or {}
    if q.get("apostrophes", 0) > 0 and q.get("apostrophes", 0) > q.get("properApostrophes", 0):
        r.add("typography", MINOR, f"{q['apostrophes']} straight apostrophes vs {q.get('properApostrophes',0)} typographic",
              "typographic marks", kind="taste", sc=None,
              summary="Straight apostrophes/quotes in rendered copy (Bringhurst)",
              fix="Use ’ and “ ” in copy strings, or a smartypants transform at render.")

    fam_names = [f.get("value", "") for f in ty.get("families", [])]
    slopfaces = [f for f in fam_names[:1] if f in ("Inter", "Roboto", "Poppins", "Montserrat", "Arial", "Helvetica")]
    if slopfaces:
        r.add("typography", MAJOR, f"primary rendered face is {slopfaces[0]}", "a face with a voice",
              kind="taste",
              summary=f"{slopfaces[0]} is the most-used face on the page — a competent fallback doing the "
                      f"job of a voice",
              fix="Pick a display face with a point of view; keep the neutral sans for UI chrome only.")

    # ---------------- Spacing & system ----------------
    sy = get(primary, "system", default={})
    off = get(sy, "spacing", "offFourBaseCount", default=0)
    offvals = get(sy, "spacing", "offFourBase", default=[])
    if len(offvals) > 6:
        r.add("spacing", MAJOR, f"{len(offvals)} distinct off-4px spacing values", "all on a 4/8 base",
              summary=f"{len(offvals)} spacing values sit off the 4px base; the grid is not being felt",
              evidence=[f"off-base: {offvals[:14]}"],
              fix="Snap to the token scale; keep 1-2px only for hairlines and optical corrections.")
    elif len(offvals) > 2:
        r.add("spacing", MINOR, f"{len(offvals)} off-4px spacing values", "all on a 4/8 base",
              summary="A few spacing values drift off the base scale", evidence=[f"off-base: {offvals[:10]}"])

    sdist = get(sy, "spacing", "distinct", default=0)
    if sdist > 24:
        r.add("spacing", MAJOR, f"{sdist} distinct padding/margin values", "6-8 named steps",
              summary=f"{sdist} distinct spacing values means the rhythm is per-component improvisation",
              evidence=sel_list(get(sy, "spacing", "top", default=[]), key="value", extra=["count"]))

    rad = get(sy, "radius", "distinct", default=0)
    if rad > 5:
        r.add("craft", MAJOR, f"{rad} distinct border-radius values", "2-3 + pill",
              summary=f"{rad} radii in use; a radius scale is 2-3 meaningful values plus a pill",
              evidence=sel_list(get(sy, "radius", "top", default=[]), key="value", extra=["count"]))
    elif rad == 1:
        r.add("craft", MINOR, "one radius value everywhere", "2-3 meaningful values", kind="taste",
              summary="A single uniform radius on everything is the shadcn-default tell — no radius hierarchy")

    sh = get(sy, "shadow", "distinct", default=0)
    if sh > 5:
        r.add("craft", MINOR, f"{sh} distinct box-shadows", "3-4 elevation steps",
              summary=f"{sh} distinct shadows cannot share one light source; elevation reads incoherent",
              evidence=sel_list(get(sy, "shadow", "top", default=[]), key="value", extra=["count"]))

    z = get(sy, "zIndex", "distinct", default=0)
    if z > 8:
        r.add("craft", MINOR, f"{z} distinct z-index values", "4-6 named layers",
              summary=f"{z} z-index values: nobody owns the stacking model",
              evidence=[f"values: {get(sy,'zIndex','values',default=[])[:12]}"])

    # ---------------- Interaction & performance ----------------
    it = get(primary, "interaction", default={})
    fr = it.get("focusRing") or {}
    if fr.get("invisible"):
        r.add("interaction", CRIT, f"{fr['invisible']} of {fr.get('tested')} focused elements showed no visual change",
              "every focusable element", sc="2.4.7",
              summary=f"{fr['invisible']} focusable elements have no visible focus indicator (WCAG 2.4.7 AA)",
              evidence=sel_list(fr.get("list"), extra=["text"]),
              fix="Add a :focus-visible ring token with >=3:1 against both the element and its surround.")

    t24 = it.get("belowWcagTarget24") or {}
    if t24.get("count"):
        r.add("interaction", CRIT, f"{t24['count']} targets under 24x24 CSS px", ">=24x24 (2.5.8), aim 44",
              sc="2.5.8", summary=f"{t24['count']} interactive targets are below the WCAG 2.5.8 minimum",
              evidence=sel_list(t24.get("list"), extra=["w", "h", "text"]),
              fix="Grow the hit area with padding (keep the visual size) or a ::before overlay.")
    t44 = it.get("belowFittsTarget44") or {}
    if t44.get("count"):
        r.add("interaction", MINOR, f"{t44['count']} targets between 24 and 44px", "44px (Fitts)",
              summary=f"{t44['count']} targets clear WCAG but sit under the 44px comfortable minimum",
              evidence=sel_list(t44.get("list"), extra=["w", "h"]))

    mp = it.get("missingPointerCursor") or {}
    if mp.get("count"):
        r.add("interaction", MINOR, f"{mp['count']} clickable elements without cursor:pointer", "pointer on all",
              summary="Clickable elements render the default cursor — a signifier failure (Norman)",
              evidence=sel_list(mp.get("list"), extra=["cursor", "text"]),
              fix="Add cursor-pointer to the interactive base class, not per component.")

    perf = payload.get("performance") or {}
    if perf:
        lab = " (LAB, one machine — not p75 CrUX)"
        lcp, cls = perf.get("largestContentfulPaint"), perf.get("cumulativeLayoutShift")
        if lcp and lcp > 2500:
            r.add("interaction", MAJOR, f"lab LCP {lcp}ms", "<=2500ms at p75",
                  summary=f"LCP measures {lcp}ms{lab}; the budget is 2.5s and perf is UX",
                  fix="Find the LCP element, reserve its box, preload it, and cut render-blocking work.")
        if cls is not None and cls > 0.1:
            r.add("interaction", MAJOR, f"lab CLS {cls}", "<0.1 at p75",
                  summary=f"CLS measures {cls}{lab}; unreserved media or late-injected banners shift the layout")
        tb = perf.get("transferBytes") or 0
        if tb > 2_500_000:
            r.add("interaction", MINOR, f"{round(tb/1024/1024,2)}MB transferred", "<2.5MB",
                  summary="Page weight is high enough to be a design decision, not just an engineering one",
                  evidence=[f"by initiator: {perf.get('transferByInitiator')}"])
        dn = perf.get("domNodes") or 0
        if dn > 3000:
            r.add("interaction", MINOR, f"{dn} DOM nodes", "<3000",
                  summary=f"{dn} DOM nodes; INP suffers long before this is a rendering problem")

    if payload.get("consoleErrors"):
        r.add("craft", MAJOR, f"{len(payload['consoleErrors'])} console errors", "0",
              summary="The page logs errors in a real browser — craft is not finished while the console is red",
              evidence=payload["consoleErrors"][:3])

    # ---------------- Accessibility ----------------
    a = get(primary, "a11y", default={})
    for key, sev, sc, label, fix in [
        ("imagesMissingAlt", CRIT, "1.1.1", "images without an alt attribute",
         'Add alt text, or alt="" if genuinely decorative.'),
        ("fieldsMissingLabel", CRIT, "3.3.2", "form fields with no accessible label",
         "Add a <label for>, or aria-label where a visible label is impossible."),
        ("controlsMissingAccessibleName", CRIT, "4.1.2", "controls with no accessible name",
         "Icon-only buttons need aria-label; links need discernible text."),
    ]:
        node = a.get(key) or {}
        if node.get("count"):
            r.add("a11y", sev, f"{node['count']} {label}", "0", sc=sc,
                  summary=f"{node['count']} {label} (WCAG {sc})",
                  evidence=sel_list(node.get("list"), extra=["type", "src", "html"]), fix=fix)

    po = a.get("fieldsPlaceholderOnly") or {}
    if po.get("count"):
        r.add("a11y", MAJOR, f"{po['count']} fields labelled by placeholder only", "persistent visible label",
              sc="3.3.2", summary="Placeholder-as-label disappears on input and fails at zoom and for screen readers",
              evidence=sel_list(po.get("list"), extra=["placeholder"]))

    hd = a.get("headings") or {}
    if hd.get("skippedLevels"):
        r.add("a11y", MAJOR, f"{len(hd['skippedLevels'])} skipped heading levels", "sequential",
              sc="1.3.1", summary="Heading levels skip, so the document outline lies to assistive tech",
              evidence=[f"{s['from']} -> {s['to']} '{s.get('text','')[:30]}'" for s in hd["skippedLevels"][:4]])
    if hd.get("h1", 0) == 0:
        r.add("hierarchy", MAJOR, "no h1 on the page", "exactly one",
              summary="No h1: neither the eye nor the outline has a stated subject")
    elif hd.get("h1", 0) > 1:
        r.add("hierarchy", MINOR, f"{hd['h1']} h1 elements", "exactly one",
              summary=f"{hd['h1']} h1s compete for the page's subject")

    if a.get("ariaHiddenContainingFocusable"):
        r.add("a11y", CRIT, f"{a['ariaHiddenContainingFocusable']} aria-hidden containers hold focusable children",
              "0", sc="4.1.2",
              summary="Focusable elements inside aria-hidden are reachable by keyboard but invisible to screen readers")
    if a.get("positiveTabindex"):
        r.add("a11y", MAJOR, f"{a['positiveTabindex']} elements with positive tabindex", "0",
              sc="2.4.3", summary="Positive tabindex hijacks tab order away from DOM order")
    if a.get("duplicateIds", {}).get("count"):
        r.add("a11y", MINOR, f"{a['duplicateIds']['count']} duplicate ids", "0",
              summary="Duplicate ids break label/for and aria-labelledby wiring",
              evidence=a["duplicateIds"].get("list"))
    if not a.get("lang"):
        r.add("a11y", MAJOR, "no lang on <html>", 'lang="xx"', sc="3.1.1",
              summary="Missing document language: screen readers pick the wrong voice")
    lm = a.get("landmarks") or {}
    if lm.get("main", 0) == 0:
        r.add("a11y", MAJOR, "no <main> landmark", "one main", sc="1.3.1",
              summary="No main landmark, so skip-to-content and rotor navigation have nothing to target")
    if not a.get("skipLink") and lm.get("nav", 0) >= 1:
        r.add("a11y", MINOR, "no skip link with a nav present", "skip link", sc="2.4.1",
              summary="Keyboard users tab the whole nav on every page load")

    # ---------------- Responsiveness ----------------
    for run in light:
        if get(run, "layout", "horizontalOverflow", default=False):
            w = get(run, "meta", "viewport", "w", default="?")
            r.add("responsive", CRIT if int(w or 0) <= 400 else MAJOR,
                  f"document scrolls horizontally at {w}px "
                  f"({get(run,'layout','scrollWidth')} > {get(run,'layout','clientWidth')})",
                  "no unintended horizontal scroll",
                  summary=f"Unintended horizontal scroll at {w}px wide",
                  evidence=sel_list(get(run, "layout", "overflowingElements", default=[]), extra=["right", "width"]),
                  fix="Find the element wider than the viewport; usually a fixed px width or an unwrapped table.")
    small = [x for x in light if get(x, "meta", "viewport", "w", default=9999) <= 430]
    if not small:
        r.add("responsive", MINOR, "no viewport <=430px probed", "320 and 390 probed",
              summary="Mobile widths were not measured — Responsiveness cannot be graded above provisional")
    for run in small:
        t = get(run, "interaction", "belowWcagTarget24", "count", default=0)
        if t:
            r.add("responsive", MAJOR, f"{t} sub-24px targets at {get(run,'meta','viewport','w')}px", "0",
                  sc="2.5.8", summary="Targets shrink below the minimum at mobile width",
                  evidence=sel_list(get(run, "interaction", "belowWcagTarget24", "list", default=[]), extra=["w", "h"]))

    # ---------------- Motion ----------------
    mo = get(primary, "motion", default={})
    if reduced:
        before = mo.get("animatedElements", 0)
        after = get(reduced, "motion", "animatedElements", default=0)
        if before and after >= before:
            r.add("motion", MAJOR, f"{after} animated elements still running under prefers-reduced-motion",
                  "motion stops or shortens", sc="2.3.3",
                  summary="prefers-reduced-motion is ignored: the same animations run with the preference set",
                  fix="Wrap keyframes/transitions in @media (prefers-reduced-motion: no-preference), or zero them out.")
    elif mo.get("animatedElements"):
        r.add("motion", MINOR, f"{mo['animatedElements']} animated elements, reduced-motion not probed",
              "probe with reducedMotion:true",
              summary="Motion exists but the reduced-motion pass was not run — Motion stays provisional")
    if (mo.get("infiniteAnimations") or {}).get("count"):
        r.add("motion", MINOR, f"{mo['infiniteAnimations']['count']} infinite animations", "finite, or purposeful",
              summary="Infinite animation draws the eye forever; it should be a spinner, not decoration",
              evidence=sel_list(mo["infiniteAnimations"].get("list"), extra=["name", "duration"]))
    if mo.get("transitionsOver600ms"):
        r.add("motion", MINOR, f"{len(mo['transitionsOver600ms'])} transitions over 600ms", "150-300ms UI",
              summary="Transitions long enough to feel like lag rather than continuity",
              evidence=sel_list(mo["transitionsOver600ms"], extra=["duration", "property"]))
    if (mo.get("transitionPropertyAll") or 0) > 30:
        r.add("motion", PETTY, f"{mo['transitionPropertyAll']} elements transition `all`", "named properties",
              summary="transition: all animates properties nobody chose, including layout ones")

    # ---------------- Content & voice ----------------
    sl = get(primary, "slop", default={})
    gen = sl.get("genericMarketingCopy") or []
    if gen:
        r.add("content", MAJOR, f"{len(gen)} generic marketing phrases", "specific nouns and verbs",
              kind="taste", summary="Copy leans on category filler that says nothing about this product",
              evidence=[f'"{g}"' for g in gen[:5]],
              fix="Replace each with the specific claim: what it does, for whom, with a number if you have one.")
    if sl.get("aiBadgeCopy"):
        r.add("content", MAJOR, f"{len(sl['aiBadgeCopy'])} 'powered by <model>' badges", "0", kind="taste",
              summary="Model-provider badges advertise the dependency, not the product",
              evidence=sl["aiBadgeCopy"])
    em = sl.get("emojiInHeadingsOrButtons") or {}
    if em.get("count"):
        r.add("content", MINOR, f"{em['count']} emoji in headings/buttons", "0", kind="taste",
              summary="Emoji standing in for iconography or enthusiasm",
              evidence=sel_list(em.get("list"), extra=["text"]))

    # ---------------- Enterprise app surfaces ----------------
    for t in get(primary, "app", "tables", default=[]):
        if t.get("rows", 0) < 3:
            continue
        if not t.get("hasScope") and t.get("columns"):
            r.add("a11y", MAJOR, f"table with {t['columns']} headers has no scope", "th[scope]",
                  sc="1.3.1", summary="Data table headers are not associated with their cells",
                  evidence=[t.get("sel", "?")])
        if t.get("numericCells", 0) >= 4 and t.get("numericRightAligned", 0) < t["numericCells"] / 2:
            r.add("craft", MINOR,
                  f"{t['numericCells']} numeric cells, only {t.get('numericRightAligned',0)} right-aligned",
                  "numerals right-aligned",
                  summary="Numeric columns are not right-aligned, so magnitudes cannot be compared by eye (Tufte)",
                  evidence=[t.get("sel", "?")],
                  fix="Right-align numerals and use tabular-nums so digits line up.")
        if t.get("rows", 0) > 15 and not t.get("stickyHeader"):
            r.add("ia", MINOR, f"{t['rows']}-row table without a sticky header", "sticky header past ~15 rows",
                  summary="Column meaning scrolls away on a long table", evidence=[t.get("sel", "?")])
        mrh = t.get("medianRowHeight")
        if mrh and mrh > 72:
            r.add("spacing", MINOR, f"table row height {mrh}px", "40-56px",
                  summary=f"{mrh}px rows put very little data on screen for a review surface",
                  evidence=[t.get("sel", "?")])

    # ---------------- Craft / meta ----------------
    meta = get(primary, "meta", default={})
    if not meta.get("title"):
        r.add("craft", MAJOR, "no document title", "a real title",
              summary="Missing <title>: the tab, history, and search results have nothing to show")
    if not meta.get("hasFavicon"):
        r.add("craft", MINOR, "no favicon link", "favicon present",
              summary="No favicon — the tab shows a default glyph")
    if not meta.get("hasViewportMeta"):
        r.add("responsive", CRIT, "no viewport meta tag", "width=device-width",
              summary="Without a viewport meta the mobile layout is a scaled-down desktop page")
    if meta.get("elementsTruncated"):
        r.add("craft", PETTY, "probe hit its element cap", "raise maxElements",
              summary="The page has more elements than the probe scanned; counts are lower bounds")

    return r, {"primary": primary, "dark": dark, "reduced": reduced, "light": light}


# --------------- slop grade (deterministic) ---------------
SLOP_RULES = [
    # (key, predicate, weight in letters, label)
    ("purpleOrIndigoGradients", lambda v: v >= 1, 1.0, "blue/indigo->purple gradient"),
    ("largeRadialGradients", lambda v: v >= 1, 1.0, "gradient-mesh/orb hero"),
    ("threeUpFeatureGrids", lambda v: v >= 1, 1.0, "symmetrical three-up feature grid"),
    ("backdropBlurElements", lambda v: v >= 6, 1.0, "glassmorphism on everything"),
    ("centredShare", lambda v: v >= 60, 1.0, "centred-everything layout"),
    ("iconsInColouredCircles", lambda v: v >= 3, 0.5, "icons in coloured circles"),
    ("colouredLeftBorderCards", lambda v: v >= 2, 0.5, "coloured left-border cards"),
    ("gradientClippedText", lambda v: v >= 1, 0.5, "gradient text on headlines"),
    ("grayscaleLogoStrips", lambda v: v >= 1, 0.25, "grayscale logo strip"),
]
SLOP_LADDER = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"]


def slop_grade(primary):
    sl = get(primary, "slop", default={})
    hits, drop = [], 0.0
    for key, pred, weight, label in SLOP_RULES:
        v = sl.get(key)
        if isinstance(v, dict):
            v = v.get("count", 0)
        if v is None:
            continue
        if pred(v):
            hits.append((label, weight, v))
            drop += weight
    gen = len(sl.get("genericMarketingCopy") or [])
    if gen:
        w = 0.5 if gen < 3 else 1.0
        hits.append((f"generic hero/marketing copy ({gen} phrases)", w, gen)); drop += w
    em = (sl.get("emojiInHeadingsOrButtons") or {}).get("count", 0)
    if em:
        hits.append((f"emoji as design elements ({em})", 0.5, em)); drop += 0.5
    if sl.get("aiBadgeCopy"):
        hits.append(("'powered by <model>' badge", 0.25, len(sl["aiBadgeCopy"]))); drop += 0.25
    # Each full letter is 3 quarter-steps on the ladder above.
    steps = int(round(drop * 3))
    grade = SLOP_LADDER[min(steps, len(SLOP_LADDER) - 1)]
    return grade, drop, hits


# --------------- output ---------------
COVERED = {
    "typography": "probe measures families, scale, measure, leading",
    "color": "probe measures every rendered contrast pair",
    "spacing": "probe measures the real spacing set",
    "interaction": "probe tests focus, cursors, target sizes, lab perf",
    "a11y": "probe tests names, labels, landmarks, outline, tab order",
    "responsive": "probe sweeps viewports for overflow and target shrink",
    "craft": "probe measures radius/shadow/z scale, console, meta",
    "motion": "probe compares a reduced-motion pass",
    "content": "probe matches known filler copy only",
}
HUMAN_ONLY = {
    "hierarchy": "where the eye lands first, and whether that is the primary action",
    "ia": "whether the nav matches the user's mental model and vocabulary",
    "content": "whether the copy is TRUE, specific, and in the brand's voice",
    "consistency": "whether 3+ pages look like one product",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("probe_json")
    ap.add_argument("--emit-findings", help="write a findings JSON skeleton for score.py")
    ap.add_argument("--expect-fixture", action="store_true",
                    help="assert the known fixture defects were caught")
    ap.add_argument("--quiet", action="store_true", help="table only, no guidance")
    args = ap.parse_args()

    with open(args.probe_json) as fh:
        payload = json.load(fh)

    rep, ctx = analyse(payload)
    primary = ctx["primary"]
    grade, drop, hits = slop_grade(primary)

    print(f"probe-report — {payload.get('label','?')}  {payload.get('url','')}")
    print(f"probed: {payload.get('probedAt','?')} · viewports: "
          f"{', '.join(x.get('tag','?') for x in payload.get('runs',[]))}")
    print("=" * 78)

    if not rep.rows:
        print("No threshold breaches in the measured layer.")
    else:
        order = {CRIT: 0, MAJOR: 1, MINOR: 2, PETTY: 3}
        rep.rows.sort(key=lambda r: (order[r["severity"]], r["pillar"]))
        print(f"{len(rep.rows)} candidates (measured layer only):\n")
        for row in rep.rows:
            wc = f" [WCAG {row['wcag']}]" if row["wcag"] else ""
            kind = "" if row["kind"] == "rule" else " (taste call)"
            print(f"{row['id']} {row['severity'].upper():<8} {row['pillar']:<11}{wc}{kind}")
            print(f"    {row['summary']}")
            print(f"    measured: {row['measured']}   ·   threshold: {row['threshold']}")
            for e in row["evidence"]:
                print(f"      - {e}")
            if row["fix"]:
                print(f"    fix: {row['fix']}")
            print()

    print("-" * 78)
    print(f"AI Slop (measured layer): {grade}   (cumulative drop {drop:.2f} letters)")
    for label, w, v in hits:
        print(f"    -{w:<5} {label}  (measured {v})")
    if not hits:
        print("    no automatable slop tells fired — grade the taste layer by eye")

    wcag = sorted({r["wcag"] for r in rep.rows if r["wcag"] and r["severity"] == CRIT})
    print("-" * 78)
    if wcag:
        print(f"WCAG AA failure candidates: {', '.join(wcag)}")
        print("If ANY survives confirmation, pass --wcag-fail to score.py. The cap is not optional.")
    else:
        print("No WCAG AA failure candidates in the measured layer.")

    if not args.quiet:
        print("-" * 78)
        print("Evidence ledger — what this run can and cannot grade:")
        for p, why in COVERED.items():
            print(f"  measured   {p:<12} {why}")
        for p, why in HUMAN_ONLY.items():
            print(f"  YOUR EYE   {p:<12} {why}")
        print()
        print("Rules: every row above is a CANDIDATE. Confirm each in the browser or")
        print("in source before it becomes a finding, reject the ones that are the")
        print("correct engineering choice (see scoring.md 'does NOT dock for'), then")
        print("add the findings only your eye can see. Grade from the merged file.")

    if args.emit_findings:
        with open(args.emit_findings, "w") as fh:
            json.dump({
                "page": payload.get("label"),
                "url": payload.get("url"),
                "probedAt": payload.get("probedAt"),
                "slopMeasured": {"grade": grade, "drop": drop,
                                 "hits": [{"tell": h[0], "letters": h[1], "measured": h[2]} for h in hits]},
                "findings": rep.rows,
            }, fh, indent=1)
        print(f"\nwrote {args.emit_findings} — confirm/reject each, add eye-level findings, then:")
        print(f"  python3 score.py --findings {args.emit_findings}")

    if args.expect_fixture:
        need = {"color", "a11y", "interaction", "craft", "typography", "responsive", "motion", "content"}
        got = {r["pillar"] for r in rep.rows}
        missing = need - got
        print()
        if missing:
            print(f"FIXTURE CHECK FAILED — no candidate raised for: {', '.join(sorted(missing))}")
            sys.exit(1)
        print(f"fixture check ok — candidates raised across {len(got)} pillars, slop graded {grade}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
