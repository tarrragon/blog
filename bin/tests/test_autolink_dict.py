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

[unlisted]
business = "測試用"
skills = "測試用"

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

    def test_prints_names_that_stop_being_linked(self):
        self.repo.run()
        r = self.repo.run()
        self.assertNotIn("不再自動連結", r.stderr)
        # 新卡跟既有卡同名：Transaction 變成 ambiguous，從 terms 消失
        path = os.path.join(self.repo.dir, "content/backend/01-database/knowledge-cards/tx.md")
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as f:
            f.write(card("Transaction（資料庫交易）"))
        r = self.repo.run("--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("不再自動連結的名字：Transaction", r.stderr)
        r = self.repo.run()
        self.assertIn("不再自動連結的名字：Transaction", r.stderr)

    def test_removed_names_compare_with_head(self):
        self.repo.run()
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "base")
        path = os.path.join(self.repo.dir, "content/backend/01-database/knowledge-cards/tx.md")
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as f:
            f.write(card("Transaction（資料庫交易）"))
        self.repo.run()
        # 第二次重產生：工作樹的詞典已經沒有 Transaction，跟 HEAD 比仍然印得出來
        r = self.repo.run()
        self.assertIn("不再自動連結的名字：Transaction", r.stderr)

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
        self.assertEqual(self.repo.run("--check", "--staged", "--with", "x").returncode, 2)
        # HEAD 與工作樹都沒有的路徑（打錯、或整份清單被當成一個參數）
        r = self.repo.run("--check", "--with", "content/backend/knowledge-cards/typo.md data/autolink.toml")
        self.assertEqual(r.returncode, 2)
        self.assertIn("都不存在", r.stderr)

    def test_check_with_compares_head_plus_listed_files(self):
        # session-edits-check 不帶 --staged 時用這個：詞典由 HEAD 加上這次的檔案決定
        self.repo.run()
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "base")
        mine = "content/backend/knowledge-cards/mine.md"
        for rel, title in (("content/backend/knowledge-cards/other.md", "Other Session Card"), (mine, "My New Card")):
            with open(os.path.join(self.repo.dir, rel), "w", encoding="utf-8") as f:
                f.write(card(title))
        dict_path = "data/autolink_terms.json"
        r = self.repo.run("--check", "--with", mine, dict_path)
        self.assertEqual(r.returncode, 1)
        self.assertIn("term(s)", r.stderr)  # 過期時也印計數
        # 清單沒列詞典：拿 HEAD 的詞典比對會誤判成過期，所以 exit 2
        r = self.repo.run("--check", "--with", mine)
        self.assertEqual(r.returncode, 2)
        self.assertIn("清單要含", r.stderr)
        self.assertEqual(self.repo.run("--check", "--with", mine, "./" + dict_path).returncode, 1)  # ./ 開頭也認得
        self.repo.run("--with", mine)
        r = self.repo.run("--check", "--with", mine, dict_path)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.repo.dir, ".git", "index.lock")))
        # 詞典裡混進別人的卡時對不上
        self.repo.run()
        self.assertEqual(self.repo.run("--check", "--with", mine, dict_path).returncode, 1)

    def test_derived_names_from_title_shapes(self):
        self.repo.cleanup()
        self.repo = Repo(
            site(
                **{
                    "content/backend/knowledge-cards/sli-slo.md": card("SLI / SLO"),
                    "content/backend/knowledge-cards/iac.md": card("Infrastructure as Code (IaC)"),
                    "content/backend/knowledge-cards/hit.md": card("Cache Hit / Miss"),
                    "content/backend/knowledge-cards/pubsub.md": card("Pub/Sub"),
                    "content/backend/knowledge-cards/asp.md": card("Average Selling Price，平均單價"),
                    "content/backend/knowledge-cards/mac.md": card("Mandatory Access Control（強制存取控制）：SELinux 與 AppArmor"),
                    "content/backend/knowledge-cards/bench.md": card("MMLU / HumanEval 等"),
                    "content/backend/knowledge-cards/hum.md": card("HumanEval"),
                }
            )
        )
        r = self.repo.run("--report")
        self.assertEqual(r.returncode, 0, r.stderr)
        t = self.terms()
        for name, slug in (
            ("SLI / SLO", "sli-slo"),  # 正式名字照收
            ("SLI", "sli-slo"),
            ("SLO", "sli-slo"),
            ("Infrastructure as Code", "iac"),
            ("IaC", "iac"),
            ("Cache Hit", "hit"),
            ("Pub/Sub", "pubsub"),
            ("Average Selling Price", "asp"),
            ("平均單價", "asp"),
            ("Mandatory Access Control", "mac"),
            ("強制存取控制", "mac"),
            ("MMLU", "bench"),
            ("HumanEval", "hum"),  # 衍生名字跟另一張卡的正式名字同名：正式名字優先，不判成 ambiguous
        ):
            self.assertIn((name, f"backend/knowledge-cards/{slug}"), t)
        names = {n for n, _ in t}
        self.assertNotIn("Miss", names)  # 一般英文單字不收
        self.assertEqual(self.excluded()["Miss"], "derived-word")  # 列進 excluded，autolink-gaps 才列得出
        self.assertNotIn("Pub", names)  # 沒有空白的斜線不拆
        self.assertNotIn(("HumanEval", "backend/knowledge-cards/bench"), t)
        self.assertNotIn("HumanEval", self.excluded())
        self.assertIn("backend/knowledge-cards/hit\tCache Hit\tMiss", r.stdout)
        self.assertIn("HumanEval\tbackend/knowledge-cards/bench", r.stdout)

    def test_shared_suffix_and_cross_folder_primary_wins(self):
        self.repo.cleanup()
        self.repo = Repo(
            site(
                **{
                    "content/backend/knowledge-cards/rh.md": card("Readiness / Health Check"),
                    "content/business/knowledge-cards/hc.md": card("Health Check（健康檢查）"),
                    "content/backend/knowledge-cards/topp.md": card("Top-K / Top-P Sampling"),
                }
            )
        )
        r = self.repo.run("--report")
        self.assertEqual(r.returncode, 0, r.stderr)
        t = self.terms()
        self.assertIn(("Readiness Check", "backend/knowledge-cards/rh"), t)
        self.assertIn(("Top-K Sampling", "backend/knowledge-cards/topp"), t)
        self.assertIn(("Top-K", "backend/knowledge-cards/topp"), t)
        # 衍生的 Health Check 跟另一個資料夾的正式名字同名：不收
        self.assertNotIn(("Health Check", "backend/knowledge-cards/rh"), t)
        self.assertIn(("Health Check", "business/knowledge-cards/hc"), t)
        self.assertIn("Health Check\tbackend/knowledge-cards/rh", r.stdout)

    def test_folder_registration(self):
        # 新增的第一層資料夾沒有登記
        self.repo.cleanup()
        self.repo = Repo(site(**{"content/newmod/a.md": card("A")}))
        r = self.repo.run()
        self.assertEqual(r.returncode, 2)
        self.assertIn("content/newmod/ 沒有登記", r.stderr)
        self.assertNotIn("term(s)", r.stderr)
        # 登記了不存在的資料夾（改名或收進大分類之後）
        self.repo.cleanup()
        self.repo = Repo(site(**{"data/autolink.toml": CONFIG.replace('backend = ["backend"]', 'backend = ["backend", "gone"]')}))
        r = self.repo.run("--check")
        self.assertEqual(r.returncode, 2)
        self.assertIn("gone 在 content/ 第一層找不到", r.stderr)
        # 同時列在兩處
        self.repo.cleanup()
        self.repo = Repo(site(**{"data/autolink.toml": CONFIG.replace('business = "測試用"', 'business = "測試用"\nbackend = "x"')}))
        r = self.repo.run()
        self.assertEqual(r.returncode, 2)
        self.assertIn("同時列在", r.stderr)

    def test_folder_registration_reads_index_when_staged(self):
        self.repo.run()
        self.git("add", "-A")
        self.assertEqual(self.repo.run("--check", "--staged").returncode, 0)
        os.makedirs(os.path.join(self.repo.dir, "content/newmod"))
        with open(os.path.join(self.repo.dir, "content/newmod/_index.md"), "w", encoding="utf-8") as f:
            f.write(card("新模組"))
        self.assertEqual(self.repo.run("--check", "--staged").returncode, 0)  # 還沒 staged 的資料夾不影響
        self.git("add", "content/newmod/_index.md")
        self.assertEqual(self.repo.run("--check", "--staged").returncode, 2)

    def test_with_folder_failure_says_config_was_read_from_head(self):
        self.repo.run()
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "base")
        os.makedirs(os.path.join(self.repo.dir, "content/newmod"))
        with open(os.path.join(self.repo.dir, "content/newmod/a.md"), "w", encoding="utf-8") as f:
            f.write(card("A"))
        with open(os.path.join(self.repo.dir, "data/autolink.toml"), "a", encoding="utf-8") as f:
            f.write('\n[unlisted.x]\n')  # 工作樹的設定改了，卻沒列進 --with
        r = self.repo.run("--with", "content/newmod/a.md")
        self.assertEqual(r.returncode, 2)
        self.assertIn("讀的是 HEAD 的 data/autolink.toml", r.stderr)

    def test_unreadable_card_exits_2_not_1(self):
        path = os.path.join(self.repo.dir, "content/backend/knowledge-cards/bad.md")
        with open(path, "wb") as f:
            f.write(b"---\ntitle: \"\xff\xfe\"\n---\n")
        r = self.repo.run("--check")
        self.assertEqual(r.returncode, 2)
        self.assertIn("UTF-8", r.stderr)


if __name__ == "__main__":
    unittest.main()
