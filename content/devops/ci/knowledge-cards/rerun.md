---
title: "Rerun"
date: 2026-05-21
description: "說明 CI/CD 與 data pipeline 中重跑任務前需要判斷的輸出語意與副作用"
tags: ["CI", "CD", "data-pipeline", "rerun", "knowledge-card"]
weight: 18
aliases: ["/ci/knowledge-cards/rerun/"]
---

Rerun 的核心概念是「用明確條件重新執行同一段流程」。它和 [Flaky Test](/devops/ci/knowledge-cards/flaky-test/) 的治理有關，也常依賴 [Checkpoint](/devops/ci/knowledge-cards/checkpoint/) 判斷接續位置。

## 跟其他概念的關係

Rerun 位在測試失敗、[部署預演](/devops/ci/knowledge-cards/deployment-dry-run/)失敗、資料任務失敗或 pipeline repair 之後，負責判斷重新執行是否會改變輸出或擴大副作用。

## 可觀察訊號

- 同一 commit 的測試結果前後不一致。
- 資料任務部分成功、部分失敗。
- 部署 dry run 失敗後需要確認是否可安全再跑。

## 接近真實服務的例子

每日營收 pipeline 第三個 partition 寫入失敗。團隊先確認前兩個 partition 已完成且輸出可覆寫，再指定 run id 與 partition 範圍 rerun，避免重複計算全部歷史資料。

## 判斷條件與後果

Rerun 是否安全，取決於重新執行是否改變已經完成的輸出。流程具備 idempotency、輸出可以覆寫時（每日營收 pipeline 的 partition 寫回同一個位置），指定失敗的範圍重跑只補上缺的那一段；輸出會累加或觸發外部副作用時（寄信、扣款、對外發布），重跑同一段讓結果重複出現。測試的重跑是另一種情形：同一 commit 重跑後轉綠，代表失敗來自 flaky 而非這次變更，重跑結果沒有被記錄時，這個 flaky 訊號跟著消失。副作用撤不回的流程，重跑前因此要經過人工確認。
