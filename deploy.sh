#!/usr/bin/env bash
# deploy.sh — publish the built index.html (catalog page) to the page branch, which GitHub
# Pages serves at data.cds.bu.edu. page is kept as one amended commit and force-pushed, so the
# public page accumulates no history. Adapted from pub-cds-scc/deploy.sh.
# DEPLOY_PUSH=0 stages the commit locally without pushing. CATALOG_DOMAIN= (empty) omits CNAME
# so the page serves on the default github.io address. Uses git worktree: run outside a
# restrictive sandbox.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(git -C "$ROOT" rev-parse --show-toplevel)"
PAGE="$ROOT/index.html"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
DOMAIN="${CATALOG_DOMAIN-data.cds.bu.edu}"   # CATALOG_DOMAIN= (empty): default github.io domain, no CNAME
[ -f "$PAGE" ] || { echo "deploy: no index.html to publish" >&2; exit 1; }

# unconditional gate: the page must pass check_page and must have been built from this
# checkout's catalog (catalog.toml + datasets/), so a sample or preview build can never reach
# the page branch.
# publish.sh additionally runs check_links and, when pushing, requires GA.
if ! PYTHONPATH="$ROOT" "$PY" -P -m scripts.check_page "$PAGE" --catalog "$ROOT"; then
  echo "deploy: REFUSED -- index.html fails check_page" >&2
  exit 1
fi
if [ "${DEPLOY_PUSH:-1}" = 1 ]; then
  branch="$(git -C "$REPO" rev-parse --abbrev-ref HEAD)"
  [ "$branch" = main ] || {
    echo "deploy: REFUSED -- on '$branch'; a push publishes only from main (DEPLOY_PUSH=0 stages)" >&2
    exit 1
  }
fi

# reap a stale registration first: a deploy that died between 'worktree add' and 'remove'
# leaves page claimed by a temp worktree whose directory is gone, wedging every later add
git -C "$REPO" worktree prune

# create page once (orphan, single commit) if it does not exist yet
if ! git -C "$REPO" show-ref --verify -q refs/heads/page; then
  WT0="$(mktemp -d)"
  trap 'git -C "$REPO" worktree remove --force "$WT0" 2>/dev/null || rm -rf "$WT0"; git -C "$REPO" worktree prune' EXIT
  git -C "$REPO" worktree add -q --detach "$WT0"
  ( cd "$WT0" && git checkout -q --orphan page \
      && git rm -rq --cached . && git clean -fdxq \
      && : > .nojekyll && cp "$PAGE" index.html \
      && git add -f index.html .nojekyll \
      && git -c commit.gpgsign=false commit -q -m "Publish $(date '+%F %H:%M %Z')" )
  git -C "$REPO" worktree remove --force "$WT0"
  trap - EXIT
fi

# publish: amend the single page commit with the current page
WT="$(mktemp -d)"
trap 'git -C "$REPO" worktree remove --force "$WT" 2>/dev/null || rm -rf "$WT"; git -C "$REPO" worktree prune' EXIT
git -C "$REPO" worktree add -q "$WT" page
cp "$PAGE" "$WT/index.html"; : > "$WT/.nojekyll"
git -C "$WT" add -f index.html .nojekyll
if [ -n "$DOMAIN" ]; then
  printf '%s\n' "$DOMAIN" > "$WT/CNAME"   # Pages needs CNAME in the published branch
  git -C "$WT" add -f CNAME
else
  git -C "$WT" rm -q --cached --ignore-unmatch CNAME; rm -f "$WT/CNAME"
fi
git -C "$WT" -c commit.gpgsign=false commit -q --amend -m "Publish $(date '+%F %H:%M %Z')"
if [ "${DEPLOY_PUSH:-1}" = 1 ]; then
  git -C "$WT" push -qf origin page
  echo "deploy: pushed index.html to page"
else
  echo "deploy: staged page locally (DEPLOY_PUSH=0, not pushed)"
fi
git -C "$REPO" worktree remove --force "$WT"
trap - EXIT
