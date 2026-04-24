---
title: "7.R11.12 第三方授權濫用"
date: 2026-04-24
description: "說明第三方授權流程為何容易成為供應商事件傳導節點"
weight: 7222
---

第三方授權的核心風險是把外部信任直接映射成內部操作能力。當授權範圍與回收節奏沒有分域，外部事件會快速傳導到內部。

## 為什麼會出問題

第三方授權流程通常強調整合便利性。便利導向若缺少範圍限制與失效節奏，授權結果會長期超出原始用途。

## 常見失效樣式

- 第三方 token 權限過寬且期限過長。
- 授權撤銷與內部會話失效不同步。
- 供應商事件後缺少分域盤點流程。

## 判讀訊號

- 第三方 token 在非預期服務持續被使用。
- 供應商事件後高權限 token 存續比例偏高。
- 第三方授權事件在責任主體回查上出現斷點。

## 案例觸發參考

- [Okta + Cloudflare 2023](../cases/identity-access/okta-cloudflare-2023-support-supply-chain/)
- [Cloudflare 2023](../cases/identity-access/cloudflare-2023-okta-token-follow-through/)
- [Slack 2022](../cases/identity-access/slack-2022-token-compromise/)

## 可連動章節

- [7.6 秘密管理與機器憑證治理](../../secrets-and-machine-credential-governance/)
- [7.10 Workload Identity 與聯邦信任邊界](../../workload-identity-and-federated-trust/)

## 對應失效樣式卡

- [7.R11.P12 第三方 token 授權範圍過寬](fp-overscoped-third-party-token-grant/)
