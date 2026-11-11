---
title: "Request/Response Protocol"
date: 2026-04-23
description: "說明同步請求如何在 client 與 service 之間對齊互動規則"
weight: 1
---

Request/Response Protocol 的核心概念是「client 發出請求，service 回應結果時，雙方如何對齊格式、錯誤與語意」。 可先對照 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 跟其他概念的關係

Request/Response Protocol 位在 client、[API Gateway](/backend/knowledge-cards/api-gateway/)、service 與 RPC layer 之間。它適用於同步互動的請求/回應模型。

## 可觀察訊號

系統需要 request/response protocol 的訊號是呼叫方必須等待結果，且錯誤格式、重試條件與版本相容需要穩定。

## 接近真實網路服務的例子

HTTP API、gRPC method 與內部 RPC call 都屬於 request/response protocol。這類通訊要明確定義 request schema、response schema 與 error shape。

## 判斷條件與後果

Request/Response Protocol 的判斷對象是呼叫方能否只靠約定處理每一種回應。錯誤碼沒有約定時，呼叫方分不出哪些失敗可以重試、哪些要回報使用者；逾時期待沒有約定時，呼叫方的 timeout 可能比 service 的處理時間短，請求在 service 端完成了，呼叫方卻當成失敗；欄位名稱、必填欄位與版本演進方式沒有約定時，新增或改名欄位會讓還沒升級的呼叫方解析失敗。這些都是同步互動的約定，連線與傳輸的細節由 transport 層處理。
