---
title: "Diagnostic Endpoint"
tags: ["診斷端點", "Diagnostic Endpoint"]
date: 2026-04-23
description: "說明健康檢查、診斷與調試入口如何控制暴露面"
weight: 1
---

Diagnostic Endpoint 的核心概念是「讓平台或工程師查詢服務狀態，但不暴露業務資料」。它包含 [health check](/backend/knowledge-cards/health-check/)、readiness、metrics snapshot、debug info 等入口。

## 跟其他概念的關係

Diagnostic Endpoint 位在運維系統、負載平衡器、監控工具與 application 之間。它通常不承擔產品功能，而是承擔操作判斷。 可先對照 [Health Check](/backend/knowledge-cards/health-check/)。

## 可觀察訊號

系統需要 diagnostic endpoint 的訊號是平台要判斷服務是否可接流量，或工程師需要快速確認特定狀態，但不想翻 log。

## 接近真實網路服務的例子

[health check](/backend/knowledge-cards/health-check/)、readiness 檢查、liveness 檢查、debug status、版本資訊與依賴健康狀態，都可能透過 diagnostic endpoint 暴露。

## 判斷條件與後果

Diagnostic Endpoint 的風險由它回傳的資訊範圍與它跟 public API 的距離決定。回傳內容包含設定值、連線字串或內部位址時，呼叫得到這個 endpoint 的人就拿得到攻擊需要的資訊，原因是負載平衡器與監控工具要能直接呼叫它，它的存取限制常比業務 API 寬。它跟 public API 共用路由與授權時，產品功能的改動會改到平台判斷所依賴的回應，或把診斷資訊經由 public API 開放出去。它服務的是平台的自動判斷（是否可以接流量、是否要重啟），回應的格式與判斷依據要穩定；為了人工排障方便而加進來的細節讓回應變大、暴露的資訊變多，所以回傳內容只留平台判斷用得到的狀態。
