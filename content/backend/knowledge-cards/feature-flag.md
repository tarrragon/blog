---
title: "Feature Flag"
tags: ["功能旗標", "Feature Flag"]
date: 2026-04-23
description: "說明如何用可動態開關控制功能曝光與風險"
weight: 155
---


Feature flag 的核心概念是「把功能啟用控制與部署分離」。它可用於灰度發布、A/B 測試與緊急關閉。可先對照 [Dark Launch](/backend/knowledge-cards/dark-launch/) 與 [Remote Config](/backend/knowledge-cards/remote-config/)。

## 概念位置

常出現在高風險功能、實驗功能與跨租戶差異化控制。旗標的值放在伺服器端時由服務實例讀取（見 [Runtime Config](/backend/knowledge-cards/runtime-config/)）；放在行動 App 讀取的 [Remote Config](/backend/knowledge-cards/remote-config/) 時，會被多個 App 版本讀到，生效要等裝置下一次讀取。

## 設計責任

設計時要定義旗標生命週期、預設值、回退策略與清理節點，避免旗標長期堆積。行動 App 讀取的旗標另有兩件事：讀不到設定時用 App 內建的預設值（預設關閉），以及依 App 版本設開啟條件；收斂為開啟的旗標，移除時要先發一版不再讀它、行為寫死為開啟的 App，再等最後一個讀它的版本低於最低支援版本，才刪掉遠端定義，見 [11.15 自家行動 App 與後端的 API 契約：版本回報、最低支援版本、商店審核下的上線順序、分階段發布、熱更新與回退手段](/backend/11-api-design/mobile-client-api-contract/) 的〈功能提前內建與上線日遠端啟用〉。
