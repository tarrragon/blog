---
title: "7.BM3 藍隊推演情境素材"
tags: ["Blue Team", "Scenario", "Tabletop"]
date: 2026-04-30
description: "定義藍隊推演情境模板，協助把來源與案例轉成 tabletop 與 Game Day"
weight: 7253
---

藍隊推演情境素材的責任是把來源與案例轉成可演練情境。每個情境都要能回答觸發訊號、初始判讀、控制面、升級路由、驗證證據與回寫位置。

## 情境模板

| 欄位               | 責任                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------- |
| Scenario trigger   | 第一個可觀測訊號                                                                             |
| Initial hypothesis | 初始判讀與替代假設                                                                           |
| Control surface    | 需要驗證的身份、入口、資料或供應鏈控制面                                                     |
| Response route     | triage、[severity](/backend/knowledge-cards/incident-severity/)、owner 與 escalation         |
| Evidence target    | 需要保留的 log、[artifact](/backend/knowledge-cards/artifact-provenance/) 或 decision record |
| Write-back target  | 演練後要更新的章節、[runbook](/backend/knowledge-cards/runbook/) 或控制模式                  |

## 初始情境方向

推演情境先從四類高價值服務壓力開始：身份濫用、入口曝險、供應鏈 [artifact](/backend/knowledge-cards/artifact-provenance/) 偏移與低頻資料外送。這四類能直接承接 7.2、7.3、7.12 與 7.13。

## Source-first 規則

推演情境卡的責任是把真實案例轉成中性服務演練。每張情境卡都要標示來源案例，並把情境改寫成通用服務語言。

情境可以合成多個來源的壓力點，但每個主要壓力都要能回查到 field case 或 professional source。這個規則讓 tabletop 與 Game Day 保持可討論性，也避免情境只停留在想像中的攻防故事。

## 下一輪情境大綱

| 情境                                | 觸發訊號                                    | 驗證控制面                                 | 回寫位置                                                                                                          |
| ----------------------------------- | ------------------------------------------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| Identity takeover tabletop          | 高風險登入、支援工具操作或 token 異常       | identity、session、escalation              | [情境卡](/backend/07-security-data-protection/blue-team/materials/scenarios/identity-support-token-tabletop/)     |
| Edge exposure game day              | 外部通報、掃描命中或 exploit 指標           | entrypoint、patch window、containment      | [情境卡](/backend/07-security-data-protection/blue-team/materials/scenarios/edge-session-hijack-game-day/)        |
| Supply chain artifact drill         | artifact provenance 偏移或 build 證據不一致 | ci pipeline、release gate、rollback        | [情境卡](/backend/07-security-data-protection/blue-team/materials/scenarios/supply-chain-artifact-drill/)         |
| Low-frequency exfiltration tabletop | 低頻大量匯出、跨租戶查詢或異常下載          | data protection、audit trail、notification | [情境卡](/backend/07-security-data-protection/blue-team/materials/scenarios/low-frequency-exfiltration-tabletop/) |

情境卡的完成條件是能直接產生演練腳本。每張卡至少包含 scenario trigger、initial hypothesis、response route、evidence target 與 write-back target。
