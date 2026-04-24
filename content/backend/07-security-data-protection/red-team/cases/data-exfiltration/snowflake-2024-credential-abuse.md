---
title: "7.R7.4.2 Snowflake 2024：憑證濫用與資料竊取"
date: 2026-04-24
description: "外洩憑證與 MFA 缺口如何在資料平台形成高風險外送事件"
weight: 71742
---

## 事故摘要

2024 年公開資訊指出，攻擊者利用外洩憑證在部分 Snowflake 客戶環境進行資料竊取與勒索活動。

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

- 共同基線：以 [runbook](../../../../knowledge-cards/runbook/) 與 [incident timeline](../../../../knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：資料平台預設強制 MFA 與網路政策。
- 日常：建立異常查詢與匯出告警。
- 事故中：分批停用可疑憑證、限制外送並啟動調查。

## 可引用章節

- `backend/07-security-data-protection` 的身份與資料治理
- `backend/04-observability` 的行為告警設計

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[snowflake.com](https://www.snowflake.com/en/blog/communication-on-recent-cyber-threat-activity/)
- 政府或監管：[cisa.gov](https://www.cisa.gov/news-events/alerts/2024/06/03/snowflake-recommends-customers-take-steps-prevent-unauthorized-access)
- 技術分析：[cloud.google.com](https://cloud.google.com/blog/topics/threat-intelligence/unc5537-snowflake-data-theft-extortion)
