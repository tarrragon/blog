---
title: "Authentication Middleware"
date: 2026-04-23
description: "說明請求進入 handler 前如何完成身份驗證"
weight: 0
---

Authentication Middleware 的核心概念是「在 request 進入業務處理前，先確認呼叫者是誰」。

## 概念位置

Authentication Middleware 位在 transport layer 與 handler 之間。它負責把 token、session、signature 或其他身份憑證轉成已驗證的 caller context。

## 可觀察訊號

系統需要 authentication middleware 的訊號是多數 handler 都要先確認身份，且驗證規則應集中管理。

## 接近真實網路服務的例子

[API Gateway](api-gateway/) 驗證 bearer token、內部服務驗證 service token、webhook 驗證簽章，都屬於 authentication middleware 的責任範圍。

## 設計責任

Authentication Middleware 要處理憑證提取、驗證失敗回應、context 寫入與錯誤分類，不應混入業務邏輯。
