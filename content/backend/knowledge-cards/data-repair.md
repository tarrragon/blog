---
title: "Data Repair"
date: 2026-07-20
description: "說明資料修復如何用 dry-run、稽核與可逆設計把已確認差異安全改回正式狀態"
weight: 388
tags: ["backend", "knowledge-card", "database", "reliability"]
---

Data repair 的核心責任是把已確認的資料差異，用可控、可稽核、可逆的方式改回正式狀態，而不是「一個工程師動手改」。它跟 [data reconciliation](/backend/knowledge-cards/data-reconciliation/) 是流程上的下一棒：reconciliation 找出差異、data repair 執行修復，兩者的判讀邏輯完全不同——前者是比對兩個來源，後者是決定用什麼手段改動正式狀態、留下什麼證據。

## 概念位置

Data repair 位在 [rollback window](/backend/knowledge-cards/rollback-window/) 關閉之後、[fail-forward](/backend/knowledge-cards/fail-forward/) 之前的資料層動作：回退回不去舊狀態時，修復是把資料改到正確狀態的具體手段。修復對象分三種，處理路徑各不相同——正式欄位錯誤要修 [source of truth](/backend/knowledge-cards/source-of-truth/) 本身，衍生狀態（cache、index、read model）錯誤要重建，外部副作用（退款、通知、webhook）漏做要走補償流程。判讀重點是先確認問題落在哪一層，再決定用哪條路徑。

## 可觀察訊號與例子

需要 data repair 的訊號是差異已經被 reconciliation 分類確認、且業務判斷需要修復而非等待收斂。付款狀態卡在 `pending` 但金流 provider 顯示已扣款時，修復動作是把訂單狀態改成 `paid`；訂單主表寫入成功但 line items 沒寫入時，修復動作是重建缺漏的關聯資料。修復規模決定執行方式：單筆到十筆是客服等級（一人執行、一人審核）；萬筆以上要當成 production deploy 處理，先在小比例流量試跑再擴大。

## 設計責任

Data repair 要在執行前完成 dry-run（用同樣的 WHERE 條件跑 SELECT、估算影響筆數與連帶效果），並遵守三個原則：[idempotency](/backend/knowledge-cards/idempotency/)（同樣的修復跑兩次結果要一樣）、可稽核（每次修復留下 actor、reviewer、修復前後 snapshot 到 [audit log](/backend/knowledge-cards/audit-log/)）、可逆（不可逆操作要先備份、留 rollback path）。高風險修復（金錢、權限、個資）要求兩位以上人員各自看過 dry-run 結果才能執行。事故壓力下跳過 dry-run 直接 UPDATE、反而容易讓單點差異擴大成批次污染——時間壓力正是 dry-run 最有價值的時候。完整的分級執行策略、四眼審核流程與跨服務對帳責任分派見 [1.9 Reconciliation 與 Data Repair](/backend/01-database/reconciliation-data-repair/)。
