---
title: "Service Registry"
date: 2026-04-24
description: "說明服務實例如何被註冊、維護與摘除"
weight: 152
---

Service Registry 的核心概念是「保存目前可用服務實例的位址、狀態與 metadata，供 discovery、load balancer 或內部呼叫查找」。

## 概念位置

Service Registry 位在 deployment platform、health check、service discovery 與 load balancing 之間。它負責維持「目前有哪些實例可用」這份資料。

## 可觀察訊號

系統需要 service registry 的訊號是：

- 服務實例會動態擴縮
- instance 需要在啟動後自動登錄
- instance 失效時要自動摘除
- 呼叫端需要依據 metadata 找到合適實例

## 接近真實網路服務的例子

Kubernetes 會把 pod、labels 與 endpoint 維持成可查找狀態；service mesh 會用 registry 資料決定流量要導向哪個 instance；服務縮容時若 registry 沒有及時摘除舊實例，呼叫端就可能打到已下線節點。

## 設計責任

Service Registry 要定義註冊來源、heartbeat 或 TTL、失效摘除條件、metadata 結構與回復方式。它的重點是讓查找方拿到可信且更新的實例資料。

## 英文術語對照
- Service registry
- Instance registry
