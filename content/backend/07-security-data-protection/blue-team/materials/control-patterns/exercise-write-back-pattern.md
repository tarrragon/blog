---
title: "Exercise Write-back Pattern"
tags: ["Blue Team", "Control Pattern", "Game Day"]
date: 2026-04-30
description: "定義 tabletop 與 game day 如何把 finding 回寫成控制更新、runbook 更新與 tripwire"
weight: 72545
---

Exercise write-back pattern 的責任是把演練結果轉成工程任務。演練完成後，finding 需要回寫到控制面、[runbook](/backend/knowledge-cards/runbook/)、owner、tripwire 與後續驗證節奏。

## 支撐素材

| 素材                                                                                                                                    | 可支撐論點                                                      |
| --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| [MOVEit exfiltration case](/backend/07-security-data-protection/blue-team/materials/field-cases/moveit-2023-mft-exfiltration-pressure/) | data scope 與 notification finding 需要回寫資料出口控制         |
| [3CX supply chain case](/backend/07-security-data-protection/blue-team/materials/field-cases/3cx-2023-supply-chain-artifact-pressure/)  | release gate、artifact provenance 與 customer advisory 需要回寫 |
| [NIST SP 800-61r3](/backend/07-security-data-protection/blue-team/materials/professional-sources/nist-sp-800-61r3-incident-response/)   | incident response 應納入治理、復原與持續改進                    |

## 欄位

| 欄位           | 責任                   |
| -------------- | ---------------------- |
| Finding        | 描述演練中觀察到的缺口 |
| Control update | 定義控制面要改什麼     |
| Runbook update | 定義操作流程要補什麼   |
| Owner          | 指定回寫任務主責       |
| Tripwire       | 定義何時重新演練或升級 |

## 判讀訊號

| 訊號                             | 代表需求                        |
| -------------------------------- | ------------------------------- |
| 演練結束後只有會議紀錄           | 需要 finding 到 task 的回寫欄位 |
| 同一缺口在多次 tabletop 重複出現 | 需要 owner 與 tripwire          |
| 情境有結論但 release gate 沒變   | 需要 control update 與驗證條件  |

## 適用邊界

此模式適合 tabletop、game day、incident postmortem 與 threat-informed validation。小型演練可保留 finding、owner 與 due date，重大演練要完整回寫控制面與 tripwire。

## 下一步路由

- [7.B4 Tabletop 與 Game Day 設計](/backend/07-security-data-protection/blue-team/tabletop-and-game-day-design/)
- [7.24 資安事故如何回寫產品與架構](/backend/07-security-data-protection/security-incident-write-back-to-product-and-architecture/)
- [Low-frequency exfiltration tabletop](/backend/07-security-data-protection/blue-team/materials/scenarios/low-frequency-exfiltration-tabletop/)
