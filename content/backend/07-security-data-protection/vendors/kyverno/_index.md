---
title: "Kyverno"
date: 2026-05-18
description: "K8s-native policy engine、YAML policy（非 Rego）、五類 rule（Validate / Mutate / Generate / Verify Images / Cleanup）、CNCF Incubating"
weight: 21
tags: ["backend", "security", "vendor", "kyverno", "policy-as-code", "kubernetes"]
---

Kyverno 是 K8s-native 的 policy engine、CNCF Incubating（2024 升級）、設計 mindset 把 *policy 寫成 YAML* 而不是引入新語言（vs [OPA](/backend/07-security-data-protection/vendors/opa/) 的 Rego、[Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) 也用 Rego）。它的核心不是「更輕量的 OPA」、而是 *K8s 專用 policy engine* — 把 Validate / Mutate / Generate / Verify Images / Cleanup 五類動作做成 first-class rule type、跟 K8s admission webhook + GitOps + cosign / Sigstore ecosystem 深度整合。

## 服務定位

Kyverno 的定位是 *K8s admission controller-shaped policy engine、policy 用 YAML 表達*。底層是 dynamic admission webhook + background controller、頂層 CRD 包含 *ClusterPolicy*（cluster 範圍）/ *Policy*（namespace 範圍）/ *PolicyException*（明確例外）/ *ClusterCleanupPolicy*（過期 resource 清理）/ *PolicyReport*（CIS / NIST 等審計輸出）。Nirmata 是 Kyverno 商業版、補 policy library / multi-cluster management / audit dashboard / 24x7 support。

跟 [OPA](/backend/07-security-data-protection/vendors/opa/) 比、Kyverno 走 *narrow + opinionated* — OPA 是 general-purpose policy engine（K8s / API gateway / Terraform / 自家服務都能用、語言是 Rego）、Kyverno *K8s-only + YAML*、學習成本對 K8s admin 接近零。跟 [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/) 比、Gatekeeper 也是 K8s admission controller 但底層用 OPA + Rego、ConstraintTemplate / Constraint 兩層 CRD；Kyverno 不用 Rego、policy 就是 YAML rule list。跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) 的 misconfig scan 比、Trivy 是 *scan static manifest*、Kyverno 是 *admission gate + background scan*、定位互補不衝突。

關鍵張力：*YAML policy 的表達力上限* ↔ *跨平台統一 policy 的訴求*。Kyverno YAML rule 對 90% K8s 場景夠用、但需要跨 K8s / API gateway / Terraform 統一 policy decision 時、Rego 的表達力跟可移植性勝出。要看清楚 policy *邊界是否就在 K8s 內*。

## 本章目標

讀完本頁、讀者能判斷：

1. Kyverno 在 K8s 治理 stack 中承擔哪一段（admission gate / mutation / generation / image verify / cleanup）、跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) scan / [SBOM Tools](/backend/07-security-data-protection/vendors/syft-grype/) / Sigstore cosign 怎麼分工
2. ClusterPolicy / Policy 的 ownership 設計（platform team 還是 app team 寫、誰 review、PolicyException 怎麼治理）
3. Validate / Mutate / Generate / Verify Images / Cleanup 五類 rule 的使用邊界跟陷阱
4. 何時用 Kyverno、何時走 OPA / Gatekeeper / K8s native ValidatingAdmissionPolicy 的取捨

## 最短判讀路徑

判斷 Kyverno deployment 是否健康、最少看四件事：

- **Policy 是否走 GitOps**：ClusterPolicy / Policy 是否在 Git 版控、走 ArgoCD / Flux sync、policy change 是否經 PR review、staging cluster 跑過 audit mode 才 promote 到 enforce
- **Mode 配置**：每條 policy 是 *Audit*（只記、不擋）還是 *Enforce*（擋 admission）、新規則是否先 audit 觀察 24-48hr 再 enforce、Background scan 是否開（補 admission 不到的 historical drift）
- **Verify Images 啟用度**：production cluster 是否要求 image 必須通過 cosign signature verify、SBOM attestation 是否驗、policy 是否包含 keyless verify（Fulcio + Rekor）
- **PolicyException 治理**：例外是否走 PR 申請 + 到期日 + owner、跟 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 的 exception governance 對齊

四件事任一缺失、就是 [7.12 供應鏈完整性](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 邊界的待補項目。

## 日常操作與決策形狀

**ClusterPolicy / Policy 結構**：Kyverno policy 是 K8s CRD、結構 `spec.rules[]` 一條條 rule、每條 rule 有 `match`（套用對象、kind / namespace / label / name）+ `exclude`（明確排除）+ rule body（`validate` / `mutate` / `generate` / `verifyImages` / `cleanup` 五選一）。ClusterPolicy 套整個 cluster、Policy 套單一 namespace、app team 通常只能改自家 namespace 的 Policy、平台 team 控 ClusterPolicy。

**Validate rule**：admission 階段檢查 manifest 是否符合條件、不符合就拒絕。最常見場景 — 禁止 `latest` tag、要求所有 pod 有 resource limit、禁止 privileged container、要求 specific label。寫法是 `validate.pattern` 或 `validate.deny`（後者支援更複雜的 boolean expression）、output 是 admission webhook reject。Validate 是 *K8s policy as code* 的入門場景、80% 的 ClusterPolicy 都是 Validate rule。

**Mutate rule**：admission 階段修改 manifest、把缺的欄位補上或改成符合的值。常見場景 — 自動注入 sidecar（service mesh proxy / log forwarder）、自動加 resource limit default、自動加 label（cost center / owner）、自動把 imagePullPolicy 改成 `Always`。Mutate 是 OPA / Gatekeeper 做不到的（兩者都偏 Validate-only）、是 Kyverno 的 *K8s-specific 強項*。陷阱是 mutate 變更後 GitOps diff 會永遠不一致、要在 ArgoCD ignoreDifferences 上對齊。

**Generate rule**：cluster event（namespace 建立、resource 變動）觸發、自動建立 *關聯 resource*。最常見場景 — 新 namespace 自動建 default NetworkPolicy（deny-all egress 起手）、自動建 ResourceQuota / LimitRange、自動 copy ConfigMap / Secret 到新 namespace。Generate 是把 *security default* 從文件層落到 runtime layer、避免 app team 忘記設 NetworkPolicy 就把整個 cluster 暴露。Generate 也是 OPA / Gatekeeper 做不到、Kyverno 獨有。

**Verify Images rule**：admission 階段驗證 container image 的簽章 / SBOM attestation / in-toto provenance。實作底層 [Sigstore](https://docs.sigstore.dev/) cosign — keyless 簽章驗 Fulcio CA + Rekor transparency log、key-based 驗 public key、attestation 驗 SLSA provenance / SBOM。production 場景 — internal registry image 必須 cosign 簽 + 來自 trusted CI runner、external image 必須在 allowlist。對應 [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/) 的 supply chain attack 防禦邊界。

**Cleanup policy**：ClusterCleanupPolicy / CleanupPolicy 是 K8s 1.27+ 引入、Kyverno 1.10+ 支援、按 cron 跑、清掉符合條件的 resource。常見場景 — 過 30 天的 completed Job、過 7 天的 failed Pod、ephemeral namespace（PR preview env）超過 TTL 自動刪。Cleanup 補的是 K8s 沒有 *resource lifecycle policy* 的洞、TTL controller 只覆蓋 Job / Pod 子集。

**Background scan**：除了 admission 攔截 *新 resource*、Kyverno 定期掃描 *已存在 resource* 是否違反 policy、結果寫入 PolicyReport CRD。意義是補 *歷史 drift* — policy 是後來加的、已 deploy 的 resource 不會被 admission 攔到、background scan 才會找出來。production 一定要開、不開等於 policy 只防新犯不抓舊案。

**ValidatingAdmissionPolicy (VAP) 整合**：K8s 1.30+ 內建 CEL-based admission policy、不需要 admission webhook（VAP 由 kube-apiserver 直接 enforce、延遲低、不會因為 Kyverno pod 掛掉就讓 admission 失敗）。Kyverno 1.11+ 可以從 ClusterPolicy *生成* VAP、把簡單 Validate rule 卸載給 K8s native engine、複雜 rule（Mutate / Generate / Verify Images）留在 Kyverno。長期趨勢 — K8s native VAP 會吃掉 Kyverno *Validate-only* 的場景、Mutate / Generate / Verify Images 仍是 Kyverno 護城河。

**GitOps 整合**：ClusterPolicy / Policy 是普通 K8s CRD、走 ArgoCD / Flux sync 沒任何特殊性。staging cluster 跑 Audit mode 24-48hr 看 PolicyReport 有多少違規 → tune rule 或加 PolicyException → 確認沒誤殺再 promote 到 production cluster 的 Enforce mode。對應 [Detection Engineering Lifecycle](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/) 的 propose → staging → promote pattern。

**Policy Reporter**：OSS dashboard（不是 Kyverno 內建、是社群專案）、把 PolicyReport CRD 視覺化、給 platform team / app team 看 cluster 違規概況。Nirmata 商業版有更完整的 multi-cluster dashboard + 歷史 trend + compliance mapping（CIS / NIST / PCI）。

## 核心取捨表

| 取捨維度         | Kyverno                                                | OPA + Gatekeeper                              | OPA standalone                          | Conftest                                  |
| ---------------- | ------------------------------------------------------ | --------------------------------------------- | --------------------------------------- | ----------------------------------------- |
| Policy 語言      | YAML（patterns / deny / preconditions）                | Rego（DSL、表達力強）                         | Rego                                    | Rego                                      |
| 覆蓋範圍         | K8s only                                               | K8s only                                      | K8s / API / Terraform / 任意 JSON 輸入  | CI-time static file（Terraform / Docker） |
| Rule 類型        | Validate / Mutate / Generate / Verify Images / Cleanup | Validate-only（Mutate 是 experimental）       | 由 host application 決定                | Validate（CI-time）                       |
| 部署形態         | K8s admission webhook + controller                     | K8s admission webhook（Gatekeeper 是 OPA 包） | sidecar / library / standalone server   | CLI（CI pipeline）                        |
| 學習曲線         | 緩 — K8s admin 已熟 YAML                               | 陡 — 要學 Rego                                | 陡 — 要學 Rego + host integration       | 中 — Rego 但範圍小                        |
| Image signature  | 內建 Verify Images（cosign + Sigstore）                | 需自己接 cosign CLI                           | 需自己接                                | 不適用                                    |
| Background scan  | 內建                                                   | gator audit（弱）                             | 不適用                                  | 不適用                                    |
| 跨 platform 一致 | 弱 — K8s only                                          | 弱 — K8s only                                 | 強 — 同份 Rego 跑 K8s / API / Terraform | 強 — CI 跑同份 Rego                       |
| 適合場景         | K8s-heavy + 想用 YAML + 需 Mutate / Generate / Image   | K8s + 已有 Rego 投資 + Validate-only          | 跨 K8s / API / Terraform 統一 policy    | CI-time pre-merge 檢查                    |
| 退場成本         | 中 — YAML rule 跟 K8s CRD 綁                           | 中 — Rego 可移植到 OPA standalone             | 低 — Rego 跨平台                        | 低                                        |

選 Kyverno 的核心訴求：*K8s-only 場景 + 不想學 Rego + 需要 Mutate / Generate / Verify Images 的 K8s-specific 能力*。團隊已投資 Rego ecosystem、或 policy 邊界跨 K8s + Terraform + API gateway、走 OPA / Gatekeeper 更合適。CI-time pre-merge 檢查走 Conftest 補位。

## 進階主題

**Verify Images 進階 — cosign keyless + SBOM attestation**：production-grade image trust 不只驗 signature、要驗 *who signed it from where with what build process*。keyless 模式驗 Fulcio CA-issued 短期憑證 + Rekor transparency log entry、確認簽章來自 trusted CI runner 的 OIDC identity（例如 `https://github.com/myorg/myrepo/.github/workflows/release.yaml@refs/tags/v*`）。SBOM attestation 用 `verifyImages.attestations` 驗 in-toto envelope、確認 image 帶 SLSA provenance + SBOM（[CycloneDX / SPDX](/backend/07-security-data-protection/vendors/syft-grype/)）。對應 [XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/) 的 lesson：maintainer takeover 也能簽 image、要靠 build provenance attestation 看出 build process 跟過去不一致。

**Mutate policy 跟 GitOps 的張力**：Mutate 自動補欄位、ArgoCD / Flux 會永遠看到 live state 跟 Git state diff。處理方式有三 — *ignoreDifferences* on specific fields（ArgoCD `spec.ignoreDifferences`、Flux `spec.patches`）、*把 mutate 改成 validate + 在 PR template 補預設*（成本高但 GitOps diff 乾淨）、*Mutate at create only*（用 `mutate.mutateExistingOnPolicyUpdate: false`、只在 admission 動、不重複 mutate existing resource）。

**Generate policy 跟 multi-tenant security default**：新 namespace 一建立、Generate rule 自動建 default-deny NetworkPolicy + ResourceQuota + LimitRange + 必要 RoleBinding。意義是 *security default 從 README 落到 runtime*、app team 開新 namespace 不會忘記設安全邊界。陷阱是 generated resource 的 ownership — 預設 Kyverno owns、app team 修改會被 reconcile 回去；要讓 app team 改、用 `synchronize: false`。

**Nirmata Enterprise**：商業版補三件事 — *Policy Library*（CIS / NIST / PCI / SOC 2 預製 policy pack）、*Multi-cluster Management*（中央 console 推 policy 到多 cluster + audit dashboard + drift detection）、*Policy Reporter Plus*（trend + compliance mapping + JIRA / Slack integration）。對大企業多 cluster + 合規驅動的場景值得評估、中小 deployment OSS Kyverno + 社群 Policy Reporter 夠用。

**PolicyException 治理**：Kyverno 1.9+ 引入 PolicyException CRD、讓特定 resource 明確繞過特定 policy、避免「app team 為了 deploy 直接把 policy 改寬」。Exception 走 PR + 到期日 + owner、跟 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 的 exception lifecycle 對齊 — 例外不是黑箱、是 *暫時性、有 owner、有 review 日期*。

## 排錯與失敗快速判讀

- **Policy 改了沒生效**：admission webhook 沒 ready、或 policy 寫在錯的 namespace（Policy CRD 是 namespace-scoped、放錯 namespace 不會作用）— `kubectl get clusterpolicies` 看 ready 狀態、`kubectl describe` 看 events
- **Admission 卡住 / Pod 起不來**：Kyverno webhook 掛掉、failurePolicy 設 `Fail` 結果整個 cluster 不能 deploy — production 對 critical workload 設 `failurePolicy: Ignore` + 監控 Kyverno controller availability、不要讓 policy engine 變成 cluster-wide SPOF
- **Mutate 後 ArgoCD 永遠 OutOfSync**：mutate 改的欄位沒在 ArgoCD `ignoreDifferences` 排除 — 對應加 `spec.ignoreDifferences[*].jsonPointers` 或 `.jqPathExpressions`、不然每次 sync 都跳 diff
- **Verify Images 全部失敗**：cluster 沒對外網路、Fulcio / Rekor 拉不到、或 image 真的沒簽 — 先 audit mode 跑 + 看 PolicyReport 統計 unsigned image 比例、確認預期路徑（內部 image 簽 / 外部 image allowlist）後才 enforce
- **Background scan 跑爆 controller**：cluster 太大、scan interval 太短 — 調整 `backgroundScan: false` for 高頻變動 policy、或拉長 scan interval、或 Nirmata 用分散式 scan
- **PolicyException 變成漏洞**：例外沒到期日、owner 離職、規則永久繞過 — Exception CRD 補 metadata（owner / expiry / ticket）+ 定期 audit 過期 Exception
- **VAP migration 不一致**：Kyverno 生成的 VAP 跟原 ClusterPolicy 行為有差（CEL 不支援部分 Kyverno feature）— 對 critical rule 保留 Kyverno 不 migrate、只把簡單 Validate 卸載

## 何時改走其他服務

| 需求形狀                                      | 改走                                                                                                                      |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 跨 K8s + API gateway + Terraform 統一 policy  | [OPA standalone](/backend/07-security-data-protection/vendors/opa/)                                                       |
| K8s only 但團隊已投資 Rego                    | [Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/)                                                    |
| CI-time pre-merge 檢查 Terraform / Dockerfile | Conftest（OPA 系列、CLI-based）                                                                                           |
| Image 漏洞 / misconfig scan（scan, not gate） | [Trivy](/backend/07-security-data-protection/vendors/trivy/) / [Snyk](/backend/07-security-data-protection/vendors/snyk/) |
| SBOM 生成 / 管理                              | [SBOM Tools](/backend/07-security-data-protection/vendors/syft-grype/)                                                    |
| Image signing pipeline                        | Sigstore cosign（CI 簽、Kyverno 驗）                                                                                      |
| K8s 1.30+ 簡單 Validate-only 場景             | K8s native ValidatingAdmissionPolicy（CEL、kube-apiserver 內建）                                                          |

## 不在本頁內的主題

- Kyverno policy 完整 YAML reference、JMESPath 進階用法
- Sigstore cosign CLI 操作、Fulcio / Rekor 部署
- Nirmata Enterprise 詳細功能跟 pricing
- K8s ValidatingAdmissionPolicy CEL 語法 reference
- 跟 service mesh（Istio / Linkerd）整合的 sidecar injection 細節

## 案例回寫

| 案例                                                                                                                                   | 跟 Kyverno 的關係（對照啟示）                                                                                                                                                      |
| -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                 | Kyverno Verify Images policy 強制 production cluster 只 deploy 已 cosign 簽章 + Rekor transparency log entry 的 image、未簽 / 來源異常 image 在 admission 階段擋掉                 |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/) | Kyverno admission policy 配 [Trivy](/backend/07-security-data-protection/vendors/trivy/) scan 結果 — image 帶 vulnerability label 超過閾值就擋 deploy、補 CI scan 沒攔到的舊 image |
| [XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)        | Kyverno Verify Images + SBOM attestation 補位 — maintainer takeover 也能簽 image、但缺乏 SLSA build provenance attestation 會被 Kyverno admission 擋住                             |
| [7.12 供應鏈完整性 (section)](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)                         | Kyverno 是 *K8s admission gate* 的 K8s-specific 落實工具、跟 CI-time SBOM 生成 + cosign 簽章 + Rekor transparency log 組成 supply chain trust chain 的 runtime enforcement 段      |
| [Detection Engineering Lifecycle (section)](/backend/07-security-data-protection/blue-team/detection-engineering-lifecycle/)           | ClusterPolicy / Policy 走 propose → staging audit mode → tune → promote enforce mode 的工程 lifecycle、PolicyException 是 lifecycle 一部分、不是黑箱繞過                           |

## 下一步路由

- 上游：[7.12 供應鏈完整性](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)、[Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[OPA](/backend/07-security-data-protection/vendors/opa/)、[Gatekeeper](/backend/07-security-data-protection/vendors/gatekeeper/)
- 下游：[Trivy](/backend/07-security-data-protection/vendors/trivy/)（scan + label）、[Snyk](/backend/07-security-data-protection/vendors/snyk/)（vuln 資訊源）、[SBOM Tools](/backend/07-security-data-protection/vendors/syft-grype/)（attestation 來源）
- 跨類：Sigstore cosign（CI 簽、Kyverno 驗）、ArgoCD / Flux（GitOps sync policy 本身）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（policy violation → IR routing）
- 官方：[Kyverno Documentation](https://kyverno.io/docs/)、[Sigstore Documentation](https://docs.sigstore.dev/)
