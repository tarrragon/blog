---
title: "Validation Middleware"
date: 2026-04-23
description: "說明請求進入 handler 前如何完成共通驗證"
weight: 0
---

Validation Middleware 的核心概念是「在 request 進入業務處理前，先確認輸入格式與基本條件」。

## 概念位置

Validation Middleware 位在 transport layer 與 handler 之間。它負責共通輸入驗證，而不是 domain 規則本身。

## 可觀察訊號

系統需要 validation middleware 的訊號是很多 handler 都要重複檢查格式、必要欄位或基本範圍。

## 接近真實網路服務的例子

JSON schema 檢查、header 驗證、基本參數完整性與 payload shape 檢查，都適合放在 validation middleware。

## 設計責任

Validation Middleware 要快速拒絕明顯無效的 request，並把輸入錯誤與 domain 錯誤區分開。
