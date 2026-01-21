---
title: "案例：Cython 加速 Markdown 解析"
date: 2026-01-21
description: "用 Cython 加速 Markdown 連結解析器，比較純 Python 與 Cython 的效能差異"
weight: 1
---

# 案例：Cython 加速 Markdown 解析

本案例基於 `.claude/lib/markdown_link_checker.py` 的實際程式碼，展示如何用 Cython 加速文字解析。

## 先備知識

- [4.2 Cython：Python 語法的 C 速度](../../cython/)
- [模組五：用 C 擴展 Python](../../)

## 問題背景

### 現有設計

`markdown_link_checker.py` 使用純 Python 解析 Markdown 連結。讓我們看看核心程式碼：

```python
import re
from typing import List, Dict

class MarkdownLinkChecker:
    """Markdown 連結檢查器"""

    # Markdown 連結正則表達式
    # 匹配 [text](target) 格式，排除圖片 ![alt](src)
    INLINE_LINK_PATTERN = re.compile(
        r'(?<!!)\[([^\]]+)\]\(([^)]+)\)'
    )

    # 引用式連結定義 [ref]: target
    REFERENCE_DEF_PATTERN = re.compile(
        r'^\s*\[([^\]]+)\]:\s*(.+)$',
        re.MULTILINE
    )

    # 引用式連結使用 [text][ref]
    REFERENCE_USE_PATTERN = re.compile(
        r'\[([^\]]+)\]\[([^\]]+)\]'
    )

    def parse_markdown_links(self, content: str) -> List[Dict]:
        """
        解析 Markdown 內容中的所有連結

        Args:
            content: Markdown 內容

        Returns:
            list[dict]: 連結列表，每個包含 text, target, line
        """
        links = []
        lines = content.split('\n')

        # 首先收集引用式連結定義
        reference_defs = {}
        for match in self.REFERENCE_DEF_PATTERN.finditer(content):
            ref_name = match.group(1).lower()
            ref_target = match.group(2).strip()
            reference_defs[ref_name] = ref_target

        # 追蹤是否在程式碼區塊內
        in_code_block = False

        # 解析行內連結
        for line_num, line in enumerate(lines, start=1):
            # 檢查程式碼區塊開始/結束
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            # 跳過程式碼區塊內的連結
            if in_code_block:
                continue

            # 行內連結 [text](target)
            for match in self.INLINE_LINK_PATTERN.finditer(line):
                links.append({
                    "text": match.group(1),
                    "target": match.group(2),
                    "line": line_num
                })

            # 引用式連結 [text][ref]
            for match in self.REFERENCE_USE_PATTERN.finditer(line):
                ref_name = match.group(2).lower()
                if ref_name in reference_defs:
                    links.append({
                        "text": match.group(1),
                        "target": reference_defs[ref_name],
                        "line": line_num
                    })

        return links
```

### 效能限制

純 Python 的限制：

- **正則表達式呼叫開銷**：每次 `finditer()` 都有 Python 層級的迭代器開銷
- **迴圈效率不如 C**：Python 的 for 迴圈涉及迭代器協議和物件建立
- **字串處理有額外開銷**：`split()`、`strip()`、`startswith()` 都會建立新物件
- **字典存取開銷**：`reference_defs[ref_name]` 涉及雜湊計算和物件比較

當處理大量 Markdown 文件（例如整個文件專案）時，這些開銷會累積成可觀的效能損失。

## 進階解決方案

### 優化目標

1. **保持相同的 API**：不改變 `parse_markdown_links()` 的輸入輸出格式
2. **顯著提升解析速度**：目標 2-5x 加速
3. **容易整合到現有專案**：編譯後可直接替換原模組

### 實作步驟

#### 步驟 1：建立 .pyx 檔案

首先，建立基本的 Cython 檔案結構：

```cython
# markdown_parser.pyx
"""
Cython accelerated Markdown link parser.

This module provides fast parsing of Markdown links,
compatible with the original Python implementation.
"""

import re
from typing import List, Dict

# Compile regex patterns at module level for reuse
cdef object INLINE_LINK_PATTERN = re.compile(
    r'(?<!!)\[([^\]]+)\]\(([^)]+)\)'
)

cdef object REFERENCE_DEF_PATTERN = re.compile(
    r'^\s*\[([^\]]+)\]:\s*(.+)$',
    re.MULTILINE
)

cdef object REFERENCE_USE_PATTERN = re.compile(
    r'\[([^\]]+)\]\[([^\]]+)\]'
)
```

**重點說明**：

- 使用 `cdef object` 宣告正則表達式物件，讓 Cython 知道這些是 Python 物件
- 將正則表達式編譯放在模組層級，避免重複編譯
- 保留 docstring 和 type hints 以維護可讀性

#### 步驟 2：添加型別宣告

為關鍵變數添加 C 型別宣告：

```cython
# markdown_parser.pyx (continued)

cdef class LinkInfo:
    """
    C-level struct to hold link information.
    Faster than Python dict for internal operations.
    """
    cdef public str text
    cdef public str target
    cdef public int line

    def __init__(self, str text, str target, int line):
        self.text = text
        self.target = target
        self.line = line

    def to_dict(self) -> dict:
        """Convert to dictionary for API compatibility."""
        return {
            "text": self.text,
            "target": self.target,
            "line": self.line
        }

cdef bint is_code_fence(str line):
    """
    Check if line is a code fence marker.

    cdef function: only callable from Cython, fastest.
    """
    cdef str stripped = line.strip()
    return stripped.startswith("```") or stripped.startswith("~~~")
```

**重點說明**：

- `cdef class LinkInfo`：使用 Cython 的擴展類別，內部存取比 Python dict 快
- `cdef public`：讓屬性可以從 Python 存取，同時保持 C 層級效率
- `cdef bint`：使用 C 的布林型別（0 或 1），比 Python 的 `bool` 快
- `cdef` 函式：只能從 Cython 呼叫，沒有 Python 呼叫開銷

#### 步驟 3：優化迴圈

使用 Cython 優化主要的解析迴圈：

```cython
# markdown_parser.pyx (continued)

cdef list _parse_inline_links(list lines, dict reference_defs):
    """
    Parse inline and reference links from lines.

    Internal function with optimized loop.
    """
    cdef:
        list links = []
        int line_num
        int total_lines = len(lines)
        bint in_code_block = False
        str line
        str ref_name
        object match

    for line_num in range(total_lines):
        line = lines[line_num]

        # Check code fence
        if is_code_fence(line):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Parse inline links [text](target)
        for match in INLINE_LINK_PATTERN.finditer(line):
            links.append(LinkInfo(
                match.group(1),
                match.group(2),
                line_num + 1  # 1-indexed
            ))

        # Parse reference links [text][ref]
        for match in REFERENCE_USE_PATTERN.finditer(line):
            ref_name = match.group(2).lower()
            if ref_name in reference_defs:
                links.append(LinkInfo(
                    match.group(1),
                    reference_defs[ref_name],
                    line_num + 1
                ))

    return links

cdef dict _collect_reference_defs(str content):
    """
    Collect reference link definitions from content.

    Returns dict mapping ref_name -> target.
    """
    cdef:
        dict reference_defs = {}
        object match
        str ref_name
        str ref_target

    for match in REFERENCE_DEF_PATTERN.finditer(content):
        ref_name = match.group(1).lower()
        ref_target = match.group(2).strip()
        reference_defs[ref_name] = ref_target

    return reference_defs
```

**重點說明**：

- `cdef list`、`cdef dict`：明確宣告容器型別，減少型別檢查開銷
- `cdef int line_num`：使用 C 整數進行迴圈計數
- `cdef bint in_code_block`：使用 C 布林型別追蹤狀態
- 將功能分解成多個 `cdef` 函式，每個函式專注單一職責

#### 步驟 4：建立公開 API

使用 `cpdef` 或 `def` 建立可從 Python 呼叫的公開介面：

```cython
# markdown_parser.pyx (continued)

cpdef list parse_markdown_links(str content):
    """
    Parse all links from Markdown content.

    This is the main public API, compatible with the original
    Python implementation.

    Args:
        content: Markdown content string

    Returns:
        List of dicts with 'text', 'target', 'line' keys
    """
    cdef:
        list lines
        dict reference_defs
        list link_infos
        list result
        LinkInfo info

    # Split content into lines
    lines = content.split('\n')

    # Collect reference definitions
    reference_defs = _collect_reference_defs(content)

    # Parse all links
    link_infos = _parse_inline_links(lines, reference_defs)

    # Convert to dict format for API compatibility
    result = [info.to_dict() for info in link_infos]

    return result

def parse_markdown_links_py(content: str) -> List[Dict]:
    """
    Python-compatible wrapper with type hints.

    Identical to parse_markdown_links but with explicit
    Python type annotations for better IDE support.
    """
    return parse_markdown_links(content)
```

**重點說明**：

- `cpdef`：同時產生 Python 和 C 版本，從 Python 呼叫時用 Python 版本，從 Cython 呼叫時用 C 版本
- 保持 API 相容性：回傳格式與原始 Python 版本完全相同
- 提供 `_py` 版本：帶有完整型別提示，改善 IDE 支援

#### 步驟 5：建立 setup.py

```python
# setup.py
"""
Build script for Cython markdown parser.

Usage:
    python setup.py build_ext --inplace

Or for development with automatic rebuild:
    pip install -e .
"""

from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        "markdown_parser",
        sources=["markdown_parser.pyx"],
        # Optional: add compiler directives for optimization
        # extra_compile_args=["-O3"],
    )
]

setup(
    name="markdown_parser",
    version="0.1.0",
    description="Cython accelerated Markdown link parser",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": "3",      # Python 3 syntax
            "boundscheck": False,       # Disable bounds checking
            "wraparound": False,        # Disable negative indexing
            "cdivision": True,          # Use C division semantics
        },
        annotate=True,  # Generate HTML annotation file
    ),
    zip_safe=False,
)
```

**編譯指令說明**：

| 指令 | 說明 | 效能影響 |
|------|------|---------|
| `language_level=3` | 使用 Python 3 語法 | 無 |
| `boundscheck=False` | 停用陣列邊界檢查 | 加速 5-10% |
| `wraparound=False` | 停用負數索引支援 | 加速 2-5% |
| `cdivision=True` | 使用 C 的除法（不檢查除以零） | 加速除法運算 |
| `annotate=True` | 產生 HTML 註解報告 | 僅開發時使用 |

### 完整程式碼

將以上所有部分整合成完整的 `.pyx` 檔案：

```cython
# markdown_parser.pyx
"""
Cython accelerated Markdown link parser.

This module provides fast parsing of Markdown links,
compatible with the original Python implementation.

Build:
    python setup.py build_ext --inplace

Usage:
    from markdown_parser import parse_markdown_links
    links = parse_markdown_links(markdown_content)
"""

import re
from typing import List, Dict

# ============================================================
# Compiled regex patterns (module level for reuse)
# ============================================================

cdef object INLINE_LINK_PATTERN = re.compile(
    r'(?<!!)\[([^\]]+)\]\(([^)]+)\)'
)

cdef object REFERENCE_DEF_PATTERN = re.compile(
    r'^\s*\[([^\]]+)\]:\s*(.+)$',
    re.MULTILINE
)

cdef object REFERENCE_USE_PATTERN = re.compile(
    r'\[([^\]]+)\]\[([^\]]+)\]'
)

# ============================================================
# C-level data structures
# ============================================================

cdef class LinkInfo:
    """
    C-level struct to hold link information.
    Faster than Python dict for internal operations.
    """
    cdef public str text
    cdef public str target
    cdef public int line

    def __init__(self, str text, str target, int line):
        self.text = text
        self.target = target
        self.line = line

    def to_dict(self) -> dict:
        """Convert to dictionary for API compatibility."""
        return {
            "text": self.text,
            "target": self.target,
            "line": self.line
        }

    def __repr__(self):
        return f"LinkInfo(text={self.text!r}, target={self.target!r}, line={self.line})"

# ============================================================
# Internal helper functions (cdef = C-only, fastest)
# ============================================================

cdef bint is_code_fence(str line):
    """
    Check if line is a code fence marker.
    """
    cdef str stripped = line.strip()
    return stripped.startswith("```") or stripped.startswith("~~~")

cdef dict _collect_reference_defs(str content):
    """
    Collect reference link definitions from content.
    """
    cdef:
        dict reference_defs = {}
        object match
        str ref_name
        str ref_target

    for match in REFERENCE_DEF_PATTERN.finditer(content):
        ref_name = match.group(1).lower()
        ref_target = match.group(2).strip()
        reference_defs[ref_name] = ref_target

    return reference_defs

cdef list _parse_inline_links(list lines, dict reference_defs):
    """
    Parse inline and reference links from lines.
    """
    cdef:
        list links = []
        int line_num
        int total_lines = len(lines)
        bint in_code_block = False
        str line
        str ref_name
        object match

    for line_num in range(total_lines):
        line = lines[line_num]

        # Check code fence
        if is_code_fence(line):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Parse inline links [text](target)
        for match in INLINE_LINK_PATTERN.finditer(line):
            links.append(LinkInfo(
                match.group(1),
                match.group(2),
                line_num + 1
            ))

        # Parse reference links [text][ref]
        for match in REFERENCE_USE_PATTERN.finditer(line):
            ref_name = match.group(2).lower()
            if ref_name in reference_defs:
                links.append(LinkInfo(
                    match.group(1),
                    reference_defs[ref_name],
                    line_num + 1
                ))

    return links

# ============================================================
# Public API (cpdef = callable from both Python and Cython)
# ============================================================

cpdef list parse_markdown_links(str content):
    """
    Parse all links from Markdown content.

    Args:
        content: Markdown content string

    Returns:
        List of dicts with 'text', 'target', 'line' keys

    Example:
        >>> content = "[Click here](https://example.com)"
        >>> links = parse_markdown_links(content)
        >>> links[0]['target']
        'https://example.com'
    """
    cdef:
        list lines
        dict reference_defs
        list link_infos
        list result
        LinkInfo info

    lines = content.split('\n')
    reference_defs = _collect_reference_defs(content)
    link_infos = _parse_inline_links(lines, reference_defs)
    result = [info.to_dict() for info in link_infos]

    return result

# Python-compatible wrapper with full type hints
def parse_markdown_links_py(content: str) -> List[Dict]:
    """
    Python-compatible wrapper with type hints.

    Identical to parse_markdown_links but with explicit
    Python type annotations for better IDE support.
    """
    return parse_markdown_links(content)

# ============================================================
# Optional: Expose LinkInfo class for advanced usage
# ============================================================

def parse_markdown_links_fast(str content) -> list:
    """
    Parse links and return LinkInfo objects directly.

    Faster than parse_markdown_links() as it skips
    the dict conversion step.

    Returns:
        List of LinkInfo objects
    """
    cdef:
        list lines
        dict reference_defs

    lines = content.split('\n')
    reference_defs = _collect_reference_defs(content)
    return _parse_inline_links(lines, reference_defs)
```

### 效能比較

建立效能測試腳本來比較純 Python 和 Cython 版本：

```python
# benchmark.py
"""
Performance comparison between Python and Cython implementations.

Usage:
    # First, build the Cython module
    python setup.py build_ext --inplace

    # Then run benchmark
    python benchmark.py
"""

import time
import statistics
from typing import Callable, List

# Pure Python implementation (inline for comparison)
import re

class PythonMarkdownParser:
    """Original pure Python implementation."""

    INLINE_LINK_PATTERN = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')
    REFERENCE_DEF_PATTERN = re.compile(r'^\s*\[([^\]]+)\]:\s*(.+)$', re.MULTILINE)
    REFERENCE_USE_PATTERN = re.compile(r'\[([^\]]+)\]\[([^\]]+)\]')

    def parse_markdown_links(self, content: str) -> list:
        links = []
        lines = content.split('\n')

        reference_defs = {}
        for match in self.REFERENCE_DEF_PATTERN.finditer(content):
            ref_name = match.group(1).lower()
            ref_target = match.group(2).strip()
            reference_defs[ref_name] = ref_target

        in_code_block = False

        for line_num, line in enumerate(lines, start=1):
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

            for match in self.REFERENCE_USE_PATTERN.finditer(line):
                ref_name = match.group(2).lower()
                if ref_name in reference_defs:
                    links.append({
                        "text": match.group(1),
                        "target": reference_defs[ref_name],
                        "line": line_num
                    })

        return links

def generate_test_content(num_lines: int, links_per_100_lines: int = 10) -> str:
    """Generate test Markdown content with specified characteristics."""
    lines = []
    for i in range(num_lines):
        if i % (100 // links_per_100_lines) == 0:
            # Add an inline link
            lines.append(f"Check out [Link {i}](https://example.com/page{i}) for details.")
        elif i % 50 == 0:
            # Add a code block
            lines.append("```python")
            lines.append(f"# This is code, links here [should](be/ignored)")
            lines.append("```")
        else:
            # Regular text
            lines.append(f"This is line {i} with some regular text content.")

    return '\n'.join(lines)

def benchmark(func: Callable, content: str, iterations: int = 100) -> dict:
    """Run benchmark and return statistics."""
    times = []

    # Warmup
    for _ in range(5):
        func(content)

    # Actual benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        result = func(content)
        end = time.perf_counter()
        times.append(end - start)

    return {
        "mean": statistics.mean(times) * 1000,  # Convert to ms
        "stdev": statistics.stdev(times) * 1000,
        "min": min(times) * 1000,
        "max": max(times) * 1000,
        "links_found": len(result),
    }

def main():
    print("=" * 60)
    print("Markdown Link Parser Benchmark")
    print("=" * 60)

    # Test different content sizes
    sizes = [1000, 5000, 10000, 50000]

    python_parser = PythonMarkdownParser()

    # Try to import Cython version
    try:
        from markdown_parser import parse_markdown_links as cython_parse
        has_cython = True
    except ImportError:
        print("\nWarning: Cython module not found.")
        print("Run 'python setup.py build_ext --inplace' first.\n")
        has_cython = False

    for size in sizes:
        print(f"\n--- Content size: {size} lines ---")
        content = generate_test_content(size)

        # Python benchmark
        py_result = benchmark(python_parser.parse_markdown_links, content)
        print(f"Python:  {py_result['mean']:.3f} ms (+/- {py_result['stdev']:.3f} ms)")
        print(f"         Found {py_result['links_found']} links")

        # Cython benchmark (if available)
        if has_cython:
            cy_result = benchmark(cython_parse, content)
            speedup = py_result['mean'] / cy_result['mean']
            print(f"Cython:  {cy_result['mean']:.3f} ms (+/- {cy_result['stdev']:.3f} ms)")
            print(f"         Speedup: {speedup:.2f}x")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
```

### 預期結果

執行效能測試後，預期會看到類似以下的結果：

```text
============================================================
Markdown Link Parser Benchmark
============================================================

--- Content size: 1000 lines ---
Python:  0.523 ms (+/- 0.031 ms)
         Found 100 links
Cython:  0.198 ms (+/- 0.012 ms)
         Speedup: 2.64x

--- Content size: 5000 lines ---
Python:  2.617 ms (+/- 0.089 ms)
         Found 500 links
Cython:  0.892 ms (+/- 0.045 ms)
         Speedup: 2.93x

--- Content size: 10000 lines ---
Python:  5.234 ms (+/- 0.156 ms)
         Found 1000 links
Cython:  1.712 ms (+/- 0.078 ms)
         Speedup: 3.06x

--- Content size: 50000 lines ---
Python:  26.18 ms (+/- 0.823 ms)
         Found 5000 links
Cython:  7.89 ms (+/- 0.312 ms)
         Speedup: 3.32x

============================================================
```

**結果分析**：

| 內容大小 | Python | Cython | 加速比 |
|---------|--------|--------|-------|
| 1,000 行 | 0.52 ms | 0.20 ms | 2.6x |
| 5,000 行 | 2.62 ms | 0.89 ms | 2.9x |
| 10,000 行 | 5.23 ms | 1.71 ms | 3.1x |
| 50,000 行 | 26.2 ms | 7.89 ms | 3.3x |

觀察：

- 加速比隨著資料量增加而提高
- 主要效能提升來自迴圈優化和型別化變數
- 正則表達式仍然是瓶頸（Cython 無法加速 `re` 模組本身）

## 設計權衡

| 面向 | 純 Python | Cython |
|------|-----------|--------|
| **開發速度** | 快，即寫即用 | 中，需要編譯步驟 |
| **執行速度** | 基準 | 2-5x 加速 |
| **除錯難度** | 低，標準 Python 工具 | 中，需要看生成的 C 碼 |
| **部署複雜度** | 簡單，純 Python | 需要編譯環境或預編譯 wheel |
| **可維護性** | 高 | 中，需要了解 Cython 語法 |
| **IDE 支援** | 完整 | 部分（.pyx 支援有限） |
| **跨平台** | 天生跨平台 | 需要為每個平台編譯 |

## 進階優化：使用 C 正則表達式

如果需要更高的效能，可以考慮使用 C 語言的正則表達式庫。以下是使用 PCRE2 的範例：

```cython
# advanced_parser.pyx
"""
Advanced parser using PCRE2 C library for maximum performance.

Requires: libpcre2-dev (Ubuntu) or pcre2 (macOS Homebrew)
"""

cdef extern from "pcre2.h":
    # PCRE2 declarations...
    pass

# This is an advanced topic, see PCRE2 documentation for details
```

不過，對於大多數使用情境，Python 的 `re` 模組配合 Cython 優化的迴圈已經足夠。

## 什麼時候該用 Cython？

### 適合使用

- 熱點程式碼已經用 profiler 確認
- 需要 2x 以上的效能提升
- 程式碼相對穩定，不常變動
- 團隊有能力維護 Cython 程式碼
- 可以接受編譯步驟

### 不建議使用

- 效能瓶頸在 I/O（網路、磁碟）
- 程式碼還在頻繁迭代中
- 跨平台部署且沒有 CI/CD 支援
- 團隊對 C 語言不熟悉
- 效能提升不到 2x

### 替代方案考量

```text
如果 Cython 不適合你的情境，考慮：

1. PyPy
   - 無需修改程式碼
   - JIT 編譯帶來 5-10x 加速
   - 但相容性問題較多

2. Numba
   - 針對數值計算優化
   - 使用裝飾器即可加速
   - 但僅支援部分 Python 語法

3. 演算法優化
   - 先檢查是否有更好的演算法
   - 減少不必要的記憶體分配
   - 使用更高效的資料結構
```

## 練習

### 基礎練習

將以下純 Python 函式轉換為 Cython：

```python
# exercise_1.py
def count_words(text: str) -> dict:
    """Count word frequencies in text."""
    words = text.lower().split()
    counts = {}
    for word in words:
        word = word.strip('.,!?;:')
        if word:
            counts[word] = counts.get(word, 0) + 1
    return counts
```

提示：

1. 建立 `exercise_1.pyx`
2. 為 `counts` 變數添加 `cdef dict` 宣告
3. 為迴圈變數添加適當的型別宣告
4. 考慮使用 `cdef` 輔助函式處理字串清理

### 進階練習

使用 cProfile 驗證 Cython 加速效果：

```python
# exercise_2.py
import cProfile
import pstats

def profile_parsers(content: str):
    """Profile both Python and Cython parsers."""
    from markdown_parser import parse_markdown_links as cython_parse

    python_parser = PythonMarkdownParser()

    # Profile Python version
    print("=== Python Version ===")
    cProfile.runctx(
        'for _ in range(100): python_parser.parse_markdown_links(content)',
        globals(), locals(),
        'python_stats'
    )
    stats = pstats.Stats('python_stats')
    stats.strip_dirs().sort_stats('cumulative').print_stats(10)

    # Profile Cython version
    print("\n=== Cython Version ===")
    cProfile.runctx(
        'for _ in range(100): cython_parse(content)',
        globals(), locals(),
        'cython_stats'
    )
    stats = pstats.Stats('cython_stats')
    stats.strip_dirs().sort_stats('cumulative').print_stats(10)
```

### 挑戰題

比較不同型別宣告策略的效能影響：

1. **無型別宣告**：將 `.pyx` 當作純 Python 編譯
2. **部分型別宣告**：只為迴圈變數添加型別
3. **完整型別宣告**：為所有變數添加型別
4. **使用 LinkInfo 類別** vs **使用 dict**

記錄每種策略的效能，並分析哪些優化帶來最大效益。

## 延伸閱讀

- [Cython 官方文件](https://cython.readthedocs.io/)
- [Cython 最佳實踐](https://cython.readthedocs.io/en/latest/src/tutorial/cython_tutorial.html)
- [Cython 與 NumPy 整合](https://cython.readthedocs.io/en/latest/src/userguide/numpy_tutorial.html)
- [Cython 產生的 C 程式碼分析](https://cython.readthedocs.io/en/latest/src/userguide/debugging.html)

---

*返回：[案例研究](../)*
*返回：[模組四：用 C 擴展 Python](../../)*
