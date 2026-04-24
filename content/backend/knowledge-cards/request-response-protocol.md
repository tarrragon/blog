---
title: "Request/Response Protocol"
date: 2026-04-23
description: "說明同步請求如何在 client 與 service 之間對齊互動規則"
weight: 0
---

Request/Response Protocol 的核心概念是「client 發出請求，service 回應結果時，雙方如何對齊格式、錯誤與語意」。

## 概念位置

Request/Response Protocol 位在 client、[API Gateway](../api-gateway/)、service 與 RPC layer 之間。它適用於同步互動的請求/回應模型。

## 可觀察訊號

系統需要 request/response protocol 的訊號是呼叫方必須等待結果，且錯誤格式、重試條件與版本相容需要穩定。

## 接近真實網路服務的例子

HTTP API、gRPC method 與內部 RPC call 都屬於 request/response protocol。這類通訊要明確定義 request schema、response schema 與 error shape。

## 設計責任

Request/Response Protocol 要定義欄位名稱、必填欄位、錯誤碼、逾時期待與版本演進方式。它不是討論 transport 細節，而是討論同步互動的約定。
