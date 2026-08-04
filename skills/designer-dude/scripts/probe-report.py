#!/usr/bin/env python3
"""probe-report - turn probe.js measurements into severity-tagged candidates.

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
import re
import sys

# Severity vocabulary shared with scoring.md and score.py.
CRIT, MAJOR, MINOR, PETTY = "critical", "major", "minor", "petty"

# WCAG success criteria that trigger the hard cap when CONFIRMED.
WCAG_TRIGGERS = {
    "1.1.1", "1.3.1", "1.3.5", "1.4.1", "1.4.3", "1.4.4", "1.4.11", "1.4.12",
    "1.4.13", "2.1.1", "2.4.1", "2.4.3", "2.4.7", "2.4.11", "2.5.3", "2.5.7", "2.5.8", "3.1.1",
    "3.1.2", "3.3.2", "3.3.7", "3.3.8", "4.1.2", "4.1.3",
}

# Runs that are NOT a plain light-theme viewport sweep. Each holds one
# deliberately changed variable, so the viewport-loop checks must skip them:
# a forced-colors pass measured as if it were a 1440 baseline reports every
# system-coloured text node as a contrast failure, which is a threshold firing
# on correct code -- the expensive kind of wrong. They are analysed instead by
# override_passes() below, as a DELTA against the baseline viewport.
AUX_TAG_PREFIXES = ("dark", "reduced", "forced-colors", "contrast-more",
                    "text-spacing", "text-zoom", "text-expansion", "rtl",
                    "vision-", "content-stress", "state-")

# The overrides the runner is expected to attempt, and what each one is for.
OVERRIDE_PASSES = {
    "forced-colors": ("Windows High Contrast strips backgrounds and background-images", None),
    "contrast-more": ("prefers-contrast: more", None),
    "text-spacing": ("SC 1.4.12 text spacing overrides", "1.4.12"),
    "text-zoom-200": ("SC 1.4.4 text resized to 200%", "1.4.4"),
}


class Report:
    def __init__(self):
        self.rows = []
        self.notes = []
        self.n = 0

    def note(self, text):
        """Something the run MEASURED and decided is not a defect.

        Silence here reads as 'not checked'. An applied exception that nobody
        can see gets re-measured by hand every round, which is how the same
        twenty small buttons end up in three consecutive ledgers.
        """
        self.notes.append(text)

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

    light = [x for x in runs if not x.get("tag", "").startswith(AUX_TAG_PREFIXES)]
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
                  evidence=[f"{f['sel']} - {f['ratio']}:1 (needs {f['required']}, Lc{f.get('apcaLc')}) "
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
                  sc="1.4.3", summary="Dark mode fails contrast where light mode passes - inverted, not designed",
                  evidence=[f"{f['sel']} - {f['ratio']}:1 {f['fg']}"
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
              summary=f"{len(used)} type sizes in real use - that is a pile, not a scale",
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
              summary=f"{slopfaces[0]} is the most-used face on the page - a competent fallback doing the "
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
              summary="A single uniform radius on everything is the shadcn-default tell - no radius hierarchy")

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
    if fr.get("completelyObscured"):
        r.add("a11y", CRIT,
              f"{fr['completelyObscured']} focused elements are entirely obscured",
              "0 completely obscured focused components", sc="2.4.11",
              summary="Keyboard focus is completely hidden by author-created content after it is scrolled into view",
              evidence=sel_list(fr.get("obscuredList"), extra=["text", "covering", "visiblePoints"]),
              fix="Add scroll-padding/scroll-margin for sticky chrome, or move/dismiss the covering layer before focus lands.")
    if fr.get("tested") and fr.get("strongOutlineProven", 0) < fr.get("tested", 0):
        r.note("focus appearance AAA: a >=2px, >=3:1 author outline was proven for "
               f"{fr.get('strongOutlineProven', 0)} of {fr.get('tested', 0)} focused controls. "
               "The remainder may use valid borders, inset rings or custom shapes and require pixel/human review; "
               "they are NOT automatic failures.")

    col_links = get(primary, "states", "colorOnlyLinks", default={}) or {}
    if col_links.get("count"):
        r.add("a11y", CRIT,
              f"{col_links['count']} prose links rely on colour alone",
              "persistent non-colour cue, or >=3:1 plus hover and focus cues",
              sc="1.4.1",
              summary=f"{col_links['count']} links inside body copy are not distinguishable without colour",
              evidence=sel_list(col_links.get("list"),
                                extra=["linkToTextRatio", "hoverCue", "focusCue"]),
              fix="Underline links in body copy. If colour alone is deliberate, keep >=3:1 against "
                  "surrounding text and add a non-colour cue on both hover and keyboard focus.")

    # The probe applies 2.5.8's Inline and Spacing exceptions itself, so this
    # count is failures, not "everything small". Do not re-measure these by
    # hand and do not re-raise the exempt ones next round.
    t24 = it.get("belowWcagTarget24") or {}
    exempt = it.get("target24SpacingExempt") or {}
    inline_exempt = it.get("target24InlineExemptCount") or 0
    # A probe JSON written before the Spacing exception existed carries the
    # UNFILTERED list. Describing it as "crowded" would put a claim in the
    # report that nothing ever computed -- the exact fabricated certainty this
    # rig exists to prevent. Say it is stale and demand a re-probe instead.
    exceptions_computed = "target24SpacingExempt" in it
    if t24.get("count") and exceptions_computed:
        r.add("interaction", CRIT, f"{t24['count']} targets under 24x24 CSS px AND crowded",
              ">=24x24 (2.5.8), aim 44",
              sc="2.5.8", summary=f"{t24['count']} interactive targets fail WCAG 2.5.8: under 24x24 "
                                  f"with another target inside the 24px spacing circle",
              evidence=sel_list(t24.get("list"), extra=["w", "h", "text", "crowdedBy"]),
              fix="Grow the hit area with padding (keep the visual size) or a ::before overlay.")
    elif t24.get("count"):
        r.add("interaction", MAJOR, f"{t24['count']} targets under 24x24, exceptions NOT applied",
              ">=24x24 (2.5.8), aim 44",
              sc="2.5.8", summary=f"{t24['count']} targets measure under 24x24, but this probe JSON "
                                  f"predates the 2.5.8 Spacing/Inline exception computation, so an "
                                  f"unknown share of them CONFORM. Re-probe before quoting a failure "
                                  f"or passing --wcag-fail.",
              evidence=sel_list(t24.get("list"), extra=["w", "h", "text"]),
              fix="Re-run the probe with the current probe.js, then read this row again.")
    if exempt.get("count") or inline_exempt:
        r.note(f"2.5.8 exceptions applied: {exempt.get('count', 0)} undersized targets pass the "
               f"Spacing exception (nothing else within a 24px circle), {inline_exempt} pass the "
               f"Inline exception. These are NOT failures - do not dock for them.")
    # The 44px "comfortable minimum" is a TOUCH figure - Apple HIG 44pt, Material
    # 48dp - and it is meaningless against a mouse, which is why every desktop
    # reference in calibration.md ships nav rows at 32px: linear.app measures 114
    # targets in the 24-44px band on a pointer surface, stripe.com 101 under even
    # the 24px WCAG floor. Reading it off the widest (always mouse) run therefore
    # fired on correct desktop craft every single time, on reference sites and on
    # `fixtures/clean.html` case C6 alike. Graded on the touch-emulated runs only,
    # where the number came from and where a thumb actually has to hit it.
    touch_runs = [x for x in runs if get(x, "emulation", "touch", default="mouse") == "touch"]
    t44 = max((get(x, "interaction", "belowFittsTarget44", default={}) or {} for x in touch_runs),
              key=lambda d: d.get("count", 0), default={})
    if t44.get("count"):
        r.add("interaction", MINOR, f"{t44['count']} targets between 24 and 44px on a touch viewport",
              "44px (Fitts)",
              summary=f"{t44['count']} targets clear WCAG but sit under the 44px comfortable "
                      f"minimum where the pointer is a thumb",
              evidence=sel_list(t44.get("list"), extra=["w", "h"]))

    mp = it.get("missingPointerCursor") or {}
    if mp.get("count"):
        r.add("interaction", MINOR, f"{mp['count']} clickable elements without cursor:pointer", "pointer on all",
              summary="Clickable elements render the default cursor - a signifier failure (Norman)",
              evidence=sel_list(mp.get("list"), extra=["cursor", "text"]),
              fix="Add cursor-pointer to the interactive base class, not per component.")

    # ---- designed states (measured from stylesheet rules) ----
    st = get(primary, "states", default={})
    if st:
        blind = st.get("inaccessibleStylesheets", 0)
        readable = st.get("stylesheetsRead", 0)
        n = st.get("interactiveElements", 0)
        if blind and blind > readable:
            # Most CSS is cross-origin, so rule matching sees almost nothing. A
            # 0% coverage number here means UNMEASURED, and reporting it as a
            # finding would invent a catastrophic defect on a site that is fine.
            r.add("interaction", PETTY,
                  f"{blind} stylesheets unreadable (cross-origin) vs {readable} readable",
                  "same-origin CSS", kind="rule",
                  summary="State coverage could not be measured: most CSS is cross-origin. "
                          "Interaction stays provisional; exercise the states by hand.",
                  fix="Run the probe against the local build, where the CSS is same-origin.")
        elif n:
            hov = st.get("hoverCoverage")
            fv = st.get("focusVisibleCoverage")
            if hov is not None and hov < 60:
                r.add("interaction", MAJOR if hov < 25 else MINOR,
                      f"{hov}% of {n} interactive elements have a :hover rule", ">=90%",
                      summary=f"{st.get('missingHoverCount', 0)} interactive elements have no hover "
                              f"state defined anywhere in the CSS that matches them",
                      evidence=sel_list(st.get("missingHoverExamples"), extra=["text"]),
                      fix="Put hover on the interactive base class rather than per component.")
            # A hover rule that exists is not a hover state that works. These
            # two are the difference, and neither is visible in a screenshot
            # taken without a pointer over the row.
            inert = st.get("inertHoverFills", 0)
            if inert:
                r.add("interaction", MAJOR,
                      f"{inert} hover fill(s) the same colour as what they sit on",
                      "a visible change", kind="rule",
                      summary="These elements declare a hover background that resolves to the "
                              "colour already behind them, so hovering changes nothing. Rule "
                              "coverage counts them as having a hover state; a user cannot see one.",
                      evidence=sel_list(st.get("inertHoverFillExamples"),
                                        extra=["text", "declared", "delta"]),
                      fix="Pick the hover tint against the surface the component ACTUALLY renders "
                          "on. A shared component lands on more than one background, so the tint "
                          "has to be a step from every one of them.")
            over_rule = st.get("hoverFillsCoveringOwnRule", 0)
            if over_rule:
                r.add("interaction", MINOR,
                      f"{over_rule} hover fill(s) painted on the same box as their own rule",
                      "rule on the row, tint on a child", kind="rule",
                      summary="The background paints under the border, so hovering erases the "
                              "separator and the band's edge lands exactly where the previous "
                              "row ended - it reads as crowding the row above rather than "
                              "sitting inside its own",
                      evidence=sel_list(st.get("hoverFillsCoveringOwnRuleExamples"), extra=["text"]),
                      fix="Move the rule to the row and the tint to a child with a small block "
                          "margin and a radius. Same width, separated by air. In a TABLE this is "
                          "the convention and is already excluded.")
            dead_border = st.get("inertHoverBorders", 0)
            if dead_border:
                r.add("interaction", MINOR,
                      f"{dead_border} hover border(s) re-declaring the colour already there",
                      "a visible change", kind="rule",
                      summary="`border-line hover:border-line` and its equivalents: the rule "
                              "exists, the transition runs, the border does not move",
                      evidence=sel_list(st.get("inertHoverBorderExamples"),
                                        extra=["text", "declared"]),
                      fix="Step the border to the strong variant of the same role, or drop the "
                          "declaration so the hover is carried by something that does change.")
            hue_only = st.get("hueOnlyHoverFills", 0)
            if hue_only:
                r.add("interaction", MINOR,
                      f"{hue_only} hover fill(s) that change hue but not lightness",
                      "a lightness step too", kind="rule",
                      summary="The hover tint sits at the same lightness as the surface behind "
                              "it. It reads on a good screen and disappears in greyscale, on a "
                              "cheap panel, and for a colour vision deficiency in that axis.",
                      evidence=sel_list(st.get("hueOnlyHoverFillExamples"),
                                        extra=["text", "declared", "delta"]),
                      fix="Move the tint a step in lightness as well as hue, or render the "
                          "component on the one surface its tint was designed against.")
            tight = st.get("hoverFillsWithoutPadding", 0)
            if tight:
                r.add("interaction", MINOR,
                      f"{tight} wide hover fill(s) with no horizontal padding",
                      "ink >=8px from the fill edge", kind="rule",
                      summary="A full-width row paints a hover band that stops dead at the first "
                              "and last glyph, which reads as a rendering artefact rather than a "
                              "designed row",
                      evidence=sel_list(st.get("hoverFillsWithoutPaddingExamples"),
                                        extra=["text", "width", "inkGapLeft", "inkGapRight"]),
                      fix="Give the row inline padding and pay it back on the list "
                          "(negative margin), so the text keeps its alignment and the band "
                          "gets margins.")
            if fv is not None and fv < 40 and st.get("withFocusRule", 0) == 0:
                r.add("interaction", MAJOR,
                      f"{fv}% of interactive elements have a :focus-visible rule", ">=90%",
                      sc="2.4.7",
                      summary="Most interactive elements have no focus-visible rule matching them; "
                              "keyboard users are relying on the UA default, if anything")
            elif fv is not None and fv < 40:
                r.add("interaction", MINOR,
                      f"{fv}% use :focus-visible ({st.get('withFocusRule')} use plain :focus)",
                      ":focus-visible", summary="Plain :focus shows a ring on mouse click too")
            if st.get("disabledControlsPresent") and st.get("withDisabledRule", 0) == 0:
                r.add("interaction", MINOR,
                      f"{st['disabledControlsPresent']} disabled controls, no :disabled styling",
                      "designed disabled state",
                      summary="Disabled controls are present but nothing styles the disabled state, "
                              "so unavailable and available read the same")

    perf = payload.get("performance") or {}
    if perf:
        lab = " (LAB, one machine - not p75 CrUX)"
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
              summary="The page logs errors in a real browser - craft is not finished while the console is red",
              evidence=payload["consoleErrors"][:3])

    unstable_shots = [x for x in payload.get("screenshotStability", []) or []
                      if x.get("status") == "unstable"]
    if unstable_shots:
        r.note(f"screenshot stability: {len(unstable_shots)} passes changed between consecutive "
               "animation-disabled captures. Visual baselines from those passes are invalid until volatile regions are masked or stabilized.")

    # ---------------- Accessibility ----------------
    a = get(primary, "a11y", default={})
    for key, sev, sc, label, fix in [
        ("imagesMissingAlt", CRIT, "1.1.1", "images without an alt attribute",
         'Add alt text, or alt="" if genuinely decorative.'),
    ]:
        node = a.get(key) or {}
        if node.get("count"):
            r.add("a11y", sev, f"{node['count']} {label}", "0", sc=sc,
                  summary=f"{node['count']} {label} (WCAG {sc})",
                  evidence=sel_list(node.get("list"), extra=["type", "src", "html"]), fix=fix)

    browser_missing = a.get("browserMissingAccessibleName")
    if isinstance(browser_missing, dict):
        for source, sc, label, fix in (
            ("field", "3.3.2", "form fields with no browser-computed accessible name",
             "Add a <label for>, or aria-label where a visible label is impossible."),
            ("control", "4.1.2", "controls with no browser-computed accessible name",
             "Icon-only buttons need aria-label; links need discernible text."),
        ):
            failures = [x for x in browser_missing.get("list", []) if x.get("source") == source]
            if failures:
                r.add("a11y", CRIT, f"{len(failures)} {label}", "0", sc=sc,
                      summary=f"{len(failures)} {label} (WCAG {sc})",
                      evidence=sel_list(failures, extra=["type", "html", "reason"]), fix=fix)
        if browser_missing.get("inconclusive"):
            r.note(f"accessible-name confirmation: {len(browser_missing['inconclusive'])} candidates were inconclusive; they are ungraded evidence gaps")
    else:
        raw_missing = ((a.get("fieldsMissingLabel") or {}).get("count", 0) +
                       (a.get("controlsMissingAccessibleName") or {}).get("count", 0))
        if raw_missing:
            raw_items = ((a.get("fieldsMissingLabel") or {}).get("list", []) +
                         (a.get("controlsMissingAccessibleName") or {}).get("list", []))
            r.add("a11y", MAJOR, f"{raw_missing} DOM accessible-name candidates need browser confirmation",
                  "browser-computed names checked", summary="The DOM fallback found possible unnamed controls, but ACT cases show it is not conformance-grade by itself",
                  evidence=sel_list(raw_items, extra=["type", "html"]),
                  fix="Run probe-runner.mjs and grade only browserMissingAccessibleName failures.")

    browser_label = a.get("browserLabelInName") or {}
    if browser_label.get("failures"):
        r.add("a11y", CRIT,
              f"{browser_label['failures']} controls expose a name that omits their visible label",
              "visible label contained in browser-computed accessible name", sc="2.5.3",
              summary="Voice-control users cannot reliably address controls by the words printed on screen",
              evidence=sel_list(browser_label.get("list"),
                                extra=["visibleLabel", "computedName", "accessibleNameSource"]),
              fix="Start the accessible name with the complete visible label; append extra context after it.")
    elif (a.get("labelInName") or {}).get("count") and not browser_label:
        fallback = a.get("labelInName") or {}
        r.add("a11y", MAJOR,
              f"{fallback['count']} possible visible-label/accessibility-name mismatches",
              "confirm with the browser-computed accessible name", sc=None,
              summary="The DOM fallback suggests Label in Name mismatches, but this run did not capture browser ARIA names",
              evidence=sel_list(fallback.get("list"), extra=["visibleLabel", "domAccessibleName"]),
              fix="Run probe-runner.mjs (ARIA snapshots enabled) and only attach WCAG 2.5.3 to browser-confirmed mismatches.")
    if browser_label.get("inconclusive"):
        r.note(f"label-in-name: {len(browser_label['inconclusive'])} candidates could not be resolved "
               "against a browser ARIA snapshot and remain unchecked, not passed.")

    invalid_ac = a.get("invalidAutocomplete") or {}
    if invalid_ac.get("count"):
        r.add("a11y", CRIT, f"{invalid_ac['count']} invalid autocomplete token sequences",
              "valid purpose tokens on applicable user-data fields", sc="1.3.5",
              summary="Declared input-purpose metadata is invalid; confirm each field collects information about the current user",
              evidence=sel_list(invalid_ac.get("list"), extra=["value"]),
              fix="Use the exact HTML autocomplete token sequence for the field's purpose. Reject the WCAG candidate if the field is not about the current user.")
    purpose_review = a.get("inputPurposeReview") or {}
    if purpose_review.get("count"):
        r.note(f"input purpose: {purpose_review['count']} plausibly user-data fields have no autocomplete metadata. "
               "This is contextual (the value may describe another person), so confirm applicability before creating a 1.3.5 finding.")

    invalid_lang = a.get("invalidLanguageTags") or {}
    if invalid_lang.get("count"):
        r.note(f"language syntax: {invalid_lang['count']} tags are not strict BCP 47 but retain a known primary language. "
               "ACT/WCAG permits this for 3.1.1/3.1.2 because browsers and AT use the primary subtag; normalize them as craft, not conformance failures.")
    unknown_lang = a.get("unrecognizedLanguageTags") or {}
    if unknown_lang.get("count"):
        html_bad = any(str(x.get("sel", "")).startswith("html") for x in unknown_lang.get("list", []))
        r.add("a11y", CRIT, f"{unknown_lang['count']} language tags have no known primary subtag",
              "known primary language subtag", sc="3.1.1" if html_bad else "3.1.2",
              summary="The declared primary language is not recognized, so browsers and assistive technology cannot select reliable pronunciation rules",
              evidence=sel_list(unknown_lang.get("list"), extra=["value"]),
              fix="Use the registered primary language subtag. Full strict BCP 47 grammar is not required when the primary is known.")

    broken = a.get("requiredBrokenAriaReferences") or {}
    if broken.get("count"):
        r.add("a11y", CRIT, f"{broken['count']} broken ARIA ID references", "0", sc="4.1.2",
              summary="ARIA labels, descriptions, errors or controlled panels point to missing elements",
              evidence=sel_list(broken.get("list"), extra=["attr", "missing"]),
              fix="Repair each ID reference or remove the stale attribute; verify the accessible name "
                  "and relationship in the browser accessibility tree.")

    deferred_controls = a.get("deferredAriaControls") or {}
    if deferred_controls.get("count"):
        r.add("interaction", MINOR,
              f"{deferred_controls['count']} collapsed controls reference panels absent at rest",
              "target exists when the control opens",
              summary="Controlled content may be lazily mounted; exercise each trigger before deciding the ARIA relationship is broken",
              evidence=sel_list(deferred_controls.get("list"),
                                extra=["attr", "missing", "expanded", "selected"]),
              fix="Open each trigger in the browser. Confirm a finding only if aria-controls still "
                  "points nowhere once expanded/selected; otherwise reject this candidate.")

    role_issues = a.get("ariaRoleStateIssues") or {}
    if role_issues.get("count"):
        r.add("a11y", CRIT, f"{role_issues['count']} ARIA widgets miss required state or naming",
              "all required role properties", sc="4.1.2",
              summary="Custom ARIA widgets expose an incomplete role/state contract to assistive technology",
              evidence=sel_list(role_issues.get("list"), extra=["role", "missing"]),
              fix="Prefer the native element. If the custom role is necessary, add its required ARIA "
                  "state and implement the matching APG keyboard interaction.")

    landmark_issues = a.get("landmarkNameIssues") or {}
    if landmark_issues.get("count"):
        r.add("a11y", MAJOR,
              f"{landmark_issues['count']} repeated landmarks are unnamed or share a name",
              "a unique accessible name for each repeated landmark role",
              summary="Landmark navigation cannot distinguish repeated regions with the same role",
              evidence=sel_list(landmark_issues.get("list"), extra=["role", "issue", "name"]),
              fix="Give each repeated nav/main/aside a short unique aria-label or aria-labelledby. "
                  "Do not repeat the role word in the label.")

    po = a.get("fieldsPlaceholderOnly") or {}
    if po.get("count"):
        r.add("a11y", MAJOR, f"{po['count']} fields labelled by placeholder only", "persistent visible label",
              sc="3.3.2", summary="Placeholder-as-label disappears on input and fails at zoom and for screen readers",
              evidence=sel_list(po.get("list"), extra=["placeholder"]))

    hd = a.get("headings") or {}
    if hd.get("skippedLevels"):
        r.add("a11y", MAJOR, f"{len(hd['skippedLevels'])} skipped heading levels", "sequential",
              # W3C encourages nested ranks but does not define every skipped
              # rank as a 1.3.1 failure. Confirm that the semantic relationship
              # is actually wrong before attaching a conformance criterion.
              sc=None, summary="Heading levels skip; verify that the semantic outline still matches the content",
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
              sc=None, summary="Positive tabindex overrides DOM order; verify the resulting focus sequence is logical",
              fix="Prefer DOM order with tabindex=0. Attach WCAG 2.4.3 only if the exercised order loses meaning or operability.")
    if a.get("duplicateIds", {}).get("count"):
        r.add("a11y", MINOR, f"{a['duplicateIds']['count']} duplicate ids", "0",
              summary="Duplicate ids break label/for and aria-labelledby wiring",
              evidence=a["duplicateIds"].get("list"))
    if not a.get("lang"):
        r.add("a11y", MAJOR, "no lang on <html>", 'lang="xx"', sc="3.1.1",
              summary="Missing document language: screen readers pick the wrong voice")
    lm = a.get("landmarks") or {}
    if lm.get("main", 0) == 0:
        r.add("a11y", MAJOR, "no <main> landmark", "one main", sc=None,
              summary="No main landmark; this removes a fast navigation route but is not by itself a WCAG failure")
    if not a.get("skipLink") and lm.get("nav", 0) >= 1:
        r.add("a11y", MINOR, "no skip link with a nav present", "skip link", sc=None,
              summary="Keyboard-only browser users tab the whole nav; headings or landmarks may still satisfy WCAG 2.4.1",
              fix="Add a visible-on-focus skip link for mainstream keyboard users. Do not attach 2.4.1 if headings or landmarks already provide a sufficient bypass mechanism.")

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
              summary="Mobile widths were not measured - Responsiveness cannot be graded above provisional")
    for run in small:
        t = get(run, "interaction", "belowWcagTarget24", "count", default=0)
        # Same staleness rule as above: without the exception pass this count
        # is "everything small", not "everything failing".
        if t and "target24SpacingExempt" in (get(run, "interaction", default={}) or {}):
            r.add("responsive", MAJOR, f"{t} sub-24px targets at {get(run,'meta','viewport','w')}px", "0",
                  sc="2.5.8", summary="Targets shrink below the minimum at mobile width",
                  evidence=sel_list(get(run, "interaction", "belowWcagTarget24", "list", default=[]), extra=["w", "h"]))

    # -- was the narrow sweep actually a TOUCH device? ---------------------
    # setViewportSize only resizes. If touch emulation did not take, every
    # mobile conclusion here came from a narrow desktop: hover still worked,
    # pointer:coarse never matched, and any coarse-pointer CSS branch went
    # unexercised. That is an evidence gap, not a product defect -- report it
    # as one so the pillar cannot be graded on coverage it never had.
    touch_runs = [x for x in small if get(x, "meta", "device", "pointerCoarse", default=False)]
    if small and not touch_runs:
        r.add("responsive", MAJOR, "mobile widths probed without touch emulation",
              "pointer:coarse at <=430px",
              summary="Narrow viewports were measured as a desktop browser in a small window: "
                      "hover still worked and no coarse-pointer CSS branch was exercised",
              fix="Re-run the probe with touchBelowPx set (default 500); if the summary shows "
                  "[NO-EMU] the CDP session was refused and Responsiveness stays provisional.")

    # -- content that only a hover can reveal ------------------------------
    for run in (touch_runs or small):
        n = get(run, "states", "hoverOnlyContent", default=[])
        cnt = get(run, "states", "hoverOnlyContentCount", default=0)
        if not cnt:
            continue
        coarse = get(run, "meta", "device", "pointerCoarse", default=False)
        interactive = [x for x in n if x.get("interactive")]
        # On a real touch run this is lost functionality, not a polish note.
        sev = CRIT if (coarse and interactive) else (MAJOR if coarse else MINOR)
        r.add("responsive", sev,
              f"{cnt} hover-revealed element(s) at {get(run,'meta','viewport','w')}px"
              + (" containing controls" if interactive else ""),
              "reachable without hover",
              sc="2.1.1" if interactive else None,
              summary=("Content that only appears on hover is unreachable on a touch device"
                       + (" - and it contains interactive controls" if interactive else "")),
              evidence=sel_list(n, extra=["text"]),
              fix="Give it a tap/focus path: focus-within, an aria-expanded toggle, or show it "
                  "unconditionally under @media (hover: none).")
        break   # one per page, not one per viewport

    # -- notch / home-indicator safe areas ---------------------------------
    # The runtime insets are ALWAYS 0 here: a desktop browser has no notch, and
    # no amount of viewport emulation gives it one. So the measurable question
    # is not "how big is the inset" but "does this page, which opted into
    # drawing under the notch, account for one anywhere in its CSS".
    for run in small:
        dev = get(run, "meta", "device", default={}) or {}
        if not dev.get("viewportFitCover"):
            break
        stuck = [s for s in (get(run, "layout", "stickyOrFixed", default=[]) or [])]
        declared = get(run, "states", "safeAreaInsetRules", default=0)
        readable = get(run, "states", "stylesheetsRead", default=0)
        if stuck and readable and not declared:
            r.add("responsive", MAJOR, "viewport-fit=cover, fixed chrome, no env(safe-area-inset-*) anywhere",
                  "safe-area padding on fixed edges",
                  summary="The page opts into drawing under the notch and home indicator but never "
                          "pads for either, so fixed bars sit under them on every modern iPhone",
                  evidence=sel_list(stuck, extra=["position"]),
                  fix="pb-[env(safe-area-inset-bottom)] on fixed bottom bars, "
                      "pt-[env(safe-area-inset-top)] on fixed headers.")
        break

    # -- short viewports (landscape phone) ---------------------------------
    # A full-height hero is fine at 844px tall and swallows the screen at 390.
    for run in light:
        if get(run, "meta", "device", "orientation", default="") != "landscape":
            continue
        vh = get(run, "meta", "viewport", "h", default=9999)
        if vh > 450:
            continue
        sticky_h = get(run, "layout", "stickyTotalHeight", default=0) or 0
        if sticky_h and sticky_h > vh * 0.25:
            r.add("responsive", MAJOR,
                  f"sticky/fixed chrome is {sticky_h}px of a {vh}px-tall viewport "
                  f"({round(sticky_h / vh * 100)}%)", "<25% of a short viewport",
                  summary="On a landscape phone the fixed chrome eats most of the screen",
                  fix="Collapse or hide the sticky header under @media (max-height: 450px).")
        break
    if not any(get(x, "meta", "device", "orientation", default="") == "landscape"
               and get(x, "meta", "viewport", "h", default=9999) <= 450 for x in light):
        r.note("no short/landscape-phone viewport probed; short-viewport bugs "
               "(100vh heroes, fixed bars) were not measured")

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
              summary="Motion exists but the reduced-motion pass was not run - Motion stays provisional")
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

    frames = sl.get("llmSentenceFrames") or []
    if frames:
        r.add("content", MAJOR, f"{len(frames)} LLM sentence frames", "0", kind="taste",
              summary="Copy uses the sentence shapes that mark text as machine-written",
              evidence=[f'"{f}"' for f in frames[:4]],
              fix="Rewrite each as one plain claim. 'Not just X, but Y' always survives "
                  "being cut down to Y.")
    steps = sl.get("decorativeStepNumbers") or 0
    if steps >= 2:
        r.add("content", MINOR, f"{steps} decorative 01/02/03 step numbers", "0", kind="taste",
              summary="Zero-padded ordinals used as section ornament add no information "
                      "the heading does not already carry",
              evidence=sel_list(sl.get("decorativeStepNumberSamples"), extra=["text"]),
              fix="Delete them, or make them real ordered-list markers if the steps are "
                  "actually a sequence.")
    em_rate = sl.get("emDashesPer1kChars") or 0
    if em_rate >= 3:
        r.add("content", MINOR,
              f"{sl.get('emDashesInCopy')} em dashes ({em_rate}/1k chars)", "<3 per 1k",
              kind="taste",
              summary="Em-dash density at a rate human copy does not sustain",
              fix="Replace most with a comma, a colon, or a full stop. Keep the one that "
                  "is doing real work.")

    # ---------------- Browser chrome: what the OS draws, not the page --------
    #
    # Scrollbars, the <select> popup, autofill and date pickers never appear in
    # a screenshot and never show up in a CSS review, which is exactly why they
    # are where a dark theme most visibly stops being one.
    ch = get(primary, "chrome", default={})
    if ch.get("darkSurfaceWithoutColorScheme"):
        r.add("craft", MAJOR, "dark surface with no `color-scheme` declared",
              "color-scheme: dark (or light dark)",
              summary="The browser still draws its own chrome light: scrollbars, the "
                      "<select> option popup, autofill backgrounds, the caret and spin "
                      "buttons all stay in the light theme on a dark page",
              evidence=[f"page luminance {ch.get('pageLuminance')}, "
                        f"color-scheme: {ch.get('colorScheme')}"],
              fix="Add `color-scheme: light dark` to :root (or `dark` on the dark theme). "
                  "One declaration, and it is the widest-blast-radius line in the file.")
    if ch.get("hiddenScrollbars"):
        r.add("interaction", MAJOR,
              f"{ch['hiddenScrollbars']} scroll region(s) with the scrollbar suppressed",
              "a visible scroll affordance",
              summary="`scrollbar-width: none` on a region the user must scroll removes "
                      "the only signal that more content exists, and removes a pointer "
                      "user's ability to drag it",
              evidence=sel_list(ch.get("hiddenScrollbarList"), extra=["scrollsY", "scrollsX"]),
              fix="Restore the scrollbar, or keep an edge fade plus an overlay scrollbar "
                  "on hover. An UNSTYLED scrollbar is a preference; a hidden one is a defect.")
    if ch.get("unstyledStrippedSelects"):
        r.add("craft", MAJOR,
              f"{ch['unstyledStrippedSelects']} select(s) with `appearance: none` and no chevron",
              "a replacement chevron",
              summary="The native dropdown arrow was removed and nothing was put back, so "
                      "the control no longer says it is a control",
              evidence=sel_list(ch.get("strippedSelectList")),
              fix="Add your own chevron with enough right padding that a long option label "
                  "never runs under it. references/components.md section 4.")
    if ch.get("nativeTitleTooltips"):
        sev = MAJOR if ch["nativeTitleTooltips"] >= 3 else MINOR
        r.add("interaction", sev,
              f"{ch['nativeTitleTooltips']} native `title` tooltip(s)", "a real tooltip",
              # WCAG 1.4.13 explicitly exempts user-agent-controlled content
              # and names HTML title tooltips as its example. This is a real
              # cross-input UX defect, but it must not trigger the AA hard cap.
              sc=None,
              summary="The OS tooltip is slow to appear, unstyled, invisible on touch, "
                      "unreachable by keyboard, and it vanishes while it is being read",
              evidence=sel_list(ch.get("nativeTitleTooltipList"), extra=["title"]),
              fix="Replace with a tooltip that follows 1.4.13 (hoverable, dismissable with "
                  "Escape, persistent), or move the text into the page. `title` on an "
                  "iframe, or repeating an element's own visible text, is fine and is "
                  "already excluded here.")

    # ---------------- Enterprise app surfaces ----------------
    for t in get(primary, "app", "tables", default=[]):
        if t.get("rows", 0) < 3:
            continue
        if (t.get("needsHeaderAssociations") and not t.get("hasHeaderAssociations")
                and t.get("columns")):
            r.add("a11y", MAJOR,
                  f"complex/large table with {t['columns']} headers has no explicit associations",
                  "scope or headers/id",
                  sc="1.3.1", summary="Ambiguous data-table headers are not associated with their cells",
                  evidence=[f"{t.get('sel', '?')} - rows={t.get('rows')} "
                            f"headerRows={t.get('headerRows')} rowHeaders={t.get('rowHeaders')} "
                            f"spanningHeaders={t.get('spanningHeaders')}"],
                  fix="Use scope=col/row for directional headers; use headers/id for genuinely "
                      "multi-level relationships. A small one-direction table needs only <th>.")
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
              summary="No favicon - the tab shows a default glyph")
    if not meta.get("hasViewportMeta"):
        r.add("responsive", CRIT, "no viewport meta tag", "width=device-width",
              summary="Without a viewport meta the mobile layout is a scaled-down desktop page")
    if meta.get("elementsTruncated"):
        r.add("craft", PETTY, "probe hit its element cap", "raise maxElements",
              summary="The page has more elements than the probe scanned; counts are lower bounds")

    # ---------------- Override passes (deltas, not absolutes) ----------------
    #
    # Each override pass changed exactly one thing about the user's environment.
    # So the finding is never "this pass has N failures" -- system colours and
    # 200% text will legitimately move numbers -- it is "this pass made
    # something WORSE than the same viewport without the override". A delta is
    # attributable; an absolute is an argument.
    baseline = next((x for x in light if x.get("tag") == "1440x900"), None) or primary

    def metrics(run):
        return {
            "contrast": get(run, "color", "textContrast", "failures", default=0),
            "checked": get(run, "color", "textContrast", "checked", default=0),
            "focusInvisible": get(run, "interaction", "focusRing", "invisible", default=0),
            "overflow": bool(get(run, "layout", "horizontalOverflow", default=False)),
            "clipped": get(run, "layout", "clippedContent", "count", default=0),
        }

    base_m = metrics(baseline)
    attempted = {o.get("pass"): o for o in payload.get("overridePasses", []) or []}

    for tag, (what, sc) in OVERRIDE_PASSES.items():
        run = next((x for x in runs if x.get("tag") == tag), None)
        state = (attempted.get(tag) or {}).get("status")
        if run is None:
            if state == "unavailable":
                r.add("a11y", MINOR, f"{tag} pass unavailable in this browser",
                      "pass runs", summary=f"{what} could not be emulated here, so it is UNCHECKED, "
                                           f"not clean", sc=sc,
                      evidence=[(attempted.get(tag) or {}).get("reason", "")[:120]])
            else:
                r.note(f"{tag}: not run (add \"{tag}\": true to the probe config) - "
                       f"{what} is unchecked")
            continue

        m = metrics(run)
        if m["overflow"] and not base_m["overflow"]:
            r.add("responsive", MAJOR, f"horizontal overflow appears under {tag}",
                  "no overflow with the override applied", sc=sc,
                  summary=f"The layout survives 1440x900 but overflows once {what} is applied - "
                          f"the container is sized in fixed px rather than to its content",
                  fix="Replace fixed heights/widths on text containers with min-* and let them grow.")
        if m["focusInvisible"] > base_m["focusInvisible"]:
            r.add("a11y", MAJOR,
                  f"{m['focusInvisible']} invisible focus rings under {tag} "
                  f"(vs {base_m['focusInvisible']} without it)",
                  "no new invisible rings", sc="2.4.7",
                  summary=f"Focus becomes invisible once {what} is applied - the ring is drawn with "
                          f"something the override removes (usually a box-shadow or a background)",
                  fix="Draw focus with `outline` + `outline-offset`, which survives forced colours.")
        # Content vanishing is the forced-colors failure mode that no contrast
        # measurement finds: the element is still in the DOM, it just has
        # nothing left to see. A 2% band absorbs normal reflow.
        if base_m["checked"] and m["checked"] < base_m["checked"] * 0.98:
            lost = base_m["checked"] - m["checked"]
            r.add("a11y", MAJOR, f"{lost} text nodes stop being visible under {tag}",
                  "no content lost", sc=sc,
                  summary=f"{lost} of {base_m['checked']} text nodes disappear once {what} is applied "
                          f"(usually text over a background-image, or colour set on a parent the "
                          f"override overrides)",
                  fix="Give text an explicit colour and a real background element, not a "
                      "background-image; test with forced-colors-adjust only where deliberate.")
        if tag == "contrast-more" and m["contrast"] > base_m["contrast"]:
            r.add("color", MINOR,
                  f"{m['contrast']} contrast failures under prefers-contrast: more "
                  f"(vs {base_m['contrast']})",
                  "no worse than the default theme",
                  summary="A theme may ignore prefers-contrast, but getting WORSE under it means the "
                          "high-contrast branch is half-built",
                      fix="Either honour the preference properly or do not branch on it at all.")

    # ---------------- Internationalisation stress ----------------
    for tag, description in (("text-expansion", "approximately 35% expanded pseudo-localized text"),
                             ("rtl", "the configured RTL direction")):
        run = next((x for x in runs if x.get("tag") == tag), None)
        attempted_state = (attempted.get(tag) or {}).get("status")
        if run is None:
            if attempted_state == "unavailable":
                r.add("responsive", MINOR, f"{tag} pass unavailable", "configured pass runs",
                      summary=f"The {description} pass was requested but could not run, so it is unchecked",
                      evidence=[(attempted.get(tag) or {}).get("reason", "")[:140]])
            else:
                r.note(f"{tag}: not run - internationalisation stress is unchecked")
            continue
        m = metrics(run)
        if m["overflow"] and not base_m["overflow"]:
            r.add("responsive", MAJOR, f"horizontal overflow under {tag}",
                  "no new overflow", summary=f"The layout overflows under {description}",
                  fix="Use logical properties, min-width:0, wrapping and content-sized containers; do not patch the synthetic string.")
        extra_clipped = max(0, m["clipped"] - base_m["clipped"])
        if extra_clipped:
            r.add("responsive", MINOR, f"{extra_clipped} additional clipped containers under {tag}",
                  "no new clipping", summary=f"Content that fits at baseline is clipped under {description}",
                  evidence=sel_list(get(run, "layout", "clippedContent", "list", default=[]),
                                    extra=["scrollWidth", "clientWidth", "scrollHeight", "clientHeight", "ellipsis"]),
                  fix="Let the container grow or wrap. Confirm intentional ellipsis against product requirements before keeping the finding.")

    # Reviewed translations are stronger than synthetic expansion. Each
    # locale-* run is a like-for-like 1440 delta. A missing selector makes the
    # fixture partial and therefore an evidence gap even when the remaining
    # strings happen to fit.
    for attempt in sorted((x for x in payload.get("overridePasses", []) or []
                           if str(x.get("pass") or "").startswith("locale-")),
                          key=lambda x: str(x.get("pass"))):
        tag = attempt.get("pass")
        locale = attempt.get("locale") or tag.removeprefix("locale-")
        run = next((x for x in runs if x.get("tag") == tag), None)
        if attempt.get("status") == "unavailable" or run is None:
            r.add("responsive", MINOR, f"locale fixture {locale} unavailable",
                  "configured locale pass runs",
                  summary="A requested real-translation layout pass produced no evidence",
                  evidence=[str(attempt.get("reason") or "")[:160]])
            continue
        if attempt.get("status") == "partial":
            missing = attempt.get("missingSelectors") or []
            r.add("content", MINOR, f"locale fixture {locale} misses {len(missing)} selectors",
                  "every declared translation selector resolves",
                  summary="The locale screenshot mixes translated and baseline content, so it cannot certify the surface",
                  evidence=[str(x) for x in missing[:10]])
        m = metrics(run)
        if m["overflow"] and not base_m["overflow"]:
            r.add("responsive", MAJOR, f"horizontal overflow in locale {locale}",
                  "no new overflow", summary=f"Reviewed {locale} content breaks a layout that fits at baseline",
                  fix="Fix the shared layout with logical properties, wrapping and content-sized containers; keep the real translation unchanged.")
        extra_clipped = max(0, m["clipped"] - base_m["clipped"])
        if extra_clipped:
            r.add("responsive", MINOR, f"{extra_clipped} additional clipped containers in locale {locale}",
                  "no new clipping", summary=f"Reviewed {locale} content is clipped",
                  evidence=sel_list(get(run, "layout", "clippedContent", "list", default=[]),
                                    extra=["scrollWidth", "clientWidth", "scrollHeight", "clientHeight", "ellipsis"]))

    # ---------------- Content stress ----------------
    stress = next((x for x in runs if x.get("tag") == "content-stress"), None)
    if stress is None:
        r.note("content-stress: not run - the layout is graded against seeded fixture "
               "content only (add \"stress\": true)")
    else:
        sm = metrics(stress)
        if sm["overflow"] and not base_m["overflow"]:
            r.add("craft", MAJOR, "horizontal overflow with one long unbroken string",
                  "no overflow", summary="The layout holds on seeded content and breaks on a real "
                                         "one: a long unbroken value pushes the page sideways",
                  fix="Add `min-w-0` to the flex/grid child and `break-words` (or `truncate` with a "
                      "title) to the text itself.")

    # ---------------- States ----------------
    #
    # The seven states used to be graded by reading source while everything
    # else was measured. A state that was CONFIGURED and could not be reached
    # is a finding in itself -- most often the app has no such state.
    state_runs = [x for x in runs if x.get("tag", "").startswith("state-")]
    for s in payload.get("statePasses", []) or []:
        if s.get("status") == "unreachable":
            r.add("content", MINOR, f"state '{s.get('label')}' could not be reached",
                  "the state renders",
                  summary=f"The configured '{s.get('label')}' state did not load, so it is unchecked. "
                          f"If the app has no such state, that is the finding.",
                  evidence=[s.get("reason", "")[:160]])
    for run in state_runs:
        tag = run.get("tag")
        label = tag[len("state-"):]
        sm = metrics(run)
        if sm["contrast"]:
            r.add("color", CRIT, f"{sm['contrast']} contrast failures in the '{label}' state",
                  "0 failures", sc="1.4.3",
                  summary=f"The '{label}' state fails AA contrast. Skeletons, empty states and error "
                          f"text are the surfaces most often styled once and never re-checked.",
                  evidence=[f"{f['sel']} - {f['ratio']}:1 (needs {f['required']})"
                            for f in get(run, "color", "textContrast", "failureList", default=[])[:3]])
        if sm["overflow"]:
            r.add("responsive", MAJOR, f"horizontal overflow in the '{label}' state", "no overflow",
                  summary=f"The '{label}' state overflows horizontally at 1440x900")
        # An empty or error state with nothing to click is a dead end: the
        # user is told there is nothing here and given no way forward.
        clickable = get(run, "interaction", "clickable", default=0)
        if label.startswith(("empty", "error", "zero", "404")) and clickable <= 1:
            r.add("content", MAJOR, f"'{label}' state offers {clickable} interactive elements",
                  "a named next action",
                  summary=f"The '{label}' state is a dead end - it says there is nothing here and "
                          f"gives no way forward (voice.md: an empty state names the next action)",
                  fix="Add the one action that resolves the state: create the first record, "
                      "clear the filter, retry the request.")
    if not state_runs:
        r.note("states: none probed - loading, empty, error and permission-denied are graded "
               "from source, not measured (add \"states\" to the probe config)")

    # ---------------- Configured behavior ----------------
    behavior = payload.get("behavioralEvidence") or {}
    announcements = behavior.get("announcements") or []
    for item in announcements:
        status = item.get("status")
        label = item.get("label", "action")
        if status == "failed":
            r.add("a11y", CRIT, f"configured '{label}' action produced no matching status announcement",
                  "a programmatic status message without moving focus", sc="4.1.3",
                  summary=f"The '{label}' action changes status visually but its configured announcement expectation was not observed",
                  evidence=[f"expected={item.get('expected')!r}",
                            f"observed={[m.get('text') for m in item.get('messages', [])][:3]}",
                            f"focusMoved={item.get('focusMoved')}"] +
                           ([item.get("expectedError")] if item.get("expectedError") else []),
                  fix="Update an existing role=status/alert or appropriate aria-live region with the concise result; do not move focus merely to announce it.")
        elif status == "unreachable":
            r.add("interaction", MINOR, f"configured announcement action '{label}' was unreachable",
                  "journey executes", summary="Behavioral evidence was requested but not captured",
                  evidence=[item.get("reason", "")[:180]])
        timing = item.get("eventTiming") or {}
        if timing.get("supported") and timing.get("maxDuration", 0) > 200:
            r.add("interaction", MAJOR,
                  f"'{label}' interaction event took {timing['maxDuration']}ms in the lab",
                  "<=200ms interaction latency (field INP remains authoritative)",
                  summary="A configured user action exceeded the INP good threshold in this lab run",
                  evidence=[f"entries={timing.get('entries', [])[-4:]}"])
        loaf = item.get("longAnimationFrames") or {}
        if loaf.get("supported") and loaf.get("maxDuration", 0) > 100:
            r.add("interaction", MINOR,
                  f"'{label}' caused a {loaf['maxDuration']}ms long animation frame",
                  "no >100ms UI-thread stall during the action",
                  summary="The configured interaction contains a lab-observed UI-thread stall; LoAF is diagnostic, not a field-vitals substitute",
                  evidence=[f"count={loaf.get('count')} entries={loaf.get('entries', [])[-3:]}"])
    if not announcements:
        r.note("status announcements: no actions configured - live-region behavior is unchecked")

    widgets = behavior.get("widgets") or []
    for item in widgets:
        if item.get("status") == "verified":
            continue
        label = item.get("label", "widget")
        if item.get("status") == "failed":
            if item.get("kind") == "dialog":
                r.add("a11y", CRIT, f"configured dialog '{label}' failed focus/escape behavior",
                      "focus enters and stays in the dialog, Escape closes, focus returns", sc="2.4.3",
                      summary="The dialog does not preserve a logical keyboard focus sequence",
                      evidence=[f"focusInsideAtOpen={item.get('focusInsideAtOpen')}",
                                f"focusEscaped={item.get('focusEscaped')}",
                                f"escapeClosed={item.get('escapeClosed')}",
                                f"focusRestored={item.get('focusRestored')}"])
            else:
                r.add("a11y", CRIT, f"configured {item.get('kind')} '{label}' failed its arrow-key contract",
                      "forward and reverse APG keys both change widget state/focus", sc="2.1.1",
                      summary="The custom composite widget is present but its configured keyboard interaction does not operate",
                      evidence=[f"forward={item.get('forwardKey')} changed={item.get('forwardChanged')}",
                                f"reverse={item.get('reverseKey')} changed={item.get('reverseChanged')}",
                                f"selector={item.get('selector')}"])
        else:
            r.add("interaction", MINOR, f"configured widget '{label}' was unreachable",
                  "widget contract executes", summary="APG behavior was requested but could not be exercised",
                  evidence=[item.get("reason", "")[:180]])
    if not widgets:
        r.note("custom widgets: no APG contracts configured - static roles were checked, keyboard behavior was not")

    auth = behavior.get("authentication") or []
    for item in auth:
        if item.get("status") == "unreachable":
            r.add("interaction", MINOR, f"authentication check '{item.get('label')}' was unreachable",
                  "configured field is exercised", summary="Accessible-authentication evidence was not captured",
                  evidence=[item.get("reason", "")[:180]])
            continue
        if item.get("pasteAllowed") is False:
            r.add("a11y", CRIT, f"authentication field '{item.get('label')}' blocks paste",
                  "paste/password-manager path remains available", sc="3.3.8",
                  summary="The authentication flow prevents a cognitive-function-free entry method",
                  evidence=[f"selector={item.get('selector')}", f"autocomplete={item.get('autocomplete')}"])
        elif item.get("expectedPresent") is False:
            r.add("a11y", MAJOR, f"authentication field '{item.get('label')}' misses expected autocomplete metadata",
                  "declared password/OTP purpose", sc=None,
                  summary="Password-manager or one-time-code support is weakened; confirm the complete flow before attaching WCAG 3.3.8",
                  evidence=[f"selector={item.get('selector')}", f"autocomplete={item.get('autocomplete')}"])
    if not auth:
        r.note("accessible authentication: no fields configured - paste/password-manager behavior is unchecked")

    drag = behavior.get("dragAlternatives") or []
    for item in drag:
        if item.get("status") == "verified":
            continue
        if item.get("status") == "failed":
            r.add("a11y", CRIT, f"drag action '{item.get('label')}' has no keyboard-reachable single-pointer alternative",
                  "declared alternative is visible, enabled and keyboard reachable", sc="2.5.7",
                  summary="The configured operation requires a dragging movement",
                  evidence=[f"drag={item.get('dragSelector')}", f"alternative={item.get('alternativeSelector')}",
                            f"present={item.get('alternativePresent')} keyboard={item.get('alternativeKeyboardReachable')}"])
        else:
            r.add("interaction", MINOR, f"drag-alternative check '{item.get('label')}' was unreachable",
                  "configured action is exercised", summary="Dragging-movement evidence was not captured",
                  evidence=[item.get("reason", "")[:180]])
    if not drag:
        r.note("dragging movements: none configured - alternative-pointer behavior is unchecked")

    redundant = behavior.get("redundantEntries") or []
    for item in redundant:
        if item.get("status") == "verified":
            continue
        if item.get("status") == "failed":
            r.add("a11y", CRIT, f"multi-step process '{item.get('label')}' requires re-entering the same value",
                  "previous value is auto-populated or available to select", sc="3.3.7",
                  summary="The configured process imposes redundant entry without exposing the prior value",
                  evidence=[f"autoPopulated={item.get('autoPopulated')}", f"selectable={item.get('selectable')}",
                            f"second={item.get('secondSelector')} available={item.get('availableSelector')}"])
        else:
            r.add("interaction", MINOR, f"redundant-entry journey '{item.get('label')}' was unreachable",
                  "configured process executes", summary="Multi-step entry evidence was not captured",
                  evidence=[item.get("reason", "")[:180]])
    if not redundant:
        r.note("redundant entry: no multi-step processes configured - WCAG 3.3.7 behavior is unchecked")

    vision = payload.get("visionDeficiencyPasses") or []
    if vision:
        ran = [x.get("kind") for x in vision if x.get("status") == "ran"]
        bad = [x for x in vision if x.get("status") != "ran"]
        if ran:
            r.note("colour-vision evidence captured for " + ", ".join(ran) +
                   ". Pixel changes are expected; only a human-confirmed loss of status/selection/chart meaning may become a finding.")
        for item in bad:
            r.note(f"vision-{item.get('kind')}: {item.get('status')} - simulation unchecked")

    return r, {"primary": primary, "dark": dark, "reduced": reduced, "light": light,
               "states": state_runs, "baseline": baseline}


# --------------- slop grade (deterministic) ---------------
SLOP_RULES = [
    # (key, predicate, weight in letters, label)
    ("purpleOrIndigoGradients", lambda v: v >= 1, 1.0, "blue/indigo->purple gradient"),
    ("largeRadialGradients", lambda v: v >= 1, 1.0, "gradient-mesh/orb hero"),
    # Half a letter, not a full one: a three-up feature section is a
    # CONVENTION -- stripe.com and claude.com both ship one, and grading them
    # down a whole letter for it says the rubric is wrong, not the sites. The
    # slop version is the COMBINATION, handled as a combo rule below.
    ("threeUpFeatureGrids", lambda v: v >= 1, 0.5, "symmetrical three-up feature grid"),
    ("backdropBlurElements", lambda v: v >= 6, 1.0, "glassmorphism on everything"),
    ("centredShare", lambda v: v >= 60, 1.0, "centred-everything layout"),
    ("iconsInColouredCircles", lambda v: v >= 3, 0.5, "icons in coloured circles"),
    ("colouredLeftBorderCards", lambda v: v >= 2, 0.5, "coloured left-border cards"),
    ("gradientClippedText", lambda v: v >= 1, 0.5, "gradient text on headlines"),
    ("grayscaleLogoStrips", lambda v: v >= 1, 0.25, "grayscale logo strip"),
    # Decorative zero-padded ordinals as section ornament. Gated in probe.js to
    # patterned repeats, so a lone "01" of data never reaches here.
    ("decorativeStepNumbers", lambda v: v >= 2, 0.5, "decorative 01/02/03 step numbers"),
    # Em dashes are a RATE, not a count. One is a writer; a page that sustains
    # more than three per thousand characters is a model. Docking a page for a
    # single correct em dash is how a slop detector gets muted.
    ("emDashesPer1kChars", lambda v: v >= 3, 0.5, "em dashes at a density no writer sustains"),
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
    frames = len(sl.get("llmSentenceFrames") or [])
    if frames:
        w = 0.5 if frames < 2 else 1.0
        hits.append((f"LLM sentence frames ({frames}: 'not just X but Y' and kin)", w, frames))
        drop += w

    # The template tell is the STACK, not any one element: a three-up grid, with
    # icons in coloured circles, over category filler copy, is the landing page
    # that wrote itself. Any one of those alone is a choice; all of them
    # together is an absence of choices.
    three = sl.get("threeUpFeatureGrids") or 0
    circles = sl.get("iconsInColouredCircles") or 0
    if three >= 1 and (circles >= 3 or gen >= 2):
        hits.append(("...and it is the full template stack (3-up + icon circles/filler copy)",
                     0.5, f"grids={three} circles={circles} filler={gen}"))
        drop += 0.5
    # Each full letter is 3 quarter-steps on the ladder above.
    steps = int(round(drop * 3))
    grade = SLOP_LADDER[min(steps, len(SLOP_LADDER) - 1)]
    return grade, drop, hits


# --------------- A+ credit prequalification ---------------
#
# Above 92 the composite moves only on CREDITS, and until now credits were the
# one part of the scale with no measurement behind them: every gate in score.py
# is procedural (names a criterion, has evidence, cites two surfaces, sits on a
# clean pillar). So the scorer left the measurement rig at exactly the altitude
# where the pressure to be generous is highest.
#
# This closes that in the only direction that is safe: it FALSIFIES. Several
# clauses of each A+ criterion are measurable, and a measurable clause that
# fails means the credit is not available no matter how good the argument is.
# Nothing here ever awards a credit -- the stubs it writes are status
# "candidate", which score.py does not count -- and the clauses it cannot
# measure are printed as UNKNOWN so they stay somebody's job to argue.
#
# Read the verdicts as: BLOCKED = do not write this credit, the measurement
# says no. OPEN = the machine clauses hold; the human ones are still unproven.
# HUMAN = nothing here is measurable, argue it or drop it.
SLOP_FACES = {"Inter", "Roboto", "Poppins", "Montserrat", "Arial", "Helvetica",
              "system-ui", "-apple-system", "Segoe UI", "sans-serif",
              # The CSS Fonts 4 generic keywords. These belong here for exactly
              # the same reason `system-ui` does - they ARE the absence of a
              # decision - and leaving them out was a hole big enough to drive a
              # product through: Sheevook's DESIGN.md specifies Geist Sans and
              # Geist Mono, neither was ever installed, every surface rendered
              # `ui-sans-serif`, and this clause returned "a face chosen on
              # purpose: pass" for three rounds. A generic keyword resolving to
              # whatever the OS happens to ship is the definition of nobody
              # choosing.
              "ui-sans-serif", "ui-serif", "ui-monospace", "ui-rounded",
              "BlinkMacSystemFont", "monospace", "serif"}


def _surface(payload):
    """Flatten one probe payload into the facts the credit clauses ask about."""
    runs = payload.get("runs", [])
    light = [x for x in runs if not x.get("tag", "").startswith(AUX_TAG_PREFIXES)]
    if not light:
        return None
    primary = max(light, key=lambda x: get(x, "meta", "viewport", "w", default=0))
    base = next((x for x in light if x.get("tag") == "1440x900"), None) or primary
    dark = next((x for x in runs if x.get("tag", "").startswith("dark")), None)
    reduced = next((x for x in runs if x.get("tag", "").startswith("reduced")), None)
    narrow = [x for x in light if get(x, "meta", "viewport", "w", default=9999) <= 400]
    return {
        "label": payload.get("label") or "?",
        "payload": payload, "runs": runs, "light": light,
        "primary": primary, "base": base, "dark": dark, "reduced": reduced,
        "narrow": narrow,
        "productionBuild": bool(get(payload, "performance", "productionBuild", default=False)),
        "consoleErrors": len(payload.get("consoleErrors") or []),
    }


def _clause(name, verdict, detail):
    return {"clause": name, "verdict": verdict, "detail": detail}


def _typography_clauses(s):
    ty = get(s["primary"], "typography", default={})
    fams = [f.get("value", "") for f in ty.get("families", [])]
    out = []
    if not fams:
        out.append(_clause("a face chosen on purpose", "unknown", "no families measured"))
    elif fams[0] in SLOP_FACES:
        out.append(_clause("a face chosen on purpose", "fail",
                           f"the most-used face is {fams[0]} - a fallback doing the job of a voice"))
    else:
        out.append(_clause("a face chosen on purpose", "pass", f"primary face {fams[0]}"))

    # sizesUsedTwicePlus is a bare number list in current probes and a
    # {value,count} list in older ones. Accept both rather than crashing on a
    # payload from a previous round.
    sizes = sorted({float(x.get("value", 0)) if isinstance(x, dict) else float(x)
                    for x in ty.get("sizesUsedTwicePlus", [])})
    near = [(a, b) for a, b in zip(sizes, sizes[1:]) if b - a < 1.5 or (a and b / a < 1.06)]
    if not sizes:
        out.append(_clause("no near-duplicate steps", "unknown", "no repeated sizes measured"))
    elif near:
        out.append(_clause("no near-duplicate steps", "fail",
                           f"{len(near)} near-duplicate pairs: {near[:4]}"))
    else:
        out.append(_clause("no near-duplicate steps", "pass",
                           f"{len(sizes)} steps in real use: {[int(x) if x == int(x) else x for x in sizes]}"))

    ratios = [x for x in ty.get("adjacentRatios", []) if x]
    distinct_r = sorted({round(x, 2) for x in ratios})
    if not ratios:
        out.append(_clause("one ratio", "unknown", "no adjacent ratios measured"))
    elif len(distinct_r) > 3:
        out.append(_clause("one ratio", "fail",
                           f"{len(distinct_r)} distinct step ratios {distinct_r} - a scale, not a ratio"))
    else:
        out.append(_clause("one ratio", "pass", f"ratios {distinct_r}"))

    tables = get(s["primary"], "app", "tables", default=[])
    numeric = sum(t.get("numericCells", 0) for t in tables)
    aligned = sum(t.get("numericRightAligned", 0) for t in tables)
    if not numeric:
        out.append(_clause("tabular numerals where numbers align", "unknown",
                           "no numeric table columns on this surface"))
    elif aligned < numeric:
        out.append(_clause("tabular numerals where numbers align", "fail",
                           f"{numeric - aligned} of {numeric} numeric cells not right-aligned"))
    else:
        out.append(_clause("tabular numerals where numbers align", "unknown",
                           f"{numeric} numeric cells all right-aligned; the probe cannot read "
                           f"font-variant-numeric - confirm tabular-nums in source"))
    return out


def _spacing_clauses(s):
    sy = get(s["primary"], "system", default={})
    off = get(sy, "spacing", "offFourBase", default=[])
    dist = get(sy, "spacing", "distinct", default=0)
    out = [_clause("zero off-base values", "fail" if off else "pass",
                   f"off-base: {off[:8]}" if off else "every spacing value on the base")]
    out.append(_clause("6-8 named steps", "fail" if dist > 16 else "unknown",
                       f"{dist} distinct computed values - the probe counts COMPUTED spacing, so "
                       f"this is an upper bound; check the token file for the named count"))
    return out


def _color_clauses(s):
    share = get(s["primary"], "color", "accentPixelShare", default=0)
    out = [_clause("accent under 10% of pixels", "fail" if share >= 10 else "pass",
                   f"accent is {share}% of pixels")]
    if s["dark"] is None:
        out.append(_clause("a dark theme designed, not inverted", "unknown", "no dark pass in this payload"))
    else:
        dfail = get(s["dark"], "color", "textContrast", "failures", default=0)
        out.append(_clause("a dark theme designed, not inverted",
                           "fail" if dfail else "unknown",
                           f"{dfail} contrast failures in dark" if dfail else
                           "dark passes contrast; whether it was DESIGNED or inverted is an eye call "
                           "(color.md's five coherence tests, contrast.py --harmony)"))
    out.append(_clause("semantic roles in a perceptual space", "unknown",
                       "not visible from the rendered page - run contrast.py --harmony on the token file"))
    return out


def _interaction_clauses(s):
    out = []
    if not s["productionBuild"]:
        out.append(_clause("Core Web Vitals measured on a production build", "fail",
                           "this payload is a LAB run and is not flagged productionBuild - "
                           "observation is not a measurement"))
    else:
        perf = get(s["payload"], "performance", default={})
        lcp, cls = perf.get("largestContentfulPaint"), perf.get("cumulativeLayoutShift")
        bad = []
        if lcp and lcp > 2500:
            bad.append(f"LCP {lcp}ms > 2500")
        if cls is not None and cls >= 0.1:
            bad.append(f"CLS {cls} >= 0.1")
        out.append(_clause("Core Web Vitals measured on a production build",
                           "fail" if bad else "pass",
                           "; ".join(bad) or f"LCP {lcp}ms CLS {cls} on a production build "
                                             "(INP still needs a real interaction trace)"))
    # Judged on the MEASURED ring (the probe focuses things and looks), not on
    # CSS rule coverage. A single `*:focus-visible` rule scores badly on
    # coverage while every control in the product has a visible ring, and
    # blocking a credit on that is a threshold arguing with a fact.
    invisible = get(s["primary"], "interaction", "focusRing", "invisible", default=0)
    tested = get(s["primary"], "interaction", "focusRing", "tested", default=0)
    st = get(s["primary"], "states", default={})
    hover, disabled = st.get("hoverCoverage", 0), st.get("withDisabledRule", 0)
    out.append(_clause("all seven states designed", "fail" if invisible else "unknown",
                       f"{invisible} of {tested} focused elements had no visible ring" if invisible
                       else f"focus visible on all {tested} tested; hover rules on {hover}% and "
                            f"{disabled} disabled rules - loading, empty and error states still "
                            f"need an eye"))
    behavior = s["payload"].get("behavioralEvidence") or {}
    actions = ((behavior.get("announcements") or []) + (behavior.get("widgets") or []) +
               (behavior.get("authentication") or []) + (behavior.get("dragAlternatives") or []) +
               (behavior.get("redundantEntries") or []))
    failed = [x.get("label", "?") for x in actions if x.get("status") != "verified"]
    out.append(_clause("configured actions and widgets pass behavioral contracts",
                       "fail" if failed else "pass" if actions else "unknown",
                       f"failed/unreachable: {failed}" if failed else
                       f"{len(actions)} configured contracts verified" if actions else
                       "none configured; confirm not-applicable or run them"))
    return out


def _a11y_clauses(s):
    fails = sum(get(r, "color", "textContrast", "failures", default=0) for r in s["runs"]
                if not r.get("tag", "").startswith(("forced-colors", "contrast-more")))
    browser_missing = get(s["primary"], "a11y", "browserMissingAccessibleName", default=None)
    raw_names = (get(s["primary"], "a11y", "fieldsMissingLabel", "count", default=0)
                 + get(s["primary"], "a11y", "controlsMissingAccessibleName", "count", default=0))
    confirmed_names = browser_missing.get("failures", 0) if isinstance(browser_missing, dict) else raw_names
    missing_images = get(s["primary"], "a11y", "imagesMissingAlt", "count", default=0)
    missing = confirmed_names + missing_images
    name_state = "unknown" if browser_missing is None and raw_names and not missing_images else "fail" if missing else "pass"
    out = [_clause("zero AA failures in every pass", "fail" if fails else "pass",
                   f"{fails} contrast failures across all runs" if fails else "0 across all runs"),
           _clause("every control named", name_state,
                   f"{missing} browser-confirmed unnamed controls/images" if missing else
                   f"{raw_names} DOM candidates need runner confirmation" if name_state == "unknown" else "0 unnamed")]
    obscured = get(s["primary"], "interaction", "focusRing", "completelyObscured", default=0)
    browser_label = get(s["primary"], "a11y", "browserLabelInName", default={}) or {}
    structural = (get(s["primary"], "a11y", "unrecognizedLanguageTags", "count", default=0) +
                  get(s["primary"], "a11y", "invalidAutocomplete", "count", default=0))
    out.append(_clause("focus is never completely obscured", "fail" if obscured else "pass",
                       f"{obscured} completely obscured" if obscured else "0 completely obscured"))
    out.append(_clause("browser-confirmed Label in Name",
                       "fail" if browser_label.get("failures") else
                       "pass" if "failures" in browser_label else "unknown",
                       f"{browser_label.get('failures')} failures" if browser_label.get("failures") else
                       f"{browser_label.get('checked', 0)} candidates browser-checked" if browser_label else
                       "browser ARIA-name enrichment absent"))
    out.append(_clause("valid language and input-purpose metadata",
                       "fail" if structural else "pass",
                       f"{structural} invalid declarations" if structural else "no invalid declarations"))
    ran = {o.get("pass") for o in s["payload"].get("overridePasses", []) or []
           if o.get("status") == "ran"}
    want = set(OVERRIDE_PASSES)
    out.append(_clause("survives the user overrides",
                       "unknown" if want - ran else "pass",
                       f"not run: {', '.join(sorted(want - ran))}" if want - ran
                       else "forced-colors, contrast-more, text-spacing and 200% zoom all ran"))
    return out


def _responsive_clauses(s):
    over = [r.get("tag") for r in s["light"] if get(r, "layout", "horizontalOverflow", default=False)]
    out = [_clause("no horizontal overflow at any width", "fail" if over else "pass",
                   f"overflow at {over}" if over else f"clean across {len(s['light'])} viewports")]
    if not s["narrow"]:
        out.append(_clause("320px as considered as 1440px", "unknown", "no viewport <=400px probed"))
    else:
        tiny = sum(get(r, "interaction", "belowWcagTarget24", "count", default=0) for r in s["narrow"])
        out.append(_clause("320px as considered as 1440px", "fail" if tiny else "unknown",
                           f"{tiny} sub-24px targets on narrow viewports" if tiny else
                           "targets hold on narrow viewports; whether each breakpoint is a DECISION "
                           "is an eye call"))
    baseline = next((r for r in s["runs"] if r.get("tag") == "1440x900"), s["primary"])
    base_clip = get(baseline, "layout", "clippedContent", "count", default=0)
    for tag, label in (("text-expansion", "text expansion"), ("rtl", "applicable RTL")):
        run = next((r for r in s["runs"] if r.get("tag") == tag), None)
        if run is None:
            out.append(_clause(f"{label} stress", "unknown",
                               f"{tag} pass not run; confirm not-applicable or run it"))
            continue
        regressed = (get(run, "layout", "horizontalOverflow", default=False) and
                     not get(baseline, "layout", "horizontalOverflow", default=False))
        extra_clip = max(0, get(run, "layout", "clippedContent", "count", default=0) - base_clip)
        out.append(_clause(f"{label} stress", "fail" if regressed or extra_clip else "pass",
                           f"overflow={regressed}, additional clipping={extra_clip}"))
    return out


def _craft_clauses(s):
    sy = get(s["primary"], "system", default={})
    rad = get(sy, "radius", "distinct", default=0)
    sh = get(sy, "shadow", "distinct", default=0)
    z = get(sy, "zIndex", "distinct", default=0)
    out = [_clause("disciplined radius scale", "fail" if rad > 5 else "pass", f"{rad} radii"),
           _clause("disciplined shadow scale", "fail" if sh > 5 else "pass", f"{sh} shadows"),
           _clause("a named z-scale", "fail" if z > 6 else "pass", f"{z} z-index layers"),
           _clause("clean console", "fail" if s["consoleErrors"] else "pass",
                   f"{s['consoleErrors']} console errors" if s["consoleErrors"] else "no console errors")]
    stability = s["payload"].get("screenshotStability") or []
    unstable = [x.get("tag") for x in stability if x.get("status") != "stable"]
    out.append(_clause("stable visual baselines",
                       "fail" if unstable else "pass" if stability else "unknown",
                       f"unstable: {unstable}" if unstable else
                       f"{len(stability)} consecutive capture pairs stable" if stability else
                       "runner stability evidence absent"))
    out.append(_clause("no critical target-engine regression", "unknown",
                       "cross-engine.json is separate evidence; attach it or document target scope"))
    return out


def _motion_clauses(s):
    out = []
    if s["reduced"] is None:
        out.append(_clause("honours prefers-reduced-motion completely", "unknown",
                           "no reduced-motion pass in this payload"))
    else:
        still = get(s["reduced"], "motion", "animatedElements", default=0)
        out.append(_clause("honours prefers-reduced-motion completely",
                           "fail" if still else "pass",
                           f"{still} elements still animating under the preference" if still
                           else "nothing animates under the preference"))
    out.append(_clause("one moment someone would remember", "unknown",
                       "not measurable - name it or drop the credit"))
    return out


CREDIT_CLAUSES = {
    "typography": _typography_clauses,
    "spacing": _spacing_clauses,
    "color": _color_clauses,
    "interaction": _interaction_clauses,
    "a11y": _a11y_clauses,
    "responsive": _responsive_clauses,
    "craft": _craft_clauses,
    "motion": _motion_clauses,
}
# Criterion ids duplicated from score.py's A_PLUS_CRITERIA, which is the source
# of truth. --credits asserts they still match before printing anything, so a
# rename there cannot leave a stub naming a criterion that no longer exists.
CREDIT_IDS = {
    "typography": "typography.voice-and-ratio",
    "spacing": "spacing.composed-grid",
    "color": "color.designed-dark-and-range",
    "interaction": "interaction.states-and-vitals",
    "a11y": "a11y.beyond-aa",
    "responsive": "responsive.designed-breakpoints",
    "craft": "craft.decided-details",
    "motion": "motion.signature-moment",
}
HUMAN_ONLY_PILLARS = {
    "hierarchy": "hierarchy.singular-primary",
    "content": "content.voice-with-a-point-of-view",
    "ia": "ia.predictable-object-model",
}


def credit_prequal(paths, emit=None):
    surfaces = []
    for p in paths:
        with open(p) as fh:
            s = _surface(json.load(fh))
        if s:
            s["path"] = p
            surfaces.append(s)
    if not surfaces:
        print("No usable probe payloads.", file=sys.stderr)
        return 2

    print("A+ credit prequalification - what the measurements FALSIFY")
    print(f"surfaces: {', '.join(s['label'] for s in surfaces)}")
    print("=" * 78)
    if len(surfaces) < 2:
        print("WARNING: a credit needs >=2 probed surfaces. With one, every verdict below")
        print("is provisional and no stub is written.\n")

    stubs, blocked, open_ = [], [], []
    for pillar, fn in CREDIT_CLAUSES.items():
        per_surface = {s["label"]: fn(s) for s in surfaces}
        merged = {}
        for label, clauses in per_surface.items():
            for c in clauses:
                cur = merged.setdefault(c["clause"], {"verdict": "pass", "detail": []})
                # Worst verdict wins: one surface failing is the whole credit failing.
                order = {"pass": 0, "unknown": 1, "fail": 2}
                if order[c["verdict"]] >= order[cur["verdict"]]:
                    cur["verdict"] = c["verdict"]
                cur["detail"].append(f"{label}: {c['detail']}")
        fails = [k for k, v in merged.items() if v["verdict"] == "fail"]
        unknown = [k for k, v in merged.items() if v["verdict"] == "unknown"]
        verdict = "BLOCKED" if fails else "OPEN"
        print(f"\n{pillar:<12} {verdict:<8} {CREDIT_IDS[pillar]}")
        for name, v in merged.items():
            mark = {"pass": "  ok  ", "fail": " FAIL ", "unknown": "  ??  "}[v["verdict"]]
            print(f"  [{mark}] {name}")
            for d in v["detail"][:3]:
                print(f"           {d}")
        if fails:
            blocked.append((pillar, fails))
        else:
            open_.append((pillar, unknown))
            if len(surfaces) >= 2:
                stubs.append({
                    "id": f"CREDIT-{pillar.upper()}",
                    "pillar": pillar, "kind": "credit",
                    "criterion": CREDIT_IDS[pillar],
                    "evidence": "; ".join(f"{s['label']}: {s['path']}" for s in surfaces),
                    "surfaces": [s["label"] for s in surfaces],
                    "status": "candidate",
                    "unverifiedClauses": unknown,
                    "note": "Machine clauses hold. This is NOT a credit until the clauses above "
                            "are argued with evidence and the status is set to confirmed.",
                })

    print("\n" + "=" * 78)
    for pillar, criterion in HUMAN_ONLY_PILLARS.items():
        print(f"{pillar:<12} HUMAN    {criterion} - nothing here is measurable")
    print("-" * 78)
    print(f"BLOCKED by measurement: {', '.join(p for p, _ in blocked) or 'none'}")
    print(f"Machine clauses hold:   {', '.join(p for p, _ in open_) or 'none'}")
    print()
    print("A blocked pillar cannot carry a credit however good the argument is - fix the")
    print("measured clause first. An open pillar is not a credit either: the ?? clauses are")
    print("still yours to argue, on a pillar with zero open findings, in a LATER round than")
    print("the one that fixed its last defect.")

    if emit:
        with open(emit, "w") as fh:
            json.dump({"generated": "probe-report.py --credits",
                       "surfaces": [s["label"] for s in surfaces],
                       "findings": stubs}, fh, indent=1)
        print(f"\nwrote {emit} - {len(stubs)} candidate stub(s), status 'candidate' so score.py")
        print("does not count them. Promote one to 'confirmed' only with the argument written in.")
    return 0


# --------------- output ---------------
COVERED = {
    "typography": "probe measures families, scale, measure, leading",
    "color": "probe measures every rendered contrast pair",
    "spacing": "probe measures the real spacing set",
    "interaction": "probe tests focus, cursors, target sizes, native tooltips, scroll affordance, lab perf",
    "a11y": "probe tests names, labels, landmarks, outline, tab order, and the four override passes",
    "responsive": "probe sweeps viewports for overflow and target shrink",
    "craft": "probe measures radius/shadow/z scale, color-scheme, select chrome, console, meta",
    "motion": "probe compares a reduced-motion pass",
    "content": "probe matches filler copy, LLM sentence frames, em-dash rate, 01/02/03 ornament - never whether the copy is TRUE",
}
HUMAN_ONLY = {
    "hierarchy": "where the eye lands first, and whether that is the primary action",
    "ia": "whether the nav matches the user's mental model and vocabulary",
    "content": "whether the copy is TRUE, specific, and in the brand's voice",
    "consistency": "whether 3+ pages look like one product",
}


def cross_surface(paths):
    """Measure whether several surfaces look like ONE product.

    Brand Coherence asks that question and the answer was previously a letter
    somebody felt. Type voice, radius scale, spacing scale and accent
    discipline either match across surfaces or they do not, and that is
    countable. It stays a SUGGESTION -- consistency of system tokens is
    necessary for a product to look like itself, not sufficient.
    """
    def norm_font(name):
        # `anthropicSans`, `Anthropic Sans` and `"Anthropic Sans"` are one face.
        # Comparing raw computed strings reports 0% shared type voice across
        # pages of the SAME product, which is a bug in the comparison rather
        # than a finding about the product.
        return re.sub(r"[^a-z0-9]", "", str(name).lower())

    def norm_num(v):
        try:
            return str(int(round(float(v))))     # 9.6 and 10 are the same step
        except (TypeError, ValueError):
            return str(v)

    surfaces = []
    seen_labels = {}
    for p in paths:
        with open(p) as fh:
            payload = json.load(fh)
        runs = payload.get("runs", [])
        light = [x for x in runs if not x.get("tag", "").startswith(AUX_TAG_PREFIXES)]
        if not light:
            continue
        primary = max(light, key=lambda x: get(x, "meta", "viewport", "w", default=0))
        label = payload.get("label") or p
        if label in seen_labels:                 # keep labels distinguishable
            seen_labels[label] += 1
            label = f"{label}#{seen_labels[label]}"
        else:
            seen_labels[label] = 1
        surfaces.append({
            "label": label,
            "fonts": {norm_font(f["value"]) for f in get(primary, "typography", "families", default=[])},
            # families is ordered by usage, so [0] is the face doing the work.
            "primaryFont": norm_font((get(primary, "typography", "families", default=[{}])[:1] or [{}])[0].get("value", "")),
            "sizes": {norm_num(x) for x in get(primary, "typography", "sizesUsedTwicePlus", default=[])},
            # Prefer the full value sets; fall back to top-N for probe JSON
            # written before probe.js exported them.
            "radii": {norm_num(v) for v in (get(primary, "system", "radius", "values", default=None)
                      or [r["value"] for r in get(primary, "system", "radius", "top", default=[])])},
            "spacing": {norm_num(v) for v in (get(primary, "system", "spacing", "values", default=None)
                        or [s["value"] for s in get(primary, "system", "spacing", "top", default=[])])},
            "textColors": {c["value"] for c in get(primary, "color", "textColors", default=[])},
            "accent": get(primary, "color", "accentPixelShare", default=0),
            "shadows": get(primary, "system", "shadow", "distinct", default=0),
        })

    if len(surfaces) < 2:
        print("Need at least 2 probe files to compare. Pass 3+ for a Brand Coherence letter.")
        return 2

    print(f"Cross-surface consistency - {len(surfaces)} surfaces")
    print("=" * 78)
    for s in surfaces:
        print(f"  {s['label']:<22} fonts={len(s['fonts'])} radii={len(s['radii'])} "
              f"shadows={s['shadows']} accent={s['accent']}%")
    print("-" * 78)

    def overlap(key):
        """Overlap coefficient: shared / smallest set, NOT shared / union.

        The question is "do these surfaces share a vocabulary", not "do they use
        it equally often". A dense table legitimately uses more radii than a
        settings page; Jaccard-over-union punishes it for the extra values and
        reported F for three pages of one design system. Dividing by the
        smallest set asks the right question: is the smaller surface's
        vocabulary a subset of the others'.
        """
        sets = [s[key] for s in surfaces if s[key]]
        if not sets:
            return 1.0, set(), set()
        inter = set.intersection(*sets)
        union = set.union(*sets)
        smallest = min(len(x) for x in sets)
        return (len(inter) / smallest if smallest else 1.0), inter, union

    jaccard = overlap   # keep the call sites below reading naturally

    penalties = []
    rows = []
    # Type VOICE is the primary face, not the family set: a page that also loads
    # a mono face for one code sample has not changed its voice, and requiring
    # the whole set to intersect reported 0% shared voice across three pages of
    # one design system.
    primaries = {s["primaryFont"] for s in surfaces if s["primaryFont"]}
    if len(primaries) > 1:
        penalties.append(("type voice", 0, 3))
    print(f"  {'type voice':<16} " +
          ("consistent" if len(primaries) <= 1 else "DIFFERS") +
          f"   (primary face per surface: " +
          ", ".join(f"{s['label'].split('#')[0]}={s['primaryFont'] or '?'}" for s in surfaces) + ")")

    # weight 0 = reported but never penalised. The font SET differs the moment
    # one surface renders a code sample in mono, and text-colour sets differ the
    # moment one surface has an inverted section: both are normal, and
    # penalising them reported drift between pages that share one system. Voice
    # is covered by the primary-face check above.
    for key, label, weight, floor in [("fonts", "font set (info)", 0, 0.5),
                                      ("radii", "radius scale", 2, 0.6),
                                      ("sizes", "type scale", 2, 0.6),
                                      ("spacing", "spacing scale", 2, 0.6),
                                      ("textColors", "text colours (info)", 0, 0.3)]:
        share, inter, union = jaccard(key)
        rows.append((label, share, len(inter), len(union), floor))
        if share < floor and weight:
            penalties.append((label, share, weight))
    for label, share, inter, union, floor in rows:
        flag = "  <- drift" if share < floor else ""
        print(f"  {label:<16} {share * 100:5.1f}% shared   ({inter} common of {union} distinct){flag}")

    accents = [s["accent"] for s in surfaces]
    spread = max(accents) - min(accents)
    print(f"  {'accent share':<16} {min(accents)}% to {max(accents)}%   (spread {spread:.1f} points)")
    if spread > 12:
        penalties.append(("accent discipline", 0, 2))

    uniq = []
    for key, label in [("fonts", "font family"), ("radii", "radius")]:
        for s in surfaces:
            others = set.union(*[o[key] for o in surfaces if o is not s])
            only = s[key] - others
            if only:
                uniq.append(f"{s['label']} is the only surface using {label} {sorted(only)[:4]}")
    if uniq:
        print("\n  One-off usage (each of these is a place the system was not followed):")
        for u in uniq[:8]:
            print(f"    - {u}")

    # Suggested letter: start at A, drop by weighted drift.
    ladder = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"]
    steps = min(sum(w for _, _, w in penalties), len(ladder) - 1)
    print("-" * 78)
    print(f"Suggested --consistency: {ladder[steps]}"
          + (f"   (drift in: {', '.join(p[0] for p in penalties)})" if penalties else "   (no drift measured)"))
    if len(surfaces) < 3:
        print("Only 2 surfaces compared - Brand Coherence wants 3+ before the letter means much.")
    print("SUGGESTED, not decided: matching tokens are necessary for a product to look")
    print("like itself, not sufficient. Confirm against the screenshots before grading.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("probe_json", nargs="?")
    ap.add_argument("--compare", nargs="+", metavar="PROBE_JSON",
                    help="compare 2+ probe files for cross-surface consistency")
    ap.add_argument("--emit-findings", help="write a findings JSON skeleton for score.py")
    ap.add_argument("--credits", nargs="+", metavar="PROBE_JSON",
                    help="A+ credit prequalification: falsify the measurable clauses of each "
                         "criterion across 2+ surfaces")
    ap.add_argument("--emit-credits", metavar="FILE",
                    help="with --credits: write candidate credit stubs (never counted by score.py)")
    ap.add_argument("--expect-fixture", action="store_true",
                    help="assert the known fixture defects were caught")
    ap.add_argument("--quiet", action="store_true", help="table only, no guidance")
    args = ap.parse_args()

    if args.credits:
        # score.py owns A_PLUS_CRITERIA. Drifting ids would let this script
        # write stubs naming a criterion that no longer exists, which score.py
        # would then silently refuse - a stub that looks earned and never
        # counts is worse than no stub.
        try:
            sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
            from score import A_PLUS_CRITERIA
            drift = {p: (CREDIT_IDS.get(p), A_PLUS_CRITERIA[p][0])
                     for p in A_PLUS_CRITERIA
                     if p in CREDIT_IDS and CREDIT_IDS[p] != A_PLUS_CRITERIA[p][0]}
            missing = set(A_PLUS_CRITERIA) - set(CREDIT_IDS) - set(HUMAN_ONLY_PILLARS)
            if drift or missing:
                print("CRITERION DRIFT vs score.py - fix before trusting this output:",
                      file=sys.stderr)
                for p, (mine, theirs) in drift.items():
                    print(f"  {p}: this file says '{mine}', score.py says '{theirs}'", file=sys.stderr)
                for p in sorted(missing):
                    print(f"  {p}: score.py has a criterion this file does not cover", file=sys.stderr)
                return 2
        except ImportError:
            print("note: score.py not importable, criterion ids unverified\n")
        return credit_prequal(args.credits, emit=args.emit_credits)
    if args.compare:
        return cross_surface(args.compare)
    if not args.probe_json:
        ap.error("give a probe JSON, or --compare with 2+ of them")

    with open(args.probe_json) as fh:
        payload = json.load(fh)

    rep, ctx = analyse(payload)
    primary = ctx["primary"]
    grade, drop, hits = slop_grade(primary)

    print(f"probe-report - {payload.get('label','?')}  {payload.get('url','')}")
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

    if rep.notes:
        print("-" * 78)
        print("Measured and NOT counted (exceptions applied by the probe):")
        for n in rep.notes:
            print(f"  · {n}")

    print("-" * 78)
    print(f"AI Slop (measured layer): {grade}   (cumulative drop {drop:.2f} letters)")
    for label, w, v in hits:
        print(f"    -{w:<5} {label}  (measured {v})")
    if not hits:
        print("    no automatable slop tells fired - grade the taste layer by eye")

    wcag = sorted({r["wcag"] for r in rep.rows if r["wcag"] in WCAG_TRIGGERS})
    print("-" * 78)
    if wcag:
        print(f"WCAG AA failure candidates: {', '.join(wcag)}")
        print("If ANY survives confirmation, pass --wcag-fail to score.py. The cap is not optional.")
    else:
        print("No WCAG AA failure candidates in the measured layer.")

    if not args.quiet:
        print("-" * 78)
        print("Evidence ledger - what this run can and cannot grade:")
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
        print(f"\nwrote {args.emit_findings} - confirm/reject each, add eye-level findings, then:")
        print(f"  python3 score.py --findings {args.emit_findings}")

    if args.expect_fixture:
        need = {"color", "a11y", "interaction", "craft", "typography", "responsive", "motion", "content"}
        got = {r["pillar"] for r in rep.rows}
        missing = need - got
        print()
        if missing:
            print(f"FIXTURE CHECK FAILED - no candidate raised for: {', '.join(sorted(missing))}")
            sys.exit(1)
        print(f"fixture check ok - candidates raised across {len(got)} pillars, slop graded {grade}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
