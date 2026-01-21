---
title: "模組八：實戰效能優化"
date: 2026-01-21
description: "將入門系列的並行處理與效能優化知識應用於真實系統"
weight: 8
---

# 模組八：實戰效能優化

本模組將入門系列學到的「並行處理」和「效能優化」知識，應用於 `.claude/lib` 的實際程式碼，展示如何分析、測量、優化真實系統。

## 與入門系列的關係

```text
入門系列                          本模組
3.7 並行處理 ──────────────────→ 並行處理實戰
    (概念與 API)                   (應用於真實系統)

3.8 效能優化 ──────────────────→ 效能調優實戰
    (原則與工具)                   (實際測量與改善)
```

入門系列教你「工具怎麼用」，本模組教你「什麼時候用、用了效果如何」。

## 為什麼需要這個模組？

在入門系列中，我們學習了：

- `ThreadPoolExecutor` 和 `ProcessPoolExecutor` 的用法
- `timeit`、`cProfile` 等效能測量工具
- 正則表達式、資料結構選擇等優化技巧

但在實際專案中，你可能會問：

- **這段程式碼值得優化嗎？** → 需要先測量
- **用並行能快多少？** → 需要實際比較
- **優化後維護成本增加多少？** → 需要權衡

本模組透過真實案例回答這些問題。

## 章節列表

| 章節 | 主題 | 關鍵收穫 |
| ---- | ---- | -------- |
| [8.1](parallel-processing/) | 並行處理實戰 | 將 I/O 密集任務並行化 |
| [8.2](performance-tuning/) | 效能調優實戰 | 測量、分析、優化的完整流程 |

## 案例研究

基於 `.claude/lib` 實際程式碼的進階案例：

| 案例 | 素材 | 學習重點 |
| ---- | ---- | -------- |
| [並行檔案檢查](case-studies/parallel-file-check/) | markdown_link_checker.py | ThreadPoolExecutor |
| [並行 Hook 驗證](case-studies/parallel-hook-validation/) | hook_validator.py | as_completed + 進度報告 |
| [正則表達式預編譯](case-studies/regex-precompile/) | hook_validator.py | re.compile 效能提升 |
| [LRU 快取](case-studies/lru-cache-branch/) | git_utils.py | functools.lru_cache |
| [資料結構選擇](case-studies/data-structure-choice/) | hook_validator.py | list vs set 查詢效能 |

## 可執行程式碼

本模組提供完整的可執行程式碼，放在 `/static/code/practical-optimization/`：

```text
practical-optimization/
├── original/           # 原始版本（對照組）
├── optimized/          # 優化版本
├── benchmarks/         # 效能測試腳本
└── profiling/          # 效能分析腳本
```

你可以下載這些程式碼，在自己的環境中執行效能測試。

## 先備知識

| 章節 | 需要先讀 |
| ---- | -------- |
| 8.1 並行處理實戰 | 入門系列 [3.7 並行處理](../../python/03-stdlib/concurrency/) |
| 8.2 效能調優實戰 | 入門系列 [3.8 效能優化](../../python/03-stdlib/performance/) |

## 學習目標

完成本模組後，你將能夠：

1. **識別優化機會**：判斷哪些程式碼值得優化
2. **測量效能基準**：使用 cProfile、timeit 建立基準數據
3. **應用並行處理**：選擇適當的並行模式加速 I/O 任務
4. **實施效能優化**：正則預編譯、快取策略、資料結構選擇
5. **評估優化效果**：比較優化前後的效能差異

## 學習時間

每章節約 30-45 分鐘，全模組約 2-3 小時

---

*上一模組：[模組七：打包與發布](../07-packaging/)*
