---
title: "Google Security Operations"
date: 2026-05-18
description: "Google 雲原生 SIEM + SOAR + Mandiant threat intel 三合一（前 Chronicle）、UDM + YARA-L、fixed-price by data tier、PB-scale 友善"
weight: 4
tags: ["backend", "security", "vendor", "google-security-operations", "chronicle", "siem", "soar"]
---

Google Security Operations 是 Google 雲端的 SOC 整合平台、2023 年起把前 *Chronicle SIEM* + 2022 收購的 *Siemplify SOAR* + 2022 收購的 *Mandiant threat intel* 三條產品線整合成單一品牌。它跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) 的差異不在 *偵測能力本身*、而在 *資料規模假設 + 計費哲學 + threat intel 內建程度* — Google 的設計假設是 *PB/day ingestion + Google 級基礎設施 + 固定費率 by data tier*、跟 Splunk per-GB 累進的計費哲學完全相反。

## 服務定位

Google Security Operations 的核心定位是 *為超大規模 SOC 設計的雲原生 SIEM + SOAR + threat intel 一體機*、底層走 Google 自家 search infrastructure、上層由四個 first-class concept 撐起來：*UDM*（Unified Data Model、Google 自定 schema、所有 source 強制 normalize）、*YARA-L*（Google 自家 detection rule 語言）、*Curated Detection*（Google 維護的 detection rule 訂閱、客戶不需自己拉）、*Mandiant Applied Threat Intel*（事件期間自動 enrich + IoC push）。

跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) 比、Google 走 *fixed-price by data tier + 強制 schema normalization* — Splunk per-GB ingestion 計費在 PB-scale 會痛、Google 在 multi-PB 通常便宜 3-5 倍、但客戶要接受 UDM 強制 schema 跟 YARA-L 新語法。跟 [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) 比、Google 是 SaaS-only + 大規模優化、Elastic 可自管 + OSS-friendly。跟 [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) 比、Google 是 *純 SOC 專用工具*、Datadog 是 *observability 平面上的 security view*；Datadog 適合中等規模 + observability 已用 Datadog、Google 適合大規模 SOC + 不需要 observability 同 plane。

關鍵張力：*fixed-price tier* 在小規模反而不划算、PB-scale 才回本。組織要看清楚自己的 ingestion 量級 — TB/day 以下走 Datadog / Elastic 通常更便宜、TB-PB/day 之間是模糊地帶、PB/day 以上 Google 是少數能撐又便宜的選擇。Mandiant threat intel 跟 Gemini for Security 是 Google-only 的加值、但這兩個是 *enhancement*、不是選 Google 的主理由。

## 本章目標

讀完本頁、讀者能判斷：

1. Google Security Ops 在 SOC stack 承擔哪一段（log aggregation + SIEM + SOAR + threat intel 一體）、跟 [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) / [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) 怎麼整合
2. UDM forced normalization 跟 YARA-L 對 detection 設計的影響（schema-first 而非 query-first）
3. Curated Detection + Mandiant Applied Threat Intel 在偵測 lifecycle 的位置（不是自己拉、是訂閱）
4. 何時選 Google Security Ops、何時走 Splunk / Elastic / Datadog 的取捨

## 最短判讀路徑

判斷 Google Security Ops deployment 是否健康、最少看四件事：

- **Ingestion 邊界**：哪些 source 進來（Forwarder / GCS bucket / Pub/Sub feed / Cloud-native API feed）、UDM normalization 是否覆蓋全部 source、自家 app log 的 parser 是否寫好
- **Detection 治理**：誰能改 YARA-L rule、Curated Detection 開了哪些、自家 rule 是否走版控（Git → API push）、staging tenant 是否在 production 之前 sanity-check
- **Threat intel 流向**：Mandiant Applied Threat Intel 是否啟用、Curated Detection 是否跟新 IoC 自動同步、IoC enrichment 是否回 alert 上下文
- **Response 流向**：Siemplify SOAR 是否接 alert、playbook 是否進版控、跟 [8 incident response](/backend/08-incident-response/) 的 routing 是否定義

四件事任一缺失、就是 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 的待補項目。

## 日常操作與決策形狀

**Ingestion 路徑**：log 進 Google Security Ops 有三種主路徑 — *Chronicle Forwarder*（agent-based、on-prem / VM、syslog / file tail）、*Cloud Storage feed*（log 先進 GCS bucket、Google 拉）、*Pub/Sub feed*（serverless / GCP 原生 push）、再加 *Direct API feed*（cloud SaaS 像 Okta / Azure AD / AWS CloudTrail 透過原廠 connector）。SaaS-heavy 環境通常以 Direct API feed 為主、on-prem 才需要 Forwarder。

**UDM (Unified Data Model)**：UDM 是 Google 自定的統一 event schema、所有 source（CloudTrail / Azure AD / Okta / endpoint / DNS）在 ingestion 時 *強制 normalize* 到 UDM 欄位（`principal.user`、`target.resource`、`security_result.action` 等）。跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) CIM 同概念、但 Splunk CIM 是 *選擇性 mapping*、Google UDM 是 *forced normalization* — 不寫 parser 就不能 ingest custom source。設計取捨：schema-first 讓跨 source query 一致、但客製 source 的 onboarding 變重。

**YARA-L detection rule**：Google 自家 detection rule 語言、跟 SPL / EQL 同類但結構更明示 — `events { }` 段定義 source pattern、`match { }` 段定義 join / time window、`condition { }` 段定義 threshold、`outcome { }` 段定義 risk score。比 SPL 的 pipe 風格更接近 *關聯式宣告*、特別適合表達 *time-bounded sequence + cross-source join*。Uber MFA 那種「5min 內 50 個 MFA fail + 新裝置 + 異常地理」用 YARA-L 直接寫成 sequence pattern 比 SPL 清楚。

**Curated Detection**：Google 維護的 detection rule 訂閱集合、跟 Splunk Security Content 同類但 Google 是 *built-in subscription*、客戶不需要自己拉 / merge — Google 自動跟 Mandiant threat intel 同步、新 IoC 發布後對應 rule 自動 enable。組織通常 *先全部啟用 baseline、再選擇性 disable noisy 規則 + 補自家 custom YARA-L*。

**Applied Threat Intel (Mandiant)**：事件發生時 Google 自動把 alert 裡的 IoC（IP / domain / hash）跟 Mandiant feed 對照、若命中已知 APT 活動就升級 risk score + 附上 Mandiant 報告。跟其他 SIEM 走第三方 threat intel feed 需要自己 maintain enrichment pipeline 不同、Google 走 *vertical integration* — 收購 Mandiant 後直接內建。

**Siemplify SOAR**：2022 收購 Siemplify 後整合進 Google Security Ops、playbook 處理 alert triage + 自動 response — 例如 leaked credential 自動 rotate（拉 [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) API）、suspect user 自動 disable（拉 [Okta](/backend/07-security-data-protection/vendors/okta/) / Google Workspace API）、suspect IP 自動加 firewall block（拉 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) custom rule）。playbook 進版控、走 approval gate for high-impact action、不能黑箱 fire-and-forget。

**Entity Graph**：Google Security Ops 把 user / asset / IP / domain / hash 等實體做 graph、做 *correlation + lateral movement detection*。Snowflake 2024 那種「同一 credential / IP 跨多個 Snowflake account」的橫向擴散用 Entity Graph 直接視覺化關聯。

**Google Cloud 整合**：跟 [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) / Workload Identity Federation 整合度高 — GCP audit log 直接內建 connector、IAM policy change 直接 surface 成 alert 候選、跨 GCP project 的 federation 走 [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) 認證。非 GCP 環境（AWS / Azure / on-prem）一樣支援、但設定路徑比 Splunk add-on 略陡。

## 核心取捨表

| 取捨維度          | Google Security Operations                    | Splunk                                | Elastic Security                      | Datadog Security                          |
| ----------------- | --------------------------------------------- | ------------------------------------- | ------------------------------------- | ----------------------------------------- |
| 計費模型          | Fixed price by data tier（PB-scale 划算）     | Ingestion-based（GB/day、累進）       | Resource-based（node / cluster size） | Per-host + per-event（events/month）      |
| Schema 處理       | UDM forced normalization                      | CIM optional mapping                  | ECS optional mapping                  | Tag-based、彈性高                         |
| Detection 語言    | YARA-L（結構化 events / match / condition）   | SPL（pipe-based、表達力強）           | KQL / EQL                             | Datadog query                             |
| Detection content | Curated Detection 內建訂閱                    | Splunk Security Content（OSS、自拉）  | Elastic Prebuilt + Sigma              | Datadog Security Rules                    |
| Threat intel      | Mandiant Applied Threat Intel 內建            | 需第三方 feed + 自家 pipeline         | 需第三方 feed                         | Datadog 內建 + 第三方                     |
| SOAR / Response   | Siemplify SOAR 內建                           | Splunk SOAR（前 Phantom、業界先驅）   | Cases + Elastic Defend                | Workflow Automation（基本）               |
| LLM-assisted      | Gemini for Security 內建（2024+）             | Splunk AI Assistant                   | Elastic AI Assistant                  | Bits AI                                   |
| 部署模型          | SaaS only（Google Cloud）                     | Self-hosted / SaaS                    | Self-hosted / SaaS / Serverless       | SaaS only                                 |
| 適合場景          | PB-scale SOC、Google Cloud heavy、要 Mandiant | Enterprise + 跨 on-prem、預算允許     | OSS-friendly、Elastic stack 已用      | Cloud-native + observability 已用 Datadog |
| 退場成本          | 中 — YARA-L 跟 UDM 是 Google-specific         | 高 — SPL / detection / dashboard 量多 | 中 — Sigma / Lucene 較可移植          | 中                                        |

選 Google Security Ops 的核心訴求：*PB-scale ingestion + fixed-price 計費可預期 + Mandiant threat intel 內建 + Google Cloud 整合度*。中等規模 / on-prem 為主 / 預算敏感 / 需要 observability 同 plane 的場景都更適合走 Splunk / Elastic / Datadog。

## 進階主題

**Risk Score multi-signal aggregation**：Google Security Ops 給每個 entity（user / asset）累積 risk score、跨多 rule 加總、超 threshold 才升級 alert。設計上跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) RBA 同類、但 Google 把 risk decay 跟 attribution 走 Entity Graph、跨 entity 關係的 risk 傳遞比較細。配對 [Uber 2022 MFA Fatigue](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/) 的 lesson：MFA fail 累積 + 新裝置 login + 異常地理三個 signal 加總、單獨任一個都不該 alert。

**Cross-tenant federated search**：MSSP / 大型集團多 BU 可在 Google Security Ops 跨多個 tenant 做 federated search、單一 console 看跨組織 detection。權限走 [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) role assignment、跨 tenant admin 是高權限角色、走 break-glass + audit。

**Applied Threat Intel + Curated Detection 同步**：Mandiant 揭露新 APT 活動後、Curated Detection 對應 rule 自動 enable + Applied Threat Intel IoC 自動 push、客戶 SOC 不需要手動 onboard。SolarWinds 2020 揭露當下、Mandiant client 是少數能即時 enable 對應 detection 的 SOC。

**Siemplify playbook 工程化**：playbook 走 *graph-based workflow*（不是 linear pipeline）、可以 branching / approval gate / human-in-the-loop。Production rule 走 *containment-first*（disable session、不 delete account）+ approval gate for irreversible action。

**Gemini for Security (2024+)**：LLM-assisted investigation — natural language 問「過去 24hr 哪些 user 有異常 GCP API 行為」直接生成 UDM query、alert 自動 summarize + 提供 next step 建議。不取代 SOC analyst、但縮短 triage time。

## 排錯與失敗快速判讀

- **Custom source ingest 失敗**：UDM parser 沒寫 / 寫錯、source 進不來或欄位 NULL — 補 parser、staging tenant 跑 sanity check、看 UDM event count by source 確認 normalization 通過
- **Detection 沒觸發 / 漏報**：YARA-L 的 `match { }` 段 time window 寫太短、或 `condition { }` threshold 寫太高 — staging tenant 用歷史資料 backtest、tune window / threshold 後 promote
- **Alert volume 過多**：Curated Detection 全開沒 tune、env-specific noise 沒 disable — 跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) 一樣走 staging 觀察 false positive curve、tune 或 disable 個別規則
- **Mandiant threat intel 沒命中**：licensing tier 沒包 Mandiant Advantage、或 enrichment pipeline 沒啟用 — 檢查 tier、確認 Applied Threat Intel 開
- **Siemplify playbook 黑箱 fire-and-forget**：自動 disable 結果誤殺合法 user — playbook 走 approval gate、預設 containment 不 deletion、定期 dry-run
- **Cross-tenant admin 太多**：日常運維用 cross-tenant admin、blast radius 太大 — 收 admin、改 tenant-scoped role + 特定 capability、跨 tenant 走 break-glass
- **Cost 比預期高**：data tier 選錯（買了 Enterprise Plus 卻只用 Enterprise feature）、retention 設太長 — 看實際 ingestion + retention 用量、tier 跟 retention 一起 review

## 何時改走其他服務

| 需求形狀                                  | 改走                                                                                                                                                          |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Enterprise + 跨 on-prem + detection 成熟  | [Splunk](/backend/07-security-data-protection/vendors/splunk/)                                                                                                |
| OSS-friendly / 自管 / 預算敏感            | [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)                                                                            |
| Cloud-native + observability 已用 Datadog | [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)                                                                            |
| DLP / sensitive data discovery            | [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) |
| Endpoint detection 為主                   | CrowdStrike Falcon / Microsoft Defender for Endpoint                                                                                                          |
| Incident routing                          | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                                                                              |

## 不在本頁內的主題

- YARA-L 完整語法 reference、UDM 全欄位 schema
- Chronicle / Siemplify / Mandiant 三條產品線整合前的歷史細節
- Mandiant Advantage 平台（threat intel 訂閱、跟 SIEM 整合但獨立產品）
- VirusTotal（Google 旗下、跟 Mandiant 互補但獨立服務）
- Gemini for Security 的 prompt engineering 細節
- Google Workspace security center（屬 Google Workspace、不在 Security Ops 範圍）

## 案例回寫

Google Security Ops 在 07 案例庫沒有直接 vendor-level 事件、但所有 detection-related case 都是 SIEM 偵測覆蓋率的對照：

| 案例                                                                                                                                                       | 跟 Google Security Ops 的關係（對照啟示）                                                                                                                                                            |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Microsoft Storm-0558 Signing Key Chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | UDM 強制 normalize 跨 Azure AD / GCP / Okta token validation 欄位、YARA-L 跨 source join 直接表達跨租戶 token forging pattern、Entity Graph 視覺化                                                   |
| [Uber 2022 MFA Fatigue](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/)                                        | YARA-L sequence pattern 直接表達「MFA fail count + 新裝置 login」、Risk Score 累積到 threshold 觸發 Siemplify playbook 自動 disable session                                                          |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                                     | Mandiant 揭露 IoC 後 Applied Threat Intel 自動 push、Curated Detection 對應規則自動 enable、客戶不需要手動 onboard rule                                                                              |
| [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)                  | YARA-L 表達「query 體積 / 跨 schema scan / 來源 IP baseline」三軸 correlation rule；Entity Graph 聚合 credential / IP / data warehouse account 視覺化異常擴散（公開 UNC5537 跨客戶模式屬案例外延伸） |
| [Detection Engineering Lifecycle (section)](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)                               | Curated Detection + 自家 YARA-L rule 走 propose → staging → promote lifecycle、Google Security Ops 內建 rule versioning + Git → API push                                                             |
| [Alert Fatigue and Signal Quality (section)](/backend/07-security-data-protection/blue-team/alert-fatigue-and-signal-quality/)                             | Risk Score multi-signal aggregation 是 alert fatigue 的工程化解法、跟 Splunk RBA 同類但 risk 傳遞走 Entity Graph、跨 entity 關係更細                                                                 |

## 下一步路由

- 上游：[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)、[Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)
- 平行：[Splunk](/backend/07-security-data-protection/vendors/splunk/)、[Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)、[Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)
- 下游：[Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)（DLP signal 進 Google Security Ops）
- 跨類：[Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)（GCP IAM log + Workload Identity Federation）、[Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/)（SOAR playbook 拉 API）、[Okta](/backend/07-security-data-protection/vendors/okta/)（IdP log source）、[Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)（WAF log + auto-block）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（alert → IR routing）、[4 observability](/backend/04-observability/)（log pipeline 共用判斷）
- 官方：[Google Security Operations Documentation](https://cloud.google.com/security/products/security-operations)
