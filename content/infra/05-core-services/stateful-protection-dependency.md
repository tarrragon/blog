---
title: "Stateful 資源保護與跨服務依賴表達"
date: 2026-06-26
description: "stateful 資源的保護策略（multi-AZ、備份、刪除保護）、stateful 與 stateless 的操作差異，以及用 output 與 data source 表達服務間依賴"
weight: 5
tags: ["infra", "iac", "stateful", "dependency"]
---

核心服務寫進 IaC 之後，stateful 資源需要一套與 stateless 截然不同的保護與操作規範。資料庫、裝了正式資料的 S3 bucket、持久化 volume 這類資源的共同特性是：重建代價極高甚至不可逆。運算節點掛了重開一台，資料刪了就是刪了。這個差別會傳導到 IaC 的描述方式、變更的審查強度、以及 drift 的處理策略。

本篇同時處理服務之間依賴的表達方式 — output 與 data source — 因為依賴表達直接影響 stateful 資源的爆炸半徑：同一份 state 裡的資料庫跟運算綁在一起 apply，還是拆成獨立 state 各自演進，決定了一次 apply 失敗會波及多少資源。

## stateful 資源的保護策略

stateful 資源的 IaC 描述要把「保護狀態」當成第一類需求，而非事後補上的選項。保護的三個面向 — 可用性、可還原性、防誤刪 — 各自對應不同的機制，混在一起談會讓判斷失焦。

### multi-AZ 的職責邊界

multi-AZ 用一個布林屬性開啟，背後是 RDS 在另一個可用區維護同步副本。它承擔的是可用性：主庫所在的可用區故障時，RDS 自動 failover 到 standby，服務在秒級到一兩分鐘的窗口後恢復。

multi-AZ 的邊界要明確界定，因為把它當成超出職責的工具會在事故裡踩空：

- **standby 是熱備不可讀**。multi-AZ 的 standby 不接受任何查詢流量，所以它不提供讀取擴展。要分攤讀流量得另開 read replica，這是另一個資源、另一個端點、另一套複寫延遲要管。
- **failover 有切換窗口**。切換期間應用的資料庫連線會中斷、需要重連。應用層如果沒有處理連線中斷的重試邏輯，failover 就會變成一段可見的服務中斷，而非透明切換。
- **它不防邏輯損壞**。誤刪一張 table、一筆錯誤的批次 UPDATE、一段有 bug 的 migration script — 這些操作會同步複製到 standby。multi-AZ 防的是硬體與可用區故障，邏輯損壞的防線是備份與時間點還原（PITR）。

這三條邊界說明 multi-AZ 和 backup 的職責正交：前者解可用性，後者解可還原性。兩者要分別配置、分別驗證。成本參考：multi-AZ RDS 的費用約為 single-AZ 的兩倍（standby instance 按相同規格計費）。這筆費用對應的能力是可用區故障時的分鐘級自動 failover——判斷值不值得時，用主庫所承載的服務停機每小時的商業代價來衡量。

### 備份保留與時間點還原

backup 用保留天數與備份視窗描述。RDS 依此每日自動快照並保留交易日誌，以支援還原到任意時間點（PITR）。自動備份的保留上限是 35 天，更長的留存要靠手動快照或匯出到 S3 自行管理。

`backup_retention_period` 取多少天，以 RPO（Recovery Point Objective）與合規要求反推。RPO 問的是「出事時最多能接受遺失多久的資料」— PITR 能還原到最近 5 分鐘內的時間點，但前提是自動備份有開、交易日誌有保留。保留天數決定的是「能回溯多遠」：14 天是 AWS RDS 自動備份 35 天上限的保守折衷，足以涵蓋多數營運場景下「發現問題到決定還原」的時間差；受監理的服務往 30 天推，以滿足稽核追溯窗口。

```hcl
resource "aws_db_instance" "primary" {
  multi_az                  = true
  backup_retention_period   = 14
  backup_window             = "03:00-04:00"
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "app-prod-final-${formatdate("YYYYMMDD", timestamp())}"
}
```

備份視窗選在流量低谷（如 UTC 凌晨），避免快照 IO 跟尖峰流量競爭。手動快照用獨立資源描述，常見用途是重大變更前的保險點 — 大版本升級、schema migration、或任何會改變資料結構的操作。

### 刪除保護與 final snapshot

`deletion_protection = true` 讓 `terraform destroy` 無法直接刪除這個 instance — 要先用另一次 apply 把保護關掉，這一步本身就會出現在 plan 裡、被 review 攔住。`skip_final_snapshot = false` 確保即使確實要刪，也會先拍一份最終快照。兩者搭配是正式資料庫的硬性下限。

該在 review 攔下的訊號是：正式環境的 stateful 資源若 `backup_retention_period` 為 0 或 `deletion_protection` 為 false，代表狀態保護沒有寫進程式碼。把這些屬性視為正式資料庫的預設值，而非可調的偏好。

S3 bucket 的保護同理但機制不同。versioning 讓覆寫或刪除的物件可以回到先前版本；MFA delete 要求刪除前提供第二因素驗證；lifecycle rule 控制舊版本的保留時間 — 這三者分別對應「可還原」「防誤刪」「控成本」三個職責，見[儲存（S3）](/infra/05-core-services/storage-s3/)。

### 跨 region 災難復原的邊界

multi-AZ 解的是可用區級故障 — 單一資料中心出問題時，同 region 的另一個可用區接手。跨 region 的災難復原（cross-region read replica、S3 cross-region replication、Route 53 failover routing）屬於更高級的可用性投資，解的是整個 region 不可用的極端情境。它的成本與複雜度顯著上升：跨 region 複寫有延遲、failover routing 需要健康檢查與 DNS TTL 配合、兩個 region 的 infra 要各自維護。多數服務在單 region 的 multi-AZ + 備份做完之後再評估是否需要跨 region，依據是業務的 RTO（Recovery Time Objective）對 region 級故障的容忍度。

跨 region 的 infra 投資在 B2B SaaS 的合約義務下更容易成立。[Genesys 的客服平台跨 15 個 region 用 DynamoDB 達成 99.999% 可用性](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)——年停機只有 5 分鐘。對 B2B SaaS 來說，客戶服務中斷等於客戶的終端使用者打不通電話，可用性是合約義務而非行銷敘述。infra 層的判斷依據是：multi-AZ 不夠用（業務需要跨 region failover）的情況通常由合約 SLA 驅動，而非技術判斷驅動。

## stateful 與 stateless 的操作差異

stateful 與 stateless 資源的根本差別在重建代價。這個差別傳導到三個操作後果，每一個都影響日常的 PR review 與 apply 流程。

### 刪除保護的必要性

stateless 資源（ECS service、ALB、無狀態運算）重建只是換一組新實例，幾分鐘內恢復、沒有資料損失，所以它們可以被頻繁地 destroy 與 recreate — 這是 IaC 最擅長的對象。stateful 資源重建意味著資料遺失或漫長的還原，代價可能是數小時的停機與不可逆的損失。開啟 deletion protection 讓「不小心 destroy」需要先顯式關閉保護這一步，多一道人為確認。

### drift 容忍度

stateless 資源的 drift 可以靠重建抹平 — apply 一次就回到程式碼的狀態，副作用只是新實例的短暫滾動更新。stateful 資源的 drift 要謹慎處理，因為 IaC 的「修正回程式碼狀態」動作可能觸發重啟甚至重建。

一個常見的情境：某人手動改了 RDS 的 parameter group，Terraform plan 顯示要把它改回程式碼的版本。這個改回動作是 `update in-place`（改設定、不重建）還是 `replace`（先刪後建），取決於哪個參數被改了 — 某些 parameter 的修改需要重啟，而某些需要整個 instance 重建。判讀方式是先跑 plan、看 drift 修正的結果，`update in-place` 通常安全（可能觸發重啟），`replace` 對資料庫意味著先刪後建，在 prod 上需要額外的確認。

### 變更審查強度

改動 stateful 資源的 plan 輸出要逐行看，特別警惕任何顯示為 `replace`（`-/+`）或標記 `forces replacement` 的項目。某些欄位的改動看似無害但會觸發 replace：

| 欄位                        | 預期行為     | 實際行為                    |
| --------------------------- | ------------ | --------------------------- |
| RDS `identifier` 改名       | 改個名字而已 | forces replacement          |
| RDS `engine_version` 大版本 | 升級引擎版本 | 可能 replace 或 in-place    |
| RDS `storage_type` 變更     | 換儲存類型   | 部分組合 forces replacement |
| S3 bucket `bucket` 改名     | 改個名字而已 | forces replacement          |

Review 時看到 stateful 資源出現 `forces replacement`，在 prod 路徑上幾乎都該先暫停、確認回退路徑（手動快照是否已拍）再決定是否繼續。常見做法是把這個差別寫進流程：stateful 資源的變更走更嚴格的 PR review 與分階段套用（先在 dev apply 驗證、確認是 in-place 後再推 prod），自動化護欄在[模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)展開。

## 服務之間的依賴怎麼表達

服務間依賴用 output 與 data source 表達，讓引用關係成為程式碼裡可追蹤的邊，而非靠人記憶的隱性約定。引用方式的選擇直接影響 state 的大小與爆炸半徑。

### 同 state 內的引用

同一個 state 內，直接引用資源屬性即可建立依賴。運算資源引用資料庫的端點，IaC 自動推導出「資料庫先於運算」的邊，也讓端點變更時上層自動取得新值：

```hcl
resource "aws_ecs_task_definition" "api" {
  container_definitions = jsonencode([{
    environment = [
      { name = "DB_HOST", value = aws_db_instance.primary.endpoint }
    ]
  }])
}
```

同 state 引用的好處是依賴圖最完整 — apply 一次就把所有引用解析到正確的值。代價是 state 越大、單次 apply 的爆炸半徑越大。一份包含網路、資料庫、運算、LB 的 state，一次 apply 失敗可能讓所有資源處於半完成狀態。

### 跨 state 的 data source

跨 state（例如網路地基與核心服務分屬不同 Terraform state，呼應[模組四：環境分離與模組化](/infra/04-environment-separation/)的拆分）時，下游用 data source 唯讀地讀取上游已建立的資源：

```hcl
data "aws_vpc" "main" {
  tags = { Name = "app-${var.env}" }
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
  tags = { tier = "private" }
}
```

下游查詢上游的 VPC 與 subnet，取得 ID 來放置自己的資源，而不複製貼上硬編碼的值。

### 同 state vs 跨 state 的取捨

兩種方式的取捨在耦合與隔離之間：

| 維度       | 同 state 引用               | 跨 state data source                    |
| ---------- | --------------------------- | --------------------------------------- |
| 依賴圖     | 完整、自動推導              | 跨 state 邊界，需約定上游先 apply       |
| 爆炸半徑   | state 越大、單次 apply 越大 | 各 state 獨立、爆炸半徑小               |
| 適合場景   | 少量緊密耦合的資源          | 地基層與服務層分離                      |
| drift 風險 | 低（引用自動追蹤）          | 中（上游重建後 data source 可能查不到） |

用 grep 搜一遍核心服務的 HCL：如果出現大量寫死的 subnet ID 或 VPC ID，代表該用 data source 而沒用。這些硬編碼是日後上游重建時 drift 與 broken reference 的來源。把它們換成 data source，依賴關係才會在程式碼裡顯性化、可被工具與 review 看見。

data source 查詢的可靠性取決於查詢條件的穩定度。用 `tags` 查比用 `Name` 查更穩 — tag 是自己定義的、可控的值，而某些資源的 Name 可能在重建時改變。用 `terraform_remote_state` data source 直接讀上游的 state output 是最精確的方式，但它把兩份 state 的 backend 設定耦合在一起，上游搬 state 時下游也要跟著改。在團隊規模小、state 拆分不多的階段，`terraform_remote_state` 的耦合代價通常可接受；團隊變大後，用 tag-based data source 或 SSM Parameter Store 當中間層，能讓上下游各自獨立演進。

## 跨分類引用

- → [模組三：網路地基](/infra/03-network-foundation/)：核心服務落在哪些 subnet、security group 怎麼引用
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：跨 state 的拆分策略
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：stateful 變更的自動化護欄
- → [運維 模組六：高可用](/operations/06-high-availability/)：multi-AZ 這個 infra 能力層之上的冗餘設計、failover 與 DR 策略
