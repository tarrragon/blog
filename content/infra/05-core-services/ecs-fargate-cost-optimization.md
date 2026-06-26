---
title: "ECS Fargate 成本分析與優化"
date: 2026-06-26
description: "Fargate 的計價模型、與 EC2 launch type 的成本交叉點、Spot 與 Savings Plans 的折扣機制、task 規格的 rightsizing 方法，以及何時該切回 EC2"
weight: 7
tags: ["infra", "ecs", "fargate", "cost", "optimization"]
---

Fargate 把運算的維運面外包給 AWS — 不需要管 EC2 instance、不需要管 AMI 更新、不需要管 capacity provider 的擴縮邏輯。這份簡化的代價是單位成本較高。當服務規模小或流量不穩定時，Fargate 的簡化值回票價；當服務規模穩定且持續運行時，EC2 launch type 的單位成本優勢會累積到值得切換的量級。本篇的目標是讓讀者能判斷自己的服務在成本曲線的哪個位置、以及有哪些槓桿可以調。

## Fargate 計價模型

Fargate 按 task 的 vCPU 時數和記憶體時數分別計費，從 task 啟動（pull image 完成、進入 RUNNING）到停止。計費的最小粒度是一分鐘，不足一分鐘按一分鐘算。

以 ap-northeast-1（東京）為例的單價（截至撰寫時的量級參考，實際以 AWS 定價頁為準）：

| 資源     | 單價（每小時） |
| -------- | -------------- |
| 1 vCPU   | ~$0.05056      |
| 1 GB RAM | ~$0.00553      |

一個 1 vCPU / 2 GB 的 task 持續運行一個月（730 小時）的費用約為 $0.05056 × 730 + $0.00553 × 2 × 730 ≈ $44.97。這個數字是所有後續比較的基線。

Fargate 的計費粒度還有一個常被忽略的面向：task 規格只能從 AWS 預定義的 vCPU/memory 組合中選。如果應用只需要 0.3 vCPU / 512 MB，最小可選的配置是 0.25 vCPU / 0.5 GB，但如果需要 0.3 vCPU / 1 GB，就得選 0.5 vCPU / 1 GB — 多付了 0.2 vCPU 的費用。這個「階梯式浪費」在小規格 task 上比例最高。

## Fargate vs EC2 launch type 的成本比較

EC2 launch type 的成本結構不同：付的是 EC2 instance 的時數（不管上面跑幾個 task），加上 ECS 本身不收費。省的是 Fargate 的 markup，多的是 instance 管理（AMI 更新、capacity provider 設定、instance 閒置時仍計費）。

| 場景                               | Fargate 月費      | EC2（t3.medium）月費          | 差異  |
| ---------------------------------- | ----------------- | ----------------------------- | ----- |
| 1 task, 1 vCPU / 2 GB, 持續        | ~$45              | ~$30（共享 instance）         | +50%  |
| 5 tasks, 各 0.5 vCPU / 1 GB        | ~$113             | ~$30（1 台 t3.medium 裝得下） | +277% |
| 20 tasks, 各 1 vCPU / 2 GB         | ~$900             | ~$240（4 台 t3.xlarge）       | +275% |
| 流量波動大，尖峰 10 tasks / 離峰 1 | ~$180（加權平均） | ~$150（需預留尖峰容量）       | +20%  |

幾個判讀要點：

- task 數量少且持續運行時，Fargate 的溢價比例最高（+50% 到 +277%），但絕對金額小（$15-$80/月的差距），不值得為此承擔 instance 管理的維運負擔
- task 數量多且持續運行時，EC2 的絕對節省量開始可觀（$660/月），這時候切換的維運成本有回報
- 流量波動大時，Fargate 的優勢是按需計費 — 離峰時 task 數降下來就停止計費，EC2 instance 閒置時仍然計費。波動越大，Fargate 的成本效益越接近或超過 EC2

## Fargate Spot

Fargate Spot 使用 AWS 的閒置容量，價格約為 on-demand 的 30%（折扣幅度 ~70%），代價是 AWS 可以隨時回收容量、task 會收到 SIGTERM 後被終止。

適用條件：task 能在 120 秒內優雅停止、應用有重試機制或上游有 load balancer 自動移除不健康的 target。批次處理、背景 worker、可中斷的佇列消費者是典型的 Spot 候選。對外直接服務的 API 通常混合部署 — 基線容量用 on-demand、彈性擴張部分用 Spot。

```hcl
resource "aws_ecs_service" "api" {
  # ...

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 2  # 至少 2 個 on-demand task 保底
  }

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 3  # 擴張時 3/4 的 task 用 Spot
  }
}
```

`base = 2` 確保至少有兩個 on-demand task 在線（不會被回收），`weight` 比例讓後續擴張的 task 優先使用 Spot。中斷發生時 ECS 會自動在 on-demand 上補充，但補充需要時間（task 啟動 + health check 通過），這段期間服務容量會短暫下降。

## Compute Savings Plans

Compute Savings Plans 是對 Fargate（和 EC2、Lambda）的預付承諾折扣：承諾每小時固定消費 X 美元的運算量，換取 1 年或 3 年的折扣（1 年約 -20%、3 年約 -40%，視具體方案）。

關鍵判斷：承諾量（$/hr）設在實際用量的多少比例。保守做法是設在過去 3 個月最低用量的 80% — 這部分幾乎確定會用到，享受折扣；超過承諾量的部分自動按 on-demand 計費，不會浪費。

```bash
# 查過去 90 天的 Fargate 用量趨勢
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-06-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Elastic Container Service"]}}'
```

Savings Plans 跟 Fargate Spot 可以疊加：Spot task 的費用也能用 Savings Plans 折抵。先用 Savings Plans 降低基線成本，再用 Spot 降低彈性擴張的成本，兩層折扣疊起來可以把 Fargate 的實際單價壓到接近 EC2 on-demand。

## Task 規格的 rightsizing

Fargate task 的 vCPU 和記憶體配置如果設得過大，多出來的資源每小時都在計費。rightsizing 的目標是讓 task 規格貼合實際使用量，但留足安全餘裕。

### 量測實際使用量

開啟 CloudWatch Container Insights 後，每個 task 的 CPU 和記憶體使用量會自動上報。觀察 7-14 天的 p95 值：

```bash
# 查 ECS service 過去 7 天的 CPU p95
aws cloudwatch get-metric-statistics \
  --namespace ECS/ContainerInsights \
  --metric-name CpuUtilized \
  --dimensions Name=ServiceName,Value=api Name=ClusterName,Value=prod \
  --start-time 2026-06-19T00:00:00Z \
  --end-time 2026-06-26T00:00:00Z \
  --period 3600 \
  --statistics p95
```

### 判斷調整方向

| p95 使用率   | 判斷                                | 動作                       |
| ------------ | ----------------------------------- | -------------------------- |
| CPU < 30%    | 過度配置，浪費明顯                  | 降一級 vCPU                |
| CPU 30-70%   | 合理範圍，有足夠餘裕應對尖峰        | 維持                       |
| CPU > 80%    | 餘裕不足，尖峰時可能觸發 throttling | 升一級 vCPU 或增加 task 數 |
| Memory < 40% | 過度配置                            | 降一級 memory              |
| Memory > 80% | OOM kill 風險                       | 升一級 memory              |

調整後觀察 3-5 天確認沒有效能退化再進入下一輪。每次只調一個維度（CPU 或 memory），避免同時改兩個變數無法歸因。

### Fargate 可選的規格組合

Fargate 的 vCPU 和 memory 不能任意搭配。常用的組合：

| vCPU | 可選 Memory 範圍             | 典型用途               |
| ---- | ---------------------------- | ---------------------- |
| 0.25 | 0.5 / 1 / 2 GB               | 輕量 sidecar、cron job |
| 0.5  | 1 / 2 / 3 / 4 GB             | 小型 API、worker       |
| 1    | 2 / 3 / 4 / 5 / 6 / 7 / 8 GB | 標準 API、中型 worker  |
| 2    | 4 ~ 16 GB                    | 高負載 API、批次處理   |
| 4    | 8 ~ 30 GB                    | 資料處理、ML inference |

選的時候從最小的「能跑」組合開始，用 Container Insights 量測後再調。常見的浪費是把所有 task 都設成 1 vCPU / 2 GB — 一個只用 0.1 vCPU / 256 MB 的 sidecar 也配了同樣的規格。

## 何時從 Fargate 切到 EC2

切換的判斷不只看成本差額，還要看維運能力。EC2 launch type 需要管理：AMI 更新（安全 patch）、instance draining（rolling update 時把 task 遷走再關 instance）、capacity provider 的擴縮邏輯、instance 的 security group 與 IAM role。

| 判斷維度     | 留在 Fargate        | 切到 EC2                             |
| ------------ | ------------------- | ------------------------------------ |
| 月費差額     | < $200              | > $500 且持續 3 個月                 |
| 團隊維運能力 | 沒有專人管 instance | 有平台工程師或 DevOps                |
| 流量型態     | 波動大、有明顯離峰  | 穩定、24/7 持續運行                  |
| GPU 需求     | 不需要              | 需要（Fargate 不支援 GPU）           |
| 啟動速度     | 可接受 cold start   | 需要 <1s 啟動（EC2 instance 已在線） |

混合部署是常見的中間路線：基線容量用 EC2（成本低、啟動快），尖峰彈性用 Fargate Spot（按需、不需預留）。這需要同時維護兩種 capacity provider，複雜度較高。

## 成本監控

把 ECS 的成本歸因到服務層級需要兩個機制：task 層的 tag propagation 和 Cost Explorer 的 tag 維度。

```hcl
resource "aws_ecs_service" "api" {
  # ...
  propagate_tags = "SERVICE"

  tags = {
    service     = "payment-api"
    env         = "prod"
    cost-center = "cc-payments"
  }
}
```

`propagate_tags = "SERVICE"` 讓 service 的 tag 自動傳播到每個 task，Cost Explorer 就能按 `service` 或 `cost-center` 維度拆分 Fargate 費用。這跟[模組八：治理好習慣](/infra/08-governance-habits/)的 tagging 規範對齊 — tag 是成本可見性的地基。

定期（月初或月中）檢查 Cost Explorer 的 Fargate 費用趨勢：

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-06-01,End=2026-06-26 \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --group-by Type=TAG,Key=service \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Elastic Container Service"]}}'
```

費用突然跳升時，先看是 task 數增加（auto-scaling 觸發）還是單價變化（Savings Plans 過期或 Spot 中斷後自動回補為 on-demand）。這兩者的處理方式不同：前者檢查 scaling policy、後者檢查 Savings Plans 到期日和 Spot 回收頻率。

## 跨分類引用

- → [運算平台上 IaC](/infra/05-core-services/compute-ecs-eks/)：ECS vs EKS 選型、Fargate 的定位
- → [模組八：治理好習慣](/infra/08-governance-habits/)：tagging 與成本可見性的地基
- → [devops 模組八：成本管理](/devops/08-cost-management/)：運行期的 RI / Spot / rightsizing 策略
