---
title: "Burn Rate"
date: 2026-06-22
description: "說明 error budget 消耗速度如何支援告警與事故分級"
weight: 102
tags: ["backend", "observability"]
---

Burn rate 的核心概念是「[error budget](/backend/knowledge-cards/error-budget/) 被消耗的速度」。Burn rate = 1 代表按 [SLO](/backend/knowledge-cards/sli-slo/) 允許的速度正常消耗；burn rate = 10 代表消耗速度是允許值的 10 倍 — 如果持續下去，error budget 會在 SLO 週期的 1/10 內耗盡。

## 概念位置

Burn rate 是 SLO alerting 的核心機制，把 [SLI](/backend/knowledge-cards/sli-slo/) 的 error ratio 轉成可行動的嚴重度判斷。短時間高 burn rate（14x、5 分鐘窗口）代表急性事故；長時間中等 burn rate（1x、數小時窗口）代表慢性可靠性退化。

Burn rate alerting 比固定閾值 alert 更能反映使用者影響 — 低流量時段的幾筆 error 可能 burn rate 很低（對 error budget 影響小），高流量時段的相同 error rate 可能 burn rate 很高（影響大量使用者）。

## 使用情境

系統需要 burn rate 的訊號是固定閾值 alert（error rate > 1%）在不同流量時段的表現不穩定 — 低流量時 false alarm、高流量時漏報。Burn rate 自動適應流量基線。

## 設計責任

Burn rate alerting 用 multi-window 策略：短窗口（5min）抓急性 + 長窗口（1hr）做確認，兩個窗口都超過閾值才觸發。Recording rule 預計算各窗口的 error ratio，讓 alert evaluate 讀預計算結果而非重算 raw series。完整設計見 [4.6 SLI/SLO 訊號設計](/backend/04-observability/sli-slo-signal/)。
