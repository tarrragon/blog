---
title: "身分與憑證地基 — IAM 模型、OIDC 短期憑證與權限邊界設計"
date: 2026-06-26
description: "IAM 的 identity / policy / role 三元件、最小權限的持續收斂、用 OIDC 取代長期 access key，以及 SCP 與 Permissions Boundary 的環境隔離"
weight: 1
tags: ["infra", "iam", "oidc", "security"]
---

權限一旦散落，後面每一層都建在沙上。網路收斂得再好，只要一把權限過大的長期憑證流出，攻擊者就能繞過所有邊界直接動到核心資源；環境分得再乾淨，只要 production 跟 staging 共用同一組身分，一次誤操作就跨環境炸開。身分與憑證是地基層最先該收斂的能力，因為它決定了「誰能動什麼」這個問題有沒有可信的答案。

## IAM 的心智模型

IAM（Identity and Access Management）是雲端平台用來回答「某個身分能不能對某個資源做某件事」的授權系統。它把授權拆成三個獨立的零件：identity（身分，發起動作的主體）、policy（政策，描述允許或拒絕的規則）、role（角色，一組可以被臨時取得的權限集合）。理解這三者的分工，是後面所有憑證決策的前提。

### identity：長期主體 vs 臨時假扮

identity 分兩類，這個區分在後面設計權限邊界時會反覆用到。一類是 user，代表一個長期存在的主體，通常對應到一個真人或一個固定的服務帳號，本身可以持有長期憑證（密碼或 access key）。另一類是 role，代表一組權限的暫時授予 — 沒有自己的長期密碼，而是讓某個被信任的身分「假扮（assume）」成它、換取一段有時效的臨時憑證。

把 identity 想成「護照」和「通行證」的差別：user 是護照，長期有效、全程攜帶；role 是通行證，到了管制區域臨時換發、離開就失效。多數安全事故源自於把通行證當護照用 — 某個 role 被長期假扮且從未被撤回，或某個 user 持有永不輪替的 access key。

### policy：描述「允許對什麼做什麼」

policy 是貼在 user 或 role 上的規則文件，列出 `Action`（能做什麼，如 `s3:GetObject`）、`Resource`（對哪個資源，如特定 bucket 的 ARN）、`Effect`（Allow 或 Deny）。一條 policy 可以包含多個 statement，每條 statement 描述一組操作許可。

```hcl
# 最小權限範例：CI 只能讀寫特定 bucket，不給整個 S3
data "aws_iam_policy_document" "ci_artifacts" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["arn:aws:s3:::myapp-artifacts/*"]
  }
}
```

這段 policy 只允許對 `myapp-artifacts` 這一個 bucket 做讀寫。如果寫成 `resources = ["*"]`，同一把身分被攻破時，攻擊者就能讀寫帳號內所有 bucket — 差別不在語法，在 `Resource` 欄位收到多緊。

### role：臨時身分的載體

role 本身不持有長期密碼。它靠 trust policy（信任政策）定義「誰能假扮我」，靠 permissions policy 定義「假扮後能做什麼」。trust policy 和 permissions policy 是兩份獨立的文件，分別回答「誰進得來」與「進來後能做什麼」。

```hcl
# trust policy：只允許 ECS 服務假扮此 role
data "aws_iam_policy_document" "ecs_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api_task" {
  name               = "api-task-prod"
  assume_role_policy = data.aws_iam_policy_document.ecs_trust.json
}
```

trust policy 裡的 `principals` 決定能進門的身分。上面這段把進門權限限給 ECS 服務本身，意味著只有跑在 ECS 上的 task 才能取得這個 role 的臨時憑證 — 一個在本地筆電跑的程式呼叫 `AssumeRole` 會被拒絕。

## 最小權限：持續收斂而非一次設定

最小權限（least privilege）是貫穿整套系統的設計原則：一個身分只應該拿到完成它本職工作所需的最小權限集合。多一個 action 是多一條攻擊面，多一個 resource 是多一個爆炸半徑。

最小權限是持續收斂的過程，而非一次設定就結束的靜態狀態。服務初期常為了快速上線給寬鬆權限 — 一個新的 ECS task role 掛上 `AmazonS3FullAccess` 讓它能跑起來，半年後這個 role 實際只用了 `s3:GetObject` 和 `s3:PutObject` 兩個 action、針對一個 bucket，但 policy 裡寫的還是全部 S3 操作對所有 bucket。

收斂的工具是 access analyzer。AWS IAM Access Analyzer 能分析 CloudTrail 日誌，列出某個 role 在過去 N 天內實際用了哪些 action 與 resource，據此產出一份建議的最小 policy。用它的步驟是：開著寬 policy 跑一段時間 → 用 access analyzer 產出實際使用清單 → 把 policy 收斂到這份清單 → 確認服務仍正常。

```bash
# 產出建議 policy：分析 api-task-prod role 過去 90 天的實際用量
aws accessanalyzer generate-policy \
  --policy-generation-details '{
    "principalArn": "arn:aws:iam::123456789012:role/api-task-prod",
    "cloudTrailDetails": {
      "trailArn": "arn:aws:cloudtrail:ap-northeast-1:123456789012:trail/main",
      "startTime": "2026-03-01T00:00:00Z",
      "endTime": "2026-06-01T00:00:00Z"
    }
  }'
```

一個快速的盤點方式：列出所有掛著 `AdministratorAccess`、`PowerUserAccess`、`*FullAccess` 這類寬鬆 managed policy 的 role，每個命中都問一次「這個 role 確實需要這些權限嗎」。CI role 的 policy 裡出現 `*:*` 更是明確的收斂目標。

## 長期 access key 的風險

長期 access key 是一組沒有到期時間的靜態憑證（access key ID + secret），任何持有它的人或程式都能以對應身分的全部權限呼叫 API，直到有人手動撤銷為止。它最大的問題是「沒有時效」這個性質本身，會在三個方向上累積風險，而且風險隨團隊規模與時間單調上升。

### 散落

長期 key 為了被程式使用，會被複製進 `.env` 檔、CI 設定、本機 `~/.aws/credentials`、Slack 訊息、甚至誤推進 git 歷史。每多一個副本就多一個外洩點。一把 key 在半年內可能被貼到六個地方 — 部署腳本、兩個 CI 平台的環境變數、某台共用跳板機的 profile、一封交接信、一位已離職同事的筆電 — 而這六個副本沒有任何中央清單能列舉。

### 權限過大

因為輪替麻煩，團隊傾向給一把 key 配足夠寬的權限「一次搞定」。建立時圖方便掛了 AdministratorAccess，打算「等穩定了再收斂」，但那天從來沒有到來。於是一把本來只該讀 artifact 的 key 同時握有刪除 production 資料庫的能力。

### 難以輪替

輪替一把長期 key 意味著找出所有副本、同步替換、確認沒有遺漏。這個成本高到讓多數團隊選擇拖延，於是 key 的有效期變成「無限」，外洩後的曝險窗口也跟著變成無限。用一個問題辨認風險：能不能在五分鐘內回答「這把 key 被用在哪些地方、上次輪替是什麼時候」？答不出來，它就已經是技術債。

常見的散落路徑：部署腳本使用的 admin key 留在 CI 環境變數，建立者離職後沒人知道這把 key 的存在與權限範圍。這類情境的風險在於外洩後沒有手段限制影響範圍 — key 的權限有多大，影響範圍就有多大。用 credential report 定期盤點帳號內所有 access key 的建立時間與使用時間，見[模組負一：還沒有 infra 的環境](/infra/before-infra/)。

長期憑證風險的實際規模可以從兩個案例看到。Snowflake 2024 事件中，攻擊者利用外洩的長期憑證登入缺少 MFA 的客戶環境，執行大量資料匯出，造成跨客戶的資料竊取與勒索（見 [Snowflake 2024：憑證濫用與資料竊取](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)）。LastPass 2022 事件則顯示備份路徑的憑證管理缺口會讓影響範圍沿信任鏈擴散——開發環境取得的資訊被用來存取雲端備份，整條路徑的金鑰隔離不足是根因（見 [LastPass 2022：備份路徑與鏈式入侵](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/)）。兩個案例的共同教訓是：長期憑證的風險不止於外洩本身，而在於外洩後缺乏限制影響範圍的機制。

## OIDC：給 CI/CD 的短期憑證

OIDC（OpenID Connect）聯合讓 CI/CD 平台用一段每次執行才簽發、幾分鐘後就失效的短期憑證取代長期 key，從根本上消掉「靜態密鑰散落」這個問題。它的運作方式是建立信任關係：雲端帳號信任某個外部 identity provider（如 GitHub Actions 的 OIDC issuer），當管線執行時，CI 平台簽發一個帶有可驗證 claim 的 token（描述「這是哪個 repo、哪個 branch、哪個 workflow 在跑」），雲端用這個 token 換出一段臨時憑證。沒有任何長期 secret 需要被儲存在 CI 設定裡。

### trust policy 的收斂

關鍵設計在 role 的 trust policy 上 — 它規定「哪個外部身分被允許假扮成這個 role」。trust policy 要用 token 的 claim 把假扮條件收到最緊。

```hcl
# OIDC trust policy：只允許特定 repo 的 main branch 假扮此 role
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

每個 condition 各守一段邊界。`aud` 的 `StringEquals` 確認 token 是發給 AWS STS 的（防止用錯 audience 的 token 闖入）。`sub` 的 `StringLike` 把假扮限定在特定 repo 的 main branch — 設成 `repo:my-org/*` 等於讓組織內任何 repo 的任何 branch 都能假扮這個 role，這是常見的設定陷阱。

收斂 trust policy 的判讀問法是：「如果 my-org 底下某個公開 fork 跑了一個惡意 workflow，它能不能假扮這個 role？」如果答案是能，`sub` 條件就太鬆了。

### 分離 plan 與 apply 的 role

進一步的收斂是替 `plan` 和 `apply` 分別建立 role。plan 只需要唯讀存取（讀 state、讀雲端現況），apply 需要寫入權限。把兩者分成獨立 role，讓 PR 階段的 CI 用唯讀 role 跑 plan、合併後才用寫入 role 跑 apply。任何拿到 plan role 的 token 無法修改基礎設施。

```hcl
# plan role：只需讀取 state 與雲端現況
resource "aws_iam_role" "ci_plan" {
  name               = "infra-ci-plan"
  assume_role_policy = data.aws_iam_policy_document.ci_trust.json
}

resource "aws_iam_role_policy_attachment" "ci_plan_read" {
  role       = aws_iam_role.ci_plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

# apply role：需要寫入權限，trust policy 限定只有 main branch
resource "aws_iam_role" "ci_apply" {
  name               = "infra-ci-apply"
  assume_role_policy = data.aws_iam_policy_document.ci_trust_main_only.json
}
```

這一章把 role 與 trust policy 設計好，OIDC 的實際回報要到[模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)建管線時才兌現 — 屆時管線用這裡定義好的 role 取得短期權限執行 `plan` 與 `apply`，CI 環境裡不需要存任何 access key。

## 權限邊界設計

權限邊界是把不同類型的身分與不同環境之間的權限刻意隔開，讓任何一個身分被攻破時，爆炸半徑都被限制在它本職的範圍內。邊界設計有兩條軸線需要分別處理：人 vs 機器，以及環境之間。

### 人 vs 機器

兩者的存取模式根本不同，混在同一個身分上會同時喪失兩邊的保護。

人類身分需要互動式登入、應該強制 MFA、權限隨職責變動，且通常透過 SSO 集中管理。機器身分（CI runner、ECS task、Lambda function）需要的是程式化、無人值守的存取，應該用 role 假扮取得短期憑證，永遠不該配長期 key。

機器身分還要再依「跑在哪裡」分兩類。跑在雲上的 workload（EC2 instance、ECS task、Lambda）由平台直接把 role 綁在執行環境上 — AWS 用 instance profile 把 role 掛在 EC2、用 task role 掛在 ECS task，workload 從實例 metadata 端點自動取得輪替的短期憑證。跑在雲外的 CI/CD（GitHub Actions、GitLab CI）拿不到實例 metadata，需要前面那套 OIDC 信任關係換憑證。

一個常見陷阱是工程師用自己的個人 key 跑自動化腳本 — 這把人的廣泛權限直接送進了無人值守的執行環境，MFA 保護形同虛設（API 呼叫不需要 MFA challenge），權限範圍比任何 CI role 都大。

### 環境之間

環境之間的邊界，目的是讓 production 的權限與 staging、dev 完全不交叉。驗證邊界的方式是用 dev 環境的 CI role 嘗試列出或刪除 production 的資源——能做到，就代表邊界沒有建立。

#### 帳號級護欄：SCP

Organizations 把環境拆成獨立帳號，再用 SCP（Service Control Policy）對整個帳號或組織單位設定權限天花板，連帳號內的管理員都越不過去。SCP 是 deny-based 的頂層限制 — 它不授予任何權限，只限制「即使有人給了權限也不准做」。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyLeaveOrg",
      "Effect": "Deny",
      "Action": ["organizations:LeaveOrganization"],
      "Resource": "*"
    },
    {
      "Sid": "DenyDisableCloudTrail",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail"
      ],
      "Resource": "*"
    }
  ]
}
```

這份 SCP 掛在整個組織底下的所有帳號上，確保任何帳號都不能關閉稽核日誌或退出組織 — 即使該帳號裡有人持有 AdministratorAccess。SCP 的定位是組織層的不可踰越底線。

#### Role 級護欄：Permissions Boundary

Permissions Boundary 是掛在單一 role 上的權限上限。它跟 SCP 的差別在粒度：SCP 管整個帳號，Permissions Boundary 管單一身分。即使有人後來給一個 role 貼了過寬的 policy，Boundary 也會擋住超出上限的部分。

```hcl
# Permissions Boundary：CI role 最多只能操作特定服務
resource "aws_iam_policy" "ci_boundary" {
  name = "ci-boundary-prod"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:*", "ecr:*", "s3:*", "logs:*"]
        Resource = "*"
      },
      {
        Effect   = "Deny"
        Action   = ["iam:*", "organizations:*", "account:*"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "ci_apply" {
  name                 = "infra-ci-apply"
  assume_role_policy   = data.aws_iam_policy_document.ci_trust.json
  permissions_boundary = aws_iam_policy.ci_boundary.arn
}
```

SCP 與 Permissions Boundary 疊起來的效果是：SCP 在帳號層鎖住最危險的操作（關日誌、退組織），Boundary 在 role 層限制單一身分最多能做什麼，permissions policy 在這兩層天花板之內授予實際需要的權限。三者各管一層，缺一層就少一道屏障。

身分控制面本身的韌性在兩個案例中被檢驗。Azure AD 2021 事件中，身分服務的控制面故障導致所有依賴身份驗證的服務同時受影響，事故處理需要在身份恢復與服務降級策略之間排優先序（見 [Azure AD：Identity Control-plane 事件](/backend/07-security-data-protection/cases/azure-ad-identity-control-plane-2021/)）。Microsoft Storm-0558 事件則顯示簽章金鑰一旦失守，token 驗證的信任鏈會跨租戶失效，修復不只是修補漏洞、而是重建整條 key lifecycle 與 issuer 驗證流程（見 [Microsoft：Storm-0558 簽章金鑰事件](/backend/07-security-data-protection/cases/microsoft-storm-0558-signing-key-2023/)）。這兩個案例揭露的是：權限邊界只管「某個身分能做什麼」，但身分系統本身的控制面如果失效，所有建立在它之上的邊界都跟著失效。

環境隔離的更完整實作（帳號結構、模組化參數）會在[模組四：環境分離與模組化](/infra/04-environment-separation/)展開。

## 身分層 vs 應用層 secret 的邊界

這一章談的是身分與憑證 — 誰是誰、怎麼證明、能動什麼。憑證背後引用的應用層 secret（資料庫密碼、第三方 API key）怎麼安全儲存與注入，屬於[模組八：治理好習慣](/infra/08-governance-habits/)的 secret management 範圍。兩者的交集是：身分層決定「誰能讀到 secret store」，secret 層決定「secret 怎麼存與輪替」。把 IAM role 的 policy 收到只能讀取該服務路徑下的 secret（如 `prod/payments/*`），是同時落實最小權限與 secret 隔離的結合點。

身分與憑證的地基備妥後，下一步是劃清服務之間的網路邊界——這正是[模組三：網路地基](/infra/03-network-foundation/)的範圍。

## 跨分類引用

- → [模組負一：還沒有 infra 的環境](/infra/before-infra/)：長期 key 盤點與護欄
- → [模組三：網路地基](/infra/03-network-foundation/)：身分備妥後，劃清服務之間的網路邊界
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：環境之間的帳號結構與隔離強度
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：CI/CD 管線用 OIDC 取得短期權限
- → [模組八：治理好習慣](/infra/08-governance-habits/)：應用層 secret 的儲存與引用
- → [backend 模組七：資安與資料保護](/backend/07-security-data-protection/)：Secret Management 與憑證管理交集
