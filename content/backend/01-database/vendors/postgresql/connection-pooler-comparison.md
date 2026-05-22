---
title: "PostgreSQL Connection Pooler Comparison"
date: 2026-05-22
description: "PostgreSQL PgBouncer、Odyssey、RDS Proxy、application pool 與 transaction pooling 的選型比較"
tags: ["backend", "database", "postgresql", "connection-pooling"]
---

PostgreSQL connection pooler comparison 的核心責任是把連線數壓力、transaction 語意與維運責任拆開判讀。PostgreSQL backend process 成本高，application instance 擴張後，connection pooler 常成為保護資料庫的第一層容量控制。

本文的判讀錨點是：pooler 解決的是 connection fan-out 與 queueing，而非查詢本身變快。查詢慢、lock wait、transaction 過長、index 錯誤仍要回到 [Query Optimization](../query-optimization/) 與 [MVCC / lock model](../mvcc-lock-model/)。

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

| 選項             | 主要責任                           | 適合情境                                    |
| ---------------- | ---------------------------------- | ------------------------------------------- |
| PgBouncer        | 輕量 PostgreSQL connection pooling | 自管 VM / K8s、transaction pooling 標準路線 |
| Odyssey          | 多租戶與複雜 routing pooler        | 大型部署、需要進階 routing / auth           |
| RDS Proxy        | AWS managed connection proxy       | RDS / Aurora 生態、希望降低 proxy 維運      |
| Application pool | 服務內部連線池                     | instance 數少、連線總量可控                 |
| No pooler        | 直接連 PostgreSQL                  | 小型服務、低併發、連線數遠低於上限          |

PgBouncer 的操作重點是 mode、pool size、server reset query、auth、TLS 與 metrics。它很適合放在 application 與 database 中間，承擔連線排隊與 backpressure。

Managed proxy 的操作重點是平台限制、failover behavior、credential integration、latency overhead 與 observability。若 team 想少維護一個 pooler process，managed proxy 可以降低操作成本，但要接受雲平台邊界。

## Decision Signals

Decision signals 的核心責任是判斷何時導入 pooler，以及導入哪一種。連線數壓力要用 evidence 說明。

| 訊號                               | 代表問題                       | 建議路由                                  |
| ---------------------------------- | ------------------------------ | ----------------------------------------- |
| `max_connections` 接近上限         | application fan-out 過高       | PgBouncer transaction pooling             |
| 大量 idle connection               | client 連線長期閒置            | transaction pooling 或 app pool 調整      |
| failover 後 reconnect storm        | client 同時重連衝擊 primary    | pooler queue + jitter                     |
| query latency 高但 connection 不高 | 查詢 / lock / index 問題       | query optimization                        |
| session state 依賴多               | transaction pooling 相容性風險 | session pooling 或 refactor session state |

Connection pooler 的成功訊號是 database backend count 下降、queue 可觀測、error rate 穩定、tail latency 受控。若導入後只是把 timeout 從 DB 移到 pooler，代表 capacity model 仍需調整。

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

Connection pooler comparison 完成後，實作層讀 [PgBouncer config](../pgbouncer-config/)；要觀察連線壓力讀 [Connection Scaling](../connection-scaling/)；需要演練讀 [Connection Pool Lab](../hands-on/connection-pool-lab/)。
