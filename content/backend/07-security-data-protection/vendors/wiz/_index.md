---
title: "Wiz"
date: 2026-05-18
description: "Agentless CNAPP、Security Graph + Toxic Combination 風險優先級、API-only scan 不需 workload agent"
weight: 16
tags: ["backend", "security", "vendor", "wiz", "cnapp", "cspm", "cloud-security"]
---

Wiz 是 *agentless CNAPP*（Cloud-Native Application Protection Platform）的代表、用 *cloud API + snapshot scan* 從外面看雲、不在 workload 上裝 agent。2020 年由前 Microsoft Cloud Security Group 創辦人成立、2024 估值約 $12B、是 CNAPP 賽道的後起黑馬。它跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) 的差異不在 *能不能掃出 vulnerability*、而在 *風險優先級的組合方式* — Wiz 用 *Security Graph + Toxic Combination* 把多個 low-risk finding 串成 *attack path*、而不是給你 10000 個獨立 CVE。

## 服務定位

Wiz 的核心定位是 *agentless cloud posture + workload protection platform*、把 CSPM（Cloud Security Posture Management）/ CWP（Cloud Workload Protection）/ CIEM（Cloud Infrastructure Entitlement Management）/ KSPM（Kubernetes Security Posture Management）/ DSPM（Data Security Posture Management）整合在同一個 Security Graph 上面。底層是 *Connector*（讀 AWS / GCP / Azure / OCI / K8s 的 read-only API + snapshot scan）、頂層是 *Issues + Projects + Toxic Combination rules*。

跟 Prisma Cloud / Lacework 比、Wiz 走 *graph-first* — 不是給你一張 finding list、而是把 resource / IAM / vulnerability / secret / network exposure 連成圖、可以用 query 問「哪些 EC2 有 RCE CVE 且 IMDS v1 且能 assume 跨帳戶 admin role」。跟 CrowdStrike Falcon Cloud Security 比、Wiz 是 *agentless-first*（CWP 才用 sensor、posture / 漏洞掃描 0 agent）、Falcon CS 走 *endpoint agent 延伸到雲*。跟 [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) CSPM 比、Datadog 是 *observability platform 上的 security view*、Wiz 是 *security-first CNAPP*、Wiz 的 graph 跟 toxic combination 深度大幅領先、但獨立 SIEM / log 能力不如 Datadog / [Splunk](/backend/07-security-data-protection/vendors/splunk/)。跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) 比、Snyk 走 *developer-first SAST + SCA + container*、Wiz 走 *cloud posture + agentless workload scan*、兩者場景互補不替代 — 多數客戶 Snyk 管 left-shift dev 階段、Wiz 管 runtime cloud。

關鍵張力：*agentless + multi-cloud + Security Graph* ↔ *單一 workload count 計費 + 多模組組合容易踩 sticker shock*。Wiz 的價值前提是組織夠大、cloud account / workload 夠多到 *toxic combination* 比 *單點 CVE list* 更有意義；小型團隊 + 單一雲 + 預算敏感、用 Wiz 等於買保時捷送外賣。

## 本章目標

讀完本頁、讀者能判斷：

1. Wiz 在 cloud security stack 中承擔哪一段（CSPM / CWP / CIEM / KSPM / DSPM / Wiz Code）、哪些要外接（[Splunk](/backend/07-security-data-protection/vendors/splunk/) 等 SIEM 接 Issues、[Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/) 是否要保留 dev-time scan）
2. Security Graph query 跟 Toxic Combination rule 的 ownership 設計（誰寫 rule、誰 triage Issue、誰調 Project scope）
3. Agentless scan 的可見性邊界（snapshot 能看到 / 看不到什麼、需不需要 Wiz Sensor / Defend 補 runtime）
4. 何時用 Wiz、何時走 Prisma Cloud / Lacework / CrowdStrike Falcon CS / Datadog CSPM 的取捨

## 最短判讀路徑

判斷 Wiz deployment 是否健康、最少看四件事：

- **Connector 覆蓋率**：所有 prod cloud account（AWS / GCP / Azure / OCI）跟 K8s cluster 是否都接上、IAM role 是否最小權限（Wiz 給的 CloudFormation / Terraform template 不要自己加權限）、snapshot scan 是否涵蓋所有 region / disk type
- **Toxic Combination rule 設計**：是不是只開預設 rule、有沒有針對自家環境 anti-pattern 寫 custom rule（例如 *cross-account assume + payment service + secret access*）、rule 走不走 PR review
- **Issue triage SLA**：critical / high Issue 的 mean-time-to-resolve、是否跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / Jira / Slack 整合、Project scope 是否依 service owner 切（不是丟整包給 SecOps）
- **Wiz Code / Wiz Defend coverage 邊界**：IaC scan 跟 dev-time CI 是 Wiz Code 還是 [Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/)、runtime detection 是 Wiz Defend 還是 Falco / CrowdStrike、不要兩邊都裝又都沒人 triage

四件事任一缺失、就是 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/) 跟 [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 的待補項目。

## 日常操作與決策形狀

**Connector 跟 agentless scan**：Wiz 透過 *Connector*（每個 cloud account 一個 IAM role）讀 cloud control plane API、定期 snapshot EBS / Persistent Disk / Managed Disk、在 Wiz 自家環境裡 mount snapshot 做 vulnerability / secret / malware scan。對 workload 0 影響、不需要在 EC2 / GKE node / VM 裡裝任何 agent。代價是 *runtime 行為看不到*（process / network connection / syscall）— 那段要 Wiz Defend / Wiz Sensor 或外接 Falco / CrowdStrike。

**Security Graph**：Wiz 把所有 resource（compute / storage / IAM principal / network / secret / vulnerability finding）建成 graph、用 GraphQL-like query 跨類型查詢。Security Graph 是 first-class concept、不只是 visualization — Toxic Combination rule、Issue correlation、blast radius 估算都走 graph。寫 SPL / KQL 跟寫 Wiz query 的 mindset 不一樣 — Wiz query 是 *relationship-first*（從 resource A 走幾跳到 resource B）、SPL 是 *event-first*（時間序列上的 log）。

**Toxic Combination**：CNAPP vs 傳統 vulnerability scanner 的根本差異。單一 finding 是 low risk（一個 CVE / 一條 over-permission / 一個 public S3）、組合起來是 critical attack path（*public-facing EC2 + RCE CVE + IMDS v1 + assume admin role + 觸碰 customer PII bucket*）。Wiz 預設帶幾十條 toxic combination rule（attack-path-style）、organization 應該加自家 anti-pattern。對應 [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/) 跟 [7.5 應用層風險](/backend/07-security-data-protection/entrypoint-and-server-protection/) 的跨 control 整合。

**Issues + Projects**：finding 進 Wiz 後變 *Issue*、按 *Project* 路由 — Project 是邏輯切分（按 BU / service / 環境）、每個 Project 有 owner、Issue 自動分派。反例是 *單一 default Project 收所有 Issue*、SecOps 一天看 5000 個 Issue 看不完、跟 [Alert Fatigue and Signal Quality](/backend/07-security-data-protection/blue-team/alert-fatigue-and-signal-quality/) 同樣模式。production 要 Project scope 對齊 service ownership、跟 Jira / Slack / [Splunk](/backend/07-security-data-protection/vendors/splunk/) 整合自動建 ticket。

**Wiz Code**：dev-time / IaC scan、覆蓋 Terraform / CloudFormation / K8s manifest / Helm + container image build-time scan + SCA、跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) Code/IaC 跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) Config 重疊。多數客戶選一邊用、不會雙開。Wiz Code 的賣點是 *跟 runtime Wiz finding 同一個 graph* — 在 IDE / PR 階段就能看到「這條 IaC 改動會在 prod 產生哪條 toxic combination」。

**Wiz Defend (Gem)**：2024 收購 Gem Security 整合 runtime detection / cloud detection、補 Wiz 早期缺的 runtime 層。Wiz Defend 走 *cloud-native log + Wiz Sensor*（K8s eBPF sensor）混合、跟 CrowdStrike Falcon EDR / Falco 競爭。產品成熟度仍在跟進、2024-2025 才大量 GA、不要假設它已經是 CrowdStrike / SentinelOne 等級的 EDR 替代品。

**Wiz Sensor**：K8s admission controller + eBPF runtime sensor、補 agentless 看不到的 runtime 行為（container process / network connection / file integrity）。是 *選配*、不裝 Wiz 仍能做 posture / vulnerability scan、裝了才有 runtime detection。資源開銷比 Falco 大、跟 CrowdStrike Falcon container sensor 競爭。

**SIEM 整合**：Wiz Issues / Detections 可推到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/) 走 SOAR playbook。常見 pattern：Wiz 偵測到 toxic combination → 推 Issue 到 Splunk → SOAR playbook 自動 isolate workload 或 rotate credential、走 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) API。

## 核心取捨表

| 取捨維度       | Wiz                                           | Prisma Cloud (Palo Alto)                 | Lacework                                        | CrowdStrike Falcon CS                   |
| -------------- | --------------------------------------------- | ---------------------------------------- | ----------------------------------------------- | --------------------------------------- |
| 部署模型       | Agentless-first（snapshot scan）+ 選配 Sensor | Agent + agentless 混合                   | Agent + agentless 混合、Polygraph behavior-base | Agent-first（Falcon sensor 延伸）       |
| 核心 concept   | Security Graph + Toxic Combination            | Cloud Security 套件（CSPM/CWP/CIEM/DSPM) | Polygraph（ML behavior model）                  | Falcon platform（EDR + cloud workload） |
| 計費模型       | Per workload + module                         | Credit-based（modular）                  | Per workload + data ingestion                   | Per endpoint + module                   |
| Multi-cloud    | 強（AWS/GCP/Azure/OCI/K8s）                   | 強                                       | 強                                              | 強（但 Falcon-first 文化）              |
| Runtime 偵測   | Wiz Defend（2024+、成熟度仍在跟進）           | Prisma Cloud Defender（成熟）            | Polygraph 行為偵測（成熟）                      | 業界最強（EDR 出身）                    |
| Developer 整合 | Wiz Code（IaC/SCA/PR scan）                   | Prisma Cloud Code Security               | 弱                                              | 弱                                      |
| 學習曲線       | 中 — Graph query 是新語法但結構清楚           | 陡 — 模組多、UX 較重                     | 中                                              | 中 — Falcon UI 一致                     |
| 適合場景       | Multi-cloud + 大型 org + 看重 attack path     | 已用 Palo Alto 生態、需要 NGFW 整合      | ML-first 偵測、不想自己寫 rule                  | 已用 Falcon EDR、想擴到 cloud workload  |
| 退場成本       | 中 — Graph query / Toxic Combination 量大     | 高 — 跟 Palo Alto 生態耦合               | 中                                              | 高 — Falcon sensor 已大規模部署很難換   |

選 Wiz 的核心訴求：*multi-cloud + 中大型組織 + 願意接受 agentless 的 runtime 邊界 + 重視 toxic combination 的優先級*。如果組織已重度使用 CrowdStrike Falcon EDR、走 Falcon CS 延伸更一致；如果已重度 Palo Alto、走 Prisma Cloud 整合更深。

## 進階主題

**Security Graph query language**：類 GraphQL 的 query syntax、可以寫「找所有 public-facing EC2、有 CVE-2024-XXX、能 assume role 到 admin account、且該 role 可讀 prod-pii bucket」這種 5-hop query。production 用法：把高頻 query 存成 *Saved Query* + alert、把 attack pattern 寫成 *Toxic Combination rule*。Graph query 寫得好不好直接決定 *attack path 是否被涵蓋*、跟 SPL 寫 correlation rule 是同一個 ownership 議題。

**Toxic Combination 設計**：預設 rule 是 *generic 雲安全 anti-pattern*（public + vulnerable + over-permission）、organization 應該補 *industry-specific* 跟 *organization-specific* anti-pattern — 金融業要看「payment workload + cross-region replication + non-encrypted snapshot」、SaaS 多租戶要看「tenant-A workload + assume tenant-B role + 跨 tenant data access」。Toxic combination rule 走 PR review + staging tenant 驗證、跟 [Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/) 同流程。

**Wiz AI (2024+)**：LLM-assisted investigation — 用自然語言查 graph（「show me all critical issues touching prod payment service」翻譯成 graph query）、Issue triage 自動 summarize attack path、根因建議。實務上是 query 翻譯 + summarize、不是替代 analyst 判讀；高 stake 決策仍要人類 review。

**Agentless secret scan**：Wiz snapshot scan disk 時也掃 hardcoded secret（AWS access key / API token / private key）、跟 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) / [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) 整合做 rotation 路由。對應 [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) 的偵測層。

**Sigstore / SBOM 整合**：Wiz 可消費 SBOM（[Syft / Grype](/backend/07-security-data-protection/vendors/syft-grype/) 或 [Trivy](/backend/07-security-data-protection/vendors/trivy/) 產出）+ verify Cosign / Sigstore 簽章、把 *artifact trust* 接進 Security Graph。對應 [7.12 供應鏈完整性與工件信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 的 build-to-runtime 證據鏈。

**Wiz for AI**：2024+ 新 module、針對 AI workload（LLM model storage / training dataset / inference endpoint）做 posture scan、找 misconfigured model bucket / exposed inference endpoint / training data leak。早期產品、定位是 *AI workload 的 CSPM 延伸*、不是替代 [AI red team / prompt injection 偵測](/backend/07-security-data-protection/entrypoint-and-server-protection/) 工具。

## 排錯與失敗快速判讀

- **Issue 爆炸 / 沒人 triage**：default Project 收所有 finding、沒對齊 service ownership — 切 Project 給每個 BU / service、autoclose 已知 accepted risk、跟 Jira / Slack 整合自動分派
- **Toxic Combination 沒命中真實 incident**：只開預設 rule、沒寫 organization-specific rule — 從 [red team case 庫](/backend/07-security-data-protection/red-team/) 反推自家環境的 attack path、寫成 custom rule
- **Snapshot scan 漏掉 ephemeral workload**：scan 間隔 12-24hr、短命 Lambda / Fargate task 沒掃到 — 補 Wiz runtime sensor 或外接 Falco；ephemeral workload 改用 build-time scan（[Trivy](/backend/07-security-data-protection/vendors/trivy/) / Wiz Code）
- **Connector IAM role 權限漂移**：自己加了權限結果踩 over-permission — Connector role 用 Wiz 提供的 CloudFormation / Terraform template、走 [Terraform](/backend/05-deployment-platform/vendors/terraform/) 版控、不手改
- **Sticker shock / 計費爆炸**：開了所有 module（CSPM + CWP + CIEM + KSPM + DSPM + Wiz Code + Defend）、workload count 暴衝 — 只開核心 module、ephemeral workload 走 sampling、enterprise contract 談 cap
- **Wiz Code 跟 Snyk / Trivy 雙開**：dev team 用 Snyk、SecOps 用 Wiz Code、PR 兩邊 finding 重複 — 選一邊做 dev-time gate、另一邊只當 visibility、不要兩邊都 block PR
- **Wiz Defend 當 EDR 用結果偵測能力不夠**：runtime detection 期待 CrowdStrike 等級 — Wiz Defend 仍在跟進、純 EDR 需求保留 CrowdStrike / SentinelOne、Wiz Defend 補 cloud context 層
- **Audit log retention 不夠**：Wiz 預設 audit retention 偏短、incident 回查時資料缺 — push Issue 跟 audit log 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Datadog](/backend/07-security-data-protection/vendors/datadog-security/) 做長期保存

## 何時改走其他服務

| 需求形狀                                   | 改走                                                                                                                                                                                                                                                         |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 已用 Palo Alto NGFW / Prisma 生態          | Prisma Cloud                                                                                                                                                                                                                                                 |
| 已用 CrowdStrike Falcon EDR                | Falcon Cloud Security                                                                                                                                                                                                                                        |
| ML-first 偵測 / 不想寫 rule                | Lacework                                                                                                                                                                                                                                                     |
| 小型 / 單一雲 / 預算敏感                   | [Trivy](/backend/07-security-data-protection/vendors/trivy/) + cloud-native scanner（AWS Inspector / GCP SCC）                                                                                                                                               |
| Developer-first SAST + SCA                 | [Snyk](/backend/07-security-data-protection/vendors/snyk/) / [GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/)                                                                                              |
| Observability 已用 Datadog、不想再買 CNAPP | [Datadog Security CSPM](/backend/07-security-data-protection/vendors/datadog-security/)                                                                                                                                                                      |
| SIEM / 跨 source correlation               | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/) |
| Runtime container 行為偵測 (OSS)           | Falco / Cilium Tetragon                                                                                                                                                                                                                                      |
| Incident routing                           | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                                                                                                                                                                             |

## 不在本頁內的主題

- Security Graph query syntax 完整 reference 跟所有 built-in toxic combination rule 清單
- Wiz Defend / Wiz Sensor 的 eBPF 內部實作細節
- Wiz Code 跟 IDE plugin（VSCode / JetBrains）的具體設定
- Cloud-native scanner（AWS Inspector / GCP Security Command Center / Azure Defender）的對照細節
- Wiz API 的具體 SDK 用法跟 Terraform Provider 配置
- CNAPP 市場的完整 vendor 比較（Gartner Magic Quadrant 等）

## 案例回寫

Wiz 在 07 案例庫沒有直接 vendor-level 事件、但多個 case 是 CNAPP 風險組合的對照：

| 案例                                                                                                                                      | 跟 Wiz 的關係（對照啟示）                                                                                                               |
| ----------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/) | Security Graph 可關聯「leaked credential + 過寬 IAM + 缺 MFA + 大量 data egress」四個 low-risk finding 成 toxic combination、提前 alert |
| [LastPass 2022 Backup Chain](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/)           | Wiz 可掃 S3 bucket public exposure + sensitive data + IAM scope、發現 backup bucket 配置漂移、對應 DSPM 場景                            |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)    | Agentless snapshot scan 在 Log4Shell 期間可秒級回答「哪些 prod workload 有 log4j-core vulnerable version」、不需 endpoint agent rollout |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                    | Wiz Code + Sigstore 整合可驗證 build artifact 來源、Security Graph 可串「signed artifact + 異常 runtime behavior」                      |
| [7.3 入口治理與伺服器防護 (section)](/backend/07-security-data-protection/entrypoint-and-server-protection/)                              | Network exposure scan + IAM analysis 對應 section 原則、把「public + over-permission + sensitive」串成 toxic combination                |
| [7.12 供應鏈完整性 (section)](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)                            | Wiz Code IaC scan + image scan + SBOM 消費對應 build-to-runtime 證據鏈                                                                  |

## 下一步路由

- 上游：[7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)、[7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[Snyk](/backend/07-security-data-protection/vendors/snyk/)（dev-first SAST/SCA）、[Trivy](/backend/07-security-data-protection/vendors/trivy/)（OSS scanner）、[Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)（observability + CSPM）
- 下游：[Splunk](/backend/07-security-data-protection/vendors/splunk/)（Issues → SIEM）、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（SOAR 自動 rotation）、[Syft / Grype](/backend/07-security-data-protection/vendors/syft-grype/)（SBOM 接 Wiz Code）
- 跨類：[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) / [Azure RBAC](/backend/07-security-data-protection/vendors/azure-rbac/)（CIEM 分析對象）、[Terraform](/backend/05-deployment-platform/vendors/terraform/)（Connector / IaC 版控）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Toxic combination → IR routing）、[5 部署平台](/backend/05-deployment-platform/)（cloud account / K8s onboarding）
- 官方：[Wiz Documentation](https://docs.wiz.io/)
