---
title: "Mapping Table"
date: 2026-05-11
description: "說明遷移或轉換期間如何把舊語意明確對應到新語意"
weight: 146
tags: ["backend", "knowledge-card", "database", "migration"]
---

Mapping table 的核心概念是「把舊資料語意明確對應到新資料語意」。它連接 [schema migration](/backend/knowledge-cards/schema-migration/)、[correctness check](/backend/knowledge-cards/correctness-check/) 與 [validation-query](/backend/knowledge-cards/validation-query/)，讓轉換規則成為可查證 artifact，而不是工程師腦中的口頭規則。

## 跟其他概念的關係

Mapping table 位在 [backfill](/backend/knowledge-cards/backfill/)、[data reconciliation](/backend/knowledge-cards/data-reconciliation/) 與 [migration gate](/backend/knowledge-cards/migration-gate/) 之間。Backfill 依它轉換資料，validation query 依它判斷 mismatch，incident decision log 則依它追溯當時的判讀依據。

## 可觀察訊號

系統需要 mapping table 的訊號是：

- 舊欄位混合多種業務語意，需要拆到新欄位
- 多個舊狀態會對應到同一個新狀態
- 某些舊狀態需要人工確認或例外處理
- 事後要能解釋 mismatch 是資料錯誤還是轉換規則錯誤

## 接近真實網路服務的例子

訂單服務把 `pending_payment`、`paid`、`payment_failed`、`refunded` 對應到 `payment_state` 的 `pending`、`captured`、`failed`、`refunded`。這張 mapping table 同時支撐 backfill job、validation query 與 cutover gate。

## 判斷條件與後果

Mapping table 的欄位各自保留一種事後追查要用的資訊。只有來源欄位與新欄位、沒有對應理由時，看得到舊值轉成哪個新值，看不到為什麼這樣轉，規則被質疑時沒有依據可查；沒有例外狀態時，需要人工確認的舊狀態被直接對到某個新狀態；沒有 owner 時，規則要修改時不知道該由誰確認。高風險的 mapping 沒有版本化、也沒有進入 [evidence package](/backend/knowledge-cards/evidence-package/) 時，資料漂移之後，團隊分不出 mismatch 來自資料本身、轉換程式還是當時的對應規則，原因是規則可能在那之後改過，當時的版本沒有留下。
