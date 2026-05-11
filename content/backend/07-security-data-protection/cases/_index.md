---
title: "模組七案例正文"
date: 2026-05-07
description: "資安控制面與控制平面轉換案例入口。"
weight: 85
tags: ["backend", "security", "case-study"]
---

這個資料夾的核心責任是把資安與控制平面事故轉成可回寫治理控制的案例正文。

## 案例列表

| 章節                                                                                          | 主題                       | 核心責任                                  |
| --------------------------------------------------------------------------------------------- | -------------------------- | ----------------------------------------- |
| [7.C1](/backend/07-security-data-protection/cases/cloudflare-route-leak-2026/)                | Cloudflare 2026 Route Leak | 路由策略自動化失誤如何回寫治理與 tripwire |
| [7.C2](/backend/07-security-data-protection/cases/cloudflare-control-plane-token-2023/)       | Cloudflare 2023 Token 事件 | 控制面 token 風險如何轉成機器憑證治理     |
| [7.C3](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/)      | Azure AD 2021 控制面事件   | 身分控制面事故如何影響多服務信任鏈        |
| [7.C4](/backend/07-security-data-protection/cases/microsoft-storm-0558-signing-key-2023/)     | Microsoft Storm-0558       | 簽章金鑰事件如何回寫 identity 信任邊界    |
| [7.C5](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/)         | Okta support 系統事件      | 支援系統憑證風險如何擴散到客戶租戶        |
| [7.C6](/backend/07-security-data-protection/cases/okta-cross-tenant-impersonation-2023/)      | Okta cross-tenant 事件     | 跨租戶 impersonation 如何回寫防禦與偵測   |
| [7.C7](/backend/07-security-data-protection/cases/okta-byo-telephony-security-shift/)         | Okta BYO Telephony         | MFA 供應鏈責任如何轉為客戶可控治理        |
| [7.C9](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/) | 反例：憑證輪替失敗         | 憑證輪替未分 scope 導致跨系統連鎖中斷     |
| [7.C10](/backend/07-security-data-protection/cases/contrast-identity-governance-by-scale/)    | 對照：規模差異下身份治理   | 不同規模服務在 identity 控制面的風險差異  |
