---
title: "Release Channel"
date: 2026-05-21
description: "說明 stable、beta、internal 等發行通道如何控制 artifact 接觸到的使用者範圍"
tags: ["CD", "release", "channel", "knowledge-card"]
weight: 21
---

Release Channel 的核心概念是「用通道控制版本接觸範圍」。它是 [Rollout Strategy](/ci/knowledge-cards/rollout-strategy/) 的分發面，常和 [App Signing](/ci/knowledge-cards/app-signing/) 與 update feed 一起設計。

## 概念位置

Release Channel 位在 artifact 發布與使用者取得之間，常見通道包含 internal、alpha、beta、stable、enterprise、nightly 與 rollback channel。

## 可觀察訊號

- 同一產品需要內測、公開測試與正式版本分流。
- 錯誤版本需要停止擴散或切回回復通道。
- 客戶端更新需要依風險分批推進。

## 接近真實服務的例子

桌面 app 先把 signed installer 推到 internal channel，驗證更新成功率後再推 beta channel，最後推 stable channel。若 stable 版本出現 crash，feed 可切回 rollback channel 或暫停更新。

## 設計責任

Release Channel 要定義通道用途、進入條件、artifact 命名、可見範圍、停損條件與回復路徑，讓版本擴散具備控制面。
