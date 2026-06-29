---
title: "9.C5 Amazon Ads：DynamoDB 9000 萬 reads/sec 的廣告事件量測"
date: 2026-05-12
description: "Amazon Ads 在 DynamoDB 上跑 9000 萬 reads/sec + 500 萬 writes/sec、99.999% 可用性的廣告事件量測"
weight: 5
tags: ["backend", "performance", "capacity", "case-study", "db-kv", "aws", "sustained-growth"]
---

這個案例的核心責任是提供「key-value 持續高吞吐」的極限參考點。廣告事件量測屬 *write-heavy + read-heavy 同時存在* 的負載 — 每個曝光都要寫進度、每個曝光也都要查 metadata。這類負載沒有明顯峰谷、是長期 sustained growth、跟事件型峰值的容量設計邏輯不同。

## 觀察

Amazon Ads 在 DynamoDB 的關鍵數字（引自 [DynamoDB customers](https://aws.amazon.com/dynamodb/customers/)）：

| 指標   | 數字               |
| ------ | ------------------ |
| 讀吞吐 | 9000 萬 reads / 秒 |
| 寫吞吐 | 500 萬 writes / 秒 |
| 可用性 | 99.999%            |
| 用途   | 廣告事件量測       |

讀寫比約 18:1。這個比例反映「曝光發生 1 次、後續查詢可能發生 18 次」的廣告計費邏輯。

## 判讀

這個案例最重要的不是「DynamoDB 能撐多少」、而是「為什麼可以這樣設計」。

1. **單表分散到上千個 partition**：DynamoDB 把每個 table 拆成多個 partition、每個 partition 內部還可以再分散。9000 萬 reads / 秒 是上千個 partition 加總的結果、單一節點達不到這個量級。對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 的 sharding 邊界、跟 [01 資料庫模組](/backend/01-database/) 的 partition 設計。
2. **partition key 選擇直接決定容量上限**：DynamoDB 的容量是「每 partition 上限 × partition 數量」。partition key 不均勻會出現 hot partition、實際容量遠低於名義容量。對應 [9.4 Saturation Discovery](/backend/09-performance-capacity/) 的 saturation 不一定是整體 saturation、而是 *最熱的 partition* saturation。
3. **99.999% availability ≈ 5 分鐘 / 年的容錯**：廣告計費 1 分鐘斷線可能損失幾百萬美金廣告收入。這個 SLO 不是行銷數字、是真實的營收邊界。對應 [04.16 SLI / SLO 訊號](/backend/04-observability/sli-slo-signal/) 與 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/)。

需要警惕：「9000 萬 reads / 秒」這種敘述通常是 *年度峰值的最高一秒*、不是平均值。容量規劃要區分「最大瞬時」、「99 百分位平均」、「常態流量」三個不同口徑。

## 策略

可重用的工程做法：

1. **partition key 設計是 KV 容量的第一決策**：均勻分散、避免 hot partition、必要時加 random suffix 強制分散。對應 [01 資料庫模組](/backend/01-database/) 的 schema design 章節。
2. **read-heavy 跟 write-heavy 比例變化是容量警訊**：當業務邏輯改變（例如新增即時報表）、讀寫比可能跳一個量級、原本的容量規劃會失效。對應 [9.8 效能可觀測性](/backend/09-performance-capacity/) 持續監控比例變化。
3. **on-demand vs provisioned 是成本 vs 反應速度的取捨**：on-demand 自動擴容但成本高、provisioned 便宜但需要預測。Amazon Ads 這種 sustained workload 通常用 provisioned + auto scaling、不用 on-demand。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)。

跨平台等效：GCP Cloud Bigtable + 良好 row key 設計、Azure Cosmos DB partition key 設計都是對等概念。差異是 DynamoDB 的 partition 透明度（你看不到 partition 數量）vs Bigtable 的明確 tablet 模型。

## 下一步路由

- 想規劃 KV 高吞吐架構 → [9.5 瓶頸定位流程](/backend/09-performance-capacity/) + [01 資料庫模組](/backend/01-database/)
- 想避免 hot partition → [01.6 高併發資料存取](/backend/01-database/high-concurrency-access/) + [9.4 Saturation Discovery](/backend/09-performance-capacity/)
- 想對照其他 KV 案例 → [9.C11 Minecraft Earth Cosmos DB](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)（Azure 全球分散）
- 想深入 DynamoDB hot partition 反模式 → [DynamoDB partition key 反模式](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)
- 想拆 access pattern 對應的 single-table design → [DynamoDB single-table design](/backend/01-database/vendors/dynamodb/single-table-design-pattern/)
- 想評估 on-demand vs provisioned 切換時機 → [DynamoDB on-demand vs provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)

## 引用源

- [Amazon DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)
- [Handle traffic spikes with Amazon DynamoDB provisioned capacity](https://aws.amazon.com/blogs/database/handle-traffic-spikes-with-amazon-dynamodb-provisioned-capacity/)
- [Demystifying Amazon DynamoDB on-demand capacity mode](https://aws.amazon.com/blogs/database/demystifying-amazon-dynamodb-on-demand-capacity-mode/)
