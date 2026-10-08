"""Tests for scripts.render: v2 page structure, escaping, no-JS defaults, contrast tokens."""

from __future__ import annotations

import re
import unittest
from datetime import date
from pathlib import Path

from scripts import snippets
from scripts.manifest import Catalog, load_catalog
from scripts.render import (
    CONTRAST_TEXT,
    CONTRAST_UI,
    PAGE_JS,
    PANEL_CSS,
    PREVIEW_MARK,
    TOKENS,
    Assets,
    ga_tag,
    human_size,
    render_dataset,
    render_page,
)
from tests.helpers import dataset_dict, file_dict, parse, url_for

ASSETS = Assets(
    plate="data:image/png;base64,UExBVEU=",
    signature="data:image/png;base64,U0lH",
    signature_dark="data:image/png;base64,REFSSw==",
    font_semibold="data:font/woff2;base64,U0VNSQ==",
    font_book="data:font/woff2;base64,Qk9PSw==",
    favicon="data:image/x-icon;base64,SUNP",
)
DAY = date(2026, 10, 6)
SAMPLE = load_catalog(Path("examples/sample"))


def one(**overrides: object):
    return parse(dataset_dict(**overrides))


def page(*datasets, notice: str | None = None, **kw: object) -> str:
    return render_page(Catalog(notice, (), list(datasets)), ASSETS, DAY, None, **kw)


def lum(hex_color: str) -> float:
    def ch(i: int) -> float:
        c = int(hex_color[i : i + 2], 16) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(1) + 0.7152 * ch(3) + 0.0722 * ch(5)


def ratio(a: str, b: str) -> float:
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class HumanSize(unittest.TestCase):
    def test_values(self) -> None:
        cases = {1: "1 B", 1024: "1.0 KiB", 1536: "1.5 KiB", 5 * 1024**3: "5.0 GiB"}
        for n, expected in cases.items():
            with self.subTest(n=n):
                self.assertEqual(human_size(n), expected)


class Card(unittest.TestCase):
    def test_header_buttons_named_for_dataset(self) -> None:
        html = render_dataset(one(title="Penguins"))
        self.assertIn('aria-label="Cite Penguins"', html)
        self.assertIn('aria-label="Get data for Penguins"', html)
        self.assertLess(html.index("Cite"), html.index("Get data"))

    def test_meta_line(self) -> None:
        files = [file_dict(name=n, url=url_for(n)) for n in ("a.csv", "b.geojson", "README.md")]
        html = render_dataset(one(file=files, doi="10.5281/zenodo.1"))
        self.assertIn("3 files (CSV, GeoJSON) · ", html)
        self.assertIn(
            '6.0 KiB</span> download · added <span class="nw">2026-10-06</span> · DOI ', html
        )

    def test_badges(self) -> None:
        html = render_dataset(one(license="CC0-1.0", tags=["example", "other"]))
        self.assertIn(
            '<a class="lic" href="https://spdx.org/licenses/CC0-1.0.html">CC0-1.0</a>', html
        )
        self.assertIn('<a class="tag" href="?tag=other">other</a>', html)
        self.assertIn(
            '<span class="lic">Public domain</span>', render_dataset(one(license="Public domain"))
        )

    def test_details_hold_files_source_contact(self) -> None:
        html = render_dataset(one(source="https://s.org/x"))
        det = html[html.index('<details class="det">') :]
        for part in ("Source:", "Contact:", '<table class="files">'):
            self.assertIn(part, det)

    def test_popovers(self) -> None:
        html = render_dataset(one())
        for label in ("Download all", "AWS CLI", "rclone", "Python", "R", "APA", "BibTeX", "RIS"):
            self.assertIn(f">{label}</label>", html)
        self.assertIn("<legend>Format</legend>", html)
        self.assertIn("<legend>Citation style</legend>", html)
        self.assertIn('download="example.bib" href="data:application/x-bibtex;charset=utf-8,', html)

    def test_citation_doi_not_on_card_meta(self) -> None:
        html = render_dataset(
            one(
                citation={
                    "authors": ["A, B."],
                    "year": 2020,
                    "title": "T",
                    "publisher": "P",
                    "doi": "10.7289/V5D21VHZ",
                }
            )
        )
        meta = html[
            html.index('<p class="meta">') : html.index("</p>", html.index('<p class="meta">'))
        ]
        self.assertNotIn("DOI", meta)
        self.assertIn("10.7289/V5D21VHZ", html)  # still in the Cite popover

    def test_get_data_primary_with_files_tab(self) -> None:
        html = render_dataset(one())
        self.assertIn('<summary class="btn primary" aria-label="Get data for', html)
        self.assertIn('<summary class="btn" aria-label="Cite', html)
        gd = html[html.index("Get data for") :]
        self.assertLess(gd.index(">Files</label>"), gd.index(">Download all</label>"))
        self.assertIn('<ul class="flist"><li><a href="', gd)

    def test_panel_css_covers_every_get_data_tab(self) -> None:
        tabs = 1 + len(snippets.get_data(one()))  # Files + the snippet tabs
        self.assertIn(f"nth-of-type({tabs}):checked~.panel:nth-of-type({tabs})", PANEL_CSS)

    def test_names_carry_context(self) -> None:
        html = render_dataset(one(title="Penguins"))
        self.assertIn('<h2 id="t-example">Penguins</h2>', html)
        self.assertIn('<summary aria-describedby="t-example">Details</summary>', html)
        self.assertIn(
            'class="more" aria-expanded="false" aria-describedby="t-example" hidden', html
        )
        self.assertIn(
            '<button type="button" class="copy" aria-describedby="t-example" hidden>Copy</button>',
            html,
        )

    def test_chip_label_counts(self) -> None:
        html = render_page(SAMPLE, ASSETS, DAY, None)
        self.assertRegex(
            html,
            r'class="chip" data-tag="boston" aria-pressed="false" aria-label="boston, \d+ datasets"',
        )

    def test_escaping(self) -> None:
        html = render_dataset(one(title="<script>x</script> & co"))
        self.assertNotIn("<script>x", html)
        self.assertIn("&lt;script&gt;x&lt;/script&gt; &amp; co", html)

    def test_filter_data_attributes(self) -> None:
        html = render_dataset(one(title="Big Trees", tags=["example", "other"]))
        self.assertIn('data-tags="example other"', html)
        self.assertRegex(html, r'data-text="big trees [^"]*example other"')

    def test_js_only_controls_hidden(self) -> None:
        html = render_dataset(one())
        self.assertRegex(html, r'class="more" aria-expanded="false"[^>]* hidden>more')
        self.assertTrue(
            all(" hidden>" in m for m in re.findall(r'<button[^>]*class="copy"[^>]*>', html))
        )
        self.assertNotIn("clamp", html)

    def test_more_than_five_files_collapse(self) -> None:
        files = [file_dict(name=f"f{i}", url=url_for(f"f{i}")) for i in range(7)]
        self.assertIn("<summary>Show 2 more files</summary>", render_dataset(one(file=files)))


class Page(unittest.TestCase):
    def test_sample_cards_newest_first_and_sidebar(self) -> None:
        html = render_page(SAMPLE, ASSETS, DAY, None)
        ids = re.findall(r'<article class="ds" id="([^"]+)"', html)
        self.assertEqual(ids, [d.slug for d in SAMPLE.datasets])
        toc = re.findall(r'<li><a href="#([^"]+)"', html)
        self.assertEqual(toc, ids)
        self.assertIn('<div class="filters" hidden>', html)
        self.assertIn(f"{len(ids)} of {len(ids)} datasets", html)

    def test_chips_counted_and_extras_collapsed(self) -> None:
        html = render_page(SAMPLE, ASSETS, DAY, None)
        chips = re.findall(r'class="chip( extra)?" data-tag="([a-z-]+)"', html)
        self.assertEqual(len(chips), len(SAMPLE.tags))
        self.assertGreater(len(chips), 12)  # the sample is built to exercise "More tags"
        self.assertEqual(sum(1 for extra, _ in chips if extra), len(chips) - 12)
        self.assertIn('class="more-tags"', html)

    def test_summary_line(self) -> None:
        total = sum(d.total_size for d in SAMPLE.datasets)
        html = render_page(SAMPLE, ASSETS, DAY, None)
        self.assertIn(
            f"24 datasets · {human_size(total)} total download · "
            'updated <span class="nw">2026-10-06</span>',
            html,
        )

    def test_empty_catalog(self) -> None:
        html = page()
        self.assertIn("No datasets published yet.", html)
        self.assertNotIn('<nav class="toc"', html)

    def test_notice_escaped(self) -> None:
        self.assertIn('<p class="notice">Demo &lt;b&gt;</p>', page(one(), notice="Demo <b>"))

    def test_empty_state_and_live_regions(self) -> None:
        html = page(one())
        self.assertIn('<p class="empty" hidden>No datasets match.', html)
        self.assertIn('<p class="count" aria-live="polite">', html)
        self.assertIn('<p class="sr" id="live" aria-live="polite"></p>', html)

    def test_footer(self) -> None:
        html = page()
        self.assertIn('<a class="ft-link" href="catalog.json">catalog.json</a>', html)
        self.assertIn(ASSETS.signature_dark, html)
        self.assertIn("Updated 2026-10-06", html)

    def test_ga_and_preview(self) -> None:
        html = render_page(Catalog(None, (), [one()]), ASSETS, DAY, "G-TEST123")
        self.assertIn(ga_tag("G-TEST123"), html)
        self.assertIn(PREVIEW_MARK, page(preview=True))

    def test_page_script_embedded_last(self) -> None:
        self.assertTrue(page().endswith(f"<script>{PAGE_JS}</script></body></html>\n"))

    def test_search_field_border_is_visible(self) -> None:
        self.assertIn(
            ".side input[type=search]{width:100%;padding:7px 9px;border:1px solid var(--muted);",
            page(),
        )

    def test_v21_layout_rules(self) -> None:
        html = page(one())
        for rule in (
            "--content-max:1920px",
            "@media(min-width:1100px){header{position:sticky;top:0;",
            "html{scroll-padding-top:calc(var(--hdr) + 12px);}",
            "@media(max-width:1099px){.wrap{display:block;}.side{position:sticky;top:0;",
            "@media(min-width:1300px){.ds{display:grid;",
            ".meta{grid-area:2/1;}",
            ".badges{grid-area:2/2/5/3;",
            "@media print{",
            "@media(max-width:700px){main{display:flex;flex-direction:column;}.terms{order:9;}}",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, html)
        self.assertIn("background:var(--bg);font-size:1rem;", html)

    def test_terms_outside_intro_and_separator_hidden(self) -> None:
        html = page(one())
        intro = html[html.index('<section class="intro">') : html.index("</section>")]
        self.assertNotIn("terms", intro)
        self.assertIn('<p class="terms">', html)
        self.assertIn('<span class="hsep" aria-hidden="true">|</span>', html)

    def test_dark_tokens_and_rules(self) -> None:
        html = page()
        self.assertIn("color-scheme:light dark", html)
        dark = html[html.index("@media(prefers-color-scheme:dark){:root{") :]
        self.assertIn("--bg:#14110e", dark.split("}", 1)[0])
        self.assertEqual(html.count("prefers-color-scheme:dark){:root{"), 1)  # one dark block
        self.assertIn("[hidden]{display:none!important}", html)


class Contrast(unittest.TestCase):
    def test_text_pairs_meet_aa(self) -> None:
        for theme in (0, 1):
            for fg, bg in CONTRAST_TEXT:
                with self.subTest(theme=theme, fg=fg, bg=bg):
                    self.assertGreaterEqual(ratio(TOKENS[fg][theme], TOKENS[bg][theme]), 4.5)

    def test_ui_pairs_meet_3_to_1(self) -> None:
        for theme in (0, 1):
            for fg, bg in CONTRAST_UI:
                with self.subTest(theme=theme, fg=fg, bg=bg):
                    self.assertGreaterEqual(ratio(TOKENS[fg][theme], TOKENS[bg][theme]), 3.0)


if __name__ == "__main__":
    unittest.main()
