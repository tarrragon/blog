---
title: "Time Range"
date: 2026-05-11
description: "說明證據、查詢與事故判讀如何用時間窗保留可回放上下文"
weight: 318
tags: ["backend", "knowledge-card", "observability", "incident-response"]
---

Time range 的核心概念是「證據或查詢對應的明確時間窗」。它連接 [evidence package](/backend/knowledge-cards/evidence-package/)、[incident timeline](/backend/knowledge-cards/incident-timeline/) 與 [steady state](/backend/knowledge-cards/steady-state/)，讓同一組資料能被事中交班、release gate 與事後復盤一致解讀。

## 概念位置

Time range 位在 [dashboard](/backend/knowledge-cards/dashboard/)、[query link](/backend/knowledge-cards/query-link/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 之間。Dashboard 顯示狀態，query link 保留查詢入口，time range 則定義這次判讀看的時間範圍。

## 可觀察訊號

系統需要 time range 的訊號是：

- 同一張圖在不同時間重跑會得到不同結果
- release gate 要判斷某批 rollout 是否已穩定
- 事故交班需要知道某個 evidence 觀察的是哪段時間
- 復盤要對齊 deploy、alert、customer report 與 rollback 的先後

## 接近真實網路服務的例子

資料庫 migration 的 validation query 若標示 `2026-05-11T02:10:00Z/2026-05-11T02:20:00Z`，下一班 on-call 就能把 mismatch、replication lag 與 slow query 放回同一個 backfill batch 判讀。

## 設計責任

Time range 要定義開始時間、結束時間、時區、資料延遲限制與關聯事件。它應進入 [evidence package](/backend/knowledge-cards/evidence-package/) 與 [rollback condition](/backend/knowledge-cards/rollback-condition/)，避免團隊用不同時間窗比較同一個決策。
