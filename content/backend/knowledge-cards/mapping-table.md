---
title: "Mapping Table"
date: 2026-05-11
description: "說明遷移或轉換期間如何把舊語意明確對應到新語意"
weight: 145
tags: ["backend", "knowledge-card", "database", "migration"]
---

Mapping table 的核心概念是「把舊資料語意明確對應到新資料語意」。它連接 [schema migration](/backend/knowledge-cards/schema-migration/)、[correctness check](/backend/knowledge-cards/correctness-check/) 與 [validation-query](/backend/knowledge-cards/validation-query/)，讓轉換規則成為可查證 artifact，而不是工程師腦中的口頭規則。

## 概念位置

Mapping table 位在 [backfill](/backend/knowledge-cards/backfill/)、[data reconciliation](/backend/knowledge-cards/data-reconciliation/) 與 [migration gate](/backend/knowledge-cards/migration-gate/) 之間。Backfill 依它轉換資料，validation query 依它判斷 mismatch，incident decision log 則依它追溯當時的判讀依據。

## 可觀察訊號

系統需要 mapping table 的訊號是：

- 舊欄位混合多種業務語意，需要拆到新欄位
- 多個舊狀態會對應到同一個新狀態
- 某些舊狀態需要人工確認或例外處理
- 事後要能解釋 mismatch 是資料錯誤還是轉換規則錯誤

## 接近真實網路服務的例子

訂單服務把 `pending_payment`、`paid`、`payment_failed`、`refunded` 對應到 `payment_state` 的 `pending`、`captured`、`failed`、`refunded`。這張 mapping table 同時支撐 backfill job、validation query 與 cutover gate。

## 設計責任

Mapping table 要保留來源欄位、新欄位、對應理由、例外狀態與 owner。高風險 mapping 要版本化，並進入 [evidence package](/backend/knowledge-cards/evidence-package/)；否則資料漂移時，團隊很難判斷問題出在資料、程式還是規則本身。
