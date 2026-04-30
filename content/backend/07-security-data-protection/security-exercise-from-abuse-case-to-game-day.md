---
title: "7.19 資安演練：從 Abuse Case 到 Game Day"
tags: ["資安演練", "Abuse Case", "Game Day", "Tabletop"]
date: 2026-04-30
description: "建立 abuse case、tabletop exercise 與 game day 之間的演練大綱"
weight: 89
---

本篇的責任是把資安問題節點轉成可演練的團隊流程。讀者讀完後，能從一張 abuse case 或 problem card 出發，設計 tabletop exercise、game day 與回寫任務。

## 核心論點

資安演練的核心概念是「用受控情境驗證控制面與協作流程」。Abuse case 提供攻擊或濫用假設，game day 驗證團隊能否在訊號、角色與決策節奏上完成收斂。

## 讀者入口

本篇適合銜接 [7.R11 流程濫用問題卡片](/backend/07-security-data-protection/red-team/problem-cards/)、[7.16 從公開事故到工程 Workflow](/backend/07-security-data-protection/incident-case-to-control-workflow/) 與 [Game Day](/backend/knowledge-cards/game-day/)。它把資安案例庫轉成演練材料。

## 演練模型

演練模型的責任是把不同粒度的材料放在同一條路徑上：

| 材料                                               | 演練用途                 | 產出                         |
| -------------------------------------------------- | ------------------------ | ---------------------------- |
| [Abuse Case](/backend/knowledge-cards/abuse-case/) | 定義合法功能被濫用的情境 | 濫用路徑、風險範圍、判讀訊號 |
| Problem Card                                       | 定義可重複失效樣式       | 控制面假設、驗證問題         |
| Tabletop Exercise                                  | 驗證角色與決策流程       | 指揮節奏、升級路徑、缺口清單 |
| [Game Day](/backend/knowledge-cards/game-day/)     | 驗證系統與團隊反應       | 操作證據、修復任務、回寫項目 |

這條路徑的關鍵是先用抽象層材料定義問題，再用現場演練驗證行為。如此可以讓同一張 problem card 在不同服務情境重用。

## 演練前置設計

演練前置設計的責任是讓每次演練都能回答同一組問題，並用固定欄位維持命名一致性。建議欄位如下：

1. Scenario：定義服務情境與風險邊界。
2. Trigger：定義演練起點訊號。
3. Roles：定義決策角色與操作角色。
4. Expected path：定義預期路由與完成條件。
5. Evidence：定義演練後要保留的證據。

## Tabletop 演練

Tabletop 的責任是驗證決策與協作。重點是讓角色在時間壓力下仍能維持一致路由，並把升級流程與外部溝通節奏跑過一次。

Tabletop 推薦輸出：

1. Decision timeline：每個決策點何時產生、由誰承接。
2. Escalation record：何時升級、升級依據為何。
3. Gap list：本輪找到的流程缺口。

## Game Day 演練

Game day 的責任是驗證系統與流程在真實操作下的穩定度。重點是把 control path、alert path、recovery path 串在同一輪場景。

Game day 推薦輸出：

1. Signal evidence：告警、log、metric、trace 片段。
2. Control evidence：release gate、rollback、token revocation 操作記錄。
3. Write-back task：對應回寫到章節與卡片的位置。

## 演練回寫流程

演練回寫的責任是讓演練成果進入知識網。建議回寫順序：

1. 先回寫 problem card 的失效樣式與補強點。
2. 再回寫 7.x 判讀訊號與風險邊界描述。
3. 最後回寫 incident workflow 的任務模板與檢查點。

## 兩種常見演練場景

1. 身份與會話場景：檢查 token 濫用、權限收斂與 session 失效節奏。
2. 供應鏈場景：檢查 artifact provenance、release freeze、tripwire 與放行條件。

## 判讀訊號與路由

| 判讀訊號                          | 代表演練需求                | 下一步路由             |
| --------------------------------- | --------------------------- | ---------------------- |
| problem card 已存在但缺少驗證情境 | 需要設計 abuse case 演練    | 7.19 → tabletop        |
| 控制面描述完整但角色分工鬆散      | 需要 tabletop exercise      | 7.19 → escalation path |
| runbook 存在但缺少實際操作證據    | 需要 game day 驗證          | 7.19 → 06 reliability  |
| 演練後任務分散在多處              | 需要回寫到 case-to-workflow | 7.19 → 7.16            |

判讀表格的重點是從訊號直接推到下一步行動。這種路由格式可以直接轉成演練 backlog。

## 必連章節

- [7.R7 事故案例庫](/backend/07-security-data-protection/red-team/cases/)
- [7.R8 控制面失效樣式](/backend/07-security-data-protection/red-team/control-failure-patterns/)
- [7.R11 流程濫用問題卡片](/backend/07-security-data-protection/red-team/problem-cards/)
- [7.16 從公開事故到工程 Workflow](/backend/07-security-data-protection/incident-case-to-control-workflow/)

## 完稿判準

完稿時要讓讀者能用一張 problem card 建立一次資安演練。演練設計至少包含場景、角色、訊號、決策點、操作證據、關閉條件與回寫位置。
