---
title: "模組五：用 Rust 擴展 Python"
date: 2026-01-20
description: "學習使用 PyO3 和 Maturin 用 Rust 擴展 Python"
weight: 5
---

# 模組五：用 Rust 擴展 Python

本模組介紹如何使用 Rust 擴展 Python，結合 Rust 的記憶體安全與高效能。

## 為什麼選擇 Rust？

- **記憶體安全**：沒有空指標、沒有資料競爭
- **零成本抽象**：高階語法，底層效能
- **現代工具鏈**：Cargo 生態系統的便利性

## 章節列表

| 章節 | 主題 | 關鍵收穫 |
|------|------|---------|
| [5.1](why-rust/) | 為什麼選擇 Rust？ | Rust vs C/C++ 的比較 |
| [5.2](pyo3-basics/) | PyO3 基礎 | Rust 的 Python 綁定 |
| [5.3](maturin-workflow/) | Maturin 開發流程 | 建構與發布工具 |
| [5.4](real-world-examples/) | 實戰案例分析 | 知名專案的 Rust 應用 |

## 使用 Rust 的知名 Python 套件

- **tiktoken**（OpenAI）：快速的 tokenizer
- **tokenizers**（Hugging Face）：NLP tokenizer
- **polars**：高效能 DataFrame 函式庫
- **pydantic-core**：Pydantic v2 的核心

## 先備知識

- 進階系列 [模組三：CPython 內部機制](../03-cpython-internals/)
- 基本的 Rust 語言知識（所有權、生命週期、Result/Option）

## 學習時間

每章節約 45-60 分鐘，全模組約 3-4 小時

---

*上一模組：[模組四：用 C 擴展 Python](../04-c-extensions/)*
*下一模組：[模組六：打包與發布](../06-packaging/)*
