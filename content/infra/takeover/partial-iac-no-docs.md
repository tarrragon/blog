---
title: "有半套 IaC 但文件缺失的環境接管"
date: 2026-06-26
description: "IaC 覆蓋不完整、部分資源在 state 外、文件缺失的環境怎麼盤點差距、修復 state 健康、收斂 drift 並重建文件"
weight: 3
tags: ["infra", "takeover", "terraform", "drift", "state"]
---

接手一個有半套 IaC 的環境，比接手全手動的環境更難處理。全手動環境的規則簡單：所有東西都在 Console，逐一盤點就好。半套 IaC 的環境則有兩套真相並存 — 有些資源由程式碼管理、有些是手動加的、有些曾經由程式碼管理但後來被手動改過。`terraform plan` 跑出來一長串 diff，哪些是該收進來的手動變更、哪些是該回退的設定漂移、哪些資源根本不在 state 裡，都要逐一判斷。在搞清楚這些之前，任何 `apply` 都可能覆蓋正在服務客戶的設定。

本篇的操作流程從盤點差距開始，經過 state 健康檢查、drift 收斂、文件重建，到最後排出收斂的優先序。每一步都在不影響線上服務的前提下進行。

## state 與現實的差距盤點

盤點的第一步是跑 `terraform plan` 但不 apply — plan 的輸出就是程式碼描述的狀態與雲端現實之間的完整差距清單。

```bash
terraform plan -no-color > plan-baseline-$(date +%Y%m%d).txt
```

把這份輸出存進 repo，它是接手時的基線快照。之後每一次收斂動作的效果都用「跟這份基線比少了幾項 diff」來衡量。

### 三類 diff 的判讀

plan 輸出的每一項 diff 歸屬三類，各自的風險等級與處理方式不同：

| diff 類型 | plan 標記             | 含義                                                | 風險 | 處理方式                                    |
| --------- | --------------------- | --------------------------------------------------- | ---- | ------------------------------------------- |
| 要改      | `~` (update in-place) | 資源存在於 state 與雲端，但屬性不一致               | 中   | 逐項判斷是採納手動變更還是回退              |
| 要建      | `+` (create)          | 資源在程式碼裡但雲端不存在                          | 低   | 通常是前人寫了但沒 apply、或曾 destroy      |
| 要刪      | `-` (destroy)         | 資源在 state 裡但雲端不存在、或雲端有但程式碼想移除 | 高   | 絕對不要盲目 apply — 先確認資源是否仍在使用 |

「要刪」是最危險的一類。常見成因是：前人在 Console 手動刪了某個資源但沒同步從程式碼移除（state 裡還有紀錄），或者前人在程式碼裡移除了某段 HCL 但沒跑 apply（雲端資源還在、state 記得它）。兩種情況都需要先確認該資源在雲端是否存在、是否仍被服務依賴，再決定是從 state 移除（`terraform state rm`）還是補回 HCL。

另一個需要留意的標記是 `-/+`（forces replacement）— 它代表 Terraform 判定這個屬性的變更無法原地更新，必須先刪除再重建。對 stateful 資源（RDS、EBS volume）來說這等於資料遺失，在接手階段看到這個標記要先暫停、查清楚是哪個屬性觸發了 replacement。

## 哪些資源在 state 裡、哪些不在

`terraform state list` 列出所有被 IaC 管理的資源。但 state 只是一份已知的清單 — 雲端上可能還有大量不在這份清單裡的資源。

```bash
# state 裡有什麼
terraform state list > managed-resources.txt

# 雲端上有什麼（以 EC2 + RDS + SG 為例）
aws ec2 describe-instances --query 'Reservations[].Instances[].InstanceId' --output text > cloud-ec2.txt
aws rds describe-db-instances --query 'DBInstances[].DBInstanceIdentifier' --output text > cloud-rds.txt
aws ec2 describe-security-groups --query 'SecurityGroups[].GroupId' --output text > cloud-sg.txt
```

用這兩份清單做比對，分成三類：

| 類別   | 定義                 | 下一步                            |
| ------ | -------------------- | --------------------------------- |
| 已管理 | state 裡有、雲端也有 | 處理 drift（上一節的 diff）       |
| 未管理 | 雲端有、state 裡沒有 | 評估是否需要 import               |
| 孤兒   | state 裡有、雲端沒有 | `terraform state rm` 清除過時紀錄 |

未管理的資源需要逐一判斷：這個資源是前人刻意排除在 IaC 外的（例如一個還在實驗的測試機），還是應該納管但漏了？判斷依據是它的角色 — security group、IAM role、VPC 這類地基資源應該優先 import；一台跑完就該關的測試 EC2 可以暫時留在手動。

## state 的健康檢查

state 本身的存放方式決定了後續所有操作的安全性。接手後第一件事是確認 state 的健康狀態。

### 存放位置

```bash
# 查看 backend 設定
grep -A 10 'backend' *.tf
```

如果 backend 是 `local`（或沒有 backend 設定），state 檔只存在某台機器的磁碟上。這代表如果有第二個人從自己的機器跑 `apply`，兩人會用不同版本的 state 互相覆蓋。把 state 搬到 remote backend（S3 + DynamoDB lock）是接手後的第一優先事項，做法見[IaC 工具選型與 state 地基](/infra/01-minimal-iac/iac-tool-state-backend/)。

### 加密與版本控制

如果 state 已經在 S3，確認三件事：

```bash
# bucket 有沒有 versioning
aws s3api get-bucket-versioning --bucket <state-bucket>

# bucket 有沒有加密
aws s3api get-bucket-encryption --bucket <state-bucket>

# 有沒有 lock table
aws dynamodb describe-table --table-name <lock-table> 2>/dev/null
```

versioning 沒開的話，一次壞掉的 apply 寫壞 state 就回不去了。加密沒開的話，state 裡的敏感值（資料庫密碼、private key 輸出）以明文存在 S3。

### state 裡的敏感值

state 檔經常包含不該暴露的值。確認 state 有沒有在 Git 歷史裡：

```bash
git log --all --diff-filter=A -- '*.tfstate' '*.tfstate.backup'
```

如果命中，代表 state 曾經被推進 repo。此時 Git 歷史裡的敏感值已經無法徹底清除（`git filter-branch` 可以嘗試，但無法保證所有 clone 都更新）。務實的處理是：列出 state 裡的敏感值（`terraform show -json | jq '.. | .password? // .secret? // empty' 2>/dev/null`），全部輪替。

## drift 收斂策略

盤點完差距、確認 state 健康之後，逐項收斂 drift。對 plan 輸出的每一項 diff 做一個二選一的決定：採納手動變更（改 HCL 去符合現實），或回退到程式碼版本（讓下一次 apply 把現實改回來）。

### 採納 vs 回退的判斷

多數 drift 應該採納。前人在 Console 手動改設定通常有一個操作理由（即使沒有記錄下來）— 加了一條 security group 規則可能是為了讓某個新服務連進來，改了 RDS 的 `max_connections` 可能是為了解決連線數不足。在沒有充分理解這些改動的背景之前，回退它們等於撤銷一個可能正在支撐服務運作的設定。

回退適用的情境是：drift 明顯是誤操作（例如 `0.0.0.0/0` 打開了不該打開的埠）、或 drift 的屬性是有標準答案的（例如 S3 的 `block_public_access` 被關掉了）。

### 操作步驟

```bash
# 1. 刷新 state 到最新雲端狀態（不改資源、只更新 state 的快照）
terraform apply -refresh-only

# 2. 再跑一次 plan — 刷新後 diff 會減少（純 state 過期的 diff 消失）
terraform plan -no-color > plan-after-refresh.txt

# 3. 對剩餘的 diff 逐項處理
#    採納：改 HCL 讓程式碼跟現實一致 → plan 確認該項 diff 消失
#    回退：不改 HCL、讓 apply 把現實改回程式碼版本 → 先確認影響
```

`-refresh-only` 是安全的操作 — 它只更新 state 裡的屬性快照，不會改動任何雲端資源。但它會把手動變更「記進」state，讓後續 plan 的 diff 只剩程式碼與 state 的差異（而非程式碼與雲端的差異）。刷新後 plan 的 diff 更精確、更少、更容易逐項處理。

### import 未管理的資源

對未管理的資源，用 `import` 區塊一次處理一個，每次 import 後都跑 plan 確認零新增 diff：

```hcl
import {
  to = aws_security_group.legacy_app
  id = "sg-0abc123def456"
}
```

```bash
# 生成對應的 HCL
terraform plan -generate-config-out=generated_legacy_app.tf

# 確認生成的 HCL 跟現實一致
terraform plan
# 預期：只有 import 動作、沒有 change/destroy
```

生成的 HCL 需要人工確認 — 有些屬性是雲端自動設的預設值，Terraform 會把它們全部列出來，造成 HCL 冗長。移除純預設值的屬性、只保留有意義的設定，讓 HCL 反映設計意圖而非雲端預設。

## 文件重建

接手的環境通常沒有文件、或者文件已經過時到比沒有更糟（記載的是兩個版本前的架構）。文件重建的目標不是寫一份完美的架構文件，而是讓下一個接手者不需要重複同樣的盤點過程。

### 來源

能重建的資訊來源有限，但每個都有價值：

| 來源       | 能找到什麼                                |
| ---------- | ----------------------------------------- |
| Git log    | commit 訊息裡可能有「為什麼這樣改」的線索 |
| PR 歷史    | review 討論裡可能有決策脈絡               |
| HCL 程式碼 | 變數命名、module 結構反映架構意圖         |
| CloudTrail | 過去 90 天的 API 呼叫紀錄                 |
| 帳單       | 哪些服務在花錢、量級多大                  |

### 最小可行文件

寫一份 `INFRA-STATE.md` 放在 repo 根目錄，包含：

- **管理範圍**：哪些資源由 IaC 管理、哪些是手動的、為什麼手動的沒有 import（例：還在實驗、不穩定、計畫廢棄）
- **已知 drift**：目前 plan 輸出裡還有哪些未處理的 diff、每個 diff 的處理方向（採納/回退/待調查）
- **state 存放位置**：backend 設定、bucket 名稱、lock table 名稱
- **credential 狀態**：有幾把 access key、哪些還在用、上次輪替時間
- **接手日期與盤點結果**：盤點時的資源數量、覆蓋率（managed / total）

這份文件不需要精美，需要的是準確且持續更新。每次收斂一項 drift 或 import 一個資源，就更新對應的段落。前任團隊的知識已經不在了，這份文件取代它成為環境的記憶。

## 收斂到完整 IaC 的優先序

把整個收斂過程排成四個階段，每個階段都能獨立交付價值：

| 階段 | 目標        | 交付物                                    | 預估時間 |
| ---- | ----------- | ----------------------------------------- | -------- |
| 1    | state 健康  | remote backend + 加密 + versioning + lock | 1-2 天   |
| 2    | 地基 import | security group、IAM role、VPC 納管        | 1-2 週   |
| 3    | drift 收斂  | 已管理資源的 plan 歸零                    | 1-2 週   |
| 4    | 覆蓋率提升  | 應用層資源逐批 import                     | 持續     |

每個階段的驗證方式相同：`terraform plan` 的輸出是否比上一階段乾淨。階段一完成後，plan 的可信度才成立；階段二和三是把 plan 的 diff 清到零；階段四是擴大 plan 的管轄範圍。

每一步操作之前都先備份 state（如果 bucket 有 versioning 就靠它；沒有的話手動下載一份）。state 操作失敗時的回退路徑是從備份還原 state 檔 — 資源本身不受影響，只是工具對現實的記憶回到上一個正確的版本。

## 跨分類引用

- → [IaC 工具選型與 state 地基](/infra/01-minimal-iac/iac-tool-state-backend/)：state 怎麼從 local 搬到 remote backend
- → [Console 唯讀鐵律](/infra/01-minimal-iac/console-readonly-minimal-viable/)：drift 的來源與偵測
- → [環境分離與模組化](/infra/04-environment-separation/)：收斂完成後怎麼把單環境拆成 per-env module
- → [infra 走 PR 流程](/infra/07-infra-as-pr/)：收斂完成後的變更怎麼走 review
