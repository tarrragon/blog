---
title: "Cilium Tetragon"
date: 2026-05-18
description: "eBPF-based runtime security + inline enforcement、跟 Cilium CNI 同生態、TracingPolicy CRD、process credentials tracking + KillerAction"
weight: 25
tags: ["backend", "security", "vendor", "cilium-tetragon", "runtime-detection", "ebpf", "kubernetes"]
---

Tetragon 是 Cilium 旗下的 *eBPF-based runtime security + enforcement* 元件、Isovalent 主導、2024 年起在 CNCF 屬 Incubating 階段。跟 [Falco](/backend/07-security-data-protection/vendors/falco/) 的核心差異在於 *偵測 vs 偵測 + 可 enforce* — Falco 預設 alert-only、Tetragon 設計支援 *kernel-level inline enforcement*（直接 kill process、override syscall return value）；對 K8s heavy + 已用 Cilium CNI 的環境、Tetragon 把 *network policy + process policy* 收進同一個 eBPF 生態。

## 服務定位

Tetragon 的核心定位是 *eBPF 為基底的 runtime observability + enforcement*、TracingPolicy CRD 是 first-class concept — 一份 YAML 同時描述 *要觀察什麼 syscall / kprobe / tracepoint* 跟 *觀察到後要不要 enforce*。底層 hook 點包括 syscall entry/exit、kprobe（任意 kernel function）、tracepoint（穩定 kernel event）、uprobe（user-space function），enforcement action 包括 `Sigkill`（kill process）、`Override`（override syscall return value）、`NotifyEnforcer`、`Post`（送 event 出 plane）。

跟 [Falco](/backend/07-security-data-protection/vendors/falco/) 比、Falco rule 用 Sysdig filter syntax、Tetragon 用 K8s CRD + JSON schema、對 K8s native 模型更貼近；Falco 主走 *alert*、Tetragon 主走 *alert + enforce*；Falco 對非 K8s VM-heavy 場景更 mature。跟 *Datadog Cloud Workload Security* 比、Datadog 是 SaaS-only + per-host 計費、Tetragon 是 OSS Apache 2.0 + 自管 + Isovalent Enterprise 付費版可選。跟 *Prisma Cloud Defender* 比、Prisma 是 CSPM/CWPP 一體化平台、Tetragon 專注 runtime + 跟 Cilium L3-L7 network policy 同 plane。

關鍵張力：*eBPF inline enforcement 的爆炸半徑* ↔ *偵測即時性*。在 kernel-level 直接 kill process 比 userspace agent 更難 bypass、但 TracingPolicy 寫錯（match 太寬）可能誤殺合法 workload、且回退路徑只能改 CRD 再 reload。要看清楚自己 *能不能承擔 enforcement 規則錯誤的 blast radius*、再決定哪些 policy 進 enforce、哪些只 observe。

## 本章目標

讀完本頁、讀者能判斷：

1. Tetragon 在 K8s runtime stack 中承擔哪一段（process visibility / file access / network syscall / enforcement）、哪些要外接（[Falco](/backend/07-security-data-protection/vendors/falco/) for VM-heavy、SIEM for log aggregation）
2. TracingPolicy 的 ownership 設計（誰寫 CRD、enforcement action 誰簽核、staging vs production rollout）
3. *Observe* vs *Enforce* 的階段化決策、什麼樣的 policy 適合 inline kill、什麼樣的應該停在 alert
4. 何時用 Tetragon、何時走 Falco / Datadog CWS / Prisma Defender 的取捨

## 最短判讀路徑

判斷 Tetragon deployment 是否健康、最少看四件事：

- **TracingPolicy 治理**：CRD 是否走 Git + PR review、enforcement action（Sigkill / Override）是否需額外簽核、staging cluster 是否先跑 24-48hr 觀察 false positive 才 promote production
- **跟 Cilium 整合深度**：Hubble flow + Tetragon process event 是否同 plane export、Pod identity 是否在 process event 自動 enrich、跟 Cilium NetworkPolicy 是否雙層 enforcement 設計
- **Enforcement coverage 分層**：哪些 policy 處於 observe-only（log JNDI lookup / setuid abuse / unexpected outbound）、哪些升到 enforce（kill known exploit pattern）、升級條件是什麼
- **Event export pipeline**：Tetragon event 是否進 SIEM（OpenTelemetry / JSON log → Splunk / Elastic）、是否跟 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 邊界一致

四件事任一缺失、就是 runtime security 邊界的待補項目。

## 日常操作與決策形狀

**TracingPolicy CRD**：Tetragon 的 first-class concept、一份 YAML 描述 hook 點 + match selector + enforcement action。Hook 點包含 *syscall*（最穩定但 surface 廣）、*kprobe*（任意 kernel function、版本相依）、*tracepoint*（穩定 kernel event、首選）、*uprobe*（user-space function、低層用）。Match selector 支援 K8s namespace / pod label / container image、process credentials（UID / GID / capabilities）、parent process。Production rule 用 *pod label selector + 具體 syscall name + 額外 process credentials 條件*、避免 cluster-wide 寬鬆 match 誤殺。

**kprobe / tracepoint / syscall hook 的選擇**：tracepoint 是 kernel 公開穩定介面、跨版本不變、首選；kprobe 可 hook 任意 kernel function 但跟 kernel build 緊綁、kernel upgrade 後可能要重寫；raw syscall 適合 audit 整類 syscall（如全部 `execve`）但量大、需要 in-kernel filter 控成本。

**Process credentials tracking**：Tetragon 從 process exec 開始 track UID / GID / capabilities / namespace、偵測 *privilege escalation*（setuid abuse、capabilities drift、container escape）是 first-class use case。跟 audit log 比、credentials drift 是 *狀態變遷*、不是單一事件、更能 surface lateral movement 早期訊號（process 開始時 UID 1000、跑到一半變 0 是異常）。

**Pod identity correlation**：Tetragon 在 K8s 環境會自動把 process event enrich K8s metadata（namespace / pod name / container image / service account）、不用後處理 join；event schema 跟 Hubble flow 同根、可在 Hubble UI 看 *某 Pod 的 network flow + process event* 同 timeline。

**跟 Cilium NetworkPolicy 雙層 enforcement**：Cilium 控 *network ingress / egress / L7 HTTP*、Tetragon 控 *process / syscall / file access*。雙層設計的意義是 — network layer 擋不住的（如 process 內部 lateral movement、container escape syscall）由 process layer 補上；process layer 漏的（如合法 process 突然 outbound 異常 destination）由 network layer 補上。對 supply chain 攻擊特別有效、攻擊鏈通常跨 *malicious process spawn + outbound C2*。

**Event export 跟 SIEM 整合**：Tetragon event 預設走 JSON log 到 stdout、可走 OpenTelemetry exporter 進 collector pipeline、再 fanout 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)。在 SIEM 端做跨來源 correlation（process event + IdP audit + cloud control plane）是 production 標配、不可只看 Tetragon 自家視圖。

**Observe → Enforce 階段化**：TracingPolicy 通常 *先進 observe-only*、跑 1-2 週收 baseline、確認 false positive 可控、再加 enforcement action 進 staging cluster、staging 觀察 24-48hr 才 promote production。對應 [Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/) 的章節原則 — runtime enforcement 不是 console 直改、是 detection content lifecycle。

## 核心取捨表

| 取捨維度       | Cilium Tetragon                                | Falco                                            | Datadog CWS                              | Prisma Cloud Defender                   |
| -------------- | ---------------------------------------------- | ------------------------------------------------ | ---------------------------------------- | --------------------------------------- |
| 偵測技術       | eBPF（kprobe / tracepoint / syscall / uprobe） | eBPF + kernel module 兩種 driver                 | eBPF agent                               | eBPF + kernel module                    |
| Enforcement    | 內建（Sigkill / Override syscall return）      | 預設 alert-only（plugin 可擴 response）          | 自動 response（kill / isolate、SaaS 控） | 內建（block process / file / network）  |
| 規則語言       | K8s CRD（TracingPolicy YAML）                  | Sysdig filter syntax（YAML rule）                | Datadog Security Rules（JSON / UI）      | Prisma Runtime Rules（UI / JSON）       |
| 計費 / 授權    | OSS Apache 2.0、Isovalent Enterprise 付費      | OSS Apache 2.0、Sysdig Secure 付費               | SaaS per-host                            | 商業 per-defender                       |
| K8s native     | 強 — Pod identity 自動 enrich、跟 Cilium 同源  | 中 — K8s metadata 需 audit endpoint              | 強 — Datadog Agent 已熟                  | 強 — Prisma 平台一體                    |
| Network policy | 跟 Cilium L3-L7 雙層（同 plane）               | 無 — 純 process / file                           | 無 — 跟 Datadog Network 分離             | 內建 micro-segmentation                 |
| VM / 非 K8s    | 弱 — Linux only、K8s-first                     | 強 — VM / bare metal mature                      | 中 — 跨環境同 agent                      | 強 — VM / serverless / container 全覆蓋 |
| 部署模型       | Self-hosted DaemonSet（K8s）                   | Self-hosted DaemonSet / VM agent                 | SaaS                                     | 商業 self-hosted + SaaS console         |
| 適合場景       | K8s heavy + 已用 Cilium + 要 inline enforce    | VM-heavy / K8s 混合、需要 mature alert ecosystem | Datadog 已用、要 unified observability   | 多雲 CSPM/CWPP 一體化、合規驅動         |
| 退場成本       | 中 — TracingPolicy CRD 跨 cluster 可移植       | 中 — Falco rule 跟 Sigma 可互轉                  | 高 — SaaS lock-in                        | 高 — 商業平台 lock-in                   |

選 Tetragon 的核心訴求：*K8s heavy + 已用 Cilium CNI + 想要 kernel-level inline enforcement + OSS 免授權成本*、且有 SRE / security team 能維護 TracingPolicy CRD lifecycle。VM-heavy 或 K8s 但用其他 CNI 走 Falco 更划算。

## 進階主題

**Inline enforcement 的 blast radius 設計**：`Sigkill` 直接 kill 觸發 process、`Override` 改寫 syscall return value（讓 process 以為成功但實際沒做）— 兩者都在 kernel-level、攻擊者很難 bypass、但寫錯規則的 blast radius 是 *整個 cluster 內 match 到的 process 全死*。實務治理：enforcement action 規則進 GitOps、PR 需 security + SRE 雙簽、staging cluster 跑 namespace-scoped 規則先驗證、production rollout 走 canary namespace 再擴散。

**Process credentials drift detection**：track UID / GID / capabilities 變遷、偵測 setuid abuse（process 從 uid 1000 變 0）、capabilities 突然新增（特別是 CAP_SYS_ADMIN / CAP_NET_ADMIN）。對 lateral movement 早期警報是 first-class signal — 攻擊者拿到初始 access 後通常要 escalate privilege、credentials drift 是必經訊號。配對 [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/) 的 lesson：簽章驗證通過但 runtime 行為異常需 *runtime credentials + process behavior* 雙重 baseline。

**跟 Cilium L3-L7 雙層 enforcement**：典型 supply chain 攻擊鏈 — *malicious dependency loaded → process spawn → C2 outbound*、network layer 擋 outbound（Cilium NetworkPolicy 限制 egress destination）、process layer 擋 process（Tetragon KillerAction kill 異常 spawn）。雙層任一通則攻擊鏈中斷。對應 [3CX 2023 Desktop App Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/3cx-2023-desktopapp-supply-chain/) 的 case shape。

**跟 SBOM / image signing 整合 baseline**：Tetragon 偵測 runtime 行為偏離 baseline、SBOM / image signing 控 build-time 信任、合在一起是 *trusted artifact + verified runtime behavior* 雙重保障。runtime 行為 baseline 通常從 SBOM 列出的合法 process / syscall set 出發、deviation 進 alert。

**Isovalent Enterprise**：商業版加值在 multi-cluster management、policy 集中下發、support SLA、跟 Isovalent Hubble Enterprise / Cilium Service Mesh Enterprise 整合。OSS 版本核心功能完整、Enterprise 主要解 *多 cluster 大規模管理* 跟 *企業 support*、不是 feature gating。

## 排錯與失敗快速判讀

- **TracingPolicy 誤殺合法 workload**：match selector 太寬、cluster-wide 沒加 namespace / pod label 條件 — 改 namespace-scoped + 加 process credentials 額外條件、staging 跑 48hr 再 promote
- **kprobe rule kernel upgrade 後壞**：hook 的 kernel function 改名或 signature 變 — 改用 tracepoint（穩定介面）、kprobe 進 staging 版本相依測試
- **Event volume 爆炸 / SIEM ingestion cost 飆**：raw syscall hook 沒做 in-kernel filter、所有 `execve` 都進 event — 加 in-kernel filter（按 pod label / process name），讓 filter 在 eBPF 端做、不要事後 drop
- **Inline enforcement 規則錯誤 blast radius 太大**：production 直接上 `Sigkill` 沒走 staging — enforcement action 規則一律先 observe-only 1 週、staging cluster 24-48hr、canary namespace、才 production
- **跟 Cilium NetworkPolicy 重疊或衝突**：同一個 attack pattern 被 network + process 同時阻擋、log 重複、誤判 — 設計時雙層各管 *互補面*（network 管 destination、process 管 process spawn）、不重複管同一面
- **non-K8s workload 進不來**：Tetragon DaemonSet 只在 K8s 跑、VM / bare metal 不支援 — VM-heavy 環境改走 [Falco](/backend/07-security-data-protection/vendors/falco/)、K8s + VM 混合走雙 stack
- **Pod identity enrich 不全**：某些 process event 缺 namespace / pod name — 通常是 process 在 pod sandbox 啟動前 spawn、或 short-lived process 太快結束、調 Tetragon 的 process cache lifetime + K8s API server 連線健康

## 何時改走其他服務

| 需求形狀                          | 改走                                                                                                                                                |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| VM-heavy / 非 K8s 為主            | [Falco](/backend/07-security-data-protection/vendors/falco/)                                                                                        |
| Datadog observability 已用        | [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)（Cloud Workload Security）                                       |
| 多雲 CSPM/CWPP 一體化、合規驅動   | Prisma Cloud Defender（商業）                                                                                                                       |
| SIEM 偵測為主、不需 inline kill   | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) |
| Endpoint EDR（user laptop / VDI） | CrowdStrike Falcon / Microsoft Defender for Endpoint                                                                                                |
| 偵測覆蓋率治理                    | [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)                                         |
| Incident routing                  | [8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)                                                                                    |

## 不在本頁內的主題

- TracingPolicy CRD 完整欄位 reference 跟 kprobe / tracepoint 寫法 cookbook
- Cilium NetworkPolicy 寫法（屬 network 治理、跨章節）
- eBPF kernel programming 內部原理跟 verifier 限制
- Isovalent Enterprise 跟 Cilium Service Mesh 商業整合細節
- Hubble UI 操作（屬 observability 視角、跨章節）

## 案例回寫

Tetragon 在 07 案例庫沒有直接 vendor-level 事件、但所有 runtime detection + supply chain case 都是 eBPF inline enforcement 的對照：

| 案例                                                                                                                                    | 跟 Tetragon 的關係（對照啟示）                                                                                                           |
| --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)  | TracingPolicy 可 hook JNDI lookup 相關 syscall、配 `Sigkill` 直接 kill exploit process、比 userspace WAF 更難 bypass                     |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                  | process credentials drift detection 對 lateral movement 早期警報、簽章驗證通過但 runtime 行為異常需 runtime baseline 補位                |
| [3CX 2023 Desktop App Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/3cx-2023-desktopapp-supply-chain/) | 偵測 desktop app 異常 outbound、Tetragon 抓 process + Cilium NetworkPolicy 同層擋 destination、雙層 enforcement 中斷攻擊鏈               |
| [Detection Engineering Lifecycle (section)](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)            | TracingPolicy CRD 走 GitOps + PR review + staging tune + canary rollout、inline enforcement 不可 console 直改                            |
| [Alert Fatigue and Signal Quality (section)](/backend/07-security-data-protection/blue-team/alert-fatigue-and-signal-quality/)          | observe-only 階段先收 baseline、in-kernel filter 控 event volume、enforcement 只升給高 confidence pattern、避免 alert / log 雙重 fatigue |

## 下一步路由

- 上游：[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)、[Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)
- 平行：[Falco](/backend/07-security-data-protection/vendors/falco/)、[Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/)
- 下游：[Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)（Tetragon event 進 SIEM 做跨來源 correlation）
- 跨類：[Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)（network edge 擋 + process 層補位）、[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（credentials drift 配 secret rotation）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（runtime alert → IR routing）、[4 observability](/backend/04-observability/)（Hubble + Tetragon event pipeline 共用）
- 官方：[Tetragon Documentation](https://tetragon.io/)、[Cilium Project](https://cilium.io/)
