""".claude/hooks/markdown_formatter.py 的測試。

這支 hook 在每次 Write 或 Edit 一份 .md 之後重寫檔案。案例取自一次實際的損壞：
文章裡放了一支 Python 腳本的原始碼，頂層定義之間的兩個空行被壓成一個，
程式碼區塊因此跟原檔不再逐字相同。每個測試把檔案寫進暫存目錄，照 Claude Code
的方式把 hook 的輸入（JSON）餵進 stdin 執行 hook，再讀回檔案比對，不 import。

跑法：python3 -m unittest discover -s bin/tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".claude", "hooks", "markdown_formatter.py"))


def run_hook(text, name="doc.md"):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": path}})
        r = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)
        if r.returncode != 0:
            raise AssertionError(f"hook failed: {r.stdout}{r.stderr}")
        with open(path, encoding="utf-8") as f:
            return f.read()


class TestBlankLines(unittest.TestCase):
    def test_two_blank_lines_inside_python_fence_are_kept(self):
        src = "# T\n\n```python\nimport os\n\n\ndef f():\n    pass\n\n\nclass C:\n    pass\n```\n"
        self.assertEqual(run_hook(src), src)

    def test_blank_lines_outside_fences_collapse_to_one(self):
        self.assertEqual(run_hook("a\n\n\n\nb\n"), "a\n\nb\n")

    def test_outside_collapses_while_inside_is_kept(self):
        src = "a\n\n\nb\n\n```bash\nx\n\n\ny\n```\n\n\nc\n"
        want = "a\n\nb\n\n```bash\nx\n\n\ny\n```\n\nc\n"
        self.assertEqual(run_hook(src), want)

    def test_tilde_fence_containing_backticks_stays_open(self):
        # ~~~ 開的區塊裡出現 ``` 不算結束，後面的兩個空行仍在區塊裡
        src = "~~~markdown\n```python\n\n\nx = 1\n```\n\n\n~~~\n"
        self.assertEqual(run_hook(src), src)

    def test_indented_fence_in_list_is_kept(self):
        src = "- item\n\n  ```text\n  a\n\n\n  b\n  ```\n"
        self.assertEqual(run_hook(src), src)

    def test_non_markdown_file_is_untouched(self):
        src = "a\n\n\n\nb\n"
        self.assertEqual(run_hook(src, name="note.txt"), src)


if __name__ == "__main__":
    unittest.main()
