---
title: "5.8 Deployment Rollout with Drain and Rollback（實作示範）"
date: 2026-05-11
description: "以 checkout service 示範部署切換如何交付 canary evidence、drain signal、release gate 與 incident decision log。"
weight: 8
tags: ["backend", "deployment", "implementation", "rollout", "incident"]
---

Deployment rollout with drain and rollback 的核心責任是把版本、流量、連線、設定與回退條件拆成可驗證批次。這篇以 checkout service 為例，示範平台切換如何從 preflight、canary、drain 到事故回退都保留一致證據。

## 服務路徑與切換責任

這條路徑是 `client -> load balancer -> checkout-api -> payment provider/order db/order event`。部署期間新舊版本會同時承接流量，核心風險在流量生命週期是否可收斂，image 替換本身反而是最可預測的部分。

切換責任分三層：

1. 版本可啟動：container/runtime/config 可用。
2. 版本可接流量：readiness 與依賴狀態對齊。
3. 版本可退場：drain 與在途請求可收束。

## Preflight：先驗證可服務基線

Preflight 的責任是把「可啟動」與「可服務」拆開驗證。最小檢查包含：

1. image 與 runtime config 版本對齊。
2. secret 已注入且權限正確。
3. startup/readiness probe 能反映真實依賴狀態。
4. [load balancer contract](/backend/knowledge-cards/load-balancer-contract/) 參數與服務期望一致。
5. service discovery 註冊與摘除路徑可用。

Preflight 失敗時不進 canary。先把失敗收斂在控制面，避免切流後才發現版本不可服務。

## Canary Batch 與 Stop Condition

小流量先驗證新版本行為，再決定是否擴批——Canary 回答的是「這個版本值不值得擴大」。

| 批次階段 | 判讀重點                                     | 停損條件                       |
| -------- | -------------------------------------------- | ------------------------------ |
| 1-5%     | per-version error rate、p95/p99 latency      | 錯誤率高於基線、延遲持續惡化   |
| 10-25%   | payment dependency timeout、fallback 比例    | 依賴 timeout 連續超門檻        |
| 50%      | drain 成功率、reconnect 波形、下游事件完整性 | drain 未完成或 reconnect storm |
| 100% 前  | 新舊版本差異是否收斂、rollback 可行性        | 仍需依賴舊版本特殊路徑         |

canary 判讀要維持 per-version 視角。只看整體服務平均值會掩蓋新版本局部退化。

## Traffic / Drain：把退場變成可驗證流程

Drain 的責任是讓舊版本在下線前完成在途請求，不讓 rollout 把短暫切換放大成用戶錯誤。

退場順序：

1. 舊實例 readiness 先轉 `not-ready` 停接新流量。
2. 保留 drain 窗口完成 [in-flight](/backend/knowledge-cards/in-flight/) request。
3. 確認連線數下降到門檻後再終止進程。
4. 驗證無異常 reconnect 尖峰再進下一批。

Drain 條件的完整 workload 分類回到 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/)，本段以 checkout service 為例：短 API 的 [draining](/backend/knowledge-cards/draining/) 窗口可短，長輪詢與 webhook callback 要更保守。

## Rollback Compatibility

舊版本回來時仍可運作，是 rollback 能成立的前提——回退如果變成第二次故障，就失去了回退的工程價值。

要先驗證四個相容面：

1. config 相容：新設定不會讓舊版啟動失敗。
2. schema 相容：資料結構仍可被舊版讀取。
3. cache key 相容：舊版可讀新快取或有 fallback。
4. event schema 相容：舊版 consumer 不會因新事件欄位崩潰。

若這四項未完成，所謂 rollback 只會停在「版本回切」，無法恢復服務正確性。

## Evidence Package

每一批切換要可被判讀、可被追責、可被回放——部署 evidence 支撐這三個條件。

| 欄位                                                   | 內容                                                          |
| ------------------------------------------------------ | ------------------------------------------------------------- |
| Source                                                 | deployment logs、LB metrics、service metrics、dependency logs |
| [Time range](/backend/knowledge-cards/time-range/)     | 每批 rollout/drain 觀察窗口                                   |
| [Query link](/backend/knowledge-cards/query-link/)     | per-version error、latency、5xx、timeout、drain completion    |
| Owner                                                  | platform owner、checkout owner、SRE on-call                   |
| [Data quality](/backend/knowledge-cards/data-quality/) | 指標延遲、分區覆蓋、log 掉點                                  |
| [Confidence](/backend/knowledge-cards/confidence/)     | confirmed / suspected / needs follow-up                       |
| [Known gap](/backend/knowledge-cards/known-gap/)       | 尚未覆蓋長連線場景、低流量區域樣本不足                        |

這份 evidence 要對齊 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。

## Release Gate

Release gate 的責任是決定下一批切換與是否凍結 rollout，不是報告「目前看起來正常」。

| Gate 欄位                                                | 最小內容                                                                            |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| [Gate decision](/backend/knowledge-cards/gate-decision/) | 放行下一批、維持 canary、freeze rollout、rollback version                           |
| Checks                                                   | per-version SLI、dependency timeout、drain completion                               |
| Stop condition                                           | error [burn rate](/backend/knowledge-cards/burn-rate/)、reconnect storm、drain 逾時 |
| Rollback window                                          | 可回切時間、舊版可服務窗口、config 回退窗口                                         |
| Owner                                                    | release owner、platform on-call                                                     |

這組欄位要對齊 [6.8 Release Gate](/backend/06-reliability/release-gate/)。

## Incident Decision Log

freeze rollout、rollback version、隔離 region、延長 drain 都屬事故決策，需寫入 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。涉及流量規則 / [control plane](/backend/knowledge-cards/control-plane/) 設定推送的決策、見 [5.7](/backend/05-deployment-platform/traffic-config-control-plane-boundary/) 跟 [8.23 Control Plane Decision Log](/backend/08-incident-response/control-plane-decision-log-write-back/)。

```yaml
incident_decision:
  timestamp: 2026-05-11T15:06:00Z
  decision: "freeze rollout at 25% and rollback one region"
  context: "new version timeout to payment provider increased in ap-northeast"
  evidence:
    - query: checkout_error_rate_by_version_region
    - query: payment_timeout_ratio_by_region
  owner: release-incident-commander
  expected_effect: "contain customer impact and restore baseline success rate"
  rollback_condition: "timeout ratio does not recover after rollback batch completes"
```

## Case Write-back 與邊界

這篇回寫對齊 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)、[5.C1 Tradeshift](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/) 與 [5.C3 Orbitera](/backend/05-deployment-platform/cases/orbitera-managed-kubernetes-migration/)：前者看切換失序，後兩者看遷移路徑與回退策略。preflight / canary / drain 各階段的生命週期定義回到 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/)。

這篇不處理 schema migration 本身、cache stampede 或 queue replay。若核心風險在資料正式狀態、快取回源或事件恢復，路由到 [1.7 Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/)、[2.9 Cache Migration 與 Stampede Rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/) 或 [3.8 Queue Consumer Retry 與 Replay Handoff](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)。
