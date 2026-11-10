"""neighbor_link_check.py 的測試。執行：python3 -m unittest discover -s tests（在 skill 目錄下）。"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import neighbor_link_check as nlc  # noqa: E402

FM = "---\ntitle: x\n---\n"


def card(intro: str, pos: str | None, heading: str = "概念位置", fm: str = FM) -> str:
    body = fm + intro + "\n"
    if pos is not None:
        body += f"\n## {heading}\n\n{pos}\n"
    body += "\n## 判讀方式\n\n[elsewhere](/x/a/)\n"
    return body


class NeighborLinkCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name) / "til" / "cards"
        self.d.mkdir(parents=True)
        self.write("b.md", card("x", "x"))
        self.write("c.md", card("x", "x"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name: str, text: str) -> Path:
        p = self.d / name
        p.write_text(text, encoding="utf-8")
        return p

    def run_check(self, files=("a.md",), heading="概念位置"):
        lines, problems = nlc.check(self.d, list(files), heading)
        return {l.split("\t")[1].rsplit("/", 1)[-1]: l for l in lines}, problems

    def assert_counts(self, intro: str, pos: str, expected: str, **kw):
        self.write("a.md", card(intro, pos, **kw))
        out, _ = self.run_check(heading=kw.get("heading", "概念位置"))
        self.assertIn(expected, out["a.md"])

    # 認得出的鄰卡連結形態
    def test_absolute_relative_and_same_dir_links_count(self):
        self.assert_counts("[B](/til/cards/b/) 與 [C](../c/)", "[B](b.md) [C](./c.md)", "首段:2 概念位置:2")

    def test_anchor_trailing_slash_and_titles(self):
        self.assert_counts("[B](/til/cards/b/#sec) [C](c.md 'C')", "[B](<b.md> \"B\")", "首段:2 概念位置:1")

    def test_reference_style_links(self):
        self.write("a.md", card("見 [B][bref] 與 [c][]", "[B][bref]") + "\n[bref]: b.md\n[c]: /til/cards/c/\n")
        out, _ = self.run_check()
        self.assertIn("首段:2 概念位置:1", out["a.md"])

    # 不算鄰卡連結的形態
    def test_article_with_same_slug_and_other_module_card_do_not_count(self):
        self.assert_counts("[文章](/elsewhere/articles/b/) [wiki](https://en.wikipedia.org/wiki/B)",
                           "[別模組](../../other-module/cards/b/) [文章](../../../articles/b.md)",
                           "首段:0 概念位置:0")

    def test_image_and_code_links_do_not_count(self):
        self.assert_counts("![B](b.md) `[B](b.md)`", "```\n[B](b.md)\n```", "首段:0 概念位置:0")

    def test_self_link_does_not_count(self):
        self.assert_counts("[自己](/til/cards/a/)", "[自己](a.md)", "首段:0 概念位置:0")

    # 段落的切法
    def test_fence_heading_is_not_a_section(self):
        self.write("a.md", FM + "[B](b.md)\n\n```\n## 概念位置\n```\n\n## 概念位置\n\n[C](c.md)\n")
        out, _ = self.run_check()
        self.assertTrue(out["a.md"].startswith("OK\t"))

    def test_heading_argument_with_hashes_and_heading_with_anchor(self):
        self.write("a.md", card("[B](b.md)", "[B](b.md)", heading="概念位置 {#pos}"))
        out, _ = self.run_check()
        self.assertTrue(out["a.md"].startswith("OK\t"))
        out, _ = self.run_check(heading="## 概念位置")
        self.assertTrue(out["a.md"].startswith("OK\t"))

    def test_heading_with_regex_characters_matches_literally(self):
        self.assert_counts("[B](b.md)", "[B](b.md)", "首段:1 概念位置:1", heading="Position / context (x)")

    def test_toml_frontmatter_and_horizontal_rule(self):
        self.assert_counts("前文\n\n---\n\n後文 [B](b.md)", "[B](b.md)", "首段:1 概念位置:1",
                           fm="+++\ntitle = 'x'\n+++\n")

    # 判定與引數
    def test_missing_heading_is_nohead(self):
        self.write("a.md", card("[B](b.md)", "[B](b.md)", heading="概念的位置"))
        out, _ = self.run_check()
        self.assertTrue(out["a.md"].startswith("NOHEAD\t"))

    def test_zero_link_section_is_nolink(self):
        self.write("a.md", card("沒有連結", "[B](b.md)"))
        out, problems = self.run_check()
        self.assertTrue(out["a.md"].startswith("NOLINK\t"))
        self.assertEqual(problems, 1)

    def test_bare_name_and_slug_resolve_but_wrong_dir_path_does_not(self):
        self.write("a.md", card("[B](b.md)", "[B](b.md)"))
        lines, problems = nlc.check(self.d, ["a.md", "b", "other/dir/c.md"], "概念位置")
        self.assertEqual([l.split("\t")[0] for l in lines], ["OK", "NOLINK", "MISSING"])

    def test_no_files_checks_whole_dir_without_index(self):
        self.write("_index.md", card("x", None))
        self.write("a.md", card("[B](b.md)", "[B](b.md)"))
        lines, _ = nlc.check(self.d, [], "概念位置")
        self.assertEqual(sorted(l.split("\t")[1].rsplit("/", 1)[-1] for l in lines), ["a.md", "b.md", "c.md"])

    def test_main_exit_codes(self):
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        self.write("a.md", card("[B](b.md)", "[B](b.md)"))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(nlc.main([str(self.d), "a.md"]), 0)
            self.assertEqual(nlc.main([str(self.d), "nope.md"]), 1)
            self.assertEqual(nlc.main([str(self.d / "absent")]), 2)
            self.assertEqual(nlc.main([str(empty)]), 2)


if __name__ == "__main__":
    unittest.main()
