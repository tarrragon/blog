---
title: "部署順序與資料庫上 IaC"
date: 2026-06-26
description: "核心服務的依賴圖決定部署順序，資料庫作為第一批上層服務需要最謹慎的 IaC 描述 — 涵蓋 RDS 接線、連線管理、read replica 與端點暴露"
weight: 1
tags: ["infra", "iac", "rds", "database"]
---

地基就緒後，依「地基 → 上層」的順序把實際承載業務的服務寫進 IaC。[身分（IAM）](/infra/02-identity-credentials/)、[網路（VPC / subnet）](/infra/03-network-foundation/)與[環境分離](/infra/04-environment-separation/)構成底層平面，這一層在它們之上描述資料庫、運算、儲存與入口 — 業務流量真正落地的地方。順序與依賴的表達方式決定了這層能不能被乾淨地重建、拆除與演進。共通原則是：描述服務的「身分與接線」，而非把每個執行期參數都塞進程式碼。

本篇先確立依賴圖怎麼驅動部署順序，再展開核心服務裡最需要謹慎描述的一類 — 資料庫。資料庫持有無法重建的狀態，它的 IaC 描述比其他 stateless 資源多出保護策略、連線管理與讀寫分流三個維度。

## 核心服務的部署順序

核心服務的部署順序由依賴方向決定：被依賴的先建，依賴別人的後建。網路與身分是幾乎所有上層服務的共同前置 — 資料庫要放進私有 subnet、運算要套用 IAM role 才能讀 S3、load balancer 要掛在公開 subnet 並引用 security group。這些底層平面若還沒成形，上層資源會在 apply 時因為找不到 subnet ID 或 role ARN 而失敗，或更糟，建在預設 VPC 裡繞過了所有隔離設計。

把順序交給 IaC 工具的依賴圖自動推導，比人工排序可靠。當運算資源的定義引用了 subnet 與 security group 的資源屬性，Terraform 會解析出「subnet 先於運算」的邊，apply 時自動排程。人工維護一份「先做 A 再做 B」的清單會隨資源增加而失準，依賴圖則隨程式碼本身演進。

### 四層依賴結構

依賴圖的典型展開順序呈現四層結構：

| 層次 | 資源                                  | 依賴來源                                |
| ---- | ------------------------------------- | --------------------------------------- |
| 1    | VPC、subnet、security group、IAM role | 無（地基層，由模組二到四建立）          |
| 2    | RDS、ElastiCache、S3 bucket           | 引用 subnet group、security group       |
| 3    | ECS service / EKS workload、RDS Proxy | 引用 subnet、IAM role、DB 端點          |
| 4    | ALB、listener、target group、ACM 憑證 | 引用 public subnet、security group、ECS |

這四層不需要手動編排。只要程式碼裡的引用關係正確，Terraform 就會自動按這個順序 apply。當 plan 輸出的順序看起來不合直覺 — 例如 ALB 先於 ECS — 通常代表某個引用斷了、兩者之間沒有依賴邊。

### 順序失控的徵兆

順序失控的早期徵兆是：某個上層資源的定義裡寫了一串 hardcode 的 subnet ID 或 VPC ID。

```hcl
# 硬編碼 ID — 依賴圖斷裂，底層重建時上層不會跟上
resource "aws_db_subnet_group" "private" {
  subnet_ids = ["subnet-0abc123", "subnet-0def456"]
}
```

這段 code 跟底層的 subnet 資源沒有引用關係。底層一旦重建、ID 改變，上層不會自動跟上，state 與雲端現實之間的不一致（即 drift）就此產生。修法是把硬編碼的 ID 換成對底層資源屬性的引用：

```hcl
# 引用資源屬性 — 依賴圖自動推導，底層重建時上層自動取得新 ID
resource "aws_db_subnet_group" "private" {
  subnet_ids = [for s in aws_subnet.private : s.id]
}
```

跨 state 的情境（網路地基與核心服務分屬不同 state）則用 data source 取代直接引用 — 這個取捨在[服務依賴與跨 state 引用](/infra/05-core-services/stateful-protection-dependency/)展開。

### 隱性依賴與 depends_on

自動推導涵蓋的是「引用屬性時產生的邊」。少數情況下兩個資源之間有依賴卻沒有屬性引用 — 例如一個 IAM policy attachment 必須在某個 role 被 ECS task 使用之前完成，但 task 引用的是 role ARN 而非 attachment 的輸出。這時用 `depends_on` 顯式宣告邊：

```hcl
resource "aws_ecs_service" "api" {
  # ...
  depends_on = [aws_iam_role_policy_attachment.ecs_task_s3]
}
```

`depends_on` 應該只出現在自動推導覆蓋不了的場景。如果一個 module 裡到處都是 `depends_on`，通常代表引用關係寫得不夠明確，該把隱性依賴改成屬性引用。

## 資料庫（RDS）

資料庫是核心服務裡最需要謹慎描述的資源，因為它持有無法重建的狀態。IaC 定義它的 instance class、引擎版本、所在的 subnet group（決定它落在哪些私有 subnet）、套用的 parameter group 與 security group。連線端點不要硬編碼，改用資源 output 暴露給上層運算引用，這樣端點隨主庫 failover 或重建而改變時，上層引用自動更新。

```hcl
resource "aws_db_instance" "primary" {
  identifier             = "app-${var.env}-primary"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = var.db_instance_class
  allocated_storage      = 100
  storage_encrypted      = true

  db_subnet_group_name   = aws_db_subnet_group.private.name
  vpc_security_group_ids = [aws_security_group.db.id]

  multi_az                  = var.env == "prod" ? true : false
  backup_retention_period   = var.env == "prod" ? 14 : 1
  backup_window             = "03:00-04:00"
  deletion_protection       = var.env == "prod" ? true : false
  skip_final_snapshot       = var.env == "prod" ? false : true
  final_snapshot_identifier = var.env == "prod" ? "app-prod-final-${formatdate("YYYYMMDD", timestamp())}" : null

  tags = { service = "payments" }
}

output "db_endpoint" {
  value = aws_db_instance.primary.endpoint
}
```

### 加密的不可逆性

`storage_encrypted = true` 確保磁碟層級的加密在資源建立時就生效。[RDS](/infra/knowledge-cards/rds/) 不支援事後對既有 instance 開加密 — 漏了只能重建。補救路徑是匯出快照、用加密 KMS key 複製快照成加密版本、再用加密快照還原成新 instance。這個過程需要停機或切換端點，對已經承載流量的 production 資料庫代價很高。prod 的 RDS 若 `storage_encrypted` 為 false，這筆技術債越早處理越便宜。

### parameter group 的角色

parameter group 定義資料庫引擎層級的行為參數（如 `max_connections`、`work_mem`、`log_min_duration_statement`），是 RDS instance 的設定骨架。IaC 描述 parameter group 的好處是讓這些參數進版本控制 — 有人改了 `max_connections` 會出現在 PR diff 裡，而不是某天在 Console 改了沒人知道。

```hcl
resource "aws_db_parameter_group" "postgres16" {
  family = "postgres16"
  name   = "app-${var.env}-pg16"

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }
}
```

修改 parameter group 的某些參數需要重啟 RDS instance（稱為 `apply_method = "pending-reboot"`），修改前要先確認這個參數屬於「立即生效」還是「要重啟」。在 Terraform plan 裡不會明確標示重啟，要靠 AWS 文件交叉比對。

### 連線管理

運算到資料庫之間有一段常被略過的接線：連線管理。無狀態運算水平擴張時，每個實例各自開連線，容易把資料庫的連線數打滿。一個 ECS service 從 5 個 task 擴到 50 個、每個 task 開 10 條連線，就從 50 條跳到 500 條 — 而一台 `db.r6g.large` 的 `max_connections` 預設約在 1600 左右，500 條已經吃掉三分之一。

出現「擴運算反而拖垮 DB」的訊號時，解法是引入連線池或受管的連線代理。RDS Proxy 是 AWS 的受管方案：它在運算與 RDS 之間當一層連線池，把下游的數百條短連線收斂成對 RDS 的少量長連線。在 IaC 裡一併定義，輸出 proxy 端點給運算引用：

```hcl
resource "aws_db_proxy" "app" {
  name                   = "app-${var.env}-proxy"
  engine_family          = "POSTGRESQL"
  role_arn               = aws_iam_role.rds_proxy.arn
  vpc_subnet_ids         = [for s in aws_subnet.private : s.id]
  vpc_security_group_ids = [aws_security_group.db.id]

  auth {
    auth_scheme = "SECRETS"
    secret_arn  = aws_secretsmanager_secret.db_password.arn
  }
}

output "db_proxy_endpoint" {
  value = aws_db_proxy.app.endpoint
}
```

運算端引用 `db_proxy_endpoint` 而非 `db_endpoint`，連線管理就從各 task 自己處理轉成由 proxy 統一收斂。RDS Proxy 同時提供 failover 的連線保持 — 主庫切換到 standby 時，proxy 維護的連線不會全部斷開重建，應用端感受到的是短暫延遲而非連線錯誤。

判讀是否需要 RDS Proxy 的訊號是連線數成長曲線：如果運算的擴縮範圍固定且連線數上限遠低於 `max_connections`，直連即可；如果運算會頻繁擴縮或連線數可能逼近上限，proxy 值得引入。proxy 本身有額外成本（按 vCPU 計費），不是所有環境都划算 — dev 環境通常直連就夠。

### read replica

當讀流量遠大於寫、且能容忍副本的複寫延遲（通常是毫秒到秒級）時，read replica 是把讀請求導離主庫的下一步。replica 在 IaC 裡用獨立資源描述，引用主庫的 identifier：

```hcl
resource "aws_db_instance" "read_replica" {
  identifier             = "app-${var.env}-replica"
  replicate_source_db    = aws_db_instance.primary.identifier
  instance_class         = var.db_replica_class
  vpc_security_group_ids = [aws_security_group.db.id]
}

output "db_replica_endpoint" {
  value = aws_db_instance.read_replica.endpoint
}
```

運算端依讀寫分流引用不同端點 — 寫走 `db_endpoint`（或 `db_proxy_endpoint`），讀走 `db_replica_endpoint`。這個分流邏輯屬於應用層的責任，infra 只負責把端點暴露出來。

read replica 的邊界要講清楚：它緩解讀流量對主庫的壓力，但它不是備份。replica 會同步複製主庫的所有變更 — 包括誤刪的資料。需要還原到某個時間點的保護由 backup retention 與 PITR（point-in-time recovery）提供，這兩者的 IaC 描述在 [stateful 保護策略](/infra/05-core-services/stateful-protection-dependency/)。

### 引擎版本升級的取捨

RDS 引擎版本（`engine_version`）寫進 IaC 後，版本升級就成為一個需要 PR review 的變更。升級分 minor 和 major：minor 升級（16.2 → 16.3）通常向後相容、可在維護視窗自動套用；major 升級（15 → 16）可能有 breaking change，需要先在 dev 環境驗證、備份、排維護窗口。

在 IaC 裡把 `engine_version` 寫死是刻意的選擇 — 它阻止 AWS 在背景自動升級 major 版本，讓版本變更必須走 PR。代價是需要定期檢查是否有 EOL 版本還在用。如果 `engine_version` 指向的版本已經超過 AWS 的支援期限，Terraform apply 會在某天失敗（AWS 會強制升級），這比主動升級更不可控。

資料庫在規模放大後的治理維度也會改變。[Netflix 把分散的 Aurora 叢集整併](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)後成本降了 28%——多個團隊各自開的 RDS instance 加起來的閒置容量遠超一個整併後的叢集。infra 層的教訓是 RDS 的 IaC 描述不只管單一 instance 的設定，長期還要管叢集的分布與合併策略。另一個維度是合規需求驅動的資料落地：[Hard Rock Digital 因為 Wire Act 法規要求資料留在特定州](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)，用 AWS Outposts 在地端跑運算——這類情境下 infra 的 region 與可用區選擇由法規約束驅動，而非純技術決策。

## 跨分類引用

- → [模組三：網路地基](/infra/03-network-foundation/)：資料庫的 subnet group 引用 private subnet
- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：RDS Proxy 的 IAM role 與 secret 存取
- → [模組四：環境分離與模組化](/infra/04-environment-separation/)：prod / dev 用同一個 module、不同參數值
- → [stateful 保護與跨 state 引用](/infra/05-core-services/stateful-protection-dependency/)：backup retention、deletion protection、multi-AZ 的完整討論
- → [運算上 IaC](/infra/05-core-services/compute-ecs-eks/)：運算端怎麼引用資料庫端點
- → [backend 模組一：資料庫](/backend/01-database/)：schema 設計、migration、query 層面的服務端討論
