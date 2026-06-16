---
title: "AWS ElastiCache 的責任邊界：managed 接手了什麼、又默默留下什麼"
date: 2026-06-16
description: "ElastiCache 把 failover、patching、snapshot、跨 AZ 複製接走，但 cache stampede、client 重連、key 設計、eviction policy 還是你的事。本文用 shared responsibility 拆解 managed 的真實邊界、展開 engine 選擇與 cluster mode 配置、5 個把『以為 AWS 全包』寫成事故的 production 踩坑，以及 ElastiCache 到 MemoryDB 的 durability 邊界"
weight: 11
tags: ["backend", "cache", "aws-elasticache", "managed", "failover", "deep-article"]
---

> 本文是 [AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/) overview 的 implementation-layer deep article。選型層（為何用 managed、engine 選擇、跟自管取捨）見 overview；本文只處理「決定用 ElastiCache 後，哪些是 AWS 的責任、哪些仍是你的」。CLI 與計費以 [AWS ElastiCache 官方文件](https://docs.aws.amazon.com/elasticache/)、[ElastiCache 定價](https://aws.amazon.com/elasticache/pricing/) 為準、最後檢查日 2026-06-16（managed 服務的引數與價格會變、以官方為準）。

## managed 不等於 hands-off

把 cache 換成 ElastiCache 之後，最危險的心態是「現在 AWS 全包了」。AWS 確實接走了一大塊運維——它幫你做 failover、patching、snapshot、跨 AZ 複製，你不用再自己部署 Sentinel、不用半夜起來手動切 master。但有一類問題 ElastiCache 一個都沒幫你解，而且因為「以為 AWS 會處理」，這些問題在 managed 環境反而更容易被忽略到上線才爆。

[Tinder 的配對引擎](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/)跑在 ElastiCache for Valkey 上、4700 萬月活、sub-millisecond 延遲——這證明 managed 撐得起極大規模，但 Tinder 仍要自己設計 key、處理 cache miss、控制 client 行為。ElastiCache for Redis 7.1 在 r7g.4xlarge 上單 node 可達約 100 萬 RPS、單 cluster 約 5 億 RPS（引自 [AWS Database Blog](https://aws.amazon.com/blogs/database/achieve-over-500-million-requests-per-second-per-cluster-with-amazon-elasticache-for-redis-7-1/)）——這個吞吐是 AWS 給的，但用不用得好取決於你的 key 分布與 client 設計。

理解 ElastiCache 就是劃清這條責任邊界。本文按 shared responsibility 展開：AWS 管什麼、你管什麼、邊界上的踩坑在哪。

## 核心概念：shared responsibility 的兩側

ElastiCache 的責任劃分可以列成一張清楚的表，這張表是判讀所有 ElastiCache 事故的起點：

| 面向                 | AWS 的責任（managed）      | 你的責任（仍要自己做）                   |
| -------------------- | -------------------------- | ---------------------------------------- |
| 硬體 / OS / patching | 全包                       | —                                        |
| failover             | 自動偵測 + replica 晉升    | client 要有 reconnect 邏輯               |
| 跨 AZ 複製           | Multi-AZ 自動複製          | 接受非同步複製的 stale window            |
| snapshot / backup    | 自動 + 手動 snapshot       | 決定保留策略、驗證能還原                 |
| eviction             | 提供 maxmemory-policy 參數 | 選對 policy、設對 TTL                    |
| cache stampede       | 不管                       | client-side jitter / singleflight 自己做 |
| key 設計 / hot key   | 不管                       | key 分布、hot key 兩層 cache 自己處理    |
| 連線管理             | 提供 endpoint              | 連線池、socket timeout 自己設            |

左欄是用 managed 換到的，右欄是用 managed 換不掉的。[2.C9 cache stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/) 的雪崩、[連線風暴](/backend/02-cache-redis/vendors/redis/connection-pipeline-latency/)、[eviction 選錯](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/) 在 ElastiCache 上跟自管 Redis 一模一樣會發生——因為這些是 cache 使用方式的問題，不是運維的問題。

### engine 選擇與 cluster mode

ElastiCache 的兩個結構性決策：

**engine**：2024 起 default 是 Valkey（成本約低 20%、OSI 開源、Redis 7.2.4 fork、API 相容）；Redis OSS 仍可選但 AWS 不推；Memcached 是另一條線（純 KV、無 cluster mode 概念）。新部署或既有 Redis 遷移都走 Valkey（相容、便宜），純 cache 才考慮 Memcached。

**cluster mode**：disabled 是 1 primary + 最多 5 replica、單 shard、上限約 340GB；enabled 是多 shard（最多 500）、自動 sharding、橫向擴展。判讀：dataset < 300GB 且不需 sharding 用 disabled（簡單），> 300GB 或要橫向擴展用 enabled（但 client 要 cluster-aware）。

## 配置：建立與治理的設定路徑

```bash
# 建立 Valkey replication group（Multi-AZ、auto failover、cluster mode disabled）
aws elasticache create-replication-group \
  --replication-group-id prod-cache \
  --replication-group-description "prod cache" \
  --engine valkey \
  --cache-node-type cache.r7g.large \
  --num-cache-clusters 3 \           # 1 primary + 2 replica
  --automatic-failover-enabled \
  --multi-az-enabled \
  --snapshot-retention-limit 7 \     # 自動 snapshot 保留 7 天
  --at-rest-encryption-enabled \
  --transit-encryption-enabled

# 自訂 parameter group（maxmemory-policy 等仍是你的責任）
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name prod-params \
  --cache-parameter-group-family valkey8 \
  --description "prod cache params"
aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name prod-params \
  --parameter-name-values "ParameterName=maxmemory-policy,ParameterValue=allkeys-lru"
```

配置判讀：

- `--automatic-failover-enabled` + `--multi-az-enabled` 是 HA 的核心，把 [Sentinel 那條 failover 時序鏈](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)託管掉
- `maxmemory-policy` 透過 parameter group 設定——AWS 給旋鈕、選哪個是你的責任（見 [eviction 調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)）
- `--transit-encryption-enabled` 加 TLS，但 TLS 增加 client 建連成本，連線池更重要
- IAM authentication（Redis 7+）取代 AUTH password，對應 [security 模組](/backend/07-security-data-protection/)

## Production 故障演練

### Case 1：failover 期間 client 持續 error

**徵兆**：ElastiCache 觸發 failover（看 `describe-events`），AWS 端 replica 晉升完成，但 application 持續 30 秒到幾分鐘大量連線 error。

**根因**：failover 時 primary endpoint 的 DNS 切到新 primary，但 client 的連線池還握著舊 primary 的連線、DNS 也可能有快取。AWS 完成了 failover，但 client 重連是你的責任——ElastiCache 不會幫你的 application 重連。

**修法**：

1. client 用支援自動重連的 library，設合理的 socket timeout 與 retry（見 [連線調校](/backend/02-cache-redis/vendors/redis/connection-pipeline-latency/)）
2. 連到 primary endpoint（會跟著 failover 更新 DNS），不要連到特定 node 的 endpoint
3. 縮短 client 的 DNS 快取 TTL，讓 failover 後的 DNS 切換更快被看到
4. failover 期間的寫入中斷無法完全避免（非同步複製 + 重連時間），latency-sensitive 服務要設計降級

### Case 2：跨 AZ replication lag 造成 stale read

**徵兆**：寫入 primary 後立刻從 replica 讀，偶爾讀到舊值；CloudWatch 的 `ReplicationLag` 在高寫入時段上升。

**根因**：ElastiCache 的跨 AZ 複製是非同步的，replica 有 lag。AWS 保證複製會發生，但不保證即時——read-from-replica 在寫後立即讀的場景會看到 stale window。這跟自管 Redis 的 replica 行為一致，managed 沒有消除它。

**修法**：

1. 寫後需要立即一致讀的路徑，強制 read from primary
2. 監控 CloudWatch `ReplicationLag`，持續高代表寫入超過複製能力，要 scale up node 或降寫入
3. 接受 cache 的最終一致性——這是 cache copy 的本質，不是 bug（見 [cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)）
4. 需要強一致 + durability 走 [MemoryDB](#capacity--cost-邊界)

### Case 3：Serverless 計費超出預期

**徵兆**：用了 ElastiCache Serverless 想省容量規劃，月底帳單遠超預期。

**根因**：Serverless 按 ECPU（運算）+ storage 計費，流量尖峰或低效的 access pattern（大量小命令、大 value）會推高 ECPU 消耗。Serverless 解的是「不想規劃容量」，不是「一定更便宜」——可預測的穩態流量用 node-based + Reserved Instance 通常更省。

**修法**：

1. 流量可預測、穩態高的 workload 用 node-based + Reserved Instance（1/3 年承諾、折扣約 30-60%）
2. 流量不可預測、有大量閒置時段的才適合 Serverless
3. 監控 ECPU 消耗，找出推高成本的 access pattern（用 pipeline 合併小命令降 ECPU）
4. 成本模型對比要算實際 workload，不要假設 Serverless 一定划算

### Case 4：cluster mode enabled 但 client 不是 cluster-aware

**徵兆**：建了 cluster mode enabled 的 cluster，application 連線報 `MOVED` redirect 或連不上某些 key。

**根因**：cluster mode enabled 把 keyspace 分到多 shard，client 必須 cluster-aware（懂 `CLUSTER SLOTS`、處理 `MOVED`/`ASK` redirect）才能正確路由。普通 standalone client 連 cluster mode enabled 會失敗。

**修法**：

1. cluster mode enabled 一律用 cluster-aware client（連 configuration endpoint 不是單一 node）
2. 確認 application 的多 key 操作用 hash tag 把相關 key co-locate 同 slot（見 [cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)）
3. dataset < 300GB 且不需 sharding，用 cluster mode disabled 省掉這層複雜度
4. 從 disabled 升 enabled 是有成本的架構變更，初期規劃就要決定

### Case 5：snapshot 期間記憶體尖峰、node 不穩

**徵兆**：自動 snapshot 時段 node 延遲上升、`DatabaseMemoryUsagePercentage` 衝高，偶爾 snapshot 失敗。

**根因**：Redis engine 的 snapshot 靠 fork（見 [persistence / fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)），fork 期間 copy-on-write 推高記憶體。如果 node 記憶體已吃緊，snapshot 的 fork 把它推爆。AWS 託管了 snapshot 排程，但 fork 的記憶體成本仍在 engine 層存在。

**修法**：

1. node 記憶體留 headroom（不要長期 > 80%），給 snapshot 的 fork copy-on-write 空間
2. snapshot window 設在低流量時段，減少 fork 期間被改的 page
3. 監控 CloudWatch `DatabaseMemoryUsagePercentage`，> 80% 考慮 scale up node type
4. Valkey engine 繼承 Redis 的 fork 模型，這個成本換 engine 到 Valkey 也還在（fork-less 要 DragonflyDB、但 ElastiCache 不提供）

## Capacity / cost 邊界

ElastiCache 的容量判讀，混合了 AWS 的 metric 與 engine 層的行為：

| 訊號                            | 健康區間            | 警戒與動作                                   |
| ------------------------------- | ------------------- | -------------------------------------------- |
| `DatabaseMemoryUsagePercentage` | < 80%               | > 80% → scale up node 或調 maxmemory-policy  |
| `ReplicationLag`                | < 1 秒              | 持續高 → 寫入超過複製能力                    |
| `CurrConnections`               | 遠低於 node 上限    | 接近上限 → client 連線池問題                 |
| `CacheHitRate`                  | > 90%（多數 cache） | 下滑 → TTL / eviction / key 設計問題         |
| Serverless ECPU                 | 對齊預算            | 暴衝 → access pattern 低效、用 pipeline 合併 |

撞牆後的路由判斷：

- **需要 source-of-truth 的 Redis API（不是 cache）**：ElastiCache 是 cache 語意（資料可重建）。需要 durability 走 **AWS MemoryDB**——Redis-compatible 但有 multi-AZ transaction log、提供 source-of-truth 語意，成本約 ElastiCache 的 2-3 倍。判讀：[Tubi 把 feature store 從 ScyllaDB 遷到 ElastiCache](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) 的前提是「feature 可重新計算」——可重建選 ElastiCache，不可重建選 MemoryDB 或 database。
- **跨雲 / 不在 AWS 生態**：ElastiCache 綁 AWS，跨雲走自管 [Redis / Valkey](/backend/02-cache-redis/vendors/redis/) 或 GCP Memorystore / Azure Cache。
- **極端單機 throughput**：要榨單機多核走自管 [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)（ElastiCache 不提供 Dragonfly engine）。
- **跨 region active-passive DR**：ElastiCache 的 Global Datastore（1 primary region + 多 secondary read replica、跨 region lag < 1 秒），不支援 active-active multi-master。

## 整合 / 下一步

ElastiCache 的 deep article 本質是「劃清 managed 邊界」，它跟 engine 層的調校知識緊密相連：

- **跟 [Redis 全系列 deep article](/backend/02-cache-redis/vendors/redis/)**：eviction、persistence/fork、連線的調校在 ElastiCache 上仍適用（engine 是 Redis/Valkey），AWS 託管的是 failover/patching/snapshot 排程，不是這些 engine 行為。
- **跟 [Valkey 相容性](/backend/02-cache-redis/vendors/valkey/redis-compatibility-and-io-threads/)**：ElastiCache 的 default engine 就是 Valkey，相容性與 io-threads 的判讀直接適用。
- **跟 [Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/)**：EVCache 是 Netflix 自管的 Memcached-based 全域 cache，對照 ElastiCache for Memcached + Global Datastore——展示了自管跨區 vs managed 跨區的取捨。
- **跟 [Tinder](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) / [Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)**：兩個 ElastiCache 規模化案例，一個是 sub-ms 配對引擎、一個是 ML feature store p99<10ms，都展示了「AWS 給吞吐、你給設計」的邊界。

## 相關連結

- 上游 vendor 頁：[AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)
- engine 層 deep article：[Redis 記憶體與淘汰](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)、[persistence 與 fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)、[Sentinel 與 failover 時序](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)、[Valkey 相容性](/backend/02-cache-redis/vendors/valkey/redis-compatibility-and-io-threads/)
- 上游能力：[0.6 成本取捨](/backend/00-service-selection/cost-risk-tradeoffs/)、[cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)
- Methodology：[Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)
