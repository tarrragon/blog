---
title: "Migration Gate"
date: 2026-04-24
description: "說明遷移流程何時可以進入下一階段或正式切換"
weight: 140
---


Migration Gate 的核心概念是「在遷移流程中，用明確條件決定能不能進下一階段或正式切換」。 可先對照 [Migration](/backend/knowledge-cards/migration/)。

## 概念位置

Migration Gate 位在 migration、backfill、correctness check、data completeness 與 cutover 之間。它是遷移內部的階段控制點，不等於一般的 release gate。 可先對照 [Migration](/backend/knowledge-cards/migration/)。

## 可觀察訊號

系統需要 migration gate 的訊號是：

- 新舊狀態會並存一段時間
- 進下一階段前要先確認資料已補齊或結果已比對
- 切換前必須先確認副作用可控
- 遷移失敗時要能停在安全階段

## 接近真實網路服務的例子

資料搬遷到新 table 後，先確認 row count、關聯完整性與抽樣結果，再決定能否進入 cutover；搜尋索引重建完成後，先通過 correctness check 與 shadow read，再把讀取流量切過去。這些決定都屬於 migration gate。

## 設計責任

Migration Gate 要定義每一階段的通過條件、資料證據、擁有者與停止條件。它的目標是讓遷移不只是「做完」，而是「安全地前進或回頭」。
