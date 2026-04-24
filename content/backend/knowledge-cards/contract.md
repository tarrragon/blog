---
title: "Boundary Contract"
date: 2026-04-23
description: "說明跨邊界約定如何維持相容與可驗證"
weight: 0
---

Boundary Contract 的核心概念是「邊界兩端共同承認的約定」。它描述不同系統、元件或流程在互相協作時，需要遵守的共同規則。

## 概念位置

Boundary Contract 位在 client 與 service、service 與 service、程式與平台之間。當兩端都需要依同一份規則運作時，就需要 contract 來避免含糊地帶。

## 可觀察訊號

系統需要 boundary contract 的訊號包括：不同團隊共同整合、版本需要相容、欄位變更可能影響下游、健康檢查與接流量條件要明確。

## 接近真實網路服務的例子

API contract 會定義欄位名稱、必要欄位、錯誤格式與相容版本；deployment contract 會定義 readiness、shutdown、[draining](../draining/) 與 [resource limit](../resource-limit/)；queue contract 會定義 ack、重試與重複投遞行為；load balancer contract 會定義流量切換、[health check](../health-check/) 與排空行為。

## 設計責任

Boundary Contract 設計要清楚定義版本、相容性、破壞性變更、驗證方式與回復流程。若 contract 不穩，應搭配 contract test、[Release Gate](../release-gate/) 與文件化規則。
