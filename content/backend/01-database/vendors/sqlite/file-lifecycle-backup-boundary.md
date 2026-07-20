---
title: "SQLite file lifecycle 與 backup boundary"
date: 2026-05-21
description: "把 SQLite 單檔案正式狀態拆成 WAL、backup API、restore drill、corruption recovery 與操作責任邊界"
tags: ["backend", "database", "sqlite", "backup", "wal", "deep-article"]
---

> 本文是 [SQLite](/backend/01-database/vendors/sqlite/) overview 的 implementation-layer deep article。Overview 已說明 SQLite 適合 embedded、local-first、edge 與低操作成本場景；本文聚焦 *SQLite 檔案生命週期 + backup / restore 邊界*。

SQLite 的 file lifecycle 是把「一個資料庫檔案」升級成正式狀態的操作契約。SQLite 省掉 server process、帳號管理與網路連線，但它把 durability、backup、restore、locking 與 corruption recovery 放回 application process、filesystem 與 runbook；讀者要判斷的是這些責任是否已經有人承擔。

這篇文章適合三種情境。第一種是 CLI、desktop、mobile 或 edge service 已經用 SQLite 保存正式資料；第二種是 single-instance backend 想用 SQLite 降低操作成本；第三種是 test fixture 用 SQLite，但需要知道哪些差異會讓 production database 的 bug 漏掉。

## 核心模型：資料庫檔案是一組受 SQLite 管理的狀態檔

SQLite 的資料庫狀態由 main database file 與 journal / WAL sidecar 共同構成。Rollback journal mode 會在寫入期間產生 journal file；WAL mode 會讓寫入先進入 `-wal` 檔，並用 `-shm` 檔協調 reader / writer。操作上看似「一個 `.db` 檔」，production runbook 要把 sidecar file、checkpoint、backup API 與 restore test 一起納入。

| 檔案 / 機制 | 服務責任                          | 操作判讀                                                    |
| ----------- | --------------------------------- | ----------------------------------------------------------- |
| `.db`       | 持久化資料、schema、index         | file owner、permission、storage durability、snapshot 位置   |
| `-wal`      | WAL mode 下尚未 checkpoint 的寫入 | WAL growth、checkpoint cadence、backup 是否包含一致快照     |
| `-shm`      | WAL index 與跨 connection 協調    | local filesystem lock 是否可靠、部署是否跨 process 共用檔案 |
| checkpoint  | 把 WAL 內容合併回 main database   | checkpoint latency、writer pause、檔案大小是否持續膨脹      |
| backup API  | 線上複製一致 snapshot             | backup 是否在 application 還活著時仍能取得一致狀態          |

這張表的讀法是先找「誰有權改檔案」。SQLite 的核心風險多半來自繞過 SQLite library 的檔案操作，例如直接 copy 活躍 WAL database、把 database 放在 lock 語意不可靠的 filesystem、或讓多個不協調的 process 同時寫同一份檔案。

## WAL mode：讀取並發提升後，writer boundary 仍然存在

WAL mode 的工程價值是讓 reader 與 writer 的衝突下降。讀取可以看 main database 加上 WAL 中的 snapshot，寫入則 append 到 WAL；這讓 read-heavy workload 比 rollback journal mode 更容易撐住互動式服務。

WAL mode 同時保留 single writer boundary。SQLite 仍以檔案鎖與 transaction serialisation 控制寫入；寫入交易越長，其他 writer 等待時間越長，application 看到的訊號通常是 `SQLITE_BUSY`、latency spike 或 background job 卡住。

| 訊號                  | 常見原因                              | 第一輪處理                                                       |
| --------------------- | ------------------------------------- | ---------------------------------------------------------------- |
| `SQLITE_BUSY` 增加    | 長交易、background migration、慢 disk | 縮短 write transaction、加 busy timeout、把批次寫入切小          |
| `-wal` 檔持續變大     | checkpoint 追不上、long reader 卡住   | 找出長讀取、調整 checkpoint cadence、把 analytics query 移出路徑 |
| restore 後資料落差    | backup 沒取得一致 snapshot            | 改用 `.backup` / backup API / `VACUUM INTO`，並演練 restore      |
| latency 受 fsync 拉高 | `synchronous=FULL` + 高寫入頻率       | 重新定義 durability 需求，評估 server SQL 或 managed service     |

WAL mode 的 capacity gate 是「寫入是否仍能用一個 writer 排隊」。如果服務壓力來自大量並行寫入、多 instance active write 或跨 region 寫入，SQLite 的簡單性開始變成排隊與恢復成本；這時候要回到 [PostgreSQL](/backend/01-database/vendors/postgresql/)、[MySQL](/backend/01-database/vendors/mysql/) 或 [global distributed OLTP](/backend/01-database/global-distributed-oltp/)。

## Backup boundary：複製檔案與取得一致 snapshot 是兩件事

SQLite backup 的核心責任是取得某一時間點的一致 snapshot。當 database live 且 WAL mode 開啟時，直接複製 `.db` 檔容易漏掉 `-wal` 中尚未 checkpoint 的寫入；即使同時複製 sidecar file，也要面對複製期間狀態變動的 race。正式服務應使用 SQLite 提供的 backup path 或可驗證的 filesystem snapshot。

| 方法                   | 適合情境                             | 邊界                                                            |
| ---------------------- | ------------------------------------ | --------------------------------------------------------------- |
| `.backup` / Backup API | live database、application 仍在服務  | SQLite 管理 source lock，產出開始備份時的一致 snapshot          |
| `VACUUM INTO`          | 想同時 compact + 輸出新檔            | 需要 I/O 空間與時間，適合 maintenance 或低流量窗口              |
| filesystem snapshot    | VM / volume 層已有一致 snapshot 能力 | 要確認 snapshot 包含 main file 與 WAL sidecar，且 lock 語意清楚 |
| Litestream             | single-primary SQLite 的持續備份     | 適合 DR / restore，不把 SQLite 變成 multi-primary database      |
| 手動 `cp`              | database 已關閉或已完成 checkpoint   | live WAL database 的一致性風險高，production runbook 應改路由   |

Backup method 的選擇要先回到 [RPO](/backend/knowledge-cards/rpo/) 與 [RTO](/backend/knowledge-cards/rto/)。如果產品可以接受每天一次快照，`VACUUM INTO` 或 scheduled backup 足夠；如果資料損失窗口要降到分鐘級或秒級，就要看 Litestream 類連續複製，或直接升級到 server database 的 PITR / replica 模型。

## Restore drill：SQLite production readiness 看還原，不只看備份成功

Restore drill 的責任是證明備份能在事故時接回服務。SQLite 的備份檔通常只有一個 target file，表面上比 PostgreSQL PITR 或 MySQL binlog recovery 簡單；真正的風險在 application binary、schema migration version、file permission、deployment path 與舊 WAL sidecar 是否一起對齊。

一個最小 restore drill 應保留五個檢查點：

1. 從備份產出新的 database file，不覆蓋 production path。
2. 用 application binary 啟動 read-only smoke test，確認 schema version 與 migration table。
3. 跑 row count、critical query、checksum 或 domain validation query。
4. 驗證 file owner、permission、disk path、SELinux / container mount 或 volume 設定。
5. 以 incident decision log 記錄 restore time、data freshness、known gap 與 owner。

Restore drill 的交付物應接回 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 與 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。SQLite 的低操作成本來自日常元件少；事故時仍需要 evidence、owner 與 rollback condition。

## Corruption recovery：先保全證據，再決定修復或還原

SQLite [corruption recovery](/backend/knowledge-cards/corruption-recovery/) 的核心責任是區分「資料庫檔案本身受損」與「application 寫入了錯誤資料」。前者要走 file-level evidence、`.recover`、backup restore 與 filesystem / hardware investigation；後者要走資料修復、migration rollback 或 business [reconciliation](/backend/knowledge-cards/data-reconciliation/)。

| 觀察訊號                      | 優先判讀                    | 下一步路由                                                                                                          |
| ----------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `SQLITE_CORRUPT`              | database page / btree 受損  | 複製原檔保存證據、用 `.recover` 嘗試導出、從最近 backup 建新檔                                                      |
| power loss 後啟動異常         | journal / WAL recovery 問題 | 確認 sidecar file 是否仍在、檢查 storage sync 與 `synchronous` 設定                                                 |
| restore 後 business data 錯誤 | 備份點或 migration 錯誤     | 對照 validation query、migration log、事件補償與 [reconciliation](/backend/01-database/reconciliation-data-repair/) |
| network filesystem 上偶發錯誤 | lock 語意與 filesystem 問題 | 把 SQLite 移回 local disk，或升級 server database                                                                   |

Corruption 事件的第一個操作是保存原始檔案與 sidecar。直接在疑似受損檔案上跑修復、vacuum 或 application migration，會讓後續 root cause analysis 失去證據；比較穩定的流程是複製原檔、在副本上嘗試 `.recover`，同時從備份恢復服務路徑。

## Anti-recommendation：維持 SQLite 的條件要可被操作驗證

SQLite 的合理使用條件是「單一 writer、檔案生命週期清楚、restore drill 成立」。只要這三件事能被 runbook 驗證，SQLite 在 embedded、desktop、mobile、edge-local 或 small backend 場景可以是 production state。

升級條件則來自操作責任外溢。需要 database user / role、中心化 audit、多人同時寫、跨 instance failover、online schema migration、PITR、read replica 或跨 region transaction 時，server SQL 或 managed SQL 的操作模型會比繼續包裝 SQLite 清楚。

| 目前壓力                | 留在 SQLite 的條件                       | 升級路由                                                    |
| ----------------------- | ---------------------------------------- | ----------------------------------------------------------- |
| read-heavy local store  | WAL + restore drill 成立                 | 維持 SQLite，補 observability 與 backup evidence            |
| single-instance backend | writer queue 可接受、RPO / RTO 明確      | SQLite + Litestream；或升級 PostgreSQL / MySQL              |
| edge / serverless       | 平台已提供 SQLite-compatible 運作模型    | Cloudflare D1 / Turso；跨 region transaction 回到 global DB |
| multi-tenant SaaS       | tenant 數少且 file ownership 清楚        | PostgreSQL / Aurora / CockroachDB                           |
| regulated data          | backup encryption、audit、restore 可驗證 | PostgreSQL / managed SQL + audit / PITR                     |

這張表的核心是把操作責任具體化，而非替 SQLite 設流量天花板。小型服務可能用 SQLite 長期穩定運作；同樣流量下，一旦合規、稽核、多人操作或 HA 需求進來，server database 的長期成本會更容易被治理。

## 操作檢查清單

SQLite production runbook 至少要能回答下列問題：

1. Database file、WAL sidecar 與 backup target 在哪個 volume、由誰擁有。
2. `journal_mode`、`synchronous`、busy timeout、checkpoint cadence 與 migration policy 如何設定。
3. Backup 用 `.backup` / backup API / `VACUUM INTO` / Litestream 的哪一條路徑。
4. Restore drill 最近一次何時執行，RPO / RTO 是否符合產品承諾。
5. `SQLITE_BUSY`、WAL growth、disk full、backup failure 與 restore failure 如何告警。
6. Corruption recovery 時誰保存原檔、誰啟動 restore、誰決定修復或 [fail-forward](/backend/knowledge-cards/fail-forward/)。

這份清單要接到服務 ownership，而非留在工程師個人習慣。SQLite 的優勢是 deployment surface 小；production 化的代價是把檔案、備份與恢復流程寫進同一份可交接 runbook。

## 引用路徑

- 上游 overview：[SQLite vendor page](/backend/01-database/vendors/sqlite/)
- 服務責任：[Source of Truth](/backend/knowledge-cards/source-of-truth/)、[Database](/backend/knowledge-cards/database/)
- 恢復目標：[RPO](/backend/knowledge-cards/rpo/)、[RTO](/backend/knowledge-cards/rto/)
- 證據交接：[Observability Evidence Package](/backend/04-observability/observability-evidence-package/)、[Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 官方文件：[SQLite Write-Ahead Logging](https://www.sqlite.org/wal.html)、[SQLite Backup API](https://www.sqlite.org/backup.html)、[How To Corrupt An SQLite Database File](https://www.sqlite.org/howtocorrupt.html)、[Recovering Data From A Corrupt SQLite Database](https://www.sqlite.org/recovery.html)、[Appropriate Uses For SQLite](https://www.sqlite.org/whentouse.html)、[Most Widely Deployed SQL Database Engine](https://www.sqlite.org/mostdeployed.html)
- 延伸工具：[Litestream restore reference](https://litestream.io/reference/restore/)、[Litestream getting started](https://litestream.io/getting-started/)
