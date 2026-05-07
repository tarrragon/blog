---
title: "0.13 操作控制 vertical slice 實作入口"
date: 2026-05-07
description: "用一個服務串起觀測證據、可靠性驗證、事故決策與回寫閉環"
weight: 13
tags: ["backend", "vertical-slice", "observability", "reliability", "incident-response"]
---

操作控制 vertical slice 的核心責任是把「看得見、驗得過、接得住、回寫得動」落到同一個服務流程。這一章把 [evidence package](/backend/knowledge-cards/evidence-package/)、[steady state](/backend/knowledge-cards/steady-state/)、[incident decision log](/backend/knowledge-cards/incident-decision-log/) 與 action item closure 串成第一個可實作切片。

## 大綱

- 實作目標：選一個核心 user journey，建立最小操作控制閉環
- 輸入：服務入口、核心依賴、SLO / SLI、告警、驗證場景、事故流程
- 產出：evidence package、verification evidence handoff、incident decision log、write-back item
- 邊界：先做 artifact 與路由，工具與語言實作留給 04 / 06 / 08 與語言教材
- 驗收：能從一次異常走完 triage、verification、decision、write-back

## 實作目標

Vertical slice 的目標是先做一條可回放的操作控制路徑。選一個核心 user journey，例如 checkout、message delivery、document publish、login 或 invoice generation，讓這條路徑同時具備觀測證據、驗證門檻、事故決策與回寫機制。

這一輪的交付是 artifact 與流程責任。工具可以是現有 log search、dashboard、ticket、runbook repository 與 chat；重點是資料欄位與流程責任先成立，後續才判斷是否需要 Prometheus、OpenTelemetry backend、PagerDuty、incident.io 或 chaos tooling。

## 選擇服務切片

服務切片的選擇責任是找到最能暴露 04 / 06 / 08 交接問題的路徑。第一條 slice 應該具備使用者影響、依賴邊界、可量測訊號與可驗證失敗模式。

| 候選切片         | 適合原因                     | 常見失敗模式                   |
| ---------------- | ---------------------------- | ------------------------------ |
| Checkout         | 直接連到收入與客戶痛點       | payment timeout、inventory lag |
| Message delivery | 同時包含同步入口與非同步處理 | queue lag、redelivery loop     |
| Login            | 影響所有後續功能             | identity provider outage       |
| Document publish | 涵蓋寫入、背景工作與通知     | stale read、worker backlog     |
| Invoice          | 牽涉正確性與客戶信任         | duplicate charge、missing file |

Checkout 適合第一輪，因為它同時暴露 latency、dependency failure、customer impact 與 rollback decision。若團隊沒有交易路徑，可以選 message delivery 或 login；判準是這條路徑一旦失效，on-call 需要在 15 分鐘內做出明確決策。

Message delivery 適合用來驗證 async observability。它能暴露 request id、correlation id、queue lag、DLQ、retry policy 與 replay runbook 的交接品質。

Login 適合用來驗證外部依賴事故。它能暴露 identity provider、fallback、status page、security split 與 customer communication 的邊界。

## Artifact 契約

Artifact 契約的責任是讓每個環節都有可交接輸出。這些 artifact 可以先用 Markdown、ticket 欄位或 incident template 表達，等流程跑通後再導入工具自動化。

| Artifact                       | 最小欄位                                                                           | 來源章節                                                            | 下游使用                         |
| ------------------------------ | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------- |
| Observability evidence package | source、time range、query link、owner、data quality、confidence、known gap         | [4.20](/backend/04-observability/observability-evidence-package/)   | triage、release gate、PIR        |
| Verification evidence handoff  | hypothesis、scope、steady state、workload / fault、result、decision、owner         | [6.23](/backend/06-reliability/verification-evidence-handoff/)      | release gate、runbook、drill     |
| Incident decision log          | timestamp、decision、context、evidence、owner、expected effect、rollback condition | [8.19](/backend/08-incident-response/incident-decision-log/)        | handoff、stakeholder update、PIR |
| Incident evidence write-back   | finding、evidence、target artifact、owner、closure signal、review date             | [8.22](/backend/08-incident-response/incident-evidence-write-back/) | dashboard、experiment、runbook   |

Observability evidence package 是第一個 artifact。它保存查詢、時間窗、資料品質與 owner，讓後面的驗證與事故流程使用同一組事實。

Verification evidence handoff 是第二個 artifact。它把一次 load test、chaos drill、DR rehearsal 或 readiness review 的結果轉成 release gate 與 incident drill 可用的證據。

Incident decision log 是第三個 artifact。它把事中決策、證據、預期效果與回退條件保存下來，讓交班與復盤可以直接引用。

Incident evidence write-back 是第四個 artifact。它把事故學習轉成 dashboard、alert、SLO、experiment、runbook 或 automation boundary 的修改項。

## 實作步驟

實作步驟的責任是讓 slice 能被單次演練走完。每一步都產生一個可檢查輸出，避免流程只停在口頭共識。

1. 選定服務切片與核心 user journey。
2. 定義 steady state：success rate、latency、queue lag、data correctness、customer impact。
3. 補 observability evidence package：dashboard、query、trace、log、audit、data quality。
4. 補 verification evidence handoff：load、chaos、DR 或 rollback rehearsal 的 hypothesis 與 result。
5. 建 incident intake template：source、confidence、impact scope、evidence link、severity candidate。
6. 建 incident decision log template：decision、owner、expected effect、rollback condition。
7. 建 write-back template：finding、target artifact、closure signal、review date。
8. 跑一次 tabletop 或 game day，確認 artifact 能被實際填寫。
9. 把缺口回寫到 04 readiness、06 experiment 或 08 runbook。

第一步要避免選太大的系統。選「checkout」比選「整個支付平台」更好，因為 slice 需要在一輪演練中跑完。

第二步要先定義穩態。沒有 steady state，load test、chaos 與 incident recovery 都會缺少共同終點。

第三步要保留 data quality 限制。若 trace sampling、log drop 或 metric ingest delay 會影響判讀，限制要跟 evidence 一起交接。

第四步要把驗證結果變成下游可用語言。Pass、conditional、fail 都要附上 scope、hypothesis 與下一步路由。

第五到第七步要先用輕量 template。template 跑通後，再把欄位搬進 incident tool、ticket system 或 runbook platform。

第八步要實際演練。tabletop 可以先驗證欄位與角色，game day 再驗證工具與訊號。

## 最小 template

最小 template 的責任是讓第一輪不用等待工具導入。以下欄位可以直接放進 Markdown、ticket、incident doc 或 runbook。

```yaml
service_slice:
  journey: checkout
  owner: payments-team
  steady_state:
    success_rate: ">= 99.9% over 30m"
    latency: "p95 <= 800ms"
    queue_lag: "<= 5m"
    customer_impact: "failed checkout count <= threshold"

evidence_package:
  source: "dashboard / log query / trace / audit"
  time_range: "incident window plus baseline"
  query_link: "stable query URL or saved query name"
  owner: "service or platform owner"
  data_quality: "sampling, freshness, missing fields"
  confidence: "confirmed / suspected / weak"
  known_gap: "missing signal or schema drift"

verification_handoff:
  hypothesis: "payment provider timeout triggers fallback within 2m"
  scope: "staging or 10% production traffic"
  workload_or_fault: "timeout injection against provider adapter"
  result: "pass / conditional / fail"
  decision: "release / block / follow-up / runbook update"
  owner: "closure owner"

incident_decision:
  timestamp: "2026-05-07T10:15:00Z"
  decision: "enable checkout fallback"
  context: "provider timeout and rising failed checkout"
  evidence: "evidence_package link"
  owner: "incident commander or service owner"
  expected_effect: "failed checkout drops within 10m"
  rollback_condition: "fallback stale data exceeds threshold"

write_back:
  finding: "provider timeout alert lacks tenant dimension"
  target_artifact: "dashboard / alert / experiment / runbook"
  closure_signal: "game day triggers tenant-scoped alert within 5m"
  review_date: "next readiness review"
```

這份 template 的價值是把四個 artifact 放在同一份文件中。第一輪可以手動填寫，第二輪再拆到不同工具。

## 驗收門檻

驗收門檻的責任是判斷 slice 是否已經能支援實際事故。完成狀態要由團隊能否沿著 artifact 做出同一組判斷來確認。

| 驗收項目      | 通過訊號                               | 回寫位置          |
| ------------- | -------------------------------------- | ----------------- |
| Triage        | on-call 能用 evidence 判斷是否啟動事故 | 8.18 intake       |
| Verification  | release owner 能讀 handoff 做放行判斷  | 6.8 release gate  |
| Decision      | IC 能用 decision log 交班與回退        | 8.19 decision log |
| Communication | stakeholder update 能引用同一組 impact | 8.10 comms        |
| Write-back    | PIR action item 有 target 與 closure   | 8.22 write-back   |

Triage 通過代表 evidence 能支援事故啟動。若 on-call 還需要臨場重新找資料，回到 4.16 readiness 與 4.20 evidence package。

Verification 通過代表驗證結果能支援 release 決策。若 release owner 只看到 pass / fail，回到 6.23 handoff 補 hypothesis、scope 與 data quality。

Decision 通過代表事故現場有共同記憶。若交班後需要重問背景，回到 8.19 decision log 補 context、evidence 與 rollback condition。

Write-back 通過代表事故學習有落點。若 action item 只有「補監控」或「更新文件」，回到 8.22 write-back 補 target artifact 與 closure signal。

## Tripwire

Tripwire 的責任是提醒團隊何時回到概念層補缺口。Vertical slice 的目的在於快速暴露 routing chain 哪裡斷掉，再用最小修正補上 artifact 與 owner。

| 訊號                   | 判讀                      | 下一步                                           |
| ---------------------- | ------------------------- | ------------------------------------------------ |
| evidence 找不到 owner  | 觀測 operating model 缺口 | 回到 4.18 owner 與 review cadence                |
| pass / fail 缺少決策力 | verification handoff 缺口 | 回到 6.23 補 scope、hypothesis、decision         |
| IC 交班缺少共同記憶    | decision log 缺口         | 回到 8.19 補最近決策、未完成動作與 rollback 條件 |
| PIR action 缺少關閉力  | write-back 缺口           | 回到 8.22 補 closure signal 與 review date       |
| template 填寫成本過高  | 欄位過多或工具摩擦        | 刪到最小欄位，再跑一次 tabletop                  |

這些 tripwire 出現時，先修 artifact 與流程，再考慮導入新工具。工具能降低填寫成本，但欄位責任與 owner 需要先清楚。

## 交接路由

- [0.12 operations control service selection](/backend/00-service-selection/operations-control-service-selection/)：判斷目前缺的是訊號、驗證、響應還是閉環。
- [4.20 observability evidence package](/backend/04-observability/observability-evidence-package/)：建立可交接觀測證據。
- [6.22 steady state definition](/backend/06-reliability/steady-state-definition/)：定義實驗與事故共用成功條件。
- [6.23 verification evidence handoff](/backend/06-reliability/verification-evidence-handoff/)：把驗證結果交給 release 與 incident。
- [8.19 incident decision log](/backend/08-incident-response/incident-decision-log/)：保存事中決策與回退條件。
- [8.22 incident evidence write-back](/backend/08-incident-response/incident-evidence-write-back/)：把事故學習回寫成可關閉改善。
