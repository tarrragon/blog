---
title: "App Signing"
date: 2026-05-06
description: "說明行動與桌面應用的簽章憑證如何影響發布能力"
tags: ["CD", "app", "signing", "knowledge-card"]
weight: 14
aliases: ["/ci/knowledge-cards/app-signing/"]
---

App Signing 的核心概念是「簽章憑證即發布能力」。它決定 [artifact](/devops/ci/knowledge-cards/artifact/) 是否被平台接受與使用者裝置信任。

## 跟其他概念的關係

App Signing 位在 app build 與 [release channel](/devops/ci/knowledge-cards/release-channel/) 之間，涉及 certificate、provisioning profile、keystore 與 secret 管理。

## 可觀察訊號

- 發布因簽章失敗中斷。
- 簽章憑證過期導致發版中斷。
- 金鑰輪替缺乏演練造成交付風險。

## 接近真實服務的例子

iOS 發版需匹配正確 certificate 與 provisioning profile，Android 發版需維護 keystore 一致性與安全儲存。

## 判斷條件與後果

簽章憑證等於發布能力，它的保存與輪替出問題時，發布本身停下來。團隊自行保管 keystore 而金鑰遺失時，Android 平台只接受同一把金鑰簽的更新，已上架的 app 無法再發布新版本；金鑰外洩時，他人能簽出被裝置信任的版本。憑證過期而沒有輪替節奏時，發版在到期當天因簽章失敗中斷；輪替從未演練時，換憑證的步驟要在中斷當下摸索；沒有權限分離時，能觸發 CI 的人都能簽出正式版本。緊急回復流程決定這些失效發生之後，發布能力中斷多久。
