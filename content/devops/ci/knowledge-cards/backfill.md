---
title: "Backfill"
date: 2026-05-21
description: "說明資料處理與 migration 中如何受控補算歷史資料"
tags: ["CI", "CD", "data-pipeline", "backfill", "knowledge-card"]
weight: 16
aliases: ["/ci/knowledge-cards/backfill/"]
---

Backfill 的核心概念是「用新邏輯受控補算既有資料」。它通常和 [Migration](/devops/ci/knowledge-cards/migration/) 共享相容窗口，並依賴 [Checkpoint](/devops/ci/knowledge-cards/checkpoint/) 保存進度。

## 跟其他概念的關係

Backfill 位在資料 schema、transform logic 或歷史資料修補之後，常出現在 data pipeline、database [migration](/devops/ci/knowledge-cards/migration/)、search index rebuild 與 feature store 更新。

## 可觀察訊號

- 新欄位需要從既有資料補值。
- 歷史 partition 需要用新版邏輯重新計算。
- 補算任務需要節流、停損與對帳。

## 接近真實服務的例子

訂單報表新增 `net_revenue` 欄位時，pipeline 先讓新資料寫入新欄位，再分批 backfill 過去 12 個月的 partition，並用 row count 與金額總和比對結果。

## 判斷條件與後果

Backfill 改寫的是既有資料，每一項控制缺席時，錯誤會寫進原本正確的歷史資料。補算範圍沒有界定時，任務改到不該動的 partition；批次太大時，單批佔滿資料庫或 pipeline 的資源，線上寫入跟著變慢；沒有 [checkpoint](/devops/ci/knowledge-cards/checkpoint/) 時，中斷後只能從頭跑；沒有停損條件時，新邏輯有錯也會一路寫完全部歷史資料；沒有對帳方式（row count、金額總和）時，補完之後無法證明結果正確。
