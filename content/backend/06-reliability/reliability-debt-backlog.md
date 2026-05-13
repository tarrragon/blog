---
title: "6.21 Reliability Debt Backlog"
date: 2026-05-02
description: "把反覆事故、演練缺口與手動修復累積成可排序、可關閉的 reliability debt"
weight: 21
tags: ["backend", "reliability"]
---

## 大綱

- reliability debt 的責任：把可靠性缺口從口頭風險變成可管理 backlog
- 來源：post-incident review、game day、load test、chaos、on-call toil、customer ticket
- debt 類型：missing automation、weak rollback、manual recovery、fragile dependency、observability gap
- 欄位：impact、frequency、owner、evidence、mitigation、target state、closure signal
- 排序方式：SLO 影響、事故重複率、toil 成本、blast radius、修復成本
- 關閉條件：測試、演練、runbook 更新、alert 改善、manual step 移除
- 跟 08 的交接：PIR action item 進 reliability debt，集中成可追蹤工作
- 反模式：每次復盤都列改善，三個月後仍 open；toil 沒有量化；debt 無 owner

Reliability debt backlog 的重點是把「事故教訓」轉成「可交付工作」。沒有 backlog，團隊每次復盤都會得到相似結論；有 backlog，才有辦法把缺口排序、分派、驗收並逐步關閉。

## 概念定位

Reliability debt backlog 是管理可靠性缺口的工作佇列，責任是把反覆事故、演練缺口與手動修復轉成可排序、可驗證、可關閉的工程工作。

這一頁處理的是債務治理。可靠性問題常以事故、值班疲勞與手動操作出現；backlog 讓這些訊號進入產品與工程排程。

debt backlog 也提供跨團隊溝通語言。平台、服務、SRE 與產品可以用同一組欄位討論優先序，讓決策建立在同一批證據與欄位定義上。

## 核心判讀

判讀 reliability debt 時，先看缺口是否有 evidence，再看關閉條件是否可驗證。

重點訊號包括：

- debt 是否連到事故、演練或 toil 證據
- owner 是否能決定修復方案與排程
- impact 是否能對應 SLO、customer impact 或 on-call cost
- mitigation 是否只降低風險，或真正移除根因
- closure signal 是否能由測試、演練或監控證明

| 欄位                | 目的                   | 驗收重點                       |
| ------------------- | ---------------------- | ------------------------------ |
| Impact / Frequency  | 定義業務與技術代價     | 是否可量化到 SLO / toil / 客訴 |
| Owner / Due         | 明確責任與時程         | 是否有人可決策與執行           |
| Evidence            | 連回事故或演練證據     | 是否能追溯原始問題             |
| Mitigation / Target | 區分短期止血與長期修法 | 是否避免只補 workaround        |
| Closure Signal      | 定義完成條件           | 是否可由測試或演練驗證         |

## 判讀訊號

- 同類事故重複發生，但每次 action item 都重新命名
- on-call 反覆手動修同一個問題
- runbook 記錄 workaround，但沒有工程化任務
- debt backlog 只有優先級，缺少 impact / evidence / closure
- reliability 工作永遠輸給 feature，但事故成本持續上升

實務上最常見的失敗模式是 action item 全留在會議筆記。三個月後同類事故再發生，團隊才重新開同一張單。把 PIR 直接轉進 debt backlog，才能讓「是否真的改善」變成可驗證事實。

## Action Item 分級跟 Release Gate 綁定

Action item 沒分級時、所有改進項並列在 backlog、跟 feature 競爭同一批資源。沒有強制力的 action item 容易被延後到失效。

對應 [G2 Google Postmortem Action Item Closure 治理](/backend/06-reliability/cases/google/postmortem-action-item-closure-governance/)：揭露三層機制 — action item 分級（P0/P1/P2）、可驗證完成條件（不是「優化」「強化」抽象字）、closure 進固定 review cadence。

P0/P1/P2 分級的核心價值是「給高風險 action item 強制力」：

- P0 重複事故高機率再發生：下個 release 週期前完成並驗證
- P1 會放大事故影響面：要有落地日期跟 gate 條件
- P2 提升診斷或操作效率：可排 backlog、但保留追蹤節點

最關鍵的綁定是 **P0/P1 直接掛到 release gate**：未完成時不得放行關聯變更。沒有這層綁定、action item 即使分級也只是 backlog 的優先序、不是真正的工程強制力。詳見 [6.8 release gate 變更分層](/backend/06-reliability/release-gate/#變更分層跟-gate-政策)。

## Toil Budget：把重複手動工作變成預算問題

Reliability debt 的另一條來源是 toil — 重複的、可自動化的手動工作。Toil 沒被治理時、會持續吸收 SRE 時間、讓改進工作被推遲。

對應 [G3 Google Toil Budget 與 Automation 投資政策](/backend/06-reliability/cases/google/toil-budget-and-automation-investment-policy/)：揭露四個機制 — toil 分類（哪些屬可自動化）、時間配比（典型門檻 50%）、超標處理（凍結部分 feature、轉投自動化）、改善驗證（closure 指標跟 evidence）。

Toil budget 跟 reliability debt backlog 是兩個面向：

- Reliability debt backlog：管「失效缺口」（事故 / 演練揭露的工程化任務）
- Toil budget：管「日常壓力」（on-call 反覆手動工作的時間成本）

兩者要共用同一個 closure 機制：toil 超標時、超標部分強制轉投自動化、進 debt backlog 排序、按完成條件驗收。沒有這層綁定、toil 會被當「正常運維」、常態化壓在團隊上。Toil ratio 是 leading indicator、超標前就該觸發改善排程、不是等 on-call burnout 才補。

## 交接路由

- 04.8 signal governance loop：把觀測缺口變成 debt
- 06.8 release gate：高風險 debt 可成為 freeze 條件
- 06.18 reliability metrics governance：量化 debt 趨勢
- 08.5 post-incident review：PIR action items 的上游來源
- 08.13 repeated incident / toil：反覆事故與 toil 的事故端入口
