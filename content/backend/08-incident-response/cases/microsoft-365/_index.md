---
title: "Microsoft 365"
date: 2026-05-01
description: "Microsoft 365 SaaS 套件事故與企業客戶影響"
weight: 23
---

Microsoft 365（Exchange Online / Teams / SharePoint）是企業 SaaS 套件的代表、事故影響企業生產力、Microsoft 的 PIR 揭露格式具有教學價值。

## 規劃重點

- 企業 SaaS 套件的 blast radius：跨產品事故對企業客戶的影響
- 跟 Azure AD 的依賴：Identity 失效 vs M365 服務失效的分層
- Tenant-level vs region-level 影響：多租戶 SaaS 的部分事故揭露
- PIR 格式：Microsoft 的 Public Incident Report 結構

## 預計收錄事故

| 年份 | 事故                       | 教學重點                       |
| ---- | -------------------------- | ------------------------------ |
| 2023 | Exchange Online 大規模失效 | 跨企業客戶通訊影響             |
| 2024 | Teams 全球失效             | 同步通訊工具失效的 IR 通訊困境 |

## 案例定位

Microsoft 365 這個案例在講的是一組共享 productivity 服務如何把單點事故變成廣域通訊問題。讀者先看懂 service health、PIR 與 [readiness](/backend/knowledge-cards/readiness/) 的責任，再把 M365 視為企業客戶的協作底層。

## 判讀重點

當 Exchange Online 或 Teams 失效時，復原不只是在服務本身恢復，還要讓客戶知道通訊與協作功能何時能回來。這類事故的關鍵在於可見性與一致的對外更新，讓企業能決定是否切換替代流程。

## 可操作判準

- 能否快速判斷影響的是哪個 M365 子服務
- 能否從 service health 看出恢復順序
- 能否把 PIR 的資訊轉成客戶能執行的替代路徑
- 能否把 [readiness](/backend/knowledge-cards/readiness/) 與實際 outage 對齊

## 與其他案例的關係

Microsoft 365 和 Azure AD 是一組必讀對照，前者看協作服務層的影響，後者看 identity 基礎層的失效。它也能和 Slack 一起讀，因為兩者都在說明當通訊平台出事時，客戶需要的是清楚的狀態與替代流程，而不是只有技術術語。

## 代表樣本

- Exchange Online 大規模失效代表企業通訊與協作服務的廣域影響。
- Teams 全球失效則顯示 IR 通訊本身也會受到通訊工具失效的影響。
- service health 與 PIR 的公開格式會影響客戶判讀速度。
- tenant-level 與 region-level 失效要分開看。
- [readiness](/backend/knowledge-cards/readiness/) 讓 Microsoft 能把復原流程標準化。
- built-in service resiliency 是企業 SaaS 的預設期待。
- shared productivity suite 讓一個服務失效就能放大成企業生產力問題。
- customer communication 與技術復原並行，才能避免恢復過程的資訊落差。

## 引用源

- [Service health and continuity](https://learn.microsoft.com/en-us/office365/servicedescriptions/office-365-platform-service-description/service-health-and-continuity?country=au&culture=en-au)：M365 服務健康、PIR 與通訊政策。
- [How to check Microsoft 365 service health](https://learn.microsoft.com/microsoft-365/enterprise/view-service-health?view=o365-worldwide)：Service health 的使用方式。
- [Microsoft 365 incident readiness - Unified](https://learn.microsoft.com/en-us/services-hub/unified/health/ir-m365)：Microsoft 的 incident readiness / PIR 流程。
- [Built-in service resiliency in Microsoft 365](https://learn.microsoft.com/en-us/compliance/assurance/assurance-m365-service-resiliency?source=recommendations)：M365 服務韌性與 downtime 定義。
