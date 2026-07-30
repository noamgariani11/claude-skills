/*
 * designer-dude probe runner — Playwright-side driver for probe.js.
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
 *     "viewports": [[1440,900],[1024,768],[768,1024],[390,844],[320,720]],
 *     "dark":      true,        // also probe with colorScheme: dark
 *     "reducedMotion": true,    // also probe with prefers-reduced-motion: reduce
 *     "waitMs":    700,
 *     "fullPage":  true,
 *     "skillDir":  "/abs/path/to/skills/designer-dude/scripts"  // optional override
 *   }
 *
 * Runs in the CURRENT browser context, so an authenticated session established
 * by earlier browse steps carries over — which is the only way to review the
 * surfaces behind a login. Use it against local dev and seeded test accounts;
 * on a page holding a REAL user's session, use browser_evaluate with a
 * `filename` instead (see mode-d-review.md).
 */
async (page) => {
  const fs = await import("node:fs");
  const os = await import("node:os");
  const path = await import("node:path");

  const cfgPath = path.join(os.homedir(), ".cache", "designer-dude", "probe-config.json");
  if (!fs.existsSync(cfgPath)) {
    return `NO CONFIG. Write ${cfgPath} first — see the header of probe-runner.mjs.`;
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

  const viewports = (cfg.viewports && cfg.viewports.length)
    ? cfg.viewports : [[1440, 900], [768, 1024], [390, 844]];
  const waitMs = cfg.waitMs == null ? 700 : cfg.waitMs;
  const shotDir = path.join(cfg.outDir, "screenshots");
  fs.mkdirSync(shotDir, { recursive: true });

  const consoleErrors = [];
  const failedRequests = [];
  page.on("console", (m) => {
    if (m.type() === "error" && consoleErrors.length < 25) consoleErrors.push(m.text().slice(0, 300));
  });
  page.on("requestfailed", (r) => {
    if (failedRequests.length < 25) {
      const f = r.failure();
      failedRequests.push(`${r.method()} ${r.url().slice(0, 160)} — ${f ? f.errorText : "?"}`);
    }
  });

  if (cfg.url) await page.goto(cfg.url, { waitUntil: "domcontentloaded" });

  // Performance facts for the Interaction & Performance pillar. LAB numbers on
  // one machine and one network -- NOT the p75 field data the budgets are
  // defined against. probe-report.py labels them so, and they must never be
  // quoted as a Core Web Vitals result.
  const perf = () => page.evaluate(() => {
    const nav = performance.getEntriesByType("navigation")[0];
    const lcpEntries = performance.getEntriesByType("largest-contentful-paint");
    const paints = {};
    performance.getEntriesByType("paint").forEach((p) => { paints[p.name] = Math.round(p.startTime); });
    let cls = 0;
    try {
      for (const e of performance.getEntriesByType("layout-shift")) if (!e.hadRecentInput) cls += e.value;
    } catch (err) { /* not supported */ }
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

  const probeOnce = async (tag, w, h) => {
    await page.setViewportSize({ width: w, height: h });
    await page.waitForTimeout(waitMs);
    const shot = path.join(shotDir, `${cfg.label}-${tag}.png`);
    try {
      await page.screenshot({ path: shot, fullPage: !!cfg.fullPage });
    } catch (e) { /* a very tall fullPage shot can exceed limits */ }
    const data = await page.evaluate(([src]) => {
      // eslint-disable-next-line no-new-func
      new Function(src)();
      return window.__ddProbe({});
    }, [probeSrc]);
    data.tag = tag;
    data.screenshot = shot;
    runs.push(data);
    const c = (data.color || {}).textContrast || {};
    const i = data.interaction || {};
    const a = data.a11y || {};
    summary.push(
      `${tag.padEnd(16)} contrast=${c.failures}/${c.checked} ` +
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

  const performanceData = await perf();

  if (cfg.dark) {
    await page.emulateMedia({ colorScheme: "dark" });
    await probeOnce("dark-1440x900", 1440, 900);
    await page.emulateMedia({ colorScheme: "light" });
  }
  if (cfg.reducedMotion) {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await probeOnce("reduced-motion", 1440, 900);
    await page.emulateMedia({ reducedMotion: "no-preference" });
  }

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
    runs,
  }, null, 1));

  return [
    `probe written:  ${outFile}`,
    `screenshots:    ${shotDir}/${cfg.label}-*.png`,
    `url:            ${cfg.url || page.url()}`,
    `console errors: ${consoleErrors.length} · failed requests: ${failedRequests.length}`,
    `LAB perf: FCP=${performanceData.firstContentfulPaint}ms ` +
      `LCP=${performanceData.largestContentfulPaint}ms ` +
      `CLS=${performanceData.cumulativeLayoutShift} ` +
      `transfer=${Math.round((performanceData.transferBytes || 0) / 1024)}KB ` +
      `dom=${performanceData.domNodes}`,
    "",
    ...summary,
    "",
    `Next: python3 ~/.claude/skills/designer-dude/scripts/probe-report.py ${outFile}`,
  ].join("\n");
}
