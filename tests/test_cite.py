"""Tests for scripts.cite: APA, BibTeX and RIS from [citation] or the catalog-entry fallback."""

from __future__ import annotations

import unittest

from scripts import cite
from tests.helpers import dataset_dict, parse

FULL = {
    "authors": ["Horst, Allison M.", "Hill, Alison P.", "Gorman, Kristen B."],
    "year": 2020,
    "title": "palmerpenguins: Palmer Archipelago (Antarctica) penguin data",
    "publisher": "Zenodo",
}


def ds(**kw: object):
    return parse(dataset_dict(**kw))


class Effective(unittest.TestCase):
    def test_fallback_cites_catalog_entry(self) -> None:
        c = cite.effective(ds())
        self.assertEqual(c.authors, (cite.ORG,))
        self.assertEqual(c.year, 2026)
        self.assertEqual(c.publisher, "BU CDS Public Research Data")

    def test_link_order(self) -> None:
        self.assertEqual(cite.link(ds()), "https://data.cds.bu.edu/#example")
        self.assertEqual(cite.link(ds(source="https://s.org/x")), "https://s.org/x")
        self.assertEqual(
            cite.link(ds(source="https://s.org/x", doi="10.5281/zenodo.1")),
            "https://doi.org/10.5281/zenodo.1",
        )
        self.assertEqual(cite.link(ds(citation={**FULL, "url": "https://u.org"})), "https://u.org")
        self.assertEqual(  # APA 7 prefers the DOI to a URL
            cite.link(ds(citation={**FULL, "url": "https://u.org", "doi": "10.5281/zenodo.1"})),
            "https://doi.org/10.5281/zenodo.1",
        )


class Apa(unittest.TestCase):
    def test_three_authors(self) -> None:
        text = cite.apa(ds(citation={**FULL, "doi": "10.5281/zenodo.3960218"}))
        self.assertEqual(
            text,
            "Horst, A. M., Hill, A. P., & Gorman, K. B. (2020). palmerpenguins: Palmer "
            "Archipelago (Antarctica) penguin data [Data set]. Zenodo. "
            "https://doi.org/10.5281/zenodo.3960218",
        )

    def test_two_authors_and_organization(self) -> None:
        two = {**FULL, "authors": ["Menne, Matthew J.", "NOAA National Climatic Data Center"]}
        self.assertTrue(cite.apa(ds(citation=two)).startswith(
            "Menne, M. J., & NOAA National Climatic Data Center. (2020)."))  # fmt: skip

    def test_group_author_ends_with_period(self) -> None:
        self.assertTrue(
            cite.apa(ds()).startswith(f"{cite.ORG}. (2026). Example dataset [Data set].")
        )

    def test_publisher_omitted_when_it_is_the_author(self) -> None:
        same = {**FULL, "authors": ["Natural Earth"], "publisher": "Natural Earth"}
        self.assertIn(  # no "Natural Earth." repeat between the title and the retrieval note
            "[Data set]. Retrieved", cite.apa(ds(citation=same, source="https://n.org"))
        )


class Bibtex(unittest.TestCase):
    def test_full(self) -> None:
        text = cite.bibtex(ds(citation={**FULL, "doi": "10.5281/zenodo.3960218"}))
        self.assertTrue(text.startswith("@misc{example,\n"))  # slugs are unique keys
        self.assertIn(
            "  author = {Horst, Allison M. and Hill, Alison P. and Gorman, Kristen B.},", text
        )
        self.assertIn("  doi = {10.5281/zenodo.3960218},", text)
        self.assertTrue(text.endswith("\n}"))

    def test_escapes_and_keeps_organization_whole(self) -> None:
        text = cite.bibtex(ds())  # fallback author contains '&'
        self.assertIn(
            "author = {{Boston University Faculty of Computing \\& Data Sciences}},", text
        )
        odd = cite.bibtex(ds(title="50% of #1 {x} a_b ~^\\"))
        self.assertIn(
            "title = {{50\\% of \\#1 \\{x\\} a\\_b \\textasciitilde{}\\textasciicircum{}"
            "\\textbackslash{}}},",
            odd,
        )

    def test_non_ascii_names_kept(self) -> None:
        text = cite.bibtex(ds(citation={**FULL, "authors": ["Müller, Zoë"]}))
        self.assertIn("author = {Müller, Zoë},", text)


class Ris(unittest.TestCase):
    def test_lines(self) -> None:
        lines = cite.ris(ds(citation={**FULL, "doi": "10.5281/zenodo.3960218"})).splitlines()
        self.assertEqual(lines[0], "TY  - DATA")
        self.assertIn("AU  - Gorman, Kristen B.", lines)
        self.assertIn("PY  - 2020", lines)
        self.assertIn("DO  - 10.5281/zenodo.3960218", lines)
        self.assertEqual(lines[-1], "ER  - ")


class Retrieved(unittest.TestCase):
    """A citation without a DOI points at a living source: pin the copy by its catalog date."""

    def test_no_doi_carries_retrieval_date_everywhere(self) -> None:
        d = ds(citation={**FULL, "url": "https://u.org"})
        self.assertEqual(cite.retrieved(d), d.added.isoformat())
        when = f"{d.added:%B} {d.added.day}, {d.added.year}"
        self.assertTrue(cite.apa(d).endswith(f"Zenodo. Retrieved {when}, from https://u.org"))
        self.assertIn(f"  urldate = {{{d.added.isoformat()}}}", cite.bibtex(d))
        self.assertIn(f"Y2  - {d.added.isoformat().replace('-', '/')}", cite.ris(d).splitlines())

    def test_doi_needs_no_retrieval_date(self) -> None:
        d = ds(citation={**FULL, "doi": "10.5281/zenodo.3960218"})
        self.assertIsNone(cite.retrieved(d))
        self.assertNotIn("Retrieved", cite.apa(d))
        self.assertNotIn("urldate", cite.bibtex(d))
        self.assertFalse(any(x.startswith("Y2") for x in cite.ris(d).splitlines()))


class CitationDoi(unittest.TestCase):
    def test_own_doi_not_mixed_into_the_originals_reference(self) -> None:
        d = ds(citation={**FULL, "url": "https://orig.org"}, doi="10.5281/zenodo.1")
        self.assertEqual(cite.link(d), "https://orig.org")
        self.assertNotIn("zenodo.1", cite.bibtex(d) + cite.ris(d))

    def test_citation_doi_used_everywhere(self) -> None:
        d = ds(citation={**FULL, "doi": "10.7289/V5D21VHZ"})
        self.assertEqual(cite.link(d), "https://doi.org/10.7289/V5D21VHZ")
        self.assertIn("  doi = {10.7289/V5D21VHZ},", cite.bibtex(d))
        self.assertIn("DO  - 10.7289/V5D21VHZ", cite.ris(d).splitlines())


if __name__ == "__main__":
    unittest.main()
