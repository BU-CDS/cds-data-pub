"""Shared test fixtures: valid raw dataset entries and on-disk catalogs to mutate per test."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from scripts.manifest import BUCKET_BASE, parse_dataset

SHA = "a" * 64
VOCAB = ("example", "other")


def url_for(name: str = "data.csv", slug: str = "example") -> str:
    """Public URL in the bucket layout for a test file."""
    return f"{BUCKET_BASE}{slug}/{name}"


def file_dict(**overrides: object) -> dict:
    """Return a valid [[file]] table, with overrides applied."""
    entry = {"name": "data.csv", "url": url_for(), "size": 2048, "sha256": SHA}
    entry.update(overrides)
    return entry


def dataset_dict(**overrides: object) -> dict:
    """Return a valid datasets/<slug>.toml table, with overrides applied."""
    entry = {
        "title": "Example dataset",
        "description": "First paragraph.\n\nSecond paragraph.",
        "license": "CC-BY-4.0",
        "contact": "someone@example.org",
        "added": date(2026, 10, 6),
        "tags": ["example"],
        "file": [file_dict()],
    }
    entry.update(overrides)
    return entry


def parse(entry: dict | None = None, slug: str = "example", vocab: tuple[str, ...] = VOCAB):
    """Parse one dataset table as datasets/<slug>.toml."""
    return parse_dataset(slug, entry or dataset_dict(), vocab, f"datasets/{slug}.toml")


def dataset_toml(slug: str = "example", added: str = "2026-10-06") -> str:
    """A valid datasets/<slug>.toml file body."""
    return (
        f'title = "Dataset {slug}"\ndescription = "About {slug}."\nlicense = "CC0-1.0"\n'
        f'added = {added}\ntags = ["example"]\n\n[[file]]\nname = "data.csv"\n'
        f'url = "{url_for(slug=slug)}"\nsize = 2048\nsha256 = "{SHA}"\n'
    )


def write_catalog(
    root: Path, datasets: dict[str, str], catalog: str = 'tags = ["example", "other"]\n'
) -> Path:
    """Write catalog.toml and datasets/<slug>.toml files under root; return root."""
    (root / "datasets").mkdir(parents=True, exist_ok=True)
    (root / "catalog.toml").write_text(catalog, encoding="utf-8")
    for slug, text in datasets.items():
        (root / "datasets" / f"{slug}.toml").write_text(text, encoding="utf-8")
    return root
