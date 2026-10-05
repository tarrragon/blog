---
title: "Remote Config（遠端設定）"
date: 2026-10-05
description: "要讓已安裝的行動 App 不經更新就改變行為時：設定值由裝置向服務方讀取、有讀取間隔與快取、讀不到時用內建預設值、同一個值會被多個 App 版本讀到"
weight: 449
tags: ["backend", "mobile", "release", "knowledge-card"]
---

Remote Config（遠端設定）的核心概念是「已安裝的 App 向服務方讀取一組設定值，服務方改了值，App 不必更新就能讀到」。它是行動 App 在不經商店審核的前提下改變行為的主要通道，常見的產品是 Firebase Remote Config。可先對照 [Feature Flag](/backend/knowledge-cards/feature-flag/) 與 [Runtime Config](/backend/knowledge-cards/runtime-config/)。

## 概念位置

遠端設定和伺服器端的設定管理是兩件事。[Runtime Config](/backend/knowledge-cards/runtime-config/) 與 [Config Rollout](/backend/knowledge-cards/config-rollout/) 管的是服務實例怎麼讀取設定、新設定怎麼下發到運作中的實例，持有設定的是服務方自己的機器；遠端設定的持有者是使用者的裝置，服務方改值之後，要等每一台裝置下一次讀取並套用才生效。[Feature Flag](/backend/knowledge-cards/feature-flag/) 是放在遠端設定裡最常見的一種值，[Minimum Supported Version](/backend/knowledge-cards/minimum-supported-version/) 是另一種。

## 可觀察訊號與例子

遠端設定有三個伺服器端設定沒有的性質，設計時各自要處理：

- **讀取間隔與快取**：App 不會每次用到設定都向服務方讀。Firebase Remote Config 預設 12 小時才重新抓一次，要更快就整合即時更新的監聽，或縮短間隔（縮短會碰到服務方的節流）。關掉一個出問題的功能能多快生效，取決於這個間隔。
- **內建預設值**：離線或第一次啟動讀不到設定時，App 用打包在安裝檔裡的預設值。預設值的方向要依那個值的用途決定：功能開關預設關閉，最低支援版本預設不擋任何已上架版本（取捨見 [Fail-Safe Default](/ux-design/knowledge-cards/fail-safe-default/)）。
- **多個版本讀同一個值**：線上同時有好幾個 App 版本讀同一個值。開啟時依 App 版本設條件，只對實作完整、沒有已知問題的版本開啟（先前的版本可能帶著不完整的實作，值的名稱日後也可能被重用）。收斂為開啟的開關，移除要分兩步：先發一版不再讀它、行為寫死為開啟的 App，再等最後一個讀它的版本低於最低支援版本，才刪掉遠端定義；提早刪掉時，仍讀它的版本會改用內建預設值。

完整推導見 [11.15 自家行動 App 與後端的 API 契約：版本回報、最低支援版本、商店審核下的上線順序、分階段發布、熱更新與回退手段](/backend/11-api-design/mobile-client-api-contract/)。

## 設計責任

遠端設定的值不是祕密：設定服務的讀取憑證打包在 App 裡，被改過的客戶端也能自己改值，所以它只能控制畫面與行為，權限檢查要放在後端。每個值要寫明用途、預設值方向、依 App 版本的開啟條件與移除時機；讀取間隔要短到出問題時關得掉功能，或整合即時更新。
