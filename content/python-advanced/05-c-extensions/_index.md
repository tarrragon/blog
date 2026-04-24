---
title: "模組五：用 C 擴展 Python"
date: 2026-01-20
description: "學習使用 ctypes、cffi、Cython、pybind11 擴展 Python"
weight: 5
---


本模組介紹如何使用 C/C++ 擴展 Python，提升效能或整合現有的 C 函式庫。

## 為什麼學習 C 擴展？

- **效能極致**：當 Python 太慢時的解決方案
- **整合現有庫**：呼叫 C/C++ 函式庫
- **理解生態系**：NumPy、SciPy 等高效能套件的實現原理

## 章節列表

| 章節                                                 | 主題           | 關鍵收穫             |
| ---------------------------------------------------- | -------------- | -------------------- |
| [5.1](/python-advanced/05-c-extensions/ctypes-cffi/) | ctypes 與 cffi | 動態綁定 C 函式庫    |
| [5.2](/python-advanced/05-c-extensions/cython/)      | Cython         | Python 語法的 C 速度 |
| [5.3](/python-advanced/05-c-extensions/pybind11/)    | pybind11       | 現代 C++ 綁定        |
| [5.4](/python-advanced/05-c-extensions/when-to-use/) | 選擇指南       | 工具比較與決策       |

## 工具選擇快速指南

```text
沒有原始碼 ──────→ ctypes / cffi
純 C 函式庫 ─────→ cffi 或 Cython
C++ 函式庫 ──────→ pybind11
優化現有 Python ─→ Cython
```

## 先備知識

- 進階系列 [模組四：CPython 內部機制](/python-advanced/04-cpython-internals/)
- 基本的 C 語言知識（指標、結構體、記憶體管理）

## 學習時間

每章節約 45-60 分鐘，全模組約 3-4 小時

---

*上一模組：[模組四：CPython 內部機制](/python-advanced/04-cpython-internals/)*
*下一模組：[模組六：用 Rust 擴展 Python](/python-advanced/06-rust-extensions/)*
