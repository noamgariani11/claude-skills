---
name: browse
description: |
  Drive a real browser to inspect and interact with a local or remote web app — set the
  viewport, navigate, snapshot the DOM/accessibility tree, click and fill elements, take
  screenshots, and read the console + network for errors. Works in one long-lived tab, re-pointed
  at each URL as needed, so login, app state, and the console/network buffers survive the whole
  run instead of being thrown away per page. Built on Playwright MCP, which is
  pre-wired at user scope and pre-approved, so it never asks to install anything. Includes
  serve.sh, which reuses an already-running dev server only when it actually belongs to the
  project under test, otherwise starts one on a verified-free port so it never steals a port
  from another process, and can build and serve a production bundle with --prod. This is the
  standalone browser driver the user-test flow delegates to. Note that bug-hunt deliberately
  does NOT use it and drives its own Playwright engine instead. Use when asked to "browse",
  "open the page", "screenshot the app", "check the console", "click through the flow", or to
  visually verify a UI change in a real browser.
---

# browse — standalone browser driver

A dependency-free way to drive a browser for inspection and testing. **Playwright MCP is the
only engine**, and it is already wired up permanently — do not ask the user to install it.

## Preflight: just go

Playwright MCP is registered at user scope in `~/.claude.json` as
`npx -y @playwright/mcp@latest --browser chromium`, and `mcp__playwright` is on the permission
allowlist in `~/.claude/settings.json`. Chromium is already downloaded under
`~/.cache/ms-playwright` (`chromium-<build>/chrome-linux64/chrome`).

So: **never run `npx playwright install`, never ask permission to install, never offer to set
it up.** The `mcp__playwright__*` tools should simply be present. Call them directly.

Three failure modes, each with a different fix. The error text matters; read it before acting.

- **Tools absent from the session.** The MCP server failed to start (usually a stale npx cache
  or a malformed config). Say so plainly, suggest a session restart, and fall back to text-only
  source analysis.
- **`Chromium distribution 'chrome' is not found at /opt/google/chrome/chrome`** — a *channel*
  problem. Without `--browser chromium` the server targets the branded Google Chrome channel,
  which is not installed here. Restore that argument in `~/.claude.json` and restart the
  session. Do **not** run the `npx playwright install chrome` that the message suggests: it
  downloads a second, branded browser instead of using the Chromium that is already present.
- **`Browser "chrome-for-testing" is not installed`** — the one case where installing is
  correct. `--browser chromium` resolves to Playwright's Chrome-for-Testing build, and the
  cached build can fall out of step with `@playwright/mcp@latest`. Run
  `npx @playwright/mcp install-browser chrome-for-testing` (about 300 MB, one time). If a
  download is not acceptable, point the server at a build already in the cache instead:
  `--executable-path ~/.cache/ms-playwright/chromium-<build>/chrome-linux64/chrome`. Both are
  verified working.

Note that `--browser` officially advertises only `chrome, firefox, webkit, msedge`; `chromium`
is accepted and is what routes to Chrome-for-Testing. Config changes need a session restart,
because a running MCP server keeps the arguments it launched with.

That restart requirement is why `verify-mcp.py` sits next to this SKILL.md. It spawns the
configured server itself, speaks MCP over stdio, and drives a real browser, so you can prove a
fix works *before* asking the user to restart, and tell the difference between a broken config
and a stale one:

```bash
~/.claude/skills/browse/verify-mcp.py                        # browser only
~/.claude/skills/browse/verify-mcp.py http://localhost:3000  # also assert the page rendered
~/.claude/skills/browse/verify-mcp.py <url> -y @playwright/mcp@latest --browser chromium
```

The trailing arguments override the configured ones, so candidate fixes can be tested without
editing `~/.claude.json` first. Exit code 0 means every documented call succeeded.

In every case, note the failure in the writeup rather than quietly downgrading to source
reading and presenting the result as if you had looked at the page. Do not try to install or
launch some other browser daemon.

Do **not** hold a second persistent Chromium alongside Playwright's — a redundant long-lived
browser process has crashed WSL2/WSLg VMs in the past. Playwright MCP manages one browser; use it.

For the same reason, **do not use this skill inside a flow that runs its own browser.**
`bug-hunt` drives `research/tools/browser_crawl.py` and explicitly bans this skill; defer to
whatever engine the outer flow already owns rather than adding a second one.

## Getting a URL to browse: `serve.sh`

Never start a dev server by hand, and never assume port 3000 is yours.

`serve.sh` lives in this skill's own directory, next to this SKILL.md. Use that path; do not
hardcode someone else's home directory. If you do not have it, find it once:

```bash
SERVE=$(find ~/.claude ~/claude-skills -name serve.sh -path '*/browse/*' 2>/dev/null | head -1)
BASE=$("$SERVE" --dir /path/to/project)
```

It prints a base URL on stdout (diagnostics go to stderr) and follows three rules: **reuse
before you start, never take a port that is already in use, and never hand back a server
belonging to a different project.** In order, it will:

1. Probe 3000-3005, 4000, 4321, 5173, 5174, 8000, 8080, 8081 for a live HTTP server, over both
   IPv4 and IPv6. For each hit it resolves the listening pid's working directory and reuses the
   server **only if that directory is inside, or contains, `--dir`.** A server it cannot tie to
   your project is skipped, not reused. This is what stops you from testing an unrelated app on
   :3000 and reporting confidently wrong findings.
2. If nothing matching is serving, pick the first genuinely free port and start the project,
   auto-detecting the package manager from the lockfile (`pnpm-lock.yaml` → pnpm, `yarn.lock`
   → yarn, `bun.lock*` → bun, else npm) and the script from `package.json` (`dev`, else
   `start`, `serve`, `preview`). It sets both `PORT` and `--port`, because plenty of dev
   scripts hardcode a port and ignore the flag. A directory with no `package.json` but an
   `index.html` is served statically instead.
3. Poll on a real 90-second wall-clock deadline. If the script bound a different port than
   requested, it reads the actual port out of the server's own log and follows it there. If it
   lost a race for the port (`EADDRINUSE`), it retries on the next free one. If the server dies
   or times out, it dumps the last 20 log lines to stderr.

Flags: `--check` (report only, never start anything), `--port N` (try N first),
`--dir PATH` (project root, defaults to cwd), `--prod` (see below), `--any` (reuse a live
server even when its owner cannot be verified), `--stop` (stop only servers this script started).

Servers it starts are backgrounded with logs at `$TMPDIR/browse-dev-<port>.log` and the pid at
`$TMPDIR/browse-dev-<port>.pid`. **Only ever kill a server whose pidfile this script wrote** —
a reused server belongs to the user and killing it will wreck their session. Use `--stop`
rather than `kill` by hand: it kills the process group, so dev-server children die too.

If the script reports it cannot determine which ports are free, it exits rather than guessing.
Do not work around that by starting a server yourself.

**Monorepos:** point `--dir` at the specific app package, not the workspace root. The root
usually has no runnable app of its own, and `dev` there may start something you did not mean
to test. The script warns when `--dir` looks like a workspace root.

### Testing against a production build: `--prod`

`--prod` runs the project's `build` script, then serves the result with `start`/`preview`
instead of `dev`. It deliberately does **not** reuse an existing server, because a live server
cannot be distinguished from a dev server and reusing one would quietly invalidate the point of
asking for prod. Builds get a 10-minute budget.

Reach for it whenever the finding depends on production behavior: performance and Core Web
Vitals, bundle size, hydration errors, image optimization, caching headers, minified error
messages, or anything behind `NODE_ENV`. Dev-server numbers are not evidence about production
(see "What counts as a finding"), and `--prod` is how you stop disclaiming and actually check.

## Command reference (Playwright MCP)

Map the intent you want to the Playwright MCP tool:

| Intent | Playwright MCP tool |
|--------|---------------------|
| Set viewport (do this first, every session) | `mcp__playwright__browser_resize` |
| Navigate to a URL | `mcp__playwright__browser_navigate` |
| Snapshot DOM / accessibility tree | `mcp__playwright__browser_snapshot` |
| **Find one element without a full snapshot** | `mcp__playwright__browser_find` |
| **Wait for text/state to appear** | `mcp__playwright__browser_wait_for` |
| Click an element | `mcp__playwright__browser_click` |
| Type into a single field | `mcp__playwright__browser_type` |
| Fill a whole form at once | `mcp__playwright__browser_fill_form` |
| Choose from a `<select>` | `mcp__playwright__browser_select_option` |
| Hover (menus, tooltips) | `mcp__playwright__browser_hover` |
| Drag and drop | `mcp__playwright__browser_drag` / `browser_drop` |
| **Accept/dismiss a native dialog** | `mcp__playwright__browser_handle_dialog` |
| Upload a file | `mcp__playwright__browser_file_upload` |
| Take a screenshot | `mcp__playwright__browser_take_screenshot` |
| Keyboard / press a key (e.g. Tab) | `mcp__playwright__browser_press_key` |
| Read console messages / JS errors | `mcp__playwright__browser_console_messages` |
| Inspect network requests the page made | `mcp__playwright__browser_network_requests` |
| **Issue one request directly (probe an API)** | `mcp__playwright__browser_network_request` |
| Browser back | `mcp__playwright__browser_navigate_back` |
| List / switch / open tabs (rarely — see "One tab") | `mcp__playwright__browser_tabs` |
| Evaluate JS in the page | `mcp__playwright__browser_evaluate` |
| Close the browser when all browser work is done | `mcp__playwright__browser_close` |

`browser_run_code_unsafe` also exists: it runs arbitrary Playwright client code against the
live session, bypassing the guardrails of the tools above. `browser_evaluate` covers almost
every real need. Reach for the unsafe variant only for something genuinely unreachable
otherwise (custom waits, multi-step trace capture), never on a page holding a real user's
authenticated session.

Recommended per-session order: **serve.sh → resize → navigate → snapshot** before interacting,
so element handles from the snapshot are current. That is a *per-session* order, not a
per-page one: after the first setup you keep navigating the same tab (see "One tab, kept open"),
and you do not re-resize unless the viewport actually needs to change.

`browser_network_request` is the one to reach for when you want to check an endpoint's status,
shape, or auth behavior without navigating away and losing page state. `browser_find` is the
cheap alternative to a full snapshot when you already know what you are looking for.

### Standard viewports

Resize before the first navigation, and use these unless the task names its own. Consistent
sizes are what make screenshots comparable between runs and between personas.

| Name | Size | Use for |
|------|------|---------|
| mobile | 390 x 844 | iPhone-class; the default for anything "on my phone" |
| tablet | 768 x 1024 | breakpoint boundary, portrait |
| desktop | 1440 x 900 | the default for general review |
| wide | 1920 x 1080 | only when testing max-width / ultrawide layout |

## One tab, kept open

**The default is a single tab that stays open for the whole run, re-pointed at whatever URL you
need next.** Opening a tab per page, or closing the browser between checks, is the wrong shape
for this skill. It is slower, it throws away everything worth keeping, and it produces findings
that are wrong in ways that are hard to notice.

What a fresh tab or a fresh browser costs you:

- **Login state and app state.** A new browser means logging in again. A new tab keeps cookies
  but loses in-page state — a half-filled form, an open modal, a client-side route, scroll
  position, a populated store.
- **The evidence buffers.** `browser_console_messages` and `browser_network_requests` report
  what the *current page context* has accumulated. Churning tabs and browsers empties them, so
  the errors you were about to report vanish.
- **Dev-server warmth.** Every navigation to a route the server has already compiled is nearly
  free; a cold start re-pays the compile. Reusing the tab is also what keeps the compile graph
  from being rebuilt over and over.
- **Viewport.** A new browser is back to the default size, and comparing a screenshot taken at
  the default against one taken at 1440x900 is a phantom layout finding.

So, in practice:

- **Change the URL, do not open a tab.** `browser_navigate` on the tab you already have is the
  normal way to move between pages. Same for going back — `browser_navigate_back`, not a new tab.
- **Prefer clicking the app's own links** over typing a URL when the point is to test the flow.
  Navigating directly skips the client-side transition, which is exactly where the bug often is.
  Type a URL when you want to test that route in isolation, or to jump past a flow you have
  already exercised.
- **Do not close the browser between checks.** `browser_close` is for the end of all browser
  work in the session, not the end of a page. If more browsing might follow — another persona,
  a re-check after a fix, the user's next question — leave it open.
- **Re-navigating is not a reset.** The tab keeps cookies, storage, and the session. If you
  actually want a clean slate, clear it deliberately (logout route, or `browser_evaluate` on
  `localStorage`/`sessionStorage`) rather than assuming a navigation did it for you.
- **Re-snapshot after each navigation.** Element refs do not survive it. This is the one thing
  you must repeat per page; see "Reliability rules".

When a second tab genuinely is the right tool — open one, and close it when done:

- The app itself opened it (`target="_blank"`, an OAuth popup, a payment window). Switch to it
  with `browser_tabs`, do the work, close it, and switch back.
- You need two states side by side that cannot coexist in one tab: two accounts mid-flow, a
  before/after comparison, a page you must not navigate away from while checking another.
- Concurrent subagents are browsing at once — see "Session state and parallel personas".

And when you only want to *inspect* something rather than visit it, do not navigate at all:
`browser_network_request` hits an endpoint and returns the response without touching the page,
so status, shape, and auth checks cost you no state.

## Reliability rules

Most bogus browser findings come from asserting against a page that was not ready, or from
acting on a stale handle. These rules prevent nearly all of it:

- **Re-snapshot after anything that changes the DOM.** Element refs from a snapshot are
  positional and go stale the moment the page navigates, re-renders, or opens a modal. Acting
  on a stale ref either errors or, worse, hits the wrong element.
- **Never conclude "it's broken" from the first snapshot after a click.** SPA routes, data
  fetches, and skeleton states resolve asynchronously. Use `browser_wait_for` on the text or
  state you expect, and only report a failure if the wait itself times out. "Button does
  nothing" is the single most common false positive in this skill's output.
- **The first hit on any route in dev mode is slow.** Next and Vite compile per route on
  demand, so a first navigation to a deep route can take many seconds even though the root
  answered instantly. `serve.sh` only waits for `/`. Treat a slow or blank first load of a new
  route as cold compilation: `browser_wait_for` the content, or warm it with
  `browser_network_request` first. Never report a first-visit timeout as a bug without a
  second visit to confirm, and never quote a first-visit load time as a performance number.
- **A dev server that vanishes mid-run is usually not an app crash.** A browser plus one or
  more dev servers can exhaust memory on a WSL2 host, and the kernel kills whatever is
  convenient. The tell is a log that ends in `[ELIFECYCLE] Command failed.` straight after a
  successful request, or several unrelated servers dying at once. Re-run `serve.sh`, close
  browsers you are done with, and do not report it as a defect in the app without a
  reproduction. `serve.sh` never kills a server it did not start, so it is not the culprit.
- **A native `alert`/`confirm`/`prompt` blocks every subsequent call.** If tools start hanging
  or erroring right after a click, a dialog is open. Clear it with `browser_handle_dialog`.
- **Clear the interstitials before judging a page.** Cookie banners, newsletter modals, and
  onboarding tours will otherwise dominate every screenshot and every accessibility snapshot,
  and get reported as layout bugs.

## Getting past a login wall

Most real flows are behind auth, and guessing at it wastes a whole run. Before starting:

- **Find the credentials rather than inventing them.** Check `.env.example`, `.env.local`,
  `README`, and any seed or fixture script (`prisma/seed.*`, `scripts/seed*`,
  `docker-compose.yml`) for a test account. If there is genuinely no test account, ask the user
  for one instead of burning the run on a wall you cannot pass, and say which flows you skipped.
- **Never use real user credentials, and never register a real third-party account** (payment,
  OAuth to a live provider, an SMS-verified number) to get through a signup flow. Stop and ask.
- **Log in once.** The Playwright MCP browser keeps cookies for the whole session, so the login
  survives subsequent navigations, tabs, and subagents. Do it once at the start rather than per
  flow, and verify it took by snapshotting a known logged-in element before proceeding.
- **Check the auth state you are actually in before every judgment.** A session that silently
  expired, or a leftover login from a previous persona, turns into phantom findings in both
  directions: "this page is public" when you were logged in, or "I got redirected" when you were
  not. If a page surprises you, confirm the session first.
- **Test logged-out deliberately, not accidentally.** Clear state (`browser_evaluate` on
  `localStorage`/`sessionStorage` plus a logout route) rather than assuming a fresh tab is
  anonymous. Tabs do not isolate cookies.

## Session state and parallel personas

The Playwright MCP server holds **one browser, shared by everything in the session**. State
persists between calls and across subagents: cookies, login session, viewport, current URL,
scroll position.

This matters most for the fan-out flows. `user-test` runs its personas as concurrent `Agent`
subprocesses, and they are *not* isolated at the browser layer — if Mobile Tapper calls
`browser_resize` to 390px while Careful Reader is mid-flow, Careful Reader is now silently
looking at the mobile layout and will report phantom findings.

So:

- **Serialize anything viewport-sensitive.** Personas with different viewports must run one at
  a time, not in parallel. Only run personas concurrently when they share a viewport and do not
  depend on login state.
- **Give concurrent work its own tab** via `browser_tabs`, and re-select the tab before each
  action. Tabs isolate URL and scroll, but *not* cookies or viewport. This is the exception to
  "One tab, kept open" — one tab *per concurrent worker*, held for that worker's whole run and
  re-navigated within it, not one per page. A worker closes only its own tab, and never calls
  `browser_close` while another worker is still browsing.
- **Reset state between personas.** A fresh persona should not inherit the previous one's login
  session. Navigate to a logout route, or clear storage with `browser_evaluate`, before starting.
- **State from a prior turn is still live.** Do not assume you start on a blank page; navigate
  explicitly.

## Keeping the run affordable

Snapshots and screenshots are the two things that blow up context on a long run. Neither
warrants being stingy about evidence; both warrant not collecting evidence twice.

- **Snapshot to orient, `browser_find` to locate.** A full accessibility snapshot of a large
  page is expensive. Take one when you need the layout of the page, and use `browser_find` when
  you already know the element you want.
- **Use the snapshot's own limiters.** `browser_snapshot` takes `depth` (cap the tree),
  `target` (scope to one element or selector), and `filename` (write the snapshot to a file
  instead of returning it inline). For a big page, `depth: 3` gives you the structure for a
  fraction of the tokens; `target` on a known container beats snapshotting the document.
  `browser_console_messages` takes the same `filename`, plus `level` — ask for `error` rather
  than filtering a full `info` dump by hand.
- **Viewport screenshots by default.** Take a full-page screenshot only when the question is
  about layout, spacing, or long-scroll behavior.
- **Read each screenshot once.** You need to look at it to write it up, but re-reading the same
  PNG later adds nothing; refer back to what you already described.
- **Do not screenshot what you are not going to reference.** One image per meaningful state
  beats one per click.

## Screenshot conventions

- Write screenshots to the session scratchpad directory, never into the user's repo, where they
  would show up as untracked files in their next `git status`.
- **Pass absolute paths.** A bare filename is resolved relative to the MCP server's working
  directory, and the server drops its output into a `.playwright-mcp/` folder there. Started
  from a repo, that quietly litters the repo. This applies to every tool that takes a
  `filename`, including `browser_snapshot` and `browser_console_messages`, not just screenshots.
- Prefix each file with the tester/context id: `t1-`, `t2-`, `tech-`, `adv-`.
- Zero-pad a sequence number and add a short semantic label:
  `t1-01-landing.png`, `t1-02-form-error.png`, `t1-03-confirmation.png`.
- Always `Read` the PNG you captured so you can actually see it when writing up findings. A
  screenshot you did not look at is not evidence.

## What counts as a finding

Console and network output from a dev server is noisy. Report signal, not volume:

- **Console:** report `error` level, and `warning` only when it names a real defect (failed
  prop types, accessibility violations, deprecation that will break on upgrade). Ignore
  dev-only noise: HMR/Fast Refresh chatter, source-map warnings, React DevTools nags, and
  hydration warnings that do not reproduce in a production build.
- **Network:** report 4xx and 5xx on requests the app itself made. Ignore expected 401s on
  pre-login probes, 404s for optional assets like `favicon.ico`, and anything from a third-party
  script the app does not control.
- **Attribute honestly.** Label each finding `[OBSERVED]` when you saw it in the browser and
  `[INFERRED]` when you reasoned it from source. Never present the second as the first.
- **Dev mode is not production.** Performance timings, bundle sizes, and hydration behavior from
  a dev server are not evidence about production. Re-check with `serve.sh --prod` before
  reporting any of them, or label the finding as unverified against a real build.

## Not running the machine out of memory

This is the failure mode that has actually taken this box down, so it gets its own rules.

A dev server driven by an automated browser is not the same workload as a human clicking
around. Turbopack (the default for `next dev` since Next 16) keeps an incremental compilation
graph in memory, and every fresh route an agent visits pulls more of the app into it. Nothing
evicts it. On 2026-07-19 a `next-server` reached **15.9GB RSS / 68GB virtual** after ~2 hours
of automated browsing across a 123-route app, tripped the kernel's *global* OOM killer, and
WSL shut the whole distro down mid-session — taking the VS Code session with it.

`serve.sh` now caps the heap of every server it starts (4096MB default, `BROWSE_HEAP_MB` to
override). That contains the blast radius; it does not remove the need for discipline:

- **Check before a long run.** `free -g` — if available memory is already under ~8GB, say so
  and stop rather than starting a browser on top of it.
- **Watch the server you started.** On any run that crosses ~50 page loads, check it:
  `ps -o rss=,comm= -p "$(cat /tmp/browse-dev-*.pid 2>/dev/null)"`. Past ~4GB RSS, restart it
  before continuing. A restart costs one warm-up compile; an OOM costs the whole session.
- **A dev server dying mid-run is a memory event until proven otherwise.** Do not just restart
  it and carry on — check `dmesg -T | tail -30` for `Out of memory: Killed process`. If that is
  what happened, report it as an environment failure and say which findings were lost. Silently
  restarting hides the thing the user most needs to know.
- **Never run more than one dev server at a time.** Two servers on one large app is most of the
  way to the ceiling before the browser has loaded a single page. `serve.sh --stop` the first.
- **Prefer `--prod` for long sweeps.** A production build has a flat memory profile and no
  compilation graph. If the run does not specifically need HMR or dev-only errors, use it —
  it is both safer and more honest about real behavior.
- **Turbopack's on-disk cache grows too.** `.next/dev/cache` reached 3.5GB on one project and
  14GB on another. If disk is tight, `rm -rf <project>/.next/dev` is safe and fully
  regenerable — but mention it rather than deleting silently.

## Finishing up

- **Close the browser** with `browser_close` once **all** browser work is done — the end of the
  task, not the end of a page, and not between checks that a single tab could have carried (see
  "One tab, kept open"). Leaving Chromium resident across unrelated work is what has crashed
  WSL2/WSLg VMs before, so the rule is: keep exactly one browser for as long as you are still
  browsing, then close it rather than letting it idle into the next, unrelated piece of work.
  If you expect the user to ask a follow-up about the same page, say the browser is still open
  instead of closing and silently re-opening later.
- **Stop only your own servers**, with `serve.sh --stop`. If the run reused the user's existing
  dev server, leave it exactly as you found it. Leaving a capped-but-idle dev server resident
  after a run is how the *next* session starts already halfway to the memory ceiling.
- **Say which surfaces you did not reach** (login-walled, paywalled, needing real payment or a
  third-party account). An unreported gap reads as "checked and fine".

## Fallback (no Playwright MCP)

If Playwright MCP is unavailable: analyze the relevant source (routes, components, handlers)
directly, describe expected behavior, and **state prominently** that this was a text-only
review with no live browser — findings are inferred, not observed.
