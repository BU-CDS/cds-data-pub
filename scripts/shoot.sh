#!/usr/bin/env bash
# shoot.sh — screenshot a built page at fixed widths and fail on horizontal overflow.
# Usage: scripts/shoot.sh [PAGE] [OUTDIR]   (defaults: previews/index.html, previews)
# Writes OUTDIR/shot-<width>.png (full page) for 1920, 1440, 820, 390 and 320 px, and exits 1 if
# the page is wider than the viewport at any width, also with the first popover open. Uses playwright-cli (headless), which keeps its
# daemon under ~/Library/Caches/ms-playwright: run outside a restrictive sandbox. file:// pages
# need PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS (playwright-cli blocks file: by default).
set -euo pipefail

PAGE="${1:-previews/index.html}"
OUT="${2:-previews}"
WIDTHS=(1920 1440 820 390 320)
HEIGHT=900
[ -f "$PAGE" ] || { echo "shoot: no page at $PAGE" >&2; exit 1; }
mkdir -p "$OUT"
URL="file://$(cd "$(dirname "$PAGE")" && pwd)/$(basename "$PAGE")"
OUT_ABS="$(cd "$OUT" && pwd)"
SESSION="cdsdata-$$"
export PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS=true
pw(){ playwright-cli -s="$SESSION" "$@"; }
trap 'pw close >/dev/null 2>&1 || true' EXIT

pw open "$URL" >/dev/null
FAILS=0
for w in "${WIDTHS[@]}"; do
  pw resize "$w" "$HEIGHT" >/dev/null
  dims="$(pw eval '() => document.documentElement.scrollWidth + "x" + document.documentElement.clientWidth' \
    | grep -oE '"[0-9]+x[0-9]+"' | tr -d '"' || true)"
  [ -n "$dims" ] || { echo "shoot: could not read the page width at ${w}px" >&2; exit 1; }
  scroll="${dims%x*}"; client="${dims#*x}"
  pw screenshot --full-page --filename="$OUT_ABS/shot-$w.png" >/dev/null
  if [ "$scroll" -gt "$client" ]; then
    echo "shoot: FAIL ${w}px: page is ${scroll}px wide in a ${client}px viewport"
    FAILS=$((FAILS+1))
  else
    echo "shoot: ok   ${w}px -> $OUT_ABS/shot-$w.png"
  fi
  pw eval '() => { const p = document.querySelector("details.pop"); if (p) p.open = true; }' >/dev/null
  dims="$(pw eval '() => document.documentElement.scrollWidth + "x" + document.documentElement.clientWidth' \
    | grep -oE '"[0-9]+x[0-9]+"' | tr -d '"' || true)"
  scroll="${dims%x*}"; client="${dims#*x}"
  if [ -n "$dims" ] && [ "$scroll" -gt "$client" ]; then
    echo "shoot: FAIL ${w}px (popover open): page is ${scroll}px wide in a ${client}px viewport"
    FAILS=$((FAILS+1))
  fi
  pw eval '() => { const p = document.querySelector("details.pop"); if (p) p.open = false; }' >/dev/null
done
[ "$FAILS" -eq 0 ]
