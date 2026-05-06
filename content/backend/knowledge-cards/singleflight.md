---
title: "Singleflight"
date: 2026-04-23
description: "說明相同工作同時發生時如何合併成一次下游請求"
weight: 97
---


Singleflight 的核心概念是「相同 key 的並發工作只讓一個執行者真正打下游，其餘等待同一份結果」。它用來降低 cache miss、重建資料或初始化時的重複下游壓力。 可先對照 [SLI / SLO](/backend/knowledge-cards/sli-slo/)。

## 概念位置

Singleflight 是 cache stampede 與 thundering herd 的防護工具。它適合相同 key、相同結果、短時間內大量重複請求的場景。 可先對照 [SLI / SLO](/backend/knowledge-cards/sli-slo/)。

## 可觀察訊號與例子

系統需要 singleflight 的訊號是熱門 key 過期後，同時有大量 request 查同一筆資料。商品詳情 cache miss 時，只需要一個 request 回資料庫查詢，其他 request 等待同一結果。

## 設計責任

Singleflight 要定義 key、等待 timeout、錯誤分享策略與結果快取方式。若下游查詢失敗，系統要決定所有等待者都失敗，或部分使用 stale data。
