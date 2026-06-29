---
title: "Falco"
date: 2026-05-18
description: "CNCF Graduated runtime cloud-native threat detection、eBPF / kmod driver、Rule YAML + Falcosidekick + Talon、K8s container runtime 偵測為主"
weight: 24
tags: ["backend", "security", "vendor", "falco", "runtime-detection", "ebpf", "open-source"]
---

Falco 是 CNCF Graduated 的 runtime cloud-native threat detection engine、原 Sysdig 開源、Apache 2.0 license。它在 host / container 上用 eBPF（或 kernel module / userspace fallback）攔截 syscall、跟 Plugin 拉到的 audit log 串成同一條 event stream、丟給 Rule engine 比對 YAML rule、命中後 alert 到 stdout / Falcosidekick / SIEM。它跟商業 CNAPP runtime 模組（[Datadog CWS](/backend/07-security-data-protection/vendors/datadog-security/) / [Lacework Polygraph](/backend/07-security-data-protection/vendors/lacework/) / [Prisma Cloud Defender](/backend/07-security-data-protection/vendors/prisma-cloud/)）的差異在 *OSS rule-based vs SaaS ML-based + 平台廣度 + 自動 response 的工程責任歸屬*、偵測技術本身相近。

## 服務定位

Falco 的核心定位是 *K8s container runtime detection engine 的 OSS 基準*、不是 full CNAPP、也不是 inline enforcement。底層 Driver 分三層：*modern eBPF*（Linux 5.8+、預設）、*legacy kernel module (kmod)*（舊 kernel fallback）、*pdig userspace probe*（沒 root 或非 Linux）；Driver 抓 syscall 跟 K8s audit / cloud audit event、送進 Falco engine；engine 用 Sysdig filter syntax 比對 YAML rule、命中後吐 alert。Plugin 系統讓 Falco 看到非 syscall event（K8s audit log、Okta event、GitHub audit、AWS CloudTrail）— 變成 *general detection engine*、不只 host runtime。

跟 [Cilium Tetragon](/backend/07-security-data-protection/vendors/cilium-tetragon/) 比、Falco 走 *rule engine + alert-only*、Tetragon 走 *eBPF + 可 enforce kill action*；Falco 偵測為主、Tetragon 偵測 + 防護。跟 [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)（CWS）比、Datadog 是 SaaS observability 上加 runtime security view、ML-based behavioral baseline 內建、但 vendor lock + per-host 計費；Falco 是 OSS 自管、rule 完全可寫、但 ML baseline / threat intel / cross-source correlation 要自己接 SIEM。跟 [Lacework](/backend/07-security-data-protection/vendors/lacework/) Polygraph 比、Lacework 走 behavior graph 自動建 baseline、Falco 走 rule-explicit、邊界看得到也好 audit。

關鍵張力：*偵測 vs 防護* 跟 *rule-explicit vs ML-baseline* 是兩條取捨軸。Falco 預設只發 alert、要 inline kill / cordon 要靠 Falco Talon 或外接 SOAR；rule 完全可寫是優點也是負擔 — 自家 anti-pattern 要自己寫成 condition、不像 SaaS CNAPP 預設有 ML baseline。

## 本章目標

讀完本頁、讀者能判斷：

1. Falco 在 K8s runtime security stack 中承擔哪一段（syscall detection / audit log detection / alert forwarding）、哪些要外接（Talon / SIEM / SOAR）
2. Driver 選擇（modern eBPF / kmod / pdig）跟 kernel 環境 / 部署模型 的對應、選錯會 silent miss event
3. Rule 寫作的 ownership 設計（誰寫、誰 review、staging 怎麼觀察 false positive）
4. 何時用 Falco、何時改走 Tetragon（要 enforcement）或商業 CNAPP（要 ML baseline + 跨雲 posture）

## 最短判讀路徑

判斷 Falco deployment 是否健康、最少看四件事：

- **Driver 是否符合 kernel 環境**：modern eBPF on 5.8+ / kmod on legacy / pdig on serverless 或 non-root container；driver 跟 kernel 不對等於 silent miss，要看 `falco --version` 跟啟動 log 確認 driver 載入成功
- **Rule ownership 跟 lifecycle**：Falco 內建 rule（`falco_rules.yaml` / `k8s_audit_rules.yaml`）+ 自家 custom rule 是否走 Git PR review、staging tenant 跑幾小時觀察 false positive、再 promote production
- **Alert sink + downstream routing**：Falco 預設輸出 stdout / file / syslog、production 幾乎都接 Falcosidekick 做 fan-out（Slack / SIEM / S3 / Webhook），跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) 的接點明確
- **Response 是 alert-only 還是有 enforcement**：純 alert 走 [8 事故處理](/backend/08-incident-response/) routing；要自動 kill pod / cordon node 需 Falco Talon 或 SOAR、且 high-impact action 走 approval gate

四件事任一缺失、就是 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 邊界的待補項目。

## 日常操作與決策形狀

**Driver layer**：Falco 三種 driver — *modern eBPF*（CO-RE、Linux 5.8+、預設、不需 kernel header）、*legacy kernel module*（kmod、舊 kernel 唯一選、要 DKMS build）、*pdig*（userspace、ptrace-based、非 root container 或 macOS dev 環境用、效能差）。production K8s deployment 幾乎都走 modern eBPF、DaemonSet 部署到每個 node、kernel 版本不夠才走 kmod；不要混用 driver、否則 alert source 難對齊。

**Rule YAML 結構**：Falco rule 由 `condition`（Sysdig filter syntax、類 SQL where）、`output`（alert template、含 field interpolation）、`priority`（emergency / alert / critical / error / warning / notice / informational / debug）、`tags`（mitre / cis / NIST 對應）組成。`condition` 寫法跟 Linux syscall 緊耦合（`evt.type=execve`、`fd.name=/etc/passwd`、`proc.name=nc`）— rule engineer 要對 syscall 跟 process tree 熟悉。`macro` 跟 `list` 讓 rule 可重用（`macro: container_started` / `list: shell_binaries`）、production rule 庫應該 macro-first、不是每條 rule 重寫 condition。

**Plugin ecosystem**：Plugin 把 Falco 從 host syscall 擴張到任意 event source — *k8saudit plugin* 接 K8s API server audit log（看 RBAC change / Secret access）、*cloudtrail plugin* 接 AWS CloudTrail、*okta plugin* 接 Okta system log、*github plugin* 接 GitHub audit log。Plugin 讓 Falco 成為 *general detection engine*、不只 container runtime；但 plugin event source 跟 SIEM 重疊、要清楚 ownership — *Falco 做近 host 即時偵測、SIEM 做跨來源歷史 correlation*、別兩邊都跑同一條 rule。

**Falcosidekick + alert fan-out**：Falco engine 預設輸出 stdout / file / gRPC、production 接 Falcosidekick（DaemonSet 旁邊或單獨 Deployment）做 fan-out — 同一個 alert 同時 forward 到 Slack（SOC chat）、Splunk HEC / Elastic / Loki（SIEM 持久化）、S3（合規 archive）、Webhook（自家 dashboard）、Prometheus（metrics）。Sidekick 是 stateless forwarder、不做 dedup / aggregation、那層要在 SIEM 處理。

**Falco Talon + 自動 response**：Talon 是 response orchestrator、訂閱 Falcosidekick 的 webhook output、依照 rule action 自動執行 — kill pod、cordon node、加 NetworkPolicy、call webhook 通知 SOAR。Talon 把 *偵測 → 處置* 從手動 SOC playbook 變 declarative YAML、但 high-impact action（kill prod pod、cordon node）必須走 approval gate 或限制在 staging namespace、不能黑箱 fire-and-forget。對應 [Detection to Response Routing](/backend/07-security-data-protection/blue-team/detection-to-response-routing/) 的章節原則。

**Helm chart 部署 + GitOps**：Falco 官方 Helm chart 把 DaemonSet（Falco engine + driver）、Deployment（Falcosidekick）、ConfigMap（rule YAML）、ServiceAccount + RBAC 包成一組。生產 deployment 走 Argo CD / Flux 同步 Helm value、rule YAML 進 Git PR review、merge 觸發 staging tenant deploy、人工觀察 24-48hr false positive、再 promote production。Rule 直接改 ConfigMap、不走版控等於 detection drift、後續審計接不上。

**跟 SIEM / 8 事故處理整合**：Falco alert 經 Falcosidekick 進 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) 後、走跟其他 detection signal 同一條 correlation + triage 管線、不獨立 channel。Notable / high-priority alert 進 [8 事故處理](/backend/08-incident-response/) 的 IR queue、走 incident commander handoff。

## 核心取捨表

| 取捨維度       | Falco                                   | Cilium Tetragon                         | Datadog CWS                                | Lacework Polygraph                         |
| -------------- | --------------------------------------- | --------------------------------------- | ------------------------------------------ | ------------------------------------------ |
| License        | Apache 2.0 OSS                          | Apache 2.0 OSS                          | Commercial SaaS                            | Commercial SaaS                            |
| Detection 模型 | Rule-explicit（YAML + Sysdig filter）   | Rule-explicit（YAML + TracingPolicy）   | ML-based behavioral baseline + rule        | Behavior graph 自動 baseline               |
| Enforcement    | Alert-only（Talon 補 response）         | Inline enforce（kill / signal、可阻擋） | Inline enforce（Datadog Agent）            | Alert + workload baseline drift            |
| Driver         | modern eBPF / kmod / pdig               | eBPF only（cilium ecosystem）           | eBPF（Datadog Agent）                      | eBPF（Lacework Agent）                     |
| 涵蓋面         | Container + host + plugin (audit log)   | Container + host（cilium 整合 network） | Container + host + cloud + app             | Cloud + container + workload + IaC posture |
| Cross-source   | 靠 Plugin + Falcosidekick → SIEM        | 靠 Cilium Hubble + 外接 SIEM            | 內建（Datadog observability plane）        | 內建（Polygraph graph）                    |
| 學習曲線       | 中 — Sysdig filter + macro              | 中 — TracingPolicy + cilium 知識        | 緩 — 沿用 Datadog UI / Workload Security   | 緩 — SaaS console                          |
| 適合場景       | OSS-first、SIEM 已部署、rule 想完全可寫 | 要 inline enforcement、cilium CNI 已用  | Datadog 已用、cloud-native、預算允許       | CNAPP + posture 一站、跨雲                 |
| 退場成本       | 低 — rule 是 YAML、可移植 Sigma         | 中 — TracingPolicy 跟 cilium 綁定       | 高 — Workload Security rule 跟 platform 綁 | 高 — Polygraph data 跟 platform 綁         |

選 Falco 的核心訴求：*K8s container runtime detection、OSS + rule-customizable、SIEM 已部署、SOC 有 detection engineer 寫得了 Sysdig filter rule*。要 inline enforcement 直接走 Tetragon；要 ML baseline + 跨雲 posture + 不想自管 rule lifecycle 直接走 Datadog CWS / Lacework / [Wiz](/backend/07-security-data-protection/vendors/wiz/) + [CrowdStrike Falcon CS](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/)。

## 進階主題

**Custom rule 設計**：production rule 庫應該 *macro-first*、把可重用條件抽成 macro（`container_started` / `sensitive_mount` / `shell_in_container`）跟 list（`shell_binaries` / `sensitive_files`）；rule 引用 macro 而非重寫 condition、修改 macro 等於同時更新所有引用 rule。Rule 反例是 *single-event noisy rule*（看到一個 shell exec 就 alert）— production rule 應該 *context-bounded*（shell exec **in container** + parent **不在 allowlist** + image **非 trusted registry**）+ priority 階梯（生產 Notice、staging Warning、新規則先 Informational 觀察）。

**eBPF driver vs kmod 取捨**：modern eBPF 用 CO-RE（Compile Once, Run Everywhere）、不需 per-kernel build、運行時動態 attach；kmod 需要 DKMS 在 host build、跟 kernel version 強耦合、升級 kernel 要重 build。所有現代 Linux distro 預設都該走 modern eBPF；只有 RHEL 7 / 老 Ubuntu LTS（kernel < 5.8）才有理由用 kmod。pdig 給沒 root / 沒 eBPF 的環境（某些 serverless container、macOS dev）、效能差不適合 production。

**Falco Talon 自動 response 設計**：Talon 把「Falco alert → 自動處置」變 declarative — rule action 可以是 *kubernetes:terminate-pod*、*kubernetes:label-pod*、*kubernetes:cordon-node*、*aws:disable-iam-user*、*calico:add-networkpolicy*。production 用 Talon 的關鍵原則：*high-impact action 走 approval gate*（PagerDuty incident → human approve → execute）、*containment-first not deletion*（先 cordon + label、再人工決定是否 terminate）、*blast radius 限制*（只能影響特定 namespace / label selector）、*audit trail*（每個 action 進 Splunk + IR queue）。

**Plugin ecosystem 邊界**：Plugin 把 Falco 變 general detection engine、但要明確 plugin event 跟 SIEM 重疊處的 ownership。建議：*host syscall + container runtime → Falco rule*（即時 + low latency）、*K8s audit + cloud audit + IdP audit → 同時跑 Falco plugin（近即時 alert） + SIEM（歷史 correlation）*、*純跨來源 correlation（多 user 多 source 多時段）→ SIEM 為主*。別讓 Falco plugin 跟 SIEM rule 跑重複條件、會 double-alert 也 double-cost。

**Sigstore + SBOM 整合的位置**：Falco 不做 image scan / SBOM 驗證（那是 [Trivy](/backend/07-security-data-protection/vendors/trivy/) / [Syft & Grype](/backend/07-security-data-protection/vendors/syft-grype/) 的位置）、但 runtime detection 是 [Supply Chain Integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 縱深防禦的最後一層 — image scan 過、簽章驗證過、但 runtime 出現異常 syscall（log4shell 觸發 outbound LDAP、SolarWinds 合法簽章但行為異常）、Falco rule 是最後抓的點。

## 排錯與失敗快速判讀

- **Falco 啟動成功但完全沒 event**：driver 沒載入（modern eBPF 在舊 kernel fallback 失敗）— 看啟動 log 確認 `driver loaded successfully`、`falco --version` 對 driver 版本、舊 kernel 改 kmod
- **大量 false positive 淹沒 SOC**：rule 寫太寬（`shell in container` 但合法 debug shell 也 trigger）— staging tenant 跑 48hr 統計 FP、加 exception list 或改 macro 排除已知合法 source、新 rule 先 Informational priority 觀察
- **Alert 沒進 SIEM**：Falcosidekick 沒接、或 output channel 設錯 — 確認 Falcosidekick Deployment up、output webhook 對、SIEM HEC token 沒過期；Falco engine 本身的 stdout / file output 仍會留、不會 silent miss
- **Rule update 後 detection drift**：直接改 ConfigMap、沒走 Git PR + staging 觀察 — 強制 GitOps（Argo CD / Flux）、ConfigMap immutable、rule change 必須走 PR review + staging promote
- **Plugin event lag / 漏抓**：plugin polling cloud audit log（CloudTrail / Okta）的 latency 跟 API rate limit、不是即時 — 純即時偵測別靠 plugin、改靠 SIEM streaming ingest；plugin 適合補 syscall 看不到的層
- **Talon 自動 response 誤殺 prod**：rule action 直接 kill pod、沒 approval gate — 高影響 action 拆成兩步（先 label + cordon、再人工 approve terminate）、blast radius 限 namespace / label selector、audit trail 全進 SIEM
- **eBPF driver 跟 kernel 升級不對齊**：node kernel 升級後 modern eBPF 仍 CO-RE 自動適配、但 Falco 版本太舊不支援新 syscall — Falco engine 跟著定期升級、別 pin 在兩年前的 version

## 何時改走其他服務

| 需求形狀                       | 改走                                                                                                                                                                                                                                                       |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 要 inline kill / enforcement   | [Cilium Tetragon](/backend/07-security-data-protection/vendors/cilium-tetragon/)                                                                                                                                                                           |
| ML behavioral baseline + 跨雲  | [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)、[Lacework](/backend/07-security-data-protection/vendors/lacework/)、[Wiz](/backend/07-security-data-protection/vendors/wiz/)                                           |
| Full CNAPP + posture + runtime | [Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/)、[CrowdStrike Falcon CS](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/)                                                                                   |
| Image scan / SBOM / SCA        | [Trivy](/backend/07-security-data-protection/vendors/trivy/)、[Syft & Grype](/backend/07-security-data-protection/vendors/syft-grype/)、[Snyk](/backend/07-security-data-protection/vendors/snyk/)                                                         |
| Cross-source SIEM correlation  | [Splunk](/backend/07-security-data-protection/vendors/splunk/)、[Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)、[Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/) |
| Incident routing               | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                                                                                                                                                                           |

## 不在本頁內的主題

- Sysdig filter syntax 完整 reference、syscall field 細目
- Falco source code 內部架構（libsinsp / libscap）
- Sysdig Secure（Falco 的商業版、Sysdig Inc. 維護、含 ML baseline + cloud posture）的功能對照細節
- Container image scan / SBOM 驗證（屬 [Trivy](/backend/07-security-data-protection/vendors/trivy/) / [Syft & Grype](/backend/07-security-data-protection/vendors/syft-grype/) 的位置）
- Kubernetes RBAC / Pod Security Standards / NetworkPolicy 的設計（屬 K8s 平台層、不在 runtime detection 範圍）

## 案例回寫

Falco 在 07 案例庫沒有直接 vendor-level 事件、但多個 runtime / supply chain case 都是 Falco rule 第一線該抓的場景：

| 案例                                                                                                                                      | 跟 Falco 的關係（對照啟示）                                                                                                                                 |
| ----------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [3CX 2023 Desktop App Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/3cx-2023-desktopapp-supply-chain/)   | Falco rule 偵測 desktop app process spawn 異常子程序 + outbound callback、補簽章驗證之外的 runtime 行為層                                                   |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)    | Falco rule 偵測 JNDI lookup 觸發的 outbound LDAP / DNS、補 [Trivy](/backend/07-security-data-protection/vendors/trivy/) image scan 之外的 runtime detection |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                    | 合法簽章 binary 但 runtime 行為異常（process tree / outbound C2 / 異常 file access）、Falco rule + Talon containment 是最後一層                             |
| [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/) | 對照啟示：Falco 主場是 host / container runtime、cloud-native data warehouse 行為偵測要走 SIEM + 平台層 audit、非 Falco 範圍                                |
| [Detection Engineering Lifecycle (section)](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)              | Falco rule + macro + list 走 propose → staging tune → promote → review 的工程 lifecycle、不是 ConfigMap 直改                                                |
| [Alert Fatigue and Signal Quality (section)](/backend/07-security-data-protection/blue-team/alert-fatigue-and-signal-quality/)            | Falco rule priority 階梯（新規則先 Informational、staging 觀察 48hr、再 promote Warning / Critical）是 alert fatigue 的工程化解法                           |

## 下一步路由

- 上游：[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)、[Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)、[Detection to Response Routing](/backend/07-security-data-protection/blue-team/detection-to-response-routing/)
- 平行：[Cilium Tetragon](/backend/07-security-data-protection/vendors/cilium-tetragon/)、[Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)、[Lacework](/backend/07-security-data-protection/vendors/lacework/)、[Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/)
- 下游：[Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)（Falco alert 進 SIEM 做 cross-source correlation）
- 跨類：[Trivy](/backend/07-security-data-protection/vendors/trivy/) / [Syft & Grype](/backend/07-security-data-protection/vendors/syft-grype/)（image scan + SBOM、跟 runtime detection 構成 supply chain 縱深）、[Wiz](/backend/07-security-data-protection/vendors/wiz/) / [CrowdStrike Falcon CS](/backend/07-security-data-protection/vendors/crowdstrike-falcon-cs/)（商業 CNAPP runtime 對照）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Falco notable alert → IR routing）、[Supply Chain Integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)（artifact trust 跟 runtime detection 的縱深關係）
- 官方：[Falco Documentation](https://falco.org/docs/)、[Falco Rules Repository](https://github.com/falcosecurity/rules)
