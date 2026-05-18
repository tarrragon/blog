---
title: "Snyk"
date: 2026-05-18
description: "跨 SCM 多模組 application security platform：Open Source (SCA) + Code (SAST) + Container + IaC + Cloud (CSPM)、Reachability analysis"
weight: 5
tags: ["backend", "security", "vendor", "snyk", "sca", "sast", "supply-chain"]
---

Snyk 是 *developer-first* 的 *跨 SCM 多模組 application security platform*、把 SCA、SAST、Container scan、IaC scan、CSPM 整合到一個 dashboard、五大模組共用同一套 Project / Issue / Fix 模型。流量打到 GitHub / GitLab / Bitbucket / Azure Repos 任一 SCM、Snyk 拉取 repo、按 manifest 建 Project、發現 Issue 後送 PR 修補。跟 [GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/) 比、Snyk *跨 SCM* 跟 *跨技術棧*；跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) 比、Snyk 是商業 SaaS、覆蓋面更廣、但年費按 Project 計價。

## 服務定位

Snyk 的核心定位是 *用一個工具一個 dashboard 同時管 SCA + SAST + IaC + Container + Cloud*。五大模組 — *Snyk Open Source*（SCA、依賴漏洞）、*Snyk Code*（SAST）、*Snyk Container*（image scan）、*Snyk IaC*（Terraform / CloudFormation / K8s manifest 安全）、*Snyk Cloud*（CSPM、雲端配置 drift）— 共用 Project / Target / Organization / Issue 模型、Issue 跨模組可一起 prioritize。對 *多 SCM + 多技術棧* 的組織、Snyk 比拼裝 GHAS + Trivy + Dependabot 更整合。

跟 [GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/) 的核心差異是 *部署模型跟 SCM 範圍*：GHAS 綁 GitHub、走 GitHub Actions、PR 整合更深（Code Scanning alert 直接顯示在 PR review）；Snyk 走 SaaS、SCM 中立、但需要 OAuth 連到每個 repo。組織用 GitLab / Bitbucket / Azure Repos 或同時用多種 SCM、Snyk 是天然選擇。

跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) 比、Trivy 是 OSS、主 container + IaC、適合 CI 內 self-hosted；Snyk 商業 SaaS、覆蓋更廣（含 SAST 跟 Reachability）、適合 *組織級 governance + 跨團隊統一 dashboard*。Trivy 是 *跑工具*、Snyk 是 *買治理*。

關鍵張力：Snyk 的 *Project 是計費單位*。每個 manifest 算一個 Project（一個 repo 有 package.json + requirements.txt + Dockerfile = 3 Project）。大 monorepo 容易暴量、需要 *project filter / archive* 治理、否則年費失控。

## 本章目標

讀完本頁、讀者能判斷：

1. Snyk 五大模組在 application security stack 承擔哪一段、哪些靠其他工具
2. Project 計費模型、monorepo 跟 multi-manifest repo 的 Project 暴量風險跟治理路徑
3. Reachability analysis 的價值跟限制、何時減 noise、何時被誤判
4. 何時用 Snyk、何時走 [GHAS](/backend/07-security-data-protection/vendors/github-advanced-security/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/) / [Dependabot](/backend/07-security-data-protection/vendors/dependabot/) 的取捨

## 最短判讀路徑

判斷 Snyk 配置是否健康、最少看四件事：

- **誰能 enable Snyk**：Organization 的 admin / collaborator role 配置、Service Account token scope（不要用 personal API token 跑 CI、用 Service Account + scoped token）、Audit Log 是否同步到 SIEM
- **Project import 治理**：每個 SCM target 自動 import 哪些 manifest、是否有 *project filter* 排除 test fixture / vendored dependency、archived project 是否真的不計費、monorepo 是否走 *.snyk policy file* 控制
- **Reachability analysis 是否啟用**：Snyk Code + Open Source 整合、call graph 分析「我的 code 真的呼叫到 vulnerable 函式嗎」— 大幅減少 *transitive dep 但 unreachable* 的 noise、production 應該啟用
- **SBOM export 是否走 release pipeline**：CycloneDX / SPDX 格式是否定期匯出、是否進 [supply chain integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 流程、合規要求（EO 14028 / NIS2）是否覆蓋

四件事任一缺失、就是 [Audit Log](/backend/knowledge-cards/audit-log/) 與 supply chain 治理邊界的待補項目。

## 日常操作與決策形狀

**Project / Target / Organization 模型**：*Organization* 是計費跟 RBAC 邊界、對應一個團隊或一個 BU。*Target* 是一個 SCM 來源（一個 GitHub repo / 一個 container registry image / 一個 Terraform stack）。*Project* 是 Target 內的單一掃描單位（一個 manifest 或一個 image tag）。Issue 是發現的漏洞 / license / misconfig、有 severity（Critical / High / Medium / Low）、CVSS、exploit maturity、fix availability。Project 暴量的根因通常是 monorepo 內 nested manifest 全被 auto-import、用 `.snyk` 或 import filter 排除。

**五大模組分工**：*Snyk Open Source*（SCA）掃 package manifest（npm、pip、Maven、Go modules、Composer、NuGet 等 20+ 生態）對 Snyk Vulnerability DB（自家維護、補強 NVD 延遲）。*Snyk Code*（SAST）掃源碼、symbolic execution + ML、覆蓋 OWASP Top 10 跟 CWE。*Snyk Container* 掃 image base layer + installed package、支援 Docker / OCI / ECR / GCR / Harbor。*Snyk IaC* 掃 Terraform / CloudFormation / K8s YAML / Helm chart 對 CIS Benchmark + custom policy。*Snyk Cloud*（2023 收購 Fugue 後加入）是 CSPM、scan AWS / Azure / GCP runtime 配置 + IaC drift detection（cloud 實際狀態 vs Terraform 狀態的差異）。

**Snyk Code (SAST) vs GHAS CodeQL**：Snyk Code 走 *快速 inline scan*（秒級回饋、走 cloud inference）、適合 dev loop；CodeQL 走 *深度 dataflow query*（分鐘級、執行更慢但表達力更強）、適合 release gate。同時用兩者並不矛盾 — Snyk Code 在 IDE / PR 給快速訊號、CodeQL 在 release 前跑深度檢查。

**Reachability analysis**：跟 *純 dependency list 比對 CVE* 不同、Snyk 結合 Snyk Code (SAST) 跟 Snyk Open Source (SCA)、做 *call graph 分析*、判斷「我的 code 是否真的呼叫到 vulnerable 函式」。實務影響：多數 transitive dependency 的 CVE 在你的 app 內 *不 reachable*（你引入的 lib 沒呼叫到那條 path）— Reachability 過濾後、可以從 *幾百個 Critical / High* 降到 *幾個真的 exploitable*。限制：只支援部分語言（Java / JS / Python / Go 較完整）、且 dynamic dispatch / reflection / runtime plugin load 會被當成 reachable（false positive）或 unreachable（false negative）— 不可全信、是 *prioritization signal* 不是 *binary verdict*。

**Fix advice / Auto PR**：發現 vuln 後、Snyk 自動發 PR 升級到 *最小 fix version*（包含 transitive dep 的 root cause upgrade）。跟 [Dependabot](/backend/07-security-data-protection/vendors/dependabot/) 功能重疊、差異是 Snyk 跨 SCM（不只 GitHub）、且 fix advice 含 Reachability 標註（reachable vuln 的 PR 優先級高）。重複用兩者要關掉其一、否則 PR 量翻倍。

**跟 CI 整合**：`snyk` CLI（`snyk test` / `snyk monitor` / `snyk container test` / `snyk iac test`）走 SNYK_TOKEN 環境變數、可在任何 CI 跑。官方 Snyk Action（GitHub Actions）跟 Jenkins / GitLab CI / CircleCI plugin 是 wrapper。release gate 推薦在 build 後跑 `snyk test --severity-threshold=high --fail-on=upgradable`、只擋 *可升級* 的 high+ vuln（無 fix 的 vuln 阻塞 release 沒意義、走 *.snyk policy* 暫時 ignore + alert）。

**SBOM export**：`snyk sbom --format=cyclonedx1.4+json` / `--format=spdx2.3+json` 產 SBOM、支援 Snyk attestation（signed SBOM）。近年 supply chain compliance（US EO 14028、EU NIS2 / CRA）要求 SBOM、Snyk 是自動產線之一。SBOM 應該在 *release artifact 旁* 一起發布、走 [supply chain integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 流程。

**License compliance**：除了漏洞、Snyk 也掃 dependency license（GPL / AGPL / LGPL / proprietary / unknown）、可設 *license policy*（allow / disallow / require-review）、PR 引入違規 license 直接 fail check。對需要避開 copyleft license 的商業產品、license scan 跟 vulnerability scan 一樣關鍵。

**API token 治理**：CI / 第三方 integration 用 *Service Account + scoped token*（限 Organization、限 permission）、不要用個人 personal token（離職就失效）。Token 進 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) / [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) / [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/)、定期 rotate。

## 核心取捨表

| 取捨維度       | Snyk                                                | GitHub Advanced Security            | Trivy                                  |
| -------------- | --------------------------------------------------- | ----------------------------------- | -------------------------------------- |
| 部署模型       | 商業 SaaS                                           | GitHub 整合 SaaS                    | OSS、self-hosted CLI                   |
| SCM 範圍       | 跨 SCM（GitHub / GitLab / Bitbucket / Azure Repos） | GitHub only                         | SCM 無關（CI / local 跑）              |
| SCA            | Snyk Open Source（含 Reachability）                 | Dependabot（純 manifest 比對）      | 是、限 OS package + language package   |
| SAST           | Snyk Code（fast inline）                            | CodeQL（dataflow query）            | 否                                     |
| Container scan | Snyk Container                                      | 透過 Dependabot + 第三方            | Trivy Container（主打）                |
| IaC scan       | Snyk IaC                                            | 透過 Code Scanning + KICS / Checkov | Trivy Config（主打）                   |
| CSPM           | Snyk Cloud                                          | 無                                  | 無                                     |
| Reachability   | 有（限部分語言）                                    | 部分 CodeQL query 有                | 無                                     |
| Auto-fix PR    | Snyk PR + fix advice                                | Dependabot PR                       | 無                                     |
| 計費模型       | 按 Project（manifest）數                            | GitHub seat-based                   | 免費                                   |
| 學習曲線       | 中 — UI 友善、CLI 直觀                              | 低 — 跟 GitHub 一體                 | 低 — 單一 binary、CLI 為主             |
| 適合場景       | 多 SCM + 多 stack + 想統一 dashboard                | 純 GitHub + 想跟 PR 深整合          | 純 container / IaC + 想 OSS + 預算敏感 |

選 Snyk 的核心訴求：*組織用多個 SCM 或多技術棧（後端 + 前端 + container + Terraform + cloud）* + 需要 *統一 dashboard + 跨團隊 prioritization* + 接受按 Project 計費的成本。純 GitHub 組織用 GHAS 更整合、純 container CI 用 Trivy 免費、極大型 monorepo 用 Snyk 容易爆 Project 數要小心。

## 進階主題

**Snyk Cloud (CSPM) 跟 IaC drift detection**：Snyk Cloud 連 AWS / Azure / GCP read-only role、掃 runtime 配置（S3 bucket public、IAM over-permission、security group 0.0.0.0/0）對 CIS Benchmark + custom policy。跟 *Snyk IaC* 結合做 *drift detection* — Terraform 內定義是 private bucket、但 cloud 實際是 public（有人 console 手改）、Snyk 報 drift。對標 [Wiz](https://www.wiz.io/) / Prisma Cloud / Lacework、Snyk Cloud 是 *跟 Snyk IaC 同源治理* 的優勢（同個 dashboard 看 IaC + runtime）。

**Custom Rule（Snyk IaC custom policy）**：Snyk IaC 預設規則庫覆蓋 CIS Benchmark + AWS / GCP / Azure 最佳實踐、可寫 *custom policy*（Rego-like / SnykIQL）擴展。例：禁止 RDS 沒開 encryption-at-rest、禁止 S3 沒 versioning、禁止 K8s pod 跑 hostNetwork。Custom policy 走版控（git）跟 PR review、避免在 console 直接改。

**Reachability vs 純 static SCA**：純 SCA（如 Dependabot / Trivy）只看 *manifest 中聲明的版本是否有 CVE*、不分 reachable / unreachable。結果是 Critical / High alert 大量、開發者 *alert fatigue* 後直接 ignore。Snyk Reachability 用 SAST + SCA 整合做 call graph、過濾掉 *vulnerable lib 載入了但 vulnerable 函式從未被呼叫* 的案例。限制：dynamic dispatch / reflection / 動態載入 plugin / native binding 都會讓 reachability 判斷失準、不可當成 binary truth。

**Snyk Insights（風險優先級 prioritization）**：除了 CVSS、Snyk 加入 *exploit maturity*（exploit in-the-wild / PoC / no known exploit）、*fix availability*（有無 fix version）、*social trend*（CVE 被討論度）、*Reachability* 綜合算 *Priority Score*。production 用 Priority Score 排 backlog、而非單純 CVSS — 一個 *Critical 但 unreachable + no fix* 的 vuln 不該擋 release。

**SBOM 流程整合**：把 `snyk sbom` 接到 CI release step、SBOM artifact 跟 release binary 一起進 registry / object store、走 [in-toto attestation](https://in-toto.io/) 或 [SLSA](https://slsa.dev/) provenance 流程、合規時可回溯。跟 [Syft + Grype](/backend/07-security-data-protection/vendors/syft-grype/) 流程的差異：Syft + Grype 是 OSS local-first + Unix philosophy、Snyk 是 SaaS、SBOM 含 Snyk Issue ID 跟 fix advice link。

**License policy enforcement**：除了 vulnerability、license 違規（GPL / AGPL 引入到 proprietary product、unknown license dep）走同套 policy / PR fail-check 機制、production 應該把 license policy 跟 vulnerability policy 並列當 release gate。

## 排錯與失敗快速判讀

- **Project 暴量計費**：monorepo 自動 import 把 test fixture / node_modules-vendored 全當 Project — 用 *.snyk* 跟 import filter 排除、archived project 確認真的不計費
- **Reachability 漏判 / 誤判**：dynamic dispatch / reflection / plugin load 讓 call graph 失準、Critical vuln 被標 unreachable 但實際 reachable — 對 framework-heavy code（Spring / Django middleware / Rails initializer）保守處理、不全信 Reachability
- **PR noise**：Snyk + Dependabot 同時開、依賴升級 PR 翻倍 — 二選一、或讓 Snyk 處理 vuln-driven upgrade、Dependabot 處理 routine version bump
- **CI fail-on 設不對**：`--severity-threshold=low` 把 release 整個擋死 / `--severity-threshold=critical` 漏 high — production 通常 `--severity-threshold=high --fail-on=upgradable`、再用 `.snyk` policy file 例外管理
- **License check 誤殺**：transitive dep 引入 LGPL 被當 GPL 阻擋 — 細分 license policy（allow LGPL-with-dynamic-linking、disallow GPL）、走 review workflow 而非 fail-fast
- **API token over-scoped**：CI 拿到 admin-level Service Account token、整 org Project 都能改 — 改 scoped token、限 Organization + 限 permission、進 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)
- **SBOM 沒進 release pipeline**：SBOM 只在 Snyk dashboard、release artifact 沒附 — 把 `snyk sbom` 加進 CI release step、SBOM 跟 binary 一起發
- **Snyk Cloud drift 沒人看**：CSPM alert 進 dashboard 但沒 routing 到 on-call — 接 [SIEM](/backend/07-security-data-protection/vendors/) / Slack / PagerDuty、高 severity drift 觸發 ticket

## 何時改走其他服務

| 需求形狀                                     | 改走                                                                                               |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 純 GitHub + 想跟 PR / Action 深整合          | [GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/) |
| 純 container / IaC + OSS + 預算敏感          | [Trivy](/backend/07-security-data-protection/vendors/trivy/)                                       |
| 純 dependency 升級（routine version bump）   | [Dependabot](/backend/07-security-data-protection/vendors/dependabot/)                             |
| Secret scanning（leaked API key in repo）    | GitGuardian / Gitleaks（Snyk 不主打）                                                              |
| Runtime container threat detection           | Falco / Cilium Tetragon                                                                            |
| 深度 SAST（dataflow query / taint analysis） | CodeQL / Semgrep（Snyk Code 偏 fast inline、深度查走 CodeQL）                                      |
| CSPM 跨 multi-cloud + asset inventory        | Wiz / Prisma Cloud / Lacework（Snyk Cloud 較新、功能仍在追）                                       |

## 不在本頁內的主題

- Snyk 完整 pricing tier（Team / Business / Enterprise）跟 Project 計費細節
- Snyk Vulnerability DB 跟 NVD / GHSA 的覆蓋差異對照
- Snyk Code SAST 規則完整 reference
- Snyk IaC 內建 policy 完整列表 + CIS Benchmark 對照
- Snyk Cloud 多雲 onboarding 步驟（AWS / Azure / GCP read-only role 設置）

## 案例回寫

Snyk 在 07 案例庫沒有直接 vendor-level 事件、但多個 supply chain 案例展示 Snyk 工具能力的 *範圍跟邊界*：

| 案例                                                                                                                                                     | 跟 Snyk 的關係                                                                                                               |
| -------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)                   | 對照啟示 — Reachability analysis 能快速回答「我的 service 是否真用到 vulnerable JndiLookup」、減少 emergency triage 的 noise |
| [XZ Backdoor 2024 Open Source Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/) | 對照啟示 — Snyk 看 package version + CVE、看不到 maintainer takeover；需補 release-tarball 比對 + maintainer trust signal    |
| [3CX 2023 Desktop App Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/3cx-2023-desktopapp-supply-chain/)                  | 對照啟示 — Snyk Container 看 image 內 package CVE、看不到 update channel 被植入；需配合 artifact provenance / SLSA           |
| [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)                                     | 章節對應 — Snyk SBOM + License policy 是 supply chain governance 的工具、合規門檻（EO 14028 / NIS2）的標準產線之一           |

## 下一步路由

- 上游：[7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- 平行：[GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/)、[Trivy](/backend/07-security-data-protection/vendors/trivy/)、[Dependabot](/backend/07-security-data-protection/vendors/dependabot/)
- 下游：[7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)（vuln 阻擋不完全時、資料層也要遮罩）
- 跨類：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)、[AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/)（Snyk API token 存放）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（Critical CVE 揭露時的 emergency triage routing）
- 官方：[Snyk Documentation](https://docs.snyk.io/)
