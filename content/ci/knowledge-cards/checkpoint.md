---
title: "Checkpoint"
date: 2026-05-21
description: "說明長時間任務如何記錄進度以支援接續、重跑與事故修復"
tags: ["CI", "CD", "data-pipeline", "checkpoint", "knowledge-card"]
weight: 17
---

Checkpoint 的核心概念是「保存可接續的處理進度」。它讓 [Backfill](/ci/knowledge-cards/backfill/) 與 [Rerun](/ci/knowledge-cards/rerun/) 可以從明確位置恢復，避免每次都從頭開始。

## 概念位置

Checkpoint 位在長時間 job、stream processor、batch pipeline 與 migration 任務之間，常以 partition、offset、run id、cursor 或 processed marker 呈現。

## 可觀察訊號

- 任務執行時間長，失敗後需要接續。
- 重跑同一區間可能造成重複寫入。
- streaming consumer 需要保存 offset 或 event position。

## 接近真實服務的例子

資料回填每次處理一個日期 partition，完成後寫入 `backfill_runs` 表。任務中斷時，下一次從最後成功 partition 的下一段開始。

## 設計責任

Checkpoint 要定義進度格式、提交時機、失敗恢復、重跑覆寫與觀測欄位，讓長時間任務具備可恢復性。
