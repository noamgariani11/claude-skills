#!/usr/bin/env bash
# designer-dude ratchet - turn a campaign result into a floor that holds.
#
# Why this exists. A campaign spends rounds collapsing a type scale, deleting
# radii, snapping spacing back to the base and removing hardcoded colour. Then
# it ends, and every one of those counts starts drifting up again on the next
# feature branch. Nobody notices until the NEXT campaign re-measures, by which
# time the work has to be done twice. The gains were never defended.
#
# So: record the counts once, then fail a push that makes any of them worse.
# It is a RATCHET, not a gate. It never demands improvement and it never fires
# on code that was already there -- it can only fail on a NEW regression, which
# is what makes it safe to wire into a hook on day one.
#
# It is deliberately STATIC and DB-free (greps, no browser, no server) so it
# costs a second and can live in a pre-push hook. The rendered layer -- real
# contrast, focus rings, target sizes -- needs probe.js and regress.py; this
# covers the countable source facts that a probe run cannot be asked for on
# every push.
#
# Usage:
#   ratchet.sh --emit [root]      write .design/ratchet.json from today's counts
#   ratchet.sh [root]             compare today against it; exit 1 on a regression
#   ratchet.sh --file <path> ...  use a ratchet file elsewhere
#
# Exit: 0 = no regression (or no ratchet recorded yet), 1 = something got worse.

set -uo pipefail

MODE="check"
ROOT="."
FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --emit) MODE="emit"; shift ;;
    --file) FILE="$2"; shift 2 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) ROOT="$1"; shift ;;
  esac
done
cd "$ROOT" 2>/dev/null || { echo "no such root: $ROOT" >&2; exit 0; }
FILE="${FILE:-$(pwd)/.design/ratchet.json}"

# ---------- stack discovery (same shape as micro-checks.sh) ----------
SRC_DIRS=()
for d in src app lib components pages resources/views templates; do
  [ -d "$d" ] && SRC_DIRS+=("$d")
done
[ ${#SRC_DIRS[@]} -eq 0 ] && SRC_DIRS=(".")

probe_ext () {
  find "${SRC_DIRS[@]}" -type f -name "*.$1" \
    -not -path '*/node_modules/*' -not -path '*/.next/*' \
    -not -path '*/dist/*' -not -path '*/build/*' -not -path '*/.git/*' \
    -print -quit 2>/dev/null
}
EXTS=()
for ext in tsx jsx vue svelte astro html erb blade.php templ hbs mdx js ts; do
  [ -n "$(probe_ext "$ext")" ] && EXTS+=("$ext")
done
CSS_EXTS=()
for ext in css scss sass less styl; do
  [ -n "$(probe_ext "$ext")" ] && CSS_EXTS+=("$ext")
done
if [ ${#EXTS[@]} -eq 0 ] && [ ${#CSS_EXTS[@]} -eq 0 ]; then
  echo "ratchet: no source files found under ${SRC_DIRS[*]} - nothing to measure"
  exit 0
fi
INCLUDES=()
for e in "${EXTS[@]:-}" "${CSS_EXTS[@]:-}"; do [ -n "$e" ] && INCLUDES+=(--include="*.${e}"); done
MARKUP_INCLUDES=()
for e in "${EXTS[@]:-}"; do
  case "$e" in ts|js) ;; *) [ -n "$e" ] && MARKUP_INCLUDES+=(--include="*.${e}") ;; esac
done
EXCLUDES=(--exclude-dir=node_modules --exclude-dir=.next --exclude-dir=dist
          --exclude-dir=build --exclude-dir=.git --exclude-dir=vendor
          --exclude-dir=coverage --exclude-dir=.svelte-kit --exclude-dir=.turbo
          --exclude-dir=out --exclude-dir=storybook-static)
g () { grep -rn "$@" "${SRC_DIRS[@]}" "${EXCLUDES[@]}" 2>/dev/null; }

# ---------- the metrics ----------
#
# Each one is a count that a campaign DRIVES DOWN and that ordinary feature
# work drives back up. Nothing subjective, nothing that needs a browser, and
# nothing that fires on a pattern a competent codebase legitimately uses.
distinct_radii=$(g "${INCLUDES[@]:-}" -ohE "border-radius:[[:space:]]*[0-9.]+(px|rem)" \
                 | grep -oE "[0-9.]+(px|rem)" | sort -u | wc -l)
hardcoded_colour=$(g "${INCLUDES[@]:-}" -ohE "#[0-9a-fA-F]{3,8}\b|rgba?\([0-9]" \
                 | wc -l)
off_base_spacing=$(g "${INCLUDES[@]:-}" -ohE "(margin|padding|gap)(-(top|right|bottom|left))?:[[:space:]]*[0-9]+px" \
                 | grep -oE "[0-9]+px" | grep -vE "^(0|2|4|6|8|10|12|16|20|24|32|40|48|64|80|96)px$" | wc -l)
glyph_icons=$(g "${MARKUP_INCLUDES[@]:-}" -oE "←|→|↑|↓|‹|›|✓|✔|✗|✘|×|&larr;|&rarr;|&darr;|&uarr;|&times;|&#10003;" | wc -l)
# Killing the outline is only a defect when nothing replaces it, so the metric
# is the UNREPLACED ones. Counting every `outline-none` would fire on the
# correct `outline-none focus-visible:ring-2` idiom and make the ratchet
# something people learn to bypass. Native `title=` tooltips are deliberately
# NOT here: the static form cannot tell an HTML attribute from a component prop
# of the same name, and probe.js measures the real ones at runtime.
outline_none_unringed=$(g "${INCLUDES[@]:-}" -nE "outline:[[:space:]]*none|outline-none" \
                 | grep -vE "ring|focus-visible|outline-offset|box-shadow" | wc -l)
important=$(g "${INCLUDES[@]:-}" -oE "![[:space:]]*important" | wc -l)
zindex_literals=$(g "${INCLUDES[@]:-}" -ohE "z-index:[[:space:]]*[0-9]+" | grep -oE "[0-9]+$" | sort -u | wc -l)
font_families=$(g "${CSS_EXTS:+${INCLUDES[@]}}" -ohE "font-family:[^;}]+" | sort -u | wc -l)
em_dashes=$(g "${MARKUP_INCLUDES[@]:-}" -o "—" | wc -l)

METRICS=(distinct_radii hardcoded_colour off_base_spacing glyph_icons
         outline_none_unringed important zindex_literals
         font_families em_dashes)

declare -A LABEL=(
  [distinct_radii]="distinct border-radius literals"
  [hardcoded_colour]="colour literals outside the token layer"
  [off_base_spacing]="spacing literals off the base scale"
  [glyph_icons]="unicode glyphs standing in for icons"
  [outline_none_unringed]="outline killed with nothing put back"
  [important]="!important declarations"
  [zindex_literals]="distinct z-index literals"
  [font_families]="distinct font-family declarations"
  [em_dashes]="em dashes in rendered markup"
)

if [ "$MODE" = "emit" ]; then
  mkdir -p "$(dirname "$FILE")"
  {
    echo "{"
    echo " \"recordedAt\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo " \"note\": \"designer-dude ratchet. These are CEILINGS, not targets. A push may lower any of them; raising one fails the gate. Re-emit deliberately, with the reason in the commit body.\","
    echo " \"metrics\": {"
    last=${METRICS[${#METRICS[@]}-1]}
    for m in "${METRICS[@]}"; do
      comma=","; [ "$m" = "$last" ] && comma=""
      echo "  \"$m\": ${!m}$comma"
    done
    echo " }"
    echo "}"
  } > "$FILE"
  echo "ratchet recorded -> $FILE"
  for m in "${METRICS[@]}"; do printf '  %-40s %s\n' "${LABEL[$m]}" "${!m}"; done
  echo
  echo "Wire it into the project's own gate (this repo runs CI as .githooks/pre-push):"
  echo "  bash ~/.claude/skills/designer-dude/scripts/ratchet.sh . || exit 1"
  exit 0
fi

if [ ! -f "$FILE" ]; then
  echo "ratchet: no $FILE yet - run 'ratchet.sh --emit' at the end of a campaign round."
  exit 0
fi

fail=0
echo "designer-dude ratchet vs $(python3 -c "import json,sys;print(json.load(open('$FILE'))['recordedAt'])" 2>/dev/null || echo "$FILE")"
for m in "${METRICS[@]}"; do
  was=$(python3 -c "import json;print(json.load(open('$FILE'))['metrics'].get('$m',''))" 2>/dev/null)
  now=${!m}
  [ -z "$was" ] && continue
  if [ "$now" -gt "$was" ]; then
    printf '  REGRESSED  %-40s %s -> %s\n' "${LABEL[$m]}" "$was" "$now"
    fail=1
  elif [ "$now" -lt "$was" ]; then
    printf '  improved   %-40s %s -> %s\n' "${LABEL[$m]}" "$was" "$now"
  fi
done

if [ "$fail" -eq 1 ]; then
  echo
  echo "A design count went the wrong way. Either fix it, or -- if the increase is"
  echo "deliberate and correct -- re-emit the ratchet in the same commit and say why"
  echo "in the body. Silently raising the ceiling is how the campaign gets undone."
  exit 1
fi
echo "  no regressions"
exit 0
