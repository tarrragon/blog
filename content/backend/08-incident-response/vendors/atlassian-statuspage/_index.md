---
title: "Atlassian Statuspage"
date: 2026-05-01
description: "公開狀態頁 SaaS、Atlassian 出品、enterprise polish + Atlassian 生態整合、subscriber notification + component dependency 是核心責任"
weight: 7
tags: ["backend", "incident-response", "vendor"]
---

Statuspage 是 Atlassian 收購整合的公開狀態頁 SaaS、承擔三個責任：對外公開服務狀態揭露（component / incident / maintenance）、subscriber notification（email / SMS / Slack / Microsoft Teams / webhook / RSS）、自有 domain + branding。是公開狀態頁的事實標準、跟 [Opsgenie](/backend/08-incident-response/vendors/opsgenie/) 同屬 Atlassian 事故處理生態（搭配 Jira Service Management、Confluence post-mortem template）、也跟 [PagerDuty](/backend/08-incident-response/vendors/pagerduty/) / [incident.io](/backend/08-incident-response/vendors/incident-io/) 等第三方 IR 平台廣泛整合。

## 服務定位

Statuspage 的定位是 *對外狀態頁領導品牌*、責任邊界是 *把內部 incident state 翻譯成對外可讀的公告*、不是 IR workflow 本身。功能涵蓋 component status（operational / degraded / partial outage / major outage / under maintenance）、incident update（lifecycle + template）、scheduled maintenance（pre-announce + auto-publish + auto-resolve）、metrics chart（uptime / latency 公開圖表、來源 Datadog / Pingdom / New Relic / Library）、audience targeting（public / private / partner / per-customer 分軌）。

跟 [Opsgenie](/backend/08-incident-response/vendors/opsgenie/) / Confluence / Jira Service Management 是同生態 — Statuspage 接 Opsgenie alert 自動 create incident draft、incident resolve 自動 publish post-mortem 到 Confluence、JSM ticket 連結 Statuspage incident URL。enterprise polish（custom CSS / 自有 domain / multi-language / SSO admin）是賣點、defaults 也夠用、是大型 SaaS public-facing 的主流選擇。

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

## 最短判讀路徑

判斷 Statuspage deployment 是否健康、最少看四件事：

- **誰能 publish update**：admin / page admin / incident manager 的權限分層、incident publish 是否走 template + reviewer、API token 是否分 *human ops* 跟 *machine push* 兩條
- **Component dependency 設計**：component 是否對應 *使用者可感知的服務面*（不是內部 microservice）、group 是否拆得太細導致 status update 散落、dependency map 是否誇大內部架構讓對外公告失焦
- **Metrics integration**：uptime / latency chart 來源是否跟內部 SLO 對齊（Datadog / Pingdom / 自家 API push）、metrics 是否跟 incident state 同步（incident 開了 metrics 還綠燈 = 對外公信力下降）
- **Audience targeting**：public / private / partner page 是否清楚分軌、subscriber list 是否定期清理（離職者 / 失效 email / SMS bounce）、per-customer audience 是否走 SSO 控管

四件事任一缺失、就是 [Incident Communication](/backend/08-incident-response/incident-communication/) 邊界的待補項目。

## 日常操作與決策形狀

### Component / group 設計

子議題：

- Component 對應服務 / API endpoint（粒度跟使用者可感知一致、不是內部服務拓樸）
- Group 組織多 component（按產品線 / 區域 / 客戶層）
- Status：operational / degraded / partial outage / major outage / under maintenance
- Component dependency：parent component 自動匯總 child status（過細會造成內部架構洩漏）

### Incident lifecycle + Subscriber

子議題：

- Investigating → Identified → Monitoring → Resolved 四段、每段都該推 update
- Template（標準措辭、降低 incident commander 寫稿壓力、避免揭露過多內部細節）
- Email / SMS / Slack / Microsoft Teams / webhook / RSS subscriber
- Subscribe by component（部分訂閱、避免 noise）

## 進階主題（按需閱讀）

### Audience-specific page

子議題：public（所有人）/ private（authenticated、內部員工 / 特定客戶）/ partner（B2B 獨立 view）、per-customer / per-region status（大型 SaaS 用、避免單一 region 事故影響全球公信力）

### Scheduled maintenance

子議題：提前公告 maintenance window、auto-publish + auto-resolve、跟 change management 流程串接、recurring maintenance 用 template

### Subscription management

子議題：email / SMS / Slack / Microsoft Teams / webhook 多通道、bounce 清理、SMS provider 限額（高峰 incident 可能塞車）、subscriber list growth 變廣告管理目標時需 GDPR / CAN-SPAM 治理

### Templates

子議題：incident template（standard outage / degraded performance / scheduled maintenance）、避免每次 incident commander 重新寫稿、降低措辭風險

### IR 平台整合

子議題：[PagerDuty](/backend/08-incident-response/vendors/pagerduty/) Status Pages integration、[incident.io](/backend/08-incident-response/vendors/incident-io/) Statuspage sync、[Opsgenie](/backend/08-incident-response/vendors/opsgenie/) incident-to-Statuspage workflow、[FireHydrant](/backend/08-incident-response/vendors/firehydrant/) auto-publish

### API automation

子議題：從 IR 平台 push update、跟 Opsgenie alert sync、custom field、API token 分軌（human ops vs machine push）、retry / idempotency

### Custom domain + branding

子議題：status.example.com vs example.statuspage.io、custom CSS / logo、多語言、SSO trap（admin SSO 設錯導致 lock-out）

### Metrics 公開

子議題：uptime / response time 圖表、來源（Datadog / Pingdom / New Relic / 自家 API push）、metrics 跟 incident state 同步、避免 metrics 綠燈但 incident open

## 排錯快速判讀

- **Incident update 沒發**：API token 失效 / IR 沒 trigger / template variable 漏帶
- **Stale status（incident 過了還掛 active）**：auto-resolve 規則沒設 / IR 平台 close 沒 sync / oncall 手動忘記 resolve
- **Subscriber 沒收到**：email bounce / SMS provider 限額 / Slack workspace token expired
- **Component dependency map 過細**：把內部 microservice 都拉成 component、對外公告失焦、攻擊面間接洩漏架構
- **Subscriber list growth 變廣告管理**：上萬 subscriber 後接近 marketing list、需 GDPR / CAN-SPAM 治理、定期清離職 + bounce
- **Component status 跟實際不符**：自動 sync 規則錯 / 手動沒更新 / metrics 來源延遲
- **Custom domain 失效**：DNS / SSL cert 過期、Statuspage cert auto-renew 沒 enable
- **SSO trap**：admin SSO 切過去後 IdP 出事、Statuspage admin 進不去、break-glass token 沒留

## 何時改走其他服務

| 需求形狀                  | 改走                                                                       |
| ------------------------- | -------------------------------------------------------------------------- |
| 預算敏感 / 小型團隊       | [Instatus](/backend/08-incident-response/vendors/instatus/) / Better Stack |
| OSS / 自管 / 完全 control | Cachet                                                                     |
| IR 平台內建 status        | [FireHydrant](/backend/08-incident-response/vendors/firehydrant/)          |
| IR workflow + Status 一體 | [incident.io](/backend/08-incident-response/vendors/incident-io/)          |
| 內部 only                 | 內部 dashboard（Grafana / Datadog）                                        |

選 Statuspage 的核心訴求：*enterprise polish + Atlassian 生態整合（Opsgenie / JSM / Confluence）+ subscriber scale（百萬級 email/SMS）+ audience targeting 需求（partner / per-customer page）*。中小團隊 / 預算敏感走 Instatus / Better Stack 更划算；IR workflow + status 想一體化走 incident.io。

## 不在本頁內的主題

- 完整 API reference / Custom CSS / Statuspage Connect
- Atlassian SSO 設定細節（屬 IdP 範疇）
- SLA 計算 / SLO dashboard（屬 observability、不屬對外狀態頁）

## 案例回寫

**Statuspage 廣泛使用**：GitHub / Cloudflare / Atlassian / Slack / Discord / Datadog / Fastly / Heroku / Reddit / Roblox 等大型 SaaS 的 public-facing status communication 多為 Statuspage 託管、是 *對外揭露節奏跟措辭* 的事實標準。

| 案例                                                                | 對應主題                                    |
| ------------------------------------------------------------------- | ------------------------------------------- |
| [GitHub cases](/backend/08-incident-response/cases/github/)         | Statuspage update 與長尾事故時序            |
| [Cloudflare cases](/backend/08-incident-response/cases/cloudflare/) | 控制面事故的公開揭露節奏                    |
| [Atlassian cases](/backend/08-incident-response/cases/atlassian/)   | 自家 Statuspage、14 天長尾事故對外通訊      |
| [Slack cases](/backend/08-incident-response/cases/slack/)           | 通訊平台失效時的 status 訊息分軌            |
| [Discord cases](/backend/08-incident-response/cases/discord/)       | Gateway 事故的 component 拆分               |
| [Datadog cases](/backend/08-incident-response/cases/datadog/)       | 觀測平台失效時的 status 自我宣告            |
| [Fastly cases](/backend/08-incident-response/cases/fastly/)         | 全球邊緣事故的單頁公開時程                  |
| [Heroku cases](/backend/08-incident-response/cases/heroku/)         | 平台型 Routing 事故的 incident 分層         |
| [Reddit cases](/backend/08-incident-response/cases/reddit/)         | Kubernetes 升級事故的對外揭露策略           |
| [Roblox cases](/backend/08-incident-response/cases/roblox/)         | 長時間核心基礎設施事故的 incident lifecycle |

## 下一步路由

- 上游：[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 平行：[Instatus](/backend/08-incident-response/vendors/instatus/)、[Opsgenie](/backend/08-incident-response/vendors/opsgenie/)、[incident.io](/backend/08-incident-response/vendors/incident-io/)
- 下游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
