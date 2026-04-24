---
title: "7.R7.1 Identity & Access 類案例"
date: 2026-04-24
description: "整理身分流程、社交工程、支援系統與 token 鏈的事故案例"
weight: 7171
---

本分類的責任是檢查身分與授權流程是否能在攻擊壓力下維持邊界。核心判讀是：登入成功只代表入口被通過，控制面仍需要持續驗證、隔離與收斂。

## 案例列表

- [Uber 2022：MFA 疲勞與內部工具擴散](uber-2022-mfa-fatigue/)
- [Okta + Cloudflare 2023：支援流程與身分供應鏈](okta-cloudflare-2023-support-supply-chain/)
- [Twilio 2022：社交工程與員工帳號路徑](twilio-2022-social-engineering/)
- [MGM 2023：身分流程被打穿後的營運中斷](mgm-2023-identity-lateral-impact/)
- [Microsoft Storm-0558 2023：簽章金鑰鏈與郵件存取](microsoft-storm-0558-2023-signing-key-chain/)
- [Cloudflare 2023：供應商事件後的身分收斂](cloudflare-2023-okta-token-follow-through/)
- [Slack 2022：企業 token 與程式碼資產路徑](slack-2022-token-compromise/)
- [Dropbox 2022：釣魚入侵與程式碼倉儲風險](dropbox-2022-code-repo-phishing-chain/)
