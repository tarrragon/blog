---
title: "6.21 Reliability Debt Backlog"
date: 2026-05-02
description: "把反覆事故、演練缺口與手動修復累積成可排序、可關閉的 reliability debt"
weight: 21
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

## 交接路由

- 04.8 signal governance loop：把觀測缺口變成 debt
- 06.8 release gate：高風險 debt 可成為 freeze 條件
- 06.18 reliability metrics governance：量化 debt 趨勢
- 08.5 post-incident review：PIR action items 的上游來源
- 08.13 repeated incident / toil：反覆事故與 toil 的事故端入口
