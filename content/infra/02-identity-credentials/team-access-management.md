---
title: "團隊權限分級與存取管理"
date: 2026-06-26
description: "用 admin / operator / viewer 三級劃分團隊成員的雲端操作權限，設計臨時提權流程、定期 access review 節奏，以及 contractor 與外部 vendor 的存取邊界"
weight: 3
tags: ["infra", "iam", "access-management", "security"]
---

IAM 的 role 與 policy 提供「某個身分能不能對某個資源做某件事」的技術機制（見[身分與憑證地基](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)）。機制備妥後，下一個問題是組織層面的設計：團隊裡每個角色該拿到哪一級權限、臨時需要更高權限時怎麼提權、離職或合約結束時怎麼確保存取被回收。這些設計的目的是讓「誰能動什麼」在任何時間點都有可稽核的答案。

## 權限分級：admin / operator / viewer

團隊成員的日常操作權限用三級來劃分，每一級對應不同的操作範圍與風險。分級的依據是「這個角色的日常工作需要碰到什麼層級的資源」，不是職稱或年資。

### Admin

Admin 能修改 IAM policy、網路拓撲、帳號層級設定（Organizations、SCP、billing）。這是影響範圍最大的一級——一條 SCP 寫錯可以鎖死整個帳號的操作，一條 IAM policy 開太寬可以讓任何角色取得不該有的權限。

持有 admin 權限的人數應該收斂到最少：通常是平台團隊的 1-2 人加上一個 break-glass 備援角色。Admin 權限不應該是某個人的「日常身分」——即使是平台工程師，日常操作也用 operator 等級，只有在需要改 IAM 或帳號設定時才 assume 到 admin role。

```hcl
# Admin role 的信任政策：只允許特定 IAM user assume
data "aws_iam_policy_document" "admin_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = [
        "arn:aws:iam::123456789012:user/platform-lead",
        "arn:aws:iam::123456789012:user/platform-backup",
      ]
    }
    condition {
      test     = "Bool"
      variable = "aws:MultiFactorAuthPresent"
      values   = ["true"]
    }
  }
}

resource "aws_iam_role" "admin" {
  name               = "infra-admin"
  assume_role_policy = data.aws_iam_policy_document.admin_trust.json
  max_session_duration = 3600  # 1 小時後自動失效
}
```

`max_session_duration` 限制 assume 後的有效時間。Admin session 設 1 小時是讓操作者完成當次任務後權限自動回收，不需要手動登出。MFA 條件確保即使帳號密碼外洩，沒有第二因素也無法提權。

### Operator

Operator 能部署服務、修改應用層資源（ECS task、RDS parameter group、S3 lifecycle）、查看與操作日常維運所需的一切。多數工程師的日常身分落在這一級。

Operator 的 policy 用 resource scope 限制它碰不到 IAM 和帳號層級設定——能改 ECS service 但不能改 ECS service 用的 IAM role，能改 RDS 參數但不能改 RDS 的 subnet group。這個邊界讓 operator 的操作失誤影響範圍停在服務層，不會擴散到地基層。

```hcl
data "aws_iam_policy_document" "operator" {
  # 允許操作應用層資源
  statement {
    actions = [
      "ecs:UpdateService", "ecs:DescribeServices",
      "rds:ModifyDBInstance", "rds:DescribeDBInstances",
      "s3:GetObject", "s3:PutObject",
      "logs:GetLogEvents", "logs:FilterLogEvents",
    ]
    resources = ["*"]
  }

  # 明確拒絕碰 IAM 和帳號設定
  statement {
    effect = "Deny"
    actions = [
      "iam:*",
      "organizations:*",
      "account:*",
    ]
    resources = ["*"]
  }
}
```

Deny 語句確保即使未來有人不小心把過寬的 managed policy attach 到 operator role，IAM 和帳號操作仍然被擋。Deny 在 IAM 評估中優先於 Allow。

### Viewer

Viewer 能讀取 Console、查 log、看 metric dashboard，但不能修改任何資源。適合的角色包括：值班但不需要改設定的 on-call、需要查 log 排查問題的 support 團隊、需要看資源狀態的管理層。

Viewer 用 AWS 的 managed policy `ReadOnlyAccess` 作為基線，再根據需要排除敏感資料的讀取（例如 Secrets Manager 的 `GetSecretValue`）。

三級的對應關係：

| 級別     | 能做什麼                       | 典型角色                 | 人數控制   |
| -------- | ------------------------------ | ------------------------ | ---------- |
| Admin    | 改 IAM、網路、帳號設定         | 平台 lead + break-glass  | 2-3 人     |
| Operator | 部署、改服務設定、查 log       | 工程師                   | 團隊規模   |
| Viewer   | 讀 Console、查 log、看 metrics | on-call、support、管理層 | 依需求開放 |

導入時程參考：三級權限的 IAM role 與 policy 建立約需 1-2 天，包含 trust policy 設定與初次分配。後續的權限變更走版本控制的 PR 流程，讓每次 policy 調整都有提案、審查與歷史紀錄（見[infra 走 PR 流程](/infra/07-infra-as-pr/)）。

## 臨時提權（break-glass）

Operator 在日常工作中偶爾需要 admin 層級的操作——排查一個涉及 IAM 的事故、緊急修改一條 security group 規則、回應安全事件。常態性地把 admin 權限開給所有 operator 會讓三級分級失效，但每次都等 admin 角色的人上線又太慢。Break-glass 流程處理的就是這個中間地帶。

### 機制

Break-glass 的實作是一個平時不被 assume 的 admin role，加上一套提權紀錄。Operator 在需要時 assume 這個 role，取得一段時效有限的 admin session。這個 assume 動作會在 CloudTrail 留下紀錄（誰、什麼時候、session 多長），事後可稽核。

```hcl
resource "aws_iam_role" "break_glass" {
  name                 = "infra-break-glass"
  assume_role_policy   = data.aws_iam_policy_document.break_glass_trust.json
  max_session_duration = 3600

  tags = { Purpose = "emergency-escalation" }
}
```

如果團隊有 ChatOps 或 ticketing 系統，把 break-glass 的觸發綁進去可以增加一層人為確認：operator 在 Slack 或 ticket 裡申請提權、另一個人核可、系統開放 assume。這層確認的目的是在事後稽核時留下一條清楚的「誰授權了這次提權」紀錄，而非阻止操作本身。

### 事後回顧

每一次 break-glass 使用都應該進入事後回顧：為什麼需要提權？這個操作能不能改寫成 operator 層級的權限就能完成？如果某類操作反覆觸發 break-glass，代表 operator 的權限邊界需要調整——把那類操作從 admin 降到 operator，而不是讓 break-glass 變成常態。

回顧的輸出是權限邊界的校準，不是對操作者的檢討。

## 定期 access review

權限分配不是一次性的設定。人會換組、離職、從 contractor 轉正職、從開發角色轉管理角色，每一次角色變動都可能讓既有的權限配置過期。定期 review 的責任是找出「權限比當前角色需要的更寬」的身分，把它們收斂回來。

### 節奏與方法

每季做一次 access review 是多數團隊能維持的最小節奏。Review 的步驟：

1. 拉出所有 IAM user 和 role 的清單，標注每個身分目前的分級（admin / operator / viewer）
2. 比對每個身分的實際角色——這個人現在還在做需要 operator 權限的工作嗎？
3. 用 IAM Access Analyzer 檢查哪些權限在過去 90 天沒被使用過——沒用到的權限是收斂候選
4. 特別檢查 break-glass 的使用紀錄——有沒有人的 break-glass 使用頻率高到代表他的基線權限該調整

```bash
# 產出 credential report，列出所有 user 的 key 建立時間與使用時間
aws iam generate-credential-report
aws iam get-credential-report --output text --query Content | base64 -d | head -20

# 查 Access Analyzer 的 finding（哪些權限可收斂）
aws accessanalyzer list-findings --analyzer-arn <analyzer-arn> \
  --filter '{"status": {"eq": ["ACTIVE"]}}'
```

### 管理層報告

Access review 的結果適合用兩個數字向管理層報告：**覆蓋率**（已 review 的身分數 / 總身分數）與**異常數**（權限過寬或長期未使用的身分數）。異常數的趨勢比單次數字更有意義——持續上升代表新人 onboarding 時的權限配置流程有缺口，持續下降代表 review 在發揮作用。

導入時程參考：第一次 access review 約需半天到一天（盤點 + 比對 + 收斂），後續每季約需 2-4 小時。

## 職務交接與離職處理

一個人離開團隊時，他持有的所有存取路徑都需要被回收。手動建立的存取路徑越多，離職處理越容易遺漏。

### 離職 checklist

| 項目                           | 操作                                            | 驗證方式                       |
| ------------------------------ | ----------------------------------------------- | ------------------------------ |
| IAM user / SSO 帳號            | 停用或刪除                                      | credential report 裡不再出現   |
| 長期 access key                | 撤銷所有 key                                    | `list-access-keys` 回傳空      |
| 個人 MFA 裝置                  | 解除綁定                                        | `list-mfa-devices` 回傳空      |
| 被加進的 IAM group             | 移除成員                                        | `get-group` 裡不再出現         |
| 可 assume 的 role trust policy | 從 principal 清單移除                           | trust policy 裡沒有該 user ARN |
| 第三方服務的 SSO 授權          | 撤銷（GitHub org、CI 平台、Slack workspace 等） | 該帳號無法登入                 |
| 共用密碼 / shared credential   | 輪替（如果存在的話）                            | Secrets Manager 版本更新       |

權限設計越集中在 role-based（用 IAM group 或 SSO permission set），離職處理越簡單——停用 SSO 帳號就自動切斷所有透過 SSO 取得的 role。反過來，如果有大量手動 attach 的 policy 或直接寫在 trust policy 裡的 user ARN，離職時要逐一找出並移除，容易遺漏。

離職後的 credential rotation 有一個常被忽略的風險：輪替範圍沒有按作用域分批。一個反例是多個服務共用同一把 secret，輪替時切新憑證的服務跟還只認舊憑證的服務之間出現認證窗口不一致，導致跨系統連鎖中斷。穩定的做法是先分域隔離受影響服務、恢復雙憑證窗口、再逐批收斂（見 [反例：憑證輪替未分 Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)）。

### 交接的可執行性

交接的成本取決於知識有多少沉澱在程式碼裡、有多少留在個人腦中。如果環境的建立方式是一份 IaC、變更方式是 PR 歷史，新接手的人讀 code 跟 PR 描述就能重建脈絡。如果關鍵操作（某台資料庫的特殊 parameter、某條 security group 規則的理由）只存在離職者的記憶裡，交接窗口一過就永久遺失。

可操作的檢驗：問「如果這個人下週離職，團隊能不能只靠讀 repo 就安全地操作他負責的環境？」答案是否定的部分，就是交接的優先補強項——優先把它們寫進 IaC 或 PR 描述，而不是寫進交接文件（交接文件會過期，IaC 跟著環境一起演進）。

這個議題在[知識共享優於個人英雄主義](/infra/09-driving-adoption/trust-alignment-knowledge-sharing/)有組織層面的展開。

## Contractor 與外部 vendor 存取

外部人員（contractor、顧問、SaaS vendor 的技術支援）需要存取雲端環境時，原則是給最小範圍、設明確時限、留完整紀錄。

### 範圍限制

外部人員的 role 用 Permissions Boundary 設定權限天花板，確保即使有人誤 attach 了過寬的 policy，操作範圍也不超過 boundary 允許的上限。Scope 到具體的資源 ARN（某個 S3 bucket、某台 RDS instance），而非帳號級別的 wildcard。

如果團隊已經有[跨帳號策略](/infra/02-identity-credentials/multi-account-strategy/)，把外部人員的 workload 放在獨立帳號或 sandbox OU 裡，用 SCP 限制該帳號能操作的服務類型，是比 role 級別限制更強的隔離。

### 時限控制

外部存取的 IAM user 或 SSO 帳號在建立時就設定到期日。多數雲端平台支援 session duration 限制（role 的 `max_session_duration`）和帳號層級的停用排程。合約結束日應該對應到存取到期日——這個對應關係寫進 IaC（用 tag 標注到期日）或團隊的 access review checklist，避免合約結束後存取仍然開著。

### 稽核紀錄

外部人員的操作需要比內部人員更嚴格的稽核。CloudTrail 預設記錄所有 API 呼叫，但 review 的頻率要提高——外部人員的操作紀錄每週抽查，而非等到季度 access review 才回頭看。查的是：有沒有存取超出約定範圍的資源？有沒有在非工作時間操作？有沒有大量的 read 操作指向敏感資料？

這些紀錄同時也是合約管理的依據——如果外部 vendor 的技術支援存取了超出約定範圍的資源，紀錄是釐清責任的事實基礎。

## 跨分類引用

- → [身分與憑證地基](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)：IAM role / policy / OIDC 的技術機制
- → [跨帳號策略](/infra/02-identity-credentials/multi-account-strategy/)：用 OU 和 SCP 在帳號層級隔離外部人員
- → [治理好習慣](/infra/08-governance-habits/tagging-secrets/)：tagging 標注存取到期日、secrets 不進 code
- → [怎麼把 infra 推動起來](/infra/09-driving-adoption/trust-alignment-knowledge-sharing/)：知識共享與交接的組織面
