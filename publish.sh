#!/usr/bin/env bash
# publish.sh — build, gate, link-check and deploy the catalog page; all or nothing (set -e).
# DEPLOY_PUSH=0 runs every step and stages the page commit locally without pushing.
# A push needs a clean tree (no changed or untracked files: every datasets/*.toml is built) and
# the GA tag; deploy.sh pushes only when called from here, and only from main.
# Uses git worktree (deploy.sh): run outside a restrictive sandbox.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
export PYTHONPATH="$ROOT"

GATE=()
if [ "${DEPLOY_PUSH:-1}" = 1 ]; then
  [ -z "$(git -C "$ROOT" status --porcelain)" ] || {
    echo "publish: REFUSED -- uncommitted or untracked files; commit or remove them first (DEPLOY_PUSH=0 stages)" >&2
    git -C "$ROOT" status --short >&2
    exit 1
  }
  GATE=(--require-ga "$("$PY" -P -c 'from scripts.build_page import GA_ID; print(GA_ID)')")
fi

"$PY" -P -m scripts.build_page --out "$ROOT/index.html"
for f in index.html about.html publish.html; do
  "$PY" -P -m scripts.check_page "$ROOT/$f" ${GATE[@]+"${GATE[@]}"}
done
if ! "$PY" -P -c 'import sys; from pathlib import Path; from scripts.manifest import load_catalog
sys.exit(not load_catalog(Path(sys.argv[1])).steward)' "$ROOT"; then
  echo "publish: WARNING -- no steward contact in catalog.toml: Publish says a contact is coming" >&2
fi
"$PY" -P -m scripts.check_links --catalog "$ROOT"
CDS_PUBLISH_GATED=1 "$ROOT/deploy.sh"
