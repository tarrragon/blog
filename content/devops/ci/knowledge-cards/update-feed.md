---
title: "Update Feed"
date: 2026-05-21
description: "說明桌面與客戶端應用如何透過更新來源取得已簽章版本與回復路徑"
tags: ["CD", "desktop", "update", "knowledge-card"]
weight: 22
aliases: ["/ci/knowledge-cards/update-feed/"]
---

Update Feed 的核心概念是「告訴已安裝客戶端該取得哪個版本」。它連接 [Release Channel](/devops/ci/knowledge-cards/release-channel/) 與 [App Signing](/devops/ci/knowledge-cards/app-signing/)，讓自動更新具備信任與回復能力。

## 跟其他概念的關係

Update Feed 位在 signed [artifact](/devops/ci/knowledge-cards/artifact/)、release channel 與已安裝 app 之間，常包含版本號、下載 URL、signature、checksum、release notes 與[最低支援版本](/backend/knowledge-cards/minimum-supported-version/)。

## 可觀察訊號

- 客戶端需要自動偵測新版本。
- beta 與 stable 使用者需要看到不同版本。
- 錯誤版本需要從更新來源撤下。

## 接近真實服務的例子

Electron app 啟動時讀取 stable feed，取得最新 signed installer 與 signature。若新版本 crash rate 升高，團隊先撤下 feed 指向，讓未更新使用者停止取得錯誤版本。

## 判斷條件與後果

Update Feed 指向的版本會被已安裝的客戶端自動下載並執行，所以 feed 的設定決定錯誤或被竄改的版本是否會到達使用者：

- **簽章驗證**：客戶端不驗 signature 與 checksum 時，能改動 feed 或下載 URL 的人就能讓客戶端安裝任意程式。
- **channel 分流**：beta 與 stable 讀同一個 feed 時，beta 版本直接推給所有使用者。
- **撤版與 telemetry**：沒有 crash rate 這類回報時，團隊不知道哪個版本該撤；feed 沒有撤版的方式時，錯誤版本持續被還沒更新的使用者取得。
