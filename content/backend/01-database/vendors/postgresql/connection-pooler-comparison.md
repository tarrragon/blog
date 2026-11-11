---
title: "PostgreSQL Connection Pooler Comparison"
date: 2026-05-22
weight: 16
description: "PostgreSQL PgBouncer、Odyssey、RDS Proxy、Cloudflare Hyperdrive、application pool 與 transaction pooling 的選型比較"
tags: ["backend", "database", "postgresql", "connection-pooling"]
---

PostgreSQL connection pooler comparison 的核心責任是把連線數壓力、transaction 語意與維運責任拆開判讀。PostgreSQL backend process 成本高，application instance 擴張後，connection pooler 常成為保護資料庫的第一層容量控制。

本文涵蓋 pool mode 的綁定模型、各 pooler 選項的責任邊界、導入 pooler 的判斷訊號、transaction pooling 的相容性、Cloudflare Workers 經由 Hyperdrive 連既有 PostgreSQL 時的連線池與查詢快取、pool size 的設定與觀測，以及常見的反模式。

## Pooling Models

Pooling model 的核心責任是決定 client connection 和 server connection 的綁定時間。PgBouncer 代表最常見的 PostgreSQL pooler 模型；官方文件將 pool mode 分成 session、transaction 與 statement。

| 模式        | Server connection 綁定 | 適合情境                         | 主要風險                                      |
| ----------- | ---------------------- | -------------------------------- | --------------------------------------------- |
| Session     | client session 全程    | 使用 session state、temp table   | 壓縮率低                                      |
| Transaction | transaction 期間       | Web API、短交易、Stateless query | session variable、prepared statement 語意受限 |
| Statement   | single statement       | 特殊 read-only workload          | transaction workflow 受限                     |
| App pool    | application process 內 | 單服務、低 fan-out               | 多 instance 後總連線失控                      |

[Transaction pooling](/backend/knowledge-cards/transaction-pooling/) 的價值在於把大量 idle client connection 收斂成少量 active server connection。它要求 application 把 session state 放回 request / transaction boundary，例如 timezone、role、search_path、prepared statement 與 advisory lock 都要明確管理。

Session pooling 的價值在於相容性。若 application 大量使用 temp table、LISTEN / NOTIFY、session-level setting 或 server-side prepared statement，session pooling 能降低行為差異，但連線壓縮效果較弱。

## Product Boundary

Product boundary 的核心責任是把 pooler 放在正確的維運位置。不同選項的責任邊界差異很大。

| 選項                  | 主要責任                                          | 適合情境                                                               |
| --------------------- | ------------------------------------------------- | ---------------------------------------------------------------------- |
| PgBouncer             | 輕量 PostgreSQL connection pooling                | 自管 VM / K8s、transaction pooling 標準路線                            |
| Odyssey               | 多租戶與複雜 routing pooler                       | 大型部署、需要進階 routing / auth                                      |
| RDS Proxy             | AWS managed connection proxy                      | RDS / Aurora 生態、希望降低 proxy 維運                                 |
| Cloudflare Hyperdrive | Workers 前面的 managed connection pool 與查詢快取 | application 部署在 Cloudflare Workers、資料留在既有 PostgreSQL / MySQL |
| Application pool      | 服務內部連線池                                    | instance 數少、連線總量可控                                            |
| No pooler             | 直接連 PostgreSQL                                 | 小型服務、低併發、連線數遠低於上限                                     |

PgBouncer 的操作重點是 mode、pool size、server reset query、auth、TLS 與 metrics。它很適合放在 application 與 database 中間，承擔連線排隊與 backpressure。

Managed proxy 的操作重點是平台限制、failover behavior、credential integration、latency overhead 與 observability。若 team 想少維護一個 pooler process，managed proxy 可以降低操作成本，但要接受雲平台邊界。

## Decision Signals

Decision signals 的核心責任是判斷何時導入 pooler，以及導入哪一種。連線數壓力要用 evidence 說明。

| 訊號                                                                     | 代表問題                       | 建議路由                                  |
| ------------------------------------------------------------------------ | ------------------------------ | ----------------------------------------- |
| `max_connections` 接近上限                                               | application fan-out 過高       | PgBouncer transaction pooling             |
| 大量 idle connection                                                     | client 連線長期閒置            | transaction pooling 或 app pool 調整      |
| failover 後 [reconnect storm](/backend/knowledge-cards/thundering-herd/) | client 同時重連衝擊 primary    | pooler queue + jitter                     |
| query latency 高但 connection 不高                                       | 查詢 / lock / index 問題       | query optimization                        |
| session state 依賴多                                                     | transaction pooling 相容性風險 | session pooling 或 refactor session state |

Connection pooler 的成功訊號是 database backend count 下降、queue 可觀測、error rate 穩定、tail latency 受控。若導入後只是把 timeout 從 DB 移到 pooler，代表 capacity model 仍需調整。

Pooler 解決的是 connection fan-out 與 queueing；查詢慢、lock wait、transaction 過長、index 錯誤要回到 [Query Optimization](../query-optimization/) 與 [MVCC / lock model](../mvcc-lock-model/)。

## Transaction Pooling Compatibility

Transaction pooling compatibility 的核心責任是找出 application 對 session state 的隱性依賴。這些依賴要在 staging 先測出來。

| 依賴類型           | 風險                                  | 修正策略                                   |
| ------------------ | ------------------------------------- | ------------------------------------------ |
| `SET search_path`  | 下一個 transaction 可能換連線         | 每個 transaction 明確設定或固定 schema     |
| temp table         | transaction 後 server connection 釋放 | 改 permanent staging table 或 session mode |
| prepared statement | server-side state 不穩定              | 使用 client-side prepare 或 session mode   |
| advisory lock      | lock ownership 混亂                   | transaction-scoped lock 或移出 pooler path |
| LISTEN / NOTIFY    | session channel 需要持續連線          | 專用 direct connection                     |

Compatibility review 要在 repository / migration / background job 三個層面跑。Web request 通常容易改成 transaction-safe；migration tool、CDC job、worker queue 常有長連線與 session state，要分開配置。

## Cloudflare Hyperdrive：Workers 連既有 PostgreSQL 的連線池與查詢快取

Hyperdrive 是 Cloudflare 讓 Workers 連到既有 PostgreSQL 或 MySQL 的 managed connection pool，跟 RDS Proxy 同屬平台託管的連線代理。[Hyperdrive 官方文件](https://developers.cloudflare.com/hyperdrive/)寫明它支援任何 PostgreSQL 或 MySQL 資料庫，列出的例子有放在 AWS、Google Cloud、Azure、Supabase、Neon、PlanetScale 上的資料庫。它把連線池放在離資料庫最近的區域，Worker 跟 Hyperdrive 之間的連線在 Worker 附近建立，每個請求不必重新跟資料庫完成建立連線的往返。下面幾項行為的來源是 Hyperdrive 的 [How Hyperdrive works](https://developers.cloudflare.com/hyperdrive/concepts/how-hyperdrive-works/)、[query caching](https://developers.cloudflare.com/hyperdrive/concepts/query-caching/)、[limits](https://developers.cloudflare.com/hyperdrive/platform/limits/) 與 [pricing](https://developers.cloudflare.com/hyperdrive/platform/pricing/) 頁（2026-11 查閱），這條路這次沒有實跑；舉例以 PostgreSQL 為主，MySQL 那一端的對應行為官方頁面沒有寫。

- **transaction pooling**：Hyperdrive 的連線池以 [transaction pooling](/backend/knowledge-cards/transaction-pooling/) 運作，交易結束時連線回到池子並被重設（`RESET`），`SET` 的設定只在同一個交易或同一個查詢裡有效，下一個交易就不在了；歸還時不重設 session 狀態的 pooler，則可能把 `SET` 留給下一個 client（見卡片）。session 層級的 [advisory lock](/backend/knowledge-cards/advisory-lock/)（`pg_advisory_lock` 這組）不支援，交易層級的 `pg_advisory_xact_lock` 這組可以用。named prepared statement 只有 `postgres.js` 與 `node-postgres` 兩個 driver 的實作確定支援。上方〈Transaction Pooling Compatibility〉表裡的其他依賴（temp table、LISTEN / NOTIFY），官方頁面沒有逐項寫明，照 transaction pooling 的通則審查。
- **查詢快取**：快取預設開啟，快取結果的存活時間 `max_age`（[TTL](/backend/knowledge-cards/ttl/)）預設 60 秒、最長 1 小時。只快取唯讀查詢；用到 PostgreSQL 標記為 `STABLE` 或 `VOLATILE` 的函式（`NOW()`、`RANDOM()`、`LASTVAL()` 這類）的查詢不快取，查詢文字的註解裡出現這些函式名也會被當成不可快取。application 寫入資料庫時，Hyperdrive 不讓已快取的讀取結果失效，寫完立刻讀取的路徑在 `max_age` 到期之前讀到舊值（[stale read](/backend/knowledge-cards/stale-read/)）。官方文件的做法是另建一個帶 `--caching-disabled` 的 Hyperdrive configuration，跟有快取的那一個一起綁到 Worker，登入、權限、帳務狀態與寫完立刻讀取的查詢走關閉快取的那一個。
- **延遲**：連線池靠近資料庫，省下的是建立連線的時間；沒有命中快取的查詢仍要從 Worker 執行的位置往返資料庫所在的區域。官方文件給的量級是每個查詢從遠端區域 20 到 30 ms、放在附近 1 到 3 ms；一個請求依序執行好幾個查詢時，官方建議用 Workers 的 Placement（指定或讓平台選擇 Worker 執行區域的設定，見 [Workers placement 文件](https://developers.cloudflare.com/workers/configuration/placement/)）讓 Worker 在資料庫附近執行，一個請求只有一個查詢時放在哪裡端到端延遲都一樣。
- **方案限制**：Free 方案每天 100,000 次查詢、每個 Hyperdrive configuration（一個 configuration 對應一個要連的資料庫）約 20 條連到資料庫的連線；Paid 方案查詢次數不限、約 100 條；單一查詢最長 60 秒。這些數字會隨方案調整，採用時以 limits 與 pricing 頁的現值為準。

Hyperdrive 跟 SQLite 生態的 Cloudflare D1 怎麼選，判斷依據是資料庫由誰維運，寫在 [SQLite D1 / Turso / libSQL Comparison](/backend/01-database/vendors/sqlite/d1-turso-libsql-comparison/) 的 Decision Route。

## Sizing and Evidence

Sizing and evidence 的核心責任是用 workload 設定 pool size。Pooler 設太大會把壓力直接傳到 PostgreSQL；設太小會造成 queue 與 timeout。

基本 sizing 步驟：

1. 量測 active query concurrency，而非只看 request concurrency。
2. 設定 database 保留連線給 admin、replication、migration 與 emergency access。
3. 每個 service 設定 pool quota，避免單一服務吃掉全部 backend。
4. 觀測 wait time、server utilization、client timeout、query latency。
5. 用 load test 驗證 failover / reconnect storm。

Pooler dashboard 至少要有 client connections、server connections、waiting clients、pool wait time、server reuse、timeout count 與 authentication failure。

## Anti-Patterns

Anti-pattern 的核心責任是把 pooler 常見誤用提前排除。

| 反模式                       | 風險                                 | 修正方向                           |
| ---------------------------- | ------------------------------------ | ---------------------------------- |
| 把 pool size 設到 DB 上限    | DB 失去保護層                        | 每個服務配額 + 保留 admin capacity |
| transaction pooling 直接上線 | session state 依賴在 production 爆出 | staging compatibility matrix       |
| pooler 沒有 metrics          | queueing 事故難以判讀                | pooler dashboard + alert           |
| migration 共用 web pool      | 長 DDL 卡住 web request              | migration 專用連線與維護窗口       |
| retry 無 jitter              | reconnect storm 放大                 | exponential backoff + jitter       |

Pooler 是 backpressure 元件。它要讓系統在過載時可排隊、可拒絕、可觀測，而非把所有請求推進 database。

## 下一步路由

選定 pooler 之後，PgBouncer 的實際設定讀 [PgBouncer config](../pgbouncer-config/)；要觀察連線壓力讀 [Connection Scaling](../connection-scaling/)；需要演練讀 [Connection Pool Lab](../hands-on/connection-pool-lab/)。
