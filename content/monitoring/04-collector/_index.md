---
title: "模組四：Collector 設計"
date: 2026-06-19
description: "收 → 驗 → 存 → 查 → 觸發的完整鏈路 — Go 單一 binary、JSONL 儲存、rule engine"
weight: 4
tags: ["monitoring", "collector", "go", "storage", "rule-engine"]
---

回答「收到的事件怎麼處理」。挑戰在 collector 端，不在 SDK 端。

## 待寫章節

- [x] Collector 架構（HTTP endpoint → JSON Schema 驗證 → JSONL 儲存 → CLI 查詢 → rule engine）
- [x] JSONL 儲存設計（一天一檔、保留策略、gzip 壓縮）
- [x] 查詢 API 設計（CLI grep 友好 vs HTTP 查詢 endpoint）
- [x] Rule engine 設計（條件 → 動作 → 模板）
- [x] 規模演進：grep → SQLite → 時間序列 DB 的觸發條件

## 跨分類引用

- → [backend 01 資料庫](/backend/01-database/)：當 JSONL 撐不住時的儲存升級路徑
- → [backend 09 效能容量](/backend/09-performance-capacity/)：高併發寫入 / 大資料查詢的效能挑戰
- 實作 repo：tarrragon/monitor 的 collector/ + docs/challenges/（撞牆記錄）
