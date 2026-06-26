---
title: "模組五：核心服務上 IaC"
date: 2026-06-26
description: "資料庫、運算、儲存、load balancer 怎麼寫進基礎設施程式碼，以及上線順序"
weight: 5
tags: ["infra", "iac", "rds", "compute", "storage"]
---

地基就緒後，依「地基 → 上層」的順序把實際承載業務的服務寫進 IaC。前四個模組建立的身分、網路與環境分離是底層平面，這一層在它們之上描述資料庫、運算、儲存與入口 — 業務流量真正落地的地方。順序與依賴的表達方式決定了這層能不能被乾淨地重建、拆除與演進。

## 上核心服務的順序

核心服務的部署順序由依賴方向決定：被依賴的先建，依賴別人的後建。網路與身分是幾乎所有上層服務的共同前置 — 資料庫要放進私有 subnet、運算要套用 IAM role 才能讀 S3、load balancer 要掛在公開 subnet 並引用 security group。這些底層平面若還沒成形，上層資源會在 apply 時因為找不到 subnet ID 或 role ARN 而失敗，或更糟，建在預設 VPC 裡繞過了所有隔離設計。

把順序交給 IaC 工具的依賴圖自動推導，比人工排序可靠。當運算資源的定義引用了 subnet 與 security group 的資源屬性，Terraform 會解析出「subnet 先於運算」的邊，apply 時自動排程。人工維護一份「先做 A 再做 B」的清單會隨資源增加而失準，依賴圖則隨程式碼本身演進。

順序失控的早期徵兆是：某個上層資源的定義裡寫了一串 hardcode 的 subnet ID 或 VPC ID，代表它沒有透過依賴圖連到底層平面。底層一旦重建、ID 改變，上層不會自動跟上，state 與雲端現實之間的不一致（即 drift）就此產生。把硬編碼的 ID 換成對底層資源屬性或 data source 的引用，順序才會回到工具掌控之內。

## 各類服務怎麼描述

四類核心服務承擔不同責任，IaC 描述它們時關注的屬性也不同。共通原則是：描述服務的「身分與接線」，而非把每個執行期參數都塞進程式碼。

**資料庫（RDS）** 是這層裡最需要謹慎描述的資源，因為它持有無法重建的狀態。IaC 定義它的 instance class、引擎版本、所在的 subnet group（決定它落在哪些私有 subnet）、套用的 parameter group 與 security group。連線端點不要硬編碼，改用資源 output 暴露給上層運算引用。

```hcl
resource "aws_db_instance" "primary" {
  identifier             = "app-prod-primary"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = "db.r6g.large"
  db_subnet_group_name   = aws_db_subnet_group.private.name
  vpc_security_group_ids = [aws_security_group.db.id]
}
```

**運算（ECS / EKS）** 描述的是業務程式碼的執行載體。重點屬性是它跑在哪些 subnet、套用哪個 task / pod 的 IAM role、掛到哪個 load balancer 的 target group，以及與容器映像版本解耦 — 映像 tag 通常由 CI/CD 在部署期注入，不寫死在 infra 程式碼裡。這層只描述「運算容量與接線」，實際跑什麼版本由部署流程決定，這個邊界讓 infra 變更與應用發布各走各的節奏。

ECS 與 EKS 在這裡被併寫，但兩者的維運模型不同、存在實際選型：ECS 是受管的容器編排，控制平面由雲商代管、心智負擔低，接線概念貼近 AWS 原生資源；EKS 是受管的 Kubernetes，換來跨雲可攜的生態與更細的編排控制，代價是要承擔 Kubernetes 自身的運維面（升級、附加元件、RBAC）。團隊已有 Kubernetes 能力或需要其生態時 EKS 的成本才划算，否則 ECS 的低負擔通常是預設起點。IaC 描述的接線骨架相近，差異主要落在編排層的資源類型。

運算到資料庫之間還有一段常被略過的接線：連線管理。無狀態運算水平擴張時，每個實例各自開連線，容易把資料庫的連線數打滿 — 出現「擴運算反而拖垮 DB」的訊號時，要引入連線池或受管的連線代理（如 RDS Proxy），把連線收斂後再進資料庫，這層也可寫進 IaC 並輸出端點給運算引用。當讀流量遠大於寫、且能容忍副本的複寫延遲時，read replica 是把讀請求導離主庫的下一步，運算端依讀寫分流引用不同端點。

**儲存（S3）** 描述的是 bucket 的存在、命名、加密設定、版本控制與存取政策。bucket 本身幾乎沒有重建代價意義上的狀態問題 — 困難在它「裝的東西」。空 bucket 可隨時重建，裝了正式資料的 bucket 與 RDS 一樣不可隨意 destroy。描述時把加密、public access block、生命週期規則寫進去，這些是安全與成本的預設防線。

**入口（ALB）** 描述流量進入系統的第一站。它定義 listener（監聽哪些 port 與協定）、target group（流量導向哪些運算後端）、health check 條件與 TLS 憑證。ALB 本身是 stateless 的 — 重建一個 load balancer 不會遺失資料，但會換掉它的 DNS 名稱，所以對外服務通常在它前面再掛一層穩定的 DNS 記錄。健康檢查的路徑與閾值是這裡最常被忽略的判讀點：閾值太寬鬆會把壞掉的後端留在輪替裡，太嚴格會在部署瞬間誤判健康的新實例。HTTPS listener 引用的 TLS 憑證也屬於這層的接線 — 憑證由 ACM 簽發與自動續期，IaC 用憑證資源描述它（涵蓋網域與驗證方式），再把憑證 ARN 接到 listener 上，讓「憑證存在、續期、掛載」整條鏈都進版本控制，而非在 Console 手動上傳一份會過期沒人盯的憑證。

## stateful 資源的特殊處理

stateful 資源的 IaC 描述要把「保護狀態」當成第一類需求，而非事後補上的選項。RDS 是典型 — 它的高可用、備份與還原能力全都能、也應該用程式碼描述，這樣保護策略本身就進入版本控制與審查流程，而非散落在某人手動點過的 Console 設定裡。

multi-AZ 用一個布林屬性開啟，背後是 RDS 在另一個可用區維護同步副本。它解的是可用性：主庫故障時 failover 到 standby，但這個切換有秒級到一兩分鐘的窗口而非零停機，期間連線會中斷重連。要先界定它的邊界，才不會把它當成超出職責的工具。standby 副本是熱備不可讀，所以 multi-AZ 不提供讀取擴展 — 要分攤讀流量得另開 read replica 或改用 multi-AZ cluster 形態。它也不防邏輯損壞：誤刪一張表或一筆錯誤的批次更新會同步複製到 standby，這類風險由 backup 與時間點還原（PITR）負責，與 multi-AZ 的可用性職責正交，兩者要分別配置。

backup 用保留天數與備份視窗描述，RDS 依此每日自動快照並保留交易日誌以支援還原到任意時間點。自動備份的保留上限是 35 天，更長的留存要靠手動快照或匯出到 S3 自行管理。下方 `backup_retention_period` 取 14 是以 RPO 與合規要求反推的結果 — 一般營運場景 14 天足以涵蓋「發現問題到決定還原」的時間差，受監理或需要更長追溯窗口的服務則往 30 天甚至接上手動快照保險。手動快照用獨立資源描述，常見於重大變更前的保險點。

```hcl
resource "aws_db_instance" "primary" {
  multi_az                   = true
  backup_retention_period    = 14
  backup_window              = "03:00-04:00"
  deletion_protection        = true
  skip_final_snapshot        = false
  final_snapshot_identifier  = "app-prod-final"
}
```

該在 review 攔下的訊號是：正式環境的 stateful 資源若 `backup_retention_period` 為 0 或 `deletion_protection` 為 false，代表狀態保護沒有寫進程式碼。把這些屬性視為正式資料庫的硬性下限，而非可調的偏好。

## stateful 與 stateless 的差異怎麼影響操作

stateful 與 stateless 資源的根本差別在重建代價，這個差別會傳導到刪除保護與 drift 風險的處理方式。stateless 資源（ECS service、ALB、無狀態運算）重建只是換一組新實例，幾分鐘內恢復、沒有資料損失，所以它們可以被頻繁地 destroy 與 recreate，是 IaC 最擅長的對象。

stateful 資源（RDS、裝了資料的 S3、持久化 volume）重建意味著資料遺失或漫長的還原，代價可能是數小時的停機與不可逆的損失。這個差別帶來三個操作後果。第一，刪除保護是必要的：stateful 資源開啟 deletion protection，讓「不小心 destroy」需要先顯式關閉保護這一步，多一道人為確認。第二，state drift 的容忍度不同：stateless 資源的 drift 可以靠重建抹平，stateful 資源的 drift（例如有人手動改了 parameter group）要謹慎處理，因為 IaC 的「修正回程式碼狀態」動作可能觸發重啟或重建。第三，變更的審查強度不同：改動 stateful 資源的 plan 輸出要逐行看，特別警惕任何顯示為 `replace`（先刪後建）而非 `update in-place` 的項目 — 對資料庫而言這通常代表資料會被丟棄。

實務上把這個差別寫進流程：stateful 資源的變更走更嚴格的 PR review 與分階段套用，這部分的自動化護欄在「模組七：infra 走 PR 流程與自動化護欄」展開。

## 服務之間的依賴怎麼表達

服務間依賴用 output 與 data source 表達，讓引用關係成為程式碼裡可追蹤的邊，而非靠人記憶的隱性約定。同一個 state 內，直接引用資源屬性即可建立依賴 — 運算資源引用資料庫的端點 output，IaC 自動推導出「資料庫先於運算」，也讓端點變更時上層自動取得新值。

```hcl
output "db_endpoint" {
  value = aws_db_instance.primary.endpoint
}
```

跨 state（例如網路地基與核心服務分屬不同 Terraform state，呼應「模組四：環境分離與模組化」的拆分）時，下游用 data source 唯讀地讀取上游已建立的資源。下游查詢上游的 VPC 與 subnet，取得 ID 來放置自己的資源，而不複製貼上硬編碼的值。

```hcl
data "aws_vpc" "main" {
  tags = { Name = "app-prod" }
}
```

兩種方式的取捨在耦合與隔離之間。同 state 引用最直接、依賴圖最完整，但 state 越大、單次 apply 的爆炸半徑越大。跨 state 的 data source 把爆炸半徑切小、讓網路地基能獨立演進，代價是依賴關係跨越了 state 邊界、需要約定上游一定先 apply。判讀訊號是：若一份核心服務程式碼裡出現大量寫死的 ID，通常代表該用 data source 而沒用 — 這是日後上游重建時 drift 與 broken reference 的來源。把硬編碼的引用換成 data source，依賴關係才會在程式碼裡顯性化、可被工具與 review 看見。

服務都接上後，下一個關注點是讓它們可被觀測 — log 與 metric 與服務同生命週期建立，這部分在「模組六：可觀測性與 log 同生命週期」展開。

## 章節文章

| 文章                                                                                         | 主題                                                                                     |
| -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| [部署順序與資料庫上 IaC](/infra/05-core-services/deployment-order-database/)                 | 依賴圖決定部署順序，RDS 接線、連線管理、read replica 與端點暴露                          |
| [運算平台上 IaC — ECS 與 EKS](/infra/05-core-services/compute-ecs-eks/)                      | ECS 與 EKS 選型、task definition 與映像版本解耦、IAM task role、auto-scaling             |
| [儲存上 IaC — S3 bucket 的安全與生命週期](/infra/05-core-services/storage-s3/)               | 加密、版本控制、公開存取封鎖、生命週期規則、bucket policy 與事件通知                     |
| [入口上 IaC — ALB、TLS 與健康檢查](/infra/05-core-services/loadbalancer-alb/)                | listener、target group、健康檢查閾值設計、ACM 憑證與 DNS 別名                            |
| [Stateful 資源保護與跨服務依賴表達](/infra/05-core-services/stateful-protection-dependency/) | multi-AZ 邊界、備份保留、刪除保護、stateful vs stateless 操作差異、output 與 data source |

## 跨分類引用

- → [backend 模組五：部署平台](/backend/05-deployment-platform/)：PaaS / container 平台跑在這層之上
- → [devops 實務指南](/devops/)：這些服務上線後的運行期維運
