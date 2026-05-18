---
title: "Conftest"
date: 2026-05-18
description: "OPA CLI wrapper for static config policy check、Rego policy + 多 parser（Terraform / K8s / Dockerfile / JSON）、CI-time gate"
weight: 23
tags: ["backend", "security", "vendor", "conftest", "policy-as-code", "ci-cd", "open-source"]
---

Conftest 是 *OPA CLI wrapper for static config policy check*、Open Policy Agent project 旗下的 CLI 工具、Apache 2.0 OSS、無商業版。它的核心定位不是 admission runtime、而是 *CI-time policy gate*：在 git commit / PR / merge 階段、用 Rego policy 對 config file（Terraform HCL / K8s YAML / Dockerfile / JSON / TOML / INI / serverless.yml）做 static check、把 misconfiguration 攔在 deploy 之前。跟 [OPA](/backend/07-security-data-protection/vendors/opa/) / [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/) Config 的差異不在 *規則表達力*、而在 *執行時機 + 客製化方式*。

## 服務定位

Conftest 是 OPA 生態中 *最輕量的 CI-time tool* — 拿一份 Rego policy + 一份 config file、跑 `conftest test` 就出 violation report。它不需要 cluster、不需要 daemon、不接 admission webhook、只是個 binary。跟 [OPA](/backend/07-security-data-protection/vendors/opa/) 比、OPA 是 *runtime decision engine*（HTTP server / library / sidecar 提供 policy decision）、Conftest 只是 *CLI 跑 once、結束即關*。跟 [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) 比、Gatekeeper 是 *K8s admission controller runtime*、會在 kubectl apply 時攔下違規；Conftest 是在 PR 階段就攔下、deploy 前就 fail CI。跟 [Kyverno](/backend/07-security-data-protection/vendors/kyverno/) 比、Kyverno 是 K8s-only 的 admission policy（YAML 語法）、Conftest 跨多 config format（不只 K8s）且用 Rego。跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) Config 比、Trivy Config 是 *built-in misconfig rule*（開箱即用、預定義常見 anti-pattern）、Conftest 是 *自己寫 Rego policy*（客製化彈性大但要寫 rule）。

關鍵張力：*CI-time static check* ↔ *runtime admission enforcement* 是兩種互補機制、不是替代。CI 抓在 deploy 之前、但 manifest 不一定都走 PR（kubectl apply 直接打 cluster 就漏接）；admission 抓 runtime 寫入、但 deploy 後才 fail 已經慢。production 通常 CI（Conftest / Trivy Config）+ admission（Gatekeeper / Kyverno）雙層覆蓋。

## 本章目標

讀完本頁、讀者能判斷：

1. Conftest 在 policy-as-code stack 中承擔哪一段（CI gate）、跟 admission runtime 怎麼分工
2. Rego policy directory / `conftest test` / `conftest verify` / Bundle / Combine flag 的 ownership 跟工程化做法
3. Conftest vs Trivy Config vs Checkov vs OPA + custom CI wrapper 的取捨
4. 何時用 Conftest、何時走 Trivy Config（不想學 Rego）或 Gatekeeper（runtime enforcement）

## 最短判讀路徑

判斷 Conftest 導入是否健康、最少看四件事：

- **Policy directory 走版控**：Rego files（`policy/*.rego`）跟 application code 同 repo、或抽到中央 policy repo + Bundle 拉取、PR review 才能改 policy
- **`conftest verify` 是否跑**：Rego policy 本身有單元測試（`*_test.rego`）、policy 改動有 test coverage、不是寫完就上 production CI
- **CI integration 點**：跑在 PR check / merge gate、fail 阻斷 merge、不是只跑 warning 沒人看
- **跟 admission 是否雙層**：CI fail 之外、cluster 也裝 [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) / [Kyverno](/backend/07-security-data-protection/vendors/kyverno/) 接 runtime；否則 kubectl apply 繞過 CI 就破口

四件事任一缺失、就是 [Supply Chain Integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 邊界的待補項目。

## 日常操作與決策形狀

**Policy directory（Rego files）**：Conftest 預設讀 `./policy/` 目錄下所有 `*.rego` 檔。Policy 用 `deny[msg]` / `warn[msg]` / `violation[msg]` rule 表達 — `deny` 失敗整個 test、`warn` 只 print 不 fail、`violation` 給結構化輸出（含 metadata 給後續 SOAR 處理）。慣例是一個 policy 檔對一個 anti-pattern（`policy/k8s_privileged.rego` / `policy/terraform_public_s3.rego`）、不混寫。

**`conftest test` command**：`conftest test deployment.yaml` / `conftest test --policy ./custom-policy terraform.plan.json` 是日常入口。支援 `--all-namespaces`（K8s 多 manifest）、`--input`（強制 parser 類型）、`--combine`（跨檔 check）、`--output json|tap|table`（CI 報表格式）。CI integration 通常 `conftest test infra/**/*.yaml --output github` 直接 emit GitHub Actions annotation。

**Parser（多 format 支援）**：Conftest 原生支援 HCL（Terraform）/ YAML / JSON / TOML / INI / Dockerfile / CUE / Jsonnet / EDN / XML / VCL（Fastly）/ Cyclonedx SBOM 等。同一份 Rego 可跑多 format — parser 把不同 format normalize 成 Rego input JSON、policy 寫 `input.spec.containers[_].securityContext.privileged == true` 不管原本是 YAML 還是 JSON。這是 Conftest 比 Checkov / Trivy Config 客製化彈性更大的關鍵：同一個 policy 引擎處理跨 format misconfig。

**Combine flag（跨檔 check）**：`conftest test --combine *.yaml` 把多檔合併成單一 input array、policy 可跨檔 reference。實務場景：K8s deployment 必須有對應 service + configmap + networkpolicy、缺一就 fail；Terraform module 跨檔 reference（VPC + subnet + security group）必須一致。沒有 Combine 就只能單檔檢查、跨檔 invariant 抓不到。

**`conftest verify`（policy unit test）**：Policy 本身要有測試 — `policy/k8s_privileged_test.rego` 寫 `test_privileged_denied` / `test_non_privileged_allowed`、`conftest verify` 跑這些測試。Policy 改動先跑 verify、再 merge policy 到 production CI。沒做 verify 的 policy 是「policy 自己 broken 沒人發現」的常見破口。

**Bundle（OPA bundle 拉 policy）**：`conftest pull` 從 OCI registry / HTTP / git / S3 拉 policy bundle、policy 集中在 central repo、各 service repo 不重複維護。Bundle 包含 Rego files + data files + manifest、可簽章驗證（配 [Sigstore cosign](https://docs.sigstore.dev/)）。大組織通常 platform team 維護 policy bundle、application team 在 CI 拉最新版本跑。

**CI integration**：GitHub Actions（`open-policy-agent/conftest-action`）/ GitLab CI / Jenkins / CircleCI 都有現成 step。跑點通常在 PR check 階段（review 前 fail fast）+ merge gate（防止繞過）。失敗訊息含 file / line / policy name、SOC / SRE 看 annotation 就知道哪行違規。

## 核心取捨表

| 取捨維度    | Conftest                             | Trivy Config                          | Checkov                           | OPA + custom CI wrapper            |
| ----------- | ------------------------------------ | ------------------------------------- | --------------------------------- | ---------------------------------- |
| 規則來源    | 自己寫 Rego（彈性大、要學 Rego）     | 內建 misconfig rule（開箱即用）       | 內建 + 自訂 Python rule           | 自己寫 Rego + 自己包 CI            |
| 學習曲線    | 中 — Rego 語法 + Conftest CLI        | 緩 — `trivy config` 一個指令          | 緩 — 內建 rule、自訂 Python 稍重  | 陡 — Rego + 自己組 CI 跑點         |
| Format 支援 | 廣 — Terraform / K8s / Dockerfile 等 | 中 — Terraform / K8s / CloudFormation | 中 — Terraform / K8s / Serverless | 看自己包                           |
| 客製彈性    | 高 — 任意 Rego policy                | 低 — 內建 rule、客製要寫 plugin       | 中 — Python custom rule           | 高                                 |
| 跨檔 check  | 強 — `--combine` flag                | 弱 — 主要單檔                         | 中                                | 看自己寫                           |
| Policy 共享 | OPA Bundle（OCI / git / HTTP）       | Trivy DB（中央更新）                  | Checkov rule pack                 | 自己管                             |
| 計費        | OSS Apache 2.0                       | OSS（Aqua 商業版有加值）              | OSS（Bridgecrew 商業版）          | OSS（OPA）                         |
| 適合場景    | 客製化 policy、Rego 已用、跨 format  | 開箱即用、團隊不想學 Rego             | Terraform-heavy、Python team 熟   | OPA 已是 runtime、CI 想複用 policy |

選 Conftest 的核心訴求：*組織有 custom policy 需求* + *已用 OPA / Rego（admission 走 Gatekeeper、CI 走 Conftest 統一語言）* + *跨多 config format 需要同一個 policy 引擎*。如果只是要 K8s privileged container / Terraform public S3 這類常見 anti-pattern 攔截、直接 Trivy Config 開箱即用更划算。

## 進階主題

**`conftest verify`（policy unit test lifecycle）**：Policy 是 code、code 要有測試。`policy/k8s_privileged_test.rego` 寫 `test_privileged_denied { count(deny) > 0 with input as {...} }`、CI 跑 `conftest verify ./policy` 把 policy test 當 unit test。Policy change 走 PR → verify pass → 部署到 central bundle → application CI 拉新版本。沒 verify 的 policy 是「沒人知道 policy 自己壞掉、所有 application CI 都 silently pass」的 systemic 風險。

**Bundle 從 OCI registry pull + 簽章驗證**：`conftest pull oci://registry.example.com/policy-bundle:v1.2.3` 從 OCI registry 拉 policy bundle、policy distribution 走 container image 同一套 supply chain。配 [Sigstore cosign](https://docs.sigstore.dev/) 簽章驗證、policy bundle 也走 [7.12 供應鏈完整性](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 的 release gate 邏輯 — policy 本身就是 artifact、需要 signing + verification。

**跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) Config 混用**：實務上 *Trivy Config 跑預設 rule*（CIS / NSA / OWASP baseline、開箱即用）+ *Conftest 跑客製 rule*（organization-specific：必須有特定 label、必須走特定 namespace、必須引用特定 ConfigMap）。兩者 CI 階段都跑、報表合併。不是二選一、是 baseline + custom 的分工。

**跟 admission 雙層**：CI 階段 Conftest fail 之外、cluster 也裝 [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) 接 admission。Gatekeeper 用 ConstraintTemplate（也是 Rego）、同一份 Rego policy 理論上 CI / runtime 共用 — 但實務上 admission 場景跟 static check 場景的 input shape 不同（admission 拿 AdmissionReview object、static 拿 raw manifest）、policy 通常分兩份維護或寫 abstraction layer 共用。

## 排錯與失敗快速判讀

- **Policy pass 但 production 還是 misconfig**：CI 沒卡在 merge gate、或有 `kubectl apply` 繞過 PR — 加 admission controller（[Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) / [Kyverno](/backend/07-security-data-protection/vendors/kyverno/)）做 runtime 雙層
- **Rego policy 自己 broken / silently pass**：沒寫 `*_test.rego` + `conftest verify` — 補 policy unit test、CI 跑 verify 才 promote
- **`conftest test` 跑出 0 violations 但 manifest 有問題**：policy directory 沒讀對、或 parser 自動偵測選錯 — 顯式 `--policy ./policy --input yaml`
- **跨檔 invariant 抓不到**（deployment 沒對應 service）：忘記用 `--combine` flag — 改 `conftest test --combine *.yaml`
- **Bundle 拉到舊版本 / policy drift**：沒固定 bundle tag、用 `latest` 漂移 — bundle reference 用 digest（`sha256:...`）或 immutable tag
- **False positive 多 / team 開始 ignore CI**：policy 寫得太寬、沒考慮合理例外 — Rego 加 exception list（`data.exceptions`）、走 [Exception Workflow](/backend/07-security-data-protection/blue-team/) lifecycle
- **Policy 散落各 application repo / 維護不一致**：沒走 central bundle — 抽 policy 到中央 repo、各 application 拉 bundle

## 何時改走其他服務

| 需求形狀                      | 改走                                                                                                                                      |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 開箱即用、不想學 Rego         | [Trivy Config](/backend/07-security-data-protection/vendors/trivy/)                                                                       |
| K8s admission runtime         | [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) / [Kyverno](/backend/07-security-data-protection/vendors/kyverno/) |
| Runtime application policy    | [OPA](/backend/07-security-data-protection/vendors/opa/)                                                                                  |
| Terraform-heavy + Python team | Checkov / tfsec                                                                                                                           |
| Cloud-native CNAPP            | Wiz / Prisma Cloud                                                                                                                        |

## 不在本頁內的主題

- Rego 完整語法 reference、`every` / `walk` / built-in function 進階用法
- OPA Bundle 的 server-side 實作（policy publish pipeline）
- Conftest 跟 Open Policy Agent runtime 的內部架構差異
- Sigstore cosign 的 keyless signing flow 細節

## 案例回寫

Conftest 在 07 案例庫沒有直接 vendor-level 事件、但所有 supply chain case 都是 CI-time policy gate 的對照：

| 案例                                                                                                                                   | 跟 Conftest 的關係（對照啟示）                                                                                                              |
| -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                 | Conftest 在 CI 階段檢查 Terraform / K8s manifest 是否符合 image signing policy（image 必須來自 signed registry、必須有 cosign attestation） |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/) | Conftest 配 SBOM 檔案做 CI-time vulnerable component check、補 admission 之前的 gate（image 含 log4j-core <2.17 直接 PR fail）              |
| [7.12 供應鏈完整性 (section)](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)                         | Conftest 是 release gate 在 CI 階段的 policy enforcement 工具、跟 admission 雙層覆蓋、policy bundle 本身也走 cosign 簽章 supply chain       |

## 下一步路由

- 上游：[7.12 供應鏈完整性與 artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- 平行：[OPA](/backend/07-security-data-protection/vendors/opa/)、[Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/)、[Kyverno](/backend/07-security-data-protection/vendors/kyverno/)、[Trivy](/backend/07-security-data-protection/vendors/trivy/)
- 跨類：[GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/)（CI security check pipeline 共用）
- 官方：[Conftest Documentation](https://www.conftest.dev/)
