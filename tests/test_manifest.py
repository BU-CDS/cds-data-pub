"""Tests for scripts.manifest: every rule refuses with the dataset and field named."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, date, datetime
from pathlib import Path

from scripts.manifest import MAX_FILES, ManifestError, load_manifest, parse_manifest
from tests.helpers import SHA, dataset_dict, file_dict, url_for


def parse(*datasets: dict, **top: object):
    return parse_manifest({**top, "dataset": list(datasets)})


class Valid(unittest.TestCase):
    def test_minimal(self) -> None:
        cat = parse(dataset_dict())
        self.assertIsNone(cat.notice)
        (ds,) = cat.datasets
        self.assertEqual(ds.slug, "example")
        self.assertEqual(ds.total_size, 2048)
        self.assertIsNone(ds.doi)
        self.assertIsNone(ds.source)

    def test_empty_manifest(self) -> None:
        self.assertEqual(parse_manifest({}).datasets, [])

    def test_notice_doi_source(self) -> None:
        cat = parse(
            dataset_dict(doi="10.5281/zenodo.1", source="https://example.org/x"),
            notice="Demo data.",
        )
        self.assertEqual(cat.notice, "Demo data.")
        self.assertEqual(cat.datasets[0].doi, "10.5281/zenodo.1")
        self.assertEqual(cat.datasets[0].source, "https://example.org/x")

    def test_nested_path_under_bucket(self) -> None:
        url = f"{url_for('x.csv', slug='demo/example')}"
        parse(dataset_dict(file=[file_dict(name="x.csv", url=url)]))

    def test_sha_lowercased(self) -> None:
        cat = parse(dataset_dict(file=[file_dict(sha256="A" * 64)]))
        self.assertEqual(cat.datasets[0].files[0].sha256, "a" * 64)

    def test_newest_first_then_slug(self) -> None:
        a = dataset_dict(slug="a", added=date(2026, 1, 1), file=[file_dict(url=url_for(slug="a"))])
        b = dataset_dict(slug="b", added=date(2026, 5, 1), file=[file_dict(url=url_for(slug="b"))])
        c = dataset_dict(slug="c", added=date(2026, 5, 1), file=[file_dict(url=url_for(slug="c"))])
        self.assertEqual([d.slug for d in parse(a, c, b).datasets], ["b", "c", "a"])

    def test_load_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "m.toml"
            p.write_text('notice = "hi"\n', encoding="utf-8")
            self.assertEqual(load_manifest(p).notice, "hi")


class Refused(unittest.TestCase):
    def assertRefused(self, fragment: str, *datasets: dict, **top: object) -> None:
        with self.assertRaises(ManifestError) as ctx:
            parse(*datasets, **top)
        self.assertIn(fragment, str(ctx.exception))

    def test_unknown_top_level_key(self) -> None:
        self.assertRefused("unknown top-level", dataset_dict(), banner="x")

    def test_empty_notice(self) -> None:
        self.assertRefused("notice", dataset_dict(), notice="  ")

    def test_unknown_dataset_key(self) -> None:
        self.assertRefused("unknown field(s): version", dataset_dict(version=1))

    def test_each_required_field(self) -> None:
        for key in ("slug", "title", "description", "license", "contact", "added", "file"):
            with self.subTest(key=key):
                entry = dataset_dict()
                del entry[key]
                self.assertRefused(f"missing field '{key}'", entry)

    def test_bad_slug(self) -> None:
        self.assertRefused("field 'slug'", dataset_dict(slug="Bad_Slug"))

    def test_duplicate_slug(self) -> None:
        self.assertRefused("duplicate slug", dataset_dict(), dataset_dict())

    def test_added_datetime(self) -> None:
        self.assertRefused("field 'added'", dataset_dict(added=datetime(2026, 1, 1, 9, tzinfo=UTC)))

    def test_contact_without_at(self) -> None:
        self.assertRefused("field 'contact'", dataset_dict(contact="nobody"))

    def test_bad_doi(self) -> None:
        self.assertRefused("field 'doi'", dataset_dict(doi="https://doi.org/10.1/x"))

    def test_source_must_be_https(self) -> None:
        for bad in ("http://example.org", "javascript:alert(1)", "https://a b"):
            with self.subTest(bad=bad):
                self.assertRefused("field 'source'", dataset_dict(source=bad))

    def test_no_files(self) -> None:
        self.assertRefused("at least one", dataset_dict(file=[]))

    def test_too_many_files(self) -> None:
        files = [file_dict(name=f"f{i}", url=url_for(f"f{i}")) for i in range(MAX_FILES + 1)]
        self.assertRefused("limit is 50", dataset_dict(file=files))

    def test_unknown_file_key(self) -> None:
        self.assertRefused("unknown field(s): md5", dataset_dict(file=[file_dict(md5="x")]))

    def test_url_other_bucket(self) -> None:
        url = "https://mghp.osn.xsede.org/bu-cds-test/example/data.csv"
        self.assertRefused("field 'url'", dataset_dict(file=[file_dict(url=url)]))

    def test_url_http(self) -> None:
        url = url_for().replace("https://", "http://")
        self.assertRefused("field 'url'", dataset_dict(file=[file_dict(url=url)]))

    def test_url_name_mismatch(self) -> None:
        self.assertRefused(
            "must end with /data.csv", dataset_dict(file=[file_dict(url=url_for("other.csv"))])
        )

    def test_url_query_or_fragment(self) -> None:
        for url in (url_for("actual.csv#/data.csv"), url_for() + "?v=1"):
            with self.subTest(url=url):
                self.assertRefused("field 'url'", dataset_dict(file=[file_dict(url=url)]))

    def test_url_dot_or_empty_segments(self) -> None:
        for slug in ("example/..", "example/.", "example/"):
            with self.subTest(slug=slug):
                f = file_dict(url=url_for(slug=slug))
                self.assertRefused("path segment", dataset_dict(file=[f]))

    def test_url_percent_encoding_or_backslash(self) -> None:
        # browsers decode %2e%2e to .. and treat \ as /, escaping the bucket
        for url in (
            url_for(slug="x/%2e%2e/%2E%2e/bu-cds-test/example"),
            url_for(slug="x\\..\\..\\bu-cds-test\\example"),
            url_for("a%20b.csv"),
        ):
            with self.subTest(url=url):
                name = url.rsplit("/", 1)[1]
                f = file_dict(name=name, url=url)
                self.assertRefused("field 'url'", dataset_dict(file=[f]))

    def test_url_with_quote_or_space(self) -> None:
        for name in ("a'b.csv", "a b.csv"):
            with self.subTest(name=name):
                f = file_dict(name=name, url=url_for(name))
                self.assertRefused("field 'url'", dataset_dict(file=[f]))

    def test_duplicate_file_name(self) -> None:
        self.assertRefused("duplicate file", dataset_dict(file=[file_dict(), file_dict()]))

    def test_bad_size(self) -> None:
        for bad in (0, -1, True, 1.5, "10"):
            with self.subTest(bad=bad):
                self.assertRefused("field 'size'", dataset_dict(file=[file_dict(size=bad)]))

    def test_bad_sha(self) -> None:
        self.assertRefused("field 'sha256'", dataset_dict(file=[file_dict(sha256=SHA[:-1])]))

    def test_error_names_slug(self) -> None:
        self.assertRefused("dataset 'example'", dataset_dict(license=""))

    def test_invalid_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "m.toml"
            p.write_text("[[dataset]\n", encoding="utf-8")
            with self.assertRaises(ManifestError):
                load_manifest(p)


if __name__ == "__main__":
    unittest.main()
