---
title: "SQLite D1 / Turso / libSQL Comparison"
date: 2026-05-21
description: "Cloudflare D1、Turso、libSQL 與 local SQLite 在 edge、replication、consistency、migration 與 vendor boundary 的比較"
tags: ["backend", "database", "sqlite", "edge", "d1", "turso"]
---

D1 / Turso / libSQL comparison 的核心責任是把 SQLite-compatible edge products 和 local SQLite 分開判讀。它們共享 SQLite 開發體驗的一部分，但它們承擔的服務責任不同：Cloudflare D1 把 SQLite-like database 放進 Workers 生態與 managed edge platform；Turso / libSQL 把 SQLite family 延伸到 remote primary、embedded replica 與同步模型；local SQLite 則是 application process 直接管理單一 database file。

本文的判讀錨點是：SQLite compatibility 代表開發入口接近，服務責任仍要重新審查。採用 edge SQLite 前，要先確認 write authority、read freshness、migration limit、backup evidence、observability、cost 與 vendor exit，而非只看 SQL 語法能否執行。

## Product Boundary

Product boundary 的核心責任是定義誰持有資料、誰執行 SQL、誰負責恢復。Local SQLite 的資料在你的 filesystem；D1 的資料由 Cloudflare D1 平台管理並和 Workers binding 整合；Turso / libSQL 的資料通常有 remote database 與 client / embedded replica 的分工。

| 選項                | 主要責任                    | 適合情境                              | 關鍵審查點                         |
| ------------------- | --------------------------- | ------------------------------------- | ---------------------------------- |
| Local SQLite        | Process-local formal state  | CLI、desktop、single-node app         | file lifecycle、backup、WAL、lock  |
| Cloudflare D1       | Workers-integrated database | edge app、serverless API、low ops     | platform limit、migration、binding |
| Turso / libSQL      | Remote primary + replicas   | low-latency read、embedded replica    | freshness、sync、driver semantics  |
| Litestream / LiteFS | Backup / replica operation  | single-node app with recovery / read  | RPO、RTO、primary ownership        |
| PostgreSQL          | Server SQL operation        | multi-tenant、central audit、HA、role | operation team、PITR、schema gate  |

Local SQLite 的判斷重點是 file ownership。若 app 與 database file 位於同一個 host，備份、restore、disk full、permission 與 app upgrade 都在你的 runbook 裡；這條路線承接 [file lifecycle / backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/)。

D1 的判斷重點是 platform integration。Cloudflare 官方 D1 docs 把 D1 放在 Workers 與 Wrangler workflow 內，並公開 [D1 limits](https://developers.cloudflare.com/d1/platform/limits/)；因此採用 D1 時要把 database decision 與 Workers deployment、local preview、batch migration、import/export limit 一起審查。

Turso / libSQL 的判斷重點是 replica freshness 與 client semantics。Turso docs 對 [embedded replicas](https://docs.turso.tech/features/embedded-replicas/introduction) 的描述顯示：application 可以持有 local replica 並透過同步取得資料；這會把「讀得快」和「讀到多新」變成同一個設計問題。

## Edge Data Model

Edge data model 的核心責任是把 latency 改善與一致性責任拆開。Edge database 的價值常來自 closer read path、serverless deployment 與較低操作表面；風險則集中在 write authority、replication lag、region routing 與平台限制。

| 問題                   | 要觀察的訊號                         | 設計含義                                         |
| ---------------------- | ------------------------------------ | ------------------------------------------------ |
| 誰可以寫               | single primary、remote write、queue  | 決定 conflict、retry、idempotency 設計           |
| 讀取要多新             | read-after-write、sync interval      | 決定 UI freshness、cache invalidation、fallback  |
| migration 怎麼跑       | CLI、batch limit、preview / prod gap | 決定 release gate 與 rollback plan               |
| 失敗時如何恢復         | export、backup、restore command      | 決定 RPO / RTO 與 vendor exit                    |
| observability 在哪一層 | platform metrics、app log、query log | 決定 incident triage 從 app 還是 platform 開始查 |

Write authority 是 edge SQLite 的第一個分水嶺。若所有 write 都集中到 remote primary，application 要處理 network error、retry、idempotency 與 read freshness；若 write 發生在 local replica，系統要有 conflict resolution、sync ordering 與 delete propagation。

Read locality 是 edge SQLite 的主要收益。它適合 session-local preference、read-mostly catalog、低風險 personalization、feature flag snapshot、tenant-local small dataset；這些情境的共同點是資料量小、write rate 低、freshness 可以定義。

Global transaction 是 edge SQLite 的高風險區。若產品需求包含跨 region balance transfer、inventory reservation、ledger posting、strongly consistent permission decision，設計應路由到 [Global Distributed OLTP](/backend/01-database/global-distributed-oltp/) 或 PostgreSQL / CockroachDB / Spanner 的 transactional model。

## Migration Gap

Migration gap 的核心責任是確認 SQLite file 可以搬到 edge product 後，release workflow 仍可驗證。SQL syntax compatibility 只解決起點；真正會造成事故的是 batch limit、extension 差異、driver API、local preview 與 production platform 行為差異。

| 差異面          | 審查問題                              | Evidence                                     |
| --------------- | ------------------------------------- | -------------------------------------------- |
| SQL dialect     | schema、index、trigger、JSON 是否可用 | compatibility matrix + migration dry run     |
| Data movement   | seed / import / export 的容量與時間   | sample import、row count、checksum           |
| Runtime binding | app 如何取得 database connection      | staging deployment + smoke test              |
| Transaction     | write path 是否跨 request / region    | failure injection、retry log、freshness test |
| Backup / exit   | 如何拿回 SQLite-compatible artifact   | export file、restore drill、retention note   |

D1 migration 要把 Wrangler workflow 納入 release gate。Cloudflare D1 的 limits 文件明確列出 import、query、batch 等限制；因此大型 update / delete 要拆 batch，migration 要有 staging dry run 與 production rollback step。

Turso / libSQL migration 要把 driver semantics 納入 release gate。Local SQLite driver 直連 file；libSQL client 可能連 remote endpoint 或 embedded replica；application 要把 connection lifecycle、sync timing、auth token、network failure 與 local cache freshness 寫進測試。

## Operational Model

Operational model 的核心責任是把 managed convenience 轉成 ownership map。Edge SQLite 減少了部分 server operation，但新增 platform limit、billing、region behavior、vendor incident、CLI workflow 與 local preview mismatch。

Production runbook 至少要保存五種證據：

1. Schema migration history 與每次 release 的 dry-run result。
2. Data import / export 指令、檔案大小、row count 與 checksum。
3. Region latency、read freshness、write error rate 與 retry count。
4. Platform limit 命中紀錄、batch policy 與成本警戒線。
5. Vendor exit route：回 local SQLite、PostgreSQL 或另一個 edge database 的最小搬遷步驟。

成本模型要同時看 request、storage、egress、operation time 與工程鎖定。Edge product 常把起步成本壓低，但當資料變大、batch migration 變長、observability 需要外掛、vendor API 滲入 repository layer 時，長期成本會出現在 release 與 incident。

## Decision Route

Decision route 的核心責任是把需求送到相符的資料模型。D1 / Turso / libSQL 適合 edge locality 與低操作表面；當需求轉向 high-write OLTP、central audit、role-based permission、global transaction 或跨服務資料治理，應轉向 server SQL 或 distributed OLTP。

| 需求訊號                                  | 優先路由                                                                                                 |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Workers app 需要小型 relational data      | Cloudflare D1 + explicit limits review                                                                   |
| App 需要 local read latency + remote sync | Turso / libSQL + freshness contract                                                                      |
| Single-node app 只需要備份與恢復          | Local SQLite + [Litestream / LiteFS](/backend/01-database/vendors/sqlite/litestream-litefs-replication/) |
| 多 tenant、central audit、DB role         | [PostgreSQL](/backend/01-database/vendors/postgresql/)                                                   |
| Global write consistency                  | [CockroachDB](/backend/01-database/vendors/cockroachdb/) 或 Spanner                                      |

D1 的採用條件是 edge runtime 本身就是主平台。若 application 已在 Workers 上、資料量可控、query pattern 清楚、migration 可 batch，D1 可以把 database operation 融入 deployment workflow。

Turso / libSQL 的採用條件是 local read value 高於同步複雜度。若產品可明確定義 stale read window、write path 與 conflict policy，embedded replica 可以降低 latency；若使用者需要立即看見跨裝置變更，就要先設計 freshness evidence。

## Production Tripwires

Production tripwires 的核心責任是指出何時重新評估 edge SQLite。這些訊號出現時，系統通常已從「SQLite-compatible convenience」進入正式 database governance。

| Tripwire                     | 意義                                                                      | 下一步                                      |
| ---------------------------- | ------------------------------------------------------------------------- | ------------------------------------------- |
| Migration batch 經常碰 limit | schema 與資料量超過 edge workflow                                         | 評估 PostgreSQL / managed SQL               |
| Read freshness ticket 增加   | replica / sync 語意影響產品體驗                                           | 建 freshness SLO 或改集中讀寫               |
| Export / restore 未演練      | vendor exit 與災難恢復缺 evidence                                         | 補 restore drill 與 retention policy        |
| Driver API 滲入 domain       | [vendor lock-in](/backend/knowledge-cards/vendor-lock-in/) 進入核心程式碼 | 建 repository adapter 與 compatibility test |
| Cross-region write 需求出現  | edge-local read 已不足                                                    | 路由到 distributed OLTP                     |

這些 tripwire 要寫進設計文件與 runbook。Edge SQLite 的優勢在於低摩擦起步；它的長期品質來自早期把 ownership、limits、exit 與 evidence 設計清楚。

## 下一步路由

D1 / Turso / libSQL comparison 完成後，下一步要依壓力路由。要處理 local file 與 backup，讀 [file lifecycle / backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/)；要處理 replica / restore，讀 [Litestream / LiteFS replication](/backend/01-database/vendors/sqlite/litestream-litefs-replication/)；要從 local SQLite 移到 edge product，讀 [SQLite to D1 / Turso migration](/backend/01-database/vendors/sqlite/migrate-to-d1-turso/)；要處理 global write，回到 [Global Distributed OLTP](/backend/01-database/global-distributed-oltp/)。
