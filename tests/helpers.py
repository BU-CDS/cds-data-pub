"""Shared test fixtures: valid raw manifest entries to mutate per test."""

from __future__ import annotations

from datetime import date

from scripts.manifest import BUCKET_BASE

SHA = "a" * 64


def url_for(name: str = "data.csv", slug: str = "example") -> str:
    """Public URL in the bucket layout for a test file."""
    return f"{BUCKET_BASE}{slug}/{name}"


def file_dict(**overrides: object) -> dict:
    """Return a valid [[dataset.file]] table, with overrides applied."""
    entry = {"name": "data.csv", "url": url_for(), "size": 2048, "sha256": SHA}
    entry.update(overrides)
    return entry


def dataset_dict(**overrides: object) -> dict:
    """Return a valid [[dataset]] table, with overrides applied."""
    entry = {
        "slug": "example",
        "title": "Example dataset",
        "description": "First paragraph.\n\nSecond paragraph.",
        "license": "CC-BY-4.0",
        "contact": "someone@example.org",
        "added": date(2026, 10, 6),
        "file": [file_dict()],
    }
    entry.update(overrides)
    return entry
