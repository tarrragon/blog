---
title: "Recovery Readiness Pattern"
tags: ["Blue Team", "Control Pattern", "Recovery", "Resilience"]
date: 2026-04-30
description: "定義長時間 outage 復原、備援存取與外部依賴溝通的共同欄位"
weight: 72547
---

Recovery readiness pattern 的責任是把復原能力變成事前可驗證資產。它讓服務在 ransomware、邊界批量利用或關鍵供應商中斷時,具備備援存取、復原時序與外部依賴溝通的最小骨架。

## 支撐素材

| 素材                                                                                                                                                             | 可支撐論點                                               |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| [Change Healthcare recovery case](/backend/07-security-data-protection/blue-team/materials/field-cases/change-healthcare-2024-recovery-and-dependency-pressure/) | 核心服務需要多週量級的復原計畫與下游溝通                 |
| [Ivanti Connect Secure case](/backend/07-security-data-protection/blue-team/materials/field-cases/ivanti-connect-secure-2024-edge-mass-exploitation/)            | Emergency directive 要求暫時 disconnect,需要備援存取路徑 |
| [Citrix Bleed edge case](/backend/07-security-data-protection/blue-team/materials/field-cases/citrix-bleed-2023-edge-session-pressure/)                          | 修補後仍需 session 收斂與服務驗證才算復原                |
| [MOVEit exfiltration case](/backend/07-security-data-protection/blue-team/materials/field-cases/moveit-2023-mft-exfiltration-pressure/)                          | 資料系統復原需要與通報、法務節奏對齊                     |

## 欄位

| 欄位                  | 責任                                        |
| --------------------- | ------------------------------------------- |
| Recovery objective    | 定義 RTO / RPO 與接受降級的服務範圍         |
| Backup access path    | 定義關鍵入口下線時的備援存取與 break-glass  |
| Restore verification  | 定義復原後的功能、資料完整性與 session 驗證 |
| Dependency map        | 列出下游機構、第三方供應商與通知對象        |
| Communication cadence | 定義內部、客戶與監管通報的節奏              |

## 判讀訊號

| 訊號                                | 代表需求                                     |
| ----------------------------------- | -------------------------------------------- |
| 演練只演到 patch 完成、忽略復原驗證 | 需要 restore verification                    |
| Emergency disconnect 後缺少備援入口 | 需要 backup access path                      |
| 下游機構在事件期間缺少對接窗口      | 需要 dependency map 與 communication cadence |
| 復原期程估計失準                    | 需要更新 recovery objective                  |

## 適用邊界

此模式適合關鍵交易服務、產業共用平台、邊界設備與資料系統。低風險內部工具可保留簡化版的 RTO 與通知欄位,但仍要記錄 dependency map。

## 下一步路由

- [Runbook](/backend/knowledge-cards/runbook/)
- [7.24 資安事故如何回寫產品與架構](/backend/07-security-data-protection/security-incident-write-back-to-product-and-architecture/)
- [Edge session hijack game day](/backend/07-security-data-protection/blue-team/materials/scenarios/edge-session-hijack-game-day/)
- [Vulnerability response pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/vulnerability-response-pattern/)
