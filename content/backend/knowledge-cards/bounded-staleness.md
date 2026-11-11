---
title: "Bounded Staleness"
date: 2026-05-13
description: "允許資料延遲，但把落後上限限制在可量化範圍內的一致性語意"
weight: 248
---

Bounded staleness 的核心概念是「接受資料不是最新，但限定最多落後多少時間或多少版本」。它的責任是把一致性風險轉成可監控的上限，而不是放任不一致無邊界擴大，可搭配 [latency-budget](/backend/knowledge-cards/latency-budget/) 一起設計。

## 跟其他概念的關係

Bounded staleness 是一致性與延遲取捨的中間層，可搭配 [pacelc](/backend/knowledge-cards/pacelc/) 做設計判讀。它常用在跨區查詢、報表與次要讀路徑，降低全域強一致的延遲成本。

## 可觀察訊號與例子

需要 bounded staleness 的訊號是「使用者可接受短暫延遲，但不能接受長時間舊資料」，例如庫存瀏覽、內容列表、營運看板。若 stale window 超標，通常會觸發告警或降級策略。

## 判斷條件與後果

Bounded staleness 的上限要有上限值、量測方法與超標處置三件事才檢查得了。沒有量測方法時，沒有人知道 stale window 目前多大；沒有超標處置時，量到超標也沒有告警或降級接手，舊資料照樣回給使用者。缺其中任何一件，stale window 都是沒有 tripwire 的口頭承諾，不能當成 release gate 或事故判讀的依據，原因是兩者都要拿實際落後量去比對上限。
