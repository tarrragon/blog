---
title: "Startup Probe"
date: 2026-06-23
description: "保護慢啟動服務不被 liveness probe 過早重啟的探針"
weight: 132
tags: ["probe", "deployment", "lifecycle"]
---

Startup probe 的核心概念是「在服務啟動期間持續探測、確認初始化完成後再交棒給 liveness 與 readiness [probe](/backend/knowledge-cards/probe/)」。它保護啟動時間長的服務（JVM warmup、大量依賴連線建立）不被 liveness 在初始化期間判定失敗而反覆重啟。可先對照 [Probe](/backend/knowledge-cards/probe/)。

## 跟其他概念的關係

Startup probe 位在 container 啟動與 [readiness](/backend/knowledge-cards/readiness/) / liveness 之間。startup probe 成功前，liveness 和 readiness 不會啟動。startup probe 一旦成功就永久停用，由 liveness 和 readiness 接手。可先對照 [Graceful Shutdown](/backend/knowledge-cards/graceful-shutdown/)。

## 可觀察訊號

系統需要 startup probe 的訊號是「服務啟動時間超過 liveness 的預設容忍窗口」。典型場景：JVM 服務 warmup 需 30-60 秒、依賴多的服務需要等資料庫連線池和 cache 連線建立。沒有 startup probe 時，liveness 會在初始化期間把健康的服務判定為壞掉，觸發 restart loop。

## 判斷條件與後果

startup probe 的總容忍時間 = `failureThreshold × periodSeconds`，它跟服務在最差情境下的啟動時間（冷啟動 + image pull + 依賴連線）的差距，決定服務啟動時的狀態。容忍時間短於最差啟動時間時，startup probe 在初始化完成前判定失敗，container 被重啟，下一次啟動在同樣的位置再次失敗，形成 restart loop；容忍時間只比平常的啟動時間多一點時，平常啟動順利，遇到 image pull 或依賴連線變慢的那一次才被重啟；所以容忍時間以量測到的最差啟動時間再加 headroom 來設。startup probe 跟 `initialDelaySeconds` 處理同一件事，差別在 startup probe 在啟動期間持續探測，初始化一完成就交給 liveness 與 readiness，啟動失敗也偵測得到；`initialDelaySeconds` 是盲等，等待期間觀測不到啟動進度，設短了會重啟還在初始化的服務，設長了會讓啟動後卡住的服務等滿這段時間才被偵測。
