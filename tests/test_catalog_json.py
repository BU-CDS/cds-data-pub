"""Tests for scripts.catalog_json: the machine-readable catalog mirrors the page's data."""

from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from scripts.catalog_json import to_json
from scripts.manifest import load_catalog

DAY = date(2026, 10, 7)


class ToJson(unittest.TestCase):
    def test_sample_round_trip(self) -> None:
        cat = load_catalog(Path("examples/sample"))
        data = json.loads(to_json(cat, DAY))
        self.assertEqual(data["updated"], "2026-10-07")
        self.assertEqual(len(data["datasets"]), len(cat.datasets))
        first, ds = data["datasets"][0], cat.datasets[0]
        self.assertEqual(first["slug"], ds.slug)
        self.assertEqual(first["total_size"], ds.total_size)
        self.assertEqual([f["sha256"] for f in first["files"]], [f.sha256 for f in ds.files])
        self.assertIn("bibtex", first["citation"])
        self.assertTrue(to_json(cat, DAY).endswith("}\n"))

    def test_shape_fields_published(self) -> None:
        cat = load_catalog(Path("."))  # the real catalog carries rows, columns and coverage
        data = {d["slug"]: d for d in json.loads(to_json(cat, DAY))["datasets"]}
        pen = data["palmer-penguins"]
        self.assertTrue(pen["coverage"])
        csv = next(f for f in pen["files"] if f["name"] == "penguins.csv")
        self.assertEqual((csv["rows"], len(csv["columns"])), (344, 8))
        readme = next(f for f in pen["files"] if f["name"] == "README.md")
        self.assertEqual((readme["rows"], readme["columns"]), (None, []))

    def test_digest_stamped(self) -> None:
        cat = load_catalog(Path("examples/sample"))
        self.assertEqual(json.loads(to_json(cat, DAY, digest="ab"))["catalog_digest"], "ab")


if __name__ == "__main__":
    unittest.main()
