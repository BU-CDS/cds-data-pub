#!/usr/bin/env bash
# deploy.sh — publish the built index.html (catalog page) to the page branch, which GitHub
# Pages serves at data.cds.bu.edu. page is kept as one amended commit and force-pushed, so the
# public page accumulates no history. Adapted from pub-cds-scc/deploy.sh.
# DEPLOY_PUSH=0 stages the commit locally without pushing. A push happens only when publish.sh
# calls this (CDS_PUBLISH_GATED=1), so a direct run cannot skip its clean-tree, GA and link gates
# by accident (the flag guards against mistakes, not against someone setting it on purpose).
# CATALOG_DOMAIN switches the custom domain; it cannot be empty: dropping CNAME while DNS still
# points at GitHub Pages leaves data.cds.bu.edu open to takeover. Uses git worktree: run outside
# a restrictive sandbox.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(git -C "$ROOT" rev-parse --show-toplevel)"
PAGE="$ROOT/index.html"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
DOMAIN="${CATALOG_DOMAIN-data.cds.bu.edu}"
[[ "$DOMAIN" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || {
  echo "deploy: REFUSED -- CATALOG_DOMAIN must be a host name; an empty one would unbind the domain" >&2
  exit 1
}
CAT="$ROOT/catalog.json"
[ -f "$PAGE" ] || { echo "deploy: no index.html to publish" >&2; exit 1; }
[ -f "$CAT" ] || { echo "deploy: no catalog.json to publish (run build_page)" >&2; exit 1; }
DOCS=(about.html publish.html)   # written by build_page beside index.html
for d in "${DOCS[@]}"; do
  [ -f "$ROOT/$d" ] || { echo "deploy: no $d to publish (run build_page)" >&2; exit 1; }
done

# unconditional gate: the page must pass check_page, and both index.html and catalog.json must
# have been built from this checkout's catalog (catalog.toml + datasets/), so a sample or
# preview build can never reach the page branch.
# publish.sh additionally runs check_links and, when pushing, requires GA.
for f in "$PAGE" "${DOCS[@]/#/$ROOT/}"; do
  if ! PYTHONPATH="$ROOT" "$PY" -P -m scripts.check_page "$f" --catalog "$ROOT"; then
    echo "deploy: REFUSED -- $(basename "$f") fails check_page" >&2
    exit 1
  fi
done
if ! PYTHONPATH="$ROOT" "$PY" -P -c 'import json, sys
from pathlib import Path
from scripts.manifest import catalog_digest
sys.exit(json.load(open(sys.argv[1])).get("catalog_digest") != catalog_digest(Path(sys.argv[2])))' "$CAT" "$ROOT"; then
  echo "deploy: REFUSED -- catalog.json was not built from this checkout's catalog" >&2
  exit 1
fi
if [ "${DEPLOY_PUSH:-1}" = 1 ]; then
  [ "${CDS_PUBLISH_GATED:-}" = 1 ] || {
    echo "deploy: REFUSED -- push through ./publish.sh, which runs the clean-tree, GA and link gates" >&2
    exit 1
  }
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

# page must stay one root commit; amending a commit with parents would publish their history
if git -C "$REPO" rev-parse -q --verify 'page^' >/dev/null; then
  echo "deploy: REFUSED -- local page has history; inspect it, then 'git branch -D page' and rerun" >&2
  exit 1
fi

# publish: amend the single page commit; its tree is exactly the files below, nothing older
WT="$(mktemp -d)"
trap 'git -C "$REPO" worktree remove --force "$WT" 2>/dev/null || rm -rf "$WT"; git -C "$REPO" worktree prune' EXIT
git -C "$REPO" worktree add -q "$WT" page
git -C "$WT" rm -rqf -- .
cp "$PAGE" "$WT/index.html"; cp "$CAT" "$WT/catalog.json"; : > "$WT/.nojekyll"
for d in "${DOCS[@]}"; do cp "$ROOT/$d" "$WT/$d"; done
printf '%s\n' "$DOMAIN" > "$WT/CNAME"   # Pages needs CNAME in the published branch
git -C "$WT" add -f index.html .nojekyll catalog.json CNAME "${DOCS[@]}"
git -C "$WT" -c commit.gpgsign=false commit -q --amend -m "Publish $(date '+%F %H:%M %Z')"
if [ "${DEPLOY_PUSH:-1}" = 1 ]; then
  # overwrite only the page we last fetched or pushed: an edit made on GitHub since then (a web
  # commit to page) refuses the push instead of vanishing
  seen="$(git -C "$REPO" rev-parse -q --verify refs/remotes/origin/page || true)"
  git -C "$WT" push -q --force-with-lease="page:$seen" origin page || {
    echo "deploy: REFUSED -- page on GitHub changed since the last fetch or publish." >&2
    echo "  Look first: git fetch origin +refs/heads/page:refs/remotes/origin/page" >&2
    echo "  then git show --stat origin/page, and rerun to publish over it." >&2
    exit 1
  }
  echo "deploy: pushed index.html, about.html, publish.html and catalog.json to page"
else
  echo "deploy: staged page locally (DEPLOY_PUSH=0, not pushed)"
fi
git -C "$REPO" worktree remove --force "$WT"
trap - EXIT
