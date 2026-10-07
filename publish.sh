#!/usr/bin/env bash
# publish.sh — build, gate, link-check and deploy the catalog page; all or nothing (set -e).
# DEPLOY_PUSH=0 runs every step and stages the page commit locally without pushing.
# A push needs a clean tree (tracked files) and the GA tag; deploy.sh refuses any branch but main.
# Uses git worktree (deploy.sh): run outside a restrictive sandbox.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
export PYTHONPATH="$ROOT"

GATE=()
if [ "${DEPLOY_PUSH:-1}" = 1 ]; then
  git -C "$ROOT" diff --quiet HEAD -- || {
    echo "publish: REFUSED -- uncommitted changes to tracked files; commit first (DEPLOY_PUSH=0 stages)" >&2
    exit 1
  }
  GATE=(--require-ga "$("$PY" -P -c 'from scripts.build_page import GA_ID; print(GA_ID)')")
fi

"$PY" -P -m scripts.build_page --out "$ROOT/index.html"
"$PY" -P -m scripts.check_page "$ROOT/index.html" ${GATE[@]+"${GATE[@]}"}
"$PY" -P -m scripts.check_links --catalog "$ROOT"
"$ROOT/deploy.sh"
