---
title: "模組四：Collector 設計"
date: 2026-06-19
description: "收 → 驗 → 存 → 查 → 觸發的完整鏈路 — Go 單一 binary、可插拔 Storage Backend、rule engine"
weight: 4
tags: ["monitoring", "collector", "go", "storage", "rule-engine"]
---

回答「收到的事件怎麼處理」。挑戰在 collector 端，不在 SDK 端。

## 章節

- [Collector 架構](/monitoring/04-collector/architecture/) — HTTP endpoint → JSON Schema 驗證 → 儲存 → 查詢 → rule engine 的完整鏈路
- [JSONL 匯出與備份格式](/monitoring/04-collector/jsonl-storage/) — 匯出格式、gzip 壓縮、備份保留策略
- [查詢 API 設計](/monitoring/04-collector/query-api/) — CLI grep 友好 vs HTTP 查詢 endpoint 的設計
- [Rule engine 設計](/monitoring/04-collector/rule-engine/) — 條件 → 動作 → 模板的規則引擎設計
- [規模演進](/monitoring/04-collector/scaling-evolution/) — 可插拔 Storage Backend、SQLite 預設與 PostgreSQL 觸發時機
- [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/) — SQLite 層 vs PostgreSQL 層的功能邊界
- [查詢消費模式](/monitoring/04-collector/query-consumption-patterns/) — Debug / Alerting / 產品決策 / 安全審計 / 效能監控五類消費模式
- [DevOps Dashboard 設計](/monitoring/04-collector/dashboard-devops/) — 系統健康指標的 dashboard 設計
- [Developer Dashboard 設計](/monitoring/04-collector/dashboard-developer/) — error 搜尋與 debug 體驗的 dashboard 設計
- [中台 Dashboard 設計](/monitoring/04-collector/dashboard-business/) — 營運與產品決策的 dashboard 設計
- [Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/) — SDK 取樣 → Collector 背壓 → 水平擴展 → Queue 解耦四層防線
- [SQLite Backend 效能基準](/monitoring/04-collector/sqlite-performance-baseline/) — 寫入吞吐、查詢延遲、資源消耗的量化預期
- [Container 部署設計](/monitoring/04-collector/container-deployment/) — SQLite 在 container 中的 I/O 考量、volume mount、graceful shutdown
- [讀寫分離與查詢擴展](/monitoring/04-collector/read-write-separation/) — 讀寫競爭辨識、Read Replica、預聚合、CQRS 判讀訊號
- [端到端資料完整性](/monitoring/04-collector/data-integrity/) — 資料損失地圖、完整性指標、被自己 SDK DDoS 的防護
- [Error Fingerprint 與去重分群](/monitoring/04-collector/error-fingerprint/) — fingerprint 演算法、message normalization、error_groups 表

## 跨分類引用

- → [backend 01 資料庫](/backend/01-database/)：PostgreSQL backend 的資料庫設計、[State Ownership 與 Query Boundary](/backend/01-database/state-ownership-query-boundary/)
- → [backend 04 觀測查詢設計](/backend/04-observability/observability-query-design/)：觀測領域的讀取路徑設計、CQRS 特化應用
- → [backend 09 效能容量](/backend/09-performance-capacity/)：高併發寫入 / 大資料查詢的效能挑戰
- → [運行期維運 流量管控](/operations/03-traffic-management/)：背壓、rate limit、熔斷的基礎概念
- → [運行期維運 突發流量](/operations/07-burst-traffic/)：突發流量分類、降級策略、queue 緩衝
- → [斷網環境的監控](/infra/air-gapped/air-gapped-monitoring/)：Collector 在斷網環境的部署方式——endpoint 改指 self-hosted backend、SDK 的 offline buffer 更重要
- 實作 repo：tarrragon/monitor 的 collector/ + docs/challenges/（撞牆記錄）
