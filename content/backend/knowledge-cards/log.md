---
title: "Log"
date: 2026-04-23
description: "說明 log 如何記錄單一事件的上下文並支援事故排查"
weight: 140
---

Log 的核心概念是「記錄單一事件發生時的上下文」。它描述某個時間點發生了什麼、由誰觸發、處理結果如何，以及需要哪些欄位才能和 request、[trace](/backend/knowledge-cards/trace/)、[queue](/backend/knowledge-cards/queue/) 或資料變更關聯。

## 跟其他概念的關係

Log 是可觀測性的事件明細層。[Metrics](/backend/knowledge-cards/metrics/) 負責趨勢，trace 負責跨服務路徑，log 負責提供單一事件的判斷證據；[log schema](/backend/knowledge-cards/log-schema/) 則讓這些紀錄可以被穩定搜尋與聚合。

## 可觀察訊號與例子

系統需要 log 設計的訊號是事故時需要回答「哪一筆資料在哪一步失敗」。Checkout 失敗時，團隊需要用 [request id](/backend/knowledge-cards/request-id/)、order id、payment id 與錯誤分類找出同一流程的所有紀錄。

## 判斷條件與後果

事故時 log 能否回答「哪一筆資料在哪一步失敗」，取決於寫入時定了哪些內容。事件名稱、欄位與錯誤分類有定義時，團隊用 [request id](/backend/knowledge-cards/request-id/)、order id 與錯誤類型就篩得出同一流程的所有紀錄；沒有定義時，只能全文搜尋訊息字串，而每個工程師寫的措辭都不同。log level 沒有分級時，除錯用的大量紀錄與錯誤混在一起，查詢與儲存成本一起上升。敏感資料沒有遮罩、[retention](/backend/knowledge-cards/retention/) 沒有上限時，讀得到 log 的人都讀得到個資，而且這份副本長期保存。高風險操作的紀錄只寫在一般 log 時，它跟著一般 log 的保存期限被刪除，一般 log 也不保證寫入後不被改動，事後要證明誰做了什麼時沒有可靠的依據，所以這類操作另外寫入 [audit log](/backend/knowledge-cards/audit-log/)。
