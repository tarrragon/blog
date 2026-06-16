---
title: "AWS ElastiCache"
date: 2026-05-01
description: "AWS managed Redis / Valkey / Memcached"
weight: 5
tags: ["backend", "cache", "vendor"]
---

AWS ElastiCache 是 AWS managed cache 服務、承擔三個責任：託管 Redis / Valkey / Memcached engine（無需自管 broker）、自動 failover + 跨 AZ 複製、AWS 生態原生整合（IAM / VPC / CloudWatch / KMS）。設計取捨偏向「把運維責任轉給 AWS、付 managed premium 換可預測 SLA」、AWS 生態下的 cache 預設選擇。2024 起 default engine 從 Redis 改為 Valkey（成本約低 20%）。

對「AWS 生態服務需要 cache、不想自管 Redis cluster、跨 AZ 高可用」這條路徑、ElastiCache 是首選。本頁先給最短路徑、再展開日常 cluster 管理跟 engine 選擇、最後進階治理（Serverless、MemoryDB 對照）跟排錯。

## 本章目標

讀完本章後、你應該能：

1. 用 AWS CLI 建立 ElastiCache cluster、選擇 engine（Redis / Valkey / Memcached）
2. 區分 Cluster mode enabled vs disabled 的選用條件
3. 配置 auto failover、cross-AZ replication、snapshot backup
4. 評估 ElastiCache Serverless vs node-based 的成本取捨
5. 區分 ElastiCache 跟 MemoryDB（durable）跟自管 Redis 的定位

## 最短路徑：5 分鐘把 ElastiCache 跑起來

```bash
# 1. 建立 Valkey replication group（cluster mode disabled、單 primary + 1 replica、Multi-AZ）
aws elasticache create-replication-group \
  --replication-group-id demo \
  --replication-group-description "demo cache" \
  --engine valkey \
  --cache-node-type cache.t4g.micro \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --multi-az-enabled

# 2. 取得 primary endpoint（建立需數分鐘、status 變 available 才有 endpoint）
aws elasticache describe-replication-groups \
  --replication-group-id demo \
  --query "ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint.Address" --output text

# 3. 從 VPC 內（EC2 / Lambda）用 redis-cli 連線（ElastiCache 只在 VPC 內可達）
redis-cli -h <primary-endpoint> -p 6379 PING   # → PONG
```

指令依 [AWS ElastiCache CLI 官方文件](https://docs.aws.amazon.com/cli/latest/reference/elasticache/)、最後檢查日 2026-06-16（managed 服務需 AWS 帳號與 VPC、本機無法 docker 驗證、引數以官方為準）。ElastiCache 端點只在 VPC 內可達、不對公網開放。實際 production 需要評估 cluster mode、節點大小、replica 數、AZ 分布。

## 日常操作與決策形狀

### AWS CLI 與 console

子議題：

- CLI 指令對照表（create-cache-cluster / create-replication-group / describe-* / modify-* / delete-*）
- Console 操作流程（VPC subnet group / security group / parameter group）
- Terraform / CloudFormation 範例
- 對應指令範例：`aws elasticache describe-replication-groups --replication-group-id <id>`

### Engine 選擇

子議題：

- **Valkey**（2024+ default）：成本低 20%、OSI 開源、Redis 7.2.4 fork
- **Redis OSS**（legacy support）：仍可選、但 AWS 不推
- **Memcached**：純 cache 場景、無 cluster mode 概念（client-side sharding）
- 選擇判讀：新部署 → Valkey；既有 Redis 遷移 → Valkey（API 相容）；純 cache → Memcached

### Cluster mode enabled vs disabled

子議題：

- **Disabled**：1 primary + N replica（最多 5）、單 shard、上限 ~340GB
- **Enabled**：多 shard（最多 500）、自動 sharding、橫向擴展
- 客戶端要求：Cluster mode enabled 需要 cluster-aware client
- 選擇判讀：< 300GB + 簡單 → disabled；> 300GB 或要 sharding → enabled

### Snapshot 與 backup

子議題：

- Automatic snapshot（保留 1-35 天）
- Manual snapshot（保留永久、可跨 region 複製）
- Restore：從 snapshot 建新 cluster
- 對應指令：`aws elasticache create-snapshot`

## 進階主題（按需閱讀）

### Auto failover 機制

子議題：

- Multi-AZ 部署：primary 失敗、replica 自動晉升
- Failover 時間：~30 秒到幾分鐘（依 client 重連)
- Client 影響：DNS 切到新 primary、client 要 reconnect
- 對應 [2.C6 Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/) 跨 AZ 對照

### ElastiCache Serverless

子議題：

- On-demand 模式：不選 node type、按 ECPU + storage 計費
- 自動 scale：流量增加自動擴
- 適合：流量不可預測、不想規劃容量
- 不適合：成本敏感（serverless premium）、極大 dataset

### 跨 region replication（Global Datastore）

子議題：

- Global Datastore：1 primary region + 多個 secondary region read replica
- 跨 region replication lag < 1 second（業界宣稱）
- 適合 active-passive DR
- 不支援 active-active multi-master

### MemoryDB 對照

子議題：

- ElastiCache：cache、Multi-AZ replica 但仍是 cache 語意（資料可重建）
- MemoryDB：Redis-compatible durable database、multi-AZ transaction log
- MemoryDB cost 2-3x ElastiCache、但提供 source-of-truth 語意
- 選擇判讀：要 source-of-truth Redis API → MemoryDB；cache 用途 → ElastiCache

### Parameter group 與配置

子議題：

- Parameter group：custom maxmemory-policy、timeout、client-output-buffer-limit
- Cluster vs parameter group 的應用範圍
- 對應指令：`aws elasticache modify-cache-parameter-group`

### IAM authentication（Redis 7+）

子議題：

- 從 Redis AUTH password 升級到 IAM-based authentication
- IAM role / user 連 ElastiCache、無需傳 password
- 對應 [security 模組](/backend/07-security-data-protection/)

### Cost 模型

子議題：

- Node type 成本（t4g.micro 到 r7g.16xlarge）
- Reserved Instance（1/3 年承諾、折扣 30-60%）
- Data transfer cost（同 AZ 免費、跨 AZ 收費）
- Snapshot storage cost

## 排錯快速判讀

### Endpoint 連不上

操作原則：先確認 VPC + security group + subnet group 配置正確。

```bash
aws elasticache describe-replication-groups --replication-group-id <id> \
  --query "ReplicationGroups[0].Status"
# 從 VPC 內 EC2 測試連通性
redis-cli -h <primary-endpoint> -p 6379 PING
```

判讀路徑：security group 沒開 6379 → VPC peering 不通 → DNS 解析失敗。

### Failover 過程中 client 持續 error

操作原則：failover 期間 client 重連需要時間、確認 client 有 reconnect 邏輯。

```bash
aws elasticache describe-events --source-identifier <id> --source-type replication-group
# 看 failover 開始 / 完成事件、對照 client 重連時間軸
```

### Replication lag 高

操作原則：cross-AZ replication 通常 ms 級、若 > 1 sec 看 CloudWatch ReplicationLag metric。原因可能是 write throughput 過高、replica node 規格不足。

### Memory pressure / eviction

操作原則：看 CloudWatch DatabaseMemoryUsagePercentage、超 80% 考慮 scale up node type 或調 maxmemory-policy。

### Snapshot 失敗

操作原則：snapshot 過程暫時 fork（Redis）會佔用記憶體、若 memory 已緊張可能失敗。看 CloudWatch BytesUsedForCache。

## 何時改走其他服務

| 需求形狀                        | 改走                                                                                                     |
| ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 需要 source-of-truth Redis API  | AWS MemoryDB（durable Redis-compatible）                                                                 |
| 跨雲                            | 自管 [Redis](/backend/02-cache-redis/vendors/redis/) / [Valkey](/backend/02-cache-redis/vendors/valkey/) |
| 極端 throughput single instance | [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/) self-host                                    |
| Edge / HTTP cache               | CloudFront / Cloudflare Cache（T4 候選）                                                                 |
| 不在 AWS 生態                   | GCP Memorystore / Azure Cache for Redis                                                                  |
| 完全 serverless 計費            | ElastiCache Serverless（同模組內）/ Momento                                                              |

## 不在本頁內的主題

- AWS IAM / VPC / Security Group 完整配置（見 security 模組）
- CloudFormation / Terraform 完整模板
- AWS pricing 詳細計算
- ElastiCache vs Memorystore vs Azure Cache 完整對照

## 案例回寫

### 直接相關案例

| 案例                                                                                               | 對 ElastiCache 的對應                                                                                 |
| -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| [2.C6 Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/)          | EVCache 為 Netflix 自管 Memcached based 全域 cache、對應 ElastiCache for Memcached + Global Datastore |
| [2.C5 Shopify write-through](/backend/02-cache-redis/cases/shopify-write-through-cache-at-scale/)  | Write-through 在 managed cache 的實作、ElastiCache 提供同樣 Redis/Valkey API、無 self-host 維運負擔   |
| [2.C3 Shopify serialization](/backend/02-cache-redis/cases/shopify-cache-serialization-migration/) | Payload 雙軌遷移 client-side 實作、ElastiCache 對應為 engine version upgrade + parameter group 滾動   |

**待補 ElastiCache-specific 案例**：Airbnb / Lyft / Pinterest 等公開的 ElastiCache 規模化案例、re:Invent talks（如 ElastiCache for Valkey 遷移、Serverless 採用、Global Datastore active-passive DR 實作）。

### 跨 vendor 對照

| 案例                                                                                                    | 對 ElastiCache 的對應                                                                                    |
| ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| [2.C9 Cache Stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)         | Managed 也會 stampede、AWS 不會幫你做 client-side jitter / singleflight、需自行設計                      |
| [2.C10 規模對照](/backend/02-cache-redis/cases/contrast-cache-strategy-by-scale/)                       | 小型 single primary / 中型 Multi-AZ replica / 大型 Cluster mode enabled + Global Datastore               |
| [2.C2 Meta mcrouter](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/)                 | ElastiCache 對應為 Cluster mode + Configuration Endpoint（client-side discovery）、無原生 protocol proxy |
| [2.C1 Meta cache consistency](/backend/02-cache-redis/cases/meta-cache-consistency-upgrade/)            | Failover / replica promotion 期間 ElastiCache 也會出現一致性議題、CloudWatch ReplicationLag 是主要訊號   |
| [2.C7 Cloudflare Cache Reserve](/backend/02-cache-redis/cases/cloudflare-cache-reserve-tiered-storage/) | 分層儲存對照、AWS 對應為 ElastiCache（hot）+ S3 / DynamoDB（cold）的應用層分層設計                       |

## 下一步路由

- 上游概念：[2.2 Cache Aside](/backend/02-cache-redis/cache-aside/)、[0.6 成本取捨](/backend/00-service-selection/cost-risk-tradeoffs/)
- 平行 vendor：[Redis](/backend/02-cache-redis/vendors/redis/)、[Valkey](/backend/02-cache-redis/vendors/valkey/)
- 下游能力：[2.7 cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)
