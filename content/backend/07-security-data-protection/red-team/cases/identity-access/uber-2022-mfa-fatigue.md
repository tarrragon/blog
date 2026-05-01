---
title: "7.R7.1.1 Uber 2022：MFA 疲勞與內部工具擴散"
date: 2026-04-24
description: "從社交工程到內部工具存取，拆解身分流程與權限邊界的失效點"
weight: 71711
---

## 事故摘要

2022 年 9 月，攻擊者先取得承包商帳號，再透過重複 MFA 請求與社交工程進入內部系統，後續接觸到多個內部管理工具。

**本案例的演示焦點**：social engineering → MFA push fatigue → 既有身份接入內部高權限工具的 identity-chain 失效。供應鏈植入、邊界零時差、資料外送量級壓力等其他 threat surface 由 supply-chain / edge-exposure / data-exfiltration 案例分類承擔。

## 攻擊路徑

1. 取得初始帳號。
2. 以 MFA fatigue 增加使用者誤同意機率。
3. 使用已登入身份接觸內部高權限工具。
4. 擴大可見範圍並造成營運干擾。

## 失效控制面

- 高風險登入路徑缺少 step-up 驗證。
- 內部工具授權邊界不足，初始落點可快速擴散。
- 身分異常事件與值班告警串接不足。

## 如果 workflow 少一步會發生什麼

若值班流程缺少「異常 MFA 請求密度」檢查，團隊會把登入異常當成一般使用者問題，導致處置時間延後、擴散面增加。

## 可落地的 workflow 檢查點

- 發布前：高風險操作要求 phishing-resistant 強認證（WebAuthn / passkey、阻擋可被連續同意的 push approval）+ 裝置信任綁定（managed device / posture check），mechanism 是讓「同意」不再是攻擊者唯一所需的人類動作。
- 日常：監控 [authentication](/backend/knowledge-cards/authentication/) 異常事件（短時內 MFA 請求密度、跨地理 / 跨裝置序列）與 [on-call](/backend/knowledge-cards/on-call/) 升級規則。
- 事故中：快速凍結可疑身分、切斷高權限工具存取（依賴內部工具事先有 token revocation 與 session kill 能力）、建立 [incident timeline](/backend/knowledge-cards/incident-timeline/)。

## 從本案例到實作的 chain

本案例是事故敘事 layer，沿三步 chain 進入 implementation：

- **失效樣式**：[第三方授權濫用](/backend/07-security-data-protection/red-team/problem-cards/third-party-authorization-abuse/) + [權限提升流程濫用](/backend/07-security-data-protection/red-team/problem-cards/privilege-escalation-flow-abuse/) —— 把本案例的 mechanism 抽象為可重用失效樣式。
- **控制面**：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/) + [7.3 入口與伺服端保護](/backend/07-security-data-protection/entrypoint-and-server-protection/) —— mitigation 的 mechanism / 前提 / context-dependence 在這裡定義。
- **演練 / 控制落地**：[Identity support token tabletop](/backend/07-security-data-protection/blue-team/materials/scenarios/identity-support-token-tabletop/) + [Credential hygiene pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/credential-hygiene-pattern/) —— 把樣式轉成 tabletop 與 release gate 欄位。

## 來源

| 來源                                                                                                                       | 類型      | 可引用範圍                                                     |
| -------------------------------------------------------------------------------------------------------------------------- | --------- | -------------------------------------------------------------- |
| [uber.com](https://www.uber.com/newsroom/security-update/)                                                                 | 官方      | 攻擊者進入路徑、影響範圍與第一手時序                           |
| [cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-320a)                                            | 政府/監管 | Scattered Spider / UNC3944 TTP、跨組織 social engineering      |
| [cloud.google.com](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-sms-phishing-sim-swapping-ransomware/) | 技術分析  | Mandiant 對 social engineering、SIM swap、後續勒索鏈 telemetry |
