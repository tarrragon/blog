---
title: "OPA Gatekeeper"
date: 2026-05-18
description: "OPA 官方 K8s admission controller、ConstraintTemplate + Constraint 兩層、Rego policy + Audit + Mutation"
weight: 22
tags: ["backend", "security", "vendor", "gatekeeper", "policy-as-code", "kubernetes", "opa"]
---

OPA Gatekeeper 是 OPA 官方在 Kubernetes admission 層的落實、把 OPA 的 general-purpose policy engine 適配成 K8s-native admission controller。它跟 [OPA](/backend/07-security-data-protection/vendors/opa/) / [Kyverno](/backend/07-security-data-protection/vendors/kyverno/) / [Conftest](/backend/07-security-data-protection/vendors/conftest/) 的差異不在「policy 能不能寫」、而在 *對接面 + 抽象層次 + 工具鏈定位* — Gatekeeper 是 OPA 在 K8s admission 的 first-class 落實、ConstraintTemplate + Constraint 兩層抽象把 Rego policy 變成 K8s CRD、Audit 補位 background scan、Mutation 2024 起進 stable。

## 服務定位

Gatekeeper 的核心定位是 *Rego policy 在 K8s admission 層的 K8s-native 包裝*、不是另一個 policy engine。底層仍是 OPA、Rego 是同一套語言；上層加了兩個 K8s-specific 抽象 — *ConstraintTemplate*（Rego policy + parameter schema 的 CRD 定義）跟 *Constraint*（Template 的 instance、指定 match scope 與 parameter）。意義是同一份 Rego policy 寫一次、在不同 cluster / 不同 namespace 給不同 Constraint instance、不用改 Rego 本體。

跟 [OPA](/backend/07-security-data-protection/vendors/opa/)（純 sidecar）比、Gatekeeper 走 *K8s-native + 兩層抽象*、犧牲 OPA 純 sidecar 的跨平台彈性（OPA 可同時管 K8s admission + API gateway + Terraform plan）、換來 K8s 內部 CRD + RBAC + GitOps 的一致體驗。跟 [Kyverno](/backend/07-security-data-protection/vendors/kyverno/) 比、Gatekeeper 走 *Rego DSL*、Kyverno 走 *YAML pattern matching* — team 已投資 OPA / Rego（API gateway / Terraform 已用 Rego）就走 Gatekeeper、純 K8s shop + 沒 Rego 包袱直接用 Kyverno 較省學習成本。跟 [Conftest](/backend/07-security-data-protection/vendors/conftest/) 比、Conftest 是 *CI-time static config check*、Gatekeeper 是 *runtime admission + audit*、兩者互補不互斥（CI 用 Conftest 擋 PR、admission 用 Gatekeeper 擋 deploy）。

關鍵張力：*Rego 學習曲線* ↔ *跨平台 policy 一致性* 是 Gatekeeper 跟 Kyverno 最大的選擇分水嶺。純 K8s 場景 Kyverno YAML 寫起來快、但同樣的 image signature 規則若要在 Terraform plan / CI / admission 三處 enforce、Rego 寫一次跨三處比 YAML / Cue / Sentinel 多種語言混用乾淨。

## 本章目標

讀完本頁、讀者能判斷：

1. Gatekeeper 在 cluster policy stack 中承擔哪一段（admission validation / audit / mutation）、哪些要外接（[OPA](/backend/07-security-data-protection/vendors/opa/) 純 sidecar 管非 K8s 對象、[Conftest](/backend/07-security-data-protection/vendors/conftest/) 補 CI-time）
2. ConstraintTemplate 跟 Constraint 兩層怎麼切（Template 由 platform team 維護、Constraint 給 app team 在 namespace 內 instantiate）
3. Audit / Mutation / External Data Provider 何時開、開了之後 cost 與 failure mode
4. 何時用 Gatekeeper、何時改 Kyverno 或退回純 OPA 的取捨

## 最短判讀路徑

判斷 Gatekeeper deployment 是否健康、最少看四件事：

- **ConstraintTemplate 的 ownership**：誰寫 Rego、誰 review、Template 是否走 Git（PR review + Gator CLI unit test）、是否有共用 library 避免每個 Template 重寫 K8s helper
- **Audit coverage**：除了 admission 攔截、Audit 是否定期 scan 已存在 resource（pre-Gatekeeper 部署的 legacy resource 違規）、`auditFromCache` 是否開、audit interval 是否合理（預設 60s、production 通常拉到 5-10min 避 API server 壓力）
- **Failure mode 治理**：Constraint `enforcementAction` 是 `deny` / `warn` / `dryrun`、Webhook failurePolicy 是 `Fail` / `Ignore`、`Fail` + Gatekeeper pod down 會擋全 cluster deploy
- **跟 GitOps 的對接**：ConstraintTemplate / Constraint 是否走 ArgoCD / Flux 部署、policy change 是否經 staging cluster 驗證、emergency exception 流程是否定義

四件事任一缺失、就是 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 在 admission 層的待補項目。

## 日常操作與決策形狀

**ConstraintTemplate（CT）— Rego policy + CRD 定義**：CT 是 Gatekeeper 的核心抽象、由 Rego policy + parameter schema（OpenAPI v3）兩段組成。Template 寫好 apply 到 cluster 後、Gatekeeper 會生成同名 CRD（例 `K8sRequiredLabels`）、app team 就能用該 CRD 寫 Constraint。Template 由 platform team 維護、不該每個 app team 自己寫 Rego — 集中維護才能保證 helper / convention / unit test 一致。

**Constraint — Template 的 instance + match scope**：Constraint 指定三件事 — *該套用哪個 Template*（kind）、*套用範圍*（match：kinds / namespaces / labelSelector / excludedNamespaces）、*parameter 值*（spec.parameters、對應 Template 的 schema）。同一個 Template 可以有多個 Constraint instance（production / staging 不同 threshold、不同 namespace 不同 required label set）。這層抽象的意義是 *policy logic 跟 environment-specific configuration 分開*。

**Audit — background scan 已存在 resource**：除了 admission webhook 在 create / update 時攔、Audit controller 定期（預設 60s）掃整個 cluster 找違規 resource、結果寫到 Constraint status 的 `violations` 欄位。意義是 *legacy resource 在你 install Gatekeeper 之前就在那、admission 不會觸發、Audit 才會抓到*。`auditFromCache: true` 用 Gatekeeper 自己的 informer cache 不打 API server、適合大 cluster。

**Mutation — 2024+ stable**：早期 Gatekeeper 只有 Validation、Mutation 在 v3.10+ 進 beta、2024 隨 v3.14+ 進 stable。Mutation 走獨立 CRD（`Assign` / `AssignMetadata` / `ModifySet`）、不走 ConstraintTemplate。常見用法：注入 `securityContext.runAsNonRoot: true`、補 default resource limit、加 organization label。Mutation 跟 Validation 都開的話、Mutation 先跑、Validation 看 mutated 後的結果。

**Sync Resources — cross-resource lookup**：Rego policy 若要查 *別的 resource*（例：擋 Service 用了不存在的 Namespace）、要先 declare `Config` CRD 把該 resource type 加進 Gatekeeper 的 sync list、Gatekeeper 才會在 cache 裡有那個 resource 供 Rego 查。沒 sync 的 resource 不能跨 reference、是常見踩雷點。

**External Data Provider — query 外部 API 做 decision**：Gatekeeper v3.10+ 引入 External Data Provider、Rego 可以 call 外部 HTTPS endpoint 取 runtime data 做 policy decision。典型用法：query image scan service（例 [Trivy](/backend/07-security-data-protection/vendors/trivy/) server）確認 image 沒 CVE、query SBOM attestation service 確認 supply chain 完整、query custom IAM 確認 namespace owner 有權建立該 resource。要設 timeout + cache、外部 service down 不能擋全 cluster admission。

**Gator CLI — policy unit test**：Gator 是 Gatekeeper 官方 CLI、本機跑 Template + Constraint 對 mock K8s manifest、不需 cluster。CI pipeline 跑 `gator test` 對每個 Template 跑 fixture、policy change 出 PR 時自動驗證 — 避免 production deploy 才發現 Template Rego bug 擋全 cluster。

**跟 GitOps 整合**：ConstraintTemplate / Constraint / Mutation / Config CRD 都是純 YAML、走 ArgoCD / Flux 部署是標準作法。實務 layout：`gatekeeper-system` namespace 裝 Gatekeeper、`gatekeeper-policies` repo 放 Template 跟 baseline Constraint（platform team owned）、各 app namespace 的 Constraint instance 可以由 app team 在自己 repo 管理（透過 ArgoCD AppProject 限制 Constraint kind）。

## 核心取捨表

| 取捨維度       | OPA Gatekeeper                                | Kyverno                                    | OPA 純 sidecar                              | Conftest                              |
| -------------- | --------------------------------------------- | ------------------------------------------ | ------------------------------------------- | ------------------------------------- |
| 對接面         | K8s admission + Audit（K8s-only）             | K8s admission + Audit（K8s-only）          | 任意 — API gateway / Terraform / K8s        | CI-time（static config check）        |
| Policy 語言    | Rego（OPA 同一套）                            | YAML pattern matching（K8s-native）        | Rego                                        | Rego（OPA 同一套）                    |
| 抽象層次       | ConstraintTemplate + Constraint 兩層          | ClusterPolicy / Policy（單層）             | OPA policy bundle（無 K8s-specific 抽象）   | conftest test file（無 cluster 概念） |
| Mutation       | 支援（v3.14+ stable）                         | 支援（first-class、Kyverno 強項）          | 不支援（需自寫 admission webhook）          | 不適用                                |
| Cross-resource | Sync Resources（要 declare）                  | Context API（內建）                        | 看自己 sidecar 怎麼寫                       | 看 CI 怎麼 load                       |
| 外部 data      | External Data Provider（v3.10+）              | Context API（image registry / ConfigMap）  | 看自己 sidecar 怎麼寫                       | 不適用（純 static）                   |
| 學習曲線       | Rego 陡 + 兩層抽象多概念                      | YAML 直觀、K8s-native idiom                | Rego 陡 + 自管 deployment                   | Rego 陡 + CI integration              |
| 適合場景       | team 已投資 Rego / OPA、跨 K8s + 其他平台一致 | 純 K8s shop、無 Rego 包袱、Mutation 是重點 | 跨 K8s + API + Terraform 一致 policy 管理面 | PR 階段擋 manifest / IaC config       |
| 退場成本       | 高 — Template / Constraint / Rego 量多        | 中 — YAML 較可移植                         | 中 — Rego 可搬到 Gatekeeper                 | 低                                    |

選 Gatekeeper 的核心訴求：*team 已用 Rego（API gateway / Terraform plan / CI 已 OPA）+ 想把 same policy 延伸到 K8s admission + 看重 OPA ecosystem 一致性*。純 K8s shop 沒 Rego 包袱、又特別需要 Mutation 場景密集（PSP 廢除後重建、跨 namespace 統一 sidecar 注入）直接走 Kyverno 更省學習成本。

## 進階主題

**Rego idioms for K8s admission**：K8s admission review 物件結構是 `input.review.object`、Template 的 `violation` rule 走 `violation[{"msg": msg}] { ... }` 形式。常見 idiom：`match.kinds` 跟 `match.namespaceSelector` 在 Constraint 層處理 scope、Rego 內只寫 *policy logic*；K8s helper（label 取值、container loop、init container 排除）抽到 shared library Template；錯誤訊息要帶 `input.review.object.metadata.name` 幫 app team 定位是哪個 resource 被擋。

**External Data Provider 的 production 治理**：Provider 是獨立 service、Gatekeeper webhook 透過 HTTPS call、cache 在 Gatekeeper 內。要設 timeout（預設 3s、過時 ConstraintTemplate `failurePolicy` 決定 fail-open / fail-closed）、cache TTL、Provider 自身的 readiness / liveness。Provider down 不該擋全 cluster — 用 `failurePolicy: Ignore` 對 External Data Provider 例外、但記錄 metric alert。對應 [XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/) 的 SBOM attestation 查詢場景。

**Gator CLI 在 CI 的 pipeline 設計**：`gator test` 對 fixture 跑、`gator verify` 跑 Template 自帶 test suite、`gator expand` 預覽 Mutation 結果。PR 流程：Template change → `gator verify` 跑 unit test → kind cluster 起 Gatekeeper apply Template + sample violation manifest → confirm 擋下來才 merge。

**跟 Styra DAS / Nirmata 整合**：Gatekeeper OSS 本身沒 central management UI、多 cluster deployment 看 violation status 要自己拼。Styra DAS 是 OPA 商業 control plane、可以 push Template / Constraint 到多 cluster Gatekeeper、彙整 audit violation、做 policy impact analysis。Nirmata 走類似路線。OSS-only deployment 通常用 ArgoCD ApplicationSet + Prometheus exporter（gatekeeper-policy-manager / Open Policy Agent metrics）拼。

## 排錯與失敗快速判讀

- **Gatekeeper webhook timeout / 擋全 cluster admission**：Rego policy 寫了 expensive operation（大量 cross-resource lookup、External Data Provider call without cache）— webhook timeout 預設 3s、超過就走 failurePolicy；改寫 Rego 用 indexed lookup、External Data Provider 加 cache、`failurePolicy: Ignore` for non-critical Template
- **新 Template apply 後 admission 整個壞**：Rego syntax / logic bug、production 才發現 — PR 必跑 `gator verify` + staging cluster 24-48hr soak、Constraint 先用 `enforcementAction: dryrun` 觀察 violation count 才切 `deny`
- **Audit 跑很慢 / API server 壓力大**：cluster resource 量大、Audit interval 預設 60s 太頻繁 — 拉長到 5-10min、`auditFromCache: true` 用 informer 不打 API server、大 cluster 開 `auditChunkSize` 分批處理
- **legacy resource 不擋**：admission webhook 只攔 create / update、`kubectl apply` 沒改動 spec 不觸發 — 用 Audit 抓 violation、配合手動 migration plan、不要期待 admission 自動修
- **Mutation 跟 Validation 衝突**：Mutation 加了 label、Validation 又擋說 label 不該存在 — Mutation 先跑、Validation 看 mutated 結果；設計 policy 時要對齊兩端、不能各自寫
- **Sync 沒 declare、cross-resource policy 看不到對象**：Rego `data.inventory.namespace["foo"].v1.Pod` 回 undefined — `Config` CRD 加 sync targets、確認 Gatekeeper pod restart 後 cache 載入
- **External Data Provider down 擋全 cluster**：Provider service 自己掛、`failurePolicy: Fail` 整個 admission 壞 — Provider 走 `failurePolicy: Ignore` + metric alert、Provider 自身 HA 部署、cache TTL 拉長

## 何時改走其他服務

| 需求形狀                              | 改走                                                                                        |
| ------------------------------------- | ------------------------------------------------------------------------------------------- |
| 純 K8s + 無 Rego 包袱 + Mutation 重點 | [Kyverno](/backend/07-security-data-protection/vendors/kyverno/)                            |
| 跨 K8s + API gateway + Terraform      | [OPA](/backend/07-security-data-protection/vendors/opa/)（純 sidecar）                      |
| CI-time / PR 階段擋 manifest          | [Conftest](/backend/07-security-data-protection/vendors/conftest/)                          |
| Image scan 結果作為 policy 來源       | [Trivy](/backend/07-security-data-protection/vendors/trivy/)（feed External Data Provider） |
| Runtime threat detection（syscall）   | Falco / Cilium Tetragon（屬 runtime detection、不在 admission 層）                          |
| Multi-cluster policy 集中管理         | Styra DAS / Nirmata（OPA / Gatekeeper 商業 control plane）                                  |
| 偵測 / SIEM                           | [Splunk](/backend/07-security-data-protection/vendors/splunk/) 或同類 SIEM                  |

## 不在本頁內的主題

- Rego 完整語法 reference（unification、comprehension、partial evaluation）
- Gatekeeper helm chart / installation 細節（看官方 docs）
- Open Policy Agent 在 service mesh / API gateway 的 sidecar 部署模式（看 [OPA](/backend/07-security-data-protection/vendors/opa/) 頁）
- Pod Security Admission（K8s 內建、跟 Gatekeeper 互補但不是 Gatekeeper 一部分）
- Multi-cluster policy bundle 的 OCI registry 分發（屬 [7.12 供應鏈完整性](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 邊界）

## 案例回寫

Gatekeeper 在 07 案例庫沒有直接 vendor-level 事件、但 supply chain 跟 admission policy 相關 case 都是 Gatekeeper 落實位置的對照：

| 案例                                                                                                                                   | 跟 Gatekeeper 的關係（對照啟示）                                                                                                                            |
| -------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                 | ConstraintTemplate 配 cosign image signature verify、擋未簽 / 簽章不符 image 進 cluster；Audit 補位掃既有 deployment 找未簽 image                           |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/) | Gatekeeper External Data Provider 接 [Trivy](/backend/07-security-data-protection/vendors/trivy/) server、admission 階段查 image 是否有 critical CVE 直接擋 |
| [XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)        | External Data Provider 可 query SBOM attestation 服務做 policy decision、不只看 image hash 而看 component provenance 鏈                                     |
| [7.12 供應鏈完整性 (section)](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)                         | Gatekeeper 是 OPA ecosystem 在 K8s admission 的官方落實、artifact trust gate 從 CI（Conftest）延伸到 runtime（Gatekeeper）的閉環                            |

## 下一步路由

- 上游：[7.12 供應鏈完整性與 Artifact Trust](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)、[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[OPA](/backend/07-security-data-protection/vendors/opa/)、[Kyverno](/backend/07-security-data-protection/vendors/kyverno/)、[Conftest](/backend/07-security-data-protection/vendors/conftest/)
- 下游：[Trivy](/backend/07-security-data-protection/vendors/trivy/)（image scan 結果 feed External Data Provider）、[SPIRE](/backend/07-security-data-protection/vendors/spire/)（workload identity 跟 admission policy 互補）
- 跨類：[Splunk](/backend/07-security-data-protection/vendors/splunk/)（admission violation event 進 SIEM correlation）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（policy violation → IR routing）
- 官方：[OPA Gatekeeper Documentation](https://open-policy-agent.github.io/gatekeeper/)
