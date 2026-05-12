---
title: "9.C17 BookMyShow：印度年售 2 億張票的資料架構現代化"
date: 2026-05-12
description: "BookMyShow 從 15 年自建 analytics 遷移到 AWS modern data architecture、4 個月完成、分析成本下降 80%"
weight: 17
tags: ["backend", "performance", "capacity", "case-study", "data-architecture", "aws", "flash-sale-spike", "sustained-growth"]
---

這個案例的核心責任是說明「規模化 ticketing 平台」的長期工程議題 — 跟 [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的「單一搶票事件」不同、BookMyShow 是 *每天都有上百個 flash-sale 事件* 的平台、年售 2 億張票、跨 5 個國家。容量問題從「單一峰值」變成「峰值的常態化」、加上「資料層怎麼跟得上業務變化」。

## 觀察

BookMyShow 在 AWS 的關鍵敘述（引自 [BookMyShow AWS Migration Blog](https://aws.amazon.com/blogs/business-intelligence/how-bookmyshow-saved-80-in-costs-by-migrating-to-an-aws-modern-data-architecture/)）：

| 指標         | 數字                                     |
| ------------ | ---------------------------------------- |
| 年售票量     | 2 億張 / 年（pre-COVID baseline）        |
| 服務地理     | 印度 + 斯里蘭卡 + 新加坡 + 印尼 + 中東   |
| 遷移時程     | 4 個月完成                               |
| 舊系統年數   | 15 年自建 analytics solution             |
| 儲存成本下降 | 90%                                      |
| 分析成本下降 | 80%                                      |
| 資料整合     | 從 80 TB 多份副本 → 單一 source of truth |

資料架構：

- **Data Lake**：Amazon S3 統一儲存
- **Ingestion**：Kafka consumers、AWS Glue ETL、AWS IoT Core（MQTT）
- **Processing**：Amazon EMR（streaming permanent cluster + batch transient cluster）
- **Data Warehouse**：Amazon Redshift + materialized views
- **Analytics**：Amazon Athena（ad-hoc）+ Amazon QuickSight（dashboard）
- **ML**：Amazon SageMaker（內容熱度、活動熱度、搜尋趨勢模型）
- **Orchestration**：Amazon MWAA + AWS Step Functions

關鍵業務支撐：「sudden spikes with new movies or events launched」靠 serverless（S3、Glue、Athena、Step Functions、Lambda）自動擴容、無需人工介入。

## 判讀

BookMyShow 案例揭露三個規模化 ticketing 平台的長期工程重點。

1. **單一搶票 → 常態多事件 = 架構從「為峰值設計」變「為流量分佈設計」**：每天上百場電影 + 數十場演唱會 + 各種活動同時開票、每場都是 mini flash-sale。容量問題不再是「為一場演唱會準備」、而是「為每天上百個峰值同時準備」。對應 [9.2 Workload Modeling](/backend/09-performance-capacity/) 從單一 workload 變成 workload portfolio。
2. **資料層比交易層更難擴**：8 TB → 80 TB 過程中、舊 analytics 系統用 15 年才走到極限。交易層擴容靠 stateless EC2 + auto-scaling 相對容易、資料層 schema migration、ETL 重寫、報表回對都是長 lead time 工作。對應 [01 資料庫模組](/backend/01-database/) 的 schema migration 與 [04 可觀測性模組](/backend/04-observability/) 的 cost attribution。
3. **跨國市場 = 多重合規約束**：印度、新加坡、印尼、中東各自有資料駐留 / 加密 / 報稅規則。S3 + EMR + Redshift 的「資料分區」不只是性能議題、也是合規議題。對應 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 的合規容量規劃。

需要警惕的判讀盲點：

- 「年售 2 億張」是 *年度總和*、不是 *峰值*。實際單秒峰值（板球比賽決賽開票、寶萊塢新片首映）案例本身沒揭露。
- 案例聚焦在 *資料分析層* 的遷移、不是 *交易層* 的 flash-sale 設計。讀者若想學「單場 flash-sale 怎麼撐」、應該回 [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 或 [9.C16 SeatGeek](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)。
- 「80% 成本下降」是 *vs 15 年舊系統*、不是 *vs 競爭對手*。舊系統的儲存效率、運維成本本來就低、改善幅度部分來自「現代化紅利」、不只是 AWS 服務本身。

## 策略

可重用的工程做法：

1. **大規模 ticketing 平台要分「交易層」跟「資料層」兩條容量規劃**：交易層為單一 event flash-sale 設計（[9.C15](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) / [9.C16](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 模式）；資料層為「上千場活動的長期分析」設計（BookMyShow 模式）。兩者用不同服務、不同 SLO。
2. **跨國平台先解決資料駐留、再規劃跨國 analytics**：印度資料不能搬到新加坡分析、合規必須各國資料本地處理、再彙整 metadata。對應 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)。
3. **serverless data stack 是 ticketing 平台的長期方向**：S3 + Glue + Athena + Step Functions 的成本曲線比 EMR cluster 平穩、沒事件時近乎 0、有事件時自動擴。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)。
4. **遷移時程 4 個月 = 計畫密度極高**：15 年資產 4 個月遷完不是常態、需要先把 *資料模型* canonical 化、再 batch 平行遷。對應 [01.4 database migration playbook](/backend/01-database/database-migration-playbook/) 的 schema 對映先行。

跨平台等效：GCP BigQuery + Dataflow + Cloud Storage + Pub/Sub 是對等 stack；Azure Synapse + Data Lake + Event Hubs；自建 Delta Lake + Spark + Kafka 都可以實作對等架構。差異是 vendor 整合度跟 serverless 透明度。

## 下一步路由

- 想規劃多事件 ticketing 平台 → [9.2 Workload Modeling](/backend/09-performance-capacity/) + [01 資料庫模組](/backend/01-database/)
- 想看單一 flash-sale 設計 → [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) + [9.C16 SeatGeek](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)
- 想做跨國合規容量規劃 → [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) + [00 服務選型模組](/backend/00-service-selection/)
- 想做大規模 migration → [01.4 database migration playbook](/backend/01-database/database-migration-playbook/) + [9.C9 Spotify migration](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/)

## 引用源

- [How BookMyShow saved 80% in costs by migrating to an AWS modern data architecture](https://aws.amazon.com/blogs/business-intelligence/how-bookmyshow-saved-80-in-costs-by-migrating-to-an-aws-modern-data-architecture/)
- [AWS Modern Data Architecture](https://aws.amazon.com/architecture/analytics-big-data/)
