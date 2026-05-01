---
title: "7.R11.P12 第三方 token 授權範圍過寬"
date: 2026-04-24
description: "說明第三方 token 授權範圍過寬如何放大供應商事件傳導"
weight: 7242
---

這個失效樣式的核心問題是外部授權範圍超出實際用途邊界。當第三方 token 權限過寬，外部事件會快速傳導到內部高風險路徑。

## 常見形成條件

- 第三方 token scope 與實際用途不一致。
- token 期限過長且回收節奏落後。
- 供應商事件後缺少分域收斂流程。

## 判讀訊號

- token 在非預期服務持續被使用。
- 供應商事件後高權限 token 存續比例偏高。
- 第三方授權事件在責任回查鏈上出現斷點。

## 案例觸發參考

- [Okta + Cloudflare 2023](/backend/07-security-data-protection/red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/)
- [Cloudflare 2023](/backend/07-security-data-protection/red-team/cases/identity-access/cloudflare-2023-okta-token-follow-through/)
- [Slack 2022](/backend/07-security-data-protection/red-team/cases/identity-access/slack-2022-token-compromise/)

## 來源流程卡

- [第三方授權濫用](/backend/07-security-data-protection/red-team/problem-cards/third-party-authorization-abuse/)

## 下一步路由

本失效樣式對應的實作 chain：

**控制面（mitigation 在這裡定義）**：

- [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)
- [7.5 工作負載身份與 federated trust](/backend/07-security-data-protection/workload-identity-and-federated-trust/)

**演練 / 控制落地（轉成欄位）**：

- [Credential hygiene pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/credential-hygiene-pattern/)
