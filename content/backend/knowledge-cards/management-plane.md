---
title: "Management Plane"
tags: ["管理平面", "Management Plane"]
date: 2026-04-24
description: "說明管理平面如何與業務流量平面分離，避免高權限入口擴散"
weight: 265
---

Management plane 的核心概念是「承載高權限控制操作的系統平面」。它通常包含管理介面、配置變更入口、平台控制 API 與維運工具。 可先對照 [Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)。

## 跟其他概念的關係

Management plane 位在 [admin-endpoint](/backend/knowledge-cards/admin-endpoint/)、[trust-boundary](/backend/knowledge-cards/trust-boundary/)、[runtime-config](/backend/knowledge-cards/runtime-config/) 與 [audit-log](/backend/knowledge-cards/audit-log/) 之間。它需要和業務流量平面維持清楚邊界。

## 可觀察訊號與例子

系統需要管理平面治理的訊號是管理入口可由一般流量路徑到達，或管理操作缺少獨立稽核。邊界設備、雲端控制台、平台管控 API 都屬於管理平面。

## 判斷條件與後果

管理平面的操作能改變整個系統的配置，所以它的存取邊界與紀錄決定了一次誤用或入侵的影響範圍。管理入口可以由一般流量路徑到達時，業務平面上任何一個被攻破的元件都能成為進入管理操作的起點，控制能力從那一點橫向擴散。管理操作沒有獨立審核與責任鏈時，事件發生後查不出是誰在什麼時候改了什麼，鎖定高風險入口要從逐台查設定開始。變更時序沒有定義、多個管理變更同時進行時，出事之後分不出是哪一個變更造成的。
