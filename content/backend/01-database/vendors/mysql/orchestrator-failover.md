---
title: "MySQL Orchestrator Failover：HA 工具自己怎麼 HA？raft cluster + GTID-based promotion 的兩段 paradox"
date: 2026-05-19
description: "Orchestrator 是 MySQL HA 自動 failover 的 de facto standard、但讀者第一個問題往往是「HA 工具自己會壞嗎」。本文走 Orchestrator 的雙層架構（管 MySQL 的 raft cluster + 被 raft 管的 orchestrator instance）→ topology discovery → failure detection → failover decision tree → promote action → 5 production 踩雷（split-brain 跟 fencing / pre-failover hook 失敗 / anti-flapping window / GTID errant transaction / VIP 跟 ProxySQL 整合斷層）→ 跟 ProxySQL / Patroni / RDS 對比"
weight: 15
tags: ["backend", "database", "mysql", "orchestrator", "ha", "failover", "deep-article"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) overview 的 implementation-layer deep article。Overview 已說明 MySQL 在 OLTP 譜系的定位、本文聚焦 *Orchestrator failover* — 自動 HA 的工具雙層架構跟 5 段 decision tree。

---

> 用詞註：Orchestrator 工具命名與 MySQL 5.7- SQL 命令（`SHOW SLAVE STATUS` / `CHANGE MASTER TO` / `STOP SLAVE` 等）沿用 *master / slave*。MySQL 8.0+ 改採 *primary / replica*、但 SQL syntax 仍保留別名。本文出現 master / slave 處對應 8.0 primary / replica 概念。

讀者第一個會問的問題：「Orchestrator 自己會壞嗎？壞了誰 failover Orchestrator？」這個 paradox 是 *任何 HA 工具* 的核心議題、PostgreSQL 的 Patroni 用 DCS（etcd / Consul）解決、MySQL 的 Orchestrator 用 *內建 raft cluster* 解決：

```text
被管的 (Layer 1):       primary MySQL → replica MySQL → replica MySQL → ...
管理者 (Layer 2):       orchestrator instance × 3 (or 5) — 用 raft 自己選 leader
管理者狀態存放 (Layer 3): 每個 orchestrator instance 自己有 MySQL backend (state)
```

Orchestrator 3 個 instance 構成 *raft cluster*、自己選 leader。Leader 才有 *寫入 state* + *發起 failover* 權限、其他 instance follower 同步 state。Leader 失聯 → raft 重新選 leader（< 10 秒）、新 leader 繼續 manage MySQL topology。

跟 [PostgreSQL Patroni](/backend/01-database/vendors/postgresql/patroni-ha/) 不同：Patroni 需要 *外部 DCS*（etcd / Consul）作為 source of truth、Patroni 本身 stateless；Orchestrator 內建 raft、不需要外部 DCS、但每個 orchestrator instance 需要 *自己的 MySQL backend* 存 state。

## Orchestrator 雙層架構：管 MySQL 的 Layer 2

Layer 1 是 *被管的* MySQL cluster — primary + replica 群。Layer 2 是 *管理者* — orchestrator instance 群。Layer 2 監視 Layer 1、Layer 2 自己用 raft 自管。

**Layer 1 對 Orchestrator 的需求**：

- 所有 MySQL server 啟用 `binlog` + `log_slave_updates`（讓 Orchestrator 看得到 binlog event）
- 啟用 GTID（Orchestrator failover decision 依賴 GTID 比較進度、不用算 binlog position）
- 每個 server 有 *orchestrator user*（`GRANT SUPER, REPLICATION CLIENT, REPLICATION SLAVE, PROCESS ON *.* TO 'orchestrator'@'%'`）

**Layer 2 配置**：

```ini
# /etc/orchestrator.conf.json (簡化)
{
  "MySQLOrchestratorHost": "orchestrator-backend.example.com",
  "MySQLOrchestratorPort": 3306,
  "MySQLOrchestratorDatabase": "orchestrator",

  # 用 backend MySQL（每個 orchestrator instance 自己一個）+ raft 同步
  "RaftEnabled": true,
  "RaftDataDir": "/var/lib/orchestrator",
  "RaftBind": "10.0.1.10:10008",
  "RaftNodes": [
    "orchestrator1.example.com:10008",
    "orchestrator2.example.com:10008",
    "orchestrator3.example.com:10008"
  ],

  # Topology discovery
  "DiscoverByShowSlaveHosts": true,
  "InstancePollSeconds": 5,

  # Failover detection
  "FailureDetectionPeriodBlockMinutes": 60,
  "RecoveryPeriodBlockSeconds": 3600,

  # Failover automation
  "RecoverMasterClusterFilters": ["*"],
  "RecoverIntermediateMasterClusterFilters": ["*"],
  "PreFailoverProcesses": ["/usr/local/bin/orchestrator-fence-master.sh"],
  "PostFailoverProcesses": ["/usr/local/bin/orchestrator-notify-proxysql.sh"]
}
```

## Stage 1：Topology Discovery — 自動發現 + manual seed

Orchestrator 啟動後 *seed* 一個或多個 MySQL server、自動發現整個 topology：

- 連 seed server → `SHOW SLAVE HOSTS` → 發現所有 replica
- 對每個 replica 跑 `SHOW MASTER STATUS` + `SHOW SLAVE STATUS` → 建立 *父子關係 graph*
- 持續 poll（`InstancePollSeconds=5`）每 5 秒更新 topology state

**Topology graph 的 node**：

- *Master*：no slave status、被多個 replica 指
- *Intermediate master*：有 slave status 也有下游 replica（chained replication）
- *Co-master*：互相 replicate（罕見、active-passive failover 場景）
- *Replica*：有 slave status、無下游

Topology 可視化：Orchestrator UI（web）顯示 cluster 樹狀圖、操作員可手動 drag-and-drop replica 重新 attach。

## Stage 2：Failure Detection — 區分真壞跟假壞

Orchestrator 不是 *單一 ping 失敗就 failover*、有 *holistic detection*：

| 指標                        | 解讀                                                                           |
| --------------------------- | ------------------------------------------------------------------------------ |
| Master `connect fail`       | 可能 network blip、不一定真壞                                                  |
| Master `timeout poll`       | 可能 master loaded、不一定真壞                                                 |
| **Replica 全部 `IO error`** | Master 真的對 replica 不可達、強訊號                                           |
| Replica 看到 master 還活著  | Master 對 orchestrator 不可達、可能是 *orchestrator network* 問題、不是 master |
| Replica lag 暴增            | Master 可能還活著但 overload、不一定要 failover                                |

**Detection rule**：Master *自己連不上* + *至少一個 replica 也看 master IO error* → 判定 `DeadMaster`。單一 orchestrator 連不上 master 不觸發 — 防 orchestrator network 隔離造成的 false positive failover。

## Stage 3：Failover Decision Tree — 選哪個 replica promote

判定 `DeadMaster` 後不是 *選最近的 replica*、用 decision tree：

1. **GTID 最新的 replica**：跟舊 master 同步最完整（用 `Executed_Gtid_Set` 對比）
2. **同 DC / AZ 的 replica**（如果有 multi-DC 配置）
3. **手動指定的 promotion candidate**（`promote_rule=must` 或 `prefer`）
4. **Semi-sync ack 的 replica**（如果 semi-sync 啟用）

GTID 最新是基本要求。其他規則是 *tie-breaker*。

**Errant transaction 處理**：選出的 candidate replica 如果有 *errant GTID*（master 沒有但 replica 有的 transaction）、Orchestrator *不會 promote 這個 replica*（怕 errant transaction 變成 new master state）。改選次優 candidate。

## Stage 4：Promote Action — 5 步 atomic（理想情況）

選好 candidate 後執行：

1. **Fence 舊 master**（pre-failover hook）：把舊 master 對外停掉、防 split-brain
2. **STOP SLAVE on candidate**：candidate 不再從舊 master pull binlog
3. **RESET SLAVE ALL on candidate**：candidate 清掉 slave 配置、變成獨立 master
4. **Re-attach 其他 replica**：用 `CHANGE MASTER TO MASTER_HOST=<candidate>, MASTER_AUTO_POSITION=1`（GTID auto-position）
5. **Post-failover hook**：通知 ProxySQL / HAProxy / DNS 切流量

每步任一失敗、Orchestrator 可能停在中間狀態、需要 *人工介入*。

## Stage 5：Recovery — Old master 怎麼處理

Failover 完、舊 master 可能：

- *真的死了*：物理 server 故障 / region outage → 不必處理、未來修好作為新 replica re-attach
- *Network blip 後復活*：舊 master 自己 *仍認為自己是 master*、再次接受寫入會造成 split-brain

修法：

- *Fencing*（必須）：pre-failover hook 把舊 master 對外 firewall 掉、或 force `read_only=1`、防舊 master 復活後接受寫入
- *Manual reset*：舊 master 復活後人工 confirm 是否變成新 master 的 replica（不要自動、自動容易誤判）

Orchestrator UI 在偵測到 errant master 時會標 warning、不會自動處理。

## 5 個 Production 踩雷

### 1. Split-brain — pre-failover hook 沒 fence 舊 master

舊 master network blip 後復活、orchestrator 已 promote 新 master、application 部分 instance 連舊 master、部分連新 master、雙寫造成 data divergence。

修法：

- *Pre-failover hook 必須 fence*（不是可選）：
   - 物理 fencing：透過 IPMI 重啟 / 關 server
   - Network fencing：透過 firewall rule 切斷 server 對外連線
   - MySQL fencing：`SET GLOBAL read_only=1` + `KILL` 所有 active connection
- 用 *VIP / DNS* 配合：fence 完才切 VIP / DNS 到新 master、避免 application 連舊 IP
- 不依賴 application 連線 string 動態變更（DNS TTL 期間仍可能連舊 IP）

### 2. Pre-failover hook 失敗 — Orchestrator 該停還是該繼續

Pre-failover hook 跑失敗（fence script 因為 SSH 不通、IPMI 沒回應）。Orchestrator 有兩種策略：

- *PostponeReplicaRecoveryOnLagMinutes*：等 hook 成功才繼續、可能永遠 stuck
- *FailMasterPromotionOnLagMinutes*：放棄 promotion、留 cluster degraded（無 master）

兩者都不理想。多數 production 選 *PostponeReplicaRecoveryOnLagMinutes=10*：等 10 分鐘 hook 成功、超時則 alert 人工介入、不繼續 auto-promote（人工 review 才是正確選擇）。

### 3. Anti-flapping 窗口太短 — Master 抖動 vs 真死

`FailureDetectionPeriodBlockMinutes=60`：偵測一次 failure 後 60 分鐘內不再 trigger failover（即使再偵測到 failure）。預設 60 分鐘對 *第一次 failover 後 master 仍不穩* 的場景太長 — 60 分鐘內 master 真的死了第二次、orchestrator 不 failover。預設 60 分鐘對 *網路抖動* 的場景太短 — 60 分鐘內可能 multiple failover、cluster 一直在 promote。

修法：

- 評估自己 cluster 的 *typical recovery time*：1-2 小時、設 `FailureDetectionPeriodBlockMinutes=120`
- 監控 *failover 頻率*、單週 > 2 次表示底層問題（網路 / hardware）、不是調 anti-flapping window 解決

### 4. GTID errant transaction — Orchestrator 拒絕 promote 但沒講原因

Candidate replica 有 *errant GTID*（從別處 inject 的 transaction）、Orchestrator 拒絕 promote、log 訊息 `errant GTID detected`、但 *沒寫實際是哪個 GTID*。On-call 在事故中沒辦法 debug。

修法：

- 平時 *監控 errant GTID*：定期跑 `pt-show-grants` + GTID 比對、不要等 failover 才發現
- Orchestrator 的 `OrchestratorIssuesAGtidPurge` 設 true：preview mode 看 errant GTID 的位置
- Errant GTID 來源通常是 *人為 inject*（DBA 直接寫 replica 然後 binlog 出現）、教育 DBA 不要直接連 replica 寫

### 5. VIP / ProxySQL 整合斷層 — 切流量延遲

Post-failover hook 跑完 *script 上報*「我切完了」、但實際 *VIP / DNS / ProxySQL 還沒看到變化*。Application 連 stale endpoint 30 秒、寫入失敗。

修法：

- *Post-failover hook 不只 trigger 切換、要 wait 切換完成*：
   - VIP：等 `arping` 確認新 IP 已 propagate
   - ProxySQL：等 `mysql_servers` runtime table 更新 + 確認 monitor module 看到新 primary
   - DNS：先把 TTL 降到極短（5 秒）、再切 DNS、等 TTL 過
- Orchestrator `PostFailoverProcessesFailOnError=true`：hook 失敗整個 failover 標記失敗、人工檢查
- ProxySQL 用 `mysql_replication_hostgroups` 自動偵測 read_only flag、可不依賴 hook（推薦）

## 容量規劃要點

| 元件                        | 配置建議                                                   |
| --------------------------- | ---------------------------------------------------------- |
| Orchestrator instance 數量  | 3（raft cluster 最小、odd number、容忍 1 個故障）          |
| 每個 instance MySQL backend | 1 個獨立 MySQL（不要共用、不要用被管的 cluster）           |
| Backend MySQL spec          | t3.small 級別、Orchestrator state ~1 GB                    |
| Network latency             | raft 同 region 內、跨 AZ 可接受（< 5ms）、跨 region 不推薦 |
| InstancePollSeconds         | 5 秒（預設）— 越小越敏感、越大越省連線                     |

3 instance raft cluster 容忍 1 instance 故障。5 instance 容忍 2 instance 故障但 quorum cost 高、99% 場景 3 個夠用。

## 跟其他模組整合

### 跟 Replication topology

Orchestrator 100% 依賴 GTID + binlog ROW format（[Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)）。沒 GTID 用 binlog position、failover 時 re-pointing 容易出錯、Orchestrator 強烈建議 GTID。

### 跟 ProxySQL

[ProxySQL](/backend/01-database/vendors/mysql/proxysql-config/) 用 `mysql_replication_hostgroups` 自動偵測 `read_only` flag — orchestrator 切完新 master 後、ProxySQL monitor module 自動看到新 master 的 `read_only=0`、自動更新 routing、application 不用改 connection string。

這個 *無需 post-failover hook 通知 ProxySQL* 的整合是 ProxySQL + Orchestrator 組合的最大優勢、比手動 hook 通知 VIP / DNS 可靠。

### 跟 Patroni（PostgreSQL 對應）

| 維度               | Orchestrator                   | Patroni                           |
| ------------------ | ------------------------------ | --------------------------------- |
| DCS                | 內建 raft（不需外部）          | 外部（etcd / Consul / ZooKeeper） |
| State storage      | 每 instance 一個 MySQL backend | DCS 本身                          |
| Topology discovery | 自動 + manual seed             | 自動（透過 DCS）                  |
| Fencing            | Pre-failover hook（自實作）    | Watchdog（內建）                  |
| 5+ year 生產驗證   | GitHub / Booking.com / Shopify | Zalando / 多個歐美企業            |

兩者角色相同、設計取捨不同。Patroni 對 DCS 高依賴、Orchestrator 對自己 backend MySQL 高依賴。

### 跟 RDS / Aurora MySQL

AWS RDS / Aurora 內建 multi-AZ failover、*不用 Orchestrator*。Aurora failover < 30 秒、RDS failover ~60-120 秒。Aurora 把 replication / failover 整套封進 storage layer、application 看到的是 reader endpoint + writer endpoint。

詳見 [Aurora vendor page](/backend/01-database/vendors/aurora/)。

### 跟 Vitess

Vitess shard 內部用 *VTOrc*（Vitess fork of Orchestrator）— 概念跟 Orchestrator 一致、針對 Vitess topology metadata 適配。

詳見 *Vitess sharding 設計* 篇（待寫）。

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（GTID 是 Orchestrator pre-requisite）
- [MySQL ProxySQL 配置](/backend/01-database/vendors/mysql/proxysql-config/)（Orchestrator + ProxySQL 自動失效切換組合）
- [PostgreSQL Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)（PG sibling、不同 HA 機制）
- [Aurora vendor page](/backend/01-database/vendors/aurora/)（managed MySQL、Orchestrator 不需要）
- [quorum 卡片](/backend/knowledge-cards/quorum/) / [failover 卡片](/backend/knowledge-cards/failover/)
- 官方：[orchestrator GitHub](https://github.com/openark/orchestrator) / [orchestrator docs](https://github.com/openark/orchestrator/tree/master/docs)
