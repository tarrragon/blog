---
title: "模組三：CPython 內部機制"
description: "深入 CPython 直譯器，理解 Python 如何運作"
weight: 3
---

# 模組三：CPython 內部機制

本模組深入 CPython 直譯器的內部，幫助你理解 Python 的運作原理。

## 為什麼學習 CPython 內部？

- **寫出更好的程式碼**：理解底層機制有助於避免效能陷阱
- **除錯能力**：深入理解有助於解決複雜問題
- **銜接擴展**：為 C/Rust 擴展開發打基礎

## 章節列表

| 章節 | 主題 | 關鍵收穫 |
|------|------|---------|
| [3.1](object-model/) | PyObject 與物件模型 | 理解「一切皆物件」 |
| [3.2](memory-gc/) | 記憶體管理與垃圾回收 | 理解記憶體如何管理 |
| [3.3](bytecode/) | Bytecode 與虛擬機 | 理解程式碼如何執行 |
| [3.4](gil-threading/) | GIL 與執行緒模型 | 深入理解 GIL |

## 先備知識

- 入門系列 [3.7 並行處理](../../python/03-stdlib/concurrency/)
- 入門系列 [3.8 Free-Threading](../../python/03-stdlib/free-threading/)

## 學習時間

每章節約 30-45 分鐘，全模組約 2-3 小時

---

*上一模組：[模組二：元編程](../02-metaprogramming/)*
*下一模組：[模組四：用 C 擴展 Python](../04-c-extensions/)*
