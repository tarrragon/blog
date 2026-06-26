---
title: "State 修復與清理"
date: 2026-06-26
description: "接手的 Terraform state 損壞、有 orphaned entry、或需要搬遷時，怎麼診斷問題、安全操作、以及從錯誤中回復"
weight: 20
tags: ["infra", "takeover", "terraform", "state"]
---

接手一個有半套 IaC 的環境時，state 是工具對現實的唯一記憶，但這份記憶可能已經失真——有些記錄對應的雲端資源已經不存在、有些雲端資源從來沒被記錄、有些記錄的屬性跟現實對不上。在動任何資源之前，先把 state 修到一個可信的狀態，是所有後續操作的前提。

## 診斷 state 的健康狀態

`terraform plan` 的輸出是診斷 state 健康度的主要工具。在不做任何 code 變更的前提下跑 plan，輸出的每一行差異都代表 state 與現實的落差：

```bash
terraform plan -detailed-exitcode -no-color > plan-diagnosis.txt 2>&1
# exit code: 0=無差異, 1=錯誤, 2=有差異
```

Plan 的差異分三類，每一類的處理方式不同：

| Plan 顯示           | 意義                                  | 處理方式                              |
| ------------------- | ------------------------------------- | ------------------------------------- |
| `~ update in-place` | state 記錄的屬性跟雲端不同（drift）   | 判斷要保留手動改的值還是回退到 code   |
| `+ create`          | code 裡有但 state 裡沒有（漏 import） | 確認資源是否已存在於雲端，是則 import |
| `- destroy`         | state 裡有但 code 裡沒有（orphan）    | 確認資源是否還在雲端、是否還在用      |

Plan 跑到一半報錯（exit code 1）而非產出差異，通常代表更嚴重的問題：provider 版本不相容、state 格式損壞、或 state 引用的資源 ID 在雲端已經不存在。錯誤訊息裡的 resource address 指向問題所在。

### Orphaned entry 的辨認

State 裡有一筆資源記錄，但雲端已經沒有對應的資源（手動刪除、帳號切換、或 region 不對），plan 會顯示 `- destroy` 或直接報 `Error: reading ... NotFound`。這種 orphaned entry 需要從 state 移除，否則每次 plan 都會嘗試操作一個不存在的目標。

```bash
# 列出 state 裡所有資源，逐一確認是否還存在
terraform state list | while read addr; do
  echo "Checking: $addr"
  terraform state show "$addr" > /dev/null 2>&1 || echo "  POSSIBLY ORPHANED: $addr"
done
```

這個腳本不連雲端驗證（只檢查 state 內部一致性），真正的驗證要靠 plan 輸出。如果 plan 對某個資源報 NotFound，那就是 orphaned。

## State 操作前的備份

所有 state 操作（rm、mv、push、import）都是直接改寫 state 檔的破壞性操作。操作前的備份是唯一的回退路徑。

```bash
# 從遠端 backend 拉一份完整的 state 到本地
terraform state pull > state-backup-$(date +%Y%m%d-%H%M).json

# 確認備份可用：檢查 JSON 格式和 resource 數量
jq '.resources | length' state-backup-*.json
```

如果 state 存在 S3 且 bucket 有開 versioning（應該有，見[模組一](/infra/01-minimal-iac/)），S3 的版本歷史是第二道保險。但 `state pull` 的本地備份更可控——S3 versioning 的回復要操作 bucket、權限要對、而且版本 ID 需要另外查。

## 移除 orphaned entry：state rm

`terraform state rm` 把一筆資源從 state 裡移除，但不觸碰雲端的實際資源。用途是清理 state 裡對應不到雲端的記錄，讓 plan 不再嘗試操作不存在的目標。

```bash
# 移除單一 orphaned resource
terraform state rm 'aws_instance.old_bastion'

# 移除整個 module 的記錄（module 被拆掉但資源還在雲端、要重新 import）
terraform state rm 'module.legacy_network'
```

移除後立刻跑 plan 驗證：原本針對這個資源的 destroy / error 應該消失。如果移除後 plan 反而出現 `+ create`（想重建這個資源），代表 code 裡還有對應的 resource block——要麼也刪 code，要麼這個資源需要 import 而不是 rm。

判斷「該 rm 還是該 import」的依據：資源在雲端還存在嗎？存在就 import（讓 state 重新追蹤它），不存在就 rm（清掉過時的記錄）。

## 搬移資源：state mv 與 moved block

重構 Terraform code（把資源搬進 module、改 resource name、改 module 結構）時，state 裡的 resource address 會跟著變。如果不處理，plan 會判定「舊 address 要 destroy、新 address 要 create」——對 stateless 資源只是多等一次重建，對 RDS 這類 stateful 資源是資料遺失。

Terraform 1.1+ 的 `moved` block 是宣告式的搬遷，寫在 HCL 裡、可 review、可回滾：

```hcl
moved {
  from = aws_security_group.web
  to   = module.network.aws_security_group.web
}
```

跑 plan 時 Terraform 會把 state 裡的舊 address 自動對應到新 address，plan 顯示 `(moved)` 而非 `destroy + create`。驗證 plan 為零變更後 apply，moved block 生效後可以從 code 裡刪掉。

`terraform state mv` 是指令式的搬遷，直接操作 state 檔。它比 moved block 靈活（可以跨 state 搬）、但不可 review、不進版本控制、操作錯了只能靠備份回退。

| 操作          | moved block          | state mv                                |
| ------------- | -------------------- | --------------------------------------- |
| 可 review     | 是（寫在 HCL）       | 否（直接改 state）                      |
| 可回滾        | 是（刪 moved block） | 否（靠備份）                            |
| 跨 state 搬遷 | 不支援               | 支援                                    |
| 適用情境      | 同 state 內的重構    | 跨 state 搬遷、moved 表達不了的複雜搬移 |

優先用 moved block，state mv 留給 moved 做不到的場景。

## 手動編輯 state：pull → 改 → push

極少數情況需要直接編輯 state JSON——例如修正一個 resource 的 ID（某次 import 用了錯的 ID）、或手動修改一個 attribute 讓 plan 不再觸發不必要的變更。

```bash
# 拉到本地
terraform state pull > state-edit.json

# 編輯（用 jq 或文字編輯器，改目標 resource 的 attributes）
# 極度小心：改錯任何欄位都可能讓 plan 產生破壞性差異

# 推回遠端
terraform state push state-edit.json
```

`state push` 有 lineage 和 serial 檢查——如果本地的 state 跟遠端的 lineage 不同（來自不同的 init），push 會被拒絕。加 `-force` 可以繞過，但這意味著覆蓋遠端、丟棄遠端從你 pull 之後的所有變更。

手動編輯 state 的操作規則：備份 → 改一個欄位 → push → plan 驗證 → 確認只有預期的變化。批次改多個欄位時，每改一個就走一輪 push + plan，不要累積修改。

## 從錯誤的 state push 回復

如果 `state push` 推了一個錯誤的 state，回復路徑取決於 backend 有沒有版本歷史。

### S3 backend 有 versioning

```bash
# 列出 state 檔的所有版本
aws s3api list-object-versions \
  --bucket acme-tf-state \
  --prefix prod/network/terraform.tfstate \
  --query 'Versions[].{VersionId:VersionId,LastModified:LastModified,Size:Size}' \
  --output table

# 下載上一個正確的版本
aws s3api get-object \
  --bucket acme-tf-state \
  --key prod/network/terraform.tfstate \
  --version-id "correct-version-id" \
  state-recovered.json

# 用 terraform state push 推回
terraform state push state-recovered.json
```

### 沒有 versioning

如果 bucket 沒開 versioning、又沒有本地備份，state 的上一個版本就沒了。這時候的選項：

1. 從 plan 的輸出反推哪些 resource 的 state 記錄是錯的，逐一用 `state rm` + `import` 修正
2. 作為最後手段，刪掉整份 state、從零 import 所有資源——這等於重做一次完整的 IaC 導入

這正是[模組一](/infra/01-minimal-iac/)要求 state bucket 開 versioning 的理由——沒有版本歷史的 state backend，一次 push 錯誤就沒有回退路徑。

## State backend 搬遷

接手的環境可能用本地 state（`.terraform/terraform.tfstate`）或者 state 放在不符合安全要求的位置（沒加密的 S3、沒有鎖表、甚至存在某個人的桌機上）。搬遷到正規的遠端 backend 是接手後的優先工作。

### 本地 → S3 + DynamoDB

```hcl
# 在 backend.tf 加上遠端 backend 設定
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

```bash
# 重新初始化，Terraform 會偵測到 backend 變更並提示搬遷
terraform init -migrate-state

# 確認搬遷成功
terraform plan  # 應該顯示零變更
```

`-migrate-state` 會把本地 state 的內容寫入新的遠端 backend。搬遷後本地的 `.terraform/terraform.tfstate` 變成一個指向遠端 backend 的指標，不再存放實際 state 內容。

### 舊 S3 → 新 S3

跟本地搬遷流程相同——改 backend.tf 的 bucket/key/region，跑 `terraform init -migrate-state`。Terraform 會從舊 backend 讀 state、寫入新 backend。

搬遷後驗證：plan 為零變更、新 bucket 裡有 state 檔、舊 bucket 的 state 檔可以保留一段時間作為備份。搬遷過程中 DynamoDB 的 lock 會確保沒有人同時 apply。

搬遷期間的風險：如果有人在你改 backend.tf 之後、跑 init 之前，用舊 backend 跑了 apply，新 backend 的 state 會缺少那次變更。搬遷時通知團隊暫停所有 Terraform 操作，搬遷完成後再恢復。

時程參考：單一 orphaned entry 的 rm 操作約 15-30 分鐘（含備份和驗證）。Backend migration 約 1-2 小時。5-10 個問題項的完整 state 整理約半天到一天。

## 跨分類引用

- → [有半套 IaC 但文件缺失的環境接管](/infra/takeover/partial-iac-no-docs/)：本篇的上層操作流程
- → [Drift 分類處理](/infra/takeover/partial-iac-drift-triage/)：state 修復完成後，下一步是處理 managed resource 的 drift
- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：state backend 的設計與 versioning 要求
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：moved block 在環境拆分 retrofit 裡的角色
