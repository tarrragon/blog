---
title: "Azure AD / Entra ID"
date: 2026-05-01
description: "Microsoft Identity 控制面失效與 cascading 影響"
weight: 14
---

Azure AD（現 Entra ID）是 Microsoft 生態的 identity 控制面、其失效會讓所有依賴 SSO 的服務無法登入、是 identity-as-cascading-point 的代表。

## 規劃重點

- Identity 控制面 single point of cascading：SSO 失效擴散到所有下游
- 配置變更 staged rollout 的限制：identity 服務難以 region-staged
- Token cache 緩衝：客戶端 token 有效期決定 outage 感受時間
- 跨產品依賴：M365 / Teams / GitHub Enterprise 等的隱性依賴

## 預計收錄事故

| 年份 | 事故                | 教學重點                                |
| ---- | ------------------- | --------------------------------------- |
| 2020 | 多次全球登入失效    | Identity cascading、staged rollout 限制 |
| 2021 | DNS / token service | Identity 服務的 sub-component 風險      |

## 案例定位

Azure AD 這個案例在講的是 identity 控制面一旦退化，許多看似獨立的服務都會一起受影響。讀者先看懂 Entra ID、Service Health 與 M365 health console 的分工，再把身份驗證視為跨服務的基礎路由。

## 判讀重點

當 identity control plane 出現異常時，恢復順序往往比單一服務本身更重要。先讓監控與通訊路徑回穩，再處理驗證與登入流量，才能避免修復過程再度放大故障。

## 可操作判準

- 能否把身份驗證失效與單一應用失效分開判讀
- 能否從 Service Health 找到影響範圍與恢復節奏
- 能否把 PIR 與 health dashboard 當成同一條對外路由
- 能否辨識哪些障礙來自 identity，哪些來自下游服務

## 與其他案例的關係

Azure AD 是 Microsoft 365、GitHub Enterprise 與其他 SaaS 服務的基礎路由，這讓它和 AWS S3、GCP 一樣都屬於「控制面失效會放大」的案例。它最適合拿來和 Microsoft 365 一起讀，因為兩者分別描述了 identity 層與協作層的相依關係。

## 代表樣本

- 2020 年多次全球登入失效是 identity cascading 的典型樣本。
- 2021 年 DNS / token service 問題則顯示 sub-component 也能放大成平台級風險。
- Azure Service Health 與 M365 health console 是對外路由的關鍵。
- token cache 會決定 outage 在使用者端維持多久。
- identity 是所有 SSO 服務的基礎路由。
- staged rollout 在 identity 服務上特別難做，因為影響面太大。
- token service 與 DNS 故障會把身份驗證整體拉下來。
- service health 變成客戶理解影響範圍的第一手資訊。

## 引用源

- [Service Level Agreement performance for Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/identity/monitoring-health/reference-sla-performance)：Entra ID 的 SLA / incident history 入口。
- [What is Azure Service Health?](https://learn.microsoft.com/en-us/azure/service-health/service-health-overview)：Azure Service Health 與 status / advisories 的官方說明。
- [How to check Microsoft 365 service health](https://learn.microsoft.com/microsoft-365/enterprise/view-service-health?view=o365-worldwide)：M365/Entra 相關 health console 的用法。
- [Azure reliability documentation](https://learn.microsoft.com/mt-mt/azure/reliability)：Azure 可靠性文件總入口。
