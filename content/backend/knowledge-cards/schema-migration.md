---
title: "Schema Migration"
date: 2026-04-23
description: "說明資料庫結構如何隨應用程式版本安全演進"
weight: 15
---

Schema migration 的核心概念是「用版本化流程修改 [database](../database/) 結構」。資料表、欄位、索引、constraint 與資料修補都會影響 application，因此 [migration](../migration/) 要和部署、回滾、資料量與相容性一起設計。

## 概念位置

Migration 是 database 與 release 流程的交界。小型服務可能只需要簡單版本檔；正式服務通常需要 [Expand / Contract](../expand-contract/) 策略，先新增可相容欄位，再部署 application，最後移除舊欄位。

## 可觀察訊號與例子

系統需要 migration 策略的訊號是多個版本會同時存在。Rolling update 期間，新舊 application 可能同時讀寫資料庫；若 migration 一次移除舊欄位，舊版本 instance 可能立刻失敗。

## 設計責任

Migration 設計要包含相容性、[backfill](../backfill/)、索引建立成本、鎖表風險、回滾策略與 [Release Gate](../release-gate/)。高風險 migration 應先在接近正式資料量的環境驗證。
