---
title: "7.R7.2.2 GitHub OAuth 2022：第三方 token 供應鏈風險"
date: 2026-04-24
description: "第三方整合 token 被竊後，如何形成跨組織存取風險"
weight: 71722
---

## 事故摘要

2022 年 4 月，GitHub 公告指出攻擊者使用從第三方整合服務取得的 OAuth token 存取受影響組織資料。

**本案例的演示焦點**：第三方整合 OAuth token 被竊 → 跨組織下游存取的 federated trust supply-chain 風險。重點在 OAuth scope / lifetime / inventory 設計、跟身分鏈接管 (identity-access category) 形成互補視角。

## 攻擊路徑

1. 攻擊第三方整合節點。
2. 取得可用 OAuth token。
3. 使用 token 存取下游客戶資產。

## 失效控制面

- token 權限範圍過寬。
- token 生命周期偏長，撤銷速度慢。
- 整合關係資產盤點與監控不足。

## 如果 workflow 少一步會發生什麼

若缺少「第三方 token 全域盤點與快速撤銷」，事件發生後仍會留下可用 token，形成二次入侵窗口。

## 可落地的 workflow 檢查點

- 共同基線：以 [runbook](/backend/knowledge-cards/runbook/) 與 [incident timeline](/backend/knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：採最小權限 token 與明確用途分域（OAuth scope 不用 catch-all、按 audience 切），mechanism 是讓單個 token 接管不會通往無關資產。
- 日常：建立第三方整合清單與失效期限巡檢（含 token 上次使用時間、長期未用就主動失效）。
- 事故中：依清單自動化撤銷、輪替、補授權（前提是 token issuer 提供 bulk revocation API）。

## 從本案例到實作的 chain

本案例是事故敘事 layer，沿三步 chain 進入 implementation：

- **控制面**：[7.5 工作負載身份與 federated trust](/backend/07-security-data-protection/workload-identity-and-federated-trust/) + [7.8 secrets 與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) —— mitigation 的 mechanism / 前提 / context-dependence 在這裡定義。
- **演練 / 控制落地**：[Supply chain artifact drill](/backend/07-security-data-protection/blue-team/materials/scenarios/supply-chain-artifact-drill/) + [Credential hygiene pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/credential-hygiene-pattern/) —— 把樣式轉成 token 治理欄位與輪替演練。
- **跨章交接**：[backend/04-observability](/backend/04-observability/) 的第三方整合監測、[backend/05-deployment-platform](/backend/05-deployment-platform/) 的部署 token 治理。

供應鏈類事故不對應紅隊 problem-cards，主要 chain 直接從控制面起步。

## 來源

| 來源                                                                                                   | 類型      | 可引用範圍                                       |
| ------------------------------------------------------------------------------------------------------ | --------- | ------------------------------------------------ |
| [github.blog](https://github.blog/news-insights/company-news/security-alert-stolen-oauth-user-tokens/) | 官方      | OAuth token 被竊起點、影響組織範圍、初步處置時序 |
| [github.blog](https://github.blog/2022-12-08-notice-of-security-incident/)                             | 官方延伸  | 後續事件、跨整合影響評估                         |
| [cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-320a)                        | 政府/監管 | 跨組織 OAuth abuse / federated chain TTP         |
