"""fetch_pages.py 的單元測試：不連網路。curl 以替身取代，測登記表解析、分流、擋頁判定、欄位抽取與 main 的 exit code。

執行（在 skill 目錄下）：python3 -I -m unittest discover -s tests -v
"""

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_pages as fp  # noqa: E402

REGISTRY_SAMPLE = """
| 網域 | 查證方式 | 觀察到的回應 |
| ---- | -------- | ------------ |
| `amazon.com` | curl | 200 |
| `books.com.tw` | 瀏覽器 | 403 |
| `example.org` | Browser | 打錯的值要略過 |
沒有表格符號的行要略過
"""


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = fp.main(argv)
    return code, out.getvalue(), err.getvalue()


class LoadRegistryTest(unittest.TestCase):
    def test_parses_curl_and_browser_rows_only(self):
        routes = fp.load_registry(REGISTRY_SAMPLE)
        self.assertEqual(routes, {"amazon.com": "curl", "books.com.tw": "browser"})

    def test_real_registry_rows(self):
        routes = fp.load_registry(fp.REGISTRY.read_text(encoding="utf-8"))
        for domain in ("books.com.tw", "law.moj.gov.tw"):
            self.assertEqual(routes.get(domain), "browser", domain)
        for domain in ("amazon.com", "sanmin.com.tw", "tenlong.com.tw"):
            self.assertEqual(routes.get(domain), "curl", domain)


class RouteForTest(unittest.TestCase):
    def setUp(self):
        self.routes = fp.load_registry(REGISTRY_SAMPLE)

    def test_subdomain_matches(self):
        self.assertEqual(fp.route_for("https://www.books.com.tw/products/1", self.routes), "browser")

    def test_lookalike_domain_does_not_match(self):
        self.assertEqual(fp.route_for("https://notbooks.com.tw/x", self.routes), "curl")

    def test_unregistered_and_mistyped_default_to_curl(self):
        self.assertEqual(fp.route_for("https://unknown.example/x", self.routes), "curl")
        self.assertEqual(fp.route_for("https://example.org/x", self.routes), "curl")

    def test_longest_domain_wins(self):
        routes = {"books.com.tw": "curl", "www.books.com.tw": "browser"}
        self.assertEqual(fp.route_for("https://www.books.com.tw/x", routes), "browser")


class BlockedTest(unittest.TestCase):
    def test_status_codes(self):
        for status in sorted(fp.BLOCK_STATUS):
            self.assertTrue(fp.is_blocked(status, "<html></html>"))
        for status in ("200", "404", "000"):
            self.assertFalse(fp.is_blocked(status, "<html>ok</html>"))

    def test_every_marker_on_200_page(self):
        for marker in fp.BLOCK_MARKERS:
            self.assertTrue(fp.is_blocked("200", f"<p>{marker.upper()}</p>"), marker)

    def test_recaptcha_script_and_title_are_not_blocks(self):
        self.assertFalse(fp.is_blocked("200", '<script src="https://www.google.com/recaptcha/api.js">'))
        self.assertFalse(fp.is_blocked("200", "<title>CAPTCHA: Using Hard AI Problems</title>"))


class ExtractTest(unittest.TestCase):
    def test_title_unescapes_and_strips_pipe(self):
        page = "<title>\n Book &amp; Why | Amazon </title>"
        self.assertEqual(fp.extract_title(page), "Book & Why / Amazon")

    def test_title_missing(self):
        self.assertEqual(fp.extract_title("<html></html>"), "")

    def test_big5_page_decoded_by_meta_charset(self):
        raw = '<meta charset="big5"><title>因果革命</title>'.encode("big5")
        self.assertEqual(fp.extract_title(fp.decode_page(raw)), "因果革命")

    def test_isbn13_checksum_dedup_and_hyphens(self):
        page = "978-1-5416-0898-6 ... 9781541608986 ... 9789866525636 ... order 9781234567890"
        self.assertEqual(fp.extract_isbns(page), ["9781541608986", "9789866525636"])

    def test_isbn10_after_label_only(self):
        page = "ISBN-10: 0393929728 ... ISBN: 0-691-15284-5 ... phone 0393929728"
        self.assertEqual(fp.extract_isbns(page), ["0393929728", "0691152845"])

    def test_isbn10_with_direction_marks(self):
        page = "<span>ISBN-10 ‏ : ‎</span> <span>1541608984</span>"
        self.assertEqual(fp.extract_isbns(page), ["1541608984"])

    def test_cap(self):
        isbns = []
        base = 978000000000
        n = 0
        while len(isbns) < fp.MAX_ISBNS + 5:
            d12 = str(base + n)
            n += 1
            check = (10 - sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d12)) % 10) % 10
            isbns.append(d12 + str(check))
        self.assertEqual(len(fp.extract_isbns(" ".join(isbns))), fp.MAX_ISBNS)


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def write_list(self, *urls):
        p = self.tmp / "urls.txt"
        p.write_text("\n".join(urls) + "\n", encoding="utf-8")
        return p

    def test_wrong_argc(self):
        self.assertEqual(run_main(["x"])[0], 2)

    def test_missing_list_file(self):
        self.assertEqual(run_main(["x", str(self.tmp / "nope.txt"), str(self.tmp / "p")])[0], 2)

    def test_empty_list(self):
        p = self.write_list("# comment", "")
        self.assertEqual(run_main(["x", str(p), str(self.tmp / "p")])[0], 2)

    def test_browser_rows_send_no_request(self):
        p = self.write_list("https://www.books.com.tw/products/1")
        with mock.patch.object(fp.subprocess, "run") as run:
            code, out, err = run_main(["x", str(p), str(self.tmp / "p")])
        run.assert_not_called()
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "1|browser|-|-|https://www.books.com.tw/products/1||")
        self.assertIn("1 url(s), 0 curl, 1 browser, 0 blocked, 0 failed", err)

    def test_no_curl_in_path(self):
        p = self.write_list("https://www.amazon.com/dp/1")
        with mock.patch.object(fp.shutil, "which", return_value=None):
            self.assertEqual(run_main(["x", str(p), str(self.tmp / "p")])[0], 2)

    def test_same_host_waits_between_requests(self):
        p = self.write_list("https://www.amazon.com/dp/1", "https://www.amazon.com/dp/2",
                            "https://law.moj.gov.tw/x")
        ok = subprocess.CompletedProcess([], 0, stdout="200", stderr="")
        with mock.patch.object(fp.subprocess, "run", return_value=ok), \
                mock.patch.object(fp.time, "monotonic", return_value=100.0), \
                mock.patch.object(fp.time, "sleep") as sleep:
            code, _, _ = run_main(["x", str(p), str(self.tmp / "p")])
        self.assertEqual(code, 0)
        sleep.assert_called_once_with(fp.MIN_INTERVAL_SECONDS)

    def test_failed_fetch_does_not_read_stale_page(self):
        p = self.write_list("https://www.amazon.com/dp/1")
        pages = self.tmp / "p"
        pages.mkdir()
        (pages / "1.html").write_text("<title>Old Book</title> 9789866525636", encoding="utf-8")
        failed = subprocess.CompletedProcess([], 6, stdout="000", stderr="curl: (6) Could not resolve host\n")
        with mock.patch.object(fp.subprocess, "run", return_value=failed):
            code, out, err = run_main(["x", str(p), str(pages)])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "1|curl|000|no|https://www.amazon.com/dp/1||")
        self.assertFalse((pages / "1.html").exists())
        self.assertIn("Could not resolve host", err)
        self.assertIn("1 failed", err)


if __name__ == "__main__":
    unittest.main()
