---
title: "模組二：元編程"
description: "深入 Python 的元編程機制，理解框架的實現原理"
weight: 2
---

# 模組二：元編程

元編程（Metaprogramming）是指撰寫可以操作程式碼的程式碼。Python 提供了豐富的元編程機制，包括 Descriptor、Metaclass、類別裝飾器等。

## 為什麼學習元編程？

理解元編程機制有多重好處：

- **理解框架**：Django Model、SQLAlchemy、Pydantic 都大量使用元編程
- **建立抽象**：可以設計更優雅的 API
- **深入 Python**：理解 Python 物件模型的本質

## 章節列表

| 章節 | 主題 | 關鍵收穫 |
|------|------|---------|
| [2.1](descriptors/) | Descriptor Protocol 完整指南 | 理解 @property 的本質 |
| [2.2](metaclasses/) | Metaclass 設計與應用 | 控制類別的建立過程 |
| [2.3](class-creation/) | 類別裝飾器與動態類別 | @dataclass 的實現原理 |
| [2.4](introspection/) | 反射與 inspect 模組 | 程式檢視自身的能力 |

## 先備知識

- 入門系列 [4.4 單例與快取](../../python/04-oop/singleton-cache/)
- 熟悉 Python 的類別與物件

## 何時使用元編程？

元編程強大但複雜，使用前請考慮：

| 場景 | 建議 |
|------|------|
| 需要驗證屬性 | 先考慮 @property |
| 需要修改類別 | 先考慮類別裝飾器 |
| 需要控制子類別 | 先考慮 __init_subclass__ |
| 需要深度定制 | 才考慮 Metaclass |

**原則**：能用簡單方案解決就不用複雜方案。

## 學習時間

每章節約 30-45 分鐘，全模組約 2-3 小時

---

*上一模組：[模組一：非同步程式設計](../01-asyncio/)*
*下一模組：[模組三：CPython 內部機制](../03-cpython-internals/)*
