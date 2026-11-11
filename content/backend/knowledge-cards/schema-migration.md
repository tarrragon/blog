---
title: "Schema Migration"
date: 2026-04-23
description: "說明資料庫結構如何隨應用程式版本安全演進"
weight: 16
---

Schema migration 的核心概念是「用版本化流程修改 [database](/backend/knowledge-cards/database/) 結構」。資料表、欄位、索引、constraint 與資料修補都會影響 application，因此 [migration](/backend/knowledge-cards/migration/) 要和部署、回滾、資料量與相容性一起設計。

## 跟其他概念的關係

Migration 是 database 與 release 流程的交界。小型服務可能只需要簡單版本檔；正式服務通常需要 [Expand / Contract](/backend/knowledge-cards/expand-contract/) 策略，先新增可相容欄位，再部署 application，最後移除舊欄位。

## 可觀察訊號與例子

系統需要 migration 策略的訊號是多個版本會同時存在。Rolling update 期間，新舊 application 可能同時讀寫資料庫；若 migration 一次移除舊欄位，舊版本 instance 可能立刻失敗。

## 判斷條件與後果

一次 schema migration 是否讓服務讀寫失敗或停頓，取決於它跟新舊版本並存、既有資料量與回滾路徑的關係。Migration 不相容於舊版本時（一次移除舊欄位），rolling update 期間仍在跑的舊版本 instance 從 migration 執行的那一刻開始讀寫失敗；新欄位需要既有資料補值而沒有 [backfill](/backend/knowledge-cards/backfill/) 時，新版本讀到空值；在大表上建索引或改欄位型別時，鎖表的時間隨資料量增長，這段期間的寫入等待鎖、逾時或失敗；沒有回滾策略時，新版本出錯只能往前修，因為退回的舊版本程式碼面對的是已經變更的 schema。鎖表與 backfill 的耗時都隨資料量增長，小資料量的測試環境量不出來，所以高風險 migration 先在接近正式資料量的環境驗證，驗證結果作為 [Release Gate](/backend/knowledge-cards/release-gate/) 的依據。
