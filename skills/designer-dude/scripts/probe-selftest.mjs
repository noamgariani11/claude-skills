/*
 * probe-selftest — prove probe.js still detects what it claims to detect.
 *
 * Loads fixtures/selftest.html (a page of enumerated, deliberate defects) in a
 * short-lived headless Chromium, runs the probe, and asserts every planted
 * defect is caught. A measurement tool nobody re-validates drifts into
 * confident silence: the check stops firing, the scorecard keeps printing A,
 * and the skill's whole value -- not flattering the work -- quietly inverts.
 *
 * Run it after ANY edit to probe.js:
 *   node ~/.claude/skills/designer-dude/scripts/probe-selftest.mjs
 *
 * This is the one place the skill launches its own browser rather than going
 * through Playwright MCP, and it is deliberate: it must work when the MCP
 * profile is locked by another session, it must be runnable in CI, and it
 * touches nothing but a local file:// fixture. It starts no dev server, uses
 * its own throwaway profile, and always closes the browser. Reviews still go
 * through MCP / the browse skill.
 */
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

function resolvePlaywright() {
  const candidates = ["playwright", "playwright-core"];
  for (const name of candidates) {
    try { return require(name); } catch { /* keep looking */ }
  }
  // Fall back to the copy the Playwright MCP server already brought along.
  const globs = [
    join(process.env.HOME || "", ".npm/_npx"),
  ];
  for (const root of globs) {
    try {
      const { readdirSync } = require("node:fs");
      for (const d of readdirSync(root)) {
        const p = join(root, d, "node_modules", "playwright-core");
        try { return require(p); } catch { /* next */ }
      }
    } catch { /* no npx cache */ }
  }
  return null;
}

const pw = resolvePlaywright();
if (!pw) {
  console.error("Could not resolve playwright or playwright-core. Install one, or run this from a project that has it.");
  process.exit(3);
}

const probeSrc = readFileSync(join(here, "probe.js"), "utf8");

// --url <u> probes a real page instead of the fixture and skips the
// assertions: a smoke test for "does the probe survive a real DOM", and the
// fallback path when the Playwright MCP browser profile is locked by another
// session. --out <file> writes the full JSON for probe-report.py.
const argv = process.argv.slice(2);
const argOf = (flag) => { const i = argv.indexOf(flag); return i >= 0 ? argv[i + 1] : null; };
const urlArg = argOf("--url");
const outArg = argOf("--out");
const precision = argv.includes("--precision");
const fixture = urlArg ||
  ("file://" + join(here, "fixtures", precision ? "clean.html" : "selftest.html"));

// Each entry: [id, description, predicate over the probe result].
const EXPECT = [
  ["D2",  "AA contrast failure detected",        (d) => d.color.textContrast.failures >= 2],
  ["D2b", "contrast failures carry a ratio",     (d) => d.color.textContrast.failureList.every((f) => typeof f.ratio === "number" && f.ratio > 0)],
  ["D2c", "APCA Lc reported alongside",          (d) => d.color.textContrast.failureList.some((f) => typeof f.apcaLc === "number")],
  ["D1",  "pure black/white text counted",       (d) => d.color.pureBlackOrWhiteText >= 1],
  ["D3",  "radius sprawl (>=6 distinct)",        (d) => d.system.radius.distinct >= 6],
  ["D4",  "off-4px spacing found",               (d) => d.system.spacing.offFourBaseCount >= 2],
  ["D5",  "invisible focus ring found",          (d) => d.interaction.focusRing.invisible >= 1],
  ["D5b", "focus ring test actually ran",        (d) => d.interaction.focusRing.tested >= 3],
  ["D6",  "clickable without pointer cursor",    (d) => d.interaction.missingPointerCursor.count >= 1],
  ["D7",  "blue->purple gradient detected",      (d) => d.slop.purpleOrIndigoGradients >= 1],
  ["D7b", "gradient-clipped text detected",      (d) => d.slop.gradientClippedText >= 1],
  ["D8",  "glassmorphism counted",               (d) => d.slop.backdropBlurElements >= 3],
  ["D9",  "three-up feature grid detected",      (d) => d.slop.threeUpFeatureGrids >= 1],
  ["D9b", "icons in coloured circles",           (d) => d.slop.iconsInColouredCircles >= 3],
  ["D10", "coloured left-border card",           (d) => d.slop.colouredLeftBorderCards >= 1],
  ["D11", "infinite animation found",            (d) => d.motion.infiniteAnimations.count >= 1],
  ["D11b","transition over 600ms found",         (d) => d.motion.transitionsOver600ms.length >= 1],
  ["D12", "target below WCAG 24px",              (d) => d.interaction.belowWcagTarget24.count >= 1],
  ["D13", "measure out of 45-78ch band",         (d) => d.typography.offenders.measureOutOfBand.length >= 1],
  ["D13b","leading out of band",                 (d) => d.typography.offenders.leadingOutOfBand.length >= 1],
  ["D14", "field border below 3:1",              (d) => d.color.nonTextContrast.fieldBorderFailures >= 1],
  ["D15", "centred-text share computed",         (d) => d.slop.centredShare >= 20],
  ["D16", "z-index sprawl",                      (d) => d.system.zIndex.distinct >= 6],
  ["D17", "skipped heading level",               (d) => d.a11y.headings.skippedLevels.length >= 1],
  ["D18", "field missing a label",               (d) => d.a11y.fieldsMissingLabel.count >= 1],
  ["D19", "image missing alt",                   (d) => d.a11y.imagesMissingAlt.count >= 1],
  ["D20", "control with no accessible name",     (d) => d.a11y.controlsMissingAccessibleName.count >= 1],
  ["D21", "duplicate ids",                       (d) => d.a11y.duplicateIds.count >= 1],
  ["D22", "aria-hidden wrapping focusable",      (d) => d.a11y.ariaHiddenContainingFocusable >= 1],
  ["D23", "positive tabindex",                   (d) => d.a11y.positiveTabindex >= 1],
  ["D24", "horizontal overflow",                 (d) => d.layout.horizontalOverflow === true],
  ["D25", "table without scope/caption",         (d) => d.app.tables.length >= 1 && d.app.tables[0].hasScope === false],
  ["D25b","numeric cells counted in table",      (d) => d.app.tables[0].numericCells >= 2],
  ["G1",  "generic marketing copy caught",       (d) => d.slop.genericMarketingCopy.length >= 3],
  ["G2",  "AI badge copy caught",                (d) => d.slop.aiBadgeCopy.length >= 1],
  ["G3",  "emoji in heading/button caught",      (d) => d.slop.emojiInHeadingsOrButtons.count >= 1],
  ["T1",  "type scale ratios computed",          (d) => Array.isArray(d.typography.adjacentRatios) && d.typography.adjacentRatios.length >= 2],
  ["T2",  "families counted",                    (d) => d.typography.distinctFamilies >= 1],
  ["T3",  "measure median computed",             (d) => d.typography.measureCh && d.typography.measureCh.median > 0],
  ["S1",  "no probe section errored",            (d) => d.errors.length === 0],
];

// --precision runs the OTHER fixture: fixtures/clean.html, a page built out of
// constructs that are correct, deliberate, or explicitly exempt. Every entry
// here is a false positive that once cost a real review round -- a reviewer
// re-measuring twenty small buttons by hand, or arguing `transition: all` in a
// ledger. Recall and precision are different properties and only one of them
// was ever tested; a check that fires on everything is not a check.
const REJECT = [
  ["C1",  "UA-default head elements are not pure-black TEXT", (d) => d.color.pureBlackOrWhiteText === 0],
  ["C2",  "no contrast failures on a passing palette",        (d) => d.color.textContrast.failures === 0],
  ["C3",  "field borders at 3:1 are not flagged",             (d) => d.color.nonTextContrast.fieldBorderFailures === 0],
  ["C4",  "2.5.8: isolated sub-24px target is NOT a failure",  (d) => d.interaction.belowWcagTarget24.count === 0],
  ["C5",  "...and the spacing exception was actually applied", (d) => d.interaction.target24SpacingExempt.count >= 1],
  ["C6",  "no 24-44px targets invented",                      (d) => d.interaction.belowFittsTarget44.count === 0],
  ["C6b", "sr-only skip link is not a 1x1 tap target",        (d) => !JSON.stringify(d.interaction.belowWcagTarget24.list || [])
                                                                        .includes("skip") &&
                                                                     !JSON.stringify(d.interaction.target24SpacingExempt.list || [])
                                                                        .includes("skip")],
  ["C7",  "disabled control is not a missing-pointer finding", (d) => d.interaction.missingPointerCursor.count === 0],
  ["C8",  "a real focus ring is seen",                        (d) => d.interaction.focusRing.invisible === 0],
  ["C9",  "half-steps + computed margins are not off-base",   (d) => d.system.spacing.offFourBaseCount === 0],
  ["C10", "`transition: all` initial value is not counted",   (d) => d.motion.transitionPropertyAll === 0],
  ["C11", "no infinite animations invented",                  (d) => d.motion.infiniteAnimations.count === 0],
  ["C12", "no over-600ms transitions invented",               (d) => d.motion.transitionsOver600ms.length === 0],
  ["C13", "labelled fields are not unlabelled",               (d) => d.a11y.fieldsMissingLabel.count === 0],
  ["C14", "alt-bearing and decorative images pass",           (d) => d.a11y.imagesMissingAlt.count === 0],
  ["C15", "aria-label counts as an accessible name",          (d) => d.a11y.controlsMissingAccessibleName.count === 0],
  ["C16", "no duplicate ids invented",                        (d) => d.a11y.duplicateIds.count === 0],
  ["C17", "sequential headings are not skips",                (d) => d.a11y.headings.skippedLevels.length === 0],
  ["C18", "aria-hidden on a leaf svg is fine",                (d) => d.a11y.ariaHiddenContainingFocusable === 0],
  ["C19", "exactly one h1 is seen",                           (d) => d.a11y.headings.h1 === 1],
  ["C20", "no horizontal overflow",                           (d) => d.layout.horizontalOverflow === false],
  ["C21", "measure inside the band",                          (d) => d.typography.offenders.measureOutOfBand.length === 0],
  ["C22", "leading inside the band",                          (d) => d.typography.offenders.leadingOutOfBand.length === 0],
  ["C23", "typographic apostrophes are not straight ones",    (d) => d.typography.straightQuotes.apostrophes === 0 &&
                                                                     d.typography.straightQuotes.properApostrophes >= 1],
  ["C24", "no slop tells on a plain page",                    (d) => d.slop.purpleOrIndigoGradients === 0 &&
                                                                     d.slop.backdropBlurElements === 0 &&
                                                                     d.slop.iconsInColouredCircles === 0 &&
                                                                     d.slop.threeUpFeatureGrids === 0 &&
                                                                     d.slop.colouredLeftBorderCards === 0 &&
                                                                     d.slop.gradientClippedText === 0],
  ["C25", "no generic marketing copy invented",               (d) => d.slop.genericMarketingCopy.length === 0 &&
                                                                     d.slop.aiBadgeCopy.length === 0 &&
                                                                     d.slop.emojiInHeadingsOrButtons.count === 0],
  ["C26", "table with scope + caption passes",                (d) => d.app.tables.length >= 1 && d.app.tables[0].hasScope === true],
  ["C27", "scales are read as scales, not sprawl",            (d) => d.system.radius.distinct <= 4 &&
                                                                     d.system.shadow.distinct <= 4 &&
                                                                     d.system.zIndex.distinct <= 6],
  ["C28", "no probe section errored",                         (d) => d.errors.length === 0],
];

const profile = mkdtempSync(join(tmpdir(), "dd-selftest-"));
let browser;
try {
  // launch() (not launchPersistentContext) so this never contends with the
  // Playwright MCP server's profile lock — the selftest must run even while
  // another session is holding the shared browser.
  browser = await pw.chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  // --runner exercises probe-runner.mjs the way the MCP tool does: evaluate the
  // file to a function and hand it a page. Worth having as a real test, because
  // the runner is the one component whose contract with the harness cannot be
  // verified from here -- and an unexercised runner is where a whole review
  // silently fails to collect any evidence.
  if (argv.includes("--runner")) {
    const { readFileSync: rf, writeFileSync: wf, mkdirSync: mk, existsSync: ex, rmSync: rms } =
      await import("node:fs");
    const { homedir } = await import("node:os");
    const cfgDir = join(homedir(), ".cache", "designer-dude");
    const cfgPath = join(cfgDir, "probe-config.json");
    mk(cfgDir, { recursive: true });
    const had = ex(cfgPath) ? rf(cfgPath, "utf8") : null;   // never clobber a real config
    const outDir = join(profile, "design");
    try {
      wf(cfgPath, JSON.stringify({
        outDir, label: "fixture", url: fixture,
        viewports: [[1440, 900], [390, 844]],
        dark: true, reducedMotion: true, waitMs: 200, fullPage: false,
        skillDir: here,
      }));
      const src = rf(join(here, "probe-runner.mjs"), "utf8");
      // Same shape the harness uses: the file is a bare async (page) => {...}
      const fn = new Function("return (" + src + ")")();
      if (typeof fn !== "function") throw new Error("probe-runner.mjs did not evaluate to a function");
      const outText = await fn(page);
      console.log(outText);
      const jsonPath = join(outDir, "probe-fixture.json");
      const ok = ex(jsonPath) && ex(join(outDir, "screenshots", "fixture-1440x900.png"));
      const parsed = ok ? JSON.parse(rf(jsonPath, "utf8")) : null;
      const runCount = parsed ? parsed.runs.length : 0;
      console.log(`\nrunner check: json=${ex(jsonPath)} screenshots=${ex(join(outDir, "screenshots", "fixture-1440x900.png"))} runs=${runCount} (expect 4)`);
      if (!ok || runCount !== 4) {
        console.log("RUNNER CHECK FAILED");
        process.exitCode = 1;
      } else {
        console.log("runner check ok");
      }
    } finally {
      if (had === null) { try { rms(cfgPath); } catch { /* ignore */ } }
      else wf(cfgPath, had);
    }
    await browser.close();
    process.exit(process.exitCode || 0);
  }
  await page.goto(fixture, { waitUntil: "load" });
  await page.waitForTimeout(300);

  // ---- precision pass: the clean fixture must yield no findings at all ----
  if (precision) {
    const runProbe = async (tag) => {
      await page.waitForTimeout(150);
      const d = await page.evaluate(([src]) => {
        // eslint-disable-next-line no-new-func
        new Function(src)();
        return window.__ddProbe({});
      }, [probeSrc]);
      d.tag = tag;
      return d;
    };
    const runs = [];
    await page.setViewportSize({ width: 1440, height: 900 });
    const primary = await runProbe("1440x900");
    runs.push(primary);
    await page.setViewportSize({ width: 390, height: 844 });
    runs.push(await runProbe("390x844"));
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.emulateMedia({ colorScheme: "dark" });
    runs.push(await runProbe("dark-1440x900"));
    await page.emulateMedia({ colorScheme: "light", reducedMotion: "reduce" });
    runs.push(await runProbe("reduced-motion"));
    await page.emulateMedia({ reducedMotion: "no-preference" });

    let pass = 0;
    const missed = [];
    for (const [id, desc, pred] of REJECT) {
      let ok = false, err = "";
      try { ok = !!pred(primary); } catch (e) { err = " (threw: " + e.message + ")"; }
      if (ok) pass++; else missed.push(`  ${id.padEnd(5)} ${desc}${err}`);
    }
    console.log(`probe-selftest --precision: ${pass}/${REJECT.length} correct constructs left alone`);
    if (missed.length) {
      console.log("FALSE POSITIVES (the probe flagged something that is fine):");
      missed.forEach((m) => console.log(m));
      process.exitCode = 1;
    }

    // The thresholds live in probe-report.py, so precision has to be tested
    // there too: a probe that measures honestly and a threshold that fires at
    // the wrong value produce the same wasted round.
    const { writeFileSync } = await import("node:fs");
    const payloadPath = join(profile, "probe-clean.json");
    writeFileSync(payloadPath, JSON.stringify({
      label: "clean-fixture", url: fixture, probedAt: new Date().toISOString(),
      consoleErrors: [], runs,
    }, null, 1));
    if (outArg) writeFileSync(outArg, readFileSync(payloadPath, "utf8"));

    const { spawnSync } = await import("node:child_process");
    const rep = spawnSync("python3", [join(here, "probe-report.py"), payloadPath, "--quiet"],
                          { encoding: "utf8" });
    const out = (rep.stdout || "") + (rep.stderr || "");
    const m = out.match(/^(\d+) candidates/m);
    const n = m ? Number(m[1]) : (/No threshold breaches/.test(out) ? 0 : -1);
    console.log(`probe-report on the clean fixture: ${n < 0 ? "could not parse output" : n + " candidates"}`);
    if (n !== 0) {
      console.log(out);
      console.log("THRESHOLD FALSE POSITIVES — a correct page must score clean.");
      process.exitCode = 1;
    } else if (!missed.length) {
      console.log("clean fixture is clean — probe.js and probe-report.py are not inventing work");
    }
    await browser.close();
    process.exit(process.exitCode || 0);
  }

  const data = await page.evaluate(([src]) => {
    // eslint-disable-next-line no-new-func
    new Function(src)();
    return window.__ddProbe({});
  }, [probeSrc]);

  if (argv.includes("--dump")) console.log(JSON.stringify(data, null, 1));
  if (outArg) {
    const { writeFileSync } = await import("node:fs");
    writeFileSync(outArg, JSON.stringify({
      label: urlArg ? new URL(urlArg).hostname : "fixture",
      url: fixture, probedAt: new Date().toISOString(),
      runs: [Object.assign({ tag: "1440x900" }, data)]
    }, null, 1));
    console.log("wrote " + outArg);
  }

  if (urlArg) {
    const c = data.color.textContrast, i = data.interaction, a = data.a11y;
    console.log(`smoke probe of ${urlArg}`);
    console.log(`  contrast: ${c.failures} fail / ${c.checked} checked (${c.skippedImageBackdrop} skipped: image backdrop)`);
    console.log(`  focus ring invisible: ${i.focusRing.invisible}/${i.focusRing.tested} tested`);
    console.log(`  no pointer: ${i.missingPointerCursor.count} · <24px targets: ${i.belowWcagTarget24.count}`);
    console.log(`  a11y: no-alt=${a.imagesMissingAlt.count} no-label=${a.fieldsMissingLabel.count} no-name=${a.controlsMissingAccessibleName.count} h1=${a.headings.h1} skips=${a.headings.skippedLevels.length}`);
    console.log(`  system: radii=${data.system.radius.distinct} shadows=${data.system.shadow.distinct} spacing=${data.system.spacing.distinct} off4=${data.system.spacing.offFourBaseCount} z=${data.system.zIndex.distinct}`);
    console.log(`  type: families=${data.typography.distinctFamilies} sizes=${data.typography.distinctSizes} measure(median)=${data.typography.measureCh?.median}`);
    console.log(`  colour: accent=${data.color.accentPixelShare}% textColors=${data.color.distinctTextColors} gradients=${data.color.gradients.count}`);
    console.log(`  slop: purpleGrad=${data.slop.purpleOrIndigoGradients} glass=${data.slop.backdropBlurElements} iconCircles=${data.slop.iconsInColouredCircles} centred=${data.slop.centredShare}% generic=${data.slop.genericMarketingCopy.length}`);
    console.log(`  errors: ${data.errors.length ? data.errors.join(" | ") : "none"}`);
    process.exit(data.errors.length ? 1 : 0);
  }

  let pass = 0;
  const failed = [];
  for (const [id, desc, pred] of EXPECT) {
    let ok = false, err = "";
    try { ok = !!pred(data); } catch (e) { err = " (threw: " + e.message + ")"; }
    if (ok) { pass++; } else { failed.push(`  ${id.padEnd(5)} ${desc}${err}`); }
  }

  console.log(`probe-selftest: ${pass}/${EXPECT.length} planted defects detected`);
  if (data.errors.length) {
    console.log("probe reported internal errors:");
    data.errors.forEach((e) => console.log("  ! " + e));
  }
  if (failed.length) {
    console.log("MISSED:");
    failed.forEach((f) => console.log(f));
    process.exitCode = 1;
  } else {
    console.log("all planted defects detected — probe.js is behaving");
  }
} catch (e) {
  console.error("selftest could not run: " + (e && e.stack ? e.stack : e));
  process.exitCode = 3;
} finally {
  if (browser) await browser.close();
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* best effort */ }
}
