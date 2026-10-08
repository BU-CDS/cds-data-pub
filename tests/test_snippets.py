"""Tests for scripts.snippets: format names, the shared folder, and safe download commands."""

from __future__ import annotations

import unittest

from scripts import snippets
from tests.helpers import dataset_dict, file_dict, parse, url_for


def ds(*names: str):
    files = [file_dict(name=n, url=url_for(n)) for n in names]
    return parse(dataset_dict(file=files))


class Formats(unittest.TestCase):
    def test_names(self) -> None:
        cases = {
            "a.csv": "CSV",
            "a.csv.gz": "CSV (gzip)",
            "a.jsonl.zst": "JSONL (zstd)",
            "a.tar.gz": "TAR (gzip)",
            "a.tgz": "TAR (gzip)",
            "a.gz": "GZ",
            "Makefile": "file",
            "README.md": None,
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(snippets.file_format(name), expected)

    def test_unique_in_first_seen_order(self) -> None:
        d = ds("b.geojson", "a.csv", "README.md", "c.csv")
        self.assertEqual(snippets.formats(d), ["GeoJSON", "CSV"])

    def test_main_file_skips_readme(self) -> None:
        self.assertEqual(snippets.main_file(ds("README.md", "a.csv")).name, "a.csv")
        self.assertEqual(snippets.main_file(ds("README.md")).name, "README.md")


class GetData(unittest.TestCase):
    def tabs(self, d) -> dict[str, snippets.Snippet]:
        return {s.label: s for s in snippets.get_data(d)}

    def test_labels_and_docs(self) -> None:
        tabs = snippets.get_data(ds("a.csv"))
        self.assertEqual(
            [s.label for s in tabs], ["Shell (curl)", "AWS CLI", "rclone", "Python", "R"]
        )

    def test_bulk_commands_use_the_folder(self) -> None:
        tabs = self.tabs(ds("a.csv", "b.csv"))
        self.assertEqual(
            tabs["AWS CLI"].code,
            "aws s3 sync s3://bu-cds-public-data/example/ ./example/ \\\n"
            "  --no-sign-request --endpoint-url https://mghp.osn.xsede.org",
        )
        self.assertEqual(
            tabs["rclone"].code,
            "rclone copy :s3:bu-cds-public-data/example ./example \\\n"
            "  --s3-provider Other --s3-endpoint https://mghp.osn.xsede.org",
        )
        self.assertIn('curl -gfO "$base/$f"', tabs["Shell (curl)"].code)  # -g: [ ] { } are literal
        self.assertIn("All 2 files", tabs["Shell (curl)"].hint)
        self.assertIn("macOS or Linux terminal", tabs["Shell (curl)"].hint)  # not a download button

    def test_python_and_r_by_format(self) -> None:
        csv = self.tabs(ds("a.csv"))
        self.assertIn("pd.read_csv(", csv["Python"].code)
        self.assertIn("read.csv(", csv["R"].code)
        pq = self.tabs(ds("a.parquet"))
        self.assertIn('pd.read_parquet("a.parquet")', pq["Python"].code)
        self.assertIn('arrow::read_parquet("a.parquet")', pq["R"].code)
        other = self.tabs(ds("a.zip"))
        self.assertIn("urllib.request.urlretrieve(", other["Python"].code)
        self.assertIn('mode = "wb"', other["R"].code)

    def test_shell_metacharacters_quoted(self) -> None:
        tabs = self.tabs(ds("a&b.csv", "$x.csv"))
        loop = tabs["Shell (curl)"].code
        self.assertIn("'a&b.csv'", loop)
        self.assertIn("'$x.csv'", loop)


if __name__ == "__main__":
    unittest.main()
