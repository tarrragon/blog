---
title: "跨帳號策略 — Organizations、SCP 與帳號工廠"
date: 2026-06-26
description: "用 AWS Organizations 把環境拆成獨立帳號、用 SCP 設定連管理員都越不過的護欄、用帳號工廠讓每個新帳號自帶安全基線"
weight: 2
tags: ["infra", "iam", "organizations", "scp", "multi-account"]
---

單一帳號走到某個規模後，帳號本身會變成隔離的瓶頸。IAM policy 能控制「誰能做什麼」，但同一個帳號裡的所有資源共用同一組 service quota、同一份 CloudTrail、同一張帳單，一個團隊的操作失誤或資源耗盡會波及整個帳號。把環境拆成獨立帳號，讓每個帳號只承載一個職責，是 IAM 之上的第二層隔離 — [模組二的身分與憑證地基](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)控制的是「誰能做什麼」，帳號邊界控制的是「做錯了波及多遠」。

## 單帳號 vs 多帳號：什麼時候該切

單帳號在早期是合理的起點 — 資源少、人少、管理成本低。帳號邊界帶來的隔離收益要跟它的管理成本比較：每多一個帳號就多一份 CloudTrail、多一組 IAM 基線、多一個需要管理的 state backend。

三個訊號出現時，單帳號的邊際風險開始超過多帳號的管理成本：

第一，production 和 dev 的資源開始互相影響。一個 dev 環境的壓力測試把帳號的 EC2 instance quota 吃滿，production 的 auto-scaling 因為拿不到新 instance 而失敗 — 這個故障跟程式碼品質無關，純粹是兩個環境共用同一組配額。帳號分開後，dev 吃滿自己的 quota 不會碰到 production。

第二，權限邊界用 IAM 已經管不住。一個工程師的 IAM policy 限制他只能操作 `env=dev` 的資源，但他手滑用了一個沒有 tag 條件的 policy、或者某個 IAM role 的 trust policy 太寬，他就能碰到 production 資源。帳號邊界是比 IAM policy 更硬的護欄 — 即使 IAM 設定出錯，帳號邊界本身就是物理隔離。

第三，合規或稽核要求明確區分環境。SOC 2 或金融監管可能要求 production 環境有獨立的存取紀錄和變更審計，與開發環境完全分離。同帳號裡做這件事要靠大量的 IAM 條件和 CloudTrail filter，跨帳號則天然滿足。

## OU 結構：帳號怎麼分群

AWS Organizations 用 Organizational Unit（OU）把帳號分群，OU 是 SCP 的掛載點 — 一條 SCP 掛在 OU 上，底下所有帳號都受約束。OU 的設計決定了護欄的作用範圍。

常見的 OU 拓撲有四層：

| OU                 | 底下的帳號                         | 職責                                            |
| ------------------ | ---------------------------------- | ----------------------------------------------- |
| Security           | Log Archive、Security Tooling      | 集中存放 CloudTrail / Config 日誌、安全工具帳號 |
| Workload / Prod    | 每個產品線或服務的 production 帳號 | 承載正式流量，SCP 最嚴格                        |
| Workload / NonProd | dev、staging 帳號                  | 承載開發與驗證，SCP 較寬鬆但仍有底線            |
| Sandbox            | 個人實驗帳號                       | 可隨時重建，SCP 限制預算上限和禁止的服務        |

環境怎麼對應到帳號，跟[模組四的環境分離](/infra/04-environment-separation/directory-module-parameterization/)是同一個問題的不同層次 — 模組四用目錄和 state 分離環境的 IaC，這裡用帳號分離環境的雲端資源。兩者可以疊加：每個帳號裡的 IaC 仍然用獨立目錄和 state 管理。

OU 結構的設計原則是「按信任等級分群、按職責隔離」。Prod 跟 NonProd 分開是因為信任等級不同（prod 的 SCP 更嚴格）。Security 獨立是因為它的職責是「監控其他所有帳號」— 如果 security 帳號被攻破，攻擊者能修改稽核日誌來掩蓋行蹤，所以它的存取權限要收到最小。

一個常見的錯誤是把 OU 當成組織架構的映射（按部門分 OU）。OU 的分群依據是安全邊界和 SCP 策略，不是彙報線。兩個部門如果需要相同的 SCP，它們的帳號應該在同一個 OU 底下；一個部門如果有 prod 和 dev 環境，它們應該在不同 OU 底下。

## SCP：連管理員都越不過的護欄

Service Control Policy（SCP）是掛在 OU 或帳號上的權限天花板。它跟 IAM policy 的差別是層級：IAM policy 控制「這個身分能做什麼」，SCP 控制「這個帳號裡的任何身分最多能做什麼」。即使帳號內的 root user 或 AdministratorAccess role，也受 SCP 約束。

SCP 的設計策略以 deny-list 為主 — 預設允許所有動作，用 SCP 明確禁止少數高風險操作。相比 allow-list（預設禁止、逐一開放），deny-list 的管理成本低得多，因為 AWS 的 service 和 action 數量龐大，逐一列舉允許清單容易漏、也容易在新服務上線時擋住正常使用。

三條適合從第一天就掛上去的 SCP：

### 禁止關閉 CloudTrail

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyCloudTrailDisable",
    "Effect": "Deny",
    "Action": [
      "cloudtrail:StopLogging",
      "cloudtrail:DeleteTrail",
      "cloudtrail:UpdateTrail"
    ],
    "Resource": "*"
  }]
}
```

CloudTrail 是事後追溯「誰做了什麼」的唯一來源。攻擊者入侵帳號後的第一步往往是關掉稽核日誌來掩蓋行蹤，用 SCP 禁止這個動作，讓日誌在帳號層級不可關閉。

### 禁止離開指定 region

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyOutsideRegion",
    "Effect": "Deny",
    "NotAction": [
      "iam:*",
      "sts:*",
      "organizations:*",
      "support:*"
    ],
    "Resource": "*",
    "Condition": {
      "StringNotEquals": {
        "aws:RequestedRegion": ["ap-northeast-1", "us-east-1"]
      }
    }
  }]
}
```

限制資源只能建在指定 region，避免有人在沒人注意的 region（如 `af-south-1`）開資源 — 不管是誤操作還是攻擊者利用。`NotAction` 裡排除 IAM 和 STS 等全域服務，因為它們不分 region。`us-east-1` 通常要保留，因為 CloudFront、ACM（global cert）等服務的 API 端點在 us-east-1。

### 禁止刪除 VPC Flow Logs

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyDeleteFlowLogs",
    "Effect": "Deny",
    "Action": "ec2:DeleteFlowLogs",
    "Resource": "*"
  }]
}
```

VPC Flow Logs 記錄網路層的流量軌跡，是安全事件排查的關鍵資料。跟 CloudTrail 的邏輯一樣 — 稽核資料不允許被帳號內的操作者刪除。

### SCP 的繼承模型

SCP 沿著 OU 樹向下繼承：掛在 Root OU 的 SCP 對所有帳號生效，掛在子 OU 的 SCP 只對該 OU 底下的帳號生效。多層 SCP 的效果是交集 — 父 OU 禁止的動作，子 OU 無法用 SCP 重新允許。這個交集模型讓安全團隊能在頂層設「絕對底線」，各子 OU 只能在底線之內進一步收斂、不能放寬。

把 SCP 用 Terraform 管理：

```hcl
resource "aws_organizations_policy" "deny_cloudtrail_disable" {
  name        = "deny-cloudtrail-disable"
  description = "Prevent anyone from stopping or deleting CloudTrail"
  type        = "SERVICE_CONTROL_POLICY"
  content     = file("policies/deny-cloudtrail-disable.json")
}

resource "aws_organizations_policy_attachment" "root_deny_cloudtrail" {
  policy_id = aws_organizations_policy.deny_cloudtrail_disable.id
  target_id = aws_organizations_organization.main.roots[0].id
}
```

SCP 的 JSON 存在 repo 的 `policies/` 目錄，變更走 PR review，讓護欄本身也在版本控制與審查流程裡。

控制面 token 的治理是 SCP 護欄之外需要同步處理的議題。Cloudflare 2023 事件中，控制面 token 的生命週期與最小權限沒有對齊，機器憑證形成跨服務的高權限風險（見 [Cloudflare：Control-plane Token 事件](/backend/07-security-data-protection/cases/cloudflare-control-plane-token-2023/)）。Okta 2023 事件則顯示身份治理若只覆蓋生產系統而忽略支援工具鏈，支援系統的 session 和 token 會成為跨租戶的風險放大點（見 [Okta：Support System 事件](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/)）。兩個案例的共同教訓是：SCP 管的是 AWS API 層的動作上限，但 token / session 這類應用層的機器憑證需要獨立的 lifecycle 治理。

## 帳號工廠：每個新帳號自帶安全基線

跨帳號策略（帳號數量、OU 結構、SCP 規則）屬於影響全組織的架構決策，建議在實施前取得技術主管或 CTO 的對齊。SCP 一旦套用到 OU，該 OU 下所有帳號立即受影響，回退需要修改 SCP 或移動帳號到不同 OU。

手動建帳號的問題跟手動建資源一樣 — 每次都靠人記得「開完帳號後要開 CloudTrail、要刪預設 VPC、要設基線 IAM role」。帳號工廠（Account Factory）把這些步驟自動化成一個可重複的流程：建一個帳號、自動套用安全基線、自動加進正確的 OU。

AWS Control Tower 是 AWS 提供的帳號工廠實作，它包裝了 Organizations、SCP、Config Rules 和 CloudFormation StackSet，提供一個「建帳號 → 自動配置」的流水線。它的好處是一鍵啟用、內建一組 AWS 建議的護欄；代價是它對 OU 結構和 SCP 有自己的意見，跟團隊已有的設計可能衝突，而且它用 CloudFormation StackSet 做基線配置，跟 Terraform 管理的資源需要劃清邊界。

不用 Control Tower 時，帳號工廠可以用 Terraform + 腳本自建。核心是一個 module 接受帳號名稱和 OU 作為參數，產出：帳號建立、CloudTrail trail、預設 VPC 刪除、基線 IAM role（讓管理帳號能 assume 進來做維護）、Config recorder 啟用。

每個新帳號該自帶的安全基線至少包含：

- CloudTrail 開啟並寫到集中的 Log Archive 帳號
- 預設 VPC 刪除（預設 VPC 的 security group 全通、CIDR 固定且跨帳號重複，留著是隱患）
- 基線 IAM role 讓管理帳號能 assume 進來
- Config recorder 啟用（記錄資源設定變更歷史）
- 掛上所屬 OU 的 SCP

導入時程參考：初次設定 Organizations + OU 結構 + day-1 SCP 約需 2-3 天；之後每開一個新帳號（含基線配置）約需 2-4 小時。

## 跨帳號存取：role assumption

多帳號架構裡，人或自動化需要在不同帳號之間切換操作。跨帳號存取用 IAM role 的 trust policy 實現 — 目標帳號建一個 role，trust policy 允許來源帳號的特定身分 assume 這個 role。

AWS Organizations 在建子帳號時會自動建一個 `OrganizationAccountAccessRole`，讓管理帳號的 admin 能 assume 進去。這個 role 的權限是 AdministratorAccess — 它的用途是初始設定和緊急存取，日常操作不該用它。日常的跨帳號存取應該建立職責專用的 role：部署用的 role 只有部署相關權限、唯讀稽核用的 role 只有 read 權限。

```hcl
resource "aws_iam_role" "deploy_from_cicd" {
  name = "deploy-from-cicd-account"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::111111111111:role/cicd-runner" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "sts:ExternalId" = "deploy-prod-2026" }
      }
    }]
  })
}
```

`ExternalId` 是防止 confused deputy 攻擊的機制 — 如果 trust policy 只用帳號 ID 驗證，任何能在來源帳號建 role 的人都能 assume 目標 role。加上 ExternalId 讓 assumption 多一個只有雙方知道的驗證值。

跨帳號存取的設計與[模組二的 OIDC 短期憑證](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)互補 — OIDC 解決「雲外到雲內」的身分聯合（CI/CD → AWS），role assumption 解決「雲內帳號之間」的身分切換。

## 帳單整合

Organizations 的附帶收益是合併帳單（Consolidated Billing）。所有子帳號的用量合併到管理帳號的帳單裡，一方面簡化付款流程（一張帳單而非多張），另一方面可以享受跨帳號的用量折扣 — 例如 S3 的定價階梯是看總用量，三個帳號各用 1TB 分開計費跟合併成 3TB 計費，後者的單位價格更低。

合併帳單跟成本歸屬的 tagging 互補。合併帳單讓所有費用匯到一張帳單，tagging 讓這張帳單能拆到各團隊和用途 — 這兩件事在[模組八的成本可見性](/infra/08-governance-habits/cost-visibility-rhythm/)展開。帳號邊界本身也是一層成本隔離：每個帳號的用量可以獨立查看，讓「這個帳號這個月花了多少」變成自動可查、不需要依賴 tag。

## 跨分類引用

- → [身分與憑證地基](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)：IAM role / policy / OIDC 是帳號內的身分控制，本篇是帳號間的隔離
- → [環境分離與模組化](/infra/04-environment-separation/directory-module-parameterization/)：目錄與 state 分離環境的 IaC，帳號分離是雲端資源層的對應
- → [成本可見性](/infra/08-governance-habits/cost-visibility-rhythm/)：合併帳單 + tagging 的成本歸屬
- → [infra 走 PR 流程](/infra/07-infra-as-pr/plan-review-apply-guardrails/)：SCP 的 JSON 存 repo、變更走 PR review
