---
title: "9.C20 Zomato：從 TiDB 遷移到 DynamoDB、吞吐 4 倍、延遲降 90%、成本減 50%"
date: 2026-05-12
description: "Zomato 帳單系統從 TiDB 遷移到 DynamoDB、吞吐 2K→8K RPM、延遲降 90%、成本減 50%"
weight: 20
tags: ["backend", "performance", "capacity", "case-study", "db-kv", "aws", "sustained-growth"]
---

這個案例的核心責任是提供「同樣業務需求、不同 DB 技術」的具體對照數字。Zomato 帳單系統從 TiDB 遷移到 DynamoDB、留下三個關鍵改善百分比、是 DB 選型決策的少見 *可量化* 對照樣本。

## 觀察

Zomato 帳單系統遷移的關鍵數字（引自 [AWS Database Blog](https://aws.amazon.com/blogs/database/unlocking-performance-scalability-and-cost-efficiency-of-zomatos-billing-platform-by-switching-from-tidb-to-dynamodb/)）：

| 指標         | TiDB（遷移前） | DynamoDB（遷移後） |
| ------------ | -------------- | ------------------ |
| 微服務吞吐   | 2,000 RPM      | 8,000 RPM（4x）    |
| 延遲降幅     | baseline       | -90%               |
| 成本降幅     | baseline       | -50%               |
| 每日事件量   | 10M（共用）    | 10M                |
| 餐廳合作夥伴 | 350,000+       | 350,000+           |

關鍵動機：TiDB 必須為「突發流量峰值」提前 over-provision、付出常態成本；DynamoDB on-demand 模式「pay only for what we use」、避免 over-provisioning。

## 判讀

Zomato 遷移揭露三個 DB 選型決策的判讀重點。

1. **NewSQL vs NoSQL 的取捨不只是 schema**：TiDB 提供 SQL 介面跟 ACID、DynamoDB 提供 KV 介面跟最終一致性。Zomato 選 DynamoDB 是判斷「帳單事件本身可以接受 eventually consistent」、用一致性換性能跟成本。對應 [01.5 transaction boundary](/backend/01-database/transaction-boundary/) 的一致性取捨。
2. **TiDB 必須 over-provision 是分散式 SQL 的常態**：分散式 SQL 為了支援跨節點交易、必須有預留容量、否則峰值會出現 leader election storm 或 follower lag。這跟 [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 的「節點數即容量」是同類取捨、Spanner 也必須預先 scale 節點。
3. **2K → 8K RPM 是 4 倍、但延遲降 90% 才是真關鍵**：吞吐改善可能來自架構優化、延遲改善才是 DB 本質差。從 baseline → 10% 通常代表少了 1-2 個 hop（例如 cross-region replication、coordinator round-trip）。對應 [9.1 壓測理論與系統行為](/backend/09-performance-capacity/) 的 Little's Law。

需要警惕：

- 「成本降 50%」是 *當下流量下的對照*。如果未來流量繼續成長、DynamoDB 的 cost-per-request 成長率比 TiDB 自管 cluster 高 — 達到某規模後 TiDB 反而更便宜。讀遷移案例要看「在當下流量下划算」、不等於「永遠划算」。
- 「90% 延遲降」可能只是 p50、p99 / p999 改善幅度通常較小。

## 策略

可重用的工程做法：

1. **DB 遷移前先確認業務一致性需求**：能接受 eventually consistent 的工作負載適合 KV / NoSQL；必須 strong consistency 的工作負載必須 SQL / NewSQL。對應 [01.5 transaction boundary](/backend/01-database/transaction-boundary/)。
2. **遷移評估要看「總成本曲線」、不是「當下 snapshot」**：算未來 12-24 個月在預期流量下的成本對照、不是只算現在。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)。
3. **遷移過程要 dual-write + shadow read 驗證**：避免新舊系統行為不一致導致業務問題。對應 [01.3 schema migration rollout evidence](/backend/01-database/schema-migration-rollout-evidence/)。
4. **on-demand vs provisioned 的選擇與業務流量形狀對應**：突發流量適合 on-demand、可預測流量適合 provisioned。對應 [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的 on-demand 應用。

跨平台等效：MongoDB Atlas → DynamoDB、Cassandra → DynamoDB、PostgreSQL → Aurora、CockroachDB → Spanner 都是常見遷移路徑。每條路徑的取捨類似。

## 下一步路由

- 想做 DB 遷移評估 → [01 資料庫模組](/backend/01-database/) + [01.4 database migration playbook](/backend/01-database/database-migration-playbook/)
- 想理解一致性取捨 → [01.5 transaction boundary](/backend/01-database/transaction-boundary/) + [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)
- 想做總成本評估 → [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)
- 對照其他 DB 遷移 → [9.C9 Spotify Kafka→Pub/Sub](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/)

## 引用源

- [Unlocking performance, scalability, and cost-efficiency of Zomato's Billing Platform by switching from TiDB to DynamoDB](https://aws.amazon.com/blogs/database/unlocking-performance-scalability-and-cost-efficiency-of-zomatos-billing-platform-by-switching-from-tidb-to-dynamodb/)
- [How Zomato Boosted Performance 25% and Cut Compute Cost 30% Migrating Trino and Druid Workloads to AWS Graviton](https://aws.amazon.com/blogs/opensource/how-zomato-boosted-performance-25-and-cut-compute-cost-30-migrating-trino-and-druid-workloads-to-aws-graviton/)
