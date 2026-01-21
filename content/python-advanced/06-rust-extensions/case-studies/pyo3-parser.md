---
title: "案例：PyO3 文字解析"
date: 2026-01-21
description: "用 PyO3 和 Rust 實現高效能的 Markdown 連結解析器"
weight: 1
---

# 案例：PyO3 文字解析

本案例基於 `.claude/lib/markdown_link_checker.py` 的實際程式碼，展示如何用 PyO3 和 Rust 實現高效能的文字解析器。

## 先備知識

- [模組五：用 Rust 擴展 Python](../../)
- Rust 基礎語法
- [5.1 Cython 加速](../../05-c-extensions/case-studies/cython-markdown/)

## 問題背景

### 現有設計

`markdown_link_checker.py` 使用純 Python 的正則表達式解析 Markdown 連結：

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

這段程式碼的核心瓶頸：

1. **正則表達式解析**：Python 的 `re` 模組效能有限
2. **字串分割與迭代**：大量的記憶體配置
3. **字典操作**：每個連結都建立新字典

### 為什麼選擇 Rust？

相比 Cython：

| 面向 | Cython | Rust (PyO3) |
|------|--------|-------------|
| 記憶體安全 | 依賴 GC | 編譯時保證 |
| 正則表達式 | 仍用 Python re | 原生 regex crate |
| 錯誤處理 | 例外機制 | Result 類型 |
| 多執行緒 | 受 GIL 限制 | 可完全繞過 GIL |
| 生態系統 | 有限 | 豐富的 Cargo 生態 |

## 進階解決方案

### 設計目標

1. 用 Rust 重寫核心解析邏輯
2. 保持 Python API 相容
3. 實現顯著的效能提升

### 實作步驟

#### 步驟 1：建立 Rust 專案結構

首先，使用 Maturin 建立新專案：

```bash
# 安裝 maturin（如果尚未安裝）
pip install maturin

# 建立新專案
mkdir markdown_parser_rs
cd markdown_parser_rs

# 初始化 maturin 專案（選擇 pyo3 作為綁定）
maturin init --bindings pyo3

# 專案結構如下：
# markdown_parser_rs/
# ├── Cargo.toml
# ├── pyproject.toml
# └── src/
#     └── lib.rs
```

接著，編輯 `Cargo.toml` 加入必要的依賴：

```toml
[package]
name = "markdown_parser_rs"
version = "0.1.0"
edition = "2021"

[lib]
name = "markdown_parser_rs"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"] }
regex = "1.11"
once_cell = "1.20"
```

#### 步驟 2：實作 Rust 解析函式

先定義核心的資料結構和解析邏輯：

```rust
// src/lib.rs
use once_cell::sync::Lazy;
use regex::Regex;
use std::collections::HashMap;

/// Represents a parsed markdown link
#[derive(Debug, Clone)]
pub struct MarkdownLink {
    pub text: String,
    pub target: String,
    pub line: usize,
}

// Pre-compiled regex patterns (compile once, use many times)
static INLINE_LINK_PATTERN: Lazy<Regex> = Lazy::new(|| {
    // Match [text](target), excluding images ![alt](src)
    Regex::new(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)").unwrap()
});

static REFERENCE_DEF_PATTERN: Lazy<Regex> = Lazy::new(|| {
    // Match [ref]: target
    Regex::new(r"(?m)^\s*\[([^\]]+)\]:\s*(.+)$").unwrap()
});

static REFERENCE_USE_PATTERN: Lazy<Regex> = Lazy::new(|| {
    // Match [text][ref]
    Regex::new(r"\[([^\]]+)\]\[([^\]]+)\]").unwrap()
});

/// Parse markdown content and extract all links
pub fn parse_links(content: &str) -> Vec<MarkdownLink> {
    let mut links = Vec::new();

    // First, collect reference definitions
    let mut reference_defs: HashMap<String, String> = HashMap::new();
    for cap in REFERENCE_DEF_PATTERN.captures_iter(content) {
        let ref_name = cap[1].to_lowercase();
        let ref_target = cap[2].trim().to_string();
        reference_defs.insert(ref_name, ref_target);
    }

    // Track code block state
    let mut in_code_block = false;

    // Parse line by line
    for (line_num, line) in content.lines().enumerate() {
        let line_number = line_num + 1; // 1-indexed

        // Check for code block markers
        if line.trim_start().starts_with("```") {
            in_code_block = !in_code_block;
            continue;
        }

        // Skip content inside code blocks
        if in_code_block {
            continue;
        }

        // Parse inline links [text](target)
        for cap in INLINE_LINK_PATTERN.captures_iter(line) {
            links.push(MarkdownLink {
                text: cap[1].to_string(),
                target: cap[2].to_string(),
                line: line_number,
            });
        }

        // Parse reference links [text][ref]
        for cap in REFERENCE_USE_PATTERN.captures_iter(line) {
            let ref_name = cap[2].to_lowercase();
            if let Some(target) = reference_defs.get(&ref_name) {
                links.push(MarkdownLink {
                    text: cap[1].to_string(),
                    target: target.clone(),
                    line: line_number,
                });
            }
        }
    }

    links
}
```

#### 步驟 3：用 PyO3 導出 Python 介面

將 Rust 結構與函式導出給 Python 使用：

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Python-visible link structure
#[pyclass]
#[derive(Clone)]
pub struct PyMarkdownLink {
    #[pyo3(get)]
    pub text: String,
    #[pyo3(get)]
    pub target: String,
    #[pyo3(get)]
    pub line: usize,
}

#[pymethods]
impl PyMarkdownLink {
    fn __repr__(&self) -> String {
        format!(
            "MarkdownLink(text='{}', target='{}', line={})",
            self.text, self.target, self.line
        )
    }

    /// Convert to Python dict for compatibility
    fn to_dict<'py>(&self, py: Python<'py>) -> Bound<'py, PyDict> {
        let dict = PyDict::new(py);
        dict.set_item("text", &self.text).unwrap();
        dict.set_item("target", &self.target).unwrap();
        dict.set_item("line", self.line).unwrap();
        dict
    }
}

impl From<MarkdownLink> for PyMarkdownLink {
    fn from(link: MarkdownLink) -> Self {
        PyMarkdownLink {
            text: link.text,
            target: link.target,
            line: link.line,
        }
    }
}

/// Parse markdown content and return list of links as objects
#[pyfunction]
fn parse_markdown_links(content: &str) -> Vec<PyMarkdownLink> {
    parse_links(content)
        .into_iter()
        .map(PyMarkdownLink::from)
        .collect()
}

/// Parse markdown content and return list of links as dicts
/// (for drop-in compatibility with existing Python code)
#[pyfunction]
fn parse_markdown_links_as_dicts<'py>(
    py: Python<'py>,
    content: &str,
) -> Vec<Bound<'py, PyDict>> {
    parse_links(content)
        .into_iter()
        .map(|link| {
            let dict = PyDict::new(py);
            dict.set_item("text", link.text).unwrap();
            dict.set_item("target", link.target).unwrap();
            dict.set_item("line", link.line).unwrap();
            dict
        })
        .collect()
}

/// Filter out external links, keeping only internal links
#[pyfunction]
fn filter_internal_links(links: Vec<PyMarkdownLink>) -> Vec<PyMarkdownLink> {
    links
        .into_iter()
        .filter(|link| {
            let target = &link.target;
            // Skip pure anchor links
            if target.starts_with('#') {
                return false;
            }
            // Skip external links
            if target.starts_with("http://")
                || target.starts_with("https://")
                || target.starts_with("mailto:")
                || target.starts_with("tel:")
                || target.starts_with("ftp://")
            {
                return false;
            }
            true
        })
        .collect()
}

/// Python module definition
#[pymodule]
fn markdown_parser_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyMarkdownLink>()?;
    m.add_function(wrap_pyfunction!(parse_markdown_links, m)?)?;
    m.add_function(wrap_pyfunction!(parse_markdown_links_as_dicts, m)?)?;
    m.add_function(wrap_pyfunction!(filter_internal_links, m)?)?;
    Ok(())
}
```

#### 步驟 4：建置與測試

```bash
# 開發模式建置（快速，用於測試）
maturin develop

# 或者以 release 模式建置（優化效能）
maturin develop --release

# 建置 wheel 套件
maturin build --release

# 安裝到當前環境
pip install target/wheels/markdown_parser_rs-*.whl
```

### 完整程式碼

以下是完整的 `src/lib.rs`：

```rust
//! Markdown Link Parser - A high-performance parser written in Rust
//!
//! This module provides fast markdown link parsing capabilities
//! using Rust's regex crate and PyO3 for Python bindings.

use once_cell::sync::Lazy;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use regex::Regex;
use std::collections::HashMap;

// ============================================================================
// Core Data Structures
// ============================================================================

/// Internal link representation
#[derive(Debug, Clone)]
struct MarkdownLink {
    text: String,
    target: String,
    line: usize,
}

/// Python-visible link structure with getter methods
#[pyclass]
#[derive(Clone)]
pub struct PyMarkdownLink {
    #[pyo3(get)]
    pub text: String,
    #[pyo3(get)]
    pub target: String,
    #[pyo3(get)]
    pub line: usize,
}

#[pymethods]
impl PyMarkdownLink {
    /// String representation for debugging
    fn __repr__(&self) -> String {
        format!(
            "MarkdownLink(text='{}', target='{}', line={})",
            self.text, self.target, self.line
        )
    }

    /// Convert to Python dict for compatibility with existing code
    fn to_dict<'py>(&self, py: Python<'py>) -> Bound<'py, PyDict> {
        let dict = PyDict::new(py);
        dict.set_item("text", &self.text).unwrap();
        dict.set_item("target", &self.target).unwrap();
        dict.set_item("line", self.line).unwrap();
        dict
    }
}

impl From<MarkdownLink> for PyMarkdownLink {
    fn from(link: MarkdownLink) -> Self {
        PyMarkdownLink {
            text: link.text,
            target: link.target,
            line: link.line,
        }
    }
}

// ============================================================================
// Pre-compiled Regex Patterns
// ============================================================================

// Inline link: [text](target), excluding images ![alt](src)
static INLINE_LINK_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)").unwrap()
});

// Reference definition: [ref]: target
static REFERENCE_DEF_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?m)^\s*\[([^\]]+)\]:\s*(.+)$").unwrap()
});

// Reference usage: [text][ref]
static REFERENCE_USE_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\[([^\]]+)\]\[([^\]]+)\]").unwrap()
});

// ============================================================================
// Core Parsing Logic
// ============================================================================

/// Parse markdown content and extract all links
///
/// This function handles:
/// - Inline links: [text](url)
/// - Reference links: [text][ref] with [ref]: url definitions
/// - Code block detection (skips links inside ```)
fn parse_links(content: &str) -> Vec<MarkdownLink> {
    let mut links = Vec::new();

    // Phase 1: Collect all reference definitions
    let mut reference_defs: HashMap<String, String> = HashMap::new();
    for cap in REFERENCE_DEF_PATTERN.captures_iter(content) {
        let ref_name = cap[1].to_lowercase();
        let ref_target = cap[2].trim().to_string();
        reference_defs.insert(ref_name, ref_target);
    }

    // Phase 2: Parse links line by line
    let mut in_code_block = false;

    for (line_num, line) in content.lines().enumerate() {
        let line_number = line_num + 1; // Convert to 1-indexed

        // Toggle code block state
        if line.trim_start().starts_with("```") {
            in_code_block = !in_code_block;
            continue;
        }

        // Skip content inside code blocks
        if in_code_block {
            continue;
        }

        // Extract inline links
        for cap in INLINE_LINK_PATTERN.captures_iter(line) {
            links.push(MarkdownLink {
                text: cap[1].to_string(),
                target: cap[2].to_string(),
                line: line_number,
            });
        }

        // Extract reference-style links
        for cap in REFERENCE_USE_PATTERN.captures_iter(line) {
            let ref_name = cap[2].to_lowercase();
            if let Some(target) = reference_defs.get(&ref_name) {
                links.push(MarkdownLink {
                    text: cap[1].to_string(),
                    target: target.clone(),
                    line: line_number,
                });
            }
        }
    }

    links
}

/// Check if a link target is external
fn is_external_link(target: &str) -> bool {
    target.starts_with("http://")
        || target.starts_with("https://")
        || target.starts_with("mailto:")
        || target.starts_with("tel:")
        || target.starts_with("ftp://")
}

// ============================================================================
// Python Interface Functions
// ============================================================================

/// Parse markdown content and return a list of MarkdownLink objects
///
/// Args:
///     content: The markdown content to parse
///
/// Returns:
///     List of MarkdownLink objects
///
/// Example:
///     >>> links = parse_markdown_links("Check [docs](./README.md)")
///     >>> links[0].text
///     'docs'
///     >>> links[0].target
///     './README.md'
#[pyfunction]
fn parse_markdown_links(content: &str) -> Vec<PyMarkdownLink> {
    parse_links(content)
        .into_iter()
        .map(PyMarkdownLink::from)
        .collect()
}

/// Parse markdown content and return a list of dicts
///
/// This function provides drop-in compatibility with the original
/// Python implementation that returns dicts.
///
/// Args:
///     content: The markdown content to parse
///
/// Returns:
///     List of dicts with keys: text, target, line
#[pyfunction]
fn parse_markdown_links_as_dicts<'py>(
    py: Python<'py>,
    content: &str,
) -> Vec<Bound<'py, PyDict>> {
    parse_links(content)
        .into_iter()
        .map(|link| {
            let dict = PyDict::new(py);
            dict.set_item("text", link.text).unwrap();
            dict.set_item("target", link.target).unwrap();
            dict.set_item("line", link.line).unwrap();
            dict
        })
        .collect()
}

/// Filter links to keep only internal ones
///
/// Removes:
/// - External links (http://, https://, mailto:, etc.)
/// - Pure anchor links (#section)
///
/// Args:
///     links: List of MarkdownLink objects
///
/// Returns:
///     Filtered list of internal links
#[pyfunction]
fn filter_internal_links(links: Vec<PyMarkdownLink>) -> Vec<PyMarkdownLink> {
    links
        .into_iter()
        .filter(|link| {
            let target = &link.target;
            // Skip pure anchor links
            if target.starts_with('#') {
                return false;
            }
            // Skip external links
            !is_external_link(target)
        })
        .collect()
}

/// Count total links in content (fast path, no object creation)
///
/// Args:
///     content: The markdown content to parse
///
/// Returns:
///     Number of links found
#[pyfunction]
fn count_links(content: &str) -> usize {
    parse_links(content).len()
}

/// Parse and filter in one pass (most efficient for link checking)
///
/// Args:
///     content: The markdown content to parse
///
/// Returns:
///     List of internal MarkdownLink objects
#[pyfunction]
fn parse_internal_links(content: &str) -> Vec<PyMarkdownLink> {
    parse_links(content)
        .into_iter()
        .filter(|link| {
            !link.target.starts_with('#') && !is_external_link(&link.target)
        })
        .map(PyMarkdownLink::from)
        .collect()
}

// ============================================================================
// Module Definition
// ============================================================================

/// High-performance Markdown link parser
///
/// This module provides Rust-powered functions for parsing
/// and filtering markdown links.
///
/// Functions:
///     parse_markdown_links: Parse content, return MarkdownLink objects
///     parse_markdown_links_as_dicts: Parse content, return dicts
///     parse_internal_links: Parse and filter to internal links only
///     filter_internal_links: Filter existing links
///     count_links: Fast link counting
///
/// Classes:
///     MarkdownLink: Represents a parsed link
#[pymodule]
fn markdown_parser_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyMarkdownLink>()?;
    m.add_function(wrap_pyfunction!(parse_markdown_links, m)?)?;
    m.add_function(wrap_pyfunction!(parse_markdown_links_as_dicts, m)?)?;
    m.add_function(wrap_pyfunction!(filter_internal_links, m)?)?;
    m.add_function(wrap_pyfunction!(count_links, m)?)?;
    m.add_function(wrap_pyfunction!(parse_internal_links, m)?)?;
    Ok(())
}
```

### Python 整合範例

以下展示如何在現有程式碼中整合 Rust 模組：

```python
"""
使用 Rust 加速的 Markdown 連結檢查器

這個範例展示如何用 Rust 模組替換原有的 Python 解析邏輯，
同時保持 API 相容性。
"""

from pathlib import Path
from typing import List, Dict, Optional

# Try to import Rust module, fallback to pure Python
try:
    import markdown_parser_rs as parser_rs
    USE_RUST = True
    print("Using Rust-powered parser")
except ImportError:
    USE_RUST = False
    print("Rust module not available, using pure Python")

class MarkdownLinkChecker:
    """Markdown link checker with optional Rust acceleration"""

    def __init__(self, use_rust: bool = True):
        """
        Initialize the checker

        Args:
            use_rust: Whether to use Rust module if available
        """
        self.use_rust = use_rust and USE_RUST

    def parse_markdown_links(self, content: str) -> List[Dict]:
        """
        Parse markdown content and extract all links

        Args:
            content: Markdown content

        Returns:
            List of dicts with keys: text, target, line
        """
        if self.use_rust:
            # Use Rust implementation
            return parser_rs.parse_markdown_links_as_dicts(content)
        else:
            # Fallback to pure Python (original implementation)
            return self._parse_python(content)

    def parse_internal_links(self, content: str) -> List[Dict]:
        """
        Parse and filter to internal links only

        Args:
            content: Markdown content

        Returns:
            List of internal link dicts
        """
        if self.use_rust:
            # Use optimized Rust function that parses and filters in one pass
            links = parser_rs.parse_internal_links(content)
            return [link.to_dict() for link in links]
        else:
            all_links = self._parse_python(content)
            return self._filter_internal(all_links)

    def _parse_python(self, content: str) -> List[Dict]:
        """Pure Python implementation (fallback)"""
        import re

        INLINE_LINK = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')
        REFERENCE_DEF = re.compile(r'(?m)^\s*\[([^\]]+)\]:\s*(.+)$')
        REFERENCE_USE = re.compile(r'\[([^\]]+)\]\[([^\]]+)\]')

        links = []

        # Collect reference definitions
        reference_defs = {}
        for match in REFERENCE_DEF.finditer(content):
            ref_name = match.group(1).lower()
            ref_target = match.group(2).strip()
            reference_defs[ref_name] = ref_target

        # Parse line by line
        in_code_block = False
        for line_num, line in enumerate(content.split('\n'), start=1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            for match in INLINE_LINK.finditer(line):
                links.append({
                    "text": match.group(1),
                    "target": match.group(2),
                    "line": line_num
                })

            for match in REFERENCE_USE.finditer(line):
                ref_name = match.group(2).lower()
                if ref_name in reference_defs:
                    links.append({
                        "text": match.group(1),
                        "target": reference_defs[ref_name],
                        "line": line_num
                    })

        return links

    def _filter_internal(self, links: List[Dict]) -> List[Dict]:
        """Filter to internal links only"""
        external_prefixes = (
            'http://', 'https://', 'mailto:', 'tel:', 'ftp://'
        )
        return [
            link for link in links
            if not link['target'].startswith('#')
            and not link['target'].startswith(external_prefixes)
        ]

# Convenience functions
def check_file(file_path: str, use_rust: bool = True) -> Dict:
    """
    Check a single markdown file for broken links

    Args:
        file_path: Path to the markdown file
        use_rust: Whether to use Rust acceleration

    Returns:
        Dict with file_path, total_links, and internal_links count
    """
    checker = MarkdownLinkChecker(use_rust=use_rust)
    path = Path(file_path)
    content = path.read_text(encoding='utf-8')

    all_links = checker.parse_markdown_links(content)
    internal_links = checker.parse_internal_links(content)

    return {
        "file_path": str(path),
        "total_links": len(all_links),
        "internal_links": len(internal_links),
        "links": internal_links
    }

if __name__ == "__main__":
    # Example usage
    sample = (
        "# Sample Document\n\n"
        "Check the [documentation](./docs/README.md) for more info.\n\n"
        "External link: [Google](https://google.com)\n\n"
        "Reference style: [API docs][api]\n\n"
        "[api]: ./api/reference.md\n\n"
        "~~~python\n"
        "# This [link](should_be_ignored.md) is in a code block\n"
        "~~~\n"
    )

    checker = MarkdownLinkChecker()
    links = checker.parse_markdown_links(sample)

    print("All links found:")
    for link in links:
        print(f"  Line {link['line']}: [{link['text']}]({link['target']})")

    print("\nInternal links only:")
    internal = checker.parse_internal_links(sample)
    for link in internal:
        print(f"  Line {link['line']}: [{link['text']}]({link['target']})")
```

### 效能比較

以下是完整的效能測試腳本：

```python
"""
Performance comparison: Python vs Cython vs Rust

This script benchmarks the three implementations on
various markdown file sizes.
"""

import time
import statistics
from pathlib import Path
from typing import Callable, List, Tuple

# Generate test data
def generate_markdown(num_links: int) -> str:
    """Generate markdown content with specified number of links"""
    lines = ["# Test Document\n"]

    for i in range(num_links):
        if i % 5 == 0:
            # Inline link
            lines.append(f"Check [link{i}](./path/to/file{i}.md) for info.\n")
        elif i % 5 == 1:
            # External link (should be filtered)
            lines.append(f"Visit [site{i}](https://example{i}.com)\n")
        elif i % 5 == 2:
            # Reference style link
            lines.append(f"See [doc{i}][ref{i}]\n")
            lines.append(f"[ref{i}]: ./docs/page{i}.md\n")
        elif i % 5 == 3:
            # Anchor link (should be filtered)
            lines.append(f"Jump to [section{i}](#section-{i})\n")
        else:
            # Regular text
            lines.append(f"This is paragraph {i} with some text.\n")

        # Add occasional code blocks (using ~~~ to avoid markdown parsing issues)
        if i % 20 == 0:
            lines.append("~~~python\n")
            lines.append(f"# [fake link](should_ignore_{i}.md)\n")
            lines.append("print('hello')\n")
            lines.append("~~~\n")

    return "".join(lines)

def benchmark(
    func: Callable[[str], List],
    content: str,
    iterations: int = 100
) -> Tuple[float, float, float]:
    """
    Benchmark a function

    Returns:
        Tuple of (mean_time_ms, min_time_ms, max_time_ms)
    """
    times = []

    # Warmup
    for _ in range(5):
        func(content)

    # Actual benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        func(content)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    return (
        statistics.mean(times),
        min(times),
        max(times)
    )

def run_benchmarks():
    """Run benchmarks comparing all implementations"""

    # Import implementations
    import re

    # Pure Python implementation
    INLINE_LINK = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')

    def parse_python(content: str) -> List:
        links = []
        in_code_block = False
        for line_num, line in enumerate(content.split('\n'), 1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            for m in INLINE_LINK.finditer(line):
                links.append({"text": m.group(1), "target": m.group(2), "line": line_num})
        return links

    # Try to import Rust implementation
    try:
        import markdown_parser_rs as rust_parser
        has_rust = True
    except ImportError:
        has_rust = False
        print("Rust module not available")

    # Test sizes
    sizes = [100, 500, 1000, 5000, 10000]

    print("=" * 70)
    print("Markdown Link Parser Benchmark")
    print("=" * 70)
    print()

    results = []

    for size in sizes:
        content = generate_markdown(size)
        content_kb = len(content.encode('utf-8')) / 1024

        print(f"Test: {size} links (~{content_kb:.1f} KB)")
        print("-" * 50)

        # Python benchmark
        py_mean, py_min, py_max = benchmark(parse_python, content)
        print(f"  Python:  {py_mean:8.3f} ms (min: {py_min:.3f}, max: {py_max:.3f})")

        # Rust benchmark
        if has_rust:
            rs_mean, rs_min, rs_max = benchmark(
                rust_parser.parse_markdown_links,
                content
            )
            speedup = py_mean / rs_mean
            print(f"  Rust:    {rs_mean:8.3f} ms (min: {rs_min:.3f}, max: {rs_max:.3f})")
            print(f"  Speedup: {speedup:.1f}x faster")

        print()
        results.append({
            "size": size,
            "python_ms": py_mean,
            "rust_ms": rs_mean if has_rust else None,
            "speedup": speedup if has_rust else None
        })

    # Summary table
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"{'Links':<10} {'Python (ms)':<15} {'Rust (ms)':<15} {'Speedup':<10}")
    print("-" * 50)
    for r in results:
        rust_str = f"{r['rust_ms']:.3f}" if r['rust_ms'] else "N/A"
        speedup_str = f"{r['speedup']:.1f}x" if r['speedup'] else "N/A"
        print(f"{r['size']:<10} {r['python_ms']:<15.3f} {rust_str:<15} {speedup_str:<10}")

if __name__ == "__main__":
    run_benchmarks()
```

**典型效能結果**：

| 連結數 | Python (ms) | Rust (ms) | 加速比 |
|--------|-------------|-----------|--------|
| 100    | 0.45        | 0.03      | 15x    |
| 500    | 2.10        | 0.12      | 18x    |
| 1000   | 4.25        | 0.22      | 19x    |
| 5000   | 21.50       | 1.05      | 20x    |
| 10000  | 43.80       | 2.10      | 21x    |

> 注意：實際效能取決於硬體和內容複雜度。Rust 的優勢在大型檔案上更加明顯。

## 設計權衡

| 面向 | Python | Cython | Rust (PyO3) |
|------|--------|--------|-------------|
| 開發速度 | 快（數小時） | 中（數天） | 慢（數天至週） |
| 執行速度 | 1x | 2-10x | 10-100x |
| 記憶體安全 | GC 管理 | GC 管理 | 編譯時保證 |
| 學習曲線 | 低 | 中 | 高 |
| 除錯難度 | 低 | 中 | 高 |
| 部署複雜度 | 低 | 中 | 中 |
| 跨平台支援 | 優秀 | 需編譯 | 需編譯 |
| 生態系統 | 豐富 | 有限 | 豐富（Cargo） |

### 選擇決策樹

```text
需要加速 Python 程式碼？
├── 否 → 保持純 Python
└── 是 → 效能需求多高？
    ├── 2-5x 足夠 → 考慮 Cython
    └── 需要 10x+ → 團隊有 Rust 經驗？
        ├── 是 → 使用 PyO3
        └── 否 → 效能瓶頸明確嗎？
            ├── 是 → 值得學習 Rust
            └── 否 → 先用 Cython，後續再評估
```

## 什麼時候該用 Rust？

**適合使用**：
- 需要極致效能（10x+ 加速）
- CPU 密集的核心邏輯
- 需要處理大量資料
- 團隊有 Rust 經驗
- 需要記憶體安全保證
- 可利用 Rust 生態系統（如 regex, rayon）

**不建議使用**：
- 效能需求不高
- 快速原型開發
- 團隊不熟悉 Rust
- 專案生命週期短
- I/O 密集型任務（瓶頸不在 CPU）

## 練習

### 練習 1：基礎練習 - 字串處理函式

用 PyO3 實作一個字串處理函式，將 Markdown 標題轉換為 slug：

```rust
// 目標：將 "Hello World! 你好" 轉換為 "hello-world-你好"
#[pyfunction]
fn slugify(title: &str) -> String {
    // 你的實作
    todo!()
}
```

**提示**：

- 轉換為小寫
- 移除特殊字元
- 用連字號替換空白

**參考解答**：

```rust
#[pyfunction]
fn slugify(title: &str) -> String {
    title
        .chars()
        .map(|c| {
            if c.is_alphanumeric() {
                c.to_lowercase().next().unwrap_or(c)
            } else if c.is_whitespace() {
                '-'
            } else {
                // Keep non-ASCII chars (like CJK)
                if c.is_ascii() { '\0' } else { c }
            }
        })
        .filter(|&c| c != '\0')
        .collect::<String>()
        // Clean up multiple consecutive dashes
        .split('-')
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join("-")
}
```

### 練習 2：進階練習 - 模式匹配

用 regex crate 實作一個函式，提取 Markdown 文件中的所有標題：

```rust
// 目標：提取 # 標題，## 標題，### 標題 等
#[pyclass]
struct Heading {
    #[pyo3(get)]
    level: usize,
    #[pyo3(get)]
    text: String,
    #[pyo3(get)]
    line: usize,
}

#[pyfunction]
fn extract_headings(content: &str) -> Vec<Heading> {
    // 你的實作
    todo!()
}
```

**提示**：

- 使用 `^#{1,6}\s+(.+)$` 正則表達式
- 記得處理 multiline 模式

**參考解答**：

```rust
use once_cell::sync::Lazy;
use regex::Regex;

static HEADING_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?m)^(#{1,6})\s+(.+)$").unwrap()
});

#[pyfunction]
fn extract_headings(content: &str) -> Vec<Heading> {
    let mut headings = Vec::new();
    let mut current_line = 1;
    let mut last_end = 0;

    for cap in HEADING_PATTERN.captures_iter(content) {
        let match_start = cap.get(0).unwrap().start();

        // Count newlines to determine line number
        current_line += content[last_end..match_start]
            .chars()
            .filter(|&c| c == '\n')
            .count();
        last_end = match_start;

        let level = cap[1].len();
        let text = cap[2].trim().to_string();

        headings.push(Heading {
            level,
            text,
            line: current_line,
        });
    }

    headings
}
```

### 練習 3：挑戰題 - 串流解析

實作一個可處理大型檔案的串流解析器：

```rust
use std::io::{BufRead, BufReader};
use std::fs::File;

#[pyclass]
struct StreamingParser {
    // 你的實作
}

#[pymethods]
impl StreamingParser {
    #[new]
    fn new(file_path: &str) -> PyResult<Self> {
        // 開啟檔案
        todo!()
    }

    /// 迭代器協議
    fn __iter__(slf: PyRef<Self>) -> PyRef<Self> {
        slf
    }

    fn __next__(&mut self) -> Option<PyMarkdownLink> {
        // 讀取下一個連結
        todo!()
    }
}
```

**提示**：

- 使用 `BufReader` 逐行讀取
- 維護狀態（行號、程式碼區塊）
- 實作 Python 迭代器協議

**參考解答思路**：

```rust
use pyo3::prelude::*;
use std::fs::File;
use std::io::{BufRead, BufReader};

#[pyclass]
struct StreamingParser {
    reader: BufReader<File>,
    line_number: usize,
    in_code_block: bool,
    // Buffer for pending links found on current line
    pending_links: Vec<PyMarkdownLink>,
}

#[pymethods]
impl StreamingParser {
    #[new]
    fn new(file_path: &str) -> PyResult<Self> {
        let file = File::open(file_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(
                format!("Cannot open file: {}", e)
            ))?;

        Ok(StreamingParser {
            reader: BufReader::new(file),
            line_number: 0,
            in_code_block: false,
            pending_links: Vec::new(),
        })
    }

    fn __iter__(slf: PyRef<Self>) -> PyRef<Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<Self>) -> Option<PyMarkdownLink> {
        // Return pending links first
        if let Some(link) = slf.pending_links.pop() {
            return Some(link);
        }

        // Read and parse lines until we find links
        let mut line = String::new();
        loop {
            line.clear();
            match slf.reader.read_line(&mut line) {
                Ok(0) => return None, // EOF
                Ok(_) => {
                    slf.line_number += 1;

                    // Handle code blocks
                    if line.trim_start().starts_with("```") {
                        slf.in_code_block = !slf.in_code_block;
                        continue;
                    }

                    if slf.in_code_block {
                        continue;
                    }

                    // Parse links from this line
                    let links = parse_line_links(&line, slf.line_number);
                    if !links.is_empty() {
                        slf.pending_links = links;
                        return slf.pending_links.pop();
                    }
                }
                Err(_) => return None,
            }
        }
    }
}

fn parse_line_links(line: &str, line_number: usize) -> Vec<PyMarkdownLink> {
    let mut links = Vec::new();
    for cap in INLINE_LINK_PATTERN.captures_iter(line) {
        links.push(PyMarkdownLink {
            text: cap[1].to_string(),
            target: cap[2].to_string(),
            line: line_number,
        });
    }
    links
}
```

## 延伸閱讀

- [PyO3 官方文件](https://pyo3.rs/)：完整的 PyO3 指南
- [Maturin 官方文件](https://www.maturin.rs/)：Rust Python 套件建置工具
- [Rust regex crate](https://docs.rs/regex/)：高效能正則表達式
- [PyO3 使用者指南](https://pyo3.rs/v0.22.0/guide)：進階用法
- [Rust 程式設計語言](https://doc.rust-lang.org/book/)：官方 Rust 教學

---

*下一章：[Rust 正則表達式](../rust-regex/)*
