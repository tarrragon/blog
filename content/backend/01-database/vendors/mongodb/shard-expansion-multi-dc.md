---
title: "MongoDB Shard Expansion + Multi-DC：Type F「不需要 parallel run」的 multi-region 例外"
date: 2026-05-19
description: "MongoDB sharded cluster 加 shard + 跨 DC expansion 是 Type F「topology re-layout」第 3 個 dogfood — 同時改 sharding + replication topology + region distribution；驗證 [#128](/report/data-topology-as-audit-dimension/) self-aware limitation 第 3 點「Type F 不需要 parallel run」claim 的例外（multi-region rollout 必須 parallel run + 切流量）；涵蓋 chunk migration / replica set add member / cross-DC routing"
weight: 12
tags: ["backend", "database", "mongodb", "sharded", "multi-dc", "topology", "type-f", "deep-article"]
---

> 本文是 [MongoDB](/backend/01-database/vendors/mongodb/) overview 的 implementation-layer deep article。對應 [#128 Type F「Topology re-layout」](/report/data-topology-as-audit-dimension/) 第 3 個 dogfood、特別驗證 self-aware limitation 第 3 點「不需要 parallel run」claim 的 *multi-region rollout 例外* — 本文是反例的具體實證。

## Reviewer D 的質疑：Type F 一定不需要 parallel run 嗎

[#128 Self-aware limitation](/report/data-topology-as-audit-dimension/) 第 3 點承認：

> 「不需要 parallel run」claim 部分不成立：multi-region rollout（#128 列為 Type F 情境）必須 parallel run — 兩 region 同時跑然後切流量、不然就是停機切換、跟 Type A phase 3 機制相同。

本文是該 claim 的 *正面實證* — MongoDB sharded cluster 從 single-DC 加 shard + 加 secondary DC、確實需要 parallel run + 流量切換、跟 Type A phased migration 局部同構：

| Type F 假設                          | Single-DC re-sharding（Redis case）| **Multi-DC expansion（本文）**         |
| ------------------------------------ | ---------------------------------- | --------------------------------------- |
| 同 cluster 不同 state                | yes                                | yes（同 MongoDB cluster）               |
| 不需 schema translation              | yes                                | yes                                     |
| 不需 parallel run                    | yes（slot migration 內部完成）    | **no — 兩 DC 同跑後切流量**            |
| 不需 cleanup phase                   | yes                                | partial（舊 DC 角色降為 standby）       |
| Step-by-step + rollback boundary     | yes                                | yes                                     |

→ Type F anatomy 仍適用、但「不需 parallel run」是 *子情境條件*、不是 universal claim。

## 兩個操作合併：shard 加 + DC 加

實務上中型公司常 *同時* 跑兩個 topology 變動：

1. **Shard expansion**：現有 3-shard cluster 加到 5-shard、chunk migration 平均分佈
2. **Multi-DC**：從 single-DC（us-east-1）加到 multi-DC（us-east-1 + us-west-2）

兩個操作的 [diff dimension audit](/report/content-structure-by-max-diff-dimension/)：

| 維度                 | Shard 加（單獨）  | Multi-DC（單獨）  | 兩者同跑              |
| -------------------- | ------------------ | ----------------- | --------------------- |
| Schema / API         | Low                | Low               | Low                   |
| Operational model    | Low                | Medium（跨 DC ops）| Medium                |
| Paradigm             | Low                | Low               | Low                   |
| Components           | Low（加 shard、同 cluster）| Low      | Low                   |
| Application change   | Low                | Low-Medium（cross-DC latency aware）| Low-Medium |
| **Data topology**    | **High**（sharding strategy）| **High**（replication + region）| **High**（雙變、複合 topology）|

兩者主導維度都是 topology = High、組合走 Type F multi-axis 子情境。

## Pre-layout analysis：當前 + 目標 topology

```javascript
// 1. 當前 shard 分佈
sh.status({verbose: false});
// 期望輸出: 3 shard、每個 ~33% chunks、no migration in progress

db.printShardingStatus({verbose: false});
// 找 hot shard、imbalanced chunk distribution

// 2. Replication topology
rs.status();
// 各 replica set primary/secondary 健康度、replication lag

// 3. Cross-DC network baseline (在 add DC 前測)
// us-east-1 → us-west-2 RTT、bandwidth
```

Pre-layout 階段 output：

- **當前**：3 shard × 1 replica set per shard (3 member) = 9 node、全在 us-east-1
- **目標**：5 shard × 1 replica set per shard (5 member: 3 us-east + 2 us-west) = 25 node
- **Migration scope**：加 2 shard + 加 2 DC member 每 shard、共 +16 node
- **Chunk migration estimate**：30% chunk 需重分（從 33% × 3 變 20% × 5）

## Re-layout 機制

兩個 mechanism 平行進行：

### Shard expansion mechanism

```javascript
// 1. 新增 shard 到 cluster
sh.addShard("rs-shard4/host10:27017,host11:27017,host12:27017");
sh.addShard("rs-shard5/host13:27017,host14:27017,host15:27017");

// 2. balancer 自動 chunk migration
sh.startBalancer();
// 觀察 progress: db.adminCommand({balancerStatus: 1})

// 3. 完成後 verify shard distribution
sh.status();
```

Chunk migration 是 *background* job、balancer 控制 throttle；不阻塞 production query、但 CPU / network 上升 30-50%。

### Multi-DC expansion mechanism

```javascript
// 1. 對每 shard 的 replica set 加 us-west-2 member (priority 0)
rs.add({
  host: "us-west-2-host:27017",
  priority: 0,           // 不能當 primary
  votes: 1,              // 參與投票
  hidden: false
});

// 2. 等 initial sync 完成（依資料量 1 小時 - 1 天）
rs.printReplicationInfo();

// 3. 確認 secondary 健康後、提升 priority 或 votes
// 不要立刻設 priority 1、避免 unintended failover

// 4. Cross-DC routing 透過 readPreference 在 application 設
const client = new MongoClient(uri, {
  readPreference: 'secondaryPreferred',
  readPreferenceTags: [{ region: 'us-west-2' }, {}],
});
```

關鍵：multi-DC 是 *漸進加 member*、不是 atomic switch；每 shard 獨立加、整體耗時 = shard 數 × initial sync time。

## Execution flow（含 parallel run + 流量切換）

8 step、包含 *parallel run + 切流量* 段——驗證 [#128 self-aware limitation](/report/data-topology-as-audit-dimension/) 第 3 點：

| Step              | 動作                                       | Parallel run? | Rollback boundary                          |
| ----------------- | ------------------------------------------ | ------------- | ------------------------------------------ |
| 1 Pre-check       | 量化當前 topology、確認 cluster 健康       | no            | -                                          |
| 2 加 us-east shard | sh.addShard、balancer migrate chunk        | no（cluster 內）| removeShard、chunk migrate 回             |
| 3 加 us-west member | 對每 shard rs.add 跨 DC member            | no            | rs.remove、initial sync 投入廢棄           |
| 4 **Initial sync wait** | 等所有 us-west member catch up        | **parallel run starts**：兩 DC 同時 serve | -                          |
| 5 **Cross-DC dual-serve** | 兩 DC 都跑 read traffic（不切 write）| **yes、parallel run**：app 用 secondary preferred us-west | readPref 切回 us-east primary |
| 6 **流量切換**     | application us-west traffic 走 us-west read | **yes** | DNS / readPref 切回                       |
| 7 Promote us-west（optional） | 一個 shard 的 us-west member priority 提到 1 | post-cutover | demote priority 回 0   |
| 8 Cleanup         | Verify、archive log、document new topology | no            | -                                          |

Step 4-6 是 *parallel run + 切流量* — **Type F 有此例外、跟 Type A phase 3 機制同構**；anatomy 中「Execution flow per-step」段必須含 parallel run 子段。

## Production 故障演練

### Case 1：Balancer 跑 chunk migration 撞 production peak

**徵兆**：加 shard 後 balancer 開始 migrate chunk、production write latency p99 從 10ms 跳到 100ms；application 端 timeout 大量。

**根因**：MongoDB balancer 預設 24×7 跑、chunk migrate 是 *blocking* 操作（migration lock 期間阻塞 write 到該 chunk）；產線高峰時間 balancer 不會自動暫停。

**修法**：

```javascript
// 限 balancer 跑在 low-traffic window
sh.setBalancerState(true);
db.settings.update(
  { _id: "balancer" },
  { $set: { activeWindow: { start: "02:00", stop: "06:00" } } },
  { upsert: true }
);
```

且設 `chunkSize` 較小（128MB → 64MB）讓 migration 步驟細、單次 lock 時間短。

### Case 2：Cross-DC initial sync 期間 oplog 跑出窗口

**徵兆**：加 us-west member 後、initial sync 跑 4 小時、結束時 member 顯示「too stale to catch up」、需要 full re-sync。

**根因**：MongoDB oplog 是 capped collection、預設 size 5% disk；4 小時 initial sync 期間 primary 寫入量超出 oplog 保留範圍、member 拿到的 oplog start point 已被覆蓋。

**修法**：

1. **預先擴 oplog size**：`db.adminCommand({replSetResizeOplog: 1, size: 51200})` 加到 50GB、覆蓋 sync window
2. **Off-peak initial sync**：跑在低流量時間、oplog 寫入較慢
3. **Manual initial sync via snapshot**：用 `mongodump` 從 primary snapshot、restore 到 new member、跳過 oplog tail catch-up

### Case 3：跨 DC read 路由錯誤、stale data 影響業務

**徵兆**：切流量到 us-west 後、application 偶爾抓到 5-30 秒前的 stale data；customer 報告「明明剛改了 setting、refresh 又變回去」。

**根因**：us-west member 是 secondary、replication lag 5-30 秒；application readPreference 設 `secondaryPreferred` 但沒 `maxStalenessSeconds`、可能讀到嚴重 stale member。

**修法**：

```javascript
const client = new MongoClient(uri, {
  readPreference: 'secondaryPreferred',
  readPreferenceTags: [{ region: 'us-west-2' }, {}],
  maxStalenessSeconds: 90,  // 限 stale 不超過 90 秒
});

// 對 strict consistency 場景強制 primary
const client_strict = new MongoClient(uri, {
  readPreference: 'primary',  // 強制讀 us-east primary
});
```

Application-level read pattern 必須區分「accept stale read」vs「require fresh read」、不是 cluster-level 統一配置。

### Case 4：Shard tag-aware routing 沒設、cross-DC traffic 爆 cost

**徵兆**：multi-DC 跑了 1 個月、AWS egress cost 從 $500 / month 漲到 $8000 / month；99% 流量還是 us-east → us-west 跨 DC。

**根因**：sharded cluster 沒設 *zone sharding*、application 不知道哪些 chunk 在哪個 DC、所有 query 預設打 us-east primary、跨 DC bandwidth 爆。

**修法**：

```javascript
// 1. 給 shard 加 zone tag
sh.addShardTag("rs-shard1", "us-east");
sh.addShardTag("rs-shard2", "us-east");
sh.addShardTag("rs-shard3", "us-east");
sh.addShardTag("rs-shard4", "us-west");
sh.addShardTag("rs-shard5", "us-west");

// 2. 對 collection 加 zone range（按 region key）
sh.addTagRange(
  "myapp.events",
  { region: "us-east", _id: MinKey },
  { region: "us-east", _id: MaxKey },
  "us-east"
);
sh.addTagRange(
  "myapp.events",
  { region: "us-west", _id: MinKey },
  { region: "us-west", _id: MaxKey },
  "us-west"
);

// 3. balancer 重新分配 chunk 到對應 zone
```

Zone sharding 是 multi-DC 必要設計、不設等於白付 egress cost。

### Case 5：Failover 後跨 DC primary 切換、application 連線中斷

**徵兆**：production 跑 6 個月後、us-east-1 outage、某 shard primary 切到 us-west member；application 5-10 秒內大量 connection error。

**根因**：MongoDB driver 預設 election timeout 10 秒、application 沒設 server selection retry；primary 切換期間 client 沒重連。

**修法**：

```javascript
const client = new MongoClient(uri, {
  serverSelectionTimeoutMS: 30000,    // 等 30 秒給 election
  retryWrites: true,
  retryReads: true,
  heartbeatFrequencyMS: 5000,         // 更頻繁 detect topology 變動
});
```

且 multi-DC primary 應該設 *priority asymmetry*：us-east member priority 2、us-west priority 1；正常情況不切換、災難時自動切。

## Capacity / cost

| 維度                | Single-DC 3-shard            | Multi-DC 5-shard                 | Trade-off                                              |
| ------------------- | ---------------------------- | -------------------------------- | ------------------------------------------------------ |
| Node count          | 9                            | 25                                | ~3x infrastructure cost                                |
| Storage redundancy  | 3 replica                    | 5 replica (3 east + 2 west)       | +2 copy、storage cost +66%                            |
| Network egress      | 內部 VPC、低                 | Cross-DC、高（需 zone sharding）  | $500 → $8000 / month if no zone sharding            |
| Latency p99 (write) | 5-10ms                       | 5-15ms（primary 仍 us-east）      | 略升                                                   |
| Latency p99 (read)  | 5-10ms                       | 2-5ms (local DC)                  | Multi-DC 區域 read 加快                                |
| Disaster recovery   | RTO 30 分鐘（rebuild）       | RTO < 1 分鐘（auto failover）     | 顯著改善                                               |
| Operational complexity | 低                          | 高（zone sharding / DR drill）   | +1 SRE FTE 維護                                       |

**判讀**：multi-DC 是 *DR 投資*、不是 cost optimization；只在 *availability SLA > 99.9% 或合規要求* 場景值得。

## 整合 / 下一步

### 跟 [MongoDB → Atlas migration](/backend/01-database/vendors/mongodb/migrate-to-atlas/) 對位

Self-managed multi-DC 複雜度高、Atlas 把 multi-cluster + cross-region 簡化成 UI 配置；如果走 multi-DC、考慮直接遷 Atlas。

### 跟 Application read pattern 整合

zone sharding + readPreference 跟 application logic 緊密耦合；不能事後補、應在 multi-DC 設計階段就設計 application 端的 region-aware routing。

### 跟 [Cassandra keyspace re-balance](https://cassandra.apache.org/) 對比

Cassandra 是另一個 Type F multi-DC 典型 case；用 *NetworkTopologyStrategy + replication factor per DC*、跟 MongoDB zone sharding 概念對等但 mechanism 完全不同。Reviewer D 把 Cassandra 列為 Type F 反例 — 本文以 MongoDB 替代驗證。

### 下一步議題

- **Cross-region active-active**：MongoDB 不支援 multi-primary、cross-region active-active 需要 application-level conflict resolution
- **PostgreSQL Citus / CockroachDB multi-region** 對比：distributed SQL 對 multi-region 有不同設計
- **Cost optimization**：跨 DC egress 是 long-term concern、zone sharding 設好後仍要 quarterly review

## 相關連結

- 上游 vendor 頁：[MongoDB](/backend/01-database/vendors/mongodb/)
- 平行 migration playbook：[MongoDB → Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/)
- 平行 Type F dogfood：[Redis Cluster Re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)（dogfood #1）/ [PostgreSQL Partition Redesign](/backend/01-database/vendors/postgresql/partition-redesign/)（dogfood #2）
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/) / [#128 Data topology 是第 6 audit 維度](/report/data-topology-as-audit-dimension/)（本文驗證 self-aware limitation 第 3 點）
