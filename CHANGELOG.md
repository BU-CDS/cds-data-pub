# Changelog

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
