---
title: "7.B9 Blue Team Scenario Library"
tags: ["Blue Team", "Scenario", "Tabletop", "Game Day"]
date: 2026-04-30
description: "把高風險服務情境轉成可重用推演素材，支援 tabletop 與 game day 設計"
weight: 729
---

本篇的責任是建立 blue team scenario library。讀者讀完後，能把風險情境轉成可演練劇本與回寫欄位。

## 核心論點

Scenario library 的核心概念是把防守知識轉成可重播情境。可重播情境讓控制驗證從一次性討論變成可累積資產。

## 讀者入口

本篇適合銜接 [7.B4 Tabletop 與 Game Day 設計](/backend/07-security-data-protection/blue-team/tabletop-and-game-day-design/)、[7.BM3 藍隊推演情境素材](/backend/07-security-data-protection/blue-team/materials/scenarios/) 與 [7.B7 Threat-Informed Validation](/backend/07-security-data-protection/blue-team/threat-informed-validation/)。

## 情境卡模板

| 欄位              | 責任                   | 產出              |
| ----------------- | ---------------------- | ----------------- |
| Trigger           | 定義起始訊號           | scenario trigger  |
| Hypothesis        | 定義初始判讀與替代假設 | triage note       |
| Control surface   | 定義要驗證的控制面     | control checklist |
| Response route    | 定義分級、接手與升級   | response path     |
| Evidence target   | 定義要保留的證據       | evidence list     |
| Write-back target | 定義要回寫的位置       | update backlog    |

## 初始情境組合

初始情境組合的責任是聚焦高價值風險。可先固定四組：

1. 身份濫用與權限擴張。
2. 入口曝險與管理面異常。
3. 供應鏈 artifact 偏移。
4. 低頻資料外送與長尾訊號。

## 演練節奏

演練節奏的責任是讓情境能持續更新。每輪演練後同步更新觸發條件、分級基準、證據欄位與 runbook，並記錄下一輪要驗證的假設。

## 指標設計

指標設計的責任是評估情境品質。建議追蹤命中率、triage 時間、升級一致性、證據完整度與回寫完成率。

## 判讀訊號與路由

| 判讀訊號                 | 代表需求                 | 下一步路由   |
| ------------------------ | ------------------------ | ------------ |
| 演練腳本每次都重寫       | 需要固定情境卡模板       | 7.B9 → 7.BM3 |
| 演練命中訊號但處置不同步 | 需要補 response route    | 7.B9 → 7.B6  |
| 演練結束後無回寫任務     | 需要補 write-back target | 7.B9 → 7.24  |
| 情境只覆蓋單一風險類型   | 需要擴充 threat 組合     | 7.B9 → 7.B7  |

## 必連章節

- [7.B4 Tabletop 與 Game Day 設計](/backend/07-security-data-protection/blue-team/tabletop-and-game-day-design/)
- [7.B6 Incident Triage Loop](/backend/07-security-data-protection/blue-team/incident-triage-loop/)
- [7.B7 Threat-Informed Validation](/backend/07-security-data-protection/blue-team/threat-informed-validation/)
- [7.BM3 藍隊推演情境素材](/backend/07-security-data-protection/blue-team/materials/scenarios/)

## 完稿判準

完稿時要讓讀者能把一個風險轉成可演練情境。輸出至少包含 trigger、hypothesis、control surface、response route、evidence target 與 write-back target。
