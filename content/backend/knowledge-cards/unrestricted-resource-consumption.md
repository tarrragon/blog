---
title: "Unrestricted Resource Consumption"
date: 2026-04-23
description: "說明缺少資源限制如何讓 API 被濫用或拖垮"
weight: 117
---

Unrestricted resource consumption 的核心概念是「API 沒有對資源使用量設定足夠限制」。攻擊者或錯誤 client 可以用大量 request、大型 payload、昂貴查詢或大量匯出耗盡系統資源。 可先對照 [Validation Middleware](/backend/knowledge-cards/validation-middleware/)。

## 跟其他概念的關係

資源消耗限制連接 rate limit、payload limit、timeout、pagination、query cost、queue quota 與 tenant quota。它同時是可靠性與資安問題。 可先對照 [Validation Middleware](/backend/knowledge-cards/validation-middleware/)。

## 可觀察訊號與例子

系統需要資源消耗限制的訊號是 API 支援搜尋、匯出、上傳、批次操作或複雜 filter。未限制日期範圍的報表匯出，可能讓單一 request 掃描多年資料。

## 判斷條件與後果

API 少了哪一種資源限制，就留下哪一種耗盡方式。沒有大小限制時，單一大型 payload 佔滿記憶體或頻寬；沒有速率限制時，大量 request 佔滿處理能力；沒有分頁或查詢成本上限時，一個未限制日期範圍的匯出掃描多年資料；沒有 timeout 時，昂貴查詢一直佔著連線；沒有租戶配額時，單一租戶耗盡共用資源，其他租戶跟著變慢；沒有告警時，這些耗用要到服務變慢才被發現。被擋下的 client 只拿到通用錯誤時，會原樣重送同一個請求，所以錯誤回應寫出超過了哪一項限制、怎麼縮小請求。
