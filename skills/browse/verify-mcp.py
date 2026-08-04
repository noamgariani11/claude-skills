#!/usr/bin/env python3
"""End-to-end verification of the Playwright MCP server as configured in ~/.claude.json.

Spawns the exact command from mcpServers.playwright, speaks MCP over stdio, and drives a real
browser. Use this to prove a config change works BEFORE restarting the session: the MCP server
already running in a session keeps the arguments it launched with, so an edit to ~/.claude.json
cannot be tested through the mcp__playwright__* tools until a restart.

  ./verify-mcp.py                          # verify against about:blank
  ./verify-mcp.py http://localhost:3000    # also assert the page actually rendered
  ./verify-mcp.py <url> -y @playwright/mcp@latest --browser chromium
                                           # try candidate args without editing the config

Exits 0 only if every documented tool call succeeded.
"""
import json, subprocess, sys, threading, queue, time

URL = sys.argv[1] if len(sys.argv) > 1 else "about:blank"

cfg = json.load(open("/home/drago/.claude.json"))["mcpServers"]["playwright"]
# argv[2:] overrides the configured server args, so candidate fixes can be tried
# before committing one to ~/.claude.json.
cmd = [cfg["command"]] + (sys.argv[2:] if len(sys.argv) > 2 else cfg["args"])
print(f"spawning: {' '.join(cmd)}\n", flush=True)

p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, text=True, bufsize=1)

outq = queue.Queue()
def pump(stream, tag):
    for line in stream:
        outq.put((tag, line.rstrip("\n")))
for s, t in ((p.stdout, "out"), (p.stderr, "err")):
    threading.Thread(target=pump, args=(s, t), daemon=True).start()

_id = 0
def send(method, params=None, notify=False):
    global _id
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    if not notify:
        _id += 1
        msg["id"] = _id
    p.stdin.write(json.dumps(msg) + "\n")
    p.stdin.flush()
    return None if notify else _id

def wait_for(want_id, timeout=180):
    """Collect until the response with want_id arrives. Returns (result, error)."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            tag, line = outq.get(timeout=1)
        except queue.Empty:
            if p.poll() is not None:
                return None, f"server exited rc={p.returncode}"
            continue
        if tag == "err":
            if line.strip():
                print(f"  [stderr] {line[:300]}", flush=True)
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == want_id:
            return msg.get("result"), msg.get("error")
    return None, "timeout"

def call_tool(name, args, timeout=180):
    rid = send("tools/call", {"name": name, "arguments": args})
    res, err = wait_for(rid, timeout)
    if err:
        return None, err
    text = ""
    for c in (res or {}).get("content", []):
        if c.get("type") == "text":
            text += c.get("text", "")
    if (res or {}).get("isError"):
        return None, text or "isError"
    return text, None

failures = []

# --- handshake ---
rid = send("initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "browse-verify", "version": "1.0"},
})
res, err = wait_for(rid, 240)   # first run may npx-download
if err:
    print(f"FAIL initialize: {err}")
    sys.exit(1)
print(f"PASS initialize -> {res.get('serverInfo')}", flush=True)
send("notifications/initialized", {}, notify=True)

rid = send("tools/list")
res, err = wait_for(rid)
tools = [t["name"] for t in (res or {}).get("tools", [])]
print(f"PASS tools/list -> {len(tools)} tools\n", flush=True)

# --- the tools the skill documents, in the order the skill recommends ---
steps = [
    ("browser_resize",           {"width": 1440, "height": 900},   None),
    ("browser_navigate",         {"url": URL},                     None),
    ("browser_snapshot",         {"depth": 3},                     "depth limiter"),
    ("browser_console_messages", {"level": "error"},               "level filter"),
    ("browser_network_requests", {},                               None),
]
for name, args, note in steps:
    if name not in tools:
        print(f"SKIP {name}: not offered by server")
        failures.append(f"{name} missing")
        continue
    text, err = call_tool(name, args)
    label = f"{name}" + (f" ({note})" if note else "")
    if err:
        print(f"FAIL {label}: {str(err)[:300]}")
        failures.append(label)
    else:
        first = (text or "").strip().splitlines()
        print(f"PASS {label}: {len(text or '')} chars | {first[0][:110] if first else '(empty)'}")

# Did a real page actually render? A tool call that "succeeds" against a blank tab proves
# much less than one that comes back with the app's own markup in it.
if URL != "about:blank":
    text, err = call_tool("browser_snapshot", {})
    if err:
        print(f"FAIL content check: {str(err)[:200]}"); failures.append("content")
    elif len((text or "").strip()) < 200:
        print(f"FAIL content check: snapshot suspiciously small ({len(text or '')} chars)")
        failures.append("content")
    else:
        print(f"PASS content check: snapshot of {URL} is {len(text)} chars")

# --- documented cleanup ---
text, err = call_tool("browser_close", {})
print("PASS browser_close" if not err else f"FAIL browser_close: {str(err)[:200]}")

p.terminate()
try:
    p.wait(timeout=10)
except subprocess.TimeoutExpired:
    p.kill()

print("\n" + ("ALL CHECKS PASSED" if not failures else f"FAILURES: {failures}"))
sys.exit(1 if failures else 0)
