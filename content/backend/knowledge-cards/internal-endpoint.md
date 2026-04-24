---
title: "Internal Endpoint"
tags: ["內部端點", "Internal Endpoint"]
date: 2026-04-23
description: "說明服務內部通訊入口如何配合網路邊界與服務發現"
weight: 0
---

Internal Endpoint 的核心概念是「只供系統內部服務彼此呼叫的入口」。它不是公開給外部 client 的功能入口。

## 概念位置

Internal Endpoint 位在 service discovery、internal network、[API Gateway](/backend/knowledge-cards/api-gateway/) 與 application 之間，並可能受到 [Request Routing](/backend/knowledge-cards/request-routing/) 影響。它通常依賴封閉網段、服務身份與內部流量控制。

## 可觀察訊號

系統需要 internal endpoint 的訊號是多個服務之間要交換資料，但不希望這些入口暴露到外部網路。

## 接近真實網路服務的例子

內部訂單同步、跨服務查詢、background worker 呼叫下游系統，或 control plane 對 service 下發設定，都會使用 internal endpoint。

## 設計責任

設計時要定義內部網路邊界、授權方式、服務發現與變更時的回復策略。Internal Endpoint 的暴露範圍應比 public API 更嚴格。
