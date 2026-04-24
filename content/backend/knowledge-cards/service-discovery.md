---
title: "Service Discovery"
tags: ["服務發現", "Service Discovery"]
date: 2026-04-23
description: "說明服務實例如何被查找與路由"
weight: 151
---

Service discovery 的核心概念是「讓呼叫端根據 registry 或 DNS 找到目前可用的服務實例」。它支援擴容、滾動更新與故障切換。

## 概念位置

常與 [Service Registry](/backend/knowledge-cards/service-registry/)、load balancer、健康檢查與部署平台整合，決定流量如何導向健康節點。

## 設計責任

設計時要定義查找條件、轉譯規則與回復條件，避免流量導向未準備好的實例。
