#!/usr/bin/env bash
# test_deploy.sh — deploy.sh in throwaway repos: worktree lifecycle, page gate, page branch shape,
# push guards (publish.sh only, remote edits, domain); publish.sh's clean-tree gate.
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
  for f in index.html about.html publish.html; do printf '%s\n' "${2//@@SHA@@/$sha}" > "$1/$f"; done
  git -C "$1" add -A
  git -C "$1" -c commit.gpgsign=false commit -qm init
}
wt_count(){ git -C "$1" worktree list | wc -l | tr -d ' '; }
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

# 1. happy path: page branch carries exactly the three pages, catalog.json, .nojekyll, CNAME
D="$WORK/r1"; mkrepo "$D" "$CLEAN"
out="$(DEPLOY_PUSH=0 "$D/deploy.sh" 2>&1)" || bad "happy path failed: $out"
files="$(git -C "$D" ls-tree --name-only page | LC_ALL=C sort | tr '\n' ' ')"
[ "$files" = ".nojekyll CNAME about.html catalog.json index.html publish.html " ] && ok "page branch shape" || bad "page has: $files"
[ "$(git -C "$D" show page:CNAME)" = "data.cds.bu.edu" ] && ok "CNAME is data.cds.bu.edu" || bad "CNAME wrong"
[ "$(wt_count "$D")" = 1 ] && ok "no leftover worktree" || bad "worktree left behind"

# 2. a second deploy amends: page stays one commit
sha="$(digest "$D")"
printf '%s\n' "${CLEAN/2026-10-06/2026-10-07}" | sed "s/@@SHA@@/$sha/" > "$D/index.html"
DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1 || bad "second deploy failed"
[ "$(git -C "$D" rev-list --count page)" = 1 ] && ok "page stays a single commit" || bad "page grew history"
git -C "$D" show page:index.html | grep -q 2026-10-07 && ok "second deploy carries new page" || bad "stale page"

# 2b. an empty CATALOG_DOMAIN is refused (dropping CNAME would unbind the domain); page untouched
before="$(git -C "$D" rev-parse page)"
out="$(CATALOG_DOMAIN= DEPLOY_PUSH=0 "$D/deploy.sh" 2>&1)" && bad "empty CATALOG_DOMAIN deployed"
grep -q "unbind" <<<"$out" && ok "empty CATALOG_DOMAIN refused" || bad "wrong refusal: $out"
[ "$(git -C "$D" rev-parse page)" = "$before" ] && ok "refused domain left page alone" || bad "page changed"

# 2b2. a file that reached page by other means is not carried into the next publish
git -C "$D" worktree add -q "$WORK/extra" page
printf 'x\n' > "$WORK/extra/private-notes.txt"; git -C "$WORK/extra" add private-notes.txt
git -C "$WORK/extra" -c commit.gpgsign=false commit -q --amend -m extra
git -C "$D" worktree remove --force "$WORK/extra"
DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1 || bad "deploy over an extra file failed"
git -C "$D" ls-tree --name-only page | grep -q private-notes && bad "stray file kept on page" || ok "stray file dropped from page"

# 2b3. a page branch with history is refused (amending would publish that history)
git -C "$D" worktree add -q "$WORK/hist" page
git -C "$WORK/hist" -c commit.gpgsign=false commit -q --allow-empty -m child
git -C "$D" worktree remove --force "$WORK/hist"
out="$(DEPLOY_PUSH=0 "$D/deploy.sh" 2>&1)" && bad "page with history deployed"
grep -q "has history" <<<"$out" && ok "page with history refused" || bad "wrong refusal: $out"

# 2c. a missing catalog.json is refused
D="$WORK/r1b"; mkrepo "$D" "$CLEAN"; rm "$D/catalog.json"
if DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1; then bad "deployed without catalog.json"
elif git -C "$D" show-ref -q --verify refs/heads/page; then bad "missing catalog.json still created page"
else ok "missing catalog.json refused before any page commit"; fi

# 2c2. a missing doc page, or one that fails the gate, is refused before any page commit
D="$WORK/r1c"; mkrepo "$D" "$CLEAN"; rm "$D/about.html"
if DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1; then bad "deployed without about.html"
elif git -C "$D" show-ref -q --verify refs/heads/page; then bad "missing about.html still created page"
else ok "missing about.html refused before any page commit"; fi
D="$WORK/r1d"; mkrepo "$D" "$CLEAN"
printf '<script src="https://evil.example/x.js"></script>\n' >> "$D/publish.html"
if DEPLOY_PUSH=0 "$D/deploy.sh" >/dev/null 2>&1; then bad "deployed a publish.html that fails check_page"
else ok "publish.html failing check_page refused"; fi

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
out="$(CDS_PUBLISH_GATED=1 "$D/deploy.sh" 2>&1)" && bad "off-main push allowed"
grep -q "only from main" <<<"$out" && ok "off-main push refused" || bad "wrong refusal: $out"
git -C "$D" show-ref -q --verify refs/heads/page && bad "off-main run created page" || ok "no page branch created"

# 3d. a push without publish.sh's gates is refused before any commit
D="$WORK/g-direct"; mkrepo "$D" "$CLEAN"
out="$("$D/deploy.sh" 2>&1)" && bad "direct push allowed"
grep -q "through ./publish.sh" <<<"$out" && ok "direct push refused" || bad "wrong refusal: $out"
git -C "$D" show-ref -q --verify refs/heads/page && bad "direct push created page" || ok "no page branch created"

# 4. a failed push must not strand a worktree; the next run is not wedged
export CDS_PUBLISH_GATED=1
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

# 6. pushes to a real remote: first and repeat publish succeed; an edit made on the remote since
#    (a web commit to page) refuses the push and survives; after a fetch the publish goes through
D="$WORK/r6"; mkrepo "$D" "$CLEAN"; git init -q --bare "$WORK/r6.git"
git -C "$D" remote add origin "$WORK/r6.git"
"$D/deploy.sh" >/dev/null 2>&1 && ok "first push to an empty remote" || bad "first push failed"
"$D/deploy.sh" >/dev/null 2>&1 && ok "repeat push" || bad "repeat push failed"
git clone -q -b page "$WORK/r6.git" "$WORK/r6-web"
printf 'x\n' > "$WORK/r6-web/web.txt"; git -C "$WORK/r6-web" add web.txt
git -C "$WORK/r6-web" -c user.email=w@w -c user.name=w -c commit.gpgsign=false commit -qm web
git -C "$WORK/r6-web" push -q origin page
web="$(git -C "$WORK/r6.git" rev-parse page)"
out="$("$D/deploy.sh" 2>&1)" && bad "pushed over a remote edit"
grep -q "changed since" <<<"$out" && ok "remote edit refuses the push" || bad "wrong refusal: $out"
[ "$(git -C "$WORK/r6.git" rev-parse page)" = "$web" ] && ok "remote edit survives" || bad "remote edit lost"
git -C "$D" fetch -q origin page
"$D/deploy.sh" >/dev/null 2>&1 && ok "push after fetch" || bad "push after fetch failed"
[ "$(git -C "$WORK/r6.git" rev-list --count page)" = 1 ] && ok "remote page is one commit" || bad "remote page grew history"

# 7. publish.sh refuses untracked files (an uncommitted datasets/*.toml would be published)
D="$WORK/r7"; mkrepo "$D" "$CLEAN"; cp "$R/publish.sh" "$D/publish.sh"
git -C "$D" add publish.sh && git -C "$D" -c commit.gpgsign=false commit -qm publish
mkdir -p "$D/datasets"; printf 'title = "draft"\n' > "$D/datasets/draft.toml"
out="$("$D/publish.sh" 2>&1)" && bad "published with an untracked dataset"
grep -q "untracked" <<<"$out" && ok "untracked dataset refused" || bad "wrong refusal: $out"
unset CDS_PUBLISH_GATED

echo "failures: $FAILS"; [ "$FAILS" -eq 0 ]
