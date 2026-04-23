---
title: "Message Protocol"
date: 2026-04-23
description: "說明 queue 或 stream message 如何對齊格式與處理語意"
weight: 0
---

Message Protocol 的核心概念是「producer 與 consumer 對訊息格式、處理順序與失敗結果達成一致」。

## 概念位置

Message Protocol 位在 producer、broker 與 consumer 之間。它適用於 queue、stream 與事件傳遞。

## 可觀察訊號

系統需要 message protocol 的訊號是工作離開 request 後仍要被處理，而且需要明確的 schema、重試語意與去重責任。

## 接近真實網路服務的例子

訂單事件、付款事件、通知事件與分析事件都需要 message protocol。消息格式變更時，producer 與 consumer 都要能解讀版本演進。

## 設計責任

Message Protocol 要定義欄位結構、版本相容、錯誤處理與重播安全。它與 queue contract 不同，前者偏向資料交換語意，後者偏向交付保證。
