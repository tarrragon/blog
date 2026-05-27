---
title: "Query Cardinality Explosion"
date: 2026-05-27
description: "Query 結果行數因 join / cross product / 條件缺失爆炸性放大的反模式"
weight: 356
---

Query cardinality explosion 的核心責任是命名「query 結果行數遠超業務直覺」這類反模式 — 通常源於多對多 join 沒加 filter、或誤用 cross join。一個應該回 100 行的 query 變成回 10000 行（10000 × M）、應用層拉回 deserialize 後記憶體爆掉、DB 也付出不必要的 scan + serialization 成本。跟 [keyset pagination](/backend/knowledge-cards/keyset-pagination/) 是 query 結果集大小判讀的雙刃 — cardinality 是「沒控制 join 行數爆掉」、keyset 是「沒控制 offset 跳行爆掉」、修法方向不同但都屬 result-set sizing 維度。

## 概念位置

Cardinality explosion 處於 SQL query 設計的「結果集大小判讀」維度、跟 [keyset pagination](/backend/knowledge-cards/keyset-pagination/) 都是大表查詢反模式修法。常見成因：多對多 join 缺 filter（100 訂單 × 10 item × 5 tag × 5 評論 = 25000 行）、誤用 CROSS JOIN（忘了 JOIN 條件、結果是 N × M 笛卡兒積）、遞迴 CTE 沒終止條件（可能跑出百萬行）。

跟 metric cardinality（time-series 維度爆）不同情境、本卡專指 query result-set 行數爆 — 是兩個獨立議題、不混寫。

## 可觀察訊號與例子

業務上預期回 100 行、實際拿到 10000+ 行；`EXPLAIN` 估計 rows 異常大（與表的實際大小數量級不符）；應用層記憶體用量隨流量線性升高、但 QPS 沒成比例升；同樣的 query 在小資料量正常、大資料量 query 變慢且記憶體爆。電商訂單列表頁、報表查詢、後台搜尋是高發場景。

## 設計責任

修法方向：拆 query（先拿主資源、再用 IN 條件批次取相關資源、從 join 改成 N+1 但 N 可控）；用 EXISTS / 半連接取代 JOIN（只要知道「有沒有」而非「全列出」時、`WHERE EXISTS (...)` 比 join 便宜）；明確 LIMIT（大資料量 query 強制加 limit）；重新評估資料模型（頻繁出現代表表關係設計可能過度正規化）。CI 加 query result size middleware、超過閾值觸發 review 比事後從 slow log 找問題早。
