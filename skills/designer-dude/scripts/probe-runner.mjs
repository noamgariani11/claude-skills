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
 * It reads its config from a fixed absolute path (there is no way to pass
 * arguments through that tool), writes one JSON per viewport plus screenshots
 * to disk, and returns a ~15-line summary. Write the config first:
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
 *     "fullPage":  true
 *   }
 *
 * Runs in the CURRENT browser context, so an authenticated session
 * established by earlier browse steps carries over — which is the only way
 * to review the surfaces behind a login.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export default async function run(page) {
  const here = dirname(fileURLToPath(import.meta.url));
  const probeSrc = readFileSync(join(here, "probe.js"), "utf8");

  const cfgPath = join(homedir(), ".cache", "designer-dude", "probe-config.json");
  if (!existsSync(cfgPath)) {
    return `NO CONFIG. Write ${cfgPath} first — see the header of probe-runner.mjs.`;
  }
  const cfg = JSON.parse(readFileSync(cfgPath, "utf8"));
  if (!cfg.outDir || !cfg.label) return "CONFIG INVALID: outDir and label are required.";

  const viewports = cfg.viewports?.length ? cfg.viewports : [[1440, 900], [768, 1024], [390, 844]];
  const waitMs = cfg.waitMs ?? 700;
  const shotDir = join(cfg.outDir, "screenshots");
  mkdirSync(shotDir, { recursive: true });

  if (cfg.url) {
    await page.goto(cfg.url, { waitUntil: "domcontentloaded" });
  }

  const consoleErrors = [];
  const failedRequests = [];
  page.on("console", (m) => {
    if (m.type() === "error" && consoleErrors.length < 25) consoleErrors.push(m.text().slice(0, 300));
  });
  page.on("requestfailed", (r) => {
    if (failedRequests.length < 25) failedRequests.push(`${r.method()} ${r.url().slice(0, 160)} — ${r.failure()?.errorText ?? "?"}`);
  });

  // Performance facts the Interaction & Performance pillar asks for. Lab
  // numbers on one machine, NOT the p75 CrUX field data the budget is defined
  // against -- probe-report.py labels them that way so they are never quoted
  // as a Core Web Vitals result.
  async function perf() {
    return page.evaluate(() => {
      const nav = performance.getEntriesByType("navigation")[0];
      const lcpEntries = performance.getEntriesByType("largest-contentful-paint");
      const paints = {};
      performance.getEntriesByType("paint").forEach((p) => { paints[p.name] = Math.round(p.startTime); });
      let cls = 0;
      try {
        for (const e of performance.getEntriesByType("layout-shift")) if (!e.hadRecentInput) cls += e.value;
      } catch { /* not supported */ }
      const res = performance.getEntriesByType("resource");
      const bytes = res.reduce((a, r) => a + (r.transferSize || 0), 0);
      const byType = {};
      res.forEach((r) => {
        const t = r.initiatorType || "other";
        byType[t] = (byType[t] || 0) + (r.transferSize || 0);
      });
      return {
        note: "LAB measurement on one machine and one network. NOT p75 CrUX field data.",
        domContentLoaded: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
        loadEvent: nav ? Math.round(nav.loadEventEnd) : null,
        firstPaint: paints["first-paint"] ?? null,
        firstContentfulPaint: paints["first-contentful-paint"] ?? null,
        largestContentfulPaint: lcpEntries.length ? Math.round(lcpEntries[lcpEntries.length - 1].startTime) : null,
        cumulativeLayoutShift: Math.round(cls * 1000) / 1000,
        transferBytes: bytes,
        transferByInitiator: byType,
        requests: res.length,
        domNodes: document.querySelectorAll("*").length,
        stylesheets: document.styleSheets.length
      };
    });
  }

  const runs = [];
  const summary = [];

  async function probeOnce(tag, w, h) {
    await page.setViewportSize({ width: w, height: h });
    await page.waitForTimeout(waitMs);
    const shot = join(shotDir, `${cfg.label}-${tag}.png`);
    try {
      await page.screenshot({ path: shot, fullPage: !!cfg.fullPage });
    } catch { /* a fullPage shot on a very tall page can exceed limits */ }
    const data = await page.evaluate(
      ([src]) => {
        // eslint-disable-next-line no-new-func
        new Function(src)();
        return window.__ddProbe({});
      },
      [probeSrc]
    );
    data.tag = tag;
    data.screenshot = shot;
    runs.push(data);
    const c = data.color?.textContrast;
    const a = data.a11y;
    summary.push(
      `${tag.padEnd(16)} contrast-fails=${c?.failures ?? "?"}/${c?.checked ?? "?"} ` +
      `focus-invisible=${data.interaction?.focusRing?.invisible ?? "?"} ` +
      `tiny-targets=${data.interaction?.belowWcagTarget24?.count ?? "?"} ` +
      `no-pointer=${data.interaction?.missingPointerCursor?.count ?? "?"} ` +
      `no-label=${a?.fieldsMissingLabel?.count ?? "?"} ` +
      `no-alt=${a?.imagesMissingAlt?.count ?? "?"} ` +
      `h-overflow=${data.layout?.horizontalOverflow ?? "?"} ` +
      `radii=${data.system?.radius?.distinct ?? "?"} ` +
      `fonts=${data.typography?.distinctFamilies ?? "?"} ` +
      `accent=${data.color?.accentPixelShare ?? "?"}%` +
      (data.errors?.length ? ` ERRORS=${data.errors.length}` : "")
    );
  }

  for (const [w, h] of viewports) await probeOnce(`${w}x${h}`, w, h);

  const performance_ = await perf();

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

  const payload = {
    label: cfg.label,
    url: cfg.url || page.url(),
    probedAt: new Date().toISOString(),
    performance: performance_,
    consoleErrors,
    failedRequests,
    runs
  };
  const outFile = join(cfg.outDir, `probe-${cfg.label}.json`);
  mkdirSync(cfg.outDir, { recursive: true });
  writeFileSync(outFile, JSON.stringify(payload, null, 1));

  return [
    `probe written: ${outFile}`,
    `screenshots:   ${shotDir}/${cfg.label}-*.png`,
    `url:           ${payload.url}`,
    `console errors: ${consoleErrors.length} · failed requests: ${failedRequests.length}`,
    `LAB perf: FCP=${performance_.firstContentfulPaint}ms LCP=${performance_.largestContentfulPaint}ms CLS=${performance_.cumulativeLayoutShift} transfer=${Math.round((performance_.transferBytes || 0) / 1024)}KB dom=${performance_.domNodes}`,
    "",
    ...summary,
    "",
    `Next: python3 ~/.claude/skills/designer-dude/scripts/probe-report.py ${outFile}`
  ].join("\n");
}
