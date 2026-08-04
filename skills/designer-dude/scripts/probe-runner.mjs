/*
 * designer-dude probe runner - Playwright-side driver for probe.js.
 *
 * Run it with the MCP tool that loads Playwright code from a FILE, so neither
 * the probe source nor its JSON output ever enters the conversation:
 *
 *   mcp__playwright__browser_run_code_unsafe({
 *     filename: "/home/<you>/.claude/skills/designer-dude/scripts/probe-runner.mjs"
 *   })
 *
 * FILE SHAPE: this file is a bare `async (page) => { ... }` EXPRESSION, because
 * that tool documents its `code` parameter as exactly that and `filename` as
 * loading the same thing. It therefore avoids import statements and
 * `import.meta` and uses dynamic `await import()` instead, so it evaluates
 * correctly whether the harness eval's it or imports it. If your harness
 * instead wants a module, prefix the arrow function with `export default `.
 *
 * It reads its config from a fixed absolute path (there is no way to pass
 * arguments through that tool), writes one JSON per surface plus screenshots to
 * disk, and returns a ~15-line summary. Write the config first:
 *
 *   ~/.cache/designer-dude/probe-config.json
 *   {
 *     "outDir":    "/abs/path/to/repo/.design",   // required
 *     "label":     "dashboard",                   // required, becomes the filename
 *     "url":       "http://localhost:3000/dashboard",  // optional; omit to probe the current page
 *     "viewports": [[1920,1080],[1440,900],[1024,768],[768,1024],[390,844],[320,720]],
 *     "dark":      true,        // also probe with colorScheme: dark
 *     "reducedMotion": true,    // also probe with prefers-reduced-motion: reduce
 *     "landscapePhone": true,   // default true; adds an 844x390 short-viewport pass
 *     "touchBelowPx":  500,     // viewports narrower than this get REAL touch
 *                               // emulation: pointer:coarse, hover:none,
 *                               // maxTouchPoints=5. Without it a 390px run is
 *                               // just a narrow desktop and hover-only UI passes.
 *     "waitMs":    700,
 *     "fullPage":  true,
 *     "stableScreenshots": true, // default; two identical animation-disabled captures
 *     "ariaSnapshots": true,  // default true; accessibility tree per pass
 *
 *     // Internationalisation and perception stress. Text expansion is safe
 *     // for any product; RTL is applicable only when an RTL locale is in
 *     // scope. Vision simulations are advisory screenshots, never findings
 *     // merely because pixels changed.
 *     "i18n": { "textExpansion": true, "rtl": true },
 *     "visionDeficiencies": ["achromatopsia", "deuteranopia"],
 *
 *     // Override passes. All four default ON; set false to skip one. Each
 *     // re-measures at 1440x900 with ONE user override applied, so a
 *     // regression is attributable. See the block that runs them for the
 *     // WCAG criterion each covers.
 *     "forced-colors":  true,   // Windows High Contrast
 *     "contrast-more":  true,   // prefers-contrast: more
 *     "text-spacing":   true,   // SC 1.4.12, the SC's own metrics
 *     "text-zoom-200":  true,   // SC 1.4.4, 200% text at an unchanged viewport
 *
 *     // Content stress: opt-in, MUTATES the page, reloads after.
 *     "stress": { "selector": "td, th, h1", "token": "Long-Unbroken-String" },
 *
 *     // State coverage. Probes the states a happy-path run never sees.
 *     // Each is a URL the app already has, or one selector to click.
 *     "states": [
 *       { "label": "empty",   "url": "http://localhost:3000/properties?seed=none" },
 *       { "label": "error",   "url": "http://localhost:3000/properties/does-not-exist" },
 *       { "label": "loading", "url": "http://localhost:3000/reports", "wait": 0 },
 *       { "label": "form-invalid", "click": "form button[type=submit]", "wait": 400 }
 *     ],
 *
 *     // Configured behavior: expectations are explicit, so a checker never
 *     // guesses which click should announce or which custom widget contract
 *     // the product intended.
 *     "announcements": [
 *       { "label": "save", "click": "button[type=submit]", "wait": 500,
 *         "expected": "saved|updated" }
 *     ],
 *     "widgets": [
 *       { "label": "report tabs", "kind": "tablist", "selector": "[role=tablist]" }
 *     ],
 *     "authChecks": [
 *       { "label": "sign in password", "selector": "#password",
 *         "expectedAutocomplete": "current-password" }
 *     ],
 *     "dragAlternatives": [
 *       { "label": "reorder invoice", "dragSelector": ".drag-handle",
 *         "alternativeSelector": "button[aria-label='Move invoice']" }
 *     ],
 *     "redundantEntries": [
 *       { "label": "shipping email", "firstSelector": "#email", "value": "test@example.com",
 *         "advance": "#next", "secondSelector": "#confirm-email" }
 *     ],
 *
 *     "skillDir":  "/abs/path/to/skills/designer-dude/scripts"  // optional override
 *   }
 *
 * Runs in the CURRENT browser context, so an authenticated session established
 * by earlier browse steps carries over - which is the only way to review the
 * surfaces behind a login. Use it against local dev and seeded test accounts;
 * on a page holding a REAL user's session, use browser_evaluate with a
 * `filename` instead (see mode-d-review.md).
 */
async (page) => {
  const fs = await import("node:fs");
  const crypto = await import("node:crypto");
  const os = await import("node:os");
  const path = await import("node:path");

  const cfgPath = path.join(os.homedir(), ".cache", "designer-dude", "probe-config.json");
  if (!fs.existsSync(cfgPath)) {
    return `NO CONFIG. Write ${cfgPath} first - see the header of probe-runner.mjs.`;
  }
  const cfg = JSON.parse(fs.readFileSync(cfgPath, "utf8"));
  if (!cfg.outDir || !cfg.label) return "CONFIG INVALID: outDir and label are required.";

  // Locate probe.js without import.meta (see FILE SHAPE above).
  const candidates = [
    cfg.skillDir && path.join(cfg.skillDir, "probe.js"),
    path.join(os.homedir(), ".claude", "skills", "designer-dude", "scripts", "probe.js"),
    path.join(os.homedir(), "claude-skills", "skills", "designer-dude", "scripts", "probe.js"),
  ].filter(Boolean);
  const probePath = candidates.find((p) => fs.existsSync(p));
  if (!probePath) {
    return "Could not find probe.js. Add \"skillDir\" to the config. Looked in:\n  " +
           candidates.join("\n  ");
  }
  const probeSrc = fs.readFileSync(probePath, "utf8");

  // The default matrix covers the five widths the Responsiveness pillar names,
  // each chosen for a failure it uniquely catches:
  //   1920 - no max-width: measure explodes past 75ch on wide monitors
  //   1440 - the design target; where everything looks fine
  //   1024 - small laptop / tablet landscape; the first breakpoint to collapse
  //    768 - tablet portrait; nav and table decisions land here
  //    390 - modern phone; the real mobile target
  //    320 - smallest supported (iPhone SE); where horizontal overflow appears
  // Landscape phone is added separately below.
  const viewports = (cfg.viewports && cfg.viewports.length)
    ? cfg.viewports
    : [[1920, 1080], [1440, 900], [1024, 768], [768, 1024], [390, 844], [320, 720]];
  const waitMs = cfg.waitMs == null ? 700 : cfg.waitMs;

  // ---- touch emulation -------------------------------------------------
  //
  // page.setViewportSize() ONLY resizes. It does not make the browser a phone:
  // `pointer: coarse`, `hover: none` and `navigator.maxTouchPoints` stay at
  // their desktop values. Without this block every "390x844" run is a desktop
  // browser in a narrow window, hover-only affordances keep working, and any
  // coarse-pointer branch of the CSS is never exercised -- while the report
  // still says "probed at 390px", which is the kind of false coverage that is
  // worse than an admitted gap.
  //
  // Playwright's emulateMedia() cannot set pointer/hover, so this goes through
  // CDP. Chromium-only, which the MCP browser is. If the session refuses it we
  // record touchEmulation:"unavailable" and probe-report.py downgrades the
  // responsive evidence rather than silently claiming the coverage.
  const touchBelow = cfg.touchBelowPx == null ? 500 : cfg.touchBelowPx;
  let cdp = null, cdpBroken = false;
  const getCdp = async () => {
    if (cdp || cdpBroken) return cdp;
    try { cdp = await page.context().newCDPSession(page); }
    catch (e) { cdpBroken = true; }
    return cdp;
  };
  const setTouch = async (on) => {
    const s = await getCdp();
    if (!s) return "unavailable";
    try {
      // maxTouchPoints must be 1..16 when present - sending 0 to disable is a
      // protocol error, so omit it entirely on the way out.
      await s.send("Emulation.setTouchEmulationEnabled",
        on ? { enabled: true, maxTouchPoints: 5 } : { enabled: false });
      await s.send("Emulation.setEmitTouchEventsForMouse", {
        enabled: on, configuration: on ? "mobile" : "desktop",
      });
      await s.send("Emulation.setEmulatedMedia", {
        features: on ? [
          { name: "pointer", value: "coarse" },
          { name: "any-pointer", value: "coarse" },
          { name: "hover", value: "none" },
          { name: "any-hover", value: "none" },
        ] : [],
      });
      return on ? "touch" : "mouse";
    } catch (e) { cdpBroken = true; return "unavailable"; }
  };
  const shotDir = path.join(cfg.outDir, "screenshots");
  const ariaDir = path.join(cfg.outDir, "accessibility");
  fs.mkdirSync(shotDir, { recursive: true });
  if (cfg.ariaSnapshots !== false || (Array.isArray(cfg.announcements) && cfg.announcements.length)) {
    fs.mkdirSync(ariaDir, { recursive: true });
  }

  const consoleErrors = [];
  const failedRequests = [];
  page.on("console", (m) => {
    if (m.type() === "error" && consoleErrors.length < 25) consoleErrors.push(m.text().slice(0, 300));
  });
  page.on("requestfailed", (r) => {
    if (failedRequests.length < 25) {
      const f = r.failure();
      failedRequests.push(`${r.method()} ${r.url().slice(0, 160)} - ${f ? f.errorText : "?"}`);
    }
  });

  if (cfg.url) await page.goto(cfg.url, { waitUntil: "domcontentloaded" });

  // Performance facts for the Interaction & Performance pillar. LAB numbers on
  // one machine and one network -- NOT the p75 field data the budgets are
  // defined against. probe-report.py labels them so, and they must never be
  // quoted as a Core Web Vitals result.
  const perf = () => page.evaluate(async () => {
    const nav = performance.getEntriesByType("navigation")[0];
    // LCP and layout-shift are NOT retrievable with getEntriesByType in
    // Chromium - that call returns an empty list however long you wait, and the
    // runner reported `LCP=null` on every run because of it. They are only
    // reachable through a PerformanceObserver with `buffered: true`, which
    // replays the entries the browser recorded before the observer existed.
    // Reporting a null LCP as a measurement is the failure this fixes: the
    // vitals half of the Interaction pillar was ungraded while looking graded.
    const buffered = (type) => new Promise((resolve) => {
      const seen = [];
      try {
        const obs = new PerformanceObserver((list) => { seen.push(...list.getEntries()); });
        obs.observe({ type, buffered: true });
        // One task is enough for a buffered replay; do not hang if unsupported.
        setTimeout(() => { try { obs.disconnect(); } catch (e) { /* gone */ } resolve(seen); }, 120);
      } catch (err) { resolve(seen); }
    });
    const [lcpEntries, shifts] = await Promise.all([
      buffered("largest-contentful-paint"),
      buffered("layout-shift"),
    ]);
    const paints = {};
    performance.getEntriesByType("paint").forEach((p) => { paints[p.name] = Math.round(p.startTime); });
    let cls = 0;
    for (const e of shifts) if (!e.hadRecentInput) cls += e.value;
    const res = performance.getEntriesByType("resource");
    const byType = {};
    res.forEach((r) => {
      const t = r.initiatorType || "other";
      byType[t] = (byType[t] || 0) + (r.transferSize || 0);
    });
    return {
      note: "LAB measurement on one machine and one network. NOT p75 CrUX field data.",
      domContentLoaded: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
      loadEvent: nav ? Math.round(nav.loadEventEnd) : null,
      firstContentfulPaint: paints["first-contentful-paint"] || null,
      largestContentfulPaint: lcpEntries.length
        ? Math.round(lcpEntries[lcpEntries.length - 1].startTime) : null,
      cumulativeLayoutShift: Math.round(cls * 1000) / 1000,
      transferBytes: res.reduce((a, r) => a + (r.transferSize || 0), 0),
      transferByInitiator: byType,
      requests: res.length,
      domNodes: document.querySelectorAll("*").length,
      stylesheets: document.styleSheets.length,
    };
  });

  const runs = [];
  const summary = [];
  const accessibilitySnapshots = [];
  const screenshotStability = [];

  const speechNorm = (value) => String(value || "").normalize("NFKC")
    .toLocaleLowerCase().replace(/[\p{P}\p{S}\s]+/gu, "");
  const rootFromAriaSnapshot = (tree) => {
    const first = String(tree || "").split(/\r?\n/, 1)[0];
    if (!first.trim()) return { inTree: false, name: null };
    const quoted = first.match(/^\s*-\s+[^\s:]+\s+("(?:[^"\\]|\\.)*")/);
    if (quoted) {
      try { return { inTree: true, name: JSON.parse(quoted[1]) }; } catch { return { inTree: true, name: null }; }
    }
    const single = first.match(/^\s*-\s+[^\s:]+\s+'([^']*)'/);
    return { inTree: true, name: single ? single[1].replace(/''/g, "'") : "" };
  };

  // Confirm SC 2.5.3 against the browser's computed accessibility tree. The
  // in-page fallback can identify candidates, but only the browser knows the
  // full Accessible Name computation (host-language rules, hidden references,
  // SVG and platform semantics). Keep inconclusive selectors separate; never
  // silently convert them to passes.
  const verifyLabelInName = async (data) => {
    const candidates = (((data || {}).a11y || {}).labelInName || {}).list || [];
    const checked = [], failures = [], inconclusive = [];
    for (const item of candidates) {
      try {
        const loc = page.locator(item.locator || item.sel).first();
        if (await loc.count() < 1 || typeof loc.ariaSnapshot !== "function") {
          inconclusive.push({ ...item, reason: "element or locator.ariaSnapshot unavailable" });
          continue;
        }
        const root = rootFromAriaSnapshot(await loc.ariaSnapshot());
        const computedName = root.name;
        if (!root.inTree || computedName == null) {
          inconclusive.push({ ...item, reason: "computed name could not be parsed" });
          continue;
        }
        const verified = { ...item, computedName, accessibleNameSource: "browser-aria-snapshot", computed: true };
        checked.push(verified);
        if (!speechNorm(computedName).includes(speechNorm(item.visibleLabel))) failures.push(verified);
      } catch (e) {
        inconclusive.push({ ...item, reason: String(e).slice(0, 140) });
      }
    }
    data.a11y.browserLabelInName = {
      candidates: candidates.length, checked: checked.length,
      failures: failures.length, list: failures, inconclusive,
    };
  };

  const verifyMissingNames = async (data) => {
    const fields = ((((data || {}).a11y || {}).fieldsMissingLabel || {}).list || [])
      .map((item) => ({ ...item, source: "field" }));
    const controls = ((((data || {}).a11y || {}).controlsMissingAccessibleName || {}).list || [])
      .map((item) => ({ ...item, source: "control" }));
    const candidates = [...fields, ...controls];
    const confirmed = [], dismissed = [], inconclusive = [];
    for (const item of candidates) {
      try {
        const loc = page.locator(item.locator || item.sel).first();
        if (await loc.count() < 1 || typeof loc.ariaSnapshot !== "function") {
          inconclusive.push({ ...item, reason: "element or locator.ariaSnapshot unavailable" });
          continue;
        }
        const root = rootFromAriaSnapshot(await loc.ariaSnapshot());
        if (!root.inTree) dismissed.push({ ...item, reason: "not in accessibility tree" });
        else if (root.name == null) inconclusive.push({ ...item, reason: "computed name could not be parsed" });
        else if (String(root.name).trim()) dismissed.push({ ...item, computedName: root.name, reason: "browser computed a name" });
        else confirmed.push({ ...item, computedName: "", reason: "browser accessibility-tree name is empty" });
      } catch (e) {
        inconclusive.push({ ...item, reason: String(e).slice(0, 140) });
      }
    }
    data.a11y.browserMissingAccessibleName = {
      candidates: candidates.length, checked: confirmed.length + dismissed.length,
      failures: confirmed.length, list: confirmed, dismissed, inconclusive,
    };
  };

  // Captured HERE, before a single viewport resize, and never later.
  //
  // LCP is not final until the first user interaction: every resize can paint
  // a new largest element and register a new entry. The viewport sweep below
  // does four of them, so reading LCP after it measured a post-resize repaint
  // rather than the page load - /about reported 2876ms, then 4308ms, then
  // 2860ms across three consecutive rounds while the same page measured 84ms
  // in a fresh context. That number is load-bearing: it blocks the interaction
  // credit's vitals clause, so a rig artifact was reading as a product defect.
  const performanceData = await perf();

  const probeOnce = async (tag, w, h, opts) => {
    const wantTouch = opts && opts.touch != null ? opts.touch : w < touchBelow;
    let touchState = await setTouch(!!wantTouch);
    await page.setViewportSize({ width: w, height: h });
    await page.waitForTimeout(waitMs);
    await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
    const shot = path.join(shotDir, `${cfg.label}-${tag}.png`);
    try {
      const shotOpts = { path: shot, fullPage: !!cfg.fullPage, animations: "disabled", caret: "hide" };
      const first = await page.screenshot(shotOpts);
      if (cfg.stableScreenshots !== false) {
        let previous = first;
        let previousHash = crypto.createHash("sha256").update(previous).digest("hex");
        const firstHash = previousHash;
        let stable = null, captures = 1;
        while (!stable && captures < 3) {
          await page.waitForTimeout(80);
          const next = await page.screenshot({ ...shotOpts, path: undefined });
          const nextHash = crypto.createHash("sha256").update(next).digest("hex");
          captures++;
          if (previousHash === nextHash) stable = { buffer: next, sha256: nextHash };
          previous = next; previousHash = nextHash;
        }
        if (stable) {
          fs.writeFileSync(shot, stable.buffer); // the stored baseline is one of the stable pair
          screenshotStability.push({ tag, status: "stable", sha256: stable.sha256, captures });
        } else {
          const unstable = path.join(shotDir, `${cfg.label}-${tag}-stability-2.png`);
          fs.writeFileSync(unstable, previous);
          screenshotStability.push({ tag, status: "unstable", firstSha256: firstHash,
                                     lastSha256: previousHash,
                                     captures, lastCapture: unstable });
        }
      }
    } catch (e) { /* a very tall fullPage shot can exceed limits */ }
    // A fullPage screenshot resizes the viewport through
    // Emulation.setDeviceMetricsOverride, and Chromium drops the emulated
    // media features and touch points on the way back out. Without this
    // re-assert, every mobile run is a desktop browser in a narrow window
    // while the summary still prints [touch] -- the exact false coverage the
    // block above exists to prevent. The probe reads pointer:coarse from the
    // page, so it must be true at evaluate() time, not at setViewportSize().
    if (cfg.fullPage) touchState = await setTouch(!!wantTouch);
    const data = await page.evaluate(([src]) => {
      // eslint-disable-next-line no-new-func
      new Function(src)();
      return window.__ddProbe({});
    }, [probeSrc]);
    await verifyLabelInName(data);
    await verifyMissingNames(data);
    data.tag = tag;
    data.screenshot = shot;
    // The DOM can look correctly wired while the computed accessibility tree
    // exposes a wrong name, role, state or hierarchy. Playwright's ARIA
    // snapshot is the browser's accessibility view, stored separately so it
    // remains reviewable without bloating the probe JSON or model context.
    if (cfg.ariaSnapshots !== false) {
      const ariaFile = path.join(ariaDir, `${cfg.label}-${tag}.aria.yml`);
      try {
        if (typeof page.ariaSnapshot !== "function") throw new Error("page.ariaSnapshot unavailable");
        const tree = await page.ariaSnapshot();
        fs.writeFileSync(ariaFile, tree);
        data.ariaSnapshot = ariaFile;
        accessibilitySnapshots.push({ tag, status: "written", path: ariaFile });
      } catch (e) {
        data.ariaSnapshot = null;
        accessibilitySnapshots.push({ tag, status: "unavailable", reason: String(e).slice(0, 160) });
      }
    }
    data.emulation = {
      touch: touchState,                       // "touch" | "mouse" | "unavailable"
      requestedTouch: !!wantTouch,
      orientation: w >= h ? "landscape" : "portrait",
    };
    runs.push(data);
    const c = (data.color || {}).textContrast || {};
    const i = data.interaction || {};
    const a = data.a11y || {};
    summary.push(
      `${tag.padEnd(16)} ${touchState === "touch" ? "[touch]" : touchState === "unavailable" ? "[NO-EMU]" : "[mouse]"} ` +
      `contrast=${c.failures}/${c.checked} ` +
      `focus-invisible=${(i.focusRing || {}).invisible} ` +
      `tiny=${(i.belowWcagTarget24 || {}).count} ` +
      `no-pointer=${(i.missingPointerCursor || {}).count} ` +
      `no-label=${(a.fieldsMissingLabel || {}).count} ` +
      `no-name=${(a.controlsMissingAccessibleName || {}).count} ` +
      `no-alt=${(a.imagesMissingAlt || {}).count} ` +
      `h-overflow=${(data.layout || {}).horizontalOverflow} ` +
      `radii=${((data.system || {}).radius || {}).distinct} ` +
      `fonts=${(data.typography || {}).distinctFamilies} ` +
      `accent=${(data.color || {}).accentPixelShare}%` +
      ((data.errors || []).length ? ` PROBE-ERRORS=${data.errors.length}` : "")
    );
  };

  for (const vp of viewports) await probeOnce(`${vp[0]}x${vp[1]}`, vp[0], vp[1]);

  // Every override below runs at 1440x900 and is graded as a delta. A custom
  // viewport matrix used to be able to omit that baseline, leaving the report
  // to compare unlike viewports (or silently fall back to the primary run).
  // Capture the matching control whenever any delta pass can run.
  const deltaPasses = ["forced-colors", "contrast-more", "text-spacing", "text-zoom-200"];
  const needsComparisonBaseline =
    deltaPasses.some((name) => cfg[name] !== false) || cfg.dark || cfg.reducedMotion ||
    Boolean(cfg.i18n?.textExpansion || cfg.i18n?.rtl || cfg.i18n?.profiles?.length);
  if (needsComparisonBaseline && !runs.some((run) => run.tag === "1440x900")) {
    await probeOnce("1440x900", 1440, 900, { touch: false });
  }

  // Landscape phone. A distinct device state, not a redundant width: it is
  // where `h-screen`/`100vh` sections, sticky headers and fixed bottom bars
  // eat the entire viewport, and it is the orientation reviewers never check.
  // Short-viewport bugs are invisible at every portrait size.
  if (cfg.landscapePhone !== false) await probeOnce("landscape-844x390", 844, 390);

  // Asserted by whoever wrote the config, never detected: nothing in the page
  // reliably says "this bundle came from a production build". Without it the
  // interaction credit can never pass its vitals clause however the server was
  // started, which reads as a product defect when it is a rig gap. Set it in
  // the config ONLY when the URL really is a production build.
  performanceData.productionBuild = cfg.productionBuild === true;

  // Preference passes are desktop/mouse on purpose -- they isolate ONE
  // variable each. Mixing touch into the dark pass makes a contrast
  // regression and a coarse-pointer regression indistinguishable.
  // The dark pass RELOADS, and the reload is the whole point. Most products do
  // not theme off `prefers-color-scheme` directly: they run a pre-paint script
  // that reads localStorage, falls back to the media query, and stamps
  // `data-theme` / `.dark` on <html>. That script runs once, at load. Flipping
  // the media query on a live page therefore changes nothing at all, and the
  // pass returns the LIGHT theme's numbers under the label "dark-1440x900" --
  // which reads as "dark is clean" and is how a dark theme goes unmeasured for
  // a whole campaign. Reloading re-runs the script under the emulated
  // preference, which is what a real user with an OS dark setting gets.
  // Verified against Sheevook: without the reload the dark screenshot was
  // pixel-identical to the light one.
  if (cfg.dark) {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.reload({ waitUntil: "load" }).catch(() => {});
    await page.waitForTimeout(waitMs);
    await probeOnce("dark-1440x900", 1440, 900, { touch: false });
    await page.emulateMedia({ colorScheme: "light" });
    await page.reload({ waitUntil: "load" }).catch(() => {});
    await page.waitForTimeout(waitMs);
  }
  if (cfg.reducedMotion) {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await probeOnce("reduced-motion", 1440, 900, { touch: false });
    await page.emulateMedia({ reducedMotion: "no-preference" });
  }

  // ---- override passes ---------------------------------------------------
  //
  // Four user overrides that no amount of contrast measuring will catch,
  // because each one changes the page rather than reading it. They are
  // deliberately shaped like the dark and reduced-motion passes above: same
  // viewport, mouse pointer, one variable each, so probe-report.py can diff a
  // pass against the 1440 baseline and attribute any regression to the
  // override itself.
  //
  // Every one of them is a documented WCAG failure mode:
  //   forced-colors  - Windows High Contrast strips backgrounds and
  //                    background-images. Icon-only buttons and any control
  //                    whose meaning lives in a background disappear.
  //   contrast: more - prefers-contrast, which a theme is allowed to ignore
  //                    but not allowed to regress under.
  //   text-spacing   - SC 1.4.12. The user's stylesheet loosens line, letter,
  //                    word and paragraph spacing; fixed-height containers
  //                    clip and text overlaps. Values are the SC's, exactly.
  //   text-zoom-200  - SC 1.4.4. Text at 200% with the viewport unchanged.
  //                    Distinct from the 320px pass: a fluid narrow layout
  //                    passes that one and still shatters under zoom, because
  //                    the failure is px-fixed containers, not width.
  //
  // Anything the browser refuses is recorded as unavailable rather than
  // skipped silently -- an unrun pass that looks run is the false coverage
  // this file already guards against for touch.
  const overrides = [];
  const overridePass = async (name, enable, disable) => {
    if (cfg[name] === false) return;
    try {
      await enable();
    } catch (e) {
      overrides.push({ pass: name, status: "unavailable", reason: String(e).slice(0, 160) });
      return;
    }
    await probeOnce(name, 1440, 900, { touch: false });
    try { await disable(); } catch (e) { /* best effort restore */ }
    overrides.push({ pass: name, status: "ran" });
  };

  await overridePass("forced-colors",
    () => page.emulateMedia({ forcedColors: "active" }),
    () => page.emulateMedia({ forcedColors: "none" }));

  await overridePass("contrast-more",
    () => page.emulateMedia({ contrast: "more" }),
    () => page.emulateMedia({ contrast: "no-preference" }));

  // SC 1.4.12 metrics, applied with !important so a component's own
  // line-height cannot quietly win and make the pass a no-op.
  const SPACING_CSS =
    "*, *::before, *::after { line-height: 1.5 !important; " +
    "letter-spacing: 0.12em !important; word-spacing: 0.16em !important; } " +
    "p, li, blockquote, dd { margin-bottom: 2em !important; }";
  let spacingTag = null;
  await overridePass("text-spacing",
    async () => {
      spacingTag = await page.addStyleTag({ content: SPACING_CSS });
    },
    async () => { if (spacingTag) await spacingTag.evaluate((el) => el.remove()); });

  await overridePass("text-zoom-200",
    () => page.evaluate(() => {
      const html = document.documentElement;
      html.dataset.ddPriorFontSize = html.style.fontSize || "";
      html.style.fontSize = "200%";
    }),
    () => page.evaluate(() => {
      const html = document.documentElement;
      html.style.fontSize = html.dataset.ddPriorFontSize || "";
      delete html.dataset.ddPriorFontSize;
    }));

  // ---- internationalisation stress ------------------------------------
  // These passes answer layout questions only. They do not claim that an
  // English-only product owes an RTL locale, or that generated pseudo-copy is
  // linguistically correct. Running them must be an explicit applicability
  // decision in config; once configured, an overflow/clipping delta is real.
  const i18nCfg = cfg.i18n && typeof cfg.i18n === "object" ? cfg.i18n : {};
  if (i18nCfg.textExpansion) {
    try {
      await page.evaluate(() => {
        const root = document.body;
        const originals = [];
        const skip = /^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA|CODE|PRE|SVG)$/;
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
          acceptNode(node) {
            const p = node.parentElement;
            if (!p || skip.test(p.tagName) || p.closest("[contenteditable=true]")) return NodeFilter.FILTER_REJECT;
            if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
            return NodeFilter.FILTER_ACCEPT;
          },
        });
        const nodes = [];
        while (walker.nextNode() && nodes.length < 1000) nodes.push(walker.currentNode);
        const accent = { a:"á", e:"ë", i:"ï", o:"ø", u:"ü", A:"Á", E:"Ë", I:"Ï", O:"Ø", U:"Ü" };
        for (const node of nodes) {
          originals.push([node, node.nodeValue]);
          node.nodeValue = node.nodeValue.replace(/[A-Za-z]{3,}/g, (word) => {
            const marked = word.replace(/[aeiouAEIOU]/g, (c) => accent[c] || c);
            return marked + "~".repeat(Math.max(1, Math.ceil(word.length * 0.35)));
          });
        }
        window.__ddTextExpansionOriginals = originals;
      });
      await probeOnce("text-expansion", 1440, 900, { touch: false });
      overrides.push({ pass: "text-expansion", status: "ran", expansion: "approximately 35% per word" });
    } catch (e) {
      overrides.push({ pass: "text-expansion", status: "unavailable", reason: String(e).slice(0, 160) });
    } finally {
      await page.evaluate(() => {
        for (const pair of window.__ddTextExpansionOriginals || []) pair[0].nodeValue = pair[1];
        delete window.__ddTextExpansionOriginals;
      }).catch(() => {});
    }
  }
  if (i18nCfg.rtl) {
    try {
      await page.evaluate(() => {
        const html = document.documentElement;
        window.__ddPriorDirection = { had: html.hasAttribute("dir"), value: html.getAttribute("dir") };
        html.setAttribute("dir", "rtl");
      });
      await probeOnce("rtl", 1440, 900, { touch: false });
      overrides.push({ pass: "rtl", status: "ran", applicability: "declared by config" });
    } catch (e) {
      overrides.push({ pass: "rtl", status: "unavailable", reason: String(e).slice(0, 160) });
    } finally {
      await page.evaluate(() => {
        const prior = window.__ddPriorDirection;
        if (prior && prior.had) document.documentElement.setAttribute("dir", prior.value || "");
        else document.documentElement.removeAttribute("dir");
        delete window.__ddPriorDirection;
      }).catch(() => {});
    }
  }

  // Real locale fixtures. Pseudo-expansion is a useful pressure test but it
  // cannot reproduce CJK line breaking, Arabic shaping, mixed bidi text,
  // translated labels, or locale-specific formatted values. A profile maps
  // stable selectors to reviewed translations while setting lang/dir and the
  // browser's Intl locale. Every mutation is restored after its own capture.
  const localeProfiles = Array.isArray(i18nCfg.profiles) ? i18nCfg.profiles : [];
  for (const profile of localeProfiles) {
    const label = String(profile?.label || profile?.locale || "locale")
      .toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48);
    const tag = `locale-${label || "unnamed"}`;
    let session = null;
    try {
      if (!profile || typeof profile !== "object" || !profile.locale ||
          (!profile.text || typeof profile.text !== "object")) {
        throw new Error("profile needs locale and a text selector map");
      }
      // Intl.Locale rejects syntactically invalid BCP 47 tags. Do this before
      // touching the page so an invalid fixture cannot produce plausible art.
      new Intl.Locale(profile.locale);
      session = await getCdp();
      if (session) await session.send("Emulation.setLocaleOverride", { locale: profile.locale });
      const mutation = await page.evaluate((p) => {
        const html = document.documentElement;
        const state = { html: { lang: html.getAttribute("lang"), dir: html.getAttribute("dir") },
                        text: [], attrs: [], missing: [] };
        html.setAttribute("lang", p.locale);
        if (p.dir) html.setAttribute("dir", p.dir);
        for (const [selector, value] of Object.entries(p.text || {}).slice(0, 500)) {
          const element = document.querySelector(selector);
          if (!element) { state.missing.push(selector); continue; }
          state.text.push([element, element.textContent]);
          element.textContent = String(value);
        }
        for (const [selector, values] of Object.entries(p.attributes || {}).slice(0, 200)) {
          const element = document.querySelector(selector);
          if (!element) { state.missing.push(selector); continue; }
          for (const [name, value] of Object.entries(values || {})) {
            state.attrs.push([element, name, element.hasAttribute(name), element.getAttribute(name)]);
            element.setAttribute(name, String(value));
          }
        }
        window.__ddLocaleOriginals = state;
        return { missing: state.missing, replacements: state.text.length,
                 attributes: state.attrs.length };
      }, profile);
      await probeOnce(tag, 1440, 900, { touch: false });
      overrides.push({ pass: tag, status: mutation.missing.length ? "partial" : "ran",
                       locale: profile.locale, direction: profile.dir || "document-default",
                       replacements: mutation.replacements, attributes: mutation.attributes,
                       missingSelectors: mutation.missing.slice(0, 30) });
    } catch (e) {
      overrides.push({ pass: tag, status: "unavailable", locale: profile?.locale,
                       reason: String(e).slice(0, 200) });
    } finally {
      await page.evaluate(() => {
        const state = window.__ddLocaleOriginals;
        if (!state) return;
        for (const [element, value] of state.text) element.textContent = value;
        for (const [element, name, had, value] of state.attrs) {
          if (had) element.setAttribute(name, value || ""); else element.removeAttribute(name);
        }
        if (state.html.lang === null) document.documentElement.removeAttribute("lang");
        else document.documentElement.setAttribute("lang", state.html.lang);
        if (state.html.dir === null) document.documentElement.removeAttribute("dir");
        else document.documentElement.setAttribute("dir", state.html.dir);
        delete window.__ddLocaleOriginals;
      }).catch(() => {});
      if (session) await session.send("Emulation.setLocaleOverride", { locale: "" }).catch(() => {});
    }
  }

  // Colour-vision simulations are evidence for human inspection. A changed
  // screenshot is expected and never a defect by itself; only a confirmed loss
  // of a semantic distinction belongs in the findings ledger.
  const visionResults = [];
  const visionKinds = Array.isArray(cfg.visionDeficiencies) ? cfg.visionDeficiencies : [];
  const allowedVision = new Set(["achromatopsia", "deuteranopia", "protanopia", "tritanopia", "blurredVision", "reducedContrast"]);
  for (const kind of visionKinds) {
    if (!allowedVision.has(kind)) {
      visionResults.push({ kind, status: "invalid-config" });
      continue;
    }
    const session = await getCdp();
    if (!session) { visionResults.push({ kind, status: "unavailable" }); continue; }
    try {
      await session.send("Emulation.setEmulatedVisionDeficiency", { type: kind });
      await probeOnce(`vision-${kind}`, 1440, 900, { touch: false });
      visionResults.push({ kind, status: "ran", interpretation: "advisory-human-review" });
    } catch (e) {
      visionResults.push({ kind, status: "unavailable", reason: String(e).slice(0, 160) });
    } finally {
      await session.send("Emulation.setEmulatedVisionDeficiency", { type: "none" }).catch(() => {});
    }
  }

  // ---- content stress ----------------------------------------------------
  //
  // Opt-in, because it MUTATES the page. Seeded fixtures are the kindest
  // content a product ever gets: short names, populated tables, no unbroken
  // strings. A layout graded only against them is graded against the demo.
  // This appends one long unbroken token to each matched container and
  // re-measures overflow and clipping. Run last of the in-page passes, and
  // reload afterwards so nothing downstream inherits a mutated DOM.
  if (cfg.stress) {
    const st = typeof cfg.stress === "object" ? cfg.stress : {};
    const sel = st.selector || "td, th, h1, h2, h3, [class*='truncate'], [class*='card'] p";
    const token = st.token || "Reconciliation-Adjustment-Unbroken-0123456789";
    try {
      await page.evaluate(([s, t]) => {
        const seen = document.querySelectorAll(s);
        for (let i = 0; i < Math.min(seen.length, 60); i++) {
          const el = seen[i];
          if (el.children.length === 0 && el.textContent.trim()) el.textContent += " " + t;
        }
      }, [sel, token]);
      await probeOnce("content-stress", 1440, 900, { touch: false });
      overrides.push({ pass: "content-stress", status: "ran", selector: sel });
    } catch (e) {
      overrides.push({ pass: "content-stress", status: "unavailable", reason: String(e).slice(0, 160) });
    }
    if (cfg.url) await page.goto(cfg.url, { waitUntil: "domcontentloaded" });
  }

  // ---- state coverage ----------------------------------------------------
  //
  // The seven states are a pillar input (enterprise.md) and until now they
  // were graded by READING SOURCE while everything else was measured. A
  // loading skeleton with a contrast failure, an empty state with no next
  // action, a 10k-row table that overflows -- none of it is visible in a
  // probe of the happy path at rest.
  //
  // Each state is {label, url?, click?, wait?}. Kept deliberately thin: a URL
  // the app already has for that state, or one selector to click. Anything
  // needing a real script belongs in the browse steps before the probe runs.
  // Last, because navigating away ends the run for every pass above.
  const states = Array.isArray(cfg.states) ? cfg.states : [];
  const stateResults = [];
  for (const s of states) {
    if (!s || !s.label) continue;
    try {
      if (s.url) await page.goto(s.url, { waitUntil: "domcontentloaded" });
      if (s.click) await page.click(s.click, { timeout: 5000 });
      if (s.wait) await page.waitForTimeout(s.wait);
      await probeOnce(`state-${s.label}`, 1440, 900, { touch: false });
      stateResults.push({ label: s.label, status: "ran", url: s.url || null, click: s.click || null });
    } catch (e) {
      stateResults.push({ label: s.label, status: "unreachable", reason: String(e).slice(0, 200) });
    }
  }

  // ---- configured status announcements + interaction timing ------------
  // A live-region count proves markup, not behavior. Observe the actual DOM
  // mutation caused by a named action, preserve before/after accessibility
  // trees, and collect Event Timing / LoAF entries from the same interaction.
  const announcementResults = [];
  for (const spec of Array.isArray(cfg.announcements) ? cfg.announcements : []) {
    if (!spec || !spec.label) continue;
    const safeLabel = String(spec.label).replace(/[^a-z0-9_-]+/gi, "-").replace(/^-|-$/g, "") || "action";
    try {
      if (spec.url) await page.goto(spec.url, { waitUntil: "domcontentloaded" });
      const beforeTree = typeof page.ariaSnapshot === "function" ? await page.ariaSnapshot() : null;
      const beforeFile = path.join(ariaDir, `${cfg.label}-action-${safeLabel}-before.aria.yml`);
      if (beforeTree != null) fs.writeFileSync(beforeFile, beforeTree);
      await page.evaluate(() => {
        const state = { messages: [], events: [], loaf: [], observers: [], startedAt: performance.now() };
        const add = (el) => {
          if (!el || el.nodeType !== 1) return;
          const live = el.matches('[aria-live],[role="alert"],[role="status"]')
            ? el : el.closest('[aria-live],[role="alert"],[role="status"]');
          const nodes = [];
          if (live) nodes.push(live);
          if (el.querySelectorAll) nodes.push(...el.querySelectorAll('[aria-live],[role="alert"],[role="status"]'));
          for (const node of nodes) {
            const text = (node.innerText || node.textContent || "").replace(/\s+/g, " ").trim();
            if (text && !state.messages.some((m) => m.text === text)) {
              state.messages.push({ text: text.slice(0, 300), role: node.getAttribute("role"),
                                    ariaLive: node.getAttribute("aria-live") });
            }
          }
        };
        const mo = new MutationObserver((records) => {
          for (const record of records) {
            add(record.target.nodeType === 1 ? record.target : record.target.parentElement);
            for (const node of record.addedNodes || []) add(node.nodeType === 1 ? node : node.parentElement);
          }
        });
        mo.observe(document.body, { subtree: true, childList: true, characterData: true });
        state.observers.push(mo);
        for (const type of ["event", "long-animation-frame"]) {
          try {
            const po = new PerformanceObserver((list) => {
              for (const e of list.getEntries()) {
                if (e.startTime + e.duration < state.startedAt) continue;
                const item = { name: e.name, duration: Math.round(e.duration * 10) / 10,
                               startTime: Math.round(e.startTime * 10) / 10 };
                if (type === "event") state.events.push(item); else state.loaf.push(item);
              }
            });
            po.observe(type === "event" ? { type, buffered: true, durationThreshold: 16 }
                                         : { type, buffered: true });
            state.observers.push(po);
          } catch (e) { /* unsupported is represented by an empty list */ }
        }
        window.__ddBehaviorObservation = state;
      });
      const activeBefore = await page.evaluate(() => document.activeElement &&
        (document.activeElement.id || document.activeElement.tagName));
      if (spec.click) await page.click(spec.click, { timeout: 5000 });
      else if (spec.press && typeof spec.press === "object") {
        await page.locator(spec.press.selector).press(spec.press.key);
      } else if (spec.fill && typeof spec.fill === "object") {
        await page.locator(spec.fill.selector).fill(String(spec.fill.value || ""));
      } else throw new Error("announcement needs click, press, or fill");
      await page.waitForTimeout(spec.wait == null ? 500 : spec.wait);
      const observed = await page.evaluate(() => {
        const state = window.__ddBehaviorObservation || { messages: [], events: [], loaf: [], observers: [] };
        for (const observer of state.observers || []) { try { observer.disconnect(); } catch (e) {} }
        const out = { messages: state.messages || [], events: state.events || [], loaf: state.loaf || [] };
        delete window.__ddBehaviorObservation;
        return out;
      });
      const afterTree = typeof page.ariaSnapshot === "function" ? await page.ariaSnapshot() : null;
      const afterFile = path.join(ariaDir, `${cfg.label}-action-${safeLabel}-after.aria.yml`);
      if (afterTree != null) fs.writeFileSync(afterFile, afterTree);
      const activeAfter = await page.evaluate(() => document.activeElement &&
        (document.activeElement.id || document.activeElement.tagName));
      let expectedMatched = true, expectedError = null;
      if (spec.expected) {
        try {
          const re = new RegExp(spec.expected, "i");
          expectedMatched = observed.messages.some((m) => re.test(m.text));
        } catch (e) { expectedMatched = false; expectedError = "invalid expected regex: " + String(e).slice(0, 100); }
      }
      const maxEvent = observed.events.reduce((m, e) => Math.max(m, e.duration || 0), 0);
      const maxLoaf = observed.loaf.reduce((m, e) => Math.max(m, e.duration || 0), 0);
      announcementResults.push({
        label: spec.label, status: observed.messages.length && expectedMatched ? "verified" : "failed",
        messages: observed.messages, expected: spec.expected || null, expectedMatched, expectedError,
        focusMoved: activeBefore !== activeAfter, activeBefore, activeAfter,
        eventTiming: { supported: observed.events.length > 0, maxDuration: maxEvent, entries: observed.events.slice(-10) },
        longAnimationFrames: { supported: observed.loaf.length > 0, count: observed.loaf.length,
                               maxDuration: maxLoaf, entries: observed.loaf.slice(-10) },
        ariaBefore: beforeTree == null ? null : beforeFile,
        ariaAfter: afterTree == null ? null : afterFile,
      });
    } catch (e) {
      await page.evaluate(() => {
        const state = window.__ddBehaviorObservation;
        for (const observer of (state && state.observers) || []) { try { observer.disconnect(); } catch (err) {} }
        delete window.__ddBehaviorObservation;
      }).catch(() => {});
      announcementResults.push({ label: spec.label, status: "unreachable", reason: String(e).slice(0, 220) });
    }
  }

  // ---- configured APG composite-widget contracts -----------------------
  const widgetResults = [];
  const widgetRoles = {
    tablist: { item: '[role="tab"]', forward: "ArrowRight", reverse: "ArrowLeft" },
    radiogroup: { item: '[role="radio"]', forward: "ArrowRight", reverse: "ArrowLeft" },
    menu: { item: '[role="menuitem"],[role="menuitemcheckbox"],[role="menuitemradio"]', forward: "ArrowDown", reverse: "ArrowUp" },
    listbox: { item: '[role="option"]', forward: "ArrowDown", reverse: "ArrowUp", containerFocus: true },
    tree: { item: '[role="treeitem"]', forward: "ArrowDown", reverse: "ArrowUp" },
    toolbar: { item: 'button,[role="button"],[role="checkbox"],[role="radio"]', forward: "ArrowRight", reverse: "ArrowLeft" },
  };
  for (const spec of Array.isArray(cfg.widgets) ? cfg.widgets : []) {
    if (!spec || !spec.label) continue;
    try {
      if (spec.url) await page.goto(spec.url, { waitUntil: "domcontentloaded" });
      const opener = spec.open ? page.locator(spec.open).first() : null;
      if (opener) await opener.click({ timeout: 5000 });
      if (spec.kind === "dialog") {
        const dialog = page.locator(spec.selector).first();
        if (await dialog.count() < 1 || !(await dialog.isVisible())) throw new Error(`dialog not visible: ${spec.selector}`);
        const focusInsideAtOpen = await dialog.evaluate((root) => root.contains(document.activeElement));
        const focusables = dialog.locator('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])');
        const focusableCount = await focusables.count();
        let escaped = false;
        for (let i = 0; i < Math.max(2, focusableCount + 1); i++) {
          await page.keyboard.press("Tab");
          if (!(await dialog.evaluate((root) => root.contains(document.activeElement)))) { escaped = true; break; }
        }
        await page.keyboard.press("Escape"); await page.waitForTimeout(60);
        const closed = await dialog.count() === 0 || !(await dialog.isVisible());
        const restored = opener ? await opener.evaluate((el) => el === document.activeElement) : null;
        widgetResults.push({ label: spec.label, kind: "dialog", selector: spec.selector,
                             status: focusInsideAtOpen && !escaped && closed && (restored !== false) ? "verified" : "failed",
                             focusInsideAtOpen, focusableCount, focusEscaped: escaped, escapeClosed: closed,
                             focusRestored: restored });
        continue;
      }
      const contract = widgetRoles[spec.kind];
      if (!contract) throw new Error(`unsupported widget kind '${spec.kind}'`);
      const container = page.locator(spec.selector).first();
      if (await container.count() < 1) throw new Error(`widget not found: ${spec.selector}`);
      const items = container.locator(contract.item);
      const count = await items.count();
      if (count < 2) throw new Error(`widget needs >=2 ${contract.item} items (found ${count})`);
      const fingerprint = () => container.evaluate((root) => {
        const active = document.activeElement;
        const all = Array.from(root.querySelectorAll('[role],button,[tabindex]'));
        return JSON.stringify({
          active: all.findIndex((el) => el === active || el.contains(active)),
          activeDescendant: root.getAttribute("aria-activedescendant"),
          states: all.map((el) => [el.getAttribute("aria-selected"), el.getAttribute("aria-checked"), el.tabIndex]),
        });
      });
      if (contract.containerFocus) await container.focus(); else await items.first().focus();
      const before = await fingerprint();
      const keyTarget = contract.containerFocus ? container : items.first();
      await keyTarget.press(contract.forward);
      await page.waitForTimeout(40);
      const forward = await fingerprint();
      const current = page.locator(":focus");
      await current.press(contract.reverse);
      await page.waitForTimeout(40);
      const reverse = await fingerprint();
      widgetResults.push({ label: spec.label, kind: spec.kind, selector: spec.selector,
                           status: before !== forward && forward !== reverse ? "verified" : "failed",
                           itemCount: count, forwardKey: contract.forward, reverseKey: contract.reverse,
                           forwardChanged: before !== forward, reverseChanged: forward !== reverse });
    } catch (e) {
      widgetResults.push({ label: spec.label, kind: spec.kind, selector: spec.selector,
                           status: "unreachable", reason: String(e).slice(0, 220) });
    }
  }

  // ---- accessible authentication, dragging, and redundant entry --------
  const authResults = [];
  for (const spec of Array.isArray(cfg.authChecks) ? cfg.authChecks : []) {
    if (!spec || !spec.label || !spec.selector) continue;
    try {
      if (spec.url) await page.goto(spec.url, { waitUntil: "domcontentloaded" });
      const field = page.locator(spec.selector).first();
      if (await field.count() < 1) throw new Error(`authentication field not found: ${spec.selector}`);
      const facts = await field.evaluate((el, expected) => {
        const event = typeof ClipboardEvent === "function"
          ? new ClipboardEvent("paste", { bubbles: true, cancelable: true })
          : new Event("paste", { bubbles: true, cancelable: true });
        const dispatched = el.dispatchEvent(event);
        const tokens = (el.getAttribute("autocomplete") || "").toLowerCase().split(/\s+/);
        return { pasteAllowed: dispatched && !event.defaultPrevented,
                 autocomplete: el.getAttribute("autocomplete"),
                 expectedPresent: !expected || tokens.includes(expected.toLowerCase()) };
      }, spec.expectedAutocomplete || null);
      authResults.push({ label: spec.label, selector: spec.selector,
                         status: facts.pasteAllowed && facts.expectedPresent ? "verified" : "failed", ...facts });
    } catch (e) {
      authResults.push({ label: spec.label, selector: spec.selector,
                         status: "unreachable", reason: String(e).slice(0, 220) });
    }
  }

  const dragResults = [];
  for (const spec of Array.isArray(cfg.dragAlternatives) ? cfg.dragAlternatives : []) {
    if (!spec || !spec.label || !spec.dragSelector) continue;
    try {
      if (spec.url) await page.goto(spec.url, { waitUntil: "domcontentloaded" });
      const drag = page.locator(spec.dragSelector).first();
      if (await drag.count() < 1 || !(await drag.isVisible())) throw new Error(`drag target not visible: ${spec.dragSelector}`);
      const alt = spec.alternativeSelector ? page.locator(spec.alternativeSelector).first() : null;
      const alternativePresent = !!alt && await alt.count() > 0 && await alt.isVisible() && await alt.isEnabled();
      const alternativeKeyboardReachable = alternativePresent && await alt.evaluate((el) =>
        el.matches('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])'));
      dragResults.push({ label: spec.label, dragSelector: spec.dragSelector,
                         alternativeSelector: spec.alternativeSelector || null,
                         status: alternativePresent && alternativeKeyboardReachable ? "verified" : "failed",
                         alternativePresent, alternativeKeyboardReachable,
                         equivalence: "declared-by-config; confirm the alternative produces the same result" });
    } catch (e) {
      dragResults.push({ label: spec.label, status: "unreachable", reason: String(e).slice(0, 220) });
    }
  }

  const redundantResults = [];
  for (const spec of Array.isArray(cfg.redundantEntries) ? cfg.redundantEntries : []) {
    if (!spec || !spec.label || !spec.firstSelector || !spec.advance) continue;
    try {
      if (spec.url) await page.goto(spec.url, { waitUntil: "domcontentloaded" });
      const value = String(spec.value == null ? "designer-dude-test-value" : spec.value);
      await page.locator(spec.firstSelector).fill(value);
      await page.click(spec.advance, { timeout: 5000 });
      await page.waitForTimeout(spec.wait == null ? 200 : spec.wait);
      let autoPopulated = false, selectable = false;
      if (spec.secondSelector) {
        const second = page.locator(spec.secondSelector).first();
        if (await second.count()) autoPopulated = (await second.inputValue().catch(() => "")) === value;
      }
      if (spec.availableSelector) {
        const available = page.locator(spec.availableSelector).first();
        if (await available.count() && await available.isVisible()) {
          selectable = (await available.textContent() || "").includes(value) ||
                       (await available.getAttribute("value")) === value;
        }
      }
      redundantResults.push({ label: spec.label, status: autoPopulated || selectable ? "verified" : "failed",
                              autoPopulated, selectable, secondSelector: spec.secondSelector || null,
                              availableSelector: spec.availableSelector || null });
    } catch (e) {
      redundantResults.push({ label: spec.label, status: "unreachable", reason: String(e).slice(0, 220) });
    }
  }

  await setTouch(false);   // never leave the shared browser in touch mode

  const outFile = path.join(cfg.outDir, `probe-${cfg.label}.json`);
  fs.mkdirSync(cfg.outDir, { recursive: true });
  fs.writeFileSync(outFile, JSON.stringify({
    label: cfg.label,
    url: cfg.url || page.url(),
    probedAt: new Date().toISOString(),
    probeSource: probePath,
    performance: performanceData,
    consoleErrors,
    failedRequests,
    // What was actually exercised. probe-report.py reads this to tell an
    // override that PASSED from one that never ran -- the difference between
    // "no forced-colors defects" and "forced-colors not checked".
    overridePasses: overrides,
    statePasses: stateResults,
    behavioralEvidence: { announcements: announcementResults, widgets: widgetResults,
                          authentication: authResults, dragAlternatives: dragResults,
                          redundantEntries: redundantResults },
    visionDeficiencyPasses: visionResults,
    accessibilitySnapshots,
    screenshotStability,
    runs,
  }, null, 1));

  return [
    `probe written:  ${outFile}`,
    `screenshots:    ${shotDir}/${cfg.label}-*.png`,
    `ARIA trees:     ${cfg.ariaSnapshots === false ? "disabled" : ariaDir + "/" + cfg.label + "-*.aria.yml"}`,
    `url:            ${cfg.url || page.url()}`,
    `console errors: ${consoleErrors.length} · failed requests: ${failedRequests.length}`,
    `LAB perf: FCP=${performanceData.firstContentfulPaint}ms ` +
      `LCP=${performanceData.largestContentfulPaint}ms ` +
      `CLS=${performanceData.cumulativeLayoutShift} ` +
      `transfer=${Math.round((performanceData.transferBytes || 0) / 1024)}KB ` +
      `dom=${performanceData.domNodes}`,
    `overrides: ${overrides.length ? overrides.map((o) => `${o.pass}=${o.status}`).join(" · ") : "none run"}`,
    `states:    ${stateResults.length ? stateResults.map((s) => `${s.label}=${s.status}`).join(" · ") : "none configured"}`,
    `announces: ${announcementResults.length ? announcementResults.map((s) => `${s.label}=${s.status}`).join(" · ") : "none configured"}`,
    `widgets:   ${widgetResults.length ? widgetResults.map((s) => `${s.label}=${s.status}`).join(" · ") : "none configured"}`,
    `auth:      ${authResults.length ? authResults.map((s) => `${s.label}=${s.status}`).join(" · ") : "none configured"}`,
    `drag-alt:  ${dragResults.length ? dragResults.map((s) => `${s.label}=${s.status}`).join(" · ") : "none configured"}`,
    `redundant: ${redundantResults.length ? redundantResults.map((s) => `${s.label}=${s.status}`).join(" · ") : "none configured"}`,
    `vision:    ${visionResults.length ? visionResults.map((s) => `${s.kind}=${s.status}`).join(" · ") : "none configured"}`,
    "",
    ...summary,
    "",
    `Next: python3 ~/.claude/skills/designer-dude/scripts/probe-report.py ${outFile}`,
  ].join("\n");
}
