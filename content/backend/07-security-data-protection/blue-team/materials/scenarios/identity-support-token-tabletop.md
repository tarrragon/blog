---
title: "Identity Support Token Tabletop"
tags: ["Blue Team", "Scenario", "Identity", "Tabletop"]
date: 2026-04-30
description: "以支援流程與 session token 風險設計身份接管 tabletop 情境"
weight: 72531
---

本情境的責任是演練支援流程中的身份敏感資料處置。它以 [Okta 2023 support token case](/backend/07-security-data-protection/blue-team/materials/field-cases/okta-support-token-2023-identity-pressure/) 為來源，轉成中性的 SaaS 支援系統 tabletop。

## Scenario Trigger

支援系統出現大量附件下載，同一時間有客戶回報管理員 session 異常。SOC 在 identity provider log 中看到高權限 session 從不常見位置延續使用。

## Initial Hypothesis

| 假設                     | 驗證資料                                           |
| ------------------------ | -------------------------------------------------- |
| 支援附件含 session token | HAR 檔、附件下載紀錄、支援 ticket                  |
| token 已被重放           | identity log、session metadata、device fingerprint |
| 客戶側先偵測到異常       | customer report、support timeline、通報紀錄        |

## Control Surface

控制面包含 support workflow、session management、[token revocation](/backend/knowledge-cards/token-revocation/)、customer communication 與 [ownership](/backend/knowledge-cards/ownership/)。

## Response Route

1. Triage：確認支援附件是否含敏感 session 資料。
2. Severity：依受影響 tenant、權限等級與 token 可用性分級。
3. Owner：identity owner 主責，support owner 與 incident commander 協作。
4. Containment：撤銷 session、鎖定附件下載、通知受影響客戶。
5. Write-back：更新支援附件處理、HAR sanitizer、customer notification 與 runbook。

## Evidence Target

| 證據                      | 用途                       |
| ------------------------- | -------------------------- |
| support ticket access log | 回查誰下載附件             |
| identity session log      | 判斷 session 使用範圍      |
| customer report timeline  | 對齊外部通報與內部偵測時序 |
| token revocation record   | 證明 containment 完成      |

## Write-back Target

- [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)
- [7.B6 Incident Triage Loop](/backend/07-security-data-protection/blue-team/incident-triage-loop/)
- [Control owner pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/control-owner-pattern/)
- [Exercise write-back pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/exercise-write-back-pattern/)
