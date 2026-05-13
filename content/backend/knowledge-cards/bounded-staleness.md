---
title: "Bounded Staleness"
date: 2026-05-13
description: "允許資料延遲，但把落後上限限制在可量化範圍內的一致性語意"
weight: 247
---

Bounded staleness 的核心概念是「接受資料不是最新，但限定最多落後多少時間或多少版本」。它的責任是把一致性風險轉成可監控的上限，而不是放任不一致無邊界擴大，可搭配 [latency-budget](/backend/knowledge-cards/latency-budget/) 一起設計。

## 概念位置

Bounded staleness 是一致性與延遲取捨的中間層，可搭配 [pacelc](/backend/knowledge-cards/pacelc/) 做設計判讀。它常用在跨區查詢、報表與次要讀路徑，降低全域強一致的延遲成本。

## 可觀察訊號與例子

需要 bounded staleness 的訊號是「使用者可接受短暫延遲，但不能接受長時間舊資料」，例如庫存瀏覽、內容列表、營運看板。若 stale window 超標，通常會觸發告警或降級策略。

## 設計責任

採用 bounded staleness 時，必須定義上限值、量測方法與超標處置。沒有 tripwire 的 stale window 只是口頭承諾，無法支撐 release gate 或事故判讀。
