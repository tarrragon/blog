---
title: "Rollout Strategy"
date: 2026-05-06
description: "說明新版本如何以可控節奏推進到全部流量"
tags: ["CD", "rollout", "knowledge-card"]
weight: 7
aliases: ["/ci/knowledge-cards/rollout-strategy/"]
---

Rollout Strategy 的核心概念是「用分批推進控制發布風險」，並在異常時交由 [Rollback Strategy](/devops/ci/knowledge-cards/rollback-strategy/) 收斂。它讓變更從小範圍驗證逐步擴大到全量。

## 跟其他概念的關係

Rollout Strategy 位在部署執行與正式[流量切換](/devops/ci/knowledge-cards/readiness-health-check/)之間，常見型態包含 rolling、canary、blue-green 與 phased rollout。

## 可觀察訊號

- 發布後需要觀察一段時間再擴大流量。
- 高風險變更不適合一次全量切換。
- 團隊需要把監控訊號綁定到擴大量決策。

## 接近真實服務的例子

後端 API 先以 10% canary 流量觀察錯誤率與延遲，再逐步推進。App 發布以 phased rollout 控制商店推送比例；App Store 的分階段發布只控制自動更新，主動到商店更新的使用者仍拿得到新版（兩家商店的差異見 [11.15 自家行動 App 與後端的 API 契約：版本回報、最低支援版本、商店審核下的上線順序、分階段發布、熱更新與回退手段](/backend/11-api-design/mobile-client-api-contract/)）。

## 判斷條件與後果

Rollout Strategy 的組成各自缺席時，分批推進失去的控制不同：

- **推進節點**：沒有分批的節點（10%、50%、全量）時，部署一次切到全量，失敗的影響範圍就是全部使用者。
- **觀察指標**：錯誤率與延遲沒有綁定到擴大流量的決定時，canary 階段只是等待一段時間，擴大與否沒有依據。
- **阻擋條件**：指標變差也不會停下推進，壞版本照樣擴散到全量。
- **升降級節奏**：每一批的觀察時間短於問題浮現所需的時間時，推進在問題出現之前就走完。
