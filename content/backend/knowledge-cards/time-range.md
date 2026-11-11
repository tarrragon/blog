---
title: "Time Range"
date: 2026-05-11
description: "說明證據、查詢與事故判讀如何用時間窗保留可回放上下文"
weight: 319
tags: ["backend", "knowledge-card", "observability", "incident-response"]
---

Time range 的核心概念是「證據或查詢對應的明確時間窗」。它連接 [evidence package](/backend/knowledge-cards/evidence-package/)、[incident timeline](/backend/knowledge-cards/incident-timeline/) 與 [steady state](/backend/knowledge-cards/steady-state/)，讓同一組資料能被事中交班、release gate 與事後復盤一致解讀。

## 跟其他概念的關係

Time range 位在 [dashboard](/backend/knowledge-cards/dashboard/)、[query link](/backend/knowledge-cards/query-link/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 之間。Dashboard 顯示狀態，query link 保留查詢入口，time range 則定義這次判讀看的時間範圍。

## 可觀察訊號

系統需要 time range 的訊號是：

- 同一張圖在不同時間重跑會得到不同結果
- release gate 要判斷某批 rollout 是否已穩定
- 事故交班需要知道某個 evidence 觀察的是哪段時間
- 復盤要對齊 deploy、alert、customer report 與 rollback 的先後

## 接近真實網路服務的例子

資料庫 migration 的 validation query 若標示 `2026-05-11T02:10:00Z/2026-05-11T02:20:00Z`，下一班 on-call 就能把 mismatch、replication lag 與 slow query 放回同一個 backfill batch 判讀。

## 判斷條件與後果

Time range 沒有寫明開始時間、結束時間與時區時，同一張圖在不同時間重跑得到不同結果，事中交班與事後復盤讀的不是同一段資料；沒標時區的時間在不同人的畫面上可能對應到不同的時刻。沒有寫資料延遲限制時，剛結束的時間窗裡還有資料沒進來，當下算出的 mismatch 或錯誤率偏低，判斷可能因此放行。沒有關聯事件（哪一次 deploy、哪一批 backfill）時，讀的人知道看的是哪一段時間，卻不知道那段時間裡發生了什麼。Time range 寫進 [evidence package](/backend/knowledge-cards/evidence-package/) 與 [rollback condition](/backend/knowledge-cards/rollback-condition/) 之後，release gate、交班與復盤用同一個時間窗比較同一個決策，結論才對得起來。
