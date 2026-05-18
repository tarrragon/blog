---
title: "Dependabot"
date: 2026-05-18
description: "GitHub 原生依賴更新自動化、Version Update + Security Update + Alerts、Grouped Updates 減 PR noise、Auto-merge 配 branch protection"
weight: 6
tags: ["backend", "security", "vendor", "dependabot", "dependency", "supply-chain"]
---

Dependabot 是 GitHub 內建的 *依賴更新自動化* 工具、原為 Dependabot Inc.、2019 年被 GitHub 收購後改為 GitHub native feature、目前 public repo 免費、private repo 部分功能 (Alerts / Security Update) 也免費、Version Update 跟進階治理納入 [GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/) 套餐。它做三件事：*Dependabot version updates*（定期 PR 升級依賴到最新 compatible 版本）、*Dependabot security updates*（CVE 觸發的緊急 PR 升級到 fix version）、*Dependabot alerts*（看到漏洞列在 Security tab、不一定自動 PR）。它的設計目標 *狹窄而深* — 只做 GitHub repo 的依賴 PR 自動化、不做容器掃描、不做 IaC 掃描、不跨 SCM。

## 服務定位

Dependabot 的核心定位是 *把依賴升級從人工 ritual 變成 PR review 工作流*。它把「找新版」「跑 manifest update」「開 PR」「附 release note」自動化、剩下的 *是否合併* 留給人類 / CI 判斷。這跟 [Snyk](/backend/07-security-data-protection/vendors/snyk/) 看似重疊 — 兩者都會自動發升級 PR — 但 Snyk 是 *跨 SCM + 多 stack*（GitHub / GitLab / Bitbucket、SCA + 容器 + IaC + Code）、Dependabot 是 *GitHub-only + 純依賴*。多數組織選一個、混用兩者會在同一個 manifest 上各自開 PR、造成 noise。

跟 [GHAS](/backend/07-security-data-protection/vendors/github-advanced-security/) 的關係比較細：Dependabot Alerts 跟 Security Updates 本身是 GHAS *Dependabot* 子模組的核心、但功能上 *Alerts 對所有 repo 免費*、Security Update 也免費自動發 PR、Version Update 也免費；GHAS 提供的是 *Dependency Review*（PR-time gate、阻擋 PR 引入新漏洞依賴）、*Security Overview*（org-wide dashboard）跟 enterprise-level 控制。Dependabot 是 *background PR 工廠*、GHAS Dependency Review 是 *PR-time blocker*、兩者互補不重疊。

跟 [Renovate](https://docs.renovatebot.com/)（Mend 維護的 OSS）的差異：Renovate 配置更彈性、跨 SCM、支援 ecosystem 數量多（含 Helm chart、Docker tag、ArgoCD 等）、Grouped Updates 規則更細；Dependabot 整合 GitHub 原生 UI（Security tab、Dependency graph、PR diff）更深、設定簡單。需要 *跨 SCM* 或 *Helm / ArgoCD / 自訂 ecosystem* 走 Renovate；單純 GitHub-only 加 npm / Maven / pip 等主流 ecosystem、Dependabot 配置成本更低。

## 本章目標

讀完本頁、讀者能判斷：

1. Dependabot 在 supply chain 防護裡承擔哪一段（背景 PR 升級）、哪些不在它責任內（容器掃描、IaC 掃描、PR-time gate）
2. `dependabot.yml` 的關鍵配置面：ecosystem、schedule、open-pull-requests-limit、groups、reviewers
3. Version Update vs Security Update vs Alerts 三個功能何時開、PR noise 怎麼控制
4. Auto-merge 政策的邊界：哪種更新可以全自動、哪種要保留 human approval

## 最短判讀路徑

判斷一個 repo 的 Dependabot 配置是否健康、最少看四件事：

- **`dependabot.yml` 配置**：repo 是否有 `.github/dependabot.yml`、ecosystem 是否覆蓋所有 manifest（npm / Maven / pip / Docker / GitHub Actions / Terraform）、`directory` 路徑對不對（monorepo 各 sub-package 是否獨立配置）
- **Update Schedule**：`schedule.interval` 是 daily / weekly / monthly、`open-pull-requests-limit` 是否合理（預設 5、太低會卡住 backlog、太高會 PR noise）、Grouped Updates 是否啟用（減少 minor / patch PR 數量）
- **Auto-merge 政策**：branch protection 是否設「CI green + required reviewer」、auto-merge 是否限定 *patch + minor* 自動、*major* 強制 human review、production 跟 staging branch 是否有差異化規則
- **Token 治理**：repo secrets 是否被 Dependabot PR 誤用、Dependabot secrets（私有 registry credential）是否獨立配置、PR 觸發的 Actions 是否假設 read-only token

四件事任一缺失、就是 [Supply Chain Integrity](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 邊界的待補項目。

## 日常操作與決策形狀

**`dependabot.yml` 是版控的配置檔**：放在 `.github/dependabot.yml`、跟 manifest 同 repo、所有變更走 PR review。不在 GitHub UI 直接改 — UI 只能 *啟用 / 停用* Dependabot 本身、細節必須 commit 進 repo。Monorepo 結構（例：`/services/api`、`/services/web` 各自 `package.json`）每個 sub-package 寫一個 entry、`directory` 指到 sub-package 根目錄、`package-ecosystem` 標 manifest 類型。`schedule.interval` 一般 weekly 開始、daily 適合高活躍度團隊但 PR noise 高、monthly 適合穩定 lib 但 CVE 延遲風險高。

**Version Update vs Security Update 分開**：Version Update 是 *定期掃 manifest 看有沒有 newer compatible 版本*、不分 CVE、是 hygiene 工作；Security Update 是 *Dependabot 偵測到 CVE 且 manifest 指到 vulnerable 範圍時自動發 PR 升級到 fix version*、是 incident 工作。多數組織開 Security Update 全 repo + 選擇性開 Version Update（核心服務開、archived repo 不開）— 避免 PR noise 淹沒緊急 PR。Security Update 預設啟用、Version Update 要 explicit 在 `dependabot.yml` 寫 entry 才會跑。

**Grouped Updates**：2023 推出、單一 PR 含多個 minor / patch 升級（例：一個 PR 升 10 個 npm package）、PR 數量從 10 個降到 1 個。配置在 `dependabot.yml` 的 `groups` 區、可以按 dependency name pattern（例：`@types/*` 一組、`eslint*` 一組）或 update-type（`patch` / `minor` 分組）。Major version 仍分開 PR — 因 breaking change 風險、需要單獨 review。Grouped Updates 配 auto-merge 是 *minor / patch 全自動* 的標準配置。

**Auto-merge 是 PR 級、不是 commit 級**：Dependabot 發 PR、搭配 GitHub branch protection 設「CI green + 1 approver」就 auto-merge — GitHub `gh pr merge --auto` 或 Actions workflow（`peter-evans/enable-pull-request-automerge`）都行。production 環境應該保留 human approval（至少對 major version）、staging / dev 可以全自動。常見模式：staging branch 全自動合（patch + minor）+ 自動 deploy；production branch 走 staging → cherry-pick / promote 流程、human approve。

**Reviewer / Assignee / Label 自動標記**：`dependabot.yml` 的 `reviewers` / `assignees` / `labels` 欄位讓 Dependabot 開 PR 時自動標 reviewer 跟 label。實務上配 `labels: ["dependencies"]` 讓 Dependabot PR 在 PR list 跟一般 feature PR 分開、CI workflow 可以針對 `dependencies` label 跑特化 lint（例：跑完整 e2e、不只 unit test）。

**Token 治理**：Dependabot PR 跑 GitHub Actions 時、`secrets.GITHUB_TOKEN` 是 *read-only*（GitHub 設計上限制、防 PR 觸發 supply chain attack）— 這代表 Dependabot PR 不能跑需要 write permission 的 job（推 image / 改 status / comment）。需要的話用 `pull_request_target` event（用 base branch 的 workflow + 完整 secrets）、但這也是 supply chain attack 高風險面、必須 *最少 permission*。私有 registry credential（npm private registry token、Maven private repo password）用 *Dependabot secrets*（org / repo level）配置、跟 GitHub Actions secrets 是 *不同 namespace*、不會互相讀到。

**跟 GHAS Dependency Review 搭配**：[GHAS Dependency Review](/backend/07-security-data-protection/vendors/github-advanced-security/) 在 PR-time 看 manifest diff 阻擋 *引入新漏洞依賴*、Dependabot Security Update 在 background *升級舊有漏洞依賴*、兩個方向互補。production repo 標準配置：GHAS Dependency Review 設 high severity block + Dependabot Security Update 全開 + Dependabot Version Update 選擇性開。

## 核心取捨表

| 取捨維度        | Dependabot                                                      | Snyk                                          | Renovate                                           |
| --------------- | --------------------------------------------------------------- | --------------------------------------------- | -------------------------------------------------- |
| SCM 範圍        | GitHub only                                                     | GitHub / GitLab / Bitbucket / Azure DevOps    | GitHub / GitLab / Bitbucket / Azure DevOps / Gitea |
| 涵蓋面          | 純依賴（SCA）                                                   | SCA + 容器 + IaC + Code                       | 純依賴（SCA）+ Docker tag / Helm / 自訂            |
| Ecosystem 數量  | 主流（npm / Maven / pip / Docker / Actions / Terraform 等 20+） | 主流相近 + 商業資料庫優先                     | 多（含 Helm / ArgoCD / preCommit / 自訂 regex）    |
| Grouped Updates | 有（2023+、按 pattern / update-type）                           | 有（按 type）                                 | 有（規則最細、按 manager / depType / pattern）     |
| Auto-merge      | 走 GitHub branch protection + auto-merge                        | Snyk 自家 PR + 走 SCM auto-merge              | 內建 `automerge` 配置、規則細                      |
| 漏洞資料庫      | GitHub Advisory Database（公開 + 私有）                         | Snyk Intel（商業、揭露快、加入專屬 advisory） | OSV / NVD / GitHub Advisory（聚合）                |
| PR 整合深度     | GitHub Security tab / Dependency graph 原生                     | Snyk UI 為主、SCM PR 是延伸                   | SCM PR 原生、Renovate dashboard issue 集中管理     |
| 設定方式        | `dependabot.yml`（簡單）                                        | UI + `.snyk` policy file（漏洞例外）          | `renovate.json`（極彈性、配置複雜）                |
| 商業成本        | GitHub 免費（Version Update / Security Update / Alerts 都免費） | 商業授權（含免費 tier、規模上來付費）         | OSS 免費、Mend 商業版加分析 dashboard              |
| 適合場景        | GitHub-only + 純依賴 + 設定要簡單                               | 跨 SCM、要容器 / IaC、商業 advisory 加值      | 跨 SCM 或要 Helm / ArgoCD / 自訂 ecosystem         |

選 Dependabot 的核心訴求：*GitHub-only* + 只要依賴 PR 自動化、不要容器 / IaC scan、配置成本要低、整合 GitHub Security tab。要跨 SCM 或多 stack 走 Snyk、要彈性 ecosystem / Helm chart / ArgoCD 走 Renovate。混用 Dependabot + Snyk 對同一 manifest 自動 PR 會 noise、二選一。

## 進階主題

**Multi-ecosystem repo**：一個 repo 同時有 npm + Docker + Terraform + GitHub Actions、`dependabot.yml` 寫四個 entry、各自 schedule。實務常見配置：application 依賴（npm / pip）weekly、base image（Docker）weekly、IaC（Terraform provider）monthly、GitHub Actions（CI workflow）weekly。Actions ecosystem 要特別注意 — Dependabot 升級 `uses:` 指向的 action version、可以同時 pin commit hash（防 tag re-publish 攻擊）、但 pin hash 後 release note 看不到 — 取捨 *安全 vs 可讀性*。

**Private registry support**：私有 npm registry（GitHub Packages / Artifactory / Nexus）、私有 Maven repo、私有 PyPI mirror、私有 container registry 都要在 `dependabot.yml` 配置 `registries` 區、credential 走 Dependabot secrets。Dependabot 從私有 registry 抓 package metadata 跟 release info、否則只能看 public registry、會誤判 internal lib 沒新版。Org-level Dependabot secrets 適合共用 credential、repo-level 適合特殊 credential 隔離。

**Self-hosted runner 隔離**：Dependabot PR 觸發的 Actions 預設跑在 GitHub-hosted runner、跟 Dependabot 本身的 sandbox 不同。如果 CI 跑在 self-hosted runner（內網資源 / 大 build cache）、Dependabot PR 也會跑在 self-hosted runner — 要確認 runner 不會被 PR 注入的惡意 manifest 攻擊（npm install 跑 postinstall script 是經典攻擊路徑）。Mitigation：Dependabot PR 用 ephemeral runner（每次新 VM）、隔離 build cache、不掛 sensitive volume。

**Auto-merge 風險**：auto-merge 加速合併、但也放寬 *攻擊者升級 dep 攻擊我* 的窗口。[XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/) 的攻擊路徑就是攻擊者花兩年取得 upstream maintainer 信任、發 release 帶 backdoor — 如果下游 auto-merge 升級、攻擊就直達 production。Mitigation：major version 永不 auto-merge、critical infra dep（auth / crypto / network 函式庫）pin commit hash + 手動 review、auto-merge 範圍縮到 patch + minor + low-criticality dep。

**GitHub Actions 跟 Dependabot 互動**：Dependabot PR 觸發的 workflow 預設 `GITHUB_TOKEN` 是 *read-only*、`secrets.*` 是 *empty*（Dependabot context）— 防止 PR 注入腳本竊取 secret。需要在 Dependabot PR 跑帶 secret 的 job、用 `pull_request_target` event（workflow 從 base branch 取、有完整 secret）— 但這會 *讀 PR 的 code 跑 workflow*、必須先 `checkout` base 然後最小化 PR code 的執行（不跑 PR 的 install script、只跑既有 lint）。

## 排錯與失敗快速判讀

- **PR noise 淹沒緊急 PR**：Version Update 全開 + 沒 Grouped Updates、一週 30+ PR — 啟用 `groups` 按 pattern 分組（`@types/*` / `eslint*` / `dev-dependencies`）、`open-pull-requests-limit` 設 5、archived repo 關 Version Update
- **Security Update 沒發 PR**：CVE 公告了但 Dependabot 沒動 — 確認 manifest 真的指到 vulnerable 範圍、`dependabot.yml` 沒 `ignore` 該 dependency、Security Updates 在 repo settings 是啟用、Dependency graph 有抓到該 manifest
- **私有 registry 抓不到**：Dependabot 在私有 npm / Maven repo 失敗 — `dependabot.yml` 配 `registries` 區、credential 進 Dependabot secrets（不是 Actions secrets）、URL 跟 token 範圍對齊
- **Auto-merge 不觸發**：PR 開了 CI 也綠了但沒合 — 確認 branch protection required check 跟 CI workflow 名稱對齊、`gh pr merge --auto` 在 PR comment / workflow 有觸發、reviewer count 達標
- **Dependabot PR 跑 Actions 失敗**：PR 的 workflow 報 permission denied — `GITHUB_TOKEN` 在 Dependabot context read-only、改用 `pull_request_target` 或拆 job（push secret 的部分跑在 merge 後 main branch event）
- **Major version 被 auto-merge**：規則沒寫對、major 也自動合進 production — `dependabot.yml` 的 `ignore` 加 `update-types: ["version-update:semver-major"]` 或 auto-merge 條件改 `${{ steps.metadata.outputs.update-type == 'version-update:semver-minor' }}`
- **Monorepo 漏掃**：`/services/api/package.json` 沒掃 — `dependabot.yml` 每個 sub-package 寫一個 entry、`directory` 指到正確路徑、不是只在 root 一個 entry
- **GitHub Actions ecosystem 升級拿掉 commit hash pin**：原本 `uses: actions/checkout@a12b3c4` 被升成 `uses: actions/checkout@v5` — Dependabot 會 follow 既有 reference 風格、想要 hash pin 設 `dependabot.yml` 的 ecosystem-level config 但目前限制較多、實務常另用 [pinact](https://github.com/suzuki-shunsuke/pinact) 或 Renovate 處理 Actions hash pinning

## 何時改走其他服務

| 需求形狀                       | 改走                                                                                                                                                           |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 跨 SCM（GitLab / Bitbucket）   | [Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Renovate](https://docs.renovatebot.com/)                                                         |
| 容器 / IaC scan                | [Snyk](/backend/07-security-data-protection/vendors/snyk/) / [Trivy](/backend/07-security-data-protection/vendors/trivy/)                                      |
| Helm / ArgoCD / 自訂 ecosystem | [Renovate](https://docs.renovatebot.com/)                                                                                                                      |
| PR-time block 引入新漏洞       | [GHAS Dependency Review](/backend/07-security-data-protection/vendors/github-advanced-security/)                                                               |
| SAST / Code scanning           | [GHAS Code Scanning](/backend/07-security-data-protection/vendors/github-advanced-security/) / [Snyk Code](/backend/07-security-data-protection/vendors/snyk/) |
| SBOM 生成 / 簽章               | [Syft / Grype](/backend/07-security-data-protection/vendors/syft-grype/)（含 Sigstore cosign 整合段落）                                                        |
| Secret scanning                | [GHAS Secret Scanning](/backend/07-security-data-protection/vendors/github-advanced-security/) / GitGuardian                                                   |

## 不在本頁內的主題

- `dependabot.yml` 完整欄位 reference（看 [GitHub 官方文件](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file)）
- GitHub Advisory Database 詳細運作（CVE 來源、curation 流程）
- GHAS 其他模組（Code Scanning / Secret Scanning / Dependency Review）細節 — 看 [GHAS 頁](/backend/07-security-data-protection/vendors/github-advanced-security/)
- Renovate / Snyk 完整配置 — 看各自 vendor 頁
- Container base image 升級的 multi-stage Dockerfile 處理

## 案例回寫

Dependabot 沒有自身 vendor-level case、但在 supply chain case 中是 *標準 mitigation* 或 *風險面*：

| 案例                                                                                                                                           | 跟 Dependabot 的關係                                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Log4Shell CVE-2021-44228](/backend/07-security-data-protection/red-team/cases/supply-chain/log4shell-cve-2021-44228-component-chain/)         | 對照啟示 — Dependabot Security Update 在 Log4Shell 期間自動發 log4j-core 升級 PR、auto-merge 必須有 functional + security 雙重 CI verify、不能單看 build pass |
| [GitHub OAuth 2022 Token Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/github-oauth-2022-token-supply-chain/) | 對照啟示 — Dependabot 自己用 GitHub token、需確認 Dependabot PR 不能讀 production secrets（GitHub 設計上已 read-only / empty secrets）                        |
| [CircleCI 2023 Secrets Rotation](/backend/07-security-data-protection/red-team/cases/supply-chain/circleci-2023-secrets-rotation/)             | 對照啟示 — CI 出事時 Dependabot secrets（私有 registry credential）也要 rotate、不是只 rotate Actions secrets                                                 |
| [XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)                | 對照啟示 — Dependabot auto-merge 隱含 maintainer trust、攻擊者控制 upstream 後升級 = 自動進 production；major 不 auto-merge + 重要 dep pin commit hash        |

## 下一步路由

- 上游：[7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/)
- 平行：[GitHub Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/)、[Snyk](/backend/07-security-data-protection/vendors/snyk/)
- 下游：[Trivy](/backend/07-security-data-protection/vendors/trivy/)（容器 scan）、[Syft / Grype](/backend/07-security-data-protection/vendors/syft-grype/)（SBOM）
- 跨類：artifact 簽章（Sigstore cosign）見 [Syft / Grype 頁的 SBOM attestation 段](/backend/07-security-data-protection/vendors/syft-grype/)
- 跨模組：[6 可靠性驗證流程](/backend/06-reliability/)（Dependabot PR 進 release flow 的 gate 設計）、[8 事故處理 vendor 清單](/backend/08-incident-response/vendors/)
- 官方：[Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
