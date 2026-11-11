---
title: "Data Completeness"
date: 2026-04-23
description: "說明資料是否完整到足以支持查詢、遷移與決策"
weight: 87
---

Data completeness 的核心概念是「資料是否完整到足以支持目標用途」。資料可以格式正確，但仍缺少必要筆數、欄位、時間範圍或關聯資料。 可先對照 [Migration Gate](/backend/knowledge-cards/migration-gate/)。

## 跟其他概念的關係

Completeness 是資料品質的一部分。Migration、backfill、報表、audit、搜尋索引與機器學習資料集都需要確認資料是否完整。 可先對照 [Migration Gate](/backend/knowledge-cards/migration-gate/)。

## 可觀察訊號與例子

系統需要 completeness check 的訊號是資料遷移完成後仍可能缺漏。訂單資料搬遷時，除了 row count，也要確認 order items、付款紀錄、退款紀錄與狀態歷史是否完整。

## 判斷條件與後果

Completeness 檢查只比對總量時，筆數對得上而內容缺漏的情形看不出來：訂單主表的 row count 一致，order items、付款紀錄或狀態歷史仍可能缺。分群比對看得到總量相同而某個 tenant 或類別少了資料，時間範圍比對看得到某一段期間整批漏搬，關聯完整性看得到主表有、子表沒有的資料，抽樣則檢查格式正確的資料內容是否也正確。檢查沒有留下可重跑的查詢或報表時，[Migration Gate](/backend/knowledge-cards/migration-gate/) 拿到的是一次性的結論，backfill 或修復之後無法用同一個標準再驗一次。
