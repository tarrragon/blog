---
title: "9.C32 Clearent：Azure SQL Hyperscale 撐每年 5 億筆支付交易"
date: 2026-05-13
description: "Clearent 在 Azure SQL Hyperscale 上處理每年 5 億筆支付交易、autoscale + 微服務架構"
weight: 32
tags: ["backend", "performance", "capacity", "case-study", "db-oltp", "azure", "sustained-growth"]
---

這個案例的核心責任是補強 Azure DB-OLTP 維度缺口。Clearent 是美國的中型支付處理商、跟 [9.C14 Standard Chartered 跨市場銀行 OLTP](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 形成對照 — 一個是合規驅動的跨市場分割、一個是單一規模的高吞吐處理。

## 觀察

Clearent 在 Azure SQL Hyperscale 的關鍵敘述（引自 [Clearent Customer Story](https://www.microsoft.com/en/customers/story/774969-clearent-banking-capital-markets-azure)）：

| 指標     | 數字                                                            |
| -------- | --------------------------------------------------------------- |
| 年交易量 | 5 億筆                                                          |
| 客戶基礎 | 各種規模 merchants（中小型為主）                                |
| 服務組合 | Azure SQL Database Hyperscale 服務級                            |
| 架構模式 | modern microservices architecture                               |
| 擴展能力 | 「scale automatically and almost infinitely」                   |
| 並發特性 | 「tens of thousands of users 同時存取」                         |
| 業務驅動 | 「unite all its information in one place」+ 「faster insights」 |

關鍵特性：Azure SQL Hyperscale 把 storage 跟 compute 分離、跟 [9.C23 Netflix Aurora](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 的 Aurora 是同類設計。

## 判讀

Clearent 案例揭露三個 Hyperscale 設計的工程重點。

1. **5 億筆 / 年 ≈ 1500 筆 / 秒平均、但 peak 可能 10-50x**：支付交易有日內 / 月內 / 季內節律。早上 9-11 點商家對帳高峰、下午 12-1 點消費高峰、晚上 6-8 點消費高峰、月底結算高峰。容量規劃必須按 peak 訂、不是平均。對應 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 的 peak/avg ratio 跟 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)。
2. **Hyperscale = storage / compute 解耦**：傳統 SQL Server primary 對 storage 跟 CPU / RAM 綁定、擴 storage 就要換更大 instance、不便。Hyperscale 把 storage 拉到分散式 log service、可以獨立擴 storage（最高 100 TB）、compute 獨立擴。對應 [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 的同類分離思維、跟 [9.C23 Netflix Aurora](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)。
3. **「unite all information in one place」是支付業的特殊需求**：merchants 需要對帳、退款、清算、稅務報表都即時可查、不能 OLAP 分開。Hyperscale 的 read scale-out（最多 4 個 secondary replica）讓即時報表跑在 OLTP DB 上不影響交易吞吐。

需要警惕：「scale automatically and almost infinitely」是行銷敘述。實際 Hyperscale 有上限（100 TB storage、Gen5 series 80 vCore）、超過要 sharding 應用層分散。

## 策略

可重用的工程做法：

1. **Hyperscale 跟 Aurora 是同類設計、選型按生態**：Azure 生態用 Hyperscale、AWS 生態用 Aurora、GCP 用 AlloyDB / Spanner。三家底層工程哲學一致（log-structured storage、storage / compute 分離）、選哪家取決於 application 已在哪個 cloud。
2. **微服務 + 共用 OLTP 是支付業常見架構**：服務拆細、但 OLTP 仍是 single source of truth、共用一個 Hyperscale cluster。這跟 [9.C23 Netflix microservice 各自 Aurora](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 不同 — Netflix 每微服務 *自己* Aurora、Clearent 微服務共用 Hyperscale。取捨：Clearent 的「對帳一致性」需求讓共用更划算。
3. **支付業容量規劃以 peak 為主**：不能用平均 RPS 規劃、要按單日 / 單秒 peak。歷史 peak × 預期成長 × headroom 是基本公式（[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)）。

跨平台等效：AWS Aurora Serverless v2、GCP AlloyDB、Spanner、PostgreSQL 自管 + Patroni 都可實作對等架構。差異是 vendor managed 程度跟 OLAP / OLTP 統一視覺。

## 下一步路由

- 對照其他 OLTP 案例 → [9.C4 DraftKings Aurora](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) / [9.C23 Netflix Aurora](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) / [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)
- 想設計支付業容量 → [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) + [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)
- 想理解 storage / compute 分離 → [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)

## 引用源

- [Clearent scales its modern microservices architecture to handle 500 million payment transactions a year](https://www.microsoft.com/en/customers/story/774969-clearent-banking-capital-markets-azure)
- [Announcing Azure SQL Database Hyperscale](https://azure.microsoft.com/en-us/blog/announcing-azure-sql-database-hyperscale-public-preview/)
- [Get high-performance scaling for your Azure database workloads with Hyperscale](https://azure.microsoft.com/en-us/blog/get-high-performance-scaling-for-your-azure-database-workloads-with-hyperscale/)
