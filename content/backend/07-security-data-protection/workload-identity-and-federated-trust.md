---
title: "7.10 Workload Identity 與聯邦信任邊界"
date: 2026-04-24
description: "定義非人類身份、跨平台信任與短時憑證治理問題"
weight: 80
tags: ["backend", "security"]
---

本章的責任是把機器到機器信任風險拆成可驗證邊界，讓 workload identity 與 federation 不會把外部風險直接帶入內部高權限路徑。

## 本章寫作邊界

本章聚焦 workload identity、federation、短時憑證與信任收斂，不討論雲廠商特定設定語法。

## 本章 threat scope

**In-scope**：workload 身份來源不清 / 跨平台信任擴張過快 / federation token scope 漂移 / 短時憑證策略不完整 / federation 回查不足 / 第三方授權範圍跟事件傳導半徑。

**Out-of-scope**（路由到他章）：

- 人類身分 → [7.2](../identity-access-boundary/)
- 機器憑證 lifecycle / 簽章金鑰 → [7.6](../secrets-and-machine-credential-governance/)
- 傳輸層 validation 路徑 → [7.5](../transport-trust-and-certificate-lifecycle/)
- 供應鏈 artifact 信任 → [7.12](../supply-chain-integrity-and-artifact-trust/)
- 偵測平台 → `04-observability`、實作交付 → `05` / `06` / `08`

Reader 對 in-scope 列表的 specific threat 應該能反向 trace 到本章問題節點；out-of-scope 議題請直接跳到對應章節、不在本章 audit 範圍。

## 從本章到實作

本章是 routing layer，沿兩條 chain 進入 implementation：

- **Mechanism**：問題節點表的 `[token-revocation]` 等 control link 進 knowledge-card、看具體機制 / 邊界 / context-dependence。
- **Delivery**：「下一步路由」欄位指向 `05-deployment-platform / 06-reliability / 08-incident-response`、接配置 / 驗證 / 處置交付。

兩條 chain 完成判準與模組級 chain 規格見 [從章節到實作的 chain](../#從章節到實作的-chain)。

## 跨章議題交叉引用

本章「第三方授權範圍跟事件傳導半徑」是 [7.2 供應商身分鏈傳導 SSoT](../identity-access-boundary/#跨章-ssot供應商身分鏈傳導) 在 workload identity 層的展現；canonical SSoT 在 7.2、本章補 federation token scope 過寬的 specific 訊號。

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

## Federation 信任漂移跟跨平台 token 重評估

Federation 信任漂移是 workload identity 獨有的失效模式：信任關係建立後、token 的 *來源* 跟 *用途* 隨時間逐步脫鉤、攻擊者可在非預期服務持續使用同一個 federated token。控制責任是定期重評估信任關係的有效性、把 federation 視為長期演化中的信任配置、跟業務變動 cycle 同步。

對應失效樣式 [Federated token trust drift](../red-team/problem-cards/fp-federated-token-trust-drift/)：揭露 federation 邊界失效的三個常見形成條件 — federation trust 建立後缺少定期重評估、token scope 與最小權限原則不一致、跨平台 token revocation 流程沒有同批收斂。Problem-card「判讀訊號」直接列出「同一聯邦 token 在非預期服務持續出現」「外部身分事件後高權限聯邦 token 存續比例偏高」。[Microsoft Storm-0558 2023](../red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) 作為背景 case 補上信任根失守時對 federation 漂移半徑的放大效應；該案例核心是簽章金鑰偽造、不是 federation drift 的代表 case、簽章金鑰治理見 [7.6 canonical](../secrets-and-machine-credential-governance/#簽章金鑰跟長期信任根)。

以下基於通用工程知識補充：定期重評估的工程實作要包含 *使用模式 audit*（token 實際被用在哪些 service / 跨多少 audience）跟 *授權決策回查*（federation 端的授權邏輯是否仍對應目前的業務需求）。日常治理要把 federation 視為跟業務 cycle 共演化的長期配置 — 業務變動 trigger 重評估、避免 token scope 隨時間累積到遠超實際用途。重評估節奏綁兩個 cycle：業務變動 + 時間到期、任一觸發即啟動。

## 第三方授權範圍跟事件傳導半徑

第三方授權的範圍直接決定供應商事件的內部傳導半徑。token scope 過寬時、供應商事件能影響的內部資源面積會超出原本授權的業務範圍；這層治理要在授權發起時就把 scope 收斂到最小必要、事件處置才能在已知範圍內快速分批收斂。

對應失效樣式 [Overscoped 第三方 token grant](../red-team/problem-cards/fp-overscoped-third-party-token-grant/)：揭露 token scope 過寬的三個常見形成條件 — 第三方 token scope 與實際用途不一致、token 期限過長且回收節奏落後、供應商事件後缺少分域收斂流程。同 frame 在 [Okta + Cloudflare 2023](../red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/) 案例落到事件實際處置面、可落地檢查點標明前提條件是「輪替能力涵蓋第三方授權 token、不只內部 session」。本章視角聚焦 workload identity 層 federation token scope；客戶側人類身分鏈收斂責任見 [7.2 § 第三方身分鏈的內部收斂責任](../identity-access-boundary/#第三方身分鏈的內部收斂責任)。

以下基於通用工程知識補充：scope 收斂的工程瓶頸通常在第三方平台的權限粒度 — 廠商提供的 scope 選項可能比實際需求粗、組織要在「接受粗 scope」「自建中間層收斂」「換廠商」之間取捨。中間層收斂是常見折衷、把第三方 token 在內部 proxy 後降權再傳遞給下游 service。中間層存在時、第三方 scope 跟內部 blast radius 解耦；中間層缺位時、兩者直接綁定。

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
