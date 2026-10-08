#!/usr/bin/env bash
# smoke.sh — behaviour checks for a built page in headless Chromium (playwright-cli):
# URL tag filter, empty state, unknown tag ignored, #slug reveal, Escape focus return, and light
# and dark screenshots. Usage: scripts/smoke.sh [PAGE] [OUTDIR]  (defaults: previews/index.html,
# previews). Build the page from examples/sample first. Run outside a restrictive sandbox.
set -euo pipefail

PAGE="${1:-previews/index.html}"
OUT="${2:-previews}"
[ -f "$PAGE" ] || { echo "smoke: no page at $PAGE" >&2; exit 1; }
mkdir -p "$OUT"
URL="file://$(cd "$(dirname "$PAGE")" && pwd)/$(basename "$PAGE")"
OUT_ABS="$(cd "$OUT" && pwd)"
SESSION="cdssmoke-$$"
export PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS=true
pw(){ playwright-cli -s="$SESSION" "$@"; }
val(){ pw --raw eval "$1" 2>/dev/null | tail -1 | tr -d '"'; }
trap 'pw close >/dev/null 2>&1 || true' EXIT
FAILS=0
check(){ # $1 label, $2 actual, $3 expected
  if [ "$2" = "$3" ]; then echo "smoke: ok   $1"; else echo "smoke: FAIL $1 (got '$2', want '$3')"; FAILS=$((FAILS+1)); fi
}
visible='() => document.querySelectorAll(".ds:not([hidden])").length'
expect_boston='() => [...document.querySelectorAll(".ds")].filter(c => c.dataset.tags.split(" ").includes("boston")).length'

pw open "$URL" >/dev/null
pw resize 1440 900 >/dev/null
total="$(val '() => document.querySelectorAll(".ds").length')"
check "page has dataset cards (else every count check is vacuous)" "$([ "${total:-0}" -gt 0 ] && echo yes)" "yes"
want="$(val "$expect_boston")"
pw goto "$URL?tag=boston" >/dev/null
check "?tag=boston shows only boston cards" "$(val "$visible")" "$want"
check "sidebar list follows the filter" "$(val '() => document.querySelectorAll(".toc li:not([hidden])").length')" "$want"
pw goto "$URL?q=zzqqxx-no-such-thing" >/dev/null
check "nonsense query shows the empty state" "$(val '() => !document.querySelector(".empty").hidden')" "true"
pw goto "$URL?tag=no-such-tag" >/dev/null
check "unknown tag ignored" "$(val "$visible")" "$total"
last="$(val '() => [...document.querySelectorAll(".ds")].find(c => !c.dataset.tags.split(" ").includes("boston")).id')"
pw goto "$URL?tag=boston#$last" >/dev/null
check "#slug of a filtered-out card is revealed" "$(val "() => !document.getElementById(\"$last\").hidden")" "true"
pw goto "$URL?utm_source=news&tag=boston" >/dev/null
check "other query parameters are kept" "$(val '() => new URLSearchParams(location.search).get("utm_source")')" "news"
pw goto "$URL#%E0" >/dev/null
check "a malformed #fragment leaves filtering alive" "$(val '() => { const c = document.querySelector(".chip"); c.click(); return c.getAttribute("aria-pressed"); }')" "true"
pw goto "$URL" >/dev/null
pw eval '() => document.querySelector(".acts details.pop:last-of-type > summary").click()' >/dev/null
pw press Escape >/dev/null
check "Escape closes popover and returns focus" \
  "$(val '() => { const p = document.querySelector(".acts details.pop:last-of-type"); return !p.open && document.activeElement === p.querySelector("summary"); }')" "true"
pw resize 390 600 >/dev/null
pw eval '() => document.querySelector(".acts details.pop:last-of-type > summary").click()' >/dev/null
check "short viewport: open popover's Copy is reachable" \
  "$(val '() => { const b = document.querySelector("details.pop[open] .copy"); b.scrollIntoView(); const r = b.getBoundingClientRect(); return r.height > 0 && r.bottom <= innerHeight && r.top >= 0; }')" "true"
pw resize 1440 900 >/dev/null
pw goto "$URL" >/dev/null
pw eval '() => scrollTo(0, document.body.scrollHeight)' >/dev/null
check "header stays at the top while scrolling (≥1100)" "$(val '() => Math.round(document.querySelector("header").getBoundingClientRect().top)')" "0"
mid="$(val '() => { const c = document.querySelectorAll(".ds"); return c[Math.floor(c.length / 2)].id; }')"
pw goto "$URL#$mid" >/dev/null
check "anchor target lands below the sticky header" "$(val "() => { const h = document.querySelector(\"header\").getBoundingClientRect().bottom; return h > 0 && document.getElementById(\"$mid\").getBoundingClientRect().top >= h; }")" "true"
pw resize 390 844 >/dev/null
pw goto "$URL" >/dev/null
pw eval '() => scrollTo(0, 2000)' >/dev/null
check "search stays visible on phones after scrolling" "$(val '() => { const r = document.getElementById("q").getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }')" "true"
for theme in light dark; do
  pw run-code "async page => { await page.emulateMedia({ colorScheme: '$theme' }); }" >/dev/null
  for w in 1440 390; do
    pw resize "$w" 900 >/dev/null
    pw eval '() => scrollTo(0, 0)' >/dev/null
    pw screenshot --full-page --filename="$OUT_ABS/smoke-$theme-$w.png" >/dev/null
  done
done
echo "smoke: screenshots in $OUT_ABS/smoke-{light,dark}-{1440,390}.png"
[ "$FAILS" -eq 0 ]
