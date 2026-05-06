---
title: "Provider Adapter"
date: 2026-04-23
description: "說明第三方服務如何被包裝成內部穩定介面"
weight: 0
---


Provider Adapter 的核心概念是「把外部供應商的 API、錯誤與限制，轉成 application 需要的形狀」。 可先對照 [Pub/Sub](/backend/knowledge-cards/pub-sub/)。

## 概念位置

Provider Adapter 位在 application 與 payment、notification、storage、identity 等第三方服務之間。 可先對照 [Pub/Sub](/backend/knowledge-cards/pub-sub/)。

## 可觀察訊號

系統需要 provider adapter 的訊號是同一個功能可能切換供應商，或第三方 API 經常變動、錯誤碼不一致、回應格式不穩定。

## 接近真實網路服務的例子

付款 provider adapter、簡訊 provider adapter、email provider adapter 都是 provider adapter 的例子。

## 設計責任

Provider Adapter 要隔離外部 API 差異、標準化錯誤、保留關聯欄位，並確保供應商更換不會直接擾動業務邏輯。
