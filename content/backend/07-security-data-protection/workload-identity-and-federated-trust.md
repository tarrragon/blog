---
title: "7.10 Workload Identity 與聯邦信任邊界"
date: 2026-04-24
description: "定義非人類身份、跨平台信任與短時憑證治理問題"
weight: 80
---

本章的責任是把機器到機器信任風險拆成可驗證邊界，讓 workload identity 與 federation 不會把外部風險直接帶入內部高權限路徑。

## 本章寫作邊界

本章聚焦 workload identity、federation、短時憑證與信任收斂，不討論雲廠商特定設定語法。

## Workload Identity 治理模型

workload identity 的核心責任是把機器身份與人類身份分開治理，避免長期共享憑證形成不可控傳導。

1. 身分分離：把人類操作身份與機器執行身份拆分責任。
2. 邊界定義：把 workload 可觸及資源限制在最小業務範圍。
3. 聯邦信任：把跨平台 token 交換限制在可驗證來源與用途。
4. 短時憑證：把憑證有效時窗縮短，降低竊取後可利用時間。
5. 收斂節奏：把外部事件後的信任重評估納入固定流程。

## 判讀流程

判讀流程的責任是把「機器可用憑證」轉成「機器可控身份」。

1. 先盤點 workload 身份來源、簽發路徑與責任主體。
2. 再檢查 token scope、TTL 與可觸及資源是否超出用途。
3. 接著檢查 federation 來源與授權決策是否可回查。
4. 最後把缺口交接到平台、可靠性與事件收斂流程。

## 問題節點（案例觸發式）

| 問題節點            | 判讀訊號                     | 風險後果           | 前置控制面                                                     |
| ------------------- | ---------------------------- | ------------------ | -------------------------------------------------------------- |
| 機器身份來源不清    | credential 缺乏發放責任鏈    | 憑證可用窗口失控   | [credential](/backend/knowledge-cards/credential/)             |
| 跨平台信任擴張過快  | token 使用面超出預期服務邊界 | 外部事件可快速傳導 | [trust-boundary](/backend/knowledge-cards/trust-boundary/)     |
| 短時憑證策略不完整  | 失效節奏與授權節奏分離       | 撤銷成本上升       | [token-revocation](/backend/knowledge-cards/token-revocation/) |
| federation 回查不足 | 信任來源與授權決策無法回串   | 事故判讀時間延長   | [audit-log](/backend/knowledge-cards/audit-log/)               |

## 常見風險邊界

風險邊界的責任是判斷何時機器身份治理需要升級處置。

- 機器憑證來源無法對應到責任主體時，代表信任鏈不可驗證。
- 跨平台 token 在非預期服務長期可用時，代表 federation 邊界鬆動。
- 短時憑證實作退化成長時存活時，代表撤銷窗口擴大。
- 供應商事件後內部 workload 權限未收斂時，代表外部風險仍在傳導。

## 案例觸發參考

案例觸發的責任是驗證機器身份模型是否能承受現實攻擊壓力。

- 第三方身分鏈事件： [Okta + Cloudflare 2023](/backend/07-security-data-protection/red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/)
- token 傳導與後續擴散： [Cloudflare 2023](/backend/07-security-data-protection/red-team/cases/identity-access/cloudflare-2023-okta-token-follow-through/)
- 憑證濫用下的資料平台風險： [Snowflake 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)

## 下一步路由

- 身份與平台邊界實作：`05-deployment-platform`
- 憑證輪替與驗證節奏：`06-reliability`
- 事件分級與收斂：`08-incident-response`
