---
title: "案例研究：效能優化實戰"
date: 2026-01-21
description: "基於 .claude/lib 的效能優化實戰案例"
weight: 10
---

# 案例研究：效能優化實戰

本系列案例基於 `.claude/lib` 的實際程式碼，展示如何用並行處理和效能優化技術改善真實系統。

## 案例列表

### 並行處理

| 案例 | 素材 | 技術 | 預期加速 |
| ---- | ---- | ---- | -------- |
| [並行檔案檢查](parallel-file-check/) | markdown_link_checker.py | ThreadPoolExecutor | 3-5x |
| [並行 Hook 驗證](parallel-hook-validation/) | hook_validator.py | as_completed + 進度 | 3-5x |

### 效能調優

| 案例 | 素材 | 技術 | 預期加速 |
| ---- | ---- | ---- | -------- |
| [正則表達式預編譯](regex-precompile/) | hook_validator.py | re.compile | 1.2-1.3x |
| [LRU 快取](lru-cache-branch/) | git_utils.py | functools.lru_cache | 視命中率 |
| [資料結構選擇](data-structure-choice/) | hook_validator.py | set vs list | 10-100x |

## 學習路徑

```text
並行檔案檢查（入門）
    ↓
並行 Hook 驗證（進階：含進度報告）
    ↓
正則表達式預編譯（效能調優入門）
    ↓
LRU 快取（快取策略）
    ↓
資料結構選擇（演算法思維）
```

## 可執行程式碼

所有案例都有對應的可執行程式碼：

```bash
# 下載程式碼
cd /path/to/your/workspace

# 執行效能測試
python benchmarks/benchmark_parallel.py
python benchmarks/benchmark_regex.py
python benchmarks/benchmark_cache.py
python benchmarks/benchmark_data_structure.py

# 執行效能分析
python profiling/profile_link_checker.py
```

## 先備知識

建議先完成以下章節：

- [8.1 並行處理實戰](../parallel-processing/)
- [8.2 效能調優實戰](../performance-tuning/)

---

*返回：[模組八：實戰效能優化](../)*
