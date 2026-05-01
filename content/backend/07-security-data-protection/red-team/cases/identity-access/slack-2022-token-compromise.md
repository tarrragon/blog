---
title: "7.R7.1.7 Slack 2022：企業 token 與程式碼資產路徑"
date: 2026-04-24
description: "員工帳號被社交工程利用後，企業 token 與私有程式碼資產的防線如何運作"
weight: 71717
---

## 事故摘要

Slack 2022 安全公告說明攻擊者透過員工帳號路徑接觸內部資產，突顯企業 token 與程式碼資產的連動風險。

**本案例的演示焦點**：員工身分被取得後 → 內部 token / 程式碼資產的橫向擴散風險，重點在 token 範圍邊界與 audit signal 匯流的設計。其他 threat surface 由其他 case category 承擔。

## 攻擊路徑

1. 先透過社交工程取得員工憑證。
2. 進入內部工具並接觸 token 或程式碼資產。
3. 嘗試擴大到高價值系統或資料節點。

## 失效控制面

- 員工身份遭濫用後的隔離速度不足。
- token 範圍與用途邊界定義不夠細緻。
- 程式碼資產存取異常訊號未快速匯流。

## 如果 workflow 少一步會發生什麼

若少了「內部 token 快速撤銷」步驟，攻擊者會維持有效會話，讓追查與復原成本上升。

## 可落地的 workflow 檢查點

- 發布前：把管理 token 分域並限制到最小權限（依用途切 audience，避免單一 token 跨多個敏感系統），mechanism 是讓單點接管不會直接通到所有資產。
- 日常：建立 [alert runbook](/backend/knowledge-cards/alert-runbook/) 監控異常存取（repo 異常 clone、token 跨 IP / 跨 device 序列）。
- 事故中：分層撤銷 token、並用 [blast radius](/backend/knowledge-cards/blast-radius/) 框定影響面（前提是 token 有 inventory 可查 issuer / scope）。

## 從本案例到實作的 chain

本案例是事故敘事 layer，沿三步 chain 進入 implementation：

- **失效樣式**：[委派操作濫用](/backend/07-security-data-protection/red-team/problem-cards/delegated-operation-abuse/) + [邀請流程濫用](/backend/07-security-data-protection/red-team/problem-cards/invite-flow-abuse/) —— 把員工身分接管 → token / 資產存取的 mechanism 抽象為可重用失效樣式。
- **控制面**：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/) + [7.8 secrets 與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) —— mitigation 的 mechanism / 前提 / context-dependence 在這裡定義。
- **演練 / 控制落地**：[Credential hygiene pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/credential-hygiene-pattern/) + [Evidence chain pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/evidence-chain-pattern/) —— 把樣式轉成 token 治理欄位與證據鏈。

## 來源

| 來源                                                                                                           | 類型      | 可引用範圍                                 |
| -------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------ |
| [slack.com](https://slack.com/blog/news/slack-security-update)                                                 | 官方      | 攻擊入口、影響範圍、token 處置時序         |
| [cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-320a)                                | 政府/監管 | 跨組織 social engineering TTP              |
| [cloud.google.com](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-targets-saas-applications) | 技術分析  | UNC3944 對 SaaS / token 接管模式 telemetry |
