---
title: "Elastic Security"
date: 2026-05-18
description: "Elastic Stack 上的 SIEM + EDR + Cloud Security 套件、OSS 起源、KQL/EQL/Lucene/ES|QL 多查詢語言、resource-based pricing"
weight: 2
tags: ["backend", "security", "vendor", "elastic-security", "siem", "edr", "detection"]
---

Elastic Security 是 Elastic Stack（Elasticsearch + Kibana + Beats / Agent）上的 SIEM + EDR + Cloud Security 套件、OSS 起源、現屬 Elastic 商業版的 Solution。它跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/) 的差異在 *計費模型 + 查詢語言模型 + ecosystem 開放度*、偵測能力本身相近 — Elastic 走 *resource-based pricing*（按 cluster size 而非 ingestion volume）、且提供 KQL / EQL / Lucene / ES|QL 四種互補的查詢語言。

## 服務定位

Elastic Security 的核心定位是 *Elastic Stack 上的 security solution*、底層是 *Elasticsearch*（資料層）+ *Kibana*（查詢與 UI 層）+ *Fleet / Elastic Agent*（採集層）、頂層產品分三條：*Elastic SIEM*（log aggregation + detection rule + Case + Timeline）、*Elastic Defend*（前 Endgame 收購而來、EDR + endpoint protection、跟 CrowdStrike / SentinelOne 同層）、*Elastic Cloud Security*（CSPM + CWP、雲端資源 misconfig 與 workload 防護）。

跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) 比、Elastic 走 *OSS-friendly + resource-based pricing* — TB-scale ingestion 不直接漲費用（要 scale node 但邊際成本遠低於 Splunk per-GB 累進）、Sigma rule 社群可直接 import 5000+ 規則；但 Splunk Security Content 跟 SOAR / RBA 等 detection content + SOC tooling 成熟度仍高一個量級。跟 [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) 比、Elastic 跨 on-prem + 多雲、可自管也可 Elastic Cloud SaaS；Datadog 是 SaaS-only、適合純 cloud-native。跟 [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/) 比、Elastic 多查詢語言（KQL / EQL / Lucene / ES|QL）、Google 走 YARA-L 單一統一語言、超大規模 ingestion Google 反而划算。

關鍵張力：*多查詢語言模型* 同時是 Elastic 的優勢跟負擔。EQL 寫 attack chain sequence 比 SPL correlation 更直接、KQL 過濾快、ES|QL 寫 aggregation 像 SQL 直覺、Lucene 處理 full-text；但 SOC team 要決定哪個 rule 用哪個語言、不能讓每個 analyst 各寫各的。

## 本章目標

讀完本頁、讀者能判斷：

1. Elastic Security 在 SOC stack 中承擔哪一段（log aggregation / SIEM / EDR / CSPM）、哪些要外接（[Okta](/backend/07-security-data-protection/vendors/okta/) IdP log、[Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) secret rotation）
2. KQL / EQL / Lucene / ES|QL 四種查詢語言的職責分工（誰用在哪種 rule、誰負責教育 SOC）
3. Resource-based pricing 的治理（cluster sizing、hot-warm-cold tier、Searchable Snapshots、Elastic Cloud Serverless）
4. 何時用 Elastic、何時走 Splunk / Datadog / Google Security Ops 的取捨

## 最短判讀路徑

判斷 Elastic Security deployment 是否健康、最少看四件事：

- **誰能改 detection rule**：Elastic Security app 的 rule editor 權限、`detection-rules` repo（Elastic 官方 OSS rule 庫）有沒有 fork 進組織版控、rule change 是否走 PR review + staging space 驗證
- **採集治理**：Fleet 統一管 Elastic Agent policy / 還是散落 Beats（filebeat / metricbeat / auditbeat / winlogbeat）各自設定、log source 是否分 hot / warm / cold tier、Searchable Snapshots 是否開
- **Detection content coverage**：Elastic Prebuilt rules + Sigma 社群規則 import 多少 enabled、是否跟 MITRE ATT&CK 對照、EQL sequence 規則覆蓋多少 attack chain pattern
- **Alert quality / SOC handoff**：alert volume per day、Case 跟 Timeline 是否進入日常 SOC workflow、ML anomaly job 是否在線 + threshold 是否 tuned、跟 [8 incident response](/backend/08-incident-response/) 的 routing 是否定義

四件事任一缺失、就是 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 邊界的待補項目。

## 日常操作與決策形狀

**Ingestion architecture**：log 進 Elastic 三種主路徑 — *Elastic Agent + Fleet*（現代部署的預設、單一 agent 收 system / endpoint / cloud / app log、中央 Fleet server 統一管 policy）、*Beats*（filebeat / metricbeat / auditbeat / winlogbeat 等專用 agent、Fleet 推出前的傳統做法、現在持續支援但建議遷移到 Elastic Agent）、*Logstash*（pipeline-style ETL、用在 enrich / filter / route 複雜場景）。production 通常 Elastic Agent + Fleet 為主、Logstash 補 ETL 缺口。

**KQL / EQL / Lucene / ES|QL 的職責分工**：四種查詢語言各有 first-class 場景。*KQL*（Kibana Query Language）是 Kibana 預設過濾語法、`user.name : "alice" and event.action : "logon-failed"`、簡單直觀、適合 dashboard / Discover 過濾。*EQL*（Event Query Language）做 sequence pattern matching、`sequence by user.name [authentication where event.outcome=="failure"] [authentication where event.outcome=="success" and source.geo.country != "TW"]`、表達 attack chain 比 SPL correlation 更直接。*Lucene* 是底層 full-text query、特殊需要時直接寫。*ES|QL*（Elasticsearch Query Language、2024+）是新版 SQL-like、`FROM logs-* | WHERE event.category == "authentication" | STATS count = COUNT(*) BY user.name`、寫 aggregation 直覺；屬新語言、production 採用 cadence 還在跟進中。

**Detection rule 種類**：Elastic Security 的 rule type 是六種 first-class 概念、不是只有「query rule」一種 — *Query rule*（KQL / Lucene 觸發）、*EQL rule*（sequence pattern）、*Threshold rule*（聚合超過閾值、例如同一 IP 5min 內 login fail > 100）、*ML rule*（綁 Elastic ML anomaly job、anomaly score 超過閾值觸發）、*New term rule*（首次出現的 entity、例如某 user 第一次從某國登入）、*Indicator match rule*（事件 enrich 比對 threat intel feed、IoC hit 觸發）。production rule 經常組合多種 — query rule 做粗篩、EQL rule 抓 sequence、threshold + ML 補 baseline anomaly。

**Sigma rule import**：Sigma 是 OSS 通用 detection rule 格式（YAML、跨 SIEM 可移植）、社群維護 5000+ 規則。Elastic 支援直接 import Sigma rule 轉成 Elastic detection rule、是 Elastic 拉開跟商業 SIEM 距離的 OSS 槓桿。實務做法：先 import Sigma baseline + 全部走 staging space 跑 false positive 觀察、再 enable 到 production；不要直接全 enable、Sigma rule 跨 SIEM 通用所以 environment-specific tuning 必須自己做。

**Case + Timeline**：Case 是 incident 容器、聚合 alert + comment + assignment + status；Timeline 是 SOC analyst 的 investigation workspace、可以 pin event / annotate / link related alert、產出 investigation narrative。兩者組合是 Elastic 的 SOC workflow first-class、不是外掛 — 對應 Splunk ES 的 Notable Event + Incident Review、但 Elastic 走 OSS 化、Case 可 export markdown 進 ticketing。

**Elastic Defend（EDR）**：前 Endgame 收購整合、提供 endpoint detection + prevention（malware block / ransomware protection / behavior detection）、跟 CrowdStrike Falcon / SentinelOne 同層。Elastic Defend 跑在 Elastic Agent 內、policy 從 Fleet 推。實務上多數 SIEM 客戶不會用內建 EDR、而是外接專業 EDR feed 進 Elastic SIEM；但 OSS-friendly + 預算敏感的中型客戶可以直接整合到一個 stack。

**Cross-cluster search**：跨多個 Elastic cluster 統一查詢（`remote_cluster:index-name`）、適合 multi-region / multi-tenant SOC、不需要把所有 log 搬到單一 cluster。對應 Splunk Cloud federated search。實務場景：歐洲 GDPR 資料留在 EU cluster、美國 cluster query 過去做 incident investigation 而不複製資料。

**ML jobs（anomaly detection）**：Elastic ML 內建 unsupervised anomaly detection、pre-built ML job library 覆蓋 SOC 常見場景（user behavior baseline、host login pattern、port scan detection、rare process）。ML rule 綁 ML job、anomaly score 超過閾值觸發 detection rule。對應 Splunk UBA、但 Elastic ML 是 stack 內建、不是 add-on app。

**Resource-based pricing 治理**：Elastic Cloud 按 *cluster size*（node count × node size）計費、不按 ingestion volume — 意義是 ingest 多 log 不直接漲費用、但要 scale node 維持查詢效能。實務治理：*hot tier*（最近 7-30 天、SSD 高效能 node）、*warm tier*（30-90 天、低 IO node）、*cold tier* / *frozen tier*（90 天以上、Searchable Snapshots on S3 / GCS、查詢慢但成本極低）。對應 Splunk SmartStore、但 Elastic frozen tier 把 retention 從幾個月延長到幾年、cost 不線性漲。

## 核心取捨表

| 取捨維度          | Elastic Security                            | Splunk                                        | Datadog Security                          | Google Security Operations                |
| ----------------- | ------------------------------------------- | --------------------------------------------- | ----------------------------------------- | ----------------------------------------- |
| 計費模型          | Resource-based（node / cluster size）       | Ingestion-based（GB/day、累進）               | Per-host + per-event（events/month）      | Fixed price by data tier（PB-scale 划算） |
| 查詢語言          | KQL / EQL / Lucene / ES\|QL 四種互補        | SPL（單一強表達力）                           | Datadog Query（沿用 observability 語法）  | YARA-L（統一、結構清楚）                  |
| Sequence 表達     | EQL `sequence by` 直接表達 attack chain     | SPL transaction / streamstats                 | log + metrics + trace 同 plane            | UDM + YARA-L 多事件 rule                  |
| 部署模型          | Self-hosted / Elastic Cloud / Serverless    | Self-hosted (Enterprise) / SaaS (Cloud)       | SaaS only                                 | SaaS only（Google Cloud）                 |
| Detection content | Elastic Prebuilt rules + Sigma 社群 5000+   | Splunk Security Content（最豐富、社群活躍）   | Datadog Security Rules（中等）            | Google YARA-L + Google threat intel       |
| EDR 整合          | Elastic Defend 內建（前 Endgame）           | 外接 CrowdStrike / Defender                   | Workload Security（容器 focus）           | 外接（透過 forwarder）                    |
| SOAR / Response   | Cases + Endpoint response（Elastic Defend） | Splunk SOAR（前 Phantom、業界先驅）           | Workflow Automation（基本）               | SOAR 內建（前 Siemplify）                 |
| 適合場景          | OSS-friendly、中大型、Elastic stack 已用    | Enterprise + 跨 on-prem、預算允許             | Cloud-native + observability 已用 Datadog | 超大規模 ingestion、Google 雲 + 多雲 SOC  |
| 退場成本          | 中 — Sigma / Lucene / EQL 部分可移植        | 高 — SPL / detection content / dashboard 量多 | 中                                        | 中                                        |

選 Elastic 的核心訴求：*OSS-friendly 文化 + resource-based pricing 友善 + Elastic Stack 已作為 observability 在用*、團隊有能力跨四種查詢語言（或至少把 EQL 跟 KQL 雙語分工清楚）、能接受 detection content 跟 SOAR 成熟度 trade-off。TB-scale ingestion 時 Elastic 比 Splunk 省 60-80% license cost 是最大誘因、但要算進 cluster sizing 跟 SRE 維運的隱形成本。

## 進階主題

**EQL sequence pattern（時序攻擊鏈）**：EQL 的 `sequence by` 是 Elastic 表達 attack chain 的 first-class 武器、比 SPL correlation 直接。例如 MFA fatigue 寫成 `sequence by user.name with maxspan=5m [authentication where event.outcome=="failure"] [authentication where event.outcome=="failure"] [authentication where event.outcome=="success" and source.ip != known_ip]`、序列邏輯直接表達。配對 [Uber 2022 MFA Fatigue](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/) lesson：MFA fail 序列 + 新裝置 success 直接觸發。

**Elastic Defend endpoint response**：除偵測外、Defend 支援 host isolation（隔離受感染 endpoint 但保留 SOC 連線）、process kill、file quarantine 等 response action、直接從 Kibana Security app 觸發。對應 CrowdStrike Real Time Response。production 採用前要設 approval gate、避免 SOC analyst 誤觸動 production server。

**CSPM / CWP（Elastic Cloud Security）**：CSPM（Cloud Security Posture Management）對 AWS / GCP / Azure 帳號做 misconfig 掃描（S3 bucket public、IAM over-permission、security group 0.0.0.0/0）、對照 CIS Benchmark；CWP（Cloud Workload Protection）對 Kubernetes workload 跑 runtime detection。屬較新的功能、跟 Wiz / Lacework 等專業 CNAPP 比覆蓋還在追趕。

**Cross-cluster search 跨環境 federated query**：multi-region SOC 的 first-class 工具 — query 寫 `FROM logs-auth-*, eu-cluster:logs-auth-*`、Elastic 自動路由跨 cluster。實務注意：跨 cluster query 延遲較高、要設 timeout；資料合規（GDPR）必須留意 query 結果是否包含跨境資料、不是搬資料但 query 結果回傳算不算傳輸要法務確認。

**Sigma 規則社群**：Sigma 是 OSS detection rule 通用格式、Elastic 是 Sigma 主力使用者（內建 importer + Elastic 工程師參與 Sigma upstream）。實務做法：fork SigmaHQ repo 進組織版控、CI pipeline 自動轉 Sigma → Elastic detection rule、staging space 跑 false positive curve、promote 到 production；不要每次 manually import。

**Elastic Cloud Serverless（2024+）**：新模型、按 *workload type*（search / observability / security）計費、不再按 cluster size — 減少 sizing 決策、autoscaling 由 Elastic 託管。屬新模型、production 採用 cadence 還在跟進中、適合 greenfield 部署或 PoC、existing cluster 遷移 roadmap 還在演進。

## 排錯與失敗快速判讀

- **Alert volume 爆炸 / SOC 看不完**：Sigma rule 全 enable 沒 tune、或 threshold rule 閾值太低 — staging space 跑 1 週統計 FP、tune threshold、加 exception list 排除已知合法 source、ML rule 補 user-specific baseline
- **EQL sequence rule 跑不動 / timeout**：sequence span 太長（24h）或 by field cardinality 太高、查詢成本爆炸 — 縮短 maxspan、限定 index pattern、加 pre-filter 條件
- **Cluster 查詢慢 / Kibana 卡**：hot tier 塞太多舊資料、沒做 hot-warm-cold tier 分層 — 開 ILM（Index Lifecycle Management）policy 自動 rollover、warm tier 用便宜 node、cold / frozen 走 Searchable Snapshots
- **Fleet agent enrollment 失敗**：Fleet server 跟 Elasticsearch 之間網路 / 憑證 / token 問題 — 檢查 Fleet server health、確認 enrollment token 未過期、agent log 看 specific 錯誤
- **Sigma rule import 後大量 FP**：Sigma rule 是 cross-SIEM 通用、沒有 environment-specific exclusion — 不要全 enable、staging tune 後再 promote、加 exception list（known scanner IP / 內部測試帳號）
- **Resource-based pricing 超預算**：node 過度 scale 或 hot tier 留太多 — 開 hot-warm-cold ILM、把 retention 超過 30 天的 index 推到 frozen tier on S3、Searchable Snapshots 是預設應該開
- **ML job anomaly score 不準**：training data 包含已 compromise 期間、baseline 被汙染 — 確認 training window 在乾淨期、定期重訓、配 detection rule 用 anomaly_score > 75 而非 > 50

## 何時改走其他服務

| 需求形狀                                  | 改走                                                                                                                                                          |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Enterprise + detection content 最豐富     | [Splunk](/backend/07-security-data-protection/vendors/splunk/)                                                                                                |
| Cloud-native + observability 已用 Datadog | [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)                                                                            |
| 超大規模 ingestion + Google 雲            | [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)                                                        |
| DLP / sensitive data discovery            | [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) |
| Endpoint detection 為主、不要全 stack     | CrowdStrike Falcon / Microsoft Defender for Endpoint / SentinelOne                                                                                            |
| CNAPP 為主（雲端 posture + workload）     | Wiz / Lacework / Prisma Cloud（Elastic Cloud Security 較新）                                                                                                  |
| Incident routing                          | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                                                                              |

## 不在本頁內的主題

- KQL / EQL / ES|QL 完整語法 reference、Lucene query DSL 進階用法
- Elasticsearch index sharding / replica / ILM tuning 細節（屬 observability / 資料工程範圍）
- Elastic Observability（APM / logs / metrics）— 屬 observability 不屬 security
- Elastic Cloud Serverless 詳細 sizing 與 pricing 模型（2024+ 新模型、變動中）
- Elastic Stack 自管的維運（cluster upgrade、Kibana plugin 開發）

## 案例回寫

Elastic Security 在 07 案例庫沒有直接 vendor-level 事件、但所有 detection-related case 都是 SIEM 偵測覆蓋率的對照：

| 案例                                                                                                                                                       | 跟 Elastic Security 的關係（對照啟示）                                                                                                                             |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Uber 2022 MFA Fatigue](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/)                                        | Elastic EQL `sequence by user.name [auth fail count > 50 in 5min] [auth success from new device]` 直接表達 MFA fatigue pattern、Sigma 社群有現成規則可 import 起步 |
| [Microsoft Storm-0558 Signing Key Chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | 跨租戶 token 異常驗證需 Elastic Cross-cluster search 跨 Azure AD log + GCP audit log + 自家 app log 同時 query、不需先搬資料                                       |
| [3CX 2023 Desktop App Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/3cx-2023-desktopapp-supply-chain/)                    | Elastic Defend 直接看到 desktop app process spawn + 異常網路 callback、不需外接 EDR feed；EQL `sequence` 抓 process → DNS → C2 行為鏈                              |
| [Detection Engineering Lifecycle (section)](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)                               | Elastic rule 走 `detection-rules` repo（OSS、Elastic 官方維護）+ Sigma fork + staging space + promote 工程化 lifecycle、不是 Kibana UI 直改                        |
| [Alert Fatigue and Signal Quality (section)](/backend/07-security-data-protection/blue-team/alert-fatigue-and-signal-quality/)                             | Elastic 沒有 Splunk RBA 對應、用 ML anomaly rule + threshold rule severity + Case grouping 三層降噪、要設 ML job 重訓 lifecycle                                    |

## 下一步路由

- 上游：[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)、[Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)
- 平行：[Splunk](/backend/07-security-data-protection/vendors/splunk/)、[Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)、[Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)
- 下游：[Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)（DLP signal 進 Elastic SIEM）
- 跨類：[Okta](/backend/07-security-data-protection/vendors/okta/)（IdP log source）、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（secret rotation API）、[Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)（WAF log + Sigma rule 對接）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Case → IR routing）、[4 observability](/backend/04-observability/)（Elastic Stack 共用 log pipeline）
- 官方：[Elastic Security Documentation](https://www.elastic.co/guide/en/security/current/index.html)、[detection-rules repo](https://github.com/elastic/detection-rules)
