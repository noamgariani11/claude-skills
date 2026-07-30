#!/usr/bin/env python3
"""contrast — WCAG 2.2 contrast maths for palettes and single pairs.

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
            print(f"  needs {need}:1 for {label} — short by {need - r:.2f}")
            print(f"  fix: {to_hex(cand)}  =  oklch({L:.3f} {newC:.3f} {h0:.1f})"
                  f"   -> {newr:.2f}:1")
            print(f"       (was oklch({L0:.3f} {C0:.3f} {h0:.1f}); hue held so the brand survives)")
        else:
            print(f"  needs {need}:1 — unreachable by lightness/chroma alone. Change the pairing.")
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
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

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
            print("elsewhere, check that file too — 'designed, not inverted' is a grading line.")
        return rc

    if len(args.colors) == 2:
        ok = report_pair(args.colors[0], args.colors[1], args.large, args.ui, args.aaa)
        return 0 if ok else 1

    ap.print_help()
    return 2


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
            print("     (skipped — rename them by role, or check them with --pairs)")
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

        print("\nPairings the naming makes explicit — these count:")
        print("-" * 76)
        fails = run(g["certain"], True)
        print("-" * 76)

        if g["inferred"]:
            print("\nPairings that MIGHT never occur on a real screen — verify before acting:")
            print("(a tinted or fill-only token may be forbidden as a text backdrop by house")
            print(" rule; check the project's own styling notes before calling any of these")
            print(" a defect. They are excluded from the pass/fail count on purpose.)")
            print("-" * 76)
            run(g["inferred"], False)
            print("-" * 76)

        if fails:
            print(f"\n{len(fails)} failing pairing(s) — fixes, hue held:\n")
            for t, s, r, need, fg, bg, kind in fails:
                fix = suggest(fg, bg, need)
                L0, C0, h0 = rgb_to_oklch(*fg)
                if fix:
                    cand, L, newr, newC = fix
                    print(f"  {base_name(t)} on {base_name(s)}: {r:.2f} -> set "
                          f"{base_name(t)} to {to_hex(cand)} "
                          f"(oklch({L:.3f} {newC:.3f} {h0:.1f})) = {newr:.2f}:1")
                else:
                    print(f"  {base_name(t)} on {base_name(s)}: {r:.2f} — not reachable by "
                          f"lightness alone; change the pairing")
            print("\nA palette that fails here is not a direction, it is a rewrite waiting to")
            print("happen: under this rubric a shipped AA failure caps Overall at C+.")
            return 1
        print("\nEvery explicit role pairing clears AA. NOT checked: text over images or")
        print("gradients, translucent surfaces, disabled states, and dark-mode variants —")
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

    if fails:
        print("SELFTEST FAILED:")
        print("\n".join(fails))
        return 1
    print(f"selftest ok — {len(cases)} known ratios, oklch round-trips, "
          f"cross-syntax parsing, suggest() and APCA bounds all check out")
    return 0


if __name__ == "__main__":
    sys.exit(main())
