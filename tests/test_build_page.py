"""Tests for scripts.build_page: asset loading fails closed, CLI writes the page."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from scripts import build_page
from scripts.manifest import catalog_digest
from scripts.render import PREVIEW_MARK
from tests.helpers import write_catalog

SIBLING_FILES = (
    "bu_plate_white.png",
    "faculty_compt_data_sci_signature_toptier_rgb.png",
    "faculty_compt_data_sci_signature_toptier_rgbwhite.png",
    "WhitneySSmAdvancedSemibold.woff2",
    "WhitneySSmAdvancedBook.woff2",
)


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.sibling = self.tmp / "sibling"
        self.own = self.tmp / "own"
        self.sibling.mkdir()
        self.own.mkdir()
        for name in SIBLING_FILES:
            (self.sibling / name).write_bytes(name.encode())
        (self.own / "favicon.ico").write_bytes(b"ICO")


class LoadAssets(Fixture):
    def test_all_present(self) -> None:
        assets = build_page.load_assets(self.sibling, self.own)
        self.assertTrue(assets.plate.startswith("data:image/png;base64,"))
        self.assertTrue(assets.font_book.startswith("data:font/woff2;base64,"))
        self.assertEqual(assets.favicon, "data:image/x-icon;base64,SUNP")

    def test_each_missing_sibling_asset_named(self) -> None:
        for name in SIBLING_FILES:
            with self.subTest(name=name):
                path = self.sibling / name
                data = path.read_bytes()
                path.unlink()
                with self.assertRaises(build_page.BuildError) as ctx:
                    build_page.load_assets(self.sibling, self.own)
                self.assertIn(name, str(ctx.exception))
                path.write_bytes(data)

    def test_missing_favicon_named(self) -> None:
        (self.own / "favicon.ico").unlink()
        with self.assertRaises(build_page.BuildError) as ctx:
            build_page.load_assets(self.sibling, self.own)
        self.assertIn("favicon.ico", str(ctx.exception))


class GaId(unittest.TestCase):
    def test_ga_id_is_this_pages_own_property(self) -> None:
        self.assertEqual(build_page.GA_ID, "G-MTV6EXSR2V")  # data.cds.bu.edu stream
        self.assertRegex(build_page.GA_ID, build_page.GA_ID_RE)


class Main(Fixture):
    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with (
            redirect_stdout(out),
            redirect_stderr(err),
            mock.patch.object(build_page, "OWN_ASSETS", self.own),
        ):
            code = build_page.main(["--assets", str(self.sibling), *args])
        return code, out.getvalue(), err.getvalue()

    def test_builds_sample_preview(self) -> None:
        page = self.tmp / "p" / "index.html"
        code, out, _ = self.run_main(
            "--catalog",
            "examples/sample",
            "--out",
            str(page),
            "--preview",
            "--updated",
            "2026-10-06",
        )
        self.assertEqual(code, 0)
        html = page.read_text(encoding="utf-8")
        self.assertIn(PREVIEW_MARK, html)
        self.assertIn("Updated 2026-10-06", html)
        self.assertEqual(html.count('<article class="ds"'), 24)
        self.assertIn("preview", out)

    def test_writes_catalog_json_beside_page(self) -> None:
        page = self.tmp / "out" / "index.html"
        self.run_main("--catalog", "examples/sample", "--out", str(page), "--preview")
        data = json.loads((page.parent / "catalog.json").read_text("utf-8"))
        self.assertEqual(len(data["datasets"]), 24)

    def test_preview_never_carries_ga(self) -> None:
        page = self.tmp / "index.html"
        with mock.patch.object(build_page, "GA_ID", "G-TEST123"):
            self.run_main("--catalog", ".", "--out", str(page), "--preview")
        self.assertNotIn("googletagmanager", page.read_text(encoding="utf-8"))

    def test_page_carries_catalog_digest(self) -> None:
        page = self.tmp / "index.html"
        self.run_main("--catalog", "examples/sample", "--out", str(page), "--preview")
        digest = catalog_digest(Path("examples/sample"))
        self.assertIn(f'<meta name="cds-manifest" content="{digest}">', page.read_text("utf-8"))

    def test_deploy_build_carries_ga_when_set(self) -> None:
        page = self.tmp / "index.html"
        with mock.patch.object(build_page, "GA_ID", "G-TEST123"):
            code, _, _ = self.run_main("--catalog", ".", "--out", str(page))
        self.assertEqual(code, 0)
        html = page.read_text(encoding="utf-8")
        self.assertIn('gtag("config","G-TEST123")', html)
        self.assertNotIn(PREVIEW_MARK, html)

    def test_malformed_ga_id_refused(self) -> None:
        with mock.patch.object(build_page, "GA_ID", "UA-123"):
            code, _, err = self.run_main("--catalog", ".", "--out", str(self.tmp / "x"))
        self.assertEqual(code, 1)
        self.assertIn("GA_ID", err)

    def test_bad_catalog_exits_1_with_message(self) -> None:
        bad = write_catalog(self.tmp / "bad", {"x": 'title = "x"\n'})
        code, _, err = self.run_main("--catalog", str(bad), "--out", str(self.tmp / "x"))
        self.assertEqual(code, 1)
        self.assertIn("missing field", err)
        self.assertFalse((self.tmp / "x").exists())

    def test_missing_asset_exits_1_with_name(self) -> None:
        (self.sibling / "bu_plate_white.png").unlink()
        code, _, err = self.run_main("--catalog", ".", "--out", str(self.tmp / "x"))
        self.assertEqual(code, 1)
        self.assertIn("bu_plate_white.png", err)

    def test_missing_catalog_exits_1(self) -> None:
        code, _, err = self.run_main("--catalog", str(self.tmp / "nope"), "--out", "x")
        self.assertEqual(code, 1)
        self.assertIn("catalog.toml", err)


if __name__ == "__main__":
    unittest.main()
