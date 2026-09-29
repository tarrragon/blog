---
title: "MySQL Orchestrator Failover：HA 工具自身的 HA 靠內建 raft cluster、promotion 靠 GTID"
date: 2026-05-19
description: "Orchestrator 是 MySQL HA 自動 failover 的 de facto standard、但讀者第一個問題往往是「HA 工具自己會壞嗎」。本文走 Orchestrator 的雙層架構（管 MySQL 的 raft cluster + 被 raft 管的 orchestrator instance）→ topology discovery → failure detection → failover decision tree → promote action → 5 production 踩雷（split-brain 跟 fencing / pre-failover hook 失敗 / anti-flapping window / GTID errant transaction / VIP 跟 ProxySQL 整合斷層）→ 跟 ProxySQL / Patroni / RDS 對比"
weight: 15
tags: ["backend", "database", "mysql", "orchestrator", "ha", "failover", "deep-article"]
---

> 用詞註：Orchestrator 工具命名與 MySQL 5.7- SQL 命令（`SHOW SLAVE STATUS` / `CHANGE MASTER TO` / `STOP SLAVE` 等）沿用 *master / slave*。MySQL 8.0 改採 *primary / replica*（`SHOW REPLICA STATUS` / `CHANGE REPLICATION SOURCE TO` / `STOP REPLICA`）、舊語法在 8.0 保留為別名；MySQL 8.4 移除了舊語法，`SHOW SLAVE STATUS`、`CHANGE MASTER TO`、`STOP SLAVE`、`SHOW SLAVE HOSTS` 都回語法錯誤。本文出現 master / slave 處對應 primary / replica 概念。

這篇涵蓋 Orchestrator 對 MySQL replication topology 做自動 failover 的機制與 production 設定：Orchestrator 怎麼用 raft cluster 讓自己保持可用，以及一次自動 failover 從 topology discovery、failure detection、選 promotion candidate、promote 到處理舊 master 的過程；範圍從 MySQL 已經設好 replication 開始。任何 HA 工具都要回答自己失效時由誰接手：PostgreSQL 的 Patroni 把狀態交給外部 DCS（etcd / Consul），MySQL 的 Orchestrator 讓多個 orchestrator instance 組成 *內建 raft cluster*。整個部署因此有三組元件：

```text
被管的 MySQL topology:      primary MySQL → replica MySQL → replica MySQL → ...
orchestrator raft cluster:  orchestrator instance × 3 (or 5) — 用 raft 自己選 leader
orchestrator backend:       每個 orchestrator instance 自己有一個 backend DB 存 state
```

Orchestrator 3 個 instance 構成 *raft cluster*、自己選 leader。Leader 才有 *寫入 state* + *發起 failover* 權限、其他 instance follower 同步 state。Leader 失聯 → raft 重新選 leader（< 10 秒）、新 leader 繼續 manage MySQL topology。

跟 [PostgreSQL Patroni](/backend/01-database/vendors/postgresql/patroni-ha/) 不同：Patroni 需要 *外部 DCS*（etcd / Consul）作為 source of truth、Patroni 本身 stateless；Orchestrator 內建 raft、不需要外部 DCS、但每個 orchestrator instance 需要 *自己的 backend DB*（MySQL 或 SQLite）存 state。

## Orchestrator 的部署：被管的 MySQL topology 與 orchestrator raft cluster

被管的 MySQL topology 是 primary 加上它的 replica 群；orchestrator raft cluster 是 orchestrator instance 群。orchestrator raft cluster 監視被管的 MySQL topology，自己的 leader 選舉由 raft 處理。

**被管的 MySQL topology 對 Orchestrator 的需求**：

- 可能被 promote 的 MySQL server 啟用 `log_bin` + `log_slave_updates`：replica 被 promote 成 primary 之後，其餘 replica 要從它的 binlog 接續複製
- 啟用 GTID、replica 設 `MASTER_AUTO_POSITION=1`（Orchestrator 用 GTID 比較各 replica 的進度、re-point replica 時不必換算 binlog position）
- 每個 server 有 *orchestrator user*（官方文件列的權限：`GRANT SUPER, PROCESS, REPLICATION SLAVE, REPLICATION CLIENT, RELOAD ON *.* TO 'orchestrator'@'orc_host'`）

**orchestrator raft cluster 配置**：

```json
{
  "MySQLOrchestratorHost": "orchestrator-backend.example.com",
  "MySQLOrchestratorPort": 3306,
  "MySQLOrchestratorDatabase": "orchestrator",
  "RaftEnabled": true,
  "RaftDataDir": "/var/lib/orchestrator",
  "RaftBind": "10.0.1.10:10008",
  "RaftNodes": [
    "orchestrator1.example.com:10008",
    "orchestrator2.example.com:10008",
    "orchestrator3.example.com:10008"
  ],
  "DiscoverByShowSlaveHosts": true,
  "InstancePollSeconds": 5,
  "FailureDetectionPeriodBlockMinutes": 60,
  "RecoveryPeriodBlockSeconds": 3600,
  "RecoverMasterClusterFilters": ["*"],
  "RecoverIntermediateMasterClusterFilters": ["*"],
  "PreFailoverProcesses": ["/usr/local/bin/orchestrator-fence-master.sh"],
  "PostFailoverProcesses": ["/usr/local/bin/orchestrator-notify-proxysql.sh"]
}
```

這份 `/etc/orchestrator.conf.json` 是簡化版，設定依用途分組：`MySQLOrchestrator*` 指向這個 instance 自己的 backend；`Raft*` 讓三個 instance 組成 raft cluster，`RaftBind` 填這台 instance 自己的位址；`DiscoverByShowSlaveHosts` 與 `InstancePollSeconds` 控制 topology discovery；`FailureDetectionPeriodBlockMinutes` 與 `RecoveryPeriodBlockSeconds` 控制失效偵測與自動 recovery 的阻擋窗口；`Recover*ClusterFilters` 與兩組 hook 控制自動 failover。Orchestrator 用 JSON 解析設定檔，JSON 不接受 `#` 註解，所以分組說明寫在這裡、不寫進檔案。

## Topology Discovery — 從 seed server 自動發現整個 topology

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

## Failure Detection — 區分 master 真的失效與只是 Orchestrator 連不上

Orchestrator 不是 *單一 ping 失敗就 failover*、有 *holistic detection*：

| 指標                        | 解讀                                                                           |
| --------------------------- | ------------------------------------------------------------------------------ |
| Master `connect fail`       | 可能 network blip、不一定真壞                                                  |
| Master `timeout poll`       | 可能 master loaded、不一定真壞                                                 |
| **Replica 全部 `IO error`** | Master 真的對 replica 不可達、強訊號                                           |
| Replica 看到 master 還活著  | Master 對 orchestrator 不可達、可能是 *orchestrator network* 問題、不是 master |
| Replica lag 暴增            | Master 可能還活著但 overload、不一定要 failover                                |

**Detection rule**：Orchestrator 連不上 master，*而且 master 的所有 replica 都複製失敗*，才判定 `DeadMaster`。只有 Orchestrator 連不上、replica 仍在正常複製時不觸發 — 防 Orchestrator 自己的網路被隔離造成的 false positive failover。

## Failover Decision Tree — 選哪個 replica promote

判定 `DeadMaster` 後不是 *選最近的 replica*、用 decision tree：

1. **GTID 最新的 replica**：跟舊 master 同步最完整（用 `Executed_Gtid_Set` 對比）
2. **同 DC / AZ 的 replica**（如果有 multi-DC 配置）
3. **手動指定的 promotion candidate**（`promote_rule=must` 或 `prefer`）
4. **Semi-sync ack 的 replica**（如果 semi-sync 啟用）

GTID 最新是基本要求。其他規則是 *tie-breaker*。

**Errant transaction 處理**：選出的 candidate replica 如果有 *errant GTID*（master 沒有但 replica 有的 transaction）、Orchestrator *不會 promote 這個 replica*（怕 errant transaction 變成 new master state）。改選次優 candidate。

## Promote Action — 依序執行、任一步失敗就停在中間狀態

選好 candidate 後執行：

1. **Fence 舊 master**（pre-failover hook）：把舊 master 對外停掉、防 split-brain
2. **STOP SLAVE on candidate**：candidate 不再從舊 master pull binlog
3. **RESET SLAVE ALL on candidate**：candidate 清掉 slave 配置、變成獨立 master
4. **Re-attach 其他 replica**：用 `CHANGE MASTER TO MASTER_HOST=<candidate>, MASTER_AUTO_POSITION=1`（GTID auto-position）
5. **Post-failover hook**：通知 ProxySQL / HAProxy / DNS 切流量

每步任一失敗、Orchestrator 可能停在中間狀態、需要 *人工介入*。

## Recovery — 舊 master 怎麼處理

Failover 完、舊 master 可能：

- *真的死了*：物理 server 故障 / region outage → 不必處理、未來修好作為新 replica re-attach
- *Network blip 後復活*：舊 master 自己 *仍認為自己是 master*、再次接受寫入會造成 split-brain

修法：

- *Fencing*（必須）：pre-failover hook 把舊 master 對外 firewall 掉、或 force `read_only=1`、防舊 master 復活後接受寫入
- *Manual reset*：舊 master 復活後人工 confirm 是否變成新 master 的 replica（不要自動、自動容易誤判）

Orchestrator UI 在偵測到復活的舊 master 時會標 warning、不會自動處理。

## Production 踩雷

### Split-brain — pre-failover hook 沒 fence 舊 master

舊 master network blip 後復活、orchestrator 已 promote 新 master、application 部分 instance 連舊 master、部分連新 master、雙寫造成 data divergence。

修法：

- *Pre-failover hook 必須 fence*（不是可選）：
   - 物理 fencing：透過 IPMI 重啟 / 關 server
   - Network fencing：透過 firewall rule 切斷 server 對外連線
   - MySQL fencing：`SET GLOBAL read_only=1` + `KILL` 所有 active connection
- 用 *VIP / DNS* 配合：fence 完才切 VIP / DNS 到新 master、避免 application 連舊 IP
- 不依賴 application 連線 string 動態變更（DNS TTL 期間仍可能連舊 IP）

### Pre-failover hook 失敗 — Orchestrator 中止這次 recovery

Pre-failover hook 跑失敗（fence script 因為 SSH 不通、IPMI 沒回應）。`PreFailoverProcesses` 裡任何一個 process 以非零 exit code 結束，Orchestrator 就中止這次 recovery，cluster 留在沒有可寫 master 的狀態，等人工介入。

Orchestrator 在這裡中止，是因為 fence 沒有確認成功就 promote，舊 master 可能還在接受寫入而造成 split-brain。所以 fence script 要自己處理重試與 timeout，失敗時以非零 exit code 結束並發 alert；on-call 確認舊 master 已經停止接受寫入之後，手動發起 recovery（手動 recovery 不受 `RecoveryPeriodBlockSeconds` 阻擋）。

`PostponeReplicaRecoveryOnLagMinutes` 與 `FailMasterPromotionOnLagMinutes` 跟 hook 失敗無關，處理的是 replica 落後：`PostponeReplicaRecoveryOnLagMinutes` 讓落後超過設定分鐘數的 replica 延到新 master 選出、hook 跑完之後才重新接上；`FailMasterPromotionOnLagMinutes` 在 candidate 落後達到設定分鐘數時放棄 promotion。

### Anti-flapping 窗口的長度 — master 抖動 vs 真的失效

自動 failover 的 anti-flapping 窗口由 `RecoveryPeriodBlockSeconds`（預設 3600）決定：同一個 cluster 做完一次自動 recovery 之後，窗口內再偵測到失效，Orchestrator 不自動再做一次 recovery，要等窗口過去、或有人 acknowledge 前一次 recovery。`FailureDetectionPeriodBlockMinutes`（預設 60）管的是另一件事：同一個失效在這段時間內不重複通知，它不阻擋 recovery。

窗口越長，第一次 failover 後新 master 在窗口內又失效時，Orchestrator 越不會自動處理，要靠 on-call 手動發起 recovery（手動 recovery 不受這個窗口阻擋）；窗口越短，網路抖動越容易讓同一個 cluster 在短時間內連續 promote 好幾次。

修法：

- 窗口內的第二次失效要靠人處理，所以確認這段時間內的失效 alert 會叫到 on-call，窗口長度設成 on-call 來得及到場判斷的時間
- 監控 *failover 頻率*、單週 > 2 次表示底層問題（網路 / hardware）、不是調 anti-flapping window 解決

### GTID errant transaction — Orchestrator 拒絕 promote 但沒講原因

Candidate replica 有 *errant GTID*（從別處 inject 的 transaction）、Orchestrator 拒絕 promote、log 訊息 `errant GTID detected`、但 *沒寫實際是哪個 GTID*。On-call 在事故中沒辦法 debug。

修法：

- 平時 *監控 errant GTID*、不要等 failover 才發現：定期在 primary 與每台 replica 各跑一次 `SELECT @@GLOBAL.gtid_executed`，再用 `GTID_SUBTRACT` 算出 replica 有而 primary 沒有的 GTID：

```sql
-- 第一個引數貼 replica 的 @@GLOBAL.gtid_executed，第二個貼 primary 的；下面的 UUID 是佔位值
SELECT GTID_SUBTRACT(
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:1-100,bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb:1-3',  -- replica
  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:1-100'                                           -- primary
) AS errant_gtid;
-- 回傳 bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb:1-3：這三筆 transaction 只在 replica 上執行過，就是 errant GTID；回傳空字串代表沒有
```

- Errant GTID 來源通常是 *人為 inject*（DBA 直接寫 replica 然後 binlog 出現）、教育 DBA 不要直接連 replica 寫

### VIP / ProxySQL 整合斷層 — 切流量延遲

Post-failover hook 跑完 *script 上報*「我切完了」、但實際 *VIP / DNS / ProxySQL 還沒看到變化*。Application 連 stale endpoint 30 秒、寫入失敗。

修法：

- *Post-failover hook 不只 trigger 切換、要 wait 切換完成*：
   - VIP：等 `arping` 確認新 IP 已 propagate
   - ProxySQL：等 `mysql_servers` runtime table 更新 + 確認 monitor module 看到新 primary
   - DNS：先把 TTL 降到極短（5 秒）、再切 DNS、等 TTL 過
- Orchestrator 在 recovery 成功之後才執行 `PostFailoverProcesses`，recovery 失敗時執行的是另一組 `PostUnsuccessfulFailoverProcesses`；post-failover hook 自己要在切換沒有完成時以非零 exit code 結束並發 alert，交給人工檢查
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

Orchestrator 用 GTID 比較 replica 進度並 re-point replica（[Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)）。沒有 GTID 的 topology 它也支援，改用 Pseudo-GTID；binlog 格式 statement 與 row 都支援。兩者都沒有時 re-point 要換算 binlog position，failover 時容易出錯，所以 Orchestrator 建議用 GTID。

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

詳見 [MySQL Vitess Sharding](/backend/01-database/vendors/mysql/vitess-sharding/)。

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（GTID 是 Orchestrator pre-requisite）
- [MySQL ProxySQL 配置](/backend/01-database/vendors/mysql/proxysql-config/)（Orchestrator + ProxySQL 自動失效切換組合）
- [PostgreSQL Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)（PG sibling、不同 HA 機制）
- [Aurora vendor page](/backend/01-database/vendors/aurora/)（managed MySQL、Orchestrator 不需要）
- [quorum 卡片](/backend/knowledge-cards/quorum/) / [failover 卡片](/backend/knowledge-cards/failover/)
- 官方：[orchestrator GitHub](https://github.com/openark/orchestrator) / [orchestrator docs](https://github.com/openark/orchestrator/tree/master/docs)
