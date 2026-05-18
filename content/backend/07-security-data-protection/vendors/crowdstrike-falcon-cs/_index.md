---
title: "CrowdStrike Falcon Cloud Security"
date: 2026-05-18
description: "CrowdStrike 在 Falcon endpoint EDR 之上的 CNAPP、agent 統一跨 endpoint + workload + container、CrowdStrike Intelligence 內建"
weight: 19
tags: ["backend", "security", "vendor", "crowdstrike-falcon-cs", "cnapp", "cspm", "edr"]
---

CrowdStrike Falcon Cloud Security 是 CrowdStrike 在 Falcon endpoint EDR 平台之上擴張出來的 CNAPP（Cloud-Native Application Protection Platform）產品線。它的核心邏輯是把已經跑在 endpoint 上的 *Falcon agent* 同時拿來收 cloud workload / container / Kubernetes node 的 telemetry、再把 CrowdStrike Intelligence 的 threat actor profile 直接餵進 detection rule。對已是 CrowdStrike endpoint 客戶來說、邊際 onboarding cost 接近 0；對非 CrowdStrike 環境、選它的訴求應該是 *threat intel + EDR 同 console* 而不是 CSPM 本身。

## 服務定位

Falcon Cloud Security 的定位是 *agent-first 的 CNAPP*、設計重心在「endpoint EDR agent 順便收 cloud workload 訊號」這條路徑、agentless CSPM 是補位、不是主軸。產品線靠多次收購整合：*Bionic*（2023 收購、現為 Falcon ASPM、application security posture management）負責 application architecture + runtime risk map；*Flow Security*（2024 收購、現為 Falcon Data Protection / DSPM）負責 sensitive data 發現與 access path；endpoint / workload / container runtime 偵測由 Falcon agent 自家補。

跟 [Wiz](/backend/07-security-data-protection/vendors/wiz/) 比、Falcon CS 走 *agent-first + EDR 整合*、Wiz 走 *agentless-first + cloud workload graph*。已部署 Falcon endpoint 的客戶上 Falcon CS 邊際成本 0；純 cloud-native 沒 endpoint workload 的環境、Falcon 的 agent 紅利不存在、Wiz 更快出價值。跟 [Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/) 比、兩者都走 agent + agentless 雙軌、Prisma 強項是 *compliance pack 跟 IaC scanning 模板*、Falcon 強項是 *CrowdStrike Intelligence threat actor profile + Counter Adversary Operations 提供的 hunting 服務*。跟 Lacework 比、Lacework 走 *behavioral baseline / anomaly detection*、Falcon 走 *signature + threat intel*、兩種偵測哲學。

關鍵張力：*agent 是 single point of compromise* 是 Falcon agent-first 路線的長期信任成本。2024-07 Falcon sensor 推 bad content update 導致全球 Windows host BSOD 的事件、把 *kernel-level agent 一改全炸* 的風險具象化、對 agent-first vendor 是長期教訓。選 Falcon CS 等於買 agent 在 host kernel 的存取權、要把 *agent 自身的供應鏈* 當成風險來源納入評估。

## 本章目標

讀完本頁、讀者能判斷：

1. Falcon Cloud Security 在 cloud security stack 中承擔哪一段（CSPM / CWPP / CIEM / ASPM / DSPM）、哪些靠 Falcon agent、哪些靠 agentless connector
2. 已有 CrowdStrike endpoint 跟沒有 CrowdStrike endpoint 兩種起點下、Falcon CS 的判讀是否一樣
3. CrowdStrike Intelligence 跟 Counter Adversary Operations 在 detection lifecycle 的位置
4. 何時用 Falcon CS、何時走 [Wiz](/backend/07-security-data-protection/vendors/wiz/) / [Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/) / Lacework 的取捨

## 最短判讀路徑

判斷 Falcon Cloud Security deployment 是否健康、最少看四件事：

- **Agent coverage 跟版本治理**：哪些 host / workload / container 跑 Falcon agent、是否跨 endpoint + cloud workload + Kubernetes node 一致、agent version 跟 sensor content channel 是否走 staging tenant + canary rollout（2024-07 incident 後的硬性要求）
- **Agentless connector 覆蓋**：CSPM 連到哪些 cloud account（AWS / GCP / Azure / OCI）、CIEM 是否拉 IAM identity graph、ASPM 連到哪些 application code repo
- **Threat intel 是否接進 detection lifecycle**：CrowdStrike Intelligence 的 IoC / threat actor TTP 是否餵進 Falcon detection rule、Counter Adversary Operations（MDR / threat hunting 服務）是否訂閱
- **跟 Falcon EDR 同 console / IR handoff**：cloud finding 跟 endpoint finding 是否在同一個 Incident view、SOC team 跟 cloud team 的 routing 是否定義、跟 [8 incident response](/backend/08-incident-response/) 是否對齊

四件事任一缺失、就是 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 邊界的待補項目。

## 日常操作與決策形狀

**Falcon agent 統一**：endpoint EDR 用的 Falcon sensor 同時收 cloud workload 上的 process / file / network telemetry、不需要再裝第二支 agent。對已用 Falcon endpoint 的組織意義最大 — VM / container host 上裝 Falcon 就同時是 EDR + CWPP + container runtime detection。新環境要評估 *agent 的 kernel 存取權* 是否可接受、container 內是否能或需要部署 agent（Falcon Container Sensor 走 sidecar / DaemonSet）。

**CSPM**：agentless 連 cloud account（AWS / GCP / Azure / OCI）、掃 misconfiguration（public S3 / over-privileged role / unencrypted disk）、對照 CIS Benchmark / NIST / PCI 模板。CSPM 是 *配置面* 訊號、補 agent 看不到的 cloud control plane 行為（例如 IAM policy change、S3 bucket policy 改變）。

**CWPP — workload + container + Kubernetes**：Falcon agent 在 VM host / container host / Kubernetes node 上做 runtime detection、看 process spawn、file integrity、network connection、container escape attempt。比 agentless snapshot scan 強的是 *runtime behavior*（看到實際發生的 process tree），比 Wiz agentless 弱的是 *初始 coverage 速度*（要先部署 agent）。

**CIEM**：把 cloud IAM identity 跟 access 畫成 graph、識別 over-privileged role / unused permission / cross-account trust risk。跟 [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) Access Analyzer / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) Policy Intelligence 是補位、不是替代 — CIEM 給的是 *跨雲 + 跨 identity provider* 的 risk view。

**ASPM（前 Bionic）**：application security posture management、把 application architecture（service graph / data flow / external dependency / vulnerability）畫成 map、識別哪個 vulnerability 真的可達 production attack surface。跟 Wiz Code / Snyk 的訴求重疊、但 Bionic 強項是 *runtime + architecture* 而不是 pure SAST/SCA。導入需要拉 application telemetry、不是裝完就有結果。

**DSPM（前 Flow Security）**：data security posture management、掃 cloud storage / database / SaaS 裡的 sensitive data 位置、誰能存取、access path 是什麼。跟 [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/) 不同層 — DSPM 是 *posture 層*（who can access what）、DLP 是 *runtime 層*（actual data egress event）、兩者互補。

**CrowdStrike Intelligence 整合**：CrowdStrike Intelligence 是 CrowdStrike 自家的 threat intel team、定期發 threat actor profile（COZY BEAR / FANCY BEAR / Scattered Spider 等命名來自 CrowdStrike）、IoC、TTP。Falcon CS detection rule 直接吃這層、不用 SOC team 自己訂閱外部 threat feed。這是 Falcon CS 跟 *純 CNAPP 競品*（Wiz / Prisma）最大差異 — 競品要再買 Mandiant / Recorded Future 才能補。

**Charlotte AI**：CrowdStrike 的 LLM-assisted investigation 介面、SOC analyst 用自然語言問 incident（「過去 24hr 有哪些 process 是 first-seen across fleet」）、Charlotte 翻成 Falcon query 跑。屬 SOC productivity 補位、不是 detection logic 本身。

**跟 Falcon LogScale / Identity Protection 同 plane**：完整 CrowdStrike stack 客戶可以把 Falcon LogScale（前 Humio 收購、SIEM）+ Falcon Identity Protection（identity threat detection）跟 Falcon CS 整合在同一個 console。Single pane of glass 強、但 vendor lock-in 也最深、退場成本是業界最高。

## 核心取捨表

| 取捨維度          | CrowdStrike Falcon CS                               | Wiz                                              | Prisma Cloud                                | Lacework                                  |
| ----------------- | --------------------------------------------------- | ------------------------------------------------ | ------------------------------------------- | ----------------------------------------- |
| Agent 策略        | Agent-first（Falcon sensor）+ agentless 補位        | Agentless-first（snapshot scan）+ runtime sensor | Agent + agentless 雙軌（Defender agent）    | Agent-based（Lacework agent + Polygraph） |
| 強項              | EDR 整合、threat intel、Counter Adversary Ops       | Cloud workload graph、快速 onboarding、無 agent  | Compliance pack、IaC scanning、廣覆蓋       | Behavioral baseline、anomaly detection    |
| Threat intel      | CrowdStrike Intelligence 內建                       | 外部 feed integration                            | Unit 42 threat intel 內建                   | 外部 feed integration                     |
| ASPM / app layer  | Falcon ASPM（前 Bionic、runtime + architecture）    | Wiz Code（SAST / SCA / IaC）                     | Prisma Code Security（前 Bridgecrew）       | 有限                                      |
| DSPM              | Falcon Data Protection（前 Flow Security）          | Wiz DSPM                                         | Data Security Posture Management            | 有限                                      |
| MDR / hunting     | Counter Adversary Operations（業界先驅）            | 無 first-party MDR                               | Cortex MDR（Palo Alto）                     | 有限                                      |
| 跟 EDR 同 console | 內建（Falcon EDR / Identity Protection / LogScale） | 需外接                                           | Cortex XDR（同 Palo Alto stack）            | 需外接                                    |
| 適合場景          | 已用 Falcon endpoint、看重 threat intel + MDR       | Cloud-native、無 endpoint workload、要快         | Palo Alto stack 客戶、compliance-heavy 產業 | 中等規模、behavioral detection 為主       |
| 退場成本          | 最高（agent + console + threat intel + MDR 綁定）   | 中（agentless 退出較快）                         | 高（Palo Alto stack 整合深）                | 中                                        |

選 Falcon CS 的核心訴求：*已是 CrowdStrike endpoint 客戶 / SOC team 已熟 Falcon console + 看重 CrowdStrike Intelligence threat intel + 願意接受 agent-first 的供應鏈風險*。純 cloud-only 沒 endpoint workload、agent 紅利不存在、走 [Wiz](/backend/07-security-data-protection/vendors/wiz/) 更划算。非 CrowdStrike 環境想要 compliance + IaC、走 [Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/)。

## 進階主題

**Counter Adversary Operations（MDR + threat hunting）**：CrowdStrike 的 managed detection and response 服務、24x7 SOC team + threat hunter 主動掃客戶環境裡的 adversary 跡象。跟一般 MDR 不同的是、它直接接 CrowdStrike Intelligence 的 threat actor profile、看到 TTP 匹配就主動 hunt 而不是等 alert。對 SOC team 規模有限但要面對 nation-state actor 的組織、是補 SOC capability 的快路。

**CrowdStrike Intelligence threat actor profile**：CrowdStrike 把 threat actor 用命名規則（BEAR = Russian state、PANDA = Chinese state、KITTEN = Iranian state、SPIDER = eCrime）+ 編號管理、每個 actor 有 TTP、tooling、target sector 的 profile。Detection rule 不再只看 IoC（hash / IP）而是看 *actor 的 behavioral pattern*、IoC 變了也能抓。配對 [Microsoft Storm-0558 Signing Key Chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) 的 nation-state actor lesson。

**Falcon LogScale 整合**：Falcon LogScale（前 Humio）是 CrowdStrike 自家的 SIEM、可以把 Falcon agent telemetry + cloud log + 自家 app log 全收。跟 [Splunk](/backend/07-security-data-protection/vendors/splunk/) 比、LogScale 強在 *跟 Falcon detection 同 plane*、計費也不是 ingestion-based；弱在 *detection content 跟 ecosystem 比 Splunk 淺*。

**Charlotte AI + LLM-assisted investigation**：SOC analyst triage 時間長是普遍痛點、Charlotte AI 用 LLM 把自然語言問題翻成 Falcon query、補出 incident timeline summary。屬 SOC productivity 工具、不取代 detection rule、也不取代 analyst judgement。

**Falcon Identity Protection 補位**：identity-layer threat detection（pass-the-hash、Kerberoasting、AD enumeration）、跟 [Okta](/backend/07-security-data-protection/vendors/okta/) ITDR 訊號互補。完整 stack 客戶可把 endpoint + cloud + identity 三層 telemetry 一起 correlate。

## 排錯與失敗快速判讀

- **Agent rollout 一改全炸**：sensor content channel 沒有 staging tenant、prod 直接吃 vendor push 的 update — 2024-07 incident 後 CrowdStrike 推 Sensor Update Policy 允許客戶設 canary ring、所有 prod 都該開、不開等於把 fleet 命交給 vendor QA
- **Cloud workload coverage 不全 / 偵測盲點**：只有部分 VM 部署 Falcon agent、container / Kubernetes 沒覆蓋 — 補 Falcon Container Sensor（DaemonSet）+ CSPM agentless 連 cloud account 補配置面
- **Threat intel 沒接進 detection lifecycle**：訂了 CrowdStrike Intelligence 但 SOC team 沒把 actor TTP 對應到自家 detection rule — 走 [Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)、定期 review intel report + rule coverage gap
- **CIEM finding 太多 / SOC 看不完**：cloud IAM 累積 over-permission 沒清、CIEM 一掃幾千條 finding — 走 risk prioritization（哪些 identity 真的可達 sensitive resource）+ 跟 [Cloud IAM](/backend/07-security-data-protection/identity-access-boundary/) ownership 對齊、不是 dump 給 SOC
- **ASPM 拉不出 application graph**：Bionic 需要 application telemetry + repo integration、只裝 Falcon agent 不會有 application architecture map — 補 ASPM 的 application onboarding（repo / CI / runtime telemetry）
- **DSPM 找到 sensitive data 但沒 follow-up**：DSPM 是 *posture 層*、發現問題後要走 [Data Classification](/backend/07-security-data-protection/data-protection-and-masking-governance/) lifecycle、不是只把 finding 丟到 dashboard
- **Vendor lock-in 過深、退場時 SOC 工作流崩潰**：所有 detection content / IR playbook / Charlotte query / LogScale dashboard 都綁 Falcon — 關鍵 detection rule 同步 export 成 Sigma format（中性 format）、IR playbook 寫成 vendor-neutral 文件、不全押在 Falcon console

## 何時改走其他服務

| 需求形狀                            | 改走                                                                                                                                                                                                                                                         |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cloud-native / 無 endpoint workload | [Wiz](/backend/07-security-data-protection/vendors/wiz/)                                                                                                                                                                                                     |
| Palo Alto stack + compliance-heavy  | [Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/)                                                                                                                                                                                   |
| Behavioral baseline / anomaly 為主  | Lacework                                                                                                                                                                                                                                                     |
| Runtime container syscall 深度偵測  | [Falco](/backend/07-security-data-protection/vendors/) / Cilium Tetragon                                                                                                                                                                                     |
| DLP / sensitive data egress event   | [Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)                                                                                                |
| 純 SIEM / log aggregation           | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/) |
| Incident response routing           | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                                                                                                                                                                             |

## 不在本頁內的主題

- Falcon agent 內部 architecture（kernel module / sensor content channel 細節）
- CrowdStrike Intelligence 完整 threat actor 名單與 TTP reference
- Falcon LogScale 完整 SIEM 操作（屬獨立 SIEM 章節範圍、跟 Splunk 對照）
- 2024-07 Falcon update incident 的完整 root cause（屬 [8 incident response](/backend/08-incident-response/) 範圍）
- Falcon Identity Protection 的 AD-specific detection rule（屬 identity-access 範圍）

## 案例回寫

| 案例                                                                                                                                                       | 跟 Falcon Cloud Security 的關係（對照啟示）                                                                                                                             |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                                     | CrowdStrike 是 SolarWinds incident response 主導 vendor、Falcon endpoint + CrowdStrike Intelligence 整合在事件期間是強項、agent + threat intel 同 plane 的價值具象案例  |
| [3CX 2023 Desktop App Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/3cx-2023-desktopapp-supply-chain/)                    | CrowdStrike 公開 attribution（指向 LABYRINTH CHOLLIMA）與 detection、Falcon agent runtime 偵測異常 process spawn、signed binary 也要看 behavior                         |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)                     | Falcon agent runtime 偵測 JNDI lookup process tree、CrowdStrike Intelligence push IoC + TTP、漏洞披露 → fleet-wide detection deployment 是時間競賽                      |
| [Microsoft Storm-0558 Signing Key Chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | 對照啟示：endpoint agent vendor 自己也是 supply chain target、2024-07 Falcon bad sensor update 全球 Windows BSOD 是這個 risk 的具體表現、agent-first 路線的長期信任成本 |

## 下一步路由

- 上游：[7.12 雲端控制面安全與 CNAPP](/backend/07-security-data-protection/entrypoint-and-server-protection/)、[Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[Wiz](/backend/07-security-data-protection/vendors/wiz/)、[Prisma Cloud](/backend/07-security-data-protection/vendors/prisma-cloud/)、Lacework
- 下游：[Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)（SIEM 對照）、[Google DLP](/backend/07-security-data-protection/vendors/google-dlp/) / [Microsoft Purview](/backend/07-security-data-protection/vendors/microsoft-purview/)（DLP 補位）
- 跨類：[AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/)（CIEM 訊號來源）、[Okta](/backend/07-security-data-protection/vendors/okta/)（identity threat 對照）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（cloud finding → IR routing）、[6.4 release gate](/backend/06-reliability/)（ASPM finding → release gate）
- 官方：[CrowdStrike Falcon Cloud Security](https://www.crowdstrike.com/platform/cloud-security/)
