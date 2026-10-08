"""Ways to get a dataset: format names for the meta line and copyable download snippets.

Every command was run anonymously against the bucket on 2026-10-07 (aws-cli 1.46.1, rclone 1.75).
"""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass

from scripts.manifest import BUCKET_BASE, DataFile, Dataset

ENDPOINT, BUCKET = BUCKET_BASE.rstrip("/").rsplit("/", 1)
NAMES = {"geojson": "GeoJSON"}  # formats whose usual spelling is not all caps
COMPRESSION = {"gz": "gzip", "bz2": "bzip2", "xz": "xz", "zst": "zstd"}
DOCS = {
    "curl": "https://curl.se/docs/manpage.html",
    "aws": "https://docs.aws.amazon.com/cli/latest/reference/s3/sync.html",
    "rclone": "https://rclone.org/s3/",
    "pandas": "https://pandas.pydata.org/docs/user_guide/io.html",
    "urllib": "https://docs.python.org/3/library/urllib.request.html",
    "read.csv": "https://stat.ethz.ch/R-manual/R-devel/library/utils/html/read.table.html",
    "download.file": "https://stat.ethz.ch/R-manual/R-devel/library/utils/html/download.file.html",
    "arrow": "https://arrow.apache.org/docs/r/reference/read_parquet.html",
}


@dataclass(frozen=True)
class Snippet:
    """One Get-data tab."""

    label: str
    hint: str
    code: str
    docs: str


def file_format(name: str) -> str | None:
    """Display format of a file: 'CSV', 'CSV (gzip)', 'TAR (gzip)', 'file'; None for README.md."""
    if name == "README.md":
        return None
    parts = name.lower().split(".")
    if len(parts) == 1:
        return "file"
    if parts[-1] == "tgz":
        return "TAR (gzip)"
    if parts[-1] in COMPRESSION and len(parts) > 2:
        return f"{parts[-2].upper()} ({COMPRESSION[parts[-1]]})"
    return NAMES.get(parts[-1], parts[-1].upper())


def formats(ds: Dataset) -> list[str]:
    """Each file format once, in order of first appearance."""
    seen: list[str] = []
    for f in ds.files:
        fmt = file_format(f.name)
        if fmt and fmt not in seen:
            seen.append(fmt)
    return seen


def main_file(ds: Dataset) -> DataFile:
    """The first file that is not README.md (or README.md if it is the only one)."""
    return next((f for f in ds.files if f.name != "README.md"), ds.files[0])


def _py(f: DataFile) -> tuple[str, str]:
    url, name = json.dumps(f.url), json.dumps(f.name)
    if f.name.endswith(".csv"):
        return f"import pandas as pd\n\ndf = pd.read_csv({url})", DOCS["pandas"]
    fetch = f"import urllib.request\n\nurllib.request.urlretrieve({url}, {name})"
    if f.name.endswith(".parquet"):
        return f"{fetch}\n\nimport pandas as pd\n\ndf = pd.read_parquet({name})", DOCS["pandas"]
    return fetch, DOCS["urllib"]


def _r(f: DataFile) -> tuple[str, str]:
    url, name = json.dumps(f.url), json.dumps(f.name)
    if f.name.endswith(".csv"):
        return f"df <- read.csv({url})", DOCS["read.csv"]
    fetch = f'download.file({url}, {name}, mode = "wb")'
    if f.name.endswith(".parquet"):
        return f"{fetch}\ndf <- arrow::read_parquet({name})", DOCS["arrow"]
    return fetch, DOCS["download.file"]


def get_data(ds: Dataset) -> list[Snippet]:
    """The Get-data tabs, in display order."""
    folder = f"{BUCKET_BASE}{ds.prefix}"
    names = " \\\n         ".join(shlex.quote(f.name) for f in ds.files)
    loop = f'base={shlex.quote(folder)}\nfor f in {names}; do\n  curl -gfO "$base/$f"\ndone'
    s3 = shlex.quote(f"s3://{BUCKET}/{ds.prefix}/")
    rc = shlex.quote(f":s3:{BUCKET}/{ds.prefix}")
    dest = shlex.quote(f"./{ds.slug}")
    f = main_file(ds)
    py, py_docs = _py(f)
    r, r_docs = _r(f)
    verb = "Read" if f.name.endswith((".csv", ".parquet")) else "Download"
    n = len(ds.files)
    return [
        Snippet(  # a shell loop, not a download button: say so (Windows cmd/PowerShell 5.1 fail)
            "Shell (curl)",
            f"All {n} file{'s' * (n != 1)} · a macOS or Linux terminal",
            loop,
            DOCS["curl"],
        ),
        Snippet(
            "AWS CLI",
            "Sync the whole folder; no account needed",
            f"aws s3 sync {s3} {dest}/ \\\n  --no-sign-request --endpoint-url {ENDPOINT}",
            DOCS["aws"],
        ),
        Snippet(
            "rclone",
            "Copy the whole folder; no config needed",
            f"rclone copy {rc} {dest} \\\n  --s3-provider Other --s3-endpoint {ENDPOINT}",
            DOCS["rclone"],
        ),
        Snippet("Python", f"{verb} {f.name}", py, py_docs),
        Snippet("R", f"{verb} {f.name}", r, r_docs),
    ]
