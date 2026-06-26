---
title: "Drift 分類處理指南"
date: 2026-06-26
description: "接手半套 IaC 環境時，怎麼讀 plan 輸出分類 drift、判斷保留還是回退、處理 stateful 資源的高風險漂移，以及批次收斂的工作流"
weight: 11
tags: ["infra", "takeover", "terraform", "drift"]
---

接手一個半套 IaC 的環境後，跑 `terraform plan` 通常會看到一批非零差異。這些差異就是 drift——state 記錄的狀態跟雲端實際狀態之間的落差。每一條 drift 都需要判斷：這是該保留的手動改動，還是該回退的意外漂移？判斷錯誤的代價從「設定被覆蓋」到「stateful 資源被重建導致資料遺失」不等，所以分類要在 apply 之前完成。

## 讀 plan 輸出：三種變更類型

`terraform plan` 的輸出用符號標示每個資源的預期變更。三種類型的風險等級不同，處理方式也不同：

```text
# in-place update（~）：修改屬性，資源本身不動
~ resource "aws_security_group_rule" "api_ingress" {
    ~ cidr_blocks = ["10.0.0.0/16"] -> ["10.0.1.0/24"]
  }

# forces replacement（-/+）：刪除後重建，新資源取得新 ID
-/+ resource "aws_db_instance" "primary" {
    ~ identifier = "app-prod" -> "app-prod-v2" # forces replacement
  }

# destroy（-）：刪除資源
- resource "aws_security_group" "legacy_api" {
  }
```

| 符號  | 意義               | 風險等級 | 處理原則                             |
| ----- | ------------------ | -------- | ------------------------------------ |
| `~`   | in-place update    | 中       | 逐項判斷，多數可安全 apply           |
| `-/+` | forces replacement | 高       | stateful 資源絕對不能直接 apply      |
| `-`   | destroy            | 極高     | 代表雲端有但 code 沒有，apply 會刪除 |

`-`（destroy）是最危險的類型。它代表某個資源存在於雲端但不在 Terraform code 裡——可能是手動建的、可能是從 state 被 `state rm` 移除過、也可能是前任維護者刪了 code 但沒跑 apply。不論原因，直接 apply 會把這個資源從雲端刪除。

`-/+`（forces replacement）的危險在於它看起來像修改但實際是先刪後建。對 stateless 資源（security group rule、IAM policy）影響有限，對 stateful 資源（RDS、EBS volume）意味著資料遺失。

## 故意的 drift vs 意外的 drift

不是所有 drift 都是問題。接手的環境裡，手動改動可能有兩種來源：

**故意的改動**是前任維護者為了解決特定問題而做的。常見形態：臨時開了一條 security group 規則讓外部監控系統連進來、調高了 RDS 的 `max_connections` 參數來應對流量成長、手動把 instance type 從 `t3.small` 升到 `t3.medium` 因為記憶體不夠。這類改動通常是正確的操作決策，只是沒有同步回 code。

**意外的漂移**是無意中造成的。常見形態：在 Console 測試時改了某個設定但忘了改回來、另一個 Terraform workspace 的 apply 動到了共用的資源、AWS 自動更新了某些屬性（如 default security group 的描述）。

區分兩者的方法是查 CloudTrail——看這個改動是誰做的、什麼時候、有沒有對應的 ticket 或 changelog 記錄。如果 CloudTrail 顯示改動發生在一次事故期間、由當時的值班工程師執行，大概率是故意的。如果改動來自一個不認識的 IAM user、或時間點跟任何已知事件對不上，可能是意外。

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=sg-0abc123 \
  --start-time 2026-01-01 \
  --query 'Events[].[EventTime,Username,EventName]' \
  --output table
```

## 每條 drift 的處理決策

每條 plan 差異都需要一個明確的決定：保留手動改動（更新 HCL）、回退到 code 的版本（apply）、還是暫時擱置（不動）。

### 保留（adopt into HCL）

適用條件：手動改動是正確的操作決策，雲端的現況是期望狀態。處理方式是把 HCL 改成跟雲端一致，讓下次 plan 對這項顯示零差異。

多數 drift 應該走這條路。前任維護者調大了 instance type、加了一條 security group 規則、改了 RDS parameter——這些改動通常有操作上的理由。把 code 對齊現實，比把現實改回 code 安全。

### 回退（apply to revert）

適用條件：手動改動是錯誤的、或已經不再需要（如臨時開的除錯 port）。確認回退不會影響運行中的服務後，讓 Terraform apply 把設定改回 code 描述的版本。

回退前要確認的事：這條規則還有沒有服務在用？這個參數改回去會不會讓連線斷開？如果不確定，先 adopt 再說——adopt 的成本是改一行 HCL，回退錯誤的成本可能是服務中斷。

### 擱置（defer）

適用條件：目前無法判斷該保留還是回退（缺乏 context），或改動涉及 stateful 資源的 forces replacement 需要更多準備。擱置的做法是在 code 裡加 `lifecycle { ignore_changes = [...] }` 暫時跳過這項差異，並留下註解說明為什麼擱置、預計什麼時候處理。

```hcl
resource "aws_db_instance" "primary" {
  # drift: identifier 被手動改過，forces replacement
  # 擱置原因：直接 apply 會觸發 RDS 重建、資料遺失
  # 預計處理：確認新 identifier 後更新 HCL + 用 moved block
  lifecycle {
    ignore_changes = [identifier]
  }
}
```

擱置不是永久解法。`ignore_changes` 會讓這個屬性脫離 IaC 管理，累積越多就越接近「回到手動」。定期回顧擱置清單，逐項決定保留或回退。

## Stateful 資源的高風險 drift

stateful 資源（RDS、EBS volume、DynamoDB table）的 drift 需要特別處理，因為 forces replacement 意味著資料遺失。以下屬性的改動在 plan 裡會顯示 `-/+`（forces replacement），直接 apply 會先刪除再重建：

| 資源類型   | 觸發 replacement 的屬性                          | 後果                        |
| ---------- | ------------------------------------------------ | --------------------------- |
| RDS        | `identifier`、`engine`、某些 `storage_type` 變更 | 資料庫被刪除重建，資料遺失  |
| EBS volume | `availability_zone`、`size`（縮小）              | volume 被刪除重建，資料遺失 |
| DynamoDB   | `hash_key`、`range_key`                          | table 被刪除重建，資料遺失  |

發現 stateful 資源的 forces replacement 時，處理步驟：

1. 在 `lifecycle` 加 `ignore_changes` 暫時跳過
2. 備份資源（RDS snapshot、EBS snapshot）
3. 確認正確的目標狀態後，用 `moved` block 或 `terraform state mv` 處理 identity 變更
4. 用 `terraform plan` 驗證變更類型從 `-/+` 變成 `~`（in-place）或零差異
5. 移除 `ignore_changes`

## refresh-only：安全的 state 同步

`terraform apply -refresh-only` 只更新 state 來反映雲端現況，不改變任何雲端資源。它適用於「雲端被手動改了、想讓 state 跟上現實但還沒準備好改 HCL」的情境。

```bash
terraform apply -refresh-only
```

refresh-only 之後，state 跟雲端一致了，但 state 跟 HCL 之間的差異仍然存在——下次跑 plan 仍會看到 drift。它解的是「state 過時」的問題，不是「code 跟現實不一致」的問題。兩者要分開處理：先 refresh-only 讓 state 乾淨，再逐項決定 HCL 要不要對齊。

使用 refresh-only 的前提是確認 state backend 有 versioning——如果 refresh-only 把 state 改壞了（例如併發操作導致 state 衝突），需要能回捲到上一個版本。

## 批次 drift 收斂工作流

接手環境的 drift 通常不是一兩條，可能有幾十條。逐條處理可以但效率低，按類型批次處理比較實際：

**第一批：安全類**。security group 規則、IAM policy 的 drift 優先處理，因為它們直接影響存取邊界。全開的規則該關就關（回退），故意開的規則 adopt 進 code。

**第二批：stateless 資源的 in-place drift**。tag 不一致、description 不一致、非關鍵屬性的變更。這類 drift 風險低，可以批次 adopt（把 HCL 改成跟雲端一致）然後一次 apply 驗證。

**第三批：stateful 資源**。RDS parameter、backup retention、instance class 的變更。逐個處理，每個都要確認是 in-place update 而非 forces replacement。

**第四批：擱置項**。forces replacement、無法判斷的改動。加 `ignore_changes` 暫緩，排進 backlog 定期回顧。

每一批處理完後跑一次 plan，確認該批的 drift 消失、其他批次的 drift 沒被影響。不要一次 apply 所有批次——分批的目的是控制每次 apply 的影響範圍。

整個 drift 收斂流程的時程取決於 drift 數量和 stateful 資源的比例。20 條以內的 drift、多數是 stateless 的 in-place 變更，2-3 天可以收完。50 條以上、含多個 stateful 資源的 forces replacement，需要 1-2 週分階段處理。

## 跨分類引用

- → [有半套 IaC 但文件缺失的環境接管](/infra/takeover/partial-iac-no-docs/)：本文的上層總覽
- → [Unmanaged resource 批次 import](/infra/takeover/partial-iac-bulk-import/)：state 外的資源怎麼納管
- → [Console 唯讀鐵律](/infra/01-minimal-iac/console-readonly-minimal-viable/)：drift 的根本防線
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：drift 收斂後的環境拆分路徑
