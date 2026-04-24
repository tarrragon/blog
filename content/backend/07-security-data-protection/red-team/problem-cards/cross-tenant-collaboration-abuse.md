---
title: "7.R11.11 跨租戶協作濫用"
date: 2026-04-24
description: "說明跨租戶協作為何容易形成租戶邊界滲漏"
weight: 7221
---

跨租戶協作的核心風險是把隔離邊界與協作邊界放在同一流程。當租戶邏輯與協作語意沒有明確切分，流程會形成邊界滲漏。

## 為什麼會出問題

跨租戶協作通常服務商業生態與合作流程。協作需求若缺少租戶上下文檢查與權限最小化，讀取邊界容易被擴張。

## 常見失效樣式

- 協作邀請可直接取得跨租戶資料讀取。
- 租戶切換後沿用先前租戶權限快取。
- 協作關係中止後權限回收延遲。

## 判讀訊號

- 跨租戶查詢頻率與資料量異常上升。
- 租戶上下文切換與高風險操作連續發生。
- 協作關係變更後仍有持續存取行為。

## 案例觸發參考

- [Snowflake 2024](../../cases/data-exfiltration/snowflake-2024-credential-abuse/)
- [GitHub OAuth 2022](../../cases/supply-chain/github-oauth-2022-token-supply-chain/)

## 可連動章節

- [7.2 身分與授權邊界](../../../identity-access-boundary/)
- [7.4 資料保護與遮罩治理](../../../data-protection-and-masking-governance/)

## 對應失效樣式卡

- [7.R11.P11 跨租戶上下文快取殘留](../fp-cross-tenant-context-cache-residue/)
