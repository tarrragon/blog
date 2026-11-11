---
title: "Webhook Protocol"
date: 2026-04-23
description: "說明外部回呼如何對齊簽章、重試與 payload 語意"
weight: 1
---

Webhook Protocol 的核心概念是「外部系統把事件送進來時，雙方如何對齊驗證、payload 與失敗語意」。 可先對照 [Webhook](/backend/knowledge-cards/webhook/)。

## 跟其他概念的關係

Webhook Protocol 位在 external system、HTTP endpoint 與 service 之間。它是外部事件導入的通訊約定。 可先對照 [Webhook](/backend/knowledge-cards/webhook/)。

## 可觀察訊號

系統需要 webhook protocol 的訊號是第三方會主動呼叫服務，而且需要簽章驗證、重放防護與穩定 payload。

## 接近真實網路服務的例子

付款通知、物流更新、SaaS 事件同步與第三方 callback 都會使用 webhook protocol。呼叫方與接收方都需要知道成功與失敗時的行為。

## 判斷條件與後果

Webhook Protocol 的每一項約定缺席時，接收端各自失去一種判斷能力。沒有[簽章](/backend/knowledge-cards/message-authentication/)時，接收端分不出請求是否來自宣稱的外部系統；沒有 timestamp 時，截下的合法請求在任何時間都能重放；重送規則沒有約定時，呼叫方失敗後送幾次、接收端是否要去重，兩邊各自猜；payload schema 沒有約定時，呼叫方改一個欄位，接收端就在 production 解析失敗；錯誤回應沒有約定時，呼叫方分不出該重送還是放棄。這組約定處理的是外部系統主動推送，方向跟 public API 的主動查詢相反，所以兩者分開設計。
