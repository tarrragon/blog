---
title: "案例研究"
date: 2026-01-21
description: "基於 .claude/lib 實際程式碼的 CPython 內部機制案例"
weight: 100
---

# 案例研究

本節收錄基於 `.claude/lib` 實際程式碼的案例研究，展示如何應用 CPython 內部機制知識進行效能分析與優化。

## 案例列表

| 案例 | 素材 | 學習重點 |
|------|------|---------|
| [效能分析實戰](profiling/) | markdown_link_checker.py | cProfile、line_profiler、效能瓶頸定位 |
| [記憶體優化](memory-optimization/) | config_loader.py | __slots__、weakref、記憶體佔用分析 |

## 學習路徑

建議先完成本模組的理論章節，再閱讀案例研究：

1. 理解 CPython 的物件模型
2. 學習效能分析工具
3. 通過案例實踐優化技巧
