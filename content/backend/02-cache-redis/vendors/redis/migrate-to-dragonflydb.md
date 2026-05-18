---
title: "Redis → DragonflyDB：drop-in 相容下的容量躍升 + 5 個踩雷"
date: 2026-05-19
description: "DragonflyDB 號稱 Redis drop-in 替代、單機 throughput 25x、記憶體效率 30% 提升；遷移流程簡單但有 5 個 production 踩雷（RDB 版本差 / Lua 腳本不全支援 / Pub-Sub fanout 行為差異 / Cluster mode 兼容度 / Modules 不支援）、跟 Sentinel / Cluster 模式對位"
weight: 12
tags: ["backend", "cache", "redis", "dragonflydb", "migration", "drop-in"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [Redis](/backend/02-cache-redis/vendors/redis/)（source）跟 [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)（target）。跟前一篇 [Splunk → Elastic Security](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) 的 6-phase playbook 對照、Redis → DragonflyDB 是 *drop-in 相容* 形態的 migration、結構更接近 [vendor deep article methodology](/posts/vendor-deep-article-methodology/) 的 6-section flow + 一段「相容性驗證」前置。

## 為什麼遷：cost / single-thread / multi-tenancy 三條 driver

| Driver               | 觸發場景                                                                            |
| -------------------- | ----------------------------------------------------------------------------------- |
| **Memory cost**      | Redis 6.x cluster 跑 1-10 TB 時、機器成本爆；DragonflyDB 記憶體效率提升 ~30%、相同 dataset 少 30% RAM |
| **Single-thread bottleneck** | Redis 主執行緒在單一 hot key 寫入時是瓶頸、scale-up 受限；DragonflyDB 多執行緒 + shared-nothing 設計、單機 throughput 號稱 25x |
| **Multi-tenancy**    | Redis Cluster 多 namespace 需要 cluster-per-tenant、運維成本爆；DragonflyDB 設計上 namespace 隔離成本低 |

反向 driver（DragonflyDB → Redis）也存在 — 主要是 *Redis Modules 依賴*（RedisJSON / RedisSearch / RedisGraph）DragonflyDB 不支援、或 *Lua script 用了 redis.call 進階 API*。

## 跟 phased migration 的對照：drop-in 不需要 phased

跟前一篇 Splunk → Elastic 的 6-phase playbook 不同、Redis → DragonflyDB 的 migration *結構接近 standard deep article*：

| 維度                 | Splunk → Elastic（phased）                  | Redis → DragonflyDB（drop-in）           |
| -------------------- | ------------------------------------------- | ---------------------------------------- |
| Schema 對位          | 需要（SPL ↔ KQL / CIM ↔ ECS）             | 不需要（RESP protocol 相容）             |
| Rule translation     | 4-12 週 SOC engineering 工作                 | 不需要（command 直接相容）               |
| Parallel run         | 4-8 週 dual-SIEM 跑                          | 1-7 天 dual-write 觀察                   |
| Cutover 邊界         | 軟邊界（routing 切換、可逆 30 分鐘）         | 硬邊界（client 配置切換、單次完成）      |
| 不可逆 cleanup       | 1 年後 archive                               | 立刻（DragonflyDB 接管後 Redis 可關）    |
| 整體週期             | 4-9 個月                                     | 1-4 週                                   |

**判斷依據**：migration 結構由 *source 跟 target 的 schema / protocol 差異程度* 決定、不是 universal phased playbook。本批第 2 篇驗證 *deep article methodology 的 6-section 框架* 在 drop-in migration 仍適用（只需前置 *相容性驗證* 段、其他 6 段對位）。

## 相容性驗證：在 cutover 前要確認的清單

DragonflyDB 號稱 Redis drop-in、但「drop-in」涵蓋範圍依 Redis feature 使用程度而定。Pre-migration 必跑的相容性 audit：

| Redis feature                  | DragonflyDB 支援程度                                | Action                                       |
| ------------------------------ | --------------------------------------------------- | -------------------------------------------- |
| Basic data types (String / Hash / List / Set / ZSet) | 完全相容                          | 無需處理                                     |
| RESP protocol v2 / v3          | 完全相容                                            | 無需處理                                     |
| RDB load                       | Redis 6.x RDB 完全相容；7.x 部分 feature 待測       | 用 BGSAVE → 切換 → load 驗證                |
| AOF                            | DragonflyDB 不用 AOF、改 *snapshotting* 模式        | 不直接 import AOF、需經 RDB 中介             |
| Lua scripts                    | 90% 相容、部分 redis.call API + EVAL 邊界 case 差異  | Lua script audit 必跑、不能假設全相容        |
| Pub/Sub                        | 相容、但 message fanout 行為差異（多 thread 處理）   | 高 fanout pub/sub 場景需測 latency           |
| Cluster mode                   | DragonflyDB *單機* 即可達 cluster throughput、不必 cluster；emulated cluster mode 部分相容 | 評估是否仍需 cluster |
| Sentinel HA                    | 不直接支援、用 DragonflyDB 自家 replication       | HA 架構重設計                                |
| Redis Modules (RedisJSON / Search / Graph) | **不支援**                                | 必須前置改寫 application                     |
| Streams                        | 相容、但 consumer group 行為部分差異                 | Stream consumer 跑 dual-write 觀察           |
| Keyspace notifications         | 相容                                                | 無需處理                                     |

**Audit 的關鍵 output**：列「不相容功能」清單 + 對應 application code 修改範圍；若 Modules 在 production 使用、migration *退役*。

## Step-by-step cutover

```bash
# 1. 部署 DragonflyDB
docker run -d --name dragonfly -p 6380:6379 \
  -v /data/dragonfly:/data \
  docker.dragonflydb.io/dragonflydb/dragonfly:latest \
  --logtostderr --requirepass=<your_password>

# 2. Redis 端 BGSAVE
redis-cli -h redis-primary BGSAVE
# 等到 BGSAVE 完成
redis-cli -h redis-primary INFO Persistence | grep rdb_last_save_time

# 3. 把 dump.rdb 拷到 DragonflyDB
scp redis-primary:/var/lib/redis/dump.rdb dragonfly-host:/data/dragonfly/

# 4. 重啟 DragonflyDB 載入 RDB
docker restart dragonfly

# 5. 驗證資料一致
redis-cli -h dragonfly-host -p 6380 DBSIZE
redis-cli -h redis-primary DBSIZE
# 兩端 key 數對齊

# 6. Dual-write 1-7 天（application 同時寫兩端）
# 7. Read 切換到 DragonflyDB、Redis 端只寫不讀
# 8. Write 切換、Redis 端 standby
# 9. 觀察 1-2 週、無異常後 Redis decommission
```

關鍵時間點：

- **BGSAVE → load**：100GB RDB 約 5-15 分鐘、跨網路 SCP 時間另算
- **Dual-write window**：1-7 天觀察、application 寫兩端、read 仍走 Redis
- **Cutover**：read switch → write switch、每步間隔 24 小時
- **Decom**：Redis 保留 standby 1-2 週、無異常後關閉

## Production 故障演練

### Case 1：RDB 版本差，DragonflyDB load 失敗

**徵兆**：Redis 7.2 端 BGSAVE 出的 `dump.rdb` 在 DragonflyDB load 時報 `Unsupported RDB version`、DragonflyDB 啟動失敗。

**根因**：Redis 7.2 RDB version 11 含新 feature（function library / sharded pubsub）DragonflyDB 當前 release 沒支援；版本相容性需逐 release 確認。

**修法**：

1. **Pre-migration 版本相容矩陣 audit**：DragonflyDB release note 對照 Redis version、確認 RDB version 支援
2. **降級 BGSAVE**：Redis 端設 `rdb-version 9`（Redis 6.x 兼容版本）、犧牲 Redis 7.x 新 feature
3. **替代方案**：用 `redis-cli --scan` + `MIGRATE` 命令 incremental 搬、不用 RDB；速度慢 100x 但相容性好

### Case 2：Lua script 跑進 EVAL 不一致

**徵兆**：dual-write 階段、發現某些 EVAL script 在 Redis 跟 DragonflyDB 結果不同；具體是某個 `redis.call("OBJECT", "ENCODING", key)` 在 DragonflyDB 回不一樣的 encoding 字串。

**根因**：DragonflyDB 內部不用 Redis 的 ziplist / listpack encoding（dashtable 不需要）、`OBJECT ENCODING` 返回值不對等；script 邏輯依賴 encoding 來決定行為、結果不同。

**修法**：

1. **Audit Lua script**：grep 所有 `redis.call("OBJECT"`、列出依賴 encoding 的 script
2. **改寫 application**：不依賴 encoding、改用 `MEMORY USAGE` 或 high-level check
3. **接受差異**：DragonflyDB 不會回 encoding 但 functional 結果對等、SOC review 確認可接受

### Case 3：Pub/Sub fanout 高負載 latency

**徵兆**：production 切到 DragonflyDB 後、Pub/Sub 訂閱端 latency p99 從 5ms 漲到 20-50ms；topic fanout >10K subscriber 場景。

**根因**：DragonflyDB 多 thread 設計、Pub/Sub message 在 thread 間 dispatch 需要 routing；Redis single-thread 沒這個 overhead。高 fanout 是 DragonflyDB 設計取捨。

**修法**：

1. **架構**：高 fanout Pub/Sub 不用 DragonflyDB、改 [NATS](/backend/03-message-queue/vendors/nats/) / Redis Streams + consumer group
2. **DragonflyDB 配置調整**：`--proactor_threads` 對 Pub/Sub 影響大、調到符合 CPU 核心數
3. **接受 latency**：< 10K subscriber 差異可忽略、不必動

### Case 4：Cluster mode 看似相容但 slot routing 行為差

**徵兆**：application 用 Redis Cluster client（lettuce / Jedis cluster mode）連 DragonflyDB emulated cluster、運行幾天後 `MOVED` redirect 異常、key 找不到。

**根因**：DragonflyDB emulated cluster mode 是 *single node 模擬*、CLUSTER SLOTS 返回固定 mapping；某些 client 端 cluster topology cache 跟實際 routing 不對齊、發 redirect。

**修法**：

1. **Application 改 standalone client**：DragonflyDB single node 已能達 cluster 級 throughput、不必用 cluster client
2. **Client config**：lettuce 端 `clusterTopologyRefreshOptions(...)` 設較長 refresh、減少 redirect 機會
3. **長期**：等 DragonflyDB cluster 正式 GA 後再評估

### Case 5：Modules 用了沒注意，migration 卡住

**徵兆**：cutover 後幾天、application 某個功能完全壞、log 顯示 `ERR unknown command 'JSON.SET'`；DragonflyDB 不支援 RedisJSON。

**根因**：Pre-migration audit 漏掉 application 用了 RedisJSON（透過某 client library 抽象）；DragonflyDB 不支援該 Module 命令、application 直接壞。

**修法**：

1. **Pre-migration audit 必跑**：`MONITOR` 抓 1 小時 production traffic、grep 非 standard command（`JSON.*` / `FT.*` / `GRAPH.*`）
2. **應急回退**：Redis standby 還在、application client config 切回
3. **長期**：JSON 改用 standard Hash + serialization、Search 改 Elasticsearch / Meilisearch、Graph 改 Neo4j

## Capacity / cost 對照

| 維度                      | Redis（self-managed）                                      | DragonflyDB                                               | 取捨                                                       |
| ------------------------- | ---------------------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------- |
| Single-node throughput   | ~100K-200K ops/s                                            | ~2-5M ops/s（號稱 25x）                                   | DragonflyDB 領先、實測依 workload 而定                     |
| Memory efficiency         | baseline                                                   | -30% 平均、依資料分佈                                     | DragonflyDB 領先                                          |
| Persistence               | RDB / AOF 雙模式                                            | Snapshotting 為主、不用 AOF                              | Redis 對 durability 要求高的 workload 仍領先              |
| HA / Replication          | Sentinel + Cluster 成熟                                     | 自家 replication、HA 文件相對少                          | Redis 領先                                                |
| Modules ecosystem         | RedisJSON / Search / Graph / TimeSeries                    | 不支援                                                    | Redis 領先                                                |
| Cluster scaling           | Cluster mode 成熟                                            | 單機效能高、cluster 仍 emerging                          | Redis 領先、但 DragonflyDB 單機已能 cover 多數 use case   |
| Total cost (10TB cache)   | $8-15K USD / month                                          | $2-5K USD / month                                         | DragonflyDB 顯著便宜                                       |
| Operational maturity      | 高（10+ 年 production）                                     | 中（2022+、production 案例 1000+）                       | Redis 領先                                                |

**判讀**：cache use case 簡單（pure cache / session store）走 DragonflyDB；複雜 use case（Modules / Pub/Sub fanout / strict durability）保留 Redis。

## 整合 / 下一步

### 跟 client library 整合

主流 Redis client（lettuce / Jedis / redis-py / node-redis / go-redis）都直接相容 DragonflyDB；唯一例外是 *cluster client* 模式行為差（見 Case 4）。

### 跟 monitoring 整合

DragonflyDB exporter 提供 Prometheus metric、跟 Redis exporter 對應 metric 名稱 80% 相同；grafana dashboard 需小改：

- `redis_memory_used_bytes` → `dragonfly_memory_used_bytes`
- `redis_commands_processed_total` → `dragonfly_commands_processed_total`

### 跟 [Redis Sentinel HA](/backend/02-cache-redis/) 對位

DragonflyDB 不直接支援 Sentinel、HA 走自家 *master-replica* + DNS-based failover：

1. DragonflyDB primary + replica
2. K8s 用 StatefulSet + Service + readiness probe
3. 失敗 failover 比 Sentinel 慢（30s-2min vs 5-15s）

### 下一步議題

- **DragonflyDB Cluster GA**：正式 cluster mode 出來後重評估
- **Stream + consumer group 細節**：dual-write 期間驗證每個 consumer pattern
- **Modules 替代方案**：JSON / Search / Graph 各自的 cloud-native 替代評估

## 相關連結

- Source vendor：[Redis](/backend/02-cache-redis/vendors/redis/)
- Target vendor：[DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)
- 平行 migration playbook：[Splunk → Elastic Security](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
