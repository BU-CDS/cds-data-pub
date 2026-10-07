"""Gate over a built catalog page.

Usage: .venv/bin/python -m scripts.check_page PAGE [--preview | --require-ga G-XXXX]
       [--catalog DIR]

Refuses: any sourced script but the GA loader, inline scripts beyond the GA bootstrap, network or
storage APIs, http:// links, a missing "Updated" stamp, a preview build presented for publish,
and (with --catalog) a page built from another catalog.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scripts.manifest import catalog_digest
from scripts.render import PREVIEW_MARK

SCRIPT_TAG_RE = re.compile(r"<script\b([^>]*)>", re.IGNORECASE)
SRC_RE = re.compile(r"""\bsrc\s*=\s*["']?([^"'\s>]+)""", re.IGNORECASE)
LOADER_RE = re.compile(r"^https://www\.googletagmanager\.com/gtag/js\?id=(G-[A-Z0-9]+)$")
CONFIG_RE = re.compile(r'gtag\(\s*"config"\s*,\s*"(G-[A-Z0-9]+)"\s*\)')
HTTP_ATTR_RE = re.compile(r"""\b(?:href|src|action)\s*=\s*["']?http://""", re.IGNORECASE)
STAMP_RE = re.compile(r"Updated \d{4}-\d{2}-\d{2}")
FORBIDDEN = (
    "fetch(",
    "XMLHttpRequest",
    "localStorage",
    "sessionStorage",
    "document.cookie",
    "indexedDB",
)


def check_html(
    html: str,
    *,
    preview: bool = False,
    require_ga: str | None = None,
    manifest_sha: str | None = None,
) -> list[str]:
    """Return every problem found; an empty list means the page passes.

    Args:
        html: The built page.
        preview: The page is a local preview (must carry the preview mark and no GA).
        require_ga: Measurement id the page must carry exactly once (publish builds).
        manifest_sha: digest of the catalog the page must have been built from (deploy).
    """
    problems: list[str] = []
    loaders: list[str] = []
    inline = 0
    for attrs in SCRIPT_TAG_RE.findall(html):
        src = SRC_RE.search(attrs)
        if src is None:
            inline += 1
            continue
        loader = LOADER_RE.match(src.group(1))
        if loader is None:
            problems.append(f"sourced script not allowed: {src.group(1)}")
        else:
            loaders.append(loader.group(1))
    configs = CONFIG_RE.findall(html)

    if inline > (1 if loaders else 0):
        problems.append(f"inline script beyond the GA bootstrap ({inline} inline script(s))")
    if len(loaders) > 1 or len(configs) > 1:
        problems.append(
            f"more than one GA tag: {len(loaders)} loader(s), {len(configs)} config call(s)"
        )
    if loaders and configs and set(loaders) != set(configs):
        problems.append(f"GA loader id {loaders} does not match config id {configs}")
    if require_ga is not None and (loaders != [require_ga] or configs != [require_ga]):
        problems.append(f"page must carry exactly one GA tag with id {require_ga}")

    marked = PREVIEW_MARK in html
    if preview and not marked:
        problems.append("--preview given but the page has no preview mark")
    if preview and (loaders or configs or "googletagmanager" in html):
        problems.append("preview build carries a Google Analytics tag")
    if not preview and marked:
        problems.append("preview build cannot be published (rebuild without --preview)")

    for needle in FORBIDDEN:
        if needle in html:
            problems.append(f"forbidden API in page: {needle}")
    if HTTP_ATTR_RE.search(html):
        problems.append("insecure http:// link or source")
    if (
        manifest_sha is not None
        and f'<meta name="cds-manifest" content="{manifest_sha}">' not in html
    ):
        problems.append(
            "page was not built from this catalog (rebuild from catalog.toml + datasets/)"
        )
    if not STAMP_RE.search(html):
        problems.append('missing "Updated YYYY-MM-DD" stamp')
    return problems


def main(argv: list[str] | None = None) -> int:
    """Check a page file. Returns a process exit code."""
    parser = argparse.ArgumentParser(description="Gate over a built catalog page.")
    parser.add_argument("page", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preview", action="store_true")
    mode.add_argument("--require-ga", metavar="ID")
    parser.add_argument("--catalog", type=Path, help="refuse a page built from another catalog")
    args = parser.parse_args(argv)
    sha = catalog_digest(args.catalog) if args.catalog else None
    problems = check_html(
        args.page.read_text(encoding="utf-8"),
        preview=args.preview,
        require_ga=args.require_ga,
        manifest_sha=sha,
    )
    for problem in problems:
        print(f"check_page: {problem}")
    if problems:
        return 1
    print(f"check_page: OK {args.page}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
