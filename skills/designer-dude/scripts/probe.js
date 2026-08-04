/*
 * designer-dude in-page probe - turns the eyeball pillars into measurements.
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
 * Usage (preferred - zero context cost):
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

  // Machine locator kept separate from selectorFor's short human evidence.
  // A report may say "button.primary"; browser enrichment must identify the
  // exact node even when fifty plain buttons share that readable selector.
  function uniqueSelectorFor(el) {
    if (!el || !el.tagName) return null;
    if (el.id) return "#" + CSS.escape(el.id);
    var parts = [], node = el, depth = 0;
    while (node && node.nodeType === 1 && depth++ < 12) {
      var tag = node.tagName.toLowerCase();
      var parent = node.parentElement;
      if (parent) {
        var same = Array.prototype.filter.call(parent.children, function (x) { return x.tagName === node.tagName; });
        if (same.length > 1) tag += ":nth-of-type(" + (same.indexOf(node) + 1) + ")";
      }
      parts.unshift(tag);
      var candidate = parts.join(" > ");
      try { if (document.querySelectorAll(candidate).length === 1) return candidate; } catch (e) {}
      node = parent;
    }
    return parts.join(" > ") || null;
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
    // Content skipped by `content-visibility` -- which is how Chromium hides
    // the inside of a CLOSED <details> -- is still laid out, so it keeps a
    // non-zero rect and passes every check above. Without this gate the probe
    // reports contrast failures for answers no user has opened, and they cost
    // a full triage cycle each round to reject. checkVisibility() is the only
    // thing that knows; guarded because it is not in every engine.
    //
    // ONLY contentVisibilityAuto. Do NOT add opacityProperty here: it also
    // excludes anything inside an opacity-0 ANCESTOR, and on a page using
    // scroll-driven reveals that is most of the document at rest. Measured on
    // this project, adding it cut the checked text nodes from 309 to 68 while
    // still printing "contrast=0/68" -- a silent 78% coverage loss that reads
    // as a clean pass. A check that quietly stops looking is worse than one
    // that over-reports.
    if (typeof el.checkVisibility === "function") {
      if (!el.checkVisibility({ contentVisibilityAuto: true })) return false;
    }
    var r = el.getBoundingClientRect();
    if (!(r.width > 0 && r.height > 0)) return false;

    // Visually-hidden text: the standard sr-only recipe, which clips the box to
    // nothing while leaving it in the accessibility tree. It has no contrast
    // requirement because nobody sees it — WCAG 1.4.3 is about perceivable
    // text — and grading it invents a failure for the one pattern that exists
    // to HELP assistive tech. The tell is a 1×1-ish box with clip-path/clip
    // set, not merely a small element.
    if ((r.width <= 2 || r.height <= 2) &&
        ((cs.clipPath && cs.clipPath !== "none") ||
         (cs.clip && cs.clip !== "auto") ||
         cs.overflow === "hidden")) return false;

    // The same recipe, but with padding restored for the FOCUSED state - which
    // is exactly what a skip link is: `sr-only` plus `focus:not-sr-only px-4 py-2`.
    // The padding utilities override sr-only's `padding: 0`, so the border box
    // measures 32x16 while the content box is still 1x1 and the clip still hides
    // every pixel. The size heuristic above misses it, and the result was a WCAG
    // 2.5.8 "target under 24px" on the one element that is not a target until it
    // is focused - reported on every surface of every accessible site, since this
    // is the recommended skip-link technique. A zero-area clip is unambiguous on
    // its own: nothing is painted, whatever the box measures.
    var cp = cs.clipPath || "";
    var clipRect = (cs.clip || "").replace(/\s|px/g, "");
    if (cp === "inset(50%)" || clipRect === "rect(0,0,0,0)") return false;

    return true;
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

  // APCA (Lc) - ADVISORY ONLY. WCAG 2.2 ratio above is the conformance
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
  // Is `node` (or something just inside it) a photograph, and does it cover
  // `rect`? Depth 1 as well as the node itself, because a framework image
  // component renders <span><img></span> and the span is what the caption is a
  // sibling of.
  function coversWithImage(node, rect) {
    if (!node || node.nodeType !== 1) return false;
    var stack = [node], d = 0;
    for (var s = 0; s < stack.length && s < 12; s++) {
      var n = stack[s];
      var tag = n.tagName;
      var isPic = tag === "IMG" || tag === "VIDEO" || tag === "CANVAS" || tag === "PICTURE";
      if (!isPic) {
        var bi = getComputedStyle(n).backgroundImage;
        isPic = !!(bi && bi !== "none" && bi.indexOf("gradient") === -1);
      }
      if (isPic) {
        var r = n.getBoundingClientRect();
        // Covers, not merely touches: a thumbnail beside a paragraph is not
        // behind it. Require the text rect to sit inside the image rect.
        if (r.width > 0 && r.height > 0 &&
            r.left <= rect.left + 1 && r.right >= rect.right - 1 &&
            r.top <= rect.top + 1 && r.bottom >= rect.bottom - 1) return true;
      }
      if (d < 1 && n.children) {
        for (var c = 0; c < n.children.length && c < 8; c++) stack.push(n.children[c]);
      }
      if (s === 0) d++;
    }
    return false;
  }

  // Is this element, or anything it hangs from, taken out of normal flow?
  //
  // Only these can paint over something that is not an ancestor, which is the
  // one case where walking the DOM upward answers a different question than
  // "what is behind this text".
  function outOfFlow(el) {
    var n = el, guard = 0;
    while (n && n.nodeType === 1 && guard++ < 40) {
      var p = getComputedStyle(n).position;
      if (p === "fixed" || p === "sticky" || p === "absolute") return true;
      n = n.parentElement;
    }
    return false;
  }

  // What is ACTUALLY painted behind `rect`, by hit-testing rather than by
  // walking the DOM.
  //
  // A `position: fixed` transparent header floats over whatever the page has
  // scrolled under it, and its ancestor chain is <body> — so the upward walk
  // composites its text against the page background and reports a ratio for a
  // surface the text never touches. On a site whose header sits transparent
  // over a near-black hero this invents a whole screen of critical WCAG
  // failures: white-at-0.75 over ink-950 measures 11.19:1 and was being
  // reported as 1.03:1, on every dark-hero page, every round.
  //
  // Only the element itself and its DESCENDANTS are excluded: they are the
  // text's own box, not something behind it. Ancestors are kept, because an
  // opaque ancestor genuinely is the backdrop — a label absolutely positioned
  // inside a dark card must still measure against that card, not the page.
  // `elementsFromPoint` returns topmost-first, so the first opaque entry is
  // exactly what the compositor puts behind the glyphs.
  function paintedBehind(el, rect) {
    if (!rect || !rect.width || !document.elementsFromPoint) return null;
    var vw = window.innerWidth || 0, vh = window.innerHeight || 0;
    var x = rect.left + rect.width / 2, y = rect.top + rect.height / 2;
    // Clamp into the viewport when the box still overlaps it. At 200% text zoom
    // a header's contents reflow and an item's CENTRE can fall outside the
    // viewport while the element is plainly on screen; bailing there hands the
    // measurement back to the DOM walk and re-invents the failure this whole
    // path exists to prevent. Only clamp for a box that genuinely intersects —
    // a truly off-screen element gets no guess.
    if (rect.right > 0 && rect.left < vw && rect.bottom > 0 && rect.top < vh) {
      x = Math.min(Math.max(x, Math.max(rect.left, 0) + 1), Math.min(rect.right, vw) - 1);
      y = Math.min(Math.max(y, Math.max(rect.top, 0) + 1), Math.min(rect.bottom, vh) - 1);
    }
    if (x < 0 || y < 0 || x > vw || y > vh) return null;   // off-screen: cannot hit-test
    var stack = document.elementsFromPoint(x, y) || [];
    var found = [];
    for (var i = 0; i < stack.length; i++) {
      var n = stack[i];
      if (n === el || el.contains(n)) continue;
      var c = rgba(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) {
        found.push(c);
        if (c.a >= 1) return found;      // opaque: the stack ends here
      }
    }
    return null;                          // nothing opaque hit: keep the DOM walk's answer
  }

  function backdrop(el, rect) {
    var layers = [], node = el, imageBehind = false, guard = 0, hitOpaque = false;
    // Whether the FIRST opaque layer is the element's own background rather than
    // an ancestor's. Load-bearing for the out-of-flow branch below.
    var ownOpaque = false, first = true;
    while (node && guard++ < 40) {
      var cs = getComputedStyle(node);
      if (cs.backgroundImage && cs.backgroundImage !== "none") imageBehind = true;
      var c = rgba(cs.backgroundColor);
      if (c && c.a > 0) {
        layers.push(c);
        if (c.a >= 1) { hitOpaque = true; if (first) ownOpaque = true; break; }
      }
      first = false;
      node = node.parentElement;
    }

    // The ancestor walk catches a background-image ON the chain. It misses the
    // other common composition: a caption absolutely positioned over an <img>
    // that is its SIBLING, usually with a scrim div in between. All three share
    // a parent, so nothing on the chain carries an image, and the walk cheerfully
    // composites white caption text against the page background and reports 1:1.
    //
    // That is the difference between "measured 1:1" and "cannot be measured from
    // the DOM", and the probe's contract is to refuse the second rather than
    // guess it. Real captions of this shape pixel-measure 6.98-16.17:1, so
    // grading them from the DOM invents a critical WCAG failure that is not
    // there - and an invented critical is worse than a miss, because it survives
    // triage and gets argued about every round.
    if (!imageBehind && rect && rect.width > 0) {
      var up = el.parentElement, lift = 0;
      while (up && lift++ < 4 && !imageBehind) {
        for (var k = 0; k < up.children.length && k < 24; k++) {
          var sib = up.children[k];
          if (sib === el || sib.contains(el)) continue;
          if (coversWithImage(sib, rect)) { imageBehind = true; break; }
        }
        up = up.parentElement;
      }
    }

    // For an element taken out of flow, the upward walk answers "what are my
    // ancestors painted", which is not "what is behind me". Hit-test instead
    // and keep only the translucent layers the element itself contributes —
    // the opaque tail the walk found is an ancestor that the out-of-flow box
    // may not be sitting on at all.
    //
    // Deliberately narrow: in-flow text keeps the DOM walk (cheap, and correct
    // by construction), off-screen text cannot be hit-tested, and a hit-test
    // that finds nothing opaque falls back rather than guessing.
    //
    // And an element painting its OWN opaque background is never in doubt: that
    // colour is what its text sits on, whatever is behind the box. Skipping the
    // hit-test for it is not an optimisation, it is a correctness fix - the
    // `mine` loop below drops "the ancestor-derived opaque tail", and when the
    // first opaque layer came from the element itself that loop drops the only
    // right answer. An app shell wrapped in one `position: fixed` div makes
    // `outOfFlow` true for EVERY element under it, so a primary button measured
    // white-on-white and a whole product reported three invented critical WCAG
    // failures per surface, on every round. Verified against Sheevook: white on
    // #1d4ed8 is 6.70:1 and was being reported as 1:1.
    if (outOfFlow(el) && !ownOpaque) {
      var behind = paintedBehind(el, rect);
      if (behind) {
        var mine = [];
        for (var L = 0; L < layers.length; L++) {
          if (layers[L].a >= 1) break;    // drop the ancestor-derived opaque tail
          mine.push(layers[L]);
        }
        layers = mine.concat(behind);
      }
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
    lang: (document.documentElement.getAttribute("lang") || "").trim() || null,
    hasViewportMeta: !!document.querySelector('meta[name="viewport"]'),
    viewportMetaContent: (document.querySelector('meta[name="viewport"]') || {}).content || null,
    hasFavicon: !!document.querySelector('link[rel~="icon"]'),
    themeColor: (document.querySelector('meta[name="theme-color"]') || {}).content || null,
    fontsLoaded: document.fonts ? document.fonts.size : null,

    // What device does the PAGE think it is on? The runner asks for touch
    // emulation, but only the page can confirm it took. A "390px" run that
    // reports pointer:fine is a narrow desktop, and every coarse-pointer
    // conclusion drawn from it is void -- probe-report.py checks this rather
    // than trusting the requested config.
    device: (function () {
      var mm = function (q) { return !!(window.matchMedia && matchMedia(q).matches); };
      var cs = getComputedStyle(document.documentElement);
      // Safe-area insets read back as 0px unless viewport-fit=cover is set, so
      // report the raw values AND whether cover was requested.
      var inset = function (side) {
        var d = document.createElement("div");
        d.style.cssText = "position:fixed;height:0;width:0;padding-" + side +
                          ":env(safe-area-inset-" + side + ",0px);visibility:hidden";
        document.documentElement.appendChild(d);
        var v = parseFloat(getComputedStyle(d)["padding" + side.charAt(0).toUpperCase() + side.slice(1)]) || 0;
        d.remove();
        return Math.round(v);
      };
      return {
        pointerCoarse: mm("(pointer: coarse)"),
        anyPointerCoarse: mm("(any-pointer: coarse)"),
        hoverNone: mm("(hover: none)"),
        maxTouchPoints: navigator.maxTouchPoints || 0,
        orientation: VW >= VH ? "landscape" : "portrait",
        // WCAG 1.4.10 reflow is defined at 320 CSS px; visualViewport differs
        // from innerWidth under pinch-zoom and is what the user actually sees.
        visualViewport: window.visualViewport
          ? { w: Math.round(visualViewport.width), h: Math.round(visualViewport.height),
              scale: Math.round(visualViewport.scale * 100) / 100 }
          : null,
        viewportFitCover: /viewport-fit\s*=\s*cover/.test(
          ((document.querySelector('meta[name="viewport"]') || {}).content || "")),
        safeAreaInsets: { top: inset("top"), right: inset("right"),
                          bottom: inset("bottom"), left: inset("left") },
        colorScheme: cs.colorScheme || null,
        forcedColors: mm("(forced-colors: active)")
      };
    })()
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
    // 64x40 cells over the viewport: fine enough that a button does not round
    // up to a visible share, coarse enough to stay one small array.
    var ACCENT_COLS = 64, ACCENT_ROWS = 40;
    var accentCells = new Uint8Array(ACCENT_COLS * ACCENT_ROWS);

    var groundCells = new Uint8Array(ACCENT_COLS * ACCENT_ROWS);

    // Is this fill a GROUND rather than an accent?
    //
    // An accent marks the things you can act on: it is small, or it is
    // interactive, or both, and the threshold ("under 10% of pixels") exists
    // because an accent smeared everywhere stops signalling anything. A
    // full-bleed section band with body copy on it is doing the opposite job -
    // it is the surface the content sits on, and it is supposed to be large.
    // Charging it to the accent budget says "cut your accent" about a colour
    // that is not the accent, and the fix it recommends (move it to surface
    // tokens) is a no-op when it already IS a surface token.
    //
    // Three clauses, all required, so a full-bleed purple hero with one button
    // in it does not slip through: it must span the viewport, it must carry
    // real text of its own, and it must not be interactive.
    function isGround(el, rect) {
      if (rect.width < VW * 0.9) return false;
      if (el.closest("a[href],button,[role=button]")) return false;
      var t = (el.innerText || "").trim();
      if (t.length < 40) return false;
      return !!el.querySelector("p,h1,h2,h3,h4,li,dd,dt");
    }

    // Mark the viewport cells an element's box covers. Shared by the flat-fill
    // and the gradient path so the two cannot drift apart.
    function markGround(rect) {
      var x0 = Math.max(0, Math.min(rect.left, VW)), x1 = Math.max(0, Math.min(rect.right, VW));
      var y0 = Math.max(0, Math.min(rect.top, VH)), y1 = Math.max(0, Math.min(rect.bottom, VH));
      if (!(x1 > x0 && y1 > y0)) return;
      var cx0 = Math.floor(x0 / VW * ACCENT_COLS), cx1 = Math.ceil(x1 / VW * ACCENT_COLS);
      var cy0 = Math.floor(y0 / VH * ACCENT_ROWS), cy1 = Math.ceil(y1 / VH * ACCENT_ROWS);
      for (var gy = cy0; gy < cy1 && gy < ACCENT_ROWS; gy++) {
        for (var gx = cx0; gx < cx1 && gx < ACCENT_COLS; gx++) groundCells[gy * ACCENT_COLS + gx] = 1;
      }
    }

    function markAccent(rect) {
      var x0 = Math.max(0, Math.min(rect.left, VW)), x1 = Math.max(0, Math.min(rect.right, VW));
      var y0 = Math.max(0, Math.min(rect.top, VH)), y1 = Math.max(0, Math.min(rect.bottom, VH));
      if (!(x1 > x0 && y1 > y0)) return;
      var cx0 = Math.floor(x0 / VW * ACCENT_COLS), cx1 = Math.ceil(x1 / VW * ACCENT_COLS);
      var cy0 = Math.floor(y0 / VH * ACCENT_ROWS), cy1 = Math.ceil(y1 / VH * ACCENT_ROWS);
      for (var gy = cy0; gy < cy1 && gy < ACCENT_ROWS; gy++) {
        for (var gx = cx0; gx < cx1 && gx < ACCENT_COLS; gx++) accentCells[gy * ACCENT_COLS + gx] = 1;
      }
    }

    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      if (!visible(el, cs)) return;
      var rect = el.getBoundingClientRect();

      var bgc = rgba(cs.backgroundColor);
      if (bgc && bgc.a > 0.05) {
        tally(bgColors, cs.backgroundColor);
        var h = hsl(bgc);
        // Chromatic fill = accent-ish. Mark the viewport cells it covers.
        //
        // This used to SUM each element's clipped area, which double-counts
        // every nested chromatic element: a deep-water section containing a
        // deep-water scrim containing a deep-water panel charged the same
        // pixels three times. That is not a share, and it showed - the dark
        // pass of this very campaign reported 123%, 130% and 199%. A figure
        // above 100% is proof the metric was not measuring what it is named
        // after. Marking a coarse grid gives a real union, bounded at 100%,
        // for one bitmask instead of an accumulator.
        // Colourfulness as the eye meets it: absolute channel spread, scaled
        // by the fill's own alpha.
        //
        // The previous test was `h.s > 0.15 && 0.08 < h.l < 0.95`, and it was
        // wrong twice over, both caught on real products.
        //
        //  - Alpha was ignored, so a 10%-alpha status wash spanning a wide row
        //    was charged exactly like a solid accent fill. That is how a
        //    restrained dark console measured "accent covers 15.3%".
        //  - HSL saturation is meaningless near the ends of the lightness
        //    range. #e7eaf0 - a light-theme neutral grey, 9/255 of channel
        //    spread - reports s=0.231 and sailed past a 0.15 bar, so a light
        //    theme's own background counted as accent.
        //
        // Channel spread has neither failure: it is 9 for that grey, 111 for
        // #a78bfa, and multiplying by alpha makes a 0.1 wash contribute a
        // tenth of what the solid colour would.
        var spread = (Math.max(bgc.r, bgc.g, bgc.b) - Math.min(bgc.r, bgc.g, bgc.b)) * bgc.a;
        if (spread >= 25 && h.l > 0.06 && h.l < 0.97) {
          if (isGround(el, rect)) markGround(rect); else markAccent(rect);
          tally(chromaArea, cs.backgroundColor);
        }
      }
      if (cs.backgroundImage && /gradient/.test(cs.backgroundImage)) {
        tally(gradients, cs.backgroundImage.slice(0, 160));
        // A gradient paints pixels too. Until this existed, the accent-share
        // metric read `backgroundColor` only, so the single cheapest way to
        // hide accent overuse from this probe was to paint the section as a
        // gradient instead of a fill -- and "indigo-to-purple across the whole
        // hero" is item one on the slop list. The metric was rewarding the
        // exact pattern it exists to catch.
        //
        // Caught on a real product: a page header repainted from a two-stop
        // gradient to the identical flat token moved this figure from 2% to
        // 66.6% with PIXEL-IDENTICAL screenshots. Nothing about the page had
        // changed; the probe had simply started seeing what was already there.
        //
        // Judged on the most saturated stop, because that is what the eye
        // meets, and scored with the same spread-times-alpha bar as a flat
        // fill so the two paths cannot disagree. Photographic scrims stay
        // silent by construction: `black/80 -> transparent` and the neutral
        // portrait fades have a channel spread of zero at every stop.
        var stops = cs.backgroundImage.match(
          /(?:rgba?|hsla?|lab|lch|oklab|oklch|color)\([^()]*\)|#[0-9a-fA-F]{3,8}\b/g) || [];
        var peak = 0;
        for (var si = 0; si < stops.length; si++) {
          var sc = rgba(stops[si]);
          if (!sc) continue;
          var sl = hsl(sc).l;
          if (sl <= 0.06 || sl >= 0.97) continue;
          var ss = (Math.max(sc.r, sc.g, sc.b) - Math.min(sc.r, sc.g, sc.b)) * sc.a;
          if (ss > peak) peak = ss;
        }
        if (peak >= 25) {
          if (isGround(el, rect)) markGround(rect); else markAccent(rect);
          tally(chromaArea, cs.backgroundImage.slice(0, 160));
        }
      }
      var t = textOf(el);
      if (!t || t.length < 2) return;
      // Only elements that actually render text can have pure-black/white TEXT.
      // Run before the guard and this counts <html>, <head>, <meta>, <script>
      // and every <svg>, which merely inherit the UA default color.
      if (/^rgb\(0, 0, 0\)$|^#000/.test(cs.color) || /^rgb\(255, 255, 255\)$/.test(cs.color)) pureBlackWhite++;
      tally(textColors, cs.color);

      var fg = rgba(cs.color);
      var bd = backdrop(el, rect);
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

    // Non-text contrast (WCAG 1.4.11) on form borders - the single most
    // commonly missed 3:1 requirement in real products.
    var borderFails = mk(8);
    Array.prototype.slice.call(document.querySelectorAll("input,select,textarea"), 0, 200).forEach(function (el) {
      var cs = getComputedStyle(el);
      if (!visible(el, cs)) return;
      var bw = px(cs.borderTopWidth) || 0;
      if (bw <= 0) return;
      var bc = rgba(cs.borderTopColor),
          bd = backdrop(el.parentElement || el, el.getBoundingClientRect());
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
      accentPixelShare: (function () {
        var on = 0;
        for (var i = 0; i < accentCells.length; i++) on += accentCells[i];
        return Math.round((on / accentCells.length) * 1000) / 10;
      })(),
      // Reported separately, never hidden: a large chromatic band is a real
      // fact about the page and someone should still be able to see it. It is
      // simply not the accent budget, and grading it as one recommends
      // "move it to surface tokens" about something that already is one.
      chromaticGroundShare: (function () {
        var on = 0;
        for (var i = 0; i < groundCells.length; i++) on += groundCells[i];
        return Math.round((on / groundCells.length) * 1000) / 10;
      })(),
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
      // `mx-auto` centring is not a scale step. getComputedStyle RESOLVES auto
      // to a used pixel value, so a centred container reports whatever
      // (viewport - max-width) / 2 happens to be: 75px at 1440, 315px at 1920.
      // The "seen at most twice" exclusion below was meant to catch this, but a
      // page with three or more centred containers repeats the same number and
      // slips through as authored drift — it was the ONLY off-base value on a
      // site whose spacing is otherwise entirely on a 4px base.
      //
      // The test is deliberately narrow: equal left/right margins AND a
      // constrained box. An authored symmetric margin (`mx-8`) is on-base and
      // would not be flagged anyway, so nothing real is lost.
      var centred = cs.marginLeft === cs.marginRight &&
                    cs.maxWidth && cs.maxWidth !== "none";
      var spacingProps = centred
        ? ["paddingTop", "paddingLeft", "marginTop"]
        : ["paddingTop", "paddingLeft", "marginTop", "marginLeft"];
      spacingProps.forEach(function (p) {
        var v = px(cs[p]);
        // Fractional pixels are not scale steps. The off-base test below
        // already states the doctrine — "every Tailwind step and every
        // arbitrary value is a whole number, so a fractional pixel is
        // definitionally not authored" — but it only applied it to the
        // off-base list, while the DISTINCT count kept them. `mt-auto` in a
        // flex column resolves to whatever space is left (48.75px, 24.38px):
        // the vertical twin of the mx-auto case above, and it was inflating
        // the spacing vocabulary on exactly the pages with the most content.
        if (v && v > 0 && Math.abs(v - Math.round(v)) < 0.01) {
          tally(pads, String(v));
        }
      });
      if (cs.gap && cs.gap !== "normal") { var g = px(cs.gap); if (g) tally(gaps, String(g)); }
      var br = px(cs.borderTopLeftRadius);
      if (br !== null && br > 0) tally(radii, String(br));
      if (cs.boxShadow && cs.boxShadow !== "none") tally(shadows, cs.boxShadow.slice(0, 90));
      if (cs.transitionDuration && cs.transitionDuration !== "0s") tally(durations, cs.transitionDuration);
      var bw = px(cs.borderTopWidth); if (bw) tally(borders, String(bw));
    });

    var padKeys = Object.keys(pads).map(Number);
    // Exclusions, in order:
    //  - 1/2/3px: hairlines and insets, not scale steps.
    //  - 6/10/14/18/22/26: Tailwind's documented half-steps (1.5, 2.5, ...).
    //    A dense tool using them systematically has chosen a 2px base, which is
    //    a scale, not drift. Flagging them made every Tailwind app look broken.
    //  - values seen at most twice: `mx-auto`, flex distribution and other
    //    COMPUTED margins resolve to arbitrary pixel values (315.5, 83) that
    //    nobody authored. Real drift repeats.
    //  - non-integer values, however often they repeat. The repeat test above
    //    assumes computed margins are one-offs, and a grid defeats that: three
    //    equal columns emit the same 174.33px three times and it reads as
    //    authored drift. But a fractional pixel is definitionally not authored
    //    - every Tailwind step and every arbitrary value is a whole number, and
    //    the half-steps resolve to whole numbers at a 4px base. A page whose
    //    only "off-base" values are 91.33/99.33/174.33 has one grid, not a
    //    broken scale. Integer drift (13, 18, 37) still lands.
    var HALF_STEPS = { 6: 1, 10: 1, 14: 1, 18: 1, 22: 1, 26: 1 };
    var offBase = padKeys.filter(function (v) {
      if (v % 4 === 0) return false;
      if (v === 1 || v === 2 || v === 3) return false;
      if (HALF_STEPS[v]) return false;
      if (v !== Math.round(v)) return false;
      return (pads[v] || 0) > 2;
    });
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
    var spacingExempt = mk(EX * 2), inlineExempt = 0;
    var boxes = [];
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
      // A visually-hidden control (the sr-only skip link, 1x1 with a clip) is
      // not a 1x1 tap target -- it is invisible until focused, when it becomes
      // full size. Counting it produced a WCAG 2.5.8 "failure" on the one
      // element that exists to help keyboard users, on every page that does
      // the accessible thing.
      var clipped = (cs.clip && cs.clip !== "auto") ||
        (cs.clipPath && cs.clipPath !== "none" && w <= 2 && h <= 2);
      if (clipped && w <= 2 && h <= 2) return;
      if (w > 0 && h > 0) {
        boxes.push({
          el: el, rect: r, w: w, h: h, inline: !!inlineException,
          sel: selectorFor(el), text: (el.innerText || "").trim().slice(0, 24),
          undersized: (w < 24 || h < 24)
        });
      }
      if (inlineException && w > 0 && h > 0 && (w < 24 || h < 24)) inlineExempt++;
      if (cs.transitionDuration === "0s") noTransition++;
    });

    // WCAG 2.5.8's SPACING exception, computed rather than argued each round:
    // an undersized target conforms if a 24px-diameter circle centred on it
    // intersects neither another target's box nor another undersized target's
    // circle. Without this the probe reports every sub-24px control as a
    // failure, a reviewer re-measures them by hand at two viewports, and the
    // same twenty rows get re-litigated in the next round's ledger. Emitting
    // pass/fail here is the difference between a candidate and a chore.
    var R = 12;
    function centre(b) {
      return { x: b.rect.left + b.rect.width / 2, y: b.rect.top + b.rect.height / 2 };
    }
    function circleHitsRect(cx, cy, rad, rect) {
      var nx = Math.max(rect.left, Math.min(cx, rect.right));
      var ny = Math.max(rect.top, Math.min(cy, rect.bottom));
      var dx = cx - nx, dy = cy - ny;
      return (dx * dx + dy * dy) < rad * rad;
    }
    boxes.forEach(function (b) {
      if (!b.undersized) return;
      if (b.inline) return;                       // exempt by 2.5.8 Inline
      var c = centre(b), clash = null;
      for (var i = 0; i < boxes.length && !clash; i++) {
        var o = boxes[i];
        if (o === b) continue;
        // Nested targets (a button inside a link) are one visual target, not
        // two crowding each other. Counting them collides everything.
        if (b.el.contains(o.el) || o.el.contains(b.el)) continue;
        if (o.undersized && !o.inline) {
          var oc = centre(o), dx = c.x - oc.x, dy = c.y - oc.y;
          if (dx * dx + dy * dy < (2 * R) * (2 * R)) clash = o.sel;
        } else if (circleHitsRect(c.x, c.y, R, o.rect)) {
          clash = o.sel;
        }
      }
      if (clash) {
        tinyTargets.push({ sel: b.sel, w: b.w, h: b.h, text: b.text, crowdedBy: clash });
      } else {
        spacingExempt.push({ sel: b.sel, w: b.w, h: b.h, text: b.text });
      }
    });
    boxes.forEach(function (b) {
      if (b.undersized || b.inline) return;
      if (b.w < 44 || b.h < 44) tooSmall.push({ sel: b.sel, w: b.w, h: b.h });
    });

    // Focus ring: actually focus things and diff the computed style. This is
    // the only honest way to answer 2.4.7 - a grep cannot see a ring that
    // lives in a shared class, and a screenshot cannot see one at all.
    var FOCUSABLE = 'a[href],button,input,select,textarea,summary,[contenteditable="true"],' +
                    'audio[controls],video[controls],[tabindex]:not([tabindex="-1"])';
    var fels = Array.prototype.slice.call(document.querySelectorAll(FOCUSABLE), 0, 60);
    var active = document.activeElement;
    var priorScroll = { x: window.scrollX, y: window.scrollY };
    var noRing = mk(EX * 2), obscured = mk(EX * 2), tested = 0;
    var strongOutline = 0, outlineNotProven = 0;

    // SC 2.4.11 is behavioral: the existence and total height of sticky chrome
    // cannot tell whether the *focused control* is hidden by it. Move each
    // control into the nearest visible scroll position and hit-test nine points
    // inside the part of its border box that intersects the viewport. If none
    // of those points resolves to the control or one of its descendants, the
    // focused component is entirely covered by author content. Partial
    // obstruction is deliberately not called a failure here (AA only forbids
    // complete obstruction), which keeps sticky shadows and corner badges from
    // becoming false positives.
    function focusVisiblePoints(el) {
      var r = el.getBoundingClientRect();
      var l = Math.max(0, r.left), t = Math.max(0, r.top);
      var rr = Math.min(VW, r.right), bb = Math.min(VH, r.bottom);
      if (rr <= l || bb <= t) return [];
      var xs = [l + 1, (l + rr) / 2, rr - 1];
      var ys = [t + 1, (t + bb) / 2, bb - 1];
      var pts = [];
      xs.forEach(function (x) { ys.forEach(function (y) {
        if (x >= 0 && y >= 0 && x < VW && y < VH) pts.push([x, y]);
      }); });
      return pts;
    }
    function focusCompletelyObscured(el) {
      var pts = focusVisiblePoints(el);
      if (!pts.length) return { obscured: true, visiblePoints: 0, covering: "outside viewport" };
      var cover = "unknown";
      for (var p = 0; p < pts.length; p++) {
        var stack = document.elementsFromPoint(pts[p][0], pts[p][1]);
        // elementsFromPoint returns the covered control deeper in the stack;
        // finding it *anywhere* would therefore prove only that it exists, not
        // that a pixel is visible. The top hit must be the control or its child.
        if (stack[0] === el || (stack[0] && el.contains(stack[0]))) {
          return { obscured: false, visiblePoints: pts.length };
        }
        if (p === Math.floor(pts.length / 2) && stack[0]) cover = selectorFor(stack[0]);
      }
      return { obscured: true, visiblePoints: pts.length, covering: cover };
    }
    fels.forEach(function (el) {
      try {
        var cs0 = getComputedStyle(el);
        if (!visible(el, cs0) || el.disabled || el.getAttribute("aria-disabled") === "true") return;
        var before = [cs0.outlineWidth, cs0.outlineColor, cs0.boxShadow, cs0.borderColor, cs0.backgroundColor, cs0.outlineStyle].join("|");
        el.focus({ preventScroll: false });
        if (document.activeElement !== el) return;
        try { el.scrollIntoView({ block: "nearest", inline: "nearest" }); } catch (e) { /* old engine */ }
        var cs1 = getComputedStyle(el);
        var after = [cs1.outlineWidth, cs1.outlineColor, cs1.boxShadow, cs1.borderColor, cs1.backgroundColor, cs1.outlineStyle].join("|");
        tested++;
        var ow = parseFloat(cs1.outlineWidth) || 0;
        var hasOutline = ow > 0 && cs1.outlineStyle !== "none";
        if (before === after && !hasOutline) {
          noRing.push({ sel: selectorFor(el), text: (el.innerText || el.value || "").toString().trim().slice(0, 28) });
        }
        var occ = focusCompletelyObscured(el);
        if (occ.obscured) {
          obscured.push({ sel: selectorFor(el), text: (el.innerText || el.value || "").toString().trim().slice(0, 28),
                          covering: occ.covering, visiblePoints: occ.visiblePoints });
        }

        // A sufficient (not exhaustive) WCAG 2.4.13 AAA signal. A solid >=2px
        // outline with >=3:1 contrast against the painted surround proves a
        // strong author indicator. Anything else is "not proven", never a
        // failure: borders, inset rings and non-rectangular indicators need
        // pixel comparison or a human review, and guessing would punish valid
        // designs. This metric exists to strengthen perfection evidence, not
        // to turn an AAA criterion into an AA score cap.
        if (hasOutline && ow >= 2) {
          var oc = rgba(cs1.outlineColor);
          var bg = backdrop(el, el.getBoundingClientRect());
          if (oc && bg && !bg.imageBehind && ratio(over(oc, bg.color), bg.color) >= 3) strongOutline++;
          else outlineNotProven++;
        } else if (before !== after) outlineNotProven++;
      } catch (e) { /* element refused focus */ }
    });
    try { if (active && active.focus) active.focus({ preventScroll: true }); } catch (e) {}
    try { window.scrollTo(priorScroll.x, priorScroll.y); } catch (e) {}

    return {
      clickable: els.length,
      missingPointerCursor: missingPointer.out(),
      // Sub-24px AND crowded: an actual 2.5.8 failure. The exempt lists are
      // reported separately so a reviewer can see the exceptions were applied
      // rather than assumed, and so nobody re-measures them by hand.
      belowWcagTarget24: tinyTargets.out(),
      target24SpacingExempt: spacingExempt.out(),
      target24InlineExemptCount: inlineExempt,
      belowFittsTarget44: tooSmall.out(),
      clickableWithoutTransition: noTransition,
      focusRing: { tested: tested, invisible: noRing.n, list: noRing.list,
                   truncated: noRing.out().truncated,
                   completelyObscured: obscured.n, obscuredList: obscured.list,
                   obscuredTruncated: obscured.out().truncated,
                   strongOutlineProven: strongOutline,
                   appearanceNotProven: outlineNotProven,
                   appearanceCriterion: "WCAG 2.4.13 AAA; sufficient-outline test only" }
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
    var rulesFor = {}, universal = {};
    PSEUDO.forEach(function (p) { rulesFor[p] = []; universal[p] = false; });
    var inaccessibleSheets = 0, reducedMotionRules = 0, sheetsRead = 0;
    // Does the CSS reference env(safe-area-inset-*) anywhere? The runtime
    // insets are always 0 in a desktop browser - there is no notch to measure -
    // so the only honest signal available here is whether the page ever
    // ACCOUNTS for one. Checked against viewport-fit=cover in the report.
    var safeAreaRules = 0;
    // Selectors whose :hover rule REVEALS content (rather than just recolouring
    // it). On a coarse pointer that hover cannot happen, so whatever they show
    // is unreachable -- the single most common way a desktop-designed UI loses
    // functionality on a phone. Collected here, resolved against the live DOM
    // below.
    var hoverRevealSel = [];
    // The escape hatches: the same content revealed by focus-within / focus /
    // an :checked toggle is reachable without a pointer, so it must NOT be
    // reported. Collected the same way, and subtracted below.
    var altRevealSel = [];
    // Hover rules that PAINT: selector plus the background-colour they declare.
    // Rule coverage alone ("does a :hover rule match this element") says a
    // hover exists, not that anyone can see it -- and the failure mode is
    // common enough to deserve its own measurement. A row whose hover fill is
    // the colour its own section already is has a hover rule, full coverage,
    // and no hover state.
    var hoverPaint = [];
    // Same shape, one property over: a :hover rule that re-declares the border
    // colour the element already has. `border-line hover:border-line` is a
    // real pattern in real code and it is a state that does not exist.
    var hoverBorder = [];

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
        if (r.style && r.style.cssText && r.style.cssText.indexOf("safe-area-inset") !== -1) safeAreaRules++;
        if (r.style && /:hover|:focus-within|:focus|:checked|\[aria-expanded/.test(sel)) {
          // Does this rule move something TOWARD visible?
          var st = r.style;
          var reveals =
            (st.display && st.display !== "none") ||
            (st.visibility === "visible") ||
            (st.opacity !== "" && parseFloat(st.opacity) > 0.05) ||
            (st.maxHeight && st.maxHeight !== "0px" && st.maxHeight !== "0");
          if (reveals) {
            sel.split(",").forEach(function (part) {
              var strip = function (p) {
                return part.replace(new RegExp(p + "(\\([^)]*\\))?", "g"), "")
                           .replace(/\[aria-expanded[^\]]*\]/g, "").trim();
              };
              if (part.indexOf(":hover") !== -1) {
                var base = strip(":hover");
                if (base && hoverRevealSel.length < 200) hoverRevealSel.push(base);
              } else if (/:focus-within|:focus|:checked|\[aria-expanded/.test(part)) {
                var alt = strip(":focus-within").replace(/:focus(\([^)]*\))?/g, "")
                                               .replace(/:checked/g, "").trim();
                if (alt && altRevealSel.length < 200) altRevealSel.push(alt);
              }
            });
          }
        }
        if (r.style && sel.indexOf(":hover") !== -1) {
          var hoverBc = r.style.getPropertyValue("border-color") ||
                        r.style.getPropertyValue("border-top-color");
          if (hoverBc) {
            sel.split(",").forEach(function (part) {
              if (part.indexOf(":hover") === -1) return;
              var b = part.replace(/:hover(\([^)]*\))?/g, "").trim();
              if (b && hoverBorder.length < 300) hoverBorder.push({ base: b, col: hoverBc });
            });
          }
          var hoverBg = r.style.getPropertyValue("background-color");
          if (hoverBg) {
            sel.split(",").forEach(function (part) {
              if (part.indexOf(":hover") === -1) return;
              var base = part.replace(/:hover(\([^)]*\))?/g, "").trim();
              if (base && hoverPaint.length < 300) hoverPaint.push({ base: base, bg: hoverBg });
            });
          }
        }
        PSEUDO.forEach(function (p) {
          if (sel.indexOf(":" + p) === -1) return;
          // Strip the pseudo so the remainder can be matched against elements.
          sel.split(",").forEach(function (part) {
            if (part.indexOf(":" + p) === -1) return;
            var base = part.replace(new RegExp(":" + p + "(\\([^)]*\\))?", "g"), "").trim();
            // A BARE pseudo (`:focus-visible { outline: ... }`) strips to the
            // empty string, and `if (base)` dropped it - so the single most
            // correct way to ship a focus ring, one universal rule instead of a
            // utility on every component, was counted as covering NOTHING.
            // Sheevook ships exactly that and measured 5% coverage while the
            // empirical check focused 38 elements and found 0 without a ring.
            // An empty base means the rule matches everything; say so.
            if (!base) base = "*";
            // The 400-base cap must never drop a UNIVERSAL rule. On a Tailwind
            // build the utility selectors (`.focus-visible\:ring-2:focus-visible`
            // and friends) are emitted first and fill the list, and the app's own
            // `:focus-visible { outline: ... }` sits near the end of the sheet -
            // so the one rule that covers every element was the one thrown away.
            // A universal base also makes the rest redundant, so keep it and stop.
            if (base === "*") { rulesFor[p] = ["*"]; universal[p] = true; return; }
            if (universal[p]) return;
            if (rulesFor[p].length < 400) rulesFor[p].push(base);
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

    // WCAG 1.4.1: links embedded in prose cannot rely on colour alone unless
    // their colour differs from the surrounding text by at least 3:1 AND an
    // additional visual cue appears on both hover and keyboard focus. Keep
    // this deliberately narrower than `a[href]`: navigation, cards and button-
    // shaped links are not "links in blocks of text", and treating them as
    // such turns a useful check into a false-positive factory.
    var colorOnlyLinks = mk(EX);

    function matchesAny(el, bases) {
      return (bases || []).some(function (base) {
        try { return el.matches(base); } catch (e) { return false; }
      });
    }

    Array.prototype.slice.call(
      document.querySelectorAll("p a[href],li a[href],dd a[href],td a[href],figcaption a[href]"),
      0, 300
    ).forEach(function (el) {
      if (!visible(el)) return;
      var parent = el.parentElement;
      if (!parent) return;
      // The link must actually sit among prose, not merely be the only child
      // of a list item or table cell.
      var surrounding = Array.prototype.slice.call(parent.childNodes).filter(function (n) {
        return n !== el;
      }).map(function (n) { return n.textContent || ""; }).join(" ").replace(/\s+/g, " ").trim();
      if (surrounding.length < 20) return;

      var cs = getComputedStyle(el), ps = getComputedStyle(parent);
      var decoration = (cs.textDecorationLine || "").toLowerCase();
      var hasPersistentCue = decoration.indexOf("underline") !== -1 ||
        decoration.indexOf("overline") !== -1 ||
        parseFloat(cs.borderBottomWidth || "0") >= 1 ||
        (rgba(cs.backgroundColor) && rgba(cs.backgroundColor).a > 0.05) ||
        Math.abs((parseInt(cs.fontWeight, 10) || 400) - (parseInt(ps.fontWeight, 10) || 400)) >= 200 ||
        cs.fontStyle !== ps.fontStyle;
      if (hasPersistentCue) return;

      var link = rgba(cs.color), text = rgba(ps.color);
      if (!link || !text) return;
      var colourRatio = ratio(link, text);
      var hoverCue = matchesAny(el, rulesFor.hover);
      var focusCue = matchesAny(el, rulesFor["focus-visible"].concat(rulesFor.focus));
      if (colourRatio < 3 || !hoverCue || !focusCue) {
        colorOnlyLinks.push({
          sel: selectorFor(el), text: (el.innerText || "").trim().slice(0, 40),
          linkToTextRatio: colourRatio, hoverCue: hoverCue, focusCue: focusCue
        });
      }
    });

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

    // --- is the hover state actually a state? ------------------------------
    //
    // Two defects, both invisible to a rule-coverage count and to any
    // screenshot taken without a pointer over the element:
    //
    // 1. The fill does not change the paint. `hover:bg-surface-sunken` on a
    //    section whose background IS surface-sunken is the archetype -- the
    //    rule matches, coverage reads 100%, and nothing happens on hover.
    //    Measured as the WCAG ratio between the hovered fill and the rest
    //    fill; below 1.02 the two are the same colour to the eye.
    // 2. The fill has no horizontal padding to sit in. A wide row that paints
    //    a hover band with `padding-left: 0` stops the tint dead at the first
    //    glyph, so the band reads as a rendering artefact rather than a
    //    designed row. Only checked on genuinely wide targets, because an
    //    inline chip is not a row.
    //
    // The declared colour is resolved by handing it back to the browser inside
    // the element's own parent, so custom properties, `color-mix()` and any
    // colour space resolve the way they will when painted.
    function resolveOn(el, decl) {
      var probeEl = document.createElement("span");
      probeEl.style.cssText = "position:absolute;left:-9999px;top:0;width:0;height:0";
      probeEl.style.backgroundColor = decl;
      if (!probeEl.style.backgroundColor) return null;     // browser rejected it
      var mount = el.parentElement || document.body;
      mount.appendChild(probeEl);
      var c = rgba(getComputedStyle(probeEl).backgroundColor);
      mount.removeChild(probeEl);
      return c;
    }

    // Luminance alone cannot answer this. Two tints can sit at the same
    // lightness and differ in hue -- a warm limestone and a cool wash, say --
    // which IS a change, but a weak one: it vanishes in greyscale, for anyone
    // with a colour vision deficiency in that axis, and on a cheap panel.
    // So the two cases are separated rather than merged: same paint (nothing
    // happens) and hue-only (something happens, to some people).
    function chanDist(a, b) {
      return Math.max(Math.abs(a.r - b.r), Math.abs(a.g - b.g), Math.abs(a.b - b.b));
    }

    // Where the INK is, not where the padding says it should be.
    //
    // The first version of the fill-padding check read `padding-left` and
    // flagged anything under 8px, which reported every full-width centred
    // button on the page: `w-full` + `justify-center` has no inline padding
    // and does not need any, because the label sits nowhere near the edge.
    // The defect is a fill whose EDGE LANDS ON THE GLYPH, so measure that:
    // union the rects of the element's text nodes and its icons, and compare
    // with the fill box. A padding value is a proxy; this is the thing.
    function inkBox(el) {
      var l = Infinity, r = -Infinity, t = Infinity, b = -Infinity, found = false;
      var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, null);
      var n = walker.nextNode(), guard = 0, rect;
      while (n && guard++ < 400) {
        if (n.nodeType === 3) {
          if (n.nodeValue && n.nodeValue.trim()) {
            var rng = document.createRange();
            rng.selectNodeContents(n);
            rect = rng.getBoundingClientRect();
          } else { rect = null; }
        } else if (/^(IMG|SVG|CANVAS|VIDEO)$/i.test(n.tagName)) {
          rect = n.getBoundingClientRect();
        } else { rect = null; }
        if (rect && rect.width > 0) {
          found = true;
          if (rect.left < l) l = rect.left;
          if (rect.right > r) r = rect.right;
          if (rect.top < t) t = rect.top;
          if (rect.bottom > b) b = rect.bottom;
        }
        n = walker.nextNode();
      }
      return found ? { left: l, right: r, top: t, bottom: b } : null;
    }

    var inertHover = mk(EX), hueOnlyHover = mk(EX), unpaddedFill = mk(EX);
    var inertBorder = mk(EX), fillOverRule = mk(EX);
    var hoverFillsChecked = 0, unmeasurableHover = 0;
    els.forEach(function (el) {
      var decl = null;
      hoverPaint.forEach(function (h) {
        try { if (el.matches(h.base)) decl = h.bg; } catch (e) { /* bad selector */ }
      });
      if (!decl) return;
      var fill = resolveOn(el, decl);
      if (!fill || fill.a === 0) return;
      hoverFillsChecked++;
      var cs = getComputedStyle(el);
      var own = rgba(cs.backgroundColor);
      // Pass the element's own rect: without it `backdrop` cannot hit-test, so
      // a control inside a fixed transparent header gets measured against the
      // page background and its hover tint reads as "no change" when it is a
      // clear step against the dark surface it actually sits on.
      var bd = backdrop(el.parentElement || el, el.getBoundingClientRect());
      // Same doctrine as the contrast pass: a colour measured against a
      // gradient or a photograph is not a fact. If the element does not paint
      // its own opaque fill AND there is an image behind it, the "before"
      // colour is unknown, so this cannot be graded. Counted, not guessed --
      // a translucent chip over a gradient hero is exactly the shape that
      // would otherwise be reported as a dead hover on every such page.
      if (bd.imageBehind && !(own && own.a >= 1)) { unmeasurableHover++; return; }
      var behind = bd.color;
      var rest = (own && own.a > 0) ? over(own, behind) : behind;
      var hovered = over(fill, rest);
      var delta = ratio(hovered, rest);
      var dist = chanDist(hovered, rest);
      var rect = el.getBoundingClientRect();
      var text = (el.innerText || "").trim().replace(/\s+/g, " ").slice(0, 32);
      // The fill and the row separator painted on the SAME box. The
      // background paints under the border, so on hover the hairline
      // disappears into the tint and the band's edge lands exactly where the
      // previous row ended -- which reads as the highlight crowding the row
      // above it rather than sitting inside its own. The fix is to put the
      // rule on the row and the tint on a child with a margin, so they share
      // a width and are separated by air.
      //
      // Two exclusions, both of which cost a round of false positives before
      // they were added: a TABLE, where a fill covering the row rule is the
      // convention, and a BOX -- a card with a border on all four sides that
      // tints on hover is correct and extremely common. The defect needs a
      // SEPARATOR: a border on one horizontal edge with no vertical sides.
      var bw = px(cs.borderTopWidth) || 0, bwb = px(cs.borderBottomWidth) || 0;
      var bwl = px(cs.borderLeftWidth) || 0, bwr = px(cs.borderRightWidth) || 0;
      var bcol = rgba(bw >= 1 ? cs.borderTopColor : cs.borderBottomColor);
      if ((bw >= 1 || bwb >= 1) && bwl < 1 && bwr < 1 && bcol && bcol.a > 0.05 &&
          rect.width >= 240 && !el.closest("table")) {
        fillOverRule.push({ sel: selectorFor(el), text: text,
                            borderTopWidth: bw, borderBottomWidth: bwb });
      }
      if (delta < 1.02 && dist < 6) {
        inertHover.push({ sel: selectorFor(el), text: text, declared: decl,
                          delta: delta, channelDistance: dist });
      } else if (delta < 1.02) {
        hueOnlyHover.push({ sel: selectorFor(el), text: text, declared: decl,
                            delta: delta, channelDistance: dist });
      } else if (rect.width >= 240) {
        var ink = inkBox(el);
        if (ink) {
          var gapL = Math.round(ink.left - rect.left);
          var gapR = Math.round(rect.right - ink.right);
          var gapT = Math.round(ink.top - rect.top);
          var gapB = Math.round(rect.bottom - ink.bottom);
          // Horizontal wants more room than vertical: 8px inline, 6px block.
          // A row can be tight vertically and still read; a fill whose edge
          // lands on the glyph never does.
          if (gapL < 8 || gapR < 8 || gapT < 6 || gapB < 6) {
            unpaddedFill.push({ sel: selectorFor(el), text: text,
                                width: Math.round(rect.width),
                                inkGapLeft: gapL, inkGapRight: gapR,
                                inkGapTop: gapT, inkGapBottom: gapB });
          }
        }
      }
    });

    els.forEach(function (el) {
      var decl = null;
      hoverBorder.forEach(function (h) {
        try { if (el.matches(h.base)) decl = h.col; } catch (e) { /* bad selector */ }
      });
      if (!decl) return;
      var cs = getComputedStyle(el);
      if (px(cs.borderTopWidth) < 1 && px(cs.borderLeftWidth) < 1) return;   // no border to change
      var want = resolveOn(el, decl), have = rgba(cs.borderTopColor);
      if (!want || !have || want.a === 0 || have.a === 0) return;
      if (chanDist(want, have) < 3) {
        inertBorder.push({ sel: selectorFor(el),
                           text: (el.innerText || "").trim().replace(/\s+/g, " ").slice(0, 32),
                           declared: decl });
      }
    });

    var formControls = Array.prototype.slice.call(
      document.querySelectorAll("input,select,textarea,button"), 0, 300);
    var disabledPresent = document.querySelectorAll("[disabled],[aria-disabled=true]").length;

    // Resolve the hover-reveal selectors against the live DOM. Only elements
    // that are CURRENTLY hidden count -- a hover rule on already-visible
    // content is a hover effect, not a hover dependency. Elements that also
    // have a focus-within/focus reveal, or sit inside a details/summary or an
    // aria-expanded control, are reachable another way and are excluded.
    var hoverOnly = mk(EX);
    var hoverRevealChecked = 0;
    hoverRevealSel.forEach(function (base) {
      var nodes;
      try { nodes = document.querySelectorAll(base); } catch (e) { return; }
      Array.prototype.slice.call(nodes, 0, 20).forEach(function (el) {
        hoverRevealChecked++;
        var cs = getComputedStyle(el);
        var hidden = cs.display === "none" || cs.visibility === "hidden" ||
                     parseFloat(cs.opacity) < 0.05;
        if (!hidden) return;
        // Reachable without hover? A focus-within / focus / :checked reveal on
        // the SAME element is the documented accessible pattern - excluding it
        // is what keeps this check from punishing correct code.
        var altPath = altRevealSel.concat(rulesFor["focus-visible"], rulesFor.focus)
          .some(function (b) { try { return el.matches(b); } catch (e) { return false; } });
        if (altPath) return;
        if (el.closest("details")) return;
        if (el.closest('[aria-expanded],[aria-haspopup],[popover]')) return;
        if (hoverOnly.n < EX) {
          hoverOnly.push({
            sel: selectorFor(el),
            text: (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 40),
            interactive: !!el.querySelector('a[href],button,input,[role="button"]') ||
                         /^(A|BUTTON)$/.test(el.tagName)
          });
        } else { hoverOnly.n++; }
      });
    });

    return {
      stylesheetsRead: sheetsRead,
      // A page whose CSS is all cross-origin cannot be measured this way; say
      // so rather than reporting zero coverage as a design failure.
      inaccessibleStylesheets: inaccessibleSheets,
      // Content that only a hover can reveal. On a coarse pointer it is
      // unreachable. Read together with meta.device.hoverNone: on a run where
      // hover is still available this is a warning, on a touch run it is a
      // functional loss.
      safeAreaInsetRules: safeAreaRules,
      hoverRevealSelectors: hoverRevealSel.length,
      hoverRevealChecked: hoverRevealChecked,
      hoverOnlyContent: hoverOnly.list,
      hoverOnlyContentCount: hoverOnly.n,
      interactiveElements: els.length,
      withHoverRule: counts.hover,
      withFocusVisibleRule: counts["focus-visible"],
      withFocusRule: counts.focus,
      withActiveRule: counts.active,
      withDisabledRule: counts.disabled,
      hoverCoverage: els.length ? Math.round((counts.hover / els.length) * 100) : null,
      // Coverage says a hover rule exists. These say it does something.
      hoverFillsChecked: hoverFillsChecked,
      // Hover fills sitting over a gradient or photograph: the rest colour is
      // not knowable, so they are excluded rather than graded.
      hoverFillsUnmeasurable: unmeasurableHover,
      inertHoverFills: inertHover.n,
      inertHoverFillExamples: inertHover.list,
      // A hover that changes hue but not lightness. Real, but weak: greyscale,
      // a colour vision deficiency in that axis, or a poor panel all erase it.
      // Hover fills that paint over the separator they carry themselves.
      hoverFillsCoveringOwnRule: fillOverRule.n,
      hoverFillsCoveringOwnRuleExamples: fillOverRule.list,
      inertHoverBorders: inertBorder.n,
      inertHoverBorderExamples: inertBorder.list,
      hueOnlyHoverFills: hueOnlyHover.n,
      hueOnlyHoverFillExamples: hueOnlyHover.list,
      hoverFillsWithoutPadding: unpaddedFill.n,
      hoverFillsWithoutPaddingExamples: unpaddedFill.list,
      focusVisibleCoverage: els.length ? Math.round((counts["focus-visible"] / els.length) * 100) : null,
      colorOnlyLinks: colorOnlyLinks.out(),
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
        // innerText || textContent, for the same reason spelled out below: a
        // labelling element inside a closed <details> is not RENDERED, so
        // innerText is "" while the accessible name is perfectly real.
        n = ids.map(function (i) {
          var e = document.getElementById(i);
          return e ? (e.innerText || e.textContent || "") : "";
        }).join(" ").trim();
      }
      if (!n && el.id) {
        var lab = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
        if (lab) n = (lab.innerText || lab.textContent || "").trim();
      }
      if (!n && el.closest && el.closest("label")) {
        var wrapLab = el.closest("label");
        n = (wrapLab.innerText || wrapLab.textContent || "").trim();
      }
      if (!n) n = (el.innerText || "").trim();
      // innerText is "" for anything not currently rendered, so a perfectly
      // labelled item inside a closed dropdown reads as nameless. textContent
      // sees it. Without this, a well-built site reports dozens of phantom
      // 4.1.2 failures -- and 4.1.2 is a CRITICAL that caps the whole score.
      if (!n) n = (el.textContent || "").trim();
      if (!n) n = el.getAttribute("title") || "";
      if (!n && el.tagName === "IMG") n = el.getAttribute("alt") || "";
      if (!n && el.tagName === "AREA") n = el.getAttribute("alt") || "";
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

    // Visible-label text for SC 2.5.3. innerText alone is not sufficient: it
    // includes common sr-only recipes in some engines, which would make the
    // hidden accessible-name supplement look like part of the visible label.
    function visibleLabelText(root) {
      var text = [];
      function walk(node) {
        if (node.nodeType === 3) { text.push(node.nodeValue || ""); return; }
        if (node.nodeType !== 1 || node.getAttribute("aria-hidden") === "true") return;
        var cs = getComputedStyle(node);
        if (!visible(node, cs)) return;
        for (var i = 0; i < node.childNodes.length; i++) walk(node.childNodes[i]);
      }
      walk(root);
      return text.join(" ").replace(/\s+/g, " ").trim();
    }
    function speechNorm(value) {
      value = (value || "").toString();
      try { value = value.normalize("NFKC"); } catch (e) { /* old engine */ }
      return value.toLocaleLowerCase().replace(/[\p{P}\p{S}\s]+/gu, "");
    }
    function visibleFieldLabel(el) {
      var lab = null;
      if (el.id) lab = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (!lab && el.closest) lab = el.closest("label");
      return lab ? visibleLabelText(lab) : "";
    }

    function validAutocomplete(raw) {
      var tokens = (raw || "").trim().toLowerCase().split(/\s+/).filter(Boolean);
      if (!tokens.length) return false;
      if (tokens.length === 1 && /^(on|off)$/.test(tokens[0])) return true;
      var i = 0;
      if (/^section-[a-z0-9_-]+$/.test(tokens[i] || "")) i++;
      if (/^(shipping|billing)$/.test(tokens[i] || "")) i++;
      var contactHint = /^(home|work|mobile|fax|pager)$/.test(tokens[i] || "");
      if (contactHint) i++;
      var contact = /^(tel|tel-country-code|tel-national|tel-area-code|tel-local|tel-local-prefix|tel-local-suffix|tel-extension|email|impp)$/;
      var field = /^(name|honorific-prefix|given-name|additional-name|family-name|honorific-suffix|nickname|username|new-password|current-password|one-time-code|organization-title|organization|street-address|address-line1|address-line2|address-line3|address-level4|address-level3|address-level2|address-level1|country|country-name|postal-code|cc-name|cc-given-name|cc-additional-name|cc-family-name|cc-number|cc-exp|cc-exp-month|cc-exp-year|cc-csc|cc-type|transaction-currency|transaction-amount|language|bday|bday-day|bday-month|bday-year|sex|url|photo|tel|tel-country-code|tel-national|tel-area-code|tel-local|tel-local-prefix|tel-local-suffix|tel-extension|email|impp)$/;
      if (!field.test(tokens[i] || "")) return false;
      if (contactHint && !contact.test(tokens[i])) return false;
      i++;
      if (tokens[i] === "webauthn") i++;
      return i === tokens.length;
    }

    function validLangSyntax(value) {
      if (!(value || "").trim()) return false;
      try {
        if (typeof Intl.Locale === "function") { new Intl.Locale(value); return true; }
        Intl.getCanonicalLocales(value); return true;
      } catch (e) { return false; }
    }
    function knownLanguagePrimary(value) {
      try {
        var raw = (value || "").trim();
        // ACT/WCAG language rules care about a KNOWN PRIMARY subtag, not full
        // RFC 5646 grammar. Browsers/AT accept `en-US-GB` by its known `en`
        // primary even though the region sequence is syntactically invalid.
        if (!/^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$/.test(raw)) return false;
        var primary = raw.split("-")[0].toLowerCase();
        var locale = new Intl.Locale(primary);
        // Intl canonicalizes obsolete/bibliographic aliases (`eng` -> `en`).
        // ACT expects the actual registered primary subtag, not an alias.
        if (locale.language.toLowerCase() !== primary) return false;
        if (typeof Intl.DisplayNames !== "function") return null;
        var display = new Intl.DisplayNames(["en"], { type: "language", fallback: "code" }).of(locale.language);
        return !!display && display.toLowerCase() !== locale.language.toLowerCase();
      } catch (e) { return false; }
    }
    function inheritsLanguageContent(root) {
      var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        var text = walker.currentNode, parent = text.parentElement;
        if (!parent || !text.nodeValue || !text.nodeValue.trim()) continue;
        var owner = parent.closest("[lang]");
        if (owner && owner !== root && (owner.getAttribute("lang") || "").trim()) continue;
        if (visible(parent, getComputedStyle(parent))) return true;
      }
      var named = root.querySelectorAll("img[alt],button,input,select,textarea,[aria-label],[aria-labelledby]");
      for (var i = 0; i < Math.min(named.length, 200); i++) {
        var el = named[i], owner = el.closest("[lang]");
        if (owner && owner !== root && (owner.getAttribute("lang") || "").trim()) continue;
        if (accName(el) && (visible(el, getComputedStyle(el)) || el.getAttribute("aria-hidden") !== "true")) return true;
      }
      return false;
    }

    var imgsNoAlt = mk(EX * 2), fieldsNoLabel = mk(EX * 2), btnsNoName = mk(EX * 2),
        placeholderOnly = mk(EX), brokenRefs = mk(EX * 2), requiredBrokenRefs = mk(EX * 2),
        deferredControlRefs = mk(EX * 2), roleStateIssues = mk(EX * 2),
        labelName = mk(EX * 2), invalidAutocomplete = mk(EX * 2),
        purposeReview = mk(EX * 2), invalidLang = mk(EX * 2), unknownLang = mk(EX * 2);
    Array.prototype.slice.call(document.images, 0, 300).forEach(function (el) {
      if (!el.hasAttribute("alt")) {
        imgsNoAlt.push({ sel: selectorFor(el), src: (el.currentSrc || el.src || "").slice(-60) });
      }
    });
    Array.prototype.slice.call(document.querySelectorAll("input,select,textarea"), 0, 300).forEach(function (el) {
      if (el.type === "hidden") return;
      var n = accName(el);
      if (!n) {
        fieldsNoLabel.push({ sel: selectorFor(el), locator: uniqueSelectorFor(el), type: el.type || el.tagName });
        if (el.placeholder) placeholderOnly.push({ sel: selectorFor(el), placeholder: el.placeholder });
      }
      var fieldLabel = visibleFieldLabel(el);
      var normFieldLabel = speechNorm(fieldLabel), normFieldName = speechNorm(n);
      if (n && normFieldLabel.length >= 2 && /[\p{L}\p{N}]/u.test(fieldLabel) &&
          normFieldName.indexOf(normFieldLabel) === -1) {
        labelName.push({ sel: selectorFor(el), locator: uniqueSelectorFor(el), visibleLabel: fieldLabel.slice(0, 60),
                         domAccessibleName: n.slice(0, 80),
                         accessibleNameSource: "dom-fallback", computed: false });
      }
      var acRole = (el.getAttribute("role") || "").toLowerCase(), acHidden = false;
      for (var acNode = el; acNode && acNode.nodeType === 1; acNode = acNode.parentElement) {
        var acStyle = getComputedStyle(acNode);
        if (acStyle.display === "none" || acStyle.visibility !== "visible" ||
            acNode.getAttribute("aria-hidden") === "true") { acHidden = true; break; }
      }
      var acApplicable = !el.disabled && el.getAttribute("aria-disabled") !== "true" &&
                         acRole !== "none" && acRole !== "presentation" && !acHidden;
      if (acApplicable && el.hasAttribute("autocomplete") && el.getAttribute("autocomplete").trim() &&
          !validAutocomplete(el.getAttribute("autocomplete"))) {
        invalidAutocomplete.push({ sel: selectorFor(el), value: el.getAttribute("autocomplete") });
      } else if (!el.hasAttribute("autocomplete")) {
        // Missing purpose metadata is contextual: an email field might collect
        // a colleague's address, not the current user's. Surface only the
        // fields whose native type/name makes a user-purpose plausible and
        // require confirmation; never call this a failure from the probe.
        var hint = ((el.type || "") + " " + (el.name || "") + " " + (el.id || "") + " " + n).toLowerCase();
        if (/\b(email|tel|phone|password|username|postal|zip|address|given.?name|family.?name|first.?name|last.?name|card|cc-)\b/.test(hint)) {
          purposeReview.push({ sel: selectorFor(el), type: el.type || el.tagName, label: n.slice(0, 40) });
        }
      }
    });
    Array.prototype.slice.call(document.querySelectorAll(
      'button,a[href],area[href],[role="button"],[role="link"],[role="checkbox"],[role="radio"],[role="switch"],[role="tab"],[role="menuitem"],[role="option"]'
    ), 0, 400).forEach(function (el) {
      var name = accName(el);
      if (!name) btnsNoName.push({ sel: selectorFor(el), locator: uniqueSelectorFor(el), html: el.innerHTML.slice(0, 40) });
      var label = visibleLabelText(el);
      var normLabel = speechNorm(label), normName = speechNorm(name);
      // Single glyphs/letters and labels with no human-language characters are
      // explicitly excluded by WCAG's examples and are too ambiguous to grade.
      if (name && normLabel.length >= 2 && /[\p{L}\p{N}]/u.test(label) &&
          normName.indexOf(normLabel) === -1) {
        labelName.push({ sel: selectorFor(el), locator: uniqueSelectorFor(el), visibleLabel: label.slice(0, 60),
                         domAccessibleName: name.slice(0, 80),
                         accessibleNameSource: "dom-fallback", computed: false });
      }
    });

    Array.prototype.slice.call(document.querySelectorAll("[lang]"), 0, 300).forEach(function (el) {
      var value = el.getAttribute("lang") || "";
      if (value === "" || (el === document.documentElement && !value.trim())) return;
      if (el !== document.documentElement && !inheritsLanguageContent(el)) return;
      var known = knownLanguagePrimary(value);
      if (known === false) unknownLang.push({ sel: selectorFor(el), value: value });
      if (!validLangSyntax(value)) invalidLang.push({ sel: selectorFor(el), value: value });
    });

    // Broken IDREF wiring is invisible in a screenshot and common in copied
    // components: the trigger still paints, but its label, description, error
    // or controlled panel no longer exists. Only validate attributes whose
    // values are ID references; free-text ARIA attributes do not belong here.
    var IDREFS = ["aria-labelledby", "aria-describedby", "aria-controls",
                  "aria-owns", "aria-details", "aria-errormessage", "headers"];
    Array.prototype.slice.call(document.querySelectorAll(IDREFS.map(function (a) {
      return "[" + a + "]";
    }).join(",")), 0, 500).forEach(function (el) {
      IDREFS.forEach(function (attr) {
        if (!el.hasAttribute(attr)) return;
        var missing = (el.getAttribute(attr) || "").trim().split(/\s+/).filter(function (id) {
          return id && !document.getElementById(id);
        });
        if (missing.length) {
          var item = { sel: selectorFor(el), attr: attr, missing: missing.slice(0, 4),
                       expanded: el.getAttribute("aria-expanded"),
                       selected: el.getAttribute("aria-selected") };
          brokenRefs.push(item);
          // Collapsed/unselected disclosure content is often lazily mounted.
          // A missing aria-controls target at rest is worth exercising, not a
          // conformance verdict. Once expanded/selected, or for naming and
          // description IDREFs, the relationship must exist now.
          if (attr === "aria-controls" &&
              el.getAttribute("aria-expanded") !== "true" &&
              el.getAttribute("aria-selected") !== "true") {
            deferredControlRefs.push(item);
          } else {
            requiredBrokenRefs.push(item);
          }
        }
      });
    });

    // Native controls bring their state semantics with them. Once an author
    // chooses an ARIA widget role, these required states are the component's
    // public contract. This is intentionally limited to unambiguous required
    // properties so an informative APG preference never becomes a WCAG cap.
    Array.prototype.slice.call(document.querySelectorAll("[role]"), 0, 500).forEach(function (el) {
      var role = (el.getAttribute("role") || "").trim().split(/\s+/)[0];
      var missing = [];
      if (/^(tab)$/.test(role) && !el.hasAttribute("aria-selected")) missing.push("aria-selected");
      if (/^(checkbox|radio|switch)$/.test(role) && !el.hasAttribute("aria-checked")) missing.push("aria-checked");
      if (role === "combobox" && !el.hasAttribute("aria-expanded")) missing.push("aria-expanded");
      if (role === "slider") {
        ["aria-valuenow", "aria-valuemin", "aria-valuemax"].forEach(function (a) {
          if (!el.hasAttribute(a)) missing.push(a);
        });
      }
      if (/^(dialog|alertdialog)$/.test(role) && !accName(el)) missing.push("accessible-name");
      if (missing.length) roleStateIssues.push({ sel: selectorFor(el), role: role, missing: missing });
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

    var landmarkNameIssues = mk(EX);
    [
      ["navigation", "nav,[role=navigation]"],
      ["main", "main,[role=main]"],
      ["complementary", "aside,[role=complementary]"]
    ].forEach(function (spec) {
      var nodes = Array.prototype.slice.call(document.querySelectorAll(spec[1]), 0, 30);
      if (nodes.length < 2) return;
      var names = {};
      nodes.forEach(function (el) {
        // Landmark names come from aria-label / aria-labelledby, not from all
        // descendant text. Treating a nav's links as its accessible name made
        // every unnamed navigation region appear uniquely named by accident.
        var name = (el.getAttribute("aria-label") || "").trim();
        if (!name && el.getAttribute("aria-labelledby")) {
          name = el.getAttribute("aria-labelledby").trim().split(/\s+/).map(function (id) {
            var lab = document.getElementById(id);
            return lab ? (lab.textContent || "").trim() : "";
          }).join(" ").trim();
        }
        name = name.toLowerCase();
        if (!name) {
          landmarkNameIssues.push({ sel: selectorFor(el), role: spec[0], issue: "unnamed among repeated role" });
        } else if (names[name]) {
          landmarkNameIssues.push({ sel: selectorFor(el), role: spec[0], issue: "duplicate name", name: name });
        } else {
          names[name] = true;
        }
      });
    });

    return {
      imagesMissingAlt: imgsNoAlt.out(),
      fieldsMissingLabel: fieldsNoLabel.out(),
      fieldsPlaceholderOnly: placeholderOnly.out(),
      controlsMissingAccessibleName: btnsNoName.out(),
      labelInName: labelName.out(),
      invalidAutocomplete: invalidAutocomplete.out(),
      inputPurposeReview: purposeReview.out(),
      invalidLanguageTags: invalidLang.out(),
      unrecognizedLanguageTags: unknownLang.out(),
      brokenAriaReferences: brokenRefs.out(),
      requiredBrokenAriaReferences: requiredBrokenRefs.out(),
      deferredAriaControls: deferredControlRefs.out(),
      ariaRoleStateIssues: roleStateIssues.out(),
      landmarkNameIssues: landmarkNameIssues.out(),
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
      lang: (document.documentElement.getAttribute("lang") || "").trim() || null,
      skipLink: !!document.querySelector('a[href^="#"][class*="skip"],a[href^="#main"],a[href^="#content"]')
    };
  });

  /* ---------------- layout + responsiveness ---------------- */
  safe("layout", function () {
    var de = document.documentElement;
    var overflowers = mk(EX);
    var clipped = mk(EX * 2);
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
      if (visible(el, cs) && (cs.overflowX === "hidden" || cs.overflowX === "clip" ||
                              cs.overflowY === "hidden" || cs.overflowY === "clip") &&
          ((el.scrollWidth > el.clientWidth + 1) || (el.scrollHeight > el.clientHeight + 1)) &&
          (el.innerText || "").trim()) {
        clipped.push({ sel: selectorFor(el), scrollWidth: el.scrollWidth, clientWidth: el.clientWidth,
                       scrollHeight: el.scrollHeight, clientHeight: el.clientHeight,
                       ellipsis: cs.textOverflow === "ellipsis" });
      }
      if ((cs.position === "sticky" || cs.position === "fixed") && visible(el, cs) && sticky.length < EX) {
        var r = el.getBoundingClientRect();
        sticky.push({ sel: selectorFor(el), position: cs.position, height: Math.round(r.height), top: Math.round(r.top) });
      }
    });
    return {
      horizontalOverflow: de.scrollWidth > de.clientWidth + 1,
      scrollWidth: de.scrollWidth, clientWidth: de.clientWidth,
      overflowingElements: overflowers.list, overflowingElementCount: overflowers.n,
      clippedContent: clipped.out(),
      documentHeight: de.scrollHeight,
      stickyOrFixed: sticky,
      // 2.4.11: a sticky header taller than the gap above a focused row can
      // obscure focus. Reported as a measurement to check, not a verdict.
      //
      // A full-viewport `position: fixed` box is EXCLUDED, and the distinction is
      // the whole point of the metric. Chrome is a BAND: a header or a bar that
      // occupies part of the screen and pushes content out of the way. An element
      // pinned to the entire viewport is the app SHELL - the thing that owns
      // scrolling so the document does not - and it eats nothing. Counting it
      // reported "fixed chrome is 390px of a 390px viewport (100%)" on every
      // surface of every app built the `fixed inset-0` way, which is a large and
      // growing share of them, and the advice attached to it ("collapse the
      // sticky header") is not actionable because there is no header.
      stickyTotalHeight: sticky.reduce(function (a, b) {
        if (b.top > 1) return a;
        if (b.height >= (window.innerHeight || 0) * 0.95) return a;   // shell, not chrome
        return a + b.height;
      }, 0)
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
      var nativeThs = Array.prototype.slice.call(t.querySelectorAll("th"));
      var headerRows = new Set(nativeThs.map(function (th) { return th.parentElement; })).size;
      var rowHeaders = nativeThs.filter(function (th) {
        return th.parentElement && th.parentElement !== rows[0];
      }).length;
      var spanningHeaders = nativeThs.filter(function (th) {
        return (parseInt(th.getAttribute("rowspan") || "1", 10) > 1 ||
                parseInt(th.getAttribute("colspan") || "1", 10) > 1);
      }).length;
      var hasHeaderAssociations = !!t.querySelector("th[scope],td[headers],th[headers]");
      // W3C H63: <th> alone is sufficient for a small, simple table whose
      // headers occupy one obvious direction. Explicit association becomes
      // necessary when the table is large or has row + column / spanning /
      // multi-level headers. Do not turn a sufficient technique into a
      // universal markup requirement.
      var needsHeaderAssociations = rows.length > 10 || headerRows > 1 ||
                                    rowHeaders > 0 || spanningHeaders > 0;
      return {
        sel: selectorFor(t), rows: rows.length, columns: ths.length,
        medianRowHeight: heights.length ? heights[Math.floor(heights.length / 2)] : null,
        stickyHeader: stickyHead,
        hasScope: !!t.querySelector("th[scope]"),
        hasHeaderAssociations: hasHeaderAssociations,
        needsHeaderAssociations: needsHeaderAssociations,
        headerRows: headerRows, rowHeaders: rowHeaders, spanningHeaders: spanningHeaders,
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
      // `all` is the INITIAL value of transition-property, so every element
      // with no transition at all reports it. Only count it where the author
      // actually asked for a transition (non-zero duration), or this fires on
      // every <script>, <meta> and <svg> in the document.
      if (cs.transitionProperty === "all" && d > 0) allProp++;
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
      // HSL saturation is not a usable colourfulness test near white or black:
      // it is (max-min)/(2-max-min) above L=0.5, so it blows up as lightness
      // approaches 1. A barely-tinted white like rgb(254,252,249) reports
      // s=0.71 -- HIGHER than a genuinely tinted sky-100 circle -- which made
      // any near-white control (a drag handle, a FAB) register as the
      // "icon in a coloured circle" slop tell. Gate on raw channel spread as
      // well, which is stable at every lightness: tinted white spreads 0.02,
      // sky-100 spreads 0.19, amber-50 spreads 0.09.
      var spread = (Math.max(bg.r, bg.g, bg.b) - Math.min(bg.r, bg.g, bg.b)) / 255;
      if (hsl(bg).s < 0.15 || spread < 0.08) return;
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
      if (matching !== 3) return;
      // Three columns is not the defect. The slop-list item is a "stock 3-icon
      // feature row" -- three INTERCHANGEABLE cards of icon, two-word heading
      // and one sentence of category filler, there to fill a row rather than
      // to carry anything. Three real things in three columns is just a
      // comparison, and it is the honest layout for one.
      //
      // Caught on a real product: a pool company's emergency section -- three
      // services at $129/$195/$95, each with its own bullet list and its own
      // "Request this" link -- was being counted as a feature triptych, while
      // the same page's six-item grid had ALREADY been rewritten to two
      // columns for exactly the reason this tell exists. The detector was
      // firing on the fixed layout and silent on the pattern's real shape.
      //
      // A card earns its place if it offers an action of its own or carries
      // more than a sentence. Filler does neither: the planted fixture case is
      // "Fast / Secure / Simple", one generic line each, nothing to click.
      var substantive = kids.filter(function (k) {
        if (k.querySelector("a[href],button")) return true;
        return (k.innerText || "").trim().length > 200;
      }).length;
      if (substantive === 0) featureGrids++;
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

    // Decorative zero-padded step numbers: the "01 / 02 / 03" section label.
    // The most-copied template ornament of the current era. It carries no
    // information the heading does not already carry.
    //
    // Gate hard on ORNAMENT, not on the digits: a lone "01" is data (a jersey,
    // a version, a table cell), and docking a page for it would be exactly the
    // kind of confident wrongness this rig exists to prevent. Require the
    // element's WHOLE text to be the padded number, require at least two of
    // them on the page, and require them to be siblings-in-pattern rather than
    // scattered.
    //
    // "In pattern" is keyed on SHAPE, not on identity. Keying it on the
    // grandparent's selector (what this did until 2026-07-30) silently missed
    // the most common shipped form of the ornament: one numeral per `<li>` in
    // a list. Each numeral then has a DIFFERENT grandparent, every bucket
    // holds exactly one, and a six-service catalogue prefixed "01" through
    // "06" scored a clean zero. Repeated markup is what makes it ornament, so
    // the key is the numeral's own tag + class + size and its parent's tag:
    // template output collides on that, a lone unit number does not.
    var padded = mk(EX), paddedParents = {};
    function shapeKey(el) {
      if (!el) return "?";
      var cls = ((el.getAttribute && el.getAttribute("class")) || "").trim().replace(/\s+/g, ".");
      return el.tagName + (cls ? "." + cls : "");
    }
    ALL.forEach(function (el) {
      if (el.children.length) return;                 // leaf nodes only
      var t = (el.textContent || "").trim().replace(/[.)]$/, "");
      if (!/^0[1-9]$/.test(t)) return;
      var cs = getComputedStyle(el);
      if (!visible(el, cs)) return;
      if (el.closest("table,td,th,li[value],time,input,select,textarea")) return;
      var key = shapeKey(el) + "|" + shapeKey(el.parentElement) + "|" + px(cs.fontSize);
      paddedParents[key] = (paddedParents[key] || 0) + 1;
      padded.push({ sel: selectorFor(el), text: t,
                    fontSize: px(cs.fontSize), weight: cs.fontWeight });
    });
    var patterned = 0;
    Object.keys(paddedParents).forEach(function (k) {
      if (paddedParents[k] >= 2) patterned += paddedParents[k];
    });
    note("decorativeStepNumbers", patterned >= 2 ? patterned : 0);
    note("decorativeStepNumberSamples", padded.out().list);

    // Em dashes in rendered copy. One is a writer. Eight on a landing page is
    // a model. Reported as a rate as well as a count so a long documentation
    // page is not punished for being long.
    var emDashes = (body.match(/—/g) || []).length;
    var copyChars = body.replace(/\s+/g, " ").length;
    note("emDashesInCopy", emDashes);
    note("emDashesPer1kChars", copyChars ? Math.round((emDashes / copyChars) * 10000) / 10 : 0);

    // The LLM sentence frames. These are recognisable enough that a reader
    // clocks them before they finish the line.
    var FRAMES = [
      /\bnot just (a |an |the )?[\w-]+,? but\b/i,
      /\bit'?s not about [\w\s-]{3,30}\.? it'?s about\b/i,
      /\bisn'?t just (a|an|the)\b/i,
      /\bmore than just (a|an|the)\b/i,
      /\bin today'?s [\w-]+ world\b/i,
      /\bwhether you'?re a[\w\s-]{2,30} or a\b/i
    ];
    note("llmSentenceFrames", FRAMES.map(function (re) {
      var m = body.match(re); return m ? m[0].slice(0, 60) : null;
    }).filter(Boolean));

    return tells;
  });

  /* ---------------- chrome: the parts the OS draws for you ---------------- */
  //
  // Scrollbars, <select> popups, autofill and date pickers are drawn by the
  // browser, not by the page, so they never appear in a screenshot and never
  // show up in a CSS review. They are also where a dark theme most visibly
  // stops being a dark theme. One declaration governs nearly all of it.
  safe("chrome", function () {
    var rootCs = getComputedStyle(document.documentElement);
    var bodyCs = document.body ? getComputedStyle(document.body) : rootCs;
    var declared = (rootCs.colorScheme || "normal").toLowerCase();

    // Is this surface actually dark? Ask the pixels, not the class name.
    var pageBg = rgba(bodyCs.backgroundColor) || rgba(rootCs.backgroundColor);
    var pageLum = pageBg ? (0.2126 * pageBg.r + 0.7152 * pageBg.g + 0.0722 * pageBg.b) / 255 : null;
    var looksDark = pageLum !== null && pageLum < 0.3;

    var scrollables = [], hidden = mk(EX);
    ALL.forEach(function (el) {
      var cs = getComputedStyle(el);
      var canScrollY = el.scrollHeight > el.clientHeight + 4 &&
                       /auto|scroll|overlay/.test(cs.overflowY);
      var canScrollX = el.scrollWidth > el.clientWidth + 4 &&
                       /auto|scroll|overlay/.test(cs.overflowX);
      if (!canScrollY && !canScrollX) return;
      scrollables.push(el);
      // `scrollbar-width: none` on a region the user must scroll removes the
      // only thing saying more content exists, and removes a pointer user's
      // ability to drag it. That is a defect. An UNstyled scrollbar is not,
      // and this check deliberately does not look for one.
      if ((cs.scrollbarWidth || "").toLowerCase() === "none") {
        hidden.push({ sel: selectorFor(el),
                      scrollsY: canScrollY, scrollsX: canScrollX });
      }
    });

    // Selects whose native chevron was removed with nothing put back.
    var strippedSelects = mk(EX), selects = document.querySelectorAll("select");
    Array.prototype.slice.call(selects, 0, 60).forEach(function (el) {
      var cs = getComputedStyle(el);
      var app = (cs.appearance || cs.webkitAppearance || "").toLowerCase();
      if (app !== "none") return;
      if (cs.backgroundImage && cs.backgroundImage !== "none") return;   // own chevron
      var host = el.parentElement;
      if (host && host.querySelector("svg,img,[class*=chevron],[class*=caret],[class*=arrow]")) return;
      strippedSelects.push({ sel: selectorFor(el), appearance: app });
    });

    // Native `title` tooltips. The OS box: slow, unstyled, invisible on touch,
    // unreachable by keyboard, and it vanishes while you are reading it.
    // `title` on an iframe, or duplicating an element's own visible text, is
    // correct markup and is not counted.
    var titled = mk(EX);
    Array.prototype.slice.call(document.querySelectorAll("[title]"), 0, 200).forEach(function (el) {
      var tag = el.tagName.toLowerCase();
      if (tag === "iframe" || tag === "svg" || tag === "title") return;
      var t = (el.getAttribute("title") || "").trim();
      if (!t) return;
      var own = (el.innerText || "").trim();
      if (own && own.toLowerCase() === t.toLowerCase()) return;   // redundant, not a tooltip
      var cs = getComputedStyle(el);
      if (!visible(el, cs)) return;
      titled.push({ sel: selectorFor(el), title: t.slice(0, 60),
                    hasVisibleText: !!own, tag: tag });
    });

    return {
      colorScheme: declared,
      pageLuminance: pageLum === null ? null : Math.round(pageLum * 100) / 100,
      surfaceLooksDark: looksDark,
      // The one-line fix with the widest blast radius in the whole rig.
      darkSurfaceWithoutColorScheme: looksDark && declared.indexOf("dark") === -1,
      scrollbarColorDeclared: (rootCs.scrollbarColor || "auto").toLowerCase() !== "auto",
      scrollableRegions: scrollables.length,
      hiddenScrollbars: hidden.out().count,
      hiddenScrollbarList: hidden.out().list,
      selects: selects.length,
      unstyledStrippedSelects: strippedSelects.out().count,
      strippedSelectList: strippedSelects.out().list,
      nativeTitleTooltips: titled.out().count,
      nativeTitleTooltipList: titled.out().list
    };
  });

  return out;
}

// Make it callable from both the runner and a pasted browser_evaluate call.
if (typeof window !== "undefined") window.__ddProbe = __ddProbe;
if (typeof module !== "undefined" && module.exports) module.exports = __ddProbe;
