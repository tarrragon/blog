---
title: "資料庫 Vendor 文章撰寫規格"
date: 2026-05-20
weight: 90
description: "把 PostgreSQL 與 MySQL batch 的正文經驗整理成資料庫 vendor overview、deep article 與 migration playbook 的撰寫規格"
tags: ["backend", "database", "vendor", "writing-spec"]
---

資料庫 Vendor 文章撰寫規格的核心責任是把服務頁、深度文章與遷移 playbook 的分工固定下來。PostgreSQL 與 MySQL 已經提供 SQL baseline 的完整樣本；後續撰寫 SQLite、MongoDB、DynamoDB、Aurora、Spanner、Cosmos DB 與 CockroachDB 時，應沿用同一組教學功能檢查，但保留每個服務自己的資料形狀、操作責任與失敗語言。

這份規格承接 [Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/) 與 [Migration Playbook 寫作方法論](/posts/migration-playbook-methodology/)。本文只處理資料庫模組的落地規格：哪些內容留在 vendor overview，哪些議題升級成 deep article，哪些變更需要 migration playbook。

## 判讀錨點

資料庫 vendor 文章的錨點是正式狀態如何被保存、查詢、複製、演進與修復。產品功能、版本差異與雲端價格都只是材料；正文要把材料轉成讀者可操作的判準，讓讀者能判斷資料模型、交易需求、查詢邊界、容量壓力、操作責任與替代路由。

PostgreSQL 與 MySQL 的 batch 顯示三個穩定事實。第一，SQL baseline 已經足以支撐其他服務頁開寫；第二，深度文章需要「何時不用」與真實案例 anchor 防止過度工程化；第三，跨 vendor 或 topology 變更需要獨立 playbook，不適合塞回 overview。

## Vendor Overview 規格

Vendor overview 的責任是教讀者完成第一輪服務判斷。這一層回答服務承擔什麼資料責任、適合什麼壓力、日常有哪些操作決策、失效時先看哪些訊號，以及何時改走相鄰服務。

| 規格面       | 必答問題                                                                                                            | 交付形態                                   |
| ------------ | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| 服務定位     | 這個服務承擔 SQL、embedded、document、KV 或 [distributed SQL](/backend/knowledge-cards/distributed-sql/) 哪一種責任 | 開場段、教學路線、最短判讀路徑             |
| 資料形狀     | 資料是 row、document、key-value、time-series、geo 還是 global record                                                | 適用場景、schema / index / partition 說明  |
| 一致性與交易 | transaction、replica、multi-region 與 stale read 如何取捨                                                           | 適用場景、不適用場景、跟其他 vendor 的取捨 |
| 操作責任     | 誰負責 backup、failover、upgrade、capacity、security 與 audit                                                       | 容量規劃要點、常見陷阱、下一步路由         |
| 替代邊界     | 什麼條件下改走 SQL、document、KV、managed SQL 或 distributed SQL                                                    | 同類對比、相鄰章節路由、下游 deep article  |
| 案例與限制   | 哪些案例能提供壓力訊號，哪些 claim 需要時間敏感標記                                                                 | 案例對照、已知 limitation、後續擴充候選    |

服務定位段要先把產品名稱放回資料庫分類語言。SQLite 的定位是 embedded formal state 與低操作成本；MongoDB 的定位是 document shape 與 schema governance；DynamoDB 的定位是 managed KV / document access pattern；Aurora 的定位是 managed SQL operation transfer；Spanner、Cosmos DB 與 CockroachDB 的定位是 global 或 distributed consistency。

資料形狀段要讓讀者知道服務為哪種查詢與寫入模式付成本。Row model 適合交易與 ad-hoc query；document model 適合聚合資料與 schema flexibility；KV model 適合固定 access pattern；[distributed SQL](/backend/knowledge-cards/distributed-sql/) 適合跨 region 一致性，但會把 latency、transaction retry 與成本模型帶進設計。

一致性與交易段要接回 [transaction boundary](/backend/knowledge-cards/transaction-boundary/)、[isolation level](/backend/knowledge-cards/isolation-level/)、[replication lag](/backend/knowledge-cards/replication-lag/) 與 [stale read](/backend/knowledge-cards/stale-read/)。讀者需要知道的是哪種資料變更必須一起成功、哪種讀取可以接受延遲，以及跨 region 寫入是否值得支付協調成本。

操作責任段要把 managed 與 self-managed 的責任轉移寫清楚。自管服務保留控制權，團隊承擔 patch、backup、failover、capacity 與事故演練；managed 服務降低操作負擔，但增加平台限制、費用模型、版本節奏與 vendor-specific behavior。

替代邊界段要保留機會成本。PostgreSQL 或 MySQL 可以承擔多數 OLTP baseline；當 query 固定且高峰連線壓力明顯，DynamoDB 類服務可能更划算；當 document shape 主導資料模型，MongoDB 或 Cosmos DB 有更自然的操作語意；當 global write 是核心需求，Spanner、CockroachDB 或 Aurora DSQL 才進入主要比較。

案例與限制段要分開處理 evidence 與 backlog。案例提供流量形狀、資料形狀、失敗代價或回退路徑；limitation 承認正文還缺哪些維度，例如 PostgreSQL 目前仍需補 Security / RLS / audit logging、cross-region DR 與 managed PG 變體對比，MySQL 仍需補 deep article 的 anti-recommendation 與真實 incident anchor。

## Deep Article 規格

Deep article 的責任是把 vendor overview 點到的單一機制展開成可操作教材。這一層不重寫服務選型，而是教讀者設定、觀測、除錯、容量估算與整合某個具體機制，例如 connection pool、replication topology、online schema change、[CDC](/backend/knowledge-cards/change-data-capture/)、partitioning、lock contention 或 PITR。

| 規格面     | 必答問題                                              | 交付形態                                       |
| ---------- | ----------------------------------------------------- | ---------------------------------------------- |
| 問題情境   | 什麼 production 壓力會讓這個機制變成主題              | 開場場景、痛點、失效訊號                       |
| 核心機制   | 該 vendor 如何實作這個能力，跟通用概念差在哪          | lifecycle、模式對照、內部元件責任              |
| 操作流程   | 讀者要如何配置、驗證、調整與演練                      | step-by-step、config、query、command、驗證條件 |
| 失敗模式   | 哪些踩雷最常把服務推向事故                            | production case、徵兆、根因、修法              |
| 容量與觀測 | 什麼 metric、query、log 或 cost signal 能判斷健康狀態 | 容量規劃、觀測 metric、alert / dashboard route |
| 邊界與整合 | 什麼條件下要換 sub-tool、改架構或回到 overview        | 何時用、何時不用、sibling 對比、下一步路由     |

問題情境段要用具體壓力啟動，產品文件定義只作為補充材料。Connection pool 可以從連線風暴與 backend slot 說起；replication 可以從 lag 與 failover 說起；PITR 可以從 restore 能力與 RPO 說起；lock contention 可以從交易範圍與 deadlock 訊號說起。

核心機制段要保留 vendor-specific 語意。PostgreSQL 的 WAL / LSN / replication slot、MVCC / vacuum、process-per-connection model 與 extension lifecycle 都有自己的操作語意；MySQL 的 binlog / GTID、InnoDB clustered index、gap / next-key lock、ProxySQL query rule 與 Vitess VSchema 也要用自己的語言展開。

操作流程段要把設定與判準綁在一起。Config、SQL、CLI 或 dashboard query 只在能支撐判讀時出現；每個操作要回答「如何知道它生效」「失敗時看到什麼」「可以停在哪個 rollback boundary」。

失敗模式段是 deep article 的主要價值。PostgreSQL / MySQL 既有文章多數已具備「5 個 Production 踩雷」；後續服務要維持這個密度，並優先補真實案例 anchor，避免所有案例都停在合成數字或典型設定。

容量與觀測段要讓 deep article 接回 04 / 09。資料庫機制常見的訊號包括 connection usage、replication lag、lock wait、dead tuple、buffer hit ratio、slow query、binlog retention、WAL growth、partition pruning 與 restore duration；這些訊號要能回到 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 或 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)。

邊界與整合段要補「何時不用」。MySQL audit 已經指出 deep article 容易缺 anti-recommendation；後續每篇 deep article 至少要有一段說明什麼規模、團隊能力或 workload 下暫時維持簡單設計更划算。

## Hands-on / Artifact 規格

Hands-on / artifact 章節的責任是把 deep article 的機制判讀轉成可演練操作。這一層對齊 LLM `hands-on/` 的教學功能：讀者能跑出一個 local / staging lab，取得 config、query output、metric snapshot、validation result 或 rollback note，而不只停在概念理解。

| 規格面     | 必答問題                                          | 交付形態                                             |
| ---------- | ------------------------------------------------- | ---------------------------------------------------- |
| Lab scope  | 這個操作在 local、staging、managed sandbox 哪裡跑 | Docker Compose、CLI、SQL script、preview environment |
| Input      | 需要哪些 schema、seed data、config、credential    | setup checklist、sample data、env var                |
| 操作步驟   | 讀者照順序做什麼                                  | command / SQL / dashboard step                       |
| Evidence   | 怎麼知道操作成功、退化或失敗                      | query output、metric snapshot、log、screenshot note  |
| Cleanup    | 操作後哪些資料、帳號、route、backup 要清理        | teardown、rollback、retention note                   |
| 下一步路由 | 操作結果要回到哪篇 deep article 或 migration      | overview、deep article、release gate、incident log   |

PostgreSQL、MySQL 與 SQLite 已建立 hands-on 入口：[PostgreSQL hands-on](/backend/01-database/vendors/postgresql/hands-on/)、[MySQL hands-on](/backend/01-database/vendors/mysql/hands-on/) 與 [SQLite hands-on](/backend/01-database/vendors/sqlite/hands-on/)。後續其他 database vendor 也要先建立 hands-on 入口，再依服務責任決定是否補完整操作正文。

## Migration Playbook 規格

Migration playbook 的責任是處理跨 vendor、跨 topology 或跨 operational model 的變更流程。這一層的主體是差異盤點、階段切換、雙軌驗證、cutover、rollback / fail-forward 與 cleanup；它應作為獨立流程教材，而非 deep article 的長版或 vendor overview 的補充段。

| 規格面     | 必答問題                                                                                  | 交付形態                                                |
| ---------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Driver     | 為什麼要遷，壓力來自成本、容量、合規、operation 還是 paradigm                             | 開場 driver、no-go condition、替代方案                  |
| Diff audit | source / target 在 schema、operation、paradigm、component、application、topology 哪裡不同 | 6 維 audit、主導差異、type 判定                         |
| Phase plan | 哪些工作能分段，哪些工作必須 parallel run 或長期混合                                      | phase、stream、owner、驗證門檻                          |
| Evidence   | 每個階段用什麼資料證明可前進                                                              | validation query、row count、lag、error budget、cost    |
| Cutover    | 什麼條件下切流，切流期間誰決策                                                            | cutover window、rollback condition、decision log route  |
| Cleanup    | 哪些舊路徑能退役，哪些證據要保留                                                          | contract removal、backup retention、incident write-back |

Driver 段要先排除「因為新服務比較好」這類空泛動機。有效 driver 通常是單機 primary 上限、connection limit、replication lag、backup / restore 責任、multi-region residency、vendor operation transfer、schema feature gap 或成本曲線。

Diff audit 段要先決定 playbook type。MySQL → PostgreSQL 主要是 schema / dialect 差；PostgreSQL → Aurora 主要是 operational redesign；PostgreSQL → CockroachDB 或 Aurora DSQL 主要是 paradigm shift；partition redesign 是 topology re-layout。type 決定結構，不用把所有 playbook 壓成同一套 phase。

Phase plan 段要把不可逆動作放晚。Schema audit、application compatibility、shadow read、dual-write、backfill、CDC catch-up、read-only cutover 與 cleanup 要分出驗證門檻；長期混合架構要明確標示哪些 workload 保留在 source。

Evidence 段要把資料庫遷移接回 observability 與 reliability。Playbook 應要求 row count、checksum、replication lag、error rate、query latency、data quality 與 owner；這些 evidence 是 release gate、incident decision log 與 rollback 判斷的共同材料。

Cutover 段要把決策權責寫清楚。資料庫切流失敗通常代價高，正文要標示切流窗口、暫停條件、回退條件、資料凍結策略與 decision owner，並連到 [rollback window](/backend/knowledge-cards/rollback-window/) 或 [rollback condition](/backend/knowledge-cards/rollback-condition/)。

Cleanup 段要防止雙軌永久殘留。舊 schema、舊 writer、舊 CDC connector、舊 backup、舊 dashboard 與舊 runbook 都需要退役判準；資料保留、稽核與 incident write-back 要在 cleanup 前確認。

## 從 PostgreSQL / MySQL 回收的調整項

PostgreSQL 與 MySQL 的正文已經足以讓其他服務頁開寫。下一輪調整應集中在橫向品質；SQL baseline 可維持現有正文作為後續服務頁的比較基準。

### PostgreSQL

PostgreSQL 的下一輪擴充重點是補安全、災難復原與 managed variant。[Security / RLS / audit logging](/backend/01-database/vendors/postgresql/security-rls-audit-logging/) 可以連到資料保護與稽核章節；[cross-region DR](/backend/01-database/vendors/postgresql/cross-region-dr/) 可以連到 reliability 與 incident decision；[Managed PG Comparison](/backend/01-database/vendors/postgresql/managed-pg-comparison/) 與 [Specialized PostgreSQL Variants](/backend/01-database/vendors/postgresql/specialized-pg-variants/) 承接 AlloyDB、Cloud SQL、Cosmos DB for PostgreSQL 與 pgvectorscale。

PostgreSQL 的既有 limitation 已經標示 PG-favoring narrative 與時間敏感 claim。後續補文時要保留對手 vendor 的強項，例如專業 vector DB 的 scale、專業 time-series DB 的 ingestion、distributed SQL 的 global consistency 與 managed 平台的 operation transfer。

### MySQL

MySQL 的下一輪擴充重點是補 anti-recommendation 與真實 case anchor。多數 deep article 已經有 production 踩雷，但還要加上「何時暫時不用這個機制」的段落，讓讀者知道維持單 primary、簡單 replication、原生 partition 或標準 backup 何時更划算；security、audit、Document Store、multi-source replication、HeatWave、memory contention 與 metadata lock 已先建立 outline 路由。

MySQL 的案例段要把 GitHub、Shopify、Slack、YouTube / Vitess 這些業界來源升級成具體 anchor。案例不只列公司名稱，還要回收它提供的流量形狀、[database sharding](/backend/knowledge-cards/database-sharding/) 策略、schema change 壓力、failover 責任或工具演化原因。

## 後續服務撰寫順序

後續服務撰寫順序要從 SQL baseline 推進到資料模型與操作責任差異。每一篇先完成 vendor overview，再依 overview 暴露出的機制缺口決定 deep article 或 migration playbook。

| 批次 | 服務                | 開寫重點                                                       | 升級條件                                                                                   |
| ---- | ------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| DB2  | SQLite              | embedded formal state、local data、testing DB、backup 邊界     | local-first sync、edge deployment 或 file corruption                                       |
| DB3  | MongoDB / DynamoDB  | document shape、access pattern、partition key、capacity mode   | shard expansion、Atlas migration、[hot partition](/backend/knowledge-cards/hot-partition/) |
| DB4  | Aurora              | managed SQL、storage / compute 分離、failover、cost model      | PostgreSQL / MySQL 遷移、I/O-Optimized cost                                                |
| DB5  | Spanner / Cosmos DB | global consistency、multi-region latency、consistency level    | regional rollout、API model migration                                                      |
| DB6  | CockroachDB         | distributed SQL、transaction retry、range lease、compatibility | PostgreSQL migration、multi-region topology                                                |

SQLite 的重點是讓讀者知道單機正式狀態何時成立。它不應被寫成小型 PostgreSQL，而要處理 file lifecycle、embedded process boundary、backup、concurrency、migration 與測試資料責任。

MongoDB / DynamoDB 的重點是把資料形狀放在 SQL baseline 之後。MongoDB 應教 document shape、index、schema governance 與 transaction boundary；DynamoDB 應教 access pattern、partition key、capacity mode、[hot partition](/backend/knowledge-cards/hot-partition/) 與 connection-free scaling。

Aurora 的重點是 operation transfer。它把 PostgreSQL / MySQL 相容介面放進 AWS-managed operational model；storage / compute 分離、cluster endpoint、replica、backup、failover、cost model 與 AWS 限制都會改變團隊責任。

Spanner / Cosmos DB 的重點是 global data responsibility。Spanner 應教 TrueTime、strong consistency、multi-region latency 與 cost；Cosmos DB 應教 consistency level、API model、partition、RU 與 Azure 約束。

CockroachDB 的重點是 distributed SQL 對 application contract 的影響。SQL 相容降低導入門檻，但 transaction retry、range lease、hot range、schema feature gap 與 multi-region topology 會改變 application 與 SRE 的責任。

## LLM-depth 下一輪擴章 Backlog

LLM-depth 下一輪的責任是把每個資料庫服務從 T1 overview 推進到可教學的章節群。Overview 只回答第一輪服務判斷；deep article 回答穩定運作與排錯；migration playbook 回答跨 vendor、跨 topology 或跨 operational model 變更。

| 服務        | 目前狀態           | 下一篇 deep article                                                                                                                                                                     | 升級 playbook 候選                                                                                                                                                 |
| ----------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| SQLite      | T1 overview 已完成 | [teaching structure](/backend/01-database/vendors/sqlite/teaching-structure/) + [file lifecycle / backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/) | [SQLite → PostgreSQL](/backend/01-database/vendors/sqlite/migrate-to-postgresql/)、[SQLite → D1 / Turso](/backend/01-database/vendors/sqlite/migrate-to-d1-turso/) |
| MongoDB     | T1 overview 已完成 | document shape governance、index / shard key                                                                                                                                            | self-managed → Atlas、document model → relational split                                                                                                            |
| DynamoDB    | T1 overview 已完成 | partition key / hot partition、capacity mode                                                                                                                                            | DynamoDB → SQL / search / analytics split                                                                                                                          |
| Aurora      | T1 overview 已完成 | failover / endpoint routing、I/O cost model                                                                                                                                             | PostgreSQL / MySQL → Aurora、Aurora → distributed SQL                                                                                                              |
| Spanner     | T1 overview 已完成 | TrueTime / transaction latency、multi-region topology                                                                                                                                   | regional SQL → Spanner                                                                                                                                             |
| Cosmos DB   | T1 overview 已完成 | consistency level / RU budgeting、partitioning                                                                                                                                          | API model migration、Cosmos DB → specialized store                                                                                                                 |
| CockroachDB | T1 overview 已完成 | transaction retry、range split / leaseholder                                                                                                                                            | PostgreSQL → CockroachDB、single-region → multi-region                                                                                                             |

Backlog 的排序以學習梯度為準。SQLite 先處理單檔案正式狀態，補足「低操作成本如何 production 化」；MongoDB / DynamoDB 再處理資料形狀與 access pattern；Aurora 接 SQL operation transfer；Spanner、Cosmos DB 與 CockroachDB 最後處理 distributed consistency 與 multi-region topology。

## 規格檢查清單

資料庫 vendor 文章完成前要跑一次規格檢查。檢查通過代表本次內容可作為後續服務的基準；未通過時，先修正文再開下一篇。

- Vendor overview 已說清楚服務責任、資料形狀、一致性、操作責任、替代邊界、案例與 limitation。
- Deep article 已包含問題情境、核心機制、操作流程、失敗模式、容量與觀測、邊界與整合。
- Migration playbook 已完成 driver、diff audit、phase plan、evidence、cutover 與 cleanup。
- 表格後有情境化說明，沒有讓表格取代判讀。
- 案例提供壓力、失敗代價或回退條件，不只列公司名稱。
- 「何時不用」或 no-go condition 已出現在 deep article / migration playbook。
- Time-sensitive vendor claim 有日期語境或指向官方文件。
- 下一步路由能接回主章、knowledge card、04 / 06 / 08 / 09 或 sibling vendor。
