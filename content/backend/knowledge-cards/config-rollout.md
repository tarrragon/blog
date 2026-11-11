---
title: "Config Rollout"
tags: ["設定發布", "Config Rollout"]
date: 2026-04-24
description: "說明設定如何安全下發到正在運作的服務實例"
weight: 153
---

Config Rollout 的核心概念是「把設定變更從程式部署中分離，並以可控方式送到正在運作的服務」。它處理的是設定版本、下發節奏、回復方式與觀察驗證，不是單純修改一個環境變數值。 可先對照 [Connection Pool](/backend/knowledge-cards/connection-pool/)。

## 跟其他概念的關係

Config Rollout 位在 configuration source、deployment platform 與 running instances 之間。它通常與 service discovery、container runtime、feature flag、secret management 或配置中心一起出現。 可先對照 [Connection Pool](/backend/knowledge-cards/connection-pool/)。

## 可觀察訊號

系統需要 config rollout 的訊號是：

- 同一版程式要搭配不同環境設定
- 設定變更可能影響流量、權限或依賴連線
- 希望設定可以分批驗證與回復

## 接近真實網路服務的例子

新增下游 endpoint、切換第三方金鑰、調整 feature flag、更新來源白名單或變更 retry policy，都屬於 config rollout 問題。

## 判斷條件與後果

設定變更不經過程式部署就送到運作中的服務，config rollout 的每一個環節缺席時，設定變更的風險各以一種方式出現。設定來源沒有版本時，出事之後查不出哪一個值在什麼時候被改；分發順序是全部 instance 同時生效時，錯的設定（指錯的下游 endpoint、漏列的白名單來源）一次影響全部流量；沒有驗證方式時，設定生效之後要等使用者回報才知道它是否正確；沒有回復方式時，退回舊值要靠手動改；影響範圍沒有標出時，改 retry policy 的人看不出這個值會影響哪些服務。
