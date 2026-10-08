# Development

The catalog is one self-contained page built from `catalog.toml` + `datasets/` by Python 3.12
(standard library only). Design rationale lives in the internal `cds-osn` repo.

## Setup

    uv venv --python 3.12 .venv

BU branding assets (logo, fonts) come from a sibling clone at `../cpu-cds-scc/assets`; override
with `PUB_CPU_CLONE`. They are never copied into this repo.

## Common tasks

| Task | Command |
|---|---|
| Preview with stress-case data | `.venv/bin/python -m scripts.build_page --catalog examples/sample --out previews/index.html --preview` |
| Screenshots + overflow check (1920–320 px, also with a popover open) | `scripts/shoot.sh previews/index.html previews` |
| Browser behaviour: filters, URL state, `#slug`, Escape focus, app-shell layout, screenshots | `scripts/smoke.sh previews/index.html previews` (build from `examples/sample` first) |
| Unit tests | `.venv/bin/python -m unittest discover -s tests -t .` |
| Deploy test | `tests/test_deploy.sh` |
| Coverage (≥ 80%) | `uvx --from 'coverage==7.16.2' coverage run --source=scripts -m unittest discover -s tests -t . && uvx --from 'coverage==7.16.2' coverage report --fail-under=80` |
| Lint | `ruff check scripts tests && ruff format --check scripts tests` |
| Stage the real page without pushing | `DEPLOY_PUSH=0 ./publish.sh` |
| Publish | `./publish.sh` (from `main` only) |
| Publish to the default domain (testing; no `CNAME`) | `CATALOG_DOMAIN= ./publish.sh` → `https://bu-cds.github.io/cds-data-pub/` |

`deploy.sh`, `publish.sh`, `test_deploy.sh` (git worktree), `shoot.sh` and `smoke.sh` (playwright-cli) need to
run outside a restrictive sandbox. `check_page` is a regression check, not a security boundary: the
renderer's escaping is what keeps manifest text inert.

Layout: the header sticks on screens ≥1100px and the search block sticks below that; cards
turn two-column at ≥1300px; the page caps at 1920px (`--content-max`).

Analytics: GA4 `G-MTV6EXSR2V`. Outbound clicks are **download-link clicks**, not downloads: they
miss `curl` and include failed attempts and source/DOI links. Like cluster.cds.bu.edu (checked
2026-10-07), GA sets two first-party cookies, `_ga` and `_ga_<id>`, on `.bu.edu`: a random visitor
ID kept about 13 months, no personal data. The page's own script uses no storage or cookies.

## Catalog rules

One `datasets/<slug>.toml` per dataset; the build refuses anything else and names the file and
field. Highlights: 1–5 `tags`, each listed in `catalog.toml`; `license` an SPDX identifier or
`Public domain`; every file in one bucket folder (the Get-data commands sync that folder); an
optional `[citation]` (authors as "Family, Given" or an organization, year, title, publisher,
optional url) — without one the dataset cites its catalog entry. The full rules and their tests:
`scripts/manifest.py`, `tests/test_manifest.py`.

## Layout

| Path | What |
|---|---|
| `catalog.toml` | Site-wide: optional `notice`, the allowed `tags` |
| `datasets/<slug>.toml` | One dataset each (the file name is the slug) |
| `scripts/manifest.py` | Catalog rules; `BUCKET_BASE`; `catalog_digest` (the build stamp) |
| `scripts/render.py`, `scripts/build_page.py` | HTML/CSS and the build CLI |
| `scripts/check_page.py`, `scripts/check_links.py` | Page gate and anonymous link check |
| `publish.sh`, `deploy.sh` | Build → gate → link check → `page` branch |
| `scripts/catalog_json.py` | `catalog.json`: every dataset, file, checksum and citation, built beside `index.html` and published with it |
| `examples/sample/` | 24-dataset stress catalog (same layout) for layout work; never deployed |

Last verified: 2026-10-07
