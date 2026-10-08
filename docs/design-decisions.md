# Design decisions

Settled choices for this project's data pages. Newest first. A decision is reopened only when the
user asks, or new data or a reader test contradicts it — then add a new entry that supersedes it.

## 2026-10-08 — Fixes from the blind review of the redesign

- **Page / view:** catalog page after the band and the first review fixes; second review report in
  `clean-claude`, `evals/design-review/real/cds-data-pub/2026-10-08-after-report.md` (8 findings).
- **Chosen:** search matches every word in any order and covers formats, file names, columns,
  producer and coverage (#2, #3); "Publish your data with CDS" is the filled button only once
  `catalog.toml` names a `steward` contact, and the Publish section says the contact is coming
  until then (#1 — keeps the band, removes the dead end); white focus ring on the dark header,
  14.4:1 (#4); GHCN description ends 29 September 2026 like its data (#5); "more" re-measured when
  the width changes (#6); band named "Catalog summary" so region names are unique (#8).
- **Not changed:** the list shows about 1.5 cards at 1280×800 under the band (#7, a design opinion);
  the band stays, as chosen above. Reopen if the reader test shows people miss the list.
- **Evidence:** before/after browser probes: "boston trees", "trees boston", "street trees",
  "dbh" and "PRCP" found nothing before, the right dataset after; "csv" found 2 of 3 CSV datasets
  before, 3 after; widening 320→1280 left 4 stale "more" buttons before, 1 correct one after.

## 2026-10-08 — Present CDS with an identity band above the list

- **Page / view:** catalog page (`index.html`), top of the main column
- **Options compared:** A · header links (About, Publish your data, catalog.json in the header) ·
  B · identity band (lede, computed facts, three calls to action). Before/after comparison built
  locally from preview builds (scratch `compare.html`, Before · A · B, phone/tablet/desktop).
- **Chosen:** B — **by:** the data steward (developer)
- **Why:** "B looks best." It states what the catalog is and who runs it before the list, shows
  trust signals (no account, checksums), and gives funders, partners and researchers a next step
  (Publish your data with CDS) — the R1-portal goal. Accepted trade-off: the band costs list
  height in the desktop app shell and much of the first phone screen.
- **Evidence:** a blind first impression from a fresh agent that saw only the screenshots judged B
  the most credible to a funder or partner and A "still mostly a file list" (a model's reading,
  not a reader test). Wording keeps review finding #1 fixed: "curated and hosted by", never "from"
  CDS, because the listed datasets are produced by others.
- **Reopen if:** a reader test shows people miss the list or the search on phones, or the catalog
  grows to where list height matters more than the introduction.

## 2026-10-08 — Fixes from the design review (no options compared)

- **Page / view:** catalog page; review report in the `clean-claude` repo,
  `evals/design-review/real/cds-data-pub/2026-10-08-report.md` (all six findings confirmed).
- **Chosen:** say the catalog is curated and hosted by CDS and name each dataset's producer (#1);
  "Shell (curl)" tab for the shell loop (#2); keep a popover in view when its tab changes (#3);
  retrieval dates on citations without a DOI (#4); rows, columns and coverage per dataset, read
  from the files themselves (#5); title permalinks (#6).
- **Why:** each finding had one correct fix; no presentation choice was involved.
- **Evidence:** #3 measured at 1280×800 on the last card: Copy button 88 px below the list's edge
  before, 12 px inside after. #5 facts: each CSV downloaded from OSN, its sha256 matched the
  manifest, then header and data rows counted.
- **Open:** the data steward's contact for "Publish your data with CDS" (the page is not live).
