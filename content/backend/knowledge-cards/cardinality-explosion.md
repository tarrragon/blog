---
title: "Cardinality Explosion"
date: 2026-05-27
description: "Query 結果行數因 join / cross product / 條件缺失爆炸性放大的反模式"
weight: 356
---

Cardinality explosion 是 query 結果行數遠超業務直覺的情況、通常源於多對多 join 沒加 filter、或誤用 cross join。一個應該回 100 行的 query 變成回 10000 行（10000 × M）、應用層拉回 deserialize 後記憶體爆掉、DB 也付出不必要的 scan + serialization 成本。跟 [keyset pagination](/backend/knowledge-cards/keyset-pagination/) 是 query 結果集大小判讀的雙刃：cardinality explosion 是「沒控制 join 行數爆掉」、keyset 是「沒控制 offset 跳行爆掉」、修法方向不同但都屬「pagination / result-set sizing」維度。

## 概念位置

Cardinality explosion 處於 SQL query 設計的「結果集大小判讀」維度、跟 [keyset pagination](/backend/knowledge-cards/keyset-pagination/) 都是大結果集 query 的反模式。常見成因：

- **多對多 join 缺 filter**：`SELECT * FROM orders o JOIN order_items i ON o.id = i.order_id`、若有 100 訂單 × 平均 10 item = 1000 行、看起來正常；但若加另一個 JOIN tag、每 item 平均 5 tag、變 5000 行；再 join 評論變 25000 行
- **誤用 CROSS JOIN**：忘了 JOIN 條件、結果是 N × M 笛卡兒積
- **遞迴 CTE 沒終止條件**：無限遞迴可能跑出百萬行

## 判讀訊號

- 業務上預期回 100 行、實際拿到 10000+ 行
- `EXPLAIN` 估計 rows 異常大（與表的實際大小數量級不符）
- 應用層記憶體用量隨流量線性升高、但 QPS 沒成比例升
- 同樣的 query 在小資料量正常、大資料量 query 變慢且記憶體爆

## 修法

- **拆 query**：先拿主資源、再用 IN 條件批次取相關資源（從 join 改成 N+1 但 N 可控）
- **EXISTS / 半連接取代 JOIN**：只要知道「有沒有」而非「全列出」時、`WHERE EXISTS (...)` 比 join 便宜
- **明確 LIMIT**：大資料量 query 強制加 limit、避免不小心拉全表
- **重新評估資料模型**：頻繁出現 cardinality explosion 代表表關係設計可能有過度正規化的 join

## 對照

跟其他反模式對比：

- 跟 N+1：N+1 是發太多次 query、cardinality explosion 是單次 query 拉太多行
- 跟 missing index：missing index 是 query plan 退化、cardinality explosion 是結果集本身過大
- 跟 `SELECT *`：兩者都跟「拉過多資料」相關、但 `SELECT *` 是欄位多、cardinality 是行數多
