---
title: "運算平台上 IaC — ECS 與 EKS"
date: 2026-06-26
description: "容器運算平台的 IaC 描述：ECS 與 EKS 選型、task definition 與映像版本解耦、IAM task role 分離、auto-scaling 策略"
weight: 2
tags: ["infra", "iac", "ecs", "eks", "compute"]
---

運算是業務程式碼的執行載體。infra 這層描述的是「運算容量與接線」— 它跑在哪些 subnet、套用哪個 IAM role、掛到哪個 load balancer 的 target group、以及容量怎麼隨負載擴縮。實際跑什麼版本的程式碼由部署流程決定，這個邊界讓 infra 變更與應用發布各走各的節奏 — infra apply 不會因此改動映像，部署 pipeline 不會因此改動 subnet。

核心服務的部署順序由依賴方向決定（被依賴的先建），運算在這個[四層依賴結構](/infra/05-core-services/deployment-order-database/)裡位於第三層：它引用底層的 subnet、security group 與 IAM role，同時被上層的 load balancer target group 引用。所以運算資源的 IaC 定義裡，subnet ID、security group ID、IAM role ARN 都應該是引用而非硬編碼 — 底層重建時上層才會自動跟上。

## ECS vs EKS 選型

ECS 與 EKS 都能跑容器，差異在控制平面的維運模型與生態適配。選型看的是團隊能力與業務需求，而非功能多寡 — 兩者都能達成「容器跑在私有 subnet、用 IAM role 存取資源、掛到 ALB 接收流量」這個基本目標。

| 維度         | ECS                           | EKS                                    |
| ------------ | ----------------------------- | -------------------------------------- |
| 控制平面維運 | AWS 完全代管                  | AWS 代管 API server，附加元件自行管理  |
| 學習曲線     | 低（AWS 原生概念）            | 高（Kubernetes 生態）                  |
| 跨雲可攜     | 低（AWS 專屬）                | 高（Kubernetes 標準）                  |
| IaC 工具鏈   | 全部用 Terraform AWS provider | Terraform 建 cluster，workload 走 Helm |
| 適合場景     | AWS 單雲、團隊無 K8s 經驗     | 已有 K8s 能力或需要其生態時            |

ECS 的控制平面由 AWS 代管，service、task definition、target group 都是 AWS 原生資源，Terraform 的 provider 直接描述，心智負擔低。它的 Fargate 啟動類型更進一步 — 連 EC2 instance 都不用管，只描述 task 要多少 CPU 和記憶體，AWS 負責排程到底層主機。

EKS 的控制平面是受管的 Kubernetes，IaC 描述的是 cluster 本身與 node group，workload（Deployment、Service）則走 Kubernetes manifest 或 Helm chart。這代表 infra 工具鏈跨越了 Terraform 與 Kubernetes 兩套系統 — Terraform 負責 cluster 基礎設施，kubectl / Helm 負責工作負載，兩者的 state 與變更流程是分開的。

團隊已有 Kubernetes 能力或需要其生態（service mesh、自訂排程器、多雲部署、社群的 operator 生態）時，EKS 的複雜度才值得承擔。否則 ECS 的低負擔是預設起點。一個自測方式：團隊選了 EKS 但只用到最基本的 Deployment + Service，沒有碰 service mesh、CRD 或跨雲，那等於承擔了 Kubernetes 的維運成本卻沒用到它的回報——退回 ECS 通常更合理。

### Fargate vs EC2 launch type

ECS 的執行模式再分 EC2 launch type 和 Fargate launch type。EC2 launch type 需要自己管理 EC2 instance 組成的 capacity provider — AMI 更新、instance 擴縮、OS 層安全修補都是團隊的責任。Fargate 由 AWS 代管運算實例，不需要配 capacity provider、不需要管 AMI，進一步降低運維面。

Fargate 的代價是三個面向：單位成本較高（同規格的 vCPU/記憶體比 EC2 貴約 20-40%）、不支援 GPU workload、啟動延遲稍長（cold start 約 30-60 秒，EC2 已有 instance 時近乎即時）。多數 web API 和非 GPU 的背景工作的初始選擇是 Fargate — 省掉的運維時間通常抵得過溢價。流量穩定且需要成本最佳化時再切回 EC2 launch type，屆時增加的是 capacity provider 的設定與 instance 管理。量級參考：一個持續運行 2 vCPU / 4GB 的 Fargate task 月費約 $70，同規格 EC2 t3.medium 約 $30。月費差距在服務數量少時不顯著，當 task 數量超過 10-20 個且流量穩定時，切回 EC2 launch type 的節省量才值得投入切換工程。

後續 HCL 範例以 ECS Fargate 示意，EKS 的接線骨架（subnet、IAM、target group）相近，差異落在編排層的資源類型。

## Task definition：描述容器規格與接線

Task definition 是 ECS 描述「一個工作單元長什麼樣」的宣告：要跑哪個容器映像、給多少 CPU 和記憶體、開哪些 port、用哪個 IAM role、log 送到哪裡。它是運算 IaC 的核心資源。

```hcl
resource "aws_ecs_task_definition" "api" {
  family                   = "api-${var.env}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.api_task.arn

  container_definitions = jsonencode([{
    name  = "api"
    image = "${var.ecr_repo_url}:${var.image_tag}"
    portMappings = [{ containerPort = 8080, protocol = "tcp" }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
}
```

這段定義裡有三個刻意的設計：

**映像版本解耦**：`var.image_tag` 在 infra 的 `tfvars` 裡給一個穩定的預設值（如 `latest` 或某個基線版本），部署管線覆寫這個值推新版本。infra apply 不會因此改動映像、部署 pipeline 不會因此改動 subnet — 兩者的變更頻率與審查強度不同，混在一起會讓快的等慢的。如果每次部署新版本都要改 infra 的 Terraform code 並跑 apply，代表映像版本跟 infra 沒有解耦——應該讓部署管線直接用 `aws ecs update-service` 或修改 task definition 的 image tag，不走 Terraform。

**兩個 IAM role 的分工**：`execution_role_arn` 是 ECS 代理用來拉映像和寫 log 的身分 — 它的權限是 ECS 平台層級的，跟業務邏輯無關。`task_role_arn` 是容器內的應用程式碼在執行期取得的身分 — 它的權限對應業務需求，例如讀寫某個 S3 bucket 或呼叫某個 SQS queue。兩者混在同一個 role 上，就是把平台權限跟業務權限混在一起，違反最小權限（見[模組二：身分與憑證地基](/infra/02-identity-credentials/)）。

```hcl
resource "aws_iam_role" "api_task" {
  name               = "api-task-${var.env}"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "api_task" {
  role   = aws_iam_role.api_task.id
  policy = data.aws_iam_policy_document.api_permissions.json
}

data "aws_iam_policy_document" "api_permissions" {
  statement {
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.uploads.arn}/*"]
  }
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.notifications.arn]
  }
}
```

**Log 接線**：`logConfiguration` 把容器的 stdout/stderr 導向 CloudWatch Logs，log group 名稱引用的是同一份 IaC 裡宣告的資源 — 這正是[模組六：可觀測性與 log](/infra/06-observability-logging/) 說的「監控跟資源同生命週期」。

## ECS service：部署模式與網路接線

ECS service 控制「要跑幾個 task、怎麼部署新版本、掛到哪個 target group」。它是 task definition 的執行實例管理者。

```hcl
resource "aws_ecs_service" "api" {
  name            = "api-${var.env}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [for s in aws_subnet.private : s.id]
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8080
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}
```

`network_configuration` 把 task 放進 private subnet 並套用 security group — 它決定了這些容器在網路拓撲裡的位置（見[模組三：網路地基](/infra/03-network-foundation/)）。`assign_public_ip = false` 讓容器不拿公網 IP，對外流量經由 NAT 出去、入站流量經由 ALB 進來。

`deployment_circuit_breaker` 是 ECS 的內建保護：部署新版本時如果 task 持續啟動失敗（health check 不過、容器 crash），ECS 會自動回滾到上一版。這個行為需要明確開啟、預設是關的 — 關著的話，壞版本的 task 會反覆啟動失敗，新版始終上不來但舊版也不會回來，服務陷入降級狀態。

## 連線管理：運算到資料庫的接線

運算到資料庫之間有一段常被略過的接線：連線管理。無狀態運算水平擴張時，每個 task 各自開連線到 RDS，容易把資料庫的連線數打滿。RDS 的連線上限由 instance class 決定（例如 `db.r6g.large` 約 1000 個連線），而一個跑了 50 個 task 的 ECS service，每個 task 開 20 個連線就到上限了。

出現「擴運算反而拖垮 DB」的訊號時，要引入連線池或受管的連線代理。RDS Proxy 在運算與 RDS 之間代理連線，把運算端的大量短命連線收斂成少量長期連線再進資料庫。它也可以寫進 IaC 並輸出端點給運算引用：

```hcl
resource "aws_db_proxy" "main" {
  name                   = "api-proxy-${var.env}"
  engine_family          = "POSTGRESQL"
  role_arn               = aws_iam_role.rds_proxy.arn
  vpc_subnet_ids         = [for s in aws_subnet.private : s.id]
  vpc_security_group_ids = [aws_security_group.rds_proxy.id]

  auth {
    auth_scheme = "SECRETS"
    secret_arn  = aws_secretsmanager_secret.db_password.arn
  }
}

output "db_endpoint" {
  value = aws_db_proxy.main.endpoint
}
```

運算端的連線字串指向 proxy 端點而非 RDS 端點。proxy 的 security group 允許來自運算 security group 的流量，proxy 到 RDS 的流量則由 proxy 自己的 security group 對 RDS security group 的規則控制 — 安全邊界多了一層但更清晰。

## Auto-scaling：容量隨負載擴縮

ECS service 的 `desired_count` 是靜態的起始容量。要讓容量隨負載動態調整，需要加上 Application Auto Scaling。它的責任是在負載上升時長出更多 task、負載下降時縮回去省錢。

auto-scaling 的核心決策是「用什麼指標觸發擴縮」。常見的指標分兩類：

| 指標類型   | 典型指標                            | 適用情境                         |
| ---------- | ----------------------------------- | -------------------------------- |
| 資源利用率 | CPU utilization、memory utilization | 運算密集型服務，CPU 與負載正相關 |
| 業務吞吐量 | ALB request count per target        | I/O 密集型服務，CPU 低但併發高   |

CPU utilization 是最直覺的指標，但它在 I/O 密集型服務上會失準 — 一個等待外部 API 回應的 task，CPU 很低但已經沒有多餘的能力處理新請求。這時用 ALB 的 request count per target（每個 task 平均處理幾個請求）更能反映真實負載。

```hcl
resource "aws_appautoscaling_target" "api" {
  max_capacity       = var.api_max_count
  min_capacity       = var.api_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "api-cpu-${var.env}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = 60
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
```

`target_value = 60` 表示目標 CPU 平均維持在 60% — 留 40% 的餘裕應對突發。`scale_out_cooldown` 設短（60 秒），讓擴張反應快；`scale_in_cooldown` 設長（300 秒），避免負載短暫下降就立刻縮容、結果下一波流量來了又要重新擴張。

設了 auto-scaling 後要定期看 scaling activity log 確認它在正確的時機擴縮。從來沒觸發過有兩種可能：`min_capacity` 已經高於實際需求（資源浪費），或 target value 設太高（來不及擴）。

`max_capacity` 是成本護欄 — 設一個你能接受的上限，避免異常流量（爬蟲、攻擊、上游重試風暴）把 task 數推到遠超預期的帳單。運行期的成本優化在 [devops 模組八：成本管理](/devops/08-cost-management/) 展開。

規模放大後，auto-scaling 的行為模式會改變。[Pokémon GO 上線時實際流量達預估的 50 倍](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)，這類突發不是 auto-scaling 能事前規劃的——50 倍的 headroom 會讓平日成本不合理。Niantic 的 infra 層前提是 GKE 把容器啟動時間降到秒級，讓 surge 反應成為可能；同時依賴 Google CRE 即時補 node 容量。[Zoom COVID 期間的 30 倍突發](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) 則是結構性成長——日活從 1000 萬升到 3 億後不會回落，容量規劃的 baseline 需要永久重新校準。兩個案例的共同教訓是：auto-scaling 的 `max_capacity` 設定要預留突發空間，但極端突發的處理靠的是平台能力（容器化的快速啟動）和 vendor 支援（managed service 的彈性），不是 IaC 配置能獨立解決的。

多叢集治理是另一個規模維度。[Riot Games 用 246 個 EKS cluster 跨多遊戲多地區](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)，每個遊戲一個獨立叢集（避免跨遊戲互相影響），搭配 Terraform 做 IaC、Karpenter 做 node lifecycle，年省 1000 萬美金。infra 層的教訓是：當運算叢集數量從個位數長到數十甚至數百，叢集本身變成需要 IaC 治理的資源——叢集的建立、版本升級、安全基線都要標準化。[Condé Nast 的 EKS 平台整併](/backend/05-deployment-platform/cases/conde-nast-platform-modernization-eks/)也印證了同樣的模式：多團隊各自維護異質 K8s 叢集會造成安全基線不一致，整併到統一平台後把 kube2iam（有 race condition 風險）換成 IRSA（OIDC federation），消除了 node-level 的 credential 共用。

## 跨分類引用

- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：execution role 與 task role 的最小權限設計
- → [模組三：網路地基](/infra/03-network-foundation/)：運算放在 private subnet、security group 接線
- → [模組六：可觀測性與 log](/infra/06-observability-logging/)：log group 與 task definition 同生命週期
- → [devops 模組八：成本管理](/devops/08-cost-management/)：auto-scaling 的成本護欄與 spot/Fargate Spot 混用
