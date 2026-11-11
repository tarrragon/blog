---
title: "Service Discovery"
tags: ["服務發現", "Service Discovery"]
date: 2026-04-23
description: "說明服務實例如何被查找與路由"
weight: 152
---

Service discovery 的核心概念是「讓呼叫端根據 registry 或 DNS 找到目前可用的服務實例」。它支援擴容、滾動更新與故障切換。 可先對照 [Service Registry](/backend/knowledge-cards/service-registry/)。Prometheus 以服務發現找讀取對象時，發現給的標籤在讀取之前以 [Relabeling](/backend/knowledge-cards/relabeling/) 改寫。

## 跟其他概念的關係

常與 [Service Registry](/backend/knowledge-cards/service-registry/)、load balancer、健康檢查與部署平台整合，決定流量如何導向健康節點。

## 判斷條件與後果

Service discovery 回給呼叫端的實例清單決定流量送到哪些節點，清單收哪些實例、多久更新，由查找條件、轉譯規則與回復條件決定。查找條件只看實例是否登錄、不看健康檢查結果時，剛啟動還沒準備好或正在下線的實例也在清單裡，送到它們的請求失敗或逾時；轉譯規則（服務名稱轉成位址的方式，例如 DNS 記錄）的結果被呼叫端快取太久時，實例替換之後呼叫端仍連往舊位址；沒有回復條件時，一度被移出清單的實例恢復健康也回不到清單，可用容量隨每一次故障減少。
