---
title: "IaC 工具選型與 state 地基"
date: 2026-06-26
description: "Terraform / OpenTofu / CDK / Pulumi 的選型判準，state 作為 IaC 工具對現實的唯一記憶，以及 remote state backend 的自管與託管路線"
weight: 1
tags: ["infra", "iac", "terraform", "state"]
---

## 動手前的前提

以下步驟是寫第一行 IaC 之前需要就位的前置條件。如果已經備妥可以跳過。如果是第一次接觸雲端帳號，先讀[拿到雲端帳號的第一天](/infra/00-infra-mindset/first-day-with-cloud-account/)做安全底線和帳號現況判讀。

**雲端帳號**。需要一個 AWS 帳號（或 GCP / Azure，本模組以 AWS 為主要範例）。註冊完成後立刻對 root 帳號啟用 MFA（Multi-Factor Authentication）——root 帳號是整個雲端環境的最高權限，沒有 MFA 等於大門沒鎖。啟用路徑：AWS Console → 右上角帳號名稱 → Security credentials → Multi-factor authentication (MFA) → Assign MFA device。日常操作用 IAM user 或 IAM Identity Center 登入，root 帳號只在需要 root-only 操作時使用。

**本機工具**。安裝 IaC CLI（Terraform 或 OpenTofu）和雲端 CLI（AWS CLI）：

```bash
# macOS
brew install opentofu awscli

# Arch Linux（opentofu 和 aws-cli-v2 在 AUR，需要 AUR helper）
yay -S opentofu-bin aws-cli-v2

# 驗證安裝
tofu --version
aws --version
```

**雲端認證**。本機需要能對雲端 API 認證。最直接的方式是用 AWS CLI 設定 credentials：

```bash
aws configure
# 輸入 Access Key ID、Secret Access Key、預設 region（如 ap-northeast-1）
```

這組 access key 來自 IAM user。如果帳號裡還沒有 IAM user，到 AWS Console → IAM → Users 建立一個、附加 `AdministratorAccess` policy、在 Security credentials 分頁建立 access key。正式環境應該用 SSO 或 short-lived credentials 取代長期 key（[模組二](/infra/02-identity-credentials/)會展開），但起步階段一組 IAM user key 足以讓 `tofu apply` 跑起來。

**Git repo**。IaC 程式碼從 day 1 就應該在版本控制裡——這是[模組零](/infra/00-infra-mindset/)「可重建路徑」的落地前提。建一個 Git repo，後續所有 `.tf` 檔都放在這裡：

```bash
mkdir infra && cd infra
git init
echo '.terraform/' > .gitignore
echo '*.tfstate'  >> .gitignore
echo '*.tfstate.*' >> .gitignore
git add .gitignore && git commit -m "init: gitignore for terraform"
```

`.gitignore` 排除 `.terraform/`（provider 快取）和 `*.tfstate`（state 檔含敏感值，存放策略見下方 remote state 段落）。

---

踏上[成熟度階梯](/infra/00-infra-mindset/)（從全手動到全程式碼治理的五階分級）第二階（宣告式 IaC，也就是 state 檔誕生那一階）的最小路徑，從兩件事開始：選對工具、把 state 管好。工具決定用什麼語言描述基礎設施，state 則是工具對雲端現實的唯一記憶。這份記憶存在哪、怎麼保護、怎麼防止並行寫壞，是整套 IaC 能不能站穩的地基。

## IaC 工具選型：宣告式狀態管理 vs 程式語言抽象

IaC 工具的核心職責是把「我要的基礎設施長什麼樣」描述成可版本控制的程式碼，再由工具負責算出現況與目標的差異並收斂。市場上的工具分成兩條路線，差別落在「用什麼語言描述」與「狀態由誰持有」這兩個軸上，而非功能多寡。

### 宣告式 DSL 路線

第一條路線的代表是 Terraform 與其開源分支 OpenTofu。寫的是 HCL（HashiCorp Configuration Language），描述的是資源的最終樣貌，工具自己維護一份 state 來追蹤每個資源的真實 ID 與屬性。

```hcl
resource "aws_s3_bucket" "artifacts" {
  bucket = "acme-deploy-artifacts"
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

這段 HCL 描述的是「一個開了 versioning 的 S3 bucket 應該存在」。第一次 apply 時工具建立它，之後每次 apply 時工具比對 state 與雲端現況，只做差異收斂。讀的人看 HCL 就知道最終結果長什麼樣，不需要在腦中追蹤執行順序。

這條路線適合團隊成員背景混雜、需要讓非專職後端的人也能讀懂 infra 定義的情境 — HCL 的閱讀門檻低，diff 直觀，review 時看得出「這個 PR 會新增一個 RDS、改掉一條 security group」。缺點是 HCL 的表達力有限：遇到需要大量條件分支或動態生成的場景時，語法會變得笨拙，`count`、`for_each`、`dynamic` 區塊很快就堆出難以閱讀的嵌套。

### 程式語言路線

第二條路線的代表是 AWS CDK 與 Pulumi。寫的是 TypeScript、Python、Go 這類語言，靠迴圈、函式、類別來生成資源。這條路線適合 infra 邏輯本身複雜、需要大量條件分支與抽象複用的團隊，例如要根據環境清單動態生成數十組對稱資源。

代價是 review 難度上升。一段 `for` 迴圈展開後到底建了哪些東西，得在腦中執行程式才看得出來，diff 不再等於變更本身。一個抽象類別改了一行建構子參數，展開後可能影響所有繼承它的資源，而 PR diff 上只看到那一行。對跨職能 review（PM、SRE、安全團隊都要看的變更）來說，這是可感知的閱讀成本。

### CDK vs Pulumi：狀態由誰持有

CDK 與 Pulumi 同屬程式語言路線，但「狀態由誰持有」這個軸把它們再分開。

CDK 把程式碼 synth 成 CloudFormation 模板，再交給 CloudFormation 服務端執行與追蹤。state 由 AWS 代管 — 沒有一份 tfstate 檔要自己存放、加密、回捲，也不需要額外的鎖表來防並行。這份「狀態維運外包給雲端」正是 CDK 在 AWS 生態內的賣點之一。代價是綁定 CloudFormation 與單一雲 — CloudFormation 的更新速度、resource coverage、錯誤訊息品質都由 AWS 控制，團隊的 debug 能力受限於 CloudFormation 的回報粒度。

Pulumi 走另一邊：它維護一份自己的 state，預設交給 Pulumi Cloud 託管，也能改用 S3 之類的後端自管。形態上更接近 Terraform 的 state 模型，state 的存放、保護與並行控制重回團隊手上。同一條程式語言路線，選 CDK 等於把 state 責任讓給雲端，選 Pulumi 則保留對 state 落點的掌控。

### 選型判準

選型看的是團隊組成與變更的審查需求，可以用一張決策表歸納：

| 判準          | 宣告式 DSL（Terraform / OpenTofu） | 程式語言（CDK / Pulumi）      |
| ------------- | ---------------------------------- | ----------------------------- |
| diff 可讀性   | HCL diff 即是資源變更              | 程式碼 diff，要展開才知道結果 |
| 跨職能 review | 適合                               | 需要讀者熟悉程式語言          |
| 抽象複用      | 有限，靠 module + for_each         | 完整程式語言能力              |
| state 管理    | 自管或託管皆可                     | CDK 交 AWS；Pulumi 自管或託管 |
| 跨雲          | provider 生態支援多雲              | CDK 限 AWS；Pulumi 支援多雲   |
| 學習曲線      | HCL 語法簡單，概念模型需適應       | 語言本身熟悉，IaC 概念需適應  |

若多數變更要跨職能 review、希望 diff 一眼可讀，宣告式 DSL 較划算；若 infra 由專職平台團隊維護、抽象複用的收益大於審查透明度的損失，程式語言路線較划算。

Terraform 與 OpenTofu 之間，OpenTofu 是授權變更後社群分叉出的相容實作，HCL 與 provider 生態幾乎共用；選擇主要看對授權條款與治理模式的偏好，技術判準在這一階沒有實質差異。本模組後續一律以 HCL 示意，換成任一宣告式工具判準仍成立。

上述兩條路線之外，還有兩類工具走不同的運作模型。Kubernetes-native 路線（代表是 Crossplane）用 CRD 描述雲資源、由 controller 持續收斂，state 由 Kubernetes 的 etcd 持有，適合已經重度投入 Kubernetes 的團隊。Serverless-first 框架（代表是 SST）把部署與 IaC 合一，適合全 serverless 架構。這兩條路線的 state 模型與 CLI 驅動的 plan/apply 流程不同，本系列不展開。

## state 是工具對現實的唯一記憶

state 是 IaC 工具用來記錄「上一次 apply 之後，每個資源在雲端真實長什麼樣」的快照。它的作用是讓工具能算出「現況」與「目標」之間的最小差異。沒有 state，工具每次都得把所有資源重新查一遍才知道該不該動，而且無法分辨「這個資源是我建的、該由我管」還是「別人手動建的、不歸我管」。

一份 state 的實際內容大致長這樣（簡化版）：

```json
{
  "resources": [
    {
      "type": "aws_s3_bucket",
      "name": "artifacts",
      "instances": [
        {
          "attributes": {
            "id": "acme-deploy-artifacts",
            "arn": "arn:aws:s3:::acme-deploy-artifacts",
            "bucket": "acme-deploy-artifacts",
            "tags": { "env": "prod", "owner": "platform" }
          }
        }
      ]
    }
  ]
}
```

state 裡通常含有資源的真實 ID、相依關係，以及部分敏感屬性 — 例如資料庫的初始密碼、private key 的輸出值、加密金鑰的 ARN。這帶來兩條硬邊界，違反任一條都會在未來製造代價高昂的事故。

### state 絕不能進 git

state 含明文敏感值，一旦推進版控就等於把密碼寫進每個 clone 的歷史裡。事後 rotate 密碼也清不掉 git 歷史 — 因為 git 是 append-only 的，舊版本的 state 永遠留在 commit 裡，除非用 `git filter-branch` 或 `git filter-repo` 重寫整條歷史（這本身是一個破壞性操作，會影響所有已經 clone 的副本）。

在 `.gitignore` 裡搜尋 `*.tfstate` 和 `*.tfstate.backup`——如果這兩行不在，state 有進版控的風險。在 repo 根目錄執行一次搜索確認：

```bash
git log --all --diff-filter=A -- '*.tfstate'
```

如果有任何結果，代表 state 曾經被 commit 過，那些 commit 裡的敏感值已經暴露。

### state 不能只放本地

本地 state 的失敗模式是它把整份基礎設施的記憶綁在一台筆電上 — 換人接手、換台機器、或多人同時 apply 時，記憶就分裂了。

具體場景：工程師 A 在自己的筆電 apply 了一次，state 記住「已經建了 3 個 security group」。工程師 B 在另一台筆電上拉了同一份 code，但她的本地沒有 state（或有一份過時的 state），apply 時工具以為那 3 個 security group 不存在，又建了 3 個重複的。更糟的場景是 B 的 state 比 A 舊，工具對比後認為 A 後來新增的 security group「不在記憶裡、是多餘的」，於是 apply 時把它們刪掉 — 而 A 還以為那些規則還在保護服務。

這兩條邊界共同指向同一個結論：state 需要一個團隊共享、有版本、有存取控制、且能防止同時寫入的存放處。這就是 remote state backend 要解的問題。

## remote state backend：自管 vs 託管

remote state backend 是把 state 從本地移到團隊共享儲存的機制，它要同時滿足三件事：持久保存、防止並行寫入衝突、以及保護敏感內容。達成方式分成自管儲存與託管服務兩種，差別在維運責任落在誰身上。

### 自管 backend

自管路線以雲端物件儲存加鎖機制為典型組合。以 AWS 為例，state 檔放 S3、用一張 DynamoDB 鎖表防止兩個人同時 apply：

```hcl
terraform {
  backend "s3" {
    bucket         = "acme-tf-state"
    key            = "prod/network/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "acme-tf-lock"
  }
}
```

這段設定的每一項都對應前一節的一條邊界：

**`encrypt = true`** 讓 state 在 S3 落地時加密，回應「state 含敏感值」的風險。加密用的是 S3 的 server-side encryption，搭配 KMS key 可以進一步控制誰能解密。

**bucket versioning** 是這段設定裡沒有出現、但在建立 bucket 時就該開的屬性。apply 寫壞或誤刪 state 時，versioning 是把記憶回捲到上一個正確版本的唯一退路。沒開的話一次壞寫就讓工具失去對現實的記憶，而回復的唯一方式是從雲端逐個資源重新 import。建立 state bucket 的 HCL 應該同時開 versioning 與刪除保護：

```hcl
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.tf_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.tf_state.id

  rule {
    id     = "retain-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
```

舊版本的保留天數是成本與安全的取捨。90 天足以涵蓋大多數「發現 state 壞了再回去找正確版本」的時間差 — 超過 90 天才發現的 state 問題通常已經被後續 apply 覆蓋，回捲到更早的版本反而引入更大的落差。

**`dynamodb_table`** 指向一張鎖表。apply 開始時寫入一筆鎖、結束才釋放，第二個人同時跑就會被擋下並提示鎖被誰持有。這正是本地 state 無法提供、卻是多人協作底線的並行保護。鎖表本身的建立只需要幾行 HCL：

```hcl
resource "aws_dynamodb_table" "tf_lock" {
  name         = "acme-tf-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}
```

鎖表用 PAY_PER_REQUEST 模式足夠，因為它的讀寫頻率很低（只在 apply 開始和結束時各一次）。鎖卡住時（apply 中途失敗、沒有正常釋放鎖），用 `terraform force-unlock <lock-id>` 手動釋放，但前提是確認沒有其他 apply 正在執行。

**`key`** 是 state 在 bucket 內的路徑，這裡先用 `prod/network` 之類的分層命名。實際怎麼依環境切分 state 留待[模組四：環境分離與模組化](/infra/04-environment-separation/)展開。

### 自管 backend 的雞生蛋問題

自管 backend 有一個啟動悖論：state bucket 和 lock table 本身也是雲端資源，它們該由誰來管理？用 Terraform 管理 Terraform 的 backend？

務實的做法是接受這個循環：用一份獨立的、最小化的 Terraform code 來建立 state bucket 和 lock table，這份 code 用 local state（因為它只在啟動那一次跑）。建立完成後，所有後續的 Terraform code 都指向這個 remote backend。這份啟動 code 的 local state 可以 commit 進 repo（它不含敏感值，只有 bucket 和 DynamoDB table 的 ID），或直接在跑完後丟棄 — 因為這些資源如果需要重建，幾行 CLI 就能做到。

```hcl
# bootstrap/main.tf — 只用一次，建立 state 基礎設施
terraform {
  # 刻意用 local state，因為 remote backend 還不存在
}

resource "aws_s3_bucket" "tf_state" {
  bucket = "acme-tf-state"
}

# ... versioning, encryption, lock table
```

### 託管 backend

託管路線把上述維運細節包起來，由 Terraform Cloud、Spacelift、env0 這類平台代管 state、鎖與加密，附帶 web UI 與 audit log。

判讀訊號是團隊規模與維運餘裕。自管 backend 的成本是要自己把 bucket versioning、加密、鎖表、IAM 權限配對，配錯任何一項都可能讓 state 失去保護 — 例如忘了開 versioning，一次壞寫就回不去。託管服務用月費換掉這份配置與維運負擔，代價是 state 託付給第三方、且進階治理功能常綁在付費級距。

小團隊起步、不想第一週就花在配 backend 上，託管較划算。對 state 存放位置有合規或主權要求、或希望基礎設施盡量自持的團隊，自管較划算。託管服務（Terraform Cloud / Spacelift）的免費方案涵蓋基本功能，付費級距約 $20-70/user/月；自管 backend 的成本是初次配置半天到一天的工程師時間，加上持續的 IAM 權限與 versioning 維護。

導入時程參考：最小可行 IaC（state backend + 第一批地基資源）的導入約需 2-3 天工程師時間。第一個可見里程碑是「一條指令能在新帳號重建整個地基環境」。之後每批服務的納管約 1-2 天/批，依資源複雜度而定。

State 地基設好後，下一步是立 Console 唯讀鐵律、並用最小可行資源集合驗證整條鏈路，見[Console 唯讀鐵律與最小可行資源集合](/infra/01-minimal-iac/console-readonly-minimal-viable/)。

## 跨分類引用

- → [Console 唯讀鐵律與最小可行資源集合](/infra/01-minimal-iac/console-readonly-minimal-viable/)：state 管好之後，Console 唯讀紀律與最小 apply 閉環
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：Console 唯讀鐵律靠權限落地
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：state 的 key 怎麼依環境切分
