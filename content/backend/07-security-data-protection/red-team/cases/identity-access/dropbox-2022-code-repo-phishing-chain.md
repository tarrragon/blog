---
title: "7.R7.1.8 Dropbox 2022：釣魚入侵與程式碼倉儲風險"
date: 2026-04-24
description: "從員工釣魚事件到私有程式碼資產保護，建立身分與研發資產的聯防流程"
weight: 71718
---

## 事故摘要

Dropbox 2022 事件顯示員工帳號釣魚成功後，攻擊者可接觸私有程式碼倉儲與內部文件資產。

**本案例的演示焦點**：員工 phishing → OAuth / 內部 SSO 接管 → 高敏感研發資產（私有 repo / 內部文件）橫向存取的身分鏈。其他 threat surface 由 supply-chain（artifact 植入）/ edge-exposure（邊界漏洞）/ data-exfiltration（量級外送壓力）案例分類承擔。

## 攻擊路徑

1. 社交工程鎖定員工帳號。
2. 取得可登入的企業身份。
3. 存取程式碼倉儲與內部文件系統。

## 失效控制面

- 員工端高風險登入驗證策略不足。
- 研發資產保護缺少額外 step-up 驗證。
- 身分異常與程式碼倉儲稽核串接不足。

## 如果 workflow 少一步會發生什麼

若少了「程式碼資產異常存取升級」步驟，攻擊者可在內部環境延長停留時間並擴大探索範圍。

## 可落地的 workflow 檢查點

- 發布前：對高敏感 repo 操作要求強化 [authentication](/backend/knowledge-cards/authentication/)（phishing-resistant 因子、step-up 不只密碼 + OTP），mechanism 是讓 phishing-collected 憑證在 step-up 環節失效。
- 日常：將 repo 存取告警納入 [on-call](/backend/knowledge-cards/on-call/) 流程（異常 clone / push 模式、跨地理 / 跨裝置序列）。
- 事故中：即時凍結可疑憑證與連線、保留時間軸證據（依賴 repo / SSO 事先有 audit log retention）。

## 從本案例到實作的 chain

本案例是事故敘事 layer，沿三步 chain 進入 implementation：

- **失效樣式**：[邀請流程濫用](/backend/07-security-data-protection/red-team/problem-cards/invite-flow-abuse/) + [委派操作濫用](/backend/07-security-data-protection/red-team/problem-cards/delegated-operation-abuse/) —— 把 phishing → OAuth grant → 委派擴散的 mechanism 抽象為可重用失效樣式。
- **控制面**：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/) + [7.6 供應鏈完整性與 artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) —— 研發資產 mitigation 的 mechanism / 前提在這裡定義。
- **演練 / 控制落地**：[Credential hygiene pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/credential-hygiene-pattern/) + [Evidence chain pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/evidence-chain-pattern/) —— 把樣式轉成 release gate 欄位與證據保存欄位。

## 來源

| 來源                                                                                                           | 類型      | 可引用範圍                                       |
| -------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------ |
| [dropbox.tech](https://dropbox.tech/security/a-security-update-on-code-repositories)                           | 官方      | phishing 入口、影響範圍、研發資產處置時序        |
| [cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-320a)                                | 政府/監管 | 跨組織 social engineering TTP                    |
| [cloud.google.com](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-targets-saas-applications) | 技術分析  | UNC3944 對 SaaS 攻擊模式、phishing kit telemetry |
