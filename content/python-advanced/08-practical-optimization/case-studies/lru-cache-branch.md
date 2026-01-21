---
title: "案例：LRU 快取"
date: 2026-01-21
description: "用 functools.lru_cache 快取重複計算"
weight: 4
---

# 案例：LRU 快取

本案例基於 `.claude/lib/git_utils.py` 的 `is_protected_branch()` 和 `is_allowed_branch()` 函式，展示如何用 `functools.lru_cache` 快取重複的分支檢查結果。

## 先備知識

- [入門系列 3.8 效能優化](../../../../python/03-stdlib/performance/)
- 基本的 Git 分支概念

## 問題背景

### 現有設計

`git_utils.py` 提供兩個分支檢查函式：

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

# 允許編輯的分支模式
ALLOWED_BRANCHES = [
    "feat/*",
    "feature/*",
    "fix/*",
    "hotfix/*",
    "bugfix/*",
    "chore/*",
    "docs/*",
    "refactor/*",
    "test/*",
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

def is_allowed_branch(branch: str) -> bool:
    """
    檢查是否為允許編輯的分支

    Args:
        branch: 分支名稱

    Returns:
        bool: 如果是允許編輯的分支返回 True
    """
    for pattern in ALLOWED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False
```

### 這個設計的優點

1. **簡單直覺**：迴圈遍歷模式清單，易於理解
2. **彈性高**：支援 glob 模式，可輕易新增規則
3. **無狀態**：純函數，沒有副作用

### 重複計算的開銷

在 Hook 驗證流程中，同一個分支可能被檢查多次：

```python
def validate_hook(hook_config: dict) -> list[str]:
    """驗證 Hook 配置"""
    errors = []
    branch = get_current_branch()

    # 第一次檢查：是否允許執行
    if is_protected_branch(branch):
        errors.append("Cannot run on protected branch")

    # ... 其他驗證邏輯 ...

    # 第二次檢查：是否需要額外確認
    if is_protected_branch(branch) and hook_config.get("dangerous"):
        errors.append("Dangerous operation on protected branch")

    return errors

def process_multiple_hooks(hooks: list[dict]) -> None:
    """處理多個 Hook"""
    branch = get_current_branch()

    for hook in hooks:
        # 每個 Hook 都會檢查分支
        if not is_allowed_branch(branch):
            continue

        # 再次檢查保護狀態
        if is_protected_branch(branch):
            # ... 特殊處理 ...
            pass
```

**問題分析**：

- 同一個分支名稱被重複檢查多次
- 每次檢查都要遍歷整個模式清單
- `fnmatch.fnmatch()` 雖然快，但重複呼叫仍是浪費

**測量重複呼叫的影響**：

```python
import time

def benchmark_repeated_calls(branch: str, iterations: int = 10000) -> float:
    """測量重複呼叫的時間"""
    start = time.perf_counter()

    for _ in range(iterations):
        is_protected_branch(branch)
        is_allowed_branch(branch)

    return time.perf_counter() - start

# 測量結果
# 10000 次呼叫: ~0.05 秒
# 每次呼叫: ~5 微秒

# 看起來很快，但如果在熱路徑上...
# 100 個 Hook x 10 次檢查 = 1000 次呼叫
# 累積起來就有影響了
```

## 進階解決方案

### lru_cache 基礎

`functools.lru_cache` 是 Python 內建的記憶化（memoization）裝飾器：

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function(x: int) -> int:
    """結果會被快取"""
    return x * 2

# 第一次呼叫：實際計算
result1 = expensive_function(10)  # 計算並快取

# 第二次呼叫：直接返回快取結果
result2 = expensive_function(10)  # 從快取讀取
```

**lru_cache 的適用條件**：

1. **純函數**：相同輸入永遠產生相同輸出
2. **可雜湊參數**：所有參數必須是 hashable（可作為 dict 的 key）
3. **沒有副作用**：函數不應修改外部狀態
4. **計算成本 > 快取成本**：快取有記憶體開銷，要值得

**檢查 `is_protected_branch` 是否適用**：

```python
# 1. 純函數？
#    是 - 相同分支名稱永遠返回相同結果
#    （前提：PROTECTED_BRANCHES 不會在執行時改變）

# 2. 可雜湊參數？
#    是 - str 是 hashable

# 3. 沒有副作用？
#    是 - 只讀取全域常數，不修改任何狀態

# 4. 計算成本值得快取？
#    要測量...
```

### 實作步驟

#### 步驟 1：加入 lru_cache 裝飾器

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

ALLOWED_BRANCHES = [
    "feat/*",
    "feature/*",
    "fix/*",
    "hotfix/*",
    "bugfix/*",
    "chore/*",
    "docs/*",
    "refactor/*",
    "test/*",
]

@lru_cache(maxsize=128)
def is_protected_branch(branch: str) -> bool:
    """
    檢查是否為保護分支（帶快取）

    Args:
        branch: 分支名稱

    Returns:
        bool: 如果是保護分支返回 True

    Note:
        結果會被快取，快取大小為 128 個不同的分支名稱。
        如果 PROTECTED_BRANCHES 在執行時改變，需要呼叫
        is_protected_branch.cache_clear() 清除快取。
    """
    for pattern in PROTECTED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False

@lru_cache(maxsize=128)
def is_allowed_branch(branch: str) -> bool:
    """
    檢查是否為允許編輯的分支（帶快取）

    Args:
        branch: 分支名稱

    Returns:
        bool: 如果是允許編輯的分支返回 True

    Note:
        結果會被快取。修改 ALLOWED_BRANCHES 後需要
        呼叫 is_allowed_branch.cache_clear()。
    """
    for pattern in ALLOWED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False
```

#### 步驟 2：驗證快取行為

```python
def verify_cache_behavior():
    """驗證快取確實在運作"""
    # 清除快取，確保乾淨狀態
    is_protected_branch.cache_clear()

    # 第一次呼叫
    result1 = is_protected_branch("main")
    info1 = is_protected_branch.cache_info()
    print(f"第一次呼叫: hits={info1.hits}, misses={info1.misses}")
    # 輸出: hits=0, misses=1

    # 第二次呼叫（相同參數）
    result2 = is_protected_branch("main")
    info2 = is_protected_branch.cache_info()
    print(f"第二次呼叫: hits={info2.hits}, misses={info2.misses}")
    # 輸出: hits=1, misses=1

    # 不同參數
    result3 = is_protected_branch("feature/new")
    info3 = is_protected_branch.cache_info()
    print(f"不同參數: hits={info3.hits}, misses={info3.misses}")
    # 輸出: hits=1, misses=2

verify_cache_behavior()
```

### maxsize 的選擇

`maxsize` 決定快取可以儲存多少個不同的輸入結果：

```python
# maxsize=None：無限制快取
# 優點：所有結果都快取，命中率最高
# 缺點：記憶體可能無限增長

@lru_cache(maxsize=None)
def unlimited_cache(x):
    return x * 2

# maxsize=128（預設）：快取最多 128 個結果
# LRU = Least Recently Used，超過時淘汰最久未使用的

@lru_cache(maxsize=128)
def limited_cache(x):
    return x * 2

# maxsize=1：只快取最後一個結果
# 適用於「連續呼叫通常是相同參數」的情況

@lru_cache(maxsize=1)
def single_cache(x):
    return x * 2
```

**選擇策略**：

```python
def choose_maxsize():
    """
    選擇 maxsize 的考量因素
    """
    # 因素 1：輸入值的多樣性
    # - 分支名稱通常不多（< 100 種）
    # - 單一專案可能只有 10-20 個分支
    # - maxsize=128 綽綽有餘

    # 因素 2：記憶體使用
    # - 每個快取項目: key + value + overhead
    # - str 的 key 大小視長度而定
    # - bool 的 value 很小
    # - 128 個項目 < 10KB，可忽略

    # 因素 3：呼叫模式
    # - 如果同一個分支會被檢查很多次 → 大 maxsize
    # - 如果每次都是新分支 → 快取沒意義

    # 對於分支檢查：
    # - 通常會重複檢查目前分支
    # - maxsize=32 或 64 就足夠
    # - 用 128 是保守選擇
    pass
```

**實際測量 maxsize 的影響**：

```python
from functools import lru_cache
import random
import time

def benchmark_maxsize():
    """比較不同 maxsize 的效能"""

    # 模擬分支名稱
    branches = [
        "main", "master", "develop",
        "feature/auth", "feature/api", "feature/ui",
        "fix/bug1", "fix/bug2", "fix/bug3",
        "release/v1.0", "release/v2.0",
    ]

    # 模擬呼叫模式：80% 是常見分支，20% 是其他
    common_branches = branches[:3]

    def simulate_calls(func, iterations=10000):
        for _ in range(iterations):
            if random.random() < 0.8:
                branch = random.choice(common_branches)
            else:
                branch = random.choice(branches)
            func(branch)
        return func.cache_info()

    # 測試不同 maxsize
    for maxsize in [1, 4, 16, 64, 128, None]:
        @lru_cache(maxsize=maxsize)
        def test_func(branch):
            for pattern in PROTECTED_BRANCHES:
                if fnmatch.fnmatch(branch, pattern):
                    return True
            return False

        info = simulate_calls(test_func)
        hit_rate = info.hits / (info.hits + info.misses) * 100

        print(f"maxsize={str(maxsize):>4}: "
              f"hit_rate={hit_rate:.1f}%, "
              f"size={info.currsize}")

# 輸出範例:
# maxsize=   1: hit_rate=65.2%, size=1
# maxsize=   4: hit_rate=92.8%, size=4
# maxsize=  16: hit_rate=99.9%, size=11
# maxsize=  64: hit_rate=99.9%, size=11
# maxsize= 128: hit_rate=99.9%, size=11
# maxsize=None: hit_rate=99.9%, size=11
```

**結論**：對於分支檢查，`maxsize=32` 就足夠。用 `maxsize=128` 是安全的預設值。

### 快取命中率分析

`cache_info()` 提供詳細的快取統計：

```python
def analyze_cache_performance():
    """分析快取效能"""
    # 模擬一個 Hook 驗證流程
    is_protected_branch.cache_clear()
    is_allowed_branch.cache_clear()

    # 模擬驗證 50 個 Hook，每個 Hook 檢查 2 次
    branch = "feature/new-feature"

    for _ in range(50):
        # 每個 Hook 的驗證邏輯
        is_protected_branch(branch)
        is_allowed_branch(branch)

        # 某些 Hook 會再次檢查
        if not is_protected_branch(branch):
            is_allowed_branch(branch)

    # 分析結果
    protected_info = is_protected_branch.cache_info()
    allowed_info = is_allowed_branch.cache_info()

    print("=== 快取效能分析 ===")
    print(f"\nis_protected_branch:")
    print(f"  命中: {protected_info.hits}")
    print(f"  未命中: {protected_info.misses}")
    print(f"  命中率: {protected_info.hits / (protected_info.hits + protected_info.misses) * 100:.1f}%")
    print(f"  快取大小: {protected_info.currsize}/{protected_info.maxsize}")

    print(f"\nis_allowed_branch:")
    print(f"  命中: {allowed_info.hits}")
    print(f"  未命中: {allowed_info.misses}")
    print(f"  命中率: {allowed_info.hits / (allowed_info.hits + allowed_info.misses) * 100:.1f}%")
    print(f"  快取大小: {allowed_info.currsize}/{allowed_info.maxsize}")

# 輸出:
# === 快取效能分析 ===
#
# is_protected_branch:
#   命中: 99
#   未命中: 1
#   命中率: 99.0%
#   快取大小: 1/128
#
# is_allowed_branch:
#   命中: 99
#   未命中: 1
#   命中率: 99.0%
#   快取大小: 1/128
```

**命中率解讀**：

| 命中率 | 意義 | 建議 |
|--------|------|------|
| > 90% | 快取非常有效 | 保持現狀 |
| 70-90% | 快取有幫助 | 可考慮增加 maxsize |
| 50-70% | 效果有限 | 檢查呼叫模式 |
| < 50% | 快取可能沒意義 | 考慮移除快取 |

## 完整程式碼

```python
#!/usr/bin/env python3
"""
分支檢查工具 - 帶 LRU 快取

展示如何用 functools.lru_cache 優化重複的分支檢查。
"""

from functools import lru_cache
import fnmatch
from typing import Callable

# ===== 分支配置常數 =====

PROTECTED_BRANCHES = [
    "main",
    "master",
    "develop",
    "release/*",
    "production",
]

ALLOWED_BRANCHES = [
    "feat/*",
    "feature/*",
    "fix/*",
    "hotfix/*",
    "bugfix/*",
    "chore/*",
    "docs/*",
    "refactor/*",
    "test/*",
]

# ===== 帶快取的檢查函式 =====

@lru_cache(maxsize=128)
def is_protected_branch(branch: str) -> bool:
    """
    檢查是否為保護分支（帶快取）

    Args:
        branch: 分支名稱

    Returns:
        bool: 如果是保護分支返回 True

    Example:
        >>> is_protected_branch("main")
        True
        >>> is_protected_branch("feature/new")
        False
    """
    for pattern in PROTECTED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False

@lru_cache(maxsize=128)
def is_allowed_branch(branch: str) -> bool:
    """
    檢查是否為允許編輯的分支（帶快取）

    Args:
        branch: 分支名稱

    Returns:
        bool: 如果是允許編輯的分支返回 True

    Example:
        >>> is_allowed_branch("feat/new-feature")
        True
        >>> is_allowed_branch("random-branch")
        False
    """
    for pattern in ALLOWED_BRANCHES:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False

# ===== 快取管理工具 =====

def clear_branch_caches() -> None:
    """
    清除所有分支檢查快取

    當 PROTECTED_BRANCHES 或 ALLOWED_BRANCHES 在執行時
    被修改時，需要呼叫此函式。

    Example:
        >>> PROTECTED_BRANCHES.append("staging")
        >>> clear_branch_caches()  # 清除舊的快取結果
    """
    is_protected_branch.cache_clear()
    is_allowed_branch.cache_clear()

def get_cache_stats() -> dict:
    """
    獲取快取統計資訊

    Returns:
        dict: 包含兩個函式的快取統計

    Example:
        >>> stats = get_cache_stats()
        >>> print(f"protected hit rate: {stats['protected']['hit_rate']:.1f}%")
    """
    protected = is_protected_branch.cache_info()
    allowed = is_allowed_branch.cache_info()

    def calc_hit_rate(info):
        total = info.hits + info.misses
        return info.hits / total * 100 if total > 0 else 0.0

    return {
        "protected": {
            "hits": protected.hits,
            "misses": protected.misses,
            "hit_rate": calc_hit_rate(protected),
            "size": protected.currsize,
            "maxsize": protected.maxsize,
        },
        "allowed": {
            "hits": allowed.hits,
            "misses": allowed.misses,
            "hit_rate": calc_hit_rate(allowed),
            "size": allowed.currsize,
            "maxsize": allowed.maxsize,
        },
    }

def print_cache_stats() -> None:
    """印出快取統計的格式化報告"""
    stats = get_cache_stats()

    print("=== 分支檢查快取統計 ===")

    for name, info in stats.items():
        print(f"\n{name}:")
        print(f"  命中: {info['hits']}, 未命中: {info['misses']}")
        print(f"  命中率: {info['hit_rate']:.1f}%")
        print(f"  快取大小: {info['size']}/{info['maxsize']}")

# ===== 效能比較工具 =====

def benchmark_with_without_cache(
    branches: list[str],
    iterations: int = 1000
) -> dict:
    """
    比較有無快取的效能差異

    Args:
        branches: 要測試的分支列表
        iterations: 每個分支的呼叫次數

    Returns:
        dict: 效能比較結果
    """
    import time

    # 無快取版本
    def is_protected_no_cache(branch: str) -> bool:
        for pattern in PROTECTED_BRANCHES:
            if fnmatch.fnmatch(branch, pattern):
                return True
        return False

    # 測試無快取版本
    start = time.perf_counter()
    for branch in branches:
        for _ in range(iterations):
            is_protected_no_cache(branch)
    no_cache_time = time.perf_counter() - start

    # 清除快取，測試有快取版本
    is_protected_branch.cache_clear()

    start = time.perf_counter()
    for branch in branches:
        for _ in range(iterations):
            is_protected_branch(branch)
    with_cache_time = time.perf_counter() - start

    return {
        "no_cache_time": no_cache_time,
        "with_cache_time": with_cache_time,
        "speedup": no_cache_time / with_cache_time,
        "cache_info": is_protected_branch.cache_info(),
    }

# ===== 示範 =====

if __name__ == "__main__":
    import random

    print("=== LRU 快取示範 ===\n")

    # 測試分支
    test_branches = [
        "main",
        "feature/auth",
        "fix/bug-123",
        "develop",
        "chore/cleanup",
        "release/v1.0",
    ]

    # 模擬重複呼叫
    print("1. 模擬 Hook 驗證流程（100 次迭代）:")
    clear_branch_caches()

    for _ in range(100):
        branch = random.choice(test_branches)
        is_protected_branch(branch)
        is_allowed_branch(branch)

    print_cache_stats()

    # 效能比較
    print("\n2. 效能比較:")
    result = benchmark_with_without_cache(test_branches, iterations=10000)

    print(f"  無快取: {result['no_cache_time']:.4f}s")
    print(f"  有快取: {result['with_cache_time']:.4f}s")
    print(f"  加速比: {result['speedup']:.1f}x")
    print(f"  快取命中率: {result['cache_info'].hits / (result['cache_info'].hits + result['cache_info'].misses) * 100:.1f}%")
```

## 設計權衡

| 面向 | 無快取 | lru_cache |
|------|--------|-----------|
| 記憶體使用 | 無額外開銷 | 每個不同輸入一個快取項目 |
| 首次呼叫 | 直接計算 | 計算 + 快取開銷 |
| 重複呼叫 | 每次都計算 | O(1) 查表 |
| 程式碼複雜度 | 最簡單 | 加一行裝飾器 |
| 正確性風險 | 無 | 配置變更時需清除快取 |
| 可測試性 | 直接測試 | 需考慮快取狀態 |
| 執行緒安全 | 是 | 是（lru_cache 內建鎖） |

### 何時不該用快取

**情況 1：函數不是純函數**

```python
import os

# 錯誤示範：結果依賴外部狀態
@lru_cache(maxsize=128)
def get_env_value(key: str) -> str:
    return os.environ.get(key, "")

# 問題：環境變數改變後，快取還是返回舊值
os.environ["MY_VAR"] = "old"
print(get_env_value("MY_VAR"))  # "old"

os.environ["MY_VAR"] = "new"
print(get_env_value("MY_VAR"))  # 仍然是 "old"！
```

**情況 2：參數不可雜湊**

```python
# 錯誤示範：list 不是 hashable
@lru_cache(maxsize=128)
def process_items(items: list) -> int:  # TypeError!
    return sum(items)

# 解法：用 tuple 代替 list
@lru_cache(maxsize=128)
def process_items(items: tuple) -> int:
    return sum(items)
```

**情況 3：計算太簡單**

```python
# 不建議：快取開銷可能大於計算成本
@lru_cache(maxsize=128)
def is_empty(s: str) -> bool:
    return len(s) == 0

# len() 和 == 操作非常快
# 快取的雜湊計算和查表可能更慢
```

**情況 4：輸入值極度多樣**

```python
# 不建議：每次輸入都不同，快取永遠不會命中
@lru_cache(maxsize=128)
def process_unique_id(unique_id: str) -> dict:
    # 如果 unique_id 每次都不同...
    return {"id": unique_id}

# 快取只會一直 miss，浪費記憶體
```

**情況 5：需要即時反映外部變化**

```python
# 不建議：配置可能動態變化
@lru_cache(maxsize=128)
def is_feature_enabled(feature: str) -> bool:
    # 從資料庫讀取 feature flag
    return db.get_feature_flag(feature)

# 問題：資料庫更新後，快取還是返回舊值
# 需要額外的快取失效機制
```

## 什麼時候該用這個技術？

**適合使用 lru_cache**：

- 純函數（相同輸入，相同輸出）
- 會被重複呼叫，且輸入值有限
- 計算成本明顯高於雜湊和查表
- 配置是靜態的，不會在執行時改變

**不適合使用**：

- 函數有副作用或依賴外部狀態
- 參數不可雜湊（list、dict、set）
- 每次輸入都不同（如 UUID、時間戳）
- 計算非常簡單（如 `len()`、`+`）

**快速決策流程**：

```text
函數是純函數嗎？
├── 否 → 不要用 lru_cache
└── 是 → 參數都是 hashable 嗎？
         ├── 否 → 轉換成 hashable（如 tuple）或不用
         └── 是 → 會被重複呼叫嗎？
                  ├── 否 → 不需要快取
                  └── 是 → 適合用 lru_cache
```

## 練習

### 基礎練習

1. **測量快取效益**：在你的專案中找一個被重複呼叫的純函數，加入 `lru_cache`，比較效能差異。

2. **監控快取狀態**：寫一個裝飾器，在每次呼叫後印出 `cache_info()`，觀察快取行為。

### 進階練習

3. **帶 TTL 的快取**：實作一個有過期時間的快取裝飾器。提示：可以結合 `time.time()` 和 `lru_cache`。

```python
from functools import lru_cache, wraps
import time

def timed_lru_cache(seconds: int, maxsize: int = 128):
    """
    帶過期時間的 LRU 快取

    Args:
        seconds: 快取過期秒數
        maxsize: 快取大小

    用法：
        @timed_lru_cache(seconds=60)
        def fetch_data(url):
            ...
    """
    def decorator(func):
        # 你的實作
        pass
    return decorator
```

4. **快取命中率監控**：建立一個監控系統，追蹤多個快取函式的命中率，當命中率低於閾值時發出警告。

### 挑戰題

5. **動態配置的快取失效**：修改 `is_protected_branch`，支援在執行時新增保護分支，並自動失效相關快取（而不是清除所有快取）。

提示：考慮用 `typed=True` 選項，或自訂快取類別。

---

*上一章：[正則表達式預編譯](../regex-precompile/)*
*下一章：[資料結構選擇](../data-structure-choice/)*
