---
title: "Atlassian Statuspage → Instatus：80-95% cost reduction、但 compatibility audit 不能跳"
date: 2026-05-19
description: "Atlassian Statuspage → Instatus 是 Type B drop-in migration、6 維 audit 全 Low；典型情境是 $1500/mo → $20-50/mo（80-95% 成本削減）。本文走 compatibility audit prefix（subscriber channel 完整度 / SAML SSO / audit log / metrics integration / SLA report / API parity）、4 階段 cutover（DNS TTL + parallel run）、5 個 production 踩雷（SAML 退、metrics 來源整合斷、subscriber import format / SLA report 缺、custom CSS 不完全相容）、何時不要切（enterprise compliance / 強 Atlassian 整合）"
tags: ["backend", "incident-response", "vendor", "migration", "type-b", "drop-in"]
---

| 項目                  | Atlassian Statuspage（Business）                   | Instatus（Pro）                                                  | 差距                    |
| --------------------- | -------------------------------------------------- | ---------------------------------------------------------------- | ----------------------- |
| 月費                  | $1500（mid-tier）                                  | $20-50（Pro）                                                    | -95% ~ -98%             |
| Custom domain + SSL   | 內建                                               | Free tier 起就含                                                 | 持平                    |
| Subscriber 上限       | 5000                                               | 10000+（Pro）                                                    | Instatus 更高           |
| Component 上限        | 不限                                               | 50（Pro）+ unlimited tier                                        | Statuspage 不限         |
| Notification channel  | Email / SMS / Slack / Teams / webhook / RSS / Atom | Email / SMS / Slack / Discord / Teams / Telegram / RSS / Webhook | 持平 + Discord/Telegram |
| Metrics 圖表          | Datadog / Pingdom / New Relic / Library            | Datadog / Pingdom / New Relic / StatusCake / API                 | 持平                    |
| SAML SSO              | 內建（Enterprise tier）                            | 無                                                               | **Statuspage 獨有**     |
| Audit log             | 內建（Enterprise tier）                            | 無                                                               | **Statuspage 獨有**     |
| SLA / uptime report   | 內建                                               | 無原生（要外接）                                                 | **Statuspage 獨有**     |
| Multi-region failover | 內建                                               | 無                                                               | **Statuspage 獨有**     |
| API parity            | 完整 REST                                          | 完整 REST                                                        | 持平                    |
| Page load latency     | ~200-500ms                                         | ~50ms（自稱）                                                    | Instatus 更快           |

成本差距是這條 migration 的 *driver*、但表格右側那 4 個 **粗體 gap** 是 *blocker*。對 *不需要 SAML / audit log / SLA report / multi-region failover* 的中小 SaaS、$1500 → $20-50 / mo 是 95-98% 削減、cutover 工作量 1-4 週、ROI 極高；對 *enterprise 強合規* 的場景、這 4 個 gap 任一不能讓步、migration 直接否決。

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

Instatus *沒有 SAML SSO*。如果 status page admin 用 SAML 登入是 compliance requirement、Instatus 直接 disqualified。Pro tier 有 2FA + email/password、Team plan 才有 SSO（但是 OAuth + Google Workspace、不是企業 SAML）。

- 確認 admin login 不需要 SAML
- 確認 audit / compliance 沒要求 SSO 軌跡

### 3. Audit log

Instatus *沒有 admin action audit log*。誰 publish 哪則 incident、誰改了哪個 component status — Statuspage Enterprise 有完整 log、Instatus 沒有。

- 確認 status page 變更不需要 audit trail（多數 SaaS 公開 status 變更已是公開行為、不需要額外 internal audit、但金融 / 醫療場景要 double check）

### 4. SLA / uptime report 自動產出

Statuspage 內建 SLA report（per component uptime 月報、PDF / email 自動推給客戶）。Instatus *沒原生 SLA report*、要外接（從 Instatus API 拉 historic data、自己用 BI 工具產 report）。

- 如果 contract 寫了「每月 SLA report 自動推送客戶」、Instatus 要外接補這條
- 評估外接成本（一條 cron + 一個 BI dashboard、3-5 天工程）vs Statuspage 內建

### 5. Multi-region failover

Statuspage Enterprise 內建 multi-region failover、自己的 status page 在 region 故障時自動 failover。Instatus 是 *single-region SaaS*、自家 status page 有 outage 時 status page 本身也 down。

- 多數場景能接受 status page provider 跟自己 service 不同 region 已經足夠
- 強合規 + 「status page must never be down」場景要拒絕 Instatus

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

完成標準：DNS 100% 流量在 Instatus、$1500/mo bill 取消、SRE / SaaS provisioning team 不再 maintain Statuspage account。

## 5 個 production 踩雷

### 1. SAML SSO 用戶突然不能登入 admin

audit 漏掉 *當前 admin 用 SAML 登入* 這個事實、cutover 後 admin 無法登入 Instatus（沒 SAML）、必須改用 email/password + 2FA。修法是 cutover 前 reset admin 為 email/password、確認 2FA 已啟用、訓練 admin 流程改變。對 SOC 2 audit 期間 *admin login method 變更要記錄*的 org 來說是不可預期的 audit finding、要在 Stage 1 就溝通。

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
| 月費                | $1500               | $20-50            |
| Subscriber 上限     | 5000                | 10000+            |
| Component           | 不限                | 50                |
| 工程成本（cutover） | -                   | 1-4 週            |
| 外接 SLA report     | 不需要              | 3-5 天 / 持續維運 |
| 年化 saving         | -                   | ~$17K-18K         |

對 enterprise（30000 subscriber、50+ component、強合規）：

| 項目                  | Statuspage Enterprise | Instatus（不適合） |
| --------------------- | --------------------- | ------------------ |
| 月費                  | $5000+                | -                  |
| SAML / Audit log      | 必要                  | 無                 |
| Multi-region failover | 必要                  | 無                 |
| 結論                  | 不要遷                | -                  |

## 何時不要切

- **SAML SSO + audit log 是 compliance requirement**：金融 / 醫療 / 政府場景、Statuspage Enterprise 留
- **SLA report 是 customer contract 強制**：如果 contract 寫明 SLA report deliverable、外接成本 + 風險高、Statuspage 留
- **Multi-region failover 必要**：status page 在 region outage 時要可訪、Statuspage Enterprise 留
- **Atlassian 整合（Opsgenie / JSM / Confluence）是核心 workflow**：原生整合斷會多很多 webhook 維護、Statuspage 留
- **subscriber > 10K + 強客戶 SLA**：規模本身讓 Instatus 風險增大、Statuspage Enterprise 比較穩

## 下一步路由

- 平行 batch：[PagerDuty → incident.io](/backend/08-incident-response/vendors/pagerduty/migrate-to-incident-io/)（Type E paradigm shift）/ [PagerDuty → Opsgenie](/backend/08-incident-response/vendors/opsgenie/migrate-from-pagerduty/)（Type A schema translation）
- 同 batch Type B：（待補、本篇是 batch 唯一 Type B）
- vendor 對照：[Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/) / [Instatus](/backend/08-incident-response/vendors/instatus/)
- 方法論：[Migration Playbook Methodology](/posts/migration-playbook-methodology/)（Type B drop-in + compatibility audit prefix 結構說明）
