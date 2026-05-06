---
title: "Log"
date: 2026-04-23
description: "說明 log 如何記錄單一事件的上下文並支援事故排查"
weight: 139
---


Log 的核心概念是「記錄單一事件發生時的上下文」。它描述某個時間點發生了什麼、由誰觸發、處理結果如何，以及需要哪些欄位才能和 request、[trace](/backend/knowledge-cards/trace/)、[queue](/backend/knowledge-cards/queue/) 或資料變更關聯。

## 概念位置

Log 是可觀測性的事件明細層。[Metrics](/backend/knowledge-cards/metrics/) 負責趨勢，trace 負責跨服務路徑，log 負責提供單一事件的判斷證據；[log schema](/backend/knowledge-cards/log-schema/) 則讓這些紀錄可以被穩定搜尋與聚合。

## 可觀察訊號與例子

系統需要 log 設計的訊號是事故時需要回答「哪一筆資料在哪一步失敗」。Checkout 失敗時，團隊需要用 [request id](/backend/knowledge-cards/request-id/)、order id、payment id 與錯誤分類找出同一流程的所有紀錄。

## 設計責任

Log 設計要定義 log level、事件名稱、欄位、錯誤分類、敏感資料遮罩、[retention](/backend/knowledge-cards/retention/) 與查詢成本。高風險操作應另外寫入 [audit log](/backend/knowledge-cards/audit-log/)，保留責任證據。
