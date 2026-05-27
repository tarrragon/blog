---
title: "CockroachDB HLC + Raft Consensus：軟體時鐘 + per-range 共識的 latency 與容量結構"
date: 2026-05-27
description: "CockroachDB 用 Hybrid Logical Clock + per-range Raft 做跨節點線性化、不靠 TrueTime 原子鐘。本文走 HLC / Raft / range / leaseholder 四層機制、寫入 latency 構造、failure mode（clock skew panic / Raft majority lost / hot range）、引用 DoorDash Aurora 撞牆訊號（1.636 M QPS 屬 Aurora 痛點而非 CockroachDB 容量證明）+ Netflix 380+ artery of small DBs 容量規劃顆粒"
weight: 30
tags: ["backend", "database", "cockroachdb", "distributed-sql", "consensus", "raft", "hlc", "deep-article"]
---

> 本文是 [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/) 的 implementation-layer deep article。Overview 已界定 CockroachDB 在 distributed SQL 譜系的定位、本文聚焦 *HLC + Raft + range + leaseholder 四層機制* — 解釋為什麼 distributed SQL 的 latency / 容量曲線跟 PostgreSQL single-primary 完全不同、以及怎麼從 production 訊號倒推它對團隊的成本結構。寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

---

## 為什麼這篇先講 HLC + Raft

團隊評估 CockroachDB 替代 PostgreSQL streaming replication 時、會同時看到兩個訊號：「跨 region 強一致」很吸引人、「每次寫都經過 Raft majority」又讓人害怕。前者是賣點、後者是成本結構 — 不先把 HLC / Raft / range / leaseholder 拆清楚、後面講 survival goal、locality、transaction retry 都會卡在「為什麼這個機制存在」這層。

讀者最常問的三題：

- Spanner 用 TrueTime 原子鐘做線性化、CockroachDB 沒硬體時鐘怎麼保證 ordering？
- Raft 每次寫要等 majority ack、不是比 PostgreSQL 慢得多？
- HLC clock skew 真的大會發生什麼？節點隨機 panic 嗎？

三題都不只是 spec 問題、而是 *production 容量規劃跟 incident 訊號的根本前置*。

問題情境最常見的 trigger：[9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/) 在 2020-04-17 高峰 Aurora Postgres 撞到 1.636 M QPS、multi-hour outage。**這個數字是 Aurora 在那個時間點撞牆的痛點、case 自己警示「不是 CockroachDB 撐到 1.636 M QPS 的 throughput claim」**。case 沒揭露遷移後單一 CockroachDB cluster 的峰值、只說「跑更多 cluster、alert volume 反而下降」。要把 CockroachDB 當寫入容量解法評估、就得先理解 Raft per range 怎麼把寫入從 single-primary 分散到多 node。

[9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) 則提供另一條訊號：380+ cluster / 60+ multi-region、最大單區 cluster 60 nodes / 26.5 TB。這個規模證明 Raft 維運在 production 可承擔、但也揭露容量規劃顆粒不是「全公司一條容量曲線」、是「每 cluster 各自規劃」— artery of small DBs。

## 核心機制：HLC + Raft + range + leaseholder 四層

CockroachDB 的線性化保證來自四層機制疊加、缺一層都解釋不通實際 latency / failure 行為。

### HLC：軟體時鐘把 wall clock + logical counter 混在一起

Hybrid Logical Clock 結合 *physical time*（NTP 同步的牆鐘）跟 *logical counter*（單調遞增的事件序號）、給每個事件一個 `(physical, logical)` timestamp。對比 Spanner TrueTime 直接靠 GPS + atomic clock 給「時鐘 uncertainty bound」、CockroachDB HLC 不依賴硬體、用軟體保證「節點之間時鐘最多差 `max-offset`（default 500ms）、超過就 panic」。

```text
Node A 收到 write at wall=12:00:00.123, last_seen=12:00:00.100
  → HLC = (12:00:00.123, 0)

Node A 收到 RPC from B at wall=12:00:00.140, B.HLC=(12:00:00.200, 5)
  → A 跳到 B 的 physical (12:00:00.200)、logical = 6
  → HLC = (12:00:00.200, 6)
```

HLC 的契約 *只要節點間時鐘差不超過 max-offset、所有 transaction 仍是 linearizable*。production 必跑 NTP / chronyd — 一旦本機時鐘飄超過 500ms、節點自動 panic 保護 cluster 一致性、不會發出錯誤 commit。

跟 Spanner TrueTime 對比：

| 維度        | CockroachDB HLC                | Spanner TrueTime                        |
| ----------- | ------------------------------ | --------------------------------------- |
| 硬體依賴    | 無（純軟體 + NTP）             | GPS + atomic clock（每資料中心配）      |
| Uncertainty | 由 max-offset 上界、固定 500ms | 動態 uncertainty interval（通常 < 7ms） |
| Commit 等待 | 不需要 wait out uncertainty    | 需要 wait out（commit-wait）            |
| 部署彈性    | 任何雲 / on-prem 都可跑        | 只在有 TrueTime infra 的 GCP region     |

兩條路徑解同一個 *event ordering* 問題、用不同 trade-off。CockroachDB 把硬體成本換成軟體 max-offset 容忍度、結果是「可以跨雲跨 on-prem 跑、但 NTP 維運是必要條件」。

### Raft：每個 range 一個獨立的 majority consensus group

Raft 把寫入流程切成 *propose → replicate to majority → commit* 三段。每個 range 維護自己的 Raft group、預設 3 replica、寫入要至少 2 個 replica ack 才能 commit。

```text
Client → Leaseholder (Raft leader)
   1. Propose log entry (write intent)
   2. Replicate to 2 follower replicas
   3. Wait for majority ack (本身 + 1 個 follower)
   4. Commit、apply to state machine
   5. Reply to client
```

關鍵差異跟 PostgreSQL streaming replication 比：

- PostgreSQL primary：1 個節點 ack 就 commit（async replication）、replica 可能落後
- PostgreSQL sync replication：1 個 standby ack 才 commit、但仍是「primary 是 single point of write」
- CockroachDB Raft：majority（2 of 3）ack 才 commit、任何 replica 都可以是 leaseholder、寫入分散到所有節點

寫入 latency 因此 *結構性* 高於 PostgreSQL — 多了一次 cross-node round trip。但寫入 *吞吐* 可以線性擴展、因為不同 range 的 Raft group 跑在不同節點上。

### Range：把 key space 切成 ~512 MB 的可分裂單位

CockroachDB 把整個 key space 切成 range、每個 range 預設上限 ~512 MB、超過自動 split。每個 range 是一個獨立的 Raft group、有自己的 3 replica 分佈。

對比其他 distributed DB 的等價概念：

- DynamoDB partition：固定 hash 分區、自動 split 但 hot partition 容易撞 ceiling
- Spanner split：類似 range、但配置 / placement 語法不同
- Vitess keyspace：application 端決定 shard key、不透明 split

CockroachDB range 是 *系統內建透明* 的 — application 只看到 SQL table、不需要 shard key 設計。但 hot range 仍會發生（後面 failure mode 段展開）。

### Leaseholder：每個 range 的 read / write entry point

每個 range 在任一時間點有一個 leaseholder（通常等於 Raft leader）、承擔該 range 的所有 read / write coordination。leaseholder 也是 *follower read* 的 timestamp 邊界 holder。

leaseholder 概念對 production 訊號的影響：

- 寫入 latency 主要來自 leaseholder → follower replicas 的 Raft round trip
- leaseholder 集中在某節點 → 該節點 CPU 飽和（hot range 的根因之一）
- leaseholder 換手（lease transfer）短期 p99 spike — rebalance 期間 / 節點 graceful drain 都會觸發

## 操作流程：配置 + 驗證 + rollback 邊界

### Cluster 起手配置

最小可運行配置是 3 節點（Raft quorum 下界）、production 通常 9 節點以上（3 region × 3 replica）。每個節點啟動時必須帶 locality tag、讓 Raft placement 知道副本怎麼分佈：

```bash
cockroach start --insecure \
  --locality=region=us-east1,zone=us-east1-a \
  --max-offset=500ms \
  --join=node1:26257,node2:26257,node3:26257
```

`--max-offset` 是 HLC 容忍上界、超過會 panic — 不要為了「避免 panic」加大這個值、會犧牲 linearizability 保證。

NTP / chronyd 是 *必要前置*、不是 nice-to-have。production 應該在每個節點配置：

- NTP server 至少 3 個獨立 source（避免單一 server drift）
- 監控 `chronyc tracking` 的 offset、超過 100ms 就應該 alert（遠在 500ms panic 邊界之前）

### 驗證點

```sql
-- 看每節點當前 clock offset 跟 cluster 其他節點
SELECT node_id, address, offset_min_nanos, offset_max_nanos
FROM crdb_internal.gossip_nodes;

-- 看 Raft 健康（每個 range 的 leaseholder 跟 replica 分佈）
SELECT range_id, lease_holder, replicas
FROM crdb_internal.ranges
WHERE table_name = 'orders'
LIMIT 5;

-- 看 cluster max-offset 設定
SHOW CLUSTER SETTING server.clock.persist_upper_bound_interval;
```

### Rollback 邊界

HLC + Raft 對 rollback 的態度跟 PostgreSQL 不同：

- HLC 時鐘前進不可回滾 — 不能「改一下 max-offset 後重啟試試看」
- Raft commit 不可回滾 — 一旦 majority ack、log entry 持久化
- 想還原業務狀態 *只能新交易補償*、不能 reverse Raft log

實務上的影響：incident 時不要嘗試「強制回到舊版本」、應該走 transaction-level rollback / compensation。對應 [transaction boundary 卡](/backend/knowledge-cards/transaction-boundary/) 跟業務層補償設計。

## 失敗模式：clock skew / majority lost / hot range / retry storm

### Clock skew panic

最常見：NTP 服務掛、節點時鐘漂移超過 max-offset、節點自動 panic。production incident 訊號：

- `chronyc tracking` 顯示 offset 持續成長
- CockroachDB log 出現 `clock synchronization error`
- Prometheus metric `clock_offset_meannanos` 接近 max-offset

修法：先恢復 NTP service、節點重啟前再次驗證時鐘已同步、不要動 `--max-offset`。對比 PostgreSQL primary 不關心 time skew、distributed SQL 把時鐘變成 first-class operational concern。

### Raft majority lost

3 節點 cluster 失去 2 個、剩 1 個無法 commit、cluster 全 read-only（甚至連 read 都可能受影響、因為 leaseholder 拿不到 valid lease）。對比 PostgreSQL primary 失效後 streaming replica 仍可 read、CockroachDB 的 fault tolerance 是 *quorum-based*、不是 *primary-replica*。

production 規劃要點：跨 AZ / region 分佈時、必須保證任何 *單一 failure domain* 失敗後仍有 majority 存活。3 節點配 1 AZ → AZ 失敗 = cluster down。最小 production 配置是 3 AZ × 1 node 或 3 region × 3 node。

### Hot range：leaseholder 節點 CPU 飽和

某個 range 寫流量集中（例：訂單 table primary key 是時間序 / 自增 ID）、leaseholder 節點變成熱點。徵兆：

- CockroachDB Console「Leaseholder count per node」分佈不均
- 某節點 CPU 飽和、其他節點閒置
- `crdb_internal.ranges` 顯示該 range 的 QPS 遠高於其他 range

修法：

- 手動 `ALTER TABLE ... SPLIT AT VALUES (...)` 強制 split hot range
- 改 primary key 設計、避免時間序 / 自增 ID（用 UUID / hash-prefixed key）
- partition by region、把 hot range 切到不同 region 的 leaseholder

### Transaction retry storm

serializable contention 嚴重時 application 端 retry loop、CPU 雪崩。這個議題的 application contract 重塑屬獨立議題、見 [transaction retry pattern](../transaction-retry-pattern/)。

### Range split / rebalance 期間 p99 spike

自動 split 大 range、leaseholder 換手期間有 ~100ms 的 lease transfer 視窗、p99 短期 spike。production 訊號：CockroachDB Console「Rebalance queue size」非零 + p99 latency 同期波動。一般是良性 — rebalance 完就回穩。但連續波動代表 range 在「split → 寫熱 → 再 split」循環、要從 schema 層解。

## 容量與觀測：per-cluster 顆粒 + 來源分層

### 必看 metric

- `Raft log queue size`：Raft replication 延遲訊號、持續高代表 follower 跟不上
- `Range count per node`：range 分佈是否均勻、不均代表 placement 有偏
- `Leaseholder count per node`：leaseholder 分佈是否均勻、不均直接導致 CPU 熱點
- `HLC offset distribution`：時鐘同步健康
- `Transaction retry rate`：contention 訊號（細節在 [transaction retry pattern](../transaction-retry-pattern/)）

### Per-cluster 容量規劃顆粒（9.C40 Netflix 揭露、F4.7）

Netflix 的 380+ cluster 模型揭露一個反直覺結論：production scale 不是「全公司一條容量曲線」、而是 *artery of small DBs*。每個 cluster 對應一個 application boundary、cluster sizing 從幾個 node 到 60 nodes 不等、最大單區 60 nodes / 26.5 TB（case 觀察段表格揭露）。

容量規劃顆粒對齊 application boundary 的好處：

- 每個 cluster 各自規劃 capacity、不必預測「全公司加總 QPS」
- blast radius 限縮在單一 app — 某 cluster 撞 hot range / Raft majority lost、其他 cluster 不受影響
- upgrade / backup 可分批跑、不必整廠 maintenance window

但也帶來 ops 成本：380+ cluster 需要 *專屬 Database Platform Team*（含 backup、upgrade、incident response、capacity review）— Netflix case 直接揭露這個前置條件。沒這量級團隊就走 Cockroach Cloud managed、不要 self-host。

per-app cluster vs shared cluster 的決策軸主寫於 [aurora-dsql-spanner-decision-tree](../aurora-dsql-spanner-decision-tree/)、本篇 cross-link 不展開。

### 寫入 latency 預算（屬通用工程估算、case 未揭露具體數字）

以下數字屬通用工程估算 / 物理光速下界推導、**DoorDash / Netflix / Hard Rock 三個 direct case 都沒揭露單一 cluster p99 latency**。引用時必須明示來源層次：

- single-region 3-replica write p99 3-5ms（通用估算、跨 AZ Raft round trip）
- multi-region 跨洲 write p99 100-150ms（光速下界 — 跨洲 round trip 物理 ~70-80ms × 2）
- 單一 range 寫 throughput ~1000 QPS（通用估算、實際依 row size / contention 而定）
- 整 cluster scale-out 加 range、寫入吞吐近線性擴展（理論、實際依 hot range 分佈）

這些是「合理的工程估算量級」、不是 case 揭露的 p99 數字。讀者用這些做容量規劃時、應該 *自己 benchmark* 而不是直接套。

### DoorDash 1.636 M QPS 引用紀律（F4.1、case 自帶警示）

DoorDash case 揭露的 1.636 M QPS 是 *Aurora Postgres single-primary 在 2020-04-17 高峰撞牆的痛點*（multi-hour outage）、**不是 CockroachDB throughput claim**。case 明確警告不要把這個數字當「CockroachDB 撐 1.636 M QPS 的證據」。case 沒揭露遷移後單一 CockroachDB cluster 的峰值、只說「跑更多 cluster、alert volume 反而下降」。

引用這個數字時的口徑：

- 寫成「Aurora 撞牆訊號」、不寫成「CockroachDB 容量證明」
- single-primary 撞牆的轉折點是 *primary CPU + WAL flush rate*（DoorDash 策略段 1）、不是 IOPS
- 「換引擎」前先評估「兩階段紓壓」— DoorDash 路徑是先把 hot table 拆到獨立 Aurora cluster（紓壓）、再規劃 Aurora → CockroachDB 換引擎（[01.4 database migration playbook](/backend/01-database/database-migration-playbook/)）

### 回路徑

- [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 判斷 Raft-bound vs storage-bound
- [9.6 容量規劃模型](/backend/09-performance-capacity/) replication factor × latency budget
- [latency budget 卡](/backend/knowledge-cards/latency-budget/) cross-region quorum 預算

## 邊界與整合

### Sibling deep articles

- [CockroachDB survival goals](../survival-goals/)：Raft replica 怎麼分佈到 zone / region、決定 RTO / RPO
- [CockroachDB transaction retry pattern](../transaction-retry-pattern/)：serializable default 對 application 契約的重塑
- [CockroachDB locality-aware schema](../locality-aware-schema/)：range placement 控制 + locality 配置

### 跟 Aurora 對照

Aurora 是 *storage-level quorum*（4 of 6 storage replica）、compute 仍是 single primary。CockroachDB 是 *range-level Raft*（每個 range 獨立 majority）、compute 跟 storage 在每節點。兩者解的是不同 layer 的 consensus、結果是 Aurora 寫入仍受 primary 限制、CockroachDB 寫入隨節點線性擴。

### Aurora DSQL / Spanner 對比

完整三家 distributed SQL 對比、撞牆訊號分型、PostgreSQL 相容性 audit、團隊規模 vs vendor sizing barrier 等議題在 [aurora-dsql-spanner-decision-tree](../aurora-dsql-spanner-decision-tree/)。

### 1.x 章節互引

- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 上游選型
- [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) distributed transaction 邊界

### 何時不用本文

- single-region OLTP + 寫入未撞 PostgreSQL primary 天花板 → PostgreSQL 已足夠
- 對 cross-region quorum 100-150ms latency 預算無法接受 → 走 async replication 路線
- 沒 NTP 維運能力 → distributed SQL 把時鐘變 ops concern、沒準備好不要硬上

## 相關連結

- [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/)
- [9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/)（Aurora 1.636 M QPS 撞牆訊號）
- [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（380+ cluster artery of small DBs）
- [9.C10 Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)（TrueTime 對照）
- [distributed SQL 卡](/backend/knowledge-cards/distributed-sql/)
- [quorum 卡](/backend/knowledge-cards/quorum/)
- 官方：[CockroachDB Architecture](https://www.cockroachlabs.com/docs/stable/architecture/overview.html) / [Hybrid Logical Clocks paper](https://cse.buffalo.edu/tech-reports/2014-04.pdf) / [Raft paper](https://raft.github.io/raft.pdf)
