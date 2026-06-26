---
title: "單環境到多環境的 Retrofit 操作手冊"
date: 2026-06-26
description: "把已經跑在單一環境的 Terraform 設定拆成 module + per-env 目錄結構的完整操作步驟，含 moved block、zero-change plan 驗證與常見陷阱"
weight: 2
tags: ["infra", "environment", "retrofit", "module"]
---

單環境的 Terraform 設定在資源數量少、只有一個人操作時運作順暢。當需要第二個環境（dev 或 staging）、或第二個人開始改 infra 時，單環境的限制會開始浮現：沒有地方安全地測試變更、apply 一次就是對 production 動手。Retrofit 的目標是把這份單環境設定拆成「module + per-env 目錄」的結構，讓 dev 與 prod 各持獨立 state、共用同一套邏輯，而且在整個過程中 production 的資源不受任何影響。

## Retrofit 前的準備

Retrofit 操作的是正在服務的 production 資源，每一步都要確認「plan 顯示零變更」才能往下走。準備工作的目的是降低操作過程中的風險。

### State 備份

開始之前把 state 拉一份完整備份到本地：

```bash
terraform state pull > state-backup-$(date +%Y%m%d).json
```

這份備份是最後的回退手段。如果 retrofit 過程中 state 被弄壞（例如 moved block 指向錯誤的位置），可以用 `terraform state push state-backup.json` 回到起點重來。state push 會覆蓋遠端 state，屬於危險操作——只在回退時使用。

### 識別 stateful 資源

列出所有 state 裡的資源，標記哪些是 stateful（RDS、S3 含資料、EBS volume）：

```bash
terraform state list | sort
```

Stateful 資源在 retrofit 過程中的風險最高：如果 moved block 寫錯導致 Terraform 判定需要 replace（先刪後建），stateful 資源的 replace 代表資料遺失。後面每一步的 plan 輸出都要特別檢查 stateful 資源有沒有出現 `must be replaced` 或 `forces replacement`。

### 確認 plan baseline

在還沒改任何 code 之前先跑一次 plan，確認起點是乾淨的：

```bash
terraform plan -detailed-exitcode
```

Exit code 0 代表 state 與現實一致、沒有 drift。如果此時就有 drift（exit code 2），先解決 drift 再做 retrofit——在已經有 drift 的基礎上做結構重構，plan 的差異訊號會被 drift 淹沒，無法區分「drift 造成的差異」和「retrofit 造成的差異」。

## 步驟一：把資源宣告抽成 module

第一步純粹是程式碼重組——把 `main.tf` 裡的資源宣告搬進 `modules/` 目錄，原地改成 module 呼叫。這一步不改任何資源屬性、不改 backend、不改 provider，所有值先寫死成當前的值。

### 目標目錄結構

```text
infra/
├── modules/
│   ├── network/
│   │   ├── main.tf        # VPC、subnet、SG 從根目錄搬過來
│   │   ├── variables.tf   # 先把所有值寫死在 default 裡
│   │   └── outputs.tf     # 暴露 VPC ID、subnet IDs 等
│   └── database/
│       ├── main.tf        # RDS 從根目錄搬過來
│       ├── variables.tf
│       └── outputs.tf
├── main.tf                # 改成 module 呼叫
├── backend.tf             # 不動
└── terraform.tfvars       # 這一步還不存在
```

### 用 moved block 告訴 Terraform 搬家

資源從根目錄搬進 module 後，Terraform 的內部位址從 `aws_vpc.main` 變成 `module.network.aws_vpc.main`。如果不告訴 Terraform 這個對應關係，它會判定舊位址的資源「要刪」、新位址的資源「要建」——對 VPC 或 RDS 來說這代表服務中斷。

`moved` block 宣告式地描述搬遷：

```hcl
moved {
  from = aws_vpc.main
  to   = module.network.aws_vpc.main
}

moved {
  from = aws_subnet.public
  to   = module.network.aws_subnet.public
}

moved {
  from = aws_subnet.private
  to   = module.network.aws_subnet.private
}

moved {
  from = aws_db_instance.primary
  to   = module.database.aws_db_instance.primary
}
```

每個搬進 module 的資源都需要一條 moved block。遺漏任何一條，plan 就會顯示該資源要 destroy + create。

### Zero-change plan 驗證

```bash
terraform plan
```

這一步的 plan 輸出必須是：

```text
Plan: 0 to add, 0 to change, 0 to destroy.
```

如果 plan 顯示任何 add、change 或 destroy，先停下來檢查：

- `destroy + create`：moved block 遺漏或位址寫錯
- `change`：module 內的 resource 屬性跟搬進來之前不一致（漏了某個 attribute、default 值不同）
- `add`：新的 module output 或 data source 被 Terraform 當成新資源

修到 plan 顯示零變更才能 apply。apply 之後 state 裡的資源位址從 `aws_vpc.main` 更新成 `module.network.aws_vpc.main`，雲端資源本身不受影響。

安全暫停點：本步完成後 code 已重組、state 位址已更新、雲端資源未變，環境處於自洽狀態，可隔日繼續。

## 步驟二：把寫死的值換成參數

Module 內部的寫死值搬到 `variables.tf`，module 呼叫端從 `terraform.tfvars` 讀入。這一步的 plan 仍然必須是零變更——因為參數的值就等於原本寫死的值。

```hcl
# modules/database/variables.tf
variable "instance_class" {
  type = string
}

variable "multi_az" {
  type    = bool
  default = false
}

variable "backup_retention_days" {
  type    = number
  default = 7
}
```

```hcl
# main.tf — module 呼叫端
module "database" {
  source                = "./modules/database"
  instance_class        = var.db_instance_class
  multi_az              = var.db_multi_az
  backup_retention_days = var.db_backup_retention_days
}
```

```hcl
# terraform.tfvars — prod 的值
db_instance_class        = "db.r6g.large"
db_multi_az              = true
db_backup_retention_days = 30
```

再跑一次 plan 確認零變更。值從寫死改成參數傳入，但傳入的值跟原來一樣，所以 Terraform 算出的差異是零。

安全暫停點：本步完成後 module 已參數化、prod 行為不變，可隔日繼續。

## 步驟三：建立新環境目錄

prod 確認穩定後，建 dev 環境的獨立目錄。這一步是純新增——不碰 prod 的任何檔案。

```text
infra/
├── modules/           # 共用（不動）
├── environments/
│   ├── prod/
│   │   ├── main.tf          # 原本根目錄的 module 呼叫搬過來
│   │   ├── backend.tf       # prod 的 state 位址
│   │   └── terraform.tfvars # prod 的值
│   └── dev/
│       ├── main.tf          # 複製 prod 的 module 呼叫
│       ├── backend.tf       # dev 的獨立 state 位址
│       └── terraform.tfvars # dev 的縮小值
```

dev 的 `terraform.tfvars` 用縮小的規格：

```hcl
# environments/dev/terraform.tfvars
db_instance_class        = "db.t3.micro"
db_multi_az              = false
db_backup_retention_days = 1
```

dev 的 `backend.tf` 指向獨立的 state 路徑——dev 和 prod 的 state 從一開始就是分開的，不存在「事後拆」的需求：

```hcl
terraform {
  backend "s3" {
    bucket         = "acme-tf-state"
    key            = "dev/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "acme-tf-lock"
  }
}
```

如果原本的 prod 是在根目錄操作（不是在 `environments/prod/` 目錄），這一步還需要把 prod 的操作也搬進 `environments/prod/`。這個搬遷本身又是一次 moved block + zero-change plan 驗證的循環。

安全暫停點：本步是純新增（建目錄和檔案），不影響 prod 的 state 或資源，可隔日繼續。

## 步驟四：先在 dev apply 驗證

```bash
cd environments/dev
terraform init
terraform plan
terraform apply
```

dev 是全新環境、全新 state，apply 會建出一整套資源。這一步驗證的是 module 在「從零建立」的情境下能否正常運作。如果 dev apply 成功且環境可用，代表 module 的邏輯正確。

dev 環境 apply 後跑一次 plan 確認零 drift：

```bash
terraform plan -detailed-exitcode
# 預期 exit code 0
```

安全暫停點：dev 環境已驗證、prod 未受影響，可隔日繼續最後的 prod 驗證。

## 步驟五：驗證 prod 未受影響

回到 prod 目錄，跑 plan 確認 prod 的資源沒有任何變化：

```bash
cd environments/prod
terraform plan -detailed-exitcode
# 預期 exit code 0
```

如果此時 prod plan 顯示差異，可能的原因：

- prod 的 module 呼叫路徑變了（`source = "./modules/..."` → `source = "../../modules/..."`）但 moved block 沒跟著更新
- `terraform.tfvars` 的某個值跟原本寫死的不一致
- provider 版本在 init 時升級了

修到零變更。這一步結束後 retrofit 完成——prod 和 dev 各持獨立 state、共用同一套 module、環境差異全部收斂在 tfvars 裡。

## 常見陷阱

### moved block vs terraform state mv

兩者都能告訴 Terraform 資源搬了家。`moved` block 是宣告式的——寫在 HCL 裡、可以 review、可以 revert（刪掉 moved block 就回去）。`terraform state mv` 是命令式的——直接改 state，沒有 review 機制、改完沒有 undo。

優先用 moved block。`state mv` 留給 moved block 表達不了的情境：跨 state 搬遷（把資源從一份 state 移到另一份）、或 Terraform 版本太舊不支援 moved block（0.13 以下）。

### forces replacement 觸發

某些 resource 的某些 attribute 是「改了就要重建」的（immutable attribute）。常見的觸發：

| Resource          | Attribute    | 改了會怎樣                              |
| ----------------- | ------------ | --------------------------------------- |
| `aws_db_instance` | `identifier` | forces replacement（資料遺失）          |
| `aws_db_instance` | `engine`     | forces replacement                      |
| `aws_instance`    | `ami`        | forces replacement                      |
| `aws_s3_bucket`   | `bucket`     | forces replacement（bucket 名稱不可改） |
| `aws_vpc`         | `cidr_block` | forces replacement                      |

Retrofit 過程中如果不小心改了這些 attribute（例如把 `identifier = "mydb"` 參數化時打錯了值），plan 會顯示 `must be replaced`。stateful 資源的 replacement 代表先刪後建——對 RDS 來說就是資料遺失。所以每一步 plan 都要特別檢查有沒有 `forces replacement` 的輸出。

### State locking 與並行操作

Retrofit 期間如果有其他人同時 apply（CI pipeline 被觸發、同事在操作），兩邊的 state 操作會衝突。DynamoDB lock table 會擋下並行的 apply，但 init 和 plan 不一定會被擋。

操作建議：retrofit 開始前在團隊頻道通知「infra 暫停操作」，retrofit 完成後再解除。如果用 Atlantis，可以暫時鎖定 apply 權限。時程參考：10-20 個資源的環境，步驟一到五約需半天到一天。

## 跨分類引用

- → [環境分離與模組化](/infra/04-environment-separation/directory-module-parameterization/)：retrofit 的目標結構與設計原則
- → [IaC 工具選型與 state 地基](/infra/01-minimal-iac/iac-tool-state-backend/)：state backend 的設定與 lock 機制
- → [模組五：Stateful 資源保護](/infra/05-core-services/stateful-protection-dependency/)：stateful 資源的 replacement 風險
- → [infra 走 PR 流程](/infra/07-infra-as-pr/plan-review-apply-guardrails/)：retrofit 的每一步走 PR 讓 plan 可被 review
