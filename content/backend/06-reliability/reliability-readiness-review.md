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

## Readiness 範圍

Reliability readiness review 的範圍是服務進入 production 壓力前需要具備的最低可靠性條件。它不取代 CI、load test、release gate 或 incident drill，而是把這些控制面接成同一個放行判斷。

| 範圍     | 核心問題                       | 對應控制面                       |
| -------- | ------------------------------ | -------------------------------- |
| 服務健康 | 核心旅程是否有可靠性目標       | SLO、SLI、burn rate              |
| 容量     | 預期流量與尖峰是否被驗證       | load test、capacity model        |
| 依賴     | 下游失效是否有 timeout 與降級  | dependency budget、fallback      |
| 資料     | migration、backfill 是否可校驗 | migration safety、test data      |
| 回復     | rollback、failover 是否可執行  | DR rehearsal、rollback rehearsal |
| 操作     | on-call 是否知道如何接住事故   | runbook、escalation、drill       |

服務健康是 readiness 的第一層。核心 user journey 需要有 SLO、dashboard、alert 與 owner，讓團隊知道「服務是否仍在承諾範圍內」。

容量是 readiness 的第二層。load baseline、throughput ceiling、queue lag、dependency saturation 與 cost threshold 都需要在上線前被看見，避免第一個尖峰才揭露瓶頸。

依賴是 readiness 的第三層。每個關鍵 downstream 都需要 timeout、deadline、retry、fallback、circuit breaker 或 degradation plan，讓局部失效維持在可控範圍。

資料是 readiness 的第四層。schema migration、backfill、online migration 與資料修復需要校驗、停止條件、rollback 或補償流程，讓資料風險能被事前判讀。

操作是 readiness 的最後一層。runbook、owner、escalation policy、incident intake 與 [decision log](/backend/knowledge-cards/incident-decision-log/) 讓服務在失效時能被團隊接住。

## Review 流程

Reliability readiness review 的流程是從風險清單走向放行判斷。每個缺口都要被分類為阻擋、降級接受或後續改善，讓發布決策有清楚路由。

1. 定義本次上線或變更的服務承諾。
2. 列出核心 failure mode、dependency、資料操作與回復路徑。
3. 檢查 04 訊號是否足以支援判讀。
4. 檢查 06 驗證是否足以支援放行。
5. 檢查 08 值班與事故流程是否能接住失效。
6. 對每個缺口指定 owner、處理路由與重新評估條件。

服務承諾是 readiness review 的錨點。若本次變更影響 checkout、payment、message delivery 或 tenant migration，review 就要圍繞這些旅程的可靠性承諾，並把程式碼合併狀態視為其中一個輸入。

Failure mode 清單需要具體。依賴 timeout、queue lag、cache stampede、migration lock、feature flag misrouting、region failover 與 data reconciliation 都是不同失效模式，對應不同驗證與回復路由。

04 訊號是 readiness 的前提。若缺少 SLI、trace、log correlation 或 telemetry data quality，可靠性 review 只能停在推測；這類缺口應先回到 04.16 與 04.17。

08 流程是 readiness 的接手面。若 on-call 沒有 runbook、incident commander 不清楚啟動條件、status update 沒有節奏，可靠性缺口會在事故時轉成協作壓力。

## 判讀訊號

- 上線前只看 unit / integration test，沒有容量與回復判準
- 依賴失效時只能現場討論 fallback
- migration 執行前沒有 rollback rehearsal
- 服務 owner 需要臨場補 RTO / RPO 或核心 SLO
- on-call 第一次接觸 runbook 是事故當下

典型情境是服務通過 CI 與 integration test 就上線，結果在流量尖峰時 dependency timeout 連鎖放大。若前一輪 readiness 已要求 load baseline、fallback 驗證與 rollback rehearsal，這類事故通常會降級成可控風險，維持在局部範圍。

## 放行判斷

Reliability readiness 的放行判斷需要區分「阻擋上線」與「帶限制上線」。這個區分讓團隊既能控制風險，也能在低風險缺口存在時保持交付節奏。

| 結果             | 判斷條件                                  | 常見動作                          |
| ---------------- | ----------------------------------------- | --------------------------------- |
| Pass             | 核心路徑、容量、回復與值班皆達標          | 正常進入 release gate             |
| Conditional pass | 缺口可被降級、人工查證或短期 runbook 承接 | 記錄限制、owner 與補齊期限        |
| Block            | 核心旅程、資料或回復路徑缺少判讀          | 暫停發布，補驗證或縮小範圍        |
| Defer            | 需求價值低於可靠性風險                    | 延後變更，先處理 reliability debt |

Pass 代表核心風險已有證據支撐。這不代表系統完美，而是代表本次發布或操作有足夠訊號、驗證與回復路由。

Conditional pass 適合處理可控缺口。例如某個低風險 batch job 缺少完整 trace，但已有 log query、manual replay 與 on-call owner，可以帶著明確限制上線。

Block 適合處理核心旅程與資料風險。payment migration 缺少 rollback rehearsal、tenant backfill 缺少校驗、核心 API 缺少 SLO alert，這些缺口會讓事故處理沒有可靠入口。

Defer 適合處理價值與風險不對稱的變更。若本次變更只是次要優化，但會暴露高風險 migration 或 dependency change，延後是合理的 reliability decision。

## 常見反模式

Reliability readiness 的反模式通常來自把測試通過視為 production 準備度。測試通過證明某些功能路徑可執行，readiness 則要證明服務能在真實壓力、依賴波動與事故流程下被接住。

| 反模式               | 表面現象                    | 修正方向                          |
| -------------------- | --------------------------- | --------------------------------- |
| CI 綠燈即上線        | 只看 test pass              | 加入 SLO、capacity、rollback 判準 |
| 容量假設無驗證       | 靠估算決定尖峰承載          | 補 load baseline 與容量餘裕       |
| Rollback 只寫文件    | 回復流程沒有演練紀錄        | 補 rollback rehearsal             |
| Migration 缺停止條件 | 執行中才判斷是否暫停        | 事前定義校驗、pause、fallback     |
| On-call 臨場接手     | 事故時才找 owner 與 runbook | 補 drill 與 escalation route      |

CI 綠燈即上線會讓可靠性停在程式正確性層。production 可靠性還包含容量、依賴、資料、回復與協作，這些條件需要各自的證據。

Rollback 只寫文件會在事故現場暴露落差。回復流程需要在類 production 條件下演練過，才能知道權限、資料、流量、相容性與通訊是否接得上。

## 與 Release Gate 的關係

Reliability readiness review 是 release gate 的上游資料。readiness 負責整理風險與證據，release gate 負責根據政策做放行、暫停、縮小範圍或例外核准。

Readiness 結果應包含三種資訊：已驗證條件、已接受限制與阻擋缺口。Release gate 只看「通過 / 失敗」會遺失判讀脈絡；保留這三類資訊才能讓發布決策可復盤。

Readiness 也應回寫 reliability debt。每次 conditional pass 都代表團隊暫時接受一個缺口；若缺口反覆被接受，就應進入 [6.21 Reliability Debt Backlog](/backend/06-reliability/reliability-debt-backlog/)。

## 交接路由

- 04.16 observability readiness：確認訊號可支援 readiness 判讀
- 06.2 load test：補容量與吞吐驗證
- 06.7 DR / rollback rehearsal：補回復路徑演練
- 06.8 release gate：把 readiness 結果變成放行條件
- 08.6 drills / on-call readiness：補值班與事故演練
