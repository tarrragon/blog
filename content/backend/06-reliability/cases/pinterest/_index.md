---
title: "Pinterest"
date: 2026-05-01
description: "Pinterest Capacity Planning 與儲存架構可靠性"
weight: 22
---

Pinterest 是視覺探索平台、capacity planning 與儲存架構的工程文章揭露大規模 data-heavy service 的可靠性挑戰。

## 規劃重點

- Storage Capacity：HBase / TiDB 等 stateful 系統的 capacity model
- Cache Strategies：Memcache / Redis 大規模部署的 failure mode
- Scaling Patterns：visual search 等高運算服務的可靠性
- Migration Reliability：跨 storage backend migration 的零事故設計

## 預計收錄實踐

| 議題                  | 教學重點                             |
| --------------------- | ------------------------------------ |
| Storage Migration     | HBase → TiDB 等大規模 migration 設計 |
| Cache Reliability     | hot key、thundering herd 的工程處理  |
| Capacity Planning     | data-heavy service 的容量預測        |
| ML Serving Resilience | 推薦系統的可靠性需求                 |

## 案例定位

Pinterest 這個案例在講的是資料密集型服務如何透過 storage migration 與容量規劃維持可用性。讀者先抓 HBase、TiDB、zero downtime migration 與 RocksDB 這些原語，再把它們視為資料平台演進的路徑。

## 判讀重點

當儲存後端需要退役或升級時，重點不是把資料搬過去，而是如何在搬移過程中維持服務穩定。當推薦或搜尋系統吃到熱點流量時，cache 與 capacity 的設計要先保住查詢路徑，再處理最佳化。

## 可操作判準

- 能否把 storage migration 拆成不中斷的階段
- 能否指出 hot key 與 thundering herd 的風險位置
- 能否讓 data platform 的容量模型跟業務成長對齊
- 能否把 migration 成果寫成可重複的工程模式

## 與其他案例的關係

Pinterest 把資料平台演進和可靠性綁在一起，和 Shopify 的峰值準備、GitHub 的資料一致性、Meta 的大規模 storage 實踐都有對照價值。這頁最重要的訊息是：migration 不是搬家，而是維持服務語義的持續變更。

## 代表樣本

- HBase → TiDB migration 展示零停機遷移如何保住線上讀寫。
- RocksDB wide column database 代表新 storage backend 如何接手舊系統的壓力。
- cache strategies 讓熱點流量不直接壓垮主存儲。
- capacity planning 把資料密集型服務的擴容節奏固定下來。
- ML serving resilience 讓推薦系統在資料平台變動時仍能維持體感。
- zero-downtime migration 讓線上變更從一次性事件變成可管理流程。
- hot key mitigation 讓快取與查詢壓力不會一起炸開。
- storage backend migration 讓資料平台可以分階段換血。

## 引用源

- [HBase Deprecation at Pinterest](https://medium.com/pinterest-engineering/hbase-deprecation-at-pinterest-8a99e6c8e6b7)：HBase 退役與新 storage 方向。
- [TiDB Adoption at Pinterest](https://medium.com/pinterest-engineering/tidb-adoption-at-pinterest-1130ab787a10)：TiDB 選型與 migration 脈絡。
- [Online Data Migration from HBase to TiDB with Zero Downtime](https://medium.com/pinterest-engineering/online-data-migration-from-hbase-to-tidb-with-zero-downtime-43f0fb474b84)：零停機遷移的具體實作。
- [Building Pinterest’s new wide column database using RocksDB](https://medium.com/pinterest-engineering/building-pinterests-new-wide-column-database-using-rocksdb-f5277ee4e3d2)：新 wide column database 的工程脈絡。
