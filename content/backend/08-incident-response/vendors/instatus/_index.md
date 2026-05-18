---
title: "Instatus"
date: 2026-05-01
description: "輕量 status page SaaS、現代 UI、價格敏感替代"
weight: 8
tags: ["backend", "incident-response", "vendor"]
---

Instatus 是輕量 status page SaaS、承擔三個責任：簡潔現代 UI 的 status page、component + incident management、跟 IR 工具整合（incident.io / Rootly / FireHydrant）。設計取捨偏向「價格親民 + UI 現代 + 中小團隊適用」、是 Atlassian Statuspage 的 budget-friendly 替代。

## 服務定位

Instatus 主打 *fast + cheap + custom domain*、產品形狀直接對標 [Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/) 的核心功能（component / incident / subscriber / custom domain），但價格約 1/3-1/5、free tier 就包含 custom domain SSL。typical 客戶是中小 SaaS、indie hacker / 個人 project、不需要 enterprise SLA 但要對外呈現專業感的團隊；不適合需要 audit log、SAML SSO、複雜 access role、SLA 報表的大企業 — 那是 Statuspage / [FireHydrant](/backend/08-incident-response/vendors/firehydrant/) status 模組的場域。

Instatus 的取捨設計：UI 走 *modern + minimal*、頁面 load 快（自稱 ~50ms）、subscriber notification provider 多元（Email / SMS / Slack / Discord / Teams / Telegram / RSS / Webhook），用 *generous free tier* 拉初期用戶、進階功能（更多 component、更多 subscriber、white-label、SLA report）走分層 pricing。

關鍵張力：*cheap + custom domain from free tier* ↔ *enterprise governance（SAML / audit / role）*。Instatus 故意把 enterprise governance 砍掉以壓 pricing、所以團隊規模成長到需要區分多角色 / 留 audit trail 時、會撞到產品天花板、要評估遷移。提早估算 *什麼時候撞到天花板* 比事故當下才發現省事很多。

## 本章目標

1. 建 Instatus + 設 component
2. 寫 incident template + update
3. 配置 subscriber notification
4. API 從 IR 平台 push
5. 評估 Instatus vs Statuspage / Cachet

## 最短判讀路徑

判斷 Instatus 是否健康承載對外狀態揭露、最少看四件事：

- **誰能 publish update**：team member 角色設計（admin / member / read-only）、incident update 是否走 PR / approval、誤發 update 的回收路徑（edit / delete + email correction）
- **Component 數量 vs pricing tier**：current tier 的 component limit、現有 / 規劃中的 component 數、跨 tier 切換的成本影響（升 tier 還是合併 component）
- **Custom domain SSL**：`status.example.com` 的 CNAME 是否生效、SSL cert 自動 renew 是否健康（Instatus 用 Let's Encrypt 自動簽發、需在 DNS 加 CAA record 授權）、未來 domain 變更的遷移流程
- **Subscriber notification 健康度**：subscriber 數量是否逼近 tier 限制、Email / SMS provider quota / bounce rate、Slack / Discord webhook 是否還有效

四件事任一缺失、就是事故揭露通道有風險、應該優先補完。

## 日常操作與決策形狀

### Component / incident + Subscriber

Component 是對外揭露單位、status（operational / degraded / partial outage / major outage / maintenance）的抽象顆粒度影響事故揭露的 *精準度* — 拆太細用戶看不懂、太粗反而失真。實務上跟內部 service map 對齊但 *外部可理解語言*、例如「Web App」「API」「Login」「Webhooks」、而不是內部 microservice 名稱。

子議題：

- Component status（跟 Statuspage 相似、操作 surface 簡潔）
- Incident template + maintenance window（pre-defined template 讓事故 update 走標準格式、避免臨場寫錯）
- Email / SMS / Slack / RSS / Discord / Teams / Telegram / Webhook subscriber、各 channel 的 quota / 失敗模式不同

### API + IR 整合

REST API 用 token 認證、可程式化 create incident / update / resolve / 改 component status。典型整合：incident.io / Rootly / [FireHydrant](/backend/08-incident-response/vendors/firehydrant/) 觸發事故後同步推 Instatus、避免 SOC / on-call 還要手動雙寫。webhook 也支援反向通知、Instatus 上的 incident 變更通知到 IR 平台。

token 是高權限資源（任何持有 token 的 caller 可對外發布 incident）、應該存在 secrets manager、不放程式碼 / 環境變數明文、定期 rotate；CI / IR 平台用獨立 token、出事可單獨 revoke 不影響其他整合。

## 核心取捨表

| 取捨維度      | Instatus                                                         | Atlassian Statuspage                 | Better Stack Status          | Cachet (OSS)              |
| ------------- | ---------------------------------------------------------------- | ------------------------------------ | ---------------------------- | ------------------------- |
| 計費模型      | 分層 SaaS、free tier 含 custom domain                            | 分層 SaaS、custom domain 需付費 tier | 分層 SaaS、跟 monitoring 綁  | OSS 自管、零 license 成本 |
| UI / 速度     | 現代 + 快（~50ms load）                                          | 成熟但偏重                           | 現代、跟 monitoring 整合     | 基本、視自管 stack        |
| Custom domain | free tier 即支援、auto SSL                                       | 付費 tier、auto SSL                  | 付費 tier                    | 自架 + 自管 cert          |
| Subscriber    | Email / SMS / Slack / Discord / Teams / Telegram / RSS / Webhook | 同類但部分需高 tier                  | Email / Slack 為主           | 自實作                    |
| 適合場景      | 中小 SaaS / indie hacker / 個人 project                          | Enterprise + 跨團隊治理              | 已用 Better Stack monitoring | 嚴格資料自管、零外部 SaaS |
| 退場成本      | 低 — 標準 component / incident 結構                              | 中                                   | 中                           | 高 — 自管 ops             |

選 Instatus 的核心訴求：*cheap + fast UI + custom domain 從 free tier 就有*、且不需要 enterprise SLA / SAML / audit 報表。組織成長到要 SAML SSO / multi-team approval / SLA report 時、再評估遷移到 Statuspage 或 IR 平台內建 status。

遷移成本：標準 component / incident 結構讓 Instatus → Statuspage 的搬遷相對單純（資料模型一致、subscriber 列表可匯出）、但 *subscriber 重新確認 opt-in* 通常是最大痛點 — 切換 domain / provider 時、許多 email subscriber 不會自動轉移、要走再次訂閱流程。

## 進階主題（按需閱讀）

### Custom CSS + branding + Multi-language

`status.example.com` 走 CNAME 指到 Instatus 配發的 host、SSL 由 Instatus 透過 Let's Encrypt 自動簽發 + renew、不用自己管 cert。custom CSS / logo 在中高 tier 開放、可改色票 / 字型 / layout、適合需要跟主站視覺一致的 SaaS；不要為了美觀過度客製、status page 第一順位是 *清楚揭露事故*、視覺只是輔助。

multi-language 支援同一 incident 用多語 update、適合對外服務跨地區用戶。注意 *誰負責翻譯* — 事故當下沒人有空一條條翻、實務上 incident update 寫英文 + 主要語言、其餘語言用 fallback 或事後補。

### IR 平台 auto-create incident

Instatus 提供 REST API + webhook、典型整合是 IR 平台偵測事故後 *自動 create + update* status page incident、收尾時 *自動 resolve*。常見 pattern：[PagerDuty](/backend/08-incident-response/vendors/pagerduty/) / [Opsgenie](/backend/08-incident-response/vendors/opsgenie/) 觸發 high-severity alert → webhook → Instatus API create incident → resolve 時同步收尾。

要點是 *誰是 SSoT*：incident timeline 由 IR 平台維護、Instatus 是對外揭露 view、不能讓 status page 變第二份 timeline 否則兩邊會漂移。實務上對外揭露的 update 是 IR timeline 的 *過濾子集*（去掉內部 root cause / 人名 / 攻擊細節）、不是原文同步。

### Metrics 公開

子議題：uptime / response time、從 monitor source（如外部 uptime monitor、或自家 metrics）拉資料、決定哪些 metric 對外揭露。揭露太細（例：每個 endpoint p99）會讓潛在攻擊者 reverse-engineer attack surface 跟容量上限；只揭露用戶感受得到的 SLI（前台 availability / API success rate）通常足夠、敏感內部指標留在內部 dashboard。

## 排錯快速判讀

- **Subscriber 沒收到**：跟 Statuspage 類似、provider quota / bounce / spam filter；SMS 在某些地區需要區號白名單；事故當下若大量 subscriber 同時收到 alert、Email provider 可能短時間 throttle、要留 buffer
- **Custom domain 失效**：DNS CNAME 設定錯 / Let's Encrypt 簽發失敗（CAA record 衝突、需在 DNS 加 `letsencrypt.org` 授權）/ SSL renew 卡住 — 事故發生時才發現 cert 過期是最常見的二次事故
- **API 失敗**：rate limit / token 失效 / webhook signature 驗證錯誤；高 severity 事故時 IR 平台可能短時間發大量 update、要確認 rate limit 不會把 update 卡住
- **Pricing tier 切換成本**：升 tier 取得更多 component / subscriber、但降 tier 可能要先刪 component 或 subscriber 才生效、規劃要先估好成長曲線
- **Subscriber list 上限**：tier 有 subscriber 上限、逼近時要嘛升 tier、要嘛清理 inactive subscriber（長期 bounce / unsubscribe）；不要等到滿了才處理、新 subscriber 註冊失敗會直接傷品牌信任

## 何時改走其他服務

| 需求形狀                          | 改走                                                                                                                        |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Enterprise SLA / SAML SSO / audit | [Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/)                                         |
| OSS 自管 / 嚴格資料留在自家環境   | Cachet                                                                                                                      |
| IR 平台內建 status                | [FireHydrant](/backend/08-incident-response/vendors/firehydrant/)                                                           |
| Alert / on-call SSoT              | [PagerDuty](/backend/08-incident-response/vendors/pagerduty/) / [Opsgenie](/backend/08-incident-response/vendors/opsgenie/) |

## 不在本頁內的主題

- 完整 API reference / Pricing 細節 / Custom CSS 範本
- SLA report 設計（Instatus 提供基本 uptime 計算、複雜 SLA 報表走 Statuspage 或 IR 平台）
- Status page 對外揭露的法務 / 合約義務（合約 SLA、credit 計算）— 屬法務 / 商務、不在本頁
- IR timeline 設計本身（誰寫、誰簽 — 屬 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/) 的範圍）

## 案例回寫

**Instatus 主打輕量、低成本公開狀態頁**：本案例庫的案例多為大型平台、以 Atlassian Statuspage 揭露事故；Instatus 缺乏直接 vendor-level case、可參照的閱讀脈絡是「事故對外揭露的最小可行樣式」、特別適合中小 SaaS 跟 indie 開發者拿來對照自家 status page 的最低門檻。

| 案例                                                          | 對應主題                              | 對 Instatus 用戶的啟示                                                                                      |
| ------------------------------------------------------------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| [Heroku cases](/backend/08-incident-response/cases/heroku/)   | 平台型服務的 component 拆分與訂閱範例 | component 拆分顆粒度可借鏡（Web / API / Build / Dyno）、中小 SaaS 不需要拆到 region 等級、但要分前後台      |
| [Discord cases](/backend/08-incident-response/cases/discord/) | 事件導向產品的最小事故時序揭露對照    | incident update 節奏 — 第一則確認、後續更新、resolve 收尾、indie 級服務也至少跑這三段、不能 silent recovery |

待補 candidate：從 Statuspage 遷移至 Instatus 的中小型 SaaS cost-saving story、indie hacker 個人 project 從零搭 status page 的最小配置（含 custom domain + 一個 component + 一個 incident template）。

## 下一步路由

- 上游：[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)（決定哪些 timeline event 該對外揭露）
- 平行：[Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/)、[FireHydrant](/backend/08-incident-response/vendors/firehydrant/)、[PagerDuty](/backend/08-incident-response/vendors/pagerduty/)、[Opsgenie](/backend/08-incident-response/vendors/opsgenie/)
- 下游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)（事故結束後對外揭露的 timeline / post-mortem 整理）
- 跨類：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（一次看完 IR / status / on-call vendor map）
