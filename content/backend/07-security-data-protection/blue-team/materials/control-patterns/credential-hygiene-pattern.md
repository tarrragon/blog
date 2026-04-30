---
title: "Credential Hygiene Pattern"
tags: ["Blue Team", "Control Pattern", "Credential", "MFA"]
date: 2026-04-30
description: "定義 credential、MFA、輪替、infostealer 監控與 network boundary 的共同基線"
weight: 72546
---

Credential hygiene pattern 的責任是把 credential 生命週期變成可驗證基線。它讓平台、SaaS 與身份系統共享同一套 MFA、rotation、infostealer 監控與 network boundary 欄位,降低 credential 重用引發的事件比例。

## 支撐素材

| 素材                                                                                                                                                             | 可支撐論點                                                |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| [Snowflake credential reuse case](/backend/07-security-data-protection/blue-team/materials/field-cases/snowflake-2024-credential-reuse-pressure/)                | infostealer credential 仍長期有效、MFA 與 allow list 缺口 |
| [MGM helpdesk case](/backend/07-security-data-protection/blue-team/materials/field-cases/mgm-2023-helpdesk-social-engineering-pressure/)                         | helpdesk 重置流程承載身份重建責任,需要與 MFA 對齊         |
| [Change Healthcare recovery case](/backend/07-security-data-protection/blue-team/materials/field-cases/change-healthcare-2024-recovery-and-dependency-pressure/) | 對外入口缺少 MFA 是 ransomware initial access 起點        |
| [Okta support token case](/backend/07-security-data-protection/blue-team/materials/field-cases/okta-support-token-2023-identity-pressure/)                       | session token 與支援附件需要納入 credential 治理          |

## 欄位

| 欄位                | 責任                                         |
| ------------------- | -------------------------------------------- |
| MFA enforcement     | 定義對外入口、admin 與 SaaS 的 MFA 基線      |
| Rotation policy     | 定義 credential、token、key 的輪替週期與觸發 |
| Reset workflow      | 定義 helpdesk 重置與 callback 驗證流程       |
| Exposure monitoring | 監控 infostealer、credential dump 與外洩來源 |
| Network boundary    | 定義 IP / VPC / device allow list            |

## 判讀訊號

| 訊號                                 | 代表需求                                    |
| ------------------------------------ | ------------------------------------------- |
| infostealer 命中後 credential 仍有效 | 需要 rotation policy 與 exposure monitoring |
| SaaS 平台缺少 MFA 強制               | 需要 MFA enforcement 基線                   |
| helpdesk 能在電話中重置高權限        | 需要 reset workflow 與 callback 驗證        |
| 對外入口接受任意來源                 | 需要 network boundary                       |

## 適用邊界

此模式適合 IdP、SaaS data platform、邊界 VPN、helpdesk 與支援系統。內部服務之間若已使用 workload identity,可改用較輕量的 rotation 與監控欄位。

## 下一步路由

- [Token revocation](/backend/knowledge-cards/token-revocation/)
- [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)
- [Identity support token tabletop](/backend/07-security-data-protection/blue-team/materials/scenarios/identity-support-token-tabletop/)
- [Low-frequency exfiltration tabletop](/backend/07-security-data-protection/blue-team/materials/scenarios/low-frequency-exfiltration-tabletop/)
