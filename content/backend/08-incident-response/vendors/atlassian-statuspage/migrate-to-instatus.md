---
title: "Atlassian Statuspage → Instatus：status page 成本下降、但 compatibility audit 不能跳"
date: 2026-05-19
description: "Atlassian Statuspage → Instatus 是 Type B drop-in migration、6 維 audit 全 Low；典型情境是從 Statuspage Business / Enterprise 降到 Instatus Pro / Business、但 savings 取決於 subscriber、SSO、audit 與 SLA report 需求。本文走 compatibility audit prefix（subscriber channel 完整度 / SAML SSO / audit log / metrics integration / SLA report / API parity）、4 階段 cutover（DNS TTL + parallel run）、5 個 production 踩雷（SSO tier 選錯、metrics 來源整合斷、subscriber import format / SLA report 缺、custom CSS 不完全相容）、何時不要切（enterprise compliance / 強 Atlassian 整合）"
tags: ["backend", "incident-response", "vendor", "migration", "type-b", "drop-in"]
---

| 項目                 | Atlassian Statuspage（Business / Enterprise）      | Instatus（Pro / Business）                                       | 差距判讀                    |
| -------------------- | -------------------------------------------------- | ---------------------------------------------------------------- | --------------------------- |
| 月費                 | Business 約 $399/mo、Enterprise 約 $1,499/mo 起    | Pro 約 $20/mo、Business 約 $300/mo                               | savings 取決於 target tier  |
| Custom domain + SSL  | 內建                                               | Free tier 起就含                                                 | 持平                        |
| Subscriber 上限      | 依 tier 提升                                       | Pro 約 5,000 subscriber、Business 約 25,000 subscriber           | 需對齊現有 subscriber 數    |
| Component 上限       | 依 tier 提升                                       | Pro 有上限、Business 放寬                                        | 大型 page 要逐項確認        |
| Notification channel | Email / SMS / Slack / Teams / webhook / RSS / Atom | Email / SMS / Slack / Discord / Teams / Telegram / RSS / Webhook | Instatus 多 chat channel    |
| Metrics 圖表         | Datadog / Pingdom / New Relic / Library            | Datadog / Pingdom / New Relic / StatusCake / API                 | payload / auth 要重接       |
| SAML SSO             | Enterprise tier                                    | Business tier                                                    | 不是產品缺口、是 tier 差異  |
| Audit / activity log | Enterprise / team governance 能力                  | 需依 plan 確認                                                   | 強合規要逐項驗證            |
| SLA / uptime report  | 內建能力較成熟                                     | 需確認 plan 或外接                                               | contract deliverable 要驗證 |
| API parity           | 完整 REST                                          | REST API                                                         | endpoint / schema 不同      |

成本差距是這條 migration 的 *driver*、但表格右側的 tier 差異是 *blocker candidate*。對 *不需要 Enterprise governance / 強 SLA reporting / 深 Atlassian 整合* 的中小 SaaS、從 Statuspage Business / Enterprise 降到 Instatus Pro / Business 可以有明顯 savings、cutover 工作量通常落在 1-4 週；對 *enterprise 強合規* 的場景、SSO、audit、reporting 與可用性承諾任一不能讓步時、migration 要先停在 compatibility audit。

這篇是 Type B drop-in migration playbook、結構順序是：先跑 *compatibility audit*（確認 gap 都可接受）→ 再進 cutover。Type B 看起來簡單、但跳過 audit 直接切是這 batch 第三常見的事故來源。

## 為什麼是 Type B（全 Low）

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/#6-維-diff-dimension-audit)：

| 維度        | 評  | 說明                                                           |
| ----------- | --- | -------------------------------------------------------------- |
| Schema      | Low | component / incident / subscriber model 接近一致、欄位名稱 1:1 |
| Operational | Low | 都是 public status page + notification、ops 模型相同           |
| Paradigm    | Low | 同 paradigm（public service status disclosure）                |
| Components  | Low | 都是單一 SaaS                                                  |
| App change  | Low | API 端點換、payload 接近一致                                   |
| Topology    | Low | 都是 cloud SaaS                                                |

全 Low → **Type B drop-in + compatibility audit prefix**。

## Compatibility audit prefix

切換前先跑 audit、確認以下 9 項 *對自己的 case 是否可接受*。任一項是 *no*、回頭評估是否真要遷：

### 1. Subscriber channel 完整度

Statuspage 主要 channel：Email、SMS、Slack、Microsoft Teams、Webhook、RSS、Atom。Instatus 多了 Discord 跟 Telegram、少了 Atom（RSS 仍在）。

- 確認現有 subscriber 用的 channel 都在 Instatus 支援列表
- 特別注意 *legacy RSS Atom feed reader* — 有些 monitoring service 用 Atom 訂閱、要改成 RSS 或 webhook

### 2. SAML SSO

SAML SSO 是 *tier decision*、不是單純產品有無。Statuspage 把 SAML 放在較高 tier；Instatus 也在 Business tier 提供 SAML。真正要判斷的是：成本 savings 是否仍成立、以及 IdP / SCIM / role mapping 是否符合 audit 要求。

- 確認 target Instatus plan 是否包含 SAML
- 確認 IdP / group / role mapping 是否能對上現有 audit requirement
- 如果 savings 只在 Pro tier 成立、但 compliance 要 SAML，就不能用 Pro tier 當 ROI 基準

### 3. Audit log

Audit log 是 governance surface。誰 publish 哪則 incident、誰改了哪個 component status、誰匯入 subscriber，這些事件在 Statuspage Enterprise / Instatus Business 類 plan 的支援深度與匯出能力要逐項比對。

- 確認 status page 變更是否需要 internal audit trail
- 確認 target plan 是否能查詢、匯出與保留 admin activity
- 金融 / 醫療場景要把 audit retention 與 evidence export 放進 go/no-go gate

### 4. SLA / uptime report 自動產出

SLA / uptime report 是 customer contract surface。Statuspage 的 enterprise workflow 通常更成熟；Instatus 是否能直接覆蓋，要看 plan、API 與既有客戶報表格式。

- 如果 contract 寫了「每月 SLA report 自動推送客戶」、Instatus 要外接補這條
- 評估外接成本（一條 cron + 一個 BI dashboard、3-5 天工程）vs Statuspage 內建

### 5. 可用性承諾與 provider outage

Status page provider 本身的可用性承諾是 compatibility audit 的一部分。強合規或大型 customer-facing page 要確認 provider SLA、status page provider 自身 outage 時的 fallback、以及是否需要獨立備援頁。

- 多數場景能接受 status page provider 跟自己 service 不同供應商已經足夠
- 強合規 + 「status page must never be down」場景要設獨立 fallback，而不是只比較 UI 功能

### 6. Metrics integration 來源

兩家都接 Datadog / Pingdom / New Relic / StatusCake / Library API。Instatus 多了 StatusCake、少了某些 Statuspage 內建 library。

- 確認當前 metrics 顯示圖表的 source 在 Instatus 支援列表
- 特別注意 *custom metrics from API*（自家 push 上去的）— 兩家都支援、payload 格式不同、要重寫 push script

### 7. Custom CSS / branding 完整度

Statuspage Enterprise 允許 *完整 custom CSS override*、Instatus Pro / Team 允許 *theme customization*（颜色 / logo / font）但 *不允許任意 CSS injection*。

- 如果有大量 custom CSS 跟既有品牌 site 視覺 1:1 對齊、Instatus 可能達不到、要評估視覺退讓
- 大多數 status page 視覺 ≠ 主 product site、退讓常見

### 8. API parity 跟自動化 hook

兩家都有完整 REST API（create incident、update component status、push subscriber）。但 *endpoint URL / auth scheme / payload schema 不同*：

- Statuspage：`https://api.statuspage.io/v1/pages/{page_id}/...`、OAuth bearer token
- Instatus：`https://api.instatus.com/v1/{page_id}/...`、API key header

如果有 *從 IR 平台（incident.io / Rootly / FireHydrant / 自製 webhook）push status update* 的自動化、要重寫對接、估算 2-5 天工程。

### 9. Atlassian 生態整合（Opsgenie / JSM / Confluence）

Statuspage 跟 Opsgenie / JSM / Confluence 同生態、有原生整合（Opsgenie incident → Statuspage incident draft、Confluence post-mortem auto-link）。Instatus 跟 Atlassian 沒原生整合、要走 webhook。

- 如果 Atlassian 整合是核心 workflow、評估走 webhook 工作量
- 如果是 incident.io / Rootly / FireHydrant 主用、Instatus 反而有原生整合（這條變優勢）

## 4 階段 cutover

Audit 全過後、Type B drop-in 不需要 11-phase 結構、4 階段：

### Stage 1：Setup + parallel run（1 週）

- 在 Instatus 開帳號、設 component（先複製 Statuspage 結構 1:1）
- 設 custom domain + SSL（Instatus 預設 free tier 已含）
- 接 subscriber channels（先不切 DNS、純內部測試）
- 用 Instatus API 從 Statuspage export incident history 灌回 Instatus（保留歷史 uptime 連續性）
- Parallel run：當前若有 incident、在 Statuspage 跟 Instatus 兩邊都 push、確認 subscriber 在兩邊都收到、UI 都正常

### Stage 2：DNS 預備（1 天）

- Statuspage custom domain CNAME / ALIAS 預設 TTL 通常 1 小時、提前 48 小時把 TTL 降到 5 分鐘
- 這步是 minimize cutover window 的關鍵、不做的話 cutover 期間有 1 小時 DNS cache 兩邊 page 不同步

### Stage 3：DNS cutover（30 分鐘 - 1 小時）

- 把 status page custom domain 從 Statuspage CNAME 改指 Instatus CNAME
- 5 分鐘 TTL 後新流量都進 Instatus
- 監控 1 小時、確認 subscriber notification 從 Instatus 發出、metrics 圖表 wire 正確、history uptime continuity 沒斷
- 既有 IR 平台 webhook 改指 Instatus API endpoint

### Stage 4：Statuspage 關閉（2-4 週後）

- 不要立即取消 Statuspage 帳號 — 留 2-4 週作 rollback 緩衝
- Subscriber 通知「status page URL 不變、underlying provider 換了」（多數場景不需要、subscriber 不會察覺）
- 確認 incident history / uptime data 在 Instatus 完整、Statuspage rollback 場景 < 0.5% 後、取消 Statuspage subscription

完成標準：DNS 100% 流量在 Instatus、Statuspage subscription 取消、SRE / SaaS provisioning team 不再 maintain Statuspage account。

## 5 個 production 踩雷

### 1. SSO tier 選錯導致 admin login 退化

audit 漏掉 *當前 admin 用 SAML 登入* 這個事實、卻用不含 SAML 的 target tier 計算 savings，cutover 後 admin login 被迫退回 email/password + 2FA。修法是 Stage 1 就用含 SAML 的 target plan 測試 IdP、group mapping 與 break-glass admin。對 SOC 2 audit 期間 *admin login method 變更要記錄*的 org 來說，這是不可預期的 audit finding、要在 Stage 1 就溝通。

### 2. Metrics 圖表來源整合斷

Statuspage 接 Datadog metrics 的 OAuth integration 在 Instatus 要重接、auth flow 重做、Datadog API key 重 provision。常見漏網之魚：

- 跨 region Datadog account（US / EU）integration 重 provision 時 region 沒選對、圖表全空
- Pingdom check ID 在新 integration 重新 register、historic data 斷層
- 自家 push metrics 的 webhook payload schema 不同（Statuspage 是 `{component_id, status, ...}`、Instatus 是 `{componentId, status, ...}` camelCase）

修法是 Stage 1 parallel run 期間就把所有 metrics integration 在 Instatus wire 通、對比兩邊圖表一致再進 Stage 2。

### 3. Subscriber import format 不一致

Statuspage subscriber export CSV 是 `email, phone, slack_webhook_url, ...` 一行多 channel；Instatus import CSV 是 `email\nemail\n...` 純 email list、其他 channel 要分開 import。如果有 5000 subscriber 包含 SMS / Slack mix、import 時要拆開、否則 SMS subscriber 會掉。

修法是寫 import script 把 Statuspage CSV 拆成多個 channel-specific CSV、分批 import Instatus。

### 4. SLA report 月報突然斷

Statuspage 月報自動 push 給客戶、cutover 後 Instatus 沒原生 SLA report、客戶下個月沒收到報表會問。修法是 *cutover 前先建外接 SLA report*：

- 寫 cron job（per month）從 Instatus API 拉 component uptime data
- 用簡單 template（Google Doc / PDF generator）產 report
- 自動 email 推給原 Statuspage SLA report distribution list

如果這條 contract 強制、外接成本約 3-5 天工程、要算進 migration 總成本。

### 5. Custom CSS / branding 視覺退讓

Statuspage Enterprise 有大量 custom CSS、cutover 後 Instatus 視覺對齊不到 1:1。視覺退讓清單通常是：

- font weight 跟 line-height 微差
- mobile breakpoint 不同
- incident timeline 排版 spacing 略不同

修法是 cutover 前先在 Instatus theme customization 內把能調的調好、能接受的退讓在 Stage 1 跟設計 / brand team 確認、不能接受的就回去 audit Step 7 重新評估是否要遷。

## 容量與成本對比

對中小 SaaS（3000 subscriber、10 component、月均 2 incident）：

| 項目                | Statuspage Business | Instatus Pro      |
| ------------------- | ------------------- | ----------------- |
| 月費                | 約 $399             | 約 $20            |
| Subscriber 上限     | 依 plan             | 約 5,000          |
| Component           | 依 plan             | 有上限            |
| 工程成本（cutover） | -                   | 1-4 週            |
| 外接 SLA report     | 不需要或較成熟      | 0-5 天 / 持續維運 |
| 年化 saving         | -                   | 約數千美元等級    |

對 enterprise（30000 subscriber、50+ component、強合規）：

| 項目                | Statuspage Enterprise | Instatus Business / Enterprise |
| ------------------- | --------------------- | ------------------------------ |
| 月費                | 約 $1,499 起或 custom | 低於典型 Enterprise quote      |
| SAML / Audit log    | 必要                  | 需逐項驗證                     |
| SLA / uptime report | 必要                  | 需逐項驗證或外接               |
| 結論                | 未必適合遷            | 先跑 audit、不要只看月費       |

## 何時不要切

- **SAML SSO + audit log 是 compliance requirement**：金融 / 醫療 / 政府場景、Statuspage Enterprise 留
- **SLA report 是 customer contract 強制**：如果 contract 寫明 SLA report deliverable、外接成本 + 風險高、Statuspage 留
- **Provider availability / fallback 必要**：status page provider 自身 outage 時仍要可訪、先設獨立 fallback 或保留 Enterprise 級 provider
- **Atlassian 整合（Opsgenie / JSM / Confluence）是核心 workflow**：原生整合斷會多很多 webhook 維護、Statuspage 留
- **subscriber > 10K + 強客戶 SLA**：規模本身讓 Instatus 風險增大、Statuspage Enterprise 比較穩

## 下一步路由

- 平行 batch：[PagerDuty → incident.io](/backend/08-incident-response/vendors/pagerduty/migrate-to-incident-io/)（Type E paradigm shift）/ [PagerDuty → Opsgenie](/backend/08-incident-response/vendors/opsgenie/migrate-from-pagerduty/)（Type A schema translation）
- 同 batch Type B：（待補、本篇是 batch 唯一 Type B）
- vendor 對照：[Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/) / [Instatus](/backend/08-incident-response/vendors/instatus/)
- 方法論：[Migration Playbook Methodology](/posts/migration-playbook-methodology/)（Type B drop-in + compatibility audit prefix 結構說明）
