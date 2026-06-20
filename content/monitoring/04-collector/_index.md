---
title: "模組四：Collector 設計"
date: 2026-06-19
description: "收 → 驗 → 存 → 查 → 觸發的完整鏈路 — Go 單一 binary、可插拔 Storage Backend、rule engine"
weight: 4
tags: ["monitoring", "collector", "go", "storage", "rule-engine"]
---

回答「收到的事件怎麼處理」。挑戰在 collector 端，不在 SDK 端。

## 待寫章節

- [x] Collector 架構（HTTP endpoint → JSON Schema 驗證 → 儲存 → 查詢 → rule engine）
- [x] JSONL 匯出與備份格式（匯出格式、gzip 壓縮、備份保留）
- [x] 查詢 API 設計（CLI grep 友好 vs HTTP 查詢 endpoint）
- [x] Rule engine 設計（條件 → 動作 → 模板）
- [x] 規模演進：可插拔 Storage Backend（SQLite 預設 / PostgreSQL 觸發）
- [x] 功能分層與 Backend 選擇（SQLite 層 vs PostgreSQL 層的功能邊界）

## 跨分類引用

- → [backend 01 資料庫](/backend/01-database/)：PostgreSQL backend 的資料庫設計
- → [backend 09 效能容量](/backend/09-performance-capacity/)：高併發寫入 / 大資料查詢的效能挑戰
- → [DevOps 流量管控](/devops/03-traffic-management/)：背壓、rate limit、熔斷的基礎概念
- → [DevOps 突發流量](/devops/07-burst-traffic/)：突發流量分類、降級策略、queue 緩衝
- 實作 repo：tarrragon/monitor 的 collector/ + docs/challenges/（撞牆記錄）
