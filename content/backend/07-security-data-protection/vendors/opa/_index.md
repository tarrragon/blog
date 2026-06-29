---
title: "Open Policy Agent (OPA)"
date: 2026-05-18
description: "CNCF general-purpose policy engine、Rego Datalog-like 語言、decoupled decision + enforcement、跨 K8s / API / Terraform / SQL 統一 policy"
weight: 20
tags: ["backend", "security", "vendor", "opa", "policy-as-code", "rego", "open-source"]
---

Open Policy Agent (OPA) 是 CNCF graduated 的 *general-purpose policy engine*、設計目的是把「誰能做什麼、什麼 config 才合法」從 application code 抽到外部 policy decision layer。它跟 [Kyverno](/backend/07-security-data-protection/vendors/kyverno/) / [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) 的差別是：後兩者鎖在 K8s admission controller 領域、OPA 是 *跨 enforcement point* 的 unified policy framework — 同一份 policy 可以同時管 K8s admission、API authz、Terraform plan、SQL row-level filter。跟 [Conftest](/backend/07-security-data-protection/vendors/conftest/) 的差別是：Conftest 是 OPA 的 *CLI wrapper for static config*（在 CI 跑 Terraform / Dockerfile / K8s YAML 檢查）、OPA 本體是 *runtime evaluation engine*（線上服務查詢決策）。

## 服務定位

OPA 的核心抽象是 *decoupled decision + enforcement* — OPA 只負責 *decide*（`input` 進來、`allow` / `deny` + decision metadata 出去）、application 負責 *enforce*（拿到 decision 後實際 reject request / block deploy / mask data）。這個解耦讓同一份 policy 跨 K8s admission（透過 [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) 或 kube-mgmt sidecar）、Envoy authz filter、API gateway、Terraform pre-plan、SQL row-level filter、Kafka topic ACL 都能重用。

OPA 的查詢語言是 *Rego*、Datalog-like declarative language、設計上適合表達「給定一組 fact，這個動作合法嗎」。Rego 跟一般 imperative programming（Python / Go / YAML rules）差距大、team 要投入 1-2 週才能寫出 production-grade policy；換回的是 *表達力 + 跨情境一致性* — Kyverno 的 YAML policy 易上手、但跨 K8s 邊界後沒辦法用。

關鍵張力：*Rego 學習曲線* ↔ *unified policy 的長期價值*。只跑 K8s 的團隊用 Kyverno YAML 更直覺；只跑 CI policy 的用 Conftest 更輕；要在 K8s + API + Terraform + DB 跨層統一 policy、或要 audit-grade decision log、或預期 policy 會長期累積成資產的、才值得投資 OPA + Rego。

商業模型：核心 OPA 是 Apache 2.0 OSS、免費。Styra DAS（OPA 創辦人公司）是 enterprise SKU、提供 policy library + impact analysis + multi-cluster management + audit dashboard、適合大型團隊。OPAL（Permit.io 維護的 OSS）是 GitOps-style policy distribution layer、補 OSS OPA 缺的 bundle server。

## 本章目標

讀完本頁、讀者能判斷：

1. OPA 在 policy stack 中承擔哪一段（decision engine） vs enforcement point 各自的 ownership
2. Rego 投資門檻是否值得（K8s-only vs 跨 enforcement point）
3. Policy bundle / Decision log / Partial evaluation 三個 first-class concept 在 production 的設計形狀
4. 何時用 OPA、何時走 [Kyverno](/backend/07-security-data-protection/vendors/kyverno/) / [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) / [Conftest](/backend/07-security-data-protection/vendors/conftest/) 的取捨

## 最短判讀路徑

判斷 OPA deployment 是否健康、最少看四件事：

- **Policy ownership**：誰能寫 / 改 Rego policy（platform team / security team / SRE）、policy 是否進 Git、change 是否經 PR review + staging tenant 跑 24-48hr 觀察
- **Bundle distribution**：policy 是否 build 成 bundle（tar.gz）、是否簽章、OPA agent 是否定期 pull、bundle server 在哪（自管 nginx / S3 / OPAL / Styra DAS）
- **Decision log governance**：每個 decision 是否進 audit log（input + output + policy version + timestamp）、log 是否進 SIEM（[Splunk](/backend/07-security-data-protection/vendors/splunk/) / Elastic）、retention 多久
- **Enforcement coverage**：哪些 enforcement point 接 OPA（K8s admission / API / Envoy / Terraform）、policy 是否 share 還是各 point 各寫一份、跨 point 的一致性怎麼驗

四件事任一缺失、就是 [Policy as Code Foundations](/backend/07-security-data-protection/security-as-risk-routing-system/) 的待補項目。

## 日常操作與決策形狀

**Rego policy 形狀**：Rego 是 Datalog-like declarative language、policy 寫成 `allow { ... }` rule、所有條件成立才 evaluate 為 true。實務 idiom：底層寫 *base policy*（如 `policies/k8s/required_labels.rego`）、上層寫 *policy library*（共用 helper 如 `policies/lib/registry.rego`）、application 端傳 `input`（K8s admission request / API request / Terraform plan JSON）查詢。Rego 鼓勵 *small composable rule*、不寫長 imperative function。

**Policy bundle**：OPA 不從 Git 直接讀 policy、而是讀 *bundle*（tar.gz、含 `.rego` + data JSON、optional 簽章）。Bundle 從 *bundle server* pull（自管 nginx / S3 / OPAL / Styra DAS）、OPA agent 定期 polling（預設 60s）。Bundle 的核心價值是 *versioned + signed + atomically swap* — policy 更新不會 partial apply、簽章確保中間沒被改、版本 metadata 讓 decision log 可追到當時用哪版 policy。

**Decision log**：每個 OPA query 都可開 decision logging、log entry 含 `input` + `result` + `policy_version` + `timestamp` + `decision_id`。意義是 *audit-grade reconstruction* — 事後可以重跑 `opa eval --bundle <version> --input <log_input>` 驗證當時 decision 是否正確。Decision log 進 SIEM 後可做 *over-permission analysis*（哪些 user 拿到 allow 但實際從不該被 allow）跟 *policy coverage check*（哪些 rule 從沒被觸發過、可能是 dead code）。

**Integration pattern**：production OPA 主要四種 enforcement integration — *K8s admission*（走 [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) 是 OPA 官方 K8s integration、或 kube-mgmt 把 OPA 當 sidecar 跑、admission webhook 把 request 送進 OPA decide）；*API authz*（application 在 request handler 開頭 query OPA、拿 allow/deny 後 enforce）；*Envoy / service mesh*（Envoy 的 ext_authz filter 接 OPA、L7 authz decision）；*Infrastructure as Code*（CI 跑 [Conftest](/backend/07-security-data-protection/vendors/conftest/) 對 Terraform plan / K8s YAML 做 OPA 評估）。

**Partial evaluation**：OPA 進階 feature、把一份 policy 對某個 *partial input*（如 `user="alice"`）pre-evaluate、產出 *殘餘 query*（如 SQL `WHERE tenant_id IN (...)` 或 regex），下發給 enforcement point 直接用。意義是 *把 policy decision 推到 enforcement point 內部*、減少每次 query 都要過 OPA 的 latency；常用於 row-level data filter（policy 寫一次、partial eval 出 SQL WHERE clause、application 直接拼進 query）。

**OPAL（GitOps for OPA）**：OSS、Permit.io 維護、解決「policy 從 Git push 到所有 OPA agent」的 distribution 問題。Git → OPAL Server → OPA Agent 的 push model、policy commit 到 main branch 後幾秒內所有 OPA 更新。對應 OSS-only 的 production setup；Styra DAS 提供同等功能 + 管理 UI。

**Styra DAS（商業 management）**：Styra 是 OPA 創辦人公司、DAS 是 enterprise SKU。核心價值：*policy library*（pre-built policy for K8s / Terraform / Kafka）、*impact analysis*（policy 上 production 前 dry-run 看會 deny 多少現有 resource）、*multi-cluster policy distribution*、*audit dashboard*。OSS-only 自己拼 OPAL + decision log + SIEM 也能做、但團隊 > 50 個 cluster / 多 BU 時 DAS 划算。

**Constraint Framework**：[Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) 在 OPA 之上加的 K8s-specific 抽象、用 `ConstraintTemplate`（Rego policy 模板）+ `Constraint`（K8s CRD instance、實際 enforce）。對純 K8s 場景比直接寫 Rego 更 K8s-native；但這個抽象只在 K8s 領域有意義、不會跨到 API / Terraform。

## 核心取捨表

| 取捨維度      | OPA                                                  | Kyverno                                  | Gatekeeper                                  | Conftest                                                |
| ------------- | ---------------------------------------------------- | ---------------------------------------- | ------------------------------------------- | ------------------------------------------------------- |
| 定位          | General-purpose policy engine                        | K8s-native admission controller          | OPA 的 K8s admission integration（官方）    | OPA 的 CLI wrapper for static config                    |
| 語言          | Rego（Datalog-like declarative）                     | YAML（K8s-native）                       | Rego（透過 ConstraintTemplate）             | Rego                                                    |
| Enforcement   | K8s / API / Envoy / Terraform / SQL / Kafka 跨層     | K8s admission only                       | K8s admission only                          | CI / pre-commit（不在 runtime）                         |
| 學習曲線      | 陡 — Rego 1-2 週                                     | 緩 — YAML 1-2 天                         | 中 — ConstraintTemplate 抽象 + Rego         | 中 — Rego 1-2 週、但 scope 小                           |
| 部署模型      | OPA agent（sidecar / daemon / library embed）        | K8s controller + webhook                 | K8s controller + webhook                    | CLI（CI / 本地）                                        |
| Mutation      | 透過 Gatekeeper Mutation 或 application enforce 補上 | 原生 mutate webhook（強項）              | Mutation 是 v3.10+ beta、功能不及 Kyverno   | 無（static check only）                                 |
| Bundle / 分發 | Bundle server + sign + OPA agent pull / OPAL push    | K8s CRD apply（kubectl）                 | K8s CRD apply                               | Git repo（CI 直接 clone）                               |
| Decision log  | First-class、audit-grade                             | K8s event + audit log                    | K8s event + audit log                       | CI build log                                            |
| 商業 SKU      | Styra DAS（management + impact analysis）            | Nirmata Kyverno Enterprise               | 無（純 OSS）                                | 無（純 OSS）                                            |
| 適合場景      | 跨 enforcement point + long-term policy investment   | K8s-only + 快速上手 + YAML-friendly team | K8s-only + 已用 OPA / Rego、要 OPA 官方整合 | CI pre-deploy check + Terraform / K8s YAML / Dockerfile |
| 退場成本      | 中 — Rego policy 可移到其他 OPA-compatible engine    | 高 — YAML policy 僅 Kyverno 認           | 中 — Rego 可重用、Constraint 抽象要重寫     | 低 — CLI tool、policy 可移到 OPA runtime                |

選 OPA 的核心訴求：*跨 enforcement point 的 unified policy* + *long-term policy 資產化* + *audit-grade decision log* + 團隊願意投資 Rego。純 K8s + 想快速上手用 [Kyverno](/backend/07-security-data-protection/vendors/kyverno/)；K8s + 已決定走 OPA 生態用 [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/)；只跑 CI 不跑 runtime 用 [Conftest](/backend/07-security-data-protection/vendors/conftest/)。

## 進階主題

**Rego idioms（policy library + base policy）**：production Rego 走分層結構 — `lib/`（utility function、registry whitelist、CIDR check）、`base/`（concrete policy、引用 lib）、`tests/`（用 `opa test` 跑 unit test）。Policy 也是 code、走 PR review + CI test + staging tenant、不是 console 直改。

**Partial evaluation for SQL row-level filter**：把 policy 寫成「user 能看哪些 row」、用 `opa eval --partial` 把 `user="alice"` 部分 pre-evaluate、output 殘餘 query 變 SQL `WHERE tenant_id IN ('a', 'b', 'c')`、application 拼進 query。意義是 *policy 不在 query path latency 上*、policy 規則仍是 SSoT。對應 RLS（row-level security）的工程化作法。

**跟 [SPIRE](/backend/07-security-data-protection/vendors/spire/) workload identity 整合 authz**：service-to-service authz 場景、SPIRE 簽 SVID（SPIFFE ID + mTLS cert）證明 caller 身份、OPA 拿到 SPIFFE ID 後 decide「這個 service 能呼叫這個 API 嗎」。SPIRE 解 *who*、OPA 解 *can they do this*、職責清楚分離。

**跟 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 整合 dynamic credential policy**：Vault 簽 dynamic credential（DB password / cloud STS token）的 issue 決定可以走 OPA — Vault 收到 issue request、轉 OPA decide「這個 caller 在這個 context 能不能拿這個 scope 的 token」。對應 [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/) 的 lesson：scope 判斷不分散在應用層、集中到 policy engine。

**Decision log 進 SIEM**：OPA decision log 設成 push 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) HEC / Elastic / Datadog、進 SIEM 後可做三件事 — over-permission analysis（哪些 allow 從沒被合法理由觸發）、dead policy detection（哪些 rule 從沒被 evaluate）、anomalous decision pattern（某 service 突然大量 allow 不在 baseline）。

**跟 K8s admission 的兩條路**：純 K8s admission 場景、走 [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/)（OPA 官方 K8s integration、有 Constraint Framework 抽象、社群活躍）比直接跑 OPA + kube-mgmt sidecar 更 production-ready。kube-mgmt 路線適合 already-running OPA 想加 K8s admission 而不引入 Gatekeeper 抽象。

## 排錯與失敗快速判讀

- **Rego policy review 卡 SRE**：policy 都得 SRE 寫、security team 看不懂 — 拆 `lib/` 給 SRE 維護、`base/` 給 security review、用 `opa test` unit test 保持迭代速度
- **Bundle distribution 慢 / policy 不一致**：自管 nginx bundle server 沒高可用、agent pull 失敗 fallback 用舊版 — 換 OPAL push model 或 S3 + CloudFront、bundle pull 失敗時 OPA `--set status.console=true` 直接 alert
- **Decision log 沒進 SIEM**：OPA 開了 decision log 但只進本地 file、沒人看 — 設 decision log plugin push 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) HEC / Kafka、不是寫本地 disk
- **Policy 改完 production 大量 deny**：新 policy 沒在 staging dry-run、上 production 後合法 traffic 被擋 — Styra DAS 的 impact analysis 或自己跑 `opa eval --partial` 對歷史 decision log replay、看 deny 數量再 promote
- **OPA latency 高 / API 卡**：每個 request 都 round-trip OPA、policy 複雜 evaluation 慢 — embed OPA as library（Go SDK / WASM）跑 in-process、或用 partial evaluation 把 policy compile 進 SQL / regex
- **Rego policy bug 線上才發現**：沒 unit test、staging 沒 cover edge case — 強制 PR 要含 `opa test` case、staging 跑 shadow mode（log only 不 enforce）24hr 再切 enforce
- **跨 cluster policy drift**：多 cluster 各自 apply、版本不同步 — OPAL 或 Styra DAS multi-cluster sync、不靠 kubectl apply 人工同步

## 何時改走其他服務

| 需求形狀                                                 | 改走                                                                                                                                                  |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| K8s admission only + YAML-friendly                       | [Kyverno](/backend/07-security-data-protection/vendors/kyverno/)                                                                                      |
| K8s admission + 已選 OPA 生態                            | [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/)                                                                                |
| CI pre-deploy check（Terraform / K8s YAML / Dockerfile） | [Conftest](/backend/07-security-data-protection/vendors/conftest/)                                                                                    |
| Runtime container behavior（不是 admission）             | [Falco](/backend/07-security-data-protection/vendors/)                                                                                                |
| Image scan + vulnerability policy                        | [Trivy](/backend/07-security-data-protection/vendors/trivy/)（scan）+ OPA（gate）                                                                     |
| Workload identity / mTLS                                 | [SPIRE](/backend/07-security-data-protection/vendors/spire/) + OPA（identity → authz 分工）                                                           |
| Cloud IAM policy（AWS / GCP / Azure 本體）               | [AWS IAM](/backend/07-security-data-protection/vendors/aws-iam/) / [Google Cloud IAM](/backend/07-security-data-protection/vendors/google-cloud-iam/) |
| Decision log → SIEM                                      | [Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)   |

## 不在本頁內的主題

- Rego 完整語法 reference（rule / function / built-in / `with` / `some`）
- Gatekeeper Constraint Framework 的 ConstraintTemplate / Constraint CRD 設計細節（屬 Gatekeeper 頁）
- Conftest CLI 用法跟 `conftest test` / `conftest verify` 流程（屬 Conftest 頁）
- Kyverno YAML policy 語法跟 mutate / generate / verifyImages（屬 Kyverno 頁）
- Styra DAS 商業 license / SKU 對照、Nirmata Enterprise 對照
- WASM-compiled Rego policy 的 edge deployment 細節

## 案例回寫

| 案例                                                                                                                                   | 跟 OPA 的關係（對照啟示）                                                                                                                                      |
| -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                 | OPA admission policy 在 K8s 擋住未簽章 image deploy、配合 cosign signature verify 補 supply chain 信任鏈、policy 集中不分散到各 deployment                     |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/) | OPA admission 配合 [Trivy](/backend/07-security-data-protection/vendors/trivy/) scan result 擋住已知 vulnerable image deploy、policy 走「critical CVE = deny」 |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)    | OPA 控制 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) dynamic credential issuance policy、scope 判斷集中不分散到應用層各自 if-else   |
| [7.12 供應鏈完整性 (section)](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)                         | OPA 是 admission gate 的核心工具、跟 SLSA provenance / cosign signature 組合做 policy enforcement、不是看一兩個欄位放行                                        |
| [Policy as Code Foundations (section)](/backend/07-security-data-protection/security-as-risk-routing-system/)                          | OPA 對應 policy-as-code 的 *decoupled decision + enforcement*、跨 enforcement point 共用 policy 是設計核心、不是「再寫一份 K8s policy」                        |

## 下一步路由

- 上游：[7 章 policy-as-code foundations](/backend/07-security-data-protection/security-as-risk-routing-system/)、[7.12 供應鏈完整性](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- 平行（Policy-as-Code 批次）：[Conftest](/backend/07-security-data-protection/vendors/conftest/)（CI static check）、[Kyverno](/backend/07-security-data-protection/vendors/kyverno/)（K8s YAML-native）、[Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/)（OPA K8s integration）
- 跨類：[SPIRE](/backend/07-security-data-protection/vendors/spire/)（workload identity → OPA authz）、[Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（dynamic credential policy）、[Trivy](/backend/07-security-data-protection/vendors/trivy/)（scan → OPA gate）、[Splunk](/backend/07-security-data-protection/vendors/splunk/)（decision log → SIEM）
- 跨模組：[6 reliability](/backend/06-reliability/)（CI pre-deploy gate 接 Conftest）、[8 incident response](/backend/08-incident-response/)（policy violation alert → IR routing）
- 官方：[Open Policy Agent](https://www.openpolicyagent.org/)、[Rego Policy Language](https://www.openpolicyagent.org/docs/latest/policy-language/)、[Styra DAS](https://www.styra.com/)、[OPAL](https://github.com/permitio/opal)
