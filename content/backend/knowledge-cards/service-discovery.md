---
title: "Service Discovery"
date: 2026-04-23
description: "說明服務實例如何被註冊、查找與路由"
weight: 151
---

Service discovery 的核心概念是「讓呼叫端能找到目前可用的服務實例」。它支援擴容、滾動更新與故障切換。

## 概念位置

常與 load balancer、健康檢查與部署平台整合，決定流量如何導向健康節點。

## 設計責任

設計時要定義註冊條件、失效摘除條件與回復條件，避免流量導向未準備好的實例。

