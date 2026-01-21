---
title: "8.2 效能調優實戰"
date: 2026-01-21
description: "測量、分析、優化的完整流程"
weight: 2
---

# 效能調優實戰

在入門系列中，我們學習了效能優化的原則和工具。本章將這些知識應用於 `.claude/lib` 的實際程式碼，展示如何從「發現問題」到「驗證效果」的完整流程。

## 學習目標

完成本章後，你將能夠：

1. 使用 cProfile 分析真實程式碼的效能瓶頸
2. 判斷哪些程式碼值得優化
3. 應用正則表達式預編譯提升效能
4. 使用 `functools.lru_cache` 實現有效的快取策略
5. 根據查詢模式選擇適當的資料結構

## 先備知識

本章假設你已經閱讀：

- [入門系列 3.8 效能迷思與優化策略](/python/03-stdlib/performance/) - 效能測量工具與優化原則

如果你還不熟悉 `cProfile`、`timeit` 或「過早優化是萬惡之源」這句話的含義，請先閱讀入門系列。

## 效能分析流程

優化的正確流程是：

```text
1. 測量基準效能
       ↓
2. 找出瓶頸（cProfile）
       ↓
3. 針對瓶頸優化
       ↓
4. 驗證優化效果
       ↓
5. 評估維護成本
```

最重要的原則：**先測量，後優化**。沒有測量數據的優化是盲目的。

### 真實案例：Hook 驗證器

我們以 `.claude/lib/hook_validator.py` 為例。這個工具用來驗證 Hook 腳本是否符合專案規範，核心功能是透過正則表達式檢查程式碼內容。

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

    # ... 更多模式 ...

    def _has_import(self, content: str, patterns: list[str]) -> bool:
        """檢查是否有符合任一模式的導入"""
        return any(
            re.search(pattern, content)
            for pattern in patterns
        )
```

這段程式碼有什麼效能問題？讓我們用 cProfile 來找出答案。

## 步驟 1：測量基準效能

首先，建立測試環境並測量原始版本的效能：

```python
import cProfile
import pstats
import re
from pstats import SortKey

def generate_test_content(num_lines: int = 500) -> str:
    """生成測試用的 Hook 腳本內容"""
    lines = [
        '#!/usr/bin/env python3',
        '"""Test hook script"""',
        'import os',
        'import sys',
        'from hook_io import read_hook_input, write_hook_output',
        'from hook_logging import setup_hook_logging',
        '',
    ]

    # 加入更多程式碼行
    for i in range(num_lines):
        if i % 10 == 0:
            lines.append(f'def function_{i}():')
            lines.append(f'    """Function {i}"""')
        lines.append(f'    x_{i} = {i}')

    return '\n'.join(lines)

def benchmark_original(content: str, iterations: int = 100):
    """測量原始版本的效能"""

    # 原始實作：每次呼叫都重新編譯正則表達式
    patterns = [
        r"from\s+hook_io\s+import",
        r"from\s+lib\.hook_io\s+import",
    ]

    def has_import_original(content: str, patterns: list[str]) -> bool:
        return any(
            re.search(pattern, content)
            for pattern in patterns
        )

    # 執行效能分析
    profiler = cProfile.Profile()
    profiler.enable()

    for _ in range(iterations):
        has_import_original(content, patterns)

    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.sort_stats(SortKey.CUMULATIVE)
    stats.print_stats(10)

    return stats

# 執行測試
content = generate_test_content(1000)
print("=== 原始版本效能 ===")
benchmark_original(content)
```

執行後的輸出類似：

```text
=== 原始版本效能 ===
         501 function calls in 0.0234 seconds

   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      100    0.001    0.000    0.023    0.000 test.py:30(has_import_original)
      200    0.022    0.000    0.022    0.000 {method 'search' of 're.Pattern'}
      100    0.000    0.000    0.000    0.000 {built-in method builtins.any}
```

觀察結果：`re.search` 佔用了大部分時間。

## 步驟 2：找出瓶頸

從 cProfile 結果可以看到，`re.search` 被呼叫了 200 次（100 次迭代 x 2 個 pattern）。

問題在於：**`re.search(pattern, content)` 每次呼叫時都會重新編譯正則表達式**。

雖然 Python 的 `re` 模組有內部快取（最近使用的 pattern 會被快取），但：

1. 快取有大小限制（預設 512 個）
2. 查詢快取本身也有開銷
3. 在 Hook 驗證器中有多達 20+ 個不同的 pattern

## 正則表達式預編譯

### 問題：重複編譯的開銷

來看 `hook_validator.py` 中的實際程式碼：

```python
class HookValidator:
    """Hook 合規性驗證器"""

    # 模式定義為字串列表
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

    def _has_import(self, content: str, patterns: list[str]) -> bool:
        """檢查是否有符合任一模式的導入"""
        return any(
            re.search(pattern, content)  # 每次都要編譯！
            for pattern in patterns
        )
```

每次呼叫 `_has_import` 時，所有 pattern 都會被重新處理。

### 解決方案：預編譯

將字串 pattern 改為預編譯的 `re.Pattern` 物件：

```python
import re
from typing import Pattern

class HookValidatorOptimized:
    """優化版 Hook 驗證器"""

    # 預編譯的正則表達式模式
    HOOK_IO_PATTERNS: list[Pattern] = [
        re.compile(r"from\s+hook_io\s+import"),
        re.compile(r"from\s+lib\.hook_io\s+import"),
    ]

    HOOK_LOGGING_PATTERNS: list[Pattern] = [
        re.compile(r"from\s+hook_logging\s+import"),
        re.compile(r"from\s+lib\.hook_logging\s+import"),
    ]

    CONFIG_LOADER_PATTERNS: list[Pattern] = [
        re.compile(r"from\s+config_loader\s+import"),
        re.compile(r"from\s+lib\.config_loader\s+import"),
    ]

    GIT_UTILS_PATTERNS: list[Pattern] = [
        re.compile(r"from\s+git_utils\s+import"),
        re.compile(r"from\s+lib\.git_utils\s+import"),
    ]

    OUTPUT_PATTERNS: list[Pattern] = [
        re.compile(r"write_hook_output\s*\("),
        re.compile(r"create_pretooluse_output\s*\("),
        re.compile(r"create_posttooluse_output\s*\("),
    ]

    BAD_OUTPUT_PATTERNS: list[Pattern] = [
        re.compile(r'print\s*\(\s*json\.dumps\s*\('),
        re.compile(r'sys\.stdout\.write\s*\(\s*json\.dumps\s*\('),
    ]

    def _has_import(self, content: str, patterns: list[Pattern]) -> bool:
        """檢查是否有符合任一模式的導入"""
        return any(
            pattern.search(content)  # 直接使用預編譯的 pattern
            for pattern in patterns
        )
```

### 效能測量

比較預編譯和非預編譯的效能差異：

```python
import re
import time

def compare_regex_performance():
    """比較預編譯 vs 非預編譯的效能"""

    content = generate_test_content(1000)
    iterations = 1000

    # 字串 pattern
    str_patterns = [
        r"from\s+hook_io\s+import",
        r"from\s+lib\.hook_io\s+import",
    ]

    # 預編譯 pattern
    compiled_patterns = [re.compile(p) for p in str_patterns]

    # 測試 1：使用字串 pattern
    start = time.perf_counter()
    for _ in range(iterations):
        any(re.search(p, content) for p in str_patterns)
    str_time = time.perf_counter() - start

    # 測試 2：使用預編譯 pattern
    start = time.perf_counter()
    for _ in range(iterations):
        any(p.search(content) for p in compiled_patterns)
    compiled_time = time.perf_counter() - start

    print(f"字串 pattern:    {str_time:.4f}s")
    print(f"預編譯 pattern:  {compiled_time:.4f}s")
    print(f"加速比:          {str_time / compiled_time:.2f}x")

compare_regex_performance()
```

典型輸出：

```text
字串 pattern:    0.1234s
預編譯 pattern:  0.0987s
加速比:          1.25x
```

在這個例子中，預編譯帶來約 20-30% 的效能提升。雖然不是「快 10 倍」的驚人結果，但：

1. **改動成本極低**：只需要加上 `re.compile()`
2. **無風險**：行為完全相同
3. **累積效果**：當有更多 pattern 時，效果更明顯

## 快取策略：lru_cache

### 適用場景

`functools.lru_cache` 適合用於：

1. **純函式**：相同輸入總是產生相同輸出
2. **計算昂貴**：函式執行需要較長時間
3. **重複呼叫**：同樣的參數會被多次呼叫

### 實作範例：分支保護檢查

來看 `.claude/lib/git_utils.py` 中的 `is_protected_branch()` 函式：

```python
import fnmatch

# 保護分支列表（支援 glob 模式）
PROTECTED_BRANCHES = [
    "main",
    "master",
    "develop",
    "release/*",
    "production",
]

def is_protected_branch(branch: str) -> bool:
    """
    檢查是否為保護分支

    Args:
        branch: 分支名稱

    Returns:
        bool: 如果是保護分支返回 True
    """
    for pattern in PROTECTED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False
```

這個函式：

- **是純函式**：相同的 `branch` 總是返回相同結果
- **會被重複呼叫**：在 Hook 執行期間可能檢查同一個分支多次

### 加入 lru_cache

```python
from functools import lru_cache
import fnmatch

PROTECTED_BRANCHES = [
    "main",
    "master",
    "develop",
    "release/*",
    "production",
]

@lru_cache(maxsize=128)
def is_protected_branch(branch: str) -> bool:
    """
    檢查是否為保護分支（帶快取）

    Args:
        branch: 分支名稱

    Returns:
        bool: 如果是保護分支返回 True
    """
    for pattern in PROTECTED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False
```

### 快取命中率分析

```python
from functools import lru_cache
import fnmatch

@lru_cache(maxsize=128)
def is_protected_branch(branch: str) -> bool:
    for pattern in PROTECTED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False

def analyze_cache_performance():
    """分析快取命中率"""

    # 模擬真實的呼叫模式
    branches = [
        "main", "main", "main",  # 重複檢查 main
        "feat/new-feature",
        "main",
        "fix/bug-123",
        "main",
        "release/1.0",
        "feat/new-feature",  # 重複
    ]

    # 清除快取統計
    is_protected_branch.cache_clear()

    for branch in branches:
        result = is_protected_branch(branch)
        print(f"檢查 {branch}: {result}")

    # 查看快取統計
    info = is_protected_branch.cache_info()
    print(f"\n快取統計:")
    print(f"  命中: {info.hits}")
    print(f"  未命中: {info.misses}")
    print(f"  命中率: {info.hits / (info.hits + info.misses) * 100:.1f}%")
    print(f"  快取大小: {info.currsize}/{info.maxsize}")

analyze_cache_performance()
```

輸出：

```text
檢查 main: True
檢查 main: True
檢查 main: True
檢查 feat/new-feature: False
檢查 main: True
檢查 fix/bug-123: False
檢查 main: True
檢查 release/1.0: True
檢查 feat/new-feature: False

快取統計:
  命中: 5
  未命中: 4
  命中率: 55.6%
  快取大小: 4/128
```

### lru_cache 的注意事項

```python
# 1. 參數必須是可雜湊的（hashable）
@lru_cache
def process(data: list):  # 錯誤！list 不可雜湊
    pass

@lru_cache
def process(data: tuple):  # 正確，tuple 可雜湊
    pass

# 2. 注意快取大小
@lru_cache(maxsize=None)  # 無限制，可能耗盡記憶體
def expensive_function(x):
    pass

@lru_cache(maxsize=128)  # 建議設定合理上限
def expensive_function(x):
    pass

# 3. 可以手動清除快取
expensive_function.cache_clear()

# 4. 查看快取統計
info = expensive_function.cache_info()
# CacheInfo(hits=10, misses=5, maxsize=128, currsize=5)
```

## 資料結構選擇

### O(n) vs O(1) 的差異

在 `hook_validator.py` 中，檢查測試檔案是否存在：

```python
def check_test_exists(self, hook_path: Path) -> list[ValidationIssue]:
    """檢查對應的測試檔案是否存在"""
    issues = []

    hook_name = hook_path.stem
    test_name = f"test_{hook_name.replace('-', '_')}.py"

    # 測試檔案可能在這些位置
    possible_test_paths = [
        self.project_root / ".claude" / "lib" / "tests" / test_name,
        self.project_root / ".claude" / "hooks" / "tests" / test_name,
    ]

    test_exists = any(p.exists() for p in possible_test_paths)
    # ...
```

如果需要檢查多個檔案是否在某個集合中：

```python
# 不好的做法：用 list，O(n) 查詢
existing_tests = [
    "test_branch_verify.py",
    "test_hook_io.py",
    "test_config_loader.py",
    # ... 可能有幾十個
]

def has_test_slow(test_name: str) -> bool:
    return test_name in existing_tests  # O(n)

# 好的做法：用 set，O(1) 查詢
existing_tests_set = {
    "test_branch_verify.py",
    "test_hook_io.py",
    "test_config_loader.py",
    # ...
}

def has_test_fast(test_name: str) -> bool:
    return test_name in existing_tests_set  # O(1)
```

### 真實案例：測試檔案存在性檢查

```python
import time
from pathlib import Path

def compare_data_structures():
    """比較 list vs set 的查詢效能"""

    # 模擬測試檔案列表
    test_files_list = [f"test_hook_{i}.py" for i in range(100)]
    test_files_set = set(test_files_list)

    # 要查詢的檔案
    queries = [f"test_hook_{i}.py" for i in range(50, 150)]  # 50 個存在，50 個不存在

    iterations = 10000

    # 測試 list
    start = time.perf_counter()
    for _ in range(iterations):
        for q in queries:
            _ = q in test_files_list
    list_time = time.perf_counter() - start

    # 測試 set
    start = time.perf_counter()
    for _ in range(iterations):
        for q in queries:
            _ = q in test_files_set
    set_time = time.perf_counter() - start

    print(f"List 查詢: {list_time:.4f}s")
    print(f"Set 查詢:  {set_time:.4f}s")
    print(f"加速比:    {list_time / set_time:.1f}x")

compare_data_structures()
```

輸出：

```text
List 查詢: 0.8234s
Set 查詢:  0.0123s
加速比:    66.9x
```

當資料量為 100 個元素時，set 比 list 快約 60-70 倍。隨著資料量增加，差距會更大。

### 何時使用哪種資料結構

| 操作 | list | set | dict |
|------|------|-----|------|
| 查詢元素是否存在 | O(n) | O(1) | O(1) |
| 依索引存取 | O(1) | N/A | N/A |
| 依鍵存取 | N/A | N/A | O(1) |
| 保持順序 | Yes | No* | Yes** |
| 允許重複 | Yes | No | Keys: No |

\* Python 3.7+ 的 set 實際上保持插入順序，但這是實作細節，不是語言保證。
\** Python 3.7+ 的 dict 保證保持插入順序。

**選擇指南**：

- 需要頻繁查詢「是否存在」→ 用 `set`
- 需要依索引存取 → 用 `list`
- 需要鍵值對應 → 用 `dict`
- 需要去重 → 用 `set`

## 優化的代價

每個優化都有代價，需要評估是否值得。

### 維護成本

| 優化技術 | 效能提升 | 程式碼複雜度 | 維護成本 |
|----------|----------|--------------|----------|
| 正則表達式預編譯 | 20-30% | 低 | 低 |
| lru_cache | 視命中率而定 | 低 | 中（需注意快取失效） |
| list → set | 數十倍 | 低 | 低 |
| 自訂資料結構 | 視情況 | 高 | 高 |

### 何時不該優化

```python
# 不值得優化的情況

# 1. 執行次數很少
def setup_once():
    """只在程式啟動時執行一次"""
    config = load_all_configs()  # 即使慢也只執行一次
    return config

# 2. 已經夠快了
def check_single_file(path: str) -> bool:
    """檢查單一檔案是否存在"""
    return Path(path).exists()  # 0.0001s，不需要優化

# 3. I/O 才是真正的瓶頸
def process_files(paths: list[str]):
    for path in paths:
        content = Path(path).read_text()  # 瓶頸在這裡
        result = process(content)  # 這裡快 10 倍也沒用
```

### 優化前檢查清單

在優化之前，問自己：

1. **這段程式碼是瓶頸嗎？** - 用 cProfile 確認
2. **執行頻率高嗎？** - 每秒執行一次 vs 每天執行一次
3. **優化後維護成本增加多少？** - 複雜度 vs 效能
4. **有更簡單的解決方案嗎？** - 演算法改進 vs 微優化

## 思考題

1. 在什麼情況下，預編譯正則表達式反而可能降低效能？

2. `lru_cache` 不適合用在什麼樣的函式上？

3. 如果一個函式既需要快取，又需要在某些條件下強制重新計算，你會如何設計？

4. 為什麼說「先測量，後優化」很重要？能舉一個反例嗎？

## 實作練習

### 練習 1：分析現有程式碼

用 cProfile 分析你自己專案中的一段程式碼，找出效能瓶頸。

```python
import cProfile
import pstats
from pstats import SortKey

# 替換為你要分析的函式
def your_function():
    pass

profiler = cProfile.Profile()
profiler.enable()

# 執行多次以獲得可靠數據
for _ in range(100):
    your_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats(SortKey.CUMULATIVE)
stats.print_stats(10)
```

### 練習 2：實作帶統計的快取

擴展 `lru_cache`，加入更詳細的統計資訊：

```python
from functools import wraps
from typing import Callable, TypeVar
from collections import defaultdict
import time

T = TypeVar('T')

def cached_with_stats(maxsize: int = 128):
    """
    帶統計資訊的快取裝飾器

    統計項目：
    - 命中/未命中次數
    - 平均執行時間
    - 各參數的呼叫次數
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # 你的實作
        pass
    return decorator
```

### 練習 3：效能比較

比較以下三種檢查字串是否包含多個關鍵字的方法：

```python
keywords = ["error", "warning", "critical", "fatal"]

# 方法 1：多個 in 檢查
def method1(text: str) -> bool:
    return any(kw in text for kw in keywords)

# 方法 2：正則表達式
import re
pattern = re.compile("|".join(keywords))
def method2(text: str) -> bool:
    return bool(pattern.search(text))

# 方法 3：set 交集
keywords_set = set(keywords)
def method3(text: str) -> bool:
    words = set(text.lower().split())
    return bool(words & keywords_set)

# 測試並比較效能
# ...
```

## 延伸閱讀

### 入門系列

- [3.8 效能迷思與優化策略](/python/03-stdlib/performance/) - 效能優化的基礎知識

### 進階系列

- [模組四：CPython 內部機制](/python-advanced/04-cpython-internals/) - 理解 Python 執行原理
- [案例：效能分析實戰](/python-advanced/04-cpython-internals/case-studies/profiling/) - cProfile 深入應用

### 官方文件

- [cProfile 文件](https://docs.python.org/3/library/profile.html)
- [functools.lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache)
- [re.compile](https://docs.python.org/3/library/re.html#re.compile)

### 外部資源

- [High Performance Python](https://www.oreilly.com/library/view/high-performance-python/9781492055013/) - O'Reilly 書籍
- [line_profiler](https://github.com/pyutils/line_profiler) - 行級效能分析工具

---

*上一章：[並行處理實戰](../parallel-processing/)*
*下一章：[案例研究](../case-studies/)*
