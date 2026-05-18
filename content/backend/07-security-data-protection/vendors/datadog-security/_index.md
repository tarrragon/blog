---
title: "Datadog Security"
date: 2026-05-18
description: "Datadog observability platform 上的 security suite：Cloud SIEM + CSPM + CWS + AAP + Sensitive Data Scanner、跟 observability 同 plane"
weight: 3
tags: ["backend", "security", "vendor", "datadog-security", "siem", "cspm", "detection"]
---

Datadog Security 是 Datadog observability platform 上的 security 套件、跟 Datadog logs / metrics / APM / infrastructure 共用同一個 control plane 與 data plane。它的設計起點不是 SIEM、是 *把資安訊號當成 observability 的一個維度*：alert 不只看 log、可以同時 pivot 到 APM trace、infra metrics 與 host context。這個定位決定了它的優勢（cloud-native + 混合 incident 偵測）與限制（SaaS-only + 計費隨 host 量線性漲、不適合 on-prem-heavy 或預算敏感場景）。

## 服務定位

Datadog Security 由四個 product 構成、共用 Datadog Agent 與 backend：*Cloud SIEM*（log-based detection、跟 [Splunk Enterprise Security](/backend/07-security-data-protection/vendors/splunk/) 同類）、*Cloud Security Management (CSM)* — 涵蓋 *CSPM*（cloud config posture）與 *Cloud Workload Security (CWS)*（container / Linux runtime via eBPF）、*App and API Protection (AAP、前 ASM)* — RASP-style 在 app runtime 收 attack signal、*Sensitive Data Scanner* — scan log 中的 PII / credential 並 redact。

跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) 比、Datadog 走 *observability-first + security 是 view*、Splunk 是 *security-first*。Splunk 在 enterprise SOC tooling 深度（SOAR playbook、RBA、CIM data model）與跨 on-prem 部署上更成熟、Datadog SaaS-only 但跟 APM / Infra 同 plane、混合 incident（latency 異常是攻擊還是容量？）的判讀路徑更短。跟 [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) 比、Elastic 可跨 on-prem + OSS、Datadog 只給 SaaS；Elastic 要自己整合 observability 訊號、Datadog 出廠就有。跟 [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/) 比、Google 走 *fixed-price by data、PB-scale 划算*、Datadog 隨 host 線性漲、中等規模友善但破千 host 後 cost 曲線變陡。

關鍵張力：*observability 與 security 同 plane* 是 Datadog 最大賣點、也是 cost 風險來源。host count 跟 events/month 同時是 observability 跟 security 的計費基準、security 加上去後 bill 不會獨立 — 預算要從 *整個 Datadog 帳單* 看、不是 security 單列。

## 本章目標

讀完本頁、讀者能判斷：

1. Datadog Security 在 SOC stack 中承擔哪一段（log SIEM / CSPM / 容器 runtime / WAF-runtime / log DLP）、哪些要外接（[Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)、[Okta](/backend/07-security-data-protection/vendors/okta/) IdP log、edge WAF）
2. observability + security 同 plane 的優勢何時成立、何時是 vendor lock-in 風險
3. Cloud SIEM 計費（events/month + indexed）跟 Standard / Flex Logs retention tier 的成本治理
4. 何時用 Datadog、何時走 Splunk / Elastic / Google Security Ops 的取捨

## 最短判讀路徑

判斷 Datadog Security 部署是否健康、最少看四件事：

- **Datadog Agent coverage**：agent 是否裝在所有 host / container / serverless wrapper、log forwarder 是否覆蓋 cloud control plane（AWS CloudTrail / GCP Audit Log / Azure Activity Log）、IdP（[Okta](/backend/07-security-data-protection/vendors/okta/)）audit log 是否進來 — 缺一個就是 detection 盲點
- **Detection rule ownership**：Cloud SIEM rule 是用內建還是 custom、custom rule 是否走 Git 版控（Terraform `datadog_security_monitoring_rule`）、staging 環境是否 dry-run 24-48hr 才 promote production
- **CSPM compliance check 治理**：CIS / NIST / PCI baseline 開哪些、findings 是否進 ticket workflow、misconfig 修復 SLA 有沒有定義（critical 24hr、high 7d、medium 30d）
- **Events/month + Indexed Log 預算**：Cloud SIEM 按 events/month + indexed event 計費、新加 source 前是否估算 ingestion impact、Standard / Flex Logs retention tier 是否依 log priority 分流

四件事任一缺失、就是 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 邊界的待補項目。

## 日常操作與決策形狀

**Datadog Agent 採集**：log / metrics / trace / security event 走同一個 Agent、用 integration（150+）抓 cloud / SaaS / database / queue。security event 跟 observability event 在後端用 *attribute tag*（`env`、`service`、`host`、`trace_id`）關聯、查 incident 時可以從 log alert pivot 到同 trace_id 的 APM trace 看 attack 發生的 application context。

**Cloud SIEM detection rule**：rule 形式類似 SPL 的 query — `source:okta @evt.name:user.authentication.auth_via_mfa @outcome:failure` 加 *signal aggregation*（rolling window count、new value、anomaly detection、impossible travel）。內建 rule 跟 MITRE ATT&CK 對應、跟 [Splunk Security Content](/backend/07-security-data-protection/vendors/splunk/) 同類但 rule 數量較少；custom rule 走 Terraform provider 進版控、不在 UI 直改 production。

**CSPM compliance check**：scan AWS / GCP / Azure 配置 vs CIS / NIST 800-53 / PCI / SOC 2 baseline、發現 misconfig（public S3 bucket、overly permissive IAM、不安全 SG rule）。跟 Wiz / Prisma Cloud 同類但跟 Datadog Infra 同 dashboard、findings 可以直接看到 affected resource 的 metrics / log。優勢是 *資安發現可以直接看業務影響*、限制是 graph-based attack path（Wiz 強項）不及專業 CNAPP。

**Cloud Workload Security（CWS）**：用 Linux eBPF probe 在 kernel 層觀察 container / process behavior、偵測 cryptominer / privilege escalation / 異常 syscall / file integrity 變動。跟 [Falco](https://falco.org/) 同類但跟 Datadog Infra 同 plane、CWS alert 可以直接 pivot 到該 container 的 CPU / memory / trace。Linux eBPF 對 kernel 版本敏感、舊 kernel 部份功能不可用、production 前要確認 fleet kernel matrix。

**App and API Protection（AAP）**：RASP-style protection、Datadog APM library 在 application runtime 收 attack signal（SQLi / XSS / SSRF / 異常 traffic pattern）。跟 [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) / [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/) 不同層 — WAF 在 edge / CDN、AAP 在 app runtime 看到的是真實 request handler / DB query。兩者互補不互斥：edge WAF 擋 volumetric attack 跟已知 pattern、AAP 補 app-specific business logic abuse。

**Sensitive Data Scanner**：scan ingest 進來的 log、用內建或 custom pattern 偵測 PII / credential / payment card / API key、發現後可以 redact、quarantine 或 alert。是 *DLP-lite* — 比不上 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) 的 sensitive data discovery / classification / lineage 全套、但對 *log 中誤洩 secret* 的場景夠用、是 detection signal source 也是 DLP 補位。

**Notebooks + Workflow Automation**：Notebooks 是 incident investigation 用的 query workbook、混 log query + metric chart + APM trace + 註記、跟 [Splunk Search](/backend/07-security-data-protection/vendors/splunk/) 比較像 Jupyter notebook 的 SOC 版。Workflow Automation 是輕量 SOAR、接 PagerDuty / Slack / Jira / Webhook / [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) API、playbook 走 visual builder + Python。SOAR 深度不到 Splunk SOAR、但對中等規模 SOC（10-50 人）的常見 response 動作（rotate credential / block IP / open ticket）夠用。

**Standard Logs / Flex Logs + retention tier**：log 進 Datadog 後分 *Indexed*（hot、可全文搜尋、貴）、*Flex Logs*（warm、retention 長、查詢延遲較高、cost 1/3-1/5）、*Archive*（cold、丟 S3 / GCS、純儲存）三層。Cloud SIEM detection 跑在 indexed log 上、所以 *哪些 log 走 indexed* 直接決定 detection coverage 跟 bill。tier 1 source（IdP / cloud control plane / payment）必 indexed、tier 2 source（app log）按 sampling、tier 3（debug）走 Flex 或 Archive。

## 核心取捨表

| 取捨維度            | Datadog Security                              | Splunk                              | Elastic Security                     | Google Security Operations                   |
| ------------------- | --------------------------------------------- | ----------------------------------- | ------------------------------------ | -------------------------------------------- |
| 設計起點            | Observability + security 同 plane             | Security-first、log 統一查詢平台    | Search-first、ELK stack 延伸         | Massive scale ingestion、Google threat intel |
| 計費模型            | Per-host + per-event（events/month）          | Ingestion-based（GB/day、累進）     | Resource-based（node / cluster）     | Fixed price by data tier（PB-scale 划算）    |
| 部署模型            | SaaS only                                     | Self-hosted / SaaS                  | Self-hosted / Cloud / Serverless     | SaaS only（Google Cloud）                    |
| 觀測整合            | Native — log + APM + metrics + infra 同 query | 需自接（Splunk Observability 另收） | 需自接（Elastic Observability 另開） | 弱 — 跨產品 federation                       |
| 雲端 posture (CSPM) | 內建（CSM）                                   | 第三方 add-on / Cisco 整合          | 第三方 / Wazuh                       | 第三方 / Mandiant 整合                       |
| 容器 runtime        | 內建 CWS（eBPF）                              | 需 Falco / 第三方                   | Elastic Defend                       | 需 Falco / 第三方                            |
| App runtime（RASP） | 內建 AAP                                      | 需第三方                            | 第三方                               | 第三方                                       |
| SOAR / Response     | Workflow Automation（輕量）                   | Splunk SOAR（業界先驅）             | Cases + Endpoint response            | SOAR 內建（前 Siemplify）                    |
| 適合場景            | Cloud-native + 已用 Datadog + 中等規模 SOC    | Enterprise + 跨 on-prem、預算允許   | OSS-friendly、Elastic stack 已用     | 超大規模 ingestion、Google 雲                |

選 Datadog 的核心訴求：*已經用 Datadog observability、cloud-native 為主、SOC 規模中等（10-50 人）、需要 observability + security 同 plane 的 incident 判讀路徑*。on-prem 為主、預算敏感（host 量 1000+）、需要 enterprise SOAR / RBA 深度、走 Splunk；OSS-friendly、跨 on-prem、走 Elastic。

## 進階主題

**Cross-product correlation（log + APM + metrics 同 trace_id）**：Datadog 最特別的偵測形狀 — security alert 不只 log line、而是綁 trace_id 的 *integrated incident view*。例如 API endpoint 出現 SQLi 嘗試、Cloud SIEM 開 signal、同時 APM 看到該 request 的 DB query 跟 latency、infra 看到該 host 的 CPU。對「query latency 異常是不是被攻擊」這種混合 incident 偵測有結構性優勢、跟 [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/) 的調查路徑直接對應。

**CWS Linux eBPF 行為偵測**：eBPF probe 在 kernel 層、不需要 kernel module、不影響 process performance（< 1% overhead）。可以偵測的行為包括 file integrity（`/etc/passwd` 被改）、process tree（`bash → curl → /tmp/payload` 異常 chain）、network connection（容器對外連 cryptominer pool）、syscall pattern（`ptrace` 用於 process injection）。跟 [Falco](https://falco.org/) 同樣用 eBPF、差別是 Datadog CWS 不需要單獨部署 + 跟 Datadog 其他 signal 同 plane。

**Datadog Threat Intelligence**：內建 threat feed（malicious IP / domain / file hash）、自動標記 log / network event 命中 IoC。可以加自家 STIX/TAXII feed、不過深度比不上 [Mandiant](https://www.mandiant.com/) / Recorded Future / 專業 TI platform；中等規模 SOC 夠用、嚴重 APT 對抗場景要外接專業 TI。

**跟 Datadog Incident Management 整合**：security signal 可以直接開 Datadog Incident（內建 incident channel + timeline + post-mortem template）、跟 [PagerDuty](/backend/08-incident-response/vendors/pagerduty/) 同類但跟 observability 同 plane。對 *資安事件升級成全公司 incident* 的場景（[Change Healthcare 2024 Operations Impact](/backend/07-security-data-protection/red-team/cases/data-exfiltration/change-healthcare-2024-ops-impact/) 那種規模）可以共用 incident commander 視角、不用兩套 timeline 拼起來。

## 排錯與失敗快速判讀

- **Cloud SIEM 偵測 lag / 沒 alert**：events 沒進 indexed log（走了 Flex）、retention tier 設錯 — 檢查 log pipeline rule 是否把 security-critical source 標 indexed
- **Events/month 暴衝**：debug log / verbose log 進 Cloud SIEM index、CWS event 量爆 — log pipeline 前置 filter（Datadog Observability Pipeline 或 Cribl）、CWS rule 收斂 noisy 行為
- **CSPM findings 100+ 沒人修**：findings 沒進 ticket workflow、沒分 priority — 整合 Jira / ServiceNow、severity 對應 SLA、findings 老化超 30 天升級
- **CWS 在舊 kernel host 沒資料**：eBPF feature 對 kernel 版本敏感（< 4.18 部份功能不支援）— 升級 kernel 或標記該 host 為 CWS-incompatible、補位用 host-based agent
- **AAP false positive 卡 user**：RASP 在 app runtime 直接 block、誤殺正常 request — AAP 先走 monitor mode 1-2 週收 baseline、tune 後再轉 protect mode
- **Sensitive Data Scanner miss PII**：custom pattern 沒寫對、log format 嵌套（JSON 內又是 JSON）— 用 sample log 跑 dry-run、scanner 跑在 ingest 階段不是 retroactive
- **Workflow Automation playbook 黑箱**：自動 rotate credential 結果誤殺 prod service account — playbook high-impact action 走 approval gate、default 走 containment 不走 deletion

## 何時改走其他服務

| 需求形狀                          | 改走                                                                                                                                                          |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Enterprise + 跨 on-prem、預算允許 | [Splunk](/backend/07-security-data-protection/vendors/splunk/)                                                                                                |
| OSS-friendly / Elastic stack 已用 | [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)                                                                            |
| 超大規模 ingestion + Google 雲    | [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)                                                        |
| 嚴格 DLP / 資料分類               | [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) |
| Cloud posture graph / attack path | Wiz / Prisma Cloud / Lacework                                                                                                                                 |
| Edge WAF / volumetric attack      | [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) / [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/)             |
| Endpoint EDR                      | CrowdStrike Falcon / Microsoft Defender for Endpoint                                                                                                          |
| Incident routing                  | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                                                                              |

## 不在本頁內的主題

- Datadog Agent 完整 configuration reference、custom check 撰寫
- Datadog observability（APM / RUM / Synthetics / DBM）細節 — 屬 [4 observability](/backend/04-observability/) 模組
- Cloud SIEM rule 完整語法 reference
- CWS eBPF probe 撰寫（custom rule via Agent Expression Language）細節
- Datadog Incident Management workflow（屬 [8 IR](/backend/08-incident-response/) 模組）

## 案例回寫

Datadog Security 在 07 案例庫沒有直接 vendor-level 事件、但 observability + security 同 plane 的偵測形狀讓部份案例的調查路徑變短、值得對照：

| 案例                                                                                                                                                 | 跟 Datadog Security 的關係（對照啟示）                                                                                                            |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)            | Query volume + 連接數 + CPU 負載異常是 Datadog 同 plane 的強項、Cloud SIEM rule + DBM metrics 同 query 不用 SIEM + 監控工具拼接                   |
| [Change Healthcare 2024 Operations Impact](/backend/07-security-data-protection/red-team/cases/data-exfiltration/change-healthcare-2024-ops-impact/) | 業務中樞事件的影響評估、APM + Infra 可秒級判斷 latency 異常源自資安 vs 容量、Datadog Incident 共用 IC 視角                                        |
| [Mailchimp 2023 Support Tool Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/mailchimp-2023-support-tool-abuse/)        | APM span correlation 可看到單一 operator 短時間跨多 tenant access 的 trace pattern、log-only SIEM 看不到 application-level tenant 切換            |
| [Uber 2022 MFA Fatigue](/backend/07-security-data-protection/red-team/cases/identity-access/uber-2022-mfa-fatigue/)                                  | Cloud SIEM detection rule 配 [Okta](/backend/07-security-data-protection/vendors/okta/) MFA log + APM error rate correlation、不靠單一 log source |
| [Detection Coverage and Signal Governance (section)](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)                 | Standard / Flex Logs + retention tier 是 detection coverage 治理的工具、tier 1 source 必 indexed、tier 2 / 3 走 Flex / Archive                    |

## 下一步路由

- 上游：[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)、[Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)
- 平行：[Splunk](/backend/07-security-data-protection/vendors/splunk/)、[Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)、[Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)
- 下游：[Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)（DLP signal 進 Datadog）
- 跨類：[Okta](/backend/07-security-data-protection/vendors/okta/)（IdP log source）、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（Workflow Automation 拉 API）、[Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) / [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/)（edge WAF log 進 Cloud SIEM、AAP 在 app 層補位）
- 跨模組：[4 observability](/backend/04-observability/)（同 Agent / 同 plane）、[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Datadog Incident → IR routing）
- 官方：[Datadog Security Documentation](https://docs.datadoghq.com/security/)
