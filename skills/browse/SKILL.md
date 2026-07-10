---
name: browse
description: |
  Drive a real browser to inspect and interact with a local or remote web app — set the
  viewport, navigate, snapshot the DOM/accessibility tree, click and fill elements, take
  screenshots, and read the console + network for errors. Built on Playwright MCP with a
  text-from-source fallback when no browser tool is available. This is the standalone
  browser driver used by the user-test, bug-hunt, security-dude, and designer-dude flows.
  Use when asked to "browse", "open the page", "screenshot the app", "check the console",
  "click through the flow", or to visually verify a UI change in a real browser.
---

# browse — standalone browser driver

A dependency-free way to drive a browser for inspection and testing. **Playwright MCP is the
only engine.** There is no separate binary and no `./setup` step — if Playwright MCP is not
available in the session, fall back to a text-only analysis from source and say so loudly.

## Detecting what's available

```bash
# If mcp__playwright__* tools are present in this session, use them — that is the driver.
# If they are NOT present, do NOT try to install or launch any other browser daemon.
# Fall back to reading the source directly and flag the limitation in your output.
```

Do **not** hold a second persistent Chromium alongside Playwright's — a redundant long-lived
browser process has crashed WSL2/WSLg VMs in the past. Playwright MCP manages one browser; use it.

## Command reference (Playwright MCP)

Map the intent you want to the Playwright MCP tool:

| Intent | Playwright MCP tool |
|--------|---------------------|
| Set viewport (do this first per persona) | `mcp__playwright__browser_resize` |
| Navigate to a URL | `mcp__playwright__browser_navigate` |
| Snapshot DOM / accessibility tree | `mcp__playwright__browser_snapshot` |
| Click an element | `mcp__playwright__browser_click` |
| Fill a form field | `mcp__playwright__browser_fill_form` |
| Take a screenshot | `mcp__playwright__browser_take_screenshot` |
| Keyboard / press a key (e.g. Tab) | `mcp__playwright__browser_press_key` |
| Read console messages / JS errors | `mcp__playwright__browser_console_messages` |
| Inspect network requests | `mcp__playwright__browser_network_requests` |
| Browser back | `mcp__playwright__browser_navigate_back` |
| Evaluate arbitrary JS in the page | `mcp__playwright__browser_evaluate` |

Recommended per-session order: **resize → navigate → snapshot** before interacting, so element
handles from the snapshot are current. Re-snapshot after any navigation or DOM-changing action.

## Screenshot conventions

- Prefix each file with the tester/context id: `t1-`, `t2-`, `tech-`, `adv-`.
- Zero-pad a sequence number and add a short semantic label:
  `t1-01-landing.png`, `t1-02-form-error.png`, `t1-03-confirmation.png`.
- Always `Read` the PNG you captured so you can actually see it when writing up findings.

## Fallback (no Playwright MCP)

If Playwright MCP is unavailable: analyze the relevant source (routes, components, handlers)
directly, describe expected behavior, and **state prominently** that this was a text-only
review with no live browser — findings are inferred, not observed.
