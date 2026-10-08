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
        for label in ("Shell (curl)", "AWS CLI", "rclone", "Python", "R", "APA", "BibTeX", "RIS"):
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
        self.assertLess(gd.index(">Files</label>"), gd.index(">Shell (curl)</label>"))
        self.assertIn('<ul class="flist"><li><a href="', gd)

    def test_panel_css_covers_every_get_data_tab(self) -> None:
        tabs = 1 + len(snippets.get_data(one()))  # Files + the snippet tabs
        self.assertIn(f"nth-of-type({tabs}):checked~.panel:nth-of-type({tabs})", PANEL_CSS)

    def test_names_carry_context(self) -> None:
        html = render_dataset(one(title="Penguins"))
        self.assertIn(  # the title is the dataset's permalink
            '<h2 id="t-example"><a class="perma" href="#example">Penguins</a></h2>', html
        )
        self.assertIn('<summary aria-describedby="t-example">Details</summary>', html)

    def test_producer_named_on_card(self) -> None:
        org = {
            "authors": ["Natural Earth"],
            "year": 2022,
            "title": "T",
            "publisher": "Natural Earth",
        }
        many = {**org, "authors": ["Menne, M. J.", "Durre, I.", "Vose, R. S."]}
        two = {**org, "authors": ["Horst, A. M.", "Hill, A. P."]}
        self.assertIn(
            'from <span class="who">Natural Earth</span>', render_dataset(one(citation=org))
        )
        self.assertIn('<span class="who">Menne et al.</span>', render_dataset(one(citation=many)))
        self.assertIn(
            '<span class="who">Horst &amp; Hill</span>', render_dataset(one(citation=two))
        )
        self.assertNotIn('class="who"', render_dataset(one()))  # cites its own catalog entry

    def test_intro_does_not_claim_cds_produced_the_data(self) -> None:
        html = page()
        self.assertNotIn("datasets from research at", html)
        self.assertIn("Each dataset names who produced it.", html)

    def test_identity_band(self) -> None:  # chosen 2026-10-08 (docs/design-decisions.md)
        html = render_page(SAMPLE, ASSETS, DAY, None)
        self.assertIn('class="band"', html)
        self.assertIn(f"<b>{len(SAMPLE.datasets)}</b> datasets", html)  # computed, not typed
        self.assertNotIn('class="summary"', html)  # the band states the facts once
        self.assertNotIn("Open data from", html)  # curated and hosted, not produced, by CDS
        self.assertIn('class="orglink" href="https://www.bu.edu/cds-faculty/"', html)
        for anchor in ('href="#publish"', 'href="#about"', 'id="about"', 'id="publish"'):
            self.assertIn(anchor, html)

    def test_publish_never_dead_ends(self) -> None:
        live = Catalog(None, (), [one()], steward="data@example.edu")
        with_contact = render_page(live, ASSETS, DAY, None)
        self.assertIn('class="cta primary" href="#publish"', with_contact)
        self.assertIn('href="mailto:data@example.edu"', with_contact)
        without = page(one())
        self.assertNotIn('class="cta primary" href="#publish"', without)  # not the filled button
        self.assertIn("contact will be listed here when the catalog goes live", without)
        self.assertNotIn("mailto:", without[without.index('id="publish"') :])

    def test_regions_named_once(self) -> None:
        html = page(one())
        self.assertEqual(html.count('aria-label="About this catalog"'), 1)
        self.assertIn('class="band" aria-label="Catalog summary"', html)

    def test_header_focus_ring_is_light(self) -> None:
        self.assertIn("header :focus-visible{outline-color:var(--on-accent);}", page())

    def test_empty_catalog_has_no_band(self) -> None:
        html = page()
        self.assertNotIn('class="band"', html)
        self.assertIn("Each dataset names who produced it.", html)

    def test_table_shape_coverage_and_columns(self) -> None:
        table = file_dict(rows=33145, columns=["STATION", "DATE", "PRCP"])
        html = render_dataset(one(coverage="1936–2026, one station", file=[table]))
        self.assertIn("33,145 rows × 3 columns", html)  # on the card, before Details
        self.assertIn('<p class="cov">Coverage: 1936–2026, one station</p>', html)
        self.assertIn("Columns in data.csv (3)", html)
        self.assertIn("<code>STATION</code>, <code>DATE</code>, <code>PRCP</code>", html)
        plain = render_dataset(one())
        self.assertNotIn(" rows", plain)
        self.assertNotIn('class="cov"', plain)
        self.assertNotIn('class="cols"', plain)

    def test_chip_count_named_without_aria_label(self) -> None:
        html = render_page(SAMPLE, ASSETS, DAY, None)
        chip = html[
            html.index('data-tag="boston"') : html.index(
                "</button>", html.index('data-tag="boston"')
            )
        ]
        self.assertNotIn("aria-label", chip)
        self.assertIn('<span class="sr"> datasets</span>', chip)

    def test_heading_name_keeps_word_break(self) -> None:
        self.assertIn('Sciences</span></a> <span class="hsep" aria-hidden="true">|</span>', page())

    def test_escaping(self) -> None:
        html = render_dataset(one(title="<script>x</script> & co"))
        self.assertNotIn("<script>x", html)
        self.assertIn("&lt;script&gt;x&lt;/script&gt; &amp; co", html)

    def test_filter_data_attributes(self) -> None:
        html = render_dataset(one(title="Big Trees", tags=["example", "other"]))
        self.assertIn('data-tags="example other"', html)
        self.assertRegex(html, r'data-text="big trees [^"]*example other ')
        table = file_dict(rows=3, columns=["DBH", "spp_com"])
        cov = render_dataset(one(coverage="Boston, 2026", file=[table]))
        text = cov[cov.index('data-text="') : cov.index('"', cov.index('data-text="') + 11)]
        for word in ("csv", "data.csv", "dbh", "spp_com", "boston, 2026"):  # format, file, columns
            self.assertIn(word, text)

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
        self.assertIn('<div class="filters" hidden>', html)
        self.assertIn(f"{len(ids)} of {len(ids)} datasets", html)

    def test_chips_counted_and_extras_collapsed(self) -> None:
        html = render_page(SAMPLE, ASSETS, DAY, None)
        chips = re.findall(r'class="chip( extra)?" data-tag="([a-z-]+)"', html)
        self.assertEqual(len(chips), len(SAMPLE.tags))
        self.assertGreater(len(chips), 12)  # the sample is built to exercise "More tags"
        self.assertEqual(sum(1 for extra, _ in chips if extra), len(chips) - 12)
        self.assertIn('class="more-tags"', html)

    def test_summary_facts_in_band(self) -> None:  # the band replaced the summary line
        total = sum(d.total_size for d in SAMPLE.datasets)
        html = render_page(SAMPLE, ASSETS, DAY, None)
        band = html[html.index('<section class="band"') : html.index("</section>")]
        self.assertIn("<b>24</b> datasets", band)
        self.assertIn(f"<b>{human_size(total)}</b> to download", band)
        self.assertIn('updated <span class="nw">2026-10-06</span>', band)

    def test_empty_catalog(self) -> None:
        html = page()
        self.assertIn("No datasets published yet.", html)

    def test_notice_is_a_header_tag(self) -> None:
        html = page(one(), notice="Demo <b>")
        self.assertIn('Public Research Data <span class="hdr-tag">Demo &lt;b&gt;</span></h1>', html)
        self.assertNotIn('class="notice"', html)

    def test_empty_state_and_live_regions(self) -> None:
        html = page(one())
        self.assertIn('<p class="empty" hidden>No datasets match.', html)
        self.assertIn('<p class="count" aria-live="polite">', html)
        self.assertIn('<p class="sr" id="live" aria-live="polite"></p>', html)

    def test_footer(self) -> None:
        html = page()
        self.assertIn('<a class="ft-link" href="catalog.json">catalog.json</a>', html)
        self.assertEqual(html.count('class="ft-emblem"'), 1)  # light logo only
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
            # short windows and large text keep normal page scrolling (WCAG 1.4.4, 1.4.10)
            "@media(min-width:1100px) and (min-height:38em){html,body{height:100%;overflow:hidden;}",
            ".list{flex:1 1 auto;min-height:0;overflow:auto;",
            "@media(max-width:1099px){.wrap{display:block;}.side{position:sticky;top:0;",
            "@media(min-width:1300px){.ds{display:grid;",
            ".meta{grid-area:2/1;}",
            ".badges{grid-area:2/2/5/3;",
            # owner chose option B (2026-10-08): gap + hairline between buttons and tags
            "align-self:start;margin-top:12px;padding-top:10px;border-top:1px solid var(--border);",
            "@media print{",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, html)
        self.assertIn("background:var(--bg);font-size:1rem;", html)

    def test_sidebar_is_one_framed_filter_box(self) -> None:
        html = page(one())
        self.assertNotIn('class="toc', html)  # the cards are the only dataset list
        self.assertIn(
            ".filters{border:1px solid var(--border);border-radius:10px;"
            "background:var(--surface2);",
            html,
        )
        self.assertIn(("accent", "surface2"), CONTRAST_TEXT)  # Clear filters, More tags

    def test_script_uses_the_css_shell_query(self) -> None:
        query = "(min-width:1100px) and (min-height:38em)"
        self.assertIn(f"@media{query}{{html,body{{height:100%;overflow:hidden;}}", page(one()))
        self.assertIn(f'matchMedia("{query}")', PAGE_JS)  # the list is a tab stop only there

    def test_header_and_footer_links_match_cluster(self) -> None:
        html = page(one())  # cluster.cds.bu.edu, measured 2026-10-08: 56px bar, 13.2px links
        self.assertIn("padding:12px var(--content-pad);", html)
        self.assertNotIn("header{padding-top:8px;", html)
        self.assertIn(".ft-link{color:var(--muted);font-size:0.75rem;", html)

    def test_intro_full_width_and_no_terms_paragraph(self) -> None:
        html = page(one())
        self.assertIn(".intro p{margin:0 0 8px;}", html)
        self.assertNotIn("Data is provided as is", html)
        self.assertNotIn(".terms", html)

    def test_separator_hidden(self) -> None:
        html = page(one())
        intro = html[html.index('<section class="intro">') : html.index("</section>")]
        self.assertNotIn("terms", intro)
        self.assertIn('<span class="hsep" aria-hidden="true">|</span>', html)

    def test_cards_live_in_a_focusable_list(self) -> None:
        html = page(one())
        self.assertIn('<div class="list" role="region" tabindex="0" aria-label="Datasets">', html)
        lst = html[html.index('<div class="list"') :]
        self.assertLess(lst.index('<article class="ds"'), lst.index("</main>"))
        self.assertGreater(html.index('<div class="list"'), html.index('<section class="band"'))

    def test_light_only_like_cluster_page(self) -> None:
        html = page()
        self.assertIn(":root{color-scheme:light;", html)
        self.assertNotIn("prefers-color-scheme", html)


class Contrast(unittest.TestCase):
    def test_text_pairs_meet_aa(self) -> None:
        for fg, bg in CONTRAST_TEXT:
            with self.subTest(fg=fg, bg=bg):
                self.assertGreaterEqual(ratio(TOKENS[fg], TOKENS[bg]), 4.5)

    def test_ui_pairs_meet_3_to_1(self) -> None:
        for fg, bg in CONTRAST_UI:
            with self.subTest(fg=fg, bg=bg):
                self.assertGreaterEqual(ratio(TOKENS[fg], TOKENS[bg]), 3.0)


if __name__ == "__main__":
    unittest.main()
