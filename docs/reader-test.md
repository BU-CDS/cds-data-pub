# Reader test: data.cds.bu.edu catalog — after the 2026-10-08 redesign

**Who:** 3–5 people from the real audience, not the team that built it: at least one student,
one researcher from outside CDS, and one person who decides on funding or partnerships. Five
readers expose most problems; they do not measure how a whole audience reads the page.
**Build:** branch `design/2026-10-08-data-story` (preview build), or the live page once published.
**Time:** about 15 minutes each, on their own laptop or phone. Record answers word for word.

## 1. Cold read of the complete page

Show the first screen **as published** (header, band, intro and the first cards) for about 10
seconds, then hide it.
- "In one sentence, what is this page for?"
- "Who made these datasets?"
- "What would you do next?"

Intended takeaway (do not show): anyone can download these datasets free, with no account: find
one, check it fits, download it; and the page reads as a portal that competes with the best R1
university data portals. Who made them: other producers (City of Boston, NOAA, Natural Earth,
the penguins authors); CDS curates and hosts them.

*Optional, recorded separately:* show the band alone and ask the first question again. This
tests whether the band carries the message on its own; it is not a measure of the page.

## 2. Tasks

| # | Task (read aloud) | Success looks like | Observed (time, path, errors) |
|---|---|---|---|
| 1 | "Find a dataset of daily weather and tell me whether it records snowfall." | Finds GHCN-Daily; opens Details → Columns and sees `SNOW` (or reads it in the description) without downloading | |
| 2 | "How big is the penguins table, in rows and columns?" | 344 rows × 8 columns, read from the card | |
| 3 | "Download the tree inventory as CSV." (stop before the download starts) | Get data → Files → `bprd_trees.csv` | |
| 4 | "Copy a citation for the weather data into a paper." | Cite → APA (or BibTeX) → Copy | |
| 5 | "Your lab has a dataset to share. What would you do?" | Finds "Publish your data with CDS" and says they would contact the data steward | |
| 6 | "Send a colleague a link to the penguins dataset only." | Uses the title link (`#palmer-penguins`) | |

## 3. After the tasks (full page in view)

- "What is the main message of this page, and is there any 'but' or limit to it?" (record both:
  message and qualification — e.g. "not an archive", "public data only", "it's a demo")
- "Was anything confusing or surprising?"
- "Compared with other university data portals you have used, how does this one look, and why?"
- "Who do you think runs this, and how much would you trust the files?"

## Results (fill in, then add a line to `docs/design-decisions.md`)

| Reader | Cold read (full page) | Who made the data? | Matches intent? | Message + qualification after tasks | Tasks passed (of 6) | Notes |
|---|---|---|---|---|---|---|
