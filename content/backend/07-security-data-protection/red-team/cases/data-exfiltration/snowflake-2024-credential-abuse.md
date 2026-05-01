---
title: "7.R7.4.2 Snowflake 2024：憑證濫用與資料竊取"
date: 2026-04-24
description: "外洩憑證與 MFA 缺口如何在資料平台形成高風險外送事件"
weight: 71742
---

## 事故摘要

2024 年公開資訊指出，攻擊者利用外洩憑證在部分 Snowflake 客戶環境進行資料竊取與勒索活動。

**本案例的演示焦點**：infostealer 收集的憑證 → MFA / network policy 缺口 → 大量查詢 / 匯出的資料外送 chain。重點在「資料平台 access policy + 異常匯出偵測」設計、其他 threat surface 由其他 case category 承擔。

## 攻擊路徑

1. 收集可用憑證。
2. 針對 MFA 或存取政策薄弱環境登入。
3. 執行大量查詢與資料外送。

## 失效控制面

- 身分基線未強制 MFA 與條件式存取。
- 查詢行為異常偵測門檻不足。
- 高價值資料匯出控制較弱。

## 如果 workflow 少一步會發生什麼

若缺少「憑證事件後立即收斂存取政策」，攻擊者可在低噪音情況下持續外送資料。

## 可落地的 workflow 檢查點

- 共同基線：以 [runbook](/backend/knowledge-cards/runbook/) 與 [incident timeline](/backend/knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：資料平台預設強制 MFA 與網路政策（network rule allowlist / 條件式存取），mechanism 是讓 leaked credential 即使有效也碰不到資料平台。
- 日常：建立異常查詢與匯出告警（query 體積 / 來源 IP / 跨 schema scan 模式）。
- 事故中：分批停用可疑憑證、限制外送並啟動調查（前提是事先有 credential inventory + 分批撤銷能力）。

## 從本案例到實作的 chain

本案例是事故敘事 layer，沿三步 chain 進入 implementation：

- **失效樣式**：[批次操作濫用](/backend/07-security-data-protection/red-team/problem-cards/bulk-operation-abuse/) + [Long-lived repeatable export artifact](/backend/07-security-data-protection/red-team/problem-cards/fp-long-lived-repeatable-export-artifact/) —— 把 leaked credential → bulk export 的 mechanism 抽象為可重用失效樣式。
- **控制面**：[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/) + [7.9 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/) + [7.12 偵測涵蓋與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) —— mitigation 的 mechanism / 前提 / context-dependence 在這裡定義。
- **演練 / 控制落地**：[Low-frequency exfiltration tabletop](/backend/07-security-data-protection/blue-team/materials/scenarios/low-frequency-exfiltration-tabletop/) + [Credential hygiene pattern](/backend/07-security-data-protection/blue-team/materials/control-patterns/credential-hygiene-pattern/) —— 把樣式轉成 tabletop 與 release gate 欄位。

## 來源

| 來源                                                                                                                                 | 類型      | 可引用範圍                                      |
| ------------------------------------------------------------------------------------------------------------------------------------ | --------- | ----------------------------------------------- |
| [snowflake.com](https://www.snowflake.com/en/blog/communication-on-recent-cyber-threat-activity/)                                    | 官方      | 攻擊入口、影響範圍、客戶側建議                  |
| [cisa.gov](https://www.cisa.gov/news-events/alerts/2024/06/03/snowflake-recommends-customers-take-steps-prevent-unauthorized-access) | 政府/監管 | 跨機構處置建議                                  |
| [cloud.google.com](https://cloud.google.com/blog/topics/threat-intelligence/unc5537-snowflake-data-theft-extortion)                  | 技術分析  | UNC5537 TTP、infostealer 來源、勒索鏈 telemetry |
