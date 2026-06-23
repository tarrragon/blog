---
title: "Startup Probe"
date: 2026-06-23
description: "保護慢啟動服務不被 liveness probe 過早重啟的探針"
weight: 131
tags: ["probe", "deployment", "lifecycle"]
---

Startup probe 的核心概念是「在服務啟動期間持續探測、確認初始化完成後再交棒給 liveness 與 readiness [probe](/backend/knowledge-cards/probe/)」。它保護啟動時間長的服務（JVM warmup、大量依賴連線建立）不被 liveness 在初始化期間判定失敗而反覆重啟。可先對照 [Probe](/backend/knowledge-cards/probe/)。

## 概念位置

Startup probe 位在 container 啟動與 [readiness](/backend/knowledge-cards/readiness/) / liveness 之間。startup probe 成功前，liveness 和 readiness 不會啟動。startup probe 一旦成功就永久停用，由 liveness 和 readiness 接手。可先對照 [Graceful Shutdown](/backend/knowledge-cards/graceful-shutdown/)。

## 可觀察訊號

系統需要 startup probe 的訊號是「服務啟動時間超過 liveness 的預設容忍窗口」。典型場景：JVM 服務 warmup 需 30-60 秒、依賴多的服務需要等資料庫連線池和 cache 連線建立。沒有 startup probe 時，liveness 會在初始化期間把健康的服務判定為壞掉，觸發 restart loop。

## 設計責任

startup probe 的總容忍時間 = `failureThreshold × periodSeconds`。設計時先量測服務在最差情境下的啟動時間（冷啟動 + image pull + 依賴連線），再加 headroom。startup probe 跟 `initialDelaySeconds` 解決同一個問題，但 startup probe 在啟動期間持續探測（能偵測啟動失敗），`initialDelaySeconds` 是盲等（無法觀測啟動進度）。
