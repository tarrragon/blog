---
title: "7.B4 Tabletop 與 Game Day 設計"
tags: ["Blue Team", "Tabletop", "Game Day", "Exercise Design"]
date: 2026-04-30
description: "建立藍隊如何設計 tabletop exercise 與 game day 的大綱"
weight: 724
---

本篇的責任是把防守情境轉成可執行演練。讀者讀完後，能從 problem card、公開案例或控制面缺口出發，設計 tabletop exercise 與 game day。

## 核心論點

Tabletop 與 game day 的核心概念是「用受控演練驗證角色、訊號、決策與操作證據」。Tabletop 驗證協作與決策，game day 驗證系統與流程能否實際承接。

## 讀者入口

本篇適合銜接 [7.19 資安演練：從 Abuse Case 到 Game Day](/backend/07-security-data-protection/security-exercise-from-abuse-case-to-game-day/)、[7.B2 從偵測到回應的路由](/backend/07-security-data-protection/blue-team/detection-to-response-routing/) 與 [Game Day](/backend/knowledge-cards/game-day/)。

## 演練設計欄位

| 欄位             | 責任                     | 例子                                                |
| ---------------- | ------------------------ | --------------------------------------------------- |
| Scenario         | 定義演練情境與風險範圍   | token abuse、data export、supply chain advisory     |
| Participants     | 定義參與角色與決策權限   | service owner、security owner、incident commander   |
| Injects          | 定義逐步釋出的訊號與事件 | alert、customer report、external advisory           |
| Expected actions | 定義預期判讀與操作       | triage、containment、rollback、communication        |
| Evidence         | 定義演練後可回查的證據   | timeline、log、decision record、action item         |
| Write-back       | 定義更新位置             | problem card、runbook、release gate、detection rule |

演練設計欄位的重點是讓演練可重複。當 scenario、injects、expected actions 固定，團隊可以跨季度比較能力變化。

## 選題來源

選題來源的責任是讓演練對準實際風險。建議優先順序：

1. 已出現在 problem card 的高風險流程。
2. 近期發生變更的關鍵系統。
3. 近期公開事故對應的同類場景。

## Tabletop 設計

Tabletop 設計的責任是驗證角色協作與決策節奏。這一層可在不動系統的前提下，先跑完整個判讀與升級路由。

Tabletop 推薦輸出：

1. Decision timeline。
2. Escalation transitions。
3. Communication script。
4. Write-back draft。

## Game Day 設計

Game day 設計的責任是驗證實際操作能力。這一層會執行告警處理、控制面操作、放行或回復流程，並收集完整證據。

Game day 推薦輸出：

1. Signal evidence：告警、log、metric、trace。
2. Action evidence：runbook 操作、gate 決策、rollback 記錄。
3. Closure evidence：關閉條件驗證與回寫任務。

## 演練觀察與回寫

演練觀察的責任是把事後改進對齊到章節結構。建議每次演練至少回寫三個位置：

1. blue-team 路由與驗證章節。
2. red-team problem cards 失效樣式。
3. incident workflow 檢查點與 owner map。

## 演練節奏建議

演練節奏的責任是建立可持續運作 cadence。建議以「月度 tabletop + 季度 game day」組合，並把每輪成果寫入固定回寫模板。

## 判讀訊號與路由

| 判讀訊號                          | 代表需求             | 下一步路由  |
| --------------------------------- | -------------------- | ----------- |
| 團隊知道風險但角色分工未演練      | 需要 tabletop        | 7.B4 → 08   |
| runbook 存在但操作證據不足        | 需要 game day        | 7.B4 → 06   |
| problem card 很完整但缺少驗證流程 | 需要演練設計         | 7.B4 → 7.19 |
| 演練結果沒有更新控制面            | 需要 write-back loop | 7.B4 → 7.B3 |

判讀表格可以當作演練發起條件。當任一列被命中，團隊就有清楚起點啟動演練設計。

## 必連章節

- [7.R11 流程濫用問題卡片](/backend/07-security-data-protection/red-team/problem-cards/)
- [7.16 從公開事故到工程 Workflow](/backend/07-security-data-protection/incident-case-to-control-workflow/)
- [7.19 資安演練：從 Abuse Case 到 Game Day](/backend/07-security-data-protection/security-exercise-from-abuse-case-to-game-day/)
- [7.B3 資安控制驗證](/backend/07-security-data-protection/blue-team/security-control-validation/)

## 完稿判準

完稿時要讓讀者能設計一次 tabletop 或 game day。演練設計至少包含 scenario、participants、injects、expected actions、evidence、exit condition 與 write-back target。
