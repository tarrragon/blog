---
title: "兩套真相並存的過渡期操作"
date: 2026-06-26
description: "部分資源在 IaC、部分在手動時，怎麼安全操作避免比全手動更危險，以及怎麼縮短這個過渡期"
weight: 23
tags: ["infra", "takeover", "terraform", "transition"]
---

部分資源由 Terraform 管理、部分仍在手動操作的環境，比全手動更危險。全手動時每個人都知道要去 Console 操作，行為模式一致；半套 IaC 時同一個環境有兩套操作路徑，每一次操作都要先判斷「這個資源歸哪套管」，判斷錯了的後果是 apply 覆蓋手動設定、或手動改動讓 state 與現實分歧。這篇處理的是怎麼在這個過渡期安全操作，以及怎麼盡快離開這個狀態。

## 為什麼半套比全手動更危險

兩個方向的風險同時存在，而且互相放大。

### apply 可能摧毀未納管的資源

Terraform apply 只知道 state 裡有什麼。一個存在於雲端但不在 state 裡的資源，對 Terraform 來說「不存在」。如果某個 managed resource 引用了一個 unmanaged resource 的 ID（例如一個 security group 引用了一個手動建的 security group 作為 source），apply 不會主動碰那個 unmanaged resource——但如果有人重構了 HCL 並把那個引用移除或改掉，apply 會改動 managed 的那一端，可能讓依賴它的 unmanaged 資源失去連線。

更直接的風險是 `terraform destroy` 或 `terraform apply` 配合 `count = 0` 這類邏輯刪除：如果有人誤判某個資源已經不用了、但它其實只是不在 state 裡（被前人 `state rm` 過），destroy 不會碰它——但如果有人重新 import 它再 destroy，資源就真的被刪了。

### 手動改動讓 managed 資源 drift

有人在 Console 手動改了一個已經由 Terraform 管理的資源（例如加了一條 security group 規則），state 不知道這個改動。下一次任何人跑 apply，Terraform 會把手動加的規則判定為「不該存在」並刪除。手動改動的人以為規則已經加好了，直到某次不相關的 apply 把它默默清掉。

這兩個風險的交叉效應是：團隊對「能不能跑 apply」和「能不能手動改」都缺乏信心，結果是兩邊都不敢動，變更停滯，技術債累積速度比全手動還快。

## 過渡期操作規則

過渡期的操作紀律核心是一句話：**每個資源在任何時刻都只有一個合法的變更路徑**。managed 資源走 IaC，unmanaged 資源走 Console + 變更日誌。混用就是 drift 的來源。

### 規則一：apply 前必讀 plan

過渡期的每一次 `terraform apply` 之前，都要完整讀 `terraform plan` 的輸出，逐行確認每一項變更是預期內的。特別警惕以下訊號：

- `will be destroyed`：確認這個資源是否有其他依賴（即使它在 state 裡）
- `will be updated in-place` 且變更的屬性不是這次修改的：代表有人手動改了這個屬性，apply 會覆蓋回去
- `must be replaced`：資源會被先刪後建，stateful 資源（RDS、EBS）在這裡要暫停確認

過渡期禁止 `terraform apply -auto-approve`。即使 CI pipeline 也要把 apply 設為手動觸發（GitHub Actions 的 environment protection rule），確保有人看過 plan。

### 規則二：不手動改 managed 資源

一個資源一旦進了 Terraform state，所有對它的變更都走 HCL → plan → apply。在 Console 改它會製造 drift，而 drift 在過渡期特別危險——因為下一次 apply 可能已經隔了好幾天，中間的手動改動已經忘了。

如果遇到緊急情況必須手動改 managed 資源（例如安全事件需要立即封鎖某個 port），操作流程是：

1. 在 Console 做緊急變更
2. 立刻在變更日誌記錄：時間、資源、改了什麼、為什麼
3. 在 HCL 裡同步這個變更，提 PR
4. PR 裡的 plan 應該顯示零變更（因為 HCL 已經對齊了手動改動）
5. 合併 PR，state 透過下一次 apply 或 refresh 更新

### 規則三：記錄哪些資源歸誰管

維護一份「管理歸屬清單」——哪些資源在 Terraform state 裡、哪些還在手動管理。格式可以是 repo 裡的一個 markdown 表格：

```markdown
## 資源管理歸屬

| 資源類型       | 資源名稱/ID         | 管理方式   | 備註             |
| -------------- | -------------------- | ---------- | ---------------- |
| VPC            | vpc-0abc123          | Terraform  |                  |
| Subnet (×4)   | subnet-0def...       | Terraform  |                  |
| RDS            | app-prod-primary     | Terraform  | stateful、謹慎操作 |
| SG web         | sg-0web456           | Terraform  |                  |
| SG legacy-api  | sg-0legacy789        | 手動       | 待 import        |
| EC2 worker     | i-0worker123         | 手動       | 待 import        |
| Lambda cron    | cleanup-job          | 手動       | 待評估是否納管   |
```

這份清單的維護者是跑 apply 的人——每次 import 一個新資源後更新清單。清單同時是 team communication 的基礎：team member 要改某個資源前，先查清單確認管理方式。

## 團隊溝通

過渡期最重要的溝通是讓所有會碰 Console 的人知道哪些資源「不能手動改」。溝通的形式是直接的操作指令：

在 team channel 發一則釘選訊息：

```text
[Infra 過渡期操作規則]

以下資源已由 Terraform 管理，變更請走 PR：
- VPC 和所有 subnet
- Security group: sg-0web456, sg-0app789
- RDS: app-prod-primary
- ALB: app-prod-alb

以下資源仍為手動管理，變更請在 Console 操作後寫 changelog：
- EC2: i-0worker123
- Lambda: cleanup-job
- SG: sg-0legacy789

不確定的資源：先問再動。
```

隨著 import 進展更新這則訊息。如果團隊用的是 Slack，可以把這則訊息設成 channel bookmark。

## 縮短過渡期

過渡期越長、兩套真相並存越久、操作事故的機率越高。縮短的方式是用 import sprint 集中處理。

### Import sprint 的排程

一個 import sprint 是 1-2 天的集中工作，目標是把一批相關的 unmanaged 資源納入 Terraform。按風險從低到高排序：

| 批次 | 資源類型              | 理由                                  | 預估時間       |
| ---- | --------------------- | ------------------------------------- | -------------- |
| 1    | SG、IAM role/policy   | 高頻變更、drift 風險最高              | 半天到一天     |
| 2    | S3 bucket、CloudWatch | stateless、import 風險低              | 半天           |
| 3    | EC2 instance、ECS     | 中風險、需確認 user data 和 AMI       | 一天           |
| 4    | RDS、EBS              | stateful、import 失敗代價最高、最後做 | 一天（含驗證） |

每批的操作流程：

1. 用 `import` block + `terraform plan -generate-config-out` 產生 HCL
2. 審查生成的 HCL，修正屬性差異
3. `plan` 確認零變更
4. 合併 PR
5. 更新管理歸屬清單

### 縮短期間不要追求完美

import sprint 的目標是「納管」，不是「重構」。一個手動建的資源 import 進來後，它的 HCL 可能很醜（自動生成的 code 有大量冗餘屬性），但只要 plan 顯示零變更，它就已經是 managed 的了。重構 HCL 是 import 完成之後的事。

同樣，import sprint 期間不要同時做 module 化或環境分離。先把所有資源納管到同一份 state，之後再拆——拆的前提是所有資源都在 state 裡。

## 過渡期結束的判準

過渡期結束的定義是兩個條件同時滿足：

1. **`terraform plan` 在無 code 變更時顯示零差異**：代表 state 與雲端現實一致，沒有 drift
2. **管理歸屬清單上的「手動」欄位清空**：所有生產資源都進了 Terraform state

第一個條件用定期排程驗證（每天跑一次 plan，非零就告警）。第二個條件用資源盤點比對——雲端的 resource inventory 減去 `terraform state list` 的輸出，差集為空就完成。

過渡期結束後，操作規則簡化為：所有變更走 IaC + PR，Console 只用來觀察和排查。這就是[模組一的 Console 唯讀鐵律](/infra/01-minimal-iac/console-readonly-minimal-viable/)。

## 跨分類引用

- → [有半套 IaC 但文件缺失的環境接管](/infra/takeover/partial-iac-no-docs/)：本篇的前置操作（盤點、state 健康檢查、drift 收斂）
- → [State 修復與清理](/infra/takeover/partial-iac-state-repair/)：過渡期出問題時可能需要 state surgery
- → [模組一：Console 唯讀鐵律](/infra/01-minimal-iac/console-readonly-minimal-viable/)：過渡期結束後的操作紀律
- → [模組四：環境分離 retrofit](/infra/04-environment-separation/single-to-multi-env-retrofit/)：所有資源納管後的下一步
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/plan-review-apply-guardrails/)：過渡期結束後的完整 PR 護欄
