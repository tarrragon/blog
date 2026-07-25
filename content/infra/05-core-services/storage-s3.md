---
title: "儲存上 IaC — S3 bucket 的安全與生命週期"
date: 2026-06-26
description: "S3 bucket 的加密、版本控制、公開存取封鎖、生命週期規則、bucket policy 與事件通知怎麼寫進 IaC，讓儲存的安全與成本防線可審查可追蹤"
weight: 3
tags: ["infra", "iac", "s3", "storage"]
---

[S3](/infra/knowledge-cards/s3/) bucket 描述的是物件儲存的存在、命名、加密設定、版本控制與存取政策。bucket 本身沒有重建代價意義上的狀態問題 — 困難在它「裝的東西」。空 bucket 可隨時重建，裝了正式資料的 bucket 與 RDS 一樣不可隨意 destroy。把安全設定與生命週期規則寫進 IaC，讓這些防線成為可版本控制、可審查的程式碼，而非散落在 Console 的隱性設定。

## bucket 的四道安全防線

一個 S3 bucket 在 IaC 裡至少要描述四個獨立資源，各自對應一道防線。Terraform 把它們拆成獨立資源是設計選擇 — 每道防線可以單獨 review、單獨調整、單獨追蹤變更歷史。

```hcl
resource "aws_s3_bucket" "assets" {
  bucket = "acme-${var.env}-assets"

  tags = { service = "cdn-origin", env = var.env }
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket                  = aws_s3_bucket.assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

### versioning

`versioning` 讓物件的每次覆寫都保留前一版。誤覆寫時可以從版本歷史回退到前一個正確版本，誤刪時物件只是被標記為 delete marker、前一版仍然存在。這道防線對承載正式資料的 bucket 是必要的 — 沒有 versioning 的 bucket，一次誤操作就是資料永久遺失。

versioning 開啟後會累積歷史版本的儲存量。搭配生命週期規則設定 `noncurrent_version_expiration` 可以控制保留多少天的舊版本，避免儲存成本無限成長。這個天數是「保留能力」跟「儲存成本」的取捨 — 保留 30 天通常足以涵蓋發現問題到回退的時間差，受合規要求的資料則依規定延長。

### server-side encryption

`server_side_encryption` 確保物件在 S3 落地時加密。`aws:kms` 使用 KMS 管理的金鑰，加密操作對應用程式透明 — 寫入時自動加密、讀取時自動解密，不需要改應用程式碼。選 `aws:kms` 而非 `AES256`（SSE-S3）的判斷依據是存取控制粒度：KMS 金鑰可以獨立設定 key policy，讓「誰能解密」這件事跟「誰能讀 bucket」分開管理，適合跨帳號或跨團隊的場景。

使用 KMS 加密的 bucket 在跨帳號存取時，目標帳號除了要有 bucket 的讀取權限，還需要 KMS key 的 `kms:Decrypt` 權限 — 少了這一步會拿到 `AccessDenied`，錯誤訊息通常指向 S3 權限而非 KMS，排查時容易走錯方向。

### public access block

`public_access_block` 的四個布林全設 true，等於從 bucket 層級封死對外公開的可能。即使有人之後誤加了一條公開的 bucket policy 或 ACL，這個 block 也會擋住。它是一道兜底機制 — 擋的是設定錯誤，不是正常操作。

靜態掃描工具（checkov / tfsec）會標記缺少 public access block 的 bucket。這正是[模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)裡自動化護欄的典型攔截對象 — 漏設的 bucket 會在 PR 階段被擋下，而非部署到線上才發現。

定期用 CLI 掃一遍帳號內所有 bucket 的公開狀態，命中的每個 bucket 都要能回答「這個公開是故意的、理由是什麼」：

```bash
aws s3api list-buckets --query 'Buckets[].Name' --output text | tr '\t' '\n' | \
  while read b; do
    status=$(aws s3api get-public-access-block --bucket "$b" 2>/dev/null | \
      jq -r '.PublicAccessBlockConfiguration | to_entries[] | select(.value==false) | .key')
    [ -n "$status" ] && echo "$b: $status"
  done
```

## 生命週期規則

儲存成本隨物件數量與保留時間線性成長。生命週期規則讓 IaC 描述「某類物件多久後搬到更便宜的儲存層、再多久後刪掉」，把成本控制變成可版本控制的設定。

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    id     = "archive-old-logs"
    status = "Enabled"
    filter { prefix = "logs/" }

    transition {
      days          = 30
      storage_class = "GLACIER_IR"
    }
    expiration { days = 365 }
  }

  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"
    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
```

### 儲存層的取捨

S3 提供多個儲存層，各自在存取延遲與儲存單價之間取捨：

| 儲存層               | 存取延遲     | 適用場景                 |
| -------------------- | ------------ | ------------------------ |
| Standard             | 毫秒級       | 頻繁讀取的熱資料         |
| Standard-IA          | 毫秒級       | 不常存取但需要時立即讀到 |
| Glacier Instant      | 毫秒級       | 每季存取一次的歸檔       |
| Glacier Flexible     | 分鐘到小時級 | 稽核留存、年度查閱       |
| Glacier Deep Archive | 12 小時級    | 法規留存、極少存取       |

`transition` 規則的日數設定要回推自業務需求：log 在除錯期間需要即時讀取（Standard），超過 30 天後幾乎只在事故回顧時才翻（Glacier Instant Retrieval 或 Standard-IA），超過一年可以淘汰或移到更深的歸檔層。把這些規則寫進 IaC，「為什麼 logs 只留一年」就是一個能在 PR 上被討論的決定，而非某人在 Console 點了不知道大家知不知道的設定。

## bucket policy 與跨帳號存取

bucket policy 描述誰能對這個 bucket 做什麼操作，是 bucket 層級的存取控制。它跟 IAM policy 的差別在施力點：IAM policy 貼在身分上、定義「這個身分能做什麼」；bucket policy 貼在資源上、定義「這個 bucket 允許誰來」。兩者同時生效 — 一個請求要同時被身分端和資源端允許才會放行（除非有顯式 deny）。

跨帳號存取是 bucket policy 最常見的使用場景。一個帳號的 S3 bucket 要讓另一個帳號的 IAM role 讀取，需要兩端同時授權：bucket policy 允許那個 role 的 ARN，對方帳號的 IAM policy 也允許對這個 bucket 操作。

```hcl
resource "aws_s3_bucket_policy" "cross_account_read" {
  bucket = aws_s3_bucket.assets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowCrossAccountRead"
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::111222333444:role/data-reader" }
      Action    = ["s3:GetObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.assets.arn,
        "${aws_s3_bucket.assets.arn}/*"
      ]
    }]
  })
}
```

bucket policy 的常見陷阱是 `Principal: "*"` — 允許任何人存取。這跟 security group 的 `0.0.0.0/0` 是同一類風險。除了做為 CloudFront Origin Access Control（OAC）的配合設定，幾乎沒有合理場景需要把 Principal 設成 wildcard。checkov 的 `CKV_AWS_70` 規則專門攔這個。

把 bucket policy 寫進 IaC 的好處是每一條授權都有 PR 紀錄 — 誰在什麼時候加了一條跨帳號存取、為什麼加、reviewer 同意了沒有。散落在 Console 的 bucket policy 沒有這些追蹤，某天發現一條不認得的授權時，只能去翻 CloudTrail 猜它是什麼時候加的。

## 事件通知

S3 事件通知讓 bucket 在物件被建立、刪除或還原時，自動觸發下游處理 — 寫入後自動縮圖、上傳後自動掃毒、刪除後自動通知。這些觸發關係寫進 IaC，讓「這個 bucket 會觸發什麼」成為可查詢的事實，而非散落在 Console 的隱性接線。

```hcl
resource "aws_s3_bucket_notification" "assets" {
  bucket = aws_s3_bucket.assets.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.thumbnail.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".jpg"
  }
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.thumbnail.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.assets.arn
}
```

事件通知的兩個配置常被忽略。第一是權限：S3 要觸發 Lambda，Lambda 的 resource-based policy 必須允許 S3 呼叫它（上面的 `aws_lambda_permission`），少了這段 apply 會成功但事件不會觸發，除錯時不容易發現。第二是 filter：不設 prefix / suffix 的通知會對 bucket 裡每一個物件操作都觸發，包括生命週期搬遷產生的物件變動 — 流量遠超預期。用 filter 把觸發範圍收斂到需要處理的路徑與檔案類型。

事件通知也可以導向 SQS 或 SNS，適合需要非同步佇列處理或 fan-out 到多個消費者的場景。選擇依據是下游的消費模式：Lambda 適合輕量即時處理（毫秒級回應），SQS 適合需要 backpressure 和重試的批次處理，SNS 適合同一事件需要同時通知多個服務。

## 跨分類引用

- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：checkov / tfsec 攔截缺少 public access block 或加密的 bucket
- → [模組八：治理好習慣](/infra/08-governance-habits/)：bucket 的 tagging 與成本歸因
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：bucket policy 與 IAM policy 的權限模型交集
