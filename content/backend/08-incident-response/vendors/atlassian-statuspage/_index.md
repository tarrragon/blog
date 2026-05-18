---
title: "Atlassian Statuspage"
date: 2026-05-01
description: "公開狀態頁 SaaS、Atlassian 出品"
weight: 7
tags: ["backend", "incident-response", "vendor"]
---

Statuspage 是 Atlassian 收購整合的公開狀態頁 SaaS、承擔三個責任：對外公開服務狀態揭露（component / incident / maintenance）、subscriber notification（email / SMS / Slack / webhook / RSS）、自有 domain + branding。是公開狀態頁的事實標準、跟 Opsgenie / PagerDuty / IR 平台廣泛整合。

## 本章目標

1. 建 Statuspage + 設 component / group
2. 寫第一個 incident update（template-driven）
3. 配置 subscriber notification channels
4. API 自動化（從 IR 平台 push update）
5. 設定 custom domain + 品牌一致 UI

## 最短路徑

```bash
# 1. 註冊 Statuspage、選 plan
# 2. 建 component（按服務拆）
# 3. 寫 test incident
# 4. 訂閱者 self-service subscribe
```

## 日常操作與決策形狀

### Component / group 設計

子議題：

- Component 對應服務 / API endpoint
- Group 組織多 component
- Status：operational / degraded / partial outage / major outage

### Incident lifecycle + Subscriber

子議題：

- Investigating → Identified → Monitoring → Resolved
- Template（標準措辭）
- Email / SMS / Slack / RSS / webhook subscriber
- Subscribe by component（部分訂閱）

## 進階主題（按需閱讀）

### Scheduled maintenance

子議題：提前公告 maintenance window、auto-publish + auto-resolve

### API automation

子議題：從 IR 平台 push update、跟 Opsgenie alert sync、custom field

### Custom domain + branding

子議題：status.example.com vs example.statuspage.io、custom CSS / logo、多語言

### Metrics 公開

子議題：uptime / response time 圖表、來源（Datadog / Pingdom）

### Audience：public / private / partner

子議題：public（所有人）/ private（authenticated）/ partner（B2B 獨立 view）

## 排錯快速判讀

- **Incident update 沒發**：API token 失效 / IR 沒 trigger
- **Subscriber 沒收到**：email bounce / SMS provider 限額
- **Component status 跟實際不符**：自動 sync 規則錯 / 手動沒更新
- **Custom domain 失效**：DNS / SSL cert 過期

## 何時改走其他服務

| 需求形狀           | 改走                                                              |
| ------------------ | ----------------------------------------------------------------- |
| 預算敏感           | [Instatus](/backend/08-incident-response/vendors/instatus/)       |
| OSS / 自管         | Cachet                                                            |
| IR 平台內建 status | [FireHydrant](/backend/08-incident-response/vendors/firehydrant/) |
| 內部 only          | 內部 dashboard（Grafana / Datadog）                               |

## 不在本頁內的主題

- 完整 API reference / Custom CSS / Statuspage Connect

## 案例回寫

**Statuspage 廣泛使用**：GitHub / Cloudflare / AWS / Atlassian / Slack / Discord 等。

| 案例                                                                | 對應主題               |
| ------------------------------------------------------------------- | ---------------------- |
| [GitHub cases](/backend/08-incident-response/cases/github/)         | Statuspage update 流程 |
| [Cloudflare cases](/backend/08-incident-response/cases/cloudflare/) | Statuspage 公開時程    |
| [Atlassian cases](/backend/08-incident-response/cases/atlassian/)   | 自家用 Statuspage      |

## 下一步路由

- 上游：[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 平行：[Instatus](/backend/08-incident-response/vendors/instatus/)
- 下游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
