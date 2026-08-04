#!/usr/bin/env bash
# designer-dude environment check - what this machine can and cannot measure.
#
# Why this exists. Two campaign rounds have now been spent DISCOVERING that
# production performance could not be measured here: the prod server refuses to
# start without a local Postgres, the local Postgres needs Docker, and Docker is
# not installed. That is a fact about the machine, not about the product, and it
# should be stated in round 0 next to the target arithmetic rather than found in
# round 4 after the cheap work is gone.
#
# So: run this FIRST, once per campaign. It writes .design/environment.json and
# prints the paragraph that belongs in the first message. Everything it reports
# is a capability, and every capability it cannot confirm becomes a stated cap
# on the scorecard rather than a silent gap.
#
# Usage: env-check.sh [project-root] [--out <path>]
# Exit:  0 always - an environment limit is information, not a failure.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="."
OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    *) ROOT="$1"; shift ;;
  esac
done
cd "$ROOT" 2>/dev/null || { echo "no such root: $ROOT" >&2; exit 0; }
ROOT_ABS="$(pwd)"
OUT="${OUT:-$ROOT_ABS/.design/environment.json}"

have() { command -v "$1" >/dev/null 2>&1 && echo true || echo false; }
jbool() { [ "$1" = "true" ] && echo true || echo false; }

# ---- browser -------------------------------------------------------------
PW_CACHE="$HOME/.cache/ms-playwright"
CHROMIUM=false
FIREFOX=false
WEBKIT=false
PW_DOCTOR=""
if command -v node >/dev/null 2>&1; then
  PW_DOCTOR="$(node "$SCRIPT_DIR/cross-engine.mjs" --doctor 2>/dev/null || true)"
fi
printf '%s' "$PW_DOCTOR" | grep -q '"chromium":{"status":"ran"' && CHROMIUM=true
printf '%s' "$PW_DOCTOR" | grep -q '"firefox":{"status":"ran"' && FIREFOX=true
printf '%s' "$PW_DOCTOR" | grep -q '"webkit":{"status":"ran"' && WEBKIT=true
PW_VERSION=$(printf '%s' "$PW_DOCTOR" | sed -n 's/.*"playwrightVersion":"\([^"]*\)".*/\1/p')
CHROMIUM_VERSION=$(printf '%s' "$PW_DOCTOR" | sed -n 's/.*"chromium":{"status":"ran","version":"\([^"]*\)".*/\1/p')
FIREFOX_VERSION=$(printf '%s' "$PW_DOCTOR" | sed -n 's/.*"firefox":{"status":"ran","version":"\([^"]*\)".*/\1/p')
WEBKIT_VERSION=$(printf '%s' "$PW_DOCTOR" | sed -n 's/.*"webkit":{"status":"ran","version":"\([^"]*\)".*/\1/p')
PW_VERSION="${PW_VERSION:-unavailable}"
CHROMIUM_VERSION="${CHROMIUM_VERSION:-unavailable}"
FIREFOX_VERSION="${FIREFOX_VERSION:-unavailable}"
WEBKIT_VERSION="${WEBKIT_VERSION:-unavailable}"

# ---- replayable calibration identity ------------------------------------
OS_ID="$(uname -s 2>/dev/null)-$(uname -r 2>/dev/null)"
ARCH_ID="$(uname -m 2>/dev/null)"
DESIGNER_DUDE_VERSION=$(sha256sum "$SCRIPT_DIR/probe.js" "$SCRIPT_DIR/probe-runner.mjs" \
  "$SCRIPT_DIR/score.py" 2>/dev/null | sha256sum | awk '{print $1}')
if command -v fc-list >/dev/null 2>&1; then
  FONT_FINGERPRINT=$(fc-list 2>/dev/null | LC_ALL=C sort | sha256sum | awk '{print $1}')
else
  FONT_FINGERPRINT=$(printf '%s' "font-inventory-unavailable" | sha256sum | awk '{print $1}')
fi

# ---- memory --------------------------------------------------------------
# The global working agreement: under ~8GB available, say so and stop rather
# than starting a long browser-driven run on top of it.
MEM_AVAIL_GB=$(free -g 2>/dev/null | awk '/^Mem:/ {print $7}')
MEM_AVAIL_GB="${MEM_AVAIL_GB:-unknown}"
MEM_OK=true
if [ "$MEM_AVAIL_GB" != "unknown" ] && [ "$MEM_AVAIL_GB" -lt 8 ] 2>/dev/null; then MEM_OK=false; fi

# ---- container runtime ---------------------------------------------------
DOCKER=$(have docker)
DOCKER_RUNNING=false
[ "$DOCKER" = "true" ] && docker info >/dev/null 2>&1 && DOCKER_RUNNING=true

# ---- package manager / scripts -------------------------------------------
PM="none"
[ -f pnpm-lock.yaml ] && PM=pnpm
[ "$PM" = "none" ] && [ -f yarn.lock ] && PM=yarn
[ "$PM" = "none" ] && [ -f package-lock.json ] && PM=npm
[ "$PM" = "none" ] && [ -f bun.lockb ] && PM=bun

HAS_BUILD=false; HAS_START=false; NEEDS_DB=false
if [ -f package.json ]; then
  grep -q '"build"' package.json && HAS_BUILD=true
  grep -q '"start"' package.json && HAS_START=true
fi
# A production server that reads DATABASE_URL cannot be started from a bare
# checkout. This is the single most common reason perf goes unmeasured.
if grep -rqs "DATABASE_URL" package.json .env.example .env.local .env 2>/dev/null; then NEEDS_DB=true; fi
COMPOSE=false
{ [ -f docker-compose.yml ] || [ -f compose.yml ] || [ -f docker-compose.yaml ]; } && COMPOSE=true

# The verdict that actually matters: can Core Web Vitals be measured on a
# production build here? Only if it can be BUILT, SERVED, and its dependencies
# can run. Anything less and the Interaction pillar caps at A- and the
# scorecard says --perf-unmeasured.
PERF=true
PERF_WHY="production build is buildable and servable here"
if [ "$HAS_BUILD" != "true" ] || [ "$HAS_START" != "true" ]; then
  PERF=false; PERF_WHY="no build/start script - there is no production bundle to measure"
elif [ "$NEEDS_DB" = "true" ] && [ "$COMPOSE" = "true" ] && [ "$DOCKER_RUNNING" != "true" ]; then
  PERF=false; PERF_WHY="the production server needs a database that docker-compose provides, and Docker is not running here"
elif [ "$CHROMIUM" != "true" ]; then
  PERF=false; PERF_WHY="Playwright Chromium cannot launch - nothing can drive the built page"
fi

BROWSER_WHY="Chromium present; the probe can run"
[ "$CHROMIUM" = "true" ] || BROWSER_WHY="Playwright Chromium cannot launch - every visual pillar is provisional and NOTHING may claim to have been rendered"

mkdir -p "$(dirname "$OUT")"
cat > "$OUT" <<EOF
{
 "checkedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
 "root": "$ROOT_ABS",
 "os": "$OS_ID",
 "architecture": "$ARCH_ID",
 "playwrightVersion": "$PW_VERSION",
 "designerDudeVersion": "$DESIGNER_DUDE_VERSION",
 "browserVersions": { "chromium": "$CHROMIUM_VERSION", "firefox": "$FIREFOX_VERSION",
                       "webkit": "$WEBKIT_VERSION" },
 "fontFingerprintSha256": "$FONT_FINGERPRINT",
 "browser": { "chromium": $(jbool "$CHROMIUM"), "firefox": $(jbool "$FIREFOX"),
              "webkit": $(jbool "$WEBKIT"), "cache": "$PW_CACHE", "note": "$BROWSER_WHY" },
 "memory": { "availableGb": "$MEM_AVAIL_GB", "sufficientForLongRun": $(jbool "$MEM_OK"),
             "note": "under ~8GB available, say so and stop rather than starting on top of it" },
 "container": { "docker": $(jbool "$DOCKER"), "daemonRunning": $(jbool "$DOCKER_RUNNING"),
                "composeFile": $(jbool "$COMPOSE") },
 "project": { "packageManager": "$PM", "buildScript": $(jbool "$HAS_BUILD"),
              "startScript": $(jbool "$HAS_START"), "needsDatabase": $(jbool "$NEEDS_DB") },
 "capabilities": {
   "canProbe": $(jbool "$CHROMIUM"),
   "canRunCrossEngine": $( [ "$CHROMIUM" = true ] && [ "$FIREFOX" = true ] && [ "$WEBKIT" = true ] && echo true || echo false ),
   "canMeasureProductionPerf": $(jbool "$PERF"),
   "perfReason": "$PERF_WHY"
 },
 "impliedCaps": [
$( [ "$PERF" = "true" ] || echo '   "interaction: pass --perf-unmeasured to score.py; Core Web Vitals are not measurable here",' )
$( [ "$CHROMIUM" = "true" ] || echo '   "every visual pillar: --provisional; no page was rendered",' )
$( { [ "$FIREFOX" = "true" ] && [ "$WEBKIT" = "true" ]; } || echo '   "perfection evidence: a real Chromium/Firefox/WebKit run is unavailable; install the missing browser or native libraries",' )
   "none beyond those listed"
 ]
}
EOF

echo "designer-dude environment check"
echo "root: $ROOT_ABS"
echo "----------------------------------------------------------------------"
printf "%-26s %s\n" "chromium (probe)" "$CHROMIUM  - $BROWSER_WHY"
printf "%-26s %s\n" "firefox (cross-engine)" "$FIREFOX"
printf "%-26s %s\n" "webkit (cross-engine)" "$WEBKIT"
printf "%-26s %s\n" "memory available" "${MEM_AVAIL_GB}GB (long browser runs want >=8)"
printf "%-26s %s\n" "docker" "$DOCKER (daemon running: $DOCKER_RUNNING, compose file: $COMPOSE)"
printf "%-26s %s\n" "package manager" "$PM (build: $HAS_BUILD, start: $HAS_START, needs DB: $NEEDS_DB)"
printf "%-26s %s\n" "production perf" "$PERF  - $PERF_WHY"
echo "----------------------------------------------------------------------"
echo "wrote $OUT"
echo
echo "Say this in round 0, not round 4:"
if [ "$PERF" != "true" ]; then
  echo "  Core Web Vitals cannot be measured in this environment ($PERF_WHY),"
  echo "  so Interaction caps at A- for the whole campaign and the composite"
  echo "  ceiling drops with it. That is an environment limit, not a defect."
else
  echo "  Everything the rubric needs is measurable here. No standing caps."
fi
