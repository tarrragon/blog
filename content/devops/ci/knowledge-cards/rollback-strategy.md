---
title: "Rollback Strategy"
date: 2026-05-06
description: "說明發布異常時如何快速回到已知可用狀態"
tags: ["CD", "rollback", "knowledge-card"]
weight: 8
aliases: ["/ci/knowledge-cards/rollback-strategy/"]
---

Rollback Strategy 的核心概念是「在異常發布後縮小影響範圍並回到可用狀態」，是 [Rollout Strategy](/devops/ci/knowledge-cards/rollout-strategy/) 失敗時的對應動作。它屬於部署設計的一部分，需要在事故前完成。

## 跟其他概念的關係

Rollback Strategy 位在 deploy、rollout 與 incident handling 之間，通常要和[資料遷移](/devops/ci/knowledge-cards/migration/)、feature flag 與流量切換一起設計。

## 可觀察訊號

- 發布後錯誤率或延遲快速升高。
- 新舊版本存在相容性風險。
- 團隊需要在分鐘級別恢復核心功能。

## 接近真實服務的例子

靜態站可回退前一版 artifact。後端服務可回退 image tag 並暫停新 migration。App 場域可先用 remote config 關閉新功能，再走 hotfix 發版；remote config 的生效時間取決於 App 多久重新讀一次設定（Firebase 預設 12 小時），各回退手段對已安裝版本的作用見 [11.15 自家行動 App 與後端的 API 契約：版本回報、最低支援版本、商店審核下的上線順序、分階段發布、熱更新與回退手段](/backend/11-api-design/mobile-client-api-contract/)。

## 判斷條件與後果

Rollback Strategy 的回退動作依發布物的形態而不同：靜態站換回前一版 artifact 就完成；後端服務回退 image 時，新的 migration 也要一併暫停；App 已安裝的版本收不回，只能用 remote config 關掉新功能，生效時間取決於 App 多久重新讀一次設定。觸發條件（錯誤率或延遲到什麼程度就回退）與決定回退的責任人沒有事先寫定時，回退與否在事故當下才討論，錯誤持續的時間跟著拉長。回退後沒有驗證時，服務是否回到可用狀態無法確認，例如資料已經被新版本寫成舊版本讀不懂的形狀。回退步驟沒有演練過時，第一次執行發生在事故中，步驟裡的錯誤也在那時才出現。
