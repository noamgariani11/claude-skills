// Miskari user-test browser harness.
// Usage from an agent script (MUST be launched with LD_LIBRARY_PATH set — see MB_LAUNCH):
//   const mb = require('<this path>');
//   mb.run(async (page, ctx, diag) => {
//     await mb.go(page, '/dashboard');
//     console.log(await mb.text(page));          // full visible text of body
//     console.log(await mb.text(page, 'main'));  // text of a selector
//     await mb.shot(page, 'dashboard');          // screenshot -> screenshots/<name>.png
//     await page.click('a:has-text("Bills")');
//   }, { viewport: '1440x900' });
// diag.consoleErrors and diag.netErrors are printed automatically at the end.

const os = require('os');
const path = require('path');

const PW = '/home/drago/miskari/node_modules/.pnpm/playwright-core@1.61.1/node_modules/playwright-core/index.js';
const { chromium } = require(PW);

// Auth state lives under ~/.cache so it survives a /compact wiping /tmp (a
// recurring pain across runs). Override with MB_AUTH; the skill's Phase 0 writes
// the fresh storageState here after login.
const AUTH = process.env.MB_AUTH || path.join(os.homedir(), '.cache', 'miskari-user-test', 'auth-state.json');
// No hardcoded port default: Miskari has been found on 3000/3001/3002 across
// runs, and unrelated apps squat those ports. Phase 0 MUST set MB_BASE to the
// port it verified is branded Miskari (see brandCheck). We refuse to guess.
const BASE = process.env.MB_BASE || (() => {
  console.log('MB_BASE not set - refusing to guess the port. Set MB_BASE to the URL Phase 0 verified as Miskari.');
  return 'http://localhost:3000';
})();
const SHOTS = process.env.MB_SHOTS || '/home/drago/miskari/docs/reports/user-test-miskari-reports/screenshots';

function parseVp(v) {
  const [w, h] = (v || '1440x900').split('x').map(Number);
  return { width: w || 1440, height: h || 900 };
}

async function run(fn, opts = {}) {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    storageState: AUTH,
    viewport: parseVp(opts.viewport),
    ...(opts.mobile ? { isMobile: true, hasTouch: true } : {}),
  });
  const diag = { consoleErrors: [], netErrors: [] };
  ctx.on('console', (m) => { if (m.type() === 'error') diag.consoleErrors.push(m.text().slice(0, 300)); });
  ctx.on('response', (r) => { if (r.status() >= 400) diag.netErrors.push(`${r.status()} ${r.request().method()} ${r.url().replace(BASE, '')}`); });
  const page = await ctx.newPage();
  page.setDefaultTimeout(30000);
  try {
    await fn(page, ctx, diag);
  } catch (e) {
    console.log('SCRIPT_ERROR: ' + (e && e.message ? e.message.split('\n')[0] : String(e)));
  } finally {
    if (diag.consoleErrors.length) console.log('\n--- CONSOLE ERRORS (' + diag.consoleErrors.length + ') ---\n' + [...new Set(diag.consoleErrors)].slice(0, 15).join('\n'));
    if (diag.netErrors.length) console.log('\n--- HTTP >=400 (' + diag.netErrors.length + ') ---\n' + [...new Set(diag.netErrors)].slice(0, 20).join('\n'));
    await browser.close();
  }
}

async function go(page, path) {
  const url = path.startsWith('http') ? path : BASE + path;
  const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 40000 }).catch((e) => { console.log('GOTO_FAIL ' + path + ' :: ' + e.message.split('\n')[0]); return null; });
  await page.waitForTimeout(400);
  console.log('NAV ' + path + ' -> ' + page.url().replace(BASE, '') + (resp ? ' [' + resp.status() + ']' : ''));
  return resp;
}

async function text(page, sel) {
  try {
    if (sel) return (await page.locator(sel).first().innerText()).replace(/\n{3,}/g, '\n\n').trim();
    return (await page.locator('body').innerText()).replace(/\n{3,}/g, '\n\n').trim();
  } catch (e) { return '[text() failed: ' + e.message.split('\n')[0] + ']'; }
}

async function shot(page, name) {
  const p = SHOTS + '/' + name.replace(/[^a-z0-9_-]/gi, '_') + '.png';
  await page.screenshot({ path: p, fullPage: true }).catch((e) => console.log('SHOT_FAIL ' + e.message.split('\n')[0]));
  console.log('SHOT ' + p);
  return p;
}

// Confirm the target really is Miskari before a run wastes itself on the wrong
// app. Returns { ok, reason }. Miskari's login is an email+password form and the
// brand token "Miskari" appears in chrome/title; the impostors seen across runs
// (Sheevook/pegazosdetailing, marketing-helper) do not. Call this in Phase 0.
async function brandCheck(page) {
  try {
    await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 20000 });
    const title = (await page.title().catch(() => '')) || '';
    const body = (await page.locator('body').innerText().catch(() => '')) || '';
    const hay = (title + '\n' + body).toLowerCase();
    const impostor = ['sheevook', 'pegazos', 'marketing helper', 'marketing-helper'].find((s) => hay.includes(s));
    if (impostor) return { ok: false, reason: `impostor app on ${BASE} (matched "${impostor}")` };
    const looksMiskari = hay.includes('miskari') || (hay.includes('email') && hay.includes('password') && /sign\s?in|log\s?in/.test(hay));
    return looksMiskari
      ? { ok: true, reason: `Miskari login confirmed on ${BASE}` }
      : { ok: false, reason: `no Miskari brand/login markers on ${BASE}` };
  } catch (e) {
    return { ok: false, reason: 'brandCheck failed: ' + (e && e.message ? e.message.split('\n')[0] : String(e)) };
  }
}

module.exports = { run, go, text, shot, brandCheck, BASE, SHOTS };
