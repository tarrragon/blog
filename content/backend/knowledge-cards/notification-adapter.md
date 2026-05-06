---
title: "Notification Adapter"
date: 2026-04-23
description: "說明通知通道如何把 domain event 轉成外部傳遞格式"
weight: 0
---


Notification Adapter 的核心概念是「把 domain event 或業務狀態，轉成 email、push、webhook 或其他通知格式」。 可先對照 [Object Storage](/backend/knowledge-cards/object-storage/)。

## 概念位置

Notification Adapter 位在 application 與通知渠道之間。它負責把內部事件轉成適合發送的外部 payload。 可先對照 [Object Storage](/backend/knowledge-cards/object-storage/)。

## 可觀察訊號

系統需要 notification adapter 的訊號是同一個事件要送到多種通知渠道，且各渠道格式、限制與失敗行為不同。

## 接近真實網路服務的例子

付款完成後寄送 email、訂單更新後送 push、事件變更後發 webhook，通常都由 notification adapter 負責。

## 設計責任

Notification Adapter 要處理 payload mapping、模板選擇、渠道限制、發送失敗與重試責任，避免通知細節污染業務流程。
