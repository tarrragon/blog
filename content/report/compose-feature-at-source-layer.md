---
title: "Feature 操作要跟 Source 同層合成"
date: 2026-04-26
weight: 64
description: "Filter / sort / count / transform / search 是 stream 操作、必須跟 stream 的 materialization 同層或更上游合成。在下游做 = 操作 subset 不是 stream。本原則跨前端 UI、後端 API、演算法管線通用、不只是視覺層 vs 資料層。"
tags: ["report", "事後檢討", "工程方法論", "Architecture", "原則"]
---

## 核心原則

**Stream 操作（filter / sort / count / transform / search）必須跟 stream 的 materialization 同層或更上游合成。** 在下游合成 = 操作的對象是 subset、不是 stream。

這是 #55 [Filter 與 Source 的層錯位](../view-layer-filter-vs-source-layer/) 的抽象升級 — 不限於「視覺層 vs 資料層」、適用任何分層系統（前端 / 後端 / 演算法管線 / 資料庫）。

---

## 抽象結構

```text
[Stream Source]
   ↓ (materialize 部分)
[Subset L1]
   ↓ (再 materialize)
[Subset L2]
   ↓ ...
```

Stream 操作要套在哪一層、決定它「過濾的範圍」是什麼：

| 套在哪一層    | 操作範圍        |
| ------------- | --------------- |
| Stream Source | 完整 stream     |
| Subset L1     | L1 子集         |
| Subset L2     | L1 的子集的子集 |

使用者 / 呼叫者通常想要的是「完整 stream 的操作結果」、不是「下游 subset 的結果」。在下游做 = 跟意圖不對齊。

---

## 多面向：跨領域的同個結構

### 領域 1：前端 UI（#55 的 case）

- Stream：完整搜尋結果集
- Materialize：pagefind 分批 fetch
- Subset：已載入的 result
- 錯誤合成：在 view 層 filter（subset 上做）

### 領域 2：後端 API + middleware

```text
[Database query result]  ← stream source
  ↓
[ORM materialize as objects]  ← L1 subset (lazy load 部分欄位)
  ↓
[API response]  ← L2 subset (pagination 後)
  ↓
[Middleware filter]  ← 錯誤位置 — 已是 subset 了
```

Middleware 過濾「pagination 後的回應」 — 漏掉沒在這頁的符合項。應該推進 ORM query。

### 領域 3：演算法管線

```python
def pipeline():
    for chunk in load_chunks():       # stream source
        for item in chunk:             # L1
            processed = transform(item) # L2
            yield processed             # L3

# 錯誤合成
results = list(pipeline())
filtered = [x for x in results if matches(x)]
# ↑ 如果上游有 take(N) 或 break、filtered 對的是 subset
```

對例：filter 推到 transform 之前 / 之內。

### 領域 4：資料庫 + materialized view

```sql
-- 錯誤：在 view 上 filter
SELECT * FROM materialized_view WHERE x = 1;
-- ↑ materialized_view 可能是 partial / stale

-- 對例：filter 推進原表
SELECT * FROM source_table WHERE x = 1;
-- 或 view 重建時 filter 已加進去
```

### 領域 5：Map / Reduce

```text
[shards] → [map output partial] → [reduce]
                                       ↓
                                  [post-reduce filter]  ← 錯位
```

Filter 應該在 map 階段（per-shard）或 reduce 內、不是 reduce 後。

**五個領域共用結構**：在 materialization 下游做 stream 操作 → silent 缺口。

---

## 同層合成的具體做法

### 做法 1：把操作推進 source query

最直接 — source 端就回符合的、根本沒 subset。

對應 #61 [Pattern：推進 query](../pattern-query-side-pushdown/)。

### 做法 2：在 materialization 過程中合成

如果 source 是 lazy stream、操作放進 stream 而不是事後：

```python
# 對例：filter 放進 stream
def filtered_pipeline(predicate):
    for chunk in load_chunks():
        for item in chunk:
            if predicate(item):
                yield item
```

每筆 materialize 時就 filter、不累積到 subset 後再做。

### 做法 3：自動續抓直到湊滿

當 source 不能改、且 materialization 是分批 — 用 loop 把分批變透明。

對應 #60 [Pattern：自動續抓](../pattern-fetch-until-quota/)。

### 做法 4：明示降級到 subset 操作

不能同層合成 → 顯式告訴呼叫者「我只在 subset 上做」、而不是假裝在 stream 上做。

對應 #62 [Pattern：誠實進度 UX](../pattern-honest-progress-ui/)。

---

## 跟 #63 形狀原則的關係

[#63 資料源的形狀決定 feature 的形狀](../data-source-shape-defines-feature-shape/) 講「形狀是硬約束」 — 本文講「在硬約束下、操作該放哪一層」。

| 維度 | #63                       | 本文                   |
| ---- | ------------------------- | ---------------------- |
| 焦點 | 形狀如何約束 feature 設計 | 操作如何跟 stream 合成 |
| 階段 | 設計 / 規劃               | 實作 / 架構            |
| 結論 | 不要憑 UI 倒推資料層      | 操作要同層或更上游     |

兩者互補：#63 是 high-level 設計原則、本文是 implementation 指引。

---

## 設計取捨：操作合成的位置

四種、跟 #59 [策略五選一](../filter-source-composition-strategies/) 對應但更抽象。

### A：合成在 source

最近 stream、無 silent 缺口。對應 #61 推進 query。

### B：合成在 materialization 過程中

Stream 處理時就做、不累積到 subset 後。對應 #60 自動續抓 + 在 loop 內 filter。

### C：合成在 subset、但顯式

明示語意縮小、用誠實 UX 告訴呼叫者範圍。對應 #62。

### D：合成在 subset、隱式

silent 失敗、跟意圖有縫。實務上幾乎不存在合理情境。

選擇順序：**A → B → C → D**。

---

## 判讀徵兆

| 訊號                                                                  | 該做的事                                        |
| --------------------------------------------------------------------- | ----------------------------------------------- |
| 寫 `.filter()` / `.sort()` / `.count()` 在已 materialize 的 subset 上 | 確認 source 是不是 stream / 分批；是 → 推到上游 |
| 跨多層的系統、操作出現在最下游                                        | 評估能不能上推                                  |
| 「能用、但沒覆蓋邊界 case」的功能                                     | 多半是合成位置錯了                              |
| Map-reduce / pipeline / middleware 鏈路裡、filter 在最後一層          | 推進到 stage 內                                 |
| 內心 OS：「在最後 filter 比較容易寫」                                 | 是訊號 — 容易寫的位置通常是錯位的位置           |

**核心原則**：Stream 操作的合成位置決定它的語意。同層或更上游 = 操作 stream、跟意圖對齊。下游 = 操作 subset、跟意圖有縫。這個原則跨前端 / 後端 / 演算法 / 資料庫 / 分散式系統通用 — 不是「前端 vs 後端」的問題、是「合成位置 vs materialization 位置」的問題。
