---
title: "Correctness Check"
date: 2026-04-23
description: "說明遷移或重構期間如何驗證新舊結果是否符合規則"
weight: 85
---

Correctness check 的核心概念是「用明確規則驗證新舊結果是否一致或可接受」。它不只比對字面相等，也要理解哪些差異符合預期，哪些差異代表資料錯誤。

## 概念位置

Correctness check 是 migration、refactoring、shadow read、backfill 與 cutover 的決策依據。沒有正確性檢查，團隊只能憑錯誤率或使用者回報判斷新系統。

## 可觀察訊號與例子

系統需要 correctness check 的訊號是新舊系統會並行一段時間。價格計算服務重寫後，要比對總價、折扣、稅額、幣別與 rounding 規則，而不只是比對 response 字串。

## 設計責任

Correctness check 要定義比對欄位、容忍差異、抽樣策略、錯誤分類與停止條件。高風險差異要能追到 request id、資料版本與規則版本，並作為 [Migration Gate](../migration-gate/) 的依據。
