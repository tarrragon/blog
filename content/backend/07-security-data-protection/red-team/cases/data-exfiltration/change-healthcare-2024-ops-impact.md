---
title: "7.R7.4.3 Change Healthcare 2024：資料事件轉為營運中斷"
date: 2026-04-24
description: "醫療支付中樞事件如何同時衝擊資料安全與業務連續性"
weight: 71743
---

## 事故摘要

2024 年 Change Healthcare 事件顯示，資安事件可同時造成資料風險與支付流程中斷，影響範圍跨越供應鏈與醫療營運。

## 攻擊路徑

1. 攻擊核心服務入口。
2. 影響高集中度業務中樞。
3. 對下游機構與現金流造成連鎖效應。

## 失效控制面

- 關鍵業務中樞集中度高。
- 替代流程與手動回復路徑準備不足。
- 安全事件與業務連續性計畫連結不夠緊密。

## 如果 workflow 少一步會發生什麼

若缺少「事故中的業務連續性切換流程」，團隊會在技術修復之外承受長期營運中斷代價。

## 可落地的 workflow 檢查點

- 發布前：定義核心流程的 [RTO](../../../../../knowledge-cards/rto/) 與 [RPO](../../../../../knowledge-cards/rpo/)。
- 日常：演練核心交易路徑的降級方案。
- 事故中：技術處置與業務處置分軌並行。

## 可引用章節

- `backend/06-reliability` 的可用性與備援設計
- `backend/08-incident-response` 的事故分級與跨部門通訊

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[unitedhealthgroup.com](https://www.unitedhealthgroup.com/newsroom/2024/2024-04-22-uhg-updates-on-change-healthcare-cyberattack.html)
- 政府或監管：[cms.gov](https://www.cms.gov/newsroom/press-releases/cms-statement-change-healthcare-cyberattack)
- 技術分析：[aha.org](https://www.aha.org/cybersecurity/change-healthcare-cyberattack-updates)
