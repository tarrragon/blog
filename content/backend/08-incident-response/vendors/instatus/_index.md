---
title: "Instatus"
date: 2026-05-01
description: "輕量 status page SaaS、現代 UI、價格敏感替代"
weight: 8
tags: ["backend", "incident-response", "vendor"]
---

Instatus 是輕量 status page SaaS、承擔三個責任：簡潔現代 UI 的 status page、component + incident management、跟 IR 工具整合（incident.io / Rootly / FireHydrant）。設計取捨偏向「價格親民 + UI 現代 + 中小團隊適用」、是 Atlassian Statuspage 的 budget-friendly 替代。

## 本章目標

1. 建 Instatus + 設 component
2. 寫 incident template + update
3. 配置 subscriber notification
4. API 從 IR 平台 push
5. 評估 Instatus vs Statuspage / Cachet

## 最短路徑

```bash
# 1. 註冊 Instatus
# 2. 建 component
# 3. 寫 test incident
# 4. 訂閱者 subscribe
```

## 日常操作與決策形狀

### Component / incident + Subscriber

子議題：

- Component status（跟 Statuspage 相似）
- Incident template + maintenance window
- Email / SMS / Slack / RSS / Discord / Teams / Telegram subscriber

### API + IR 整合

子議題：REST API、跟 incident.io / Rootly 整合、webhook

## 進階主題（按需閱讀）

### Custom domain + branding + Multi-language

子議題：status.example.com、custom CSS / logo（比 Statuspage 簡潔）、多語言 incident update

### Metrics 公開

子議題：uptime / response time、從 monitor source

## 排錯快速判讀

- **Subscriber 沒收到**：跟 Statuspage 類似、provider quota
- **Custom domain 失效**：DNS / SSL
- **API 失敗**：rate limit / token 失效

## 何時改走其他服務

| 需求形狀           | 改走                                                                                |
| ------------------ | ----------------------------------------------------------------------------------- |
| Enterprise SLA     | [Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/) |
| OSS 自管           | Cachet                                                                              |
| IR 平台內建 status | [FireHydrant](/backend/08-incident-response/vendors/firehydrant/)                   |

## 不在本頁內的主題

- 完整 API reference / Pricing / Custom CSS 細節

## 案例回寫

**待補 Instatus case**：startup / mid-size 採用、從 Statuspage 遷移 cost case。

## 下一步路由

- 上游：[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 平行：[Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/)
- 下游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
