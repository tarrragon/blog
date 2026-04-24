---
title: "7.R7.1.4 MGM 2023：身分流程被打穿後的營運中斷"
date: 2026-04-24
description: "社交工程造成身分邊界失守後，如何演變成可用性與營運衝擊"
weight: 71714
---

## 事故摘要

2023 年 9 月，MGM 對外更新顯示，資安事件對營運造成明顯衝擊，反映出身份流程事件可快速轉為可用性問題。

## 攻擊路徑

1. 以身分流程弱點取得初始落點。
2. 橫向影響多個內部系統。
3. 連帶影響面向客戶的服務可用性。

## 失效控制面

- 身分事件與營運隔離界線不足。
- 關鍵業務流程缺少快速降級方案。
- 事件切換流程在高壓下不夠標準化。

## 如果 workflow 少一步會發生什麼

若缺少「服務降級與切換劇本」，即使識別到攻擊路徑，也難以在可接受時間內維持核心服務。

## 可落地的 workflow 檢查點

- 發布前：定義關鍵能力的 [degradation](../../../../knowledge-cards/degradation/) 路徑。
- 日常：演練 [failover](../../../../knowledge-cards/failover/) 與回復時序。
- 事故中：依 [incident severity](../../../../knowledge-cards/incident-severity/) 快速分級與跨團隊指揮。

## 可引用章節

- `backend/06-reliability` 的降級與回復策略
- `backend/08-incident-response` 的事故指揮模型

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：https://investors.mgmresorts.com/investors/news-releases/press-release-details/2023/MGM-Resorts-Provides-Cybersecurity-Incident-Update/default.aspx
- 政府或監管：https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-320a
- 技術分析：https://cloud.google.com/blog/topics/threat-intelligence/unc3944-targets-saas-applications
