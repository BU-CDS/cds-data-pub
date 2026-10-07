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
4. Create `datasets/<slug>.toml`: the file name is the slug (fields: any file in
   `examples/sample/datasets/`). `tags` lists 1–5 tags from `catalog.toml`; add a new tag there
   first. `license` is an SPDX identifier (`CC-BY-4.0`, `PDDL-1.0`) or `Public domain`. `contact` is
   optional and is shown publicly; leave it out unless the researcher wants an address listed.
   File URL: `https://mghp.osn.xsede.org/bu-cds-public-data/<slug>/<name>`; all of a dataset's
   files sit in that one folder.
5. Preview: `.venv/bin/python -m scripts.build_page --out previews/index.html --preview` and look.
6. Commit on `main`, then `./publish.sh`. It refuses if any link is not public or the size is off.
7. Once, for the new files: check that an anonymous download matches the listed hash,
   `curl -fsS <file url> | shasum -a 256`. HEAD checks size, not content.

## Take down

Routine: delete `datasets/<slug>.toml`, commit, `./publish.sh`, then
`rclone purge osn:bu-cds-public-data/<slug>`.

**Incident (privacy or licensing problem): files first.** The bucket lists anonymously, so a file
removed only from the page is still discoverable.

1. `rclone purge osn:bu-cds-public-data/<slug>`
2. Confirm: `curl -sI <file url> | head -1` shows 403 or 404 for each file.
3. Delete `datasets/<slug>.toml`, commit, `./publish.sh`.

## Remove the demo

Delete `notice` from `catalog.toml` and the demo files in `datasets/`, publish, then
`rclone purge osn:bu-cds-public-data/demo`.

Last verified: 2026-10-07
