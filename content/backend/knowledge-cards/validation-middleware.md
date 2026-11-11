---
title: "Validation Middleware"
date: 2026-04-23
description: "說明請求進入 handler 前如何完成共通驗證"
weight: 1
---

Validation Middleware 的核心概念是「在 request 進入業務處理前，先確認輸入格式與基本條件」。 可先對照 [WAF](/backend/knowledge-cards/waf/)。

## 跟其他概念的關係

Validation Middleware 位在 transport layer 與 handler 之間。它負責共通輸入驗證，而不是 domain 規則本身。 可先對照 [WAF](/backend/knowledge-cards/waf/)。

## 可觀察訊號

系統需要 validation middleware 的訊號是很多 handler 都要重複檢查格式、必要欄位或基本範圍。

## 接近真實網路服務的例子

JSON schema 檢查、header 驗證、基本參數完整性與 payload shape 檢查，都適合放在 validation middleware。

## 判斷條件與後果

Validation Middleware 處理的是不需要業務狀態就判得出無效的輸入。格式錯、缺必要欄位、超出基本範圍的 request 在進入 handler 之前被拒絕時，各個 handler 不必重複同樣的檢查，業務處理也不會為注定失敗的 request 開交易或呼叫下游。輸入錯誤與 domain 錯誤分開回報時，client 從錯誤碼就分得出該修正請求內容，還是請求合法而業務狀態不允許；兩種錯誤用同一種回應時，client 只知道失敗，不知道該改請求還是換時機再送。
