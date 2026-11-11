---
title: "Checkpoint"
date: 2026-05-21
description: "說明長時間任務如何記錄進度以支援接續、重跑與事故修復"
tags: ["CI", "CD", "data-pipeline", "checkpoint", "knowledge-card"]
weight: 17
aliases: ["/ci/knowledge-cards/checkpoint/"]
---

Checkpoint 的核心概念是「保存可接續的處理進度」。它讓 [Backfill](/devops/ci/knowledge-cards/backfill/) 與 [Rerun](/devops/ci/knowledge-cards/rerun/) 可以從明確位置恢復，避免每次都從頭開始。

## 跟其他概念的關係

Checkpoint 位在長時間 job、stream processor、batch pipeline 與 [migration](/devops/ci/knowledge-cards/migration/) 任務之間，常以 partition、offset、run id、cursor 或 processed marker 呈現。

## 可觀察訊號

- 任務執行時間長，失敗後需要接續。
- 重跑同一區間可能造成重複寫入。
- streaming consumer 需要保存 offset 或 event position。

## 接近真實服務的例子

資料回填每次處理一個日期 partition，完成後寫入 `backfill_runs` 表。任務中斷時，下一次從最後成功 partition 的下一段開始。

## 判斷條件與後果

Checkpoint 的提交時機排在工作寫入之前還是之後，決定恢復時會漏做還是重做。checkpoint 先提交、任務在寫入完成前中斷時，恢復後從 checkpoint 之後開始，這一段資料漏做；寫入之後才提交時，中斷讓這一段重做，重跑時的寫法（冪等寫入、整個 partition 覆寫）決定重做是否產生重複資料。進度格式記不到精確位置時（只記日期，不記 partition 或 offset），恢復點只能退回較早的位置，重做的範圍變大。沒有觀測欄位時，看不出任務停在哪個 checkpoint、多久沒有前進。
