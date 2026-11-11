---
title: "Service Registry"
tags: ["服務註冊", "Service Registry"]
date: 2026-04-24
description: "說明服務實例如何被註冊、維護與摘除"
weight: 153
---

Service Registry 的核心概念是「保存目前可用服務實例的位址、狀態與 metadata，供 discovery、load balancer 或內部呼叫查找」。 可先對照 [Session Invalidation](/backend/knowledge-cards/session-invalidation/)。

## 跟其他概念的關係

Service Registry 位在 deployment platform、health check、service discovery 與 load balancing 之間。它負責維持「目前有哪些實例可用」這份資料。 可先對照 [Session Invalidation](/backend/knowledge-cards/session-invalidation/)。

## 可觀察訊號

系統需要 service registry 的訊號是：

- 服務實例會動態擴縮
- instance 需要在啟動後自動登錄
- instance 失效時要自動摘除
- 呼叫端需要依據 metadata 找到合適實例

## 接近真實網路服務的例子

Kubernetes 會把 pod、labels 與 endpoint 維持成可查找狀態；service mesh 會用 registry 資料決定流量要導向哪個 instance；服務縮容時若 registry 沒有及時摘除舊實例，呼叫端就可能打到已下線節點。

## 判斷條件與後果

查找方拿到的實例資料是否可信，取決於實例怎麼登錄、怎麼被判定失效、怎麼被摘除與回復。註冊來源不明確時（實例自己登錄，或部署平台代為登錄），同一個實例可能被登錄兩次或漏登錄；沒有 heartbeat 或 TTL 時，registry 得不到實例停止回應的訊號，縮容或故障後的舊實例留在清單上，呼叫端連到已下線的節點；heartbeat 間隔或 TTL 設得長時，失效到摘除之間的延遲跟著變長，這段時間的請求送往已失效的實例；metadata 結構沒有約定時，呼叫端依 metadata（版本、區域）挑實例的條件對不上實際的欄位；沒有回復方式時，恢復健康的實例一直停在摘除狀態。
