---
title: "Readiness / Health Check"
date: 2026-05-06
description: "說明服務存活與可接流量判斷在部署中的不同責任"
tags: ["CD", "readiness", "health-check", "knowledge-card"]
weight: 12
---

Readiness / Health Check 的核心概念是「服務活著」與「服務可接流量」是兩個不同訊號。部署放行通常依賴 readiness，而非僅看 process alive。

## 概念位置

Readiness / Health Check 位在 rollout、load balancer 與 runtime platform 之間，是流量切換前的核心 gate。

## 可觀察訊號

- 部署後健康檢查綠燈但請求仍大量失敗。
- 新版啟動中就提早接到流量。
- rollout 失敗時缺少可觀測放行條件。

## 接近真實服務的例子

Kubernetes liveness 通過只代表 process 存活；readiness 通過才代表連線池、依賴服務與必要資料都已準備完成。

## 設計責任

Readiness / Health Check 要定義檢查內容、容錯窗口與失敗處理，讓 rollout decision 有可信訊號。
