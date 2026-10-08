#!/usr/bin/env bash
# test_deploy.sh — deploy.sh in throwaway repos: worktree lifecycle, page gate, page branch shape.
# Uses git worktree: run outside a restrictive sandbox.
set -uo pipefail

R="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHON="$R/.venv/bin/python"
FAILS=0
ok(){ echo "PASS: $*"; }
bad(){ echo "FAIL: $*"; FAILS=$((FAILS+1)); }
CLEAN='<!doctype html><html><head><meta name="cds-manifest" content="@@SHA@@"></head><body><p>Updated 2026-10-06</p></body></html>'

digest(){ PYTHONPATH="$1" "$PYTHON" -c "from pathlib import Path; from scripts.manifest import catalog_digest; print(catalog_digest(Path('$1')))"; }

mkrepo(){ # $1: dir; $2: page html
  git init -q -b main "$1"
  git -C "$1" config user.email test@test
  git -C "$1" config user.name test
  cp "$R/deploy.sh" "$1/deploy.sh"
  cp -R "$R/scripts" "$1/scripts" && rm -rf "$1/scripts/__pycache__"
  printf 'tags = ["x"]\n' > "$1/catalog.toml"
  sha="$(digest "$1")"
  printf '{"catalog_digest": "%s"}\n' "$sha" > "$1/catalog.json"
  printf '%s\n' "${2//@@SHA@@/$sha}" > "$1/index.html"
  git -C "$1" add -A
  git -C "$1" -c commit.gpgsign=false commit -qm init
}
wt_count(){ git -C "$1" worktree list | wc -l | tr -d ' '; }
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

# 1. happy path: page branch carries exactly index.html, catalog.json, .nojekyll, CNAME
D="$WORK/r1"; mkrepo "$D" "$CLEAN"
out="$(DEPLOY_PUSH=0 "$D/deploy.sh" 2>&1)" || bad "happy path failed: $out"
files="$(git -C "$D" ls-tree --name-only page | LC_ALL=C sort | tr '\n' ' ')"
[ "$files" = ".nojekyll CNAME catalog.json index.html " ] && ok "page branch shape" || bad "page has: $files"
[ "$(git -C "$D" show page:CNAME)" = "data.cds.bu.edu" ] && ok "CNAME is data.cds.bu.edu" || bad "CNAME wrong"
[ "$(wt_count "$D")" = 1 ] && ok "no leftover worktree" || bad "worktree left behind"

# 2. a second deploy amends: page stays one commit
sha="$(digest "$D")"
printf '%s\n' "${CLEAN/2026-10-06/2026-10-07}" | sed "s/@@SHA@@/$sha/" > "$D/index.html"
DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1 || bad "second deploy failed"
[ "$(git -C "$D" rev-list --count page)" = 1 ] && ok "page stays a single commit" || bad "page grew history"
git -C "$D" show page:index.html | grep -q 2026-10-07 && ok "second deploy carries new page" || bad "stale page"

# 2b. CATALOG_DOMAIN= (empty) publishes for the default github.io domain: no CNAME on page;
#     a later default deploy puts it back
CATALOG_DOMAIN= DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1 || bad "empty-domain deploy failed"
files="$(git -C "$D" ls-tree --name-only page | LC_ALL=C sort | tr '\n' ' ')"
[ "$files" = ".nojekyll catalog.json index.html " ] && ok "empty CATALOG_DOMAIN drops CNAME" || bad "page has: $files"
DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1 || bad "default deploy after empty-domain failed"
[ "$(git -C "$D" show page:CNAME 2>/dev/null)" = "data.cds.bu.edu" ] && ok "default deploy restores CNAME" || bad "CNAME not restored"

# 2c. a missing catalog.json is refused
D="$WORK/r1b"; mkrepo "$D" "$CLEAN"; rm "$D/catalog.json"
if DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1; then bad "deployed without catalog.json"
elif git -C "$D" show-ref -q --verify refs/heads/page; then bad "missing catalog.json still created page"
else ok "missing catalog.json refused before any page commit"; fi

# 2d. a catalog.json built from another catalog (e.g. a sample preview at the root) is refused
D="$WORK/r2d"; mkrepo "$D" "$CLEAN"; printf '{"catalog_digest": "%064d"}\n' 0 > "$D/catalog.json"
if DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1; then bad "catalog.json from another catalog was deployed"
else ok "catalog.json from another catalog refused"; fi

# 3. gate: refused pages never reach the page branch
for case in fetch preview nostamp; do
  D="$WORK/g-$case"
  case $case in
    fetch)   page='<html><body><p>Updated 2026-10-06</p><script>fetch("/x")</script></body></html>';;
    preview) page='<html><head><meta name="cds-build" content="preview"></head><body><p>Updated 2026-10-06</p></body></html>';;
    nostamp) page='<html><body><p>hello</p></body></html>';;
  esac
  mkrepo "$D" "$page"
  if DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1; then bad "$case page was deployed"
  elif git -C "$D" show-ref -q --verify refs/heads/page; then bad "$case page created a page branch"
  else ok "$case page refused"; fi
done

# 3b. a page built from another catalog (e.g. the sample, --preview forgotten) is refused
D="$WORK/g-other"; mkrepo "$D" "${CLEAN//@@SHA@@/$(printf '%064d' 0)}"
if DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1; then bad "page from another catalog was deployed"
else ok "page from another catalog refused"; fi

# 3c. pushing from a branch other than main is refused before any commit
D="$WORK/g-branch"; mkrepo "$D" "$CLEAN"; git -C "$D" checkout -qb feature
out="$("$D/deploy.sh" 2>&1)" && bad "off-main push allowed"
grep -q "only from main" <<<"$out" && ok "off-main push refused" || bad "wrong refusal: $out"
git -C "$D" show-ref -q --verify refs/heads/page && bad "off-main run created page" || ok "no page branch created"

# 4. a failed push must not strand a worktree; the next run is not wedged
D="$WORK/r4"; mkrepo "$D" "$CLEAN"
git -C "$D" remote add origin "$WORK/no-such-remote.git"
"$D/deploy.sh" >/dev/null 2>&1 && bad "push to a missing remote should fail"
[ "$(wt_count "$D")" = 1 ] && ok "no worktree stranded after a failed push" || bad "worktree stranded"
out="$("$D/deploy.sh" 2>&1)"
case "$out" in *"already used by worktree"*) bad "second deploy wedged";; *) ok "second deploy not wedged";; esac

# 5. a registration whose directory vanished self-heals
D="$WORK/r5"; mkrepo "$D" "$CLEAN"
DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1 || bad "baseline failed"
git -C "$D" worktree add -q "$WORK/ghost" page && rm -rf "$WORK/ghost"
DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1 && ok "stale registration self-heals" || bad "wedged by stale registration"

echo "failures: $FAILS"; [ "$FAILS" -eq 0 ]
