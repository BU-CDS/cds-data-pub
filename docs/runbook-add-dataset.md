# Steward runbook: add or take down a dataset

Needs: rclone remote `osn` with the bucket's read-write keys (never in this repo), the project
`.venv`, and a researcher's confirmation that the data is approved for public release.

## Add

1. Put the files in one local folder, plus a `README.md` (what it is, source, license, contact,
   date). At most 50 files; archive more. Review the folder contents exactly: everything in it
   becomes public, and the bucket lists anonymously.
2. Upload: `rclone copy ./<folder> osn:bu-cds-public-data/<slug>/ --exclude '.*' --exclude '.*/**' --progress`
   (demo data goes under `demo/<slug>/`).
3. Sizes and hashes: `stat -f '%z %N' <folder>/*` and `shasum -a 256 <folder>/*`.
4. Add a `[[dataset]]` block to `datasets.toml` (fields: `examples/sample.toml`). `contact` is
   optional and is shown publicly; leave it out unless the researcher wants an address listed. File URL:
   `https://mghp.osn.xsede.org/bu-cds-public-data/<slug>/<name>`.
5. Preview: `.venv/bin/python -m scripts.build_page --out previews/index.html --preview` and look.
6. Commit on `main`, then `./publish.sh`. It refuses if any link is not public or the size is off.
7. Once, for the new files: check that an anonymous download matches the listed hash,
   `curl -fsS <file url> | shasum -a 256`. HEAD checks size, not content.

## Take down

Routine: delete the `[[dataset]]` block, commit, `./publish.sh`, then
`rclone purge osn:bu-cds-public-data/<slug>`.

**Incident (privacy or licensing problem): files first.** The bucket lists anonymously, so a file
removed only from the page is still discoverable.

1. `rclone purge osn:bu-cds-public-data/<slug>`
2. Confirm: `curl -sI <file url> | head -1` shows 403 or 404 for each file.
3. Delete the `[[dataset]]` block, commit, `./publish.sh`.

## Remove the demo

Delete `notice` and the demo blocks, publish, then `rclone purge osn:bu-cds-public-data/demo`.

Last verified: 2026-10-07
