---
title: "8.22 Incident Evidence Write-back"
date: 2026-05-02
description: "把事故證據、決策與復盤結論回寫到 observability、reliability 與 runbook"
weight: 22
---

## 大綱

- evidence write-back 的責任：把事故中產生的證據、決策與學習轉成上游改善
- 輸入：incident intake、decision log、customer impact、timeline、PIR action item
- 回寫面向：observability signal、telemetry data quality、verification scenario、runbook、automation boundary
- 欄位：finding、evidence、owner、target artifact、closure signal、review date
- 跟 4.20 的關係：事故證據缺口回寫成 evidence package 與資料品質改善
- 跟 6.23 的關係：事故學習回寫成新的驗證題目與 handoff evidence
- 反模式：PIR action item 停在待辦；事故證據沒有回到 dashboard / runbook；同類事故重複發生

Incident evidence write-back 的核心是把事故學習轉成上游 artifact。事故是流程回寫點，會產生新的訊號需求、驗證題目、runbook 修訂與自動化邊界。

## 概念定位

Incident evidence write-back 是事故處理回寫到可觀測性、可靠性驗證與操作流程的閉環，責任是讓事故學習變成可驗證改善。

這一頁處理的是事故後的交接。8.18 產生 intake evidence，8.19 保留 [decision log](/backend/knowledge-cards/incident-decision-log/)，8.20 量化 customer impact；本章把這些材料轉成 04、06、08 內部可追蹤的改善 artifact。

Write-back 的價值在於避免同類事故只被記錄一次。PIR action item 若只停在待辦，下一次事故仍會遇到相同缺口；write-back 要把缺口落到 dashboard、alert、SLO、experiment、runbook 或 automation guardrail。

## 輸入材料

Evidence write-back 的輸入來自事故期間已經建立的 artifact。每個 artifact 對應不同回寫方向。

| 輸入              | 提供內容                                 | 回寫方向                            |
| ----------------- | ---------------------------------------- | ----------------------------------- |
| Incident intake   | source、confidence、impact scope         | 04 readiness、8.1 severity          |
| Decision log      | hypothesis、evidence、rollback condition | 06 experiment、8 runbook            |
| Customer impact   | user、tenant、feature、financial impact  | 8.10 stakeholder、SLO policy        |
| Incident timeline | 發生、判讀、止血、恢復順序               | runbook、handoff、PIR               |
| PIR action item   | 缺口、owner、target state                | reliability debt、signal governance |
| Automation log    | bot action、approval、manual override    | automation boundary、audit          |

Incident intake 能揭露入口缺口。若客訴早於告警，回寫方向可能是 client-side monitoring、synthetic probe 或 support-to-incident workflow。

Decision log 能揭露判讀缺口。若 IC 做決策時缺少 trace、data quality 或 rollback condition，回寫方向可能是 04 [evidence package](/backend/knowledge-cards/evidence-package/)、06 rollback rehearsal 或 runbook lifecycle。

Customer impact 能揭露通訊與補償缺口。若影響範圍在事故後才算清楚，回寫方向可能是 impact assessment query、billing evidence 或 status page template。

Incident timeline 能揭露節奏缺口。若 handoff、escalation 或 containment 花太久，回寫方向可能是 on-call drill、IC handoff 或 automation setup。

## 回寫欄位

Write-back 欄位的責任是把學習轉成可關閉工作。每個回寫項都要有目標 artifact 與 closure signal。

| 欄位            | 責任                      | 範例                               |
| --------------- | ------------------------- | ---------------------------------- |
| Finding         | 說明事故揭露的缺口        | burn alert 缺少 tenant 維度        |
| Evidence        | 連到 decision log / query | 8.19 decision log #12              |
| Target artifact | 指定要修改的上游 artifact | 4.4 alert、6.20 experiment         |
| Owner           | 指定負責角色              | service owner、platform owner      |
| Closure signal  | 定義完成後如何驗證        | drill 通過、alert 在 game day 觸發 |
| Review date     | 定義何時重新檢查          | 下一次 release readiness           |

Finding 欄位要描述控制面缺口。`checkout timeout` 是現象；`dependency timeout alert 缺少 tenant / region 維度` 才是可回寫缺口。

Target artifact 讓回寫有落點。缺口可以落到 04 dashboard、04 data quality、06 experiment、06 readiness、08 runbook、08 automation boundary 或 07 security control。

Closure signal 讓 action item 可驗證。`補監控` 不夠具體；`game day 中 vendor timeout 能在 5 分鐘內觸發 tenant-scoped alert` 才能關閉。

## 回寫路由

Evidence write-back 的路由要依缺口性質選擇上游。不同缺口需要不同 owner 與驗證方式。

| 缺口類型     | 回寫位置                              | 驗證方式                        |
| ------------ | ------------------------------------- | ------------------------------- |
| 訊號缺口     | 4.16 readiness、4.20 evidence package | 下次 intake 可直接引用 evidence |
| 資料品質缺口 | 4.17 telemetry data quality           | dashboard 標示 freshness / gap  |
| 驗證缺口     | 6.20 experiment、6.23 handoff         | 新 experiment evidence 通過     |
| 穩態缺口     | 6.22 steady state definition          | recovery complete 可量測        |
| Runbook 缺口 | 8.16 runbook lifecycle                | drill 中 runbook 可執行         |
| 自動化缺口   | 8.21 automation boundary              | bot action 有 approval / audit  |
| 資安證據缺口 | 07 audit / security workflow          | chain of custody 可追蹤         |

訊號缺口要回到 04。若事故證據需要人工跨三個系統拼接，應補 evidence package、dashboard、query、log schema 或 trace context。

驗證缺口要回到 06。若事故中某個失效模式從未演練，應新增 chaos、DR drill、rollback rehearsal 或 readiness review 題目。

Runbook 缺口要回到 08。若事故處置依賴臨場記憶，應更新 runbook lifecycle，並透過 game day 或 on-call drill 驗證。

資安證據缺口要回到 07。若事故涉及 audit log、PII、credential 或 authorization，write-back 需要保存證據鏈與權限治理。

## 常見反模式

Evidence write-back 的反模式通常來自把 PIR 當成結案文件。PIR 是輸入，write-back 才是讓系統變好的交付。

| 反模式               | 表面現象                        | 修正方向                              |
| -------------------- | ------------------------------- | ------------------------------------- |
| Action item 停在待辦 | 有清單但沒有 target artifact    | 指定 dashboard / runbook / experiment |
| 缺 closure signal    | 完成與否靠主觀判斷              | 定義可驗證門檻                        |
| 只修程式碼           | 訊號、runbook、演練沒有同步更新 | 同步回寫 04 / 06 / 08                 |
| 同類事故重複         | PIR 未轉成 shared pattern       | 回寫 incident pattern library         |
| 自動化無復盤         | bot 錯誤只被人工記住            | 回寫 automation guardrail             |

Action item 停在待辦會讓改善失去落點。每個 [action item closure](/backend/knowledge-cards/action-item-closure/) 都需要 target artifact，否則 owner 很難知道要改哪個系統面。

只修程式碼會留下流程缺口。事故通常同時暴露 product bug、signal gap、verification gap 與 runbook gap；修程式碼只是其中一條路由。

## 交接路由

- 4.16 observability readiness：回寫事故中缺少的訊號
- 4.17 telemetry data quality：回寫資料品質限制
- 4.20 observability evidence package：補 evidence 欄位與保存格式
- 6.20 experiment safety：把事故型態轉成安全驗證題目
- 6.23 verification evidence handoff：保存新驗證題目的輸出格式
- 8.16 runbook lifecycle：把有效決策與缺口回寫 runbook
- 8.21 automation boundary：把 bot 行為與人工確認缺口回寫 guardrail
