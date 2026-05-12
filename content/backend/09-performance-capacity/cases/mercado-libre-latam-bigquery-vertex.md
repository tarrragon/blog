---
title: "9.C31 Mercado Libre：LatAm 電商在 GCP 上用 Vertex AI 搜尋 1.5 億商品"
date: 2026-05-12
description: "Mercado Libre 1 億客戶 + 1.5 億商品、用 GCP Vertex AI Search + BigQuery 提供近即時搜尋與分析"
weight: 31
tags: ["backend", "performance", "capacity", "case-study", "data-architecture", "gcp", "sustained-growth"]
---

這個案例的核心責任是補強 GCP 案例庫的「商業應用」深度、並提供拉丁美洲電商規模對標。Mercado Libre 是拉丁美洲最大電商（市值 600 億美金級）、業務涵蓋 18 個國家、是區域型平台的容量規劃範本。

## 觀察

Mercado Libre 在 GCP 的關鍵敘述（引自 [Mercado Libre Customer Story](https://cloud.google.com/customers/mercado-libre)）：

| 指標          | 數字                                               |
| ------------- | -------------------------------------------------- |
| 客戶數        | 1 億                                               |
| 商品數        | 1.5 億（3 個試點國家）                             |
| 業務影響      | 數百萬美金 incremental revenue（Vertex AI Search） |
| 主要 GCP 服務 | Vertex AI Search、BigQuery                         |
| 資料即時性    | near real-time                                     |
| 服務地理      | 拉丁美洲                                           |

關鍵能力：「Vertex AI Search across 150 million items in three pilot countries that is helping its 100 million customers find the products they love faster」、「BigQuery to design a robust data architecture that ensures the availability of data in near real-time」。

## 判讀

Mercado Libre 揭露三個區域電商容量規劃重點。

1. **區域電商 ≠ 全球電商**：拉丁美洲 18 個國家、各自有獨立貨幣、稅務、物流、合規規則。容量規劃單位通常是「per country」、不是「per region」。對應 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 的市場分割、跟 [9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) 的跨國平台對照。
2. **Vertex AI Search = 「搜尋」當作 ML 服務、不是 Elasticsearch**：傳統電商搜尋靠 Elasticsearch / OpenSearch + 自訓 ranker、Mercado Libre 用 vendor managed Vertex AI Search、把「商品搜尋 + 推薦排序」當作 ML 黑盒。這個取捨用「不可調參」換「快速上線」。對應 [00 服務選型模組](/backend/00-service-selection/) 的 build vs buy、跟 [9.C9 Spotify](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/) 的 managed 轉向同類思維。
3. **「數百萬美金 incremental revenue」是 ML 容量規劃的真實 ROI**：搜尋改善 → 轉換率 → 訂單 → 收入、ML 投資的 cost 才能合理化。容量規劃不只看「能撐多大流量」、也要看「擴容能否帶業務 ROI」。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/) 的成本工程化。

需要警惕：

- 「1.5 億商品 in 3 pilot countries」是 *試點規模*、不是全平台。全平台商品總數應該更大、但案例沒揭露。
- BigQuery「near real-time」沒指明 latency（秒級、分鐘級）。BigQuery 傳統是 minutes-level、不是 sub-second、對「即時」的定義要謹慎。

## 策略

可重用的工程做法：

1. **區域電商的容量規劃是「per country × peak_factor」**：不是「per region」聚合、要按國家分別規劃。每個國家自己的 Black Friday / Cyber Monday / 雙 11 / 6.18 等本地大促時間都不同。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/)。
2. **「商品搜尋」適合用 managed AI search**：除非有自家強大的 ML team + 大量訓練資料、否則 Vertex AI Search / OpenSearch Service 等 managed 比自建 ranker 划算。
3. **BigQuery 是 LatAm / 新興市場數據平台的標配**：能處理 PB 級資料、無需 cluster 管理、適合中等工程資源的團隊。對應 [04 可觀測性模組](/backend/04-observability/) 的 data 平台選型、跟 [9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) 的 Redshift + Athena 對照。
4. **ML ROI 直接 ＝ 業務指標**：transaction conversion rate、AOV、recommendation CTR 都是 ML 容量規劃的下游 KPI。

跨平台等效：AWS Personalize + Redshift + Glue、Azure AI Search + Synapse 都是對等候選。差異是 vendor 整合度跟模型的可調參空間。

## 下一步路由

- 對照其他大規模電商 → [9.C21 ASOS Black Friday](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) / [9.C22 Wayfair burst](/backend/09-performance-capacity/cases/wayfair-gcp-burst-capacity/)
- 想規劃跨國容量 → [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) + [9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/)
- 想做 ML feature serving → [9.C25 Tubi ML feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)
- 想做 build vs buy 決策 → [00 服務選型模組](/backend/00-service-selection/) + [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)

## 引用源

- [Mercado Libre Customer Story](https://cloud.google.com/customers/mercado-libre)
- [How Mercado Libre uses real-time analytics for on-time delivery](https://cloud.google.com/blog/products/data-analytics/how-mercado-libre-uses-real-time-analytics-for-on-time-delivery)
