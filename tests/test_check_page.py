"""Tests for scripts.check_page: the real page passes; each forbidden pattern is refused."""

from __future__ import annotations

import hashlib
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

from scripts.check_page import check_html, main
from scripts.manifest import Catalog, load_manifest
from scripts.render import ga_tag, render_page
from tests.test_render import ASSETS

SAMPLE = load_manifest(Path("examples/sample.toml"))
DAY = date(2026, 10, 6)
CLEAN = render_page(SAMPLE, ASSETS, DAY, None)
PREVIEW = render_page(SAMPLE, ASSETS, DAY, None, preview=True)
WITH_GA = render_page(SAMPLE, ASSETS, DAY, "G-TEST123")


def inject(html: str, snippet: str) -> str:
    return html.replace("</main>", snippet + "</main>")


class Passes(unittest.TestCase):
    def test_clean_build(self) -> None:
        self.assertEqual(check_html(CLEAN), [])

    def test_preview_build_with_flag(self) -> None:
        self.assertEqual(check_html(PREVIEW, preview=True), [])

    def test_ga_build(self) -> None:
        self.assertEqual(check_html(WITH_GA), [])
        self.assertEqual(check_html(WITH_GA, require_ga="G-TEST123"), [])

    def test_empty_state(self) -> None:
        self.assertEqual(check_html(render_page(Catalog(None, []), ASSETS, DAY, None)), [])


class Refuses(unittest.TestCase):
    def assertProblem(self, problems: list[str], fragment: str) -> None:
        self.assertTrue(any(fragment in p for p in problems), f"{fragment!r} not in {problems}")

    def test_preview_without_flag(self) -> None:
        self.assertProblem(check_html(PREVIEW), "preview")

    def test_flag_on_non_preview(self) -> None:
        self.assertProblem(check_html(CLEAN, preview=True), "preview")

    def test_preview_with_ga(self) -> None:
        html = PREVIEW.replace("</head>", ga_tag("G-TEST123") + "</head>")
        self.assertProblem(check_html(html, preview=True), "Google Analytics")

    def test_foreign_sourced_script(self) -> None:
        for tag in (
            '<script src="https://evil.example/x.js"></script>',
            '<script async src="https://evil.example/x.js"></script>',
            "<script defer src=//cdn.example/x.js></script>",
        ):
            with self.subTest(tag=tag):
                self.assertProblem(check_html(inject(CLEAN, tag)), "sourced script")

    def test_stray_inline_script(self) -> None:
        self.assertProblem(check_html(inject(CLEAN, "<script>1</script>")), "inline script")
        self.assertProblem(check_html(inject(WITH_GA, "<script>1</script>")), "inline script")

    def test_forbidden_apis(self) -> None:
        for needle in (
            "fetch(",
            "XMLHttpRequest",
            "localStorage",
            "sessionStorage",
            "document.cookie",
            "indexedDB",
        ):
            with self.subTest(needle=needle):
                self.assertProblem(check_html(inject(CLEAN, f"<p>{needle}</p>")), needle)

    def test_http_link(self) -> None:
        self.assertProblem(check_html(inject(CLEAN, '<a href="http://x.org/">x</a>')), "http://")
        self.assertProblem(check_html(inject(CLEAN, "<img src=http://x.org/i.png>")), "http://")

    def test_missing_stamp(self) -> None:
        self.assertProblem(check_html(CLEAN.replace("Updated 2026-10-06", "")), "Updated")

    def test_two_ga_tags(self) -> None:
        html = WITH_GA.replace("</head>", ga_tag("G-TEST123") + "</head>")
        self.assertProblem(check_html(html), "more than one")

    def test_require_ga_missing(self) -> None:
        self.assertProblem(check_html(CLEAN, require_ga="G-TEST123"), "G-TEST123")

    def test_require_ga_wrong_id(self) -> None:
        self.assertProblem(check_html(WITH_GA, require_ga="G-OTHER99"), "G-OTHER99")

    def test_loader_config_mismatch(self) -> None:
        html = WITH_GA.replace('gtag("config","G-TEST123")', 'gtag("config","G-OTHER99")')
        self.assertProblem(check_html(html), "does not match")


class ManifestBinding(unittest.TestCase):
    def test_matching_hash_passes(self) -> None:
        html = render_page(Catalog(None, []), ASSETS, DAY, None, manifest_sha="ab" * 32)
        self.assertEqual(check_html(html, manifest_sha="ab" * 32), [])

    def test_other_manifest_refused(self) -> None:
        html = render_page(SAMPLE, ASSETS, DAY, None, manifest_sha="cd" * 32)
        problems = check_html(html, manifest_sha="ab" * 32)
        self.assertTrue(any("not built from" in p for p in problems), problems)

    def test_missing_hash_refused(self) -> None:
        problems = check_html(CLEAN, manifest_sha="ab" * 32)
        self.assertTrue(any("not built from" in p for p in problems), problems)

    def test_cli_manifest_flag_hashes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "datasets.toml"
            manifest.write_bytes(b"# empty\n")
            digest = hashlib.sha256(b"# empty\n").hexdigest()
            page = Path(tmp) / "index.html"
            page.write_text(
                render_page(Catalog(None, []), ASSETS, DAY, None, manifest_sha=digest), "utf-8"
            )
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(page), "--manifest", str(manifest)]), 0)
                manifest.write_bytes(b"# changed\n")
                self.assertEqual(main([str(page), "--manifest", str(manifest)]), 1)


class Cli(unittest.TestCase):
    def run_cli(self, html: str, *flags: str) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "index.html"
            page.write_text(html, encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = main([str(page), *flags])
        return code, out.getvalue()

    def test_pass(self) -> None:
        code, out = self.run_cli(CLEAN)
        self.assertEqual((code, "OK" in out), (0, True))

    def test_fail_lists_every_problem(self) -> None:
        code, out = self.run_cli(inject(PREVIEW, "<p>fetch(</p>"))
        self.assertEqual(code, 1)
        self.assertIn("preview", out)
        self.assertIn("fetch(", out)

    def test_flags_exclusive(self) -> None:
        with self.assertRaises(SystemExit):
            main(["x.html", "--preview", "--require-ga", "G-TEST123"])


if __name__ == "__main__":
    unittest.main()
