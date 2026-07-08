---
title: "模組四：Collector 設計"
date: 2026-06-19
description: "收 → 驗 → 存 → 查 → 觸發的完整鏈路 — Go 單一 binary、可插拔 Storage Backend、rule engine"
weight: 4
tags: ["monitoring", "collector", "go", "storage", "rule-engine"]
---

回答「收到的事件怎麼處理」。挑戰在 collector 端，不在 SDK 端。

## 待寫章節

- [x] Collector 架構（HTTP endpoint → JSON Schema 驗證 → 儲存 → 查詢 → rule engine）
- [x] JSONL 匯出與備份格式（匯出格式、gzip 壓縮、備份保留）
- [x] 查詢 API 設計（CLI grep 友好 vs HTTP 查詢 endpoint）
- [x] Rule engine 設計（條件 → 動作 → 模板）
- [x] 規模演進：可插拔 Storage Backend（SQLite 預設 / PostgreSQL 觸發）
- [x] 功能分層與 Backend 選擇（SQLite 層 vs PostgreSQL 層的功能邊界）
- [x] SQLite Backend 效能基準（寫入吞吐 / 查詢延遲 / 資源消耗的量化預期）
- [x] Ingestion Scaling（四層防線 — SDK 取樣 → Collector 背壓 → 水平擴展 → Queue 解耦）
- [x] 查詢消費模式（Debug / Alerting / 產品決策 / 安全審計 / 效能監控）
- [x] DevOps Dashboard 設計
- [x] Developer Dashboard 設計
- [x] 中台 Dashboard 設計
- [x] Container 部署設計（SQLite 在 container 中的 I/O 考量、volume mount、graceful shutdown）
- [x] 讀寫分離與查詢擴展（讀寫競爭辨識、Read Replica、預聚合、CQRS 判讀訊號）
- [x] 端到端資料完整性（資料損失地圖、完整性指標、被自己 SDK DDoS 的防護）
- [x] Error Fingerprint 與去重分群（fingerprint 演算法、message normalization、error_groups 表）

## 跨分類引用

- → [backend 01 資料庫](/backend/01-database/)：PostgreSQL backend 的資料庫設計、[State Ownership 與 Query Boundary](/backend/01-database/state-ownership-query-boundary/)
- → [backend 04 觀測查詢設計](/backend/04-observability/observability-query-design/)：觀測領域的讀取路徑設計、CQRS 特化應用
- → [backend 09 效能容量](/backend/09-performance-capacity/)：高併發寫入 / 大資料查詢的效能挑戰
- → [運行期維運 流量管控](/operations/03-traffic-management/)：背壓、rate limit、熔斷的基礎概念
- → [運行期維運 突發流量](/operations/07-burst-traffic/)：突發流量分類、降級策略、queue 緩衝
- → [斷網環境的監控](/infra/air-gapped/air-gapped-monitoring/)：Collector 在斷網環境的部署方式——endpoint 改指 self-hosted backend、SDK 的 offline buffer 更重要
- 實作 repo：tarrragon/monitor 的 collector/ + docs/challenges/（撞牆記錄）
