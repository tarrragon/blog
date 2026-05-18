---
title: "Gitleaks"
date: 2026-05-18
description: "OSS CLI secret scanner、Go 寫、Rule TOML + regex + entropy、SARIF output、跨 SCM、pre-commit + CI 友善"
weight: 27
tags: ["backend", "security", "vendor", "gitleaks", "secret-scanning", "open-source"]
---

Gitleaks 是 *純 CLI 的 OSS secret scanner*、MIT License、Go 寫、單一 binary 跑遍 macOS / Linux / Windows。它只做一件事 — 對 git history、working tree 或 staged changes 跑 regex + entropy + path filter 找 secret、輸出 JSON / SARIF / CSV 給下游消化。它沒有 dashboard、沒有 SaaS、沒有 cross-platform scan、也沒有 incident workflow — 這些刻意拿掉的東西是它跟 [GitGuardian](/backend/07-security-data-protection/vendors/gitguardian/) / [GHAS Secret Scanning](/backend/07-security-data-protection/vendors/github-advanced-security/) 的核心分界。

## 服務定位

Gitleaks 的核心定位是 *git-aware secret scan 的 CLI 原語*、不是 secret 治理平台。Rule 寫在 `.gitleaks.toml`、輸出走標準格式（SARIF / JSON / CSV）、跟下游 pipeline（CI、SIEM、GHAS Code Scanning）解耦。

跟 [GitGuardian](/backend/07-security-data-protection/vendors/gitguardian/) 比、GitGuardian 是 SaaS + dashboard + remediation workflow + validation endpoint（呼叫真實 API 驗證 secret 是否有效降 FP）+ honeytoken decoy、Gitleaks 沒有任一項 — 它只回答「這個 string 看起來像不像 secret」。GitGuardian 適合大型組織 + 預算允許 + 要跨 Slack / Jira / Notion 等 SaaS scan；Gitleaks 適合預算敏感 + 只需要 git scope + 內部已有 CI / SIEM 接 SARIF 的場景。

跟 [GHAS Secret Scanning](/backend/07-security-data-protection/vendors/github-advanced-security/) 比、GHAS 限 GitHub 平台、提供 push protection（partner pattern 在 push 前直接擋）跟 partner 自動 revoke 等深度整合、但只覆蓋 GitHub repo；Gitleaks 跨 GitHub / GitLab / Bitbucket / 自架 Gitea、CLI 跑哪都行、缺點是沒有 partner revoke 跟 push protection 要自己用 hook 接。

跟 TruffleHog OSS 比、兩者都是 OSS CLI secret scanner、TruffleHog 強在 *verifier*（對 200+ secret type 呼叫對應 API 驗證真偽）、Gitleaks 強在 *rule TOML 表達力跟 SARIF output 成熟度*。實務上很多組織兩個一起跑、用不同的 rule 覆蓋面互補。

關鍵張力：*Allowlist 治理* ↔ *FP 噪音* 是 Gitleaks 客戶最大的長期問題。OSS 沒有 validation endpoint、entropy + path filter 一定會誤判 test fixture / mock token / sample config、allowlist 不持續 review 會膨脹成「全部都白名單」最後 rule 失效。

## 本章目標

讀完本頁、讀者能判斷：

1. Gitleaks 在 secret scan stack 中承擔哪一段（pre-commit / CI scan / historical audit）、哪些要外接（[Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) rotate、[GHAS Code Scanning](/backend/07-security-data-protection/vendors/github-advanced-security/) 收 SARIF dashboard）
2. Custom rule 跟 allowlist 的 ownership 設計（誰寫 rule、誰核准 allowlist、定期 review 週期）
3. `detect` vs `protect` 兩個子命令的職責切分、跟 pre-commit framework / CI 整合的位置
4. 何時用 Gitleaks、何時升級到 [GitGuardian](/backend/07-security-data-protection/vendors/gitguardian/) / [GHAS Secret Scanning](/backend/07-security-data-protection/vendors/github-advanced-security/) 的取捨

## 最短判讀路徑

判斷 Gitleaks 部署是否健康、最少看四件事：

- **誰能改 `.gitleaks.toml`**：rule 跟 allowlist 是否走 Git PR review、commit message 是否帶 allowlist 原因、是否有 owner 簽核
- **`detect` vs `protect` 是否都接**：CI 跑 `gitleaks detect`（掃 history + working tree）、pre-commit hook 跑 `gitleaks protect`（只掃 staged changes）— 缺 protect 等於 leak 進 history 才知道、缺 detect 等於既有 leak 永遠不發現
- **SARIF 是否上傳 dashboard**：CI output 是否 upload 到 [GHAS Code Scanning](/backend/07-security-data-protection/vendors/github-advanced-security/) 或內部 SIEM、不然 finding 散在 CI log 沒人看
- **Allowlist 是否定期 review**：allowlist entry 是否帶 expire date / reason / owner、每季是否 revisit 把過期項目刪掉、不然 allowlist 會膨脹到掩蓋真實 leak

四件事任一缺失、就是 [Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 邊界的待補項目。

## 日常操作與決策形狀

**Rule TOML / JSON**：rule 結構是 `id` + `regex pattern` + 可選 `entropy threshold`（高熵字串通常是 secret、避開 lorem ipsum FP）+ 可選 `path filter`（限定 / 排除路徑）。預設 rule library 涵蓋 AWS / GCP / Azure / Stripe / Slack token 等 100+ pattern；organization 通常 *先 import 預設、再加自家 token format custom rule*。Custom rule 必須給 valid + invalid sample 跑 unit test、不然 regex 寫錯會大量 FP。

**`gitleaks detect`（historical scan）**：掃整個 git history + working tree、CI 跑、適合 *發現既有 leak*。預設掃 HEAD 到根、可用 `--log-opts` 限定 commit range 加速。實務上 PR scan 限定 `--log-opts="--since=...$(git merge-base origin/main HEAD)"` 只看本 PR 新增 commit、避免每次跑整個 history 慢死。

**`gitleaks protect`（pre-commit）**：只掃 staged changes、pre-commit hook 跑、適合 *攔住未來 leak*。它不掃 history、意義是 *commit 前的最後一道閘*；配合 pre-commit framework（`pre-commit-hooks` 或 [pre-commit.com](https://pre-commit.com/)）的 `repos: gitleaks` 配置直接接入。

**Report 格式（JSON / SARIF / CSV）**：JSON 是 raw 結構、適合 script 處理；SARIF 是 OASIS 標準、跟 GHAS Code Scanning / 商業 SAST dashboard 共用；CSV 適合人讀 / Excel 二次處理。Production 通常 *CI 輸出 SARIF + 上傳 GHAS Code Scanning*、把 OSS scanner 的 finding 跟商業 SAST 同 dashboard、SOC 不用切多工具。

**跟 CI 整合**：GitHub Actions 用 `gitleaks/gitleaks-action`、GitLab CI 用 official Docker image、Jenkins 用 binary download + shell step。CI 失敗策略要決定 — *block PR* 還是 *warn only*：嚴格組織 block PR、寬鬆組織 warn + 上 SARIF 讓 SOC 自行 triage、避免初期高 FP 阻塞所有 merge。

**跟 pre-commit framework 整合**：`.pre-commit-config.yaml` 加 `- repo: https://github.com/gitleaks/gitleaks` 條目、`pre-commit install` 後每次 commit 自動跑。注意 *pre-commit 只在開發者 machine 跑*、繞過很簡單（`git commit --no-verify`）、所以一定要配 CI scan 兜底、不能只信 pre-commit。

**Allowlist 治理**：`.gitleaks.toml` 裡 `[allowlist]` section 寫 `paths` / `regexes` / `commits` / `stopwords`。每個 entry 應該帶 reason（`# allowlist reason: test fixture for OAuth flow, expire 2026-Q4`）、PR review 時要問「為什麼這個是 FP、什麼時候會過期」。Quarterly 跑 audit 把過期項目刪掉、避免 allowlist 變成「全部都白名單」。

## 核心取捨表

| 取捨維度        | Gitleaks                                | GitGuardian                               | GHAS Secret Scanning                        | TruffleHog OSS               |
| --------------- | --------------------------------------- | ----------------------------------------- | ------------------------------------------- | ---------------------------- |
| License         | MIT OSS                                 | Proprietary SaaS（free tier 限個人）      | GitHub Enterprise add-on                    | AGPL OSS（Enterprise 商業）  |
| Scope           | Git only（history + tree + staged）     | Git + Slack + Jira + Notion + 自訂 source | GitHub repo only                            | Git + S3 + filesystem + more |
| Dashboard       | 無、輸出 SARIF / JSON 自己接            | 內建 incident workflow + remediation      | GitHub Security tab                         | 無（CLI / API）              |
| Validation      | 無（只看 regex + entropy）              | 有（呼叫 API 驗證真偽）                   | Partner pattern 自動 revoke                 | 有（200+ verifier）          |
| Push protection | 無、要自己 wire pre-commit              | 有（透過 ggshield）                       | 有（partner pattern、push 前擋）            | 無                           |
| 部署模型        | CLI binary、跑哪都行                    | SaaS only                                 | GitHub SaaS / Enterprise Server             | CLI binary                   |
| 計費            | 免費                                    | Per-developer / per-repo                  | Per-committer                               | 免費（OSS） / 商業另計       |
| 適合場景        | OSS-friendly、預算敏感、CI / SARIF 已有 | 跨 SaaS scan + remediation workflow       | GitHub-only + push protection 為主          | 多 source + verifier 為主    |
| 退場成本        | 低 — rule TOML 可移植到 GitGuardian     | 高 — incident history / workflow 綁定     | 中 — SARIF 可移植但 push protection 限 GHAS | 低                           |

選 Gitleaks 的核心訴求：*OSS + 預算敏感 + 只需要 git scope + 內部 CI / SIEM 已能消化 SARIF*、且願意自己投入 rule / allowlist 治理。要跨 SaaS scan + incident workflow 升 GitGuardian、要 push protection + partner revoke 走 GHAS Secret Scanning。

## 進階主題

**Custom rule 寫法（regex + entropy + path）**：自家 internal token 通常有特定 prefix（`xy_live_` / `int_token_`）、寫 custom rule 就是 `regex = '''xy_live_[A-Za-z0-9]{32}'''` + `entropy = 4.0` + `path = '''.*\.go$'''`。Entropy threshold 越高 FP 越少但 FN 越多、實務值 3.5–4.5 之間 tune。每個 rule 一定要在 repo 加 unit test fixture（valid + invalid sample）、CI 跑 rule 自我驗證、避免 regex 寫錯後 silent break。

**跟 SARIF + GHAS Code Scanning 整合補位**：Gitleaks CI 跑完輸出 SARIF、用 `github/codeql-action/upload-sarif` 上傳到 GHAS Code Scanning。GHAS Code Scanning 不限 CodeQL 來源、任何 SARIF tool 都收。意義是 *OSS scanner + GHAS dashboard* 是預算友善組合 — 不買 GHAS Secret Scanning license、但 finding 集中在 Security tab 跟 SAST 共看。對應 [GHAS Advanced Security](/backend/07-security-data-protection/vendors/github-advanced-security/) 的 Code Scanning section。

**跟 Vault 自動 rotation pipeline**：Gitleaks 找到 leak 不是終點、是 *rotation trigger*。CI 把 finding 推 SOAR（或自家 webhook）、SOAR 呼叫 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) API 對該 credential type rotate（dynamic credential 直接 revoke、static secret 換新版本）、再 broadcast 給依賴該 secret 的 service rolling restart。沒這條 pipeline、Gitleaks 只是 finding 列表沒實際治理價值。

**Allowlist 治理（FP 不能無限）**：OSS 沒 validation endpoint、test fixture / mock token / sample config 一定觸發 FP。allowlist 治理三原則 — *每個 entry 帶 reason + owner + expire date*、*PR review 必問「為什麼 FP」*、*quarterly audit 刪過期項目*。沒這個治理 allowlist 會在 6–12 個月內膨脹到「半個 repo 都在白名單」、那時候 rule 已經沒用、refactor 成本比一開始嚴格更高。

**跟 Trivy secret scan 重疊**：[Trivy](/backend/07-security-data-protection/vendors/trivy/) 內建 secret scanner（用同樣的 regex pattern）、container image / filesystem 都掃。Gitleaks 跟 Trivy secret scan 在 *container build pipeline* 階段會重疊 — 實務分工：Gitleaks 掃 source repo（git history + working tree）、Trivy 掃 built artifact（image layer + filesystem）。兩者覆蓋不同階段、不衝突。

## 排錯與失敗快速判讀

- **FP 太多、開發者開始忽略 Gitleaks finding**：rule 沒 tune entropy threshold 或 path filter — 對 high-FP rule 加 `entropy = 4.0` 跟 `paths = ['''!test/.*''']`、staging branch 跑 1 週統計 FP 再 promote
- **Pre-commit 被繞過（`--no-verify`）**：開發者本機跑不過直接 bypass — pre-commit 不能當唯一防線、CI `gitleaks detect` block PR 才是真實 gate
- **Historical scan 太慢、CI timeout**：每次掃整個 git history — PR scan 限定 `--log-opts="$(git merge-base origin/main HEAD)..HEAD"` 只看本 PR commit、nightly job 才跑 full history
- **SARIF 上傳失敗 / GHAS dashboard 沒 finding**：`github/codeql-action/upload-sarif` 權限不足或 `security-events: write` permission 沒給 — 補 GitHub Actions permission、或改 upload 內部 SIEM
- **Allowlist 膨脹、規則失效**：FP 全部塞 allowlist、沒 reason 沒 expire — quarterly audit、刪過期項目、把高 FP rule 改寫成更窄的 regex 而不是 allowlist 蓋過
- **既有 leak 沒被發現、新 commit 攔得很乾淨**：只接 `protect` 沒接 `detect` — CI 加 `detect` job、找出 history 中已 leak 的 secret 一次性 rotate（[Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) 自動化）
- **Custom rule 寫錯、silent skip 真 leak**：rule regex 沒 unit test fixture、production 才發現 — 強制 custom rule 加 valid + invalid sample、CI 跑 rule 自驗

## 何時改走其他服務

| 需求形狀                                  | 改走                                                                                                     |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 跨 Slack / Jira / Notion / 自架 SaaS scan | [GitGuardian](/backend/07-security-data-protection/vendors/gitguardian/)                                 |
| Push protection + partner auto-revoke     | [GHAS Secret Scanning](/backend/07-security-data-protection/vendors/github-advanced-security/)           |
| Validation endpoint（驗證 secret 真偽）   | [GitGuardian](/backend/07-security-data-protection/vendors/gitguardian/) 或 TruffleHog Enterprise        |
| Honeytoken decoy 主動防禦                 | [GitGuardian](/backend/07-security-data-protection/vendors/gitguardian/)（內建 honeytoken）              |
| Container image secret scan               | [Trivy](/backend/07-security-data-protection/vendors/trivy/)（內建 secret scanner）                      |
| Secret 找到後自動 rotate                  | 配 [HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) dynamic credential   |
| SAST / SCA dashboard 整合                 | [GHAS Code Scanning](/backend/07-security-data-protection/vendors/github-advanced-security/)（收 SARIF） |

## 不在本頁內的主題

- Gitleaks v8 跟 v7 的 rule 格式遷移細節
- Gitleaks 內部 git odb 解析跟性能 tuning（large monorepo 加速）
- Pre-commit framework 本身的安裝跟治理（屬開發者工作流、不在資安範圍）
- Rotation playbook 完整實作（屬 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) / [AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) 章節）
- Secret 治理整體政策（屬 [Secrets Management section](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) 上層原則）

## 案例回寫

Gitleaks 在 07 案例庫沒有直接 vendor-level 事件、所有 secret leak case 都是 git history scan + rotation pipeline 的對照：

| 案例                                                                                                                                           | 跟 Gitleaks 的關係（對照啟示）                                                                                                                                         |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [CircleCI 2023 Secrets Rotation](/backend/07-security-data-protection/red-team/cases/supply-chain/circleci-2023-secrets-rotation/)             | Gitleaks `detect` 跑整個 git history 找出已 leaked secret、配合 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) rotation 流程清乾淨             |
| [GitHub OAuth 2022 Token Supply Chain](/backend/07-security-data-protection/red-team/cases/supply-chain/github-oauth-2022-token-supply-chain/) | Pre-commit `protect` 攔未來 leak、但對既有 leak 要 historical scan 補位、單一防線不夠                                                                                  |
| [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)            | Gitleaks 找出 leaked static secret 是第一步、長期解是 [Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) dynamic credential 取代 long-lived secret |

## 下一步路由

- 上游：[7 章 Secrets Management section](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)、[Detection Coverage and Signal Governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行：[GitGuardian](/backend/07-security-data-protection/vendors/gitguardian/)、[GHAS Secret Scanning](/backend/07-security-data-protection/vendors/github-advanced-security/)、[Trivy](/backend/07-security-data-protection/vendors/trivy/)
- 下游：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/)（找到 leak 後 rotate）、[AWS Secrets Manager](/backend/07-security-data-protection/vendors/aws-secrets-manager/) / [Google Secret Manager](/backend/07-security-data-protection/vendors/google-secret-manager/) / [Azure Key Vault](/backend/07-security-data-protection/vendors/azure-key-vault/)
- 跨類：[GHAS Code Scanning](/backend/07-security-data-protection/vendors/github-advanced-security/)（收 SARIF dashboard）、[Splunk](/backend/07-security-data-protection/vendors/splunk/) / [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)（finding 進 SIEM）
- 官方：[Gitleaks GitHub](https://github.com/gitleaks/gitleaks)、[Gitleaks Documentation](https://github.com/gitleaks/gitleaks/blob/master/README.md)
