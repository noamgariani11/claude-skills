/*
 * designer-dude in-page probe — turns the eyeball pillars into measurements.
 *
 * Runs inside the page and returns one JSON object of design FACTS: rendered
 * contrast ratios, the real type scale, the real radius scale, computed
 * cursors, actual target sizes, focus-ring visibility tested by focusing
 * things, accent pixel share, and the automatable slop tells.
 *
 * Why this exists: a review that grades Typography, Color, Spacing, Craft and
 * A11y from a screenshot is guessing, and a guess dressed as a grade is the
 * one failure mode that costs the user real work. Every number here is
 * measured from computed style in a real browser at a real viewport.
 *
 * It measures. It does not judge. Thresholds live in probe-report.py so the
 * judging layer is reviewable and identical across runs.
 *
 * Usage (preferred — zero context cost):
 *   browser_run_code_unsafe({ filename: ".../probe-runner.mjs" })
 *
 * Usage (fallback, if run_code_unsafe is unavailable): paste this file's
 * body into browser_evaluate as `() => { <body>; return __ddProbe(); }` and
 * pass `filename` so the JSON is written to disk instead of into context.
 */
function __ddProbe(opts) {
  var O = opts || {};
  var MAX_EL = O.maxElements || 6000;
  var TOP = O.top || 8;
  var EX = O.examples || 5;
  var out = { meta: {}, errors: [] };

  /* ---------------- helpers ---------------- */

  function safe(name, fn) {
    try { out[name] = fn(); } catch (e) {
      out.errors.push(name + ": " + (e && e.message ? e.message : String(e)));
    }
  }

  function selectorFor(el) {
    if (!el || !el.tagName) return "?";
    if (el.id) return el.tagName.toLowerCase() + "#" + el.id;
    var s = el.tagName.toLowerCase();
    var cls = (el.getAttribute && el.getAttribute("class")) || "";
    if (cls) {
      var parts = String(cls).trim().split(/\s+/).filter(function (c) {
        // Drop framework hash/state noise so the selector stays readable.
        return c && !/^(css-|sc-|jsx-|svelte-)/.test(c) && c.length < 28;
      }).slice(0, 3);
      if (parts.length) s += "." + parts.join(".");
    }
    var p = el.parentElement, depth = 0, path = s;
    while (p && p !== document.body && depth < 2) {
      var ps = p.tagName.toLowerCase();
      if (p.id) { path = ps + "#" + p.id + " > " + path; break; }
      path = ps + " > " + path;
      p = p.parentElement; depth++;
    }
    return path.slice(0, 120);
  }

  function textOf(el) {
    var t = "";
    for (var i = 0; i < el.childNodes.length; i++) {
      var n = el.childNodes[i];
      if (n.nodeType === 3) t += n.nodeValue;
    }
    return t.replace(/\s+/g, " ").trim();
  }

  function visible(el, cs) {
    cs = cs || getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") return false;
    if (parseFloat(cs.opacity) === 0) return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  // Resolve ANY css colour string (rgb, rgba, hsl, oklch, lab,
  // color(display-p3 ...), currentColor already resolved by computed style)
  // to 8-bit sRGB by asking the browser to paint it. Parsing colour syntax by
  // hand is how a contrast checker silently starts reporting 21:1 for every
  // oklch token, which is worse than not checking at all.
  var _cvs, _ctx, _colorCache = {};
  function rgba(str) {
    if (!str) return null;
    if (_colorCache[str] !== undefined) return _colorCache[str];
    var res = null;
    if (str === "transparent" || str === "rgba(0, 0, 0, 0)") {
      res = { r: 0, g: 0, b: 0, a: 0 };
    } else {
      if (!_ctx) {
        _cvs = document.createElement("canvas"); _cvs.width = _cvs.height = 1;
        _ctx = _cvs.getContext("2d", { willReadFrequently: true });
      }
      try {
        _ctx.clearRect(0, 0, 1, 1);
        _ctx.fillStyle = "#000";
        _ctx.fillStyle = str;              // invalid strings leave #000
        _ctx.fillRect(0, 0, 1, 1);
        var d = _ctx.getImageData(0, 0, 1, 1).data;
        res = { r: d[0], g: d[1], b: d[2], a: d[3] / 255 };
      } catch (e) { res = null; }
    }
    _colorCache[str] = res;
    return res;
  }

  function over(fg, bg) {           // composite fg (with alpha) onto opaque bg
    if (!fg) return bg;
    if (fg.a >= 1 || !bg) return fg;
    var a = fg.a;
    return {
      r: fg.r * a + bg.r * (1 - a),
      g: fg.g * a + bg.g * (1 - a),
      b: fg.b * a + bg.b * (1 - a),
      a: 1
    };
  }

  function lum(c) {
    function ch(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
    return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b);
  }

  function ratio(a, b) {
    var l1 = lum(a), l2 = lum(b);
    var hi = Math.max(l1, l2), lo = Math.min(l1, l2);
    return Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100;
  }

  // APCA (Lc) — ADVISORY ONLY. WCAG 2.2 ratio above is the conformance
  // number; APCA is a draft under consideration for WCAG 3 and is NOT
  // backward compatible. It is reported because it models font size/weight
  // and polarity, which is genuinely useful when a 4.51:1 pass still looks
  // thin. Never cite Lc as a conformance result.
  function apcaLc(txt, bg) {
    function y(c) {
      function s(v) { return Math.pow(v / 255, 2.4); }
      var Y = 0.2126729 * s(c.r) + 0.7151522 * s(c.g) + 0.072175 * s(c.b);
      return Y < 0.022 ? Y + Math.pow(0.022 - Y, 1.414) : Y;
    }
    var Yt = y(txt), Yb = y(bg), S, Lc;
    if (Yb > Yt) { S = (Math.pow(Yb, 0.56) - Math.pow(Yt, 0.57)) * 1.14; Lc = S < 0.1 ? 0 : (S - 0.027) * 100; }
    else { S = (Math.pow(Yb, 0.65) - Math.pow(Yt, 0.62)) * 1.14; Lc = S > -0.1 ? 0 : (S + 0.027) * 100; }
    return Math.round(Math.abs(Lc));
  }

  function hsl(c) {                  // for chroma / hue questions
    var r = c.r / 255, g = c.g / 255, b = c.b / 255;
    var mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
    var h = 0, l = (mx + mn) / 2, s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
    if (d !== 0) {
      if (mx === r) h = 60 * (((g - b) / d) % 6);
      else if (mx === g) h = 60 * ((b - r) / d + 2);
      else h = 60 * ((r - g) / d + 4);
    }
    if (h < 0) h += 360;
    return { h: Math.round(h), s: Math.round(s * 100) / 100, l: Math.round(l * 100) / 100 };
  }

  // Effective backdrop: first ancestor with a non-transparent background,
  // compositing any translucent layers on the way up. Reports when an image
  // or gradient sits behind the text, because a ratio against a gradient is
  // not a fact and must not be graded as one.
  function backdrop(el) {
    var layers = [], node = el, imageBehind = false, guard = 0;
    while (node && guard++ < 40) {
      var cs = getComputedStyle(node);
      if (cs.backgroundImage && cs.backgroundImage !== "none") imageBehind = true;
      var c = rgba(cs.backgroundColor);
      if (c && c.a > 0) {
        layers.push(c);
        if (c.a >= 1) break;
      }
      node = node.parentElement;
    }
    var base = { r: 255, g: 255, b: 255, a: 1 };
    for (var i = layers.length - 1; i >= 0; i--) base = over(layers[i], base);
    return { color: base, imageBehind: imageBehind };
  }

  // Counted bucket: counts EVERYTHING, keeps only the first `cap` examples.
  //
  // The naive `if (list.length < CAP) list.push(x)` then reporting
  // `list.length` as the count makes every count saturate at the cap: three
  // very different sites all reported "10 controls missing an accessible
  // name" because 10 was the cap, not the answer. Severity thresholds read
  // those counts, so saturation quietly caps how bad a page is allowed to
  // look. Count first, truncate the evidence only.
  function mk(cap) {
    return {
      n: 0, list: [], cap: cap,
      push: function (x) { this.n++; if (this.list.length < this.cap) this.list.push(x); },
      out: function () {
        return { count: this.n, list: this.list,
                 truncated: this.n > this.list.length ? this.n - this.list.length : 0 };
      }
    };
  }

  function tally(map, key) { map[key] = (map[key] || 0) + 1; }
  function topN(map, n) {
    return Object.keys(map).map(function (k) { return { value: k, count: map[k] }; })
      .sort(function (a, b) { return b.count - a.count; }).slice(0, n || TOP);
  }
  function distinct(map) { return Object.keys(map).length; }
  function px(v) { var n = parseFloat(v); return isNaN(n) ? null : Math.round(n * 100) / 100; }

  var ALL = Array.prototype.slice.call(document.querySelectorAll("*"), 0, MAX_EL);
  var VW = window.innerWidth, VH = window.innerHeight;

  /* ---------------- meta ---------------- */
  out.meta = {
    url: location.href,
    title: document.title || null,
    viewport: { w: VW, h: VH, dpr: window.devicePixelRatio },
    prefersDark: !!(window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches),
    prefersReducedMotion: !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches),
    elementsScanned: ALL.length,
    elementsTruncated: document.querySelectorAll("*").length > MAX_EL,
    lang: document.documentElement.getAttribute("lang") || null,
    hasViewportMeta: !!document.querySelector('meta[name="viewport"]'),
    hasFavicon: !!document.querySelector('link[rel~="icon"]'),
    themeColor: (document.querySelector('meta[name="theme-color"]') || {}).content || null,
    fontsLoaded: document.fonts ? document.fonts.size : null
  };

  /* ---------------- typography ---------------- */
  safe("typography", function () {
    var fams = {}, sizes = {}, weights = {}, leadingBySize = {}, aligns = {};
    var measures = [];
    var tightLeading = mk(EX), looseMeasure = mk(EX), displayNoTracking = mk(EX);
    var _cv = document.createElement("canvas").getContext("2d");

    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      if (!visible(el, cs)) return;
      var t = textOf(el);
      if (!t) return;
      var fam = cs.fontFamily.split(",")[0].replace(/["']/g, "").trim();
      tally(fams, fam);
      var fs = px(cs.fontSize);
      tally(sizes, String(fs));
      tally(weights, cs.fontWeight);
      tally(aligns, cs.textAlign);

      var lh = cs.lineHeight === "normal" ? null : px(cs.lineHeight);
      if (lh && fs) {
        var r = Math.round((lh / fs) * 100) / 100;
        leadingBySize[fs] = leadingBySize[fs] || [];
        if (leadingBySize[fs].length < 40) leadingBySize[fs].push(r);
        if (t.length > 120 && (r < 1.35 || r > 1.75)) {
          tightLeading.push({ sel: selectorFor(el), size: fs, leading: r, chars: t.length });
        }
      }

      // Real measure in ch, using this element's own font metrics.
      if (t.length > 160) {
        try {
          _cv.font = cs.fontWeight + " " + cs.fontSize + " " + cs.fontFamily;
          var chw = _cv.measureText("0").width;
          if (chw > 0) {
            var w = el.getBoundingClientRect().width;
            var pl = px(cs.paddingLeft) || 0, pr = px(cs.paddingRight) || 0;
            var ch = Math.round((w - pl - pr) / chw);
            if (ch > 0 && ch < 400) {
              measures.push(ch);
              if (ch < 45 || ch > 78) {
                looseMeasure.push({ sel: selectorFor(el), measureCh: ch, chars: t.length });
              }
            }
          }
        } catch (e) { /* font string the canvas cannot parse */ }
      }

      if (fs >= 32 && (px(cs.letterSpacing) === 0 || cs.letterSpacing === "normal")) {
        displayNoTracking.push({ sel: selectorFor(el), size: fs, text: t.slice(0, 40) });
      }
    });

    // Is the size set a scale, or a pile? Ratios between adjacent used sizes.
    var used = Object.keys(sizes).map(Number).filter(function (n) { return sizes[String(n)] >= 2; }).sort(function (a, b) { return a - b; });
    var ratios = [];
    for (var i = 1; i < used.length; i++) ratios.push(Math.round((used[i] / used[i - 1]) * 1000) / 1000);

    var avgLeading = {};
    Object.keys(leadingBySize).forEach(function (k) {
      var a = leadingBySize[k];
      avgLeading[k] = Math.round((a.reduce(function (x, y) { return x + y; }, 0) / a.length) * 100) / 100;
    });

    return {
      families: topN(fams), distinctFamilies: distinct(fams),
      sizes: topN(sizes, 14), distinctSizes: distinct(sizes),
      sizesUsedTwicePlus: used, adjacentRatios: ratios,
      weights: topN(weights), distinctWeights: distinct(weights),
      leadingBySize: avgLeading,
      measureCh: measures.length ? {
        min: Math.min.apply(null, measures), max: Math.max.apply(null, measures),
        median: measures.sort(function (a, b) { return a - b; })[Math.floor(measures.length / 2)],
        samples: measures.length
      } : null,
      offenders: {
        leadingOutOfBand: tightLeading.list, leadingOutOfBandCount: tightLeading.n,
        measureOutOfBand: looseMeasure.list, measureOutOfBandCount: looseMeasure.n,
        displayWithoutTracking: displayNoTracking.list, displayWithoutTrackingCount: displayNoTracking.n
      },
      textAlign: topN(aligns),
      // Straight quotes and apostrophes in rendered copy (Bringhurst).
      straightQuotes: (function () {
        var body = document.body ? document.body.innerText || "" : "";
        return {
          apostrophes: (body.match(/\w'\w/g) || []).length,
          doubleQuotes: (body.match(/"/g) || []).length,
          properApostrophes: (body.match(/\w’\w/g) || []).length
        };
      })()
    };
  });

  /* ---------------- colour + contrast ---------------- */
  safe("color", function () {
    var fails = mk(20), nearFails = mk(8);
    var textColors = {}, bgColors = {}, chromaArea = {}, gradients = {};
    var pureBlackWhite = 0, checked = 0, unknownBackdrop = 0;
    var accentArea = 0, totalArea = Math.max(1, VW * VH);

    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      if (!visible(el, cs)) return;
      var rect = el.getBoundingClientRect();

      var bgc = rgba(cs.backgroundColor);
      if (bgc && bgc.a > 0.05) {
        tally(bgColors, cs.backgroundColor);
        var h = hsl(bgc);
        // Chromatic fill = accent-ish. Area-weight it, clipped to viewport.
        if (h.s > 0.15 && h.l > 0.08 && h.l < 0.95) {
          var vw = Math.max(0, Math.min(rect.right, VW) - Math.max(rect.left, 0));
          var vh = Math.max(0, Math.min(rect.bottom, VH) - Math.max(rect.top, 0));
          accentArea += vw * vh;
          tally(chromaArea, cs.backgroundColor);
        }
      }
      if (cs.backgroundImage && /gradient/.test(cs.backgroundImage)) {
        tally(gradients, cs.backgroundImage.slice(0, 160));
      }
      if (/^rgb\(0, 0, 0\)$|^#000/.test(cs.color) || /^rgb\(255, 255, 255\)$/.test(cs.color)) pureBlackWhite++;

      var t = textOf(el);
      if (!t || t.length < 2) return;
      tally(textColors, cs.color);

      var fg = rgba(cs.color);
      var bd = backdrop(el);
      if (!fg || !bd.color) return;
      if (bd.imageBehind) { unknownBackdrop++; return; }   // not a fact; do not grade
      var composed = over(fg, bd.color);
      var r = ratio(composed, bd.color);
      var fs = px(cs.fontSize) || 16;
      var bold = parseInt(cs.fontWeight, 10) >= 700;
      var large = fs >= 24 || (bold && fs >= 18.66);
      var need = large ? 3 : 4.5;
      checked++;
      var rec = {
        sel: selectorFor(el), text: t.slice(0, 44), ratio: r, required: need,
        fontSize: fs, weight: cs.fontWeight, fg: cs.color, bg: cs.backgroundColor !== "rgba(0, 0, 0, 0)" ? cs.backgroundColor : "inherited",
        apcaLc: apcaLc(composed, bd.color)
      };
      if (r < need) fails.push(rec);
      else if (r < need + 0.6) nearFails.push(rec);
    });

    // Non-text contrast (WCAG 1.4.11) on form borders — the single most
    // commonly missed 3:1 requirement in real products.
    var borderFails = mk(8);
    Array.prototype.slice.call(document.querySelectorAll("input,select,textarea"), 0, 200).forEach(function (el) {
      var cs = getComputedStyle(el);
      if (!visible(el, cs)) return;
      var bw = px(cs.borderTopWidth) || 0;
      if (bw <= 0) return;
      var bc = rgba(cs.borderTopColor), bd = backdrop(el.parentElement || el);
      if (!bc || !bd.color || bd.imageBehind) return;
      var r = ratio(over(bc, bd.color), bd.color);
      if (r < 3) borderFails.push({ sel: selectorFor(el), ratio: r, required: 3, borderColor: cs.borderTopColor });
    });

    return {
      textContrast: {
        checked: checked, failures: fails.n, failureList: fails.list,
        failureListTruncated: fails.out().truncated,
        borderline: nearFails.list, borderlineCount: nearFails.n,
        skippedImageBackdrop: unknownBackdrop
      },
      nonTextContrast: { fieldBorderFailures: borderFails.n, list: borderFails.list },
      distinctTextColors: distinct(textColors), textColors: topN(textColors),
      distinctBackgrounds: distinct(bgColors), backgrounds: topN(bgColors),
      pureBlackOrWhiteText: pureBlackWhite,
      accentPixelShare: Math.round((accentArea / totalArea) * 1000) / 10,
      chromaticFills: topN(chromaArea, 6),
      gradients: { count: distinct(gradients), list: topN(gradients, 4) }
    };
  });

  /* ---------------- spacing, radius, elevation ---------------- */
  safe("system", function () {
    var pads = {}, gaps = {}, radii = {}, shadows = {}, zs = {}, durations = {}, borders = {};
    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      // z-index BEFORE the visibility gate: the elements carrying the top of a
      // stacking scale are modals, drawers and toasts, which are display:none
      // until opened. Gating on visibility hides exactly the sprawl worth
      // measuring and reports a disciplined 3-step scale on a page with nine.
      if (cs.zIndex && cs.zIndex !== "auto") tally(zs, cs.zIndex);
      if (!visible(el, cs)) return;
      ["paddingTop", "paddingLeft", "marginTop", "marginLeft"].forEach(function (p) {
        var v = px(cs[p]); if (v && v > 0) tally(pads, String(v));
      });
      if (cs.gap && cs.gap !== "normal") { var g = px(cs.gap); if (g) tally(gaps, String(g)); }
      var br = px(cs.borderTopLeftRadius);
      if (br !== null && br > 0) tally(radii, String(br));
      if (cs.boxShadow && cs.boxShadow !== "none") tally(shadows, cs.boxShadow.slice(0, 90));
      if (cs.transitionDuration && cs.transitionDuration !== "0s") tally(durations, cs.transitionDuration);
      var bw = px(cs.borderTopWidth); if (bw) tally(borders, String(bw));
    });

    var padKeys = Object.keys(pads).map(Number);
    var offBase = padKeys.filter(function (v) { return v % 4 !== 0 && v !== 1 && v !== 2 && v !== 3; });
    function nums(map) {
      return Object.keys(map).map(Number).sort(function (a, b) { return a - b; });
    }
    return {
      spacing: {
        distinct: padKeys.length, top: topN(pads, 12),
        // FULL sets as well as the top-N: the cross-surface consistency check
        // compares vocabularies, and comparing truncated top-8 lists reported
        // drift between pages that actually share one scale.
        values: nums(pads).slice(0, 60),
        offFourBase: offBase.sort(function (a, b) { return a - b; }).slice(0, 20),
        offFourBaseCount: offBase.length
      },
      gaps: { distinct: distinct(gaps), top: topN(gaps, 8), values: nums(gaps).slice(0, 40) },
      radius: { distinct: distinct(radii), top: topN(radii, 10), values: nums(radii).slice(0, 40) },
      shadow: { distinct: distinct(shadows), top: topN(shadows, 5) },
      zIndex: { distinct: distinct(zs), values: Object.keys(zs).sort(function (a, b) { return a - b; }).slice(0, 20) },
      borderWidths: topN(borders, 5),
      transitionDurations: topN(durations, 8)
    };
  });

  /* ---------------- interaction ---------------- */
  safe("interaction", function () {
    var CLICKABLE = 'a[href],button,[role="button"],[role="link"],[role="tab"],[role="menuitem"],summary,input[type="submit"],input[type="button"],[onclick]';
    var els = Array.prototype.slice.call(document.querySelectorAll(CLICKABLE), 0, 600);
    var missingPointer = mk(EX * 2), tooSmall = mk(EX), tinyTargets = mk(EX * 2), noTransition = 0;
    els.forEach(function (el) {
      var cs = getComputedStyle(el);
      if (!visible(el, cs)) return;
      var disabled = el.disabled || el.getAttribute("aria-disabled") === "true";
      if (!disabled && cs.cursor !== "pointer") {
        missingPointer.push({ sel: selectorFor(el), cursor: cs.cursor, text: (el.innerText || "").trim().slice(0, 32) });
      }
      var r = el.getBoundingClientRect();
      // WCAG 2.5.8 exempts links inline in a sentence; approximate that by
      // skipping <a> whose parent is a text block containing other text.
      var inlineException = el.tagName === "A" && cs.display === "inline" &&
        el.parentElement && textOf(el.parentElement).length > 0;
      var w = Math.round(r.width), h = Math.round(r.height);
      if (!inlineException && w > 0 && h > 0) {
        if (w < 24 || h < 24) {
          tinyTargets.push({ sel: selectorFor(el), w: w, h: h, text: (el.innerText || "").trim().slice(0, 24) });
        } else if (w < 44 || h < 44) {
          tooSmall.push({ sel: selectorFor(el), w: w, h: h });
        }
      }
      if (cs.transitionDuration === "0s") noTransition++;
    });

    // Focus ring: actually focus things and diff the computed style. This is
    // the only honest way to answer 2.4.7 — a grep cannot see a ring that
    // lives in a shared class, and a screenshot cannot see one at all.
    var FOCUSABLE = 'a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])';
    var fels = Array.prototype.slice.call(document.querySelectorAll(FOCUSABLE), 0, 60);
    var active = document.activeElement;
    var noRing = mk(EX * 2), tested = 0;
    fels.forEach(function (el) {
      try {
        var cs0 = getComputedStyle(el);
        if (!visible(el, cs0)) return;
        var before = [cs0.outlineWidth, cs0.outlineColor, cs0.boxShadow, cs0.borderColor, cs0.backgroundColor, cs0.outlineStyle].join("|");
        el.focus({ preventScroll: true });
        if (document.activeElement !== el) return;
        var cs1 = getComputedStyle(el);
        var after = [cs1.outlineWidth, cs1.outlineColor, cs1.boxShadow, cs1.borderColor, cs1.backgroundColor, cs1.outlineStyle].join("|");
        tested++;
        var ow = parseFloat(cs1.outlineWidth) || 0;
        var hasOutline = ow > 0 && cs1.outlineStyle !== "none";
        if (before === after && !hasOutline) {
          noRing.push({ sel: selectorFor(el), text: (el.innerText || el.value || "").toString().trim().slice(0, 28) });
        }
      } catch (e) { /* element refused focus */ }
    });
    try { if (active && active.focus) active.focus({ preventScroll: true }); } catch (e) {}

    return {
      clickable: els.length,
      missingPointerCursor: missingPointer.out(),
      belowWcagTarget24: tinyTargets.out(),
      belowFittsTarget44: tooSmall.out(),
      clickableWithoutTransition: noTransition,
      focusRing: { tested: tested, invisible: noRing.n, list: noRing.list,
                   truncated: noRing.out().truncated }
    };
  });

  /* ---------------- designed states ---------------- */
  //
  // The Interaction pillar (weight 10) asks whether hover / focus-visible /
  // active / disabled are DESIGNED. CSS pseudo-states cannot be synthesized
  // from JS, so instead of faking a pointer this walks the stylesheets and asks
  // "is there a rule carrying :hover that matches THIS element". That answers
  // the rubric's question per element rather than by grepping the repo for the
  // word "hover" and finding 1463 hits that prove nothing.
  safe("states", function () {
    var PSEUDO = ["hover", "focus-visible", "focus", "active", "disabled"];
    var rulesFor = {};
    PSEUDO.forEach(function (p) { rulesFor[p] = []; });
    var inaccessibleSheets = 0, reducedMotionRules = 0, sheetsRead = 0;

    function walk(rules) {
      for (var i = 0; i < rules.length; i++) {
        var r = rules[i];
        if (r.type === 4 || r.media) {                  // @media
          var txt = (r.conditionText || (r.media && r.media.mediaText) || "");
          if (/prefers-reduced-motion/.test(txt)) reducedMotionRules++;
          if (r.cssRules) walk(r.cssRules);
          continue;
        }
        if (r.cssRules && !r.selectorText) { walk(r.cssRules); continue; }  // @supports, @layer
        if (!r.selectorText) continue;
        var sel = r.selectorText;
        PSEUDO.forEach(function (p) {
          if (sel.indexOf(":" + p) === -1) return;
          // Strip the pseudo so the remainder can be matched against elements.
          sel.split(",").forEach(function (part) {
            if (part.indexOf(":" + p) === -1) return;
            var base = part.replace(new RegExp(":" + p + "(\\([^)]*\\))?", "g"), "").trim();
            if (base && rulesFor[p].length < 400) rulesFor[p].push(base);
          });
        });
      }
    }

    for (var s = 0; s < document.styleSheets.length; s++) {
      try {
        var cr = document.styleSheets[s].cssRules;
        if (!cr) { inaccessibleSheets++; continue; }
        sheetsRead++;
        walk(cr);
      } catch (e) {
        inaccessibleSheets++;      // cross-origin sheet: cannot be read, not a defect
      }
    }

    var CLICKABLE = 'a[href],button,[role="button"],[role="tab"],[role="menuitem"],summary,input[type="submit"]';
    var els = Array.prototype.slice.call(document.querySelectorAll(CLICKABLE), 0, 300)
      .filter(function (el) { return visible(el); });
    var counts = {};
    PSEUDO.forEach(function (p) { counts[p] = 0; });
    var missingHover = mk(EX);

    els.forEach(function (el) {
      PSEUDO.forEach(function (p) {
        var matched = rulesFor[p].some(function (base) {
          try { return el.matches(base); } catch (e) { return false; }
        });
        if (matched) counts[p]++;
        else if (p === "hover") {
          missingHover.push({ sel: selectorFor(el), text: (el.innerText || "").trim().slice(0, 28) });
        }
      });
    });

    var formControls = Array.prototype.slice.call(
      document.querySelectorAll("input,select,textarea,button"), 0, 300);
    var disabledPresent = document.querySelectorAll("[disabled],[aria-disabled=true]").length;

    return {
      stylesheetsRead: sheetsRead,
      // A page whose CSS is all cross-origin cannot be measured this way; say
      // so rather than reporting zero coverage as a design failure.
      inaccessibleStylesheets: inaccessibleSheets,
      interactiveElements: els.length,
      withHoverRule: counts.hover,
      withFocusVisibleRule: counts["focus-visible"],
      withFocusRule: counts.focus,
      withActiveRule: counts.active,
      withDisabledRule: counts.disabled,
      hoverCoverage: els.length ? Math.round((counts.hover / els.length) * 100) : null,
      focusVisibleCoverage: els.length ? Math.round((counts["focus-visible"] / els.length) * 100) : null,
      missingHoverExamples: missingHover.list,
      missingHoverCount: missingHover.n,
      reducedMotionMediaRules: reducedMotionRules,
      formControls: formControls.length,
      disabledControlsPresent: disabledPresent
    };
  });

  /* ---------------- accessibility (structure) ---------------- */
  safe("a11y", function () {
    function accName(el) {
      var n = el.getAttribute("aria-label") || "";
      if (!n && el.getAttribute("aria-labelledby")) {
        var ids = el.getAttribute("aria-labelledby").split(/\s+/);
        n = ids.map(function (i) { var e = document.getElementById(i); return e ? e.innerText : ""; }).join(" ");
      }
      if (!n && el.id) {
        var lab = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
        if (lab) n = lab.innerText;
      }
      if (!n && el.closest && el.closest("label")) n = el.closest("label").innerText;
      if (!n) n = (el.innerText || "").trim();
      // innerText is "" for anything not currently rendered, so a perfectly
      // labelled item inside a closed dropdown reads as nameless. textContent
      // sees it. Without this, a well-built site reports dozens of phantom
      // 4.1.2 failures -- and 4.1.2 is a CRITICAL that caps the whole score.
      if (!n) n = (el.textContent || "").trim();
      if (!n) n = el.getAttribute("title") || "";
      if (!n && el.tagName === "IMG") n = el.getAttribute("alt") || "";
      // An icon-only control is named by its SVG's title/aria-label, or by an
      // inner image's alt. Assistive tech honours those; so must this.
      if (!n) {
        var svg = el.querySelector && el.querySelector("svg");
        if (svg) {
          n = svg.getAttribute("aria-label") || "";
          var ttl = svg.querySelector && svg.querySelector("title");
          if (!n && ttl) n = (ttl.textContent || "").trim();
        }
      }
      if (!n) {
        var innerImg = el.querySelector && el.querySelector("img[alt]");
        if (innerImg) n = innerImg.getAttribute("alt") || "";
      }
      return (n || "").replace(/\s+/g, " ").trim();
    }

    var imgsNoAlt = mk(EX * 2), fieldsNoLabel = mk(EX * 2), btnsNoName = mk(EX * 2),
        placeholderOnly = mk(EX);
    Array.prototype.slice.call(document.images, 0, 300).forEach(function (el) {
      if (!el.hasAttribute("alt")) {
        imgsNoAlt.push({ sel: selectorFor(el), src: (el.currentSrc || el.src || "").slice(-60) });
      }
    });
    Array.prototype.slice.call(document.querySelectorAll("input,select,textarea"), 0, 300).forEach(function (el) {
      if (el.type === "hidden") return;
      var n = accName(el);
      if (!n) {
        fieldsNoLabel.push({ sel: selectorFor(el), type: el.type || el.tagName });
        if (el.placeholder) placeholderOnly.push({ sel: selectorFor(el), placeholder: el.placeholder });
      }
    });
    Array.prototype.slice.call(document.querySelectorAll('button,[role="button"],a[href]'), 0, 400).forEach(function (el) {
      if (!accName(el)) btnsNoName.push({ sel: selectorFor(el), html: el.innerHTML.slice(0, 40) });
    });

    var hs = Array.prototype.slice.call(document.querySelectorAll("h1,h2,h3,h4,h5,h6"));
    var levels = hs.map(function (h) { return parseInt(h.tagName[1], 10); });
    var skips = [];
    for (var i = 1; i < levels.length; i++) {
      if (levels[i] - levels[i - 1] > 1) {
        skips.push({ from: "h" + levels[i - 1], to: "h" + levels[i], text: (hs[i].innerText || "").slice(0, 40) });
      }
    }

    var ids = {}, dupes = [];
    ALL.forEach(function (el) { if (el.id) { if (ids[el.id]) dupes.push(el.id); else ids[el.id] = 1; } });

    var hiddenFocusable = 0;
    Array.prototype.slice.call(document.querySelectorAll('[aria-hidden="true"]'), 0, 200).forEach(function (el) {
      if (el.querySelector('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])')) hiddenFocusable++;
    });

    return {
      imagesMissingAlt: imgsNoAlt.out(),
      fieldsMissingLabel: fieldsNoLabel.out(),
      fieldsPlaceholderOnly: placeholderOnly.out(),
      controlsMissingAccessibleName: btnsNoName.out(),
      headings: { h1: document.querySelectorAll("h1").length, total: hs.length, skippedLevels: skips },
      landmarks: {
        main: document.querySelectorAll('main,[role="main"]').length,
        nav: document.querySelectorAll('nav,[role="navigation"]').length,
        header: document.querySelectorAll('header,[role="banner"]').length,
        footer: document.querySelectorAll('footer,[role="contentinfo"]').length
      },
      duplicateIds: { count: dupes.length, list: dupes.slice(0, EX) },
      ariaHiddenContainingFocusable: hiddenFocusable,
      positiveTabindex: document.querySelectorAll('[tabindex]:not([tabindex="0"]):not([tabindex="-1"])').length,
      autofocus: document.querySelectorAll("[autofocus]").length,
      liveRegions: document.querySelectorAll("[aria-live],[role=alert],[role=status]").length,
      lang: document.documentElement.getAttribute("lang") || null,
      skipLink: !!document.querySelector('a[href^="#"][class*="skip"],a[href^="#main"],a[href^="#content"]')
    };
  });

  /* ---------------- layout + responsiveness ---------------- */
  safe("layout", function () {
    var de = document.documentElement;
    var overflowers = mk(EX);
    if (de.scrollWidth > de.clientWidth + 1) {
      ALL.forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.width > 0 && r.right > de.clientWidth + 1) {
          overflowers.push({ sel: selectorFor(el), right: Math.round(r.right), viewport: de.clientWidth, width: Math.round(r.width) });
        }
      });
    }
    var sticky = [];
    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      if ((cs.position === "sticky" || cs.position === "fixed") && visible(el, cs) && sticky.length < EX) {
        var r = el.getBoundingClientRect();
        sticky.push({ sel: selectorFor(el), position: cs.position, height: Math.round(r.height), top: Math.round(r.top) });
      }
    });
    return {
      horizontalOverflow: de.scrollWidth > de.clientWidth + 1,
      scrollWidth: de.scrollWidth, clientWidth: de.clientWidth,
      overflowingElements: overflowers.list, overflowingElementCount: overflowers.n,
      documentHeight: de.scrollHeight,
      stickyOrFixed: sticky,
      // 2.4.11: a sticky header taller than the gap above a focused row can
      // obscure focus. Reported as a measurement to check, not a verdict.
      stickyTotalHeight: sticky.reduce(function (a, b) { return a + (b.top <= 1 ? b.height : 0); }, 0)
    };
  });

  /* ---------------- enterprise app surfaces ---------------- */
  safe("app", function () {
    var tables = Array.prototype.slice.call(document.querySelectorAll('table,[role="table"],[role="grid"]'), 0, 20);
    var tableInfo = tables.map(function (t) {
      var rows = t.querySelectorAll('tr,[role="row"]');
      var heights = [];
      Array.prototype.slice.call(rows, 1, 30).forEach(function (r) {
        var h = Math.round(r.getBoundingClientRect().height); if (h > 0) heights.push(h);
      });
      heights.sort(function (a, b) { return a - b; });
      var ths = t.querySelectorAll('th,[role="columnheader"]');
      var stickyHead = false;
      if (ths.length) { var cs = getComputedStyle(ths[0]); stickyHead = cs.position === "sticky"; }
      var numericCells = 0, rightAligned = 0;
      Array.prototype.slice.call(t.querySelectorAll("td"), 0, 200).forEach(function (td) {
        var txt = (td.innerText || "").trim();
        if (/^[$€£]?[\d,.]+%?$/.test(txt) && txt.length) {
          numericCells++;
          if (getComputedStyle(td).textAlign === "right") rightAligned++;
        }
      });
      return {
        sel: selectorFor(t), rows: rows.length, columns: ths.length,
        medianRowHeight: heights.length ? heights[Math.floor(heights.length / 2)] : null,
        stickyHeader: stickyHead,
        hasScope: !!t.querySelector("th[scope]"),
        hasCaption: !!t.querySelector("caption"),
        sortableHeaders: t.querySelectorAll("th[aria-sort],th button,[role=columnheader][aria-sort]").length,
        numericCells: numericCells, numericRightAligned: rightAligned,
        selectionCheckboxes: t.querySelectorAll('input[type="checkbox"]').length
      };
    });

    var forms = Array.prototype.slice.call(document.querySelectorAll("form"), 0, 10).map(function (f) {
      var fields = f.querySelectorAll("input,select,textarea");
      var required = f.querySelectorAll("[required],[aria-required=true]");
      return {
        sel: selectorFor(f), fields: fields.length, required: required.length,
        submitButtons: f.querySelectorAll('button[type="submit"],button:not([type]),input[type="submit"]').length,
        inlineErrors: f.querySelectorAll("[aria-invalid=true],[role=alert]").length,
        fieldsets: f.querySelectorAll("fieldset").length
      };
    });

    var bodyText = (document.body ? document.body.innerText || "" : "");
    return {
      tables: tableInfo,
      forms: forms,
      // Density signal: how much of the viewport is actually carrying content.
      textDensityChars: bodyText.replace(/\s+/g, " ").length,
      emptyStateSignals: (bodyText.match(/no results|nothing here|no .{0,20}yet|get started by|add your first/gi) || []).length,
      skeletonOrSpinner: document.querySelectorAll('[class*="skeleton"],[class*="spinner"],[aria-busy="true"],[class*="animate-pulse"]').length,
      disabledControls: document.querySelectorAll("[disabled],[aria-disabled=true]").length,
      keyboardHints: (bodyText.match(/⌘|Ctrl\+|Cmd\+|press .{0,10}to /gi) || []).length,
      paginationOrVirtualization: document.querySelectorAll('[aria-label*="agina" i],[class*="paginat"],[class*="virtual"]').length
    };
  });

  /* ---------------- motion ---------------- */
  safe("motion", function () {
    var anims = 0, longRunning = mk(EX), infinite = mk(EX), allProp = 0;
    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      if (cs.animationName && cs.animationName !== "none") {
        anims++;
        if (cs.animationIterationCount === "infinite") {
          infinite.push({ sel: selectorFor(el), name: cs.animationName, duration: cs.animationDuration });
        }
      }
      var d = parseFloat(cs.transitionDuration) || 0;
      if (d > 0.6) {
        longRunning.push({ sel: selectorFor(el), duration: cs.transitionDuration, property: cs.transitionProperty });
      }
      if (cs.transitionProperty === "all") allProp++;
    });
    return {
      animatedElements: anims,
      infiniteAnimations: infinite.out(),
      transitionsOver600ms: longRunning.list, transitionsOver600msCount: longRunning.n,
      transitionPropertyAll: allProp,
      reducedMotionActive: !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches)
    };
  });

  /* ---------------- slop tells (the automatable ones) ---------------- */
  safe("slop", function () {
    var tells = {};
    function note(k, v) { tells[k] = v; }

    // 1-2. purple/indigo gradients, and gradient-mesh heroes.
    //
    // These fire only on gradients that are actually VISIBLE AND CHROMATIC.
    // Without the alpha/saturation/area gates, a design-led site's 4%-opacity
    // decorative radial wash counted as a "gradient-mesh orb hero" and a
    // near-black dark-theme scrim counted as a purple gradient -- so the tool
    // graded Linear's slop an F, which is not a finding, it is a bug. A slop
    // detector that cannot tell a brand killer from a 0.04-alpha glow will be
    // ignored exactly when it is right.
    var grads = [], purpleGrad = 0, meshy = 0;
    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      if (!cs.backgroundImage || !/gradient/.test(cs.backgroundImage)) return;
      if (!visible(el, cs)) return;
      var r = el.getBoundingClientRect();
      var area = Math.max(0, Math.min(r.right, VW) - Math.max(r.left, 0)) *
                 Math.max(0, Math.min(r.bottom, VH) - Math.max(r.top, 0));
      if (area < VW * VH * 0.04) return;          // too small to set a tone
      var bi = cs.backgroundImage;
      var stops = bi.match(/rgba?\([^)]+\)|#[0-9a-f]{3,8}|oklch\([^)]+\)|oklab\([^)]+\)|color\([^)]+\)|hsla?\([^)]+\)/gi) || [];
      var chromatic = stops.map(function (s) {
        var c = rgba(s);
        if (!c || c.a < 0.25) return null;        // a near-transparent stop sets no tone
        var h = hsl(c);
        if (h.s < 0.25 || h.l < 0.12 || h.l > 0.94) return null;  // grey, near-black, near-white
        return h;
      }).filter(Boolean);
      var hues = chromatic.map(function (h) { return h.h; });
      var hasPurple = hues.some(function (h) { return h >= 255 && h <= 305; });
      var hasBlue = hues.some(function (h) { return h >= 205 && h <= 254; });
      if (hasPurple && (hasBlue || hues.length > 1)) purpleGrad++;
      // A mesh/orb hero is chromatic and big. A monochrome vignette is not.
      if (/radial-gradient/.test(bi) && chromatic.length >= 1 && area > VW * VH * 0.15) meshy++;
      if (grads.length < 4) {
        grads.push({ sel: selectorFor(el), hues: hues.slice(0, 4),
                     areaShare: Math.round((area / (VW * VH)) * 100),
                     image: bi.slice(0, 100) });
      }
    });
    note("purpleOrIndigoGradients", purpleGrad);
    note("largeRadialGradients", meshy);
    note("gradientSamples", grads);

    // 5/8/10. glassmorphism, uniform radius, backdrop blur
    var blur = 0;
    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      if ((cs.backdropFilter && cs.backdropFilter !== "none") || (cs.webkitBackdropFilter && cs.webkitBackdropFilter !== "none")) blur++;
    });
    note("backdropBlurElements", blur);

    // 9. icon in a coloured circle
    var iconCircles = 0;
    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      var r = el.getBoundingClientRect();
      if (r.width < 24 || r.width > 96 || Math.abs(r.width - r.height) > 4) return;
      var br = px(cs.borderTopLeftRadius) || 0;
      if (br < r.width * 0.45) return;
      var bg = rgba(cs.backgroundColor);
      if (!bg || bg.a < 0.2) return;
      if (hsl(bg).s < 0.15) return;
      if (el.querySelector("svg,img,i")) iconCircles++;
    });
    note("iconsInColouredCircles", iconCircles);

    // 3. three-up feature grid of icon + heading + paragraph
    var featureGrids = 0;
    Array.prototype.slice.call(document.querySelectorAll("*"), 0, 3000).forEach(function (el) {
      var cs = getComputedStyle(el);
      if (cs.display !== "grid") return;
      var cols = (cs.gridTemplateColumns || "").split(" ").filter(Boolean).length;
      if (cols !== 3) return;
      var kids = Array.prototype.slice.call(el.children, 0, 3);
      if (kids.length !== 3) return;
      var matching = kids.filter(function (k) {
        return k.querySelector("svg,img") && k.querySelector("h2,h3,h4,strong") && k.querySelector("p");
      }).length;
      if (matching === 3) featureGrids++;
    });
    note("threeUpFeatureGrids", featureGrids);

    // 12. emoji as design elements in headings/buttons
    var EMOJI = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/u;
    var emojiUi = mk(EX);
    Array.prototype.slice.call(document.querySelectorAll("h1,h2,h3,button,a[href]"), 0, 400).forEach(function (el) {
      var t = (el.innerText || "").trim();
      if (t && EMOJI.test(t)) emojiUi.push({ sel: selectorFor(el), text: t.slice(0, 40) });
    });
    note("emojiInHeadingsOrButtons", emojiUi.out());

    // 13. coloured left-border cards
    var leftBorderCards = 0;
    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      if (!visible(el, cs)) return;
      var l = px(cs.borderLeftWidth) || 0;
      if (l < 2) return;
      if ((px(cs.borderTopWidth) || 0) > 0.5) return;
      var c = rgba(cs.borderLeftColor);
      if (!c || c.a < 0.4) return;
      var h = hsl(c);
      // Near-black and near-white compute a high HSL saturation while reading
      // as neutral, which made every dark-theme hairline a "coloured accent
      // border". Require a mid lightness before calling a border coloured.
      if (h.s > 0.25 && h.l > 0.2 && h.l < 0.85) leftBorderCards++;
    });
    note("colouredLeftBorderCards", leftBorderCards);

    // 16. gradient text
    var gradText = 0;
    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      if ((cs.webkitBackgroundClip === "text" || cs.backgroundClip === "text") && /gradient/.test(cs.backgroundImage || "")) gradText++;
    });
    note("gradientClippedText", gradText);

    // 14. generic hero copy + AI self-reference badges
    var body = (document.body ? document.body.innerText || "" : "");
    var GENERIC = [
      /welcome to /i, /unlock the power/i, /all-in-one/i, /transform your (workflow|business)/i,
      /the future of /i, /take your .{2,20} to the next level/i, /supercharge/i, /effortlessly/i,
      /revolutioni[sz]e/i, /seamlessly integrate/i, /built for the modern/i, /powered by ai/i
    ];
    var genericHits = GENERIC.map(function (re) { var m = body.match(re); return m ? m[0] : null; }).filter(Boolean);
    note("genericMarketingCopy", genericHits);
    // "Powered by <model>" is a slop tell when it advertises someone else's
    // model as your product's substance. On the model provider's OWN site it is
    // a product name, not a dependency badge -- so skip the tell when the model
    // is the brand. (Caught on claude.com, where the rule fired on the word
    // "Claude". A tool that cannot tell whose brand it is looks stupid at
    // exactly the moment it needs to be trusted.)
    var brandContext = (location.hostname + " " + (document.title || "")).toLowerCase();
    var badges = (body.match(/powered by (gpt|claude|openai|gemini|llama)|built with (claude|gpt|openai)/gi) || [])
      .filter(function (m) {
        var model = m.toLowerCase().replace(/^(powered by|built with)\s+/, "");
        return brandContext.indexOf(model) === -1;
      });
    note("aiBadgeCopy", badges.slice(0, 4));

    // 7. centred-everything
    var blocks = 0, centred = 0;
    ALL.forEach(function (el) {
      var t = textOf(el);
      if (t.length < 40) return;
      var cs = getComputedStyle(el);
      if (!visible(el, cs)) return;
      blocks++;
      if (cs.textAlign === "center") centred++;
    });
    note("textBlocks", blocks);
    note("centredTextBlocks", centred);
    note("centredShare", blocks ? Math.round((centred / blocks) * 100) : 0);

    // 17. grayscale logo strip
    var logoStrips = 0;
    ALL.forEach(function (el) {
      var imgs = el.querySelectorAll(":scope > * img, :scope > img");
      if (imgs.length < 4) return;
      var gray = 0;
      Array.prototype.slice.call(imgs, 0, 10).forEach(function (i) {
        var f = getComputedStyle(i).filter || "";
        if (/grayscale|saturate\(0/.test(f)) gray++;
      });
      if (gray >= 3) logoStrips++;
    });
    note("grayscaleLogoStrips", logoStrips);

    return tells;
  });

  return out;
}

// Make it callable from both the runner and a pasted browser_evaluate call.
if (typeof window !== "undefined") window.__ddProbe = __ddProbe;
if (typeof module !== "undefined" && module.exports) module.exports = __ddProbe;
