---
title: "7.R7.1.5 Microsoft Storm-0558 2023：簽章金鑰鏈與郵件存取"
date: 2026-04-24
description: "從簽章金鑰保護失效到雲端郵件存取，拆解身分信任鏈的關鍵控制點"
weight: 71715
---

## 事故摘要

Storm-0558 事件揭露簽章金鑰治理一旦失效，攻擊者就能沿著身分信任鏈存取雲端郵件服務。

## 攻擊路徑

1. 取得可用的簽章金鑰材料。
2. 偽造可被驗證的身分權杖。
3. 以合法樣態存取目標信箱與資料。

## 失效控制面

- 簽章金鑰生命週期治理與隔離策略不足。
- 權杖驗證邊界缺少跨服務一致性檢查。
- 高風險身分事件的追查與升級節奏偏慢。

## 如果 workflow 少一步會發生什麼

若少了「跨租戶權杖異常立即升級」步驟，攻擊者可在低噪音條件下維持存取並擴大影響面。

## 可落地的 workflow 檢查點

- 發布前：把簽章金鑰納入硬體保護與輪替節奏。
- 日常：監控 [authentication](../../../../knowledge-cards/authentication/) 與 [incident timeline](../../../../knowledge-cards/incident-timeline/) 的異常關聯。
- 事故中：同步執行金鑰收斂、權杖失效、受影響範圍比對。

## 可引用章節

- `backend/07-security-data-protection` 的身分信任鏈設計
- `backend/08-incident-response` 的升級與通報節奏

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：https://www.microsoft.com/en-us/msrc/blog/2023/07/microsoft-mitigates-china-based-threat-actor-storm-0558-targeting-of-customer-email/
- 政府或監管：https://www.cisa.gov/resources-tools/resources/review-board-report-microsoft-exchange-online-incident
- 技術分析：https://msrc.microsoft.com/blog/2023/09/results-of-major-technical-investigations-for-storm-0558-key-acquisition/
