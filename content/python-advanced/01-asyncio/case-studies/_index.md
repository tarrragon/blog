---
title: "案例研究：非同步程式設計實戰"
date: 2026-01-21
description: "基於 Hook 系統的 asyncio 實戰案例"
weight: 10
---

# 案例研究：非同步程式設計實戰

本系列案例基於 `.claude/lib` 的實際程式碼，展示如何用 asyncio 解決實際問題。

## 案例列表

| 案例 | 素材 | 進階技術 | 難度 |
|------|------|----------|------|
| [非同步 subprocess](async-subprocess/) | git_utils.py | asyncio.create_subprocess_exec | ⭐⭐ |
| [並行 I/O 操作](parallel-io/) | git_utils.py | asyncio.gather, TaskGroup | ⭐⭐ |
| [同步/非同步橋接](sync-async-bridge/) | 整個 lib | run_in_executor | ⭐⭐⭐ |

## 學習路徑

```text
非同步 subprocess（入門）
    ↓
並行 I/O 操作（基礎）
    ↓
同步/非同步橋接（整合）
```

## 先備知識

建議先完成以下章節：

- [1.1 基礎概念與事件迴圈](../fundamentals/)
- [1.2 協程與 Task 管理](../coroutines-tasks/)
- [1.4 實戰：與同步程式碼整合](../real-world/)

---

*返回：[模組一：非同步程式設計](../)*
