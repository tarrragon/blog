---
title: "7.R7.1.2 Okta + Cloudflare 2023：支援流程與身分供應鏈"
date: 2026-04-24
description: "支援工單與第三方身份供應商路徑如何變成入侵鏈的一部分"
weight: 71712
---

## 事故摘要

2023 年 10 到 11 月，Okta 與 Cloudflare 的公開說明都指出，攻擊者透過支援相關流程取得可用資訊，形成跨組織的身分供應鏈風險。

**本案例的演示焦點**：上游供應商支援流程（HAR 檔 / 工單附件 / session token）→ 客戶側身分接管的跨組織 chain。重點在 support workflow 承載身分敏感材料時的邊界 / 通報節奏設計。

## 攻擊路徑

1. 鎖定支援流程與可取得的工單資料。
2. 利用流程缺口取得敏感資訊或權限線索。
3. 以第三方身份供應商作為橋接點延伸到客戶側。

## 失效控制面

- 支援資料流沒有被視為高敏感資產。
- 憑證或會話資料生命周期管理不足。
- 供應商事件到客戶內部輪替流程沒有強制觸發。

## 如果 workflow 少一步會發生什麼

若缺少「供應商事件觸發的全域憑證輪替」，事件會停在公告層，實際可利用的憑證仍留在環境中。

## 可落地的 workflow 檢查點

- 發布前：支援系統資料分級、限制下載與外流路徑（HAR sanitizer、附件 retention 限制），mechanism 是讓支援系統的「便利性」不直接傳導到身分風險。
- 日常：建立第三方事件觸發的 [runbook](/backend/knowledge-cards/runbook/)（含 cross-vendor coordination、客戶先發現的反向通報）。
- 事故中：啟用供應商事件專用 [playbook](/backend/knowledge-cards/playbook/)、執行輪替、追蹤、封鎖（前提是輪替能力涵蓋第三方授權 token、不只內部 session）。

## 從本案例到實作的 chain

本案例是事故敘事 layer，沿三步 chain 進入 implementation：

- **失效樣式**：[第三方授權濫用](/backend/07-security-data-protection/red-team/problem-cards/third-party-authorization-abuse/) + [Overscoped 第三方 token grant](/backend/07-security-data-protection/red-team/problem-cards/fp-overscoped-third-party-token-grant/) —— 把 support workflow 承載身分材料的 mechanism 抽象為可重用失效樣式。
- **控制面**：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/) + [7.5 工作負載身份與 federated trust](/backend/07-security-data-protection/workload-identity-and-federated-trust/) + [7.12 偵測涵蓋與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) —— mitigation 的 mechanism / 前提在這裡定義。
- **演練 / 控制落地**：[Identity support token tabletop](/backend/07-security-data-protection/blue-team/materials/scenarios/identity-support-token-tabletop/) + [Credential hygiene pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/credential-hygiene-pattern/) + [Control owner pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/control-owner-pattern/) —— 把樣式轉成 tabletop、release gate 欄位與跨組織 owner 分工。

## 來源

| 來源                                                                                                                      | 類型      | 可引用範圍                                                  |
| ------------------------------------------------------------------------------------------------------------------------- | --------- | ----------------------------------------------------------- |
| [sec.okta.com](https://sec.okta.com/articles/2023/11/unauthorized-access-oktas-support-case-management-system-root-cause) | 官方      | 攻擊路徑、support system root cause、影響範圍               |
| [blog.cloudflare.com](https://blog.cloudflare.com/thanksgiving-2023-security-incident/)                                   | 政府/監管 | 客戶側偵測 / 即時回應、Zero Trust 防守效果（peer evidence） |
| [cloud.google.com](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-targets-saas-applications)            | 技術分析  | UNC3944 對 SaaS / 身分供應鏈的攻擊模式                      |
