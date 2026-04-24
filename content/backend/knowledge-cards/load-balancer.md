---
title: "Load Balancer"
tags: ["負載平衡器", "Load Balancer"]
date: 2026-04-23
description: "說明流量如何分散、排空與導向健康節點"
weight: 129
---

Load balancer 的核心概念是「把進來的流量導到合適的服務實例」。它常處理分流、健康檢查、[draining](draining/)、[sticky session](sticky-session/) 與 [idle timeout](idle-timeout/)。

## 概念位置

Load balancer 位在 client 與 application instances 之間，是服務接流量與停止接流量的入口控制層，常與 [Request Routing](request-routing/) 搭配使用。

## 可觀察訊號

系統需要 load balancer 的訊號是服務有多個 instance、要做 rolling update、需要平滑擴容，或必須在故障時把流量移開。

## 接近真實網路服務的例子

Kubernetes service、edge proxy、[API Gateway](api-gateway/) 或雲端 LB 都會把 request 導到健康節點。長連線服務也常依賴 load balancer 做 [draining](draining/)，避免關閉中的 instance 繼續接新流量，也會透過 [idle timeout](idle-timeout/) 回收空閒連線。

## 設計責任

設計時要定義健康條件、移除條件、回切條件與排空時間。Load balancer 本身不處理業務邏輯，但它直接影響可用性、切換速度與連線體驗。

