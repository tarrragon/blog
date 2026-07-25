---
title: "Rerun"
date: 2026-05-21
description: "說明 CI/CD 與 data pipeline 中重跑任務前需要判斷的輸出語意與副作用"
tags: ["CI", "CD", "data-pipeline", "rerun", "knowledge-card"]
weight: 18
---

Rerun 的核心概念是「用明確條件重新執行同一段流程」。它和 [Flaky Test](/ci/knowledge-cards/flaky-test/) 的治理有關，也常依賴 [Checkpoint](/ci/knowledge-cards/checkpoint/) 判斷接續位置。

## 概念位置

Rerun 位在測試失敗、[部署預演](/ci/knowledge-cards/deployment-dry-run/)失敗、資料任務失敗或 pipeline repair 之後，負責判斷重新執行是否會改變輸出或擴大副作用。

## 可觀察訊號

- 同一 commit 的測試結果前後不一致。
- 資料任務部分成功、部分失敗。
- 部署 dry run 失敗後需要確認是否可安全再跑。

## 接近真實服務的例子

每日營收 pipeline 第三個 partition 寫入失敗。團隊先確認前兩個 partition 已完成且輸出可覆寫，再指定 run id 與 partition 範圍 rerun，避免重複計算全部歷史資料。

## 設計責任

Rerun 要定義可重跑條件、輸出覆寫規則、idempotency、觀測結果與人工審核門檻，讓「再跑一次」成為受控恢復策略。
