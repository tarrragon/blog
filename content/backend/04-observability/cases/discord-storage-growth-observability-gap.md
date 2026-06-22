---
title: "4.C13 Discord：從儲存問題回推觀測缺口"
date: 2026-06-22
description: "每次儲存遷移都暴露觀測盲區，把儲存成長問題重新框架為訊號設計問題。"
weight: 13
tags: ["backend", "observability", "case-study", "debuggability", "data-quality"]
---

Discord 的儲存演進案例從觀測角度回推一個教訓：儲存成長問題通常先表現為觀測缺口。不是資料庫變慢了才去看 metric，是該有的 metric 從一開始就沒設計。每一次儲存遷移（MongoDB → Cassandra → ScyllaDB）都揭露了上一階段缺少的訊號。

## 業務背景

Discord 處理 trillions of messages。訊息是核心 user journey — 文字、圖片、附件、thread、搜尋全部依賴訊息儲存層。從 2015 年到 2023 年，Discord 的訊息儲存經歷三代架構。

每一代遷移都由 production 問題觸發 — 追查後發現儲存層已經撐不住，才啟動下一代架構。追查過程中反覆出現的盲區是：觀測訊號不夠早、不夠細或不夠可信。

## 技術挑戰

### MongoDB 階段：latency tail 不可見

早期用 MongoDB 儲存訊息。隨著使用者成長，部分大型 server（Discord 的群組概念）的訊息量遠超平均值。這些 server 的查詢 latency 偶爾飆升到秒級，但 aggregated latency metric（p50、p95）看起來正常 — 因為大型 server 的 request 數量在整體中佔比極低。

缺少的訊號：per-server latency breakdown。aggregated metric 遮蔽了局部惡化。

### Cassandra 階段：hot partition 沒有早期訊號

遷移到 Cassandra 後，partition key 設計（channel ID）讓某些高流量 channel 成為 hot partition。Cassandra 的 compaction 在 hot partition 上延遲，讀取 latency 上升。

問題由使用者回報「訊息載入很慢」才被發現，alert 沒有提前攔截。事後回看，Cassandra 的 read latency per partition 跟 compaction pending bytes per table 這兩個 metric 都有異常，但沒有人在 dashboard 上設 alert — 因為這兩個 metric 在 Cassandra 的預設 monitoring 裡不是 first-class 告警對象。

缺少的訊號：hot partition 識別跟 compaction health 的主動告警。

### ScyllaDB 遷移階段：dual-read 沒有比對 metric

從 Cassandra 遷移到 ScyllaDB 的過程中，Discord 做了 dual-read（同時讀舊資料庫跟新資料庫、比對結果）。dual-read 的正確性比對有做，但 latency 跟 error rate 的比對 metric 設計不完整 — 知道結果一致，但不知道 ScyllaDB 在特定 query pattern 下是否比 Cassandra 慢。

遷移後才發現某些 query pattern 在 ScyllaDB 上的 tail latency 比 Cassandra 高，需要額外的 schema 調整。如果 dual-read 階段就有 per-query-pattern latency comparison metric，這個問題可以在 cutover 前發現。

缺少的訊號：migration 期間的 per-pattern latency comparison。

## 教訓

三次遷移暴露的觀測缺口有共同結構：

| 缺口類型     | MongoDB 階段                    | Cassandra 階段                               | ScyllaDB 遷移                                   |
| ------------ | ------------------------------- | -------------------------------------------- | ----------------------------------------------- |
| 維度不夠細   | aggregated latency 遮蔽局部惡化 | table-level metric 遮蔽 partition-level 問題 | 整體 dual-read match rate 遮蔽 per-pattern 差異 |
| 告警設計缺失 | 沒有 per-entity latency alert   | 沒有 hot partition alert                     | 沒有 latency comparison alert                   |
| 發現方式     | 使用者回報                      | 使用者回報                                   | 遷移後才發現                                    |

共同模式：觀測訊號的粒度不夠、或告警只設在 aggregated 層 — 局部惡化被平均值淹沒，直到使用者感受到影響才被發現。

三個缺口的修正方向也一致：

1. 把 entity-level metric（per-server、per-partition、per-query-pattern）從 debug-only 提升為 first-class 觀測訊號
2. 在 aggregated alert 之外加 percentile 跟 tail latency alert（p99.9 而非只看 p95）
3. Migration 期間把 latency comparison 做成 per-pattern 的 real-time dashboard，不只看 overall match rate

## 回寫教材的連結

- [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)：aggregated metric 遮蔽局部惡化是 data quality 問題 — 訊號存在但粒度不足以判讀。
- [4.18 Observability Operating Model](/backend/04-observability/observability-operating-model/)：觀測缺口反覆出現代表 operating model 缺少「新服務上線 / 遷移時強制檢查觀測覆蓋」的 gate。
- [4.19 Debuggability by Design](/backend/04-observability/debuggability-by-design/)：per-entity latency breakdown 跟 migration comparison metric 應該在系統設計時就規劃，不是事故後補。

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- 使用者回報問題但 dashboard 看起來正常 — aggregated metric 可能遮蔽局部惡化
- 資料庫或儲存層偶爾變慢但找不到原因 — 可能缺少 per-entity 或 per-partition metric
- Migration 做了 dual-read 但只比對正確性、沒比對 latency — 遷移後才發現效能回歸
- 告警設計只有 error rate 跟 aggregated latency — 缺少 tail latency 跟 entity-level alert

## 引用源

- [How Discord Stores Billions of Messages](https://discord.com/blog/how-discord-stores-billions-of-messages)（MongoDB → Cassandra 階段）
- [How Discord Stores Trillions of Messages](https://discord.com/blog/how-discord-stores-trillions-of-messages)（Cassandra → ScyllaDB 階段）
