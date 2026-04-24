---
title: "模組一：資料庫與持久化"
date: 2026-04-22
description: "整理 SQL、transaction、migration 與 repository adapter 的後端實務"
weight: 1
---

資料庫模組的核心目標是說明 application 狀態進入持久化層後，如何維持一致性、可演進性與可測性。語言教材會先定義 repository port、[protocol](../knowledge-cards/protocol/) 或 interface；本模組負責說明具體資料庫 [Repository Adapter](../knowledge-cards/repository-adapter/) 如何實作這些邊界。閱讀本模組前，可先建立 [source of truth](../knowledge-cards/source-of-truth/)、[transaction boundary](../knowledge-cards/transaction-boundary/)、[schema migration](../knowledge-cards/schema-migration/)、[isolation level](../knowledge-cards/isolation-level/) 與 [connection pool](../knowledge-cards/connection-pool/) 的共同語意。

## 暫定分類

| 分類                                                         | 內容方向                                                                                                                                                                          |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SQLite                                                       | embedded [database](../knowledge-cards/database)、單機服務、[migration](../knowledge-cards/migration)、測試資料庫                                                                 |
| PostgreSQL                                                   | schema design、index、[transaction](../knowledge-cards/transaction)、[isolation level](../knowledge-cards/isolation-level)、[connection pool](../knowledge-cards/connection-pool) |
| Migration                                                    | versioned schema、rollback、[Expand / Contract](../knowledge-cards/expand-contract/) migration                                                                                    |
| Transaction                                                  | unit of work、[transaction boundary](../knowledge-cards/transaction-boundary)、deadlock、retry                                                                                    |
| Repository [adapter](../knowledge-cards/repository-adapter/) | SQL row mapping、[contract](../knowledge-cards/contract/) test、錯誤轉換                                                                                                          |

## 選型入口

資料庫選型的核心判斷是資料是否承擔正式狀態與一致性。當資料需要長期保存、支援查詢、被多個流程共同讀寫，並且需要交易保護時，應先評估 relational database 或 document database。

SQLite 適合單機服務、embedded app、測試資料庫與低操作成本場景；PostgreSQL 適合多使用者後端、複雜查詢、transaction、index 與長期 schema evolution。Migration 工具解決 schema 隨版本演進的問題；transaction boundary 解決多筆資料一起成功或失敗的問題；repository adapter 解決 application port 到具體 SQL 實作的轉換。

接近真實網路服務的例子包括訂單系統、會員系統、訂閱方案、付款紀錄與權限資料。這些資料都需要明確 [source of truth](../knowledge-cards/source-of-truth/)，因此本模組會從資料模型、一致性、migration 與 repository adapter 邊界開始說明。

## 與語言教材的分工

語言教材處理 repository interface / [protocol](../knowledge-cards/protocol/)、取消與逾時、error wrapping、memory fake 與 [contract](../knowledge-cards/contract/) test。Backend database 模組處理 SQL schema、migration tool、transaction isolation、connection pool 與資料庫錯誤語意。

## 章節列表

| 章節                            | 主題                               | 關鍵收穫                                         |
| ------------------------------- | ---------------------------------- | ------------------------------------------------ |
| [1.1](high-concurrency-access/) | 高併發下的 SQL 讀寫邊界            | 共用 `sql.DB`、控制連線池、縮小 transaction 範圍 |
| [1.2](schema-design/)           | schema design 與資料建模           | 規劃 table、index、key 與命名規則                |
| [1.3](transaction-boundary/)    | transaction 與一致性邊界           | 判斷何時使用 transaction、retry 與 isolation     |
| [1.4](repository-adapter/)      | repository adapter 實作            | 把 SQL row mapping 與錯誤轉換封裝成 adapter      |
| [1.5](red-team-data-layer/)     | 攻擊者視角（紅隊）：資料層弱點判讀 | 用越權查詢、資料外洩路徑與恢復成本檢查資料層設計 |

## 跨語言適配評估

資料庫使用方式會受語言的 connection pool、transaction scope、ORM 行為、錯誤處理與 migration 生態影響。同步 thread-based runtime 要控制 blocking query 與 pool 大小；async runtime 要確認 database client 是否真正非阻塞；輕量並發 runtime 要限制同時查詢數量，避免把大量 task 轉成資料庫連線壓力。強型別語言適合把 row mapping、schema 與錯誤分類型別化；動態語言則需要靠 migration、runtime validation、fixture 與 [contract](../knowledge-cards/contract/) test 保護資料邊界。
