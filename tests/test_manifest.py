"""Tests for scripts.manifest: every rule refuses with the file and field named."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from scripts.manifest import (
    MAX_FILES,
    ManifestError,
    catalog_digest,
    license_url,
    load_catalog,
)
from tests.helpers import SHA, dataset_dict, dataset_toml, file_dict, parse, url_for, write_catalog

CITE = {"authors": ["Horst, Allison M."], "year": 2020, "title": "T", "publisher": "Zenodo"}


class Valid(unittest.TestCase):
    def test_minimal(self) -> None:
        ds = parse()
        self.assertEqual(ds.slug, "example")
        self.assertEqual(ds.tags, ("example",))
        self.assertEqual(ds.total_size, 2048)
        self.assertEqual(ds.prefix, "example")
        self.assertIsNone(ds.doi)
        self.assertIsNone(ds.source)
        self.assertIsNone(ds.citation)

    def test_optional_fields(self) -> None:
        ds = parse(
            dataset_dict(
                doi="10.5281/zenodo.1", source="https://example.org/x", citation=dict(CITE)
            )
        )
        self.assertEqual(ds.doi, "10.5281/zenodo.1")
        self.assertEqual(ds.citation.authors, ("Horst, Allison M.",))
        self.assertIsNone(ds.citation.url)

    def test_contact_optional(self) -> None:
        entry = dataset_dict()
        del entry["contact"]
        self.assertIsNone(parse(entry).contact)

    def test_nested_prefix(self) -> None:
        url = url_for("x.csv", slug="demo/example")
        self.assertEqual(parse(dataset_dict(file=[file_dict(name="x.csv", url=url)])).prefix,
                         "demo/example")  # fmt: skip

    def test_sha_lowercased(self) -> None:
        self.assertEqual(parse(dataset_dict(file=[file_dict(sha256="A" * 64)])).files[0].sha256,
                         "a" * 64)  # fmt: skip

    def test_license_url(self) -> None:
        self.assertEqual(license_url("CC0-1.0"), "https://spdx.org/licenses/CC0-1.0.html")
        self.assertIsNone(license_url("Public domain"))


class Refused(unittest.TestCase):
    def assertRefused(self, fragment: str, entry: dict, slug: str = "example") -> None:
        with self.assertRaises(ManifestError) as ctx:
            parse(entry, slug=slug)
        self.assertIn(fragment, str(ctx.exception))

    def test_error_names_file(self) -> None:
        self.assertRefused("datasets/example.toml", dataset_dict(license=""))

    def test_bad_slug_file_name(self) -> None:
        self.assertRefused("file name", dataset_dict(), slug="Bad_Slug")

    def test_unknown_dataset_key(self) -> None:
        self.assertRefused("unknown field(s): version", dataset_dict(version=1))

    def test_each_required_field(self) -> None:
        for key in ("title", "description", "license", "added", "tags", "file"):
            with self.subTest(key=key):
                entry = dataset_dict()
                del entry[key]
                self.assertRefused(f"missing field '{key}'", entry)

    def test_license_shape(self) -> None:
        self.assertRefused("field 'license'", dataset_dict(license="CC BY 4.0"))

    def test_tags(self) -> None:
        cases = {
            "1 to 5": [],
            "not in catalog.toml": ["nope"],
            "duplicate tag": ["example", "example"],
        }
        for fragment, tags in cases.items():
            with self.subTest(tags=tags):
                self.assertRefused(fragment, dataset_dict(tags=tags))
        self.assertRefused("1 to 5", dataset_dict(tags=["example"] * 6))

    def test_tags_must_be_strings(self) -> None:
        self.assertRefused("not in catalog.toml", dataset_dict(tags=[["example"]]))

    def test_citation_rules(self) -> None:
        cases = {
            "unknown field(s): editor": {**CITE, "editor": "x"},
            "authors": {**CITE, "authors": []},
            "year": {**CITE, "year": 1800},
            "url": {**CITE, "url": "http://x.org"},
            "doi": {**CITE, "doi": "https://doi.org/10.1/x"},
            "publisher": {k: v for k, v in CITE.items() if k != "publisher"},
        }
        for fragment, cite in cases.items():
            with self.subTest(fragment=fragment):
                self.assertRefused(fragment, dataset_dict(citation=cite))

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

    def test_files_share_one_folder(self) -> None:
        files = [file_dict(), file_dict(name="b.csv", url=url_for("b.csv", slug="elsewhere"))]
        self.assertRefused("one folder", dataset_dict(file=files))

    def test_file_at_bucket_root(self) -> None:
        f = file_dict(url=f"{url_for()[: -len('example/data.csv')]}data.csv")
        self.assertRefused("folder", dataset_dict(file=[f]))

    def test_url_rules(self) -> None:
        bad = {
            "other bucket": "https://mghp.osn.xsede.org/bu-cds-test/example/data.csv",
            "http": url_for().replace("https://", "http://"),
            "fragment": url_for("actual.csv#/data.csv"),
            "query": url_for() + "?v=1",
            "percent": url_for(slug="x/%2e%2e/example"),
            "backslash": url_for(slug="x\\..\\example"),
        }
        for label, url in bad.items():
            with self.subTest(label=label):
                self.assertRefused("field 'url'", dataset_dict(file=[file_dict(url=url)]))

    def test_url_dot_or_empty_segments(self) -> None:
        for slug in ("example/..", "example/.", "example/"):
            with self.subTest(slug=slug):
                f = file_dict(url=url_for(slug=slug))
                self.assertRefused("path segment", dataset_dict(file=[f]))

    def test_url_name_mismatch(self) -> None:
        f = file_dict(url=url_for("other.csv"))
        self.assertRefused("must end with /data.csv", dataset_dict(file=[f]))

    def test_file_name_without_slash(self) -> None:
        f = file_dict(name="sub/a.csv", url=url_for("sub/a.csv"))
        self.assertRefused("field 'name'", dataset_dict(file=[f]))

    def test_reserved_slugs(self) -> None:
        for slug in ("q", "live", "chips", "chips-hd"):
            with self.subTest(slug=slug):
                self.assertRefused("reserved", dataset_dict(), slug=slug)

    def test_reserved_slug_prefixes(self) -> None:
        # the page derives ids t-<slug>, ct-<slug>-N, gd-<slug>-N: "t-foo" would clash with "foo"
        for slug in ("t-foo", "ct-foo-0", "gd-foo"):
            with self.subTest(slug=slug):
                self.assertRefused("reserved", dataset_dict(), slug=slug)
        self.assertEqual(parse(dataset_dict(), slug="tgd-ct").slug, "tgd-ct")

    def test_duplicate_file_name(self) -> None:
        self.assertRefused("duplicate file", dataset_dict(file=[file_dict(), file_dict()]))

    def test_bad_size(self) -> None:
        for bad in (0, -1, True, 1.5, "10"):
            with self.subTest(bad=bad):
                self.assertRefused("field 'size'", dataset_dict(file=[file_dict(size=bad)]))

    def test_bad_sha(self) -> None:
        self.assertRefused("field 'sha256'", dataset_dict(file=[file_dict(sha256=SHA[:-1])]))

    def test_bad_rows(self) -> None:
        for bad in (-1, True, 1.5, "10"):
            with self.subTest(bad=bad):
                self.assertRefused("field 'rows'", dataset_dict(file=[file_dict(rows=bad)]))

    def test_bad_columns(self) -> None:
        for bad in ("a,b", ["a", ""], ["a", 1], ["a", "a"], ["c"] * 1001):
            with self.subTest(bad=str(bad)[:20]):
                self.assertRefused("field 'columns'", dataset_dict(file=[file_dict(columns=bad)]))

    def test_steward_must_be_an_address(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "datasets").mkdir()
            (root / "catalog.toml").write_text('tags = ["example"]\nsteward = "the steward"\n')
            with self.assertRaises(ManifestError) as ctx:
                load_catalog(root)
            self.assertIn("field 'steward'", str(ctx.exception))
            (root / "catalog.toml").write_text('tags = ["example"]\nsteward = "data@bu.edu"\n')
            self.assertEqual(load_catalog(root).steward, "data@bu.edu")

    def test_coverage_is_one_short_line(self) -> None:
        self.assertRefused("field 'coverage'", dataset_dict(coverage="x" * 161))


class Shape(unittest.TestCase):
    def test_rows_columns_and_coverage_parsed(self) -> None:
        ds = parse(
            dataset_dict(
                coverage="2007–2009, Palmer Archipelago",
                file=[file_dict(rows=344, columns=["species", "island"])],
            )
        )
        self.assertEqual(ds.coverage, "2007–2009, Palmer Archipelago")
        self.assertEqual((ds.files[0].rows, ds.files[0].columns), (344, ("species", "island")))

    def test_all_optional(self) -> None:
        ds = parse()
        self.assertIsNone(ds.coverage)
        self.assertEqual((ds.files[0].rows, ds.files[0].columns), (None, ()))


class LoadCatalog(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_loads_newest_first_and_notice(self) -> None:
        write_catalog(
            self.root,
            {"older": dataset_toml("older", "2026-01-01"), "newer": dataset_toml("newer")},
            catalog='notice = "Demo."\ntags = ["example", "other"]\n',
        )
        cat = load_catalog(self.root)
        self.assertEqual(cat.notice, "Demo.")
        self.assertEqual(cat.tags, ("example", "other"))
        self.assertEqual([d.slug for d in cat.datasets], ["newer", "older"])

    def test_no_datasets_folder_is_empty_catalog(self) -> None:
        (self.root / "catalog.toml").write_text('tags = ["example"]\n', encoding="utf-8")
        self.assertEqual(load_catalog(self.root).datasets, [])

    def test_dotfiles_ignored(self) -> None:
        write_catalog(self.root, {"one": dataset_toml("one")})
        (self.root / "datasets" / ".DS_Store").write_bytes(b"\0\1")
        self.assertEqual(len(load_catalog(self.root).datasets), 1)

    def test_stray_file_refused(self) -> None:
        write_catalog(self.root, {"one": dataset_toml("one")})
        (self.root / "datasets" / "notes.txt").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "notes.txt"):
            load_catalog(self.root)

    def test_missing_catalog_toml(self) -> None:
        with self.assertRaisesRegex(ManifestError, "catalog.toml"):
            load_catalog(self.root)

    def test_catalog_toml_rules(self) -> None:
        for body, fragment in (
            ('tags = ["example"]\nbanner = "x"\n', "unknown top-level"),
            ('tags = ["Bad Tag"]\n', "tags"),
            ('tags = ["a", "a"]\n', "tags"),
            ('notice = " "\ntags = ["a"]\n', "notice"),
            ('notice = "A label much too long for the header"\ntags = ["a"]\n', "notice"),
        ):
            with self.subTest(body=body):
                write_catalog(self.root, {}, catalog=body)
                with self.assertRaisesRegex(ManifestError, fragment):
                    load_catalog(self.root)

    def test_invalid_toml_names_file(self) -> None:
        write_catalog(self.root, {"one": "title = \n"})
        with self.assertRaisesRegex(ManifestError, "datasets/one.toml"):
            load_catalog(self.root)

    def test_digest_tracks_content_not_dotfiles(self) -> None:
        write_catalog(self.root, {"one": dataset_toml("one")})
        first = catalog_digest(self.root)
        (self.root / "datasets" / ".DS_Store").write_bytes(b"x")
        self.assertEqual(catalog_digest(self.root), first)
        (self.root / "datasets" / "one.toml").write_text(dataset_toml("one", "2026-01-02"))
        self.assertNotEqual(catalog_digest(self.root), first)


if __name__ == "__main__":
    unittest.main()
