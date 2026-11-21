"""bin/rule-route 與 .claude/hooks/rule_read_guard.py 的測試。"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
TOOL = os.path.join(ROOT, "bin", "rule-route")
HOOK = os.path.join(ROOT, ".claude", "hooks", "rule_read_guard.py")
RULE = lambda n: os.path.join(ROOT, "docs", "rules", f"{n}.md")
SKILL_RULES = ["skills", "sentences", "writing-process", "review"]


def route(*args, cwd=ROOT):
    return subprocess.run([sys.executable, "-I", TOOL, *args], capture_output=True, text=True, cwd=cwd)


def read_call(i, path, **extra):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": f"t{i}", "name": "Read", "input": {"file_path": path, **extra}}]}}


def read_result(i, error=False):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": f"t{i}", "content": "x", "is_error": error}]}}


def reads(names, start=0, base=None):
    out = []
    for i, n in enumerate(names, start):
        path = os.path.join(base, "docs", "rules", f"{n}.md") if base else RULE(n)
        out += [read_call(i, path), read_result(i)]
    return out


COMPACT = {"type": "system", "subtype": "compact_boundary", "content": "Conversation compacted"}
MICROCOMPACT = {"type": "system", "subtype": "microcompact_boundary", "content": "x"}


def route_table():
    scope = {"__name__": "rule_route", "__file__": TOOL}
    with open(TOOL, encoding="utf-8") as f:
        exec(compile(f.read(), TOOL, "exec"), scope)
    return scope["ROUTES"]


class RuleRouteTest(unittest.TestCase):
    def lines(self, *args, **kw):
        r = route(*args, **kw)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.split()

    def test_content_path(self):
        got = self.lines("content/work-log/not-yet-created.md")
        self.assertEqual(len(got), 6)
        self.assertIn("docs/rules/content-folders.md", got)

    def test_rule_files_include_authoring(self):
        for p in ("AGENTS.md", "CLAUDE.md", "docs/rules/remote.md", "bin/rule-route"):
            got = self.lines(p)
            self.assertIn("docs/rules/rule-authoring.md", got)
            self.assertIn("docs/rules/review.md", got)

    def test_exact_path_does_not_match_as_prefix(self):
        self.assertEqual(self.lines("bin/skill-mirror-other"), ["docs/rules/rule-authoring.md"])
        self.assertEqual(self.lines("hugo.toml.bak"), [])

    def test_directory_argument_lists_rules_under_it(self):
        for p in ("content", "content/", "content/backend"):
            self.assertIn("docs/rules/content-folders.md", self.lines(p), p)
        self.assertIn("docs/rules/rule-authoring.md", self.lines("docs"))
        self.assertIn("docs/rules/skills.md", self.lines(".claude"))
        everything = {f"docs/rules/{n}.md" for _, files in route_table() for n in files}
        self.assertEqual(set(self.lines(".")), everything)

    def test_case_insensitive(self):
        self.assertEqual(len(self.lines("Content/x.md")), 6)
        self.assertIn("docs/rules/rule-authoring.md", self.lines("AGENTS.MD"))

    def test_bin_tools_hooks_and_settings_route_to_authoring(self):
        self.assertIn("docs/rules/rule-authoring.md", self.lines("bin/commit-files"))
        self.assertIn("docs/rules/claude-code.md", self.lines(".claude/hooks/ssh_guard.py"))
        self.assertIn("docs/rules/claude-code.md", self.lines(".claude/settings.json"))

    def test_every_route_name_is_printed(self):
        for prefixes, files in route_table():
            path = prefixes[0] + "x.md" if prefixes[0].endswith("/") else prefixes[0]
            got = self.lines(path)
            for name in files:
                self.assertIn(f"docs/rules/{name}.md", got)

    def test_worktree_path_routes_from_its_own_root(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            os.makedirs(os.path.join(d, "docs", "rules"))
            self.assertEqual(len(self.lines(os.path.join(d, "content", "new", "a.md"))), 6)

    def test_other_git_repo_needs_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            self.assertEqual(self.lines(os.path.join(d, "content", "a.md")), [])

    def test_symlinked_skill_path_resolves(self):
        self.assertEqual(self.lines(".agents/skills/x/SKILL.md"), self.lines(".claude/skills/x/SKILL.md"))

    def test_union_has_no_duplicates(self):
        got = self.lines("content/a.md", ".claude/skills/x/SKILL.md")
        self.assertEqual(len(got), len(set(got)))
        self.assertIn("docs/rules/skills.md", got)

    def test_relative_path_uses_cwd(self):
        self.assertEqual(self.lines("../hugo.toml", cwd=os.path.join(ROOT, "bin")), ["docs/rules/markdown.md"])

    def test_outside_repo_needs_nothing(self):
        r = route("/etc/hosts")
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertIn("1 path(s), 0 rule file(s)", r.stderr)

    def test_every_routed_file_exists(self):
        for name in {n for _, files in route_table() for n in files}:
            self.assertTrue(os.path.exists(RULE(name)), name)

    def test_no_path_is_usage_error(self):
        self.assertEqual(route().returncode, 2)


class EntryRouteTableTest(unittest.TestCase):
    def test_entry_table_matches_routes(self):
        with open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8") as f:
            text = f.read()
        start = text.index("路徑表（")
        rows = []
        for line in text[start:].splitlines()[1:]:
            if rows and not line.startswith("- "):
                break
            if line.startswith("- "):
                paths, files = line[2:].split("：", 1)
                rows.append((tuple(re.findall(r"`([^`]+)`", paths)), tuple(re.findall(r"`([^`]+)`", files))))
        self.assertEqual(rows, [(tuple(p), tuple(f)) for p, f in route_table()])


class CheckStagedTest(unittest.TestCase):
    ENTRY = "路徑表（x）：\n\n- `content/`：`writing`\n\n後文\n"
    TOOL = 'ROUTES = ((("content/",), ("writing",)),)\n'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        self.put("AGENTS.md", self.ENTRY)
        self.put("bin/rule-route", self.TOOL)
        self.put("docs/rules/writing.md", "x\n")

    def put(self, rel, text):
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        subprocess.run(["git", "add", rel], cwd=self.repo, check=True)

    def check(self):
        return route("--check-staged", cwd=self.repo)

    def test_consistent_index_passes(self):
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("checked 1 rule file(s), 0 problem(s)", r.stderr)

    def test_table_mismatch_fails(self):
        self.put("AGENTS.md", self.ENTRY.replace("`writing`", "`markdown`"))
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("路徑表", r.stderr)

    def test_oversized_entry_fails(self):
        self.put("AGENTS.md", self.ENTRY + "x" * 14336)
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("上限", r.stderr)

    def test_oversized_rule_file_fails(self):
        self.put("docs/rules/writing.md", "x" * (60 * 1024))
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("docs/rules/writing.md", r.stderr)

    def test_route_to_a_file_missing_from_the_index_fails(self):
        self.put("AGENTS.md", self.ENTRY.replace("`writing`", "`gone`"))
        self.put("bin/rule-route", self.TOOL.replace('"writing"', '"gone"'))
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("docs/rules/gone.md", r.stderr)

    def test_reads_index_not_worktree(self):
        with open(os.path.join(self.repo, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("另一個 session 還沒 staged 的內容\n")
        self.assertEqual(self.check().returncode, 0)


class RuleSizeLimitTest(unittest.TestCase):
    def test_entry_stays_under_its_size_limit(self):
        self.assertLess(os.path.getsize(os.path.join(ROOT, "AGENTS.md")), 14336)

    def test_every_rule_file_fits_one_read(self):
        # Read 對超過字數上限的檔案回傳截斷的內容而不報錯，hook 分辨不出來
        files = glob.glob(os.path.join(ROOT, "docs", "rules", "*.md"))
        self.assertTrue(files)
        for f in files:
            self.assertLess(os.path.getsize(f), 60 * 1024, f)


class HookRegistrationTest(unittest.TestCase):
    def test_guard_covers_write_tools_and_bash(self):
        with open(os.path.join(ROOT, ".claude", "settings.json"), encoding="utf-8") as f:
            entries = json.load(f)["hooks"]["PreToolUse"]
        matchers = [e["matcher"] for e in entries if any("rule_read_guard" in h["command"] for h in e["hooks"])]
        self.assertTrue(matchers)
        covered = {tool for m in matchers for tool in m.split("|")}
        self.assertLessEqual({"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"}, covered)


class RuleReadGuardTest(unittest.TestCase):
    TARGET = os.path.join(ROOT, ".claude", "skills", "x", "SKILL.md")

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.transcript = os.path.join(self.dir.name, "s.jsonl")

    def write(self, entries, path=None):
        with open(path or self.transcript, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def call(self, payload):
        payload = {"transcript_path": self.transcript, "cwd": ROOT, **payload}
        r = subprocess.run([sys.executable, "-I", HOOK], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["hookSpecificOutput"] if r.stdout.strip() else {}

    def run_hook(self, tool="Edit", target=None, **extra):
        return self.call({"tool_name": tool, "tool_input": {"file_path": target or self.TARGET}, **extra})

    def run_bash(self, command):
        return self.call({"tool_name": "Bash", "tool_input": {"command": command}})

    def assertDenied(self, out, *names):
        self.assertEqual(out.get("permissionDecision"), "deny", out)
        for n in names:
            self.assertIn(f"{n}.md", out["permissionDecisionReason"])

    def assertAllowed(self, out):
        self.assertNotIn("permissionDecision", out)

    def test_denies_when_nothing_read(self):
        self.write([])
        self.assertDenied(self.run_hook(), *SKILL_RULES)

    def test_deny_reason_asks_to_revise_the_content(self):
        self.write([])
        self.assertIn("改寫這次的內容", self.run_hook()["permissionDecisionReason"])

    def test_write_tool_is_guarded(self):
        self.write([])
        self.assertDenied(self.run_hook(tool="Write"), "skills")

    def test_allows_after_all_read(self):
        self.write(reads(SKILL_RULES))
        self.assertEqual(self.run_hook(), {})

    def test_lists_only_missing(self):
        self.write(reads(SKILL_RULES[:-1]))
        out = self.run_hook()
        self.assertDenied(out, "review")
        self.assertNotIn("skills.md", out["permissionDecisionReason"])

    def test_compaction_resets_reads(self):
        for marker in (COMPACT, MICROCOMPACT):
            self.write(reads(SKILL_RULES) + [marker])
            self.assertDenied(self.run_hook(), *SKILL_RULES)

    def test_read_after_compaction_counts(self):
        self.write(reads(SKILL_RULES) + [COMPACT] + reads(SKILL_RULES, 10))
        self.assertEqual(self.run_hook(), {})

    def test_partial_read_does_not_count(self):
        self.write(reads(SKILL_RULES[1:]) + [read_call(9, RULE("skills"), limit=40), read_result(9)])
        self.assertDenied(self.run_hook(), "skills")

    def test_failed_read_does_not_count(self):
        self.write(reads(SKILL_RULES[1:]) + [read_call(9, RULE("skills")), read_result(9, error=True)])
        self.assertDenied(self.run_hook(), "skills")

    def test_copy_outside_the_repo_does_not_count(self):
        self.write(reads(SKILL_RULES, base=self.dir.name))
        self.assertDenied(self.run_hook(), *SKILL_RULES)

    def test_read_from_the_target_worktree_counts(self):
        wt = os.path.realpath(os.path.join(self.dir.name, "wt"))
        subprocess.run(["git", "init", "-q", wt], check=True)
        os.makedirs(os.path.join(wt, "docs", "rules"))
        self.write(reads(SKILL_RULES, base=wt))
        self.assertEqual(self.run_hook(target=os.path.join(wt, ".claude", "skills", "x", "SKILL.md")), {})

    def test_unrouted_path_passes(self):
        self.write([])
        self.assertEqual(self.run_hook(target=os.path.join(ROOT, "README.md")), {})

    def test_commit_and_push_need_commit_rules(self):
        self.write([])
        for command in ("bin/commit-files -F m a.md", "cd /x && bin/push-main --mine abc", "/r/bin/commit-files -F m a"):
            self.assertDenied(self.run_bash(command), "commit-push")
        self.write(reads(["commit-push"]))
        self.assertEqual(self.run_bash("bin/commit-files -F m a.md"), {})

    def test_ssh_needs_remote_rules(self):
        self.write([])
        self.assertDenied(self.run_bash("ssh host systemctl status x"), "remote")

    def test_command_text_that_only_mentions_the_tool_passes(self):
        self.write([])
        for command in ("rg -n 'bin/commit-files' docs", "echo ssh is a tool", "git status", "sshfs a b"):
            self.assertEqual(self.run_bash(command), {}, command)

    def test_subagent_uses_its_own_transcript(self):
        self.write(reads(SKILL_RULES))  # 主 session 讀過，subagent 沒讀
        sub = os.path.join(self.dir.name, "s", "subagents")
        os.makedirs(sub)
        self.write([], os.path.join(sub, "agent-abc.jsonl"))
        self.assertDenied(self.run_hook(agent_id="abc"), "skills")
        self.write(reads(SKILL_RULES), os.path.join(sub, "agent-abc.jsonl"))
        self.assertEqual(self.run_hook(agent_id="abc"), {})

    def test_missing_subagent_transcript_warns_instead_of_using_parent(self):
        self.write(reads(SKILL_RULES))
        out = self.run_hook(agent_id="missing")
        self.assertAllowed(out)
        self.assertIn("bin/rule-route", out["additionalContext"])

    def test_unreadable_transcript_fails_open_with_warning(self):
        out = self.run_hook()  # transcript 不存在
        self.assertAllowed(out)
        self.assertIn("bin/rule-route", out["additionalContext"])

    def test_route_to_a_missing_file_warns_instead_of_denying_forever(self):
        repo = os.path.realpath(os.path.join(self.dir.name, "stub"))
        os.makedirs(os.path.join(repo, ".claude", "hooks"))
        os.makedirs(os.path.join(repo, "bin"))
        os.makedirs(os.path.join(repo, "docs", "rules"))
        shutil.copy(HOOK, os.path.join(repo, ".claude", "hooks", "rule_read_guard.py"))
        with open(os.path.join(repo, "bin", "rule-route"), "w", encoding="utf-8") as f:
            f.write('print(\'["docs/rules/gone.md", "docs/rules/here.md"]\')\n')
        with open(os.path.join(repo, "docs", "rules", "here.md"), "w", encoding="utf-8") as f:
            f.write("x\n")

        def run():
            payload = {"transcript_path": self.transcript, "cwd": repo, "tool_name": "Edit",
                       "tool_input": {"file_path": os.path.join(repo, "a.md")}}
            hook = os.path.join(repo, ".claude", "hooks", "rule_read_guard.py")
            r = subprocess.run([sys.executable, "-I", hook], input=json.dumps(payload), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return json.loads(r.stdout)["hookSpecificOutput"]

        self.write([])
        out = run()
        self.assertDenied(out, "here")
        self.assertNotIn("gone.md", out["permissionDecisionReason"])
        self.write(reads(["here"], base=repo))
        out = run()
        self.assertAllowed(out)
        self.assertIn("docs/rules/gone.md", out["additionalContext"])

    def test_bad_stdin_passes(self):
        r = subprocess.run([sys.executable, "-I", HOOK], input="not json", capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
