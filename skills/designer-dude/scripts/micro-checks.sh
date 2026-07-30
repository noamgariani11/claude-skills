#!/usr/bin/env bash
# designer-dude static checks — the countable craft facts, read from source.
#
# Two halves:
#   A. Micro-checks (1-7)  — the always-expected interaction details.
#   B. Token audit (8-14)  — the countable claims the rubric leans on most
#                            ("the radius scale has 6 values", "spacing is
#                            off the 4px base", "hexes are hardcoded past
#                            the tokens"). Counting these by eye is where a
#                            review gets a number wrong and loses the room.
#   C. Tailwind health (15) — only on Tailwind projects. Pins the MAJOR
#                            VERSION first, because that decides whether
#                            half the other hits are defects or correct
#                            code: v3 syntax generates no CSS on a v4
#                            build, silently. Then measures the token
#                            layer, which is the real system signal.
#                            Companion reference: references/tailwind.md.
#
# Stack-aware by construction: discovers the source directories and the file
# extensions actually in use before grepping, so it does not silently pass on
# a Vue, Svelte, Rails, or plain-HTML project.
#
# Read-only. Everything printed is a CANDIDATE, not a finding. Confirm in the
# browser (or read the surrounding code) before writing any of it up.
#
# Usage: micro-checks.sh [project-root]
# Exit:  0 = ran, no hard-fail candidate
#        2 = at least one WCAG hard-fail CANDIDATE (still needs confirming)
#        1 = could not run (bad root, no source found)

set -uo pipefail
ROOT="${1:-.}"
cd "$ROOT" || exit 1

HARD_FAIL_CANDIDATES=0
MAX_LINES="${MAX_LINES:-20}"

echo "designer-dude static checks"
echo "root: $(pwd)"
echo

# ---------- discover the stack ----------
SRC_DIRS=()
for d in src app lib components pages resources/views templates public; do
  [ -d "$d" ] && SRC_DIRS+=("$d")
done
# Fall back to repo root if none of the usual suspects exist.
[ ${#SRC_DIRS[@]} -eq 0 ] && SRC_DIRS=(".")

# Which markup/component extensions are actually present?
#
# NOTE ON `-print -quit` (do not "simplify" this back to `| head -1`):
# under `set -o pipefail`, `find ... | head -1` makes find die of SIGPIPE
# (141) as soon as head closes the pipe, the whole pipeline reports failure,
# and the extension is silently DROPPED. The bug scaled the wrong way -- the
# more files of a type a project had, the sooner head closed and the more
# likely that type was skipped. A 955-file .tsx app detected as "html js",
# and every check below then ran against a handful of static files and
# reported a clean bill of health. `-print -quit` stops find itself, so
# nothing dies on a pipe.
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

echo "source dirs: ${SRC_DIRS[*]}"
echo "markup exts: ${EXTS[*]:-none found}"
echo "style exts:  ${CSS_EXTS[*]:-none found}"
echo

if [ ${#EXTS[@]} -eq 0 ] && [ ${#CSS_EXTS[@]} -eq 0 ]; then
  echo "No source files found. Is this the right root? Checks skipped."
  exit 1
fi

# Sanity line: if this count is implausibly small for the project you are
# reviewing, the detection above is wrong and every result below is noise.
TOTAL_FILES=0
if [ ${#EXTS[@]} -gt 0 ]; then
  INCLUDES=()
  for e in "${EXTS[@]}"; do INCLUDES+=(--include="*.${e}"); done
fi
CSS_INCLUDES=()
for e in "${CSS_EXTS[@]:-}"; do [ -n "$e" ] && CSS_INCLUDES+=(--include="*.${e}"); done

EXCLUDES=(--exclude-dir=node_modules --exclude-dir=.next --exclude-dir=dist
          --exclude-dir=build --exclude-dir=.git --exclude-dir=vendor
          --exclude-dir=coverage --exclude-dir=.svelte-kit --exclude-dir=.turbo
          --exclude-dir=out --exclude-dir=storybook-static)

for e in "${EXTS[@]:-}" "${CSS_EXTS[@]:-}"; do
  [ -z "$e" ] && continue
  n=$(find "${SRC_DIRS[@]}" -type f -name "*.$e" \
        -not -path '*/node_modules/*' -not -path '*/.next/*' \
        -not -path '*/dist/*' -not -path '*/build/*' 2>/dev/null | wc -l)
  TOTAL_FILES=$((TOTAL_FILES + n))
  printf '  %-10s %s files\n' "$e" "$n"
done
echo "  total      $TOTAL_FILES files in scope"
echo
echo "If that total looks far too small for this project, STOP: the stack"
echo "detection missed something and every count below is meaningless."

section () { echo; echo "== $1 =="; }
# grep that never trips the script's own pipefail/errexit expectations
g () { grep -rn "$@" "${SRC_DIRS[@]}" "${EXCLUDES[@]}" 2>/dev/null; }

# ---------- 1. pointer cursor ----------
section "1. Pointer cursor on clickable elements"
if [ ${#EXTS[@]} -gt 0 ]; then
  clickable=$(g "${INCLUDES[@]}" -e "onClick" -e "@click" -e "v-on:click" \
    -e "role=[\"']button[\"']" -e "<button" -e "<a " | wc -l)
  pointer=$(g "${INCLUDES[@]}" "${CSS_INCLUDES[@]:-}" -e "cursor-pointer" -e "cursor: *pointer" | wc -l)
  echo "clickable-element references: $clickable"
  echo "explicit pointer-cursor declarations: $pointer"
  echo
  echo "Note: native <button> and <a href> get a pointer from the UA in most"
  echo "resets, but Tailwind Preflight and many CSS resets strip it from"
  echo "<button>. Check the reset before writing this up as a finding."
  echo
  echo "Clickable non-native elements (these genuinely need an explicit cursor):"
  g "${INCLUDES[@]}" -e "onClick" -e "@click" -e "v-on:click" \
    | grep -v "<button\|<a \|cursor-pointer\|cursor: *pointer" \
    | grep "<div\|<span\|<li\|<td\|<tr\|<img\|<svg\|<p " | head -"$MAX_LINES"
  echo
  echo "The browser probe (probe.js, check \`interaction.missingPointer\`)"
  echo "answers this properly -- it reads the COMPUTED cursor. Prefer it."
fi

# ---------- 2. dropdowns ----------
section "2. Dropdown quality"
if [ ${#EXTS[@]} -gt 0 ]; then
  echo "Raw <select> elements:"
  g "${INCLUDES[@]}" "<select" | head -"$MAX_LINES"
  echo
  echo "Custom dropdown components in use:"
  grep -rln "DropdownMenu\|Combobox\|Popover\|Listbox\|<details" \
    "${SRC_DIRS[@]}" "${INCLUDES[@]}" "${EXCLUDES[@]}" 2>/dev/null | head -"$MAX_LINES"
  echo
  echo "JUDGEMENT REQUIRED — a native <select> is not automatically a defect."
  echo "On mobile and with screen readers it often beats a custom listbox."
  echo "Flag it when it clashes with a heavily-styled surrounding form, or"
  echo "when the design needs option content a <select> cannot render"
  echo "(icons, two-line rows, grouping). Otherwise leave it alone and say"
  echo "why. Any custom replacement must be keyboard-navigable, focus-"
  echo "trapped, labelled, and screen-reader announced — if the current"
  echo "custom dropdown is NOT, that is the real finding."
fi

# ---------- 3. scrollbars ----------
section "3. Scrollbar styling"
if [ ${#CSS_EXTS[@]} -gt 0 ] || [ ${#EXTS[@]} -gt 0 ]; then
  hits=$(g "${CSS_INCLUDES[@]:-}" "${INCLUDES[@]:-}" \
    -e "::-webkit-scrollbar" -e "scrollbar-width" -e "scrollbar-color")
  if [ -n "$hits" ]; then
    echo "Scrollbar styling present:"; echo "$hits" | head -10
    echo
    webkit=$(echo "$hits" | grep -c "::-webkit-scrollbar")
    ff=$(echo "$hits" | grep -c "scrollbar-width\|scrollbar-color")
    echo "webkit rules: $webkit · firefox rules: $ff"
    echo "Both sides should exist. One without the other is a minor finding."
  else
    echo "No scrollbar styling found."
    echo
    echo "JUDGEMENT REQUIRED — this is a preference, not a defect. Custom"
    echo "scrollbars can reduce affordance and hit-area, and the OS default"
    echo "is what users know. Raise it as an optional polish item on a"
    echo "heavily-designed surface with a persistent scroll region. Never"
    echo "dock a full grade for it, and never make a thumb thinner than"
    echo "8px or lower-contrast than 3:1 against its track."
  fi
fi

# ---------- 4. icon hygiene ----------
section "4. Unicode symbols standing in for icons"
if [ ${#EXTS[@]} -gt 0 ]; then
  echo "Candidates (arrows, checks, crosses, warning, lock, bell):"
  g "${INCLUDES[@]}" -e "←" -e "→" -e "↓" -e "↑" -e "✓" -e "✔" -e "✗" -e "✕" \
    -e "⚠" -e "🔒" -e "🔓" -e "🔔" -e "▼" -e "▲" | head -25
  echo
  echo "Only flag symbols acting as ICONS inside a button, link, badge, or"
  echo "status indicator — replace those with a real icon component"
  echo "(lucide-react, heroicons, phosphor, whatever the repo already uses;"
  echo "check package.json before recommending a library it does not have)."
  echo "Leave genuine typographic content alone: · separators, – en-dashes,"
  echo "× in dimensions like 24×24, arrows inside prose, and anything in a"
  echo "non-DOM renderer (PDF, canvas, map-popup HTML strings)."
fi

# ---------- 5. focus-visible ----------
section "5. Focus rings (WCAG 2.4.7 / 2.4.11)"
removed=$(g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" \
  -e "outline: *none" -e "outline: *0" -e "outline-none")

if [ -n "$removed" ]; then
  # `outline-none` next to a ring/shadow/border replacement on the same
  # declaration is the CORRECT pattern, not a defect. Flagging it sends the
  # reviewer chasing a non-bug, so split the two cases apart.
  bare=$(echo "$removed" | grep -v "ring-\|box-shadow\|shadow-\|outline-offset\|border-")
  paired=$(echo "$removed" | grep -c "ring-\|box-shadow\|shadow-\|outline-offset\|border-")

  echo "outline removed WITH a visible replacement on the same line: $paired"
  echo "(that is the correct pattern — not a finding)"
  echo
  if [ -n "$bare" ]; then
    echo "outline removed with NO replacement visible on the line:"
    echo "$bare" | head -"$MAX_LINES"
    echo
    echo "Confirm by tabbing in the browser before writing this up — the"
    echo "replacement may live in a shared class or a parent rule. The probe"
    echo "(\`a11y.focusInvisible\`) tests this against computed styles."
    echo "A genuinely invisible focus ring is a WCAG 2.4.7 AA failure:"
    echo "CRITICAL, and it triggers the score cap (--wcag-fail)."
    HARD_FAIL_CANDIDATES=$((HARD_FAIL_CANDIDATES + 1))
  else
    echo "No unpaired outline removal. Good."
  fi
else
  echo "No blanket outline removal found. Good."
fi
echo
echo -n "focus-visible declarations present: "
g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" "focus-visible" | wc -l
echo "(a codebase using :focus rather than :focus-visible will show a"
echo " ring on mouse click too — worth a minor polish finding, not a fail)"

# ---------- 6. reduced motion ----------
section "6. prefers-reduced-motion"
rm_hits=$(g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" "prefers-reduced-motion" | wc -l)
anim=$(g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" \
  -e "animate-" -e "@keyframes" -e "transition:" -e "framer-motion" -e "motion\." | wc -l)
echo "animation/transition references: $anim"
echo "prefers-reduced-motion guards:   $rm_hits"
if [ "$anim" -gt 0 ] && [ "$rm_hits" -eq 0 ]; then
  echo "-> Animation with zero reduced-motion guards. WCAG 2.3.3 candidate."
  HARD_FAIL_CANDIDATES=$((HARD_FAIL_CANDIDATES + 1))
fi

# ---------- 7. radius scale discipline ----------
section "7. Radius scale (a scale is 2-3 meaningful values, plus pill)"
radii=$(g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" -o \
  -e "border-radius: *[0-9.]*\(px\|rem\|em\)" -e "rounded-\[[^]]*\]" \
  -e "rounded-\(none\|sm\|md\|lg\|xl\|2xl\|3xl\|full\)" \
  | sed 's/^[^:]*:[0-9]*://' | sort | uniq -c | sort -rn)
if [ -n "$radii" ]; then
  echo "$radii" | head -15
  distinct=$(echo "$radii" | wc -l)
  echo
  echo "distinct radius values in use: $distinct"
  [ "$distinct" -gt 5 ] && echo "-> More than 5 distinct radii reads as assembled, not decided."
  echo "Judgement: a token alias (rounded-md) and its raw value are the SAME"
  echo "step. Count steps, not spellings, before writing a finding."
else
  echo "No radius declarations found."
fi

# ---------- 8. hardcoded colour literals ----------
section "8. Hardcoded colour outside the token layer"
if [ ${#EXTS[@]} -gt 0 ]; then
  echo "Hex literals in markup/components (tokens should be referenced, not retyped):"
  g "${INCLUDES[@]}" -o "#[0-9a-fA-F]\{3,8\}\b" \
    | grep -v "\.css:" | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -12
  total_hex=$(g "${INCLUDES[@]}" -o "#[0-9a-fA-F]\{3,8\}\b" | grep -vc "\.css:")
  echo "total hex literals outside stylesheets: ${total_hex:-0}"
  echo
  echo -n "pure #000 / #fff / black / white literals: "
  g "${INCLUDES[@]}" "${CSS_INCLUDES[@]:-}" -o \
    -e "#000\b" -e "#000000" -e "#fff\b" -e "#ffffff" -e "text-white" -e "bg-black" | wc -l
  echo "(Refactoring UI: no pure black or white. On a themed product,"
  echo " text-white on a solid fill breaks the moment the theme flips.)"
fi

# ---------- 9. spacing off the 4px base ----------
section "9. Spacing off the 4/8 base"
odd=$(g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" -o \
  -e "\(margin\|padding\|gap\|top\|left\|right\|bottom\): *[0-9]\+px" \
  -e "\(p\|m\|gap\|space-[xy]\)-\[[0-9]\+px\]" \
  | grep -o "[0-9]\+px" | sort -n | uniq -c | sort -rn)
if [ -n "$odd" ]; then
  echo "$odd" | head -18
  echo
  echo "Off-base values (not divisible by 4):"
  echo "$odd" | awk '{v=$2; gsub("px","",v); if (v % 4 != 0 && v != 1 && v != 2) print "  " $0}' | head -12
  echo "(1px and 2px are legitimate hairlines/optical corrections, not drift.)"
else
  echo "No literal px spacing found — likely all on a token scale. Good sign."
fi

# ---------- 10. type voice ----------
section "10. Type voice (font families actually declared)"
g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" -o \
  -e "font-family: *[^;]*" -e "font-\(sans\|serif\|mono\)" \
  -e "next/font/\(google\|local\)" \
  | sed 's/^[^:]*:[0-9]*://' | sort | uniq -c | sort -rn | head -14
echo
echo "slop-tier faces (Inter/Roboto/Poppins/Montserrat) in a FONT context:"
# Must be a whole word AND on a line that is about type. A bare `grep -i
# Inter` matches "interest", "Internal", "interaction" and reports four
# figures of nonsense on any real codebase -- which then gets quoted at the
# user as if it were a finding.
g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" -iE \
  "(font-family|font[A-Za-z]*: *\"|next/font|@font-face|--font-)[^;]*\b(Inter|Roboto|Poppins|Montserrat)\b" \
  | head -12
echo -n "count: "
g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" -icE \
  "(font-family|font[A-Za-z]*: *\"|next/font|@font-face|--font-)[^;]*\b(Inter|Roboto|Poppins|Montserrat)\b" \
  | awk -F: '{s+=$NF} END {print s+0}'
echo "(fine as the LAST entry in a fallback stack; never as the voice —"
echo " check which position it holds before writing it up)"

# ---------- 11. image dimensions and alt (CLS + a11y) ----------
section "11. Images: reserved dimensions and alt text"
if [ ${#EXTS[@]} -gt 0 ]; then
  # A single grep line CANNOT answer this: JSX and Vue routinely wrap one
  # <img> across six lines with `alt` three lines below the tag name. Testing
  # only the opening line reports missing alt on images that have it -- and
  # this check feeds a WCAG hard-fail count, so a false positive here caps a
  # score that did not earn the cap. Read the whole tag.
  img_files=$(grep -rl "<img" "${SRC_DIRS[@]}" "${INCLUDES[@]}" "${EXCLUDES[@]}" 2>/dev/null)
  img_report=$(
    if [ -n "$img_files" ]; then
      echo "$img_files" | while IFS= read -r f; do
        awk -v F="$f" '
          # Skip <img> written inside a comment or a docstring: an ESLint
          # suppression note explaining why a raw <img> is correct is not an
          # accessibility defect, and neither is an XSS example in a comment.
          /^[[:space:]]*(\/\/|\*|\/\*|#|\{\/\*)/ { next }
          /<img/ { intag = 1; buf = ""; startline = FNR }
          intag  { buf = buf " " $0 }
          # Require a src: a bare "<img>" mentioned in prose is not a tag.
          intag && /\/?>/ && buf ~ /<img/ && buf ~ /src[ ]*[=:]/ {
            # close the tag on the first > that follows the img token
            miss = ""
            if (buf !~ /alt[ ]*=/)  miss = miss "alt "
            if (buf !~ /width[ ]*=/ && buf !~ /height[ ]*=/ &&
                buf !~ /aspect-/    && buf !~ /[ ]fill[ >]/) miss = miss "dims "
            printf "%s:%d\tmissing: %s\n", F, startline, (miss == "" ? "-" : miss)
            intag = 0
          }
        ' "$f"
      done
    fi
  )
  n_imgs=$(echo "$img_report" | grep -c ":" )
  no_alt=$(echo "$img_report" | grep -c "missing:.*alt")
  no_dim=$(echo "$img_report" | grep -c "missing:.*dims")
  echo "raw <img> tags: ${n_imgs:-0} · without alt: ${no_alt:-0} · without reserved dims: ${no_dim:-0}"
  echo "(next/image, <Image>, and CSS background images are NOT counted here)"
  if [ "${no_alt:-0}" -gt 0 ]; then
    echo "-> Missing alt is WCAG 1.1.1 A. Decorative images still need alt=\"\"."
    HARD_FAIL_CANDIDATES=$((HARD_FAIL_CANDIDATES + 1))
    echo "$img_report" | grep "missing:.*alt" | head -10
  fi
  echo "(unreserved dimensions are the classic CLS cause — a design failure,"
  echo " scored under Interaction & Performance, not a separate perf ticket)"
fi

# ---------- 12. z-index and !important sprawl ----------
section "12. Layer discipline"
echo -n "distinct z-index values: "
g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" -o -e "z-index: *[0-9]*" -e "z-\[[0-9]*\]" -e "z-[0-9]\+" \
  | sed 's/^[^:]*:[0-9]*://' | sort -u | wc -l
echo -n "!important declarations: "
g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" "!important" | wc -l
echo "(a z-index scale is 4-6 named steps; a long tail of 9999s is a symptom"
echo " of a stacking model nobody owns)"

# ---------- 13. state coverage ----------
section "13. Designed states (Interaction pillar wants all seven)"
for state in hover focus-visible active disabled loading empty error; do
  case "$state" in
    loading) pat="isLoading\|pending\|Skeleton\|aria-busy" ;;
    empty)   pat="empty\|EmptyState\|no results\|nothing here" ;;
    error)   pat="error\|Error\|aria-invalid" ;;
    *)       pat="$state" ;;
  esac
  printf '  %-14s %s\n' "$state" "$(g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" -i "$pat" | wc -l)"
done
echo "A zero here is a real gap. A large number is not proof the state is"
echo "DESIGNED — only that it exists. Confirm the designed ones in-browser."

# ---------- 14. dark mode ----------
section "14. Dark mode"
dark=$(g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" -e "prefers-color-scheme" -e "dark:" -e "\[data-theme" | wc -l)
echo "dark-mode references: $dark"
if [ "$dark" -eq 0 ]; then
  echo "-> No dark mode. Only a finding if the product promises one or the"
  echo "   audience expects one (see the 'does NOT dock for' list)."
else
  echo "Dark mode exists — grade whether it was DESIGNED or inverted:"
  echo "check for a separate dark palette (warm neutrals, reduced accent"
  echo "saturation, softer elevation) rather than the same hexes flipped."
fi

# ---------- 15. Tailwind system health ----------
#
# Only runs if Tailwind is actually present. The point is NOT to grade
# Tailwind usage -- it is to (a) pin the major version so no fix ships dead
# v3 syntax into a v4 build, and (b) measure whether a token layer exists,
# which is the real system-design signal. See references/tailwind.md.
section "15. Tailwind system health"

TW_PRESENT=0
grep -rqs "tailwindcss" package.json 2>/dev/null && TW_PRESENT=1
[ -z "$(g "${CSS_INCLUDES[@]:-}" -l -e "@import [\"']tailwindcss" -e "@tailwind " 2>/dev/null)" ] || TW_PRESENT=1

if [ "$TW_PRESENT" -eq 0 ]; then
  echo "Tailwind not detected. Section skipped."
else
  # -- major version --------------------------------------------------
  TW_VER="unknown"
  if [ -n "$(g "${CSS_INCLUDES[@]:-}" -l -e "@import [\"']tailwindcss" 2>/dev/null)" ]; then
    TW_VER="4"
  elif [ -n "$(g "${CSS_INCLUDES[@]:-}" -l -e "@tailwind base" -e "@tailwind utilities" 2>/dev/null)" ]; then
    TW_VER="3"
  fi
  PKG_VER=$(grep -os '"tailwindcss": *"[^"]*"' package.json 2>/dev/null | head -1)
  # CSS entry is the authority, but fall back to the dependency range rather
  # than reporting "unknown" -- an unknown version makes the v3-syntax verdict
  # below unusable, which is the whole point of the section.
  if [ "$TW_VER" = "unknown" ] && [ -n "$PKG_VER" ]; then
    case "$PKG_VER" in
      *'"'[^0-9]*4.*|*': "4'*|*'^4'*|*'~4'*) TW_VER="4 (from package.json)" ;;
      *'^3'*|*'~3'*|*': "3'*)               TW_VER="3 (from package.json)" ;;
    esac
  fi
  case "$TW_VER" in 4*) IS_V4=1 ;; *) IS_V4=0 ;; esac
  echo "major version (from CSS entry): v${TW_VER}"
  [ -n "$PKG_VER" ] && echo "package.json:                   ${PKG_VER}"
  echo "Confirm with: pnpm ls tailwindcss"

  # -- dead v3 syntax in a v4 build ------------------------------------
  echo
  echo "-- v3 syntax (SILENTLY DEAD if this is v4) --"
  V3_DEAD=0
  for pair in \
    "bg-gradient-to-:bg-linear-to-" \
    "flex-shrink-:shrink-" \
    "flex-grow-:grow-" \
    "overflow-ellipsis:text-ellipsis" \
    "max-w-screen-:max-w-* or a container query" \
    "shadow-inner:inset-shadow-xs" \
    "@tailwind :@import \"tailwindcss\"" ; do
    pat="${pair%%:*}"; fix="${pair#*:}"
    n=$(g "${INCLUDES[@]:-}" "${CSS_INCLUDES[@]:-}" -F -e "$pat" | wc -l)
    [ "$n" -gt 0 ] && { printf '  %-22s %-4s -> %s\n' "$pat" "$n" "$fix"; V3_DEAD=$((V3_DEAD + n)); }
  done
  n=$(g "${INCLUDES[@]:-}" -oE 'class(Name)?="[^"]*![a-z-]' | wc -l)
  [ "$n" -gt 0 ] && { printf '  %-22s %-4s -> %s\n' "!important prefix" "$n" "suffix form: flex!"; V3_DEAD=$((V3_DEAD + n)); }
  if [ "$V3_DEAD" -eq 0 ]; then
    echo "  none found."
  elif [ "$IS_V4" -eq 1 ]; then
    echo "  ^^ CONFIRMED DEFECTS on a v4 build: these classes generate NO CSS."
    echo "  Not a style quibble. Verify one in DevTools, then fix the set."
  elif [ "${TW_VER%% *}" = "3" ]; then
    echo "  ^^ correct for v3. Becomes dead on upgrade -- migration debt, not a finding."
  else
    echo "  ^^ VERSION UNKNOWN -- run 'pnpm ls tailwindcss' before judging these."
    echo "  Dead on v4, correct on v3. Do not write them up either way yet."
  fi

  # -- token layer (the real system signal) ----------------------------
  echo
  echo "-- token layer --"
  theme_block=$(g "${CSS_INCLUDES[@]:-}" -e "@theme" | wc -l)
  cfg=$([ -f tailwind.config.js ] || [ -f tailwind.config.ts ] && echo yes || echo no)
  echo "@theme blocks:            $theme_block"
  echo "legacy tailwind.config:   $cfg"
  raw=$(g "${INCLUDES[@]:-}" -oE '(text|bg|border|ring)-(gray|slate|zinc|neutral|stone)-[0-9]{2,3}' | wc -l)
  echo "raw palette refs in markup: $raw"
  if [ "$theme_block" -eq 0 ] && [ "$raw" -gt 20 ]; then
    echo "-> No @theme block and $raw raw palette references. That is a product"
    echo "   with no semantic token layer -- every colour decision is restated"
    echo "   at each call site. Scoring pillar 4 (Colour) and slop item 5."
  fi
  dark_pairs=$(g "${INCLUDES[@]:-}" -oE 'dark:(bg|text|border)-' | wc -l)
  echo "dark: colour variants:      $dark_pairs"
  if [ "$dark_pairs" -gt 40 ] && [ "$theme_block" -eq 0 ]; then
    echo "-> Every colour doubled by hand. In v4, scoped CSS vars + '@theme"
    echo "   inline' collapse these to one token pair. High-value refactor,"
    echo "   and it kills the 'someone forgot the dark variant' bug class."
  fi

  # -- arbitrary-value density = missing tokens ------------------------
  echo
  echo "-- arbitrary values (repeat = missing token) --"
  g "${INCLUDES[@]:-}" -ohE '\b[a-z-]+-\[[^]"]+\]' 2>/dev/null \
    | sed 's/.*://' | sort | uniq -c | sort -rn | awk '$1 >= 3' | head -10
  echo "(1-2 uses = fine, an escape hatch. 3+ = it wants to be a @theme"
  echo " variable. Zero output here is a healthy result.)"

  # -- v4-specific confirmed defects -----------------------------------
  echo
  echo "-- v4 traps --"
  if [ "$IS_V4" -eq 1 ]; then
    n=$(g "${INCLUDES[@]:-}" -oE 'class(Name)?="[^"]*\bborder\b(?![-a-z])' 2>/dev/null | wc -l)
    [ "$n" = "0" ] && n=$(g "${INCLUDES[@]:-}" -oE '"[^"]*\bborder "' | wc -l)
    echo "bare 'border' w/o colour:   $n  (v4 default is currentColor, not gray-200)"
    cp_base=$(g "${CSS_INCLUDES[@]:-}" -e "cursor: *pointer" | grep -c "button" || true)
    echo "Preflight cursor restore:   $cp_base  (v4 buttons get cursor:default;"
    echo "  if 0 and section 1 flagged pointers, that is ONE root cause, one fix,"
    echo "  not N separate findings.)"
  else
    echo "skipped (not a v4 build)"
  fi
  n=$(g "${INCLUDES[@]:-}" -F -e "h-screen" | wc -l)
  [ "$n" -gt 0 ] && echo "h-screen:                   $n  (mobile viewport bug -> h-dvh)"

  # -- classes that never generate -------------------------------------
  echo
  echo "-- interpolated class names (never generate) --"
  # Only PARTIAL-token interpolation breaks: `text-${c}-500` builds a class
  # name the scanner cannot see. A whole-string pass-through (`${className}`,
  # `${badgeClasses(k)}`) is the correct, idiomatic pattern -- do NOT flag it.
  # Anchored to a real utility prefix so `id={`task-${id}-title`}` and other
  # non-class template literals do not show up as noise.
  TW_PREFIX='(text|bg|border|ring|outline|decoration|from|via|to|fill|stroke|shadow'
  TW_PREFIX+='|p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|w|h|size|min-w|max-w|gap'
  TW_PREFIX+='|grid-cols|col-span|row-span|rounded|opacity|z|order|basis|leading'
  TW_PREFIX+='|tracking|font|scale|rotate|translate|duration|delay|animate)'
  g "${INCLUDES[@]:-}" -nE "[\`\"' ]${TW_PREFIX}-\\\$\\{" | head -8
  echo "(the scanner reads source as plain text; it does not evaluate JS."
  echo " Whole-string pass-through like \${className} is fine and not shown.)"
  merge=$(grep -rqs "tailwind-merge" package.json 2>/dev/null && echo yes || echo no)
  cnu=$(g "${INCLUDES[@]:-}" -e "clsx(" -e "classnames(" -e " cn(" | wc -l)
  echo "conditional-class helper uses: $cnu   tailwind-merge installed: $merge"
  if [ "$cnu" -gt 10 ] && [ "$merge" = "no" ]; then
    echo "-> Conflicting classes ('px-4' + 'px-6') resolve by Tailwind's output"
    echo "   order, not author order. Silent, and it looks like a CSS bug."
  fi
fi

# ---------- summary ----------
echo
echo "== summary =="
echo "files in scope:            $TOTAL_FILES"
echo "WCAG hard-fail candidates: $HARD_FAIL_CANDIDATES"
echo
echo "Every hit above is a CANDIDATE. Confirm in the browser before it"
echo "becomes a FINDING — a grep is evidence of a pattern, not of a defect."
echo "The static layer cannot see hierarchy, contrast as rendered, or"
echo "anything about how the page actually looks. Run probe.js for that."

[ "$HARD_FAIL_CANDIDATES" -gt 0 ] && exit 2
exit 0
