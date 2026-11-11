---
title: "Authentication Middleware"
date: 2026-04-23
description: "說明請求進入 handler 前如何完成身份驗證"
weight: 1
---

Authentication Middleware 的核心概念是「在 request 進入業務處理前，先確認呼叫者是誰」。 可先對照 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 跟其他概念的關係

Authentication Middleware 位在 transport layer 與 handler 之間。它負責把 token、session、signature 或其他存取憑證轉成已驗證的 caller context。 可先對照 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 可觀察訊號

系統需要 authentication middleware 的訊號是多數 handler 都要先確認身份，且驗證規則應集中管理。

## 接近真實網路服務的例子

[API Gateway](/backend/knowledge-cards/api-gateway/) 驗證 bearer token、內部服務驗證 service token、webhook 驗證簽章，都屬於 authentication middleware 的責任範圍。

## 判斷條件與後果

Authentication Middleware 把憑證提取、驗證失敗回應、context 寫入與錯誤分類集中在 handler 之前時，每個 handler 拿到的都是同一套規則驗過的 caller context。憑證提取散在各個 handler 時，同一種 token 有好幾種解析寫法，其中一種寫錯就是一個繞過驗證的入口；驗證結果沒有寫進 context 時，下游要再驗一次；錯誤沒有分類時，憑證過期、簽章錯誤與驗證服務本身失效混成同一種失敗，呼叫端與監控都分不出是哪一種。middleware 混入業務邏輯時，改業務規則要動到驗證這一層，每一次業務改動都可能改壞驗證。
