---
title: "7.R11.P13 聯邦 token 信任漂移"
tags: ["聯邦信任", "Federation Trust", "Token Scope", "Red Team"]
date: 2026-04-30
description: "說明跨平台聯邦 token 的來源與用途脫鉤如何放大傳導風險"
weight: 7243
---

這個失效樣式的核心問題是聯邦 token 的信任來源與實際使用範圍逐步脫鉤。當 token 可在非預期服務持續使用，外部事件會直接傳導到內部高權限路徑，形成 [trust boundary](/backend/knowledge-cards/trust-boundary/) 失衡。

## 常見形成條件

- federation trust 建立後缺少定期重評估。
- token scope 與 [least privilege](/backend/knowledge-cards/least-privilege/) 原則不一致。
- 跨平台 [token revocation](/backend/knowledge-cards/token-revocation/) 流程沒有同批收斂。

## 判讀訊號

- 同一聯邦 token 在非預期服務持續出現。
- 外部身分事件後高權限聯邦 token 存續比例偏高。
- 聯邦授權決策在 [audit log](/backend/knowledge-cards/audit-log/) 回查鏈上出現斷點。

## 案例觸發參考

- [Okta + Cloudflare 2023](/backend/07-security-data-protection/red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/)
- [Cloudflare 2023](/backend/07-security-data-protection/red-team/cases/identity-access/cloudflare-2023-okta-token-follow-through/)
- [Snowflake 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)

## 來源流程卡

- [第三方授權濫用](/backend/07-security-data-protection/red-team/problem-cards/third-party-authorization-abuse/)
