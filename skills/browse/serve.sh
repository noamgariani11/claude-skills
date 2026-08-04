#!/usr/bin/env bash
# browse/serve.sh — resolve a base URL to browse WITHOUT ever stealing a port,
# and without ever handing back a server that belongs to a different project.
#
#   ./serve.sh                    # find or start a dev server, print its base URL
#   ./serve.sh --dir /path/proj   # project root (default: $PWD)
#   ./serve.sh --check            # only report what is already live, never start anything
#   ./serve.sh --port 3005        # prefer this port
#   ./serve.sh --prod             # build, then serve the production build (not `dev`)
#   ./serve.sh --any              # reuse a live server even if it can't be tied to --dir
#   ./serve.sh --stop             # stop only the servers THIS script started
#
# Prints the base URL on stdout. All diagnostics go to stderr.
set -uo pipefail

PROJECT_DIR="${PROJECT_DIR:-$PWD}"
CHECK_ONLY=0
STOP=0
ANY=0
PROD=0
WANT_PORT=""
# Common dev-server defaults, in the order we would rather use them.
SCAN_PORTS=(3000 3001 3002 3003 3004 3005 4000 4321 5173 5174 8000 8080 8081)

# Discovery probes must be cheap: we may make one per candidate port.
PROBE_MAX_TIME=8
# A cold Next/Vite route can take a while to compile on the very first hit.
COLD_MAX_TIME=25
# Total wall-clock budget for a freshly started server to answer.
START_DEADLINE=90
# A production build is a different order of magnitude from starting `dev`.
BUILD_DEADLINE=600
# How many times we retry on a different port after losing a port race.
START_ATTEMPTS=3

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) CHECK_ONLY=1; shift ;;
    --stop)  STOP=1; shift ;;
    --any)   ANY=1; shift ;;
    --prod)  PROD=1; shift ;;
    --port)  WANT_PORT="$2"; shift 2 ;;
    --dir)   PROJECT_DIR="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

TMP="${TMPDIR:-/tmp}"
log() { echo "[serve] $*" >&2; }

# --- port probing --------------------------------------------------------------
# Fails LOUD, never open: if we cannot tell whether a port is busy we must not
# start a server on top of it.
PROBE=""
if   command -v ss   >/dev/null 2>&1; then PROBE=ss
elif command -v lsof >/dev/null 2>&1; then PROBE=lsof
elif [[ -r /proc/net/tcp ]];           then PROBE=proc
else
  log "FATAL: no ss, no lsof, no /proc/net/tcp — cannot determine which ports are free."
  log "Refusing to guess. Install iproute2, or pass an explicit URL instead of using this script."
  exit 2
fi

# Listening ports, one per line. Computed fresh on each call.
listening_ports() {
  case "$PROBE" in
    ss)   ss -ltn 2>/dev/null | awk 'NR>1 {n=split($4,a,/[:.]/); print a[n]}' ;;
    lsof) lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {n=split($9,a,":"); print a[n]}' ;;
    proc) awk '$4=="0A" {split($2,a,":"); print strtonum("0x" a[2])}' \
            /proc/net/tcp /proc/net/tcp6 2>/dev/null ;;
  esac
}

port_busy() { listening_ports | grep -qx "$1"; }

# HTTP status code from a port, or empty. $2 overrides the timeout.
# Tries IPv4 and then IPv6: a server bound only to ::1 is invisible to 127.0.0.1,
# and would otherwise look like "busy but not HTTP" and be skipped forever.
port_http() {
  local port="$1" t="${2:-$PROBE_MAX_TIME}" code
  for host in 127.0.0.1 '[::1]'; do
    code="$(curl -s -o /dev/null -w '%{http_code}' \
            --connect-timeout 2 --max-time "$t" \
            "http://$host:$port/" 2>/dev/null)"
    if [[ "$code" =~ ^[2345] ]]; then echo "$code"; return 0; fi
  done
  echo "$code"
}

# --- --stop: only ever kill what we started ------------------------------------
if [[ "$STOP" == "1" ]]; then
  found=0
  for pf in "$TMP"/browse-dev-*.pid; do
    [[ -e "$pf" ]] || continue
    pid="$(cat "$pf" 2>/dev/null)"
    port="$(basename "$pf" .pid)"; port="${port#browse-dev-}"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      # Kill the process group: dev scripts spawn children that outlive the parent.
      kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
      log "stopped server on :$port (pid $pid)"
      found=1
    fi
    rm -f "$pf"
  done
  [[ "$found" == "1" ]] || log "no servers started by this script are running"
  exit 0
fi

# Sweep pidfiles whose process is gone, so they can't masquerade as live servers.
for pf in "$TMP"/browse-dev-*.pid; do
  [[ -e "$pf" ]] || continue
  pid="$(cat "$pf" 2>/dev/null)"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null || rm -f "$pf"
done

# --- identity: does the server on this port actually belong to PROJECT_DIR? -----
# Reusing whatever answers on :3000 is how you end up testing an unrelated app
# and reporting confidently wrong findings.

# pid listening on a port, or empty.
port_pid() {
  case "$PROBE" in
    ss)   ss -ltnp 2>/dev/null | grep -E "[:.]$1[[:space:]]" \
            | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2 ;;
    lsof) lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | head -1 ;;
    *)    echo "" ;;
  esac
}

# Walk up from a pid's cwd; a monorepo dev server may run from root or a package.
paths_related() {
  local a="${1%/}" b="${2%/}"
  [[ -n "$a" && -n "$b" ]] || return 1
  [[ "$a" == "$b" || "$a" == "$b"/* || "$b" == "$a"/* ]]
}

# 0 = belongs to this project, 1 = belongs to something else, 2 = cannot tell.
port_owned_by_project() {
  local port="$1" pid cwd
  pid="$(port_pid "$port")"
  [[ -n "$pid" ]] || return 2
  cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null)"
  [[ -n "$cwd" ]] || return 2
  paths_related "$cwd" "$(readlink -f "$PROJECT_DIR")" && return 0
  log ":$port is served from $cwd, which is not $PROJECT_DIR"
  return 1
}

# --- project shape: what is here, and how does it start? -----------------------
HAS_PKG=0
[[ -f "$PROJECT_DIR/package.json" ]] && HAS_PKG=1

# Names of the scripts in package.json, one per line.
pkg_scripts() {
  local pj="$PROJECT_DIR/package.json"
  [[ -f "$pj" ]] || return 0
  if command -v node >/dev/null 2>&1; then
    node -e 'try{const s=require(process.argv[1]).scripts||{};console.log(Object.keys(s).join("\n"))}catch(e){}' "$pj"
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json,sys
try:
    print("\n".join(json.load(open(sys.argv[1])).get("scripts", {}).keys()))
except Exception:
    pass' "$pj"
  else
    # Last resort. Good enough to answer "does a script by this name exist".
    sed -n '/"scripts"[[:space:]]*:/,/^[[:space:]]*}/p' "$pj" \
      | grep -oE '"[a-zA-Z0-9:_-]+"[[:space:]]*:' | tr -d '": ' | grep -v '^scripts$'
  fi
}

SCRIPTS="$(pkg_scripts)"
has_script() { [[ -n "$SCRIPTS" ]] && grep -qx "$1" <<<"$SCRIPTS"; }

# First script from the list that actually exists.
first_script() {
  for s in "$@"; do has_script "$s" && { echo "$s"; return 0; }; done
  return 1
}

# Package manager, from the lockfile. Each forwards script args differently;
# npm is the one that needs `--`.
PM=npm
if   [[ -f "$PROJECT_DIR/pnpm-lock.yaml" ]]; then PM=pnpm
elif [[ -f "$PROJECT_DIR/yarn.lock"      ]]; then PM=yarn
elif [[ -f "$PROJECT_DIR/bun.lockb" || -f "$PROJECT_DIR/bun.lock" ]]; then PM=bun
fi

# Build the argv for running a package script on a chosen port.
run_cmd() {
  local script="$1" port="$2"
  case "$PM" in
    pnpm) RUN=(pnpm "$script" --port "$port") ;;
    yarn) RUN=(yarn "$script" --port "$port") ;;
    bun)  RUN=(bun run "$script" --port "$port") ;;
    *)    RUN=(npm run "$script" -- --port "$port") ;;
  esac
}

# A workspace root usually has no runnable app of its own. Say so rather than
# starting the wrong thing and testing a package nobody asked about.
warn_if_workspace_root() {
  local pj="$PROJECT_DIR/package.json" ws=0
  [[ -f "$pj" ]] || return 0
  grep -q '"workspaces"' "$pj" 2>/dev/null && ws=1
  # pnpm-workspace.yaml alone means nothing: modern pnpm uses it for plain config
  # (allowBuilds, onlyBuiltDependencies) in single-package repos too. Only a real
  # `packages:` list makes this a workspace root.
  if [[ -f "$PROJECT_DIR/pnpm-workspace.yaml" ]] \
     && grep -qE '^[[:space:]]*packages:' "$PROJECT_DIR/pnpm-workspace.yaml" 2>/dev/null; then
    ws=1
  fi
  if [[ "$ws" == "1" ]]; then
    log "note: $PROJECT_DIR looks like a monorepo root. If this starts the wrong app,"
    log "      re-run with --dir pointing at the specific package you want to test."
  fi
}

# --- 1. Is something already serving THIS project? Reuse it. Never kill it. -----
CANDIDATES=()
[[ -n "$WANT_PORT" ]] && CANDIDATES+=("$WANT_PORT")
for p in "${SCAN_PORTS[@]}"; do
  [[ "$p" == "$WANT_PORT" ]] && continue   # don't probe the preferred port twice
  CANDIDATES+=("$p")
done

# In --prod we cannot tell a live dev server from a production one, and reusing a
# dev server would silently invalidate the whole point of asking for prod.
if [[ "$PROD" == "1" && "$ANY" != "1" ]]; then
  log "--prod: skipping reuse of any existing server (it may be a dev server)"
else
  for p in "${CANDIDATES[@]}"; do
    port_busy "$p" || continue

    code="$(port_http "$p")"
    # Listening but silent: likely a cold server still compiling. Give it one real chance.
    if [[ ! "$code" =~ ^[2345] ]]; then
      code="$(port_http "$p" "$COLD_MAX_TIME")"
    fi
    if [[ ! "$code" =~ ^[2345] ]]; then
      log ":$p is occupied by a non-HTTP process — skipping"
      continue
    fi

    if [[ "$HAS_PKG" == "1" && "$ANY" != "1" ]]; then
      port_owned_by_project "$p"
      case $? in
        0) : ;;
        1) log ":$p belongs to another project — skipping (pass --any to use it anyway)"; continue ;;
        2) log ":$p answers but its owner can't be verified — skipping (pass --any to use it anyway)"; continue ;;
      esac
    fi

    log "reusing existing server on :$p (HTTP $code) — not touching it"
    echo "http://localhost:$p"
    exit 0
  done
fi

if [[ "$CHECK_ONLY" == "1" ]]; then
  log "nothing is serving this project; --check means no server was started"
  exit 1
fi

# --- 2. Decide what command would serve this project. --------------------------
cd "$PROJECT_DIR" || { log "no such dir: $PROJECT_DIR"; exit 2; }

STATIC=0
SCRIPT=""
if [[ "$HAS_PKG" == "1" ]]; then
  warn_if_workspace_root
  if [[ "$PROD" == "1" ]]; then
    BUILD_SCRIPT="$(first_script build || true)"
    SCRIPT="$(first_script start preview serve || true)"
    if [[ -z "$SCRIPT" ]]; then
      log "--prod needs a 'start', 'preview', or 'serve' script; package.json has none."
      log "available scripts: $(tr '\n' ' ' <<<"$SCRIPTS")"
      exit 1
    fi
    if [[ -n "$BUILD_SCRIPT" ]]; then
      log "building for production ($PM run $BUILD_SCRIPT) — this can take a few minutes"
      BUILD_LOG="$TMP/browse-build.log"
      if [[ "$PM" == "bun" ]]; then BUILD=(bun run "$BUILD_SCRIPT"); else BUILD=("$PM" run "$BUILD_SCRIPT"); fi
      if ! timeout "$BUILD_DEADLINE" "${BUILD[@]}" >"$BUILD_LOG" 2>&1; then
        log "production build failed or timed out. Last lines:"; tail -30 "$BUILD_LOG" >&2
        exit 1
      fi
      log "build ok"
    else
      log "no 'build' script; serving '$SCRIPT' as-is"
    fi
  else
    SCRIPT="$(first_script dev start serve preview || true)"
    if [[ -z "$SCRIPT" ]]; then
      log "no 'dev', 'start', 'serve', or 'preview' script in $PROJECT_DIR/package.json."
      log "available scripts: $(tr '\n' ' ' <<<"$SCRIPTS")"
      log "Pass an explicit URL instead, or point --dir at the app package."
      exit 1
    fi
    [[ "$SCRIPT" != "dev" ]] && log "no 'dev' script; falling back to '$SCRIPT'"
  fi
elif compgen -G "$PROJECT_DIR/index.html" >/dev/null; then
  # No package.json but there is something to serve: plain static hosting.
  if command -v python3 >/dev/null 2>&1; then
    STATIC=1
    log "no package.json; serving $PROJECT_DIR statically with python3 -m http.server"
  else
    log "no package.json and no python3 to serve $PROJECT_DIR statically. Pass a URL instead."
    exit 1
  fi
else
  log "no package.json and no index.html in $PROJECT_DIR — cannot auto-start. Pass a URL instead."
  exit 1
fi

# --- 3. Start it, retrying if we lose a race for the port. ---------------------
# Between "this port is free" and the server binding it, another process can take
# it. Losing that race must not look like a broken dev script.
start_once() {
  local port="$1"
  LOG="$TMP/browse-dev-$port.log"
  PIDFILE="$TMP/browse-dev-$port.pid"

  if [[ "$STATIC" == "1" ]]; then
    RUN=(python3 -m http.server "$port" --bind 127.0.0.1)
  else
    run_cmd "$SCRIPT" "$port"
  fi

  log "starting: ${RUN[*]}  (log: $LOG)"
  # Cap the Node heap for any server we launch. A Next.js/Turbopack dev server driven
  # hard by an automated browser accumulates its compilation graph and does not release
  # it: on 2026-07-19 one reached 15.9GB RSS, tripped the kernel's global OOM killer,
  # and took the entire WSL distro down mid-session. The cap makes a runaway server
  # die alone instead of killing everything around it. Respect an explicit outer value.
  local heap_cap="${BROWSE_HEAP_MB:-4096}"
  local node_opts="${NODE_OPTIONS:-}"
  [[ "$node_opts" != *max-old-space-size* ]] \
    && node_opts="${node_opts:+$node_opts }--max-old-space-size=$heap_cap"
  log "node heap cap: ${heap_cap}MB (override with BROWSE_HEAP_MB)"

  # PORT belt-and-braces: plenty of dev scripts hardcode their port and ignore --port,
  # but almost all of them respect $PORT.
  PORT="$port" NODE_OPTIONS="$node_opts" setsid nohup "${RUN[@]}" >"$LOG" 2>&1 &
  PID=$!
  echo "$PID" > "$PIDFILE"
}

# The script may have ignored both PORT and --port and bound somewhere else entirely.
# Whatever it prints to its own log is the ground truth.
port_from_log() {
  grep -oE 'https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]):[0-9]+' "$LOG" 2>/dev/null \
    | grep -oE '[0-9]+$' | tail -1
}

port_conflict_in_log() {
  grep -qiE 'EADDRINUSE|address already in use|port .* is (already )?in use' "$LOG" 2>/dev/null
}

TRIED=()
attempt=0
while (( attempt < START_ATTEMPTS )); do
  attempt=$((attempt + 1))

  FREE=""
  for p in "${CANDIDATES[@]}"; do
    [[ " ${TRIED[*]-} " == *" $p "* ]] && continue
    port_busy "$p" || { FREE="$p"; break; }
  done
  if [[ -z "$FREE" ]]; then
    log "no free candidate port left; refusing to guess. Free one or pass --port."
    exit 1
  fi
  TRIED+=("$FREE")

  start_once "$FREE"

  # --- 4. Wait for it to actually answer, on a real wall-clock deadline. --------
  # The budget below is the one in the log message: a per-probe timeout multiplied
  # by an iteration count is not a deadline.
  START_TS=$SECONDS
  ACTUAL="$FREE"
  RESULT=""
  while (( SECONDS - START_TS < START_DEADLINE )); do
    code="$(port_http "$ACTUAL" 3)"
    if [[ "$code" =~ ^[2345] ]]; then
      [[ "$ACTUAL" != "$FREE" ]] && log "note: server chose :$ACTUAL, not :$FREE"
      log "up on :$ACTUAL (HTTP $code, pid $PID)"
      [[ "$ACTUAL" != "$FREE" ]] && mv "$PIDFILE" "$TMP/browse-dev-$ACTUAL.pid" 2>/dev/null
      echo "http://localhost:$ACTUAL"
      exit 0
    fi

    if port_conflict_in_log; then
      log ":$FREE was taken between the check and the bind — retrying on another port"
      kill -TERM "-$PID" 2>/dev/null || kill -TERM "$PID" 2>/dev/null
      rm -f "$PIDFILE"
      RESULT=retry
      break
    fi

    if ! kill -0 "$PID" 2>/dev/null; then
      log "server died. Last lines:"; tail -20 "$LOG" >&2
      rm -f "$PIDFILE"
      exit 1
    fi

    logged="$(port_from_log)"
    if [[ -n "$logged" && "$logged" != "$ACTUAL" ]]; then
      log "server reported :$logged — following it there"
      ACTUAL="$logged"
    fi
    sleep 1
  done

  [[ "$RESULT" == "retry" ]] && continue

  log "timed out after ${START_DEADLINE}s waiting on :$ACTUAL. Last lines:"
  tail -20 "$LOG" >&2
  log "the server may still be starting; it is left running (pid $PID). Use --stop to kill it."
  exit 1
done

log "gave up after $START_ATTEMPTS attempts to claim a port (tried: ${TRIED[*]})"
exit 1
