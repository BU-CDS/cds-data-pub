"""Tests for scripts.render: escaping, sizes, grammar, page structure."""

from __future__ import annotations

import unittest
from datetime import date

from scripts.manifest import Catalog
from scripts.render import PREVIEW_MARK, Assets, ga_tag, human_size, render_dataset, render_page
from tests.helpers import dataset_dict, file_dict, parse, url_for

ASSETS = Assets(
    plate="data:image/png;base64,UExBVEU=",
    signature="data:image/png;base64,U0lH",
    font_semibold="data:font/woff2;base64,U0VNSQ==",
    font_book="data:font/woff2;base64,Qk9PSw==",
    favicon="data:image/x-icon;base64,SUNP",
)


def one(**overrides: object):
    return parse(dataset_dict(**overrides))


def page(*datasets, notice: str | None = None, **kw: object) -> str:
    return render_page(Catalog(notice, (), list(datasets)), ASSETS, date(2026, 10, 6), None, **kw)


class HumanSize(unittest.TestCase):
    def test_values(self) -> None:
        cases = {
            1: "1 B",
            1023: "1023 B",
            1024: "1.0 KiB",
            1536: "1.5 KiB",
            1_048_575: "1.0 MiB",
            1_048_576: "1.0 MiB",
            5 * 1024**3: "5.0 GiB",
            int(2.5 * 1024**4): "2.5 TiB",
            3 * 1024**5: "3.0 PiB",
            2048 * 1024**5: "2048.0 PiB",
        }
        for n, expected in cases.items():
            with self.subTest(n=n):
                self.assertEqual(human_size(n), expected)


class RenderDataset(unittest.TestCase):
    def test_one_file_grammar(self) -> None:
        self.assertIn("1 file ·", render_dataset(one()))

    def test_many_files_grammar(self) -> None:
        files = [file_dict(name=f"f{i}", url=url_for(f"f{i}")) for i in range(3)]
        self.assertIn("3 files ·", render_dataset(one(file=files)))

    def test_up_to_five_files_not_collapsed(self) -> None:
        files = [file_dict(name=f"f{i}", url=url_for(f"f{i}")) for i in range(5)]
        html = render_dataset(one(file=files))
        self.assertNotIn("<details", html)
        self.assertEqual(html.count('<td class="fn">'), 5)

    def test_sixth_file_collapses_with_singular_label(self) -> None:
        files = [file_dict(name=f"f{i}", url=url_for(f"f{i}")) for i in range(6)]
        html = render_dataset(one(file=files))
        self.assertIn("<summary>Show 1 more file</summary>", html)
        self.assertLess(html.index('href="' + url_for("f4") + '"'), html.index("<details"))
        self.assertGreater(html.index('href="' + url_for("f5") + '"'), html.index("<details"))

    def test_thirty_files_show_five_then_collapse(self) -> None:
        files = [file_dict(name=f"f{i}", url=url_for(f"f{i}")) for i in range(30)]
        html = render_dataset(one(file=files))
        self.assertIn("<summary>Show 25 more files</summary>", html)
        self.assertEqual(html[: html.index("<details")].count('<td class="fn">'), 5)
        self.assertEqual(html.count('<td class="fn">'), 30)

    def test_title_is_escaped(self) -> None:
        html = render_dataset(one(title="<script>alert(1)</script> & co"))
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; &amp; co", html)

    def test_url_ampersand_escaped_in_href(self) -> None:
        name = "f&b=2.csv"
        html = render_dataset(one(file=[file_dict(name=name, url=url_for(name))]))
        escaped = "https://mghp.osn.xsede.org/bu-cds-public-data/example/f&amp;b=2.csv"
        self.assertIn(f'href="{escaped}"', html)
        self.assertIn(f"curl -O '{escaped}'", html)

    def test_description_paragraphs(self) -> None:
        html = render_dataset(one(description="One\nline.\n\nTwo."))
        self.assertIn("<p>One line.</p><p>Two.</p>", html)

    def test_doi_link_only_when_present(self) -> None:
        self.assertNotIn("doi.org", render_dataset(one()))
        html = render_dataset(one(doi="10.1234/abc"))
        self.assertIn('href="https://doi.org/10.1234/abc"', html)

    def test_exact_bytes_in_title(self) -> None:
        html = render_dataset(one(file=[file_dict(size=123456789)]))
        self.assertIn('title="123,456,789 bytes">117.7 MiB<', html)

    def test_slug_is_anchor(self) -> None:
        self.assertIn('<article class="ds" id="example">', render_dataset(one()))


class RenderPage(unittest.TestCase):
    def test_empty_state(self) -> None:
        html = page()
        self.assertIn("No datasets published yet.", html)
        self.assertNotIn('class="ds"', html)

    def test_stamp_and_assets(self) -> None:
        html = page(one())
        self.assertIn("Updated 2026-10-06", html)
        for uri in (ASSETS.plate, ASSETS.signature, ASSETS.font_semibold, ASSETS.font_book):
            self.assertIn(uri, html)
        self.assertIn(f'<link rel="icon" href="{ASSETS.favicon}">', html)

    def test_no_script_without_ga(self) -> None:
        html = page(one())
        self.assertNotIn("<script", html)

    def test_ga_tag_after_icon(self) -> None:
        html = render_page(Catalog(None, (), [one()]), ASSETS, date(2026, 10, 6), "G-TEST123")
        self.assertIn(ga_tag("G-TEST123"), html)
        self.assertLess(html.index('rel="icon"'), html.index("googletagmanager"))

    def test_ga_tag_uses_window_datalayer(self) -> None:
        tag = ga_tag("G-TEST123")
        self.assertIn("function gtag(){window.dataLayer.push(arguments);}", tag)
        self.assertIn('gtag("config","G-TEST123")', tag)

    def test_preview_mark(self) -> None:
        self.assertIn(PREVIEW_MARK, page(preview=True))
        self.assertNotIn(PREVIEW_MARK, page())

    def test_layout_rules_present(self) -> None:
        html = page()
        for rule in (
            "main{max-width:min(var(--content-max),98vw);width:100%;",
            ".pagefoot{max-width:min(var(--content-max),98vw);width:100%;",
            "@media(max-width:700px){.hsep{",
            "@media(max-width:600px){.files thead{display:none;}",
            "@media(pointer:coarse)",
            "@media(min-width:900px){.files{table-layout:fixed;}.files .sz{width:6em;}",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, html)


class Contact(unittest.TestCase):
    def test_contact_line_when_set(self) -> None:
        html = render_dataset(one(contact="a@b.org"))
        self.assertIn('Contact: <a href="mailto:a@b.org">a@b.org</a>', html)

    def test_no_contact_line_without_contact(self) -> None:
        entry = dataset_dict()
        del entry["contact"]
        ds = parse(entry)
        self.assertNotIn("Contact:", render_dataset(ds))

    def test_intro_points_to_contact_or_source(self) -> None:
        self.assertIn("Questions go to the contact or source listed on each dataset.", page())


class NoticeAndSource(unittest.TestCase):
    def test_no_banner_without_notice(self) -> None:
        self.assertNotIn('class="notice"', page(one()))

    def test_notice_banner_escaped(self) -> None:
        html = page(one(), notice="Demo <b>data</b>")
        self.assertIn('<p class="notice">Demo &lt;b&gt;data&lt;/b&gt;</p>', html)

    def test_source_line_only_when_set(self) -> None:
        self.assertNotIn("Source:", render_dataset(one()))
        html = render_dataset(one(source="https://example.org/a?b=1&c=2"))
        self.assertIn('Source: <a href="https://example.org/a?b=1&amp;c=2">', html)


if __name__ == "__main__":
    unittest.main()
