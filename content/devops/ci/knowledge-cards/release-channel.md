---
title: "Release Channel"
date: 2026-05-21
description: "說明 stable、beta、internal 等發行通道如何控制 artifact 接觸到的使用者範圍"
tags: ["CD", "release", "channel", "knowledge-card"]
weight: 21
aliases: ["/ci/knowledge-cards/release-channel/"]
---

Release Channel 的核心概念是「用通道控制版本接觸範圍」。它是 [Rollout Strategy](/devops/ci/knowledge-cards/rollout-strategy/) 的分發面，常和 [App Signing](/devops/ci/knowledge-cards/app-signing/) 與 update feed 一起設計。

## 跟其他概念的關係

Release Channel 位在 [artifact](/devops/ci/knowledge-cards/artifact/) 發布與使用者取得之間，常見通道包含 internal、alpha、beta、stable、enterprise、nightly 與 rollback channel。

## 可觀察訊號

- 同一產品需要內測、公開測試與正式版本分流。
- 錯誤版本需要停止擴散或切回回復通道。
- 客戶端更新需要依風險分批推進。

## 接近真實服務的例子

桌面 app 先把 signed installer 推到 internal channel，驗證更新成功率後再推 beta channel，最後推 stable channel。若 stable 版本出現 crash，feed 可切回 rollback channel 或暫停更新。

## 判斷條件與後果

Release Channel 限制得住錯誤版本擴散到多少使用者，前提是版本要達到前一個通道的條件才進入下一個。進入條件沒有寫定（例如 internal 的更新成功率達到多少才推 beta）時，推進依時間或個人判斷，有問題的版本照樣到達 stable。停損條件與回復路徑沒有事先設定時，stable 出現 crash 之後，暫停 feed 還是切到 rollback channel 要在事故當下才決定，這段時間裡已經更新的客戶端數量持續增加。各通道的 artifact 沒有可區分的命名時，從 crash 回報看不出它來自哪個通道的哪個版本。
