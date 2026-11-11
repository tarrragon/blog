---
title: "Provider Adapter"
date: 2026-04-23
description: "說明第三方服務如何被包裝成內部穩定介面"
weight: 1
---

Provider Adapter 的核心概念是「把外部供應商的 API、錯誤與限制，轉成 application 需要的形狀」。 可先對照 [Pub/Sub](/backend/knowledge-cards/pub-sub/)。

## 跟其他概念的關係

Provider Adapter 位在 application 與 payment、notification、storage、identity 等第三方服務之間。 可先對照 [Pub/Sub](/backend/knowledge-cards/pub-sub/)。

## 可觀察訊號

系統需要 provider adapter 的訊號是同一個功能可能切換供應商，或第三方 API 經常變動、錯誤碼不一致、回應格式不穩定。

## 接近真實網路服務的例子

付款 provider adapter、簡訊 provider adapter、email provider adapter 都是 provider adapter 的例子。

## 判斷條件與後果

Provider adapter 是否到位，看業務邏輯是否直接碰到某一家供應商的 API 形狀。外部 API 的差異沒有在 adapter 裡隔離時，業務程式碼直接處理那一家的欄位與呼叫方式，換供應商就要改業務邏輯；錯誤沒有標準化時，每家的錯誤碼各不相同，業務端分不出哪些失敗可以重試、哪些要回報使用者。關聯欄位（供應商端的交易編號或請求編號）沒有保留時，對帳與客訴追查找不回對方系統裡的那一筆紀錄。這三項都在 adapter 內處理時，切換供應商的改動範圍限於 adapter。
