---
title: "Rollback Strategy"
date: 2026-05-06
description: "說明發布異常時如何快速回到已知可用狀態"
tags: ["CD", "rollback", "knowledge-card"]
weight: 8
---

Rollback Strategy 的核心概念是「在異常發布後縮小影響範圍並回到可用狀態」。它是部署設計的一部分，不是事故後才補的程序。

## 概念位置

Rollback Strategy 位在 deploy、rollout 與 incident handling 之間，通常要和資料遷移、feature flag 與流量切換一起設計。

## 可觀察訊號

- 發布後錯誤率或延遲快速升高。
- 新舊版本存在相容性風險。
- 團隊需要在分鐘級別恢復核心功能。

## 接近真實服務的例子

靜態站可回退前一版 artifact。後端服務可回退 image tag 並暫停新 migration。App 場域可先用 remote config 關閉新功能，再走 hotfix 發版。

## 設計責任

Rollback Strategy 要定義觸發條件、責任人、回退動作與回復後驗證，並定期演練。
