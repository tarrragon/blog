---
title: "9.C36 Coinbase：MongoDB 撐 Ruby 單體 + 1.5M reads/sec identity 服務"
date: 2026-05-26
description: "Coinbase 以 MongoDB 為主資料層、自建 mongobetween connection proxy、users 服務在加密貨幣 surge 時撐 1.5M reads/sec"
weight: 36
tags: ["backend", "performance", "capacity", "case-study", "db-document", "aws", "low-latency-sustained"]
---

這個案例的核心責任是說明「document database 在大規模 OLTP 場景如何撐住」。Coinbase 從 Ruby on Rails 單體 + MongoDB 起家、八年後仍保留 MongoDB 作為主資料層、並把 connection pooling、ML 預測擴容、cache + freshness token 都疊在 document model 上。跟 [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) 對照 — Microsoft 365 走「遷出 MongoDB、保留 document API」、Coinbase 走「保留 MongoDB、補周邊工具」。兩條路徑都揭露 MongoDB 在 production 主角位置會遇到什麼壓力。

## 觀察

Coinbase MongoDB 平台的關鍵數字（引自 [Coinbase Engineering Blog](https://www.coinbase.com/blog/scaling-connections-with-ruby-and-mongodb) 與 [MongoDB customer case study](https://www.mongodb.com/solutions/customer-case-studies/coinbase)）：

| 指標                       | 數字                                    |
| -------------------------- | --------------------------------------- |
| Users 服務尖峰讀取         | 1.5M reads / sec                        |
| Deploy 時 MongoDB 連線尖峰 | ~60K connections / minute（單 cluster） |
| mongobetween 後連線降幅    | 30K → ~2K（一個量級）                   |
| MongoDB cluster 數量       | many clusters（多服務 federated）       |
| 加密貨幣 surge 擴容時間    | 70 分鐘 → 25 分鐘（-64%）               |
| ML 預測擴容領先窗          | 60 分鐘                                 |
| Cache 命中後跳過 DB        | 是（Memcached query-cache）             |

服務組合：MongoDB Atlas（主資料層）、DynamoDB（部分 workload 的 federated store）、Memcached（query result cache）、自研 mongobetween proxy（連線多工）、Ruby on Rails 單體 + 多個 Fragment APIs、ML 預測模型驅動 cluster auto-scaling。

關鍵負載形狀：「加密貨幣價格突發 + 用戶交易需求湧入」雙峰疊加。價格 alert 觸發 read 爆量（users / portfolio 查詢）、下單觸發 write 爆量（order book / wallet 寫入）。兩種峰值不像 [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 的 Super Bowl 事件型可預測、是隨外部市場波動的 *low-latency-sustained 中夾雜 surge*。

## 判讀

Coinbase MongoDB 的工程選擇揭露三個 document database 在 production 主角位置的設計重點。

1. **MongoDB + Ruby 連線爆炸需要外部 connection pool**：CRuby 因為 GVL 必須每 CPU core 起一個 process、blue-green 部署期間 instance 數量 ×2、連線數隨之 ×2、單一 cluster 看到 60K 連線/分鐘。原生 MongoDB driver 沒有跨 process 的 connection pool — 跟 PostgreSQL 走 pgbouncer 是同樣需求、所以 Coinbase 自建 [mongobetween](https://github.com/coinbase/mongobetween) 做多工。對應 [01.6 高併發資料存取](/backend/01-database/high-concurrency-access/) 的 connection storm 問題、document database 不會自動解決、要主動補工具。
2. **document model 撐 1.5M reads/sec 靠 cache + freshness token**：直接打 MongoDB 不可能撐 1.5M reads/sec — Coinbase 在 users 服務前面加 Memcached query cache、單 document query 先查 cache。但 cache + write 會有一致性問題、所以引入 OCC version 跟 *freshness token*：write 成功後給 client 一個 token、client 之後 read 帶 token、server 保證返回的資料版本 ≥ token、必要時 bypass cache 直接打 DB。對應 [01.5 transaction boundary](/backend/01-database/transaction-boundary/) 的 read-after-write 設計。
3. **加密貨幣 surge 用 ML 預測、不靠 reactive scaling**：cluster 擴容要 70 分鐘、傳統 CPU / queue 觸發的 reactive scaling 在 surge 開始時才動、來不及。Coinbase 訓練 ML 模型分析價格資料、提前 60 分鐘預測流量、預先擴容。把擴容時間從 70 分鐘壓到 25 分鐘是 trigger 提前、不是擴容本身變快。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/) 的 predictive scaling。

需要警惕：

- 「1.5M reads/sec」是 users 服務 *加上 cache* 的數字、不是 MongoDB cluster 純讀取數字。讀案例時要區分「應用層觀察到」跟「DB 層實際承擔」。
- mongobetween 是 Coinbase 特殊環境（Ruby + GVL + blue-green）的產物。Go / Java / Node.js 應用因為原生支援連線多工、通常不需要這層 proxy。
- ML 預測有 false positive / false negative — 預測錯時要嘛浪費容量、要嘛 surge 真來時擋不住。Coinbase 沒揭露準確率、所以仍保留 reactive scaling 作為 safety net。

## 策略

可重用的工程做法：

1. **document database 撐大規模 OLTP 要主動補 connection pool**：MongoDB 原生 connection 模式對「process 數多 + deploy 重」的環境會爆。應用層或 sidecar proxy 做多工是基線設計。對應 [01.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)。
2. **freshness token 是 read-after-write 一致性的可重用模式**：比 strong consistency（性能差）跟 eventually consistent（read 不到剛寫的）更精細的中間路徑。token 機制可以推廣到任何「主要 eventually consistent、少數 read 要求最新」的場景。
3. **predictive scaling 適用於「外部訊號可預測流量」的服務**：加密貨幣價格、賽事行程、票務開賣時間都是外部訊號。比 reactive scaling 早一個擴容週期出手。對應 [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) 的 AI 預測式擴容。
4. **federated DB（MongoDB + DynamoDB）按 workload 分流**：document-shaped 用 MongoDB、access pattern 固定的 KV 用 DynamoDB。不是「全用 MongoDB」也不是「全遷 DynamoDB」、是按 workload 形狀分。對應 [9.C23 Netflix Aurora](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 的多 DB 整合反例（Netflix 走整合方向、Coinbase 走 federated）。

跨平台等效：

- AWS：MongoDB Atlas + ElastiCache + DynamoDB（Coinbase 配置）
- GCP：MongoDB Atlas on GCP + Memorystore + Firestore（document API）
- Azure：Cosmos DB MongoDB API + Cache for Redis、不需要 Atlas
- mongobetween 風格的 proxy：PostgreSQL 走 pgbouncer / pgcat、MongoDB 走 mongobetween / mongoproxy

## 下一步路由

- 想規劃 MongoDB 大規模 production → [MongoDB vendor page](/backend/01-database/vendors/mongodb/) + [01.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- 想做 read-after-write 一致性設計 → [01.5 transaction boundary](/backend/01-database/transaction-boundary/)
- 想做 predictive scaling → [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) + [9.6 容量規劃模型](/backend/09-performance-capacity/)
- 想對照 MongoDB 遷出 / 保留決策 → [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)（遷到 Cosmos DB MongoDB API）
- 想理解 connection storm 問題 → [01.6 高併發資料存取](/backend/01-database/high-concurrency-access/)
- 想深入 connection / proxy 治理與 cache 層 → [MongoDB connection 管理與 cache 層](/backend/01-database/vendors/mongodb/connection-management-and-cache-layer/)
- 想做 replica set 讀寫分離設計 → [MongoDB replica set read preference](/backend/01-database/vendors/mongodb/replica-set-read-preference/)

## 引用源

- [Coinbase：Scaling connections with Ruby and MongoDB](https://www.coinbase.com/blog/scaling-connections-with-ruby-and-mongodb)
- [Coinbase：Scaling Identity - How Coinbase Serves 1.5M Reads/Second](https://www.coinbase.com/blog/scaling-identity-how-coinbase-serves-1.5M-reads-second)
- [Coinbase：How We Do MongoDB Migrations at Coinbase](https://www.coinbase.com/blog/how-we-do-mongodb-migrations-at-coinbase)
- [MongoDB customer case study：Coinbase Decreases Scaling Time](https://www.mongodb.com/solutions/customer-case-studies/coinbase)
- [mongobetween GitHub repository](https://github.com/coinbase/mongobetween)
