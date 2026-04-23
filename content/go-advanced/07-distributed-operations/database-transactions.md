---
title: "7.1 資料庫 transaction 與 schema migration"
date: 2026-04-22
description: "把 repository 邊界延伸到資料庫交易、migration 與一致性語意"
weight: 1
---

資料庫整合的核心責任是讓持久化行為符合 application 的狀態規則。Repository port 決定 usecase 需要哪些資料能力；[transaction boundary](../../backend/knowledge-cards/transaction-boundary/)、[schema migration](../../backend/knowledge-cards/schema-migration/)、[Expand / Contract](../../backend/knowledge-cards/expand-contract/) 與 [isolation level](../../backend/knowledge-cards/isolation-level/) 則決定這些能力在資料庫中如何保持一致。

## 本章目標

學完本章後，你將能夠：

1. 判斷 [[transaction](../../backend/knowledge-cards/transaction) boundary](../../backend/knowledge-cards/transaction-boundary) 應該放在 repository 還是 usecase
2. 理解 [migration](../../backend/knowledge-cards/migration) 為什麼要維持向前相容
3. 分辨 application validation、constraint 與 [isolation level](../../backend/knowledge-cards/isolation-level) 的責任
4. 用 contract test 保護 memory repository 與 [database](../../backend/knowledge-cards/database) repository 的一致行為
5. 讓 SQL 細節留在 adapter，讓 domain 規則留在 application

## 前置章節

- [Go 入門：如何新增 repository port](../../go/06-practical/repository-port/)
- [Go 入門：狀態管理的安全邊界](../../go/07-refactoring/state-boundary/)
- [Go 進階：Source of Truth：狀態邊界](../04-architecture-boundaries/source-of-truth/)
- [Backend：Source of Truth](../../backend/knowledge-cards/source-of-truth/)
- [Backend：Connection Pool](../../backend/knowledge-cards/connection-pool/)

## 後續撰寫方向

1. Repository method 如何表達交易語意，讓 SQL 細節留在 adapter。
2. 一個 usecase 需要多筆寫入同時成功或失敗時，transaction boundary 應放在哪裡。
3. [Migration](../../backend/knowledge-cards/migration/) 如何維持向前相容，避免新舊程式版本互相破壞資料。
4. Isolation level、unique constraint 與 application-level validation 如何分工。
5. Contract test 如何保護 memory repository 與 database repository 的一致行為。

## 【觀察】transaction 是一致性邊界

transaction 的核心用途是把一組資料庫操作綁成單一一致性單位。判斷重點是：這個 usecase 哪些狀態要一起成功或一起失敗。效能與寫入便利性都應放在一致性需求之後評估。

例如建立訂單時，可能同時需要：

- 寫入 order 主表
- 寫入 order items
- 更新 inventory
- 寫入 outbox event

如果其中一個步驟失敗，整組操作就應回滾，避免 application 狀態和資料庫狀態分裂。

## 【判讀】transaction boundary 應該跟 usecase 對齊

交易邊界最常見的錯誤，是把 transaction 放得太低或太高。

- 放太低：repository 各自開 transaction，usecase 層看起來成功，實際上無法保證整體一致。
- 放太高：把不需要一致性的讀取、外部 API、長迴圈也包進 transaction，讓連線被占住太久。

一般原則是：

- 要維持同一個 domain 不變式的寫入，應放在同一個 transaction。
- 可以重試或可補償的外部互動，通常應放在 transaction 之外。

## 【策略】[Migration](../../backend/knowledge-cards/migration/) 要讓舊版與新版可以共存

[schema migration](../../backend/knowledge-cards/schema-migration/) 的核心是讓部署期間的新舊版本能同時活著。實務上常見的是 [Expand / Contract](../../backend/knowledge-cards/expand-contract/) 流程：

1. 先新增欄位、表或索引。
2. 讓新舊程式都能讀寫。
3. 確認流量已切到新版本。
4. 再移除舊欄位或舊邏輯。

這樣做的目的，是避免應用版本與資料庫版本在 rolling deploy 時互相踩到。

## 【判讀】constraint、validation 與 isolation level 各管不同風險

這三者的責任應清楚分工：

- application validation：在進資料庫前先檢查基本輸入是否合法。
- unique / foreign key / check constraint：在資料庫層保底，防止不合法資料落地。
- isolation level：處理多交易同時進行時的可見性與衝突問題。

如果只靠 application validation，資料庫仍可能被其他路徑寫入不合法資料。如果只靠資料庫 constraint，錯誤回報可能太晚。兩者通常要一起用。

## 【執行】contract test 檢查 repository 語意一致

當你同時有 memory repository 與 database repository 時，測試重點是它們對外暴露的語意是否一致。SQL 細節屬於 database adapter 的內部實作。

通常要測：

- 找不到資料時怎麼回傳
- 重複寫入時怎麼回傳
- transaction 失敗時是否維持一致狀態
- 欄位驗證與預設值是否相同

這類測試可以讓 repository adapter 保持可替換，讓資料庫替換時 usecase 維持穩定。

## 本章不處理

本章不會選定特定資料庫或 ORM。真正的重點是 Go application 如何定義資料一致性責任，讓 SQLite、PostgreSQL 或其他儲存技術都能成為可替換 adapter。

## 和 Go 教材的關係

這一章承接的是 Go 的 repository port 與狀態邊界；如果你要先回看語言教材，可以讀：

- [Go：如何新增 repository port](../../go/06-practical/repository-port/)
- [Go：狀態管理的安全邊界](../../go/07-refactoring/state-boundary/)
- [Go 進階：Source of Truth](../04-architecture-boundaries/source-of-truth/)
