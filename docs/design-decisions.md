# Design decisions

Settled choices for this project's data pages. Newest first. A decision is reopened only when the
user asks, or new data or a reader test contradicts it — then add a new entry that supersedes it.

## 2026-10-09 — Headline, About and Publish pages, Copy link

- **Headline:** "Open datasets, curated and hosted by BU Computing & Data Sciences. Free to
  download and reuse." Options: the owner's "curated, created, hosted … free for research and
  teaching", the branch's current line, and this one. **By:** the owner, after Codex and Gemini
  each picked it blind: "created" is not true of any dataset today, and "for research and
  teaching" is narrower than the licenses (CC0, PDDL, public domain allow any reuse). **Reopen
  when** the first CDS-made dataset is listed ("created or curated").
- **About and Publish as pages** (owner): instead of sections under the list, so they can grow.
  Publish: only CDS researchers can publish (owner). Content answers the simulated readers'
  questions (below). The steward contact stays empty, flagged by the Publish page and a
  `publish.sh` warning.
- **Copy link** (owner): two of three simulated readers looked for a Share button first.
- **Gemini** ran through `agy --dangerously-skip-permissions` (the `agy-all` alias's flag) in an
  empty folder; that worked where `/audit`'s Gemini runs did not. Its researcher persona added:
  "why re-host NOAA and the penguins?" (About now says it is a demo of the service) and that the
  "Publish your data with CDS" button reads as open to all (Publish now says CDS-only first).

## 2026-10-09 — Simulated readers (models, not people)

- **What ran:** `docs/reader-test.md` played by Codex (via `/audit`) as three personas: a first-year
  MS student on a phone, an outside environmental scientist, a foundation program officer. Each
  saw the first-screen text at their width and the page without styles or scripts. Gemini could
  not play a persona through `/audit` (research mode is blocked by a headless permission; review
  mode audited the brief instead of answering it).
- **All three:** "Publish your data with CDS" ends without a contact and does not say who may
  publish ("CDS researchers" only?). Two of three: no explanation of checksums, PDDL-1.0, DOI,
  MiB or catalog.json; "Demo" leaves it unclear whether the data is usable; looked for a Share
  button before the title link. The researcher: the page does not say the copy is unmodified,
  what "updated", "added" and the source version each mean, or how long the copy will last.
- **Artifact, not a finding:** all three missed the Copy buttons, which the page script reveals.
- **Use:** input for the About and Publish pages and a Copy-link button. Not evidence about real
  readers (data.md §5): comprehension stays *not tested* until the reader test runs.

## 2026-10-09 — Details opens one panel with labelled sections

- **Page / view:** catalog page, a card's Details expander (tested on GHCN-Daily, 110 columns).
- **Options compared:** reference (stacked lines, comma-separated column paragraph) · A · one
  panel, labelled sections (coverage and source as label/value pairs, columns as a capped grid,
  files table) · B · the same panel with tabs (Overview · Columns · Files) · C · coverage and
  source on the card, Columns and Files as two toggles. Rendered side by side from the branch's
  real card (scratch `compare.html`, phone/tablet/desktop).
- **Chosen:** A — **by:** the data steward (developer), "agree that A is the best".
- **Why:** answers coverage, source, columns and files in one place in the order a reader decides
  fit; the column list stops swamping the card.
- **Evidence:** model readings only, not a reader test: the author's prediction, a blind Claude
  first impression from screenshots alone, and Codex via `/audit` all ranked A first; Codex ranked
  B last (tabs hide facts readers compare, citing GOV.UK's tabs guidance). Gemini failed in
  research mode (headless permission) and was rerun in review mode. The blind Claude flagged
  checksums wrapping badly on phones and a cramped box-in-box; Codex suggested sentence-case
  headings, body-size text, one level of inset, the first 20 names with "Show all" and a column
  filter above 20, and a coverage line on the card.
- **Reopen if:** the reader test shows people miss coverage before opening Details, or cannot find
  a named column in long lists.

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
