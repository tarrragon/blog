---
title: "Backfill"
date: 2026-05-21
description: "說明資料處理與 migration 中如何受控補算歷史資料"
tags: ["CI", "CD", "data-pipeline", "backfill", "knowledge-card"]
weight: 16
---

Backfill 的核心概念是「用新邏輯受控補算既有資料」。它通常和 [Migration](/ci/knowledge-cards/migration/) 共享相容窗口，並依賴 [Checkpoint](/ci/knowledge-cards/checkpoint/) 保存進度。

## 概念位置

Backfill 位在資料 schema、transform logic 或歷史資料修補之後，常出現在 data pipeline、database migration、search index rebuild 與 feature store 更新。

## 可觀察訊號

- 新欄位需要從既有資料補值。
- 歷史 partition 需要用新版邏輯重新計算。
- 補算任務需要節流、停損與對帳。

## 接近真實服務的例子

訂單報表新增 `net_revenue` 欄位時，pipeline 先讓新資料寫入新欄位，再分批 backfill 過去 12 個月的 partition，並用 row count 與金額總和比對結果。

## 設計責任

Backfill 要定義補算範圍、批次大小、checkpoint、停損條件與對帳方式，讓歷史資料修補成為可停止、可接續、可驗證的流程。
