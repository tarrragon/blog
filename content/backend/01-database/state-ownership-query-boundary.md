---
title: "1.8 State Ownership 與 Query Boundary"
date: 2026-05-11
description: "說明資料庫如何承擔正式狀態，以及交易查詢、列表查詢、報表查詢與對帳查詢如何分責任。"
weight: 8
tags: ["backend", "database", "state", "query-boundary"]
---

State ownership 與 query boundary 的核心責任是先定義資料由誰承擔正式判斷，再定義不同查詢路徑能回答什麼問題。進入 MySQL、PostgreSQL、MSSQL 或其他資料庫前，讀者需要先知道資料庫同時是儲存工具與服務狀態的責任邊界。

## State Ownership

State ownership 的責任是判斷哪些資料是 [source of truth](/backend/knowledge-cards/source-of-truth/)，哪些資料屬於 cache、search index、event log 或報表副本。正式狀態會影響交易結果、權限判斷、對帳與客服修復，因此需要清楚的 owner、schema、驗證方式與變更流程。

訂單狀態、付款狀態、會員方案、權限授權與發票紀錄通常屬於正式狀態。商品搜尋索引、快取值、統計摘要與推薦結果通常是派生狀態；派生狀態可以錯過短暫更新，但正式狀態需要能被追溯、修復與稽核。

## Query Boundary

Query boundary 的責任是讓不同查詢路徑承擔不同服務問題。交易查詢、列表查詢、報表查詢與對帳查詢都可能讀同一張表，但它們的正確性、延遲與資料新鮮度要求不同。

| 查詢類型 | 服務責任                                     | 風險                                  |
| -------- | -------------------------------------------- | ------------------------------------- |
| 交易查詢 | 支援使用者當下動作，例如付款、下單、授權     | 延遲或錯誤會直接影響交易結果          |
| 列表查詢 | 支援使用者瀏覽與管理，例如訂單列表、會員清單 | 可能放大 index、pagination 與排序成本 |
| 報表查詢 | 支援營運分析、財務統計與趨勢判讀             | 容易壓迫線上資料庫與混淆資料時效      |
| 對帳查詢 | 驗證正式狀態與外部事實是否一致               | 查詢定義錯誤會造成錯修或漏修          |

這四種查詢混在一起時，資料庫會同時承擔低延遲交易與高成本分析，最後讓任何一種資料庫選型都變得模糊。

交易查詢是服務正確性的前線，設計重點是短路徑、可預期延遲與清楚交易邊界。列表查詢是產品體驗的定位工具，設計重點是排序、分頁與查詢成本。報表查詢支援營運判讀，通常可以接受資料延遲。對帳查詢承擔修復入口，結果會影響退款、補償或人工處理，因此要比一般報表保留更多證據。

## 交易路徑的邊界

交易路徑的責任是維持使用者動作的即時正確性。它需要短查詢、明確 index、可控 [transaction boundary](/backend/knowledge-cards/transaction-boundary/) 與清楚 timeout。

交易路徑的設計要把報表聚合或長時間掃描移到其他查詢路徑。若下單 API 同時查歷史報表、計算大範圍統計或同步重建派生狀態，交易延遲會被非交易責任拖慢。

## 列表與報表的邊界

列表查詢的責任是支援產品體驗中的瀏覽與定位。列表查詢需要穩定排序、分頁策略、篩選條件與查詢成本界線；它應建立自己的讀取模型或索引策略，避免直接借用交易查詢的資料模型造成 slow query、排序漂移與 pagination 重複。

報表查詢的責任是支援分析與決策。報表通常可以接受資料延遲，因此更適合使用 read replica、materialized view、ETL 或 analytics store。把報表直接壓在線上 primary 上，會讓交易服務承擔不必要的容量風險。

## 對帳查詢的邊界

對帳查詢的責任是驗證正式狀態是否與外部事實一致。付款、發票、庫存與訂閱方案都需要對帳查詢，但對帳查詢要保留時間窗、資料來源、差異定義與人工修復入口。

對帳查詢承擔比報表更直接的修復責任。報表回答「現在看起來如何」，對帳回答「哪一筆正式狀態需要修復」。因此對帳查詢結果要能進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 與 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 選型前判準

資料庫選型前要先回答四個問題：

1. 哪些資料是正式狀態，哪些是派生狀態。
2. 哪些查詢屬於交易路徑，哪些可以延遲或離線化。
3. 哪些查詢結果會觸發修復、退款、補償或人工決策。
4. 哪些資料需要 audit、masking、retention 或刪除責任。

這些問題決定後續該比較 relational database、document database、search index、analytics store 還是 cache。工具差異要放在責任邊界之後討論。

## 實體服務討論承接點

實體資料庫文章要承接本篇的 state ownership 與 query boundary。PostgreSQL、MySQL、MSSQL 或其他 relational database 的比較，應先問它們如何支援正式狀態、交易查詢、列表查詢、報表查詢與對帳查詢，再進入索引、隔離層級、replica 或工具語法。

若主問題是正式狀態與交易一致性，後續文章要優先比較 transaction、isolation、index 與 migration 能力。若主問題是報表與搜尋，後續文章要評估 read replica、materialized view、search index 或 analytics store。若主問題是對帳與修復，後續文章要比較 validation query、audit log、backup/restore 與資料修復流程。

## 下一步路由

要進一步處理 schema 與資料模型，接著讀 [1.2 schema design 與資料建模](/backend/01-database/schema-design/)。要處理 schema 演進與正式狀態變更，接著讀 [1.7 Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/)。
