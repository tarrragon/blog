---
title: "Terraform CI Pipeline 設定指南"
date: 2026-06-26
description: "用 GitHub Actions 建立完整的 Terraform CI pipeline：fmt → validate → tflint → plan → PR comment → apply，含 OIDC credential 與環境保護規則"
weight: 2
tags: ["infra", "ci-cd", "terraform", "github-actions"]
---

Terraform 的 PR 流程要發揮價值，plan 和 apply 需要在 CI 裡自動執行，而非在工程師的本機跑。本篇用 GitHub Actions 建立一條完整的 pipeline：PR 開啟時跑檢查和 plan、plan 結果貼回 PR comment 讓 reviewer 看、合併到主幹後才 apply。整條管線的 credential 用 OIDC 取得短期 token（見 [OIDC Trust Policy 設定](/infra/02-identity-credentials/oidc-trust-policy-setup/)），不存任何長期 key。

## Pipeline 的兩個階段

整條 pipeline 分成兩個觸發時機，各自承擔不同責任：

| 階段  | 觸發條件      | 責任                                         | 失敗時       |
| ----- | ------------- | -------------------------------------------- | ------------ |
| Plan  | PR 開啟或更新 | 檢查格式、驗證語法、靜態掃描、產出 plan diff | PR 無法合併  |
| Apply | 合併到 main   | 把 plan 過的變更套用到雲端                   | 需要人工介入 |

兩個階段用不同的 IAM role：plan role 只有唯讀權限（能跑 `terraform plan` 但不能改任何資源），apply role 有寫入權限。這個分離確保 PR 階段的任何 code 都沒辦法偷偷改動雲端資源。

## Plan 階段的完整 workflow

```yaml
name: Terraform Plan
on:
  pull_request:
    paths:
      - 'infra/**'

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  plan:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: infra/environments/prod

    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/infra-plan
          aws-region: ap-northeast-1

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.9.0

      - name: Format check
        run: terraform fmt -check -recursive -diff

      - name: Init
        run: terraform init -input=false

      - name: Validate
        run: terraform validate

      - name: TFLint
        uses: terraform-linters/setup-tflint@v4
        with:
          tflint_version: latest
      - run: tflint --recursive --format compact

      - name: Plan
        id: plan
        run: |
          terraform plan -no-color -input=false -out=tfplan \
            -detailed-exitcode 2>&1 | tee plan-output.txt
        continue-on-error: true

      - name: Comment plan on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const plan = fs.readFileSync('infra/environments/prod/plan-output.txt', 'utf8');
            const truncated = plan.length > 60000
              ? plan.substring(0, 60000) + '\n\n... (truncated)'
              : plan;
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `### Terraform Plan\n\`\`\`\n${truncated}\n\`\`\``
            });

      - name: Fail if plan errored
        if: steps.plan.outcome == 'failure'
        run: exit 1
```

### 各步驟的職責

**Format check** 驗證 HCL 是否符合標準排版。它不影響功能，但消除 diff 噪音——排版不一致時 PR diff 會混入純格式變更，reviewer 分不清哪些是邏輯改動。`-diff` flag 讓 CI 輸出具體哪幾行不符合，作者在本地跑 `terraform fmt` 就能修。

**Init** 初始化 provider 和 backend。`-input=false` 避免 CI 卡在等待互動式輸入。如果 backend 設定錯了（bucket 不存在、權限不足），這一步就會失敗，不會跑到後面浪費時間。

**Validate** 檢查 HCL 的語法和內部一致性——變數沒宣告、型別不匹配、必填參數缺漏。它不連線雲端，只讀 code，所以不需要 AWS credential 也能跑（但放在 init 之後是因為 validate 需要 provider schema）。

**TFLint** 做 provider 層的正確性檢查：instance type 在該 region 不存在、已棄用的參數、命名不符規範。它補的是 validate 抓不到的「語法對但值不對」的問題。

**Plan** 是整條 pipeline 的核心產出。`-detailed-exitcode` 讓 exit code 區分三種狀態：0 = 無差異、1 = 錯誤、2 = 有差異。`-out=tfplan` 把 plan 結果存成二進位檔，apply 階段可以直接用這份 plan 執行，避免 plan 和 apply 之間的時間差導致不一致。

**Comment** 把 plan 輸出貼回 PR，reviewer 看 code diff 的同時看到 plan 的實際變更。plan 輸出可能很長（幾百行），超過 GitHub comment 上限時截斷，但保留開頭（通常包含 add/change/destroy 的摘要行）。

## Apply 階段

```yaml
name: Terraform Apply
on:
  push:
    branches: [main]
    paths:
      - 'infra/**'

permissions:
  id-token: write
  contents: read

jobs:
  apply:
    runs-on: ubuntu-latest
    environment: production
    defaults:
      run:
        working-directory: infra/environments/prod

    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/infra-apply
          aws-region: ap-northeast-1

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.9.0

      - name: Init
        run: terraform init -input=false

      - name: Plan (verify)
        run: terraform plan -no-color -input=false -detailed-exitcode

      - name: Apply
        run: terraform apply -auto-approve -input=false
```

### environment protection rule

`environment: production` 這一行啟用 GitHub 的環境保護功能。在 repo 的 Settings → Environments → production 設定：

- **Required reviewers**：指定至少一個人 approve 才能執行 apply job
- **Wait timer**：合併後等 N 分鐘才開始 apply（給人反應時間）
- **Deployment branches**：限定只有 main branch 能觸發

這層保護讓高風險的變更（plan 顯示 destroy 或 replace）在 apply 前多一道人工確認。日常低風險變更（加一個 tag、調一個參數）可以直接通過。取捨點是：每次 apply 都要人按確認會拖慢頻繁的小變更，可以用 deployment rule 的條件只攔 production 環境。

### Apply 階段重跑 plan 的理由

apply 之前重跑一次 plan，是為了驗證合併後的現實跟 PR review 時看到的一致。PR 從開啟到合併可能隔了幾小時或幾天，期間有人可能手動改了雲端資源（drift）或別的 PR 先 apply 了。重跑 plan 確認差異跟預期一致，不一致就停下來而非盲目 apply。

如果使用了 plan 階段的 `-out=tfplan` 保存 plan 檔，apply 可以改為 `terraform apply tfplan` 直接執行已 review 過的 plan。代價是 plan 檔需要跨 job 傳遞（GitHub Actions 的 artifact），且 plan 檔有時效——state 在 plan 之後被修改，apply 會拒絕執行。

## 多環境的 pipeline 設計

管理 dev / staging / prod 三個環境時，pipeline 有兩種常見結構：

**單 workflow 加 matrix**：一份 YAML 用 `strategy.matrix` 跑三個環境，每個環境有自己的 working directory 和 IAM role。好處是維護一份 YAML；代價是三個環境的 plan 都在同一次 PR run 裡，reviewer 要看三份 plan 輸出。

**每環境獨立 workflow**：三份 YAML 各自觸發在對應環境目錄的變更上（`paths: ['infra/environments/dev/**']`）。好處是只有改到的環境才跑、PR comment 乾淨；代價是三份 YAML 有重複。

多數團隊起步時用單 workflow + matrix，環境數量超過三個或各環境的 apply 策略不同（dev 自動、prod 要 approval）時切到獨立 workflow。

## 安全邊界

CI pipeline 是 infra 變更的自動化執行者，它的安全性等同於 apply role 的權限。幾個邊界要守住：

**OIDC claim 收斂**：apply role 的 trust policy 只允許特定 repo 的 main branch 假扮（見 [OIDC Trust Policy 設定](/infra/02-identity-credentials/oidc-trust-policy-setup/)）。如果 claim 只驗 repo 不驗 branch，任何人在 feature branch 推一個修改過的 workflow 就能觸發 apply。

**Workflow 修改的 review**：`.github/workflows/` 底下的 YAML 變更應該跟 infra code 一樣走 PR review。修改 workflow 等於修改 pipeline 的行為——加一個 `terraform destroy` step 就能在合併時清掉整個環境。GitHub 的 CODEOWNERS 功能可以強制特定人 review workflow 變更。

**Secret 與 environment variable**：OIDC 取代了存在 repo secrets 裡的 access key，但 workflow 可能還用到其他 secret（Terraform Cloud token、Slack webhook URL）。這些 secret 要限定在特定 environment 才能存取，不開放給所有 branch。

本篇聚焦 GitHub Actions。如果團隊選擇 Atlantis（常駐服務、內建 state lock 與 apply 語意），見[主文章的 Atlantis 段](/infra/07-infra-as-pr/plan-review-apply-guardrails/)的選型討論。

## 跨分類引用

- → [OIDC Trust Policy 設定](/infra/02-identity-credentials/oidc-trust-policy-setup/)：pipeline 的 credential 來源
- → [checkov / tfsec 規則配置](/infra/07-infra-as-pr/checkov-tfsec-rule-customization/)：pipeline 裡的靜態安全掃描怎麼配
- → [infra 走 PR 流程與自動化護欄](/infra/07-infra-as-pr/plan-review-apply-guardrails/)：pipeline 背後的審查原則
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：多環境的目錄結構決定 pipeline 的 working directory
