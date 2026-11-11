---
title: "Feature Flag"
tags: ["功能旗標", "Feature Flag"]
date: 2026-04-23
description: "說明如何用可動態開關控制功能曝光與風險"
weight: 155
---

Feature flag 的核心概念是「把功能啟用控制與部署分離」。它可用於灰度發布、A/B 測試與緊急關閉。可先對照 [Dark Launch](/backend/knowledge-cards/dark-launch/) 與 [Remote Config](/backend/knowledge-cards/remote-config/)。

## 跟其他概念的關係

常出現在高風險功能、實驗功能與跨租戶差異化控制。旗標的值放在伺服器端時由服務實例讀取（見 [Runtime Config](/backend/knowledge-cards/runtime-config/)）；放在行動 App 讀取的 [Remote Config](/backend/knowledge-cards/remote-config/) 時，會被多個 App 版本讀到，生效要等裝置下一次讀取。

## 判斷條件與後果

Feature flag 的判斷條件是旗標在什麼狀態下可以移除，以及讀不到設定時程式怎麼走。沒有清理節點的旗標在功能全量開啟之後仍留在程式裡，兩條分支都要維護與測試，旗標越堆越多時，開關的組合越難推算；沒有預設值與回退策略時，設定來源讀不到的那一刻，程式走哪一條分支無法預期。行動 App 讀取的旗標多兩個條件，原因是多個 App 版本同時讀同一份 [Remote Config](/backend/knowledge-cards/remote-config/)：讀不到設定時用 App 內建的預設值（預設關閉），功能還沒準備好的版本不會被打開；開啟條件依 App 版本設定，還沒有這段程式的舊版本不會收到開啟。收斂為開啟的旗標，遠端定義一刪掉，仍在讀它的版本就退回內建的預設值（關閉），功能在那些使用者手上消失；所以移除的順序是先發一版不再讀它、行為寫死為開啟的 App，等最後一個讀它的版本低於最低支援版本，才刪掉遠端定義，見 [11.15 自家行動 App 與後端的 API 契約：版本回報、最低支援版本、商店審核下的上線順序、分階段發布、熱更新與回退手段](/backend/11-api-design/mobile-client-api-contract/) 的〈功能提前內建與上線日遠端啟用〉。
