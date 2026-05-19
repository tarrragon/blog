---
title: "MySQL Group Replication / InnoDB Cluster：single-primary vs multi-primary mode 對 transaction certification 的影響"
date: 2026-05-19
description: "MySQL Group Replication 提供 synchronous multi-primary replication、用 Paxos-like Group Communication Engine（GCE）達成 quorum-based commit。但「multi-primary」不是「single-primary 多開幾個 write 入口」、是 *transaction conflict detection + certification* 整個機制不同。本文走 GR 機制（GCE + certification + applier）、single-primary vs multi-primary mode、InnoDB Cluster 跟 MySQL Shell / Router 整合、5 production 踩雷（cert lag / write conflict / large transaction / network partition / member 加入 catch-up）、何時用 GR 何時用傳統 replication"
weight: 20
tags: ["backend", "database", "mysql", "group-replication", "innodb-cluster", "ha", "deep-article"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) overview 的 implementation-layer deep article。Overview 已說明 MySQL 在 OLTP 譜系的定位、本文聚焦 *Group Replication + InnoDB Cluster* — synchronous multi-primary 的 transaction model + 部署模型。

---

把「Group Replication multi-primary mode」當成「multi-primary 直接線性 scale write」是常見誤解。

Single-primary 跟 multi-primary 共用同一套 GR 機制（GCE atomic broadcast + certification + applier）— 切換 mode 是 *配置變更*。但 *性能效果* 經常跟讀者預期不同：在 single-primary cluster 上加開 `group_replication_single_primary_mode=OFF`、預期 *3 個 instance 都可以接受 write* 帶來吞吐倍增、實際上每個寫入仍要全 cluster GCE broadcast + certification、寫吞吐沒爆增 / latency 飆高 / certification 衝突回退增加。

這篇 deep article 把 GR 的 *certification 流程* 講清楚 — 為什麼「multi-primary」聽起來像「線性 scale」、實際是「保 strong consistency 的 multi-entry」。然後展開 InnoDB Cluster（GR + MySQL Shell + MySQL Router）作為 production deployment 工具。

## Group Replication 的 transaction model

GR 用 *Group Communication Engine (GCE)*（Paxos 變種）達成 *atomic broadcast* — 任何 write transaction 必須先 broadcast 到所有 member、所有 member 確認 *certification pass* 才 commit。

每個 transaction 的 GR lifecycle：

```text
1. Client → Member A: BEGIN; UPDATE ...; COMMIT;
2. Member A: 先 local execute、收集 write_set（被改的 row + PK + transaction GTID）
3. Member A: write_set + binlog event → GCE broadcast to all members
4. GCE: Paxos consensus、所有 member 收到 broadcast、按 *相同順序*
5. Each Member: certification phase — 看 write_set 跟 *尚未 apply 的 incoming transactions* 是否有 PK 衝突
6. 若無衝突 → apply 該 transaction（local + remote member 都 apply）、回 client COMMIT OK
7. 若衝突 → certification fail、Member A 對 client 回 ERR_LOCK_DEADLOCK / GR_CONFLICT、application 必須 retry
```

**核心結論**：

- *Single-primary mode*：只有指定 member 接受 write、其他 member 純 apply、certification 仍跑（但衝突極少、因只有一個寫入源）
- *Multi-primary mode*：所有 member 都接受 write、certification 衝突常見、application 必須處理 conflict retry

**「multi-primary 不會線性 scale write」的原因**：

- 每個 write 仍要全 cluster GCE broadcast + certification
- 寫吞吐 ceiling 受 *最慢 member + 網路延遲* 限制（不是「N members × M throughput」）
- 多寫入源增加 certification 衝突機率、衝突 retry 反而拖 throughput

**「multi-primary 真實價值」**：

- *跨 region multi-active deploy*（每個 region local member 接受 local write、無 cross-region write latency）— 但需求極少、多數場景 single-primary + Aurora DSQL / Spanner 更實際
- *零停機 maintenance*（任一 member 下線、其他繼續接 write、不必 failover）— 但 single-primary mode 也提供同等 HA

對 99% production case：**single-primary mode** 才是正確選擇。Multi-primary 是 *特殊 use case 工具*、不是 *預設 mode*。

## Group Communication Engine（GCE）

GR 內建 GCE、基於 *XCom* protocol（Paxos 變種）。GCE 責任：

- Atomic broadcast：保證 message 到所有 member、按相同順序
- Group membership：偵測 member join / leave / fail、reconfigure consensus
- Network partition handling：minority partition 自動 fence（read-only）、majority 繼續服務

**GCE 跟 Raft 對比**：

| 維度        | GR XCom (Paxos-like)                      | Raft                            |
| ----------- | ----------------------------------------- | ------------------------------- |
| Leader      | 沒固定 leader、每個 message 選一個 sender | 固定 leader、其他 follower      |
| 配置複雜度  | 高（cluster member 列表 + IP allowlist）  | 中（更易理解）                  |
| Member 數量 | 預設 3 (max 9)                            | 預設 3-5                        |
| Performance | 高吞吐、低延遲（不必每次選 leader）       | Leader bottleneck 偶有          |
| 工程實作    | XCom 在 MySQL 內部、不暴露 API            | etcd / Consul / TiKV 等獨立工具 |

GR 的設計取捨：*緊耦合 MySQL*（不必外部 DCS）、*Paxos-like consensus*（不像 Raft 那麼簡單但效率更高）。trade-off 是 *對 ops 的 transparency 較低* — XCom 內部行為對 DBA 是 black box。

## InnoDB Cluster：GR + MySQL Shell + MySQL Router

純 GR 是 *底層 replication mechanism*、要組成 production deployment 需要：

- *MySQL Shell* (`mysqlsh`)：CLI 工具、提供 `dba.createCluster()` / `cluster.addInstance()` 等 cluster 管理 API
- *MySQL Router*：connection routing layer、自動發現 cluster topology、寫入 routing 給 primary、讀取 routing replica
- *MySQL Group Replication plugin*：在每個 MySQL instance 啟用

**InnoDB Cluster = GR + Shell + Router**、是 Oracle 推薦的 production GR deployment 方式。

### 起始部署（3 member single-primary cluster）

```bash
# Step 1: 在每個 instance 啟 GR plugin + 配 my.cnf
[mysqld]
server_id = 1                          # 各 instance 不同
gtid_mode = ON
enforce_gtid_consistency = ON
log_bin = mysql-bin
binlog_format = ROW
master_info_repository = TABLE
relay_log_info_repository = TABLE
transaction_write_set_extraction = XXHASH64
plugin_load_add = 'group_replication.so'

group_replication_group_name = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
group_replication_start_on_boot = OFF
group_replication_local_address = "node1.example.com:33061"
group_replication_group_seeds = "node1:33061,node2:33061,node3:33061"
group_replication_bootstrap_group = OFF
group_replication_single_primary_mode = ON       # 99% 場景用 ON
group_replication_enforce_update_everywhere_checks = OFF

# Step 2: 用 MySQL Shell 從第一個 member bootstrap cluster
mysqlsh --user=root --host=node1.example.com
> dba.configureInstance('root@node1:3306')
> var cluster = dba.createCluster('prodCluster')
> cluster.addInstance('root@node2:3306')
> cluster.addInstance('root@node3:3306')
> cluster.status()  # 應該顯示 3 member、1 PRIMARY + 2 SECONDARY

# Step 3: 部署 MySQL Router
mysqlrouter --bootstrap root@node1:3306 --directory /etc/mysql-router --user=mysqlrouter
systemctl start mysql-router

# 完成 — application 連 mysql-router:6446 (R/W) 或 :6447 (R/O)
```

Application 連 Router、Router 自動發現 cluster topology + 自動 failover routing。Application 不必知道哪個 instance 是 primary。

## 5 個 Production 踩雷

### 1. Certification lag — Multi-primary 模式 retry storm

Multi-primary mode 下、3 個 instance 同時收到 *相同 row* 的 conflicting write、certification 階段必有 N-1 個 transaction 被退回。Application 看到 `ER_GR_CONFLICT_TRANSACTION_ABORTED`、retry、若不智能 retry（exponential backoff）會 retry storm、整個 cluster 寫吞吐暴降。

修法：

- 99% 場景用 *single-primary mode*、避開 conflict
- 真的需要 multi-primary：application 必須 sharding-aware（不同 entry 寫不同 row range）、本質上跟 Vitess sharding 同概念但用 GR 機制
- Application retry 用 *jitter exponential backoff*、不直接 retry

### 2. Certification queue 爆炸 — Single-primary mode 仍受 cert backlog 影響

Single-primary mode 下 primary 接受 write、broadcast 到 secondary。Secondary 跟 primary network latency / 處理速度差時、cert queue 累積。Cert queue 滿 → primary write 也被卡（GR 設計：所有 member 同步前不接受新 write、保 consistency）。

修法：

- 監控 `group_replication_member_stats` view：`COUNT_TRANSACTIONS_IN_QUEUE` 持續 > 0 是警訊
- 提高 `group_replication_message_cache_size`（預設 1 GB）給 large transaction 緩衝
- 確認 *所有 member 同 instance class*、不要混 spec
- 跨 region GR：完全不推薦（network latency 殺 cert throughput）

### 3. Large transaction — 全 cluster 卡住

GR 必須把整個 transaction（含所有 write_set）一次 broadcast。10 GB transaction（大批量 UPDATE）必須一次塞滿 GCE buffer、cluster 內所有 member 都暫停接受新 transaction 直到 broadcast / apply 完成。常見場景：批次 archive / 大 backfill / `INSERT ... SELECT 1 億 row`。

修法：

- `group_replication_transaction_size_limit`（預設 150 MB）超過直接 reject、不要設 unlimited
- 大批量寫入拆 chunk（每 chunk < 100 MB）、用 application 層 loop
- 對 archive / backfill 用 `INSERT INTO archive SELECT ... LIMIT 10000` chunked、不是一個 transaction

### 4. Network partition — Minority partition 自動 read-only

3 member cluster、network partition 把 1 個 member 隔離。被隔離 member 是 *minority*、自動進入 *read-only mode*（不接受 write）、防 split-brain。Application 連到 minority member 寫入會失敗。

修法：

- MySQL Router 自動發現 cluster topology、自動 route write 到 majority partition primary
- Application 必須處理 connection error + retry（甚至 connection string 改成 *Router endpoint* 而非個別 instance）
- 監控 `group_replication_primary_member` UDF、確認哪個是真 primary

### 5. Member 加入 catch-up — 大量 binlog 阻擋 cluster service

新 member 加入 cluster（new instance / 復原 failed member）必須 *catch-up* — apply 從 GR cluster start 到當前所有 binlog 才能 join consensus。如果 cluster 已運作 1 個月、binlog 累積 100 GB、catch-up 可能 6-12 小時、catch-up 期間 *該 member 不投票、其他 member 仍 service*、但 majority 安全邊界縮小（3 → 2 member working）。

修法：

- 用 *MySQL Shell clone plugin* 直接 physical-snapshot 一個 existing member、跳過 binlog replay：

    ```bash
    > cluster.addInstance('root@node4:3306', {recoveryMethod: 'clone'})
    ```

- Clone 期間原 member 暫不接 write traffic（用 Router temporarily 排除）
- 規劃 maintenance window 加 member、不要在 peak load 期間

## 何時用 GR / InnoDB Cluster

| 條件                                                                 | 建議                                                 |
| -------------------------------------------------------------------- | ---------------------------------------------------- |
| 需要 *zero-data-loss HA*（不容忍任何 binlog gap）                    | GR single-primary                                    |
| 需要 *自動 failover 而不必 Orchestrator + fence script*              | GR / InnoDB Cluster                                  |
| 需要 *跨 region multi-active*（且 conflict 可接受 / sharding-aware） | GR multi-primary                                     |
| 流量 < 50K WPS、無嚴格 zero-loss 需求                                | 傳統 Orchestrator + Semi-sync 更簡單                 |
| 已用 Aurora / Cloud SQL 等 managed                                   | 不用 GR、用 managed offering                         |
| 需要分散式 SQL（跨 region linearizable）                             | Spanner / CockroachDB / Aurora DSQL（GR 不解決這個） |

## 跟其他模組整合

### 跟 Replication topology

GR 取代傳統 async / semi-sync replication、不是 *加在上面*。啟用 GR 後不要再配 `master-slave` style replication。詳見 [Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)。

### 跟 Orchestrator

Orchestrator 跟 InnoDB Cluster 不該 *同時用* — 兩者都會 trigger failover、會打架。GR / InnoDB Cluster 內建 failover、不需要 Orchestrator。詳見 [Orchestrator Failover](/backend/01-database/vendors/mysql/orchestrator-failover/)。

### 跟 ProxySQL / MySQL Router

ProxySQL 可以連 GR cluster（自動偵測 read_only flag）、但 *MySQL Router* 是 GR 原生的 routing layer、跟 InnoDB Cluster 緊耦合（透過 MySQL Shell metadata）。

選擇邏輯：

- *純 MySQL stack, 想 Oracle-supported 整套* → MySQL Router
- *已用 ProxySQL（包含其他非 GR cluster）+ 統一 routing* → 仍用 ProxySQL

詳見 [ProxySQL 配置](/backend/01-database/vendors/mysql/proxysql-config/)。

### 跟 InnoDB Tuning

GR 對 `innodb_flush_log_at_trx_commit` / `sync_binlog` 行為更敏感 — GR 要求 binlog 必須 *fsync to disk*（`sync_binlog=1`）保 zero-loss、不能用 `sync_binlog=0` 換速度。詳見 [InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)。

### 跟 PostgreSQL Patroni 對比

| 維度                       | InnoDB Cluster                       | Patroni + PostgreSQL          |
| -------------------------- | ------------------------------------ | ----------------------------- |
| Consensus                  | GCE (Paxos-like) 內建                | 依賴外部 DCS (etcd / Consul)  |
| Multi-primary              | 支援（但少用）                       | 不支援（PG single-primary）   |
| HA tooling                 | MySQL Shell + Router 整套            | Patroni + HAProxy + pgBouncer |
| Setup 複雜度               | 中（MySQL Shell 帶很多 abstraction） | 中（Patroni config + DCS）    |
| 5-year production maturity | Oracle-backed                        | community-driven、廣用        |

兩者角色相同、設計取捨不同。詳見 [PostgreSQL Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)。

## 容量規劃要點

| 元件                      | 配置建議                                                     |
| ------------------------- | ------------------------------------------------------------ |
| Member 數量               | 3 (預設、容忍 1 failure)、5 (容忍 2 failure)                 |
| Member 間 network latency | < 5ms（同 region 同 AZ 或跨 AZ）                             |
| Network bandwidth         | 至少 1 Gbps、broadcast traffic 重                            |
| Transaction size limit    | `group_replication_transaction_size_limit=150M`              |
| Message cache             | `group_replication_message_cache_size=1G`（預設）+ 看 lag 調 |
| MySQL Router instance     | 至少 2 個（HA）、放 application 同 LB 後                     |

Member 跨 region：*不推薦*。GR 對 latency 敏感、跨 region 50-200ms RTT 嚴重影響 cert throughput。multi-region 需求用 Aurora Global Database / Spanner 等專為跨 region 設計的方案。

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（GR 取代傳統 replication）
- [MySQL Orchestrator Failover](/backend/01-database/vendors/mysql/orchestrator-failover/)（GR / InnoDB Cluster 不必 Orchestrator）
- [MySQL ProxySQL 配置](/backend/01-database/vendors/mysql/proxysql-config/)（routing layer 對比）
- [MySQL InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)（GR durability 需求）
- [PostgreSQL Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)（PG sibling、不同 consensus）
- [quorum 卡片](/backend/knowledge-cards/quorum/) / [Paxos / Raft 對比](/backend/knowledge-cards/quorum/)
- 官方：[MySQL Group Replication](https://dev.mysql.com/doc/refman/8.0/en/group-replication.html) / [InnoDB Cluster](https://dev.mysql.com/doc/mysql-shell/8.0/en/mysql-innodb-cluster.html)
