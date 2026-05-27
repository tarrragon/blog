---
title: "9.C14 Standard Chartered：受監管銀行的 Aurora 4000 TPS 容量提升"
date: 2026-05-12
description: "Standard Chartered 銀行遷移到 Aurora 後吞吐量提升 10 倍至 4000 TPS、跨 7 個受監管市場"
weight: 14
tags: ["backend", "performance", "capacity", "case-study", "db-oltp", "aws", "sustained-growth", "regulated"]
---

這個案例的核心責任是說明「受監管產業」的容量規劃跟「網路服務」的本質差異。銀行交易系統的容量目標不只是「能撐多少」、還要同時滿足合規（資料駐留、稽核、加密、可恢復性）、跟一般工程性能優化的取捨完全不同。

## 觀察

Standard Chartered 在 Aurora 的關鍵敘述（引自 [AWS search results](https://aws.amazon.com/search/) 與相關 case study）：

| 指標           | 遷移前             | 遷移後 (Aurora)            |
| -------------- | ------------------ | -------------------------- |
| 交易吞吐 (TPS) | （未公開、基線值） | 4000 TPS                   |
| 吞吐倍數       | 1x baseline        | 10x                        |
| 受監管市場     | -                  | 7 個（首批遷移）           |
| 成本下降       | -                  | 「顯著」（未公開具體數字） |
| 主要驅動       | 韌性 + 性能        | -                          |

服務組合：Amazon Aurora（PostgreSQL 或 MySQL 相容）、加密 at rest / in transit、多 AZ 部署、跨地區複製（受監管市場各自獨立）。

## 判讀

受監管銀行案例揭露三個合規驅動容量規劃的重點。

1. **資料駐留限制 = 容量規劃的單位是「per 市場」**：7 個受監管市場代表 7 個獨立 cluster（資料不能跨境）、容量規劃變成「7 個獨立規劃 × 各自合規門檻」。對應 [00 服務選型模組](/backend/00-service-selection/) 的合規要求識別、跟 [9.6 容量規劃模型](/backend/09-performance-capacity/) 的地理分片。
2. **「韌性 + 性能」並列、不是 trade-off**：傳統工程文化常把可靠性跟性能視為對立、銀行業務要求兩者同時達標。Aurora 的多 AZ storage + replica 同時提供性能（讀分流）跟韌性（故障切換）、達成 *韌性即性能* 的目標。對應 [06.18 reliability metrics governance](/backend/06-reliability/reliability-metrics-governance/) 的可靠性指標。
3. **遷移本身的合規驗證 = 容量規劃延伸**：受監管系統遷移不只是技術測試、還要過合規審查（中央銀行 / 金融監管機關）、每個市場各自審。這個審查 lead time（數月）必須算進遷移時程。對應 [01.4 database migration playbook](/backend/01-database/database-migration-playbook/) 的合規驅動 migration。

需要警惕：「10x throughput」是 *vs 舊系統*、不是 *vs 競爭對手*。受監管銀行的舊系統通常是 1990s-2000s 的 mainframe 或自建 OLTP、性能本來就低。讀案例時要對標的是「自家改善幅度」、不是「絕對性能」。

## 策略

可重用的工程做法：

1. **資料駐留是容量規劃的硬限制、不是優化選項**：受監管市場必須各自獨立 cluster、不能用「全球單一 cluster」優化。對應 [00.4 traffic data scale](/backend/00-service-selection/traffic-data-scale/) 的合規限制。
2. **多 AZ + 跨地區複製是合規基線、不是優化**：銀行業務 RPO / RTO 通常由監管要求（不能丟資料、必須 X 小時內恢復）、不是業務 SLA 選項。對應 [06.7 DR rollback rehearsal](/backend/06-reliability/dr-rollback-rehearsal/)。
3. **遷移時程要算合規 lead time**：每個受監管市場的審查可能 3-12 個月、合計遷移時程是「市場數 × 平均審查月份」、不是「技術遷移月份」。對應 [01.4 database migration playbook](/backend/01-database/database-migration-playbook/)。

跨平台等效：Azure SQL Hyperscale + Azure regions、GCP Cloud SQL / Spanner + regional configurations、各家雲端的受監管雲端方案（AWS GovCloud、Azure Government、GCP Assured Workloads）都是對等候選。差異是各家對特定監管框架（PCI-DSS、ISO27001、各國金融法規）的認證覆蓋。

## 下一步路由

- 想規劃受監管產業 OLTP → [00 服務選型模組](/backend/00-service-selection/) + [01 資料庫模組](/backend/01-database/)
- 想做合規驅動的容量規劃 → [00.4 traffic data scale](/backend/00-service-selection/traffic-data-scale/) + [9.6 容量規劃模型](/backend/09-performance-capacity/)
- 想理解韌性跟性能的同步達成 → [06.18 reliability metrics governance](/backend/06-reliability/reliability-metrics-governance/)
- 對照其他金融交易案例 → [9.C4 DraftKings Aurora](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) / [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/)
- 想拆解跨 AZ failover RTO 量級與合規 anti-recommendation → [Aurora 跨 AZ failover RTO](/backend/01-database/vendors/aurora/cross-az-failover-rto/)
- 想評估全球資料常駐與多 region 部署 → [Aurora global database 多 region](/backend/01-database/vendors/aurora/global-database-multi-region/)
- 想對照 distributed SQL（CockroachDB / Aurora DSQL / Spanner）的合規場景 → [Aurora DSQL / Spanner / CockroachDB 決策樹](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/)

## 引用源

- [Amazon Aurora Customer Stories](https://aws.amazon.com/rds/aurora/customers/)
- [Amazon Aurora for Core Banking Systems](https://aws.amazon.com/blogs/industries/amazon-aurora-for-core-banking-systems/)
- [Amazon Aurora DSQL for global-scale financial transactions](https://aws.amazon.com/blogs/database/amazon-aurora-dsql-for-global-scale-financial-transactions/)
