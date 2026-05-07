---
title: "6.23 Verification Evidence Handoff"
date: 2026-05-02
description: "把 SLO、load、chaos、DR 與 readiness 結果包成 release / incident 可用證據"
weight: 23
---

## 大綱

- verification evidence handoff 的責任：把可靠性驗證結果交給 release gate、runbook 與 incident response
- 來源：SLO policy、load test、chaos experiment、DR drill、rollback rehearsal、readiness review
- 欄位：hypothesis、steady state、result、scope、evidence package、decision、owner、next route
- 跟 4.20 的關係：使用同一 evidence package 格式承接 observability 證據
- 跟 8.22 的關係：事故復盤會回寫新的驗證題目與證據缺口
- 反模式：驗證做完只留結論；load test 圖表沒有 workload；chaos 成功但沒有 runbook 回寫

Verification evidence handoff 的核心是把可靠性驗證從「做過測試」升級成「留下可用證據」。驗證結果需要能進 release gate、runbook、incident drill 與 post-incident review，才會形成跨模組閉環。

## 概念定位

Verification evidence handoff 是可靠性模組交給發布與事故流程的證據交接，責任是讓 SLO、load、chaos、DR 與 readiness 結果能被決策使用。

這一頁處理的是驗證結果的交付格式。6.20 定義實驗安全邊界，6.22 定義 [steady state](/backend/knowledge-cards/steady-state/)；本章把這些驗證輸出整理成可以被 05 release、08 incident response 與 04 observability 回寫使用的 artifact。

驗證證據的價值在於支援未來決策。一次 load test 的圖表、一次 chaos 成功、一次 DR drill 通過，如果沒有 hypothesis、scope、steady state、[evidence package](/backend/knowledge-cards/evidence-package/) 與 action item，後續團隊很難知道它證明了什麼。

## Handoff 欄位

Verification evidence handoff 的欄位要同時保存驗證前提、觀測證據與決策結果。欄位的目標是讓下游能判斷「這個驗證能支持哪個決策」。

| 欄位             | 責任                           | 判讀用途                     |
| ---------------- | ------------------------------ | ---------------------------- |
| Hypothesis       | 說明要驗證的 failure mode      | 判斷實驗是否回答原問題       |
| Scope            | 標示服務、tenant、region 範圍  | 防止把局部結果外推           |
| Steady state     | 定義成功條件                   | 判斷是否通過                 |
| Workload / Fault | 記錄流量模型或故障注入         | 支援重播                     |
| Evidence package | 連到 log、metric、trace        | 支援查證與 handoff           |
| Result           | pass、conditional、fail        | 接 release gate 與 readiness |
| Decision         | 放行、阻擋、補驗證、補 runbook | 把結果轉成動作               |
| Owner            | 指定後續責任人                 | 支援 action item closure     |

Hypothesis 欄位讓驗證聚焦。`打掉 node` 只是操作；`打掉一個 worker 後 queue lag 應在 10 分鐘內回到 baseline` 才是可判讀假設。

Scope 欄位保護結論邊界。internal traffic、single tenant、one region、10% production traffic 與 full production 都是不同證據強度，handoff 需要明確標示。

Evidence package 欄位接 4.20。驗證結果應保存 dashboard、query、trace、log、client-side signal、time range 與 data quality 限制，讓 release gate 或 incident response 可以回放。

Result 欄位需要分層。Pass 代表在指定 scope 內符合 steady state；conditional 代表可接受但有缺口；fail 代表需要補設計、補訊號、補 runbook 或阻擋 release。

## 驗證來源

Verification evidence 的來源分成政策、容量、故障、回復與準備度。不同來源回答的決策問題不同。

| 來源               | 回答問題                        | 交接對象                       |
| ------------------ | ------------------------------- | ------------------------------ |
| SLO / Error Budget | 可靠性目標是否仍有風險餘額      | release gate、severity trigger |
| Load test          | workload 是否覆蓋容量與成本壓力 | capacity plan、release gate    |
| Chaos experiment   | failure mode 是否可被吸收       | runbook、incident drill        |
| DR drill           | RTO / RPO 是否可達              | business continuity、IR        |
| Rollback rehearsal | 版本或資料回復是否可執行        | deployment platform、incident  |
| Readiness review   | 上線前風險是否已被判讀          | release gate、service owner    |

SLO evidence 適合支援變更節奏。當 burn rate 上升或 error budget 緊張，release gate 需要知道哪些 user journey 受影響、資料品質是否可信、freeze 是否觸發。

Load test evidence 適合支援容量與成本決策。它要保留 workload model、traffic shape、data volume、dependency saturation、cost threshold 與觀測限制。

Chaos evidence 適合支援 incident drill。它要保留 injected failure、steady state、stop condition、blast radius、[decision log](/backend/knowledge-cards/incident-decision-log/) 與 action item。

DR evidence 適合支援恢復承諾。它要保留切換步驟、資料同步、RTO / RPO、權限、通訊節奏與回復完成條件。

Rollback evidence 適合支援事故止血。它要保留版本、migration、feature flag、client compatibility、cache 與資料相容性。

## 交接流程

Verification handoff 的流程是從驗證結果走向下游決策。每個結果都要明確路由，讓測試報告轉成 release、runbook 或 incident drill 的輸入。

1. 把驗證結果整理成 handoff 欄位。
2. 附上 4.20 evidence package 與 data quality 限制。
3. 判斷 result：pass、conditional、fail。
4. 把 pass 送入 release gate 或 runbook。
5. 把 conditional 送入 reliability debt 或 follow-up。
6. 把 fail 送入 block、補驗證、補 observability 或 incident drill。

Pass 的責任是支持後續放行。Pass 需要同時保留 scope，避免「小範圍通過」被誤用成「全域安全」。

Conditional 的責任是保留風險借款。若驗證結果可接受但缺 trace、runbook、owner 或資料校驗，應進入 reliability debt backlog，並設定 closure signal。

Fail 的責任是阻止風險下流。Fail 不只代表測試失敗，也可能代表 steady state 定義錯誤、evidence 不足、blast radius 過大或 stop condition 不清。

## 常見反模式

Verification evidence handoff 的反模式通常來自把驗證結果寫成結論，而沒有保留判讀過程。下游需要知道結論成立的條件。

| 反模式                 | 表面現象                | 修正方向                          |
| ---------------------- | ----------------------- | --------------------------------- |
| 只寫 pass / fail       | release gate 看不到證據 | 補 hypothesis、scope、evidence    |
| Load 圖表缺 workload   | 圖表存在但缺少重播條件  | 保存 traffic shape 與 data volume |
| Chaos 成功無 runbook   | 實驗有效但事故時用不上  | 回寫 runbook 與 drill             |
| DR 通過缺 RTO / RPO    | 切換完成但缺少承諾對齊  | 保存 recovery timeline            |
| Conditional 無關閉條件 | 風險借款長期存在        | 設定 owner 與 closure signal      |

只寫 pass / fail 會讓驗證證據失去工程價值。Pass 要說明在什麼範圍、什麼假設、什麼資料品質下成立；fail 要說明哪個控制面失效。

Conditional 無關閉條件會讓可靠性債累積。每個 conditional handoff 都需要 owner、期限、closure signal 與重新評估條件。

## 交接路由

- 4.20 observability evidence package：承接 log、metric、trace 與 data quality
- 6.8 release gate：把驗證結果轉成放行、阻擋或例外
- 6.20 experiment safety：保存 blast radius、stop condition 與權限
- 6.21 reliability debt backlog：承接 conditional 與 follow-up
- 8.6 drills / on-call readiness：把驗證結果轉成值班演練
- 8.22 incident evidence write-back：承接事故後新增的驗證題目
