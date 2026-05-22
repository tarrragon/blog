---
title: "SQLite D1 / Turso Preview Lab"
date: 2026-05-21
description: "SQLite local DB 匯出到 Cloudflare D1 或 Turso preview environment 的 compatibility、latency 與 rollback 操作說明"
tags: ["backend", "database", "sqlite", "hands-on", "edge"]
---

SQLite D1 / Turso preview lab 的核心責任是把 local SQLite 轉向 edge SQLite product 前的 compatibility gap 找出來。這篇承接 [D1 / Turso / libSQL Comparison](/backend/01-database/vendors/sqlite/d1-turso-libsql-comparison/) 與 [SQLite to D1 / Turso Migration](/backend/01-database/vendors/sqlite/migrate-to-d1-turso/)，把 edge migration 變成可回報的 query matrix。

本文的驗收標準是：你能從 local SQLite 匯出 schema / seed，匯入 D1 或 Turso preview database，跑相同 query set，記錄 unsupported SQL、latency、error mapping 與 rollback route。

## Preview Scope

Preview scope 的核心責任是把 lab 限制在 staging / preview。D1 與 Turso 都是平台產品，實際命令會依 CLI version、帳號、region 與專案設定改變；本文提供操作骨架與 evidence 格式，正式命令以官方文件為準。

官方文件路由：

| 產品                    | 官方文件                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------ |
| Cloudflare D1           | [Cloudflare D1 docs](https://developers.cloudflare.com/d1/)                          |
| D1 limits               | [Cloudflare D1 limits](https://developers.cloudflare.com/d1/platform/limits/)        |
| Turso                   | [Turso docs](https://docs.turso.tech/)                                               |
| Turso embedded replicas | [Embedded replicas](https://docs.turso.tech/features/embedded-replicas/introduction) |

Preview lab 要先確認資料不含 production PII。若 seed data 來自正式資料，先做 masking 或 synthetic data。

## Export Local SQLite

Export local SQLite 的核心責任是建立 target platform 的 seed input。沿用 `/tmp/sqlite-lab/app.db` 或 migration fixture。

```bash
mkdir -p /tmp/sqlite-edge-lab
cd /tmp/sqlite-edge-lab
cp /tmp/sqlite-lab/app.db ./app.db
sqlite3 app.db ".schema" > schema.sql
sqlite3 app.db ".dump" > seed.sql
sqlite3 app.db "SELECT COUNT(*) FROM accounts;"
sqlite3 app.db "SELECT COUNT(*) FROM ledger_entries;"
```

`schema.sql` 用來審查 DDL，`seed.sql` 用來匯入 preview database。正式 migration 可能要拆 schema / data / index，並處理 target platform limits。

## Build Query Matrix

Build query matrix 的核心責任是定義 preview 要驗證什麼。query set 要代表產品行為，而非只跑一個 `SELECT 1`。

```text
Q1 list account balances
Q2 insert ledger entry with unique idempotency key
Q3 insert duplicate idempotency key and capture error
Q4 foreign key violation
Q5 transaction rollback
Q6 pagination by created_at
Q7 explain / performance sample if platform supports it
```

這份 matrix 要保存 expected result。Local SQLite 先跑一次，把 row count、error category、latency baseline 記下來。

```bash
sqlite3 app.db <<'SQL'
.timer on
SELECT a.id, a.owner_name, SUM(l.amount_cents) AS balance_cents
FROM accounts a
JOIN ledger_entries l ON l.account_id = a.id
GROUP BY a.id, a.owner_name
ORDER BY a.id;
SQL
```

## Import to D1 Preview

Import to D1 preview 的核心責任是驗證 Cloudflare D1 workflow。以下是操作骨架，正式命令與 flags 以 Cloudflare D1 docs 和 Wrangler 版本為準。

```bash
# Example shape only. Use your project naming and official Wrangler docs.
wrangler d1 create sqlite_edge_preview
wrangler d1 execute sqlite_edge_preview --file=seed.sql
wrangler d1 execute sqlite_edge_preview --command="SELECT COUNT(*) FROM accounts;"
```

D1 preview evidence 要記錄：

| Evidence     | 內容                                |
| ------------ | ----------------------------------- |
| CLI version  | Wrangler version、account / project |
| Import log   | duration、file size、error          |
| Query result | 每個 query 的 row count / error     |
| Limit hit    | D1 limits 是否影響 seed 或 query    |
| Rollback     | 刪除 preview DB 或重建 seed         |

若 seed file 太大或某些 SQL 需要改寫，就把 gap 寫進 compatibility matrix，先保留 production migration 的審查邊界。

## Import to Turso Preview

Import to Turso preview 的核心責任是驗證 remote database、client SDK 與 embedded replica 行為。以下是操作骨架，正式命令以 Turso docs 與 CLI version 為準。

```bash
# Example shape only. Use your org, group, region and official Turso docs.
turso db create sqlite-edge-preview
turso db shell sqlite-edge-preview < seed.sql
turso db shell sqlite-edge-preview "SELECT COUNT(*) FROM accounts;"
```

Turso preview evidence 要多記 replica freshness。若使用 embedded replica，測試流程要包含 bootstrap、sync、read query、write delegation 與 sync 後 read。

```text
embedded replica evidence:
  bootstrap duration
  first read latency
  write path
  sync command / interval
  read freshness after write
```

Freshness 是 product decision。若 query matrix 只測 remote primary，仍需要追加 embedded replica 的使用者體驗驗證。

## Compatibility Matrix

Compatibility matrix 的核心責任是把 local SQLite 與 edge target 的差異留下來。建議表格欄位如下：

| Query / operation    | Local SQLite | D1 preview       | Turso preview    | Decision          |
| -------------------- | ------------ | ---------------- | ---------------- | ----------------- |
| Balance list         | pass         | pass / diff      | pass / diff      | keep / rewrite    |
| Unique violation     | error class  | error class      | error class      | map error         |
| FK violation         | error class  | error class      | error class      | enable / validate |
| Transaction rollback | pass         | pass / diff      | pass / diff      | rewrite workflow  |
| Import seed          | pass         | duration / limit | duration / limit | split batch       |

Decision 欄要寫具體下一步。`rewrite workflow` 代表 application adapter 要改；`split batch` 代表 migration runbook 要改；`map error` 代表 repository error classification 要改。

## Latency and Cost Sample

Latency and cost sample 的核心責任是避免只看功能相容。Edge SQLite migration 的收益常來自 region latency 或 managed operation，因此 preview 要量測主要使用者區域的 read / write latency。

最小量測：

1. Local baseline latency。
2. Preview target read latency。
3. Preview target write latency。
4. Error rate / retry count。
5. Estimated request / storage / egress cost。

Latency sample 要搭配 freshness。快速讀到舊資料和稍慢讀到最新資料是不同產品體驗；query matrix 要標註哪個 workflow 可以接受 stale read。

## Rollback Route

Rollback route 的核心責任是保留 local SQLite 退路。Preview lab 完成後，要能刪除 preview database、保留 local seed、重跑 local app。

```bash
sqlite3 app.db "PRAGMA integrity_check;"
sqlite3 app.db "SELECT COUNT(*) FROM accounts;"
sqlite3 app.db "SELECT COUNT(*) FROM ledger_entries;"
```

正式 cutover 的 rollback 還要處理 target-only writes。Preview 階段應避免讓真實使用者寫入 target；若需要 shadow traffic，先用 read-only 或 synthetic write。

## Completion Note

Completion note 的核心責任是決定是否進入正式 migration。Lab 完成後應輸出四個 artifact：`seed.sql`、import log、compatibility matrix、rollback note。

進入正式 migration 的條件：

1. Query matrix 主要 workflow 通過或已有 rewrite plan。
2. Platform limits 對資料量與 migration time 可接受。
3. Error mapping 已接到 repository adapter。
4. Freshness / latency 符合產品需求。
5. Export / rollback route 已演練。

完成本篇後，回到 [SQLite to D1 / Turso Migration](/backend/01-database/vendors/sqlite/migrate-to-d1-turso/) 補正式 phase plan。
