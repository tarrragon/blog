---
title: "MySQL Vitess Sharding：VTGate / VTTablet / VReplication / VSchema 四件套協作"
date: 2026-05-19
description: "Vitess 不只是 MySQL sharding proxy、是 4 個 component 協作的完整 sharding 系統 — VTGate（query routing layer）、VTTablet（per-MySQL agent）、VReplication（跨 shard 資料移動）、VSchema（sharding metadata）。本文走 4 件套各自責任、keyspace / shard / tablet 架構、shard key 設計（Vindex）、配置 step-by-step、5 production 踩雷（cross-shard transaction / VStream lag / Vindex 不均勻 / resharding 切流 / VReplication 卡住）、跟自管 sharding 跟 PlanetScale 的對比"
weight: 18
tags: ["backend", "database", "mysql", "vitess", "sharding", "deep-article"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) overview 的 implementation-layer deep article。Overview 已說明 MySQL 在 OLTP 譜系的定位、本文聚焦 *Vitess sharding* — 4 個 component 協作的完整 sharding 系統。

---

## 問題情境：MySQL 寫吞吐撞上 single primary 上限

MySQL primary 單機極限大致 50K-100K WPS（依 schema / hardware）。超過這個級別、選項三條：

1. *Application 層 sharding*：每張 table 自己決定怎麼分片、application 寫 routing logic、跨 shard query / migration 都要自己處理
2. *Vitess*：proxy layer 自動 routing、cross-shard query 可選自動 split、resharding 自動化
3. *Distributed SQL*（CockroachDB / Spanner / Aurora DSQL）：跟 MySQL 不同 engine、application 改 driver

選 Vitess 的核心 driver：*保留 MySQL wire protocol + 應用層幾乎不必改 + 透明分片*。代價是 4 個 component 的 operational complexity — Vitess 的責任範圍是完整分散式系統，而非單純 proxy。

閱讀本文前可先對齊 [Database Sharding](/backend/knowledge-cards/database-sharding/) 的 shard key、routing、resharding 與 cross-shard query 語意；容量失衡時再接 [Hot Partition](/backend/knowledge-cards/hot-partition/)。

## Vitess 四件套：每個 component 的責任

```text
                        ┌─────────────────┐
   Application ────→    │     VTGate      │  ← 對外 MySQL wire protocol
                        │  (proxy + parse + route + aggregate)  │
                        └────┬─────┬──────┘
                             │     │
                ┌────────────┘     └──────────────┐
                ▼                                 ▼
        ┌──────────────┐                  ┌──────────────┐
        │   VTTablet   │                  │   VTTablet   │
        │ (per-MySQL   │                  │ (per-MySQL   │
        │  sidecar)    │                  │  sidecar)    │
        └─────┬────────┘                  └─────┬────────┘
              │                                 │
              ▼                                 ▼
        ┌──────────────┐                  ┌──────────────┐
        │    MySQL     │                  │    MySQL     │
        │  (Shard -80) │                  │  (Shard 80-) │
        └──────────────┘                  └──────────────┘

   Topology Service (etcd / Consul / ZooKeeper)
   ↑↓ 所有 component 共享 metadata
   VSchema：keyspace 結構、shard 範圍、Vindex 定義
```

### VTGate — query routing layer

對 application 看起來像 MySQL（同樣 port、同樣 wire protocol、同樣 query 語法）、實際是 stateless proxy。每個 query VTGate：

1. Parse SQL → 找出 routing key（從 WHERE column 拿）
2. 查 VSchema → 計算 routing key 對應的 shard
3. 把 query 送該 shard 的 VTTablet
4. 等 response、aggregate（如果是 cross-shard query）、回 application

Stateless 設計 → VTGate 可以隨意 scale、放 N 個前面接 LB。多數 production 部署 3-10 個 VTGate per region。

### VTTablet — per-MySQL agent

每個 MySQL instance 旁邊都跑一個 VTTablet。VTTablet 責任：

- 把 MySQL primary 標記、上報給 topology
- 接 VTGate 的 query、轉發給 local MySQL
- 跑 *connection pool*（VTGate 跟 VTTablet 之間少量連線、VTTablet 跟 local MySQL 共享 connection）
- 跑 *query plan cache* / *transactional consistency check*
- 處理 *online schema change*（Vitess 內建 OSC）
- 跟 VTOrc（fork of Orchestrator）配合做 failover

VTTablet 是 Vitess 跟 MySQL 唯一連接點 — 沒 VTTablet 直接連 MySQL 不在 Vitess 管理下。

### VReplication — 跨 shard 資料移動

VReplication 是 Vitess *跨 shard / 跨 keyspace / 跨 cluster* 資料移動引擎、底層用 MySQL binlog。用途：

- *Resharding*：把 shard -80 拆成 -40 + 40-80、VReplication 自動拆 binlog event 對應 shard
- *Materialized view*：cross-shard aggregation 預計算
- *MoveTables*：跨 keyspace 移 table（schema-level migration）
- *VStream*：CDC、binlog event 對外輸出（可接 Kafka / Debezium）

VReplication 的主要使用者是 *Vitess operator*，它和 application 行為直接相關（resharding 期間有 write split 行為）。

### VSchema — sharding metadata

VSchema 是 keyspace 內 *哪張 table 怎麼 shard* 的定義、JSON 格式存 topology service。例子：

```json
{
  "sharded": true,
  "vindexes": {
    "hash": {
      "type": "hash"
    }
  },
  "tables": {
    "orders": {
      "column_vindexes": [
        {
          "column": "user_id",
          "name": "hash"
        }
      ]
    },
    "users": {
      "column_vindexes": [
        {
          "column": "user_id",
          "name": "hash"
        }
      ]
    }
  }
}
```

`orders.user_id` 跟 `users.user_id` 用同一個 Vindex（hash）+ 同一個 column → 同 user_id 的 orders + users 落在同 shard、可以 JOIN 不跨 shard。

## Vindex：Vitess 的 sharding function

Vindex 是 Vitess 的 *shard key 計算函數*。內建多種：

| Vindex 類型            | 計算方式                                         | 適用                                   |
| ---------------------- | ------------------------------------------------ | -------------------------------------- |
| `hash`                 | 3DES-based null hash（非 MD5）→ 對應 shard range | 預設、均勻分布、適合 primary key       |
| `binary_md5`           | MD5(binary)                                      | binary key                             |
| `unicode_loose_xxhash` | xxHash on lowercased unicode                     | string key                             |
| `numeric`              | 直接 numeric value                               | 連續 numeric range（適合 time-based）  |
| `numeric_static_map`   | 預定義 map                                       | 國家 code / region 等少 enum           |
| `lookup_hash`          | 透過 lookup table 查 shard                       | 多個 column 都要 shard、需要二級 index |

最常用：`hash`（primary key）+ `lookup_hash`（secondary access pattern）。

## Keyspace / Shard / Tablet 階層

```text
Keyspace (邏輯 database)
   └── Shards
        ├── -80 (shard range 0-128)
        │     ├── Primary tablet (1 MySQL primary)
        │     ├── Replica tablet × 2
        │     └── RDOnly tablet × 1 (analytics)
        └── 80- (shard range 128-256)
              ├── Primary tablet
              ├── Replica tablet × 2
              └── RDOnly tablet × 1
```

Shard range 用 *binary hex prefix*（`-80` 表示 0 到 0x80、`80-` 表示 0x80 到 max）— 給 resharding 留 split 餘地（`-80` 可切成 `-40` + `40-80`）。

Tablet type：

- *Primary*：寫入入口
- *Replica*：read traffic（Vitess query rules 控制）
- *RDOnly*：純 analytics / backup / VReplication source、低 SLA、不上 production read traffic

## 配置 step-by-step（local cluster）

Production 通常用 Kubernetes operator（vitess-operator）部署、但理解概念用 local cluster 最快：

```bash
# 用 vtctldclient 操作（替代舊的 vtctlclient）

# 1. 建 unsharded keyspace
vtctldclient CreateKeyspace --durability-policy=semi_sync commerce

# 2. 從一個 MySQL primary 開始（unsharded）
vtctldclient ApplySchema --sql="CREATE TABLE orders (id INT PRIMARY KEY, user_id INT)" commerce

# 3. 把 keyspace 改成 sharded、定義 VSchema
vtctldclient ApplyVSchema --vschema='{
  "sharded": true,
  "vindexes": {"hash": {"type": "hash"}},
  "tables": {
    "orders": {
      "column_vindexes": [{"column": "user_id", "name": "hash"}]
    }
  }
}' commerce

# 4. 觸發 resharding：unsharded → 2 shards (-80, 80-)
vtctldclient Reshard --workflow=initial-shard create \
  --source-shards="commerce/0" \
  --target-shards="commerce/-80,commerce/80-"

# 5. 等資料 copy 完（VReplication 跑）
vtctldclient Workflow --keyspace=commerce show initial-shard

# 6. SwitchTraffic：先切 RDOnly → 再切 Replica → 最後切 Primary
vtctldclient Reshard --workflow=initial-shard switchtraffic \
  --tablet-types="rdonly,replica"
vtctldclient Reshard --workflow=initial-shard switchtraffic \
  --tablet-types="primary"

# 7. 完成、cleanup old shard
vtctldclient Reshard --workflow=initial-shard complete
```

實際 production 走 *Vitess Kubernetes operator*、用 `VitessCluster` CRD 宣告 desired state、operator 自動操作上面這些 step。

## 5 個 Production 踩雷

### 1. Cross-shard transaction — Vitess 不支援 atomic（預設）

兩個 user 的 order 在不同 shard、`BEGIN; UPDATE orders WHERE user_id=1; UPDATE orders WHERE user_id=2; COMMIT;` 跨兩個 shard。Vitess 預設 *不保證 atomic* — 兩個 shard 各自 commit、可能一個成功一個失敗、application 看到 partial state。

修法：

- *避免 cross-shard transaction*：schema design 讓 transaction boundary 落在單一 shard 內
- 啟用 *atomic 2-phase commit*（Vitess `transaction_mode=TWOPC`、實驗性、performance penalty 大）
- 大規模需要 atomic 的場景應該換 distributed SQL（CockroachDB / Spanner），讓資料庫層承擔跨節點一致性

### 2. VStream lag — Resharding 期間 CDC 落後

Resharding 過程 VReplication 大量寫 binlog event、application *本來在用* 的 VStream（接 Kafka 等）共享同 binlog stream、可能 lag。Downstream consumer 看到 stale data 1-2 小時。

修法：

- Resharding 期間 *暫停非關鍵 VStream*（analytics ETL 可暫停、real-time recommendation 需要保留）
- 確認 binlog disk capacity > resharding 期間預估 binlog 量 × 2（buffer）
- Resharding 完成後 *手動驗證* VStream offset 已 catch up，把驗證結果留成 cutover evidence

### 3. Vindex 不均勻 — Hot shard

Vindex 預設 `hash` 對 *primary key 均勻分布*、但對 *natural key*（country / region / company_id 等）可能不均勻。10 個 country、其中 1 個 country 佔 80% traffic、單一 shard 永遠 hot。

修法：

- *Composite Vindex*：combine `country + user_id` 兩 column 作為 shard key、user-level 仍均勻
- *Synthetic shard key*：application 層加 `sharding_key=hash(actual_key) % N`、控制分布
- 監控 *per-shard QPS*：`vtctldclient ShowVDiff` + Prometheus exporter
- Hot shard 出現後 Vitess 可以 resharding 解（split hot shard 為 2 個小 shard）、但工作量大

### 4. Resharding 切流量瞬間 deadlock

Resharding 最後的 SwitchTraffic 切 primary 階段、舊 shard 仍接 write、Vitess 切 routing、Application 一瞬間連兩個 shard、相同 user_id 寫入可能跑兩邊、deadlock 或 lost update。

修法：

- *SwitchTraffic 用 ReverseTraffic 預備*：先 switch、確認問題後可 reverse 回去
- 切流量 *只在 known quiet period*（夜間 / 週末早上）
- VTGate `--retry-count=2` + `--track-vtgate-deadlock-events`：deadlock 自動 retry、不暴露給 application
- 真的失敗用 `Reshard cancel` 回 old state，讓 workflow 回到可驗證狀態

### 5. VReplication workflow 卡住 — cancel 前需要保護狀態

VReplication workflow 跑到 50% 但 *某個 row 解析錯誤*（schema mismatch / blob 大小超過 limit）、workflow stuck、進度條卡住、無 timeout。整個 resharding flow halt。

修法：

- 平時跑 *staging 資料 dry-run*、發現 schema 跟 blob 邊界問題
- Workflow 卡住時 `vtctldclient Workflow show` 看 last_message / row_state
- 手動修問題 row（直接 MySQL 改）後 *resume workflow*
- 大 cluster 建議 *VReplication 跑前先 SchemaApply audit*、確認 source / target schema 兼容

## Vitess 跟自管 sharding 對照

| 維度                       | Vitess                            | Application-level sharding                        |
| -------------------------- | --------------------------------- | ------------------------------------------------- |
| Application 改動           | 幾乎不必（保留 MySQL wire）       | 大改（routing logic 寫 application）              |
| Cross-shard query          | VTGate 自動 split（受限）         | Application 自己處理                              |
| Resharding                 | VReplication 自動                 | 手寫腳本、操作複雜                                |
| Online schema change       | Vitess 內建（VReplication-based） | 用 gh-ost / pt-osc                                |
| Failover                   | VTOrc 整合                        | 自管 Orchestrator                                 |
| Operational cost           | 高（4 component 要懂）            | 中（fewer abstractions、但 application logic 多） |
| Cross-keyspace 共用 vindex | 內建（lookup_hash 跨 keyspace）   | 自寫                                              |

Vitess 的 *operational complexity* 是它的代價。10-20 人 SRE 團隊撐得住、5 人團隊用 *managed Vitess（PlanetScale）* 更實際。

## 跟其他模組整合

### 跟 Replication topology

Vitess shard 內部仍用 MySQL replication（[Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)）— 每個 shard 有 primary + replica + rdonly。Vitess durability-policy 控制 primary 寫入是否等 replica ack（semi-sync）。

### 跟 OSC tool

Vitess *不用 gh-ost / pt-osc*、用 VReplication-based online DDL。Vitess online DDL：

```bash
vtctldclient ApplySchema --strategy=vitess \
  --sql="ALTER TABLE orders ADD COLUMN status VARCHAR(20)" commerce
```

詳見 [Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)。

### 跟 ProxySQL

*Vitess 取代 ProxySQL*。VTGate 本身做 connection pool + query routing、不再需要 ProxySQL。混用會造成 routing 衝突（VTGate 期待自己決定 shard、ProxySQL 跟 VTGate 競爭）。詳見 [ProxySQL 配置](/backend/01-database/vendors/mysql/proxysql-config/)。

### 跟 Orchestrator

Vitess 用 *VTOrc*（fork of Orchestrator）作 failover、跟 Vitess topology metadata 整合。不用獨立 Orchestrator。詳見 [Orchestrator failover 設計](/backend/01-database/vendors/mysql/orchestrator-failover/)。

### 跟 PlanetScale（managed Vitess）

PlanetScale 是 *Vitess managed service*、隱藏 4 component operational complexity、加 branch-based schema workflow。詳見 *→ PlanetScale migration playbook* 篇（待寫）。

### 跟 Aurora MySQL

Aurora 跟 Vitess 是 *不同 scale 路徑*：

- Aurora：single-region scaling（storage / compute 分離、最高 ~128 TB）
- Vitess：horizontal sharding（無上限、靠加 shard scaling）

兩者承擔的容量與操作責任不同。超過 Aurora single-region 上限的場景才考慮 Vitess。詳見 [Aurora vendor page](/backend/01-database/vendors/aurora/)。

## 何時用 Vitess

| 條件                                        | 評估                                 |
| ------------------------------------------- | ------------------------------------ |
| 流量 > 50K WPS、單 primary 撐不住           | 是 Vitess scope                      |
| 已有大量 MySQL 投資、不想換 distributed SQL | 是                                   |
| 有 5-10 人 SRE / DBA 團隊                   | 是                                   |
| 流量 < 10K WPS                              | 否（過度設計、用單 MySQL + replica） |
| 5 人團隊、不想養 DBA                        | 否（用 PlanetScale managed）         |
| 必須 multi-region 強一致 transaction        | 否（CockroachDB / Spanner 才對）     |
| 需要複雜 cross-shard analytics              | 否（搭配 BigQuery / Snowflake）      |

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（Vitess shard 內部）
- [MySQL Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)（Vitess 不用 gh-ost / pt-osc）
- [MySQL ProxySQL 配置](/backend/01-database/vendors/mysql/proxysql-config/)（Vitess 取代 ProxySQL）
- [MySQL Orchestrator failover](/backend/01-database/vendors/mysql/orchestrator-failover/)（VTOrc fork）
- [PostgreSQL Citus Distributed](/backend/01-database/vendors/postgresql/citus-distributed/)（PG sibling、coordinator + worker 模型 vs Vitess VTGate + tablet）
- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)（Vitess vs CockroachDB vs Spanner）
- [Database Sharding](/backend/knowledge-cards/database-sharding/)（shard key、routing、resharding 與 cross-shard query）
- 官方：[Vitess Documentation](https://vitess.io/docs/) / [Vitess Operator](https://github.com/planetscale/vitess-operator)
