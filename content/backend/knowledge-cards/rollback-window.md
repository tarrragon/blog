---
title: "Rollback Window"
date: 2026-05-11
description: "說明變更進入 production 後還能用哪種方式回退或改路線的時間與條件"
weight: 156
tags: ["backend", "knowledge-card", "reliability", "migration"]
---

Rollback window 的核心概念是「變更進入 production 後，仍能用特定方式回退或改路線的有效窗口」。它連接 [rollback strategy](/backend/knowledge-cards/rollback-strategy/)、[release gate](/backend/knowledge-cards/release-gate/) 與 [migration gate](/backend/knowledge-cards/migration-gate/)，讓 gate 能判斷目前還剩哪種退路。

## 概念位置

Rollback window 位在 [cutover / switchover](/backend/knowledge-cards/cutover-switchover/)、[fallback plan](/backend/knowledge-cards/fallback-plan/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 之間。Rollback strategy 說明回退決策，rollback window 說明這個決策在目前階段是否仍可執行。

## 可觀察訊號

系統需要 rollback window 的訊號是：

- expand、backfill、cutover、contract 每一階段的回退方式不同
- 舊版本或舊資料語意只能支撐一段時間
- cutover 後仍可 fallback read，但 contract 後只能資料修復或 fail-forward
- release gate 要判斷是否還能安全暫停或回退

## 接近真實網路服務的例子

資料庫 migration 在 expand 階段通常能回到舊讀取；backfill 階段可以暫停與重跑；cutover 後可回到 fallback read；contract 移除舊欄位後，回退會轉成資料修補或 fail-forward。這些差異都屬於 rollback window。

## 設計責任

Rollback window 要寫清楚目前階段、可用回退方式、最後可回退時間、資料相容性限制與 owner。它要進入 [release gate](/backend/knowledge-cards/release-gate/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/)，避免事故期間把已經關閉的退路當成可用選項。
