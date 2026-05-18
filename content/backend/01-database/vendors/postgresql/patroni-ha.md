---
title: "PostgreSQL Patroni HA：從 leader 失聯到 client 重連的 5 段 failover lifecycle"
date: 2026-05-18
description: "Patroni 把 PostgreSQL HA 拆成 detection / election / promotion / reconfiguration / recovery 五段 lifecycle、每段都有獨立配置跟 failure mode；DCS quorum + watchdog 防 split-brain、async/sync replication 取捨、5 個 production 踩雷、跟 PgBouncer / HAProxy / cert-manager 整合"
weight: 11
tags: ["backend", "database", "postgresql", "patroni", "ha", "failover", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PostgreSQL 在 OLTP 譜系的定位、本文聚焦 *Patroni-based HA* 的 lifecycle 設計 — 從正常運作到 failover 完成的 5 段、每段配置 + failure mode + recovery。

## Failover lifecycle：5 段不是一條曲線

PostgreSQL 原生沒有 auto-failover；primary 掛了、application 卡死、SRE 手動 promote standby — 整個過程通常 5-30 分鐘。Patroni 把這條鏈拆成 *自動化的 5 段 lifecycle*、每段有自己的 trigger、配置、失敗模式：

| 段                     | 觸發                                          | 動作                                                                          | 失敗模式                                        |
| ---------------------- | --------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------- |
| **1. Detection**       | Leader heartbeat 在 DCS（etcd / Consul）失聯 | Standby 們開始觀察、累積失聯時間到 TTL                                        | DCS 本身分裂 → false detection 啟動失敗 failover |
| **2. Election**        | TTL 過、DCS 開放 leader lock                  | Standby 競爭寫 leader key（DCS quorum-based）                                  | Network partition → 兩邊都自認 leader（split-brain）|
| **3. Promotion**       | 新 leader 寫 DCS key 成功                     | 跑 `pg_ctl promote`、停 streaming replication、開始接寫                       | Standby 落後太多 → 拒 promote 或承接時資料缺   |
| **4. Reconfiguration** | Patroni REST API 通知 routing 層              | HAProxy / PgBouncer 切流量到新 leader                                          | Routing 層 health check 慢 → 流量持續打舊 leader |
| **5. Recovery**        | 舊 leader 恢復（手動 / 自動）                  | 跑 `pg_rewind` + 重接 streaming replication 為 standby                        | WAL divergence 太大 → 必須重 base backup        |

每段都有獨立配置、不是「設一個 timeout 就好」。後面分段展開。

## Stage 1：Detection — DCS heartbeat 跟 TTL

```yaml
# patroni.yml 核心配置
scope: myapp-pg-cluster
namespace: /db/
name: pg-node-1                                # 跟 hostname 一致

etcd:
  hosts: etcd1:2379,etcd2:2379,etcd3:2379       # DCS quorum
  protocol: https

bootstrap:
  dcs:
    ttl: 30                                     # leader lock TTL
    loop_wait: 10                               # patroni 主循環間隔
    retry_timeout: 10                           # DCS retry 上限
    maximum_lag_on_failover: 1048576            # standby 落後 1MB 內才能 promote
    synchronous_mode: false                     # async / sync 取捨
```

關鍵直覺：

- **TTL (30s) = leader 失聯多久才被視為 dead**。設太短（< 15s）會把 transient network jitter 當 dead；設太長（> 60s）unavailability 拖長
- **loop_wait + retry_timeout < TTL**：Patroni 必須在 TTL 內成功跟 DCS 互動 N 次、`loop_wait=10 + retry_timeout=10` 給每個循環 20s buffer
- **maximum_lag_on_failover**：standby WAL 落後超過這個閾值就 *不參與 election*；防止「promote 一個落後 5 分鐘的 standby」資料丟失

## Stage 2：Election — DCS quorum + watchdog 防 split-brain

```yaml
watchdog:
  mode: required                                # required / automatic / off
  device: /dev/watchdog
  safety_margin: 5
```

Election 期間最大風險是 *split-brain* — network partition 下、舊 leader 還活著但跟 DCS 斷線；新 leader 從 standby 升上來、application 同時連兩個 PostgreSQL 寫。資料 divergence 後 *無法自動 reconcile*。

防護機制兩層：

1. **DCS quorum**：etcd / Consul 至少 3 node、過半 quorum 才能寫 leader key — 少數派 partition 無法 elect 新 leader
2. **Watchdog (Linux kernel)**：required mode 強制 — Patroni 必須定期 *poke* `/dev/watchdog`、若 Patroni 自己掛或被 OS 凍結、kernel 自動 reboot 整台機器、避免舊 leader 在 DCS 失聯後繼續接寫

Watchdog `required` 是 production-grade 的硬要求 — `automatic` / `off` 在 split-brain 場景下無法防護。

## Stage 3：Promotion — pg_ctl + replication slot 切換

新 leader 寫 DCS key 成功後、Patroni 自動執行：

```bash
# Patroni 內部、不要手動跑
pg_ctl promote -D /var/lib/postgresql/data
# postgresql.auto.conf 移除 primary_conninfo
# postgresql.auto.conf 重新計算 timeline ID
# 啟動接寫
```

Promotion 期間關鍵議題：

- **timeline divergence**：新 leader 開新 timeline ID（從 leader 失聯時的 LSN 開始）；其他 standby 需要 `pg_rewind` 把自己的 WAL fork 點對齊新 timeline
- **replication slot 處理**：舊 leader 上的 replication slot 在 DCS 中已 stale、新 leader 重建 slot；如果 logical replication consumer 沒 idempotent、會 replay 部分訊息
- **promotion latency**：通常 3-10 秒（pg_ctl 本身 < 5s、加 DCS 寫確認）

## Stage 4：Reconfiguration — client routing 切換

PostgreSQL 自己升 leader 還不夠、application 不知道；要靠前端 routing 層轉發。三種典型 pattern：

```text
[client] → [HAProxy / pgBouncer] → [pg-node-1 (leader)]
                                 → [pg-node-2 (standby, read)]
                                 → [pg-node-3 (standby, read)]
```

Patroni REST API 暴露 `/leader` / `/replica` / `/health` endpoint、HAProxy 用 *health check* 跑這些 endpoint：

```text
# haproxy.cfg
backend pg-write
  option httpchk OPTIONS /leader
  http-check expect status 200
  server pg-node-1 pg-node-1:5432 check port 8008
  server pg-node-2 pg-node-2:5432 check port 8008 backup
  server pg-node-3 pg-node-3:5432 check port 8008 backup
```

Reconfiguration 期間關鍵延遲：

- HAProxy health check 間隔（預設 2s）+ failure threshold（預設 3 次）= ~6s 切換感應
- PgBouncer 不主動 health check、要靠 application 端 retry 跟 connection drop 觸發重連
- 整個 reconfiguration 端到端通常 10-20s（含 PostgreSQL promotion 時間）

## Stage 5：Recovery — pg_rewind 跟 base backup 取捨

舊 leader 恢復後變 standby，但 WAL 已 divergence — 必須選一條 recovery path：

- **`pg_rewind`**：rewind 舊 leader WAL 到分歧點、重新接 streaming replication；條件 = 分歧 WAL 量小（< 幾 GB）且 timeline 可對齊
- **重 base backup**：用 `pg_basebackup` 從新 leader 拉完整 base + WAL；條件 = 任何時候都可、但時間長（TB 級 1-4 小時）

Patroni 預設嘗試 pg_rewind、失敗才退 base backup。production 配置：

```yaml
postgresql:
  use_pg_rewind: true
  remove_data_directory_on_rewind_failure: true   # rewind 失敗自動清 data dir、再 base backup
  remove_data_directory_on_diverged_timelines: true
```

## Production 故障演練

### Case 1：Split-brain due to DCS partition

**徵兆**：兩個 PostgreSQL node 都在接寫、application 大量寫入 conflict / unique constraint violation。

**根因**：DCS（etcd）partition — 兩個 etcd node 在 partition 兩側、都自認 quorum；其實是 split-vote、兩邊都不應該。Patroni 在兩邊各 elect 一個 leader。

**修法**：

1. DCS 必須奇數 node（3 / 5 / 7）、過半 quorum 嚴格 enforce
2. DCS 部署跨 AZ / region 時、quorum size 要考慮 partition 機率（3 AZ 各 1 node 是 production 最低標）
3. Watchdog `required` mode 是最後一道閘門 — DCS partition 加 quorum 失靈時、watchdog 強制 reboot 失聯 node

### Case 2：Standby 落後太多、無法 failover

**徵兆**：primary 失聯後、Patroni log 顯示 `Following members have lag greater than maximum_lag_on_failover`、所有 standby 都被拒 promote、cluster unavailable。

**根因**：maximum_lag_on_failover 設 1MB、但 standby replication lag 累積到 50MB（write-heavy workload + slow disk on standby）。安全機制觸發、但代價是 *無 standby 可升*、需要人工降低門檻或等 standby catch up。

**修法**：

1. **預防**：standby 容量 / IO 對齊 primary、避免 lag 累積；prometheus alert `pg_replication_lag_bytes > 10MB` 觸發前 catch
2. **臨時**：手動 `patronictl edit-config` 把 maximum_lag_on_failover 暫時拉到 50MB、接受可能丟 50MB worth of writes、換 availability
3. **長期**：sync replication（一個 standby 強制同步）、保證至少一個 standby zero-lag

### Case 3：Promotion 後 application connection storm

**徵兆**：failover 完成後 30-120 秒內、application log 大量 `connection refused` / `password authentication failed`、application 自己 retry storm。

**根因**：新 leader 剛 promote、PostgreSQL `max_connections` 容量還在 warm up（shared memory / cache 未 prime）、application 同時湧入大量 connection request；應用 retry 不夠 jitter、queue 堆積。

**修法**：

1. Application 用 *exponential backoff with jitter*、不要 immediate retry
2. PgBouncer / connection pool 限制每 application instance 對 PG 的 connection 上限、不直連 PG
3. 預先在 standby 跑 `pg_prewarm` 把熱表 cache 預熱、promotion 後 cache miss 不爆

### Case 4：pg_rewind 失敗、退到 base backup 沒做

**徵兆**：舊 leader 恢復後、Patroni log 顯示 `pg_rewind failed`、舊 leader 一直 STARTING、無法重接 cluster；SRE 手動跑 pg_basebackup 才恢復。

**根因**：`remove_data_directory_on_rewind_failure: false`（預設）— rewind 失敗時 Patroni 不主動清 data dir、需要 SRE 手動處理；運維沒 runbook、卡在這步幾小時。

**修法**：

1. Production 設 `remove_data_directory_on_rewind_failure: true` + `remove_data_directory_on_diverged_timelines: true`、讓 Patroni 自動 fallback
2. data dir 跑在獨立 PV / disk、清掉風險可控（不要跑 root disk）
3. 容量規劃：base backup 時間預估納入 RTO（TB 級 base backup 1-4 小時、不是 RTO 30 分鐘所能承受）

### Case 5：Watchdog 觸發整機 reboot、誤殺

**徵兆**：production server 在無故障時 unexpected reboot、`dmesg` 顯示 `watchdog: BUG: soft lockup`。

**根因**：Patroni 主循環因 etcd 短暫慢回應卡住 60+ 秒、kernel watchdog 觸發 reboot；但實際 PostgreSQL 沒 hang、是 Patroni-watchdog 鏈過敏。

**修法**：

1. `safety_margin` 設大一點（10-15）、給 Patroni loop_wait 抖動空間
2. etcd 跟 Patroni 部署在低延遲 network 內（同 AZ < 5ms）、跨 region etcd 不建議
3. watchdog device 用 softdog（軟體模擬）vs 硬體 watchdog、debug 時 softdog 容易觀察

## 容量規劃

| 維度                    | 估算                                                       | 警戒                                         |
| ----------------------- | ---------------------------------------------------------- | -------------------------------------------- |
| Cluster size            | 3-5 node（含 leader + 2-4 standby）                        | < 3 不能 HA（單 standby 失敗整 cluster 掛） |
| DCS size                | 3 / 5 / 7 node（奇數 quorum）                              | etcd 5 node 是 prod standard                 |
| TTL                     | 30s（default 30、production 20-60）                        | < 15s 過敏、> 60s 過鈍                       |
| maximum_lag_on_failover | 1MB（default）                                              | 大表 write-heavy 可放 10-100MB              |
| Synchronous standby     | 1 個 sync + N 個 async 是 production 預設                  | 全 async 容易丟資料、全 sync write latency 爆 |
| RTO                     | 10-30 秒（detection 30s 內 + promotion 5-10s + reconfig 5s）| > 60s 要 audit 鏈路                        |
| RPO                     | sync mode 接近 0、async mode 跟 lag 同數量級                | async 在 disk IO 慢時 lag 可能 MB-GB level   |

## 整合 / 下一步

### 跟 [PgBouncer](/backend/01-database/vendors/postgresql/pgbouncer-config/) 整合

PgBouncer 不主動感知 Patroni failover、要靠：

1. **HAProxy 在 PgBouncer 上層**：HAProxy 跑 Patroni health check、PgBouncer connection 重新路由
2. **PgBouncer reload**：failover 後 SRE / automation 跑 `pgbouncer -R`、強制重連 backend
3. **Connection pool drain**：application 端 connection pool 設 `pool_lifetime_max=5min`、舊 connection 自然汰換

### 跟 cert-manager（TLS rotation）

Patroni REST API 跟 PostgreSQL streaming replication 都用 TLS、cert rotation 不能停服務：

1. cert-manager 自動換證後、Patroni 跟 PostgreSQL 都需要 reload（不是 restart）
2. `patronictl reload <cluster>` 不會觸發 failover、只 reload config
3. PostgreSQL `pg_ctl reload` 是 SIGHUP、平滑載入新 cert

### 跟 backup / PITR

Patroni 不管 backup — 但 standby promotion 後、WAL archive 必須跟新 leader 的 timeline 對齊：

1. WAL archive 命令模板含 `%t`（timeline）：`archive_command = 'wal-g wal-push %p'`
2. Backup tool（pgBackRest / WAL-G）支援 timeline 切換、archive 不會中斷
3. 詳見 [PITR + WAL archiving deep article](/backend/01-database/vendors/postgresql/pitr-wal-archiving/)

### 下一步議題

- **Multi-region Patroni**：跨 region 部署的 DCS quorum 設計、跟單 region 的取捨完全不同
- **PostgreSQL 16+ streaming replication slot 持久化**：簡化 standby promotion 後 logical consumer 重連
- **跟 Kubernetes operator 整合**：Patroni 跑在 K8s 時、StatefulSet + pod identity + DCS 部署模式

## 相關連結

- 上游 vendor 頁：[PostgreSQL](/backend/01-database/vendors/postgresql/)
- 上游 chapter：[High Concurrency Access](/backend/01-database/high-concurrency-access/) — connection / replication / HA 全鏈
- 平行 deep article：[pgBouncer 配置](/backend/01-database/vendors/postgresql/pgbouncer-config/) / [Vault Dynamic Credential](/backend/07-security-data-protection/vendors/hashicorp-vault/dynamic-credential/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
