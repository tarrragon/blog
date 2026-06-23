---
title: "Storage Tiering"
date: 2026-06-22
description: "說明按資料熱度分層儲存以平衡查詢速度、儲存成本與保留完整性的機制"
weight: 326
tags: ["backend", "observability"]
---

Storage tiering 按資料被查詢的頻率與時間壓力，把資料放在不同速度與成本的儲存層。最近的資料放在快速儲存（hot tier），較舊的資料依序移到較慢但便宜的儲存（warm tier、cold tier），最終可歸檔到 object storage 或離線備份。它跟 [rollup](/backend/knowledge-cards/rollup/) 共同構成觀測資料的生命週期管理，受 [retention](/backend/knowledge-cards/retention/) 期限驅動。

## 概念位置

Storage tiering 是觀測資料管理的基礎設施層決策，影響查詢能力、成本結構與保留政策。它跟 [rollup](/backend/knowledge-cards/rollup/) 的分工是：tiering 決定資料放在哪種儲存、rollup 決定資料以什麼精度存放。兩者共同構成觀測資料的生命週期管理。

## 設計責任

設計 tiering 時要定義每一層的查詢 SLA、儲存成本、資料轉移觸發條件與跨層查詢行為。

| 層級 | 典型儲存             | 查詢延遲   | 資料精度          |
| ---- | -------------------- | ---------- | ----------------- |
| Hot  | SSD / in-memory TSDB | 毫秒到秒   | 原始精度          |
| Warm | HDD / 分散式儲存     | 秒到十秒   | 原始或輕度 rollup |
| Cold | Object storage / S3  | 十秒到分鐘 | rollup 或歸檔     |

跨層查詢是 tiering 設計的關鍵問題。當查詢範圍橫跨 hot 跟 warm 兩層時，回應時間由最慢的那層決定。使用者在 dashboard 把時間範圍從「最近 1 小時」拉到「最近 7 天」時，查詢延遲可能從毫秒跳到秒級，體驗落差需要在 UI 或文件中說明。

## 使用情境

需要 tiering 的訊號是觀測儲存成本持續成長但大部分查詢只命中最近的資料、或保留期因為成本壓力被迫縮短導致鑑識與稽核需求無法滿足。Elasticsearch ILM、Loki 的 chunk storage 分層、Thanos / Cortex 的 object storage backend 都是常見實作。

Tiering 對查詢能力的影響見 [4.7 cardinality 治理](/backend/04-observability/cardinality-cost-governance/) 跟 [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)。
