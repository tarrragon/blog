---
title: "7.R7.1.1 Uber 2022：MFA 疲勞與內部工具擴散"
date: 2026-04-24
description: "從社交工程到內部工具存取，拆解身分流程與權限邊界的失效點"
weight: 71711
---

## 事故摘要

2022 年 9 月，攻擊者先取得承包商帳號，再透過重複 MFA 請求與社交工程進入內部系統，後續接觸到多個內部管理工具。

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

- 發布前：高風險操作要求強認證與裝置信任。
- 日常：監控 [authentication](../../../../../knowledge-cards/authentication/) 異常事件與 [on-call](../../../../../knowledge-cards/on-call/) 升級規則。
- 事故中：快速凍結可疑身分、切斷高權限工具存取、建立 [incident timeline](../../../../../knowledge-cards/incident-timeline/)。

## 可引用章節

- `backend/07-security-data-protection` 的認證與授權設計
- `backend/08-incident-response` 的啟動條件與角色分工

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[uber.com](https://www.uber.com/newsroom/security-update/)
- 政府或監管：[cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-320a)
- 技術分析：[cloud.google.com](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-sms-phishing-sim-swapping-ransomware/)
