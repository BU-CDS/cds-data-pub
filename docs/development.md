# Development

The catalog is one self-contained page built from `datasets.toml` by Python 3.12 (standard library
only). Design rationale lives in the internal `cds-osn` repo.

## Setup

    uv venv --python 3.12 .venv

BU branding assets (logo, fonts) come from a sibling clone at `../cpu-cds-scc/assets`; override
with `PUB_CPU_CLONE`. They are never copied into this repo.

## Common tasks

| Task | Command |
|---|---|
| Preview with stress-case data | `.venv/bin/python -m scripts.build_page --manifest examples/sample.toml --out previews/index.html --preview` |
| Screenshots + overflow check | `scripts/shoot.sh previews/index.html previews` |
| Unit tests | `.venv/bin/python -m unittest discover -s tests -t .` |
| Deploy test | `tests/test_deploy.sh` |
| Coverage (≥ 80%) | `uvx --from 'coverage==7.16.2' coverage run --source=scripts -m unittest discover -s tests -t . && uvx --from 'coverage==7.16.2' coverage report --fail-under=80` |
| Lint | `ruff check scripts tests && ruff format --check scripts tests` |
| Stage the real page without pushing | `DEPLOY_PUSH=0 ./publish.sh` |
| Publish | `./publish.sh` (from `main` only) |

`deploy.sh`, `publish.sh`, `test_deploy.sh` (git worktree) and `shoot.sh` (playwright-cli) need to
run outside a restrictive sandbox. `check_page` is a regression check, not a security boundary: the
renderer's escaping is what keeps manifest text inert.

Analytics: GA4 `G-MTV6EXSR2V`. Outbound clicks are **download-link clicks**, not downloads: they
miss `curl` and include failed attempts and source/DOI links.

## Layout

| Path | What |
|---|---|
| `datasets.toml` | The catalog (optional `notice`, one `[[dataset]]` per dataset) |
| `scripts/manifest.py` | Manifest rules; `BUCKET_BASE` |
| `scripts/render.py`, `scripts/build_page.py` | HTML/CSS and the build CLI |
| `scripts/check_page.py`, `scripts/check_links.py` | Page gate and anonymous link check |
| `publish.sh`, `deploy.sh` | Build → gate → link check → `page` branch |
| `examples/sample.toml` | Stress-case manifest for layout work; never deployed |

Last verified: 2026-10-07
