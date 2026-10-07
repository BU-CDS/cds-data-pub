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


if __name__ == "__main__":
    unittest.main()
