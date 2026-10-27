"""bin/content-move、bin/empty-sections 與 bin/alias-check 的測試。

每個測試在拋棄式 git repo 裡跑工具本身（subprocess），不 import。案例取自本站實際的寫法：
還有大量相對連結、posts/work-log 這類分類的網址走 hugo.toml 的 :slug、aliases 寫成單行陣列、
程式碼區塊裡有範例路徑、有前綴相同的資料夾名（/infra/ 與 /infra-notes/）、draft 頁面不會列出。
相對連結以頁面的網址為基準解析（/backend/cards/waf/ 的 ../../ 是 /backend/），測試資料照這個寫。

跑法：python3 -m unittest discover -s bin/tests
"""

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest

BIN = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

HUGO = '[permalinks]\n  work-log = "/work-log/:slug/"\n\n[[menu.main]]\n  url = "/infra/"\n'


def page(title, body="", extra=""):
    return f"---\ntitle: \"{title}\"\ndate: 2026-01-01\n{extra}---\n\n{body}\n"


class Repo:
    def __init__(self, files):
        self.dir = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)
        for rel, text in files.items():
            self.write(rel, text)

    def write(self, rel, text):
        full = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(text) if text.startswith("\n") else text)

    def read(self, rel):
        with open(os.path.join(self.dir, rel), encoding="utf-8") as f:
            return f.read()

    def exists(self, rel):
        return os.path.exists(os.path.join(self.dir, rel))

    def run(self, tool, *args):
        return subprocess.run([os.path.join(BIN, tool), *args], cwd=self.dir, capture_output=True, text=True)

    def cleanup(self):
        shutil.rmtree(self.dir)


def site():
    return {
        "hugo.toml": HUGO,
        "content/_index.md": page("首頁", "- [Infra](/infra/)"),
        "content/devops/_index.md": page("DevOps", "## 三個階段\n\n- [Infra](/infra/)"),
        "content/infra/_index.md": page("Infra", "- [網路](./net/)"),
        "content/infra/net/_index.md": page("網路"),
        "content/infra/net/vpc.md": page(
            "VPC",
            "見 [IAM](../iam/)、[卡](/backend/cards/waf/)、[本模組](../)。\n\n"
            "```bash\ncurl /infra/net/vpc/\n```",
            'aliases: ["/infra/old-vpc/"]\n',
        ),
        "content/infra/net/iam.md": page("IAM", "連回 [VPC](../vpc/)。"),
        "content/infra-notes/_index.md": page("筆記", "- [另一個](/infra-notes/x/)"),
        "content/infra-notes/x.md": page("X"),
        "content/backend/_index.md": page("Backend"),
        "content/backend/cards/waf.md": page(
            "WAF",
            "見 [VPC](/infra/net/vpc/#subnet)、[VPC 無斜線](/infra/net/vpc)、"
            "[相對](../../../infra/net/iam/)。\n\n[ref]: /infra/net/\n\n內文提到 /infra/net/ 這個路徑。",
        ),
        "content/work-log/_index.md": page("Work log"),
        "content/work-log/bug.md": page("Bug", "見 [VPC](/infra/net/vpc/)。", "slug: bug\n"),
        "docs/rules/x.md": "見 [VPC](/infra/net/vpc/) 與 `content/infra/net/vpc.md`、[檔案](../../bin/x)。\n",
    }


class ContentMoveTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo(site())

    def tearDown(self):
        self.repo.cleanup()

    def test_dry_run_changes_nothing_and_prints_counts(self):
        r = self.repo.run("content-move", "content/infra", "content/devops/infra")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("(dry-run)", r.stderr)
        self.assertIn("4 page(s) moved", r.stderr)
        self.assertTrue(self.repo.exists("content/infra/net/vpc.md"))
        self.assertFalse(self.repo.exists("content/devops/infra"))
        self.assertIn("(/infra/net/vpc/#subnet)", self.repo.read("content/backend/cards/waf.md"))

    def test_apply_moves_directory_and_rewrites_links(self):
        r = self.repo.run("content-move", "--apply", "content/infra", "content/devops/infra")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.repo.exists("content/infra"))
        waf = self.repo.read("content/backend/cards/waf.md")
        self.assertIn("(/devops/infra/net/vpc/#subnet)", waf)  # anchor 保留
        self.assertIn("(/devops/infra/net/vpc)", waf)  # 原本沒有尾斜線，改完也沒有
        self.assertIn("(/devops/infra/net/iam/)", waf)  # 指進來的相對連結改成新網址
        self.assertIn("[ref]: /devops/infra/net/", waf)  # reference 定義
        self.assertIn("內文提到 /infra/net/ 這個路徑", waf)  # 連結以外的文字不改
        self.assertIn("(/devops/infra/net/vpc/)", self.repo.read("content/work-log/bug.md"))
        self.assertIn("(/devops/infra/)", self.repo.read("content/_index.md"))

    def test_moved_page_relative_links_become_absolute(self):
        self.repo.run("content-move", "--apply", "content/infra", "content/devops/infra")
        vpc = self.repo.read("content/devops/infra/net/vpc.md")
        self.assertIn("[IAM](/devops/infra/net/iam/)", vpc)  # 指向一起搬的頁面
        self.assertIn("[卡](/backend/cards/waf/)", vpc)  # 絕對連結指向別處，不動
        self.assertIn("[本模組](/devops/infra/net/)", vpc)
        self.assertIn("curl /infra/net/vpc/", vpc)  # 程式碼區塊不動
        self.assertIn("[VPC](/devops/infra/net/vpc/)", self.repo.read("content/devops/infra/net/iam.md"))

    def test_aliases_added_and_appended(self):
        self.repo.run("content-move", "--apply", "content/infra", "content/devops/infra")
        vpc = self.repo.read("content/devops/infra/net/vpc.md")
        self.assertIn('aliases: ["/infra/old-vpc/", "/infra/net/vpc/"]', vpc)
        self.assertIn('aliases: ["/infra/net/"]', self.repo.read("content/devops/infra/net/_index.md"))
        self.assertIn('aliases: ["/infra/"]', self.repo.read("content/devops/infra/_index.md"))

    def test_link_text_equal_to_old_url_follows(self):
        self.repo.write("content/backend/b.md", page("B", "見 [/infra/net/](/infra/net/) 與 [網路](/infra/net/)。"))
        self.repo.run("content-move", "--apply", "content/infra", "content/devops/infra")
        b = self.repo.read("content/backend/b.md")
        self.assertIn("[/devops/infra/net/](/devops/infra/net/)", b)
        self.assertIn("[網路](/devops/infra/net/)", b)

    def test_lookalike_prefix_untouched(self):
        self.repo.run("content-move", "--apply", "content/infra", "content/devops/infra")
        self.assertIn("(/infra-notes/x/)", self.repo.read("content/infra-notes/_index.md"))

    def test_docs_absolute_rewritten_relative_untouched_and_residual_reported(self):
        r = self.repo.run("content-move", "--apply", "content/infra", "content/devops/infra")
        doc = self.repo.read("docs/rules/x.md")
        self.assertIn("[VPC](/devops/infra/net/vpc/)", doc)
        self.assertIn("[檔案](../../bin/x)", doc)
        self.assertIn("docs/rules/x.md: 1", r.stdout)  # content/infra/net/vpc.md 的文字
        self.assertIn("hugo.toml: 1", r.stdout)  # 選單的 url
        self.assertIn("content/backend/cards/waf.md: 1", r.stdout)  # 正文提到的路徑
        residual = r.stdout.split("殘留")[1]
        self.assertIn("content/devops/infra/net/vpc.md: 1", residual)  # 程式碼區塊那一行；aliases 不算
        self.assertNotIn("content/devops/infra/_index.md", residual)  # 只有 aliases 提到舊網址

    def test_links_in_claude_dir_are_reported_as_residual(self):
        self.repo.write(".claude/skills/x/SKILL.md", "見 [a](/infra/net/vpc/)\n")
        r = self.repo.run("content-move", "content/infra", "content/devops/infra")
        self.assertIn(".claude/skills/x/SKILL.md: 1", r.stdout)

    def test_skill_mirror_not_rewritten_but_reported(self):
        self.repo.write("content/skills/x/skill.md", page("X", "見 [a](/infra/net/vpc/)"))
        r = self.repo.run("content-move", "--apply", "content/infra", "content/devops/infra")
        self.assertIn("(/infra/net/vpc/)", self.repo.read("content/skills/x/skill.md"))
        self.assertIn("content/skills/x/skill.md: 1", r.stdout.split("殘留")[1])

    def test_manifest_lists_old_new_and_rewritten(self):
        r = self.repo.run("content-move", "--apply", "--manifest", "m.txt", "content/infra", "content/devops/infra")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.repo.read("m.txt").splitlines()
        self.assertIn("content/infra/net/vpc.md", lines)  # 舊路徑（刪除）
        self.assertIn("content/devops/infra/net/vpc.md", lines)  # 新路徑
        self.assertIn("content/backend/cards/waf.md", lines)  # 改寫連結的檔案
        self.assertNotIn("content/infra-notes/x.md", lines)  # 沒碰到的檔案

    def test_residual_finds_baseurl_prefixed_urls_and_any_tracked_file(self):
        self.repo.write("hugo.toml", "baseURL = 'https://x.github.io/blog/'\n" + HUGO)
        self.repo.write("README.md", "見 [infra](./content/infra/)\n")
        self.repo.write("tests/e2e.spec.ts", "page.goto('/blog/infra/net/vpc/')\n")
        self.repo.write("content/backend/c.md", page("C", "```bash\ncurl https://x.github.io/blog/infra/net/\n```"))
        r = self.repo.run("content-move", "content/infra", "content/devops/infra")
        residual = r.stdout.split("殘留")[1]
        self.assertIn("README.md: 1", residual)
        self.assertIn("tests/e2e.spec.ts: 1", residual)
        self.assertIn("content/backend/c.md: 1", residual)

    def test_manifest_not_written_on_dry_run(self):
        self.repo.run("content-move", "--manifest", "m.txt", "content/infra", "content/devops/infra")
        self.assertFalse(self.repo.exists("m.txt"))

    def test_moving_back_drops_alias_equal_to_new_url(self):
        self.repo.run("content-move", "--apply", "content/infra", "content/devops/infra")
        r = self.repo.run("content-move", "--apply", "content/devops/infra", "content/infra")
        self.assertEqual(r.returncode, 0, r.stderr)
        vpc = self.repo.read("content/infra/net/vpc.md")
        self.assertIn('aliases: ["/infra/old-vpc/", "/devops/infra/net/vpc/"]', vpc)
        self.assertIn("移除了等於自己新網址的 alias", r.stdout)
        self.assertEqual(self.repo.run("alias-check").returncode, 0)

    def test_single_file_out_of_permalink_section(self):
        r = self.repo.run("content-move", "--apply", "content/work-log/bug.md", "content/devops/bug.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('aliases: ["/work-log/bug/"]', self.repo.read("content/devops/bug.md"))

    def test_link_to_permalink_page_rewritten(self):
        self.repo.write("content/backend/a.md", page("A", "見 [bug](/work-log/bug/)。"))
        self.repo.run("content-move", "--apply", "content/work-log/bug.md", "content/devops/bug.md")
        self.assertIn("(/devops/bug/)", self.repo.read("content/backend/a.md"))

    def test_rejects_existing_dest_and_dest_inside_src(self):
        r = self.repo.run("content-move", "content/infra", "content/devops")
        self.assertEqual(r.returncode, 2)
        self.assertIn("dest 已經存在", r.stderr)
        r = self.repo.run("content-move", "content/infra", "content/infra/net/x")
        self.assertEqual(r.returncode, 2)

    def test_warns_when_new_parent_has_no_index(self):
        r = self.repo.run("content-move", "content/infra", "content/platform/infra")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("content/platform/ 沒有 _index.md", r.stdout)


class EmptySectionsTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo(site())

    def tearDown(self):
        self.repo.cleanup()

    def test_index_only_section_reported(self):
        r = self.repo.run("empty-sections")
        self.assertEqual(r.returncode, 1, r.stderr)
        lines = r.stdout.splitlines()
        self.assertIn("content/devops/  body=2  DevOps", lines)
        self.assertEqual(len(lines), 1, r.stdout)
        self.assertNotIn("content/infra/net/", r.stdout)  # 有文章
        self.assertNotIn("content/infra/  ", r.stdout)  # 有子分類
        self.assertNotIn("content/backend/  ", r.stdout)  # 文章在沒有 _index 的 cards/ 底下，往上算
        self.assertNotIn("content/work-log/", r.stdout)
        self.assertIn("section(s) scanned", r.stderr)

    def test_draft_only_section_is_empty(self):
        self.repo.write("content/infra-notes/x.md", page("X", extra="draft: true\n"))
        r = self.repo.run("empty-sections", "content/infra-notes")
        self.assertEqual(r.returncode, 1)
        self.assertIn("content/infra-notes/  body=1", r.stdout)

    def test_build_list_never_is_empty(self):
        self.repo.write("content/infra-notes/x.md", page("X", extra="build:\n  list: never\n"))
        r = self.repo.run("empty-sections", "content/infra-notes")
        self.assertEqual(r.returncode, 1)

    def test_scope_without_empty_exits_zero(self):
        r = self.repo.run("empty-sections", "content/infra")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 empty of 2 section(s)", r.stderr)

    def test_bad_path_exits_two(self):
        r = self.repo.run("empty-sections", "content/nope")
        self.assertEqual(r.returncode, 2)


class AliasCheckTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo(site())

    def tearDown(self):
        self.repo.cleanup()

    def test_no_collision_after_move(self):
        self.repo.run("content-move", "--apply", "content/infra", "content/devops/infra")
        r = self.repo.run("alias-check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 collision(s)", r.stderr)

    def test_alias_equal_to_page_url(self):
        self.repo.write("content/backend/c.md", page("C", extra='aliases: ["/infra/net/iam/"]\n'))
        r = self.repo.run("alias-check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("/infra/net/iam/\t等於 content/infra/net/iam.md", r.stdout)

    def test_yaml_list_aliases_are_read(self):
        self.repo.write("content/backend/c.md", page("C", extra='aliases:\n  - "/infra/net/vpc/"\n'))
        r = self.repo.run("alias-check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("/infra/net/vpc/\t等於", r.stdout)

    def test_same_alias_declared_twice(self):
        self.repo.write("content/backend/c.md", page("C", extra='aliases: ["/infra/old-vpc/"]\n'))
        r = self.repo.run("alias-check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("/infra/old-vpc/\t被兩頁以上宣告", r.stdout)


if __name__ == "__main__":
    unittest.main()
