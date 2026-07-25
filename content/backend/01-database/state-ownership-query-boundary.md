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

## CQRS 在資料庫情境的應用

[CQRS](/backend/knowledge-cards/cqrs/) 的概念定義、設計判準與代價見知識卡。本段聚焦在資料庫層面：state ownership 的決策如何影響你要不要分離讀寫模型。

State ownership 跟 CQRS 的交叉點是：當 canonical state 的 schema 為寫入正確性最佳化（normalize、強一致、transaction boundary 清楚），但讀取面的多種消費者各自需要不同的反正規化形狀（列表頁要扁平 summary、報表要聚合、搜尋要全文索引），canonical schema 無法同時服務這些讀取需求。這時候分離 write model 跟 [read model](/backend/knowledge-cards/read-model/) 是解決形狀不對稱的方式。

資料庫情境的 CQRS 有不同的實作強度：

**最輕量 — 同 DB 不同 query path**：寫入走 canonical table，讀取走 [materialized view](/backend/knowledge-cards/materialized-view/) 或反正規化 view。同一個 PostgreSQL 裡用 materialized view 就能實現最基本的讀寫分離，不需要兩個 DB、不需要事件同步。適合讀寫形狀不同但流量規模還不需要獨立擴展的階段。

**中度 — 同 DB 加 read replica**：寫入走 primary，列表跟報表走 read replica。Replica lag 決定哪些 query 能走 replica（見下方 Replica Lag 段）。適合讀取流量開始壓迫寫入的階段。

**完整 — 獨立 read store**：寫入走 OLTP DB，讀取走獨立的 analytics store（BigQuery、Athena）或搜尋引擎（Elasticsearch）。透過 CDC 或事件同步維護 read store。適合讀取形狀、流量、SLA 都跟寫入完全不同的階段。

對應案例：[9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) — 交易層（OLTP）跟資料層（BigQuery / Athena）分開。[9.C22 Wayfair](/backend/09-performance-capacity/cases/wayfair-gcp-burst-capacity/) — on-prem OLTP + GCP BigQuery analytics。

## Event Sourcing 與 State Ownership

[Event sourcing](/backend/knowledge-cards/event-sourcing/) 的概念定義、設計判準與代價見知識卡。本段聚焦在資料庫層面：event sourcing 怎麼改變 state ownership 跟 query boundary。

Event sourcing 把 state ownership 的正式紀錄從 mutable row 改成 append-only [event log](/backend/knowledge-cards/event-log/)。這個改變影響本章的每一個面向：

**對 canonical / derived 分類的影響**：採用 event sourcing 後，event log 是 canonical state，current state 變成 derived state。這跟傳統 CRUD 架構相反 — 傳統架構中 current state（mutable row）是 canonical，歷史紀錄（audit log）是 derived。

**對 query boundary 的影響**：event log 不適合直接服務交易查詢跟列表查詢（每次 replay 整條事件流太慢）。Event sourcing 幾乎必然搭配 [projection](/backend/knowledge-cards/projection/) 維護 read model — projection 持續消費事件流、更新反正規化的查詢 view。交易查詢讀 projection 的輸出而非直接讀 event log。

**對修復流程的影響**：傳統架構的[資料修復](/backend/knowledge-cards/data-repair/)是「直接改 row」；event sourcing 的修復是「發一筆補償事件（compensating event）」。修復本身也是事件、會被記錄在 event log 裡、提供完整的修復 audit trail。

Event sourcing 的設計門檻在於 projection 的維護跟 event schema evolution。Projection 數量增長後，每次 event schema 改版都需要同步更新所有 projection；projection 的 replay 跟 [reconciliation](/backend/knowledge-cards/data-reconciliation/) 是長期運維的主要成本。這些代價決定了 event sourcing 適合「需要完整變更歷史」的業務場景（金融帳務、訂單流程、法規合規），而非所有資料存取場景。

## Materialized View 在資料庫的應用

[Materialized view](/backend/knowledge-cards/materialized-view/) 的概念定義見知識卡。本段聚焦在 OLTP 資料庫裡 materialized view 作為最輕量 read model 的具體實作。

Materialized view 是「同 DB 內最簡單的讀寫分離」。不需要事件同步、不需要獨立 read store、不需要 projection consumer — 資料庫自己定期執行查詢、存放結果。

**跟 regular view 的差別**：regular view 是 SQL 別名，每次 query 重跑底層查詢；materialized view 有實體儲存，query 時直接讀預計算結果。差別在 query-time cost — 複雜 JOIN / aggregation 重複跑時，materialized view 把計算推到 refresh 時、query 時接近零成本。

**Refresh 策略**：

- **全量 refresh**：PostgreSQL 的 `REFRESH MATERIALIZED VIEW`，refresh 期間 view 預設 unavailable。
- **Concurrent refresh**：PostgreSQL 的 `CONCURRENTLY` 模式，refresh 期間 view 仍可讀但資料可能 stale。
- **增量 refresh**：PostgreSQL 的 `pg_ivm`、Oracle 的 fast refresh — 只更新變更的部分，成本低但配置複雜。
- **Trigger-based**：特定 event 觸發 refresh，適合低頻變更的資料。

**在 state ownership 的定位**：materialized view 是 derived state，修復方式是 refresh（重建）而非直接修改。大量 materialized view 會拖累寫入吞吐 — 每次 base table 變更都可能觸發 refresh 計算。設計時要平衡 refresh 頻率跟 query freshness 需求。

**跟觀測領域的對照**：觀測領域的 [recording rule](/backend/knowledge-cards/recording-rule/) 在概念上等同於 TSDB 層的 materialized view — 定期執行 query expression、把結果寫成新 series。兩者面對同樣的設計問題：refresh 頻率、freshness lag、維護成本與儲存增長。觀測領域的 CQRS 特化應用見 [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)。

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
