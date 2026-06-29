---
title: "Prisma Cloud"
date: 2026-05-18
description: "Palo Alto CNAPP、agent (Defender) + agentless 雙軌、五模組（Compute / CSPM / Code / Data / CIEM）、Compliance template 強"
weight: 17
tags: ["backend", "security", "vendor", "prisma-cloud", "cnapp", "cspm", "palo-alto"]
---

Prisma Cloud 是 Palo Alto Networks 旗下的 CNAPP（Cloud-Native Application Protection Platform）、把 *runtime workload 防護*（Defender agent）跟 *agentless cloud posture* 同一個 Console 整合。它的歷史是多次併購疊起來的 — Twistlock（container security）/ Redlock（CSPM）/ Bridgecrew（IaC scan）/ Aporeto（microsegmentation）— 五個模組各自有獨立的 data model 與 UI 軌跡。它跟 [Wiz](/backend/07-security-data-protection/vendors/wiz/) / [Lacework](/backend/07-security-data-protection/vendors/lacework/) / [CrowdStrike Falcon Cloud Security](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/) 的差異在 *是否走 host-level agent + 是否綁 Palo Alto 生態*、功能清單相近。

## 服務定位

Prisma Cloud 的核心定位是 *agent + agentless 雙軌 CNAPP*、五模組覆蓋 cloud workload 從 IaC 到 runtime 的完整鏈：*Compute Security*（前 Twistlock、container / serverless / host workload 的 Defender agent + image scan）、*CSPM*（cloud posture、misconfiguration、compliance baseline）、*Code Security*（前 Bridgecrew、IaC 與 SCM scan）、*Data Security*（DSPM、雲端資料庫與 bucket 敏感資料偵測）、*CIEM*（cloud entitlement、跨雲 over-permission 治理）。Defender agent 是 host / pod / Lambda extension 上跑的常駐元件、提供 runtime IDS、file integrity、process anomaly 等 *agentless 抓不到的訊號*。

跟 [Wiz](/backend/07-security-data-protection/vendors/wiz/) 比、Prisma 走 *agent + agentless 雙軌*、Wiz 走 *agentless-only*。Wiz 用 cloud snapshot scan + control-plane API 抽訊號、部署快、不踩 host；Prisma Defender agent 補上 *runtime behavior* 的覆蓋（process spawn pattern、JNDI lookup、anomalous network connect）、代價是要在 host / pod / Lambda 上佈 agent、deployment 複雜度高一個層級。跟 [Lacework](/backend/07-security-data-protection/vendors/lacework/) 比、Lacework 用 *Polygraph behavior graph* 做 host-level anomaly、focus 在 detection；Prisma 覆蓋面廣（含 IaC + CIEM + DSPM）、但每個模組深度比 Lacework 偵測單點淺一點。跟 [CrowdStrike Falcon Cloud Security](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/) 比、CrowdStrike 的 endpoint agent 已在多數 enterprise 環境跑、Cloud Security 直接共用 endpoint plane；Prisma 是 *cloud-first CNAPP 加上 agent*、不是 endpoint EDR 延伸。

關鍵張力：*覆蓋面廣度* ↔ *模組整合成熟度* 是 Prisma 客戶最常踩的 trade-off。五模組來自不同收購、UI / API / data model 整合仍在進行中、客戶常遇到「同一個 finding 在 Compute Console 顯示是 critical、在 CSPM 是 medium」、或「Code Security 報的 IaC issue 跟 Runtime 報的實際 config 對不起來」。預算允許就用 Prisma 拿覆蓋面廣度、不允許就走 Wiz（agentless 部署快）或 Lacework（單模組偵測深）。

## 本章目標

讀完本頁、讀者能判斷：

1. Prisma Cloud 在 cloud security stack 中承擔哪幾段（Compute / CSPM / Code / Data / CIEM）、哪些跟既有 SIEM / EDR / IdP 重疊或互補
2. Defender agent 該佈在 host / pod / Lambda 哪幾層、跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) / [Snyk](/backend/07-security-data-protection/vendors/snyk/) 等 OSS / SaaS image scanner 的分工
3. Compliance template（PCI / HIPAA / NIST / FedRAMP）跟自家 custom policy 的混用方式、誰能改 policy、誰 review
4. 何時用 Prisma、何時改走 Wiz（agentless-only）/ Lacework（detection-focused）/ Trivy（OSS CLI）/ EDR

## 最短判讀路徑

判斷 Prisma 部署是否健康、最少看四件事：

- **Defender agent 覆蓋率**：production K8s cluster 的 DaemonSet 是否所有 node 跑、VM workload 的 agent install rate、Lambda function 的 extension 啟用比例；缺一塊就有 runtime 偵測盲點
- **Console 跟模組一致性**：Compute Console / CSPM dashboard / Code Security finding / CIEM report 同一個 resource 的風險評級是否一致、不一致時誰是 SSoT
- **Compliance template 對齊**：啟用了哪幾套（PCI-DSS / HIPAA / NIST 800-53 / CIS / FedRAMP / SOC2）、跟內部 baseline 的客製 rule 是否走版控
- **Alert 跟 SOC handoff**：Prisma alert 是進自家 incident queue 還是 forward 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)、Cortex XSOAR 是否串 playbook

四件事任一缺失、就是 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 邊界的待補項目。

## 日常操作與決策形狀

**Defender agent deployment**：agent 三種 footprint — *K8s DaemonSet*（每個 node 一個、攔截 container syscall + image runtime scan）、*VM / host agent*（Linux / Windows 安裝、file integrity + process anomaly）、*Lambda extension*（function runtime 注入、serverless 行為偵測）。Production 通常是 DaemonSet + VM agent 雙軌、Lambda extension 視 serverless workload 規模啟用。deployment 比 Wiz 多一步 — 要走 IaC（Helm chart / Terraform module）管 agent rollout、不能手動裝。

**Console 跟 RBAC**：Prisma Cloud Console 是統一入口、但底下 *Compute*（前 Twistlock UI 殘留）跟 *Cloud*（CSPM / Code / Data / CIEM）兩個 plane 分開。RBAC 角色設計常踩坑 — Compute 的 collection（host group）跟 Cloud 的 account group 是不同概念、需要分別給權限。

**CSPM connector**：CSPM 走 read-only cloud API（AWS Cross-Account Role / GCP Service Account / Azure App Registration）抽 config snapshot、定期 reconcile baseline。連 cloud account 是 onboarding 第一步、跟 [Wiz](/backend/07-security-data-protection/vendors/wiz/) / [Lacework](/backend/07-security-data-protection/vendors/lacework/) 同樣的 pattern、Prisma 的 connector permission template 偏寬、要 review 哪些 API 真用得到。

**Code Security（Bridgecrew）**：IaC scan 走 GitHub / GitLab / Bitbucket App、Terraform / CloudFormation / Kubernetes manifest / Dockerfile 在 PR 階段攔截 misconfiguration。Checkov 是 Bridgecrew 開源的底層引擎、Prisma 把 Checkov 規則庫 + 自家 policy 包成 SaaS。對應 [6.6 release gate](/backend/06-reliability/release-gate/)、IaC issue 在 PR 階段擋比 runtime 抓便宜兩個量級。

**CIEM**：cloud entitlement 治理、跨 AWS IAM / GCP IAM / Azure RBAC 找 over-permission 跟 toxic combination（例如 user 同時有 `iam:PassRole` + `lambda:CreateFunction` 可 privilege escalation）。CIEM 報告通常是大量「建議收權限」、實際 remediation 要跟 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) owner 排優先序、不是看到全收。

**Data Security（DSPM）**：雲端資料庫（RDS / BigQuery / Snowflake）+ object store（S3 / GCS）的 sensitive data discovery、跟 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) 功能重疊。Prisma DSPM 的優勢是跟 CSPM / CIEM 同 Console、可以看「敏感資料所在的 bucket 是否有 public ACL + 哪些 role 可以讀」、是 *資料 + 入口 + 身份* 同 plane 的關聯。

**Runtime Protection（Aporeto microsegmentation）**：Defender agent 提供 process / network level 的 runtime IDS / IPS — JNDI lookup 行為、異常 outbound callback、container escape 嘗試、unsigned binary 執行。比起 image-scan-only 多了 *已知 CVE 沒 patch 但 runtime 行為偵測到* 的覆蓋層。

**跟 Palo Alto 生態整合**：Prisma alert 可直接打到 Palo Alto *Cortex XSOAR*（SOAR / playbook）/ *Cortex XDR*（endpoint + cloud unified detection）/ *NGFW / SASE*（firewall rule 自動 push）。對已是 Palo Alto-heavy 環境是生態一致性增加；對非 Palo Alto 環境、Prisma 也 forward 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) 走 webhook / Syslog。

## 核心取捨表

| 取捨維度        | Prisma Cloud                                      | Wiz                                            | Lacework                                  | CrowdStrike Falcon Cloud Security           |
| --------------- | ------------------------------------------------- | ---------------------------------------------- | ----------------------------------------- | ------------------------------------------- |
| 部署模型        | Agent (Defender) + Agentless 雙軌                 | Agentless-only（snapshot scan + API）          | Lightweight agent + agentless 雙軌        | 沿用 CrowdStrike endpoint agent + agentless |
| 部署速度        | 慢 — agent rollout 走 IaC + RBAC 設定多           | 快 — connector 連 cloud account 就開始 scan    | 中 — agent 較輕、但仍需安裝               | 快（若已用 CrowdStrike）/ 中（新導入）      |
| Runtime 偵測    | 強 — Defender 攔 syscall / network / file IDS     | 弱 — runtime behavior 靠 snapshot 對照、延遲高 | 強 — Polygraph behavior graph 為核心      | 強 — endpoint agent runtime telemetry       |
| Posture / CSPM  | 強 — Redlock 出身、compliance template 最完整     | 強 — graph-based blast radius 視覺化最好       | 中 — 有 CSPM 但 focus 在 detection        | 中 — CSPM 後加入、深度比 Prisma / Wiz 淺    |
| IaC scan        | 強 — Bridgecrew 整合、Checkov 底層                | 中 — IaC scan 較新                             | 弱 — 非主力                               | 弱 — 非主力                                 |
| CIEM            | 強 — 五模組原生                                   | 強 — graph-based entitlement analysis          | 中                                        | 中                                          |
| DSPM            | 中 — Data Security 模組                           | 強 — DSPM 是近年強推                           | 弱                                        | 弱                                          |
| 模組整合成熟度  | 中 — 五次收購、UI / data model 仍在整合           | 強 — single platform 原生設計                  | 強 — 單一 data model                      | 中 — endpoint + cloud 整合中                |
| Compliance 廣度 | 強 — PCI / HIPAA / NIST / FedRAMP / SOC2 完整     | 中 — 主要 compliance 都有但模板較淺            | 中                                        | 中                                          |
| 生態整合        | 強 — Palo Alto NGFW / Cortex XDR / XSOAR 同 plane | 中 — vendor-neutral、走 webhook / API          | 中                                        | 強 — CrowdStrike Falcon 生態                |
| 計費複雜度      | 高 — module + credit + workload + multi-year      | 中 — workload / cloud account 為主             | 中                                        | 中                                          |
| 適合場景        | Palo Alto-heavy、agent + posture 雙覆蓋、合規重   | Cloud-native、agentless-first、部署速度優先    | Detection-heavy、Polygraph anomaly 為核心 | CrowdStrike-heavy、endpoint + cloud 統一    |
| 退場成本        | 高 — agent + policy + Cortex 整合多               | 中 — agentless、移除 connector 就乾淨          | 中                                        | 高（若深度整合 CrowdStrike）                |

選 Prisma 的核心訴求：*已在 Palo Alto 生態（NGFW / SASE / Cortex XDR / XSOAR）+ 需要 runtime agent + posture 雙覆蓋 + compliance audit heavy（PCI / HIPAA / FedRAMP）*、且能承擔模組整合不完美 + 部署複雜度 + multi-year contract。純 agentless 用 Wiz、detection-focused 用 Lacework、純 OSS PR scan 用 [Trivy](/backend/07-security-data-protection/vendors/trivy/) + [Syft / Grype](/backend/07-security-data-protection/vendors/syft-grype/)。

## 進階主題

**Defender agent rollout 策略**：K8s DaemonSet 用 Helm chart 管 version + tolerations、staging cluster 先跑 1-2 週觀察 syscall overhead 跟 false positive、再 promote 到 production。VM agent 走 Ansible / SCCM / Terraform user-data、image baking 把 agent 包進 golden AMI 比每次 boot 安裝穩。Lambda extension 走 Lambda Layer、只對 high-value function 開（金流 / IdP / secret access）、不是全 function 都包。

**Runtime IDS / IPS 模式**：Defender 可設 *audit only*（只 log、不阻擋）或 *prevent*（自動 kill process / block network）。production 多數 workload 走 audit、只對 *確定無誤報* 的 rule 開 prevent（已知 malware hash、明確 CVE exploit pattern）。誤判 prevent 業務 process 比放過 alert 代價高、應該預設 audit + SIEM forward + SOC triage。

**Compliance template + Custom policy 混用**：Prisma 提供 PCI-DSS / HIPAA / NIST 800-53 / CIS Benchmark / FedRAMP / SOC2 完整 baseline、可直接啟用。但 baseline 通常太嚴或太寬、實務做法是 *fork baseline + 加自家 exception + 加 organization-specific rule*、走 Git 版控（policy as code、JSON / YAML）、PR review 後 sync 回 Console。policy 不能 console 直改、否則跟既有 SIEM rule 一樣失去 change history。

**Cortex XSOAR / XDR 整合**：Prisma alert → XSOAR playbook 是 Palo Alto 環境的標準路徑、playbook 自動執行 enrichment（拉 threat intel）/ containment（NGFW block / disable IAM user）/ remediation（Terraform PR auto-create）。playbook 要走版控 + dry-run、高影響動作（disable IAM user / delete resource）走 approval gate、不能 fire-and-forget。

**計費結構**：Prisma 按 *module 選購* + 按 *credit 消耗* + 按 *workload count* 三層計費、enterprise 通常是 *multi-year package*（3 年 commit 拿折扣）。實務坑 — 加新 cloud account 沒控管會吃 credit、Code Security 對大 monorepo scan 也吃 credit、Data Security 對大 bucket scan 是高成本項。月底常見的 sticker shock 來自 *Defender agent 數量爆衝*（K8s auto-scale 把 node count 推高）跟 *新 cloud account onboard 沒走 quota 控管*。

## 排錯與失敗快速判讀

- **Defender agent overhead 影響業務 process**：DaemonSet pod 吃 CPU / memory 過高、container syscall hook 拖慢 latency-sensitive workload — 把 *runtime rule* 從 prevent 改 audit、調 collection scope 排除 latency-critical namespace、向 Palo Alto support 開 ticket 看 agent profile
- **同一個 finding 模組評級不一致**：Compute Console 顯示 critical、CSPM 顯示 medium — 確認 *SSoT 是哪個模組*、Compute 是 workload-level、CSPM 是 cloud-config-level、兩者本來就看不同 layer、用 Cortex XSOAR 統一 prioritization 而非靠 Console 對齊
- **CSPM connector permission 報錯**：Prisma 預設 IAM policy 太寬 / 太窄 — 走 *least privilege* 版本、跟 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) owner 確認哪些 API 真用到、不要照官方 template 全開
- **Compliance template 一啟用就 1000+ finding**：baseline 太嚴 + 既有環境本來就沒符合 — 走 *staged adoption*、先選 critical control（IAM / encryption / public exposure）、剩下進 backlog 排期、不要一次全開
- **Code Security PR scan block 太多**：Bridgecrew rule 對既有 IaC noisy — 用 *baseline mode*（既有 issue 標記、只 block 新 issue）、給 team 12 週 SLA 清 backlog、不要 day-1 block 全部
- **CIEM 報告太多 over-permission**：5000+ unused permission 看不完 — 排序看 *toxic combination*（privilege escalation path）優先、單純 unused 走每季 access review、不一次處理
- **Cortex XSOAR playbook 誤殺**：自動 disable IAM user 結果關到 CI/CD service account — 高影響動作走 *approval gate*、playbook default 是 *containment*（temporary block）not *deletion*

## 何時改走其他服務

| 需求形狀                            | 改走                                                                                                                                                                                                 |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 純 agentless / 部署速度優先         | [Wiz](/backend/07-security-data-protection/vendors/wiz/)                                                                                                                                             |
| Polygraph behavior detection 為核心 | [Lacework](/backend/07-security-data-protection/vendors/lacework/)                                                                                                                                   |
| CrowdStrike-heavy 環境              | [CrowdStrike Falcon Cloud Security](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/)                                                                                             |
| 純 OSS image / IaC scan             | [Trivy](/backend/07-security-data-protection/vendors/trivy/) / [Syft / Grype](/backend/07-security-data-protection/vendors/syft-grype/) / [Snyk](/backend/07-security-data-protection/vendors/snyk/) |
| DLP / sensitive data 為主           | [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)                                        |
| SIEM 偵測 / SOC                     | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)                                                  |
| 入口 WAF                            | [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) / [AWS WAF](/backend/07-security-data-protection/vendors/aws-waf/)                                                    |
| 事故 routing                        | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                                                                                                                     |

## 不在本頁內的主題

- Defender agent 完整 syscall hook 清單 / runtime rule 語法 reference
- Bridgecrew Checkov 規則庫的逐條解釋 / 自寫 Checkov rule 細節
- Palo Alto Cortex XSOAR playbook 的 Python SDK 實作
- Prisma SASE / NGFW / Cortex XDR 完整功能（屬 network security / EDR、不在 CNAPP 範圍）
- Compliance 法規的逐條解讀（PCI-DSS / HIPAA 法律面）

## 案例回寫

Prisma 在 07 案例庫沒有直接 vendor-level 事件、但多個 supply chain / edge exposure case 是 Defender runtime + image scan 雙層的對照：

| 案例                                                                                                                                    | 跟 Prisma 的關係（對照啟示）                                                                                                                                                                               |
| --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)  | Defender agent runtime 可偵測 JNDI lookup 行為、補 SBOM / image scan 看不到的 *dynamic class load 在 runtime 才觸發* 缺口、跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) image scan 互補 |
| [3CX 2023 Desktop App Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/3cx-2023-desktopapp-supply-chain/) | Defender runtime 偵測異常 process spawn + outbound C2 callback、補 image-level scan 對 *已簽章但 runtime 行為異常* 的缺口、不能只靠 IoC                                                                    |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                  | runtime behavior anomaly（DNS beacon + dormant period）優於 IoC-only 規則、配合 image signing 雙層覆蓋、Defender + Code Security 在 build / runtime 雙閘                                                   |
| [Citrix Bleed 2023 Session Hijack](/backend/07-security-data-protection/red-team/cases/edge-exposure/citrix-bleed-2023-session-hijack/) | Defender host-layer 偵測異常 session 動作（不能阻擋上游 edge zero-day、但事後 forensic 跟 lateral movement containment 有用）、補 edge appliance 看不到的 host-side 軌跡                                   |

## 下一步路由

- 上游：[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)、[7.10 供應鏈與第三方信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- 平行：[Wiz](/backend/07-security-data-protection/vendors/wiz/)、[Lacework](/backend/07-security-data-protection/vendors/lacework/)、[CrowdStrike Falcon Cloud Security](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/)
- 下游：[Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)（Prisma alert forward）、[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)（CIEM remediation 落地）
- 跨類：[Trivy](/backend/07-security-data-protection/vendors/trivy/) / [Syft / Grype](/backend/07-security-data-protection/vendors/syft-grype/)（OSS image scan 互補）、[GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/) / [Snyk](/backend/07-security-data-protection/vendors/snyk/)（SCA 互補）
- 跨模組：[6.6 release gate](/backend/06-reliability/release-gate/)（Code Security PR scan）、[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（alert handoff）
- 官方：[Prisma Cloud Documentation](https://docs.prismacloud.io/)
