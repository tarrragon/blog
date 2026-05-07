---
title: "後端部署 CI/CD"
date: 2026-05-06
description: "整理 API、worker、資料庫 migration、rollout、rollback 與 runtime 設定在後端部署 CI/CD 中的責任"
tags: ["CI", "CD", "backend", "deployment"]
weight: 11
---

後端部署 CI/CD 的核心責任是把可執行服務安全推進到 runtime 環境。後端部署不只發布程式碼，還要處理資料庫 [Migration](/ci/knowledge-cards/migration/)（backend 深入見 [Migration](/backend/knowledge-cards/migration/)）、外部依賴、runtime config、[Readiness / Health Check](/ci/knowledge-cards/readiness-health-check/)（backend 深入見 [Readiness](/backend/knowledge-cards/readiness/) / [Health Check](/backend/knowledge-cards/health-check/)）、流量切換與 rollback。

## 場域定位

後端部署的主要風險來自有狀態依賴與長時間執行。API、worker、scheduler 與 consumer 會連到資料庫、queue、cache 與第三方服務；部署流程需要確認程式、資料與流量切換順序。

| 面向                                                        | 後端部署常見責任                               | 判讀訊號                    |
| ----------------------------------------------------------- | ---------------------------------------------- | --------------------------- |
| Build                                                       | binary、package、container image               | build 是否可重現            |
| Test                                                        | unit、integration、contract、migration         | 是否覆蓋跨服務契約          |
| [Migration](/ci/knowledge-cards/migration/)                 | schema change、backfill、rollback path         | 是否可漸進、可停止、可驗證  |
| [Rollout Strategy](/ci/knowledge-cards/rollout-strategy/)   | rolling、canary、blue-green                    | health / readiness 是否可信 |
| [Rollback Strategy](/ci/knowledge-cards/rollback-strategy/) | app rollback、migration rollback / forward fix | 回復路徑是否演練            |

Build 階段負責產生可部署服務。後端 build 常見形式是 binary、package 或 container image；判讀重點是版本是否能追到 commit、依賴是否固定、產物是否能在乾淨環境重建。

Test 階段負責驗證服務契約。單元測試只能覆蓋局部邏輯，integration、contract 與 migration 測試才會揭露資料庫、queue、cache 與外部服務之間的相容性風險。

[Migration](/ci/knowledge-cards/migration/) 階段負責推進資料結構與資料狀態。真實服務要支援新舊程式短暫共存，因此 migration 應偏向可漸進、可重試、可觀測，必要時用 forward fix 取代直接回滾資料。

[Rollout Strategy](/ci/knowledge-cards/rollout-strategy/) 階段負責把流量安全導向新版本。Rolling、canary 與 blue-green 都需要可靠的 health、readiness、metrics 與 log；若 readiness 只檢查 process alive，流量仍可能被送到尚未準備好的服務。

[Rollback Strategy](/ci/knowledge-cards/rollback-strategy/) 階段負責在新版本失效時縮小影響範圍。後端 rollback 要同時考慮程式、資料、queue message、外部 side effect 與 config；只回退 image tag，通常不足以處理已寫入的資料變化。

## 常見注意事項

- Migration 要和 app rollout 分開設計，避免新舊版本不相容。
- Health check 只代表 process alive，readiness 才能判斷能否接流量。
- Worker / consumer 部署要考慮重複處理、[idempotency](/backend/knowledge-cards/idempotency/) 與 [consumer lag](/backend/knowledge-cards/consumer-lag/)。
- Config rollout 需要版本化與回退路徑（深入見 [Config Rollout](/backend/knowledge-cards/config-rollout/)）。
- Rollback 不只回程式，也要處理資料與外部副作用（深入見 [Rollback Strategy](/backend/knowledge-cards/rollback-strategy/)）。

## 下一步路由

- Gate 原理：讀 [CI gate 與 workflow 邊界](../ci-gate-workflow-boundary/)。
- Backend reliability：讀 [模組六：可靠性驗證流程](/backend/06-reliability/)。
- Release gate：讀 [6.8 Release Gate 與變更節奏](/backend/06-reliability/release-gate/)。
