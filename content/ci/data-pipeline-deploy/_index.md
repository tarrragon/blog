---
title: "Data Pipeline 部署 CI/CD"
date: 2026-05-06
description: "整理 ETL / stream / batch 任務的部署、回填、重跑與資料正確性 gate"
tags: ["CI", "CD", "data-pipeline", "deployment"]
weight: 15
---

Data Pipeline 部署 CI/CD 的核心責任是把資料處理邏輯推進到生產環境，同時維持資料正確性與可回復性。它和 API 部署不同，重點在 schema 相容、backfill、checkpoint 與重跑風險。

## 場域定位

Data pipeline 常包含 batch job、stream processor、dbt model 或 workflow scheduler。部署判斷不只看程式可執行，還要看資料是否可追溯、可對帳、可修復。

| 面向       | Data pipeline 部署常見責任               | 判讀訊號                     |
| ---------- | ---------------------------------------- | ---------------------------- |
| Build      | transform code、DAG、query model         | 版本是否可重現               |
| Validation | schema check、sample run、contract check | 輸出是否維持相容             |
| Deploy     | job version、schedule、trigger           | 新流程是否正確接管           |
| Backfill   | 歷史資料補算與節流                       | 是否有 checkpoint 與停損條件 |
| Recovery   | rerun、rollback、forward fix             | 異常資料是否可修補           |

## 常見注意事項

- schema 變更要先定義相容窗口，再切換 downstream。
- backfill 要有節流與 checkpoint，避免壓垮上游與儲存層。
- 部署後需比對新舊輸出一致性，建立 correctness check。
- 重跑流程要有 runbook，避免人工臨場判斷失誤。

## 下一步路由

- 後端資料遷移概念：讀 [Migration](/backend/knowledge-cards/migration/)。
- 資料修補與比對：讀 [Backfill](/backend/knowledge-cards/backfill/) 與 [Correctness Check](/backend/knowledge-cards/correctness-check/)。
- Gate 原理：讀 [CI gate 與 workflow 邊界](../ci-gate-workflow-boundary/)。
