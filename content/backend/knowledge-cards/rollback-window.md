---
title: "Rollback Window"
date: 2026-05-11
description: "說明變更進入 production 後還能用哪種方式回退或改路線的時間與條件"
weight: 157
tags: ["backend", "knowledge-card", "reliability", "migration"]
---

Rollback window 的核心概念是「變更進入 production 後，仍能用特定方式回退或改路線的有效窗口」。它連接 [rollback strategy](/backend/knowledge-cards/rollback-strategy/)、[release gate](/backend/knowledge-cards/release-gate/) 與 [migration gate](/backend/knowledge-cards/migration-gate/)，讓 gate 能判斷目前還剩哪種退路。

## 跟其他概念的關係

Rollback window 位在 [cutover / switchover](/backend/knowledge-cards/cutover-switchover/)、[fallback plan](/backend/knowledge-cards/fallback-plan/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 之間。Rollback strategy 說明回退決策，rollback window 說明這個決策在目前階段是否仍可執行。

## 可觀察訊號

系統需要 rollback window 的訊號是：

- expand、backfill、cutover、contract 每一階段的回退方式不同
- 舊版本或舊資料語意只能支撐一段時間
- cutover 後仍可 fallback read，但 contract 後只能資料修復或 fail-forward
- release gate 要判斷是否還能安全暫停或回退

## 接近真實網路服務的例子

資料庫 migration 在 expand 階段通常能回到舊讀取；backfill 階段可以暫停與重跑；cutover 後可回到 fallback read；contract 移除舊欄位後，回退會轉成資料修補或 fail-forward。這些差異都屬於 rollback window。

## 判斷條件與後果

Rollback window 的判斷對象是 migration 目前所在的階段還剩哪一種退路。expand 與 backfill 階段的退路是回到舊讀取或暫停重跑；contract 移除舊欄位之後，退路只剩資料修補或 fail-forward，原因是舊版本依賴的欄位已經不存在。窗口沒有寫明目前階段、最後可回退時間與資料相容性限制時，事故期間的決策者可能選了已經關閉的退路，執行到一半才發現走不通；所以每個階段的可用回退方式與 owner 記進 [release gate](/backend/knowledge-cards/release-gate/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/)。
