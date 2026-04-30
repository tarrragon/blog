---
title: "Detection Lifecycle Pattern"
tags: ["Blue Team", "Control Pattern", "Detection Engineering"]
date: 2026-04-30
description: "定義偵測規則如何管理來源、邏輯、測試事件、誤報與退場"
weight: 72543
---

Detection lifecycle pattern 的責任是把偵測規則變成可維護資產。規則需要來源、邏輯、測試事件、誤報紀錄、owner 與退場條件，才能穩定支撐 incident triage。

## 支撐素材

| 素材                                                                                                                                                  | 可支撐論點                                     |
| ----------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| [Sigma detection rule lifecycle](/backend/07-security-data-protection/blue-team/materials/professional-sources/sigma-detection-rule-lifecycle/)       | detection rule 需要格式、測試與維護語言        |
| [SANS Detection Engineering Survey](/backend/07-security-data-protection/blue-team/materials/professional-sources/sans-detection-engineering-survey/) | detection engineering 需要流程、角色與品質治理 |
| [3CX supply chain case](/backend/07-security-data-protection/blue-team/materials/field-cases/3cx-2023-supply-chain-artifact-pressure/)                | artifact 與客戶端 IOC 需要偵測規則支撐         |

## 欄位

| 欄位           | 責任                   |
| -------------- | ---------------------- |
| Source         | 定義規則來源與威脅假設 |
| Logic          | 定義命中條件與資料來源 |
| Test event     | 提供可重播測試資料     |
| False positive | 記錄誤報情境與調校依據 |
| Retirement     | 定義規則退場或替換條件 |

## 判讀訊號

| 訊號                     | 代表需求                           |
| ------------------------ | ---------------------------------- |
| 規則命中後分析結論分散   | 需要 test event 與 triage question |
| 誤報調校只靠臨場經驗     | 需要 false positive 紀錄           |
| 規則長期存在但沒有 owner | 需要 lifecycle owner 與 retirement |

## 適用邊界

此模式適合 detection rule、IOC hunting、artifact integrity check 與 low-frequency exfiltration detection。一次性查詢可先用 hunt note，穩定後再轉為規則生命週期。

## 下一步路由

- [7.B5 Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)
- [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- [Supply chain artifact drill](/backend/07-security-data-protection/blue-team/materials/scenarios/supply-chain-artifact-drill/)
