#!/usr/bin/env node
/*
 * Critical-surface evidence across Chromium, Firefox and WebKit.
 *
 * This is deliberately a CLI rather than another branch in probe-runner.mjs:
 * the MCP runner inherits an authenticated current Chromium page, while a
 * cross-engine run must launch isolated browser processes. Use storageState
 * for test accounts; never point it at a real user's live session.
 *
 *   node cross-engine.mjs --config .design/cross-engine-config.json
 *
 * Config:
 * {
 *   "outDir": "/abs/repo/.design", "label": "critical",
 *   "skillDir": "/abs/skills/designer-dude/scripts",
 *   "surfaces": [{"label":"dashboard","url":"http://localhost:3000/dashboard"}],
 *   "viewports": [[1440,900],[390,844]],
 *   "engines": ["chromium","firefox","webkit"],
 *   "storageState": "/abs/path/test-account-state.json",
 *   "waitMs": 500
 * }
 *
 * Pixel identity across engines is NOT expected. The output compares only
 * invariant failures (overflow, WCAG measurements, names, focus obstruction,
 * console errors) and stores screenshots + ARIA trees for review.
 */

import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const valueOf = (flag) => { const i = args.indexOf(flag); return i >= 0 ? args[i + 1] : null; };
const configPath = valueOf("--config");
const resolverSelftest = args.includes("--selftest-resolver");
const doctor = args.includes("--doctor");
if (!configPath && !resolverSelftest && !doctor) {
  console.error("usage: node cross-engine.mjs --config <cross-engine-config.json>");
  process.exit(2);
}

const resolvePlaywright = require(join(here, "playwright-resolve.cjs"));
const resolvedPlaywright = resolvePlaywright();
if (!resolvedPlaywright) {
  console.error("cross-engine: playwright/playwright-core not found");
  process.exit(3);
}
const pw = resolvedPlaywright.api;
if (resolverSelftest) {
  if (/-/.test(resolvedPlaywright.version)) {
    console.error(`cross-engine resolver selftest failed: selected prerelease ${resolvedPlaywright.version}`);
    process.exit(1);
  }
  console.log(`cross-engine resolver selftest ok - selected Playwright ${resolvedPlaywright.version}`);
  process.exit(0);
}
if (doctor) {
  const status = {};
  for (const name of ["chromium", "firefox", "webkit"]) {
    let browser;
    try {
      browser = await pw[name].launch({ headless: true });
      status[name] = { status: "ran", version: browser.version() };
    } catch (error) {
      status[name] = { status: "unavailable", reason: String(error).slice(0, 500) };
    } finally {
      if (browser) await browser.close().catch(() => {});
    }
  }
  const ok = Object.values(status).every((x) => x.status === "ran");
  console.log(JSON.stringify({ schema: "designer-dude-browser-doctor/v1",
    playwrightVersion: resolvedPlaywright.version, status: ok ? "pass" : "fail", engines: status }));
  process.exit(ok ? 0 : 1);
}

const cfg = JSON.parse(readFileSync(resolve(configPath), "utf8"));
if (!cfg.outDir || !cfg.label || !Array.isArray(cfg.surfaces) || !cfg.surfaces.length) {
  console.error("cross-engine: outDir, label and a non-empty surfaces array are required");
  process.exit(2);
}
const probePath = join(cfg.skillDir || here, "probe.js");
if (!existsSync(probePath)) {
  console.error(`cross-engine: probe.js not found at ${probePath}`);
  process.exit(2);
}
const probeSrc = readFileSync(probePath, "utf8");
const engines = cfg.engines || ["chromium", "firefox", "webkit"];
const viewports = cfg.viewports || [[1440, 900], [390, 844]];
const outRoot = resolve(cfg.outDir, "cross-engine", cfg.label);
mkdirSync(outRoot, { recursive: true });

const ariaRoot = (tree) => {
  const first = String(tree || "").split(/\r?\n/, 1)[0];
  if (!first.trim()) return { inTree: false, name: null };
  const quoted = first.match(/^\s*-\s+[^\s:]+\s+("(?:[^"\\]|\\.)*")/);
  if (quoted) { try { return { inTree: true, name: JSON.parse(quoted[1]) }; } catch { return { inTree: true, name: null }; } }
  const single = first.match(/^\s*-\s+[^\s:]+\s+'([^']*)'/);
  return { inTree: true, name: single ? single[1].replace(/''/g, "'") : "" };
};

const enrichBrowserNames = async (page, data) => {
  const a11y = data?.a11y;
  if (!a11y) return;
  const candidates = [
    ...((a11y.fieldsMissingLabel || {}).list || []).map((x) => ({ ...x, source: "field" })),
    ...((a11y.controlsMissingAccessibleName || {}).list || []).map((x) => ({ ...x, source: "control" })),
  ];
  const confirmed = [], dismissed = [], inconclusive = [];
  for (const item of candidates) {
    try {
      const loc = page.locator(item.locator || item.sel).first();
      if (await loc.count() < 1 || typeof loc.ariaSnapshot !== "function") {
        inconclusive.push({ ...item, reason: "locator unavailable" }); continue;
      }
      const root = ariaRoot(await loc.ariaSnapshot());
      if (!root.inTree) dismissed.push({ ...item, reason: "not in accessibility tree" });
      else if (root.name == null) inconclusive.push({ ...item, reason: "name unparseable" });
      else if (String(root.name).trim()) dismissed.push({ ...item, computedName: root.name });
      else confirmed.push({ ...item, computedName: "" });
    } catch (error) { inconclusive.push({ ...item, reason: String(error).slice(0, 120) }); }
  }
  a11y.browserMissingAccessibleName = { candidates: candidates.length,
    checked: confirmed.length + dismissed.length, failures: confirmed.length,
    list: confirmed, dismissed, inconclusive };
};

const metric = (data) => ({
  contrastFailures: data?.color?.textContrast?.failures ?? null,
  nonTextFailures: data?.color?.nonTextContrast?.fieldBorderFailures ?? null,
  horizontalOverflow: data?.layout?.horizontalOverflow ?? null,
  clippedContent: data?.layout?.clippedContent?.count ?? null,
  missingNames: data?.a11y?.browserMissingAccessibleName?.list?.filter((x) => x.source === "control").length ??
                data?.a11y?.controlsMissingAccessibleName?.count ?? null,
  missingLabels: data?.a11y?.browserMissingAccessibleName?.list?.filter((x) => x.source === "field").length ??
                 data?.a11y?.fieldsMissingLabel?.count ?? null,
  nameCheckInconclusive: data?.a11y?.browserMissingAccessibleName?.inconclusive?.length ?? null,
  labelInNameCandidates: data?.a11y?.labelInName?.count ?? null,
  focusInvisible: data?.interaction?.focusRing?.invisible ?? null,
  focusObscured: data?.interaction?.focusRing?.completelyObscured ?? null,
  probeErrors: data?.errors || [],
});

const results = [];
for (const engineName of engines) {
  const browserType = pw[engineName];
  if (!browserType) {
    results.push({ engine: engineName, status: "unavailable", reason: "unknown Playwright engine" });
    continue;
  }
  let browser;
  try {
    browser = await browserType.launch({ headless: true });
    for (const surface of cfg.surfaces) {
      if (!surface?.label || !surface?.url) {
        results.push({ engine: engineName, surface: surface?.label, status: "invalid-config" });
        continue;
      }
      for (const [width, height] of viewports) {
        const tag = `${surface.label}-${width}x${height}`;
        const dir = join(outRoot, engineName);
        mkdirSync(dir, { recursive: true });
        const errors = [];
        let context;
        try {
          context = await browser.newContext({
            viewport: { width, height },
            hasTouch: width <= (cfg.touchBelowPx ?? 500),
            storageState: cfg.storageState || undefined,
            reducedMotion: "reduce",
          });
          const page = await context.newPage();
          page.on("console", (msg) => { if (msg.type() === "error" && errors.length < 20) errors.push(msg.text()); });
          await page.goto(surface.url, { waitUntil: "domcontentloaded", timeout: cfg.timeoutMs || 30000 });
          await page.waitForTimeout(cfg.waitMs ?? 500);
          const shot = join(dir, `${tag}.png`);
          await page.screenshot({ path: shot, fullPage: cfg.fullPage !== false,
                                  animations: "disabled", caret: "hide" });
          const data = await page.evaluate(([src]) => {
            // eslint-disable-next-line no-new-func
            new Function(src)();
            return window.__ddProbe({});
          }, [probeSrc]);
          await enrichBrowserNames(page, data);
          const aria = join(dir, `${tag}.aria.yml`);
          let ariaStatus = "unavailable";
          try {
            if (typeof page.ariaSnapshot === "function") {
              writeFileSync(aria, await page.ariaSnapshot()); ariaStatus = "written";
            }
          } catch { /* recorded below */ }
          results.push({ engine: engineName, surface: surface.label, viewport: `${width}x${height}`,
                         status: "ran", screenshot: shot, ariaSnapshot: ariaStatus === "written" ? aria : null,
                         ariaStatus, consoleErrors: errors, metrics: metric(data) });
        } catch (error) {
          results.push({ engine: engineName, surface: surface.label, viewport: `${width}x${height}`,
                         status: "failed", reason: String(error).slice(0, 300), consoleErrors: errors });
        } finally {
          if (context) await context.close().catch(() => {});
        }
      }
    }
  } catch (error) {
    results.push({ engine: engineName, status: "unavailable", reason: String(error).slice(0, 300) });
  } finally {
    if (browser) await browser.close().catch(() => {});
  }
}

// Compare each non-Chromium result with the same Chromium surface/viewport.
// Only worsening invariant counts are candidates; rendering differences are
// preserved as artifacts and intentionally not converted into quality scores.
const regressions = [];
const base = new Map(results.filter((r) => r.engine === "chromium" && r.status === "ran")
  .map((r) => [`${r.surface}|${r.viewport}`, r]));
for (const row of results.filter((r) => r.engine !== "chromium" && r.status === "ran")) {
  const b = base.get(`${row.surface}|${row.viewport}`);
  if (!b) continue;
  for (const key of ["contrastFailures", "nonTextFailures", "clippedContent", "missingNames",
                     "missingLabels", "nameCheckInconclusive", "labelInNameCandidates",
                     "focusInvisible", "focusObscured"]) {
    if (typeof row.metrics[key] === "number" && typeof b.metrics[key] === "number" &&
        row.metrics[key] > b.metrics[key]) {
      regressions.push({ engine: row.engine, surface: row.surface, viewport: row.viewport,
                         metric: key, chromium: b.metrics[key], observed: row.metrics[key] });
    }
  }
  if (row.metrics.horizontalOverflow && !b.metrics.horizontalOverflow) {
    regressions.push({ engine: row.engine, surface: row.surface, viewport: row.viewport,
                       metric: "horizontalOverflow", chromium: false, observed: true });
  }
  if (row.consoleErrors.length > b.consoleErrors.length) {
    regressions.push({ engine: row.engine, surface: row.surface, viewport: row.viewport,
                       metric: "consoleErrors", chromium: b.consoleErrors.length,
                       observed: row.consoleErrors.length });
  }
}

const output = {
  schema: "designer-dude-cross-engine/v1", playwrightVersion: resolvedPlaywright.version,
  label: cfg.label, generatedAt: new Date().toISOString(), config: resolve(configPath),
  enginesRequested: engines, surfacesRequested: cfg.surfaces.map((s) => s.label),
  viewportsRequested: viewports.map(([w, h]) => `${w}x${h}`), results, regressions,
  interpretation: "Cross-engine invariant regressions are candidates. Pixel differences are review artifacts, not aesthetic scores.",
};
const outputPath = join(outRoot, "cross-engine.json");
writeFileSync(outputPath, JSON.stringify(output, null, 2));
const unavailable = results.filter((r) => r.status === "unavailable").map((r) => r.engine);
console.log(`cross-engine evidence: ${outputPath}`);
console.log(`runs: ${results.filter((r) => r.status === "ran").length} · regressions: ${regressions.length}`);
console.log(`unavailable: ${unavailable.length ? [...new Set(unavailable)].join(", ") : "none"}`);
process.exitCode = regressions.length || unavailable.length ? 1 : 0;
