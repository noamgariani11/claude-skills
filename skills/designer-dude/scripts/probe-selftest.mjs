/*
 * probe-selftest - prove probe.js still detects what it claims to detect.
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
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

const resolvedPlaywright = require(join(here, "playwright-resolve.cjs"))();
if (!resolvedPlaywright) {
  console.error("Could not resolve playwright or playwright-core. Install one, or run this from a project that has it.");
  process.exit(3);
}
const pw = resolvedPlaywright.api;

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
const mutations = argv.includes("--mutations");
const pipeline = argv.includes("--pipeline");
const fixture = urlArg ||
  ("file://" + join(here, "fixtures", (precision || mutations || pipeline) ? "clean.html" : "selftest.html"));

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
  ["D25", "ambiguous table lacks header associations", (d) => d.app.tables.length >= 1 &&
                                                               d.app.tables[0].needsHeaderAssociations === true &&
                                                               d.app.tables[0].hasHeaderAssociations === false],
  ["D25b","numeric cells counted in table",      (d) => d.app.tables[0].numericCells >= 2],
  ["G1",  "generic marketing copy caught",       (d) => d.slop.genericMarketingCopy.length >= 3],
  ["G2",  "AI badge copy caught",                (d) => d.slop.aiBadgeCopy.length >= 1],
  ["G3",  "emoji in heading/button caught",      (d) => d.slop.emojiInHeadingsOrButtons.count >= 1],
  ["T1",  "type scale ratios computed",          (d) => Array.isArray(d.typography.adjacentRatios) && d.typography.adjacentRatios.length >= 2],
  ["T2",  "families counted",                    (d) => d.typography.distinctFamilies >= 1],
  ["T3",  "measure median computed",             (d) => d.typography.measureCh && d.typography.measureCh.median > 0],
  ["D27", "hover-only content detected",         (d) => d.states.hoverOnlyContentCount >= 2],
  ["D27b","hover-only content names its controls",(d) => d.states.hoverOnlyContent.some((x) => x.interactive)],
  ["D28", "decorative 01/02/03 step numbers",    (d) => d.slop.decorativeStepNumbers >= 3],
  ["D29", "em-dash density in copy measured",    (d) => d.slop.emDashesInCopy >= 4 && d.slop.emDashesPer1kChars > 0],
  ["D30", "LLM sentence frames caught",          (d) => d.slop.llmSentenceFrames.length >= 2],
  ["D31", "native title-attribute tooltip",      (d) => d.chrome.nativeTitleTooltips >= 1],
  ["D32", "suppressed scrollbar on a scroll region", (d) => d.chrome.hiddenScrollbars >= 1],
  ["D32b","scroll regions counted at all",       (d) => d.chrome.scrollableRegions >= 1],
  ["D33", "select stripped of its chevron",      (d) => d.chrome.unstyledStrippedSelects >= 1],
  ["D34", "color-scheme left undeclared",        (d) => d.chrome.colorScheme === "normal"],
  ["D36", "padded numerals one-per-row still read as ornament",
                                                 (d) => d.slop.decorativeStepNumbers >= 6],
  ["D37", "a hover fill the colour the row already is", (d) => d.states.inertHoverFills >= 1],
  ["D38", "a wide hover fill with no horizontal padding",
                                                 (d) => d.states.hoverFillsWithoutPadding >= 1],
  ["D39", "a hover fill that moves hue but not lightness",
                                                 (d) => d.states.hueOnlyHoverFills >= 1],
  ["D40", "a hover border re-declaring the colour it already has",
                                                 (d) => d.states.inertHoverBorders >= 1],
  ["D41", "a hover fill painting over its own row separator",
                                                 (d) => d.states.hoverFillsCoveringOwnRule >= 1],
  ["D42", "a hover fill crowding its text vertically",
                                                 (d) => d.states.hoverFillsWithoutPaddingExamples.some((x) => x.inkGapTop < 6)],
  ["D43", "colour-only prose link detected",      (d) => d.states.colorOnlyLinks.count >= 1 &&
                                                             d.states.colorOnlyLinks.list.some((x) => x.linkToTextRatio < 3)],
  ["D44", "broken required ARIA IDREF detected",  (d) => d.a11y.requiredBrokenAriaReferences.count >= 1],
  ["D44b","deferred aria-controls kept provisional", (d) => d.a11y.deferredAriaControls.count >= 1],
  ["D45", "ARIA widget missing required state",   (d) => d.a11y.ariaRoleStateIssues.count >= 1],
  ["D46", "repeated landmarks need unique names", (d) => d.a11y.landmarkNameIssues.count >= 1],
  ["D47", "focused control completely obscured",   (d) => d.interaction.focusRing.completelyObscured >= 1],
  ["D48", "visible label omitted from name",       (d) => d.a11y.labelInName.count >= 1],
  ["D49", "invalid language tag detected",         (d) => d.a11y.invalidLanguageTags.count >= 1],
  ["D50", "invalid autocomplete tokens detected",  (d) => d.a11y.invalidAutocomplete.count >= 1],
  ["D51", "unrecognized language primary surfaced", (d) => d.a11y.unrecognizedLanguageTags.count >= 1],
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
  ["C26", "table with scope + caption passes",                (d) => d.app.tables.length >= 1 &&
                                                                     d.app.tables[0].hasHeaderAssociations === true],
  ["C27", "scales are read as scales, not sprawl",            (d) => d.system.radius.distinct <= 4 &&
                                                                     d.system.shadow.distinct <= 4 &&
                                                                     d.system.zIndex.distinct <= 6],
  ["C29", "focus-within/details hover reveals not flagged",   (d) => d.states.hoverOnlyContentCount === 0],
  ["C30", "declared color-scheme satisfies the chrome check",  (d) => d.chrome.colorScheme.includes("dark") &&
                                                                     d.chrome.darkSurfaceWithoutColorScheme === false],
  ["C31", "a lone padded `01` is data, not ornament",         (d) => d.slop.decorativeStepNumbers === 0],
  ["C36", "a perceptible hover fill is not an inert one",     (d) => d.states.hoverFillsChecked >= 1 &&
                                                                     d.states.inertHoverFills === 0],
  ["C37", "a padded hover fill is not an unpadded one",       (d) => d.states.hoverFillsWithoutPadding === 0],
  ["C38", "a real border-colour hover is not an inert one",   (d) => d.states.inertHoverBorders === 0],
  ["C39", "a rule on the row and a tint on the child is correct", (d) => d.states.hoverFillsCoveringOwnRule === 0],
  ["C32", "a native select keeping its chevron is fine",      (d) => d.chrome.selects >= 1 &&
                                                                     d.chrome.unstyledStrippedSelects === 0],
  ["C33", "an unstyled scrollbar is not a hidden one",        (d) => d.chrome.scrollableRegions >= 1 &&
                                                                     d.chrome.hiddenScrollbars === 0],
  ["C34", "a title repeating its own link text is not a tooltip", (d) => d.chrome.nativeTitleTooltips === 0],
  // One em dash in a page of prose is a writer. Eight is a model. The check
  // is a RATE, and this asserts the rate stays under the threshold on copy a
  // human wrote, because docking a page for a single correct em dash is how a
  // slop detector gets muted.
  ["C35", "a single em dash in prose is not a slop rate",     (d) => d.slop.emDashesInCopy <= 1 &&
                                                                     d.slop.emDashesPer1kChars < 2 &&
                                                                     d.slop.llmSentenceFrames.length === 0],
  ["C61", "underlined prose links are distinguishable",       (d) => d.states.colorOnlyLinks.count === 0],
  ["C62", "valid ARIA wiring stays clean",                     (d) => d.a11y.brokenAriaReferences.count === 0 &&
                                                                     d.a11y.requiredBrokenAriaReferences.count === 0 &&
                                                                     d.a11y.deferredAriaControls.count === 0 &&
                                                                     d.a11y.ariaRoleStateIssues.count === 0],
  ["C63", "simple table needs no explicit scope",              (d) => d.app.tables.some((t) =>
                                                                     t.needsHeaderAssociations === false &&
                                                                     t.hasHeaderAssociations === false)],
  ["C64", "repeated landmarks have unique names",              (d) => d.a11y.landmarkNameIssues.count === 0],
  ["C65", "visible label may prefix a longer accessible name",  (d) => d.a11y.labelInName.count === 0],
  ["C66", "valid nested language tags remain clean",            (d) => !d.a11y.invalidLanguageTags.list.some((x) => x.value === "fr-CA")],
  ["C67", "valid autocomplete sequences remain clean",          (d) => d.a11y.invalidAutocomplete.count === 0],
  ["C68", "no focused control is completely obscured",          (d) => d.interaction.focusRing.completelyObscured === 0],
  ["C69", "known language primary remains clean",                (d) => d.a11y.unrecognizedLanguageTags.count === 0],
  ["C70", "known primary survives non-strict trailing subtags",   (d) => d.a11y.invalidLanguageTags.list.some((x) => x.value === "en-US-GB") &&
                                                                     !d.a11y.unrecognizedLanguageTags.list.some((x) => x.value === "en-US-GB")],
  ["C71", "inapplicable autocomplete values remain clean",        (d) => d.a11y.invalidAutocomplete.count === 0],
  ["C72", "lang owner with no inherited text is inapplicable",    (d) => !d.a11y.unrecognizedLanguageTags.list.some((x) => x.sel.includes("language-owner"))],
  ["C28", "no probe section errored",                         (d) => d.errors.length === 0],
];

const profile = mkdtempSync(join(tmpdir(), "dd-selftest-"));
let browser;
try {
  // launch() (not launchPersistentContext) so this never contends with the
  // Playwright MCP server's profile lock - the selftest must run even while
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
      // Derive the expected run count from the config rather than hardcoding
      // it. A hardcoded number goes stale the moment the runner gains a pass
      // (it did, when the landscape-phone pass landed), and a selftest that
      // fails for a stale reason gets ignored for a real one.
      const runnerCfg = {
        outDir, label: "fixture", url: fixture,
        // Deliberately omit 1440: the runner must add a like-for-like control
        // for its desktop override/i18n deltas instead of comparing to 390.
        viewports: [[390, 844]],
        dark: true, reducedMotion: true, landscapePhone: true,
        i18n: {
          textExpansion: true, rtl: true,
          profiles: [
            { label: "ja-JP", locale: "ja-JP", dir: "ltr",
              text: { "h1": "請求書の承認", "#fixture-save": "保存する" } },
            { label: "ar-EG", locale: "ar-EG", dir: "rtl",
              text: { "h1": "مراجعة الفواتير", "#fixture-save": "حفظ التغييرات" } },
          ],
        },
        visionDeficiencies: ["achromatopsia"],
        announcements: [{ label: "fixture save", click: "#fixture-save", wait: 120,
                          expected: "saved successfully" }],
        widgets: [
          { label: "fixture tabs", kind: "tablist", selector: "#fixture-tabs" },
          { label: "fixture dialog", kind: "dialog", selector: "#fixture-dialog", open: "#fixture-dialog-open" },
        ],
        authChecks: [{ label: "fixture password", selector: "#fixture-password",
                       expectedAutocomplete: "current-password" }],
        dragAlternatives: [{ label: "fixture reorder", dragSelector: ".fixture-drag",
                             alternativeSelector: "#fixture-move" }],
        redundantEntries: [{ label: "fixture email", firstSelector: "#fixture-first-email",
                             value: "test@example.com", advance: "#fixture-next",
                             secondSelector: "#fixture-confirm-email" }],
        waitMs: 200, fullPage: false,
        skillDir: here,
      };
      // The four override passes default ON in the runner, so they count unless
      // the config turns them off. Omitting them is exactly the staleness the
      // comment above warns about: the formula said 5, the runner did 9, and the
      // gate failed for a bookkeeping reason on every run.
      const OVERRIDES = ["forced-colors", "contrast-more", "text-spacing", "text-zoom-200"];
      const needsComparisonBaseline =
        OVERRIDES.some((k) => runnerCfg[k] !== false) || runnerCfg.dark || runnerCfg.reducedMotion ||
        Boolean(runnerCfg.i18n?.textExpansion || runnerCfg.i18n?.rtl || runnerCfg.i18n?.profiles?.length);
      const addsComparisonBaseline = needsComparisonBaseline &&
        !runnerCfg.viewports.some(([w, h]) => w === 1440 && h === 900);
      const expectedRuns = runnerCfg.viewports.length +
        (addsComparisonBaseline ? 1 : 0) +
        (runnerCfg.dark ? 1 : 0) +
        (runnerCfg.reducedMotion ? 1 : 0) +
        (runnerCfg.landscapePhone !== false ? 1 : 0) +
        OVERRIDES.filter((k) => runnerCfg[k] !== false).length +
        (runnerCfg.i18n && runnerCfg.i18n.textExpansion ? 1 : 0) +
        (runnerCfg.i18n && runnerCfg.i18n.rtl ? 1 : 0) +
        (runnerCfg.i18n && Array.isArray(runnerCfg.i18n.profiles) ? runnerCfg.i18n.profiles.length : 0) +
        (runnerCfg.visionDeficiencies ? runnerCfg.visionDeficiencies.length : 0) +
        (runnerCfg.stress ? 1 : 0) +
        (runnerCfg.states ? runnerCfg.states.length : 0);
      wf(cfgPath, JSON.stringify(runnerCfg));
      const src = rf(join(here, "probe-runner.mjs"), "utf8");
      // Same shape the harness uses: the file is a bare async (page) => {...}
      const fn = new Function("return (" + src + ")")();
      if (typeof fn !== "function") throw new Error("probe-runner.mjs did not evaluate to a function");
      const outText = await fn(page);
      console.log(outText);
      const jsonPath = join(outDir, "probe-fixture.json");
      const shotOk = ex(join(outDir, "screenshots", "fixture-1440x900.png"));
      const ariaOk = ex(join(outDir, "accessibility", "fixture-1440x900.aria.yml"));
      const ok = ex(jsonPath) && shotOk && ariaOk;
      const parsed = ok ? JSON.parse(rf(jsonPath, "utf8")) : null;
      const runCount = parsed ? parsed.runs.length : 0;
      const ariaCount = parsed ? (parsed.accessibilitySnapshots || []).filter((x) => x.status === "written").length : 0;
      const announceOk = parsed && parsed.behavioralEvidence.announcements.some((x) => x.status === "verified");
      const widgetOk = parsed && parsed.behavioralEvidence.widgets.length === 2 &&
        parsed.behavioralEvidence.widgets.every((x) => x.status === "verified");
      const authOk = parsed && parsed.behavioralEvidence.authentication.every((x) => x.status === "verified") &&
        parsed.behavioralEvidence.authentication.length === 1;
      const dragOk = parsed && parsed.behavioralEvidence.dragAlternatives.every((x) => x.status === "verified") &&
        parsed.behavioralEvidence.dragAlternatives.length === 1;
      const redundantOk = parsed && parsed.behavioralEvidence.redundantEntries.every((x) => x.status === "verified") &&
        parsed.behavioralEvidence.redundantEntries.length === 1;
      const labelNameOk = parsed && parsed.runs.some((x) =>
        x.a11y && x.a11y.browserLabelInName && x.a11y.browserLabelInName.failures >= 1);
      const missingNameOk = parsed && parsed.runs.some((x) =>
        x.a11y && x.a11y.browserMissingAccessibleName && x.a11y.browserMissingAccessibleName.failures >= 1);
      const visionOk = parsed && parsed.visionDeficiencyPasses.some((x) => x.status === "ran");
      const localePasses = parsed ? parsed.overridePasses.filter((x) => x.pass.startsWith("locale-")) : [];
      const localeOk = localePasses.length === 2 && localePasses.every((x) => x.status === "ran");
      const stabilityOk = parsed && parsed.screenshotStability.length === expectedRuns &&
        parsed.screenshotStability.every((x) => x.status === "stable");
      console.log(`\nrunner check: json=${ex(jsonPath)} screenshots=${shotOk} aria=${ariaOk} runs=${runCount} aria-runs=${ariaCount} (expect ${expectedRuns})`);
      console.log(`behavior check: announcement=${announceOk} widget=${widgetOk} auth=${authOk} drag=${dragOk} redundant=${redundantOk} browser-name=${missingNameOk} browser-label-in-name=${labelNameOk} vision=${visionOk} locales=${localeOk} stable=${stabilityOk}`);
      if (!ok || runCount !== expectedRuns || ariaCount !== expectedRuns ||
          !announceOk || !widgetOk || !authOk || !dragOk || !redundantOk ||
          !missingNameOk || !labelNameOk || !visionOk || !localeOk || !stabilityOk) {
        console.log("RUNNER CHECK FAILED");
        if (parsed) {
          console.log("widget details: " + JSON.stringify(parsed.behavioralEvidence.widgets));
          console.log("unstable captures: " + JSON.stringify(parsed.screenshotStability.filter((x) => x.status !== "stable")));
        }
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

  // ---- differential mutation + stability benchmark ---------------------
  // A planted-defect page proves recall only in aggregate: a detector can
  // accidentally key off some neighbouring fixture detail and still pass.
  // This mode starts from the precision-clean page, introduces ONE defect at
  // a time, and requires the corresponding measurement to move. It also adds
  // semantically inert DOM noise and requires a compact measurement
  // fingerprint to remain byte-for-byte stable. That catches both silent
  // detectors and detectors that react to irrelevant implementation churn.
  if (mutations || pipeline) {
    const runProbe = async () => page.evaluate(([src]) => {
      // eslint-disable-next-line no-new-func
      new Function(src)();
      return window.__ddProbe({});
    }, [probeSrc]);
    const reloadClean = async () => {
      await page.goto(fixture, { waitUntil: "load" });
      await page.waitForTimeout(120);
    };
    const fingerprint = (d) => ({
      contrast: d.color.textContrast.failures,
      target24: d.interaction.belowWcagTarget24.count,
      noAlt: d.a11y.imagesMissingAlt.count,
      noName: d.a11y.controlsMissingAccessibleName.count,
      noLabel: d.a11y.fieldsMissingLabel.count,
      duplicateIds: d.a11y.duplicateIds.count,
      requiredAria: d.a11y.requiredBrokenAriaReferences.count,
      roleState: d.a11y.ariaRoleStateIssues.count,
      landmarks: d.a11y.landmarkNameIssues.count,
      labelInName: d.a11y.labelInName.count,
      invalidLang: d.a11y.invalidLanguageTags.count,
      unknownLang: d.a11y.unrecognizedLanguageTags.count,
      invalidAutocomplete: d.a11y.invalidAutocomplete.count,
      focusObscured: d.interaction.focusRing.completelyObscured,
      colorOnlyLinks: d.states.colorOnlyLinks.count,
      overflow: d.layout.horizontalOverflow,
      errors: d.errors,
    });

    await reloadClean();
    const clean = await runProbe();
    const cases = [
      ["M1", "missing image alternative", () => {
        const el = document.createElement("img");
        el.src = "data:image/gif;base64,R0lGODlhAQABAAAAACw=";
        el.width = 32; el.height = 32; document.body.append(el);
      }, (b, a) => a.a11y.imagesMissingAlt.count > b.a11y.imagesMissingAlt.count],
      ["M2", "text contrast regression", () => {
        const el = document.createElement("p");
        el.textContent = "Mutation contrast sample";
        el.style.cssText = "color:#777;background:#777;padding:8px";
        document.body.append(el);
      }, (b, a) => a.color.textContrast.failures > b.color.textContrast.failures],
      ["M3", "broken required ARIA reference", () => {
        const el = document.createElement("button");
        el.setAttribute("aria-labelledby", "mutation-missing-label");
        el.textContent = "Menu"; document.body.append(el);
      }, (b, a) => a.a11y.requiredBrokenAriaReferences.count > b.a11y.requiredBrokenAriaReferences.count],
      ["M4", "ARIA widget missing required state", () => {
        const el = document.createElement("div");
        el.setAttribute("role", "switch"); el.setAttribute("aria-label", "Alerts");
        el.textContent = "Alerts"; document.body.append(el);
      }, (b, a) => a.a11y.ariaRoleStateIssues.count > b.a11y.ariaRoleStateIssues.count],
      ["M5", "unnamed repeated landmark", () => {
        const el = document.createElement("nav");
        el.innerHTML = '<a href="#main">Mutation navigation</a>'; document.body.append(el);
      }, (b, a) => a.a11y.landmarkNameIssues.count > b.a11y.landmarkNameIssues.count],
      ["M6", "horizontal overflow", () => {
        const el = document.createElement("div");
        el.style.cssText = "width:200vw;height:2px"; document.body.append(el);
      }, (b, a) => a.layout.horizontalOverflow && !b.layout.horizontalOverflow],
      ["M7", "colour-only prose link", () => {
        const p = document.createElement("p");
        p.style.color = "#334155";
        p.innerHTML = 'Read the complete account reconciliation before choosing <a href="#main" style="color:#334155;text-decoration:none;font-weight:400">this report</a> for approval.';
        document.body.append(p);
      }, (b, a) => a.states.colorOnlyLinks.count > b.states.colorOnlyLinks.count],
      ["M8", "crowded undersized targets", () => {
        const box = document.createElement("div");
        box.style.cssText = "display:flex;gap:0;position:absolute;left:500px;top:500px";
        box.innerHTML = '<button aria-label="Previous" style="width:12px;height:12px;min-width:0;padding:0;font-size:1px">p</button><button aria-label="Next" style="width:12px;height:12px;min-width:0;padding:0;font-size:1px">n</button>';
        document.body.append(box);
      }, (b, a) => a.interaction.belowWcagTarget24.count > b.interaction.belowWcagTarget24.count],
      ["M9", "duplicate identifiers", () => {
        const a = document.createElement("div"), b = document.createElement("div");
        a.id = b.id = "mutation-duplicate"; a.textContent = "First"; b.textContent = "Second";
        document.body.append(a, b);
      }, (b, a) => a.a11y.duplicateIds.count > b.a11y.duplicateIds.count],
      ["M10", "unnamed interactive control", () => {
        const el = document.createElement("button");
        el.style.cssText = "width:44px;height:44px"; document.body.append(el);
      }, (b, a) => a.a11y.controlsMissingAccessibleName.count > b.a11y.controlsMissingAccessibleName.count],
      ["M11", "form field missing a label", () => {
        const el = document.createElement("input");
        el.type = "text"; document.body.append(el);
      }, (b, a) => a.a11y.fieldsMissingLabel.count > b.a11y.fieldsMissingLabel.count],
      ["M12", "visible label omitted from accessible name", () => {
        const el = document.createElement("button");
        el.textContent = "Archive invoice"; el.setAttribute("aria-label", "Delete record");
        document.body.append(el);
      }, (b, a) => a.a11y.labelInName.count > b.a11y.labelInName.count],
      ["M13", "invalid language metadata", () => {
        const el = document.createElement("span");
        el.setAttribute("lang", "not_a_language"); el.textContent = "Metadata"; document.body.append(el);
      }, (b, a) => a.a11y.invalidLanguageTags.count > b.a11y.invalidLanguageTags.count],
      ["M14", "invalid autocomplete sequence", () => {
        const lab = document.createElement("label"), el = document.createElement("input");
        el.id = "mutation-purpose"; el.type = "email"; el.setAttribute("autocomplete", "email work");
        lab.htmlFor = el.id; lab.textContent = "Work email"; document.body.append(lab, el);
      }, (b, a) => a.a11y.invalidAutocomplete.count > b.a11y.invalidAutocomplete.count],
      ["M15", "focused control completely covered", () => {
        const button = document.createElement("button"), cover = document.createElement("div");
        button.textContent = "Covered mutation";
        button.style.cssText = "position:fixed;left:8px;top:8px;width:140px;height:40px;z-index:100";
        cover.textContent = "Cover";
        cover.style.cssText = "position:fixed;left:4px;top:4px;width:150px;height:50px;z-index:101;background:white";
        document.body.append(button, cover);
      }, (b, a) => a.interaction.focusRing.completelyObscured > b.interaction.focusRing.completelyObscured],
      ["M16", "unrecognized language primary", () => {
        const el = document.createElement("span");
        el.setAttribute("lang", "zz-ZZ"); el.textContent = "Unknown language"; document.body.append(el);
      }, (b, a) => a.a11y.unrecognizedLanguageTags.count > b.a11y.unrecognizedLanguageTags.count],
      ["M17", "whitespace-only language part", () => {
        const el = document.createElement("span");
        el.setAttribute("lang", "  "); el.textContent = "Inherited language target"; document.body.append(el);
      }, (b, a) => a.a11y.unrecognizedLanguageTags.count > b.a11y.unrecognizedLanguageTags.count],
      ["M18", "unnamed image-map link", () => {
        const img = document.createElement("img"), map = document.createElement("map"), area = document.createElement("area");
        img.alt = "Plan"; img.useMap = "#mutation-map"; img.src = "data:image/gif;base64,R0lGODlhAQABAAAAACw=";
        map.name = "mutation-map"; area.href = "#main"; area.shape = "rect"; area.coords = "0,0,1,1";
        map.append(area); document.body.append(img, map);
      }, (b, a) => a.a11y.controlsMissingAccessibleName.count > b.a11y.controlsMissingAccessibleName.count],
    ];

    let passed = 0;
    const failed = [];
    for (const [id, desc, mutate, changed] of cases) {
      await reloadClean();
      await page.evaluate(mutate);
      await page.waitForTimeout(40);
      const after = await runProbe();
      let ok = false, err = "";
      try { ok = changed(clean, after); } catch (e) { err = ` (threw: ${e.message})`; }
      if (ok) passed++; else failed.push(`  ${id.padEnd(5)} ${desc}${err}`);
    }

    await reloadClean();
    const stableBefore = await runProbe();
    await page.evaluate(() => {
      document.documentElement.dataset.buildStamp = "2026-08-03T00:00:00Z";
      document.body.append(document.createComment("non-rendered deployment marker"));
      const hidden = document.createElement("div");
      hidden.hidden = true; hidden.textContent = "A changing timestamp 12:34:56";
      document.body.append(hidden);
    });
    const stableAfter = await runProbe();
    const stable = JSON.stringify(fingerprint(stableBefore)) === JSON.stringify(fingerprint(stableAfter));

    console.log(`probe-selftest --mutations: ${passed}/${cases.length} isolated defects moved their detector`);
    console.log(`probe-selftest --stability: ${stable ? "1/1" : "0/1"} inert DOM changes left measurements stable`);
    if (failed.length || !stable) {
      if (failed.length) {
        console.log("MUTATIONS NOT DETECTED:");
        failed.forEach((f) => console.log(f));
      }
      if (!stable) {
        console.log("UNSTABLE FINGERPRINT:");
        console.log("  before=" + JSON.stringify(fingerprint(stableBefore)));
        console.log("  after =" + JSON.stringify(fingerprint(stableAfter)));
      }
      process.exitCode = 1;
    } else console.log("differential benchmark passed - detectors respond to defects, not inert churn");

    if (pipeline && !failed.length && stable) {
      const expectations = {
        M1: { pillar: "a11y", wcag: "1.1.1", severity: "critical" },
        M2: { pillar: "color", wcag: "1.4.3", severity: "critical" },
        M3: { pillar: "a11y", wcag: "4.1.2", severity: "critical" },
        M6: { pillar: "responsive", severity: "major" },
        M12: { pillar: "a11y", severity: "major" },
        M13: { pillar: "a11y", wcag: "3.1.2", severity: "critical" },
        M14: { pillar: "a11y", wcag: "1.3.5", severity: "critical" },
        M15: { pillar: "a11y", wcag: "2.4.11", severity: "critical" },
        M17: { pillar: "a11y", wcag: "3.1.2", severity: "critical" },
        M18: { pillar: "a11y", wcag: "4.1.2", severity: "critical" },
      };
      const reportScript = join(here, "probe-report.py");
      const scoreScript = join(here, "score.py");
      const scoreOne = (ledger, out) => spawnSync("python3", [scoreScript, "--findings", ledger,
        "--hierarchy", "A", "--content", "A", "--ia", "A", "--out-json", out],
        { encoding: "utf8" });
      let pipelinePassed = 0;
      const pipelineFailed = [];
      const verifyPipelinePayload = (id, desc, payload, expected) => {
        const probeFile = join(profile, `${id}-probe.json`);
        const ledgerFile = join(profile, `${id}-findings.json`);
        const scoreFile = join(profile, `${id}-score.json`);
        writeFileSync(probeFile, JSON.stringify(payload));
        const reportRun = spawnSync("python3", [reportScript, probeFile, "--emit-findings", ledgerFile, "--quiet"],
          { encoding: "utf8" });
        if (reportRun.status !== 0) {
          pipelineFailed.push(`${id} report failed: ${(reportRun.stderr || reportRun.stdout).trim().slice(0, 180)}`);
          return;
        }
        const ledger = JSON.parse(readFileSync(ledgerFile, "utf8"));
        const hit = (ledger.findings || []).find((f) => f.pillar === expected.pillar &&
          (!expected.wcag || f.wcag === expected.wcag) && f.severity === expected.severity);
        if (!hit) {
          pipelineFailed.push(`${id} ${desc}: no ${expected.severity} ${expected.pillar}/${expected.wcag || "non-WCAG"} finding`);
          return;
        }
        hit.status = "confirmed";
        writeFileSync(ledgerFile, JSON.stringify(ledger));
        const scoreRun = scoreOne(ledgerFile, scoreFile);
        if (scoreRun.status !== 0) {
          pipelineFailed.push(`${id} score failed: ${(scoreRun.stderr || scoreRun.stdout).trim().slice(0, 180)}`);
          return;
        }
        const score = JSON.parse(readFileSync(scoreFile, "utf8"));
        const lowered = score.overall < 92;
        const capped = !expected.wcag || (score.overall <= 75 && score.cappedByWcag === true);
        if (!lowered || !capped) {
          pipelineFailed.push(`${id} reached report but score=${score.overall} capped=${score.cappedByWcag}`);
          return;
        }
        pipelinePassed++;
      };
      for (const [id, desc, mutate] of cases.filter((c) => expectations[c[0]])) {
        await reloadClean(); await page.evaluate(mutate); await page.waitForTimeout(40);
        const after = await runProbe(); after.tag = "1440x900";
        if (id === "M3" || id === "M18") {
          const list = (after.a11y.controlsMissingAccessibleName.list || []).map((x) => ({ ...x, source: "control" }));
          after.a11y.browserMissingAccessibleName = {
            candidates: list.length, checked: list.length, failures: list.length,
            list, dismissed: [], inconclusive: [],
          };
        }
        verifyPipelinePayload(id, desc, { label: id, url: fixture,
          probedAt: new Date().toISOString(), performance: {}, consoleErrors: [], failedRequests: [],
          overridePasses: [], statePasses: [], behavioralEvidence: {}, runs: [after] }, expectations[id]);
      }

      const cleanRun = { ...clean, tag: "1440x900" };
      const behaviorCases = [
        ["B1", "missing status announcement", { announcements: [{ label: "save", status: "failed", messages: [], expected: "saved", expectedMatched: false }] }, { pillar: "a11y", wcag: "4.1.3", severity: "critical" }],
        ["B2", "dialog focus contract", { widgets: [{ label: "dialog", kind: "dialog", status: "failed", focusInsideAtOpen: false, focusEscaped: true, escapeClosed: false, focusRestored: false }] }, { pillar: "a11y", wcag: "2.4.3", severity: "critical" }],
        ["B3", "authentication blocks paste", { authentication: [{ label: "password", status: "failed", pasteAllowed: false, expectedPresent: true }] }, { pillar: "a11y", wcag: "3.3.8", severity: "critical" }],
        ["B4", "dragging lacks alternative", { dragAlternatives: [{ label: "reorder", status: "failed", alternativePresent: false, alternativeKeyboardReachable: false }] }, { pillar: "a11y", wcag: "2.5.7", severity: "critical" }],
        ["B5", "redundant entry", { redundantEntries: [{ label: "email", status: "failed", autoPopulated: false, selectable: false }] }, { pillar: "a11y", wcag: "3.3.7", severity: "critical" }],
      ];
      for (const [id, desc, behavioralEvidence, expected] of behaviorCases) {
        verifyPipelinePayload(id, desc, { label: id, url: fixture,
          probedAt: new Date().toISOString(), performance: {}, consoleErrors: [], failedRequests: [],
          overridePasses: [], statePasses: [], behavioralEvidence, runs: [cleanRun] }, expected);
      }
      const localeRun = JSON.parse(JSON.stringify(cleanRun));
      localeRun.tag = "locale-de-de";
      localeRun.layout.horizontalOverflow = true;
      verifyPipelinePayload("L1", "reviewed locale overflow", { label: "L1", url: fixture,
        probedAt: new Date().toISOString(), performance: {}, consoleErrors: [], failedRequests: [],
        overridePasses: [{ pass: "locale-de-de", locale: "de-DE", status: "ran" }],
        statePasses: [], behavioralEvidence: {}, runs: [cleanRun, localeRun] },
        { pillar: "responsive", severity: "major" });
      const pipelineTotal = Object.keys(expectations).length + behaviorCases.length + 1;
      console.log(`probe-selftest --pipeline: ${pipelinePassed}/${pipelineTotal} defects reached report + score`);
      if (pipelineFailed.length) {
        console.log("PIPELINE FAILURES:"); pipelineFailed.forEach((f) => console.log("  " + f));
        process.exitCode = 1;
      } else console.log("pipeline benchmark passed - defects survive measurement, reporting, severity mapping and scoring");
    }
    await browser.close();
    process.exit(process.exitCode || 0);
  }

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
    // Touch emulation, mirroring probe-runner.mjs. The selftest has to walk
    // the same path the real runner does, or the precision gate passes a page
    // that the shipping runner would flag (and vice versa). See the touch
    // block in probe-runner.mjs for why setViewportSize alone is not enough.
    const cdp = await page.context().newCDPSession(page);
    const setTouch = async (on) => {
      // maxTouchPoints must be 1..16 when present - sending 0 to disable is a
      // protocol error, so omit it entirely on the way out.
      await cdp.send("Emulation.setTouchEmulationEnabled",
        on ? { enabled: true, maxTouchPoints: 5 } : { enabled: false });
      await cdp.send("Emulation.setEmitTouchEventsForMouse", {
        enabled: on, configuration: on ? "mobile" : "desktop" });
      await cdp.send("Emulation.setEmulatedMedia", {
        features: on ? [
          { name: "pointer", value: "coarse" }, { name: "any-pointer", value: "coarse" },
          { name: "hover", value: "none" }, { name: "any-hover", value: "none" },
        ] : [] });
    };

    const runs = [];
    await page.setViewportSize({ width: 1440, height: 900 });
    const primary = await runProbe("1440x900");
    runs.push(primary);
    await setTouch(true);
    await page.setViewportSize({ width: 390, height: 844 });
    runs.push(await runProbe("390x844"));
    await page.setViewportSize({ width: 844, height: 390 });
    runs.push(await runProbe("landscape-844x390"));
    await setTouch(false);
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
      console.log("THRESHOLD FALSE POSITIVES - a correct page must score clean.");
      process.exitCode = 1;
    } else if (!missed.length) {
      console.log("clean fixture is clean - probe.js and probe-report.py are not inventing work");
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
      // The page-level fields the real runner always writes. Without them a
      // regress.py diff of two --out payloads silently skips console errors
      // and perf, because regress.py treats a metric absent from the BEFORE
      // side as a new check rather than a regression.
      performance: {}, consoleErrors: [], failedRequests: [],
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
    const ch = data.chrome || {};
    console.log(`  copy: emDash=${data.slop.emDashesInCopy}(${data.slop.emDashesPer1kChars}/1k) steps01=${data.slop.decorativeStepNumbers} frames=${(data.slop.llmSentenceFrames || []).length}`);
    console.log(`  chrome: color-scheme=${ch.colorScheme} darkNoScheme=${ch.darkSurfaceWithoutColorScheme} hiddenScrollbars=${ch.hiddenScrollbars}/${ch.scrollableRegions} strippedSelects=${ch.unstyledStrippedSelects}/${ch.selects} titleTooltips=${ch.nativeTitleTooltips}`);
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

  // D35 needs a dark surface to exist before it can mean anything, so it runs
  // its own pass. The fixture darkens under prefers-color-scheme and never
  // declares `color-scheme`, which is the single most common way a dark theme
  // ships with light OS scrollbars, a white <select> popup and yellow autofill.
  let total = EXPECT.length + 1;
  await page.emulateMedia({ colorScheme: "dark" });
  await page.waitForTimeout(150);
  const darkData = await page.evaluate(([src]) => {
    // eslint-disable-next-line no-new-func
    new Function(src)();
    return window.__ddProbe({});
  }, [probeSrc]);
  await page.emulateMedia({ colorScheme: "light" });
  if (darkData.chrome && darkData.chrome.surfaceLooksDark &&
      darkData.chrome.darkSurfaceWithoutColorScheme === true) {
    pass++;
  } else {
    failed.push(`  D35   dark surface without color-scheme (looksDark=` +
                `${darkData.chrome && darkData.chrome.surfaceLooksDark})`);
  }

  console.log(`probe-selftest: ${pass}/${total} planted defects detected`);
  if (data.errors.length) {
    console.log("probe reported internal errors:");
    data.errors.forEach((e) => console.log("  ! " + e));
  }
  if (failed.length) {
    console.log("MISSED:");
    failed.forEach((f) => console.log(f));
    process.exitCode = 1;
  } else {
    console.log("all planted defects detected - probe.js is behaving");
  }
} catch (e) {
  console.error("selftest could not run: " + (e && e.stack ? e.stack : e));
  process.exitCode = 3;
} finally {
  if (browser) await browser.close();
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* best effort */ }
}
