# Changelog

## Unreleased (branch design/2026-10-08-data-story)

From the 2026-10-08 design review (all six findings confirmed by the steward):
- The intro no longer says the datasets come "from research at" CDS: it says CDS curates and
  hosts them, and each card names who produced the data ("from …", taken from its citation).
- The "Download all" tab is "Shell (curl)", hinted "a macOS or Linux terminal": it is a shell
  loop, not a download.
- Switching a Get data / Cite tab keeps the popover in view (it could fall below the list's edge).
- Citations without a DOI carry a retrieval date (the date the dataset was added): APA
  "Retrieved …, from …", BibTeX `urldate`, RIS `Y2`.
- Each dataset title links to its `#slug`; the targeted card is outlined.
- The header's CDS name links to the CDS site; an "About this catalog" and a "Publish your data
  with CDS" section close the list (text from the README).
- An identity band opens the page: what the catalog is ("curated and hosted by", never "from",
  CDS), computed facts (datasets, total size, no account, checksums, updated) and three calls to
  action (Publish your data with CDS, How it works, Use from code: catalog.json). It replaces the
  summary line. Chosen over header links after a rendered comparison
  (`docs/design-decisions.md`).
- Readers can judge fit before downloading (review #5): optional `coverage` per dataset and
  `rows` / `columns` per table file in the manifest, validated; the card shows "rows × columns",
  Details shows coverage and the column names; `catalog.json` carries all three. The four demo
  datasets carry values read from the files themselves (sha256 checked against the manifest).
- `docs/reader-test.md`: a 15-minute test with 3–5 real readers.
- From the blind review of the redesign: search matches every word in any order and also covers
  formats, file names, columns, producer and coverage; optional `steward` in `catalog.toml` (an
  email) — until it is set, Publish is an outline button and its section says the contact is
  coming, so the page has no dead end; white focus ring on the header (14.4:1, now in the
  contrast checks); "more" re-measured on width changes; the band is the "Catalog summary"
  region; GHCN's description ends 29 September 2026, like its data.
- Details opens one panel with labelled sections (chosen 2026-10-09 from rendered options):
  Coverage, Source and Contact as label/value pairs, then "Column names · N in file", then
  "Files · N, with sha256 checksums". One text size, sentence-case headings, one level of inset.
  Column names flow down the columns in file order; past 20 names the page shows the first 20,
  "Show all N column names" and a "Filter column names" box that searches every name (without
  the script every name shows). A checksum's Copy button sits on its own line. The sample's
  tide-gauge entry carries 34 synthetic columns to exercise the long list.
- Hairlines separate the Details sections: between Coverage, Source and Contact, and above
  Column names and Files (owner).
- Headline: "Open datasets, curated and hosted by BU Computing & Data Sciences. Free to download
  and reuse." (owner, with Codex and Gemini agreeing blind: CDS made none of today's datasets, and
  their licenses allow any reuse).
- About and Publish are their own pages, `about.html` and `publish.html`, built and published
  with the catalog; the band's buttons link to them. About explains sources (unmodified copies on
  a snapshot date), permanence (not an archive), demo status, dates, and the terms the cards use
  (checksum, license, DOI, MiB, catalog.json). Publish opens with "Only CDS researchers can publish
  here", then what qualifies, what you get and what the steward asks for. `deploy.sh` refuses a
  missing or failing page; `publish.sh` warns while no steward contact is set.
- Each card has a Copy link button: it copies the dataset's own address, or puts it in the
  address bar when the clipboard is unavailable.
- GHCN's description says each element has measurement, quality and source flags (it said
  "quality flags"; checked against NOAA's documentation and the file).
- Fixes from the blind design review of 2026-10-09: a dataset without a `[citation]` is shown as
  "from BU Computing & Data Sciences" (it is cited as CDS's own), so every card names a producer;
  column names fill row by row, so "Show all" leaves the first 20 where they were; landscape
  phones (height ≤ 500px) no longer pin the filter panel; Clear filters in the empty state moves
  focus to the search box; the heading's accessible name keeps a space after "Boston University";
  About's glossary is "Terms used in the catalog".

## 2026-10-07 (v2.1)

- The DOI of re-hosted data (GHCN, penguins) moves into `[citation].doi`: it appears in Cite
  (link, BibTeX, RIS) but not on the card, which shows a DOI only for datasets we publish.
  A citation's DOI always belongs to the work it cites (our own DOI never lands on the original's
  reference). In `catalog.json`, `doi` is likewise our own; the original's DOI is in its
  `citation` strings.
- Layout: on phones the search row stays visible; body text 1rem with two smaller steps; from
  1300px cards are two columns (title, summary line, description left; buttons and badges
  right); page width up to 1920px; printing drops the sidebar.
- Badges no longer touch the Cite / Get data buttons on wide cards; overridden and dead CSS removed.
- Get data is the primary button and opens on a Files tab with one plain download link per file;
  the command-line tabs follow.
- A test ties the tab CSS to the number of Get data tabs, so a new tab cannot silently never show.
- Accessibility: a Cite / Get data popover closes when focus tabs out of it (it no longer covers
  the next card), and Escape only moves focus back when it was inside; descriptions clamp by line
  with an ellipsis (first paragraph only); chips, Copy, more and Details name their dataset; the
  header separator is silent to screen readers.
- Docs: the GA cookie behaviour (same as cluster.cds.bu.edu) is written down.
- Review fixes: on phones an anchor jump clears the sticky search bar even with a filter on, and
  tapping a tag badge shows the top of the results; drag-selecting a command no longer closes its
  popover; chips read "boston 9" with
  a hidden "datasets" (no aria-label, axe clean); "More tags" keeps focus on the first new chip;
  the page heading keeps its word break for screen readers.
- The intro paragraph spans the full width of the dataset list; the "provided as is" terms
  paragraph is removed.
- Light only, like cluster.cds.bu.edu: dark mode, its colour tokens and the dark footer logo are
  removed.
- The demo notice is a small "Demo" tag in the header instead of a yellow box; `notice` is a
  short label (at most 24 characters).
- App shell from 1100px: the page no longer scrolls; only the framed dataset list does (header,
  intro and footer stay put). The list keeps its scroll position across a reload, anchor links
  and tag taps scroll inside it, and an opened Cite / Get data popover is scrolled fully into
  view. Clicking text in a popover no longer closes it (this crashed Chromium's tab). Phones keep
  normal page scrolling.
- Wide-screen sidebar: the tag filter (search, tags, count) sits in a framed box matching the
  dataset list's frame (tags white on it), and scrolls on its own in very short windows. The
  sidebar's "Datasets" jump list is removed: it only repeated the card titles.
- Review fixes: the app shell needs a window at least 38em tall (scales with the reader's text
  size), so short windows and large text fall back to normal page scrolling instead of clipping
  the list; the sidebar scrolls on its own with a long tag list (it grew past the window, and the
  chips' hidden screen-reader text stretched the page); filtering or searching from far down the
  list shows the first match; Shift+Tab out of the first card's popover closes it; the list is a
  named region and a tab stop only where it scrolls.
- Matched to cluster.cds.bu.edu (measured side by side): the title bar keeps its 56px height on
  wide screens (it was slimmed to 48px) and the footer links are 0.75rem.
- Two-column cards: a hairline and more space separate the Cite / Get data buttons from the
  license and tag badges (chosen from five rendered options).
- Slugs starting `t-`, `ct-` or `gd-` are refused: the page derives element ids from slugs with
  those prefixes, so `t-foo` would clash with dataset `foo`.
- Docs: the development guide describes the app-shell layout (the sticky-header note was stale)
  and why the custom domain is set with `CATALOG_DOMAIN`, not in the Pages settings.
- Copy and more get their dataset name from the script that shows them.

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
