---
title: "Public API Endpoint"
date: 2026-04-23
description: "說明面向外部 client 的穩定 API 入口如何被管理"
weight: 1
---

Public API Endpoint 的核心概念是「外部 client 直接呼叫服務時，所經過的穩定入口」。它承載產品功能對外的 request / response 邊界。 可先對照 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 跟其他概念的關係

Public API Endpoint 位在 client、[API Gateway](/backend/knowledge-cards/api-gateway/)、[Request Routing](/backend/knowledge-cards/request-routing/) 與 load balancer 之間。它通常是最需要版本穩定、文件清楚與錯誤回應一致的入口。

## 可觀察訊號

系統需要 public API endpoint 的訊號是產品功能要直接暴露給使用者、合作夥伴或 SDK，且需要清楚的授權、節流與回應格式。

## 接近真實網路服務的例子

查詢訂單、建立付款、更新會員資料或取得 dashboard 資料，通常都會暴露成 public API endpoint，並搭配 authentication、authorization 與 rate limit。

## 判斷條件與後果

Public API endpoint 的呼叫端是服務方控制不了更新時程的外部 client、合作夥伴與 SDK。request / response contract 或版本相容被改動時，已經發出去的 client 仍照舊格式呼叫，請求失敗；錯誤碼改變時，client 依錯誤碼寫的重試與提示邏輯判錯。觀測欄位在各 endpoint 之間不一致時，跨 endpoint 比較錯誤率要逐一換算欄位。管理操作或內部調試功能混進這個入口時，它們跟著對外暴露，[attack surface](/backend/knowledge-cards/attack-surface/) 擴大到原本只給內部使用的功能，所以這類操作放在另外的入口。
