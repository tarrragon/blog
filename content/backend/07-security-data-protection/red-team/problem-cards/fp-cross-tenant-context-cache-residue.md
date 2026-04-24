---
title: "7.R11.P11 跨租戶上下文快取殘留"
date: 2026-04-24
description: "說明跨租戶上下文快取殘留如何造成租戶邊界滲漏"
weight: 7241
---

這個失效樣式的核心問題是租戶上下文切換與快取更新節奏分離。當快取殘留，跨租戶協作路徑會產生邊界滲漏。

## 常見形成條件

- 租戶切換後快取上下文沒有即時更新。
- 協作角色變更未同步回收跨租戶權限。
- 查詢路徑共用多租戶快取鍵。

## 判讀訊號

- 跨租戶查詢頻率與資料量異常上升。
- 租戶切換後仍出現前一租戶資料回應。
- 協作關係中止後持續出現跨租戶存取。

## 案例觸發參考

- [Snowflake 2024](../../cases/data-exfiltration/snowflake-2024-credential-abuse/)
- [GitHub OAuth 2022](../../cases/supply-chain/github-oauth-2022-token-supply-chain/)

## 來源流程卡

- [跨租戶協作濫用](../cross-tenant-collaboration-abuse/)
