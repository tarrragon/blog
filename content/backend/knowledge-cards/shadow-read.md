---
title: "Shadow Read"
date: 2026-04-23
description: "說明正式讀取仍走舊路徑時如何暗中讀新路徑比對結果"
weight: 85
---

Shadow read 的核心概念是「正式結果仍使用舊路徑，同時暗中讀新路徑做比對」。它讓團隊在 cutover 前驗證新系統的正確性與延遲。 可先對照 [Migration Gate](/backend/knowledge-cards/migration-gate/)。

## 跟其他概念的關係

Shadow read 是 migration 與服務替換的驗證工具。它能在不影響使用者結果的前提下收集新舊差異，但會增加下游流量與資料存取成本。 可先對照 [Migration Gate](/backend/knowledge-cards/migration-gate/)。

## 可觀察訊號與例子

系統需要 shadow read 的訊號是新讀取路徑即將接正式流量。搜尋服務換新索引前，可以用正式查詢同時查新索引，記錄結果差異但仍回傳舊索引結果。

## 判斷條件與後果

Shadow read 讓正式請求額外讀一次新路徑，它的成本與能提供的證據隨採樣率、timeout、資料遮罩與差異記錄的設定變動。採樣率是全量時，新路徑承受跟正式路徑相同的讀取量，下游流量與資料存取成本大約多出一倍；shadow 呼叫沒有 timeout、或跟正式路徑共用同一條執行流程時，新路徑變慢就拖慢正式請求，失去「不影響使用者結果」的前提；差異記錄寫進含個資的 request 與 response 而沒有遮罩時，比對紀錄本身成為一份新的敏感資料副本；差異只散在 log、沒有彙整進 correctness dashboard 時，cutover 前拿不出一個可判讀的差異率，[Migration Gate](/backend/knowledge-cards/migration-gate/) 沒有判斷的依據。
