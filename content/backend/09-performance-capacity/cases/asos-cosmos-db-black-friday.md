---
title: "9.C21 ASOS：Cosmos DB 在 Black Friday 撐 1.67 億請求"
date: 2026-05-12
description: "ASOS 在 2016 Black Friday 用 Azure Cosmos DB 撐 24 小時 1.67 億請求、3500 req/sec、48ms 平均延遲"
weight: 21
tags: ["backend", "performance", "capacity", "case-study", "db-kv", "azure", "predictable-peak"]
---

這個案例的核心責任是補強 Azure 案例庫深度。Cosmos DB 過往只有 [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) 一篇、ASOS 提供 *傳統零售場景 + 全球分散 + 季節性峰值* 的對照、跟 Minecraft Earth 的 *AR 遊戲 + 玩家位置* 完全不同業務語意。

## 觀察

ASOS 在 Azure 的關鍵數字（引自 [ASOS Microsoft Customer Story](https://www.microsoft.com/en/customers/story/718983-asos-retail-and-consumer-goods-azure)）：

| 指標                       | 數字                            |
| -------------------------- | ------------------------------- |
| 客戶數                     | 1540 萬                         |
| Black Friday 24 小時請求量 | 1.67 億                         |
| Black Friday 請求峰值      | 3,500 req/sec                   |
| Black Friday 訂單峰值      | 33 orders/sec                   |
| 平均響應時間               | 48 ms                           |
| 商品 SKU                   | 85,000、每週新增 5,000 件       |
| 架構轉變                   | 2016 年遷移到 microservices     |
| 服務組合                   | Azure Cosmos DB + microservices |

關鍵業務驅動：「ASOS chose Azure Cosmos DB because of its global distribution and ability to handle heavy seasonal bursts like Black Friday」。

## 判讀

ASOS 案例揭露三個全球零售 KV 容量規劃重點。

1. **Black Friday 24h 1.67 億 = 平均 1,930 req/sec、峰值 3,500 req/sec**：峰值 / 平均 = 1.81 倍。這個比例顯示 Black Friday 「持續高峰」、不是「瞬間爆量」 — 24 小時內流量曲線相對平緩、跟 [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的「5 分鐘賣完」是完全不同形狀。對應 [9.2 Workload Modeling](/backend/09-performance-capacity/) 的負載形狀識別。
2. **48ms 平均響應 = 全球分散下 Cosmos DB 的代表性數字**：英國時尚電商、客戶遍及全球、Cosmos DB 在每個地區複製、讀取在最近 region 完成。這個 48ms 包含網路、DB、應用層 — DB 本身可能只佔 5-10ms、其他是網路與應用層。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) 的 latency budget 分解。
3. **85K SKU + 每週新增 5K = 高更新頻率 catalog**：商品資料不只是讀、還有頻繁更新（價格、庫存、推薦排序）。這層 write throughput 對 Cosmos DB partition key 設計（通常用 category_id 或 brand_id）至關重要。對應 [9.4 Saturation Discovery](/backend/09-performance-capacity/) 的 hot partition 識別。

需要警惕：這是 2016 年的數字、過去 10 年 ASOS 應該成長很多。但 1.67 億 req/24h 跟 33 orders/sec 對許多新興電商仍是天花板級數字、可作為「中大型零售」對標。

## 策略

可重用的工程做法：

1. **Black Friday 類「持續高峰」適合 provisioned + scheduled scaling**：跟 flash-sale 的「on-demand 吃彈性」不同、Black Friday 整天高、用 provisioned 比較划算。對應 [9.11 高峰事件準備](/backend/09-performance-capacity/) 的可預期峰值準備。
2. **全球零售用 Cosmos DB / DynamoDB Global Tables**：客戶在哪、讀取就在哪、避免跨洲 latency。對應 [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 的全球分散取捨。
3. **微服務 + Cosmos DB 是電商現代化典型路徑**：從單體 → 微服務、從關聯式 DB → multi-model NoSQL、是 2016 後零售業常見遷移。對應 [01 資料庫模組](/backend/01-database/) 與 [05 部署平台模組](/backend/05-deployment-platform/)。

跨平台等效：AWS DynamoDB Global Tables + Lambda、GCP Firestore + Cloud Run 都可以實作對等架構。差異是 Cosmos DB 的 multi-model（同一服務支援 SQL、Mongo、Cassandra、Gremlin、Table API）、AWS 對應有 DynamoDB（KV/Document）+ Neptune（Graph）+ Keyspaces（Cassandra）等多個服務。

## 下一步路由

- 對照其他可預期峰值 → [9.C1 AWS Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) / [9.C13 Hotstar IPL](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/)
- 對照 flash-sale-spike → [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)
- 想對照其他 Cosmos DB 使用 → [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)
- 想規劃全球電商 → [01 資料庫模組](/backend/01-database/) + [9.6 容量規劃模型](/backend/09-performance-capacity/)
- 想拆 Black Friday 容量背後的 RU 成本與 sizing → [Cosmos DB RU 成本模型與 sizing](/backend/01-database/vendors/cosmosdb/ru-cost-model-sizing/)
- 想做電商 partition key 設計 → [Cosmos DB partition key 設計](/backend/01-database/vendors/cosmosdb/partition-key-design/)

## 引用源

- [ASOS – Online retailer uses cloud database to deliver world-class shopping experiences](https://www.microsoft.com/en/customers/story/718983-asos-retail-and-consumer-goods-azure)
- [Azure Cosmos DB](https://azure.microsoft.com/en-us/products/cosmos-db/)
