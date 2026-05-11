---
title: "Gate Decision"
date: 2026-05-11
description: "說明 release gate 如何把證據轉成放行、暫停、回退或補證據的決策"
weight: 159
tags: ["backend", "knowledge-card", "reliability", "release-gate"]
---

Gate decision 的核心概念是「release gate 根據證據做出的明確下一步」。它連接 [release gate](/backend/knowledge-cards/release-gate/)、[evidence package](/backend/knowledge-cards/evidence-package/) 與 [stop condition](/backend/knowledge-cards/stop-condition/)，讓 gate 不只寫檢查結果，也寫出能不能前進。

## 概念位置

Gate decision 位在 [confidence](/backend/knowledge-cards/confidence/)、[rollback window](/backend/knowledge-cards/rollback-window/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 之間。Checks 描述檢查結果，gate decision 把結果轉成放行、暫停、回退、fail-forward 或補證據。

## 可觀察訊號

系統需要 gate decision 的訊號是：

- CI、SLO、validation query 都有結果，但沒人知道下一步
- evidence 足以支持部分放行，但不足以支持完整 cutover
- 變更需要逐批 rollout、backfill、warmup 或 replay
- gate 要保留 owner 與 rollback window

## 接近真實網路服務的例子

資料庫 migration 的 gate decision 可以寫成 `allow next 10% backfill; block customer-visible read cutover`。這句話比 `migration pass` 更可操作，因為它同時說明允許前進的範圍與被擋住的風險面。

## 設計責任

Gate decision 要包含決策內容、支撐 checks、stop condition、rollback window 與 owner。它要能被 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 承接，讓放行後出現異常時能回放當時依據。
