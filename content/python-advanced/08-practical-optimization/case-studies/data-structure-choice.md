---
title: "案例：資料結構選擇"
date: 2026-01-21
description: "選擇正確的資料結構：list vs set 的查詢效能差異"
weight: 5
---

# 案例：資料結構選擇

本案例基於 `.claude/lib/hook_validator.py` 的實際程式碼，展示如何選擇正確的資料結構來優化成員查詢效能。

## 先備知識

- [入門系列 3.8 效能優化](../../../../python/03-stdlib/performance/)
- 基本的時間複雜度概念（O(n)、O(1)）

## 問題背景

### 成員查詢的效能差異

在 Python 中，檢查某個元素是否存在於容器中（成員查詢）是最常見的操作之一：

```python
if item in container:
    # 做某些事
```

但這行簡單的程式碼，背後的效能差異可能高達 **100 倍以上**，取決於 `container` 是什麼資料結構。

**list 的成員查詢：O(n)**

```python
my_list = [1, 2, 3, ..., n]
if x in my_list:  # 最壞情況要檢查 n 個元素
    ...
```

list 是有序的線性結構，Python 必須從頭開始逐一比對，直到找到目標或走完整個 list。

**set 的成員查詢：O(1)**

```python
my_set = {1, 2, 3, ..., n}
if x in my_set:  # 平均只需要 1 次雜湊計算
    ...
```

set 使用雜湊表（hash table）實作，透過計算元素的雜湊值直接定位，不受容器大小影響。

### 真實案例：測試檔案存在性檢查

`hook_validator.py` 的 `check_test_exists` 方法會檢查每個 Hook 是否有對應的測試檔案：

```python
def check_test_exists(self, hook_path: Path) -> List[ValidationIssue]:
    """
    檢查對應的測試檔案是否存在

    Args:
        hook_path: Hook 檔案路徑

    Returns:
        list[ValidationIssue]: 發現的問題
    """
    issues = []

    # 生成測試檔案名稱
    hook_name = hook_path.stem
    test_name = f"test_{hook_name.replace('-', '_')}.py"

    # 測試檔案應該在 .claude/lib/tests/ 或 .claude/hooks/tests/
    possible_test_paths = [
        self.project_root / ".claude" / "lib" / "tests" / test_name,
        self.project_root / ".claude" / "hooks" / "tests" / test_name,
    ]

    test_exists = any(p.exists() for p in possible_test_paths)

    if not test_exists:
        issues.append(
            ValidationIssue(
                level="info",
                message=f"未找到對應的測試檔案: {test_name}",
                suggestion=(
                    f"建議在以下位置建立測試:\n"
                    f"  .claude/lib/tests/{test_name}"
                )
            )
        )

    return issues
```

這個程式碼有一個隱藏的效能問題：當需要驗證大量 Hook 時，每次都要呼叫 `p.exists()` 進行檔案系統操作。

假設我們要驗證 100 個 Hook，而測試目錄下有 200 個測試檔案：

```python
def validate_all_hooks(self, hooks_dir: Optional[str] = None) -> List[ValidationResult]:
    """驗證所有 Hook 檔案"""
    # ... 省略部分程式碼 ...

    results = []
    for hook_file in sorted(hooks_dir.glob("*.py")):  # 100 個 Hook
        if hook_file.name.startswith("_"):
            continue
        results.append(self.validate_hook(str(hook_file)))
        # 每個 validate_hook 會呼叫 check_test_exists
        # check_test_exists 會呼叫 2 次 Path.exists()
        # 總共：100 * 2 = 200 次檔案系統操作

    return results
```

### 問題分析

原始程式碼的瓶頸：

1. **重複的檔案系統操作**：每個 Hook 都要呼叫 `exists()` 檢查測試是否存在
2. **沒有快取**：相同的檢查可能被重複執行
3. **線性搜尋**：如果測試清單很長，用 list 儲存會導致 O(n) 的查詢時間

## 進階解決方案

### 用 set 取代 list

核心思路：**先掃描一次測試目錄，建立測試檔案的 set，然後用 O(1) 查詢取代檔案系統操作**。

```python
class HookValidator:
    """Hook 合規性驗證器（優化版）"""

    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            project_root = os.environ.get(
                "CLAUDE_PROJECT_DIR",
                os.getcwd()
            )
        self.project_root = Path(project_root)

        # 優化：預先建立測試檔案的 set
        self._test_files_cache: Optional[set[str]] = None

    @property
    def test_files(self) -> set[str]:
        """
        取得所有測試檔案名稱（快取）

        Returns:
            set[str]: 測試檔案名稱集合
        """
        if self._test_files_cache is None:
            self._test_files_cache = self._scan_test_files()
        return self._test_files_cache

    def _scan_test_files(self) -> set[str]:
        """
        掃描所有測試目錄，建立測試檔案集合

        Returns:
            set[str]: 測試檔案名稱集合
        """
        test_dirs = [
            self.project_root / ".claude" / "lib" / "tests",
            self.project_root / ".claude" / "hooks" / "tests",
        ]

        test_files = set()  # 使用 set 而非 list
        for test_dir in test_dirs:
            if test_dir.is_dir():
                for test_file in test_dir.glob("test_*.py"):
                    test_files.add(test_file.name)

        return test_files

    def check_test_exists(self, hook_path: Path) -> List[ValidationIssue]:
        """
        檢查對應的測試檔案是否存在（優化版）

        使用 set 進行 O(1) 查詢，取代檔案系統操作。
        """
        issues = []

        hook_name = hook_path.stem
        test_name = f"test_{hook_name.replace('-', '_')}.py"

        # 優化：O(1) 的 set 查詢，取代 O(n) 的 exists() 呼叫
        test_exists = test_name in self.test_files

        if not test_exists:
            issues.append(
                ValidationIssue(
                    level="info",
                    message=f"未找到對應的測試檔案: {test_name}",
                    suggestion=(
                        f"建議在以下位置建立測試:\n"
                        f"  .claude/lib/tests/{test_name}"
                    )
                )
            )

        return issues
```

### 實作步驟

#### 步驟 1：識別重複查詢

找出程式碼中哪些查詢會被重複執行：

```python
# 原始程式碼：每次驗證都會執行檔案系統操作
for hook_file in hooks:
    # possible_test_paths 中的 Path.exists() 被呼叫 2 次
    test_exists = any(p.exists() for p in possible_test_paths)
```

#### 步驟 2：收集所有可能的查詢目標

在初始化時掃描一次，建立完整的資料集：

```python
def _scan_test_files(self) -> set[str]:
    """一次性掃描所有測試檔案"""
    test_files = set()

    for test_dir in test_directories:
        if test_dir.is_dir():
            for test_file in test_dir.glob("test_*.py"):
                test_files.add(test_file.name)

    return test_files
```

#### 步驟 3：用 set 取代 list

確保查詢容器是 set 而非 list：

```python
# 錯誤：用 list 儲存
test_files = []  # O(n) 查詢
for test_file in test_dir.glob("test_*.py"):
    test_files.append(test_file.name)

# 正確：用 set 儲存
test_files = set()  # O(1) 查詢
for test_file in test_dir.glob("test_*.py"):
    test_files.add(test_file.name)
```

#### 步驟 4：加入快取機制

避免重複掃描：

```python
@property
def test_files(self) -> set[str]:
    """延遲初始化 + 快取"""
    if self._test_files_cache is None:
        self._test_files_cache = self._scan_test_files()
    return self._test_files_cache

def clear_cache(self) -> None:
    """需要時可以清除快取"""
    self._test_files_cache = None
```

## 效能測量

讓我們用 `timeit` 測量 list 和 set 的查詢效能差異：

```python
import timeit
import random
import string

def benchmark_membership_test():
    """比較 list 和 set 的成員查詢效能"""

    # 準備測試資料
    def generate_filename():
        return f"test_{''.join(random.choices(string.ascii_lowercase, k=10))}.py"

    sizes = [100, 1000, 10000]

    for size in sizes:
        # 建立測試資料
        items = [generate_filename() for _ in range(size)]
        test_list = items.copy()
        test_set = set(items)

        # 準備查詢目標（一半存在、一半不存在）
        existing_items = random.sample(items, min(100, size))
        non_existing_items = [generate_filename() for _ in range(100)]
        query_items = existing_items + non_existing_items
        random.shuffle(query_items)

        # 測量 list 查詢
        def list_lookup():
            for item in query_items:
                _ = item in test_list

        list_time = timeit.timeit(list_lookup, number=100)

        # 測量 set 查詢
        def set_lookup():
            for item in query_items:
                _ = item in test_set

        set_time = timeit.timeit(set_lookup, number=100)

        # 計算加速比
        speedup = list_time / set_time

        print(f"\n元素數量: {size:,}")
        print(f"  list 查詢: {list_time:.4f} 秒")
        print(f"  set 查詢:  {set_time:.4f} 秒")
        print(f"  加速比:    {speedup:.1f}x")

if __name__ == "__main__":
    benchmark_membership_test()
```

**典型執行結果**：

```text
元素數量: 100
  list 查詢: 0.0234 秒
  set 查詢:  0.0012 秒
  加速比:    19.5x

元素數量: 1,000
  list 查詢: 0.2156 秒
  set 查詢:  0.0013 秒
  加速比:    165.8x

元素數量: 10,000
  list 查詢: 2.1847 秒
  set 查詢:  0.0014 秒
  加速比:    1560.5x
```

**觀察重點**：

1. **set 的查詢時間幾乎不變**：無論元素數量是 100 還是 10,000，set 的查詢時間都在 0.001 秒左右
2. **list 的查詢時間線性增長**：元素增加 10 倍，查詢時間也增加約 10 倍
3. **加速比隨資料量增加**：元素越多，set 的優勢越明顯

### 實際場景測試

模擬 Hook 驗證器的真實使用場景：

```python
import timeit
from pathlib import Path
from typing import Optional, List, Set

def benchmark_hook_validation():
    """模擬 Hook 驗證器的效能差異"""

    # 模擬 200 個測試檔案
    test_files_list = [f"test_hook_{i}.py" for i in range(200)]
    test_files_set = set(test_files_list)

    # 模擬 100 個 Hook 要檢查
    hooks_to_check = [f"hook_{i}" for i in range(100)]

    def check_with_list():
        """使用 list 進行查詢"""
        results = []
        for hook_name in hooks_to_check:
            test_name = f"test_{hook_name}.py"
            exists = test_name in test_files_list  # O(n)
            results.append(exists)
        return results

    def check_with_set():
        """使用 set 進行查詢"""
        results = []
        for hook_name in hooks_to_check:
            test_name = f"test_{hook_name}.py"
            exists = test_name in test_files_set  # O(1)
            results.append(exists)
        return results

    # 測量效能
    list_time = timeit.timeit(check_with_list, number=1000)
    set_time = timeit.timeit(check_with_set, number=1000)

    print(f"驗證 100 個 Hook（執行 1000 次）：")
    print(f"  list 版本: {list_time:.4f} 秒")
    print(f"  set 版本:  {set_time:.4f} 秒")
    print(f"  加速比:    {list_time / set_time:.1f}x")

if __name__ == "__main__":
    benchmark_hook_validation()
```

**典型執行結果**：

```text
驗證 100 個 Hook（執行 1000 次）：
  list 版本: 0.3892 秒
  set 版本:  0.0087 秒
  加速比:    44.7x
```

## 設計權衡

| 資料結構 | 查詢 | 插入 | 刪除 | 記憶體 | 有序 | 重複元素 |
|----------|------|------|------|--------|------|----------|
| list | O(n) | O(1)* | O(n) | 低 | 是 | 允許 |
| set | O(1) | O(1) | O(1) | 高 | 否 | 不允許 |
| dict | O(1) | O(1) | O(1) | 高 | 是** | 鍵不允許 |

*list 的 append 是 O(1)，insert 是 O(n)

**Python 3.7+ 的 dict 保持插入順序

### 記憶體使用比較

```python
import sys

def compare_memory():
    """比較 list 和 set 的記憶體使用"""
    items = list(range(10000))

    list_version = items.copy()
    set_version = set(items)

    list_size = sys.getsizeof(list_version)
    set_size = sys.getsizeof(set_version)

    print(f"10,000 個整數：")
    print(f"  list: {list_size:,} bytes")
    print(f"  set:  {set_size:,} bytes")
    print(f"  set/list 比率: {set_size / list_size:.2f}x")

# 輸出：
# 10,000 個整數：
#   list: 87,624 bytes
#   set:  524,512 bytes
#   set/list 比率: 5.99x
```

**權衡分析**：

- set 的記憶體使用約為 list 的 4-8 倍
- 但查詢速度可以快 10-100 倍以上
- 對於大多數場景，記憶體增加可以接受

### 何時該用 list？

1. **需要保持順序**：元素的順序很重要
2. **需要重複元素**：同一個值可能出現多次
3. **需要索引存取**：經常用 `items[i]` 存取
4. **主要操作是遍歷**：很少做成員查詢
5. **資料量很小**：少於 10 個元素時差異不大

```python
# 適合用 list 的場景
commands = ["init", "build", "test", "deploy"]  # 需要順序
scores = [95, 87, 95, 92, 87]  # 需要重複
```

### 何時該用 set？

1. **主要操作是成員查詢**：頻繁使用 `in` 運算子
2. **需要去重**：自動排除重複元素
3. **需要集合運算**：交集、聯集、差集
4. **資料量較大**：幾百個以上的元素

```python
# 適合用 set 的場景
valid_extensions = {".py", ".js", ".ts"}  # 成員查詢
seen_files = set()  # 追蹤已處理的檔案（去重）
common_tags = tags_a & tags_b  # 集合運算
```

## 什麼時候該用這個技術？

### 適合使用的情況

1. **頻繁的成員查詢**：程式碼中有很多 `if x in container` 的檢查
2. **查詢容器較大**：容器有幾百個以上的元素
3. **查詢頻率高**：同一個容器被查詢多次
4. **不需要元素順序**：只關心「有沒有」而非「在哪裡」

### 不建議使用的情況

1. **需要保持插入順序**：用 list 或 dict
2. **需要重複元素**：用 list 或 collections.Counter
3. **容器很小**：10 個以下元素時差異不明顯
4. **元素不可雜湊**：list、dict 等 mutable 物件無法放入 set

```python
# 不可雜湊的物件無法用 set
items = [[1, 2], [3, 4]]  # list of lists
# set(items)  # TypeError: unhashable type: 'list'

# 解法：轉換為 tuple
items_set = {tuple(item) for item in items}  # OK
```

## 練習

### 基礎練習

1. **實作去重函式**：寫一個函式，用 set 去除 list 中的重複元素，同時保持原本的順序

```python
def deduplicate_ordered(items: list) -> list:
    """
    去除重複元素，保持順序

    Example:
        >>> deduplicate_ordered([3, 1, 2, 1, 3, 2])
        [3, 1, 2]
    """
    # Your implementation here
    pass
```

2. **優化單字計數器**：以下程式碼檢查一段文字中有多少個「停用詞」，請用 set 優化它

```python
STOP_WORDS = ["the", "a", "an", "is", "are", "was", "were", "be", "been",
              "being", "have", "has", "had", "do", "does", "did", "will",
              "would", "could", "should", "may", "might", "must", "can"]

def count_stop_words_slow(text: str) -> int:
    """計算停用詞數量（待優化）"""
    words = text.lower().split()
    count = 0
    for word in words:
        if word in STOP_WORDS:  # O(n) 查詢
            count += 1
    return count

# 請優化這個函式
def count_stop_words_fast(text: str) -> int:
    """計算停用詞數量（優化版）"""
    # Your implementation here
    pass
```

### 進階練習

3. **實作檔案比對工具**：比較兩個目錄中的檔案，找出只在其中一個目錄存在的檔案

```python
from pathlib import Path

def compare_directories(dir1: Path, dir2: Path) -> dict:
    """
    比較兩個目錄的檔案

    Returns:
        dict: {
            "only_in_dir1": set[str],
            "only_in_dir2": set[str],
            "in_both": set[str],
        }

    提示：使用 set 的交集、差集運算
    """
    # Your implementation here
    pass
```

4. **優化 Hook 驗證器**：參考本文的優化方案，為 `HookValidator` 加入以下功能：

- 快取測試檔案列表
- 支援多個測試目錄
- 在測試目錄變更時自動更新快取

---

*上一章：[LRU 快取](../lru-cache-branch/)*
*返回：[案例研究索引](../)*
