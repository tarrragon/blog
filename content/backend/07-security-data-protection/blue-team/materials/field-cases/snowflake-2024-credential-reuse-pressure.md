---
title: "Snowflake 2024:SaaS Credential 重用壓力"
tags: ["Blue Team", "Snowflake", "Credential", "SaaS"]
date: 2026-04-30
description: "把 Snowflake UNC5537 事件轉成 SaaS data platform credential、MFA 與 network allow list 壓力素材"
weight: 72527
---

本案例的責任是提供 SaaS data platform credential 壓力素材。Snowflake 2024 事件顯示,當 customer instance 的 credential 透過 infostealer 外流、且 MFA 與 network allow list 未強制時,SaaS 資料平台會成為大規模資料外送入口。

## 來源

| 來源                                                                                                                                                  | 可引用範圍                                              |
| ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| [Mandiant / Google Cloud:UNC5537 targets Snowflake](https://cloud.google.com/blog/topics/threat-intelligence/unc5537-snowflake-data-theft-extortion)  | initial access、infostealer 來源、TTP、IOC              |
| [Snowflake security advisory(整理見 Cybersecurity Dive)](https://www.cybersecuritydive.com/news/100-snowflake-customers-attacked/718454/)             | 受影響 customer instance、平台立場、recommended actions |
| [TechTarget:Mandiant root cause 摘要](https://www.techtarget.com/searchsecurity/news/366588655/Mandiant-Exposed-credentials-led-to-Snowflake-attacks) | credential reuse、MFA 缺口、credential 長期有效性       |

## Defender Pressure

| 壓力                           | 服務判讀                                      |
| ------------------------------ | --------------------------------------------- |
| Credential hygiene pressure    | infostealer 外流的舊 credential 仍長期有效    |
| MFA enforcement pressure       | SaaS data platform 需要平台側可強制的 MFA     |
| Network boundary pressure      | 資料平台需要 IP / VPC allow list 收斂存取來源 |
| Shared responsibility pressure | 客戶與供應商需要對齊偵測、通報與佐證義務      |

## Control Gap

控制缺口的核心是 SaaS 資料平台的 credential lifecycle 與 network boundary 屬於客戶責任範圍,但平台缺少強制基線。沒有 MFA、沒有 allow list、credential 長期未輪替,是同類事件重複出現的共通結構。

## Detection Route

| 訊號                                      | 判讀用途                    | 下一步                                                                            |
| ----------------------------------------- | --------------------------- | --------------------------------------------------------------------------------- |
| 資料平台出現非預期 IP 大量查詢            | 判斷 credential 是否被濫用  | 啟動 [token revocation](/backend/knowledge-cards/token-revocation/) 與 allow list |
| 同一 user account 跨多次 infostealer 命中 | 判斷 credential 仍有效期    | 啟動強制輪替與 MFA enforcement                                                    |
| 客戶通報資料外流早於平台告警              | 判斷 detection coverage gap | 啟動 platform / customer log 對齊                                                 |

## Exercise Hook

本案例可支撐 [Low-frequency exfiltration tabletop](/backend/07-security-data-protection/blue-team/materials/scenarios/low-frequency-exfiltration-tabletop/) 的 SaaS 資料平台變體。演練重點是確認 credential、MFA、network boundary 與通報流程是否能在共享責任邊界內快速協作。

## Write-back Target

- [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)
- [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)
- [Detection lifecycle pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/detection-lifecycle-pattern/)
- [Evidence chain pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/evidence-chain-pattern/)
