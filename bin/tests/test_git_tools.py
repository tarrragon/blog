"""bin/changed-lines、bin/commit-files、bin/lint-delta、bin/push-main、bin/session-edits-check 的測試。

每個測試在拋棄式 git repo 裡跑工具本身（subprocess），不 import。案例取自規則檔多輪審查
實跑出的錯：新增行留著 `+` 前綴、漏掉 staged 或未 add 的新檔、index.lock 讓 `git add -N`
失敗、改名讓 staged 清單比對失敗、frontmatter 的 lint 問題都報在第 1 行、worktree 裡切不到
main、推送範圍混進別人的 commit、context 壓縮後對不出別人改的段落。

跑法：python3 -m unittest discover -s bin/tests
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

BIN = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MDTOOLS = os.path.join(BIN, "mdtools")


def sh(args, cwd, env=None, check=True):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env)
    if check and r.returncode != 0:
        raise AssertionError(f"{args} failed: {r.stdout}{r.stderr}")
    return r


CLAUDE_ENV = ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "SESSION_EDITS_TRANSCRIPT")


def tool(name, *args, cwd, env=None):
    # 測試本身常在 Claude Code 裡跑：拿掉它的環境變數，commit-files 才不會拿真的 transcript 比對
    base = {k: v for k, v in os.environ.items() if k not in CLAUDE_ENV}
    return subprocess.run([os.path.join(BIN, name), *args], cwd=cwd, capture_output=True, text=True, env={**base, **(env or {})})


def write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def new_repo(base):
    root = os.path.join(base, "repo")
    os.makedirs(root)
    sh(["git", "init", "-q", "-b", "main"], root)
    sh(["git", "config", "user.email", "t@example.com"], root)
    sh(["git", "config", "user.name", "t"], root)
    sh(["git", "config", "commit.gpgsign", "false"], root)
    sh(["git", "config", "core.hooksPath", ".githooks"], root)
    write(root, "a.md", "第一行\n第二行\n")
    write(root, "b.md", "乙\n")
    sh(["git", "add", "."], root)
    sh(["git", "commit", "-q", "-m", "init"], root)
    return root


def lock_path(root):
    return os.path.join(root, sh(["git", "rev-parse", "--git-path", "index.lock"], root).stdout.strip())


class Base(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="git-tools-test-")
        self.root = new_repo(self.base)

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)


class ChangedLines(Base):
    def test_staged_unstaged_and_new_file_without_prefix(self):
        write(self.root, "a.md", "第一行\n第二行\nstaged 的一行\n")
        sh(["git", "add", "a.md"], self.root)
        write(self.root, "a.md", "第一行\n第二行\nstaged 的一行\n還沒 staged 的一行\n")
        write(self.root, "new.md", "title: 為什麼？\n++ 計數器\n")
        r = tool("changed-lines", "a.md", "new.md", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.split("\n")
        self.assertIn("staged 的一行", lines)
        self.assertIn("還沒 staged 的一行", lines)
        self.assertIn("title: 為什麼？", lines)  # 行首沒有 +，^ 錨定的 pattern 對得到
        self.assertIn("++ 計數器", lines)  # 內容以 ++ 開頭的行沒有被當成標頭丟掉
        self.assertNotIn("+++", r.stdout)
        self.assertIn("changed-lines: 4 added line(s) from 2 file(s)", r.stderr)

    def test_new_file_works_while_index_is_locked(self):
        write(self.root, "new.md", "一\n二\n")
        open(lock_path(self.root), "w").close()
        r = tool("changed-lines", "new.md", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "一\n二\n")

    def test_subdirectory_paths_resolve_from_cwd(self):
        write(self.root, "sub/s.md", "原本的句子\n")
        sh(["git", "add", "."], self.root)
        sh(["git", "commit", "-q", "-m", "s"], self.root)
        write(self.root, "sub/s.md", "整句改寫成完全不同的內容\n")
        sub = os.path.join(self.root, "sub")
        r = tool("changed-lines", "--level", "s.md", cwd=sub)
        self.assertIn("level: 不是排版級", r.stdout, r.stdout + r.stderr)
        r = tool("changed-lines", "s.md", cwd=sub)
        self.assertEqual(r.stdout, "整句改寫成完全不同的內容\n")
        # 在子目錄裡寫成根目錄起算的路徑，指的是不存在的 sub/sub/s.md：要報錯，不能安靜地判成沒有改動
        r = tool("changed-lines", "--level", "sub/s.md", cwd=sub)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("排版級", r.stdout)

    def test_binary_new_file_counts_without_crash(self):
        with open(os.path.join(self.root, "img.png"), "wb") as f:
            f.write(b"\x89PNG\x00\x01\xff")
        r = tool("changed-lines", "--level", "img.png", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("不是排版級（新檔（二進位））", r.stdout)
        self.assertIn("from 1 file(s)", r.stderr)

    def test_permission_only_change_is_not_layout(self):
        os.chmod(os.path.join(self.root, "a.md"), 0o755)
        r = tool("changed-lines", "--level", "a.md", cwd=self.root)
        self.assertIn("level: 不是排版級", r.stdout)

    def test_missing_path_exits_2(self):
        r = tool("changed-lines", "nope.md", cwd=self.root)
        self.assertEqual(r.returncode, 2)

    def level(self, before, after):
        write(self.root, "c.md", before)
        sh(["git", "add", "c.md"], self.root)
        sh(["git", "commit", "-q", "-m", "c"], self.root)
        write(self.root, "c.md", after)
        r = tool("changed-lines", "--level", "c.md", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_level_punctuation_and_link_url_is_layout(self):
        out = self.level("甲，乙。見[文](/a/)\n", "甲、乙；見[文](/b/)\n")
        self.assertIn("level: 排版級", out)

    def test_level_single_substitution_is_layout_and_listed(self):
        out = self.level("布署完成\n", "部署完成\n")
        self.assertIn("level: 排版級", out)
        self.assertIn("錯字候選：布→部", out)

    def test_level_substitution_of_digit_negation_or_modal_is_wording(self):
        for before, after in [("exit 1 結束\n", "exit 3 結束\n"), ("會提交\n", "不提交\n"), ("先問使用者\n", "不問使用者\n")]:
            with self.subTest(before=before):
                out = self.level(before, after)
                self.assertIn("level: 不是排版級", out)

    def test_level_weight_outside_frontmatter_or_non_numeric_is_wording(self):
        out = self.level("正文\nweight: 3 次重試\n", "正文\nweight: 永遠不重試\n")
        self.assertIn("level: 不是排版級", out)
        out = self.level("---\ndate: 2026-01-01\n---\n", "---\ndate: 這裡寫了一整句新規則\n---\n")
        self.assertIn("level: 不是排版級", out)

    def test_level_inserted_character_is_wording(self):
        out = self.level("看內容\n", "查看內容\n")
        self.assertIn("level: 不是排版級", out)

    def test_level_deleted_sentence_is_wording(self):
        out = self.level("一\n二\n三\n", "一\n三\n")
        self.assertIn("level: 不是排版級", out)

    def test_level_frontmatter_weight_is_layout(self):
        out = self.level("---\nweight: 3\n---\n", "---\nweight: 30\n---\n")
        self.assertIn("level: 排版級", out)

    def test_level_new_file_is_wording(self):
        write(self.root, "n.md", "x\n")
        r = tool("changed-lines", "--level", "n.md", cwd=self.root)
        self.assertIn("n.md: 不是排版級（新檔）", r.stdout)


class CommitFiles(Base):
    def msg(self, text="m"):
        p = os.path.join(self.base, "msg.txt")
        with open(p, "w") as f:
            f.write(text)
        return p

    def committed(self):
        out = sh(["git", "show", "--name-only", "--no-renames", "-z", "--format=", "HEAD"], self.root).stdout
        return [p for p in out.replace("\n", "\0").split("\0") if p]

    def test_commits_only_listed_files_and_keeps_others_staging(self):
        write(self.root, "b.md", "別人改的\n")
        sh(["git", "add", "b.md"], self.root)  # 別的 session staged 的
        write(self.root, "a.md", "我改的\n")
        r = tool("commit-files", "-F", self.msg(), "a.md", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.committed(), ["a.md"])
        staged = sh(["git", "diff", "--cached", "--name-only"], self.root).stdout.split()
        self.assertEqual(staged, ["b.md"])  # 對方的 staging 還在，a.md 已對齊 HEAD

    def test_locked_shared_index_commits_and_asks_follow_up(self):
        write(self.root, "a.md", "我改的\n")
        open(lock_path(self.root), "w").close()
        r = tool("commit-files", "-F", self.msg(), "a.md", cwd=self.root)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("[FOLLOW-UP]", r.stdout)
        os.remove(lock_path(self.root))
        self.assertEqual(self.committed(), ["a.md"])

    def test_other_session_staged_same_file_is_not_reset(self):
        write(self.root, "a.md", "對方的版本\n")
        sh(["git", "add", "a.md"], self.root)
        write(self.root, "a.md", "我的版本\n")
        r = tool("commit-files", "-F", self.msg(), "a.md", cwd=self.root)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("其他版本", r.stdout)
        staged = sh(["git", "diff", "--cached", "--name-only"], self.root).stdout.split()
        self.assertEqual(staged, ["a.md"])

    def test_rename_lists_both_paths(self):
        sh(["git", "mv", "b.md", "c.md"], self.root)
        r = tool("commit-files", "-F", self.msg(), "b.md", "c.md", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sorted(self.committed()), ["b.md", "c.md"])

    def test_rename_listing_only_new_path_keeps_old_file(self):
        os.rename(os.path.join(self.root, "b.md"), os.path.join(self.root, "c.md"))
        r = tool("commit-files", "-F", self.msg(), "c.md", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)  # 只列新路徑：舊檔還在 HEAD，不會被刪
        self.assertEqual(self.committed(), ["c.md"])

    def test_non_ascii_and_space_paths(self):
        write(self.root, "中文 檔.md", "內容\n")
        r = tool("commit-files", "-F", self.msg(), "中文 檔.md", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.committed(), ["中文 檔.md"])

    def test_paths_relative_to_subdirectory(self):
        write(self.root, "sub/s.md", "新\n")
        r = tool("commit-files", "-F", self.msg(), "s.md", cwd=os.path.join(self.root, "sub"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.committed(), ["sub/s.md"])

    def test_own_earlier_staging_reports_how_to_check(self):
        write(self.root, "a.md", "v1\n")
        sh(["git", "add", "a.md"], self.root)
        write(self.root, "a.md", "v2\n")
        r = tool("commit-files", "-F", self.msg(), "a.md", cwd=self.root)
        self.assertEqual(r.returncode, 3)
        self.assertIn("git diff --cached HEAD -- a.md", r.stdout)

    def test_hooks_path_not_set_stops(self):
        os.makedirs(os.path.join(self.root, ".githooks"))
        sh(["git", "config", "--unset", "core.hooksPath"], self.root)
        write(self.root, "a.md", "我改的\n")
        r = tool("commit-files", "-F", self.msg(), "a.md", cwd=self.root)
        self.assertEqual(r.returncode, 2)
        self.assertIn("make install-hooks", r.stderr)

    def test_directory_and_unchanged_file_fail_without_commit(self):
        head = sh(["git", "rev-parse", "HEAD"], self.root).stdout
        os.makedirs(os.path.join(self.root, "d"))
        r = tool("commit-files", "-F", self.msg(), "d", cwd=self.root)
        self.assertEqual(r.returncode, 1)
        r = tool("commit-files", "-F", self.msg(), "a.md", cwd=self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("內容跟 HEAD 相同", r.stderr)
        self.assertEqual(sh(["git", "rev-parse", "HEAD"], self.root).stdout, head)


class LintDelta(Base):
    def setUp(self):
        # mdtools 沒有 build 時讓測試失敗，不跳過：跳過的測試印出來仍是 OK，等於沒有在測。
        self.assertTrue(os.access(MDTOOLS, os.X_OK), "bin/mdtools 沒有 build（在 scripts/mdtools 跑 go build -o ../../bin/mdtools .）")
        super().setUp()
        os.makedirs(os.path.join(self.root, "bin"))
        os.symlink(MDTOOLS, os.path.join(self.root, "bin", "mdtools"))

    def test_frontmatter_errors_on_line_one_are_told_apart(self):
        card = "content/report/x.md"
        write(self.root, card, "---\ntitle: 卡\ndescription: 說明\nweight: 1\n---\n\n正文。\n")
        sh(["git", "add", card], self.root)
        sh(["git", "commit", "-q", "-m", "card"], self.root)  # HEAD 缺 date
        write(self.root, card, "---\ntitle: 卡\nweight: 1\n---\n\n正文。\n")  # 這次又缺 description
        r = tool("lint-delta", card, cwd=self.root)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("missing required field: description", r.stdout)
        self.assertNotIn("missing required field: date", r.stdout)
        self.assertIn("lint-delta: 1 new (1 error), 1 existing, 1 file(s) linted, 0 skipped", r.stderr)

    def test_new_file_counts_everything_as_new(self):
        write(self.root, "content/report/y.md", "---\ntitle: 卡\n---\n\n正文。\n")
        r = tool("lint-delta", "content/report/y.md", cwd=self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn(", 0 existing, 1 file(s) linted", r.stderr)

    def test_staged_rename_compares_with_old_path(self):
        write(self.root, "content/posts/p.md", "---\ntitle: 文\n---\n\n# 標題\n")
        sh(["git", "add", "."], self.root)
        sh(["git", "commit", "-q", "-m", "p"], self.root)
        sh(["git", "mv", "content/posts/p.md", "content/posts/p2.md"], self.root)
        r = tool("lint-delta", "content/posts/p2.md", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("lint-delta: 0 new", r.stderr)

    def test_non_content_and_deleted_files_are_skipped(self):
        write(self.root, "content/report/z.md", "---\ntitle: 卡\ndescription: d\nweight: 2\ndate: 2026-01-01\n---\n\n正文。\n")
        sh(["git", "add", "."], self.root)
        sh(["git", "commit", "-q", "-m", "z"], self.root)
        os.remove(os.path.join(self.root, "content/report/z.md"))
        r = tool("lint-delta", "a.md", "content/report/z.md", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 file(s) linted, 2 skipped", r.stderr)


class PushMain(Base):
    def setUp(self):
        super().setUp()
        self.remote = os.path.join(self.base, "remote.git")
        sh(["git", "init", "-q", "--bare", "-b", "main", self.remote], self.base)
        sh(["git", "remote", "add", "origin", self.remote], self.root)
        sh(["git", "push", "-q", "-u", "origin", "main"], self.root)

    def commit(self, cwd, name):
        write(cwd, name, name + "\n")
        sh(["git", "add", name], cwd)
        sh(["git", "commit", "-q", "-m", name], cwd)
        return sh(["git", "rev-parse", "HEAD"], cwd).stdout.strip()

    def remote_head(self):
        return sh(["git", "rev-parse", "main"], self.remote).stdout.strip()

    def test_pushes_own_commits(self):
        c = self.commit(self.root, "x.md")
        r = tool("push-main", "--mine", c[:8], cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.remote_head(), c)

    def test_foreign_commit_stops_push(self):
        before = self.remote_head()
        self.commit(self.root, "other.md")  # 別的 session 的
        c = self.commit(self.root, "x.md")
        r = tool("push-main", "--mine", c, cwd=self.root)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("other.md", r.stdout)
        self.assertIn("[ASK-USER]", r.stdout)
        self.assertEqual(self.remote_head(), before)

    def test_foreign_commit_on_branch_leaves_main_unmoved(self):
        main_before = sh(["git", "rev-parse", "main"], self.root).stdout
        wt = os.path.join(self.base, "wt2")
        sh(["git", "worktree", "add", "-q", "-b", "feat2", wt], self.root)
        self.commit(wt, "other.md")
        c = self.commit(wt, "x.md")
        r = tool("push-main", "--mine", c, cwd=wt)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertEqual(sh(["git", "rev-parse", "main"], self.root).stdout, main_before)

    def test_detached_head_in_worktree_is_pushed(self):
        wt = os.path.join(self.base, "wtd")
        sh(["git", "worktree", "add", "-q", "--detach", wt], self.root)
        c = self.commit(wt, "d.md")
        r = tool("push-main", "--list-unpushed", cwd=wt)
        self.assertIn("d.md", r.stdout)
        r = tool("push-main", "--mine", c, cwd=wt)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.remote_head(), c)

    def test_from_worktree_fast_forwards_main_checked_out_elsewhere(self):
        wt = os.path.join(self.base, "wt")
        sh(["git", "worktree", "add", "-q", "-b", "feat", wt], self.root)
        c = self.commit(wt, "w.md")
        r = tool("push-main", "--mine", c, cwd=wt)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.remote_head(), c)
        self.assertEqual(sh(["git", "rev-parse", "HEAD"], self.root).stdout.strip(), c)
        self.assertIn("[CLEANUP]", r.stdout)
        self.assertIn("worktree remove", r.stdout)


AFTER = "2099-01-01T00:00:00.000Z"  # 晚於測試 repo 的任何 commit
BEFORE = "2000-01-01T00:00:00.000Z"  # 早於測試 repo 的任何 commit


class SessionEditsCheck(Base):
    def transcript(self, *entries):
        path = os.path.join(self.base, "t.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("not json\n")
            for ts, result in entries:
                f.write(json.dumps({"timestamp": ts, "toolUseResult": result}, ensure_ascii=False) + "\n")
        return path

    def edit(self, rel, old, new, replace_all=False):
        return {"filePath": os.path.join(self.root, rel), "oldString": old, "newString": new, "replaceAll": replace_all}

    def run_check(self, t, *files, cwd=None):
        return tool("session-edits-check", "--transcript", t, *files, cwd=cwd or self.root)

    def test_replayed_edits_match_worktree(self):
        write(self.root, "a.md", "第一行\n改過的第二行\n")
        r = self.run_check(self.transcript((AFTER, self.edit("a.md", "第二行", "改過的第二行"))), "a.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ok: a.md", r.stdout)
        self.assertIn("1 file(s) checked, 0 ask-user", r.stderr)

    def test_hunk_from_another_session_asks_user_with_diff(self):
        write(self.root, "a.md", "別人加的行\n第一行\n改過的第二行\n")
        r = self.run_check(self.transcript((AFTER, self.edit("a.md", "第二行", "改過的第二行"))), "a.md")
        self.assertEqual(r.returncode, 3)
        self.assertIn("[ASK-USER] a.md", r.stdout)
        self.assertIn("+別人加的行", r.stdout)

    def test_edits_before_last_commit_are_not_replayed(self):
        write(self.root, "a.md", "第一行\n第二行\n補的\n")
        t = self.transcript((BEFORE, self.edit("a.md", "第一行", "早就提交的")), (AFTER, self.edit("a.md", "第二行\n", "第二行\n補的\n")))
        r = self.run_check(t, "a.md")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_new_file_from_write_and_replace_all(self):
        write(self.root, "n.md", "乙乙\n")
        t = self.transcript(
            (AFTER, {"filePath": os.path.join(self.root, "n.md"), "type": "create", "content": "甲甲\n"}),
            (AFTER, self.edit("n.md", "甲", "乙", replace_all=True)),
        )
        r = self.run_check(t, "n.md")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_change_without_any_record_asks_user(self):
        write(self.root, "b.md", "用 sed 改的\n")
        r = self.run_check(self.transcript(), "b.md")
        self.assertEqual(r.returncode, 3)
        self.assertIn("transcript 裡沒有這個檔案", r.stdout)

    def test_old_string_missing_or_ambiguous_asks_user(self):
        write(self.root, "a.md", "第一行\n第二行\n")
        r = self.run_check(self.transcript((AFTER, self.edit("a.md", "不存在的字串", "x"))), "a.md")
        self.assertEqual(r.returncode, 3)
        self.assertIn("找不到", r.stdout)
        r = self.run_check(self.transcript((AFTER, self.edit("a.md", "行", "x"))), "a.md")
        self.assertIn("出現 2 次", r.stdout)

    def test_paths_relative_to_subdirectory(self):
        write(self.root, "sub/c.md", "丙\n")
        sh(["git", "add", "."], self.root)
        sh(["git", "commit", "-q", "-m", "c"], self.root)
        write(self.root, "sub/c.md", "丁\n")
        t = self.transcript((AFTER, self.edit("sub/c.md", "丙", "丁")))
        r = self.run_check(t, "c.md", cwd=os.path.join(self.root, "sub"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_missing_transcript_exits_2(self):
        r = self.run_check(os.path.join(self.base, "nope.jsonl"), "a.md")
        self.assertEqual(r.returncode, 2)

    def update(self, rel, hunks, original=None):
        return {"filePath": os.path.join(self.root, rel), "type": "update", "content": "（不讀全文）",
                "structuredPatch": hunks, "originalFile": original}

    def test_overwrite_replays_patch_not_full_content(self):
        write(self.root, "a.md", "第一行\n改寫的第二行\n")
        hunk = {"oldStart": 1, "oldLines": 2, "newStart": 1, "newLines": 2, "lines": [" 第一行", "-第二行", "+改寫的第二行"]}
        r = self.run_check(self.transcript((AFTER, self.update("a.md", [hunk]))), "a.md")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_overwrite_after_read_does_not_launder_another_sessions_line(self):
        # 別的 session 先在檔尾加了一行；本 session Read 之後 Write 全文，全文裡帶著那一行
        write(self.root, "a.md", "第一行\n改寫的第二行\n別人加的行\n")
        hunk = {"oldStart": 1, "oldLines": 2, "newStart": 1, "newLines": 2, "lines": [" 第一行", "-第二行", "+改寫的第二行"]}
        r = self.run_check(self.transcript((AFTER, self.update("a.md", [hunk]))), "a.md")
        self.assertEqual(r.returncode, 3)
        self.assertIn("+別人加的行", r.stdout)

    def test_original_file_differing_from_replay_asks_user(self):
        write(self.root, "a.md", "別人改的\n第二行\n改\n")
        e = self.edit("a.md", "第二行\n", "第二行\n改\n")
        e["originalFile"] = "別人改的\n第二行\n"
        r = self.run_check(self.transcript((AFTER, e)), "a.md")
        self.assertEqual(r.returncode, 3)
        self.assertIn("transcript 解釋不了的改動", r.stdout)
        # 外來的內容印成 +，不是 -：使用者照這份 diff 判斷別人加了什麼
        self.assertIn("+別人改的", r.stdout)
        self.assertNotIn("-別人改的", r.stdout)
        self.assertIn("這個檔案要提交的整份改動", r.stdout)

    def test_transcript_of_another_session_exits_2(self):
        t = os.path.join(self.base, "other.jsonl")
        write(self.base, "other.jsonl", json.dumps({"sessionId": "OTHER", "timestamp": AFTER, "toolUseResult": self.edit("b.md", "乙", "丙")}) + "\n")
        write(self.root, "b.md", "丙\n")
        r = tool("session-edits-check", "--transcript", t, "b.md", cwd=self.root, env={"CLAUDE_CODE_SESSION_ID": "MINE"})
        self.assertEqual(r.returncode, 2)
        self.assertIn("不是這個 session", r.stderr)

    def test_directory_and_unparsable_transcript_exit_2(self):
        r = self.run_check(self.transcript(), ".")
        self.assertEqual(r.returncode, 2)
        self.assertIn("清單裡有目錄", r.stderr)
        t = os.path.join(self.base, "fmt.jsonl")
        call = {"type": "tool_use", "name": "Edit", "input": {}}
        write(self.base, "fmt.jsonl", json.dumps({"timestamp": AFTER, "message": {"content": [call]}}) + "\n")
        r = self.run_check(t, "a.md")
        self.assertEqual(r.returncode, 2)
        self.assertIn("格式跟這支工具讀的欄位對不上", r.stderr)

    def test_staged_compares_index_not_worktree(self):
        write(self.root, "a.md", "第一行\n改過的第二行\n")
        idx = os.path.join(self.base, "index")
        env = dict(os.environ, GIT_INDEX_FILE=idx)
        sh(["git", "read-tree", "HEAD"], self.root, env=env)
        sh(["git", "add", "a.md"], self.root, env=env)
        write(self.root, "a.md", "第一行\n改過的第二行\n檢查之後別人加的\n")  # 進工作樹、沒進 index
        t = self.transcript((AFTER, self.edit("a.md", "第二行", "改過的第二行")))
        r = tool("session-edits-check", "--staged", "--transcript", t, "a.md", cwd=self.root, env={"GIT_INDEX_FILE": idx})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = tool("session-edits-check", "--transcript", t, "a.md", cwd=self.root)
        self.assertEqual(r.returncode, 3)

    def test_commit_files_runs_the_check_in_claude_code(self):
        msg = os.path.join(self.base, "msg")
        write(self.base, "msg", "m\n")
        t = self.transcript((AFTER, self.edit("a.md", "第二行", "改過的第二行")))
        cc = {"CLAUDECODE": "1", "SESSION_EDITS_TRANSCRIPT": t}
        write(self.root, "a.md", "別人加的\n第一行\n改過的第二行\n")
        r = tool("commit-files", "-F", msg, "a.md", cwd=self.root, env=cc)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("[ASK-USER] a.md", r.stdout)
        self.assertEqual(sh(["git", "log", "--oneline"], self.root).stdout.count("\n"), 1)
        r = tool("commit-files", "--skip-session-check", "-F", msg, "a.md", cwd=self.root, env=cc)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        write(self.root, "b.md", "丙\n")
        t2 = self.transcript((AFTER, self.edit("b.md", "乙", "丙")))
        r = tool("commit-files", "-F", msg, "b.md", cwd=self.root, env={"CLAUDECODE": "1", "SESSION_EDITS_TRANSCRIPT": t2})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_subagent_transcript_is_replayed(self):
        t = self.transcript()
        write(self.base, "t/subagents/agent-x.jsonl", json.dumps({"timestamp": AFTER, "toolUseResult": self.edit("b.md", "乙", "丙")}) + "\n")
        write(self.root, "b.md", "丙\n")
        r = self.run_check(t, "b.md")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_symlink_retarget_and_mistyped_path_ask_user(self):
        write(self.root, "d1/x.md", "同\n")
        write(self.root, "d2/x.md", "同\n")
        os.symlink("d1/x.md", os.path.join(self.root, "link"))
        sh(["git", "add", "."], self.root)
        sh(["git", "commit", "-q", "-m", "link"], self.root)
        os.remove(os.path.join(self.root, "link"))
        os.symlink("d2/x.md", os.path.join(self.root, "link"))
        r = self.run_check(self.transcript(), "link", "nosuch.md")
        self.assertEqual(r.returncode, 3)
        self.assertIn("[ASK-USER] link：檔案模式變了或這是 symlink", r.stdout)
        self.assertIn("[ASK-USER] nosuch.md：HEAD 與要提交的內容裡都沒有", r.stdout)
        self.assertIn("2 file(s) checked, 2 ask-user", r.stderr)


if __name__ == "__main__":
    unittest.main()
