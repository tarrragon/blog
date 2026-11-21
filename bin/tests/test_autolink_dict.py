"""bin/autolink-dict 的測試。

每個測試在拋棄式 git repo 裡跑工具本身（subprocess）。案例取自本站卡片標題的實際寫法：
「英文（中文）」成對、只有英文、中文只有兩個字、同一個名字在兩個第一層資料夾各有一張、
同一個資料夾裡重複建卡、content/skills/ 的鏡像、draft 的卡。

跑法：python3 -m unittest discover -s bin/tests
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

BIN = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CONFIG = """\
[scopes]
backend = ["backend"]

[min_length]
han = 2
latin = 2

[names]
exclude = [
  "Index",
]
"""


def card(title, extra=""):
    return f'---\ntitle: "{title}"\ndate: 2026-01-01\n{extra}---\n\n正文\n'


class Repo:
    def __init__(self, files):
        self.dir = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)
        for rel, text in files.items():
            full = os.path.join(self.dir, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(text)

    def run(self, *args):
        return subprocess.run([os.path.join(BIN, "autolink-dict"), *args], cwd=self.dir, capture_output=True, text=True)

    def data(self):
        with open(os.path.join(self.dir, "data", "autolink_terms.json"), encoding="utf-8") as f:
            return json.load(f)

    def cleanup(self):
        shutil.rmtree(self.dir)


def site(**extra):
    files = {
        "data/autolink.toml": CONFIG,
        "content/backend/knowledge-cards/_index.md": card("卡片"),
        "content/backend/knowledge-cards/transaction.md": card("Transaction（交易）"),
        "content/backend/knowledge-cards/schema-drift.md": card("Schema Drift（結構漂移）"),
        "content/backend/knowledge-cards/orm.md": card("ORM", 'autolink_terms: ["物件關聯對映"]\n'),
        "content/backend/knowledge-cards/ci.md": card("CI"),
        "content/backend/knowledge-cards/index.md": card("Index（資料庫索引）"),
        "content/backend/knowledge-cards/retention.md": card("Retention（資料保留）"),
        "content/business/knowledge-cards/retention.md": card("Retention（留存）"),
        "content/backend/knowledge-cards/off.md": card("Quiet Card（安靜的卡）", "autolink: false\n"),
        "content/backend/knowledge-cards/draft.md": card("Draft Card", "draft: true\n"),
        "content/skills/x/knowledge-cards/mirror.md": card("Mirror Card"),
        "content/backend/article.md": card("文章"),
    }
    files.update(extra)
    return files


class AutolinkDictTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo(site())

    def tearDown(self):
        self.repo.cleanup()

    def terms(self):
        return {(t["name"], t["card"]) for t in self.repo.data()["terms"]}

    def excluded(self):
        return {e["name"]: e["reason"] for e in self.repo.data()["excluded"]}

    def test_pair_title_gives_both_names(self):
        r = self.repo.run()
        self.assertEqual(r.returncode, 0, r.stderr)
        t = self.terms()
        self.assertIn(("Transaction", "backend/knowledge-cards/transaction"), t)
        self.assertIn(("Schema Drift", "backend/knowledge-cards/schema-drift"), t)
        self.assertIn(("結構漂移", "backend/knowledge-cards/schema-drift"), t)

    def test_single_title_and_autolink_terms(self):
        self.repo.run()
        t = self.terms()
        self.assertIn(("ORM", "backend/knowledge-cards/orm"), t)
        self.assertIn(("物件關聯對映", "backend/knowledge-cards/orm"), t)

    def test_exclusion_reasons(self):
        self.repo.run()
        ex = self.excluded()
        self.assertEqual(ex["交易"], "short-han")
        self.assertEqual(ex["CI"], "short-latin")
        self.assertEqual(ex["Index"], "config")
        self.assertEqual(ex["Quiet Card"], "card-off")
        self.assertEqual(ex["安靜的卡"], "card-off")
        names = {n for n, _ in self.terms()}
        self.assertIn("資料庫索引", names)
        self.assertNotIn("Index", names)

    def test_same_name_in_two_modules_kept_for_both(self):
        self.repo.run()
        t = self.terms()
        self.assertIn(("Retention", "backend/knowledge-cards/retention"), t)
        self.assertIn(("Retention", "business/knowledge-cards/retention"), t)

    def test_same_name_twice_in_one_module_is_ambiguous(self):
        self.repo.cleanup()
        self.repo = Repo(site(**{"content/backend/01-database/knowledge-cards/tx.md": card("Transaction（資料庫交易）")}))
        self.repo.run()
        self.assertEqual(self.excluded()["Transaction"], "ambiguous")
        self.assertIn(("資料庫交易", "backend/01-database/knowledge-cards/tx"), self.terms())

    def test_skips_draft_skills_mirror_and_non_cards(self):
        self.repo.run()
        cards = {c for _, c in self.terms()}
        self.assertFalse(any("draft" in c or "mirror" in c or c.endswith("article") for c in cards))
        self.assertNotIn("backend/knowledge-cards/_index", cards)

    def test_check_detects_stale_and_counts_printed(self):
        r = self.repo.run("--check")
        self.assertEqual(r.returncode, 1)
        r = self.repo.run()
        self.assertIn("term(s)", r.stderr)
        self.assertIn("from 9 card(s)", r.stderr)  # 掃到的卡片檔（含 draft），不含 _index.md 與 skills 鏡像
        self.assertEqual(self.repo.run("--check").returncode, 0)

    def test_regenerate_is_stable(self):
        self.repo.run()
        first = self.repo.data()
        self.repo.run()
        self.assertEqual(first, self.repo.data())

    def test_report_lists_sections(self):
        r = self.repo.run("--report")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("short-han\t交易", r.stdout)
        self.assertIn("Retention\tbackend/knowledge-cards/retention business/knowledge-cards/retention", r.stdout)
        self.assertIn("Transaction\tbackend/knowledge-cards/transaction", r.stdout)

    def test_missing_config_exits_2(self):
        os.remove(os.path.join(self.repo.dir, "data", "autolink.toml"))
        r = self.repo.run()
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("term(s)", r.stderr)

    def test_bad_argument_exits_2(self):
        self.assertEqual(self.repo.run("--nope").returncode, 2)
        self.assertEqual(self.repo.run("--staged").returncode, 2)  # --staged 只跟 --check 一起用

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo.dir, check=True, capture_output=True)

    def test_staged_check_ignores_unstaged_cards(self):
        self.repo.run()
        self.git("add", "-A")
        self.assertEqual(self.repo.run("--check", "--staged").returncode, 0)
        # 另一個 session 在工作樹裡新增的卡，還沒 staged
        path = os.path.join(self.repo.dir, "content/backend/knowledge-cards/new.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(card("Brand New Card"))
        self.assertEqual(self.repo.run("--check").returncode, 1)
        self.assertEqual(self.repo.run("--check", "--staged").returncode, 0)
        # 這次 staged 了一張卡而沒有重產生詞典
        self.git("add", "content/backend/knowledge-cards/new.md")
        r = self.repo.run("--check", "--staged")
        self.assertEqual(r.returncode, 1)
        self.assertIn("git index", r.stderr)

    def test_with_builds_from_head_plus_listed_files(self):
        # HEAD 有詞典與全部卡
        self.repo.run()
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "base")
        # 另一個 session 的卡在工作樹裡、不屬於這次提交；這次提交自己的卡
        for name, title in (("other.md", "Other Session Card"), ("mine.md", "My New Card")):
            with open(os.path.join(self.repo.dir, "content/backend/knowledge-cards", name), "w", encoding="utf-8") as f:
                f.write(card(title))
        r = self.repo.run("--with", "content/backend/knowledge-cards/mine.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        names = {n for n, _ in self.terms()}
        self.assertIn("My New Card", names)
        self.assertNotIn("Other Session Card", names)
        # 照 bin/commit-files 的做法：只 stage 這次的卡與詞典，pre-commit 的檢查通過
        self.git("add", "content/backend/knowledge-cards/mine.md", "data/autolink_terms.json")
        self.assertEqual(self.repo.run("--check", "--staged").returncode, 0)
        # 對照：不用 --with 時，詞典會混進別人的卡，檢查不通過
        self.repo.run()
        self.git("add", "data/autolink_terms.json")
        self.assertEqual(self.repo.run("--check", "--staged").returncode, 1)

    def test_with_missing_file_counts_as_deleted_and_needs_paths(self):
        self.repo.run()
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "base")
        os.remove(os.path.join(self.repo.dir, "content/backend/knowledge-cards/orm.md"))
        self.repo.run("--with", "content/backend/knowledge-cards/orm.md")
        self.assertNotIn("ORM", {n for n, _ in self.terms()})
        self.assertEqual(self.repo.run("--with").returncode, 2)
        self.assertEqual(self.repo.run("--check", "--with", "x").returncode, 2)

    def test_unreadable_card_exits_2_not_1(self):
        path = os.path.join(self.repo.dir, "content/backend/knowledge-cards/bad.md")
        with open(path, "wb") as f:
            f.write(b"---\ntitle: \"\xff\xfe\"\n---\n")
        r = self.repo.run("--check")
        self.assertEqual(r.returncode, 2)
        self.assertIn("UTF-8", r.stderr)


if __name__ == "__main__":
    unittest.main()
