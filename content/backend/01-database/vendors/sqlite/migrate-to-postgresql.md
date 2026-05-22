---
title: "SQLite to PostgreSQL Migration"
date: 2026-05-21
description: "SQLite 升級到 PostgreSQL 的 driver、schema diff、data copy、dual run、cutover、rollback 與 cleanup"
tags: ["backend", "database", "sqlite", "postgresql", "migration"]
---

SQLite to PostgreSQL migration 的核心責任是把 embedded single-file state 升級成 server SQL operational model。這條路線通常由 multi-user access、HA、central audit、permission、online schema governance、write concurrency 或 team handoff 壓力觸發。

本文的判讀錨點是：升級到 PostgreSQL 是服務責任擴大，而非單純換 driver。Migration 要同時處理 schema 語意、資料搬遷、application adapter、backup / PITR、role、observability、cutover 與 rollback。

## Migration Drivers

Migration drivers 的核心責任是確認 PostgreSQL 真的承擔新增責任。SQLite 在 single-node、single-file、low-concurrency 場景很強；PostgreSQL 的價值出現在 server database governance。

| Driver               | 代表需求                        | PostgreSQL 承擔的責任                     |
| -------------------- | ------------------------------- | ----------------------------------------- |
| Concurrent writers   | 多 instance / 多使用者同時寫入  | MVCC、connection management、lock insight |
| HA / PITR            | 需要時間點恢復與 managed backup | WAL archiving、replica、restore drill     |
| Central audit        | 需要查詢與變更證據              | role、log、extension、SIEM integration    |
| Permission boundary  | app / analyst / job 權限分離    | DB role、grant、row / schema boundary     |
| Schema governance    | migration 要 online 且可審查    | migration tool、lock review、rollback     |
| Shared data platform | 多服務共用正式資料              | connection pool、capacity、ownership      |

Driver 要被量化。若問題只是單一 CLI 檔案變大，先改善 backup、VACUUM、index 與 WAL runbook；若問題是多 instance 同時寫、權限分離、audit 與 PITR，PostgreSQL 才是正確路由。

## Diff Audit

Diff audit 的核心責任是把 SQLite 語意轉成 PostgreSQL 語意。SQLite 的 type affinity、date / time convention、auto-increment、foreign key、index、JSON、transaction 與 extension 都要逐項審查。

| 面向        | SQLite source 問題                    | PostgreSQL target 決策                   |
| ----------- | ------------------------------------- | ---------------------------------------- |
| Type        | dynamic typing、STRICT usage          | integer / bigint / numeric / timestamptz |
| Primary key | rowid、INTEGER PRIMARY KEY            | identity、sequence、UUID                 |
| Date/time   | TEXT / INTEGER convention             | timestamptz、timezone policy             |
| JSON        | JSON text / function usage            | jsonb、GIN index、query rewrite          |
| Constraint  | FK pragma、check、unique collation    | enforced FK、deferrable、collation       |
| Index       | partial / expression / covering index | equivalent index + explain               |
| Transaction | single writer、savepoint              | isolation level、deadlock retry          |

Type mapping 要先保護 domain invariant。金額欄位用 integer cents 或 numeric、時間欄位用 timestamptz 或明確 UTC text、boolean 用 boolean；每個轉換都要有 invalid sample 與 round-trip test。

Index mapping 要用 production query 重跑 explain。SQLite 的 `EXPLAIN QUERY PLAN` 只能說明 SQLite planner；PostgreSQL 需要自己的 `EXPLAIN (ANALYZE, BUFFERS)`，並使用接近真實分布的資料量。

## Phase Plan

Phase plan 的核心責任是降低一次性 cutover 風險。SQLite to PostgreSQL migration 通常可以分成 schema 建模、資料匯出、adapter 切換、shadow read、freeze / cutover 與 cleanup。

| Phase          | 目的                          | Evidence                               |
| -------------- | ----------------------------- | -------------------------------------- |
| Schema rewrite | 建立 PostgreSQL target schema | migration dry run、schema review       |
| Data export    | 從 SQLite 取出穩定 snapshot   | source checksum、row count、export log |
| Data import    | 寫入 PostgreSQL               | target checksum、constraint validation |
| Adapter layer  | 將 repository 改為可切換      | dual test suite、error mapping         |
| Shadow read    | 比對新舊 query result         | mismatch report、latency profile       |
| Cutover        | 切正式寫入                    | freeze window、rollback snapshot       |
| Cleanup        | 退役 SQLite write path        | retention、credential、runbook update  |

Adapter layer 是風險控制點。Repository 應把 SQLite 與 PostgreSQL driver 差異藏在 infrastructure layer，domain 不直接依賴 vendor-specific SQL exception 或 connection object。

Shadow read 適合先驗證 read contract。正式寫入仍留在 SQLite 時，background job 可以把相同 query 跑到 PostgreSQL mirror，記錄 row count、field diff、排序差異與 latency。

## Data Movement

Data movement 的核心責任是讓搬遷結果可驗證。SQLite database file 可以透過 `.dump`、CSV export、application-level export 或 custom ETL 搬入 PostgreSQL；選擇取決於資料量、型別轉換、FK order 與 downtime window。

```bash
sqlite3 app.db ".mode csv" ".headers on" ".once orders.csv" "SELECT * FROM orders ORDER BY id;"
psql "$DATABASE_URL" -c "\\copy orders FROM 'orders.csv' CSV HEADER"
```

這段命令是教學骨架。正式 migration 要處理 quoting、NULL、timezone、large object、FK order、batch size、transaction size、retry、import log 與 sensitive data handling。

Row count 是基本證據，checksum 是更強證據。可以針對每張表計算穩定排序後的 hash，或在 application layer 對 domain key 與重要欄位做 checksum。

```sql
SELECT COUNT(*) FROM orders;
SELECT SUM(total_cents) FROM orders;
```

Aggregate checksum 適合快速抓大錯。正式驗證還要補抽樣 row diff、edge case row、foreign key check 與 business invariant。

## Cutover

Cutover 的核心責任是控制最後一次寫入切換。SQLite source 在 cutover 前應進入 read-only 或 writer freeze，確保最後 snapshot、import 與 validation 對齊。

| Cutover step   | 操作                                  | Rollback 條件                              |
| -------------- | ------------------------------------- | ------------------------------------------ |
| Freeze writers | 停止背景 job、API write、admin tool   | source 寫入仍持續或 freeze 失敗            |
| Final snapshot | SQLite backup / export                | checksum 失敗                              |
| Final import   | PostgreSQL transaction / batch import | constraint error、row mismatch             |
| Smoke test     | 核心 read/write workflow              | error rate、latency、permission failure    |
| Switch traffic | 更新 config / secret / deployment     | application error rate 超過 tripwire       |
| Monitor        | query latency、lock、connection pool  | pool exhaustion、deadlock spike、data diff |

Rollback 要保存 source snapshot。若 cutover 後發現 PostgreSQL error mapping、permission 或 performance 問題，可以切回 SQLite read/write snapshot；前提是 cutover window 內所有新寫入都能回放或被阻擋。

## PostgreSQL Operation Gate

PostgreSQL operation gate 的核心責任是確認團隊準備好接手 server DB。Migration 成功要包含資料進入 target 與 operation readiness；PostgreSQL 需要 connection pool、backup / PITR、vacuum、index bloat、role、migration lock review 與 alert。

最小 operation checklist：

1. Connection pool 設計：max connections、pool size、timeout、transaction pooling policy。
2. Backup / PITR：restore drill、retention、RPO / RTO。
3. Role / grant：application role、migration role、read-only role。
4. Migration lock review：DDL impact、online migration strategy。
5. Observability：slow query、lock wait、deadlock、replica lag、disk。
6. Incident route：rollback、restore、read-only mode、on-call owner。

這個 gate 要在 cutover 前完成。SQLite 讓 operation surface 很小；PostgreSQL 擴大能力的同時，也擴大維護責任。

## No-Go Conditions

No-go condition 的核心責任是阻止過早升級。若服務仍是 single-user、local-first、low-write、可用簡單 backup 解決，PostgreSQL 可能引入比問題更大的 operation cost。

| No-go 訊號                        | 更合適路由                                                                                |
| --------------------------------- | ----------------------------------------------------------------------------------------- |
| Single-user app 或 desktop app    | 保留 SQLite + backup / migration runbook                                                  |
| 主要壓力是備份                    | [Litestream / LiteFS](/backend/01-database/vendors/sqlite/litestream-litefs-replication/) |
| 主要壓力是 edge locality          | [D1 / Turso route](/backend/01-database/vendors/sqlite/migrate-to-d1-turso/)              |
| Team 尚未準備 server DB operation | 先補 observability / restore drill                                                        |
| Schema / query 還在快速探索       | 先穩定 domain model，再做正式 migration                                                   |

No-go 條件要轉成 tripwire。當 writer concurrency、audit、PITR、role 或 HA 需求跨過明確門檻，再啟動 migration。

## 下一步路由

SQLite to PostgreSQL migration 完成後，下一步要看 target operation。PostgreSQL 能力讀 [PostgreSQL](/backend/01-database/vendors/postgresql/)；migration 方法讀 [Database Migration Playbook](/backend/01-database/database-migration-playbook/)；若需求只是 edge platform，改讀 [SQLite to D1 / Turso migration](/backend/01-database/vendors/sqlite/migrate-to-d1-turso/)。
