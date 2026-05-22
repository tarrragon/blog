---
title: "MySQL Multi-source Replication"
date: 2026-05-22
description: "MySQL multi-source replication、channel、consolidation、conflict boundary、lag monitoring 與 migration route"
tags: ["backend", "database", "mysql", "replication", "multi-source"]
---

MySQL multi-source replication 的核心責任是讓一個 replica 從多個 source 接收資料。這種拓撲常用於資料整併、分庫匯總、migration staging、報表集中或多個 bounded context 的 read consolidation。

本文的判讀錨點是：multi-source replication 是 consolidation pattern，而非 multi-primary conflict resolution。每個 channel 要有獨立 source、schema scope、lag、error handling 與 ownership。

## Use Cases

Use cases 的核心責任是確認 multi-source 解決的是整併需求。

| 情境                | 適合條件                              |
| ------------------- | ------------------------------------- |
| Reporting replica   | 多個 source 匯入同一 read-only target |
| Migration staging   | 新平台先接多個 source binlog          |
| Regional fan-in     | 多區 local DB 匯總到中心              |
| Shard consolidation | 多 shard 同 schema 匯入 reporting DB  |
| Audit / CDC sink    | 變更集中供後續 pipeline 使用          |

Multi-source target 通常應 read-only。若 target 同時接受 application write，就要設計 conflict 與 ownership，複雜度會大幅提高。

## Channel Design

Channel design 的核心責任是把每個 source 隔離成可觀測單位。

| 設計項       | 審查問題                                |
| ------------ | --------------------------------------- |
| Channel name | 是否能看出 source / owner / purpose     |
| Schema scope | 不同 source 是否寫入不同 schema / table |
| GTID         | GTID domain / collision policy          |
| Filter       | replicate-do / ignore 規則是否可審查    |
| Credential   | 每個 channel 是否獨立 secret            |
| Lag alert    | channel-level lag 與 error              |

Channel 命名要可讀。Incident 時看到 channel 名稱，就要知道哪個 source、哪個 team、哪個用途與是否可暫停。

## Conflict Boundary

Conflict boundary 的核心責任是避免多個 source 寫同一份邏輯資料。Multi-source 沒有自動解決業務 conflict 的能力。

| Conflict 類型         | 控制方式                           |
| --------------------- | ---------------------------------- |
| Primary key collision | shard key prefix、schema isolation |
| Duplicate natural key | source namespace、dedupe layer     |
| Out-of-order update   | source ownership、event timestamp  |
| Delete collision      | tombstone policy                   |
| DDL drift             | migration coordination             |

最安全的 pattern 是每個 source 寫自己的 schema 或帶 source namespace 的 table。若多 source 寫同一 table，必須先設計 key space 與 conflict policy。

## Monitoring

Monitoring 的核心責任是讓每個 channel 的狀態可見。

```sql
SHOW REPLICA STATUS FOR CHANNEL 'source_a'\G
SHOW REPLICA STATUS FOR CHANNEL 'source_b'\G
```

要觀測：

1. IO thread / SQL thread status。
2. Seconds behind source。
3. Last IO error / SQL error。
4. Relay log growth。
5. GTID executed / retrieved。
6. Channel credential expiry。

Lag 要分 channel 告警。總體 replica 健康不足以定位哪個 source 卡住。

## Migration Pattern

Migration pattern 的核心責任是把 multi-source 用在可回退的搬遷。

| Phase        | Evidence                        |
| ------------ | ------------------------------- |
| Source audit | schema、GTID、binlog format     |
| Target setup | channel、filter、credential     |
| Backfill     | dump / load、checksum           |
| Catch-up     | channel lag、error              |
| Read test    | report query、row count         |
| Cutover      | read endpoint switch            |
| Cleanup      | stop channel、retention、secret |

Migration target 若只是 reporting，cutover 風險較低；若要成為 new primary，還要處理 write freeze、conflict、application route 與 rollback。

## Failure Modes

Failure modes 的核心責任是把 multi-source 事故分 channel 處理。

| Failure mode       | 判讀訊號              | 修正方向                           |
| ------------------ | --------------------- | ---------------------------------- |
| Single channel lag | 某 source 延遲        | 查 source load、network、SQL error |
| DDL drift          | replication SQL error | migration coordination             |
| Key collision      | duplicate key error   | namespace / key rewrite            |
| Relay log growth   | target apply 慢       | 調整 parallel apply、拆 workload   |
| Credential expired | IO thread stopped     | rotate secret、resume channel      |

Channel failure 要避免全局操作。只停問題 channel，保留其他 channel，能降低 blast radius。

## 下一步路由

Multi-source replication 完成後，基本拓撲讀 [Replication Topology](../replication-topology/)；failover 讀 [Orchestrator Failover](../orchestrator-failover/)；CDC 與 binlog 讀 [Binlog CDC](../binlog-cdc/)。
