"""Anonymous HEAD check on every file URL in the manifest.

Usage: .venv/bin/python -m scripts.check_links [--manifest PATH]

Each URL must answer 200 with a Content-Length equal to the manifest size. No credentials are
sent: this is what a public visitor sees.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from scripts.manifest import Dataset, ManifestError, load_manifest

REPO = Path(__file__).resolve().parent.parent
Head = Callable[[str], tuple[int, int | None]]


def urllib_head(url: str) -> tuple[int, int | None]:
    """HEAD a URL with no credentials; return (status, Content-Length), status 0 if no response."""
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            length = resp.headers.get("Content-Length")
            return resp.status, int(length) if length and length.isdigit() else None
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except OSError:  # URLError, timeouts, dropped and reset connections, DNS failures
        return 0, None


def check_links(datasets: list[Dataset], head: Head = urllib_head) -> list[str]:
    """Return one problem per failing file; empty means every file is reachable and sized."""
    problems: list[str] = []
    for ds in datasets:
        for f in ds.files:
            status, length = head(f.url)
            label = f"{ds.slug}/{f.name}"
            if status != 200:
                problems.append(f"{label}: HTTP {status or 'no response'} for {f.url}")
            elif length is None:
                problems.append(f"{label}: no Content-Length on HEAD; size unverified ({f.url})")
            elif length != f.size:
                problems.append(f"{label}: size {length} on OSN, {f.size} in manifest")
    return problems


def main(argv: list[str] | None = None) -> int:
    """Check every URL in the manifest. Returns a process exit code."""
    parser = argparse.ArgumentParser(description="HEAD-check every file URL.")
    parser.add_argument("--manifest", type=Path, default=REPO / "datasets.toml")
    args = parser.parse_args(argv)
    try:
        datasets = load_manifest(args.manifest).datasets
    except (ManifestError, OSError) as exc:
        print(f"check_links: {exc}", file=sys.stderr)
        return 1
    problems = check_links(datasets, urllib_head)
    for problem in problems:
        print(f"check_links: {problem}")
    total = sum(len(d.files) for d in datasets)
    print(f"check_links: checked {total} file(s), {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
