---
title: "Rollout Strategy"
date: 2026-05-06
description: "說明新版本如何以可控節奏推進到全部流量"
tags: ["CD", "rollout", "knowledge-card"]
weight: 7
---

Rollout Strategy 的核心概念是「用分批推進控制發布風險」。它讓變更從小範圍驗證逐步擴大到全量。

## 概念位置

Rollout Strategy 位在部署執行與正式流量切換之間，常見型態包含 rolling、canary、blue-green 與 phased rollout。

## 可觀察訊號

- 發布後需要觀察一段時間再擴大流量。
- 高風險變更不適合一次全量切換。
- 團隊需要把監控訊號綁定到擴大量決策。

## 接近真實服務的例子

後端 API 先以 10% canary 流量觀察錯誤率與延遲，再逐步推進。App 發布以 phased rollout 控制商店推送比例。

## 設計責任

Rollout Strategy 要定義推進節點、觀察指標、阻擋條件與升降級節奏，讓部署風險可被量化管理。
