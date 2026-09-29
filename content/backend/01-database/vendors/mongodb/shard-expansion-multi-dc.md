---
title: "MongoDB Shard Expansion + Multi-DC：加 shard 與加 DC 同時進行時的 parallel run 與流量切換"
date: 2026-05-19
description: "MongoDB sharded cluster 同時加 shard 與加 DC 的操作：chunk migration、replica set 加跨 DC member、cross-DC routing 的機制，加 DC 為什麼要兩個 DC 並行服務再切流量，balancer、initial sync、跨 DC 讀取、zone sharding 與跨 DC failover 的故障演練，以及 multi-DC 的容量與成本"
weight: 12
tags: ["backend", "database", "mongodb", "sharded", "multi-dc", "topology", "type-f", "deep-article"]
---

這篇整理 MongoDB sharded cluster 同時加 shard 與從 single-DC 擴成 multi-DC 的操作：兩種 topology 變動各自的機制、合併執行時的步驟與 rollback boundary、balancer、initial sync、跨 DC 讀取、zone sharding 與跨 DC failover 的故障演練，以及 multi-DC 的容量與成本。MongoDB 的服務定位在 [MongoDB overview](/backend/01-database/vendors/mongodb/)。

## 加 DC 需要 parallel run，加 shard 不需要

Topology re-layout 指在同一個 cluster 內改變資料分布方式的變更，多數在 cluster 內部完成、不需要新舊兩套環境並行：加 shard 時 balancer 在 cluster 內搬 chunk，Redis Cluster 的 re-sharding 靠 slot migration 在內部完成。加 DC 是例外：新 DC 的 member 完成 initial sync 之後，兩個 DC 要同時服務讀取一段時間，確認新 DC 的延遲與資料新鮮度後才把流量切過去，否則就只能停機切換。這段並行期與流量切換，跟 phased migration 的 parallel run 是同一套做法（這一類 migration 的分類見 [Data topology 是 process content 的 audit 維度](/report/data-topology-as-audit-dimension/)）。

| Topology re-layout 的常見性質    | Single-DC re-sharding（Redis case） | **Multi-DC expansion（本文）**    |
| -------------------------------- | ----------------------------------- | --------------------------------- |
| 同 cluster 不同 state            | yes                                 | yes（同 MongoDB cluster）         |
| 不需 schema translation          | yes                                 | yes                               |
| 不需 parallel run                | yes（slot migration 內部完成）      | **no — 兩 DC 同跑後切流量**       |
| 不需 cleanup phase               | yes                                 | partial（舊 DC 角色降為 standby） |
| Step-by-step + rollback boundary | yes                                 | yes                               |

「不需要 parallel run」只在 cluster 內部就能完成的 re-layout 成立，加 DC 這類要讓新位置先接流量的變更不在其中。

## 兩個操作合併：shard 加 + DC 加

實務上中型公司常 *同時* 跑兩個 topology 變動：

1. **Shard expansion**：現有 3-shard cluster 加到 5-shard、chunk migration 平均分佈
2. **Multi-DC**：從 single-DC（us-east-1）加到 multi-DC（us-east-1 + us-west-2）

兩個操作的 [diff dimension audit](/report/content-structure-by-max-diff-dimension/)：

| 維度               | Shard 加（單獨）              | Multi-DC（單獨）                     | 兩者同跑                        |
| ------------------ | ----------------------------- | ------------------------------------ | ------------------------------- |
| Schema / API       | Low                           | Low                                  | Low                             |
| Operational model  | Low                           | Medium（跨 DC ops）                  | Medium                          |
| Paradigm           | Low                           | Low                                  | Low                             |
| Components         | Low（加 shard、同 cluster）   | Low                                  | Low                             |
| Application change | Low                           | Low-Medium（cross-DC latency aware） | Low-Medium                      |
| **Data topology**  | **High**（sharding strategy） | **High**（replication + region）     | **High**（雙變、複合 topology） |

兩者主導維度都是 data topology = High，合在一起是同時改 sharding 與 replication / region 兩個 topology 軸的 re-layout。

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
- **Chunk migration estimate**：40% 的資料要搬到新 shard（每個舊 shard 從約 33% 降到 20%，兩個新 shard 各接 20%）

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

Chunk migration 是 balancer 控制的 *background* job；搬移期間 query 照常執行，每個 chunk 搬完前的 commit 階段會短暫擋住寫入那個 chunk 的操作（見〈Balancer 跑 chunk migration 撞 production peak〉），CPU / network 上升 30-50%。

### Multi-DC expansion mechanism

```javascript
// 1. 對每 shard 的 replica set 加 us-west-2 member (priority 0)
rs.add({
  host: "us-west-2-host:27017",
  priority: 0,           // 不能當 primary
  votes: 1,              // 參與投票
  hidden: false
});

// 2. 等 initial sync 完成（依資料量 1 小時 - 1 天）：新 member 的 stateStr 從 STARTUP2 變成 SECONDARY
rs.status().members.map(m => ({ name: m.name, state: m.stateStr }));

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

整個流程的步驟如下；等 us-west member 完成 initial sync、兩個 DC 並行服務讀取、把 us-west 的讀取流量切過去，這三步是 parallel run 與流量切換：

| Step                          | 動作                                         | Parallel run?                                                       | Rollback boundary                |
| ----------------------------- | -------------------------------------------- | ------------------------------------------------------------------- | -------------------------------- |
| 1 Pre-check                   | 量化當前 topology、確認 cluster 健康         | no                                                                  | -                                |
| 2 加 us-east shard            | sh.addShard、balancer migrate chunk          | no（cluster 內）                                                    | removeShard、chunk migrate 回    |
| 3 加 us-west member           | 對每 shard rs.add 跨 DC member               | no                                                                  | rs.remove、initial sync 投入廢棄 |
| 4 **Initial sync wait**       | 等所有 us-west member catch up               | **parallel run 準備**：us-west member 仍在 initial sync、不服務讀取 | -                                |
| 5 **Cross-DC dual-serve**     | 兩 DC 都跑 read traffic（不切 write）        | **yes、parallel run**：app 用 secondary preferred us-west           | readPref 切回 us-east primary    |
| 6 **流量切換**                | application us-west traffic 走 us-west read  | **yes**                                                             | DNS / readPref 切回              |
| 7 Promote us-west（optional） | 一個 shard 的 us-west member priority 提到 1 | post-cutover                                                        | demote priority 回 0             |
| 8 Cleanup                     | Verify、archive log、document new topology   | no                                                                  | -                                |

Initial sync wait、Cross-DC dual-serve、流量切換這三步是 parallel run 與流量切換，做法跟 phased migration 的 parallel run 相同；其餘步驟都在 cluster 內部完成。

## Production 故障演練

### Balancer 跑 chunk migration 撞 production peak

**徵兆**：加 shard 後 balancer 開始 migrate chunk、production write latency p99 從 10ms 跳到 100ms；application 端 timeout 大量。

**根因**：MongoDB balancer 預設 24×7 跑、chunk migrate 是 *blocking* 操作（migration lock 期間阻塞 write 到該 chunk）；產線高峰時間 balancer 不會自動暫停。

**修法**：

```javascript
// 限 balancer 跑在 low-traffic window（balancer 設定存在 config database 的 settings collection）
sh.setBalancerState(true);
db.getSiblingDB("config").settings.updateOne(
  { _id: "balancer" },
  { $set: { activeWindow: { start: "02:00", stop: "06:00" } } },
  { upsert: true }
);
```

且設 `chunkSize` 較小（128MB → 64MB）讓 migration 步驟細、單次 lock 時間短。

### Cross-DC initial sync 期間 oplog 跑出窗口

**徵兆**：加 us-west member 後、initial sync 跑 4 小時、結束時 member 顯示「too stale to catch up」、需要 full re-sync。

**根因**：MongoDB oplog 是 capped collection、預設 size 5% disk；4 小時 initial sync 期間 primary 寫入量超出 oplog 保留範圍、member 拿到的 oplog start point 已被覆蓋。

**修法**：

1. **預先擴 oplog size**：`db.adminCommand({replSetResizeOplog: 1, size: 51200})` 加到 50GB、覆蓋 sync window
2. **Off-peak initial sync**：跑在低流量時間、oplog 寫入較慢
3. **用既有 member 的資料檔做 initial sync**：對一個 secondary 做 file system snapshot，把 data directory 複製到新 member 再啟動；新 member 只需從 snapshot 的時間點開始追 oplog，不必從頭複製資料

### 跨 DC read 路由錯誤、stale data 影響業務

**徵兆**：切流量到 us-west 後、application 偶爾抓到 5-30 秒前的 stale data；customer 報告「明明剛改了 setting、refresh 又變回去」。

**根因**：us-west member 是 secondary、replication lag 5-30 秒；application readPreference 設 `secondaryPreferred` 但沒 `maxStalenessSeconds`、可能讀到嚴重 stale member。

**修法**：

```javascript
const client = new MongoClient(uri, {
  readPreference: 'secondaryPreferred',
  readPreferenceTags: [{ region: 'us-west-2' }, {}],
  maxStalenessSeconds: 90,  // 排除落後超過 90 秒的 member；driver 接受的最小值就是 90
});

// 對 strict consistency 場景強制 primary
const client_strict = new MongoClient(uri, {
  readPreference: 'primary',  // 強制讀 us-east primary
});
```

Application-level read pattern 必須區分「accept stale read」vs「require fresh read」、不是 cluster-level 統一配置。5-30 秒的 lag 在 `maxStalenessSeconds` 容許的範圍內，所以「剛改完 setting、refresh 又變回去」要靠 require fresh read 那一類讀 primary（上面的 `client_strict`）解決；`maxStalenessSeconds` 只擋掉嚴重落後的 member。

### Shard tag-aware routing 沒設、cross-DC traffic 爆 cost

**徵兆**：multi-DC 跑了 1 個月、AWS egress cost 從 $500 / month 漲到 $8000 / month；99% 流量還是 us-east → us-west 跨 DC。

**根因**：sharded cluster 沒設 *zone sharding*、application 不知道哪些 chunk 在哪個 DC、所有 query 預設打 us-east primary、跨 DC bandwidth 爆。

**修法**：

```javascript
// sh.addShardToZone / sh.updateZoneKeyRange 取代舊的 sh.addShardTag / sh.addTagRange（3.4 起）
// myapp.events 的 shard key 是 { region: 1, _id: 1 }，zone range 要落在 shard key 上

// 1. 給 shard 加 zone
sh.addShardToZone("rs-shard1", "us-east");
sh.addShardToZone("rs-shard2", "us-east");
sh.addShardToZone("rs-shard3", "us-east");
sh.addShardToZone("rs-shard4", "us-west");
sh.addShardToZone("rs-shard5", "us-west");

// 2. 對 collection 加 zone range
sh.updateZoneKeyRange(
  "myapp.events",
  { region: "us-east", _id: MinKey },
  { region: "us-east", _id: MaxKey },
  "us-east"
);
sh.updateZoneKeyRange(
  "myapp.events",
  { region: "us-west", _id: MinKey },
  { region: "us-west", _id: MaxKey },
  "us-west"
);

// 3. balancer 重新分配 chunk 到對應 zone
```

Zone sharding 是 multi-DC 必要設計、不設等於白付 egress cost。

### Failover 後跨 DC primary 切換、application 連線中斷

**徵兆**：production 跑 6 個月後、us-east-1 outage、某 shard primary 切到 us-west member；application 5-10 秒內大量 connection error。

**根因**：replica set 的 `electionTimeoutMillis` 預設 10 秒（這是 replica set 的設定，不是 driver 的），選出新 primary 之前寫入沒有 primary 可送；application 的 server selection 等待時間與重試設定要涵蓋這段 election。

**修法**：

```javascript
const client = new MongoClient(uri, {
  serverSelectionTimeoutMS: 30000,    // driver 預設值：找不到 primary 時最多等 30 秒，涵蓋 election
  retryWrites: true,                  // driver 預設已開：寫入遇到 primary 切換自動重試一次
  retryReads: true,                   // driver 預設已開
  heartbeatFrequencyMS: 5000,         // 預設 10000；調短讓 driver 更早發現 topology 變動
});
```

且 multi-DC primary 應該設 *priority asymmetry*：us-east member priority 2、us-west priority 1；正常情況不切換、災難時自動切。

## Capacity / cost

| 維度                   | Single-DC 3-shard      | Multi-DC 5-shard                 | Trade-off                                |
| ---------------------- | ---------------------- | -------------------------------- | ---------------------------------------- |
| Node count             | 9                      | 25                               | ~3x infrastructure cost                  |
| Storage redundancy     | 3 replica              | 5 replica (3 east + 2 west)      | +2 copy、storage cost +66%               |
| Network egress         | 內部 VPC、低           | Cross-DC、高（需 zone sharding） | $500 → $8000 / month if no zone sharding |
| Latency p99 (write)    | 5-10ms                 | 5-15ms（primary 仍 us-east）     | 略升                                     |
| Latency p99 (read)     | 5-10ms                 | 2-5ms (local DC)                 | Multi-DC 區域 read 加快                  |
| Disaster recovery      | RTO 30 分鐘（rebuild） | RTO < 1 分鐘（auto failover）    | 顯著改善                                 |
| Operational complexity | 低                     | 高（zone sharding / DR drill）   | +1 SRE FTE 維護                          |

**判讀**：multi-DC 是 *DR 投資*、不是 cost optimization；只在 *availability SLA > 99.9% 或合規要求* 場景值得。

## 整合 / 下一步

### 跟 [MongoDB → Atlas migration](/backend/01-database/vendors/mongodb/migrate-to-atlas/) 對位

Self-managed multi-DC 複雜度高、Atlas 把 multi-cluster + cross-region 簡化成 UI 配置；如果走 multi-DC、考慮直接遷 Atlas。

### 跟 Application read pattern 整合

zone sharding + readPreference 跟 application logic 緊密耦合；不能事後補、應在 multi-DC 設計階段就設計 application 端的 region-aware routing。

### 跟 [Cassandra keyspace re-balance](https://cassandra.apache.org/) 對比

Cassandra 是另一個 multi-DC topology re-layout 的典型；用 *NetworkTopologyStrategy + replication factor per DC*、跟 MongoDB zone sharding 概念對等但 mechanism 完全不同。

### 下一步議題

- **Cross-region active-active**：MongoDB 不支援 multi-primary、cross-region active-active 需要 application-level conflict resolution
- **PostgreSQL Citus / CockroachDB multi-region** 對比：distributed SQL 對 multi-region 有不同設計
- **Cost optimization**：跨 DC egress 是 long-term concern、zone sharding 設好後仍要 quarterly review

## 相關連結

- 上游 vendor 頁：[MongoDB](/backend/01-database/vendors/mongodb/)
- 平行 migration playbook：[MongoDB → Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/)
- 其他 topology re-layout 的操作：[Redis Cluster Re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/) / [PostgreSQL Partition Redesign](/backend/01-database/vendors/postgresql/partition-redesign/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/) / [Data topology 是 process content 的 audit 維度](/report/data-topology-as-audit-dimension/)
