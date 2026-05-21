---
title: "Data pipeline backfill、checkpoint 與 rerun 流程"
date: 2026-05-21
description: "說明資料處理任務 CI/CD 如何驗證 schema、部署 job、控制 backfill、建立 checkpoint 與處理 rerun"
tags: ["CI", "CD", "data-pipeline", "backfill", "rerun"]
weight: 1
---

Data pipeline 發布流程的核心責任是讓資料處理邏輯變更可驗證、可重跑、可修補。資料任務部署成功不等於資料正確；CI/CD 要同時檢查輸入 schema、輸出契約、[Backfill](/ci/knowledge-cards/backfill/)、[Checkpoint](/ci/knowledge-cards/checkpoint/) 與異常資料修復路徑。

## 流程定位

Data pipeline 的風險集中在資料副作用。API 發布錯誤通常會表現成 request failure；資料任務錯誤可能把錯誤結果寫進 warehouse、feature store、報表或下游模型，並在很久之後才被看見。發布流程要把 correctness check 放到 deploy 前後。

| 階段                                      | 責任                             | 判讀訊號                             |
| ----------------------------------------- | -------------------------------- | ------------------------------------ |
| Build                                     | 產生 transform code、DAG、query  | 版本是否可重現                       |
| Validation                                | 驗證 input / output schema       | 新舊欄位、型別、nullability 是否相容 |
| Deploy                                    | 推進 job、DAG、schedule、trigger | 新版本是否正確接管                   |
| [Backfill](/ci/knowledge-cards/backfill/) | 受控補算歷史資料                 | 範圍、節流、checkpoint 是否明確      |
| [Rerun](/ci/knowledge-cards/rerun/)       | 修復失敗區間或錯誤輸出           | idempotency、覆寫規則、對帳是否存在  |
| Recovery                                  | rollback、forward fix、資料修補  | 下游是否已消費錯誤資料               |

Build 階段負責固定執行邏輯。dbt model、Spark job、Flink processor、Airflow DAG 或 SQL transform 都需要能追到 commit 與 dependency，讓歷史資料重跑時能確認使用哪一版邏輯。

Validation 階段負責檢查資料契約。Schema check、sample run、contract test、row count、null ratio、distinct count 與 business invariant 都可以作為 gate；重點是讓輸出變更在下游消費前被看見。

Deploy 階段負責切換任務版本。Scheduler、trigger、checkpoint location 與 credential 都會影響新版本是否真正接管；部署後要確認下一次 run 用的是新版本，並保留舊版本停止或恢復路徑。

[Backfill](/ci/knowledge-cards/backfill/) 階段負責補算歷史資料。Backfill 應有時間範圍、節流、checkpoint、停損條件與對帳策略，避免一次掃完整個歷史區間壓垮上游或把錯誤大規模寫入下游。

[Rerun](/ci/knowledge-cards/rerun/) 階段負責修復失敗 run 或錯誤區間。Rerun 要定義輸出覆寫、去重、idempotency 與下游通知；同一段資料被跑兩次時，結果應可預期。

Recovery 階段負責處理錯誤資料已被消費的情況。資料 pipeline 的 rollback 常常採用 forward fix、重新計算、標記污染區間與通知下游重新讀取。

## Backfill 控制面

Backfill 控制面的責任是限制歷史補算的影響範圍。歷史資料量通常遠大於日常增量；沒有控制面的 backfill 會同時衝擊計算成本、上游讀取、下游寫入與資料正確性。

| 控制項                                        | 判讀問題                      | 常見做法                           |
| --------------------------------------------- | ----------------------------- | ---------------------------------- |
| Range                                         | 補算哪個時間或 partition 區間 | 先小範圍驗證，再擴大區間           |
| Throttle                                      | 每批處理多少資料              | 限制 concurrency、batch size       |
| [Checkpoint](/ci/knowledge-cards/checkpoint/) | 失敗後從哪裡接續              | 記錄 partition、offset、run id     |
| Stop loss                                     | 哪些訊號要暫停                | error rate、成本、row count 異常   |
| Reconcile                                     | 補算結果如何確認              | 新舊輸出比對、抽樣、business check |

這些控制項要寫進 workflow 或 runbook。若 backfill 只能靠工程師現場下 SQL，事故時很難保證每次操作都有相同邏輯。

## Rerun 判讀

Rerun 判讀的責任是確認重跑是否會造成二次傷害。資料任務失敗後，最危險的動作是未確認輸出語意就直接重跑。

| 訊號                    | 判讀                       | 下一步                          |
| ----------------------- | -------------------------- | ------------------------------- |
| 任務失敗但沒有輸出      | 可用同版本重跑             | 確認輸入仍可取得                |
| 部分 partition 已寫入   | 需要去重或覆寫策略         | 檢查 output mode                |
| 下游已消費錯誤輸出      | 需要通知下游或重算衍生資料 | 標記污染區間                    |
| input schema 已改       | 舊版本重跑條件可能失效     | 用相容版本或轉換層              |
| streaming checkpoint 壞 | 重跑可能重複消費或漏資料   | 評估 checkpoint repair / replay |

這張表讓 rerun 從「再跑一次」變成有條件的恢復策略。資料正確性比任務綠燈更重要；綠燈只代表 job 完成，不代表輸出可信。

## 下一步路由

- Data pipeline 部署總覽：回 [Data Pipeline 部署 CI/CD](../)。
- Migration 概念：讀 [Migration](/ci/knowledge-cards/migration/)。
- Gate 原理：讀 [CI gate 與 workflow 邊界](../../ci-gate-workflow-boundary/)。
