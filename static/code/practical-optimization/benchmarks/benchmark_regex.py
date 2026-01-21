#!/usr/bin/env python3
"""
正則表達式預編譯效能測試

比較 re.search() 與 compiled_pattern.search() 的效能差異。
"""

import re
import timeit
from typing import Pattern


# 測試用的正則表達式模式（來自 hook_validator.py）
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

# 模擬的 Hook 檔案內容
TEST_CONTENT = '''#!/usr/bin/env python3
"""
Hook for checking permissions before tool execution.
"""

import json
import sys
from pathlib import Path

from hook_io import read_hook_input, write_hook_output
from hook_logging import setup_hook_logging
from config_loader import load_config

logger = setup_hook_logging("check-permissions")


def check_permissions(hook_input: dict) -> dict:
    """Check if the tool has permission to execute."""
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Check permission logic here
    allowed = True

    return {
        "decision": "approve" if allowed else "block",
        "reason": "Permission granted" if allowed else "Permission denied"
    }


def main():
    hook_input = read_hook_input()
    result = check_permissions(hook_input)
    write_hook_output(result)


if __name__ == "__main__":
    main()
'''


def has_import_uncompiled(content: str, patterns: list[str]) -> bool:
    """使用未編譯的正則表達式檢查"""
    return any(re.search(pattern, content) for pattern in patterns)


def has_import_compiled(content: str, patterns: list[Pattern]) -> bool:
    """使用預編譯的正則表達式檢查"""
    return any(pattern.search(content) for pattern in patterns)


def benchmark_single_pattern():
    """測試單一模式的效能差異"""
    print("單一模式測試")
    print("-" * 50)

    pattern_str = r"from\s+hook_io\s+import"
    pattern_compiled = re.compile(pattern_str)

    # 未編譯版本
    uncompiled_time = timeit.timeit(
        lambda: re.search(pattern_str, TEST_CONTENT),
        number=10000,
    )

    # 預編譯版本
    compiled_time = timeit.timeit(
        lambda: pattern_compiled.search(TEST_CONTENT),
        number=10000,
    )

    print(f"未編譯版本：{uncompiled_time:.4f}s (10000 次)")
    print(f"預編譯版本：{compiled_time:.4f}s (10000 次)")
    print(f"加速比：{uncompiled_time / compiled_time:.2f}x")
    print()


def benchmark_multiple_patterns():
    """測試多模式匹配的效能差異"""
    print("多模式匹配測試")
    print("-" * 50)

    all_patterns = HOOK_IO_PATTERNS + HOOK_LOGGING_PATTERNS + OUTPUT_PATTERNS

    # 預編譯所有模式
    compiled_patterns = [re.compile(p) for p in all_patterns]

    # 未編譯版本
    uncompiled_time = timeit.timeit(
        lambda: has_import_uncompiled(TEST_CONTENT, all_patterns),
        number=10000,
    )

    # 預編譯版本
    compiled_time = timeit.timeit(
        lambda: has_import_compiled(TEST_CONTENT, compiled_patterns),
        number=10000,
    )

    print(f"未編譯版本：{uncompiled_time:.4f}s (10000 次)")
    print(f"預編譯版本：{compiled_time:.4f}s (10000 次)")
    print(f"加速比：{uncompiled_time / compiled_time:.2f}x")
    print()


def benchmark_cache_miss():
    """模擬快取未命中的情況"""
    print("快取未命中測試（清除 re 內部快取）")
    print("-" * 50)

    pattern_str = r"from\s+hook_io\s+import"
    pattern_compiled = re.compile(pattern_str)

    # 未編譯版本（每次清除快取）
    def search_with_purge():
        re.purge()  # 清除內部快取
        return re.search(pattern_str, TEST_CONTENT)

    uncompiled_time = timeit.timeit(search_with_purge, number=1000)

    # 預編譯版本（不受快取影響）
    compiled_time = timeit.timeit(
        lambda: pattern_compiled.search(TEST_CONTENT),
        number=1000,
    )

    print(f"未編譯版本（清除快取）：{uncompiled_time:.4f}s (1000 次)")
    print(f"預編譯版本：{compiled_time:.4f}s (1000 次)")
    print(f"加速比：{uncompiled_time / compiled_time:.2f}x")
    print()


def show_cache_info():
    """顯示 re 模組的快取資訊"""
    print("re 模組快取資訊")
    print("-" * 50)

    # 清除快取
    re.purge()
    print(f"清除後快取大小：{len(re._cache)}")

    # 執行一些模式匹配
    for pattern in HOOK_IO_PATTERNS + HOOK_LOGGING_PATTERNS:
        re.search(pattern, TEST_CONTENT)

    print(f"匹配後快取大小：{len(re._cache)}")
    print(f"快取最大容量：{re._MAXCACHE}")
    print()


def main():
    print("=" * 60)
    print("正則表達式預編譯效能測試")
    print("=" * 60)
    print()

    show_cache_info()
    benchmark_single_pattern()
    benchmark_multiple_patterns()
    benchmark_cache_miss()

    print("=" * 60)
    print("結論")
    print("=" * 60)
    print("""
1. 正常情況下（re 快取命中），預編譯帶來約 1.2-1.3x 的加速
2. 快取未命中時，預編譯帶來 5-6x 的加速
3. 對於頻繁使用的模式，預編譯是值得的
4. 預編譯還能提高程式碼可讀性（模式定義與使用分離）
""")


if __name__ == "__main__":
    main()
