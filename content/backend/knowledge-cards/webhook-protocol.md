---
title: "Webhook Protocol"
date: 2026-04-23
description: "說明外部回呼如何對齊簽章、重試與 payload 語意"
weight: 0
---

Webhook Protocol 的核心概念是「外部系統把事件送進來時，雙方如何對齊驗證、payload 與失敗語意」。

## 概念位置

Webhook Protocol 位在 external system、HTTP endpoint 與 service 之間。它是外部事件導入的通訊約定。

## 可觀察訊號

系統需要 webhook protocol 的訊號是第三方會主動呼叫服務，而且需要簽章驗證、重放防護與穩定 payload。

## 接近真實網路服務的例子

付款通知、物流更新、SaaS 事件同步與第三方 callback 都會使用 webhook protocol。呼叫方與接收方都需要知道成功與失敗時的行為。

## 設計責任

Webhook Protocol 要定義簽章、timestamp、重送、payload schema 與錯誤回應。它應與 public API 分開看待，因為它承擔的是外部推送而不是主動查詢。
