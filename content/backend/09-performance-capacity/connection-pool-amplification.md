---
title: "9.14 連線池放大解法（PgBouncer / RDS Proxy / ProxySQL）"
date: 2026-05-27
description: "水平擴展應用層時 DB 連線池放大問題的具體解法、connection pooler 三大選項對比、解 9.13 提出但未深入的隱性成本"
weight: 14
tags: ["backend", "performance", "scaling", "connection-pool"]
---

[9.13 擴展軸與 Stateless 前提](/backend/09-performance-capacity/scaling-axes/) 指出了水平擴展應用層時的隱性成本之一：連線池放大 — 100 臺機器 × 每臺 10 個連線 = 對 DB 開 1000 個連線、超過 PostgreSQL `max_connections` default（100）十倍。本章把這條撞牆訊號的具體解法說清楚 — connection pooler 是什麼、PgBouncer / RDS Proxy / ProxySQL 怎麼選、不同場景的取捨。

## 連線池放大的物理本質

PostgreSQL / MySQL 每個連線都會在 DB server 端配一個 backend process / thread。Backend 佔 5-15 MB 記憶體、context switch 也有成本。當應用層連線數超過 DB 機器能負擔的數量，會出現三類問題：

- **記憶體吃光**：500 個 backend × 10 MB = 5 GB、再加 shared buffer、可能直接 OOM
- **Context switch 抖動**：上百個 backend 競爭 CPU、上下文切換 overhead 變成主要消耗
- **連線建立失敗**：超過 `max_connections` 後、新請求拿不到連線、即使現有連線多數 idle

問題的根因不是「連線多」、是「連線**生命週期跟使用率不對齊**」。應用層 connection pool 通常維持「每臺機器 N 個常駐連線、避免每個 request 重新建連」、但 100 臺機器各自 keep 10 個常駐就是 1000 個 idle 連線。

解法的方向不是「砍應用層連線數」（會讓 connection acquisition 變慢、影響 latency）、是「在 DB 跟應用層之間放一層 multiplexer」— 把多個應用層連線複用到少數 DB 連線上。這層中介就是 [connection pooler](/backend/knowledge-cards/connection-pooler/)。

## Connection Pooler 三大選項

| 工具          | 部署模式               | 主要適用 DB               | 主要特點                                             |
| ------------- | ---------------------- | ------------------------- | ---------------------------------------------------- |
| PgBouncer     | Self-managed / sidecar | PostgreSQL only           | 輕量（C 寫的 single process）、三種 pooling 模式可選 |
| AWS RDS Proxy | Managed                | RDS / Aurora (PG / MySQL) | 整合 IAM auth、自動 failover、計價 per vCPU          |
| ProxySQL      | Self-managed           | MySQL                     | 規則型 routing、可做 query rewriting、自動 failover  |

### PgBouncer — 三種 pooling 模式決定一切

PgBouncer 的核心參數是 `pool_mode`：

- **Session mode**：應用層 client 拿到的連線、跟 DB backend 1:1 綁定、整個 session 結束才釋放。其實沒做 multiplexing、只是 connection caching。
- **Transaction mode**：每個 transaction 結束、應用層 client 的連線釋放回 pool、下個 transaction 再分配 DB backend。multiplexing 比較強、但**不支援 transaction-scoped state**（如 `SET LOCAL`、prepared statement、temporary table）。
- **Statement mode**：每個 statement 結束就釋放、最強 multiplexing 但**不支援 transaction**。極少用、只在純 stateless query workload 適用。

Transaction mode 是多數場景的 default。但要注意：應用層的 ORM / driver 可能默認用 prepared statement、跟 transaction mode 衝突。PostgreSQL 14+ 的 protocol-level prepared statement 才相容、JDBC / asyncpg 等需要特別配置。

### AWS RDS Proxy — managed 換掉運維

RDS Proxy 是 PgBouncer / ProxySQL 同類功能的 managed 版本：AWS 負責部署、HA、failover、IAM 整合。應用層連到 RDS Proxy endpoint、Proxy 在背後維持跟 RDS / Aurora 的連線池。

特點：

- **連線 share 模式類似 transaction mode**：自動 detect 連線是否在 transaction、空閒時釋放
- **IAM auth 整合**：應用層用 IAM token、不用維護 DB password
- **Failover 加速**：DB failover 時 Proxy 維持應用層連線不斷、background 重連 new primary。Failover 期間應用層感受最小化。
- **計價**：per vCPU-hour、Aurora 約 $0.015/vCPU-hr、RDS 約 $0.02/vCPU-hr — 加在 RDS 計價上面

不適用場景：很多 read-only / analytics workload 不需要 connection pooler、純讀 replica 直接連通常更便宜。RDS Proxy 是給「寫入混合」「連線抖動嚴重」這類場景。

### ProxySQL — MySQL 規則型 routing

ProxySQL 是 MySQL 生態的 connection pooler、但比 PgBouncer 更全功能：

- **Query routing rules**：可以按 query pattern 把 query 導去不同 backend（讀路徑去 replica、寫路徑去 primary、特定 query 強制 cache）
- **Connection multiplexing**：類似 PgBouncer transaction mode
- **Query rewriting**：可以攔截 query 改寫（debug / 漸進遷移 schema）
- **Auto failover**：監控 backend 健康、自動切流

ProxySQL 的代價是學習曲線跟運維成本 — 規則設計需要對 query pattern 跟 DB topology 有掌控、設錯規則會把 query 導去錯誤 backend、debug 困難。

## 選型對照

實務選型的關鍵變數是「DB 廠商 / managed 程度 / 規模 / 預算」：

| 場景                               | 推薦                                                                | 理由                                          |
| ---------------------------------- | ------------------------------------------------------------------- | --------------------------------------------- |
| AWS RDS / Aurora、團隊不想自管     | RDS Proxy                                                           | Managed、整合度高、failover 加速是 free value |
| AWS RDS / Aurora、需要極致省成本   | PgBouncer（PG）/ ProxySQL（MySQL）on EC2                            | 比 RDS Proxy 便宜、但要自管 HA                |
| GCP Cloud SQL / 自管 PostgreSQL    | PgBouncer                                                           | PG 生態事實標準、配置文件多                   |
| Azure Database for PostgreSQL      | PgBouncer 或 Azure 內建 connection pooling                          | Azure 部分 SKU 內建類似功能、檢查 vendor 文件 |
| MySQL 需要讀寫分離 + query routing | ProxySQL                                                            | 規則型 routing 是 ProxySQL 強項               |
| 不確定要不要 connection pooler     | 先用 vendor 內建（RDS Proxy / PG managed pooler）跑一段、再評估自管 | 降低初期決策成本                              |

## 不裝 pooler 的判讀

Connection pooler 不是必要 — 在以下情境可以暫時不裝：

- **應用層機器數 < 10**：對 DB 連線總數壓力小、deferred 安裝 pooler 沒問題
- **每臺機器連線數 < 5**：應用層 connection pool 已經很省、再加 pooler 改善有限
- **DB 機器規格大、`max_connections` 充裕**：高階 RDS instance 可開到 5000-10000 連線、有 buffer 之前不必加 pooler
- **Workload 全是長 transaction**：transaction mode pooler 在這種 workload 跟 session mode 沒差、收益低

該裝 pooler 的訊號是相反：應用層機器數 ≥ 20、每臺連線數 ≥ 10、`max_connections` 使用率 ≥ 70%、或 P99 connection wait time 升高。

## 判讀訊號

| 訊號                                       | 判讀重點                                                | 對應動作                                                                   |
| ------------------------------------------ | ------------------------------------------------------- | -------------------------------------------------------------------------- |
| DB `pg_stat_activity` 顯示大量 idle 連線   | 應用層 keep-alive 連線、實際使用率低                    | 加 connection pooler 把 idle 釋放回 DB                                     |
| 應用層 connection acquisition 等待時間升高 | 應用層 pool 太小、或 DB 連線數已撞 `max_connections`    | 加 pooler 把連線總數壓低、應用層 pool size 維持原樣                        |
| DB failover 後應用層 5-10 分鐘錯誤率高     | 應用層 connection pool 沒 detect 到 backend 切換        | RDS Proxy 的 failover 加速、或應用層 connection validation 加強            |
| Pooler 上線後出現「unexpected error」      | transaction mode 跟 prepared statement / SET LOCAL 衝突 | 改 ORM 配置、用 protocol-level prepared statement 或避開 SET LOCAL         |
| 應用層 N+1 query 仍然存在                  | Pooler 沒解 N+1、它只解連線數放大                       | 回 [1.13 query 反模式](/backend/01-database/query-anti-patterns/) 修反模式 |

## 常見誤區

把 connection pooler 當「N+1 解藥」。Pooler 解的是「連線數放大」、不是「query 數量過多」。N+1 query 在裝完 pooler 後仍然慢、只是 DB 不會因為連線爆掉而當機。兩個是正交問題、各自要解。

把 RDS Proxy 當「免費功能」。Proxy 的計價跟 RDS / Aurora 本體疊加、高 connection volume 場景 Proxy 成本可能可觀。要算實際的 cost-per-request、不是預設「managed 一定值得」。

把 transaction mode 配置當「裝完就好」。Prepared statement / SET LOCAL / temporary table 都會跟 transaction mode 衝突、ORM 預設行為要 audit 過、不然會在 production 出現難 debug 的「query 隨機失敗」。

## 定位邊界

本章專注「連線池放大的解法」。當問題進入擴展軸選擇（要垂直 vs 水平？stateful 前提？）、回 [9.13 擴展軸](/backend/09-performance-capacity/scaling-axes/)；進入 DB 本身的容量規劃（要多大規格 instance？要不要 read replica？）、進 [9.6 容量規劃](/backend/09-performance-capacity/capacity-planning/)；進入 application-level connection 設計（per-request pool / persistent pool）、進 [1.1 高併發 SQL](/backend/01-database/high-concurrency-access/)。

## 案例回寫

09 案例庫多數案例規模到 connection pool 已是 secondary concern、但兩個案例有對應參考：

- [9.C18 Zoom：COVID 30 倍突發](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) — Zoom 把 stateful 資料層改用 DynamoDB、繞過 SQL connection pool 問題（KV 沒有 backend process 概念）。對照本章可問：若 Zoom 保留 SQL、connection pool 怎麼設計才撐得住 30 倍突發？
- [9.C39 DoorDash：CockroachDB 多主寫入](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/) — DoorDash 從 Aurora single-primary 換成 CockroachDB 多主、connection pool 設計從「集中在 primary」變成「分散在多 node」。對照本章可問：CockroachDB 是否仍需要 connection pooler？

## 跨模組路由

1. 與 [9.13 擴展軸](/backend/09-performance-capacity/scaling-axes/) 的交接：9.13 提出隱性成本、本章給具體解法。
2. 與 [1.1 高併發 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/) 的交接：1.1 講應用層 connection pool 設計、本章補 DB 端 pooler 中介層。
3. 與 [01 vendors](/backend/01-database/vendors/) 的交接：各 DB vendor 的內建 pooler 能力詳見 vendor deep article。
4. 與 [9.6 容量規劃](/backend/09-performance-capacity/capacity-planning/) 的交接：pooler 加上後、DB 容量規劃的單位從「連線數」變成「DB backend 數 + Pooler vCPU」。

## 下一步路由

要看擴展軸選擇的完整 framing、回 [9.13 擴展軸與 Stateless 前提](/backend/09-performance-capacity/scaling-axes/)。要看 DB-side 高併發處理、進 [1.1 高併發 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/)。要看具體 vendor 的 pooler 文件、進對應 [vendor deep article](/backend/01-database/vendors/)。
