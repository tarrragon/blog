---
title: "Webhook"
date: 2026-04-23
description: "說明外部系統回呼事件的接收、驗證與處理邊界"
weight: 156
---

Webhook 的核心概念是「外部系統主動把事件推送到你的 endpoint」。它常用於支付、物流、第三方整合通知。 可先對照 [Website Certificate Lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/)。

## 跟其他概念的關係

Webhook 通常需要來源驗證、重放防護、重試處理與可追蹤事件 ID。 可先對照 [Website Certificate Lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/)。

## 判斷條件與後果

Webhook endpoint 對外公開，送進來的請求內容與次數由外部系統決定，每一種保護缺席都對應一種錯誤狀態。沒有簽章驗證時，任何人都能偽造一筆付款成功通知；沒有時窗限制時，截下的合法請求可以事後重放；沒有冪等處理時，外部系統的正常重送讓同一事件被處理兩次（出貨兩次、入帳兩次）；錯誤回應策略不明時，外部系統依回應碼決定是否重送，回錯碼會讓失敗的事件不再重送，或讓已處理的事件一再重送。

冪等處理這一項在對外整合時要逐家讀條款：各 vendor 用來去重的 header 名稱不同是命名之爭，而重送回什麼、事件保留多久才是語意之爭，後者跟業務形態綁在一起、沒有標準可依（見 [Idempotency key 標準化之爭](/backend/11-api-design/idempotency-key-standardization-debate/)）。各家的投遞承諾差異見 [webhook 對外承諾](/backend/11-api-design/styles/realtime/realtime-webhook-contract/)。
