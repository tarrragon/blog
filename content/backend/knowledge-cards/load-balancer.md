---
title: "Load Balancer"
tags: ["負載平衡器", "Load Balancer"]
date: 2026-04-23
description: "說明流量如何分散、排空與導向健康節點"
weight: 130
---

Load balancer 的核心概念是「把進來的流量導到合適的服務實例」。它常處理分流、健康檢查、[draining](/backend/knowledge-cards/draining/)、[sticky session](/backend/knowledge-cards/sticky-session/) 與 [idle timeout](/backend/knowledge-cards/idle-timeout/)。

## 跟其他概念的關係

Load balancer 位在 client 與 application instances 之間，是服務接流量與停止接流量的入口控制層，常與 [Request Routing](/backend/knowledge-cards/request-routing/) 搭配使用。

## 可觀察訊號

系統需要 load balancer 的訊號是服務有多個 instance、要做 rolling update、需要平滑擴容，或必須在故障時把流量移開。

## 接近真實網路服務的例子

[Kubernetes Service](/backend/knowledge-cards/kubernetes-service/)、edge proxy、[API Gateway](/backend/knowledge-cards/api-gateway/) 或雲端 LB 都會把 request 導到健康節點。長連線服務也常依賴 load balancer 做 [draining](/backend/knowledge-cards/draining/)，避免關閉中的 instance 繼續接新流量，也會透過 [idle timeout](/backend/knowledge-cards/idle-timeout/) 回收空閒連線。

## 判斷條件與後果

Load balancer 不處理業務邏輯，它對可用性、切換速度與連線體驗的影響來自四個判斷：健康條件、移除條件、回切條件與排空時間。健康條件太寬時，已經處理不了請求的 instance 仍在流量池裡，送到它的請求失敗；移除條件太敏感時，一次抖動就把 instance 移出，剩下的 instance 分攤多出來的流量。回切條件沒有定義時，剛恢復的 instance 立刻收到全量流量，可能再次失敗，在移除與回切之間來回。排空時間太短時，長連線服務的 instance 關閉時連線被切斷，使用者看到的是斷線。
