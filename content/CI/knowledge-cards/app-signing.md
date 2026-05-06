---
title: "App Signing"
date: 2026-05-06
description: "說明行動與桌面應用的簽章憑證如何影響發布能力"
tags: ["CD", "app", "signing", "knowledge-card"]
weight: 14
---

App Signing 的核心概念是「簽章憑證即發布能力」。它決定 artifact 是否被平台接受與使用者裝置信任。

## 概念位置

App Signing 位在 app build 與 release channel 之間，涉及 certificate、provisioning profile、keystore 與 secret 管理。

## 可觀察訊號

- 發布因簽章失敗中斷。
- 憑證過期導致無法發版。
- 金鑰輪替缺乏演練造成交付風險。

## 接近真實服務的例子

iOS 發版需匹配正確 certificate 與 provisioning profile，Android 發版需維護 keystore 一致性與安全儲存。

## 設計責任

App Signing 要定義密鑰保存、輪替節奏、權限分離與緊急回復流程，確保發布能力可持續。
