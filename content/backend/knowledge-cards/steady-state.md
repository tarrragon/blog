---
title: "Steady State"
tags: ["Steady State", "Chaos Engineering", "穩態"]
date: 2026-05-07
description: "說明可靠性實驗與事故恢復如何定義系統應維持的可接受狀態"
weight: 319
---

Steady state 的核心概念是「系統在正常或受控退化期間仍應維持的服務能力」。它連接 [SLI / SLO](/backend/knowledge-cards/sli-slo/)、[chaos test](/backend/knowledge-cards/chaos-test/) 與 [degradation](/backend/knowledge-cards/degradation/)，讓實驗與事故共用同一組成功條件。

## 概念位置

Steady state 位在 [error budget](/backend/knowledge-cards/error-budget/)、[blast radius](/backend/knowledge-cards/blast-radius/) 與 [RTO](/backend/knowledge-cards/rto/) / [RPO](/backend/knowledge-cards/rpo/) 之間。它把可靠性承諾轉成可量測訊號，並說明故障期間哪些能力要維持、哪些能力可以受控退化。

## 可觀察訊號與例子

系統需要 steady state 的訊號是 chaos、failover 或 DR drill 只描述故障動作，缺少成功判準。常見例子是節點被關閉後 health check 仍為綠燈，但 checkout success、queue lag 或 client-side error rate 已經偏離使用者可接受範圍。

## 設計責任

Steady state 要包含 success rate、latency、queue lag、data correctness、customer impact 與 recovery complete 門檻。它的責任是支援 [evidence package](/backend/knowledge-cards/evidence-package/)、[incident decision log](/backend/knowledge-cards/incident-decision-log/) 與 [game day](/backend/knowledge-cards/game-day/) 判斷實驗是否通過、事故是否恢復。
