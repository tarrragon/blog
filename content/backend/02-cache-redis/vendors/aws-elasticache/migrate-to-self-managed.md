---
title: "ElastiCache → 自管 Redis / Valkey：脫離 managed 的遷移路徑"
date: 2026-06-22
description: "從 AWS ElastiCache 遷移到自管 Redis 或 Valkey，處理 RDB export、DNS 切換、IAM 認證移除與監控重建的階段化流程"
weight: 12
tags: ["backend", "cache", "elasticache", "redis", "valkey", "migration"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)（source）跟 [Redis](/backend/02-cache-redis/vendors/redis/) / [Valkey](/backend/02-cache-redis/vendors/valkey/)（target）。跑 6 維 diff dimension audit 後判定為 **Type C operational redesign hybrid**：engine 層相容（Low）但 operational model 差異大（IAM auth → password/ACL、CloudWatch → 自管監控、auto failover → Sentinel/自建 HA）。

## 為什麼從 managed 遷出

ElastiCache 遷出的 driver 通常不是 engine 層問題 — 它跑的就是 Redis 或 Valkey。常見遷出原因：

- **成本**：managed premium 在大規模（數百 GB、多叢集）下比自管 + 運維人力更貴，尤其跨帳戶大量叢集時
- **跨雲或混合雲**：業務需要在 GCP、Azure 或 on-prem 同時運行 cache 層，ElastiCache 只在 AWS
- **功能限制**：ElastiCache 不支援所有 Redis module（RediSearch、RedisJSON 等），或 Valkey 8.x 新功能 ElastiCache 尚未上線
- **控制權**：自管可以自訂 redis.conf、自選 kernel 參數、自決 upgrade 時機

資料搬遷用 RDB export + import 就完成，真正的工程量在 operational model 重建 — ElastiCache 幫你管的 HA、monitoring、backup、security，遷出後全要自建。

## 6 維 diff dimension audit

| 維度                   | 評估                                                                            | 等級       |
| ---------------------- | ------------------------------------------------------------------------------- | ---------- |
| Schema / API           | 同 Redis/Valkey engine、RESP 相容                                               | Low        |
| Operational model      | IAM auth → ACL/password、CloudWatch → 自管監控、auto failover → Sentinel 或手動 | High       |
| Abstraction / paradigm | 相同（key-value cache）                                                         | Low        |
| Number of components   | ElastiCache 1 → Redis/Valkey + Sentinel/HA + 監控 + backup 多元件               | Medium     |
| Application change     | endpoint 換、認證方式換、少量 client config 修改                                | Low-Medium |
| Data topology          | RDB 相容、cluster mode 對應 Redis Cluster                                       | Low        |

Operational model 是 High — 這是 Type C 的判定依據。遷移重心在重建 ElastiCache 幫你做的那些事。

## 階段一：盤點 ElastiCache 依賴

在動手之前，先列出 ElastiCache 幫你管的所有東西，每一項都要在自管環境重建或決定不要。

### 認證與網路

- **IAM auth**：ElastiCache 支援 IAM auth token（短效 token），自管 Redis 改用 `requirepass` 或 Redis 6+ ACL
- **VPC / Security Group**：自管 Redis 仍需 VPC 隔離，但 security group 規則要自己維護
- **TLS**：ElastiCache 原生 in-transit encryption，自管要自己配 redis TLS 憑證

### 高可用

- **Auto failover**：ElastiCache 自動偵測 primary failure 並 promote replica。自管用 [Sentinel HA failover](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/) 或 Redis Cluster 內建 failover
- **Cross-AZ replication**：ElastiCache 自動跨 AZ。自管要自己在不同 AZ 部署 replica

### 監控與備份

- **CloudWatch metrics**：ElastiCache 自動發 `CurrConnections`、`CacheHitRate`、`ReplicationLag` 等。自管用 `INFO` 指令 + Prometheus redis_exporter
- **Snapshot**：ElastiCache 自動 daily snapshot + 手動 snapshot。自管用 `BGSAVE` + cron + 外部 storage

### 跨 region replication

- **Global Datastore**：ElastiCache 支援跨 region active-passive replication。自管 Redis 沒有原生跨 region replication — 若目前使用 Global Datastore，遷出前需要決定是用 application-level replication、第三方工具（Redis Enterprise Active-Active）還是放棄跨 region cache 同步

### 升級與維護

- **Engine 升級**：ElastiCache 在維護窗口自動或手動升級。自管要自己做 rolling upgrade
- **Patch**：安全 patch 由 AWS 負責。自管要自己追蹤 CVE

## 階段二：建立自管環境

### 部署架構

最小 production 架構：1 primary + 1 replica + 3 Sentinel（或 Redis Cluster 3 primary + 3 replica）。

```bash
# Docker Compose 驗證用（production 用 VM 或 K8s）
# Primary
docker run -d --name redis-primary -p 6379:6379 redis:7 \
  redis-server --requirepass "$REDIS_PASSWORD" --appendonly yes

# Replica
docker run -d --name redis-replica -p 6380:6379 redis:7 \
  redis-server --replicaof redis-primary 6379 \
  --masterauth "$REDIS_PASSWORD" --requirepass "$REDIS_PASSWORD"
```

Sentinel 或 Redis Cluster 配置見 [Sentinel HA Failover](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)。

### 監控重建

ElastiCache CloudWatch metrics 對應的自管替代：

| ElastiCache metric            | 自管替代                                            | 來源               |
| ----------------------------- | --------------------------------------------------- | ------------------ |
| CurrConnections               | `connected_clients`                                 | `INFO clients`     |
| CacheHitRate                  | `keyspace_hits / (keyspace_hits + keyspace_misses)` | `INFO stats`       |
| ReplicationLag                | `master_repl_offset - slave_repl_offset`            | `INFO replication` |
| EngineCPUUtilization          | `used_cpu_sys + used_cpu_user`                      | `INFO cpu`         |
| DatabaseMemoryUsagePercentage | `used_memory / maxmemory`                           | `INFO memory`      |
| Evictions                     | `evicted_keys`                                      | `INFO stats`       |

用 [Prometheus redis_exporter](https://github.com/oliver006/redis_exporter) 自動採集，接 Grafana dashboard。

### Backup 重建

```bash
# cron job: 每日 BGSAVE + 等完成 + 上傳 S3
# LASTSAVE 回傳 Unix timestamp，BGSAVE 完成後 LASTSAVE 會更新
0 3 * * * BEFORE=$(redis-cli -a "$REDIS_PASSWORD" LASTSAVE) && \
  redis-cli -a "$REDIS_PASSWORD" BGSAVE && \
  while [ "$(redis-cli -a "$REDIS_PASSWORD" LASTSAVE)" = "$BEFORE" ]; do sleep 5; done && \
  aws s3 cp /data/dump.rdb s3://backup-bucket/redis/$(date +\%Y\%m\%d).rdb
```

Production 建議搭配 [persistence fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/) 的監控，確認 BGSAVE 的 fork 不會造成延遲 spike。

## 階段三：資料搬遷與切換

### 搬遷策略

ElastiCache 的資料搬遷有兩條路：

**RDB export + import（適合 downtime 可接受的場景）**：

1. ElastiCache 建立手動 snapshot
2. 把 snapshot export 到 S3（ElastiCache console → Export snapshot）
3. 下載 RDB 檔，放到自管 Redis 的資料目錄
4. 重啟自管 Redis 載入 RDB

**雙寫期間遷移（適合零停機需求）**：

1. Application 同時寫 ElastiCache 和自管 Redis（雙寫）
2. 讀取仍走 ElastiCache
3. 監控自管 Redis 的資料量與命中率追上後，切讀取到自管
4. 移除 ElastiCache 寫入
5. 下線 ElastiCache

雙寫的複雜度高於 RDB export。Cache 資料可重建的特性讓第一種策略在多數場景夠用 — 短暫 cache miss 的代價是回源到 DB，通常可接受。

### Endpoint 切換

Application 用 endpoint 連 ElastiCache。切換時：

1. 把 application config 的 Redis host 改為自管 Redis endpoint
2. 確認 TLS 與認證方式對齊（IAM token → password/ACL）
3. Rolling restart application
4. 監控 cache hit rate 與 latency 回到 baseline

如果用 DNS CNAME 間接指向 ElastiCache endpoint，可以直接改 CNAME 指向自管 Redis，application 不用改 config。

## 階段四：驗證與回退

### 驗證清單

| 驗證項目      | 通過條件                                                     | 工具                        |
| ------------- | ------------------------------------------------------------ | --------------------------- |
| 連線正常      | application 能 PING、無 auth error                           | redis-cli + application log |
| 資料完整      | key count 跟 ElastiCache 一致（容許 TTL 過期差異）           | `DBSIZE` 比對               |
| 效能 baseline | latency p99 與 hit rate 跟遷移前一致                         | Prometheus + Grafana        |
| HA 測試       | kill primary，Sentinel promote replica，application 自動重連 | 手動 failover drill         |
| Backup 測試   | BGSAVE 產生 RDB、上傳成功、可還原                            | 還原到測試 instance 驗證    |

### 回退路徑

Cache 遷移的回退比 DB 遷移簡單 — cache 資料可重建。回退步驟：

1. Application config 改回 ElastiCache endpoint（或 CNAME 指回）
2. Rolling restart
3. Cache miss 回源到 DB，自然 warm up

ElastiCache 在遷移期間不要下線，保留 7-14 天作為回退保險。確認自管 Redis 穩定運行後再刪除 ElastiCache cluster。

## 成本對照

| 項目    | ElastiCache                        | 自管 Redis                       |
| ------- | ---------------------------------- | -------------------------------- |
| Compute | managed node pricing（含 premium） | EC2 / K8s 原價                   |
| HA      | auto failover 內建                 | Sentinel 或 Cluster 自建         |
| 監控    | CloudWatch 內建                    | redis_exporter + Prometheus 自建 |
| Backup  | 自動 snapshot                      | cron + S3 自建                   |
| 人力    | 低（AWS 管）                       | 高（on-call + upgrade + patch）  |
| 靈活度  | 受限（engine version、module）     | 完全自控                         |

小規模（< 50 GB、< 5 cluster）通常 ElastiCache 的 managed premium 比自管人力便宜。Compute 跟 HA 的差額在小規模可忽略，但監控跟 backup 的自建成本是固定開銷 — 即使只管一個 cluster，redis_exporter + Prometheus + cron backup 的設定跟維護都要做。大規模（數百 GB、多叢集）或跨雲場景下，managed premium 累積到 cluster 數 × node 數的倍數，自管的邊際成本反而更低，遷出 ROI 才成立。

## 交接路由

- Source vendor overview：[AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)
- Target vendor 操作：[Redis Sentinel HA](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)、[Redis Cluster Resharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)
- 監控重建：[Redis Memory Eviction Tuning](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)、[Redis Persistence Fork Latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)
- 反向路徑：[Redis → ElastiCache](/backend/02-cache-redis/vendors/redis/migrate-to-elasticache/)
