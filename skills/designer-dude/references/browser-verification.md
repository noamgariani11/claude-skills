# Verifying in a real browser - the `browse` arm of this skill

For configured status announcements, APG widget contracts, text expansion,
RTL, color-vision screenshots, cross-engine runs, and artifact baselines, also
load `behavioral-verification.md`. Those checks extend this session order; they
do not replace the manual keyboard and assistive-technology pass.

The probe reads the DOM in its rest state. It cannot hover, tab, press, scroll
or wait, so a whole class of defect is invisible to it and to every screenshot
taken alongside it. **This file is the part of designer-dude that drives a real
browser to see those.** Load it for Mode D §2c, for any campaign round, and any
time a finding is about something that only exists while a pointer or a key is
on the element.

Everything here goes through the **`browse` skill**. Load it (`Skill: browse`)
rather than reaching for Playwright yourself: it owns the MCP wiring, the dev
server, the viewport table and the memory rules, and hand-rolling around it is
what once drove a dev server to 15.9GB and took the machine down.

---

## 0. Where the browser is required - and where it is merely available

The test is always the same: **does the answer exist only in the rendering?**
If source, the probe payload, or `micro-checks.sh` settles it, settle it there.
A browser opened to read copy, confirm a token, or re-shoot a surface you did
not change is pure cost - and on a long campaign that cost is memory, which is
the one failure that ends the session (§5).

### Required - skipping these makes the review wrong

| Mode / step | What the browser is for | Where it says so |
|---|---|---|
| **D - §2b measure** | `serve.sh` for the URL (`--prod` for anything about performance), then `probe-runner.mjs` in that browser. | `mode-d-review.md` §2b |
| **D - §2c states** | The four-part state pass below. Interaction cannot be graded above B without it. | `mode-d-review.md` §2c |
| **D - §0 login** | Log in once; the MCP browser keeps the session for the whole run, subagents included. | `mode-d-review.md` §0 |
| **D - dark pass** | Hover and focus in the other theme, plus the chrome the page does not paint. | `color.md` §5 |
| **D/F - fix verification** | Re-exercise the states after each fix. A screenshot diff compares two rest states and sees nothing. | `regression.md` §7 |
| **F - every round** | Same as D, per round. A campaign of rest-state screenshots is how an A+ lands on a dead hover. | `mode-f-campaign.md` guard 8 |
| **Enterprise surfaces** | Loading, empty, error, partial, stale, permission-denied - reached by clicking, not by reading. Console and network after each. | `enterprise.md` state table |

### Discretionary - one budgeted pass, only when it changes the answer

| Mode / step | Open it when | Skip it when |
|---|---|---|
| **A - direction, intake** | The reference's *craft* is the question - its measure, its type scale, the weight of its hover. Screenshot at 1440 and 390; probe it when the question is systemic. | The user already said what they admire and why, or the reference is a well-known product whose direction is not in dispute. |
| **A / E - shotgun variants** | Always, before presenting variants - an unrendered variant is a guess about a variant. Serve `design-explore/{date}` once and shoot them all in that session. | Never skip entirely; do batch it into a single pass over all variants plus the comparison board. |
| **B - logo** | The mark is finished enough to test. Five of the seven survival tests are questions about rendering: 16px favicon, single colour, inverted, blurred, in an icon row. | The work is still a brief - `LOGO-BRIEF.md` with no SVG has nothing to render. |
| **C - plan review** | The plan's merit turns on what the current surface does. One navigation, one screenshot, close. | The plan is structural and the current page reads fine from source. |
| **Calibration** | A hover, motion or density threshold is being set or changed - those are calibrated by looking at a reference product's hover. | The anchor is a static metric; `--url` runs it headless with no MCP browser at all. |

If a required step was skipped, say which and why. "Reviewed the pages I could
reach" is honest; presenting it as a full review is not. A discretionary step
you skipped needs one clause, not an apology.

### The budget

**One browser session per round.** Plan the pass before you open it, then do
all of it while it is up: every viewport, both themes, the state pass on every
repeated component, the app states, the after-shots. Then `browser_close`.

Three separate opens in one round means the pass was not planned. Re-navigating
to a surface you already captured, at a viewport you already captured, to check
something the probe JSON on disk already contains, is the specific waste this
budget exists to stop - read the JSON.

---

## 1. Get a URL - never start a server by hand

```bash
BASE=$(~/.claude/skills/browse/serve.sh --dir /abs/path/to/project)
```

It reuses a live server **only** when that server's working directory actually
belongs to the project under test, otherwise it picks a verified-free port and
caps the Node heap of what it starts. `--prod` builds and serves a production
bundle, which is required before quoting any performance number and useful when
the finding depends on minification or `NODE_ENV`.

Stop only what you started: `serve.sh --stop`. A reused server belongs to the
user.

**Do not run `next build` while a dev server from the same project is up.** They
share `.next`, and the dev server dies mid-run. That looks exactly like an OOM
kill and will send you reading `dmesg` for nothing. Build first, or stop the
server first.

---

## 2. Session order

```
serve.sh  →  browser_resize  →  browser_navigate  →  browser_snapshot
```

Resize *before* the first navigation so the page lays out at the size you are
grading. Standard viewports come from `browse`: 390×844 mobile, 768×1024
tablet, 1440×900 desktop, 1920×1080 wide.

Re-snapshot after anything that changes the DOM; element refs go stale. Never
conclude "it's broken" from the first snapshot after a click - `browser_wait_for`
the thing you expect and report a failure only if the wait times out. The first
hit on any route in dev mode is a cold compile, so it is not a performance
number and a timeout there is not a bug.

### When the browser is locked by another session

`Browser is already in use for .../mcp-chrome-for-testing-<hash>` usually means
a previous session died holding the profile lock, not that a browser is really
running. Check before doing anything drastic:

```bash
ls -la ~/.cache/ms-playwright-mcp/mcp-chrome-for-testing-<hash>/SingletonLock
# -> symlink to <host>-<pid>.  If that pid is gone, the lock is stale:
rm -f ~/.cache/ms-playwright-mcp/mcp-chrome-for-testing-<hash>/Singleton{Lock,Cookie,Socket}
```

Only when the pid is genuinely dead. If a live Chromium holds it, it belongs to
another session - use `probe-selftest.mjs --url <url> --out <file>`, which
launches its own throwaway browser, rather than killing someone else's.

---

## 3. The state pass - the reason this file exists

**Required on every Mode D run, and Interaction may not be graded above B
without it.** For every *repeated* interactive component on the surface - list
row, card, nav item, tab, table row, chip - take the second instance, not the
first (the first is often styled specially; the second is what the template
really does) and do all four:

| Drive | Look for |
|---|---|
| `browser_hover` the element, then screenshot its **container** | Does the paint change at all? Does the fill cover the whole hit area? Does it have margins, or does it stop at the glyph? Does it eat the separator above it? |
| `browser_press_key` Tab until it is focused | Is there a ring? Does it clear both the control and the page behind it? Is it clipped by an `overflow: hidden` ancestor? |
| Hold the pointer down (`browser_click` and screenshot mid-flight, or check for an `:active` rule) | Does anything move or darken? Touch has no hover; without an active state a tap feels dead. |
| Re-run the hover in the **other theme** | A tint chosen against paper is routinely invisible on the dark surface, and vice versa. |

Screenshot the container rather than the element: the defect is usually the
relationship between the fill and its neighbours, and an element-scoped
screenshot crops exactly that away.

### What the eye catches here that the probe cannot

The probe now measures the automatable half (`states.inertHoverFills`,
`hueOnlyHoverFills`, `inertHoverBorders`, `hoverFillsCoveringOwnRule`,
`hoverFillsWithoutPadding`). Every one of those was added *after* a human
looked at a hover and said "that's wrong" - which is the honest description of
what this pass is for. Still yours alone:

- Whether the tint is the right *colour* for the brand, not merely a different one.
- Whether the band's radius agrees with the rest of the system.
- Whether the transition duration feels like feedback or like lag.
- Whether the row's hover competes with a selected or current state.
- Whether hovering the row and hovering a control inside it are distinguishable.

---

## 4. Screenshot hygiene

- **Absolute paths, into the session scratchpad.** A bare filename lands in the
  MCP server's working directory - which is the user's repo - and shows up as
  untracked files in their next `git status`. If the MCP server refuses paths
  outside the project root, write into the repo and **delete the files plus any
  `.playwright-mcp/` directory before finishing**.
- Prefix and number: `dd-01-services-rest.png`, `dd-02-services-hover.png`.
- One image per meaningful state. Read each one - a screenshot you did not look
  at is not evidence.
- Pair them: rest and hover of the same component, in the same crop, so the
  before/after in the report is a comparison rather than an assertion.

---

## 5. Memory discipline

From `browse`, and not optional on a long review:

- `free -g` first. Under ~8GB available, say so and stop.
- One dev server at a time. Past ~50 page loads, check it:
  `ps -o rss=,comm= -p "$(cat /tmp/browse-dev-*.pid)"`. Past ~4GB RSS, restart.
- A dev server that dies mid-run is a memory event until `dmesg -T | tail -30`
  proves otherwise. Do not silently restart and carry on - a restart hides an
  environment failure that invalidates whatever you measured around it.
- `browser_close` when done.

---

## 6. Report honestly

Tag every finding `[OBSERVED]` (you saw it in the browser) or `[INFERRED]` (you
reasoned it from source), and never present the second as the first. Say which
surfaces you could not reach - login-walled, paywalled, needing a real account.
An unreported gap reads as "checked and fine".
