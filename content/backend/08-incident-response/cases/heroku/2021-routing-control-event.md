---
title: "Heroku：Routing 控制事件與多租戶影響"
date: 2026-05-07
description: "PaaS 路由層異常時，如何限制租戶擴散並維持可用通訊。"
weight: 51
---

這起案例的核心責任是守住路由層故障的擴散邊界。PaaS 共享入口若失效，租戶影響會快速放大。

## 判讀訊號

| 訊號                         | 判讀重點             | 回寫章節                                                            |
| ---------------------------- | -------------------- | ------------------------------------------------------------------- |
| router error spike           | 入口故障是否擴散     | [8.3](/backend/08-incident-response/containment-recovery-strategy/) |
| tenant-level impact variance | 影響是否呈現分區差異 | [8.20](/backend/08-incident-response/customer-impact-assessment/)   |
| status lag                   | 對外更新是否落後     | [8.10](/backend/08-incident-response/stakeholder-communication/)    |

## 控制面與下一步

事故流程需先切分租戶影響，再做回復批次，並回寫 [8.4](/backend/08-incident-response/incident-communication/)。
