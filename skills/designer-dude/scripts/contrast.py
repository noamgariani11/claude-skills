#!/usr/bin/env python3
"""contrast - WCAG 2.2 contrast maths for palettes and single pairs.

The skill claims contrast is one of the three things that are never taste
calls. That claim needs a calculator behind it, or it is just a firmer opinion.

    # one pair, with a concrete fix if it fails
    contrast.py "#faf9f5" "#8a8880"
    contrast.py "oklch(0.62 0.14 40)" "#faf9f5" --large

    # a whole palette, before presenting a direction (Mode A) or after
    # changing a token (Mode D)
    contrast.py --design-md DESIGN.md
    contrast.py --css src/app/globals.css
    contrast.py --pairs pairs.json

Reads hex, rgb(), hsl(), oklch(), oklab() and the handful of CSS names worth
supporting, so it works on a modern token file rather than only on hex.

Reports the WCAG 2.x ratio as the CONFORMANCE number, and APCA Lc alongside as
advisory only: APCA is a draft under consideration for WCAG 3, is not backward
compatible, and nobody should drop WCAG 2 conformance for it.
"""

import argparse
import io
import json
import math
import re
import sys

NAMED = {
    "white": (255, 255, 255), "black": (0, 0, 0), "transparent": None,
    "red": (255, 0, 0), "grey": (128, 128, 128), "gray": (128, 128, 128),
    "currentcolor": None, "inherit": None, "none": None,
}


# ---------------- colour parsing ----------------

def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c):
    c = _clamp(c)
    v = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return round(_clamp(v) * 255)


def oklch_to_rgb(L, C, h_deg):
    """OKLCH -> sRGB, via OKLab and the LMS cube-root space (Björn Ottosson)."""
    h = math.radians(h_deg)
    a, b = C * math.cos(h), C * math.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return (_linear_to_srgb(r), _linear_to_srgb(g), _linear_to_srgb(bb))


def rgb_to_oklch(r, g, b):
    lr, lg, lb = _srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)
    l = 0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb
    m = 0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb
    s = 0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(a, bb)
    h = math.degrees(math.atan2(bb, a)) % 360
    return (L, C, h)


def hsl_to_rgb(h, s, l):
    h = h % 360
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    r, g, b = {0: (c, x, 0), 1: (x, c, 0), 2: (0, c, x),
               3: (0, x, c), 4: (x, 0, c), 5: (c, 0, x)}[int(h // 60) % 6]
    return (round((r + m) * 255), round((g + m) * 255), round((b + m) * 255))


def parse_color(s):
    """Return (r, g, b) or None. Alpha is dropped with a note to the caller:
    a contrast ratio against a translucent colour is not a fact, and quietly
    treating alpha as opaque is how a checker reports a pass that is not one."""
    if s is None:
        return None
    t = str(s).strip().lower().rstrip(";").strip('"\'')
    if t in NAMED:
        return NAMED[t]

    m = re.fullmatch(r"#([0-9a-f]{3,8})", t)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        if len(h) in (6, 8):
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        return None

    m = re.fullmatch(r"rgba?\(([^)]+)\)", t)
    if m:
        parts = re.split(r"[,\s/]+", m.group(1).strip())
        try:
            vals = []
            for p in parts[:3]:
                vals.append(round(float(p[:-1]) * 2.55) if p.endswith("%") else round(float(p)))
            return tuple(max(0, min(255, v)) for v in vals)
        except ValueError:
            return None

    m = re.fullmatch(r"hsla?\(([^)]+)\)", t)
    if m:
        parts = re.split(r"[,\s/]+", m.group(1).strip())
        try:
            h = float(re.sub(r"deg$", "", parts[0]))
            s_ = float(parts[1].rstrip("%")) / 100
            l_ = float(parts[2].rstrip("%")) / 100
            return hsl_to_rgb(h, s_, l_)
        except (ValueError, IndexError):
            return None

    m = re.fullmatch(r"oklch\(([^)]+)\)", t)
    if m:
        parts = re.split(r"[,\s/]+", m.group(1).strip())
        try:
            L = float(parts[0].rstrip("%")) / (100 if parts[0].endswith("%") else 1)
            C = float(parts[1].rstrip("%"))
            if parts[1].endswith("%"):
                C = C / 100 * 0.4
            h = float(re.sub(r"deg$", "", parts[2])) if len(parts) > 2 else 0.0
            return oklch_to_rgb(L, C, h)
        except (ValueError, IndexError):
            return None

    m = re.fullmatch(r"oklab\(([^)]+)\)", t)
    if m:
        parts = re.split(r"[,\s/]+", m.group(1).strip())
        try:
            L = float(parts[0].rstrip("%")) / (100 if parts[0].endswith("%") else 1)
            a, b = float(parts[1]), float(parts[2])
            return oklch_to_rgb(L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360)
        except (ValueError, IndexError):
            return None
    return None


def to_hex(rgb):
    return "#%02x%02x%02x" % rgb


# ---------------- contrast maths ----------------

def luminance(rgb):
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def apca_lc(text_rgb, bg_rgb):
    def y(c):
        return sum(w * (v / 255) ** 2.4 for w, v in
                   zip((0.2126729, 0.7151522, 0.072175), c))

    def soft(Y):
        return Y + (0.022 - Y) ** 1.414 if Y < 0.022 else Y

    yt, yb = soft(y(text_rgb)), soft(y(bg_rgb))
    if yb > yt:
        s = (yb ** 0.56 - yt ** 0.57) * 1.14
        lc = 0 if s < 0.1 else (s - 0.027) * 100
    else:
        s = (yb ** 0.65 - yt ** 0.62) * 1.14
        lc = 0 if s > -0.1 else (s + 0.027) * 100
    return abs(lc)


def verdicts(r):
    return {
        "AA body (4.5)": r >= 4.5,
        "AA large/UI (3.0)": r >= 3.0,
        "AAA body (7.0)": r >= 7.0,
        "AAA large (4.5)": r >= 4.5,
    }


def suggest(fg, bg, need):
    """Find the smallest OKLCH lightness change to the FOREGROUND that passes.

    Lightness only, hue and chroma held: it keeps the brand recognisable, which
    is the difference between a fix someone ships and a fix someone argues with.
    """
    L, C, h = rgb_to_oklch(*fg)
    bg_lum = luminance(bg)
    # Move away from the background: darker text on a light surface, lighter on dark.
    direction = -1 if bg_lum > 0.18 else 1
    best = None
    for i in range(1, 101):
        cand_L = _clamp(L + direction * i * 0.005, 0.0, 1.0)
        cand = oklch_to_rgb(cand_L, C, h)
        if ratio(cand, bg) >= need:
            best = (cand, cand_L, ratio(cand, bg))
            break
    if best is None:
        # Lightness alone cannot get there; try dropping chroma too.
        for i in range(1, 101):
            cand_L = _clamp(L + direction * i * 0.005, 0.0, 1.0)
            for cscale in (0.75, 0.5, 0.25, 0.0):
                cand = oklch_to_rgb(cand_L, C * cscale, h)
                if ratio(cand, bg) >= need:
                    return (cand, cand_L, ratio(cand, bg), C * cscale)
        return None
    return (best[0], best[1], best[2], C)


# ---------------- palette extraction ----------------

# Role classification. Getting this wrong is not a cosmetic problem: pairing a
# tinted background token against a page surface as though it were text
# manufactures failures on a palette that is actually fine, and a checker that
# cries wolf gets ignored exactly when it is right. So: a `*-soft` /
# `*-subtle` token is a TINTED SURFACE (the fill behind a badge), never a
# foreground, and its partner is the text drawn on it.
TEXT_HINTS = ("ink", "body", "text", "muted", "foreground", "fg", "heading",
              "label", "placeholder", "secondary-text", "on-")
PAGE_SURFACE_HINTS = ("canvas", "paper", "background", "bg", "surface", "card",
                      "panel", "sheet", "base", "elevated")
TINTED_SURFACE_HINTS = ("-soft", "-subtle", "-tint", "-muted-bg", "-bg", "wash",
                        "overlay", "input", "-faint", "-weak")
FILL_HINTS = ("primary", "accent", "brand", "danger", "success", "warn", "error",
              "info", "destructive", "cta", "action")
# Never a text/background pairing at all: hairlines, dividers, rings, shadows.
NON_TEXT_HINTS = ("rule", "border", "divider", "ring", "shadow", "outline", "stroke",
                  "field-border", "separator")


def extract_design_md(path):
    """Pull the flat `colors:` block out of a Stitch-format DESIGN.md."""
    colors = {}
    with open(path) as fh:
        lines = fh.readlines()
    in_colors = False
    for raw in lines:
        line = raw.rstrip("\n")
        if re.match(r"^\s*colors:\s*$", line):
            in_colors = True
            continue
        if in_colors:
            if re.match(r"^\S", line) and not re.match(r"^\s", line) and ":" in line and not line.startswith(" "):
                if not re.match(r"^\s+", line):
                    in_colors = False
                    continue
            m = re.match(r'^\s+([a-z0-9-]+):\s*"?([^"#\n]*#[0-9a-fA-F]{3,8}|[^"\n]+?)"?\s*(?:#.*)?$', line)
            if m:
                key, val = m.group(1), m.group(2).strip()
                if parse_color(val):
                    colors[key] = val
    if not colors:  # fall back: any key: <colour> pair anywhere in the file
        for raw in lines:
            m = re.match(r'^\s*([a-z0-9-]+):\s*"?(#[0-9a-fA-F]{3,8}|oklch\([^)]*\)|rgb\([^)]*\))"?', raw)
            if m:
                colors[m.group(1)] = m.group(2)
    return colors


def extract_css(path):
    """Pull colour custom properties out of a stylesheet, KEYED BY THEME SCOPE.

    A themed stylesheet defines the same token twice -- once under :root and
    again under .dark / [data-theme=dark] / a prefers-color-scheme media query.
    Flattening those into one dict silently checks a chimera of both themes:
    light surfaces against dark text, passing pairings that exist in neither
    theme and failing ones that are fine in both. Since the whole point is that
    every pairing clears AA in BOTH themes, they get checked separately.
    """
    with open(path) as fh:
        css = fh.read()

    scopes = {}
    # Walk the file tracking the nearest enclosing selector/at-rule. This is a
    # deliberate approximation, not a CSS parser: it handles the token-file
    # shapes that exist in practice (:root, .dark, [data-theme], @media).
    scope_stack = ["root"]
    i = 0
    buf = ""
    while i < len(css):
        ch = css[i]
        if ch == "{":
            header = buf.strip().splitlines()[-1].strip() if buf.strip() else ""
            name = "root"
            h = header.lower()
            if "prefers-color-scheme: dark" in h or ".dark" in h or 'data-theme="dark"' in h \
               or "data-theme=dark" in h or "[data-mode=dark]" in h:
                name = "dark"
            elif "prefers-color-scheme: light" in h or ".light" in h or 'data-theme="light"' in h:
                name = "light"
            elif h.startswith(":root") or h.startswith("html") or h.startswith("@theme"):
                name = scope_stack[-1]
            else:
                name = scope_stack[-1]
            scope_stack.append(name)
            buf = ""
        elif ch == "}":
            if len(scope_stack) > 1:
                scope_stack.pop()
            buf = ""
        else:
            buf += ch
            if ch == ";":
                m = re.search(r"--([a-z0-9-]+)\s*:\s*([^;]+);\s*$", buf, re.I)
                if m and parse_color(m.group(2).strip()):
                    scopes.setdefault(scope_stack[-1], {})[m.group(1)] = m.group(2).strip()
                buf = ""
        i += 1

    base = scopes.get("root", {})
    out = {"light": dict(base)}
    if "light" in scopes:
        out["light"].update(scopes["light"])
    if "dark" in scopes:
        out["dark"] = dict(base)
        out["dark"].update(scopes["dark"])
    return out


def base_name(name):
    """Strip a framework prefix so `--color-accent-soft` reads as `accent-soft`."""
    n = name.lower()
    for p in ("color-", "colour-", "clr-", "c-", "theme-"):
        if n.startswith(p):
            return n[len(p):]
    return n


def classify(name):
    n = base_name(name)
    if any(h in n for h in NON_TEXT_HINTS):
        return "nontext"
    # Order matters: a tinted surface often also contains a fill word
    # (`accent-soft`), and it is a surface, not a fill.
    if any(h in n for h in TINTED_SURFACE_HINTS):
        return "tinted"
    if n.startswith("on-") or n.endswith("-foreground") or n.endswith("-fg"):
        return "on"
    if any(h in n for h in TEXT_HINTS):
        return "text"
    if any(h in n for h in PAGE_SURFACE_HINTS):
        return "surface"
    if any(h in n for h in FILL_HINTS):
        return "fill"
    return "other"


def partner_of(on_token):
    """`on-primary` / `accent-foreground` -> the fill it is drawn on."""
    n = base_name(on_token)
    if n.startswith("on-"):
        return n[3:]
    for suf in ("-foreground", "-fg"):
        if n.endswith(suf):
            return n[: -len(suf)]
    return None


def grid(colors):
    """Build pairings, split by how confident we are that they co-occur.

    CERTAIN pairings are the ones the naming makes explicit (on-primary is
    drawn on primary; ink is drawn on the canvas). INFERRED pairings might
    never happen on a real screen -- a `wash` token may be fill-only by house
    rule -- so they are reported separately and never counted as failures.
    """
    kinds = {k: classify(k) for k in colors}
    texts = [k for k, v in kinds.items() if v == "text"]
    surfaces = [k for k, v in kinds.items() if v == "surface"]
    tinted = [k for k, v in kinds.items() if v == "tinted"]
    fills = [k for k, v in kinds.items() if v == "fill"]
    ons = [k for k, v in kinds.items() if v == "on"]
    nontext = [k for k, v in kinds.items() if v == "nontext"]

    certain, inferred = [], []
    for t in texts:
        for s in surfaces:
            certain.append((t, s, "body"))

    # An `on-x` / `x-foreground` token has several plausible partners once a
    # palette has x, x-strong and x-soft, and the NAME does not say which. If
    # it clears AA on at least one of them, that is almost certainly the one it
    # is used on -- count that and send the rest to CHECK. Only when it fails
    # against EVERY candidate is there a real defect, because then there is no
    # surface in the palette it can legally be drawn on.
    def _colors_ok(a, b, need=4.5):
        ca, cb = parse_color(colors[a]), parse_color(colors[b])
        return bool(ca and cb and ratio(ca, cb) >= need)

    for on in ons:
        target = partner_of(on)
        matched = [f for f in fills + tinted
                   if target and (base_name(f) == target or base_name(f).startswith(target))]
        if not matched:
            if surfaces:
                inferred.append((on, surfaces[0], "body"))
            continue
        passing = [f for f in matched if _colors_ok(on, f)]
        if passing:
            certain.append((on, passing[0], "body"))
            for f in matched:
                if f not in passing[:1]:
                    inferred.append((on, f, "body"))
        else:
            for f in matched:
                certain.append((on, f, "body"))

    # Text on a tinted surface: plausible (badges, callouts) but house rules
    # may forbid it. Report, do not fail.
    for t in texts:
        for s in tinted:
            inferred.append((t, s, "body"))

    # A solid fill used as a UI boundary needs 3:1 against the page canvas.
    # Tinted variants are excluded: they are backgrounds, not boundaries.
    canvas = next((s for s in surfaces
                   if any(h in base_name(s) for h in ("canvas", "paper", "background", "bg"))),
                  surfaces[0] if surfaces else None)
    if canvas:
        for f in fills:
            certain.append((f, canvas, "ui"))
        # Hairlines are exempt from 1.4.11 as decoration, but a FIELD border is
        # not -- SC 1.4.11 covers the boundary of a control the user must find.
        for nt in nontext:
            if "field" in base_name(nt) or "input" in base_name(nt):
                certain.append((nt, canvas, "ui"))
    return {"certain": certain, "inferred": inferred, "texts": texts,
            "surfaces": surfaces, "tinted": tinted, "fills": fills, "ons": ons,
            "nontext": nontext}


# ---------------- reporting ----------------

def report_pair(fg_s, bg_s, large=False, ui=False, aaa=False, quiet=False):
    fg, bg = parse_color(fg_s), parse_color(bg_s)
    if fg is None or bg is None:
        print(f"cannot parse: {'foreground ' + repr(fg_s) if fg is None else ''}"
              f"{'background ' + repr(bg_s) if bg is None else ''}")
        return False
    if re.search(r"rgba?\([^)]*[,/ ]\s*0?\.\d+\s*\)|#[0-9a-f]{4}$|#[0-9a-f]{8}$",
                 str(fg_s).strip().lower()):
        print("  note: the foreground has alpha. This ratio treats it as opaque, which")
        print("        overstates contrast. Composite it over the real backdrop first.")
    r = ratio(fg, bg)
    need = 3.0 if (large or ui) else 4.5
    if aaa:
        need = 4.5 if (large or ui) else 7.0
    lc = apca_lc(fg, bg)
    ok = r >= need
    label = "large text / UI" if (large or ui) else "body text"
    print(f"{to_hex(fg)} on {to_hex(bg)}   {r:.2f}:1   (APCA Lc {lc:.0f}, advisory)")
    for k, v in verdicts(r).items():
        print(f"    {'PASS' if v else 'FAIL'}  {k}")
    if not ok:
        fix = suggest(fg, bg, need)
        if fix:
            cand, L, newr, newC = fix
            L0, C0, h0 = rgb_to_oklch(*fg)
            print(f"  needs {need}:1 for {label} - short by {need - r:.2f}")
            print(f"  fix: {to_hex(cand)}  =  oklch({L:.3f} {newC:.3f} {h0:.1f})"
                  f"   -> {newr:.2f}:1")
            print(f"       (was oklch({L0:.3f} {C0:.3f} {h0:.1f}); hue held so the brand survives)")
        else:
            print(f"  needs {need}:1 - unreachable by lightness/chroma alone. Change the pairing.")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("colors", nargs="*", help="foreground background")
    ap.add_argument("--large", action="store_true", help="grade against the 3:1 large-text threshold")
    ap.add_argument("--ui", action="store_true", help="grade against 3:1 for a UI component boundary")
    ap.add_argument("--aaa", action="store_true", help="grade against AAA instead of AA")
    ap.add_argument("--design-md", help="check every pairing in a DESIGN.md colors: block")
    ap.add_argument("--css", help="check every colour custom property in a stylesheet")
    ap.add_argument("--pairs", help='JSON: [["#fff","#000","body"], ...]')
    ap.add_argument("--harmony", action="store_true",
                    help="palette coherence (ramps, hue families, chroma, neutral "
                         "temperature, accent budget) instead of contrast pairings")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.harmony:
        path = args.design_md or args.css
        if not path:
            print("--harmony needs --css <file> or --design-md <file>")
            return 2
        themes = ({"single": extract_design_md(path)} if args.design_md
                  else extract_css(path))
        themes = {k: v for k, v in themes.items() if v}
        if not themes:
            print(f"no colour tokens found in {path}")
            return 2
        rc = 0
        for theme_name, colors in themes.items():
            if len(themes) > 1:
                print(f"\n{'=' * 76}\nTHEME: {theme_name}\n{'=' * 76}")
            rc = harmony(colors, path, theme_name) or rc
        return rc

    if args.pairs:
        with open(args.pairs) as fh:
            pairs = json.load(fh)
        fails = 0
        for row in pairs:
            fg, bg = row[0], row[1]
            kind = row[2] if len(row) > 2 else "body"
            if not report_pair(fg, bg, large=(kind == "large"), ui=(kind == "ui"), aaa=args.aaa):
                fails += 1
            print()
        print(f"{len(pairs)} pairs, {fails} failing")
        return 1 if fails else 0

    if args.design_md or args.css:
        path = args.design_md or args.css
        themes = ({"single": extract_design_md(path)} if args.design_md
                  else extract_css(path))
        themes = {k: v for k, v in themes.items() if v}
        if not themes:
            print(f"no colour tokens found in {path}")
            return 2
        rc = 0
        for theme_name, colors in themes.items():
            if len(themes) > 1:
                print(f"\n{'=' * 76}\nTHEME: {theme_name}\n{'=' * 76}")
            rc = check_palette(path, colors, theme_name) or rc
        if len(themes) == 1 and "dark" not in themes:
            print("\nOnly one theme found in this file. If the product has a dark mode defined")
            print("elsewhere, check that file too - 'designed, not inverted' is a grading line.")
        return rc

    if len(args.colors) == 2:
        ok = report_pair(args.colors[0], args.colors[1], args.large, args.ui, args.aaa)
        return 0 if ok else 1

    ap.print_help()
    return 2


# ---------------- palette coherence (the "do these belong together" half) ----

SEMANTIC_HINTS = {
    "accent": ("accent", "primary", "brand"),
    "danger": ("danger", "error", "destructive", "critical", "negative"),
    "success": ("success", "positive", "ok", "good"),
    "warning": ("warn", "warning", "caution", "attention"),
    "info": ("info", "note", "neutral-info"),
}
NEUTRAL_C_MAX = 0.035      # above this a token is reading as chromatic
NEUTRAL_C_TINTED = 0.003   # below this it is pure grey, with no temperature
HUE_CLUSTER_DEG = 25       # hues within this arc are the same family


def _hue_gap(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _role_of(name):
    n = base_name(name)
    for role, hints in SEMANTIC_HINTS.items():
        if any(h in n for h in hints):
            return role
    return None


def harmony(colors, path, theme_name="single"):
    """The five coherence tests from references/color.md, measured.

    Every row is a CANDIDATE, exactly like the probe's output. A two-accent
    palette can be correct and a wide neutral spread can be a deliberate
    warm-surface / cool-text split. Confirm before any of this becomes a
    finding.
    """
    toks = []
    for name, raw in colors.items():
        rgb = parse_color(raw)
        if not rgb:
            continue
        L, C, h = rgb_to_oklch(*rgb)
        toks.append({"name": base_name(name), "raw": raw, "rgb": rgb,
                     "L": L, "C": C, "h": h})
    if not toks:
        print(f"no parseable colours in {path}")
        return 2

    verdicts = []

    def say(level, headline, detail=""):
        verdicts.append((level, headline, detail))

    print(f"{len(toks)} colour tokens in {path}"
          + (f"  [{theme_name}]" if theme_name != "single" else ""))

    # --- Test: ramps -------------------------------------------------------
    ramps = {}
    for t in toks:
        m = re.match(r"^(.*?)-(\d{2,3})$", t["name"])
        if m:
            ramps.setdefault(m.group(1), []).append((int(m.group(2)), t))
    ramps = {k: sorted(v) for k, v in ramps.items() if len(v) >= 3}
    if ramps:
        print("\nRAMPS")
        for base, steps in sorted(ramps.items()):
            Ls = [t["L"] for _, t in steps]
            monotonic = all(a > b for a, b in zip(Ls, Ls[1:])) or all(a < b for a, b in zip(Ls, Ls[1:]))
            gaps = [abs(a - b) for a, b in zip(Ls, Ls[1:])]
            evenness = (max(gaps) / min(gaps)) if gaps and min(gaps) > 1e-6 else 99
            flat = [f"{steps[i][0]}/{steps[i+1][0]}" for i, g in enumerate(gaps) if g < 0.02]
            Cs = [t["C"] for _, t in steps]
            c_const = (max(Cs) - min(Cs)) < 0.01 and max(Cs) > 0.05
            print(f"  {base:<16} {len(steps)} steps  "
                  f"L {min(Ls):.2f}-{max(Ls):.2f}  "
                  f"C {min(Cs):.3f}-{max(Cs):.3f}  "
                  f"evenness {evenness:.1f}x  "
                  f"{'monotonic' if monotonic else 'NOT MONOTONIC'}")
            if not monotonic:
                say("FAIL", f"ramp `{base}` is not monotonic in lightness",
                    "a step is lighter than the one above it; the ramp has no usable order")
            if flat:
                say("FAIL", f"ramp `{base}` has near-duplicate steps: {', '.join(flat)}",
                    "two steps nobody can tell apart is a step that should not exist")
            elif evenness > 2.5:
                say("CHECK", f"ramp `{base}` steps are uneven ({evenness:.1f}x)",
                    "a cliff in the ramp means a needed value is missing")
            if c_const:
                say("CHECK", f"ramp `{base}` holds chroma constant across lightness",
                    "peak chroma belongs in the middle; the ends should fall off or they clip")

    # --- Test: hue families ------------------------------------------------
    chromatic = [t for t in toks if t["C"] >= NEUTRAL_C_MAX]
    families = []
    for t in sorted(chromatic, key=lambda x: x["h"]):
        for fam in families:
            if _hue_gap(fam["hue"], t["h"]) <= HUE_CLUSTER_DEG:
                fam["members"].append(t)
                fam["hue"] = sum(m["h"] for m in fam["members"]) / len(fam["members"])
                break
        else:
            families.append({"hue": t["h"], "members": [t]})
    print(f"\nHUE FAMILIES ({len(families)} chromatic, {len(toks) - len(chromatic)} neutral)")
    for fam in sorted(families, key=lambda f: -len(f["members"])):
        names = ", ".join(sorted({m["name"] for m in fam["members"]}))
        n = len(fam["members"])
        print(f"  h~{fam['hue']:6.1f}  {n:>2} token{' ' if n == 1 else 's'}  {names[:70]}")
    if len(families) > 6:
        say("FAIL", f"{len(families)} distinct chromatic hue families",
            "a coherent palette is one accent, one neutral, and the semantics that "
            "carry meaning: 4 to 6. More than that usually means a default palette "
            "was imported and used per component")
    elif len(families) > 4:
        say("CHECK", f"{len(families)} chromatic hue families",
            "every family past accent + semantics needs a named job")

    # --- Test: neutral temperature ----------------------------------------
    tinted = [t for t in toks if NEUTRAL_C_TINTED < t["C"] < NEUTRAL_C_MAX]
    pure = [t for t in toks if t["C"] <= NEUTRAL_C_TINTED]
    print(f"\nNEUTRALS  {len(pure)} pure grey, {len(tinted)} tinted")
    if tinted:
        hues = sorted(t["h"] for t in tinted)
        spread = max(_hue_gap(a, b) for a in hues for b in hues)
        print(f"  tinted hue range {min(hues):.0f}-{max(hues):.0f} (spread {spread:.0f} deg)")
        if spread > 40:
            say("CHECK", f"neutral tints disagree by {spread:.0f} degrees of hue",
                "warm surfaces against cool borders reads as dinginess nobody can name; "
                "pick one temperature")
    if pure and not tinted:
        say("CHECK", "every neutral is pure grey (C=0)",
            "safe, and it reads slightly cold and slightly cheap. A small chroma "
            "pulled toward or deliberately away from the accent is the cheapest "
            "upgrade in a palette")

    # --- Test: chroma agreement + semantic separation ---------------------
    roles = {}
    for t in toks:
        role = _role_of(t["name"])
        if role and t["C"] >= NEUTRAL_C_MAX:
            roles.setdefault(role, []).append(t)
    if roles:
        print("\nSEMANTIC ROLES")
        for role, ts in sorted(roles.items()):
            Cs = [t["C"] for t in ts]
            hs = [t["h"] for t in ts]
            print(f"  {role:<8} {len(ts):>2} token{' ' if len(ts) == 1 else 's'}  "
                  f"h {min(hs):5.0f}-{max(hs):5.0f}  C {min(Cs):.3f}-{max(Cs):.3f}")
        peak = {r: max(t["C"] for t in ts) for r, ts in roles.items()}
        non_accent = {r: c for r, c in peak.items() if r != "accent"}
        if len(non_accent) >= 2:
            lo, hi = min(non_accent.values()), max(non_accent.values())
            if lo > 0 and hi / lo > 2.0:
                weakest = min(non_accent, key=non_accent.get)
                say("CHECK", f"semantic chroma spread is {hi / lo:.1f}x "
                            f"(`{weakest}` is the washed-out one)",
                    "semantics that came from different places do not read as a set")
        acc = roles.get("accent")
        if acc:
            acc_h = sum(t["h"] for t in acc) / len(acc)
            for role, ts in roles.items():
                if role == "accent":
                    continue
                gap = min(_hue_gap(acc_h, t["h"]) for t in ts)
                if gap < HUE_CLUSTER_DEG:
                    say("FAIL", f"`{role}` sits {gap:.0f} degrees from the accent",
                        "the user cannot tell 'this is interactive' from 'this is a "
                        f"{role} state'. Move the hue or carry the state with an icon "
                        "and a word as well")
        if "success" in roles and "danger" in roles:
            s = max(roles["success"], key=lambda t: t["C"])
            d = max(roles["danger"], key=lambda t: t["C"])
            if abs(s["L"] - d["L"]) < 0.05:
                say("CHECK", "success and danger differ in hue but not lightness "
                             f"(L {s['L']:.2f} vs {d['L']:.2f})",
                    "roughly 8% of men cannot separate them. Desaturate a screenshot "
                    "and check the states are still readable")

    # --- Test: gamut -------------------------------------------------------
    # A declared oklch() that sRGB cannot hold gets clipped on the way to the
    # screen, so the colour you shipped is not the colour you wrote. Compare
    # what was declared against what came back.
    clipped = []
    for t in toks:
        m = re.match(r"oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+([\d.]+)", str(t["raw"]).strip().lower())
        if not m:
            continue
        decl_L = float(m.group(1).rstrip("%")) / (100 if m.group(1).endswith("%") else 1)
        decl_C = float(m.group(2))
        if abs(decl_C - t["C"]) > 0.02 or abs(decl_L - t["L"]) > 0.03:
            clipped.append(f"{t['name']} (declared L{decl_L:.2f}/C{decl_C:.3f}, "
                           f"renders L{t['L']:.2f}/C{t['C']:.3f})")
    if clipped:
        say("CHECK", f"{len(clipped)} token(s) fall outside sRGB and get clipped",
            "the colour on screen is not the colour in the file: "
            + "; ".join(clipped[:4]) + ". Pull chroma down at the light and dark "
            "ends of the ramp, or gate the extra chroma behind "
            "@media (color-gamut: p3) with an sRGB base")

    # --- Test: the absolutes ----------------------------------------------
    for t in toks:
        if t["rgb"] in ((0, 0, 0), (255, 255, 255)):
            say("CHECK", f"`{t['name']}` is pure {'black' if t['rgb'][0] == 0 else 'white'}",
                "pure black text halates for astigmatic readers and pure white "
                "surfaces have nowhere to go for elevation")
    if theme_name == "dark":
        darkest = min(toks, key=lambda t: t["L"])
        if darkest["L"] < 0.12:
            say("CHECK", f"darkest surface `{darkest['name']}` is L {darkest['L']:.2f}",
                "a dark theme's base wants L 0.15-0.20; below that, elevation has "
                "nowhere to go and light text smears")

    # --- verdicts ----------------------------------------------------------
    print("\n" + "-" * 76)
    if not verdicts:
        print("COHERENT. Nothing in the palette contradicts itself.")
        print("Contrast is a separate question: run without --harmony for the pairings.")
        return 0
    order = {"FAIL": 0, "CHECK": 1}
    for level, headline, detail in sorted(verdicts, key=lambda v: order[v[0]]):
        print(f"{level:<6} {headline}")
        if detail:
            for line in _wrap(detail, 68):
                print(f"       {line}")
    fails = sum(1 for v in verdicts if v[0] == "FAIL")
    print("-" * 76)
    print(f"{fails} fail, {len(verdicts) - fails} check. Every row is a candidate: "
          "confirm it against\nthe rendered page before it becomes a finding, and "
          "record the reason if you reject it.")
    return 1 if fails else 0


def _wrap(text, width):
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        out.append(line)
    return out


def check_palette(path, colors, theme_name="single"):
        g = grid(colors)
        print(f"{len(colors)} colour tokens in {path}")
        for label, key in [("text", "texts"), ("page surface", "surfaces"),
                           ("tinted surface", "tinted"), ("solid fill", "fills"),
                           ("on-fill text", "ons"), ("non-text", "nontext")]:
            if g[key]:
                print(f"  {label + ' roles:':<22} {', '.join(base_name(k) for k in g[key])}")
        unclassified = [k for k in colors if classify(k) == "other"]
        if unclassified:
            print(f"  {'unclassified:':<22} {', '.join(base_name(k) for k in unclassified[:12])}")
            print("     (skipped - rename them by role, or check them with --pairs)")
        if not g["certain"] and not g["inferred"]:
            print("\nNo checkable pairings. Name tokens by role (ink/body/muted on canvas/surface).")
            return 2

        def run(rows, counts):
            fails = []
            seen = set()
            for t, s, kind in rows:
                if (t, s, kind) in seen:
                    continue
                seen.add((t, s, kind))
                fg, bg = parse_color(colors[t]), parse_color(colors[s])
                if not fg or not bg:
                    continue
                r = ratio(fg, bg)
                need = 3.0 if kind == "ui" else 4.5
                mark = "PASS" if r >= need else ("FAIL" if counts else "CHECK")
                if r < need:
                    fails.append((t, s, r, need, fg, bg, kind))
                print(f"  {mark:<5} {base_name(t):>22} on {base_name(s):<20} {r:5.2f}:1  "
                      f"(needs {need}, Lc {apca_lc(fg, bg):3.0f})")
            return fails

        print("\nPairings the naming makes explicit - these count:")
        print("-" * 76)
        fails = run(g["certain"], True)
        print("-" * 76)

        if g["inferred"]:
            print("\nPairings that MIGHT never occur on a real screen - verify before acting:")
            print("(a tinted or fill-only token may be forbidden as a text backdrop by house")
            print(" rule; check the project's own styling notes before calling any of these")
            print(" a defect. They are excluded from the pass/fail count on purpose.)")
            print("-" * 76)
            run(g["inferred"], False)
            print("-" * 76)

        if fails:
            print(f"\n{len(fails)} failing pairing(s) - fixes, hue held:\n")
            for t, s, r, need, fg, bg, kind in fails:
                fix = suggest(fg, bg, need)
                L0, C0, h0 = rgb_to_oklch(*fg)
                if fix:
                    cand, L, newr, newC = fix
                    print(f"  {base_name(t)} on {base_name(s)}: {r:.2f} -> set "
                          f"{base_name(t)} to {to_hex(cand)} "
                          f"(oklch({L:.3f} {newC:.3f} {h0:.1f})) = {newr:.2f}:1")
                else:
                    print(f"  {base_name(t)} on {base_name(s)}: {r:.2f} - not reachable by "
                          f"lightness alone; change the pairing")
            print("\nA palette that fails here is not a direction, it is a rewrite waiting to")
            print("happen: under this rubric a shipped AA failure caps Overall at C+.")
            return 1
        print("\nEvery explicit role pairing clears AA. NOT checked: text over images or")
        print("gradients, translucent surfaces, disabled states, and dark-mode variants -")
        print("run the probe on the rendered page for those.")
        return 0


def selftest():
    """Known-good values from the WCAG maths and the OKLCH reference."""
    cases = [
        (("#000000", "#ffffff"), 21.0, 0.05),
        (("#ffffff", "#000000"), 21.0, 0.05),
        (("#767676", "#ffffff"), 4.54, 0.02),   # the canonical AA boundary grey
        (("#949494", "#ffffff"), 3.03, 0.03),   # canonical 3:1 grey
        (("#ffffff", "#ffffff"), 1.0, 0.001),
        (("#d97757", "#faf9f5"), 3.02, 0.10),   # claude.ai terracotta on cream
    ]
    fails = []
    for (fg, bg), expect, tol in cases:
        got = ratio(parse_color(fg), parse_color(bg))
        if abs(got - expect) > tol:
            fails.append(f"  ratio({fg},{bg}) = {got:.3f}, expected {expect} +/-{tol}")

    # OKLCH round-trip through sRGB must land back within a hair.
    for hexv in ("#d97757", "#141413", "#faf9f5", "#6a9bcc", "#788c5d"):
        rgb = parse_color(hexv)
        L, C, h = rgb_to_oklch(*rgb)
        back = oklch_to_rgb(L, C, h)
        if max(abs(a - b) for a, b in zip(rgb, back)) > 1:
            fails.append(f"  oklch round-trip {hexv} -> {to_hex(back)}")

    # Parsers must agree across syntaxes for the same colour.
    same = ["#ff0000", "rgb(255,0,0)", "rgb(255 0 0)", "hsl(0 100% 50%)", "hsl(0,100%,50%)"]
    vals = [parse_color(s) for s in same]
    if len({v for v in vals}) != 1:
        fails.append(f"  syntax disagreement: {list(zip(same, vals))}")

    # A known oklch token must resolve near its hex twin.
    got = parse_color("oklch(0.7 0.1 40)")
    if got is None or not all(0 <= c <= 255 for c in got):
        fails.append(f"  oklch() did not parse: {got}")

    # suggest() must actually produce a passing colour.
    fg, bg = parse_color("#a8a8a8"), parse_color("#ffffff")
    fix = suggest(fg, bg, 4.5)
    if not fix or ratio(fix[0], bg) < 4.5:
        fails.append(f"  suggest() failed to reach 4.5: {fix}")

    # APCA sanity: black on white is the maximum-ish, equal colours are 0.
    if apca_lc(parse_color("#000"), parse_color("#fff")) < 100:
        fails.append("  APCA black-on-white below Lc 100")
    if apca_lc(parse_color("#888"), parse_color("#888")) != 0:
        fails.append("  APCA equal colours nonzero")

    # --harmony must call a coherent palette coherent and a broken one broken.
    # A coherence checker that fires on good work gets muted, and then it is
    # not a checker.
    import contextlib
    good = {"canvas": "oklch(0.99 0.004 60)", "ink": "oklch(0.22 0.008 60)",
            "muted": "oklch(0.48 0.010 60)", "border": "oklch(0.86 0.008 60)",
            "accent-300": "oklch(0.80 0.12 250)", "accent-500": "oklch(0.62 0.16 250)",
            "accent-700": "oklch(0.45 0.13 250)", "danger": "oklch(0.55 0.17 27)",
            "success": "oklch(0.68 0.15 150)", "warn": "oklch(0.75 0.15 80)"}
    bad = dict(good)
    bad["danger"] = "oklch(0.58 0.17 248)"          # collides with the accent
    bad["accent-600"] = "oklch(0.615 0.16 250)"     # a near-duplicate ramp step
    for name, palette, want in (("good", good, 0), ("bad", bad, 1)):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = harmony(palette, "<selftest>")
        if rc != want:
            fails.append(f"  --harmony on the {name} palette returned {rc}, expected {want}")
        text = buf.getvalue()
        if name == "bad" and "degrees from the accent" not in text:
            fails.append("  --harmony missed the accent/danger hue collision")
        if name == "bad" and "near-duplicate" not in text:
            fails.append("  --harmony missed the near-duplicate ramp step")

    if fails:
        print("SELFTEST FAILED:")
        print("\n".join(fails))
        return 1
    print(f"selftest ok: {len(cases)} known ratios, oklch round-trips, "
          f"cross-syntax parsing, suggest(), APCA bounds and --harmony "
          f"(coherent vs broken) all check out")
    return 0


if __name__ == "__main__":
    sys.exit(main())
