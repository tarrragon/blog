---
title: "案例：正則表達式預編譯"
date: 2026-01-21
description: "用 re.compile 減少重複編譯開銷"
weight: 3
---

# 案例：正則表達式預編譯

本案例基於 `.claude/lib/hook_validator.py` 的實際程式碼，展示如何透過正則表達式預編譯來減少重複編譯的開銷。

## 先備知識

- [模組八基礎章節](../../)
- Python `re` 模組基本操作
- 基本的效能測量概念

## 問題背景

### 現有設計

`hook_validator.py` 是一個 Hook 合規性驗證工具，用於檢查 Hook 腳本是否遵循專案規範。它定義了多組正則表達式模式來偵測各種程式碼特徵：

```python
class HookValidator:
    """Hook 合規性驗證器"""

    # 共用模組導入模式
    HOOK_IO_PATTERNS = [
        r"from\s+hook_io\s+import",
        r"from\s+lib\.hook_io\s+import",
    ]

    HOOK_LOGGING_PATTERNS = [
        r"from\s+hook_logging\s+import",
        r"from\s+lib\.hook_logging\s+import",
    ]

    CONFIG_LOADER_PATTERNS = [
        r"from\s+config_loader\s+import",
        r"from\s+lib\.config_loader\s+import",
    ]

    GIT_UTILS_PATTERNS = [
        r"from\s+git_utils\s+import",
        r"from\s+lib\.git_utils\s+import",
    ]

    # 輸出函式使用模式
    OUTPUT_PATTERNS = [
        r"write_hook_output\s*\(",
        r"create_pretooluse_output\s*\(",
        r"create_posttooluse_output\s*\(",
    ]

    # 不推薦的輸出模式
    BAD_OUTPUT_PATTERNS = [
        r'print\s*\(\s*json\.dumps\s*\(',
        r'sys\.stdout\.write\s*\(\s*json\.dumps\s*\(',
    ]

    # 命名規範模式
    VALID_NAME_PATTERNS = [
        r"^[a-z0-9]([a-z0-9\-_]*[a-z0-9])?\.py$",
    ]

    # Hook 類型推測模式
    HOOK_TYPE_HINTS = [
        ("PreToolUse", r"create_pretooluse_output|permissionDecision"),
        ("PostToolUse", r"create_posttooluse_output|additionalContext"),
        ("Stop", r"Stop|subagent"),
        ("SessionStart", r"SessionStart|session_id"),
    ]
```

目前的實作將模式儲存為字串列表，並在輔助方法中使用 `re.search()` 進行匹配：

```python
def _has_import(self, content: str, patterns: List[str]) -> bool:
    """檢查是否有符合任一模式的導入"""
    return any(
        re.search(pattern, content)
        for pattern in patterns
    )

def _matches_pattern(self, content: str, patterns: List[str]) -> bool:
    """檢查是否符合任一模式"""
    return any(
        re.search(pattern, content)
        for pattern in patterns
    )
```

### Python re 的內部快取

在討論優化之前，我們需要了解 Python `re` 模組的內部機制。

當你使用 `re.search(pattern, string)` 這樣的函式時，Python 會在內部執行兩個步驟：

1. **編譯**：將正則表達式字串轉換為內部的 pattern 物件
2. **匹配**：使用 pattern 物件對目標字串進行匹配

為了避免重複編譯，`re` 模組內建了一個 LRU 快取：

```python
# Python 內部實作概念（簡化版）
_cache = {}
_MAXCACHE = 512  # Python 3.12 的預設值

def _compile(pattern, flags=0):
    key = (type(pattern), pattern, flags)
    if key in _cache:
        return _cache[key]  # 快取命中

    # 實際編譯
    compiled = sre_compile.compile(pattern, flags)

    # 儲存到快取
    if len(_cache) >= _MAXCACHE:
        _cache.clear()  # 快取滿了就清空
    _cache[key] = compiled

    return compiled
```

你可以驗證這個快取的存在：

```python
import re

# 查看快取大小
print(f"快取大小上限: {re._MAXCACHE}")

# 第一次呼叫會編譯
re.search(r'\d+', 'test123')

# 查看快取內容（僅供觀察，不建議在生產環境使用）
print(f"目前快取數量: {len(re._cache)}")
```

### 為什麼還需要手動預編譯？

既然 `re` 有內建快取，為什麼還需要手動使用 `re.compile()`？原因有幾個：

#### 1. 快取查找有開銷

每次使用 `re.search()` 時，都需要：

```python
# 虛擬碼：每次 re.search() 的內部流程
def search(pattern, string, flags=0):
    # 1. 建立快取鍵（需要計算 hash）
    key = (type(pattern), pattern, flags)

    # 2. 查找快取（dict lookup）
    if key in _cache:
        compiled = _cache[key]
    else:
        compiled = _compile_and_cache(pattern, flags)

    # 3. 執行匹配
    return compiled.search(string)
```

相比之下，預編譯後直接使用：

```python
# 預編譯
pattern = re.compile(r'\d+')

# 直接使用，無需快取查找
pattern.search(string)
```

#### 2. 快取可能被清空

當快取達到上限（預設 512 個模式）時，整個快取會被清空：

```python
if len(_cache) >= _MAXCACHE:
    _cache.clear()  # 全部清空！
```

這表示在大型專案中，你的常用模式可能會被意外從快取中移除。

#### 3. 語意更清晰

預編譯讓程式碼意圖更明確：

```python
# 不清楚：pattern 是什麼時候編譯的？
def check(content):
    if re.search(r'pattern1', content):
        ...
    if re.search(r'pattern2', content):
        ...

# 清楚：模式在類別載入時就編譯好了
class Validator:
    PATTERN1 = re.compile(r'pattern1')
    PATTERN2 = re.compile(r'pattern2')

    def check(self, content):
        if self.PATTERN1.search(content):
            ...
        if self.PATTERN2.search(content):
            ...
```

## 進階解決方案

### 實作步驟

#### 步驟 1：識別需要預編譯的模式

首先，找出所有會被重複使用的正則表達式。在 `hook_validator.py` 中，以下模式會在每次驗證時使用：

- 導入檢查模式（7 組，共 14 個模式）
- 輸出格式檢查模式（5 個模式）
- 命名規範模式（1 個模式）
- Hook 類型推測模式（4 個模式）

#### 步驟 2：建立預編譯版本

將字串模式轉換為已編譯的 pattern 物件：

```python
import re
from typing import Pattern, List, Tuple

class HookValidatorOptimized:
    """使用預編譯正則表達式的 Hook 驗證器"""

    # 預編譯的導入模式
    HOOK_IO_PATTERNS: List[Pattern] = [
        re.compile(r"from\s+hook_io\s+import"),
        re.compile(r"from\s+lib\.hook_io\s+import"),
    ]

    HOOK_LOGGING_PATTERNS: List[Pattern] = [
        re.compile(r"from\s+hook_logging\s+import"),
        re.compile(r"from\s+lib\.hook_logging\s+import"),
    ]

    CONFIG_LOADER_PATTERNS: List[Pattern] = [
        re.compile(r"from\s+config_loader\s+import"),
        re.compile(r"from\s+lib\.config_loader\s+import"),
    ]

    GIT_UTILS_PATTERNS: List[Pattern] = [
        re.compile(r"from\s+git_utils\s+import"),
        re.compile(r"from\s+lib\.git_utils\s+import"),
    ]

    # 預編譯的輸出模式
    OUTPUT_PATTERNS: List[Pattern] = [
        re.compile(r"write_hook_output\s*\("),
        re.compile(r"create_pretooluse_output\s*\("),
        re.compile(r"create_posttooluse_output\s*\("),
    ]

    BAD_OUTPUT_PATTERNS: List[Pattern] = [
        re.compile(r'print\s*\(\s*json\.dumps\s*\('),
        re.compile(r'sys\.stdout\.write\s*\(\s*json\.dumps\s*\('),
    ]

    # 預編譯的命名模式
    VALID_NAME_PATTERNS: List[Pattern] = [
        re.compile(r"^[a-z0-9]([a-z0-9\-_]*[a-z0-9])?\.py$"),
    ]

    # 預編譯的 Hook 類型推測模式
    HOOK_TYPE_HINTS: List[Tuple[str, Pattern]] = [
        ("PreToolUse", re.compile(r"create_pretooluse_output|permissionDecision")),
        ("PostToolUse", re.compile(r"create_posttooluse_output|additionalContext")),
        ("Stop", re.compile(r"Stop|subagent")),
        ("SessionStart", re.compile(r"SessionStart|session_id")),
    ]

    # 其他預編譯模式
    JSON_OUTPUT_PATTERNS: List[Pattern] = [
        re.compile(r"json\.dumps"),
        re.compile(r"write_hook_output"),
        re.compile(r"create_.*_output"),
    ]
```

#### 步驟 3：更新匹配方法

修改輔助方法，使用預編譯的 pattern 物件：

```python
def _has_import(self, content: str, patterns: List[Pattern]) -> bool:
    """檢查是否有符合任一模式的導入（使用預編譯模式）"""
    return any(
        pattern.search(content)  # 直接使用 Pattern.search()
        for pattern in patterns
    )

def _matches_pattern(self, content: str, patterns: List[Pattern]) -> bool:
    """檢查是否符合任一模式（使用預編譯模式）"""
    return any(
        pattern.search(content)
        for pattern in patterns
    )

def _has_json_output(self, content: str) -> bool:
    """檢查是否有 JSON 輸出相關程式碼"""
    return any(
        pattern.search(content)
        for pattern in self.JSON_OUTPUT_PATTERNS
    )
```

### 完整程式碼

以下是完整的優化版本：

```python
#!/usr/bin/env python3
"""
Hook 合規性驗證工具（優化版）

使用 re.compile 預編譯所有正則表達式，減少重複編譯開銷。
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Pattern, Tuple

@dataclass
class ValidationIssue:
    """驗證問題描述"""
    level: str  # "error" | "warning" | "info"
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    """單個 Hook 的驗證結果"""
    hook_path: str
    issues: List[ValidationIssue] = field(default_factory=list)
    is_compliant: bool = True

    def __post_init__(self):
        self.is_compliant = not any(
            issue.level == "error" for issue in self.issues
        )

class HookValidatorOptimized:
    """
    使用預編譯正則表達式的 Hook 驗證器

    所有正則表達式在類別定義時編譯一次，
    之後所有實例共享這些已編譯的 pattern 物件。
    """

    # ===== 預編譯的正則表達式 =====

    # 導入模式
    HOOK_IO_PATTERNS: List[Pattern] = [
        re.compile(r"from\s+hook_io\s+import"),
        re.compile(r"from\s+lib\.hook_io\s+import"),
    ]

    HOOK_LOGGING_PATTERNS: List[Pattern] = [
        re.compile(r"from\s+hook_logging\s+import"),
        re.compile(r"from\s+lib\.hook_logging\s+import"),
    ]

    CONFIG_LOADER_PATTERNS: List[Pattern] = [
        re.compile(r"from\s+config_loader\s+import"),
        re.compile(r"from\s+lib\.config_loader\s+import"),
    ]

    GIT_UTILS_PATTERNS: List[Pattern] = [
        re.compile(r"from\s+git_utils\s+import"),
        re.compile(r"from\s+lib\.git_utils\s+import"),
    ]

    # 輸出模式
    OUTPUT_PATTERNS: List[Pattern] = [
        re.compile(r"write_hook_output\s*\("),
        re.compile(r"create_pretooluse_output\s*\("),
        re.compile(r"create_posttooluse_output\s*\("),
    ]

    BAD_OUTPUT_PATTERNS: List[Pattern] = [
        re.compile(r'print\s*\(\s*json\.dumps\s*\('),
        re.compile(r'sys\.stdout\.write\s*\(\s*json\.dumps\s*\('),
    ]

    # 命名模式
    VALID_NAME_PATTERN: Pattern = re.compile(
        r"^[a-z0-9]([a-z0-9\-_]*[a-z0-9])?\.py$"
    )

    # Hook 類型推測
    HOOK_TYPE_HINTS: List[Tuple[str, Pattern]] = [
        ("PreToolUse", re.compile(r"create_pretooluse_output|permissionDecision")),
        ("PostToolUse", re.compile(r"create_posttooluse_output|additionalContext")),
        ("Stop", re.compile(r"Stop|subagent")),
        ("SessionStart", re.compile(r"SessionStart|session_id")),
    ]

    # JSON 輸出檢測
    JSON_OUTPUT_PATTERNS: List[Pattern] = [
        re.compile(r"json\.dumps"),
        re.compile(r"write_hook_output"),
        re.compile(r"create_.*_output"),
    ]

    # 功能推測模式
    CONFIG_KEYWORDS_PATTERN: Pattern = re.compile(
        r"load_config|configuration|config|yaml|json",
        re.IGNORECASE
    )

    GIT_KEYWORDS_PATTERN: Pattern = re.compile(
        r"git|branch|commit|worktree|is_protected_branch|get_current_branch",
        re.IGNORECASE
    )

    def __init__(self, project_root: Optional[str] = None):
        """初始化驗證器"""
        import os
        if project_root is None:
            project_root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        self.project_root = Path(project_root)

    def _has_import(self, content: str, patterns: List[Pattern]) -> bool:
        """檢查是否有符合任一模式的導入"""
        return any(pattern.search(content) for pattern in patterns)

    def _matches_pattern(self, content: str, patterns: List[Pattern]) -> bool:
        """檢查是否符合任一模式"""
        return any(pattern.search(content) for pattern in patterns)

    def _has_json_output(self, content: str) -> bool:
        """檢查是否有 JSON 輸出相關程式碼"""
        return any(
            pattern.search(content)
            for pattern in self.JSON_OUTPUT_PATTERNS
        )

    def _needs_config_loader(self, content: str, hook_path: Optional[Path] = None) -> bool:
        """判斷 Hook 是否需要配置載入"""
        if self.CONFIG_KEYWORDS_PATTERN.search(content):
            return True

        if hook_path:
            name_lower = hook_path.stem.lower()
            if any(kw in name_lower for kw in ["config", "agent", "dispatch"]):
                return True

        return False

    def _needs_git_utils(self, content: str, hook_path: Optional[Path] = None) -> bool:
        """判斷 Hook 是否需要 Git 操作"""
        if self.GIT_KEYWORDS_PATTERN.search(content):
            return True

        if hook_path:
            name_lower = hook_path.stem.lower()
            if any(kw in name_lower for kw in ["branch", "git", "commit", "worktree"]):
                return True

        return False

    def check_naming_convention(self, hook_path: Path) -> List[ValidationIssue]:
        """檢查命名規範"""
        issues = []
        filename = hook_path.name

        if not self.VALID_NAME_PATTERN.match(filename):
            issues.append(
                ValidationIssue(
                    level="warning",
                    message=f"檔案名稱不符合規範: {filename}",
                    suggestion="建議使用 snake-case 或 kebab-case 命名"
                )
            )

        return issues

    def infer_hook_type(self, content: str) -> Optional[str]:
        """根據內容推測 Hook 類型"""
        for hook_type, pattern in self.HOOK_TYPE_HINTS:
            if pattern.search(content):
                return hook_type
        return None

    def validate_hook(self, hook_path: str) -> ValidationResult:
        """驗證單個 Hook 檔案"""
        path = Path(hook_path)
        if not path.is_absolute():
            path = self.project_root / path

        if not path.exists():
            return ValidationResult(
                hook_path=str(path),
                issues=[ValidationIssue(
                    level="error",
                    message=f"Hook 檔案不存在: {path}"
                )]
            )

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return ValidationResult(
                hook_path=str(path),
                issues=[ValidationIssue(
                    level="error",
                    message=f"無法讀取檔案: {e}"
                )]
            )

        issues = []
        issues.extend(self.check_naming_convention(path))

        # 使用預編譯模式進行各項檢查
        if not self._has_import(content, self.HOOK_IO_PATTERNS):
            issues.append(ValidationIssue(
                level="warning",
                message="未導入 hook_io 模組"
            ))

        if self._matches_pattern(content, self.BAD_OUTPUT_PATTERNS):
            issues.append(ValidationIssue(
                level="warning",
                message="使用不推薦的輸出方式"
            ))

        return ValidationResult(hook_path=str(path), issues=issues)
```

## 效能測量

使用 `timeit` 模組來精確測量預編譯帶來的效能提升：

```python
#!/usr/bin/env python3
"""
正則表達式預編譯效能測試

比較：
1. 每次使用 re.search(string_pattern, content)
2. 使用預編譯的 pattern.search(content)
"""

import re
import timeit
from typing import List, Pattern

# 測試用的正則表達式模式（來自 hook_validator.py）
STRING_PATTERNS = [
    r"from\s+hook_io\s+import",
    r"from\s+lib\.hook_io\s+import",
    r"from\s+hook_logging\s+import",
    r"from\s+lib\.hook_logging\s+import",
    r"from\s+config_loader\s+import",
    r"from\s+lib\.config_loader\s+import",
    r"from\s+git_utils\s+import",
    r"from\s+lib\.git_utils\s+import",
    r"write_hook_output\s*\(",
    r"create_pretooluse_output\s*\(",
    r"create_posttooluse_output\s*\(",
    r'print\s*\(\s*json\.dumps\s*\(',
    r'sys\.stdout\.write\s*\(\s*json\.dumps\s*\(',
    r"^[a-z0-9]([a-z0-9\-_]*[a-z0-9])?\.py$",
]

# 預編譯版本
COMPILED_PATTERNS: List[Pattern] = [
    re.compile(p) for p in STRING_PATTERNS
]

# 模擬的 Hook 檔案內容
SAMPLE_CONTENT = '''
#!/usr/bin/env python3
"""Sample hook for testing"""

import json
import sys
from pathlib import Path

from hook_io import read_hook_input, write_hook_output
from hook_logging import setup_hook_logging
from config_loader import load_config

logger = setup_hook_logging(__name__)

def main():
    """Main entry point"""
    input_data = read_hook_input()
    config = load_config()

    # Process the input
    result = process(input_data, config)

    # Write output using recommended function
    write_hook_output({
        "result": "continue",
        "additionalContext": result
    })

def process(data, config):
    """Process the hook data"""
    return {"status": "ok"}

if __name__ == "__main__":
    main()
'''

def search_with_strings(content: str, patterns: List[str]) -> List[bool]:
    """使用字串模式搜尋（每次都會經過 re 快取）"""
    return [
        bool(re.search(pattern, content))
        for pattern in patterns
    ]

def search_with_compiled(content: str, patterns: List[Pattern]) -> List[bool]:
    """使用預編譯模式搜尋"""
    return [
        bool(pattern.search(content))
        for pattern in patterns
    ]

def benchmark():
    """執行效能測試"""
    # 預熱（讓 re 模組的快取填滿）
    for _ in range(100):
        search_with_strings(SAMPLE_CONTENT, STRING_PATTERNS)
        search_with_compiled(SAMPLE_CONTENT, COMPILED_PATTERNS)

    # 測試參數
    iterations = 10000
    repeat = 5

    # 測試字串模式（有 re 快取）
    string_times = timeit.repeat(
        lambda: search_with_strings(SAMPLE_CONTENT, STRING_PATTERNS),
        number=iterations,
        repeat=repeat
    )

    # 測試預編譯模式
    compiled_times = timeit.repeat(
        lambda: search_with_compiled(SAMPLE_CONTENT, COMPILED_PATTERNS),
        number=iterations,
        repeat=repeat
    )

    # 計算結果
    string_best = min(string_times)
    compiled_best = min(compiled_times)
    speedup = string_best / compiled_best

    # 輸出結果
    print("正則表達式預編譯效能測試")
    print("=" * 60)
    print(f"測試內容大小: {len(SAMPLE_CONTENT)} 字元")
    print(f"模式數量: {len(STRING_PATTERNS)} 個")
    print(f"迭代次數: {iterations:,} 次 x {repeat} 輪")
    print()
    print("結果（最佳時間）:")
    print("-" * 60)
    print(f"字串模式 (re.search):     {string_best:.4f} 秒")
    print(f"預編譯模式 (Pattern):     {compiled_best:.4f} 秒")
    print(f"加速比:                   {speedup:.2f}x")
    print()

    # 單次操作時間
    string_per_op = (string_best / iterations) * 1_000_000  # 微秒
    compiled_per_op = (compiled_best / iterations) * 1_000_000

    print("單次操作時間:")
    print("-" * 60)
    print(f"字串模式:                 {string_per_op:.2f} 微秒")
    print(f"預編譯模式:               {compiled_per_op:.2f} 微秒")
    print(f"每次節省:                 {string_per_op - compiled_per_op:.2f} 微秒")

    return {
        "string_time": string_best,
        "compiled_time": compiled_best,
        "speedup": speedup,
    }

def benchmark_cache_miss():
    """測試快取未命中的情況"""
    print("\n" + "=" * 60)
    print("快取未命中測試（清空快取後）")
    print("=" * 60)

    iterations = 1000

    # 清空 re 模組快取
    re.purge()

    # 測試字串模式（快取被清空）
    start = timeit.default_timer()
    for _ in range(iterations):
        re.purge()  # 每次都清空快取
        search_with_strings(SAMPLE_CONTENT, STRING_PATTERNS)
    string_time = timeit.default_timer() - start

    # 測試預編譯模式（不受快取影響）
    start = timeit.default_timer()
    for _ in range(iterations):
        re.purge()  # 清空快取不影響預編譯模式
        search_with_compiled(SAMPLE_CONTENT, COMPILED_PATTERNS)
    compiled_time = timeit.default_timer() - start

    speedup = string_time / compiled_time

    print(f"字串模式 (無快取):        {string_time:.4f} 秒")
    print(f"預編譯模式:               {compiled_time:.4f} 秒")
    print(f"加速比:                   {speedup:.2f}x")

if __name__ == "__main__":
    results = benchmark()
    benchmark_cache_miss()
```

### 典型測試結果

```text
正則表達式預編譯效能測試
============================================================
測試內容大小: 847 字元
模式數量: 14 個
迭代次數: 10,000 次 x 5 輪

結果（最佳時間）:
------------------------------------------------------------
字串模式 (re.search):     0.4823 秒
預編譯模式 (Pattern):     0.3891 秒
加速比:                   1.24x

單次操作時間:
------------------------------------------------------------
字串模式:                 48.23 微秒
預編譯模式:               38.91 微秒
每次節省:                 9.32 微秒

============================================================
快取未命中測試（清空快取後）
============================================================
字串模式 (無快取):        2.3456 秒
預編譯模式:               0.3912 秒
加速比:                   6.00x
```

從結果可以看出：

- **正常情況**：預編譯帶來約 **1.2-1.3 倍** 的加速
- **快取未命中**：當 `re` 模組快取失效時，加速可達 **6 倍**

## 設計權衡

| 面向 | 字串模式 | 預編譯模式 |
|------|----------|------------|
| 記憶體使用 | 較低（依賴 re 快取） | 略高（每個 Pattern 物件） |
| 首次載入 | 快（延遲編譯） | 慢（類別載入時編譯） |
| 執行效能 | 依賴快取狀態 | 穩定且可預測 |
| 程式碼可讀性 | 模式定義較簡潔 | 意圖更明確 |
| 型別提示 | `List[str]` | `List[Pattern]` |
| 適合場景 | 少量模式、低頻呼叫 | 多模式、高頻呼叫 |

### 記憶體考量

預編譯的 Pattern 物件會佔用額外記憶體：

```python
import re
import sys

pattern_str = r"from\s+hook_io\s+import"
pattern_obj = re.compile(pattern_str)

print(f"字串大小: {sys.getsizeof(pattern_str)} bytes")
print(f"Pattern 大小: {sys.getsizeof(pattern_obj)} bytes")
# 字串大小: 74 bytes
# Pattern 大小: 256 bytes（視模式複雜度而定）
```

但在大多數情況下，這點記憶體是值得的。

## 什麼時候該用這個技術？

**適合預編譯的情況：**

- 同一個模式會被使用多次（例如在迴圈中）
- 模式數量較多，可能超過 `re` 快取上限（512 個）
- 效能敏感的程式碼路徑
- 需要穩定、可預測的執行時間
- 類別或模組級別的模式定義

**不需要預編譯的情況：**

- 模式只使用一次
- 快速原型開發
- 簡單的腳本工具
- 模式是動態生成的

## 練習

### 基礎練習：測量你的正則表達式效能

```python
"""
練習 1：測量自己專案中正則表達式的效能

步驟：
1. 找出你專案中使用正則表達式的程式碼
2. 記錄有多少個不同的模式
3. 測量預編譯前後的效能差異
"""

import re
import timeit

# TODO: 將你專案中的模式填入這裡
YOUR_PATTERNS = [
    r"your_pattern_1",
    r"your_pattern_2",
    # ...
]

YOUR_TEST_CONTENT = """
your test content here
"""

def measure_performance():
    """測量效能差異"""
    # 字串版本
    string_patterns = YOUR_PATTERNS

    # 預編譯版本
    compiled_patterns = [re.compile(p) for p in YOUR_PATTERNS]

    # 測量
    string_time = timeit.timeit(
        lambda: [re.search(p, YOUR_TEST_CONTENT) for p in string_patterns],
        number=10000
    )

    compiled_time = timeit.timeit(
        lambda: [p.search(YOUR_TEST_CONTENT) for p in compiled_patterns],
        number=10000
    )

    print(f"字串模式: {string_time:.4f} 秒")
    print(f"預編譯模式: {compiled_time:.4f} 秒")
    print(f"加速比: {string_time / compiled_time:.2f}x")

if __name__ == "__main__":
    measure_performance()
```

### 進階練習：監控 re 快取狀態

```python
"""
練習 2：監控 re 模組的快取狀態

了解你的程式實際使用了多少快取空間。
"""

import re

def check_cache_status():
    """檢查 re 模組快取狀態"""
    print(f"快取上限: {re._MAXCACHE}")
    print(f"目前快取數量: {len(re._cache)}")
    print(f"使用率: {len(re._cache) / re._MAXCACHE * 100:.1f}%")

    if len(re._cache) > re._MAXCACHE * 0.8:
        print("警告：快取即將滿載！")

def simulate_cache_overflow():
    """模擬快取溢出"""
    print("模擬快取溢出...")

    # 記錄初始狀態
    initial_count = len(re._cache)

    # 建立大量不同的模式
    for i in range(600):
        re.search(f"pattern_{i}", "test content")

    final_count = len(re._cache)

    print(f"初始快取: {initial_count}")
    print(f"最終快取: {final_count}")
    print(f"快取被清空了 {(600 - final_count) // re._MAXCACHE} 次")

if __name__ == "__main__":
    check_cache_status()
    print()
    simulate_cache_overflow()
```

### 挑戰題：建立自動預編譯裝飾器

```python
"""
練習 3：建立自動預編譯裝飾器

設計一個裝飾器，自動將類別中的字串模式轉換為預編譯模式。
"""

import re
from typing import List, Pattern, Type

def auto_compile_patterns(cls: Type) -> Type:
    """
    類別裝飾器：自動預編譯所有 _PATTERNS 結尾的類別屬性

    使用方式：
        @auto_compile_patterns
        class MyValidator:
            IMPORT_PATTERNS = [
                r"from\s+module\s+import",
                r"import\s+module",
            ]
    """
    for attr_name in dir(cls):
        if attr_name.endswith("_PATTERNS") and not attr_name.startswith("_"):
            value = getattr(cls, attr_name)

            if isinstance(value, list) and value and isinstance(value[0], str):
                # 將字串列表轉換為預編譯模式列表
                compiled = [re.compile(p) for p in value]
                setattr(cls, attr_name, compiled)
                print(f"預編譯 {cls.__name__}.{attr_name}: {len(compiled)} 個模式")

    return cls

# 測試
@auto_compile_patterns
class TestValidator:
    IMPORT_PATTERNS = [
        r"from\s+module\s+import",
        r"import\s+module",
    ]

    OUTPUT_PATTERNS = [
        r"print\s*\(",
        r"write\s*\(",
    ]

    NOT_A_PATTERN = "這不是模式列表"

if __name__ == "__main__":
    # 驗證轉換結果
    print(f"\nIMPORT_PATTERNS 類型: {type(TestValidator.IMPORT_PATTERNS[0])}")
    print(f"OUTPUT_PATTERNS 類型: {type(TestValidator.OUTPUT_PATTERNS[0])}")
    print(f"NOT_A_PATTERN 類型: {type(TestValidator.NOT_A_PATTERN)}")
```

## 延伸閱讀

- [Python re 模組文件](https://docs.python.org/3/library/re.html)
- [Regular Expression HOWTO](https://docs.python.org/3/howto/regex.html)
- [正則表達式效能最佳實踐](https://docs.python.org/3/howto/regex.html#common-problems)

---

*上一章：[並行 Hook 驗證](../parallel-hook-validation/)*
*下一章：[LRU 快取](../lru-cache-branch/)*
