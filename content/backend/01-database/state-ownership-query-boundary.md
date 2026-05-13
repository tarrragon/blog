---
title: "1.8 State Ownership 與 Query Boundary"
date: 2026-05-13
description: "正式狀態 vs 派生狀態的責任分層、CQRS / event sourcing / materialized view、四種 query 邊界"
weight: 8
tags: ["backend", "database", "state", "query-boundary"]
---

State ownership 與 query boundary 的核心責任是先定義資料由誰承擔正式判斷、再定義不同查詢路徑能回答什麼問題。進入 MySQL、PostgreSQL、MSSQL 或其他資料庫前、讀者需要先知道資料庫同時是儲存工具與服務狀態的責任邊界。

本章從 source of truth 的責任分層開始、引入 CQRS / event sourcing / materialized view 等模式、最後處理四種 query 邊界的設計。讀完後讀者能回答：哪些資料是正式狀態、什麼時候該分讀寫 model、materialized view 怎麼用、replica lag 怎麼影響 query。

## State Ownership

State ownership 的責任是判斷哪些資料是 [source of truth](/backend/knowledge-cards/source-of-truth/)、哪些資料屬於 cache、search index、event log 或報表副本。正式狀態會影響交易結果、權限判斷、對帳與客服修復、因此需要清楚的 owner、schema、驗證方式與變更流程。

訂單狀態、付款狀態、會員方案、權限授權與發票紀錄通常屬於正式狀態。商品搜尋索引、快取值、統計摘要與推薦結果通常是派生狀態；派生狀態可以錯過短暫更新、但正式狀態需要能被追溯、修復與稽核。

## Canonical State vs Derived State

| 維度   | Canonical state       | Derived state                             |
| ------ | --------------------- | ----------------------------------------- |
| 角色   | source of truth       | 從 canonical 計算 / 同步                  |
| 寫入   | 用戶 / 業務操作       | 從 canonical 推                           |
| 一致性 | strong / serializable | eventual 通常夠用                         |
| 修復   | 必須能精確修復        | 可以「砍掉重建」                          |
| 範例   | 訂單、付款、餘額      | 搜尋 index、recommendation、daily summary |

**Canonical state 的特徵**：

- 業務決策依據（付款、權限）
- 不能從其他地方重建（一旦丟、無法找回）
- 需要 audit log、point-in-time recovery、backup
- 通常在 OLTP DB（PostgreSQL / Aurora / Spanner）

**Derived state 的特徵**：

- 從 canonical 推算出來
- 可以「rebuild」（lazy 或 eager）
- 失效可接受（用戶可能看到舊的）
- 通常在 cache / search / analytics store
- 對應案例：[9.C6 Tinder ElastiCache](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) 配對快取、[9.C25 Tubi ML feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) feature

**設計原則**：

- 同一資料 *不能* 同時是兩個地方的 canonical → 衝突時不知道信誰
- 寫入永遠先寫 canonical、再 propagate 到 derived
- derived 出錯只能 rebuild、不能拿來「修正 canonical」

## CQRS 模式

CQRS（Command Query Responsibility Segregation）把寫入跟讀取分開、用不同 model。

**經典 CQRS**：

- Command（寫入）走 canonical schema、強一致
- Query（讀取）走 derived schema（為 query 優化）
- 兩個 model 透過 event / async sync

**為什麼用 CQRS**：

- 寫入 schema 為 *正確性* 優化（normalize、強一致）
- 讀取 schema 為 *查詢效率* 優化（denormalize、precompute）
- 兩個目標衝突時、不要硬塞同一 schema

**簡化 CQRS**：

- 不一定要兩個 DB / 兩個 model
- 同 DB 可以用 *materialized view* 實現 read model
- 應用層用 *DTO / response shape* 不同也算

**對應案例**：

- [9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) — 交易層（OLTP）跟資料層（BigQuery / Athena）分開
- [9.C22 Wayfair](/backend/09-performance-capacity/cases/wayfair-gcp-burst-capacity/) — on-prem OLTP + GCP BigQuery analytics

## Event Sourcing

event sourcing 不存 *current state*、存 *event history*、current state 從 event 推出來。

**特徵**：

- 寫入：append-only event log
- 讀取：replay event 算出 current state、或維護 read model（projection）
- 永遠可以「回到任一時刻」的 state
- 對應 [Event Log 卡片](/backend/knowledge-cards/event-log/) 跟 [Projection 卡片](/backend/knowledge-cards/projection/)

**適合場景**：

- 金融帳戶（需要 audit 任何時刻 balance）
- 訂單流程（每個 state 變化是 business event）
- 法規要求保留全變更歷史

**不適合場景**：

- 簡單 CRUD（complexity overhead）
- 需要直接 query current state（每次 replay 慢）

**搭配 CQRS**：event sourcing 是典型的 *write model*、read model 用 projection 維護快查 view。

## Materialized View

materialized view 是 *預計算的 query 結果*、定期 refresh。

**vs regular view**：

- regular view：只是 SQL 別名、每次 query 重跑
- materialized view：實際 store 結果、query 時直接讀

**何時用**：

- 複雜 JOIN / aggregation 重複跑
- query 結果變化頻率 < 重跑頻率（每天 refresh、每小時 query 千次）
- 可接受 refresh window 內看舊資料

**Refresh 策略**：

- 全量 refresh（PostgreSQL `REFRESH MATERIALIZED VIEW`）
- 增量 refresh（PostgreSQL `pg_ivm`、其他 DB 有 native incremental）
- Trigger-based（特定 event 觸發 refresh）

**注意**：

- refresh 期間 view 可能 unavailable（PostgreSQL 預設）或 stale（CONCURRENTLY 模式）
- 大量 materialized view 拖累寫入吞吐

## Query Boundary 四種

Query boundary 的責任是讓不同查詢路徑承擔不同服務問題。交易查詢、列表查詢、報表查詢與對帳查詢都可能讀同一張表、但它們的正確性、延遲與資料新鮮度要求不同。

| 查詢類型 | 服務責任                                     | 典型 latency | 容忍 stale     | 風險                                  |
| -------- | -------------------------------------------- | ------------ | -------------- | ------------------------------------- |
| 交易查詢 | 支援使用者當下動作、例如付款、下單、授權     | < 100ms      | 不容忍         | 延遲或錯誤會直接影響交易結果          |
| 列表查詢 | 支援使用者瀏覽與管理、例如訂單列表、會員清單 | < 500ms      | 可容忍秒級     | 可能放大 index、pagination 與排序成本 |
| 報表查詢 | 支援營運分析、財務統計與趨勢判讀             | 秒到分鐘級   | 可容忍 hour 級 | 容易壓迫線上資料庫與混淆資料時效      |
| 對帳查詢 | 驗證正式狀態與外部事實是否一致               | 分鐘到小時級 | 視業務         | 查詢定義錯誤會造成錯修或漏修          |

這四種查詢混在一起時、資料庫會同時承擔低延遲交易與高成本分析、最後讓任何一種資料庫選型都變得模糊。

### 交易路徑的邊界

交易路徑的責任是維持使用者動作的即時正確性。它需要短查詢、明確 index、可控 [transaction boundary](/backend/01-database/transaction-boundary/) 與清楚 timeout。

交易路徑的設計要把報表聚合或長時間掃描移到其他查詢路徑。若下單 API 同時查歷史報表、計算大範圍統計或同步重建派生狀態、交易延遲會被非交易責任拖慢。

對應 [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — 200 個獨立 Aurora cluster 把不同業務 transaction 分開、避免互相影響。

### 列表與報表的邊界

列表查詢的責任是支援產品體驗中的瀏覽與定位。列表查詢需要穩定排序、分頁策略、篩選條件與查詢成本界線；它應建立自己的讀取模型或索引策略、避免直接借用交易查詢的資料模型造成 slow query、排序漂移與 pagination 重複。

報表查詢的責任是支援分析與決策。報表通常可以接受資料延遲、因此更適合使用 read replica、materialized view、ETL 或 analytics store。把報表直接壓在線上 primary 上、會讓交易服務承擔不必要的容量風險。

對應 [9.C22 Wayfair hybrid burst](/backend/09-performance-capacity/cases/wayfair-gcp-burst-capacity/)、[9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) — 交易層跟資料層分開部署。

### 對帳查詢的邊界

對帳查詢的責任是驗證正式狀態是否與外部事實一致。付款、發票、庫存與訂閱方案都需要對帳查詢、但對帳查詢要保留時間窗、資料來源、差異定義與人工修復入口。

對帳查詢承擔比報表更直接的修復責任。報表回答「現在看起來如何」、對帳回答「哪一筆正式狀態需要修復」。因此對帳查詢結果要能進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 與 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

詳見 [1.9 Reconciliation 與 Data Repair](/backend/01-database/reconciliation-data-repair/)。

## Replica Lag 對 Query Boundary 的影響

當應用使用 read replica 擴 read traffic 時、replica lag 會直接影響 query boundary 設計。

**典型 lag**：

- PostgreSQL streaming：< 100ms（同 AZ）
- Aurora：10-30ms（同 region）
- 跨 region replica：秒級到分鐘級

**不同 query 對 lag 的容忍**：

- 交易查詢：不可容忍 lag、必須走 primary
- read-after-write（剛寫完查自己）：必須 primary、或 session sticky
- 列表查詢：通常容忍 lag < 1 秒
- 報表查詢：lag 分鐘級可接受
- 對帳查詢：通常用 batch、lag 不關鍵

**Stale read 容忍策略**：

- 「能容忍秒級 stale」的 read → replica（用戶 profile、報表）
- 「不能 stale」的 read → primary（剛寫入後的查詢、餘額確認）
- read-after-write：用 session token 標記「剛寫過」、N 秒內讀走 primary

對應 [1.1 高併發資料存取](/backend/01-database/high-concurrency-access/) 的「Read Replica Scaling」段。

## 選型前判準

資料庫選型前要先回答四個問題：

1. 哪些資料是正式狀態、哪些是派生狀態
2. 哪些查詢屬於交易路徑、哪些可以延遲或離線化
3. 哪些查詢結果會觸發修復、退款、補償或人工決策
4. 哪些資料需要 audit、masking、retention 或刪除責任

這些問題決定後續該比較 relational database、document database、search index、analytics store 還是 cache。工具差異要放在責任邊界之後討論。

## 實體服務討論承接點

實體資料庫文章要承接本篇的 state ownership 與 query boundary。PostgreSQL、MySQL、MSSQL 或其他 relational database 的比較、應先問它們如何支援正式狀態、交易查詢、列表查詢、報表查詢與對帳查詢、再進入索引、隔離層級、replica 或工具語法。

若主問題是正式狀態與交易一致性、後續文章要優先比較 transaction、isolation、index 與 migration 能力。若主問題是報表與搜尋、後續文章要評估 read replica、materialized view、search index 或 analytics store。若主問題是對帳與修復、後續文章要比較 [validation query](/backend/knowledge-cards/validation-query/)、audit log、backup/restore 與資料修復流程。

## 案例對照

| 案例                                                                                                 | state / query 設計重點                           |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| [9.C4 DraftKings Aurora](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) | 200 個獨立 cluster 隔離 transaction scope        |
| [9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/)     | OLTP 交易層 + BigQuery / Athena 分析層           |
| [9.C22 Wayfair](/backend/09-performance-capacity/cases/wayfair-gcp-burst-capacity/)                  | on-prem OLTP + GCP BigQuery 分析、典型 CQRS 配置 |
| [9.C25 Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)              | feature store（derived state）、跟 source 分離   |
| [9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/)                | watch list（user state）跟 content metadata 分層 |

## 跨模組路由

1. 與 1.2 的交接：欄位與索引語意回到 [schema design](/backend/01-database/schema-design/)
2. 與 1.3 的交接：transaction boundary 設計影響哪些 query 走 primary、哪些可走 replica
3. 與 1.7 的交接：正式狀態變更要進入 production rollout — [Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)
4. 與 1.9 的交接：對帳查詢的下游修復 — [Reconciliation and Data Repair](/backend/01-database/reconciliation-data-repair/)
5. 與 2 的交接：cache layer 是 derived state 最常見的形式 — [02 快取模組](/backend/02-cache-redis/)
6. 與 4.20 的交接：query evidence 跟 reconciliation evidence — [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)

## 下一步路由

要進一步處理 schema 與資料模型、接著讀 [1.2 schema design 與資料建模](/backend/01-database/schema-design/)。要處理 schema 演進與正式狀態變更、接著讀 [1.6 Database Migration Playbook](/backend/01-database/database-migration-playbook/) 跟 [1.7 Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/)。要處理對帳跟資料修復、接著讀 [1.9 Reconciliation](/backend/01-database/reconciliation-data-repair/)。要設計 KV / Document 的 state ownership、接著讀 [1.10 KV / Document 容量規劃](/backend/01-database/kv-document-capacity-planning/)。
