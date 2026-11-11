---
title: "Bulkhead"
date: 2026-04-23
description: "說明 bulkhead 如何用資源分艙限制故障擴散"
weight: 56
---

Bulkhead 的核心概念是「把服務資源分成彼此隔離的艙室」。某個艙室過載或失效時，其他艙室仍保留處理能力。 可先對照 [Burn Rate](/backend/knowledge-cards/burn-rate/)。

## 跟其他概念的關係

Bulkhead 是 dependency isolation 的具體模式。它常用在 thread pool、connection pool、queue、worker group、tenant capacity 與不同優先級工作。 可先對照 [Burn Rate](/backend/knowledge-cards/burn-rate/)。

## 可觀察訊號與例子

系統需要 bulkhead 的訊號是單一功能或 tenant 可以拖垮整體服務。大量報表匯出可以放到獨立 worker pool，避免它佔滿處理登入、查詢與付款的資源。

## 判斷條件與後果

分艙邊界決定哪些工作會互相影響：報表匯出和登入、付款共用同一個 worker pool 時，大量匯出佔滿 worker，登入與付款跟著排隊；匯出切成獨立的艙室時，它只耗盡自己那一艙。容量切得太細時，每一艙平時都留著閒置的資源，整體利用率下降；切得太粗時，同一艙裡仍有會互相拖慢的工作，隔離失去效果。艙室滿了之後，排隊策略與拒絕行為決定過載怎麼呈現：不設上限的排隊把那一艙的延遲傳到使用者端，明確拒絕讓呼叫端立刻收到錯誤並改走降級路徑。沒有告警時，某一艙長期滿載要等使用者回報變慢才被發現。
