"""Build the catalog page from the catalog folder (catalog.toml + datasets/).

Usage: .venv/bin/python -m scripts.build_page [--catalog DIR] [--out PATH] [--preview]

Branding assets (fonts, BU plate, CDS signature) are read from the sibling clone named by
$PUB_CPU_CLONE (default ../cpu-cds-scc) and embedded; they are never copied into this repo.
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.catalog_json import to_json
from scripts.manifest import ManifestError, catalog_digest, load_catalog
from scripts.render import Assets, render_page

REPO = Path(__file__).resolve().parent.parent
OWN_ASSETS = REPO / "assets"
GA_ID = "G-MTV6EXSR2V"  # GA4 measurement id: the data.cds.bu.edu property (one per page)
GA_ID_RE = re.compile(r"^G-[A-Z0-9]+$")
STAMP_TZ = ZoneInfo("America/New_York")  # the "Updated" stamp is a Boston date
SIBLING_ASSETS = {
    "plate": ("bu_plate_white.png", "image/png"),
    "signature": ("faculty_compt_data_sci_signature_toptier_rgb.png", "image/png"),
    "font_semibold": ("WhitneySSmAdvancedSemibold.woff2", "font/woff2"),
    "font_book": ("WhitneySSmAdvancedBook.woff2", "font/woff2"),
}


class BuildError(RuntimeError):
    """A build input is missing or invalid."""


def _data_uri(path: Path, mime: str) -> str:
    if not path.is_file():
        raise BuildError(f"missing asset: {path}")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def load_assets(sibling_assets: Path, own_assets: Path) -> Assets:
    """Read every branding asset as a data URI; fail naming the first missing file."""
    uris = {
        key: _data_uri(sibling_assets / name, mime) for key, (name, mime) in SIBLING_ASSETS.items()
    }
    return Assets(favicon=_data_uri(own_assets / "favicon.ico", "image/x-icon"), **uris)


def _default_sibling_assets() -> Path:
    return Path(os.environ.get("PUB_CPU_CLONE", REPO.parent / "cpu-cds-scc")) / "assets"


def main(argv: list[str] | None = None) -> int:
    """Build the page. Returns a process exit code."""
    parser = argparse.ArgumentParser(description="Build the catalog page.")
    parser.add_argument(
        "--catalog", type=Path, default=REPO, help="folder holding catalog.toml and datasets/"
    )
    parser.add_argument("--out", type=Path, default=REPO / "index.html")
    parser.add_argument("--preview", action="store_true", help="local preview: no GA tag, marked")
    parser.add_argument("--assets", type=Path, default=None, help="sibling clone's assets/ dir")
    parser.add_argument("--updated", type=date.fromisoformat, default=None, help=argparse.SUPPRESS)
    # Design comparison only (data-story, 2026-10-08): removed once one identity is chosen.
    parser.add_argument(
        "--identity", choices=("links", "band"), default="links", help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)

    ga_id = None if args.preview else (GA_ID or None)
    if ga_id is not None and not GA_ID_RE.match(ga_id):
        print(f"build_page: GA_ID {ga_id!r} is not a GA4 measurement id (G-...)", file=sys.stderr)
        return 1
    try:
        catalog = load_catalog(args.catalog)
        manifest_sha = catalog_digest(args.catalog)
        assets = load_assets(args.assets or _default_sibling_assets(), OWN_ASSETS)
    except (ManifestError, BuildError, OSError) as exc:
        print(f"build_page: {exc}", file=sys.stderr)
        return 1
    stamp = args.updated or datetime.now(STAMP_TZ).date()
    html = render_page(
        catalog,
        assets,
        stamp,
        ga_id,
        preview=args.preview,
        manifest_sha=manifest_sha,
        identity=args.identity,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    (args.out.parent / "catalog.json").write_text(
        to_json(catalog, stamp, manifest_sha), encoding="utf-8"
    )
    kind = "preview" if args.preview else "deploy build"
    print(f"build_page: wrote {args.out} ({len(catalog.datasets)} dataset(s), {kind})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
