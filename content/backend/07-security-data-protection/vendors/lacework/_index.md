---
title: "Lacework"
date: 2026-05-18
description: "CNAPP 走 Polygraph ML behavioral baseline 路線、2024 跟 Fortinet 合併成 FortiCNAPP、自動學 normal、anomaly 自動 alert"
weight: 18
tags: ["backend", "security", "vendor", "lacework", "cnapp", "cspm", "ml-detection"]
---

Lacework 是 CNAPP（Cloud-Native Application Protection Platform）走 *Polygraph ML behavioral baseline* 路線的代表廠商、2024 年跟 Fortinet 合併、新品牌叫 *Fortinet Lacework FortiCNAPP*、但 Lacework 名稱與獨立產品線仍在運作。它跟 [Wiz](/backend/07-security-data-protection/vendors/wiz/) / [Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/) / [CrowdStrike Falcon Cloud Security](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/) 的差異不在 *覆蓋面*、而在 *偵測設計哲學* — Lacework 的核心競爭力是 Polygraph 自動從 log + process + network + cloud API call 學 baseline、anomaly 自動觸發、不需 SOC 手寫 detection rule。

## 服務定位

Lacework 的核心定位是 *Polygraph 驅動的 CNAPP*、以 ML 自動學習正常行為作為偵測基礎。產品線涵蓋四個能力面：*CSPM*（Cloud Security Posture Management、misconfiguration 與合規 scan）、*CWPP*（Cloud Workload Protection Platform、host + container runtime 防護）、*Code Security*（IaC scan、container image scan、SAST baseline）、以及貫穿全平台的 *Polygraph behavioral baseline engine*。

跟 [Wiz](/backend/07-security-data-protection/vendors/wiz/) 比、設計哲學是相反的：Wiz 走 *Security Graph + Toxic Combination*（你顯式定義「EC2 + RCE + IMDS v1 + cross-account role」是 toxic、graph 找匹配 path）、Lacework 走 *Polygraph implicit baseline*（你不定義、ML 從 30 天歷史學 normal、偏離就 alert）。兩種都是 graph、但一個是 rule-driven graph、一個是 behavior-learned graph。跟 [Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/) 比、Prisma 是 *多模組 agent + agentless 寬覆蓋*、Lacework 主打 Polygraph 為單一核心引擎、不靠堆模組廣度競爭。跟 [CrowdStrike Falcon CS](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/) 比、Falcon CS 是 *endpoint EDR 延伸到 cloud*、Lacework 從第一天就為 cloud-native designed、沒 endpoint EDR 包袱。

關鍵張力：*implicit behavioral baseline* ↔ *explicit auditable rule* 是 Lacework 客戶最大的取捨。Polygraph 內部用 ML 學行為、好處是 zero rule maintenance、自動覆蓋未知 attack pattern；代價是內部邏輯不透明、false positive / false negative 都不容易 debug、強合規場景需要 explicit rule 可審計時會卡住。

## 本章目標

讀完本頁、讀者能判斷：

1. Lacework 在 cloud security stack 中承擔哪段（CSPM / CWPP / Code Security / behavioral detection）、哪些要外接（[Splunk](/backend/07-security-data-protection/vendors/splunk/) 等 SIEM 接 alert、[8 事故處理](/backend/08-incident-response/) 接 IR routing）
2. Polygraph ML baseline 的 ownership 設計（誰調 anomaly threshold、false positive 由誰判讀、ML model retraining cadence 誰負責）
3. *implicit baseline* vs *explicit rule* 的取捨何時偏 Lacework、何時要補 Wiz / Prisma 的 explicit rule layer
4. 何時用 Lacework、何時走 Wiz / Prisma Cloud / Falcon CS

## 最短判讀路徑

判斷 Lacework deployment 是否健康、最少看四件事：

- **Polygraph baseline 覆蓋面**：哪些 cloud account / workload / container 進了 Polygraph 學習、baseline window 多長（預設 30 天）、新 workload 進來幾天才視為 baseline 成熟、未覆蓋的 workload 是否走 fallback rule
- **Anomaly tuning ownership**：誰看 Polygraph alert、false positive 由誰標記、標記後怎麼回饋 model、有沒有 *alert backlog grooming* lifecycle（不是黑箱 fire-and-forget）
- **CSPM 跟合規 mapping**：CIS / PCI / SOC 2 / HIPAA framework 哪些開、misconfiguration finding 走 ticket workflow（誰修、deadline）、Compliance report 多久 export 一次給 audit team
- **跟 SIEM / SOAR handoff**：Polygraph alert 是否同步進 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) 給 SOC、是否跟 [8 incident response](/backend/08-incident-response/) playbook 對接、high severity 是否觸發 SOAR

四件事任一缺失、就是 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 的待補項目。

## 日常操作與決策形狀

**Polygraph behavioral baseline**：Lacework 的 first-class concept、從 cloud API call（CloudTrail / Audit Log）+ host process tree + container syscall + network connection 四種 source 同時學習、用 time-series graph 表達「正常情況下 user X 在 workload Y 上會 spawn process Z、連 destination W」。anomaly 是 graph 上不在 baseline 中的 edge、自動 trigger alert。baseline window 預設 30 天、新 workload 進來時用同類 workload 的 baseline 過渡、避免 cold start 全部 alert。

**CSPM（misconfiguration + compliance）**：agentless 從 cloud API 拉 resource 設定、對照 CIS Benchmark / PCI / SOC 2 / HIPAA / CSA CCM 等 framework 跑 rule、出 finding。這部分是 *explicit rule*、不靠 Polygraph、跟 Wiz / Prisma 的 CSPM 能力同等級。Compliance report 可 schedule export 給 audit team。

**CWPP（host + container runtime）**：兩種模式 — *agentless*（從 cloud API + snapshot 掃 vulnerability + misconfiguration、低 overhead 但無 runtime signal）、*agent-based*（Lacework agent on host / DaemonSet on K8s、提供 process tree + syscall + file integrity monitoring 給 Polygraph）。production runtime detection 必須 agent、不然 Polygraph 沒 process / syscall 資料源。

**Code Security（IaC + container image）**：Terraform / CloudFormation / Helm chart 掃 misconfiguration、container image 掃 CVE + secret + SBOM、跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/) 同層級。整合 GitHub / GitLab PR check、release gate 前 block 高風險 IaC。

**Compliance reporting**：CSPM finding 自動 map 到 framework（CIS AWS / PCI DSS / SOC 2 等）、定期 export PDF / CSV 給 audit team、不需 SOC 手工整理。跨 cloud 帳號 aggregate view 對 multi-account 治理有用。

**跟 SIEM 整合**：Polygraph alert 走 webhook / S3 export / Splunk Add-on 進 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)、做 cross-source correlation。Lacework 不取代 SIEM、是 cloud-native detection 的 *upstream signal source*。

**計費模型**：按 workload count（vCPU 數 / container 數 / cloud account 數）+ 啟用模組。enterprise contract 為主、不公開 list price。跟 Wiz / Prisma 同模型、預算敏感場景需試算。

## 核心取捨表

| 取捨維度       | Lacework                                          | Wiz                                              | Prisma Cloud                     | CrowdStrike Falcon CS                          |
| -------------- | ------------------------------------------------- | ------------------------------------------------ | -------------------------------- | ---------------------------------------------- |
| 偵測設計哲學   | Polygraph ML implicit baseline                    | Security Graph + 顯式 Toxic Combination          | 多模組 rule + ML 混合            | EDR 延伸到 cloud、process-centric              |
| 主要訴求       | zero rule maintenance、自動覆蓋未知 attack        | 顯式 rule 可審計、cross-asset 關聯路徑清楚       | 寬覆蓋、agent + agentless 混合   | endpoint + cloud 同 console、process tree 一致 |
| Runtime 偵測   | agent (Polygraph syscall + process tree)          | agent (Runtime Sensor、後加)                     | agent (Defender)                 | 強 — 沿用 Falcon EDR agent                     |
| Agentless scan | 強 — CSPM + vulnerability snapshot                | 強 — agentless 為 design 起點                    | 強 — 雙模式並重                  | 中 — 為 Falcon agent 補位                      |
| 合規可審計     | 中 — Polygraph 黑箱、CSPM 部分清楚                | 強 — 顯式 rule、規則邏輯可審查                   | 強 — rule-based、模組化清楚      | 中                                             |
| 跟 SIEM 整合   | webhook / Splunk Add-on / S3                      | webhook / 多家 SIEM connector                    | 多家 SIEM connector              | Falcon 自家 NG-SIEM 為主、外接次要             |
| 適合場景       | cloud-native + 信任 ML、不想自寫 detection rule   | 多雲 + 要顯式 rule 治理、需 cross-asset 攻擊路徑 | Palo Alto-heavy 環境、寬覆蓋優先 | CrowdStrike-heavy 環境、endpoint + cloud 統一  |
| 不適合場景     | 強合規要 explicit rule 可審計、SOC 要 rule 客製化 | 不想自己寫 rule、想 ML 自動覆蓋                  | 預算敏感（多模組計費容易膨脹）   | 沒在用 Falcon EDR、純 cloud-native             |
| Fortinet 整合  | 強（2024+ FortiCNAPP、跟 NGFW / FortiSOAR 整合）  | 無 Fortinet 直接整合                             | 無 Fortinet 直接整合             | 無 Fortinet 直接整合                           |

選 Lacework 的核心訴求：*cloud-native + 信任 ML behavioral baseline + 不想養 detection engineering team 寫 rule* + 願意接受 Polygraph 是相對黑箱、false positive 要由 ML retraining 而非 rule edit 解決。強合規要 explicit rule 可審計、或 SOC 要深度 rule 客製化、走 Wiz / Prisma 更合適。

## 進階主題

**Polygraph internals**：Polygraph 不是單一 ML model、是 time-series behavioral graph + 多個 detection algorithm 組合。node 是 entity（user / workload / process / network endpoint）、edge 是 observed interaction、edge 上掛 frequency + temporal pattern。anomaly detection 用 unsupervised learning（clustering + outlier detection）找 baseline 外的 edge。優點是 *zero-day attack pattern 不需事先定義也可能偵測到*（行為偏離即可）、缺點是 detection 為何 trigger / 為何沒 trigger 都不易解釋、tuning 不是改 rule、是調整 baseline window 或標記 false positive 回饋 model。

**Fortinet FortiCNAPP 整合（2024+）**：Fortinet 收購後加速跟 *Fortinet NGFW*（network log 進 Polygraph 當 source）、*FortiSOAR*（Lacework alert 自動觸發 firewall block / endpoint isolation playbook）、*FortiSandbox*（suspicious file 進 sandbox 再回饋 baseline）整合。Fortinet-heavy 環境吃整合紅利、非 Fortinet 環境 Polygraph 跟原 connector 仍獨立運作。

**Anomaly tuning lifecycle**：Polygraph alert 出來不是終點、要走 *triage → label false positive → ML model retraining* lifecycle。實務上 SOC 看 alert 標 *true positive / false positive / benign anomaly*（合法但意外）、Lacework 後台用 label 重訓 model、下一個 baseline cycle 調整。組織要決定 *誰負責 label*（SOC analyst / detection engineer）、*backlog grooming cadence*（每週 / 每月）、*retraining cycle*（自動 / 手動觸發）。沒 lifecycle 就是「alert 看一陣子放著」、Polygraph 退化成噪音源。

**跨 SIEM webhook / SOAR 整合**：alert 推 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) 後、SOC 可用 SIEM correlation 補 cross-source（例如 Polygraph anomaly + Okta MFA fail + GitHub clone spike）、再進 SOAR playbook 自動 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) rotate / [Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) block。Lacework 是 *detective layer*、SIEM 是 *correlation + orchestration layer*。

## 排錯與失敗快速判讀

- **新 workload 進來大量 alert（cold start）**：baseline 還沒建好、ML 把正常當異常 — 用同類 workload baseline 過渡、給 7-14 天 warm-up 再 enforce alert
- **Polygraph alert 看不懂為何 trigger**：ML 黑箱本質、不像 explicit rule 可指 line — 看 alert 帶的 *involved entities + observed deviation*、跨 entity 對 baseline 看差異、必要時補 Wiz / Prisma explicit rule 在強合規場景
- **False positive 持續多但 model 沒進步**：label lifecycle 沒跑、analyst 把 alert dismiss 沒打 label — 強制走 *true positive / false positive / benign anomaly* triage、不能直接 close
- **Agent 沒裝 / 裝不到的 workload**：legacy host / serverless / edge node 沒 agent、Polygraph 只有 cloud API source 沒 process / syscall — 接受 agentless-only 覆蓋面、不要假設 Polygraph 全 stack 看得到
- **CSPM finding backlog 爆炸**：framework 一次開全、misconfiguration 數千條沒人修 — 分批 enable framework、按 severity + asset criticality 排優先級、走 ticket workflow + deadline
- **Compliance audit 要 explicit rule 可審查**：Polygraph 內部邏輯不能交給 auditor — CSPM 部分可以審（是 explicit rule）、Polygraph 部分要補 detection engineering 文件 + label history 證明 ML 有治理
- **Alert 進 SIEM 後沒 correlation**：Lacework alert 跟 IdP / WAF / cloud control plane log 沒在 [Splunk](/backend/07-security-data-protection/vendors/splunk/) 跨 source 串 — 寫 correlation rule 把 Polygraph anomaly 當 *one signal*、不是當 final verdict

## 何時改走其他服務

| 需求形狀                          | 改走                                                                                                                                                                    |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 顯式 rule + 多雲 cross-asset 路徑 | [Wiz](/backend/07-security-data-protection/vendors/wiz/)                                                                                                                |
| 寬覆蓋 + Palo Alto-heavy          | [Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/)                                                                                              |
| Endpoint EDR + cloud 統一         | [CrowdStrike Falcon Cloud Security](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/)                                                                |
| SIEM 主導、CNAPP signal 進 SOC    | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/) |
| Container image / IaC scan 為主   | [Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/)                                               |
| 資料分類 / DLP                    | [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)           |
| Incident routing                  | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                                                                                        |

## 不在本頁內的主題

- Polygraph ML 演算法的學術細節（unsupervised clustering / graph anomaly detection 具體方法）
- FortiCNAPP 跟 Fortinet 其他產品（FortiGate / FortiAnalyzer / FortiSIEM）的 deep integration 設定
- Lacework Labs threat research 報告的逐篇解讀
- 完整 CIS / PCI / SOC 2 framework 對應的 rule 清單
- Container runtime 防護的 OS-level 細節（cgroup / namespace / seccomp）

## 案例回寫

Lacework 在 07 案例庫沒有直接 vendor-level 事件、但多個 case 是 Polygraph behavioral baseline 的對照啟示：

| 案例                                                                                                                                      | 跟 Lacework 的關係（對照啟示）                                                                                                             |
| ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                    | Polygraph 在 SolarWinds 期間可從 Orion 程序的 DNS callback 行為偏離 baseline 偵測、不靠 IoC list — Lacework marketing 強打的 zero-day 案例 |
| [3CX 2023 Desktop App Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/3cx-2023-desktopapp-supply-chain/)   | Desktop app process spawn 異常 + unusual outbound 是 Polygraph baseline 可抓的 pattern、補簽章驗證通過後的 runtime 偵測窗口                |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)    | Polygraph 偵測 JNDI lookup 後的 outbound LDAP 連線異常、補 CVE scanner agent rollout 之前的偵測窗口、不依賴事先 CVE 公開                   |
| [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/) | 對照啟示：Polygraph 對 cloud API call pattern 異常（短時間大量 GetObject / 跨 schema query）可 baseline-based 偵測、不需事先寫 query rule  |
| [Detection Engineering Lifecycle (section)](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)              | Polygraph 把 detection lifecycle 從「寫 rule → tune → review」改成「baseline → label false positive → retrain」、流程不同但治理責任沒消失  |
| [Alert Fatigue and Signal Quality (section)](/backend/07-security-data-protection/blue-team/alert-fatigue-and-signal-quality/)            | Polygraph 自動 baseline 不等於免 alert fatigue — label lifecycle 跟 retraining cadence 沒做、false positive 一樣會淹 SOC                   |

## 下一步路由

- 上游：[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)、[Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)
- 平行：[Wiz](/backend/07-security-data-protection/vendors/wiz/)、[Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/)、[CrowdStrike Falcon Cloud Security](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/)
- 下游：[Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)（SIEM 接 Polygraph alert）
- 跨類：[Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/)（Code Security 重疊、CI 階段優先級）、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（SOAR playbook 拉 API rotate）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Polygraph alert → IR routing）、[4 observability](/backend/04-observability/)（log pipeline 共用）
- 官方：[Lacework Documentation](https://docs.lacework.net/) / [Fortinet Lacework FortiCNAPP](https://www.fortinet.com/products/forticnapp)
