---
title: "Rollback Condition"
date: 2026-05-11
description: "說明決策執行後出現哪些訊號時要撤回、回退或改路線"
weight: 161
tags: ["backend", "knowledge-card", "incident-response", "reliability"]
---

Rollback condition 的核心概念是「某個決策執行後，看到哪些訊號時要撤回、回退或改路線」。它連接 [incident decision log](/backend/knowledge-cards/incident-decision-log/)、[rollback strategy](/backend/knowledge-cards/rollback-strategy/) 與 [stop condition](/backend/knowledge-cards/stop-condition/)，讓事故現場能控制次生風險。

## 跟其他概念的關係

Rollback condition 位在 [gate decision](/backend/knowledge-cards/gate-decision/)、[rollback window](/backend/knowledge-cards/rollback-window/) 與 [time range](/backend/knowledge-cards/time-range/) 之間。Stop condition 常用於流程何時停，rollback condition 則跟某筆已做出的 decision 綁在一起。

## 可觀察訊號

系統需要 rollback condition 的訊號是：

- rollback、fallback、degradation 或 fail-forward 本身也可能造成風險
- IC handoff 後，新 IC 需要知道什麼條件下要改路線
- stakeholder update 需要說明目前決策如何被監控
- PIR 需要檢查當時是否有明確撤回條件

## 接近真實網路服務的例子

客服後台切回 legacy status fallback 後，rollback condition 可以寫成 `mismatch remains above threshold after 15 minutes`。這表示 fallback 沒有降低錯誤時，團隊要改成資料修補或暫停相關入口，而不是繼續等待。

## 判斷條件與後果

Rollback condition 的判斷對象是一筆已做出的決策，在什麼證據出現時撤回。條件缺了門檻或觀察窗口時，「fallback 沒有改善」要靠現場的人各自判斷，等多久才改路線沒有定論；缺了對應動作時，條件成立之後還要再開一次討論；缺了 owner 時，IC handoff 之後沒有人確認條件是否已經成立。條件只存在口頭上時，事後的 PIR 查不回當時看到的數字；連到 [query link](/backend/knowledge-cards/query-link/) 與 [time range](/backend/knowledge-cards/time-range/) 時，撤回的決定可以重新查出當時的訊號，回放成證據。
