#!/usr/bin/env bash
# smoke.sh — behaviour checks for a built page in headless Chromium (playwright-cli):
# URL tag filter, empty state, unknown tag ignored, #slug reveal, Escape focus return, layout and
# screenshots. Usage: scripts/smoke.sh [PAGE] [OUTDIR]  (defaults: previews/index.html,
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
pw eval '() => { const s = document.querySelector(".acts details.pop:last-of-type > summary"); s.focus(); s.click(); }' >/dev/null
pw press Escape >/dev/null
check "Escape closes popover and returns focus" \
  "$(val '() => { const p = document.querySelector(".acts details.pop:last-of-type"); return !p.open && document.activeElement === p.querySelector("summary"); }')" "true"
pw eval '() => { document.querySelector(".acts details.pop:last-of-type").open = true; document.getElementById("q").focus(); }' >/dev/null
pw press Escape >/dev/null
check "Escape pressed elsewhere closes the popover but leaves focus where it was" \
  "$(val '() => !document.querySelector(".acts details.pop:last-of-type").open && document.activeElement.id === "q"')" "true"
pw resize 390 600 >/dev/null
pw eval '() => document.querySelector(".acts details.pop:last-of-type > summary").click()' >/dev/null
check "short viewport: open popover's Copy is reachable" \
  "$(val '() => { const p = document.querySelector("details.pop[open]"); p.querySelectorAll("label")[1].click(); const b = [...p.querySelectorAll(".copy")].find(x => x.offsetParent); b.scrollIntoView(); const r = b.getBoundingClientRect(); return r.height > 0 && r.bottom <= innerHeight && r.top >= 0; }')" "true"
pw resize 1440 900 >/dev/null
pw goto "$URL" >/dev/null
check "app shell (≥1100): the page itself does not scroll, the list does" "$(val '() => { const l = document.querySelector(".list"); return document.documentElement.scrollHeight <= innerHeight + 1 && l.scrollHeight > l.clientHeight; }')" "true"
mid="$(val '() => { const c = document.querySelectorAll(".ds"); return c[Math.floor(c.length / 2)].id; }')"
pw goto "$URL#$mid" >/dev/null
check "anchor target is scrolled into view inside the list" "$(val "() => { const l = document.querySelector(\".list\").getBoundingClientRect(), r = document.getElementById(\"$mid\").getBoundingClientRect(); return document.querySelector(\".list\").scrollTop > 0 && r.top >= l.top && r.top < l.bottom; }")" "true"
pw goto "$URL" >/dev/null
pw eval '() => { document.querySelector(".list").scrollTop = 1500; }' >/dev/null
pw run-code "async page => { await page.waitForTimeout(400); await page.reload(); await page.waitForTimeout(200); }" >/dev/null
check "reload keeps the list's scroll position" "$(val '() => document.querySelector(".list").scrollTop > 1000')" "true"
pw goto "$URL" >/dev/null
pw eval '() => document.querySelector(".list").focus()' >/dev/null
pw press PageDown >/dev/null
check "the list scrolls by keyboard once focused" "$(val '() => document.querySelector(".list").scrollTop > 0')" "true"
pw resize 390 844 >/dev/null
pw goto "$URL" >/dev/null
pw eval '() => scrollTo(0, 2000)' >/dev/null
check "search stays visible on phones after scrolling" "$(val '() => { const r = document.getElementById("q").getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }')" "true"
pw resize 1440 900 >/dev/null
pw goto "$URL" >/dev/null
check "Tab out of an open popover closes it" "$(val '() => { const ps = document.querySelectorAll(".acts details.pop:last-of-type"); ps[0].open = true; ps[0].querySelector("summary").focus(); ps[1].querySelector("summary").focus(); return ps[0].open; }')" "false"
pw eval '() => { document.querySelector(".list").scrollTop = 3000; document.querySelector(".chip").click(); }' >/dev/null
check "filtering from far down the list shows the first match" "$(val '() => { const l = document.querySelector(".list").getBoundingClientRect(), c = document.querySelector(".ds:not([hidden])").getBoundingClientRect(); return c.top >= l.top; }')" "true"
pw resize 390 844 >/dev/null
check "phone: the list is not a tab stop" "$(val '() => document.querySelector(".list").tabIndex')" "-1"
pw resize 1440 900 >/dev/null
check "wide: the list is a tab stop again" "$(val '() => document.querySelector(".list").tabIndex')" "0"
pw goto "$URL" >/dev/null
pw eval '() => { const s = document.querySelector(".acts details.pop > summary"); s.focus(); s.click(); }' >/dev/null
pw press Shift+Tab >/dev/null
check "Shift+Tab out of the first card's popover closes it" "$(val '() => document.querySelector(".acts details.pop").open')" "false"
pw resize 1280 400 >/dev/null
pw goto "$URL" >/dev/null
check "short window (≥1100 wide): the page scrolls as normal, no clipped list" "$(val '() => { const l = document.querySelector(".list"); return document.scrollingElement.scrollHeight > innerHeight && l.scrollHeight <= l.clientHeight + 1; }')" "true"
pw resize 1440 900 >/dev/null
pw goto "$URL" >/dev/null
pw eval '() => { const p = document.querySelector(".acts details.pop:last-of-type"); p.open = true; p.querySelector(".flist a").focus(); }' >/dev/null
pw run-code "async page => { await page.locator('.acts details.pop[open] .hint').first().click({ timeout: 3000 }); }" >/dev/null 2>&1 || true
check "a real click on text inside a popover keeps it open" "$(val '() => document.querySelector(".acts details.pop:last-of-type").open')" "true"
check "Copy and more buttons name their dataset" "$(val '() => [...document.querySelectorAll(".copy, .more")].every(b => b.getAttribute("aria-describedby") === "t-" + b.closest(".ds").id)')" "true"
check "a one-paragraph short description gets no more button" "$(val '() => [...document.querySelectorAll(".desc")].filter(d => d.children.length === 1 && d.firstElementChild.textContent.length < 60).every(d => d.nextElementSibling.hidden)')" "true"
check "clamped descriptions show only their first paragraph" "$(val '() => [...document.querySelectorAll(".desc.clamp")].every(d => [...d.children].slice(1).every(p => getComputedStyle(p).display === "none"))')" "true"
pw resize 1280 640 >/dev/null
pw goto "$URL" >/dev/null
pw eval '() => { const m = document.querySelector(".more-tags"); if (m) m.click(); const cs = document.querySelector(".chips"); for (let i = 0; i < 60; i++) cs.append(cs.firstElementChild.cloneNode(true)); }' >/dev/null
check "a long tag list: the sidebar scrolls, the page does not" \
  "$(val '() => { const s = document.querySelector(".side-in"); s.scrollTop = s.scrollHeight; const c = document.querySelector(".count").getBoundingClientRect(), r = document.querySelector(".side").getBoundingClientRect(); return c.bottom <= r.bottom + 1 && document.scrollingElement.scrollHeight <= innerHeight; }')" "true"
pw resize 390 844 >/dev/null
bmid="$(val '() => { const b = [...document.querySelectorAll(".ds")].filter(c => c.dataset.tags.split(" ").includes("boston")); return b[Math.floor(b.length / 2)].id; }')"
pw goto "$URL?tag=boston#$bmid" >/dev/null
check "phone: anchor title clears the sticky search bar with a filter on" "$(val "() => document.getElementById(\"$bmid\").querySelector(\"h2\").getBoundingClientRect().top >= document.querySelector(\".side\").getBoundingClientRect().bottom")" "true"
pw goto "$URL" >/dev/null
pw eval '() => { const c = document.querySelectorAll(".ds")[14]; c.scrollIntoView(); c.querySelector("a.tag").click(); }' >/dev/null
check "phone: tapping a tag badge shows the top of the results" "$(val '() => { const c = document.querySelector(".ds:not([hidden])"); const r = c.getBoundingClientRect(); return r.top >= 0 && r.top < innerHeight; }')" "true"
pw resize 1440 900 >/dev/null
pw goto "$URL" >/dev/null
pw eval '() => { const s = document.querySelector(".acts details.pop:last-of-type > summary"); s.focus(); s.click(); s.parentElement.querySelectorAll("label")[1].click(); }' >/dev/null
pw run-code "async page => { const b = await page.locator('.acts details.pop[open] .panel pre').filter({ visible: true }).first().boundingBox(); await page.mouse.move(b.x + 10, b.y + 8); await page.mouse.down(); await page.mouse.move(b.x - 60, b.y + 8, { steps: 4 }); await page.mouse.up(); }" >/dev/null 2>&1 || true
check "drag-select ending outside keeps the popover open" "$(val '() => document.querySelector(".acts details.pop:last-of-type").open')" "true"
pw resize 1280 700 >/dev/null
pw goto "$URL" >/dev/null
check "More tags moves focus to the first revealed chip" "$(val '() => { const m = document.querySelector(".more-tags"); m.focus(); m.click(); return document.activeElement.matches(".chip.extra"); }')" "true"
pw resize 1440 900 >/dev/null
pw goto "$URL" >/dev/null
pw eval '() => { const l = document.querySelector(".list"), lr = l.getBoundingClientRect(); const c = [...l.querySelectorAll(".ds")].find(c => c.getBoundingClientRect().top > lr.top + 0.55 * lr.height); c.querySelector(".acts details.pop:last-of-type > summary").click(); }' >/dev/null
pw run-code "async page => { await page.waitForTimeout(300); }" >/dev/null
check "a popover opened low in the list is scrolled fully into view" "$(val '() => { const l = document.querySelector(".list").getBoundingClientRect(), b = document.querySelector(".pop[open] .pop-body").getBoundingClientRect(); return b.bottom <= l.bottom + 1; }')" "true"
pw goto "$URL#boston-tide-gauge" >/dev/null
pw eval '() => { document.querySelector("#boston-tide-gauge details.det").open = true; }' >/dev/null
COLS='const sec = document.querySelector("#boston-tide-gauge .dx-cols"), shown = () => [...sec.children].filter(li => li.offsetParent).length'
check "long column list: first 20 names, filter and Show all visible" "$(val "() => { $COLS; const b = document.querySelector('#boston-tide-gauge .colmore'); return shown() + ' ' + !!b.offsetParent + ' ' + !!document.querySelector('#boston-tide-gauge .colq').offsetParent; }")" "20 true true"
check "Show all reveals every column name" "$(val "() => { $COLS; const b = document.querySelector('#boston-tide-gauge .colmore'); b.click(); return shown() + ' ' + b.getAttribute('aria-expanded') + ' ' + b.textContent; }")" "34 true Show fewer"
pw eval '() => { const b = document.querySelector("#boston-tide-gauge .colmore"); b.click(); }' >/dev/null
pw eval '() => { const q = document.querySelector("#boston-tide-gauge .colq"); q.value = "harmonic_m"; q.dispatchEvent(new Event("input")); }' >/dev/null
check "the filter searches every name, including ones Show all hides" "$(val "() => { $COLS; return shown() + ' | ' + document.querySelector('#boston-tide-gauge .colcount').textContent; }")" "8 | 8 of 34 match"
pw eval '() => { const q = document.querySelector("#boston-tide-gauge .colq"); q.value = "zzz"; q.dispatchEvent(new Event("input")); }' >/dev/null
check "a filter with no match says so" "$(val "() => document.querySelector('#boston-tide-gauge .colcount').textContent")" "No column names match"
pw resize 1440 900 >/dev/null
pw goto "$URL" >/dev/null
check "Copy link copies the dataset's address (or puts it in the address bar)" "$(val '() => new Promise(r => { const b = document.querySelector(".ds .btn.link"); b.click(); setTimeout(() => r(/^Link (copied|in address bar)$/.test(b.textContent) && (b.textContent === "Link copied" || location.hash === b.dataset.link)), 300); })')" "true"
for doc in about publish; do
  pw goto "${URL%/*}/$doc.html" >/dev/null
  check "$doc.html: scrolls like a document, links back to the catalog" "$(val '() => getComputedStyle(document.documentElement).overflowY !== "hidden" && !!document.querySelector("a.back[href=\"index.html\"]") && document.querySelector(".prose h2") !== null')" "true"
done
pw goto "$URL" >/dev/null
check "the band's buttons go to the About and Publish pages" "$(val '() => [...document.querySelectorAll(".band .cta")].map(a => a.getAttribute("href")).join(" ")')" "publish.html about.html catalog.json"
pw goto "$URL?q=zzqqxx-no-such-thing" >/dev/null
check "Clear filters in the empty state moves focus to the search box" "$(val '() => { document.querySelector(".empty .clear").click(); return document.activeElement.id; }')" "q"
pw resize 844 390 >/dev/null
pw goto "$URL" >/dev/null
check "landscape phone: the filter panel scrolls away with the page" "$(val '() => { scrollTo(0, 1500); return Math.round(document.querySelector(".side").getBoundingClientRect().bottom) <= 0; }')" "true"
pw resize 1440 900 >/dev/null
for w in 1440 390; do
  pw resize "$w" 900 >/dev/null
  pw eval '() => scrollTo(0, 0)' >/dev/null
  pw screenshot --full-page --filename="$OUT_ABS/smoke-$w.png" >/dev/null
done
echo "smoke: screenshots in $OUT_ABS/smoke-{1440,390}.png"
[ "$FAILS" -eq 0 ]
