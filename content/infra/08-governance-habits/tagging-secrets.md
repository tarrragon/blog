---
title: "Tagging 規範與 Secrets 不進 code"
date: 2026-06-26
description: "tag 讓資源可盤點、可清理、可歸屬；密鑰存在專用服務裡而非 code 或 state，兩者都屬於 day-1 就該立的治理地基"
weight: 1
tags: ["infra", "governance", "tagging", "secrets"]
---

每一個治理習慣單獨看都很小：在資源上多打三個 tag、把一段連線字串挪去別的地方。但少了這些習慣，半年後的代價是另一個量級 — 翻著一頁兩百筆沒有歸屬的資源猜哪個能砍、為了輪替一把外洩的密鑰回頭 grep 整個 repo。Tagging 與 secret 管理是治理習慣裡補救成本最陡的兩項：tag 一旦缺席就得回頭考古幾百個資源，密鑰一旦進了 git 歷史就無法清除。它們共同的特性是 day-1 建立的成本接近零，事後補的代價隨資源數量與時間複利。

## Tagging 規範：查帳與清資源的依據

Tag 是貼在每個資源上的結構化標籤，承擔「讓資源能被機器查詢與分群」的責任。沒有 tag 的資源在 console 裡只剩一個隨機後綴的名字，人能勉強認得幾個，但一旦數量過百，任何「列出所有 staging 的資源」「算出 team-a 這個月花多少」的問題都無法用查詢回答，只能逐筆翻。Tag 把這些問題從人工考古變成一行 filter。

### 最小 tag 集合

值得從第一天就強制的最小 tag 集合是三個維度，各自回答一個治理問題：

| Tag           | 回答的問題   | 典型值                       | 缺了會怎樣                                   |
| ------------- | ------------ | ---------------------------- | -------------------------------------------- |
| `env`         | 這是哪個環境 | `prod` / `staging` / `dev`   | 清資源時不敢動、怕誤刪生產                   |
| `owner`       | 出事找誰     | `team-payments` / `platform` | 資源孤兒化、沒人認領也沒人敢回收             |
| `cost-center` | 這筆錢算誰的 | `cc-1024` / `growth`         | 帳單無法拆分、成本變成一筆沒人負責的公共支出 |

`env` 是清資源時的安全護欄。回收動作最大的恐懼是誤刪生產資源。當每個資源都標了 `env`，「列出所有 `env=dev` 且 30 天無流量的資源」就是一條可以放心執行的清理查詢，而 `env=prod` 的資源自動被排除在批次刪除之外。沒有這個 tag，任何自動化清理都因為怕誤傷而不敢落地，最後退回人工逐筆確認，於是根本沒人去清。

`owner` 解決資源孤兒化。服務出狀況、或是看到一個用途不明的資源時，第一個問題是「這誰的」。標了 owner，告警可以自動路由、清理前可以自動通知認領；沒標，這個資源就停在「沒人敢動、因為不知道砍了會不會弄壞什麼」的狀態，永久占用配額與費用。團隊命名比個人名好 — 人會離職，團隊邊界相對穩定。

`cost-center` 是成本歸屬的地基，把帳單從「一筆公共支出」拆成「每個團隊各自負責的花費」。這個維度的後續應用在[成本可見性與最小可行治理節奏](/infra/08-governance-habits/cost-visibility-rhythm/)展開。

### 附加 tag 的合理時機

三個必填之外，隨著團隊規模增長，幾個常見的附加維度會自然浮現：

| Tag          | 用途                                       | 加入時機                          |
| ------------ | ------------------------------------------ | --------------------------------- |
| `managed-by` | 區分 IaC 管理 vs 手動建立                  | 導入 IaC 第一天就加               |
| `project`    | 區分同一團隊下不同產品線                   | 團隊負責超過一個產品時            |
| `ttl`        | 資源預定存活時間（如 `7d`）                | 開始有大量開發 / 測試用臨時資源時 |
| `compliance` | 標記受法規約束的資源（如 `pci` / `hipaa`） | 開始有合規稽核需求時              |

`managed-by = terraform` 搭配 `env`，可以快速找出「不在 IaC 管理下的生產資源」 — 這些就是 Console 唯讀紀律（[模組一](/infra/01-minimal-iac/)）鬆動的痕跡。附加 tag 不需要一次規劃完，但一旦加入就要跟必填 tag 一起走自動護欄。

### 用 IaC 自動標記

Tag 必須在資源建立時就由 IaC 寫進去，而不是事後補。Terraform 的 `default_tags` 讓一個 provider 區塊內的所有資源自動繼承一組 tag，避免逐個資源手動標、也避免漏標：

```hcl
provider "aws" {
  region = "ap-northeast-1"

  default_tags {
    tags = {
      env         = var.env
      owner       = var.team
      cost-center = var.cost_center
      managed-by  = "terraform"
    }
  }
}
```

用 `var` 取代寫死的值，讓同一套 provider 設定跨環境複用 — 每個環境的 `terraform.tfvars` 填入自己的值。這和[模組四：環境分離與模組化](/infra/04-environment-separation/)的參數化設計一致。

個別資源若需要額外 tag（例如 `ttl`），在資源自身的 `tags` block 裡寫，它會跟 `default_tags` 合併，不需要重複寫環境層的三個必填。兩者有相同 key 時資源層優先，所以某個特殊資源要覆蓋 owner 也行。

事後補 tag 是個會無限拖延的工作，因為它不影響任何功能、沒有 deadline、永遠排在 backlog 最後。

### Tag 合規護欄

判讀訊號很簡單：定期跑一條「列出缺少必填 tag 的資源」的查詢，數字若持續成長，代表有人繞過 IaC 手動開資源 — 這既是 tag 問題，也是模組一「Console 唯讀」紀律鬆動的徵兆。

```bash
# 列出沒有 env tag 的 EC2 instance
aws resourcegroupstaggingapi get-resources \
  --resource-type-filters ec2:instance \
  --tag-filters Key=env,Values= \
  --query 'ResourceTagMappingList[].ResourceARN'
```

手動查詢只是起點。更可靠的做法是用策略引擎在建立期或 PR 階段就擋住不合規的資源：

- **AWS Tag Policy**（Organizations 層級）：定義必填 tag 與允許值的枚舉，不符合就阻止建立。適合整個組織統一推行。
- **OPA / Sentinel**（CI / PR 層級）：在 `terraform plan` 之後、`apply` 之前檢查 plan 輸出，缺 tag 就讓 CI fail。適合跟[模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)整合。
- **checkov / tfsec 自訂規則**：靜態掃描 HCL，在 code push 時就擋。成本最低但只擋得住 IaC 管理的資源。

三層護欄互補：靜態掃描擋寫 code 時的遺漏、plan 檢查擋執行前的偏差、tag policy 擋繞過 IaC 的手動操作。早期只做一層也有價值，三層都做時覆蓋最完整。定期跑 tag 覆蓋率報告（缺少必填 tag 的資源數 / 總資源數）可以作為治理進度的量化指標。覆蓋率從 40% 到 90% 的趨勢比單次數字更有意義，適合放進月報讓管理層追蹤。

Tagging 在合規驅動的基礎設施中還有另一層用途：用 tag 標記資料的地理歸屬，讓合規查詢可以機器化。Hard Rock Digital 的運動博彩平台受美國 Wire Act 約束，不同州的投注資料必須留在州內。它們用 CockroachDB 跨 AWS Outposts 部署，每個 Outpost 的資源用地理 tag 標記歸屬州，合規稽核時用 tag 過濾而非逐台盤查。這個案例的 infra 教訓是：tag 的維度設計在受地理或法規約束的服務中，要提前納入合規需求的維度，而非只做成本和歸屬。詳見 [9.C41 Hard Rock Digital：Wire Act 合規](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)。

## Secrets 不進 code：機密值的儲存與引用

機密值 — 資料庫密碼、第三方 API key、簽章用的私鑰 — 要存在專用的密鑰管理服務裡，而 code 與 IaC 只持有指向它的參照，不持有值本身。這條規則承擔的責任是把「機密外洩的爆炸半徑」與「程式碼的散布範圍」脫鉤：一旦密碼寫進 repo，它就跟著每一次 clone、每一份 CI 快取、每一個 fork 擴散，輪替時無法保證所有副本都更新，git 歷史更是會把它永久留存，即使後來刪掉那一行。

### 密鑰管理服務的選型

密鑰管理服務提供的是一個有存取控制、有審計紀錄、可輪替的集中儲存。值放在這裡，誰讀過、什麼時候讀的都有 log，輪替時只改一個地方，所有引用方下次讀取就拿到新值。

| 服務                    | 定位                           | 適合的情境                       |
| ----------------------- | ------------------------------ | -------------------------------- |
| AWS Secrets Manager     | 受管 secret、支援自動輪替      | 資料庫密碼、需要自動輪替的 key   |
| AWS SSM Parameter Store | 輕量級 key-value、有免費額度   | 設定值、不需要自動輪替的 secret  |
| HashiCorp Vault         | 自管 / 託管、跨雲、動態 secret | 多雲或需要動態產生短期憑證的團隊 |
| GCP Secret Manager      | GCP 原生受管 secret            | GCP 生態                         |

選型看的是團隊已有的生態與輪替需求。對已在 AWS 上的團隊，Secrets Manager 適合需要自動輪替的資料庫密碼，SSM Parameter Store 適合其餘設定值（免費額度通常夠用）。跨雲或對動態 secret 有需求的團隊會走 Vault。

### IaC 怎麼引用 secret

IaC 應該存的是密鑰的 ARN（或等價的資源識別碼）與「在執行期去讀它」的指令，而不是密鑰的明文：

```hcl
data "aws_secretsmanager_secret_version" "db" {
  secret_id = "prod/payments/db-password"
}

resource "aws_db_instance" "payments" {
  password = data.aws_secretsmanager_secret_version.db.secret_string
  # ...
}
```

另一種做法是讓 IaC 只建立 secret 的「容器」（空的 Secrets Manager entry），值由人工或自動化流程在 IaC 之外寫入。這樣 state 裡只有 secret 的 metadata（ARN、名稱、版本 ID），完全不碰明文。適合密碼由安全團隊管理、IaC 只負責「確保 secret 存在且有正確的存取策略」的分工模式。

```hcl
resource "aws_secretsmanager_secret" "db" {
  name = "${var.env}/payments/db-password"
}

# 值不由 Terraform 管理 — 在 Console 或 CLI 手動設定
# secret version 生命週期在 IaC 之外
```

### state 裡的機密邊界

Terraform 即使從 Secrets Manager 讀值，那個值仍然會以明文落進 state 檔。這是一個常被忽略的邊界。「不進 code」只是第一道，state 後端的加密與存取控制（[模組一的 state 地基](/infra/01-minimal-iac/)）是同等重要的第二道 — 否則密鑰只是從 repo 搬到了一個沒鎖好的 state bucket。

State 的保護措施是一道複合防線：

- S3 bucket 開 `encrypt = true`（AES-256 或 KMS）
- Bucket 的 IAM policy 只允許跑 `apply` 的 role 讀寫
- Bucket 開 versioning，誤寫或損壞時可以回捲
- DynamoDB lock table 防止並行 apply 覆蓋

這些措施在[模組一](/infra/01-minimal-iac/)的 remote state backend 段已經詳述，這裡提醒的是：state 的安全程度決定了 secret 引用策略的上限。state 沒鎖好時，把 secret 值拉進 state 的做法等於把密碼從 repo 搬到了另一個不設防的地方。

### Secret 掃描

判讀訊號：定期用 secret 掃描工具掃 repo 與 CI log，任何命中都當成需要輪替的外洩事件處理，而不是刪掉那行就算了 — 因為 git 歷史與既有 clone 已經保不住了。

```bash
# gitleaks：掃描整個 git 歷史
gitleaks detect --source . --report-format json --report-path gitleaks-report.json

# trufflehog：掃描 git、filesystem、CI
trufflehog git file://. --json
```

兩個工具覆蓋面不同（gitleaks 用 regex pattern、trufflehog 用 detector + entropy），搭配用覆蓋更完整。放進 CI pipeline 讓每個 PR 自動掃，比人工定期跑更可靠。命中後的處理流程：先輪替被洩露的 secret，再從 repo 清除（`git filter-repo`），最後通知所有可能受影響的服務。

### Secret 命名規範

機密的命名也值得約定。用 `{env}/{service}/{purpose}` 這類有結構的路徑（如 `prod/payments/db-password`），讓存取策略可以用前綴授權：

```hcl
# 給 payments service 的 role 只能讀自己的 secret
data "aws_iam_policy_document" "payments_secrets" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = ["arn:aws:secretsmanager:*:*:secret:${var.env}/payments/*"]
  }
}
```

前綴授權的好處是新增 secret 時不需要改 IAM policy — 只要命名落在同一個前綴下，存取權限自動繼承。跟[模組二](/infra/02-identity-credentials/)的最小權限設計一致：service A 的 role 只看得到 `payments/*`，看不到 `auth/*`，即使它們存在同一個帳號的 Secrets Manager 裡。

## 跨分類引用

- → [模組一：最小可行 IaC](/infra/01-minimal-iac/)：state 後端的加密與存取控制是 secret 引用策略的安全地基
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：誰能讀哪些 secret 的 IAM 權限設計
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：tag 的環境值與 module 參數化的對齊
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：tag 合規與 secret 掃描整合進 CI pipeline
- → [backend 模組七：資安與資料保護](/backend/07-security-data-protection/)：密鑰生命週期、輪替策略與資料保護的完整討論
