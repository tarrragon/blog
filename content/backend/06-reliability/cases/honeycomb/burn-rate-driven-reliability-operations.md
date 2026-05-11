---
title: "Honeycomb：以 Burn Rate 驅動的可靠性操作"
date: 2026-05-07
description: "把 SLO burn rate 直接連到值班決策與改善優先序，降低高噪音告警造成的判讀失真。"
weight: 21
tags: ["backend", "reliability", "case-study"]
---

Honeycomb 案例的核心責任是把可觀測訊號直接轉成可靠性決策。當團隊面對大量告警時，burn rate 提供比固定閾值更接近使用者體感的判讀方式。

## 問題場景

固定閾值告警在高變化流量下容易失真。團隊可能長時間處於告警疲勞，卻看不出真正侵蝕 SLO 的事件。

## 決策機制

| 機制               | 核心問題               | 交付結果   |
| ------------------ | ---------------------- | ---------- |
| Burn rate 警示     | 可靠性消耗速度是否異常 | 優先序判讀 |
| SLO 驅動值班       | 哪些事件需要立即接手   | 響應節奏   |
| Tracing-first 分析 | 事件路徑如何定位       | 可追溯證據 |

## 可觀測訊號

| 訊號               | 判讀重點               | 對應章節                                          |
| ------------------ | ---------------------- | ------------------------------------------------- |
| fast burn          | 短期消耗是否超過容忍帶 | [6.6](/backend/06-reliability/slo-error-budget/)  |
| slow burn          | 長期趨勢是否持續惡化   | [4.6](/backend/04-observability/sli-slo-signal/)  |
| trace outlier path | 關鍵路徑是否集中退化   | [4.3](/backend/04-observability/tracing-context/) |

## 下一步路由

先用 [4.20](/backend/04-observability/observability-evidence-package/) 組證據，再在 [6.23](/backend/06-reliability/verification-evidence-handoff/) 回寫驗證條件。
