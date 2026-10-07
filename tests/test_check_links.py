"""Tests for scripts.check_links: injected HEAD responses, real HEAD error mapping, CLI."""

from __future__ import annotations

import io
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from scripts import check_links as cl
from scripts.manifest import parse_manifest
from tests.helpers import dataset_dict, file_dict, url_for

URL_B = url_for("b.csv")
DATA = parse_manifest(
    {"dataset": [dataset_dict(file=[file_dict(), file_dict(name="b.csv", url=URL_B, size=99)])]}
).datasets
SIZES = {url_for(): 2048, URL_B: 99}


class CheckLinks(unittest.TestCase):
    def test_all_good(self) -> None:
        self.assertEqual(cl.check_links(DATA, lambda u: (200, SIZES[u])), [])

    def test_each_failure_reported(self) -> None:
        cases = {
            403: "HTTP 403",
            404: "HTTP 404",
            0: "no response",
        }
        for status, text in cases.items():
            with self.subTest(status=status):
                out = cl.check_links(DATA, lambda u, s=status: (s, None))
                self.assertEqual(len(out), 2)
                self.assertIn(text, out[0])

    def test_wrong_size(self) -> None:
        out = cl.check_links(DATA, lambda u: (200, 1))
        self.assertIn("size 1 on OSN, 2048 in manifest", out[0])

    def test_missing_content_length_is_not_a_pass(self) -> None:
        out = cl.check_links(DATA, lambda u: (200, None))
        self.assertIn("size unverified", out[0])


class UrllibHead(unittest.TestCase):
    def test_http_error_and_no_response(self) -> None:
        err = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
        for exc, expected in ((err, (403, None)), (OSError("down"), (0, None))):
            with self.subTest(exc=exc), mock.patch("urllib.request.urlopen", side_effect=exc):
                self.assertEqual(cl.urllib_head("https://x"), expected)


class Main(unittest.TestCase):
    def run_main(self, head) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            m = Path(tmp) / "m.toml"
            m.write_text(
                f'[[dataset]]\nslug = "example"\ntitle = "t"\ndescription = "d"\n'
                f'license = "CC0-1.0"\ncontact = "a@b.c"\nadded = 2026-10-07\n'
                f'[[dataset.file]]\nname = "data.csv"\nurl = "{url_for()}"\nsize = 2048\n'
                f'sha256 = "{"a" * 64}"\n',
                encoding="utf-8",
            )
            out = io.StringIO()
            with (
                redirect_stdout(out),
                redirect_stderr(out),
                mock.patch.object(cl, "urllib_head", head),
            ):
                code = cl.main(["--manifest", str(m)])
        return code, out.getvalue()

    def test_pass_and_fail_exit_codes(self) -> None:
        self.assertEqual(self.run_main(lambda u: (200, 2048))[0], 0)
        code, out = self.run_main(lambda u: (404, None))
        self.assertEqual(code, 1)
        self.assertIn("1 problem(s)", out)


if __name__ == "__main__":
    unittest.main()
