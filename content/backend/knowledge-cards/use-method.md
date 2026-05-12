---
title: "USE Method"
date: 2026-05-12
description: "Brendan Gregg 提出的資源層 Utilization / Saturation / Errors 三維度量測法"
weight: 223
---

USE method 的核心概念是「對每個資源（CPU / RAM / disk / network / DB connection）量測 Utilization、Saturation、Errors 三個維度」。第一個出現 saturation 上升的資源、就是 bottleneck。可先對照 [RED Method](/backend/knowledge-cards/red-method/)。

## 概念位置

USE 是 resource-oriented 的觀察法、跟 request-oriented 的 [RED method](/backend/knowledge-cards/red-method/) 互補。USE 回答「哪個資源先頂不住」、RED 回答「哪個 endpoint 表現變差」。容量規劃通常先看 USE 找瓶頸、再看 RED 看影響面。可先對照 [Saturation Point](/backend/knowledge-cards/saturation-point/)。

## 可觀察訊號與例子

USE 三維度的典型訊號：CPU utilization 100% 但 saturation queue 空 → 還能撐；CPU 80% 但 run queue 不斷增長 → 已 saturate。對應案例：[Lemino connection limit](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — utilization 看似還行、但 connection saturation 已爆。

## 設計責任

USE method 的關鍵是「不要只看 utilization」。utilization 是「目前用了多少」、saturation 是「排隊有多少在等」 — 後者才是 capacity 真正的領先指標。每個資源都要量三個維度、不能用 average 代替 percentile。
