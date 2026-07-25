---
title: "Out-of-Band Signal（頻外訊號）"
date: 2026-07-20
description: "觀測系統本身也可能在事故中失能時、判斷該從哪個獨立通道取得系統存活狀態"
weight: 407
---

Out-of-band signal 住在觀測系統的失效邊界之外——它是一個獨立失效域、不依賴被觀測系統自己上報，用來在內部 telemetry 全黑時仍能回答「系統死沒死」。這個獨立性是它唯一的核心要求：把它跟主系統放進同一個資料庫、同一個部署管線、同一個雲區域，等於讓它跟要它救援的對象共享同一個失效點，價值就消失。可先對照 [Status Page](/backend/knowledge-cards/status-page/)。

## 概念位置

Out-of-band signal 處理的是觀測共命運失效——觀測系統跟被觀測系統共享失效域、在事故壓力下一起退化。它有兩種互補形態：心跳消失（外部偵測器監看「本該持續觸發的告警」是否停止，停止即代表監控管線本身斷了）與外部探測（blackbox / synthetic 從外部 vantage point 主動打 endpoint）。對外的一端會落到 [Status Page](/backend/knowledge-cards/status-page/)——狀態通道要跟主服務切開，否則使用者連查詢故障狀態的入口都拿不到。

## 可觀察訊號與例子

kube-prometheus 的 Watchdog alert 設計成「is always firing」，一旦停止觸發，就代表告警管線本身出了問題——這時沒有其他告警會通知「監控系統死了」，只有獨立於管線之外的偵測器（如 Dead Man's Snitch）能發現心跳消失（2026）。另一種形態是客訴：內部監控漏掉時，客服累積的電話、社群貼文與工單常是實際生效的補位訊號，但它有延遲與噪音，管的是「哪個功能對誰壞了」而非「系統死沒死」。

## 判讀方式

判斷一個訊號是否夠格當 out-of-band signal，判讀的核心是失效域重疊度——共用同一個雲帳號、同一個網路、同一組憑證都算重疊。這類訊號平時難以自我辯護：沒事故時看不出價值，review 時最容易被當成過度準備砍掉，但它的 ROI 全押在觀測退化的那一小時。完整的機制拆解與客訴升級路徑見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)。
