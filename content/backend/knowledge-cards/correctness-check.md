---
title: "Correctness Check"
date: 2026-04-23
description: "說明遷移或重構期間如何驗證新舊結果是否符合規則"
weight: 86
---

Correctness check 的核心概念是「用明確規則驗證新舊結果是否一致或可接受」。它不只比對字面相等，也要理解哪些差異符合預期，哪些差異代表資料錯誤。 可先對照 [Migration Gate](/backend/knowledge-cards/migration-gate/)。

## 跟其他概念的關係

Correctness check 是 migration、refactoring、shadow read、backfill 與 cutover 的決策依據。沒有正確性檢查，團隊只能憑錯誤率或使用者回報判斷新系統。 可先對照 [Migration Gate](/backend/knowledge-cards/migration-gate/)。

## 可觀察訊號與例子

系統需要 correctness check 的訊號是新舊系統會並行一段時間。價格計算服務重寫後，要比對總價、折扣、稅額、幣別與 rounding 規則，而不只是比對 response 字串。

## 判斷條件與後果

Correctness check 的結果是否足以放行，看它定義了哪幾項。沒有指定比對欄位與容忍差異時，比對退回 response 字串的字面相等，rounding 規則改變造成的預期差異與真正算錯的總價混在同一批 mismatch 裡，每一筆都要人工判讀。抽樣策略沒有涵蓋的路徑（某個幣別、某類折扣）算錯了也不會出現在報告裡。沒有錯誤分類與停止條件時，mismatch 上升只是一個數字，沒有一個值代表要停下並行或回退。高風險差異追不到 request id、資料版本與規則版本時，團隊知道有差異卻重現不了，原因是同一筆輸入在不同資料版本或規則版本下本來就可能算出不同結果。這些項目齊全的比對結果，才能當 [Migration Gate](/backend/knowledge-cards/migration-gate/) 的依據。
