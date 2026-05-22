---
title: "PostgreSQL to SQLite Simplification"
date: 2026-05-21
description: "PostgreSQL 降低操作成本轉向 SQLite 的適用條件、資料責任縮小、export/import、runbook 與 no-go condition"
tags: ["backend", "database", "sqlite", "postgresql", "migration"]
---

PostgreSQL to SQLite simplification 的核心責任是處理反向路線：服務責任縮小後，評估 SQLite 是否能降低操作成本。這條路線適合 single-user app、CLI、desktop app、內部工具、read-mostly artifact store、demo environment、local-first prototype 或 edge-local utility。

本文的判讀錨點是：降級到 SQLite 是責任縮小，也是讓資料模型回到 single-process / file-owned / local-state 的工程選擇。只要正式需求從 multi-user server DB 回到這個範圍，SQLite 可以提供更低元件數、更容易搬移與更低維護成本。

## Simplification Drivers

Simplification drivers 的核心責任是確認 PostgreSQL 的能力已超過服務需求。若 server DB 的 HA、role、replica、pool、vacuum、PITR、schema governance 都變成維運負擔，而產品只需要單一 process 持有資料，就可以評估 SQLite。

| Driver               | 代表情境                           | SQLite 帶來的收益                        |
| -------------------- | ---------------------------------- | ---------------------------------------- |
| Single-user app      | desktop、CLI、local admin tool     | file portability、offline use            |
| Read-mostly artifact | build metadata、catalog snapshot   | deployment simple、低 runtime dependency |
| Internal tool        | 小團隊使用、資料量小、低寫入       | 降低 DB server operation                 |
| Demo / fixture       | 每個 environment 一份可重建資料    | quick reset、deterministic seed          |
| Edge-local utility   | request-local / device-local state | low latency、local ownership             |

Driver 要連到 ownership。SQLite 適合「這份資料由某個 process / device / artifact 明確持有」；若資料仍屬於多服務共同真相，保留 PostgreSQL 或改成 managed SQL 會更穩定。

## No-Go Conditions

No-go condition 的核心責任是保護仍需要 server DB 的服務。若 PostgreSQL 的核心能力仍被業務依賴，遷到 SQLite 會把風險轉移到 application code、file backup 與人工流程。

| No-go 訊號                          | 代表責任                          | 保留路由                            |
| ----------------------------------- | --------------------------------- | ----------------------------------- |
| 多 tenant 與 centralized permission | DB role、grant、audit 仍有價值    | PostgreSQL                          |
| 多 instance concurrent writer       | SQLite writer boundary 壓力過高   | PostgreSQL / MySQL                  |
| PITR / HA 是合約要求                | server DB operation 是正式責任    | Managed PostgreSQL / Aurora         |
| Analyst / job 直接查 DB             | access control 與 query isolation | PostgreSQL read replica / warehouse |
| Cross-service source of truth       | 單檔 ownership 與服務邊界衝突     | 保留 server DB 或拆 bounded context |

No-go 條件要寫進 migration proposal。Simplification 的目標是降低操作成本；若降級後要用大量自製機制補回 role、audit、HA 與 concurrent write，成本會回到系統裡。

## Diff Audit

Diff audit 的核心責任是把 PostgreSQL 語意縮到 SQLite 可以清楚承擔的範圍。PostgreSQL extension、function、type、index、constraint、sequence、view、trigger、role 與 transaction behavior 都要盤點。

| PostgreSQL feature  | SQLite 轉換策略                        | 審查問題                            |
| ------------------- | -------------------------------------- | ----------------------------------- |
| `timestamptz`       | UTC ISO text 或 integer epoch          | timezone policy 是否固定            |
| `jsonb` + GIN       | JSON text + limited query / app filter | query 是否仍需 index                |
| Sequence / identity | INTEGER PRIMARY KEY 或 app ID          | id stability 與 import collision    |
| Partial index       | SQLite partial index                   | predicate 與 query planner 是否對齊 |
| Role / grant        | filesystem permission + app auth       | 權限是否可移到 application boundary |
| Extension           | application logic 或放棄 feature       | feature 是否仍是正式需求            |

Diff audit 的輸出是一份保留 / 移除 / 改寫清單。每個 PostgreSQL feature 都要回答：這是正式需求、歷史殘留，還是可以移到 application layer 的便利功能。

## Phase Plan

Phase plan 的核心責任是把 server DB 退場變成可回復流程。反向 migration 要超過一次性 dump：先收斂寫入、建立 SQLite schema、匯入資料、跑 adapter test、演練 backup，再退役 PostgreSQL。

| Phase             | 目的                              | Evidence                                      |
| ----------------- | --------------------------------- | --------------------------------------------- |
| Scope reduction   | 確認資料責任已縮小                | ownership doc、no-go review                   |
| Schema rewrite    | 建立 SQLite schema                | migration dry run、STRICT / constraint        |
| Data export       | 從 PostgreSQL 匯出 snapshot       | row count、checksum、dump metadata            |
| Data import       | 寫入 SQLite file                  | integrity check、foreign key check            |
| Adapter switch    | app 改用 SQLite repository        | contract test、error mapping                  |
| Backup runbook    | 建立 file lifecycle evidence      | backup restore drill                          |
| Server retirement | 關閉 PostgreSQL 寫入與 credential | retention、credential removal、incident route |

Scope reduction 是第一關。若資料仍被多個服務寫入，應先拆出 bounded context 或建立 event / export boundary；SQLite file 才能成為明確 owned artifact。

## Data Movement

Data movement 的核心責任是把 PostgreSQL snapshot 轉成 SQLite file 並保留驗證。可用 `COPY` / CSV、application ETL 或 dedicated migration tool；選擇取決於 type conversion 與資料量。

```bash
psql "$DATABASE_URL" -c "\\copy orders TO 'orders.csv' CSV HEADER"
sqlite3 app.db ".mode csv" ".import --skip 1 orders.csv orders"
sqlite3 app.db "PRAGMA integrity_check;"
```

這段命令是教學骨架。正式流程要處理 NULL、delimiter、timezone、numeric precision、FK order、transaction、temporary disk、sensitive data 與 import log。

Import 後要跑三種 evidence：database integrity、row count / checksum、business invariant。Business invariant 例如 active user count、total balance、latest event id、pending job count；這些比單純 row count 更能抓到語意錯誤。

## Runbook Shift

Runbook shift 的核心責任是把 PostgreSQL operation 移轉成 SQLite file operation。Server DB 的 backup / role / monitoring 退場後，要補上 SQLite 的 backup、restore、file permission、WAL、migration 與 disk 觀測。

最小 SQLite runbook 包含：

1. Database file path、owner process、filesystem permission。
2. Journal mode、busy timeout、foreign key、schema version。
3. Backup command、restore drill、retention、checksum。
4. Migration command、pre-migration snapshot、rollback path。
5. Observability：busy、WAL size、disk free、backup age。
6. Incident route：disk full、bad migration、corruption signal。

Runbook shift 要同步移除 PostgreSQL credential。Server database 退役時，保留 read-only archive、刪除 application secret、關閉 scheduled job、更新 dashboard 與 incident routing。

## Cleanup and Retention

Cleanup and retention 的核心責任是讓舊 PostgreSQL 不再成為影子真相。Migration 後若舊 DB 長期可寫，團隊會在事故中分不清哪份資料有效。

| Cleanup 項目       | 操作                                           |
| ------------------ | ---------------------------------------------- |
| Write disable      | PostgreSQL role 改 read-only 或關閉 app access |
| Archive snapshot   | 保存最後 dump、checksum、schema                |
| Credential removal | 移除 app secret、CI secret、admin token        |
| Dashboard update   | 停用 PostgreSQL alert、啟用 SQLite alert       |
| Documentation      | 更新 source-of-truth 與 restore route          |

Retention 要和 data protection 對齊。若 PostgreSQL 內有 PII、audit log 或 legal retention，退役流程要依 retention policy 保存或銷毀，而非直接刪除。

## Decision Route

Decision route 的核心責任是讓 simplification 保持可逆。若未來 concurrent writer、central audit、PITR 或 multi-service source-of-truth 回來，系統要能沿 [SQLite to PostgreSQL migration](/backend/01-database/vendors/sqlite/migrate-to-postgresql/) 重新升級。

| 現況                               | 建議                              |
| ---------------------------------- | --------------------------------- |
| Single-user / local artifact       | SQLite simplification             |
| Small internal tool + low write    | SQLite + restore drill            |
| Read-mostly dataset for app bundle | SQLite artifact + release version |
| Multi-user SaaS                    | 保留 PostgreSQL                   |
| Audit / HA / role 是正式要求       | 保留 managed PostgreSQL           |

Simplification 的完成標準是：SQLite file 可以被重建、備份、恢復、升級與交接。只要這些 evidence 完整，從 PostgreSQL 退到 SQLite 是清楚的工程決策。

## 下一步路由

PostgreSQL to SQLite simplification 完成後，先讀 [file lifecycle / backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/) 建立 file operation；再讀 [SQLite observability / runbook](/backend/01-database/vendors/sqlite/observability-runbook/) 補 evidence；若之後需求再成長，回到 [SQLite to PostgreSQL migration](/backend/01-database/vendors/sqlite/migrate-to-postgresql/)。
