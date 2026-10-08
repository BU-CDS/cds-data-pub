# Changelog

## 2026-10-07 (v2.1)

- The DOI of re-hosted data (GHCN, penguins) moves into `[citation].doi`: it appears in Cite
  (link, BibTeX, RIS) but not on the card, which shows a DOI only for datasets we publish.
  A citation's DOI always belongs to the work it cites (our own DOI never lands on the original's
  reference). In `catalog.json`, `doi` is likewise our own; the original's DOI is in its
  `citation` strings.
- Layout: the header stays visible on wide screens (on phones the search row does); body text
  1rem with two smaller steps; from 1300px cards are two columns (title, summary line, description
  left; buttons and badges right); page width up to 1920px; on phones the terms note moves below
  the list; printing drops the sidebar.
- Badges no longer touch the Cite / Get data buttons on wide cards; overridden and dead CSS removed.

## 2026-10-07 (v2)

- Catalog is a folder: `catalog.toml` (notice, allowed tags) plus one `datasets/<slug>.toml` per
  dataset; `--catalog DIR` replaces `--manifest`. Datasets carry 1–5 tags from the allowed list and
  an optional `[citation]`; all of a dataset's files sit in one folder; licenses are SPDX
  identifiers (`PDDL-1.0`, not `ODC-PDDL-1.0`) or `Public domain`. The sample is a 24-dataset
  catalog under `examples/sample/`.
- A non-text tag (e.g. a nested list) is refused with a clear message instead of a crash.
- Citations: APA, BibTeX and RIS generated from `[citation]` (or, without one, the catalog entry).
  The demo datasets cite their original sources, read from each source page on 2026-10-07; GHCN
  now carries its dataset DOI (10.7289/V5D21VHZ).
- Citations prefer the DOI to a URL (APA 7), omit the publisher when it is the author, and use
  the dataset slug as the BibTeX key (unique; author-year keys collided).
- Get-data snippets per dataset (download all, AWS CLI, rclone, Python, R; shell-quoted, run
  against the bucket) and format names for the meta line (`CSV (gzip)`, `TAR (gzip)`).
- The download-all loop uses `curl -g`, so file names with `[ ]` or `{ }` download instead of
  being read as curl globs.
- `catalog.json` (every dataset, file, checksum and citation) is built beside `index.html` and
  published with it; `deploy.sh` refuses to publish without it, before touching the `page`
  branch.
- One owned page script (`scripts/page.js`, no libraries): the gate admits it by sha256 and refuses
  any other inline script, JSON-LD, `eval(` and `new Function`.
- The page script keeps other query parameters (`utm_*`, `gclid`) when it updates the URL,
  survives a malformed `#` fragment, and shows no filter box for an empty catalog.
- v2 page: sticky sidebar (search, tag filter with live counts, dataset list), compact cards with
  Cite / Get data popovers, a collapsed Details section for files, dark mode (light and dark
  tokens checked for contrast), a catalog summary line. `smoke.sh` checks the filters, URL state,
  `#slug` links and Escape focus in a real browser and screenshots both themes.
- Dates no longer break at the hyphen on phones; "GeoJSON" spelled as such; the Filters button
  appears only on narrow screens (it showed, inert, on wide touch screens). Overflow and focus
  checks now open the Get data popover; theme screenshots are full-page from the top.
- Docs: catalog rules summary in the development guide; README points scripts to `catalog.json`.
- `catalog.json` carries the catalog digest and `deploy.sh` refuses one built from another
  catalog (a sample preview written at the repo root could otherwise be published). File names may
  not contain `/`; slugs `q`, `live`, `chips`, `chips-hd` are reserved by the page. The search
  field's border meets 3:1 contrast.

## 2026-10-07

- New repo, ported and trimmed from cds-osn's catalog page: manifest without versions, withdrawals
  or request files; optional `notice` banner and per-dataset `source`; contributor tooling removed.
- File URLs may not contain percent-escapes or backslashes (a browser would resolve them outside
  the bucket). The runbook's upload command excludes hidden files and hidden folders.
- `contact` is optional; a card shows a Contact line only when one is set. Demo datasets list no
  contact (questions go to the source).
- Demo catalog: four public datasets (Palmer penguins, GHCN-Daily Boston Logan, Boston street
  trees, Natural Earth countries) re-hosted unmodified under `bu-cds-public-data/demo/`. Runbook:
  one-time anonymous sha256 check after an upload.
- `CATALOG_DOMAIN= ./publish.sh` publishes without a `CNAME`, for testing on the default
  `bu-cds.github.io/cds-data-pub/` address before the custom domain moves over.
