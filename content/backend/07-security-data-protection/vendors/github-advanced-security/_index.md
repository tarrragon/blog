---
title: "GitHub Advanced Security"
date: 2026-05-18
description: "GitHub 內建 4 大模組：Code Scanning (CodeQL) + Secret Scanning + Dependency Review + Dependabot、跟 PR / Security tab 深度整合"
weight: 4
tags: ["backend", "security", "vendor", "github-advanced-security", "ghas", "sast", "supply-chain"]
---

GitHub Advanced Security（GHAS）是 GitHub 內建的 *application security platform*、由四大模組組成：*Code Scanning*（CodeQL 為預設 SAST、可接受第三方 SARIF）、*Secret Scanning*（偵測 leaked credential、含 Push Protection 預防 push）、*Dependency Review*（PR 級依賴變更 gate）、*Dependabot*（自動化依賴 update + alert、細節見獨立 vendor 頁）。它跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/) 等獨立 SCA 工具的核心差異是 *跟 GitHub workflow / PR / Security tab 深度整合* — security finding 直接出現在 PR review 跟 organization Security overview、不需另一個 dashboard。

## 服務定位

GHAS 的核心定位是 *把 application security 控制面收斂回 GitHub 平台*：SAST、Secret Scanning、Dependency Review、Dependabot 共用 GitHub 的 identity / permission / PR / branch protection / Actions / Security tab，讓 security finding 跟 code review 在同一個 surface 上決策。這跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) 走「跨 SCM、跨雲、自有 dashboard」是相反方向 — Snyk 把 security 抽到平台之上、GHAS 把 security 釘在 GitHub 之內。

跟 [Trivy](/backend/07-security-data-protection/vendors/trivy/) 比、定位差更遠。Trivy 主打 *container image / IaC / SBOM scan*、open-source 免費、適合塞進任何 CI；GHAS 主打 *source code + secret + dependency*、Enterprise 付費、container scan 有但偏弱。兩者通常 *並存* — Trivy 跑 container artifact、GHAS 跑 source repo。

跟 [Dependabot](/backend/07-security-data-protection/vendors/dependabot/) 的關係是 *內含* — Dependabot 是 GHAS 四模組之一、跟 GHAS 同一個控制平面、跟 PR / Security tab 同一條 evidence chain。本頁聚焦 GHAS 整體 + Code Scanning / Secret Scanning / Dependency Review；Dependabot 的 update PR 政策、ecosystem 覆蓋、alert routing 細節留在該頁。

關鍵張力：GHAS 計費走 *per-active-committer + per-repo*、2024 後 Secret Scanning 跟 Code Scanning 拆開計費。大型 mono-repo 或 committer 數量膨脹的組織會撞到成本天花板、需要選擇性 enable repo + 拆模組買；同時、Push Protection 這類 *預防型* 控制只有 enable 後才有效、選擇性 enable 等於默認 risk 接受。

## 本章目標

讀完本頁、讀者能判斷：

1. GHAS 四大模組各自承擔哪段控制責任（SAST / Secret / PR-level dependency gate / 自動 update）、哪些跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/) 重疊或互補
2. CodeQL 跟 SARIF 標準的關係、為什麼第三方 SAST 工具的 finding 也能進 GHAS Security tab
3. Secret Scanning 的 *Push Protection*（預防 push）跟 *Secret Scanning Alert*（偵測 leaked）的職責差、partner pattern vs custom pattern 何時用
4. 何時用 GHAS、何時改走 Snyk / Trivy / GitLab Ultimate（GitLab 自家相當品）

## 最短判讀路徑

判斷 GHAS 配置是否健康、最少看四件事：

- **誰能 enable / disable**：Organization owner / Security manager role 配置、enable GHAS 的 audit log 是否同步、誰能改 Code Scanning workflow（branch protection 是否擋住 workflow file 直接 push）
- **哪些 repo 開啟**：Org Security overview 看 *Code Scanning / Secret Scanning / Dependency Review coverage*、新建 repo 是否預設啟用（Organization-level default setting）、private / internal / public repo 是否一致開啟
- **Push Protection 狀態**：Secret Scanning Push Protection 是否 organization-wide enable、bypass 權限給誰（developer 個人 bypass vs 必須走 Security team approval）、bypass 事件是否進 audit
- **Secret Scanning Coverage**：partner pattern（AWS / GCP / Stripe / Slack 等預配）是否全開、custom pattern 是否涵蓋自家 internal token（service token、internal API key）、historical scan 是否跑過（不只新 commit、舊 commit 也要掃）

四件事任一缺失、就是 [Secret Management](/backend/knowledge-cards/secret-management/) 跟 [Supply Chain Integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 邊界的待補項目。

## 日常操作與決策形狀

**Code Scanning 走 SARIF 標準**：Code Scanning 不只是 CodeQL 的 UI、是 *SAST aggregation layer*。所有 SAST 結果（CodeQL 預設、或 Semgrep / Snyk Code / Brakeman / Bandit / SonarCloud / Checkmarx 等第三方）以 SARIF（Static Analysis Results Interchange Format）upload 到 Code Scanning、Security tab 統一展示、PR review 統一標註。意義是 *組織可以用多個 SAST 工具但只看一個 dashboard* — 不需要每個 vendor 各自登入。多工具 SARIF upload 用 GitHub Actions 的 `github/codeql-action/upload-sarif` step。

**CodeQL 是 first-class query language**：CodeQL 用 Datalog-like 語法寫 *自定 query*、可以檢測 *organization-specific anti-pattern*（例：禁用某內部 deprecated function、強制 input validation 在特定 trust boundary）。vendor-provided pack（GitHub 維護的 CodeQL pack）覆蓋 OWASP Top 10 / CWE Top 25、自定 query 補組織 idiomatic check。代價是 *CodeQL 學習曲線陡* — 不是 regex / AST pattern、是完整的 graph query language。

**Secret Scanning 三層職責**：Secret Scanning 分三層。*Partner pattern* — GitHub 跟 AWS / GCP / Stripe / Slack / npm 等 vendor 預配 token pattern、預設 detection 範圍最大、leaked token 還會通知 vendor revoke。*Push Protection* — commit push 前 scan、發現 secret 直接 reject push、開發者必須先移除才能 push；這是 *預防* 不是 *偵測*、不需要等 leaked 後 rotation。*Custom pattern* — 組織自己的 internal token（service-to-service API key、legacy auth token）寫 regex pattern、配 validation endpoint 降 FP。

**Dependency Review 是 PR-level gate**：每個 PR 跑 *新增 / 升級依賴的漏洞檢查 + license check*、把 *新引入 CVE* 列在 PR review、可設 branch protection 強制 PR 過 Dependency Review 才能 merge。這跟 [Dependabot](/backend/07-security-data-protection/vendors/dependabot/) 是互補關係：Dependabot 是 *已 merge 依賴的 update PR*（時間軸：merge 後 vuln 出現、自動發 update PR）、Dependency Review 是 *PR 加新依賴時的 gate*（時間軸：merge 前 vuln 已知、擋 PR）。兩條軸都要開。

**Security overview 是 org-level dashboard**：Organization Security tab 看 *跨 repo* 的 Code Scanning / Secret Scanning / Dependency / Dependabot alert 彙整、用 repo / severity / age filter 排序。對於 *security team 不是 repo owner* 的組織、Security manager role 給 security team 跨 repo read + triage 權限、不需要 admin。

**Security Advisories（CVE 揭露 workflow）**：自家 OSS / 商業 product 出 CVE 時、走 *GitHub Security Advisory* — 在 private fork 修補、coordinated disclosure 時間到公開 advisory、GitHub 自動向 [CVE Numbering Authority](https://www.cve.org/) 申請 CVE ID。這條 workflow 是 *維護者視角*、不是 *使用者視角*；使用者收到的是其他人發的 advisory 進 Dependabot alert。

**SARIF integration 是 GHAS 的 *aggregation* 角色關鍵**：GHAS 不強迫只用 CodeQL — Snyk Code / Semgrep / SonarCloud 等 SAST 工具跑完輸出 SARIF、CI 上傳到 GitHub、Security tab 集中展示。意義是 *組織用 Snyk 做 SAST、但 finding 走 GHAS UI* 是合法配置；GHAS 賣的不只是 CodeQL、是 SAST 統一視圖。

## 核心取捨表

| 取捨維度        | GHAS                                               | Snyk                                                | Trivy                                    | Dependabot（GHAS 子模組）          |
| --------------- | -------------------------------------------------- | --------------------------------------------------- | ---------------------------------------- | ---------------------------------- |
| 主要範圍        | Source code + secret + dependency（PR-level）      | SCA + Container + IaC + SAST（跨 SCM）              | Container image + IaC + SBOM scan        | 依賴 update + alert（merged code） |
| SCM 綁定        | 緊綁 GitHub                                        | 跨 GitHub / GitLab / Bitbucket / Azure Repos        | 無 SCM 綁定、跑在 CI / artifact registry | 緊綁 GitHub                        |
| SAST 引擎       | CodeQL 預設 + 第三方 SARIF aggregation             | Snyk Code（DeepCode）                               | 無 SAST                                  | 無                                 |
| Secret Scanning | Partner pattern + Push Protection + custom pattern | Snyk Secret Scanning（較弱）                        | 有限（filesystem secret scan）           | 無                                 |
| Container 強度  | 中（Code Scanning 可掃 Dockerfile）                | 強（Snyk Container 是主打）                         | 強（Trivy 是 container scan 標準）       | 無                                 |
| License / SBOM  | 有（Dependency Review 含 license）                 | 強（SBOM 生成、license compliance dashboard）       | 強（SBOM 是 first-class）                | 無                                 |
| PR 整合         | 深 — Security tab + PR review 直連                 | 中 — GitHub Check + 跨 SCM PR comment               | 中 — 第三方 Action 整合                  | 深 — 自動發 PR                     |
| 計費            | Per-active-committer + per-repo（Enterprise）      | Per-developer + tier                                | Open source 免費（Aqua 商業版加值）      | GHAS 一部分                        |
| 適合            | GitHub-heavy org、想統一 PR + security UI          | 多 SCM / 多雲、SCA + Container 一站、license 強需求 | Container / IaC scan 為主、CI pluggable  | GitHub repo 想要自動依賴 update    |
| 不適合          | GitLab / Bitbucket / 自管 Git 為主                 | GitHub-only 又要省成本                              | 需要 SAST + Secret Scanning              | 不想自動產生 PR（噪音）            |

選 GHAS 的核心訴求：*GitHub 是 SCM* + 想 *PR review 跟 security finding 合一* + Enterprise 預算可吸收 per-committer cost。GitLab 主要的組織直接走 GitLab Ultimate 的對等功能；多 SCM 或 container 為主走 Snyk + Trivy 組合。

## 進階主題

**CodeQL custom query 開發**：寫自定 query 用 CodeQL CLI 本地開發、跑 `codeql database analyze`、SARIF output 上傳。常見場景：禁用 internal deprecated API、特定 framework 的 misuse pattern、組織 idiomatic security check。Query pack 可以 publish 到 GitHub Container Registry 或 internal registry、跨 repo 復用。代價是 *維護成本* — CodeQL query language 學習曲線陡、組織需要至少 1-2 個 security engineer 專門養護。

**Push Protection bypass workflow**：Push Protection reject push 後、developer 可以 *bypass*（標記 false positive / test data / 風險已知）。Bypass 權限治理是關鍵 — 開放給 developer 個人 bypass 失去預防意義、強制 Security team approval 又拖慢 dev velocity。常見折中：低風險 pattern（test fixture token）developer 可 bypass、高風險 pattern（production credential）必須 Security team approve；所有 bypass 事件進 audit log。

**跟 GitHub Actions 整合**：Code Scanning 走 GitHub Actions workflow 跑 CodeQL — `github/codeql-action/init` + `github/codeql-action/analyze`。同 workflow 可以加 `upload-sarif` step 接第三方 SAST 結果。Actions 用 GitHub-hosted runner 跑 CodeQL 是預設、大型 repo 跑 CodeQL analyze 可能超時、需改 self-hosted runner（大 RAM / 多 CPU）— 但 self-hosted runner 自身是 supply chain 風險、需要 ephemeral runner + 限制 secret access。

**SARIF 多工具整合**：第三方 SAST / SCA / Container scan 工具（Snyk / Semgrep / Trivy / Brakeman / Bandit / Gosec）跑完輸出 SARIF、CI 上傳到 GHAS。實務上組織常用 *CodeQL + Semgrep* 雙軌 — CodeQL 跑深度 graph query、Semgrep 跑快速 pattern 規則；finding 在 Security tab 用 *tool* filter 分開看。

**Secret Scanning partner pattern**：GitHub 維護的 partner pattern list 涵蓋 AWS / GCP / Azure / Stripe / Slack / npm / Docker Hub / GitHub PAT 等。leaked token detect 後、GitHub 自動通知 vendor、vendor 端可選擇 *自動 revoke* 該 token。意義是 *組織不需要做 rotation* — vendor 已經把 leaked token 廢掉。custom pattern 則需要組織自己提供 validation endpoint、GHAS 呼叫驗證才確認是真 leak。

**GHAS Cloud-hosted vs Self-hosted Runner 治理**：CodeQL 跑在 GitHub-hosted runner 是預設、所有 source code 上傳到 GitHub 運算環境。對 *source code 機密度高* 的組織（金融 / 國防 / 法規限制 source 出境）、需走 self-hosted runner。Self-hosted runner 的供應鏈風險見 [GitHub OAuth 2022](/backend/07-security-data-protection/red-team/cases/supply-chain/github-oauth-2022-token-supply-chain/) — runner token 是 supply chain entry、OIDC short-lived token 是建議方向。

**GHAS Enterprise pricing trap**：Per-active-committer 計費、organization 內所有 *過去 90 天有 commit* 的 user 都算 active committer、即使只 commit 1 行也計費。大型公司容易超支；2024 後 Secret Scanning 跟 Code Scanning 拆開計費、可只買 Secret Scanning（單價較低）給全 org、Code Scanning 給關鍵 repo。Public repo 上 GHAS 功能多數免費（Code Scanning、Secret Scanning、Dependency Review）；GitHub Enterprise Cloud 的 internal / private repo 才落入 GHAS 計費範圍 — 兩者範圍不同、新組織常踩到把 private repo 全開的成本。

## 排錯與失敗快速判讀

- **新建 repo 沒自動開 GHAS**：Organization-level default 沒設、新 repo 預設 disable — 開 Organization Security settings 的 *Enable for new repositories*、現有 repo 用 bulk enable
- **Push Protection 大量誤殺**：custom pattern regex 太寬、合法字串被當 secret — 加 validation endpoint 或收緊 regex、bypass 統計看 FP rate
- **Secret Scanning 沒掃歷史 commit**：只 enable 後新 commit 觸發、舊 commit leaked secret 沒被發現 — 跑 *historical scan*（enable 後 GitHub 自動掃過去全部 commit）、可能花數小時
- **Dependency Review 沒擋住 vuln PR**：Branch protection 沒加 *Dependency Review* required check — 加進 required status check、新 PR 才強制過
- **Code Scanning workflow 跑很久 / 超時**：repo 太大、GitHub-hosted runner RAM 不足 — 換 larger runner（GitHub Larger Runners）或 self-hosted、或只跑 changed file analysis
- **Custom CodeQL query FP 多**：query 寫得太寬、commit 都跳 alert — 加 `@precision high` 標籤、用 `Sink-Source` 分析降低 reach
- **第三方 SAST SARIF 沒進 Security tab**：upload-sarif step 沒設對 category 或 permissions — `security-events: write` permission 必須在 workflow 給；同 repo 多工具用不同 `category` 區分
- **Bypass 沒進 audit**：Push Protection bypass 沒同步到 SIEM — Enterprise audit log streaming 開、event filter 加 `secret_scanning.bypass`

## 何時改走其他服務

| 需求形狀                              | 改走                                                                                                                                                                                                                                    |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 多 SCM（GitHub + GitLab + Bitbucket） | [Snyk](/backend/07-security-data-protection/vendors/snyk/)                                                                                                                                                                              |
| Container image scan 為主             | [Trivy](/backend/07-security-data-protection/vendors/trivy/) 或 Snyk Container                                                                                                                                                          |
| SBOM 生成 + license compliance        | [Syft + Grype](/backend/07-security-data-protection/vendors/syft-grype/)（SBOM-first OSS）/ [Snyk](/backend/07-security-data-protection/vendors/snyk/) + [Trivy](/backend/07-security-data-protection/vendors/trivy/)（SBOM 含在 scan） |
| GitLab 為主                           | GitLab Ultimate（SAST / Secret Detection / Dependency Scanning 內建）                                                                                                                                                                   |
| Secret scan 但不在 GitHub             | GitGuardian / Gitleaks                                                                                                                                                                                                                  |
| Runtime detection（不只 source code） | [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 系列工具                                                                                                                    |

## 不在本頁內的主題

- CodeQL 完整 query language reference
- Dependabot 的 update PR 政策、ecosystem 覆蓋、grouped update（見 [Dependabot vendor 頁](/backend/07-security-data-protection/vendors/dependabot/)）
- GHAS Enterprise Server（自管 GitHub）跟 Cloud GHAS 的功能差異
- 各語言 / 框架的 CodeQL pack 完整覆蓋表
- GHAS 跟 GitHub Copilot Autofix 整合的 AI-assisted remediation 細節

## 案例回寫

GHAS 在 07 案例庫沒有 *直接 GHAS-level vendor 事件*。對照引用展示 GHAS 在 supply chain / source-level 控制的能力邊界：

| 案例                                                                                                                                           | 跟 GHAS 的關係                                                                                                                                         |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)         | Dependency Review + Code Scanning 應覆蓋 transitive 依賴、不只 direct import；Security Advisory 是維護者揭露 CVE 的 workflow                           |
| [XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)                | 對照啟示 — GHAS Dependency Review 看 *package version*、看不到 *maintainer takeover*；需補 release-tarball vs git tag 差異跟 maintainer trust baseline |
| [SolarWinds 2020 Sunburst](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)                         | 對照啟示 — Code Scanning 是 source-level、看不到 build-time 植入；需配合 artifact provenance（SLSA L2+）+ reproducible build                           |
| [GitHub OAuth 2022 Token Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/github-oauth-2022-token-supply-chain/) | 對照啟示 — GHAS 自身 token / Actions 權限治理是 supply chain risk、Push Protection + OIDC trust（非長期 token）是 mitigation                           |
| [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)                           | GHAS 是 supply chain 治理工具集、章節原則對應四模組 workflow                                                                                           |

## 下一步路由

- 上游：[7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- 平行：[Snyk](/backend/07-security-data-protection/vendors/snyk/)、[Trivy](/backend/07-security-data-protection/vendors/trivy/)、[Dependabot](/backend/07-security-data-protection/vendors/dependabot/)、[Syft + Grype](/backend/07-security-data-protection/vendors/syft-grype/)（SBOM 走 SARIF 進 GHAS Code Scanning 是常見組合）
- 下游：[7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)（Secret Scanning 配 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) rotation）
- 跨類：[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)（GHAS alert 進 SIEM 的 routing）
- 跨模組：[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)（leaked secret / SAST critical finding 進 IR 流程）
- 官方：[GitHub Advanced Security Documentation](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security)
