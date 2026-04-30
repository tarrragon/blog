---
title: "Okta 2023 Support Token：身份支援流程壓力"
tags: ["Blue Team", "Okta", "Identity", "Support Workflow"]
date: 2026-04-30
description: "把 Okta 2023 support system incident 轉成身份供應鏈與支援流程的藍隊案例素材"
weight: 72521
---

本案例的責任是提供身份供應鏈與支援流程壓力素材。Okta 2023 support system incident 顯示，支援系統、HAR 檔、session token 與客戶通報節奏可以共同形成身份防守壓力。

## 來源

| 來源                                                                                                                                                       | 可引用範圍                                                                         |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| [Okta：Tracking Unauthorized Access to Okta's Support System](https://sec.okta.com/articles/2023/10/tracking-unauthorized-access-oktas-support-system/)    | support case management system、HAR file、stolen credential、customer notification |
| [Okta：Root Cause and Remediation](https://sec.okta.com/articles/2023/11/unauthorized-access-oktas-support-case-management-system-root-cause/)             | 影響範圍、session token hijacking、remediation                                     |
| [Cloudflare：How Cloudflare mitigated yet another Okta compromise](https://blog.cloudflare.com/fr-fr/how-cloudflare-mitigated-yet-another-okta-compromise) | 客戶側偵測、即時回應、Zero Trust 與 hardware key 防守效果                          |

## Defender Pressure

| 壓力                           | 服務判讀                                                        |
| ------------------------------ | --------------------------------------------------------------- |
| Support workflow pressure      | 支援附件與 troubleshooting 資料需要視為高敏感資料               |
| Session pressure               | session token 需要能被快速定位、撤銷與回查                      |
| Customer coordination pressure | 供應商與客戶之間需要明確通報、回應與驗證路由                    |
| Identity boundary pressure     | production service 與 support system 的風險需要共同納入身份治理 |

## Control Gap

控制缺口的核心是支援流程承載了身份敏感材料。當 HAR 檔或支援附件可能包含 session token，支援系統就不只是客服工具，而是身份供應鏈的一部分。

## Detection Route

| 訊號                             | 判讀用途                       | 下一步                                                              |
| -------------------------------- | ------------------------------ | ------------------------------------------------------------------- |
| 支援系統下載敏感附件             | 判斷 support workflow exposure | 啟動附件清查與 token 回收                                           |
| customer tenant 出現異常 session | 判斷 session hijack 風險       | 啟動 [token revocation](/backend/knowledge-cards/token-revocation/) |
| 客戶先於供應商發現異常           | 判斷 vendor coordination gap   | 啟動 incident communication route                                   |

## Exercise Hook

本案例可支撐 [Identity support token tabletop](/backend/07-security-data-protection/blue-team/materials/scenarios/identity-support-token-tabletop/)。演練重點是確認支援附件進入系統後，團隊是否能快速定位 token、撤銷 session、通知 owner 並回寫支援流程。

## Write-back Target

- [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)
- [7.B6 Incident Triage Loop](/backend/07-security-data-protection/blue-team/incident-triage-loop/)
- [Control owner pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/control-owner-pattern/)
- [Evidence chain pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/evidence-chain-pattern/)
