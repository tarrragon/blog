---
title: "案例：效能分析實戰"
date: 2026-01-21
description: "用 cProfile 和 line_profiler 分析 Markdown 連結檢查器的效能瓶頸"
weight: 1
---

# 案例：效能分析實戰

本案例基於 `.claude/lib/markdown_link_checker.py` 的實際程式碼，展示如何用 cProfile 和 line_profiler 進行效能分析。

## 先備知識

- [模組四基礎章節](../../)
- Python 正則表達式基礎

## 問題背景

### 現有設計

`markdown_link_checker.py` 是一個 Markdown 連結檢查工具，核心功能是解析文件中的連結並驗證其有效性。以下是關鍵的解析方法：

```python
import re
from typing import List, Dict

class MarkdownLinkChecker:
    """Markdown link checker with precompiled regex patterns"""

    # Precompiled regex patterns at class level (good practice!)
    INLINE_LINK_PATTERN = re.compile(
        r'(?<!!)\[([^\]]+)\]\(([^)]+)\)'
    )

    REFERENCE_DEF_PATTERN = re.compile(
        r'^\s*\[([^\]]+)\]:\s*(.+)$',
        re.MULTILINE
    )

    REFERENCE_USE_PATTERN = re.compile(
        r'\[([^\]]+)\]\[([^\]]+)\]'
    )

    def parse_markdown_links(self, content: str) -> List[Dict]:
        """
        Parse all links in Markdown content

        Args:
            content: Markdown content string

        Returns:
            list[dict]: List of links with text, target, line
        """
        links = []
        lines = content.split('\n')

        # First, collect reference-style link definitions
        reference_defs = {}
        for match in self.REFERENCE_DEF_PATTERN.finditer(content):
            ref_name = match.group(1).lower()
            ref_target = match.group(2).strip()
            reference_defs[ref_name] = ref_target

        # Track code block state
        in_code_block = False

        # Parse inline links line by line
        for line_num, line in enumerate(lines, start=1):
            # Check for code block boundaries
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            # Skip links inside code blocks
            if in_code_block:
                continue

            # Inline links: [text](target)
            for match in self.INLINE_LINK_PATTERN.finditer(line):
                links.append({
                    "text": match.group(1),
                    "target": match.group(2),
                    "line": line_num
                })

            # Reference-style links: [text][ref]
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

### 效能問題

處理大型文件時可能出現：

- **正則表達式效率問題**：複雜的 pattern 可能導致回溯
- **重複編譯正則表達式**：若 pattern 在方法內定義，每次呼叫都會重新編譯
- **不必要的字串操作**：`split()` 會建立新的字串列表
- **多次遍歷**：分別處理引用定義和行內連結

## 進階解決方案

### 分析目標

1. 找出效能瓶頸所在
2. 量化各部分的時間消耗
3. 驗證優化效果

### 實作步驟

#### 步驟 1：使用 cProfile 進行函式級分析

cProfile 是 Python 標準庫的效能分析工具，可以測量每個函式的呼叫次數和執行時間。

```python
import cProfile
import pstats
from io import StringIO
from pathlib import Path

def profile_link_checker():
    """Profile the markdown link checker with cProfile"""

    # Create test content with many links
    test_content = generate_test_content(num_links=1000)

    checker = MarkdownLinkChecker()

    # Create profiler
    profiler = cProfile.Profile()

    # Run profiling
    profiler.enable()
    for _ in range(100):  # Run multiple times for better statistics
        checker.parse_markdown_links(test_content)
    profiler.disable()

    # Analyze results
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')  # Sort by cumulative time
    stats.print_stats(20)  # Show top 20 functions

    print(stream.getvalue())

    return stats

def generate_test_content(num_links: int) -> str:
    """Generate test Markdown content with specified number of links"""
    lines = ["# Test Document\n"]

    for i in range(num_links):
        if i % 3 == 0:
            # Inline link
            lines.append(f"Check out [Link {i}](https://example.com/{i})\n")
        elif i % 3 == 1:
            # Reference-style link
            lines.append(f"See [Reference {i}][ref{i}]\n")
        else:
            # Plain text with potential regex traps
            lines.append(f"This is paragraph {i} with some [text] that looks like links.\n")

    # Add reference definitions at the end
    for i in range(num_links):
        if i % 3 == 1:
            lines.append(f"[ref{i}]: https://example.com/ref/{i}\n")

    return "".join(lines)

if __name__ == "__main__":
    profile_link_checker()
```

執行方式：

```bash
# Direct execution
python profile_link_checker.py

# Using cProfile from command line
python -m cProfile -s cumulative markdown_link_checker.py --dir ./docs/
```

#### 步驟 2：使用 pstats 分析結果

pstats 模組提供更細緻的結果分析功能：

```python
import cProfile
import pstats
from pstats import SortKey

def detailed_analysis():
    """Perform detailed analysis with pstats"""

    # Profile the code
    profiler = cProfile.Profile()
    profiler.enable()

    # Run the target function
    checker = MarkdownLinkChecker()
    content = generate_test_content(500)
    for _ in range(50):
        checker.parse_markdown_links(content)

    profiler.disable()

    # Create Stats object
    stats = pstats.Stats(profiler)

    # Different sorting options
    print("=" * 70)
    print("Top 10 by CUMULATIVE time (including sub-calls)")
    print("=" * 70)
    stats.sort_stats(SortKey.CUMULATIVE).print_stats(10)

    print("\n" + "=" * 70)
    print("Top 10 by TOTAL time (excluding sub-calls)")
    print("=" * 70)
    stats.sort_stats(SortKey.TIME).print_stats(10)

    print("\n" + "=" * 70)
    print("Top 10 by CALL count")
    print("=" * 70)
    stats.sort_stats(SortKey.CALLS).print_stats(10)

    # Filter by function name
    print("\n" + "=" * 70)
    print("Functions containing 'parse' or 'match'")
    print("=" * 70)
    stats.sort_stats(SortKey.TIME).print_stats('parse|match', 10)

    # Show callers of a specific function
    print("\n" + "=" * 70)
    print("Who calls 'finditer'?")
    print("=" * 70)
    stats.print_callers('finditer')

    # Save stats to file for later analysis
    stats.dump_stats('link_checker.prof')

    return stats

def load_and_compare_profiles():
    """Load and compare saved profile data"""
    try:
        # Load saved profile
        stats = pstats.Stats('link_checker.prof')

        # Add another profile for comparison
        stats.add('link_checker_optimized.prof')

        # Print combined stats
        stats.sort_stats(SortKey.CUMULATIVE).print_stats(20)
    except FileNotFoundError:
        print("Profile files not found. Run detailed_analysis() first.")
```

#### 步驟 3：使用 line_profiler 進行行級分析

line_profiler 可以分析每一行程式碼的執行時間，適合精確定位瓶頸。

首先安裝 line_profiler：

```bash
pip install line_profiler
```

使用裝飾器標記要分析的函式：

```python
# profile_lines.py
from line_profiler import profile

@profile
def parse_markdown_links_profiled(self, content: str):
    """
    Line-by-line profiled version of parse_markdown_links
    """
    links = []
    lines = content.split('\n')

    # Collect reference definitions
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

        # These regex operations might be slow
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

# Alternative: Manual timing for specific sections
import time

def parse_with_timing(self, content: str):
    """Manual timing for detailed analysis"""
    timings = {}

    # Time: split lines
    start = time.perf_counter()
    lines = content.split('\n')
    timings['split_lines'] = time.perf_counter() - start

    # Time: parse reference definitions
    start = time.perf_counter()
    reference_defs = {}
    for match in self.REFERENCE_DEF_PATTERN.finditer(content):
        ref_name = match.group(1).lower()
        ref_target = match.group(2).strip()
        reference_defs[ref_name] = ref_target
    timings['parse_refs'] = time.perf_counter() - start

    # Time: main parsing loop
    start = time.perf_counter()
    links = []
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

    timings['main_loop'] = time.perf_counter() - start

    return links, timings
```

執行 line_profiler：

```bash
# Run with kernprof
kernprof -l -v profile_lines.py

# Or use the newer approach
python -m line_profiler profile_lines.py
```

#### 步驟 4：分析正則表達式效能

正則表達式是常見的效能瓶頸，需要特別分析：

```python
import re
import time
from typing import Callable

def benchmark_regex_patterns():
    """Compare different regex pattern implementations"""

    # Test content with various edge cases
    test_lines = [
        "Check out [Link](https://example.com)",
        "See [Text with [brackets]](url)",
        "Multiple [link1](url1) and [link2](url2)",
        "No links here, just plain text",
        "Tricky [text](url) with more [text](url) links",
        "![Image](image.png) should be ignored",
        "[Link with spaces]( url with spaces )",
    ] * 1000

    test_content = "\n".join(test_lines)

    # Pattern 1: Original pattern
    pattern1 = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')

    # Pattern 2: Possessive-like (using atomic group simulation)
    # Note: Python re doesn't support possessive quantifiers directly
    pattern2 = re.compile(r'(?<!!)\[([^\]]*)\]\(([^)]*)\)')

    # Pattern 3: More specific pattern
    pattern3 = re.compile(r'(?<!!)\[([^\[\]]+)\]\(([^()]+)\)')

    # Pattern 4: Non-capturing groups where possible
    pattern4 = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')

    patterns = {
        "original": pattern1,
        "non_greedy": pattern2,
        "more_specific": pattern3,
        "optimized": pattern4,
    }

    results = {}

    for name, pattern in patterns.items():
        # Warmup
        for _ in range(10):
            list(pattern.finditer(test_content))

        # Benchmark
        start = time.perf_counter()
        for _ in range(100):
            matches = list(pattern.finditer(test_content))
        elapsed = time.perf_counter() - start

        results[name] = {
            "time": elapsed,
            "matches": len(matches),
        }

    # Print comparison
    print("Regex Pattern Performance Comparison")
    print("=" * 60)
    print(f"{'Pattern':<20} {'Time (s)':<12} {'Matches':<10}")
    print("-" * 60)

    baseline = results["original"]["time"]
    for name, data in results.items():
        speedup = baseline / data["time"]
        print(f"{name:<20} {data['time']:<12.4f} {data['matches']:<10} ({speedup:.2f}x)")

    return results

def analyze_regex_backtracking():
    """Analyze potential regex backtracking issues"""
    import re

    # Patterns that might cause backtracking
    problematic_patterns = [
        (r'\[(.+)\]\((.+)\)', "Greedy .+ can backtrack"),
        (r'\[([^\]]+)\]\(([^)]+)\)', "Negated class - better"),
        (r'\[(.*?)\]\((.*?)\)', "Non-greedy - still may backtrack"),
    ]

    # Pathological input that triggers backtracking
    pathological = "[" + "a" * 100 + "]"  # No closing bracket pattern

    print("Regex Backtracking Analysis")
    print("=" * 60)

    for pattern_str, description in problematic_patterns:
        pattern = re.compile(pattern_str)

        start = time.perf_counter()
        try:
            # Set a timeout using signal (Unix only)
            result = pattern.search(pathological)
            elapsed = time.perf_counter() - start
            print(f"Pattern: {pattern_str}")
            print(f"  Description: {description}")
            print(f"  Time: {elapsed:.4f}s")
            print(f"  Match: {result}")
            print()
        except Exception as e:
            print(f"Pattern: {pattern_str} - Error: {e}")

def compare_compile_vs_inline():
    """Compare precompiled vs inline regex performance"""

    test_content = generate_test_content(500)
    iterations = 100

    # Test 1: Precompiled pattern (recommended)
    compiled_pattern = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')

    start = time.perf_counter()
    for _ in range(iterations):
        list(compiled_pattern.finditer(test_content))
    compiled_time = time.perf_counter() - start

    # Test 2: Inline pattern (compiled each time by re module cache)
    start = time.perf_counter()
    for _ in range(iterations):
        list(re.finditer(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)', test_content))
    inline_time = time.perf_counter() - start

    # Test 3: Pattern compiled inside loop (worst case)
    start = time.perf_counter()
    for _ in range(iterations):
        pattern = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')
        list(pattern.finditer(test_content))
    loop_compile_time = time.perf_counter() - start

    print("Compile Strategy Comparison")
    print("=" * 60)
    print(f"{'Strategy':<25} {'Time (s)':<12} {'Relative':<10}")
    print("-" * 60)
    print(f"{'Precompiled (class)':<25} {compiled_time:<12.4f} {'1.00x':<10}")
    print(f"{'Inline (re cache)':<25} {inline_time:<12.4f} {inline_time/compiled_time:.2f}x")
    print(f"{'Compile in loop':<25} {loop_compile_time:<12.4f} {loop_compile_time/compiled_time:.2f}x")
```

#### 步驟 5：優化建議與驗證

根據分析結果，實作優化版本並驗證效果：

```python
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass(slots=True)  # Python 3.10+ optimization
class LinkInfo:
    """Link information with memory-efficient storage"""
    text: str
    target: str
    line: int

class OptimizedLinkChecker:
    """Optimized Markdown link checker based on profiling results"""

    # Precompiled patterns at class level
    INLINE_LINK_PATTERN = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')
    REFERENCE_DEF_PATTERN = re.compile(r'^\s*\[([^\]]+)\]:\s*(.+)$', re.MULTILINE)
    REFERENCE_USE_PATTERN = re.compile(r'\[([^\]]+)\]\[([^\]]+)\]')
    CODE_BLOCK_PATTERN = re.compile(r'^```')

    def parse_markdown_links_optimized(self, content: str) -> List[LinkInfo]:
        """
        Optimized link parsing with reduced memory allocation

        Optimizations:
        1. Use dataclass with slots for link storage
        2. Single pass where possible
        3. Avoid repeated string operations
        4. Use local variables for frequently accessed attributes
        """
        links = []

        # Cache pattern references for faster access
        inline_pattern = self.INLINE_LINK_PATTERN
        ref_use_pattern = self.REFERENCE_USE_PATTERN
        ref_def_pattern = self.REFERENCE_DEF_PATTERN

        # Collect reference definitions first (single pass over content)
        reference_defs = {
            match.group(1).lower(): match.group(2).strip()
            for match in ref_def_pattern.finditer(content)
        }

        # Process line by line
        in_code_block = False
        line_start = 0

        for line_num, line_end in enumerate(
            self._find_line_positions(content), start=1
        ):
            line = content[line_start:line_end]

            # Fast code block check
            if line.lstrip().startswith("```"):
                in_code_block = not in_code_block
                line_start = line_end + 1
                continue

            if not in_code_block:
                # Parse inline links
                for match in inline_pattern.finditer(line):
                    links.append(LinkInfo(
                        text=match.group(1),
                        target=match.group(2),
                        line=line_num
                    ))

                # Parse reference links
                for match in ref_use_pattern.finditer(line):
                    ref_name = match.group(2).lower()
                    target = reference_defs.get(ref_name)
                    if target:
                        links.append(LinkInfo(
                            text=match.group(1),
                            target=target,
                            line=line_num
                        ))

            line_start = line_end + 1

        return links

    def _find_line_positions(self, content: str):
        """Generator that yields line end positions"""
        pos = 0
        while True:
            newline = content.find('\n', pos)
            if newline == -1:
                yield len(content)
                break
            yield newline
            pos = newline + 1

def verify_optimization():
    """Verify that optimizations maintain correctness and improve performance"""
    import time

    # Generate test content
    test_content = generate_test_content(1000)

    # Original implementation
    original = MarkdownLinkChecker()

    # Optimized implementation
    optimized = OptimizedLinkChecker()

    # Verify correctness
    original_links = original.parse_markdown_links(test_content)
    optimized_links = optimized.parse_markdown_links_optimized(test_content)

    # Compare results
    assert len(original_links) == len(optimized_links), \
        f"Link count mismatch: {len(original_links)} vs {len(optimized_links)}"

    for orig, opt in zip(original_links, optimized_links):
        assert orig["text"] == opt.text, f"Text mismatch: {orig['text']} vs {opt.text}"
        assert orig["target"] == opt.target, f"Target mismatch"
        assert orig["line"] == opt.line, f"Line mismatch"

    print("Correctness verified!")

    # Benchmark
    iterations = 100

    # Original
    start = time.perf_counter()
    for _ in range(iterations):
        original.parse_markdown_links(test_content)
    original_time = time.perf_counter() - start

    # Optimized
    start = time.perf_counter()
    for _ in range(iterations):
        optimized.parse_markdown_links_optimized(test_content)
    optimized_time = time.perf_counter() - start

    print(f"\nPerformance Comparison ({iterations} iterations)")
    print("=" * 50)
    print(f"Original:  {original_time:.4f}s")
    print(f"Optimized: {optimized_time:.4f}s")
    print(f"Speedup:   {original_time / optimized_time:.2f}x")
```

### 完整程式碼

以下是整合所有分析功能的完整腳本：

```python
#!/usr/bin/env python3
"""
Performance Profiling Script for Markdown Link Checker

This script demonstrates various profiling techniques:
1. cProfile for function-level analysis
2. pstats for detailed statistics
3. line_profiler for line-by-line analysis
4. Regex pattern benchmarking
5. Optimization verification

Usage:
    python profiling_demo.py [--full|--quick|--regex|--verify]
"""

import argparse
import cProfile
import pstats
import re
import sys
import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from pstats import SortKey
from typing import Dict, List, Optional

# ===== Original Implementation =====

class MarkdownLinkChecker:
    """Original Markdown link checker for comparison"""

    INLINE_LINK_PATTERN = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')
    REFERENCE_DEF_PATTERN = re.compile(r'^\s*\[([^\]]+)\]:\s*(.+)$', re.MULTILINE)
    REFERENCE_USE_PATTERN = re.compile(r'\[([^\]]+)\]\[([^\]]+)\]')

    def parse_markdown_links(self, content: str) -> List[Dict]:
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

# ===== Test Data Generation =====

def generate_test_content(num_links: int) -> str:
    """Generate test Markdown content"""
    lines = ["# Test Document\n\n"]

    for i in range(num_links):
        if i % 3 == 0:
            lines.append(f"Check out [Link {i}](https://example.com/{i})\n")
        elif i % 3 == 1:
            lines.append(f"See [Reference {i}][ref{i}]\n")
        else:
            lines.append(f"Paragraph {i} with some text.\n")

    lines.append("\n")
    for i in range(num_links):
        if i % 3 == 1:
            lines.append(f"[ref{i}]: https://example.com/ref/{i}\n")

    return "".join(lines)

# ===== Profiling Functions =====

def run_cprofile_analysis(iterations: int = 50, num_links: int = 500):
    """Run cProfile analysis"""
    print("Running cProfile Analysis")
    print("=" * 70)

    content = generate_test_content(num_links)
    checker = MarkdownLinkChecker()

    profiler = cProfile.Profile()
    profiler.enable()

    for _ in range(iterations):
        checker.parse_markdown_links(content)

    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.sort_stats(SortKey.CUMULATIVE)

    print(f"\nTop 15 functions by cumulative time:")
    print("-" * 70)
    stats.print_stats(15)

    return stats

def run_regex_benchmark():
    """Benchmark different regex patterns"""
    print("\nRegex Pattern Benchmark")
    print("=" * 70)

    content = generate_test_content(500)

    patterns = {
        "Original": re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)'),
        "Non-greedy inner": re.compile(r'(?<!!)\[([^\]]*?)\]\(([^)]*?)\)'),
        "Anchored": re.compile(r'(?<!!)\[([^\[\]]+)\]\(([^()]+)\)'),
    }

    print(f"{'Pattern':<25} {'Time (ms)':<12} {'Matches':<10}")
    print("-" * 50)

    for name, pattern in patterns.items():
        # Warmup
        list(pattern.finditer(content))

        # Benchmark
        start = time.perf_counter()
        for _ in range(100):
            matches = list(pattern.finditer(content))
        elapsed = (time.perf_counter() - start) * 1000

        print(f"{name:<25} {elapsed:<12.2f} {len(matches):<10}")

def run_compile_comparison():
    """Compare precompiled vs inline regex"""
    print("\nCompile Strategy Comparison")
    print("=" * 70)

    content = generate_test_content(500)
    iterations = 100
    pattern_str = r'(?<!!)\[([^\]]+)\]\(([^)]+)\)'

    # Precompiled
    compiled = re.compile(pattern_str)
    start = time.perf_counter()
    for _ in range(iterations):
        list(compiled.finditer(content))
    compiled_time = time.perf_counter() - start

    # Inline (uses re module cache)
    start = time.perf_counter()
    for _ in range(iterations):
        list(re.finditer(pattern_str, content))
    inline_time = time.perf_counter() - start

    print(f"{'Strategy':<25} {'Time (ms)':<12} {'Relative':<10}")
    print("-" * 50)
    print(f"{'Precompiled':<25} {compiled_time*1000:<12.2f} {'1.00x':<10}")
    print(f"{'Inline (cached)':<25} {inline_time*1000:<12.2f} {inline_time/compiled_time:.2f}x")

def main():
    parser = argparse.ArgumentParser(description="Profiling Demo")
    parser.add_argument('--full', action='store_true', help='Run full analysis')
    parser.add_argument('--quick', action='store_true', help='Run quick analysis')
    parser.add_argument('--regex', action='store_true', help='Run regex benchmark')
    args = parser.parse_args()

    if args.regex:
        run_regex_benchmark()
        run_compile_comparison()
    elif args.quick:
        run_cprofile_analysis(iterations=10, num_links=100)
    else:
        run_cprofile_analysis()
        run_regex_benchmark()
        run_compile_comparison()

if __name__ == "__main__":
    main()
```

### 分析結果範例

執行 cProfile 分析後的典型輸出：

```text
Running cProfile Analysis
======================================================================

Top 15 functions by cumulative time:
----------------------------------------------------------------------
         125003 function calls in 0.892 seconds

   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
       50    0.012    0.000    0.892    0.018 checker.py:45(parse_markdown_links)
    25000    0.234    0.000    0.567    0.000 {method 'finditer' of 're.Pattern'}
       50    0.089    0.002    0.089    0.002 {method 'split' of 'str' objects}
    50000    0.156    0.000    0.156    0.000 {method 'append' of 'list' objects}
    25000    0.098    0.000    0.098    0.000 {method 'group' of 're.Match'}
    12500    0.045    0.000    0.045    0.000 {method 'lower' of 'str' objects}
    12500    0.034    0.000    0.034    0.000 {method 'strip' of 'str' objects}
    25000    0.067    0.000    0.067    0.000 {method 'startswith' of 'str' objects}
       50    0.023    0.000    0.023    0.000 {built-in method builtins.enumerate}
```

從上述結果可以觀察到：

1. **`finditer` 佔用最多時間**：正則表達式匹配是主要瓶頸
2. **`split` 操作耗時明顯**：每次解析都建立新的行列表
3. **`append` 呼叫頻繁**：大量的字典建立和列表操作

line_profiler 的典型輸出：

```text
Timer unit: 1e-06 s

Total time: 0.456 s
File: checker.py
Function: parse_markdown_links at line 45

Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
    45                                           def parse_markdown_links(self, content):
    46        50       1234.0     24.7      0.3      links = []
    47        50      89012.0   1780.2     19.5      lines = content.split('\n')
    48
    49        50         56.0      1.1      0.0      reference_defs = {}
    50      2500      45678.0     18.3     10.0      for match in self.REFERENCE_DEF_PATTERN.finditer(content):
    51      2450       3456.0      1.4      0.8          ref_name = match.group(1).lower()
    52      2450       2345.0      1.0      0.5          ref_target = match.group(2).strip()
    53      2450       1234.0      0.5      0.3          reference_defs[ref_name] = ref_target
    54
    55        50         34.0      0.7      0.0      in_code_block = False
    56
    57     25050      12345.0      0.5      2.7      for line_num, line in enumerate(lines, start=1):
    58     25000      34567.0      1.4      7.6          if line.strip().startswith("```"):
    59                                                       in_code_block = not in_code_block
    60                                                       continue
    61
    62     25000       5678.0      0.2      1.2          if in_code_block:
    63                                                       continue
    64
    65     25000     156789.0      6.3     34.4          for match in self.INLINE_LINK_PATTERN.finditer(line):
    66      8350      23456.0      2.8      5.1              links.append({...})
    67
    68     25000      78901.0      3.2     17.3          for match in self.REFERENCE_USE_PATTERN.finditer(line):
    69      2450       1234.0      0.5      0.3              ref_name = match.group(2).lower()
    70      2450        567.0      0.2      0.1              if ref_name in reference_defs:
    71      2450       1234.0      0.5      0.3                  links.append({...})
    72
    73        50         23.0      0.5      0.0      return links
```

關鍵發現：

- **第 65 行（行內連結匹配）佔 34.4%**：這是最大的瓶頸
- **第 47 行（split）佔 19.5%**：字串分割是第二大消耗
- **第 68 行（引用連結匹配）佔 17.3%**：也是重要的優化目標

## 設計權衡

| 面向 | 不分析 | 使用 cProfile | 使用 line_profiler |
|------|--------|---------------|-------------------- |
| 開發時間 | 少 | 中等 | 較多 |
| 分析粒度 | 無 | 函式級 | 行級 |
| 效能開銷 | 無 | 低 | 較高 |
| 適用場景 | 簡單程式 | 一般優化 | 精確定位 |
| 學習成本 | 無 | 低 | 中等 |
| 結果準確度 | - | 高 | 非常高 |

## 什麼時候該做效能分析？

適合分析：
- 程式明顯變慢
- 處理大量資料
- 發布前的效能驗證
- 正則表達式複雜時
- 有迴圈處理大量項目

不建議過早優化：
- 功能還在開發中
- 使用頻率很低
- 效能已經足夠
- 可讀性更重要時

## 練習

### 基礎練習：用 cProfile 分析排序函式

```python
"""
Exercise 1: Profile different sorting approaches
"""
import cProfile
import pstats
import random
from pstats import SortKey

def bubble_sort(arr):
    """Bubble sort implementation"""
    n = len(arr)
    arr = arr.copy()
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

def quick_sort(arr):
    """Quick sort implementation"""
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)

def profile_sorting():
    """Profile and compare sorting algorithms"""
    data = [random.randint(0, 10000) for _ in range(1000)]

    # Profile bubble sort
    profiler = cProfile.Profile()
    profiler.enable()
    bubble_sort(data)
    profiler.disable()

    print("Bubble Sort Profile:")
    stats = pstats.Stats(profiler)
    stats.sort_stats(SortKey.TIME).print_stats(5)

    # Profile quick sort
    profiler = cProfile.Profile()
    profiler.enable()
    quick_sort(data)
    profiler.disable()

    print("\nQuick Sort Profile:")
    stats = pstats.Stats(profiler)
    stats.sort_stats(SortKey.TIME).print_stats(5)

if __name__ == "__main__":
    profile_sorting()
```

### 進階練習：用 line_profiler 找出熱點程式碼

```python
"""
Exercise 2: Use line_profiler to find hotspots

Instructions:
1. Install line_profiler: pip install line_profiler
2. Add @profile decorator to functions you want to analyze
3. Run: kernprof -l -v exercise2.py
"""
from line_profiler import profile

@profile
def find_primes(n):
    """Find all prime numbers up to n"""
    primes = []
    for num in range(2, n + 1):
        is_prime = True
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
    return primes

@profile
def find_primes_sieve(n):
    """Find primes using Sieve of Eratosthenes"""
    sieve = [True] * (n + 1)
    sieve[0] = sieve[1] = False

    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            for j in range(i * i, n + 1, i):
                sieve[j] = False

    return [i for i, is_prime in enumerate(sieve) if is_prime]

if __name__ == "__main__":
    print("Finding primes up to 10000...")
    primes1 = find_primes(10000)
    primes2 = find_primes_sieve(10000)
    print(f"Found {len(primes1)} primes (basic)")
    print(f"Found {len(primes2)} primes (sieve)")
```

### 挑戰題：比較不同正則表達式寫法的效能差異

```python
"""
Exercise 3: Compare regex pattern performance

Task: Parse email addresses from text using different patterns
and measure their performance.
"""
import re
import time

def benchmark_email_patterns():
    """Compare different email regex patterns"""

    # Test content with mixed valid and invalid emails
    test_text = """
    Contact us at support@example.com or sales@company.org
    Invalid: not.an.email, @missing.com, missing@
    Valid: user.name+tag@domain.co.uk, test123@sub.domain.com
    Edge cases: "quoted"@domain.com, user@[192.168.1.1]
    """ * 1000

    patterns = {
        # Simple pattern (may miss some valid emails)
        "simple": re.compile(r'\b[\w.-]+@[\w.-]+\.\w+\b'),

        # More comprehensive pattern
        "comprehensive": re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ),

        # RFC 5322 inspired (complex but thorough)
        "rfc_inspired": re.compile(
            r'(?:[a-z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&\'*+/=?^_`{|}~-]+)*'
            r'|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]'
            r'|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")'
            r'@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?'
            r'|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:'
            r'(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]'
            r'|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])',
            re.IGNORECASE
        ),
    }

    print("Email Pattern Performance Comparison")
    print("=" * 60)
    print(f"{'Pattern':<20} {'Time (ms)':<12} {'Matches':<10}")
    print("-" * 60)

    for name, pattern in patterns.items():
        # Warmup
        list(pattern.findall(test_text))

        # Benchmark
        start = time.perf_counter()
        for _ in range(100):
            matches = pattern.findall(test_text)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"{name:<20} {elapsed:<12.2f} {len(matches):<10}")

    # Your task: Add more patterns and analyze the results
    # Consider: What trade-offs exist between accuracy and speed?

if __name__ == "__main__":
    benchmark_email_patterns()
```

## 延伸閱讀

- [cProfile 官方文件](https://docs.python.org/3/library/profile.html)
- [line_profiler GitHub](https://github.com/pyutils/line_profiler)
- [Python 正則表達式效能](https://docs.python.org/3/howto/regex.html#common-problems)
- [py-spy - Sampling profiler](https://github.com/benfred/py-spy)

---

*下一章：[記憶體優化](../memory-optimization/)*
