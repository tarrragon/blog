---
title: "6.19 Reliability Readiness Review"
date: 2026-05-02
description: "把上線前、重大變更前與高風險操作前的可靠性準備度變成可檢查門檻"
weight: 19
---

## 大綱

- reliability readiness 的責任：確認服務能承受預期流量、依賴失效、資料變更與回復壓力
- 檢查面向：SLO、capacity、dependency、rollback、data migration、on-call、runbook
- 上線前門檻：核心路徑有 SLI、load test、rollback path、owner 與 alert
- 重大變更門檻：migration、feature flag、dependency change、config rollout 的風險判讀
- 高風險操作門檻：手動修資料、批次任務、backfill、區域切換
- 跟 04 的交接：缺少訊號時回到 observability readiness
- 跟 08 的交接：缺少事故節奏時回到 drills / runbook lifecycle
- 反模式：release gate 只看 CI 綠燈；沒有 rollback rehearsal；容量假設沒有驗證

Reliability readiness review 的核心價值是把「上線前風險」前移成可討論的工程語言。只靠測試通過不代表服務可在真實流量與依賴波動下維持穩定，readiness 讓團隊在變更前先明確回答容量、回復、資料與值班四個問題。

## 概念定位

Reliability readiness review 是把可靠性準備度轉成可檢查門檻的流程，責任是在服務承受 production 壓力前先找出可預期失效。

這一頁處理的是準備度。readiness 要把訊號、容量、依賴、回復、資料與值班能力放在同一張檢查表中判讀。

readiness 的目標是提高發布品質。當缺口被提前看見，團隊可以選擇補驗證、縮小範圍、延後發布或先加保護措施，避免把不確定性直接帶進 production。

## 核心判讀

判讀 reliability readiness 時，先看服務的核心失敗模式是否已被驗證，再看回復路徑是否可執行。

重點訊號包括：

- 核心 user journey 是否有 SLO、load baseline 與 alert
- 主要 dependency 是否有 timeout、fallback 與 degradation plan
- rollback / failover 是否有演練紀錄
- migration / backfill 是否有停止條件與資料校驗
- on-call 是否有 runbook、owner 與 escalation policy

| 檢查面向 | 最小可用判準                     | 常見風險                   |
| -------- | -------------------------------- | -------------------------- |
| 服務健康 | 核心旅程有 SLO 與 alert          | 只看系統資源，忽略用戶結果 |
| 容量邊界 | 有 load baseline 與容量餘裕      | 流量上升時才發現瓶頸       |
| 回復路徑 | rollback / failover 有演練紀錄   | 事故現場才第一次走流程     |
| 資料操作 | migration 有校驗與停止條件       | 補資料操作擴大影響面       |
| 值班準備 | on-call 有 runbook 與 escalation | 事故當下才建立協作節奏     |

## 判讀訊號

- 上線前只看 unit / integration test，沒有容量與回復判準
- 依賴失效時只能現場討論 fallback
- migration 執行前沒有 rollback rehearsal
- 服務 owner 需要臨場補 RTO / RPO 或核心 SLO
- on-call 第一次接觸 runbook 是事故當下

典型情境是服務通過 CI 與 integration test 就上線，結果在流量尖峰時 dependency timeout 連鎖放大。若前一輪 readiness 已要求 load baseline、fallback 驗證與 rollback rehearsal，這類事故通常會降級成可控風險，維持在局部範圍。

## 交接路由

- 04.16 observability readiness：確認訊號可支援 readiness 判讀
- 06.2 load test：補容量與吞吐驗證
- 06.7 DR / rollback rehearsal：補回復路徑演練
- 06.8 release gate：把 readiness 結果變成放行條件
- 08.6 drills / on-call readiness：補值班與事故演練
