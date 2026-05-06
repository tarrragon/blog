---
title: "Config Rollout"
tags: ["設定發布", "Config Rollout"]
date: 2026-04-24
description: "說明設定如何安全下發到正在運作的服務實例"
weight: 152
---


Config Rollout 的核心概念是「把設定變更從程式部署中分離，並以可控方式送到正在運作的服務」。它處理的是設定版本、下發節奏、回復方式與觀察驗證，不是單純修改一個環境變數值。 可先對照 [Connection Pool](/backend/knowledge-cards/connection-pool/)。

## 概念位置

Config Rollout 位在 configuration source、deployment platform 與 running instances 之間。它通常與 service discovery、container runtime、feature flag、secret management 或配置中心一起出現。 可先對照 [Connection Pool](/backend/knowledge-cards/connection-pool/)。

## 可觀察訊號

系統需要 config rollout 的訊號是：

- 同一版程式要搭配不同環境設定
- 設定變更可能影響流量、權限或依賴連線
- 希望設定可以分批驗證與回復

## 接近真實網路服務的例子

新增下游 endpoint、切換第三方金鑰、調整 feature flag、更新來源白名單或變更 retry policy，都屬於 config rollout 問題。

## 設計責任

設計時要定義設定來源、分發順序、驗證方式、回復方式與影響範圍。Config Rollout 應該讓設定變更可預測，而不是把風險藏在部署流程裡。
