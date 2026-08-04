#!/usr/bin/env node
/* Run overlapping designer-dude detectors against independent W3C ACT cases. */

import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { readFileSync, writeFileSync } from "node:fs";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const args = process.argv.slice(2);
const arg = (name, fallback = null) => { const i = args.indexOf(name); return i < 0 ? fallback : args[i + 1]; };
if (args.includes("--help")) {
  console.log("usage: node act-benchmark.mjs --out <json> [--manifest <url>] [--min-cases 80]");
  process.exit(0);
}
const outPath = arg("--out");
if (!outPath) { console.error("act-benchmark: --out is required"); process.exit(2); }
const manifestUrl = arg("--manifest", "https://www.w3.org/WAI/content-assets/wcag-act-rules/testcases.json");
const minCases = Number(arg("--min-cases", "80"));
const maxCannotRatio = Number(arg("--max-cannot-tell", "0.05"));
const concurrency = Math.max(1, Math.min(12, Number(arg("--concurrency", "6"))));

const resolvedPw = require(join(here, "playwright-resolve.cjs"))();
if (!resolvedPw) { console.error("act-benchmark: Playwright not found"); process.exit(3); }
const probeSrc = readFileSync(join(here, "probe.js"), "utf8");

// Only map ACT rules whose applicability and outcome match a specific probe
// field. Similar-sounding rules (descriptive names, language matching) are
// deliberately absent because an aggregate DOM count would not implement them.
const mappings = {
  "73f2c2": { name: "autocomplete-valid", positive: (d) => d.a11y.invalidAutocomplete.count > 0 },
  "de46e4": { name: "element-lang-valid", positive: (d) => d.a11y.unrecognizedLanguageTags.list.some((x) => !String(x.sel).startsWith("html")) },
  "bf051a": { name: "html-lang-valid", positive: (d) => d.a11y.unrecognizedLanguageTags.list.some((x) => String(x.sel).startsWith("html")) },
  "b5c3f8": { name: "html-has-lang", positive: (d) => !d.a11y.lang },
  "97a4e1": { name: "button-name", selector:
    'button,input[type="button"],input[type="submit"],input[type="reset"],input[type="image"],[role="button"]' },
  "e086e5": { name: "form-field-name", selector:
    'input:not([type="hidden"]):not([type="button"]):not([type="submit"]):not([type="reset"]):not([type="image"]),select,textarea,[role="checkbox"],[role="combobox"],[role="listbox"],[role="radio"],[role="searchbox"],[role="slider"],[role="spinbutton"],[role="switch"],[role="textbox"]' },
  "c487ae": { name: "link-name", selector: 'a[href],area[href],[role="link"]' },
  "m6b1q3": { name: "menuitem-name", selector: '[role="menuitem"],[role="menuitemcheckbox"],[role="menuitemradio"]' },
};

const browserNameFailure = async (page, selector) => {
  const loc = page.locator(selector);
  const count = Math.min(await loc.count(), 100);
  for (let i = 0; i < count; i++) {
    const tree = await loc.nth(i).ariaSnapshot();
    const first = String(tree || "").split(/\r?\n/, 1)[0];
    if (!first.trim()) continue; // outside the accessibility tree: inapplicable
    const quoted = first.match(/^\s*-\s+[^\s:]+\s+("(?:[^"\\]|\\.)*")/);
    const single = first.match(/^\s*-\s+[^\s:]+\s+'([^']*)'/);
    let name = "";
    if (quoted) { try { name = JSON.parse(quoted[1]); } catch { name = null; } }
    else if (single) name = single[1].replace(/''/g, "'");
    if (name === "") return true;
  }
  return false;
};

const response = await fetch(manifestUrl);
if (!response.ok) { console.error(`act-benchmark: manifest HTTP ${response.status}`); process.exit(3); }
const manifestBytes = Buffer.from(await response.arrayBuffer());
const manifest = JSON.parse(manifestBytes.toString("utf8"));
const selected = [];
const seen = new Set();
for (const item of manifest.testcases || []) {
  if (!mappings[item.ruleId] || item.approved === false) continue;
  const key = `${item.ruleId}:${item.testcaseId}`;
  if (seen.has(key)) continue;
  seen.add(key); selected.push(item);
}

let browser;
const results = [];
try {
  browser = await resolvedPw.api.chromium.launch({ headless: true });
  let cursor = 0;
  const worker = async () => {
    const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, reducedMotion: "reduce" });
    const page = await context.newPage();
    while (cursor < selected.length) {
      const item = selected[cursor++];
      const base = { id: item.testcaseId, ruleId: item.ruleId, rule: mappings[item.ruleId].name,
                     ruleName: item.ruleName, url: item.url,
                     actExpected: item.expected,
                     expected: item.expected === "failed" ? "positive" : "negative" };
      try {
        const pageResponse = await page.goto(item.url, { waitUntil: "domcontentloaded", timeout: 20000 });
        const body = await pageResponse.body();
        const sourceSha256 = createHash("sha256").update(body).digest("hex");
        const contentType = String((await pageResponse.allHeaders())["content-type"] || "").toLowerCase();
        if (!contentType.includes("text/html")) {
          results.push({ ...base, sourceSha256, outcome: "negative",
                         reason: `ACT rule is inapplicable to ${contentType || "non-HTML"}` });
          continue;
        }
        const data = await page.evaluate(([src]) => { new Function(src)(); return window.__ddProbe({}); }, [probeSrc]);
        const mapping = mappings[item.ruleId];
        const positive = mapping.selector ? await browserNameFailure(page, mapping.selector) : mapping.positive(data);
        results.push({ ...base, sourceSha256,
                       outcome: positive ? "positive" : "negative" });
      } catch (error) {
        results.push({ ...base, outcome: "cannot-tell", reason: String(error).slice(0, 240) });
      }
    }
    await context.close();
  };
  await Promise.all(Array.from({ length: concurrency }, worker));
} finally {
  if (browser) await browser.close().catch(() => {});
}

results.sort((a, b) => (a.ruleId + a.id).localeCompare(b.ruleId + b.id));
let tp = 0, fp = 0, tn = 0, fn = 0, cannot = 0;
const perRule = {};
for (const row of results) {
  const counts = perRule[row.rule] ||= { tp: 0, fp: 0, tn: 0, fn: 0, cannotTell: 0 };
  if (row.outcome === "cannot-tell") { cannot++; counts.cannotTell++; continue; }
  const expected = row.expected === "positive", actual = row.outcome === "positive";
  const key = expected ? (actual ? "tp" : "fn") : (actual ? "fp" : "tn");
  counts[key]++;
  if (key === "tp") tp++; else if (key === "fp") fp++; else if (key === "tn") tn++; else fn++;
}
const errors = [];
if (results.length < minCases) errors.push(`only ${results.length} mapped cases; minimum ${minCases}`);
if (fp) errors.push(`${fp} false positives`);
if (fn) errors.push(`${fn} false negatives`);
if (results.length && cannot / results.length > maxCannotRatio) errors.push(`${cannot} cannot-tell outcomes exceed ratio ${maxCannotRatio}`);
const status = errors.length ? (fp || fn ? "fail" : "insufficient") : "pass";
const output = {
  schema: "designer-dude-act-benchmark/v1", mode: "detectors", status,
  generatedAt: new Date().toISOString(), producer: `designer-dude/${resolvedPw.version}`,
  source: { manifestUrl, manifestSha256: createHash("sha256").update(manifestBytes).digest("hex"),
            license: manifest.license, publishedCaseCount: manifest.count },
  thresholds: { minCases, maxCannotTellRatio: maxCannotRatio, falsePositives: 0, falseNegatives: 0 },
  confusion: { tp, fp, tn, fn, cannotTell: cannot }, perRule, errors, items: results,
};
writeFileSync(resolve(outPath), JSON.stringify(output, null, 2) + "\n");
console.log(`ACT benchmark: ${status} · ${results.length} cases · TP ${tp} FP ${fp} TN ${tn} FN ${fn} ? ${cannot}`);
console.log(`wrote ${resolve(outPath)}`);
process.exit(status === "pass" ? 0 : 1);
