---
title: "1.4 repository adapter 實作"
date: 2026-04-23
description: "整理 SQL row mapping 與錯誤轉換"
weight: 4
tags: ["backend", "database", "repository-adapter"]
---

資料庫倉儲轉接層（repository adapter）的核心責任是把應用層語意轉成資料庫可執行操作，並把資料庫錯誤回譯成業務可判讀結果。它是 `domain model` 和 `SQL model` 之間的邊界層，不承擔業務流程編排。

## 邊界責任

adapter 接收應用層輸入，負責三件事：查詢與命令組裝、row mapping、錯誤翻譯。業務規則判斷留在 service/usecase 層，adapter 聚焦在資料持久化語意與資料庫行為。

邊界清楚的好處是演進可控。schema 調整時，只需要在 adapter 收斂欄位映射與查詢變更，不用把 SQL 細節滲透回 domain 層。

## row mapping 與 nullable handling

row mapping 的責任是把資料庫欄位轉成穩定模型。欄位型別、時間格式、枚舉值、可空欄位都要有明確轉換規則。可空欄位需要顯式處理，避免把「缺值」誤當有效預設值。

資料模型演進時，新舊欄位可能共存。adapter 要支援過渡期讀寫相容，讓版本切換能分批進行。

## error translation

error translation 的責任是把底層錯誤分類成應用層可決策訊號。唯一鍵衝突、外鍵限制、交易衝突、連線逾時，都需要翻譯成可行動錯誤類型，而不是將原生錯誤字串直接外漏。

這層翻譯會直接影響重試、回退與事故判讀。分類越穩定，越能在 06/08 模組形成一致決策語言。

## contract test

[contract](/backend/knowledge-cards/contract/) test 的責任是驗證 adapter 對外語意穩定：同一輸入是否得到一致輸出、同一錯誤是否被穩定分類、同一查詢語意在 schema 演進後是否保持相容。

測試重點不是資料庫產品特性覆蓋，而是邊界語意覆蓋。這能讓 repository 介面在多版本與多環境下維持可預期行為。

## 判讀訊號

| 訊號                                  | 判讀重點                   | 對應動作                              |
| ------------------------------------- | -------------------------- | ------------------------------------- |
| 同一業務錯誤在不同路徑返回不同型別    | error translation 分類漂移 | 收斂錯誤分類介面與 mapping            |
| schema 變更後應用層出現大量 null 問題 | nullable handling 規則不足 | 補顯式轉換與 fallback 規則            |
| SQL 細節在 service 層大量出現         | adapter 邊界被繞過         | 收斂資料操作入口到 repository         |
| 同一查詢在不同環境結果不一致          | contract test 覆蓋不足     | 補跨環境合約測試與 fixture            |
| 事故排查時難以判斷重試與回退條件      | 錯誤分類無法對應決策       | 建立錯誤分類到 gate/incident 的映射表 |

## 常見誤區

把 repository adapter 寫成「直接包 SQL 的工具函式」，容易讓業務規則與資料邏輯混雜。邊界失焦後，schema 演進與事故修復都會擴大影響面。

把資料庫錯誤原樣往上拋，也會讓上層決策不穩定。錯誤翻譯是可靠性控制面的必要前置。

## 案例回寫

adapter 邊界可用 [3.C9 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) 的資料一致性段落回寫。若事件中出現同一錯誤在不同路徑被不同方式處理，通常代表 adapter 的錯誤翻譯與契約分層不足。

回寫步驟是先盤點錯誤分類，再對齊重試與回退決策，最後把分類結果映射到 [6.10 Contract Testing 與 Schema 演進](/backend/06-reliability/contract-testing/) 的驗證欄位，讓發版前可先發現漂移。

## 跨模組路由

1. 與 1.2 的交接：欄位與索引語意回到 [schema design 與資料建模](/backend/01-database/schema-design/)。
2. 與 1.3 的交接：交易錯誤與重試語意回到 [transaction 與一致性邊界](/backend/01-database/transaction-boundary/)。
3. 與 6.10 的交接：跨服務契約一致性回到 [Contract Testing 與 Schema 演進](/backend/06-reliability/contract-testing/)。
4. 與 8.19 的交接：資料層錯誤判斷與回退決策回到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

要把 adapter 放進資料演進流程，接著讀 [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/)。要把跨服務契約與資料層測試對齊，接著讀 [6.10 Contract Testing 與 Schema 演進](/backend/06-reliability/contract-testing/)。
