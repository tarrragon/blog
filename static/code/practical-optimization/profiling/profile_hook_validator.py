#!/usr/bin/env python3
"""
HookValidator 效能分析

使用 cProfile 分析 Hook 驗證器的效能瓶頸。
"""

import cProfile
import pstats
import re
import tempfile
from io import StringIO
from pathlib import Path


class HookValidator:
    """簡化版的 Hook 驗證器（用於效能分析）"""

    # 正則表達式模式
    HOOK_IO_PATTERNS = [
        r"from\s+hook_io\s+import",
        r"from\s+lib\.hook_io\s+import",
    ]

    HOOK_LOGGING_PATTERNS = [
        r"from\s+hook_logging\s+import",
        r"from\s+lib\.hook_logging\s+import",
    ]

    OUTPUT_PATTERNS = [
        r"write_hook_output\s*\(",
        r"create_pretooluse_output\s*\(",
        r"create_posttooluse_output\s*\(",
    ]

    VALID_NAME_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9\-_]*[a-z0-9])?\.py$")

    def _has_import(self, content: str, patterns: list[str]) -> bool:
        """檢查是否有符合的 import 語句"""
        return any(re.search(pattern, content) for pattern in patterns)

    def _check_naming(self, file_path: Path) -> list[str]:
        """檢查命名慣例"""
        issues = []
        if not self.VALID_NAME_PATTERN.match(file_path.name):
            issues.append(f"Invalid filename: {file_path.name}")
        return issues

    def _check_imports(self, content: str) -> list[str]:
        """檢查 import 語句"""
        issues = []

        if not self._has_import(content, self.HOOK_IO_PATTERNS):
            issues.append("Missing hook_io import")

        if not self._has_import(content, self.HOOK_LOGGING_PATTERNS):
            issues.append("Missing hook_logging import (recommended)")

        return issues

    def _check_output(self, content: str) -> list[str]:
        """檢查輸出函式"""
        issues = []

        if not self._has_import(content, self.OUTPUT_PATTERNS):
            issues.append("Missing output function call")

        return issues

    def validate_hook(self, file_path: str) -> dict:
        """驗證單一 Hook 檔案"""
        path = Path(file_path)
        issues = []

        if not path.exists():
            return {
                "file": file_path,
                "valid": False,
                "issues": ["File not found"],
            }

        # 檢查命名
        issues.extend(self._check_naming(path))

        # 讀取內容
        content = path.read_text(encoding="utf-8")

        # 檢查 import
        issues.extend(self._check_imports(content))

        # 檢查輸出
        issues.extend(self._check_output(content))

        return {
            "file": file_path,
            "valid": len(issues) == 0,
            "issues": issues,
        }

    def validate_all_hooks(self, hooks_dir: str) -> list[dict]:
        """驗證目錄中的所有 Hook"""
        results = []
        dir_path = Path(hooks_dir)

        hook_files = list(dir_path.glob("*.py"))

        for hook_file in hook_files:
            if hook_file.name.startswith("_"):
                continue
            result = self.validate_hook(str(hook_file))
            results.append(result)

        return results


def create_test_hooks(directory: Path, count: int) -> list[Path]:
    """建立測試用的 Hook 檔案"""
    files = []

    for i in range(count):
        file_path = directory / f"test-hook-{i:04d}.py"
        content = f'''#!/usr/bin/env python3
"""
Test Hook {i}

This is a test hook file for performance analysis.
"""

import json
import sys
from pathlib import Path

from hook_io import read_hook_input, write_hook_output
from hook_logging import setup_hook_logging
from config_loader import load_config

logger = setup_hook_logging("test-hook-{i:04d}")


def process_input(hook_input: dict) -> dict:
    """Process the hook input."""
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {{}})

    # Some processing logic
    result = {{
        "decision": "approve",
        "reason": "Test hook {i} approved"
    }}

    return result


def main():
    hook_input = read_hook_input()
    result = process_input(hook_input)
    write_hook_output(result)


if __name__ == "__main__":
    main()
'''
        file_path.write_text(content)
        files.append(file_path)

    return files


def profile_validator(file_count: int = 50):
    """執行效能分析"""
    print(f"建立 {file_count} 個測試 Hook...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 建立測試檔案
        create_test_hooks(tmpdir_path, file_count)

        # 建立驗證器
        validator = HookValidator()

        # 使用 cProfile 進行分析
        print("執行效能分析...")
        profiler = cProfile.Profile()
        profiler.enable()

        # 執行被分析的程式碼
        results = validator.validate_all_hooks(str(tmpdir_path))

        profiler.disable()

        # 輸出結果
        print(f"\n驗證了 {len(results)} 個 Hook")
        valid_count = sum(1 for r in results if r["valid"])
        print(f"有效：{valid_count}，無效：{len(results) - valid_count}")

        # 輸出效能分析結果
        print("\n" + "=" * 60)
        print("效能分析結果（按累計時間排序，前 20 個）")
        print("=" * 60)

        stream = StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats("cumulative")
        stats.print_stats(20)
        print(stream.getvalue())

        # 分析正則表達式相關呼叫
        print("=" * 60)
        print("正則表達式相關呼叫")
        print("=" * 60)

        stream = StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats("cumulative")
        stats.print_stats("re\.")
        print(stream.getvalue())


def main():
    print("=" * 60)
    print("HookValidator 效能分析")
    print("=" * 60)
    print()

    profile_validator(50)

    print("=" * 60)
    print("分析完成")
    print("=" * 60)
    print("""
常見瓶頸：
1. 正則表達式匹配（re.search）
2. 檔案 I/O（read_text）
3. 字串比對

優化建議：
1. 預編譯正則表達式
2. 並行處理檔案驗證
3. 使用 set 進行成員查詢
4. 快取重複計算
""")


if __name__ == "__main__":
    main()
