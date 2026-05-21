---
title: "Update Feed"
date: 2026-05-21
description: "說明桌面與客戶端應用如何透過更新來源取得已簽章版本與回復路徑"
tags: ["CD", "desktop", "update", "knowledge-card"]
weight: 22
---

Update Feed 的核心概念是「告訴已安裝客戶端該取得哪個版本」。它連接 [Release Channel](/ci/knowledge-cards/release-channel/) 與 [App Signing](/ci/knowledge-cards/app-signing/)，讓自動更新具備信任與回復能力。

## 概念位置

Update Feed 位在 signed artifact、release channel 與已安裝 app 之間，常包含版本號、下載 URL、signature、checksum、release notes 與最低支援版本。

## 可觀察訊號

- 客戶端需要自動偵測新版本。
- beta 與 stable 使用者需要看到不同版本。
- 錯誤版本需要從更新來源撤下。

## 接近真實服務的例子

Electron app 啟動時讀取 stable feed，取得最新 signed installer 與 signature。若新版本 crash rate 升高，團隊先撤下 feed 指向，讓未更新使用者停止取得錯誤版本。

## 設計責任

Update Feed 要定義簽章驗證、channel 分流、版本比較、fallback installer、撤版策略與 telemetry，讓已安裝客戶端安全升級。
