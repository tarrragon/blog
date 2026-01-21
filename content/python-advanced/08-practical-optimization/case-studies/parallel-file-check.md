---
title: "案例：並行檔案檢查"
date: 2026-01-21
description: "使用 ThreadPoolExecutor 加速 Markdown 連結檢查"
weight: 1
---

# 案例：並行檔案檢查

本案例基於 `.claude/lib/markdown_link_checker.py`，展示如何用 ThreadPoolExecutor 加速 I/O 密集的檔案檢查任務。

## 先備知識

- [8.1 並行處理實戰](../../parallel-processing/)

## 問題背景

### 現有設計

`markdown_link_checker.py` 的 `check_directory()` 方法檢查目錄下所有 Markdown 檔案的內部連結：

```python
def check_directory(
    self,
    dir_path: str,
    recursive: bool = True
) -> List[LinkCheckResult]:
    """
    檢查目錄下所有 Markdown 檔案

    Args:
        dir_path: 目錄路徑
        recursive: 是否遞迴檢查子目錄

    Returns:
        list[LinkCheckResult]: 所有檔案的檢查結果
    """
    dir_path = self._resolve_path(dir_path)

    if not dir_path.is_dir():
        return [
            LinkCheckResult(
                file_path=str(dir_path),
                total_links=0,
                broken_links=[
                    BrokenLink(
                        file=str(dir_path),
                        line=0,
                        link_text="",
                        link_target="",
                        suggestion=f"目錄不存在: {dir_path}"
                    )
                ]
            )
        ]

    # 收集所有 .md 檔案
    if recursive:
        md_files = sorted(dir_path.rglob("*.md"))
    else:
        md_files = sorted(dir_path.glob("*.md"))

    # 循序檢查每個檔案
    results = []
    for md_file in md_files:
        results.append(self.check_file(str(md_file)))

    return results
```

### 這個設計的優點

1. **簡單直覺**：循序執行，程式碼容易理解
2. **結果有序**：檔案按排序順序處理，結果也按順序返回
3. **除錯容易**：問題發生時，可以精確定位到哪個檔案

### 效能瓶頸分析

讓我們分析 `check_file()` 方法的執行時間組成：

```python
def check_file(self, file_path: str) -> LinkCheckResult:
    """檢查單個 Markdown 檔案的連結"""
    file_path = self._resolve_path(file_path)

    # 1. 檢查檔案是否存在（I/O）
    if not file_path.exists():
        return LinkCheckResult(...)

    # 2. 讀取檔案內容（I/O - 主要瓶頸）
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return LinkCheckResult(...)

    # 3. 解析連結（CPU - 很快）
    links = self.parse_markdown_links(content)

    # 4. 過濾內部連結（CPU - 很快）
    internal_links = self._filter_internal_links(links)

    # 5. 檢查每個連結（I/O - 檔案系統檢查）
    broken_links = []
    for link in internal_links:
        is_valid, suggestion = self._check_link(
            link["target"],
            file_path.parent
        )
        if not is_valid:
            broken_links.append(...)

    return LinkCheckResult(...)
```

**時間分布估計**：

```text
操作              | 類型  | 每檔案耗時
-----------------|-------|----------
read_text()      | I/O   | 1-5 ms
parse_links()    | CPU   | 0.1 ms
filter_links()   | CPU   | 0.01 ms
check_link() x N | I/O   | N * 0.5 ms
-----------------|-------|----------
總計（10 連結）  |       | ~7 ms
```

對於 100 個檔案的專案：

```python
# 循序執行
total_time = 100 * 7ms = 700ms = 0.7 秒

# 這看起來不長，但如果：
# - 檔案更多（500+ 個）
# - 每個檔案連結更多
# - 網路檔案系統（NFS）
# 時間會快速增長
```

**為什麼適合並行化？**

1. **I/O 密集**：大部分時間花在檔案讀取和存在性檢查
2. **任務獨立**：每個檔案的檢查互不依賴
3. **無共享狀態**：不需要同步機制

## 進階解決方案

### 設計目標

1. **提升效能**：利用並行化加速 I/O 操作
2. **保持 API 相容**：不改變方法簽名和返回值
3. **可配置**：允許調整並行度

### 實作步驟

#### 步驟 1：識別獨立任務

每個檔案的檢查是完全獨立的：

```python
# 這些操作可以同時執行
result_1 = checker.check_file("doc1.md")  # 獨立
result_2 = checker.check_file("doc2.md")  # 獨立
result_3 = checker.check_file("doc3.md")  # 獨立
```

#### 步驟 2：使用 ThreadPoolExecutor

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

def check_directory_parallel(
    self,
    dir_path: str,
    recursive: bool = True,
    max_workers: Optional[int] = None
) -> List[LinkCheckResult]:
    """
    並行檢查目錄下所有 Markdown 檔案

    Args:
        dir_path: 目錄路徑
        recursive: 是否遞迴檢查子目錄
        max_workers: 最大工作執行緒數，預設為 CPU 核心數

    Returns:
        list[LinkCheckResult]: 所有檔案的檢查結果
    """
    dir_path = self._resolve_path(dir_path)

    if not dir_path.is_dir():
        return [self._create_error_result(dir_path, "目錄不存在")]

    # 收集所有 .md 檔案
    pattern = "**/*.md" if recursive else "*.md"
    md_files = sorted(dir_path.glob(pattern) if not recursive
                      else dir_path.rglob("*.md"))

    if not md_files:
        return []

    # 使用 ThreadPoolExecutor 並行處理
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任務
        future_to_file = {
            executor.submit(self.check_file, str(md_file)): md_file
            for md_file in md_files
        }

        # 收集結果
        for future in as_completed(future_to_file):
            result = future.result()
            results.append(result)

    # 按檔案路徑排序（保持一致的輸出順序）
    results.sort(key=lambda r: r.file_path)

    return results
```

#### 步驟 3：選擇 max_workers

`max_workers` 的選擇影響效能：

```python
import os

# 預設值：min(32, os.cpu_count() + 4)
# 這是 Python 3.8+ 的預設行為

# 對於 I/O 密集任務，可以設定更高
def get_optimal_workers(file_count: int) -> int:
    """
    根據檔案數量計算最佳工作執行緒數

    經驗法則：
    - 檔案數 < 10: 使用檔案數
    - 檔案數 >= 10: 使用 CPU 核心數 * 2，但不超過 32
    """
    cpu_count = os.cpu_count() or 4

    if file_count < 10:
        return file_count

    return min(32, cpu_count * 2, file_count)
```

### 完整程式碼

```python
#!/usr/bin/env python3
"""
並行 Markdown 連結檢查器

基於 markdown_link_checker.py，展示如何用 ThreadPoolExecutor 加速檔案檢查。
"""

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

@dataclass
class BrokenLink:
    """失效連結描述"""
    file: str
    line: int
    link_text: str
    link_target: str
    suggestion: str = ""

@dataclass
class LinkCheckResult:
    """單個檔案的連結檢查結果"""
    file_path: str
    total_links: int
    broken_links: List[BrokenLink] = field(default_factory=list)
    is_valid: bool = True

    def __post_init__(self):
        self.is_valid = len(self.broken_links) == 0

class ParallelMarkdownLinkChecker:
    """
    並行 Markdown 連結檢查器

    相較於原版的改進：
    - check_directory() 使用 ThreadPoolExecutor 並行處理
    - 支援自訂 max_workers
    - 保持 API 相容性
    """

    INLINE_LINK_PATTERN = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')
    EXTERNAL_PATTERNS = [r'^https?://', r'^mailto:', r'^tel:', r'^ftp://']

    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            project_root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        self.project_root = Path(project_root)

    # ===== 核心方法 =====

    def check_file(self, file_path: str) -> LinkCheckResult:
        """
        檢查單個 Markdown 檔案的連結

        這個方法是執行緒安全的，可以並行呼叫。
        """
        file_path = self._resolve_path(file_path)

        if not file_path.exists():
            return LinkCheckResult(
                file_path=str(file_path),
                total_links=0,
                broken_links=[
                    BrokenLink(
                        file=str(file_path), line=0,
                        link_text="", link_target="",
                        suggestion=f"檔案不存在: {file_path}"
                    )
                ]
            )

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return LinkCheckResult(
                file_path=str(file_path),
                total_links=0,
                broken_links=[
                    BrokenLink(
                        file=str(file_path), line=0,
                        link_text="", link_target="",
                        suggestion=f"無法讀取檔案: {e}"
                    )
                ]
            )

        links = self._parse_links(content)
        internal_links = self._filter_internal_links(links)

        broken_links = []
        for link in internal_links:
            is_valid, suggestion = self._check_link(
                link["target"], file_path.parent
            )
            if not is_valid:
                broken_links.append(
                    BrokenLink(
                        file=str(file_path),
                        line=link["line"],
                        link_text=link["text"],
                        link_target=link["target"],
                        suggestion=suggestion
                    )
                )

        return LinkCheckResult(
            file_path=str(file_path),
            total_links=len(internal_links),
            broken_links=broken_links
        )

    def check_directory(
        self,
        dir_path: str,
        recursive: bool = True,
        max_workers: Optional[int] = None
    ) -> List[LinkCheckResult]:
        """
        並行檢查目錄下所有 Markdown 檔案

        Args:
            dir_path: 目錄路徑
            recursive: 是否遞迴檢查子目錄
            max_workers: 最大工作執行緒數，None 表示使用預設值

        Returns:
            list[LinkCheckResult]: 所有檔案的檢查結果（按路徑排序）
        """
        dir_path = self._resolve_path(dir_path)

        if not dir_path.is_dir():
            return [
                LinkCheckResult(
                    file_path=str(dir_path),
                    total_links=0,
                    broken_links=[
                        BrokenLink(
                            file=str(dir_path), line=0,
                            link_text="", link_target="",
                            suggestion=f"目錄不存在: {dir_path}"
                        )
                    ]
                )
            ]

        # 收集所有 .md 檔案
        if recursive:
            md_files = list(dir_path.rglob("*.md"))
        else:
            md_files = list(dir_path.glob("*.md"))

        if not md_files:
            return []

        # 計算最佳工作執行緒數
        if max_workers is None:
            max_workers = self._get_optimal_workers(len(md_files))

        # 並行處理
        results: List[LinkCheckResult] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任務
            future_to_file = {
                executor.submit(self.check_file, str(f)): f
                for f in md_files
            }

            # 收集結果（as_completed 提供最快的回應）
            for future in as_completed(future_to_file):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # 處理意外錯誤
                    md_file = future_to_file[future]
                    results.append(
                        LinkCheckResult(
                            file_path=str(md_file),
                            total_links=0,
                            broken_links=[
                                BrokenLink(
                                    file=str(md_file), line=0,
                                    link_text="", link_target="",
                                    suggestion=f"檢查失敗: {e}"
                                )
                            ]
                        )
                    )

        # 排序以保持一致的輸出順序
        results.sort(key=lambda r: r.file_path)

        return results

    # ===== 循序版本（用於比較）=====

    def check_directory_sequential(
        self,
        dir_path: str,
        recursive: bool = True
    ) -> List[LinkCheckResult]:
        """循序版本，用於效能比較"""
        dir_path = self._resolve_path(dir_path)

        if not dir_path.is_dir():
            return [
                LinkCheckResult(
                    file_path=str(dir_path),
                    total_links=0,
                    broken_links=[
                        BrokenLink(
                            file=str(dir_path), line=0,
                            link_text="", link_target="",
                            suggestion=f"目錄不存在: {dir_path}"
                        )
                    ]
                )
            ]

        if recursive:
            md_files = sorted(dir_path.rglob("*.md"))
        else:
            md_files = sorted(dir_path.glob("*.md"))

        results = []
        for md_file in md_files:
            results.append(self.check_file(str(md_file)))

        return results

    # ===== 私有方法 =====

    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.project_root / p

    def _parse_links(self, content: str) -> List[Dict]:
        links = []
        in_code_block = False

        for line_num, line in enumerate(content.split('\n'), start=1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            for match in self.INLINE_LINK_PATTERN.finditer(line):
                links.append({
                    "text": match.group(1),
                    "target": match.group(2),
                    "line": line_num
                })

        return links

    def _filter_internal_links(self, links: List[Dict]) -> List[Dict]:
        internal = []
        for link in links:
            target = link["target"]
            if target.startswith("#"):
                continue
            if any(re.match(p, target) for p in self.EXTERNAL_PATTERNS):
                continue
            internal.append(link)
        return internal

    def _check_link(
        self,
        target: str,
        base_dir: Path
    ) -> Tuple[bool, str]:
        target_path = target.split("#")[0]
        if not target_path:
            return True, ""

        resolved = (base_dir / target_path).resolve()
        if resolved.exists():
            return True, ""
        else:
            return False, f"檔案不存在: {target_path}"

    def _get_optimal_workers(self, file_count: int) -> int:
        """計算最佳工作執行緒數"""
        cpu_count = os.cpu_count() or 4
        if file_count < 10:
            return file_count
        return min(32, cpu_count * 2, file_count)

# ===== 效能測量工具 =====

def benchmark_checker(
    dir_path: str,
    iterations: int = 3
) -> Dict[str, float]:
    """
    比較循序與並行版本的效能

    Args:
        dir_path: 要檢查的目錄
        iterations: 執行次數（取平均）

    Returns:
        dict: {'sequential': 秒數, 'parallel': 秒數, 'speedup': 加速比}
    """
    import time

    checker = ParallelMarkdownLinkChecker()

    # 預熱（讓檔案系統快取生效）
    checker.check_directory(dir_path)

    # 測量循序版本
    seq_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        checker.check_directory_sequential(dir_path)
        seq_times.append(time.perf_counter() - start)

    # 測量並行版本
    par_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        checker.check_directory(dir_path)
        par_times.append(time.perf_counter() - start)

    seq_avg = sum(seq_times) / len(seq_times)
    par_avg = sum(par_times) / len(par_times)

    return {
        "sequential": seq_avg,
        "parallel": par_avg,
        "speedup": seq_avg / par_avg if par_avg > 0 else 0
    }

# ===== 示範 =====

if __name__ == "__main__":
    import sys

    # 預設檢查當前目錄
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    print(f"=== 並行 Markdown 連結檢查示範 ===\n")
    print(f"目標目錄: {target_dir}\n")

    checker = ParallelMarkdownLinkChecker()

    # 執行檢查
    results = checker.check_directory(target_dir)

    # 統計
    total_files = len(results)
    total_links = sum(r.total_links for r in results)
    broken_count = sum(len(r.broken_links) for r in results)
    invalid_files = sum(1 for r in results if not r.is_valid)

    print(f"檔案數: {total_files}")
    print(f"連結數: {total_links}")
    print(f"失效連結: {broken_count}")
    print(f"有問題的檔案: {invalid_files}")

    # 顯示失效連結
    if broken_count > 0:
        print(f"\n失效連結詳情:")
        for result in results:
            if not result.is_valid:
                print(f"\n  {result.file_path}:")
                for link in result.broken_links:
                    print(f"    Line {link.line}: [{link.link_text}]({link.link_target})")

    # 效能比較
    if total_files >= 5:
        print(f"\n=== 效能比較 ===\n")
        benchmark = benchmark_checker(target_dir)
        print(f"循序版本: {benchmark['sequential']:.3f} 秒")
        print(f"並行版本: {benchmark['parallel']:.3f} 秒")
        print(f"加速比: {benchmark['speedup']:.2f}x")
```

### 效能測量

使用 `timeit` 比較前後效能：

```python
import timeit
from parallel_link_checker import ParallelMarkdownLinkChecker

def measure_performance(dir_path: str, num_runs: int = 5):
    """測量並比較循序與並行版本的效能"""
    checker = ParallelMarkdownLinkChecker()

    # 循序版本
    seq_time = timeit.timeit(
        lambda: checker.check_directory_sequential(dir_path),
        number=num_runs
    ) / num_runs

    # 並行版本
    par_time = timeit.timeit(
        lambda: checker.check_directory(dir_path),
        number=num_runs
    ) / num_runs

    print(f"目錄: {dir_path}")
    print(f"循序版本: {seq_time:.4f} 秒")
    print(f"並行版本: {par_time:.4f} 秒")
    print(f"加速比: {seq_time / par_time:.2f}x")

# 實際測試結果（範例）
# 目錄: ./docs （50 個 .md 檔案）
# 循序版本: 0.3521 秒
# 並行版本: 0.0892 秒
# 加速比: 3.95x
```

**不同規模的預期加速比**：

| 檔案數 | 循序時間 | 並行時間 | 加速比 |
|--------|----------|----------|--------|
| 10     | 70 ms    | 25 ms    | 2.8x   |
| 50     | 350 ms   | 90 ms    | 3.9x   |
| 100    | 700 ms   | 160 ms   | 4.4x   |
| 500    | 3.5 s    | 750 ms   | 4.7x   |

> 注意：實際加速比取決於檔案大小、連結數量、磁碟速度等因素。

## 設計權衡

| 面向 | 循序版本 | 並行版本 |
|------|----------|----------|
| 效能 | 較慢，線性增長 | 快 3-5 倍 |
| 複雜度 | 簡單 | 需要理解執行緒池 |
| 除錯 | 容易 | 需要注意執行緒安全 |
| 記憶體 | 較低 | 較高（執行緒開銷） |
| 結果順序 | 保證有序 | 需要額外排序 |
| 錯誤處理 | 直接 | 需要處理 Future 例外 |

### 執行緒安全考量

`check_file()` 方法是執行緒安全的，因為：

1. **無共享狀態**：每次呼叫都獨立處理一個檔案
2. **唯讀操作**：只讀取檔案，不修改
3. **獨立返回值**：每個呼叫返回獨立的 `LinkCheckResult`

```python
# 這是安全的
def check_file(self, file_path: str) -> LinkCheckResult:
    # 所有變數都是區域變數
    file_path = self._resolve_path(file_path)  # 新物件
    content = file_path.read_text()            # 區域變數
    links = self._parse_links(content)         # 區域變數
    # ...
    return LinkCheckResult(...)                # 新物件
```

## 什麼時候該用這個技術？

### 適合使用

- **多檔案處理**：需要處理大量獨立檔案
- **I/O 密集**：主要時間花在檔案讀寫
- **任務獨立**：每個任務不依賴其他任務的結果
- **可接受亂序**：或願意在最後排序

### 不建議使用

- **檔案很少**：少於 5 個檔案，並行開銷可能大於收益
- **CPU 密集**：如果主要時間花在計算，應考慮 ProcessPoolExecutor
- **有依賴關係**：後續檔案依賴前面檔案的結果
- **記憶體受限**：並行版本會同時載入多個檔案

## 練習

### 基礎練習

#### 練習 1：加入進度回報

```python
def check_directory_with_progress(
    self,
    dir_path: str,
    callback: callable = None
) -> List[LinkCheckResult]:
    """
    並行檢查，並在每個檔案完成時呼叫 callback

    callback 簽名: callback(completed: int, total: int, result: LinkCheckResult)

    提示：使用 as_completed() 在每個任務完成時觸發回報
    """
    # Your implementation here
    pass
```

#### 練習 2：支援取消

```python
def check_directory_cancellable(
    self,
    dir_path: str,
    cancel_event: threading.Event = None
) -> List[LinkCheckResult]:
    """
    可取消的並行檢查

    當 cancel_event.is_set() 時，停止提交新任務並返回已完成的結果

    提示：在迴圈中檢查 cancel_event
    """
    # Your implementation here
    pass
```

### 進階練習

#### 練習 3：批次處理大型目錄

```python
def check_directory_batched(
    self,
    dir_path: str,
    batch_size: int = 100
) -> List[LinkCheckResult]:
    """
    分批處理大型目錄

    避免一次提交太多任務導致記憶體問題

    提示：將檔案列表分成多個批次，依序處理每批
    """
    # Your implementation here
    pass
```

#### 練習 4：加入重試機制

```python
def check_file_with_retry(
    self,
    file_path: str,
    max_retries: int = 3
) -> LinkCheckResult:
    """
    帶重試的檔案檢查

    當檔案被鎖定或暫時不可用時自動重試

    提示：捕捉特定例外，使用指數退避
    """
    # Your implementation here
    pass
```

### 挑戰題

#### 練習 5：實作並行度自動調整

```python
class AdaptiveParallelChecker:
    """
    自動調整並行度的檢查器

    根據系統負載和檢查速度動態調整 max_workers

    功能：
    - 初始使用保守的 max_workers
    - 如果任務完成很快，增加 max_workers
    - 如果系統負載高，減少 max_workers
    - 記錄最佳 max_workers 供下次使用
    """
    # Your implementation here
    pass
```

## 延伸閱讀

- [concurrent.futures 官方文件](https://docs.python.org/3/library/concurrent.futures.html)
- [ThreadPoolExecutor 使用指南](https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor)
- [as_completed vs map 的選擇](https://superfastpython.com/threadpoolexecutor-map-vs-submit/)
- 入門系列：[3.7 並行處理](../../../python/03-stdlib/concurrency/)

---

*下一章：[並行 Hook 驗證](../parallel-hook-validation/)*
