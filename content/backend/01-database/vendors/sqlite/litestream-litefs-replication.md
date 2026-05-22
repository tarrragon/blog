---
title: "SQLite Litestream / LiteFS Replication"
date: 2026-05-21
description: "Litestream、LiteFS、SQLite backup replication、read replica、failover 與 restore route"
tags: ["backend", "database", "sqlite", "replication", "litestream"]
---

Litestream / LiteFS replication 的核心責任是把 SQLite 的 single-file operation 補成可恢復、可部署、可讀擴展的服務形狀。這類工具延伸 SQLite，但它們解決的問題不同：Litestream 主要把 WAL 變化持續送到 replica storage，強化 backup 與 restore；LiteFS 主要在 Fly.io 生態中透過 primary lease 與 filesystem layer 支援 replicated SQLite deployment。

本文的判讀錨點是：replicated SQLite 要先說明 replica 的服務責任。它可能是 continuous backup、warm restore source、read replica、primary failover helper 或 deployment topology；每一種責任都有不同的 RPO、RTO、freshness 與 incident runbook。

## Replication Taxonomy

Replication taxonomy 的核心責任是把「有複本」拆成可操作的幾種能力。SQLite 周邊工具常用 replication 這個字，但 operator 需要知道它到底保護哪個風險。

| 類型              | 主要責任                  | 成功訊號                       | 常見誤判                              |
| ----------------- | ------------------------- | ------------------------------ | ------------------------------------- |
| Continuous backup | 降低資料遺失窗口          | replica lag、restore 成功      | 把 replica 當 active-active database  |
| Read replica      | 降低 read latency / 壓力  | freshness、read error rate     | 忽略 stale read                       |
| Warm standby      | 縮短 restore / failover   | promotion drill、DNS / routing | 只備份檔案、未演練切換                |
| Primary lease     | 控制單一 writer ownership | writer lease、fencing log      | 多個 node 同時寫同一份邏輯狀態        |
| Consensus SQL     | 多節點一致性寫入          | quorum、leader election        | 用 WAL shipping 取代 distributed OLTP |

Continuous backup 的語言是 [RPO](/backend/knowledge-cards/rpo/) 與 [RTO](/backend/knowledge-cards/rto/)。它關心最近一次成功送出的 WAL、snapshot freshness、object storage credential、restore 指令與演練結果。

Read replica 的語言是 freshness。Replica 能降低 read latency 或保護 primary workload，但讀者要知道 stale window、read-after-write policy、fallback to primary 與 cache invalidation。

Primary lease 的語言是 writer ownership。SQLite 的服務形狀仍適合 single writer；工具可以協助 deployment 切換，但 application 要配合 fencing、retry 與 promotion evidence。

## Litestream Boundary

Litestream boundary 的核心責任是把 SQLite WAL 變成可持續複製的 backup stream。Litestream 官方說明把它定位為 SQLite streaming replication tool，並在 [How it works](https://litestream.io/how-it-works/) 與 [restore command](https://litestream.io/reference/restore/) 文件中強調 replica 與 restore workflow。

Litestream 適合下列情境：

1. 單節點 SQLite app 要降低資料遺失窗口。
2. 系統可接受 restore 後重新啟動 service。
3. Object storage credential、retention、restore drill 可以被管理。
4. Write pattern 適中，WAL stream 與 snapshot 維護成本可控。

Litestream 的設計重點是 backup evidence。Runbook 要記錄 replica destination、last replicated generation、last restore test、expected RPO、expected RTO、restore target path、credential rotation 與 corruption triage。

```bash
litestream restore -o /var/lib/app/restored.db s3://example-bucket/app.db
sqlite3 /var/lib/app/restored.db "PRAGMA integrity_check;"
```

這段命令是 restore drill 的最小骨架。正式 runbook 要補上 service stop、database path、sidecar file、permission、checksum、application smoke test 與 rollback decision。

Litestream 的風險集中在 restore path。備份存在和服務可恢復是兩件事；每次 release 或 schema migration 後，都應用 staging data 跑一次 restore、integrity check、row count 與 application smoke test。

## LiteFS Boundary

LiteFS boundary 的核心責任是支援 replicated deployment topology，而非只做 backup。LiteFS 在 Fly.io 文件中被定位為 SQLite replication layer，透過 FUSE filesystem 與 primary lease 模型協助應用在多個 instance 間運作。

LiteFS 適合下列情境：

1. App 仍希望使用 SQLite file 與 local SQL path。
2. Deployment 有多個 instance，但 write authority 可以集中到 primary。
3. Read replica freshness 可以被產品接受。
4. Team 願意把 filesystem layer、primary lease、promotion 與 platform operation 納入 runbook。

LiteFS 的設計重點是 primary ownership。Application 要知道 write request 到哪裡執行、primary 切換時如何重試、read replica 讀到舊資料時如何回應，以及 promotion 完成前哪些 endpoint 要進入 degraded mode。

LiteFS 的 incident route 要從 writer ownership 開始查。若出現 write error、stale read 或 suspected split brain，先查看 primary lease、instance health、replication lag、pending writes 與 platform network，再處理 application retry。

## Failure Modes

Failure modes 的核心責任是把 replicated SQLite 的事故從「資料庫壞了」拆成可排查訊號。SQLite file、WAL、object storage、filesystem layer、deployment platform 與 application retry 都可能是問題來源。

| Failure mode           | 判讀訊號                          | 立即處理                                   |
| ---------------------- | --------------------------------- | ------------------------------------------ |
| Replica lag            | last replicated time 落後         | 降低 write rate、檢查 credential / network |
| Restore lag            | WAL files 過多、restore time 變長 | 觸發 snapshot、演練 restore                |
| Stale read             | 使用者讀到舊資料                  | fallback primary read、標記 freshness      |
| Writer lease confusion | 多 instance write error           | 暫停寫入、確認 primary、fencing old writer |
| Object storage failure | backup upload error               | 切換 credential / destination、補上重送    |
| Sidecar file mismatch  | restore / copy 後 integrity fail  | 回到 backup API / official restore path    |

Replica lag 要接到 alert。對 Litestream，它意味著 RPO 正在擴大；對 LiteFS，它可能同時影響 read freshness 與 failover confidence。

Restore lag 要接到 release gate。若 restore time 已超過目標 [RTO](/backend/knowledge-cards/rto/)，就要調整 snapshot frequency、資料保留策略或搬到 server database。

Stale read 要接到產品語言。使用者看到舊資料時，系統可以顯示 sync state、重讀 primary、限制 critical action 或提供 refresh；這些策略要在設計階段決定。

## No-Go Conditions

No-go condition 的核心責任是避免把 replicated SQLite 推到 distributed OLTP 的位置。SQLite 周邊 replication 工具可以強化單節點與 read replica，但高寫入、多 writer、強一致跨 region transaction 需要不同資料庫模型。

| No-go 訊號                                   | 原因                                   | 路由                                                                |
| -------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------- |
| 多 region 都要接受交易性寫入                 | single writer / primary lease 壓力過高 | [CockroachDB](/backend/01-database/vendors/cockroachdb/) 或 Spanner |
| 每秒大量 concurrent writer                   | lock contention 與 replica lag 擴大    | PostgreSQL / MySQL / managed OLTP                                   |
| Central audit / DB role 是硬需求             | SQLite file model 缺少 server role     | [PostgreSQL](/backend/01-database/vendors/postgresql/)              |
| Restore drill 經常超過 RTO                   | file size / WAL backlog 已超界         | server DB、sharding 或資料生命週期重整                              |
| Incident team 缺少 filesystem layer 維護能力 | operation model 超過組織能力           | managed SQL 或 D1 / Turso managed path                              |

No-go 條件要在 design review 階段列出。SQLite replication 的好處是低成本與低元件數；當核心需求變成跨節點一致性寫入，繼續調工具會把風險藏在 incident 時刻。

## Decision Route

Decision route 的核心責任是把資料保護、讀擴展與高可用分開選型。Litestream / LiteFS 位置清楚時，SQLite 可以保持簡潔；位置混淆時，系統會同時缺 backup evidence 與 transaction guarantee。

| 需求                                      | 建議路由                                                                                          |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------- |
| 單節點 SQLite 需要 continuous backup      | Litestream + restore drill                                                                        |
| 多 instance deployment 需要 primary lease | LiteFS + write routing / promotion runbook                                                        |
| Edge app 需要 managed SQL-like platform   | [D1 / Turso / libSQL comparison](/backend/01-database/vendors/sqlite/d1-turso-libsql-comparison/) |
| 多 tenant OLTP 需要 central operation     | PostgreSQL / MySQL / Aurora                                                                       |
| Global transaction 是核心需求             | Distributed OLTP                                                                                  |

選擇 Litestream 時，完成標準是能在 staging 從 replica restore 出可用 DB。選擇 LiteFS 時，完成標準是能演練 primary 切換、read freshness、write retry 與 degraded mode。

## 下一步路由

Litestream / LiteFS replication 完成後，下一步要回到 SQLite operation evidence。File copy、backup API 與 WAL sidecar 請讀 [file lifecycle / backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/)；busy、lock 與 writer 壓力請讀 [WAL concurrency / locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)；完整 runbook 請讀 [SQLite observability / runbook](/backend/01-database/vendors/sqlite/observability-runbook/)。
