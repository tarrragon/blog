---
title: "Singleflight"
date: 2026-04-23
description: "說明相同工作同時發生時如何合併成一次下游請求"
weight: 98
---

Singleflight 的核心概念是「相同 key 的並發工作只讓一個執行者真正打下游，其餘等待同一份結果」。它用來降低 cache miss、重建資料或初始化時的重複下游壓力。 可先對照 [SLI / SLO](/backend/knowledge-cards/sli-slo/)。

## 跟其他概念的關係

Singleflight 是 cache stampede 與 thundering herd 的防護工具。它適合相同 key、相同結果、短時間內大量重複請求的場景。 可先對照 [SLI / SLO](/backend/knowledge-cards/sli-slo/)。

## 可觀察訊號與例子

系統需要 singleflight 的訊號是熱門 key 過期後，同時有大量 request 查同一筆資料。商品詳情 cache miss 時，只需要一個 request 回資料庫查詢，其他 request 等待同一結果。

## 判斷條件與後果

Singleflight 讓同一個 key 的等待者共用一次下游呼叫的結果，key 怎麼定、等多久、失敗怎麼分享，決定被合併的是否為同一件工作，以及一次失敗波及多少請求。Key 的範圍比結果的差異寬時（結果隨使用者權限不同，key 卻只用商品 ID），等待者拿到的是別人那一份結果；等待者沒有 timeout 時，執行者的下游呼叫遲遲沒有回應，所有等待者跟著等，沒有上限；下游查詢失敗而錯誤分享給所有等待者時，一次失敗變成整批請求失敗，改成讓等待者使用 stale data 時，這批請求拿到過期而可用的結果；結果沒有短時間快取時，執行者一完成，下一波相同 key 的請求又觸發一次下游呼叫。
