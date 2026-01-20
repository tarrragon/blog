---
title: "模組一：非同步程式設計（asyncio）"
date: 2026-01-20
description: "Python 的異步程式設計模型，掌握現代 Web/網路開發的必備技能"
weight: 1
---

# 模組一：非同步程式設計（asyncio）

Python 的 `asyncio` 模組提供了異步程式設計的基礎設施。本模組將帶你從基礎概念到實戰應用，全面掌握 Python 的異步程式設計。

## 為什麼學習 asyncio？

在現代 Python 開發中，asyncio 已經成為處理 I/O 密集任務的標準方案：

- **Web 框架**：FastAPI、Starlette 都以 asyncio 為基礎
- **網路客戶端**：aiohttp、httpx 的異步 API
- **資料庫**：SQLAlchemy 2.0、asyncpg 的異步支援
- **效能**：單執行緒處理數千個並發連線

## 與入門系列的關係

入門系列介紹了 threading 和 multiprocessing，它們解決的是不同問題：

| 方案 | 適用場景 | 並發模型 |
|------|---------|---------|
| threading | I/O 密集，需要共享記憶體 | 多執行緒並行 |
| multiprocessing | CPU 密集 | 多進程並行 |
| **asyncio** | I/O 密集，大量並發 | 單執行緒協作式並發 |

asyncio 不是要取代 threading，而是提供另一種選擇：在單執行緒中高效處理大量 I/O 並發任務。

## 章節列表

| 章節 | 主題 | 關鍵收穫 |
|------|------|---------|
| [1.1](fundamentals/) | 基礎概念與事件迴圈 | 理解 asyncio 的核心概念 |
| [1.2](coroutines-tasks/) | 協程與 Task 管理 | 掌握 async/await 語法 |
| [1.3](patterns/) | 設計模式與最佳實踐 | 學會常見的異步模式 |
| [1.4](real-world/) | 實戰：與同步程式碼整合 | 在現有專案中應用 asyncio |

## 先備知識

- 入門系列 [3.7 並行處理](../../python/03-stdlib/concurrency/)
- 了解 I/O 密集 vs CPU 密集的區別
- 基本的 Python 函式與類別

## 學習建議

1. **循序漸進**：按章節順序學習，每章都建立在前一章的基礎上
2. **動手實作**：每章都有實作練習，請實際執行程式碼
3. **對比思考**：與 threading 做對比，理解各自的優缺點

## 常見誤解

在開始之前，先澄清一些常見誤解：

> **誤解**：asyncio 可以讓程式碼變快

**事實**：asyncio 不會讓單一任務變快，它讓你能在等待 I/O 時做其他事情。

> **誤解**：asyncio 是多執行緒

**事實**：asyncio 是單執行緒的協作式多任務，不會繞過 GIL。

> **誤解**：async/await 只是語法糖

**事實**：async/await 定義了一種全新的程式設計模型，需要理解其背後的概念。

## 學習時間

每章節約 30-45 分鐘，全模組約 2-3 小時

---

*上一模組：[入門系列](../../python/)*
*下一模組：[模組二：元編程](../02-metaprogramming/)*
