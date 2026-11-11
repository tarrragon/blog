---
title: "Internal Endpoint"
tags: ["內部端點", "Internal Endpoint"]
date: 2026-04-23
description: "說明服務內部通訊入口如何配合網路邊界與服務發現"
weight: 1
---

Internal Endpoint 的核心概念是「只供系統內部服務彼此呼叫的入口」。它不是公開給外部 client 的功能入口。 可先對照 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 跟其他概念的關係

Internal Endpoint 位在 service discovery、internal network、[API Gateway](/backend/knowledge-cards/api-gateway/) 與 application 之間，並可能受到 [Request Routing](/backend/knowledge-cards/request-routing/) 影響。它通常依賴封閉網段、服務身份與內部流量控制。

## 可觀察訊號

系統需要 internal endpoint 的訊號是多個服務之間要交換資料，但不希望這些入口暴露到外部網路。

## 接近真實網路服務的例子

內部訂單同步、跨服務查詢、background worker 呼叫下游系統，或 control plane 對 service 下發設定，都會使用 internal endpoint。

## 判斷條件與後果

Internal Endpoint 只供系統內部服務呼叫，暴露範圍比 public API 更嚴格。內部網路邊界沒有定義清楚時，入口可能從外部網路連得到，原本只給內部服務的資料與操作就對外開放。授權只靠封閉網段、沒有服務身份時，內網裡任何一台被入侵的機器都能呼叫它，原因是網段只證明請求從哪裡來，證明不了是哪一個服務發出的。服務發現沒有定義時，呼叫端寫死位址，下游搬遷或擴容之後呼叫失敗。變更沒有回復策略時，介面改動上線後所有內部呼叫者同時出錯，退回舊版的步驟要在事故中臨時決定。
