"""catalog.json: the catalog in machine-readable form, published beside index.html."""

from __future__ import annotations

import json
from datetime import date

from scripts import cite, snippets
from scripts.manifest import Catalog, Dataset, license_url


def _dataset(ds: Dataset) -> dict:
    return {
        "slug": ds.slug,
        "url": f"{cite.PAGE_URL}#{ds.slug}",
        "title": ds.title,
        "description": ds.description,
        "license": ds.license,
        "license_url": license_url(ds.license),
        "tags": list(ds.tags),
        "added": ds.added.isoformat(),
        "doi": ds.doi,
        "source": ds.source,
        "contact": ds.contact,
        "formats": snippets.formats(ds),
        "total_size": ds.total_size,
        "coverage": ds.coverage,
        "citation": {"apa": cite.apa(ds), "bibtex": cite.bibtex(ds), "ris": cite.ris(ds)},
        "files": [
            {
                "name": f.name,
                "url": f.url,
                "size": f.size,
                "sha256": f.sha256,
                "rows": f.rows,
                "columns": list(f.columns),
            }
            for f in ds.files
        ],
    }


def to_json(catalog: Catalog, updated: date, digest: str = "") -> str:
    """The catalog as indented JSON (UTF-8, stable key order), ending in a newline.

    ``digest`` is the catalog digest, stamped so deploy.sh can refuse a catalog.json built from
    any other catalog (the same check index.html gets).
    """
    data = {
        "catalog_digest": digest,
        "name": cite.PUBLISHER,
        "url": cite.PAGE_URL,
        "updated": updated.isoformat(),
        "notice": catalog.notice,
        "datasets": [_dataset(ds) for ds in catalog.datasets],
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
