---
title: "Public API Endpoint"
date: 2026-04-23
description: "說明面向外部 client 的穩定 API 入口如何被管理"
weight: 0
---

Public API Endpoint 的核心概念是「外部 client 直接呼叫服務時，所經過的穩定入口」。它承載產品功能對外的 request / response 邊界。

## 概念位置

Public API Endpoint 位在 client、[API Gateway](/backend/knowledge-cards/api-gateway/)、[Request Routing](/backend/knowledge-cards/request-routing/) 與 load balancer 之間。它通常是最需要版本穩定、文件清楚與錯誤回應一致的入口。

## 可觀察訊號

系統需要 public API endpoint 的訊號是產品功能要直接暴露給使用者、合作夥伴或 SDK，且需要清楚的授權、節流與回應格式。

## 接近真實網路服務的例子

查詢訂單、建立付款、更新會員資料或取得 dashboard 資料，通常都會暴露成 public API endpoint，並搭配 authentication、authorization 與 rate limit。

## 設計責任

設計時要維持 request / response contract、版本相容、錯誤碼穩定與觀測欄位一致。Public API Endpoint 不應混入管理操作或內部調試責任。
