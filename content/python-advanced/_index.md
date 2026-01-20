---
title: "Python 進階指南"
date: 2026-01-20
description: "深入 Python 內部機制與擴展開發"
weight: 31
---

# Python 進階指南

本系列為已完成入門教學的工程師設計，深入探討 Python 的內部機制、元編程技術、效能優化方案，以及如何用 C/Rust 擴展 Python。

## 目標讀者

- 已完成 [Python 維護工程師實戰指南](../python/) 的工程師
- 想深入理解 Python 運作原理的開發者
- 需要撰寫高效能或複雜系統的人
- 想要開發框架或擴展 Python 的進階使用者

## 學習目標

1. 理解 Python 的異步程式設計模型
2. 掌握元編程技術（Descriptor、Metaclass）
3. 運用進階設計模式建構可擴展系統
4. 了解 CPython 的內部機制
5. 學會用 C 或 Rust 擴展 Python
6. 掌握現代 Python 套件打包與發布

## 教學模組

### [模組一：非同步程式設計（asyncio）](01-asyncio/)

Python 的異步程式設計模型，掌握現代 Web/網路開發的必備技能。

- [基礎概念與事件迴圈](01-asyncio/fundamentals/)
- [協程與 Task 管理](01-asyncio/coroutines-tasks/)
- [設計模式與最佳實踐](01-asyncio/patterns/)
- [實戰：與同步程式碼整合](01-asyncio/real-world/)

### [模組二：元編程](02-metaprogramming/)

深入 Python 的元編程機制，理解框架（Django、SQLAlchemy）的實現原理。

- [Descriptor Protocol 完整指南](02-metaprogramming/descriptors/)
- [Metaclass 設計與應用](02-metaprogramming/metaclasses/)
- [類別裝飾器與動態類別](02-metaprogramming/class-creation/)
- [反射與 inspect 模組](02-metaprogramming/introspection/)

### [模組三：進階設計模式](03-design-patterns/)

將元編程知識應用到實際系統設計，建構可擴展、可維護的架構。

- [泛型進階](03-design-patterns/generics/)
- [異常設計架構](03-design-patterns/exception-design/)
- [進階上下文管理](03-design-patterns/context-managers/)
- [插件系統設計](03-design-patterns/plugin-system/)
- [設計模式整合案例](03-design-patterns/integration/)

### [模組四：CPython 內部機制](04-cpython-internals/)

深入 CPython 直譯器，理解 Python 如何運作。

- [PyObject 與物件模型](04-cpython-internals/object-model/)
- [記憶體管理與垃圾回收](04-cpython-internals/memory-gc/)
- [Bytecode 與虛擬機](04-cpython-internals/bytecode/)
- [GIL 與執行緒模型](04-cpython-internals/gil-threading/)
- [Free-Threading](04-cpython-internals/free-threading/)

### [模組五：用 C 擴展 Python](05-c-extensions/)

當 Python 太慢時的解決方案：用 C/C++ 擴展 Python。

- [ctypes 與 cffi：動態綁定](05-c-extensions/ctypes-cffi/)
- [Cython：Python 語法的 C 速度](05-c-extensions/cython/)
- [pybind11：現代 C++ 綁定](05-c-extensions/pybind11/)
- [選擇指南與效能比較](05-c-extensions/when-to-use/)

### [模組六：用 Rust 擴展 Python](06-rust-extensions/)

用 Rust 的記憶體安全特性擴展 Python，兼顧效能與安全。

- [為什麼選擇 Rust？](06-rust-extensions/why-rust/)
- [PyO3 基礎](06-rust-extensions/pyo3-basics/)
- [Maturin 開發流程](06-rust-extensions/maturin-workflow/)
- [實戰案例分析](06-rust-extensions/real-world-examples/)

### [模組七：打包與發布](07-packaging/)

從開發到發布的完整流程，掌握現代 Python 套件管理。

- [pyproject.toml 完整指南](07-packaging/pyproject-toml/)
- [建構系統比較：setuptools vs Poetry vs Hatch](07-packaging/build-systems/)
- [發布到 PyPI](07-packaging/distribution/)
- [套件維護最佳實踐](07-packaging/best-practices/)

## 學習路徑

### 路徑 A：Web/API 開發者

```text
模組一（asyncio）→ 模組三（設計模式）→ 模組七（打包）
```

重點：非同步程式設計、系統架構設計、套件發布

### 路徑 B：框架開發者

```text
模組二（元編程）→ 模組三（設計模式）→ 模組四（CPython）→ 模組七（打包）
```

重點：理解框架實現原理、建立自己的抽象

### 路徑 C：效能工程師

```text
模組四（CPython）→ 模組五（C 擴展）或 模組六（Rust 擴展）
```

重點：理解瓶頸、用原生語言加速

### 路徑 D：完整學習

```text
模組一 → 模組二 → 模組三 → 模組四 → 模組五/六 → 模組七
```

按順序學習，建立完整知識體系

## 先備知識

本系列假設你已經具備：

- Python 基礎語法與物件導向程式設計
- 基本的並行處理概念（threading、multiprocessing）
- 了解 GIL 的基本概念

如果還不熟悉這些概念，建議先完成 [入門系列](../python/)。

## 每章結構

每章都採用「由淺到深」的結構：

1. **原理層**：為什麼需要這個？概念解釋
2. **設計層**：如何設計？設計決策與架構選擇
3. **實作層**：如何實現？程式碼範例
4. **實戰應用**：完整案例與最佳實踐

---

*文件版本：v0.1.0*
*最後更新：2026-01-20*
*系列狀態：建構中*
