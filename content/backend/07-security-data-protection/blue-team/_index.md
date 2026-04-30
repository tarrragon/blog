---
title: "7.B 防守者視角（藍隊）與控制面驗證"
tags: ["Blue Team", "Defense", "Security Control", "Detection"]
date: 2026-04-30
description: "從防守者角度整理控制面、偵測路由、驗證策略與演練回寫"
weight: 72
---

藍隊子分類的核心目標是建立防守判讀與控制面驗證路徑。這裡的藍隊定位為防守者視角的工程交接層，負責回答要防什麼、看什麼訊號、誰接手、如何驗證與如何回寫。

## 判讀分類

| 分類                  | 內容方向                                               | 承接章節             |
| --------------------- | ------------------------------------------------------ | -------------------- |
| Defense control map   | 身份、入口、資料、供應鏈、偵測與治理控制面             | `7.B1` + `7.8`       |
| Detection routing     | signal、threshold、triage、severity、escalation        | `7.B2` + `7.13`      |
| Control validation    | release gate、evidence chain、rollback、correctness    | `7.B3` + `05/06`     |
| Tabletop and game day | scenario、role、decision route、exercise write-back    | `7.B4` + `7.19`      |
| Incident handoff      | owner、runbook、communication、post-incident review    | `7.B2` + `08`        |
| Materials             | professional sources、field cases、scenarios、patterns | `7.BM` + `7.B1-7.B4` |

## 選型入口

藍隊分析優先問「防守者如何讓風險被看見並被收斂」。當一個風險已經能被 red-team problem card 描述，下一步就是把它轉成控制面、訊號、驗證條件與回寫位置。

## 與安全主模組的關係

本子分類與資安主模組形成防守操作視角。資安主模組定義問題節點與路由規則，藍隊子分類負責把這些節點整理成防守判讀、控制面驗證與演練材料。

## 與紅隊子分類的關係

藍隊與紅隊共用同一批風險語言。紅隊從攻擊路徑確認弱點，藍隊從防守流程確認控制面是否能偵測、升級、驗證與回寫。

## 章節列表

| 章節                                                                                           | 主題                        | 目標                                       |
| ---------------------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------ |
| [7.B1](/backend/07-security-data-protection/blue-team/defense-control-map/)                    | 防守控制面地圖              | 把 7.x 風險判讀轉成控制面與 owner          |
| [7.B2](/backend/07-security-data-protection/blue-team/detection-to-response-routing/)          | 偵測到回應的路由            | 把 signal 轉成 triage、severity 與升級流程 |
| [7.B3](/backend/07-security-data-protection/blue-team/security-control-validation/)            | 資安控制驗證                | 定義控制面如何用 evidence 與演練驗證       |
| [7.B4](/backend/07-security-data-protection/blue-team/tabletop-and-game-day-design/)           | Tabletop 與 Game Day        | 把 problem card 轉成演練與回寫任務         |
| [7.B5](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)        | Detection Lifecycle         | 把偵測規則變成可維護資產與交接流程         |
| [7.B6](/backend/07-security-data-protection/blue-team/incident-triage-loop/)                   | Incident Triage Loop        | 把訊號轉成分級、接手、處置與證據循環       |
| [7.B7](/backend/07-security-data-protection/blue-team/threat-informed-validation/)             | Threat-Informed Validation  | 用威脅導向方式驗證控制面與偵測能力         |
| [7.B8](/backend/07-security-data-protection/blue-team/defensive-vocabulary-map/)               | Defensive Vocabulary Map    | 用防守詞彙統一控制面、規則與交接語言       |
| [7.B9](/backend/07-security-data-protection/blue-team/blue-team-scenario-library/)             | Scenario Library            | 把高風險情境轉成可重播演練素材             |
| [7.B10](/backend/07-security-data-protection/blue-team/alert-fatigue-and-signal-quality/)      | Alert Fatigue               | 建立訊號品質治理與調校策略                 |
| [7.B11](/backend/07-security-data-protection/blue-team/vulnerability-response-state-machine/)  | Vulnerability State Machine | 把漏洞回應拆成可交接狀態機                 |
| [7.B12](/backend/07-security-data-protection/blue-team/defender-pressure-from-real-incidents/) | Defender Pressure           | 從真實事故抽出防守壓力模型與回寫路由       |
| [7.BM](/backend/07-security-data-protection/blue-team/materials/)                              | 藍隊素材庫                  | 整理專業來源、現場案例、推演情境與控制模式 |

本子分類會先建立防守判讀順序與控制面驗證語言，再交接到部署、可靠性與事故流程的實作章節。

藍隊章節的工程交接可參考 [7.18 資安控制面如何交接到部署與事故流程](/backend/07-security-data-protection/security-control-handoff-to-delivery-and-incident/) 與 [7.19 資安演練：從 Abuse Case 到 Game Day](/backend/07-security-data-protection/security-exercise-from-abuse-case-to-game-day/)。

## 模組完成狀態

藍隊章節目前已形成從控制地圖、規則生命周期、triage、威脅導向驗證到情境庫的完整循環。下一輪可優先補 `materials/field-cases` 與 `materials/control-patterns` 的細分卡片，擴大演練覆蓋率。
