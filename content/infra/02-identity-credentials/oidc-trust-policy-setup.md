---
title: "OIDC Trust Policy 設定指南"
date: 2026-06-26
description: "GitHub Actions 與 AWS 之間的 OIDC 聯合設定：建立 provider、設計 trust policy 的 claim 收斂、plan 與 apply role 分離、常見錯誤排查"
weight: 5
tags: ["infra", "iam", "oidc", "github-actions"]
---

OIDC 聯合讓 CI/CD pipeline 用短期 token 取代長期 access key 存取雲端資源。設定本身不複雜，但 trust policy 的 claim 條件寫錯一個字就會變成「任何 repo 都能假扮這個 role」或「完全無法 assume」。本篇是 GitHub Actions 與 AWS 之間的 OIDC 聯合的完整設定步驟，從建立 provider 到 trust policy 設計到測試驗證。其他 CI 平台（GitLab CI、CircleCI）的原理相同，差別只在 issuer URL 和 claim 結構。

## 建立 OIDC Provider

OIDC provider 是 AWS 帳號裡的一個資源，聲明「我信任這個外部 identity provider 簽發的 token」。GitHub Actions 的 OIDC issuer URL 是固定的，每個 AWS 帳號只需要建一個 provider。

```hcl
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["ffffffffffffffffffffffffffffffffffffffff"]
}
```

`client_id_list` 設為 `sts.amazonaws.com` 是 GitHub 官方建議的 audience 值。`thumbprint_list` 在 2023 年之後 AWS 不再用它驗證 GitHub 的憑證鏈（改用 AWS 自己維護的根憑證清單），但欄位仍然是必填，填 40 個 `f` 作為佔位值即可。

這個 provider 建一次就好。多個 role 可以共用同一個 provider，差別在各自的 trust policy 怎麼寫。

## Trust Policy 設計：claim 收斂

Trust policy 決定「誰能假扮這個 role」。OIDC token 裡帶有多個 claim（描述「這是哪個 repo、哪個 branch、哪個 workflow 在跑」），trust policy 用 condition 比對這些 claim，全部命中才允許 assume。

### 最小可行的 trust policy

```hcl
data "aws_iam_policy_document" "ci_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:my-org/my-app:ref:refs/heads/main"]
    }
  }
}
```

兩個 condition 各守一個邊界。`aud` 驗證 audience 對不對（防止其他用途的 token 被拿來 assume）。`sub` 驗證請求來自哪個 repo 和 branch——這是最關鍵的收斂點。

### sub claim 的結構

GitHub Actions 的 `sub` claim 格式是 `repo:{owner}/{repo}:{context}`，其中 context 隨觸發方式不同：

| 觸發方式           | sub claim 值                                |
| ------------------ | ------------------------------------------- |
| push to branch     | `repo:my-org/my-app:ref:refs/heads/main`    |
| pull request       | `repo:my-org/my-app:pull_request`           |
| environment deploy | `repo:my-org/my-app:environment:production` |
| tag push           | `repo:my-org/my-app:ref:refs/tags/v1.0.0`   |
| manual dispatch    | `repo:my-org/my-app:ref:refs/heads/main`    |

Trust policy 的 `sub` condition 要根據實際需要選擇收斂到哪個層級。只允許 main branch 的 push 就寫 `repo:my-org/my-app:ref:refs/heads/main`；只允許 production environment 的 deploy 就寫 `repo:my-org/my-app:environment:production`。

### environment-based 收斂（推薦）

GitHub Actions 的 environment 功能讓 `sub` claim 帶上 environment 名稱。搭配 environment protection rules（required reviewers、wait timer），可以在 trust policy 層和 GitHub 層各設一道 gate：

```hcl
condition {
  test     = "StringEquals"
  variable = "token.actions.githubusercontent.com:sub"
  values   = ["repo:my-org/my-app:environment:production"]
}
```

Workflow 裡對應的設定：

```yaml
jobs:
  apply:
    environment: production
    permissions:
      id-token: write
      contents: read
```

只有 workflow 宣告了 `environment: production` 且通過 environment 的 protection rules 後，runner 拿到的 token 才會帶上 `environment:production` 的 sub claim，才能 assume 這個 role。

## Plan Role 與 Apply Role 分離

把 plan 和 apply 拆成兩個 role，各自給最小權限。plan 只需要 read 權限（讀 state、讀雲端現況），apply 需要 write 權限（建立/修改/刪除資源）。分離的好處是 PR 階段的 plan 即使被攻破，攻擊者也只能讀不能改。

```hcl
resource "aws_iam_role" "infra_plan" {
  name               = "infra-plan"
  assume_role_policy = data.aws_iam_policy_document.plan_trust.json
}

resource "aws_iam_role" "infra_apply" {
  name               = "infra-apply"
  assume_role_policy = data.aws_iam_policy_document.apply_trust.json
}

resource "aws_iam_role_policy_attachment" "plan_readonly" {
  role       = aws_iam_role.infra_plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}
```

Trust policy 的差異：plan role 允許任何 branch 的 PR 觸發（`repo:my-org/my-app:pull_request`）；apply role 只允許 main branch 或 production environment（`repo:my-org/my-app:environment:production`）。

```yaml
jobs:
  plan:
    if: github.event_name == 'pull_request'
    permissions:
      id-token: write
      contents: read
      pull-requests: write
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/infra-plan
          aws-region: ap-northeast-1
      - run: terraform plan -out=plan.tfplan

  apply:
    if: github.ref == 'refs/heads/main'
    environment: production
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/infra-apply
          aws-region: ap-northeast-1
      - run: terraform apply -auto-approve
```

## 常見設定錯誤

### audience 不匹配

```text
Error: Not authorized to perform sts:AssumeRoleWithWebIdentity
```

最常見的原因是 trust policy 的 `aud` condition 值跟 OIDC provider 的 `client_id_list` 不一致。兩者都要是 `sts.amazonaws.com`。如果用了舊版的 `configure-aws-credentials` action（v1），它預設用 `sigstore` 作為 audience，跟 `sts.amazonaws.com` 對不上。確認 action 版本是 v4+。

### sub condition 太寬

```hcl
condition {
  test     = "StringLike"
  variable = "token.actions.githubusercontent.com:sub"
  values   = ["repo:my-org/*"]
}
```

這允許 `my-org` 底下任何 repo 的任何 branch assume 這個 role。如果組織裡有公開 repo 或 fork 權限寬鬆的 repo，攻擊者可以在那些 repo 裡觸發 workflow 來 assume 生產環境的 role。至少收斂到 repo 層級（`repo:my-org/my-app:*`），生產環境收斂到 branch 或 environment。

### sub condition 太緊

```hcl
condition {
  test     = "StringEquals"
  variable = "token.actions.githubusercontent.com:sub"
  values   = ["repo:my-org/my-app:ref:refs/heads/main"]
}
```

這只允許 push to main 觸發的 workflow。PR 觸發的 workflow 拿到的 sub 是 `repo:my-org/my-app:pull_request`，跟這個 condition 不匹配，plan 階段會失敗。如果 plan 需要在 PR 階段跑，plan role 的 trust policy 要加 PR 的 sub pattern。

### 忘記設 permissions

```yaml
jobs:
  deploy:
    # 缺少 permissions 區塊
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
```

GitHub Actions 的 OIDC token 只有在 workflow 宣告 `permissions: { id-token: write }` 時才會簽發。缺了這一行，`configure-aws-credentials` 拿不到 token，報「OIDC token not available」。這個錯誤訊息不直觀——它說的是 token 不存在，不是權限不夠。

### 多帳號時忘記指定 provider

如果組織有多個 AWS 帳號，每個帳號都要各自建 OIDC provider。trust policy 的 `Federated` principal 要指向本帳號的 provider ARN，不能跨帳號引用。跨帳號部署時，workflow 用不同的 `role-to-assume` 切換帳號，每個帳號的 role 各自信任同一個 GitHub OIDC issuer 但是各自獨立的 provider 資源。

## 測試與驗證

設定完成後的驗證步驟：

1. **手動觸發 workflow**：push 一個無害的 commit 到 main、開一個 test PR，觀察 `configure-aws-credentials` 步驟是否成功
2. **檢查 CloudTrail**：搜尋 `AssumeRoleWithWebIdentity` 事件，確認 source identity 和 assumed role 正確
3. **反向驗證**：從一個不在 trust policy 允許範圍的 repo 或 branch 觸發 workflow，確認 assume 被拒絕
4. **權限範圍驗證**：在 plan job 裡嘗試一個 write 操作（如 `aws s3 rm`），確認被拒絕——驗證 plan role 的 read-only 限制確實生效

```bash
# 在 CloudTrail 搜尋 OIDC assume 事件
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRoleWithWebIdentity \
  --max-items 5
```

驗證通過後，這套 OIDC 設定就取代了所有存放在 CI 環境變數裡的 access key。原有的 key 可以排程停用和刪除，排程的節奏見[access key 輪替](/infra/02-identity-credentials/access-key-rotation-playbook/)。trust policy 的持續維護重點是：新增 repo 時 sub condition 要同步更新、組織改名時 issuer 的 repo 路徑要全面修正。

## 跨分類引用

- → [身分與憑證地基](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)：OIDC 的概念基礎與權限邊界設計
- → [infra 走 PR 流程](/infra/07-infra-as-pr/plan-review-apply-guardrails/)：plan/apply 的 CI pipeline 怎麼用這裡設定好的 role
- → [跨帳號策略](/infra/02-identity-credentials/multi-account-strategy/)：多帳號環境下的 OIDC provider 配置
