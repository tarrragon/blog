---
title: "Unmanaged Resource 批次 Import 工作流"
date: 2026-06-26
description: "把 Terraform state 外的雲端資源有系統地納入 IaC 管理：優先序判斷、import block 語法、generated HCL 的 review 要點、批次策略與常見失敗處理"
weight: 22
tags: ["infra", "takeover", "terraform", "import"]
---

盤點階段產出的 managed vs unmanaged 兩欄清單裡（見[盤點流程](/infra/takeover/partial-iac-no-docs/)），unmanaged 那一欄的每個資源都要決定：納入 Terraform 管理、還是維持手動並記錄原因。這篇處理的是「決定要納管」的資源怎麼有系統地 import，而不是一次全部倒進去。

## 優先序：先 import 什麼

不是所有 unmanaged resource 都值得立刻 import。判斷依據是「這個資源不在 IaC 裡的風險有多高」和「import 的操作複雜度有多低」的交集。

| 優先級 | 資源類型                          | 理由                                                                        |
| ------ | --------------------------------- | --------------------------------------------------------------------------- |
| 1      | Security group、IAM role / policy | 安全邊界資源，手動改動的風險最高，且 import 後 plan 驗證直覺                |
| 2      | VPC、subnet、route table          | 網路地基，其他資源依賴它們，import 後上層資源的引用才能從 hardcode 換成引用 |
| 3      | RDS、ElastiCache                  | 有狀態資源，import 操作本身不改資源，但 plan 不匹配時的修正要謹慎           |
| 4      | S3 bucket、CloudWatch log group   | 低風險、低依賴，但數量可能很多，適合最後批次處理                            |
| 5      | EC2 instance、Lambda              | 變動頻繁、生命週期短，import 的 ROI 低——考慮是否改用 IaC 重建而非 import    |

優先級 1-2 的資源是地基層，import 後能讓後續的 IaC 引用鏈從 hardcode ID 換成資源屬性引用，這是 import 的結構性收益。優先級 5 的資源如果生命週期短（隨部署替換），用 IaC 重新定義再 apply 比逆向 import 划算。

## import block 語法（Terraform 1.5+）

Terraform 1.5 引入了宣告式 import block，取代舊版的 `terraform import` CLI 指令。宣告式的優勢是 import 本身進版本控制、可 review、可回滾。

```hcl
import {
  to = aws_security_group.api
  id = "sg-0abc123def456"
}

import {
  to = aws_db_instance.primary
  id = "app-prod-primary"
}
```

`to` 是 Terraform 裡的資源地址（resource type + name），`id` 是雲端的資源識別碼。每種資源的 id 格式不同：security group 用 `sg-xxx`、RDS 用 DB identifier、S3 用 bucket name、IAM role 用 role name。格式查 Terraform provider 文件的 Import 段。

多個 import block 可以寫在同一個檔案裡（如 `imports.tf`），一次 plan/apply 處理整批。apply 完成後這些 import block 可以刪除——它們的作用是觸發 import 動作，import 完成後 state 已經記住了對應關係。

## generate-config-out 工作流

import block 只把資源綁進 state，不會自動產生對應的 HCL 定義。Terraform 1.5+ 提供 `-generate-config-out` flag 自動反推 HCL：

```bash
terraform plan -generate-config-out=generated_resources.tf
```

這個指令會：

1. 讀取所有 import block
2. 查詢每個資源在雲端的真實屬性
3. 把屬性寫成 HCL 資源定義，輸出到指定檔案
4. 在 plan 輸出中標示每個資源為 `import`（不是 create/change/destroy）

生成的 HCL 是起點，需要人工 review 後才能正式使用。

## 生成 HCL 的 review 要點

自動生成的 code 有幾個常見問題需要修正：

### 缺少 lifecycle 設定

生成的 code 不會包含 `lifecycle` block。有狀態資源（RDS、S3）需要手動加上保護：

```hcl
resource "aws_db_instance" "primary" {
  # ... generated attributes ...

  lifecycle {
    prevent_destroy = true
  }
}
```

沒加 `prevent_destroy` 的 stateful 資源，未來某次 plan 如果判定需要 replace，apply 會先刪除再重建——資料跟著消失。

### 預設值與隱含屬性

雲端資源有些屬性是由平台自動設定的（如 RDS 的 `ca_cert_identifier`、EC2 的 `credit_specification`），生成的 code 會把這些都寫出來。下次平台更新預設值時，plan 會顯示 drift。review 時判斷：這個屬性是刻意設定的（保留），還是平台預設的（刪掉、讓 Terraform 接受平台預設）。

判斷方法：如果一個屬性的值跟 provider 文件裡的 default 一致，通常可以刪掉。如果不確定，先保留——保留多餘的屬性只是 code 冗長，刪錯屬性可能在下次 apply 時改變資源行為。

### provider 特有的 quirk

不同 provider 有各自的 import 陷阱：

| 資源類型             | 常見 quirk                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `aws_security_group` | inline `ingress`/`egress` block 與獨立的 `aws_security_group_rule` 衝突，選其一             |
| `aws_s3_bucket`      | Terraform AWS provider 4.x 把 bucket 的子屬性（versioning、encryption）拆成獨立資源         |
| `aws_iam_role`       | `assume_role_policy` 是 JSON 字串，生成的 code 可能把 JSON 格式化方式跟 provider 預期不一致 |
| `aws_db_instance`    | `password` 屬性不會被 import（敏感值），需要手動設定或引用 Secrets Manager                  |

security group 的 inline vs 獨立規則問題最常見：如果生成的 code 用 inline `ingress` block，但環境裡同時有獨立的 `aws_security_group_rule` 指向同一個 SG，兩者會互相打架。統一選一種寫法——多數情況用獨立 rule 更彈性。

## 批次策略

一次 import 太多資源會讓 plan 輸出太長、review 不了。按服務類型分批，每批 5-15 個資源：

```text
批次 1: security groups (所有 SG + 對應的 rules)
批次 2: VPC + subnets + route tables + NAT
批次 3: IAM roles + policies
批次 4: RDS instances + subnet groups + parameter groups
批次 5: S3 buckets + bucket policies
批次 6: ALB + listeners + target groups
```

每批的操作流程固定：

1. 寫 import block → `imports-batch-N.tf`
2. `terraform plan -generate-config-out=generated-batch-N.tf` → 檢查 plan 輸出全部是 `import`、沒有 `create`/`destroy`
3. review generated code → 修正 lifecycle、刪除平台預設屬性、處理 provider quirk
4. `terraform plan` → 確認零非預期變更（import 完後的 plan 應該只有 import 標記、沒有 change）
5. `terraform apply` → 執行 import
6. `terraform plan` → 再跑一次確認零 drift（import 後的 state 與雲端一致）
7. 刪除 `imports-batch-N.tf`（import block 已完成使命）、把 `generated-batch-N.tf` rename 成正式檔名

批次之間要按依賴順序：先 import 被依賴的資源（VPC → subnet → SG），再 import 依賴它們的資源（RDS → EC2）。這樣後面批次的 generated code 可以引用前面批次已經在 state 裡的資源，而非 hardcode ID。

## 驗證：plan 必須是零非預期變更

import 完成的判準是 `terraform plan` 輸出只有兩種結果之一：

- **完全零變更**（"No changes"）— 最理想，代表 HCL 和雲端現實完全匹配
- **只有已知且可接受的差異** — 某些屬性在 HCL 裡省略了（用平台預設）、或 provider 的 plan 行為跟雲端有已知的格式差異（如 JSON 排序不同）

出現 `change`（要修改屬性）代表 HCL 跟雲端有落差，apply 會把雲端改成 HCL 的版本。在確認這個修改是安全的之前，不要 apply。

出現 `replace`（先刪後建）代表某個屬性的修改會觸發資源重建。對 stateful 資源這等於資料遺失，必須在 apply 之前解決——通常是 HCL 裡漏寫了某個 force-new 屬性。

## 常見 import 失敗與處理

| 錯誤訊息                                        | 原因                                            | 處理方式                                                |
| ----------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------- |
| `Resource already managed by Terraform`         | 資源已經在 state 裡                             | 用 `terraform state list` 確認、移除重複的 import block |
| `Cannot import non-existent remote object`      | 資源 ID 錯誤或資源已刪除                        | 確認 ID 格式正確、在 Console 確認資源存在               |
| `Error: Unsupported resource type`              | provider 版本太舊不支援該資源類型               | 升級 provider version                                   |
| `AccessDenied` / `is not authorized to perform` | 執行 import 的身分權限不足                      | import 需要對目標資源的 `Describe*` 和 `Get*` 權限      |
| Plan 顯示意外的 `destroy`                       | import block 的 `to` 地址跟已存在的資源定義衝突 | 確認 `to` 指向的 resource block 不已經管理另一個資源    |

import 操作本身不改變雲端資源——它只修改 state 檔。失敗時的回退方式是 `terraform state rm <resource_address>`，把 state 裡的對應記錄移除，資源本身不受影響。

## 時程參考

| 批次規模             | 估計時間（含 review）                |
| -------------------- | ------------------------------------ |
| 5-10 個同類資源      | 2-4 小時（含 generated code review） |
| 10-20 個混合資源     | 1-2 天                               |
| 50+ 個資源的完整環境 | 1-2 週（分 5-8 個批次、每批含驗證）  |

主要時間花在 generated HCL 的 review——生成是秒級的，確認每個屬性正確與否是人工判斷。第一批（security group）通常最慢，因為要建立 review 的肌肉記憶；後面的批次會加速。

## 跨分類引用

- → [有半套 IaC 但文件缺失的環境接管](/infra/takeover/partial-iac-no-docs/)：import 前的盤點與 state 健康檢查
- → [兩套真相並存的過渡期操作](/infra/takeover/partial-iac-dual-truth-operation/)：import 期間就是 dual-truth 狀態，操作規則見此篇
- → [模組一：IaC 工具選型與 state 地基](/infra/01-minimal-iac/)：state backend 的設定與保護
- → [模組五：Stateful 資源保護](/infra/05-core-services/stateful-protection-dependency/)：import stateful 資源後的 lifecycle 設定
