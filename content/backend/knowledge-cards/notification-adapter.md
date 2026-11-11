---
title: "Notification Adapter"
date: 2026-04-23
description: "說明通知通道如何把 domain event 轉成外部傳遞格式"
weight: 1
---

Notification Adapter 的核心概念是「把 domain event 或業務狀態，轉成 email、push、webhook 或其他通知格式」。 可先對照 [Object Storage](/backend/knowledge-cards/object-storage/)。

## 跟其他概念的關係

Notification Adapter 位在 application 與通知渠道之間。它負責把內部事件轉成適合發送的外部 payload。 可先對照 [Object Storage](/backend/knowledge-cards/object-storage/)。

## 可觀察訊號

系統需要 notification adapter 的訊號是同一個事件要送到多種通知渠道，且各渠道格式、限制與失敗行為不同。

## 接近真實網路服務的例子

付款完成後寄送 email、訂單更新後送 push、事件變更後發 webhook，通常都由 notification adapter 負責。

## 判斷條件與後果

通知渠道的細節寫在業務流程裡時，每加一種渠道或改一個模板，都要改動發出事件的那段業務程式。各渠道的格式、長度與發送頻率限制不同，payload mapping 與模板選擇不在 Notification Adapter 裡時，同一個事件要在業務程式裡依渠道各寫一份。發送失敗與重試的責任沒有歸屬時有兩種結果：業務流程等待通知送出，渠道失敗連帶讓付款、下單這類主流程失敗；或者沒有任何一層重試，失敗的通知就此遺失。
