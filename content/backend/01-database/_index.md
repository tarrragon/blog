---
title: "模組一：資料庫與持久化"
date: 2026-04-22
description: "整理 SQL、transaction、migration 與 repository adapter 的後端實務"
weight: 1
tags: ["backend", "database", "storage"]
---

資料庫模組的核心目標是說明 application 狀態進入持久化層後，如何維持一致性、可演進性與可測性。語言教材會先定義 repository port、[protocol](/backend/knowledge-cards/protocol/) 或 interface；本模組負責說明具體資料庫 [Repository Adapter](/backend/knowledge-cards/repository-adapter/) 如何實作這些邊界。閱讀本模組前，可先建立 [source of truth](/backend/knowledge-cards/source-of-truth/)、[transaction boundary](/backend/knowledge-cards/transaction-boundary/)、[schema migration](/backend/knowledge-cards/schema-migration/)、[isolation level](/backend/knowledge-cards/isolation-level/) 與 [connection pool](/backend/knowledge-cards/connection-pool/) 的共同語意。

## Vendor / Platform 清單

實作時的常用選擇見 [vendors](/backend/01-database/vendors/) — T1 收錄 PostgreSQL / MySQL / SQLite / MongoDB / DynamoDB / CockroachDB / Aurora，每個 vendor 有定位、適用場景、取捨與預計實作話題的骨架。

## 暫定分類

| 分類                                                               | 內容方向                                                                                                                                                                                            |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SQLite                                                             | embedded [database](/backend/knowledge-cards/database)、單機服務、[migration](/backend/knowledge-cards/migration)、測試資料庫                                                                       |
| PostgreSQL                                                         | schema design、index、[transaction](/backend/knowledge-cards/transaction)、[isolation level](/backend/knowledge-cards/isolation-level)、[connection pool](/backend/knowledge-cards/connection-pool) |
| Migration                                                          | versioned schema、rollback、[Expand / Contract](/backend/knowledge-cards/expand-contract/) migration                                                                                                |
| Transaction                                                        | unit of work、[transaction boundary](/backend/knowledge-cards/transaction-boundary)、deadlock、retry                                                                                                |
| Repository [adapter](/backend/knowledge-cards/repository-adapter/) | SQL row mapping、[contract](/backend/knowledge-cards/contract/) test、錯誤轉換                                                                                                                      |

## 選型入口

資料庫選型的核心判斷是資料是否承擔正式狀態與一致性。當資料需要長期保存、支援查詢、被多個流程共同讀寫，並且需要交易保護時，應先評估 relational database 或 document database。

SQLite 適合單機服務、embedded app、測試資料庫與低操作成本場景；PostgreSQL 適合多使用者後端、複雜查詢、transaction、index 與長期 schema evolution。Migration 工具解決 schema 隨版本演進的問題；transaction boundary 解決多筆資料一起成功或失敗的問題；repository adapter 解決 application port 到具體 SQL 實作的轉換。

接近真實網路服務的例子包括訂單系統、會員系統、訂閱方案、付款紀錄與權限資料。這些資料都需要明確 [source of truth](/backend/knowledge-cards/source-of-truth/)，因此本模組會從資料模型、一致性、migration 與 repository adapter 邊界開始說明。

## 與語言教材的分工

語言教材處理 repository interface / [protocol](/backend/knowledge-cards/protocol/)、取消與逾時、error wrapping、memory fake 與 [contract](/backend/knowledge-cards/contract/) test。Backend database 模組處理 SQL schema、migration tool、transaction isolation、connection pool 與資料庫錯誤語意。

## 章節列表

| 章節                                                           | 主題                                  | 關鍵收穫                                                   |
| -------------------------------------------------------------- | ------------------------------------- | ---------------------------------------------------------- |
| [1.1](/backend/01-database/high-concurrency-access/)           | 高併發下的 SQL 讀寫邊界               | 共用 `sql.DB`、控制連線池、縮小 transaction 範圍           |
| [1.2](/backend/01-database/schema-design/)                     | schema design 與資料建模              | 規劃 table、index、key 與命名規則                          |
| [1.3](/backend/01-database/transaction-boundary/)              | transaction 與一致性邊界              | 判斷何時使用 transaction、retry 與 isolation               |
| [1.4](/backend/01-database/repository-adapter/)                | repository adapter 實作               | 把 SQL row mapping 與錯誤轉換封裝成 adapter                |
| [1.5](/backend/01-database/red-team-data-layer/)               | 攻擊者視角（紅隊）：資料層弱點判讀    | 用越權查詢、資料外洩路徑與恢復成本檢查資料層設計           |
| [1.6](/backend/01-database/database-migration-playbook/)       | 資料庫轉換實作                        | 把雙寫、回填、切流與回滾做成可分段驗證流程                 |
| [1.7](/backend/01-database/schema-migration-rollout-evidence/) | Schema Migration Rollout 證據實作示範 | 以訂單付款狀態欄位演進示範 evidence、gate 與 decision log  |
| [1.8](/backend/01-database/state-ownership-query-boundary/)    | State Ownership 與 Query Boundary     | 分辨正式狀態、派生狀態與不同查詢責任                       |
| [1.9](/backend/01-database/reconciliation-data-repair/)        | Reconciliation 與 Data Repair         | 把資料錯誤轉成可驗證、可修復、可稽核流程                   |
| [1.10](/backend/01-database/kv-document-capacity-planning/)    | KV / Document DB 容量規劃             | partition key 設計、capacity mode、multi-model 取捨        |
| [1.11](/backend/01-database/global-distributed-oltp/)          | 全球分散式 OLTP                       | Spanner / Aurora DSQL / Cosmos DB multi-region 跟 CAP 取捨 |
| [1.12](/backend/01-database/large-scale-db-migration/)         | 大規模 DB 遷移實戰                    | dual-write / shadow read / cutover / rollback window       |

## 觀念網路補完方向

資料庫章節下一輪的核心責任是把正式狀態的演進路徑講完整。現有章節已經涵蓋 schema、transaction、repository adapter 與 migration playbook，但還需要補上 state ownership、query boundary、migration safety 與 reconciliation 之間的引用關係，讓讀者知道資料庫變更如何從設計、發布、觀測一路接到事故決策。

| 補完方向         | 需要回答的問題                                       | 主要路由                                                                                                                                                                  |
| ---------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| State ownership  | 哪些資料是正式狀態，哪些只是 cache、index 或事件副本 | [source of truth](/backend/knowledge-cards/source-of-truth/)、[0.2](/backend/00-service-selection/state-storage-selection/)                                               |
| Query boundary   | 交易查詢、列表查詢、報表查詢與對帳查詢是否混在一起   | [4.20](/backend/04-observability/observability-evidence-package/)、[4.17](/backend/04-observability/telemetry-data-quality/)                                              |
| Migration safety | schema 變更是否能分批、驗證、暫停與回退              | [6.11](/backend/06-reliability/migration-safety/)、[6.8](/backend/06-reliability/release-gate/)                                                                           |
| Reconciliation   | 資料錯誤發生後如何驗證、修復、對帳與留下證據         | [8.19](/backend/08-incident-response/incident-decision-log/)、[8.22](/backend/08-incident-response/incident-evidence-write-back/)                                         |
| Data protection  | 正式資料在查詢、匯出、修復與刪除時如何保留責任邊界   | [7.4](/backend/07-security-data-protection/data-protection-and-masking-governance/)、[7.7](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/) |

這些方向要寫成資料庫自己的敘事，避免把 04/06/08 的欄位直接搬進來。資料庫關心的是狀態能否正確演進；觀測、驗證與事故流程接收這個演進結果作為下游證據。

## 知識卡補強方向

資料庫模組的 knowledge card 缺口集中在「變更如何被驗證」與「資料如何被修復」。已有 [schema migration](/backend/knowledge-cards/schema-migration/)、[Expand / Contract](/backend/knowledge-cards/expand-contract/)、[backfill](/backend/knowledge-cards/backfill/) 與 [dual write](/backend/knowledge-cards/dual-write/) 可作為第一批錨點。

下一批候選卡片包括 migration validation、read compatibility、cutover window、reconciliation、data repair runbook 與 fail-forward migration。這些卡片要先定義服務責任與使用時機，再讓 1.6 migration playbook 與後續實作文章引用。

## 實作探討入口

資料庫的第一條實作路徑已完成： [1.7 Schema Migration Rollout 證據實作示範](/backend/01-database/schema-migration-rollout-evidence/)。這篇以訂單資料表付款狀態欄位演進為例，說明 migration plan、validation query、rollback condition 與 incident decision route 如何一起成立。

這條路徑的前置引用是 1.2 schema design、1.3 transaction boundary、1.6 migration playbook、[6.11 Migration Safety](/backend/06-reliability/migration-safety/) 與 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。完成後的下一個分類服務路徑，依 [0.15 後端實作教學大綱](/backend/00-service-selection/implementation-teaching-outline/) 進入 02 cache migration。

資料庫路徑的 artifact 對齊重點是「先證明資料演進正確，再討論是否放行」。對 [4.20](/backend/04-observability/observability-evidence-package/) 要交 `Source/Time range/Query link/Owner/Data quality`，並在 query 內容覆蓋 validation query、row count 差異與 replication lag；對 [6.11](/backend/06-reliability/migration-safety/) / [6.8](/backend/06-reliability/release-gate/) 要交 `Gate decision/Checks/Stop condition/Rollback window/Owner`，呈現 expand/contract 分段結果；對 [8.19](/backend/08-incident-response/incident-decision-log/) 要交 `Timestamp/Decision/Context/Evidence/Owner/Expected effect/Rollback condition`，記錄 pause / rollback / fail-forward 的判斷與依據。

## 跨語言適配評估

資料庫使用方式會受語言的 connection pool、transaction scope、ORM 行為、錯誤處理與 migration 生態影響。同步 thread-based runtime 要控制 blocking query 與 pool 大小；async runtime 要確認 database client 是否真正非阻塞；輕量並發 runtime 要限制同時查詢數量，避免把大量 task 轉成資料庫連線壓力。強型別語言適合把 row mapping、schema 與錯誤分類型別化；動態語言則需要靠 migration、runtime validation、fixture 與 [contract](/backend/knowledge-cards/contract/) test 保護資料邊界。
