---
title: "模組九案例正文"
date: 2026-05-12
description: "雲端服務商實戰案例庫 — 從 AWS / GCP / Azure 公開案例整理高併發、峰值流量與容量規劃實踐"
weight: 95
tags: ["backend", "performance", "capacity", "case-study"]
---

這個資料夾的核心責任是把雲端服務商公開的高併發實戰案例轉成可回寫主章判讀的案例正文。資料來源以 [AWS Customer Success Stories](https://aws.amazon.com/solutions/case-studies/)、[Google Cloud Customer Stories](https://cloud.google.com/customers) 與 [Azure Customer Case Studies](https://customers.microsoft.com/) 為主，因為這層案例同時提供具體流量數字、實際使用的服務組合與工程決策路徑，比一般 engineering blog 更接近實戰判讀。

跟模組七案例庫一樣、本資料夾不只服務 09 主章閱讀、也是 01-05 模組寫作時的證據來源。當寫 01 資料庫章節需要說明「Aurora 真實流量下能撐多少」、當寫 02 快取章節需要說明「ElastiCache 在持續成長服務的角色」時、可以直接回查本資料夾相應案例。

## 跟 06 案例庫的差異

| 維度     | [06 cases](/backend/06-reliability/cases/)                         | 09 cases（本資料夾）                                            |
| -------- | ------------------------------------------------------------------ | --------------------------------------------------------------- |
| 來源     | 大企業工程部落格（Google SRE Book、Netflix Tech Blog、Shopify 等） | AWS / GCP / Azure 官方 customer case studies                    |
| 證據型態 | 方法論敘事（SLO 政策、chaos hypothesis、failure mode）             | 具體流量、實例、延遲、成本數字（QPS、msg/sec、p95、cost ratio） |
| 讀法     | 失敗模式如何被驗證                                                 | 容量量化實踐：什麼配置撐多少、加多少、成本曲線怎麼走            |
| 教學責任 | 把驗證流程制度化                                                   | 把容量地圖具體化、把成本邊界量化                                |

兩層案例互補。06 教讀者「怎麼預先驗證失敗會被擋住」、09 教讀者「實際配置在實際流量下會怎麼跑」。同一個服務可以同時出現在兩處、但讀法不同。

## 案例列表

每個案例標 tag 讓多個主章可以反查。tag 維度：**雲商**（aws / gcp / azure）、**服務維度**（db-oltp / db-kv / cache / mq-stream / compute / global-edge / latency / data-architecture）、**負載形狀**（predictable-peak / event-peak / surge / flash-sale-spike / low-latency-sustained / sustained-growth）。

| 章節                                                                                        | 主題                                      | 雲商  | 服務維度          | 負載形狀              |
| ------------------------------------------------------------------------------------------- | ----------------------------------------- | ----- | ----------------- | --------------------- |
| [9.C1](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)            | AWS Prime Day 2025 dogfood                | aws   | multi             | predictable-peak      |
| [9.C2](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)          | GR8 Tech 體育博彩 AI 預測式擴容           | aws   | compute           | event-peak            |
| [9.C3](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/)    | Coinbase 超低延遲交易                     | aws   | latency           | low-latency-sustained |
| [9.C4](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)          | DraftKings Aurora 100 萬 ops/min          | aws   | db-oltp           | event-peak            |
| [9.C5](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)              | Amazon Ads DynamoDB 9000 萬 RPS           | aws   | db-kv             | sustained-growth      |
| [9.C6](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/)          | Tinder ElastiCache 配對引擎               | aws   | cache             | sustained-growth      |
| [9.C7](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/)              | Lyft 100+ 微服務 8x 峰值                  | aws   | compute           | event-peak            |
| [9.C8](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)        | Niantic Pokémon GO 50x 突發               | gcp   | compute           | surge                 |
| [9.C9](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/)       | Spotify Kafka → Pub/Sub 遷移              | gcp   | mq-stream         | sustained-growth      |
| [9.C10](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)       | Cloud Spanner 10 億 req/sec               | gcp   | db-oltp           | low-latency-sustained |
| [9.C11](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)           | Minecraft Earth Cosmos DB 全球            | azure | db-kv             | surge                 |
| [9.C12](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)               | Riot Games 246 EKS clusters               | aws   | compute           | low-latency-sustained |
| [9.C13](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/)    | Hotstar IPL 1860 萬同時觀看               | aws   | global-edge       | predictable-peak      |
| [9.C14](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)          | Standard Chartered Aurora 4000 TPS        | aws   | db-oltp           | sustained-growth      |
| [9.C15](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)        | 拓元 Tixcraft 售票搶購                    | aws   | db-kv             | flash-sale-spike      |
| [9.C16](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)              | SeatGeek Virtual Waiting Room             | aws   | compute           | flash-sale-spike      |
| [9.C17](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/)       | BookMyShow 印度年售 2 億張票              | aws   | data-architecture | flash-sale-spike      |
| [9.C18](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)                  | Zoom COVID 30x DAU 突發                   | aws   | db-kv             | surge                 |
| [9.C19](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/)                 | Capcom 遊戲後端 DynamoDB + EKS            | aws   | db-kv             | sustained-growth      |
| [9.C20](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)          | Zomato TiDB → DynamoDB 4x 吞吐            | aws   | db-kv             | sustained-growth      |
| [9.C21](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)                | ASOS Cosmos DB Black Friday               | azure | db-kv             | predictable-peak      |
| [9.C22](/backend/09-performance-capacity/cases/wayfair-gcp-burst-capacity/)                 | Wayfair GCP burst capacity                | gcp   | data-architecture | predictable-peak      |
| [9.C23](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)               | Netflix Aurora 統一 +75% 效能             | aws   | db-oltp           | sustained-growth      |
| [9.C24](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)        | Genesys 99.999% 跨 15 region              | aws   | db-kv             | low-latency-sustained |
| [9.C25](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)          | Tubi ML feature store sub-10ms p99        | aws   | cache             | low-latency-sustained |
| [9.C26](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/)            | PayPay 行動支付每日 3 億訊息              | aws   | db-kv             | sustained-growth      |
| [9.C27](/backend/09-performance-capacity/cases/disney-plus-content-metadata/)               | Disney+ 觀看歷史每日數十億動作            | aws   | db-kv             | predictable-peak      |
| [9.C28](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)        | FanDuel 直播 + 投注雙重峰值               | aws   | compute           | event-peak            |
| [9.C29](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)       | NTT DOCOMO Lemino 5M MAU / 3 個月         | aws   | db-kv             | predictable-peak      |
| [9.C30](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)          | Microsoft 365 MongoDB → Cosmos DB         | azure | data-architecture | sustained-growth      |
| [9.C31](/backend/09-performance-capacity/cases/mercado-libre-latam-bigquery-vertex/)        | Mercado Libre LatAm Vertex + BigQuery     | gcp   | data-architecture | sustained-growth      |
| [9.C32](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/)     | Clearent Azure SQL Hyperscale 5 億 txn/年 | azure | db-oltp           | sustained-growth      |
| [9.C33](/backend/09-performance-capacity/cases/maersk-bosch-azure-aks/)                     | Maersk + Bosch Azure AKS                  | azure | compute           | sustained-growth      |
| [9.C34](/backend/09-performance-capacity/cases/gcp-130k-node-gke-cluster/)                  | GCP 130K-node GKE cluster (AI)            | gcp   | compute           | low-latency-sustained |
| [9.C35](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/)                 | Snap GCP KeyDB cross-cloud cache          | gcp   | cache             | low-latency-sustained |
| [9.C36](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/)         | Coinbase MongoDB 1.5M reads/sec           | aws   | db-document       | low-latency-sustained |
| [9.C37](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/) | Forbes 自管 MongoDB → Atlas on GCP        | gcp   | db-document       | sustained-growth      |
| [9.C38](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/)    | Toyota Connected MongoDB 月 180 億 txn    | aws   | db-document       | sustained-growth      |

## 主章寫作時的反查路由

當寫 01-05 模組的具體服務章節需要援引「真實流量下會發生什麼」、查下表找對應案例。

### 寫 [01 資料庫模組](/backend/01-database/) 時

| 議題                        | 對應案例                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OLTP 高 TPS 容量            | [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) / [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) / [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)                                                                                                                                                                                                         |
| KV 極高吞吐                 | [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) / [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) / [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) / [9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) / [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)                                              |
| 全球一致性 OLTP             | [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) / [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)（multi-region active-active）                                                                                                                                                                                                                                                                            |
| Transaction boundary        | [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/)（RAFT、強順序）                                                                                                                                                                                                                                                                                                                                                                                     |
| Hot partition / 分片        | [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) / [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) / [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)                                                                                                                                                                                                         |
| DB 作為寫入緩衝             | [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)（DynamoDB 緩衝 + 傳統 server 慢速消費）                                                                                                                                                                                                                                                                                                                                                                 |
| DB 種類整合 / consolidation | [9.C23 Netflix Aurora](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) / [9.C24 Genesys DynamoDB 為預設](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)                                                                                                                                                                                                                                                                                           |
| Migration 與合規            | [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) / [9.C9 Spotify](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/) / [9.C20 Zomato TiDB → DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) / [9.C37 Forbes 自管 MongoDB → Atlas](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/)                                                           |
| 多事件 ticketing 資料層     | [9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) / [9.C22 Wayfair](/backend/09-performance-capacity/cases/wayfair-gcp-burst-capacity/)                                                                                                                                                                                                                                                                                                                |
| Document database / MongoDB | [9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/)（1.5M reads/sec、connection proxy）/ [9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/)（自管 → Atlas）/ [9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/)（IoT telematics）/ [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)（遷到 Cosmos DB） |

### 寫 [02 快取模組](/backend/02-cache-redis/) 時

| 議題                         | 對應案例                                                                                                                            |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 高吞吐 cache layer           | [9.C6 Tinder](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/)                                           |
| Cache as SoT                 | [9.C6 Tinder](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/)（配對快取為主要服務面）                   |
| ML feature store             | [9.C25 Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)（sub-10ms p99）                             |
| Sub-ms latency 需求          | [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/)（不只 cache、整體 sub-ms 設計）   |
| Cache stampede               | [9.C8 Pokémon GO surge](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)（50x 突發必觸 stampede 風險） |
| Cache hierarchy / 多層 cache | [9.C25 Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)（L1 in-process + L2 cache + L3 store）      |
| Cache vs durable store 取捨  | [9.C25 Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)（從 ScyllaDB 遷到 ElastiCache）             |

### 寫 [03 訊息佇列模組](/backend/03-message-queue/) 時

| 議題                   | 對應案例                                                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 大規模事件交付         | [9.C9 Spotify](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/)                             |
| Broker 自管 vs managed | [9.C9 Spotify](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/)                             |
| 極端 message volume    | [9.C1 AWS Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)（SQS 1.66 億 msg/sec）     |
| Queue 作為緩衝吸收洪峰 | [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)（DynamoDB 模仿 queue 行為） |
| Migration playbook     | [9.C9 Spotify](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/)                             |

### 寫 [04 可觀測性模組](/backend/04-observability/) 時

| 議題                    | 對應案例                                                                                                                                                                                                                                                                                             |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SLO 量測 baseline       | [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)（99.999% availability）/ [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)（99.999% 12 個月達成）                                                               |
| Latency budget 反推     | [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) / [9.C12 Riot](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) / [9.C25 Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)（ML p99 分解）      |
| Saturation 訊號         | [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)（25ms p95 是業務 KPI）                                                                                                                                                                                   |
| 多地區 metric 治理      | [9.C13 Hotstar](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/) / [9.C12 Riot](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) / [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)（15 主 region） |
| SLO 演進 / surge 後校準 | [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)（30x 後 baseline 永久上移）                                                                                                                                                                                          |

### 寫 [05 部署平台模組](/backend/05-deployment-platform/) 時

| 議題                        | 對應案例                                                                                                                                                                                                                                                                                                     |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| K8s multi-cluster           | [9.C12 Riot Games](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) / [9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/)（多遊戲共用 vs 多 cluster）                                                                                                    |
| Container vs VM             | [9.C8 Pokémon GO](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)                                                                                                                                                                                                              |
| 微服務切分                  | [9.C7 Lyft](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/) / [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)（微服務私有 store）                                                                                                              |
| Autoscaling 策略            | [9.C1 Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) / [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) / [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)（30 分鐘擴 130 倍） |
| Global edge / CDN           | [9.C13 Hotstar](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/) / [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)（CloudFront 卸載靜態）                                                                                      |
| 限流 / Virtual Waiting Room | [9.C16 SeatGeek](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)（明確排隊）/ [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)（隱性緩衝）                                                                                               |
| Hybrid cloud / burst        | [9.C22 Wayfair](/backend/09-performance-capacity/cases/wayfair-gcp-burst-capacity/)（on-prem + GCP burst）                                                                                                                                                                                                   |
| Control plane vs Data plane | [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)（DynamoDB 撐 metadata、影音另走 edge）                                                                                                                                                                                       |

### 寫 [00 服務選型模組](/backend/00-service-selection/) 時

| 議題                 | 對應案例                                                                                                                                                                                                                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Traffic / data scale | 全部案例都可作對標、特別是 [9.C1](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) / [9.C5](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) / [9.C10](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) |
| 合規 / 受監管        | [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)                                                                                                                                                                                |
| Vendor 戰略支援      | [9.C8 Pokémon GO](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)（Google CRE）                                                                                                                                                                        |
| 成本曲線             | [9.C12 Riot Games](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/)（$10M 年省）                                                                                                                                                                                |

## 按負載形狀的讀法引導

當讀者遇到具體容量問題卡住時、先判斷負載屬於哪一種形狀、再選對應案例。

1. **可預期極端峰值**（年度活動、預售、賽事決賽）→ [9.C1 Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) / [9.C13 Hotstar](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/) / [9.C21 ASOS Black Friday](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) / [9.C22 Wayfair](/backend/09-performance-capacity/cases/wayfair-gcp-burst-capacity/)
2. **事件型不可預期峰值**（賽事高潮、突發新聞、KOL 推廣）→ [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) / [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) / [9.C7 Lyft](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/)
3. **突發遠超預期的 surge**（產品爆紅、病毒式擴散、結構性外部事件）→ [9.C8 Pokémon GO](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)（產品爆紅、暫時）/ [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) / [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)（COVID 結構性永久）
4. **flash-sale 瞬間爆量**（售票開賣、報名活動、限量搶購）→ [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)（隱性緩衝）/ [9.C16 SeatGeek](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)（明確排隊）/ [9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/)（規模化平台資料層）
5. **持續成長 sustained**（用戶月增、業務擴張）→ [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) / [9.C6 Tinder](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) / [9.C9 Spotify](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/) / [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) / [9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) / [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) / [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)
6. **低延遲持續需求**（金融交易、即時配對、廣告競價、ML inference）→ [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) / [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) / [9.C12 Riot](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) / [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) / [9.C25 Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)

### surge 形狀的兩種次分類

surge（突發遠超預期）內部還可分兩種、設計回應完全不同：

- **產品爆紅 surge**（[9.C8 Pokémon GO](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/)）：流量隨熱度消退、是「暫時偏離 baseline 又回歸」。容量規劃焦點是「撐過熱度高峰、避免在最忙時掛」。
- **結構性 surge**（[9.C18 Zoom COVID](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)）：baseline 永久上移、是「新常態」。容量規劃焦點是「30x 後 SLO baseline 重新校準、長期成本曲線重算」。

### flash-sale-spike 形狀的特殊性

售票搶購 / 報名活動 / 限量搶購跟其他「峰值」案例有本質差異：

- **時間點精確、可秒級預測**：開賣時刻 = 公告時刻、跟 GR8 Tech 的「賽事高潮」不一樣（賽事高潮在何時 + 多大都未知）
- **持續時間極短**：5-30 分鐘賣完、跟 Prime Day（48 小時）/ Hotstar IPL（4 小時）量級差很多
- **峰值倍數極端**：t=0 前流量近 0、t=0 瞬間衝到 10K-100K 倍、平均流量沒意義、只有峰值
- **後端不容易跟上**：高流量湧入時、付款 / 簽證 / 庫存後端通常是 legacy 系統、無法等比擴容、必須靠 buffer / queue / waiting room 解耦

這個負載形狀的兩個主要設計模式：**隱性緩衝**（[Tixcraft 模式](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)：用 DynamoDB / Kafka 吸收洪峰、後端慢消費）跟**明確排隊**（[SeatGeek 模式](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)：Virtual Waiting Room + token-based queue）。實務常見組合使用 — 入口先排隊、進入後仍用 buffer。

## 案例覆蓋矩陣

下表顯示 38 個案例在 *服務維度 × 雲商* 的覆蓋情況、空格代表待補。

| 服務維度          | AWS                                        | GCP      | Azure             |
| ----------------- | ------------------------------------------ | -------- | ----------------- |
| DB-OLTP           | C4, C14, C23                               | C10      | C32               |
| DB-KV             | C5, C15, C18, C19, C20, C24, C26, C27, C29 | （待補） | C11, C21          |
| DB-Document       | C36, C38                                   | C37      | （透過 C30 對照） |
| Cache             | C6, C25                                    | C35      | （待補）          |
| MQ-Stream         | C1 (SQS), C7 (Kinesis)                     | C9       | （待補）          |
| Compute / K8s     | C2, C7, C12, C16, C19, C28                 | C8, C34  | C33               |
| Global Edge       | C13                                        | （待補） | （待補）          |
| Latency 敏感      | C3, C25, C36                               | C10, C35 | （待補）          |
| Data Architecture | C17                                        | C22, C31 | C30               |

AWS 25 個 case、GCP 8 個 case（補了 130K-node GKE + Snap KeyDB + Forbes）、Azure 5 個 case。三家覆蓋更平衡。新增 DB-Document 維度後、MongoDB 作為主角的案例（C36 Coinbase / C37 Forbes / C38 Toyota Connected）跟原本 C30 Microsoft 365（MongoDB 遷出 → Cosmos DB）形成完整 document model 案例組。剩餘缺口：Azure cache / global edge / latency、GCP DB-KV / MQ-Stream 加深、GCP / Azure global edge。

### 負載形狀 × 雲商 覆蓋

| 負載形狀              | AWS                                  | GCP           | Azure         |
| --------------------- | ------------------------------------ | ------------- | ------------- |
| predictable-peak      | C1, C13, C27, C29                    | C22           | C21           |
| event-peak            | C2, C4, C7, C28                      | -             | -             |
| surge                 | C18                                  | C8            | C11           |
| flash-sale-spike      | C15, C16, C17                        | -             | -             |
| low-latency-sustained | C3, C12, C24, C25, C36               | C10, C34, C35 | -             |
| sustained-growth      | C5, C6, C14, C19, C20, C23, C26, C38 | C9, C31, C37  | C30, C32, C33 |

flash-sale-spike 是 09 案例庫的核心 differentiator — 雲商案例庫對這個負載形狀的著墨遠勝一般 engineering blog。surge 維度補了 Zoom 之後、跟 Pokemon GO（暫時 surge）跟 Minecraft Earth（地理 surge）形成三種次分類對照。後續若有 GCP / Azure 同類售票案例可補。

## 規劃中案例（第二批）

待 09 主章寫作推進、第二批案例可從下列候選補齊。

| 候選案例                    | 預期教學重點                             | 來源                                                                                                                              |
| --------------------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Disney+ DynamoDB            | 每日數十億動作、watch list metadata      | [DynamoDB customers](https://aws.amazon.com/dynamodb/customers/)                                                                  |
| PayPay 30 億訊息/日         | 行動支付的持續高頻 message               | [DynamoDB customers](https://aws.amazon.com/dynamodb/customers/)                                                                  |
| Capcom DynamoDB             | 遊戲業數十億請求、single-digit ms        | [DynamoDB customers](https://aws.amazon.com/dynamodb/customers/)                                                                  |
| Zomato 90% 延遲下降         | 帳務處理、跨資料庫遷移效益               | [DynamoDB customers](https://aws.amazon.com/dynamodb/customers/)                                                                  |
| Zoom COVID 30x 成長         | 1000 萬 → 3 億 DAU、突發長期 sustained   | [DynamoDB customers](https://aws.amazon.com/dynamodb/customers/)                                                                  |
| FanFight 100 萬寫入/秒      | 印度 fantasy sports 體育博彩             | [DynamoDB customers](https://aws.amazon.com/dynamodb/customers/)                                                                  |
| Tubi ScyllaDB → ElastiCache | ML feature store sub-10ms p99            | [ElastiCache customers](https://aws.amazon.com/elasticache/customers/)                                                            |
| FanDuel 直播 + 投注         | 雙重峰值對齊                             | [FanDuel case study](https://aws.amazon.com/solutions/case-studies/fanduel-case-study/)                                           |
| Blockchain.com Spanner      | Crypto 高頻交易、強一致全球              | [Spanner blog](https://cloud.google.com/blog/products/databases/using-cloud-spanner-to-handle-high-throughput-writes/)            |
| Walmart Cosmos DB           | 全球零售 KV、跨地區一致性策略            | [Cosmos DB blog](https://azure.microsoft.com/en-us/blog/azure-cosmos-db-pushing-the-frontier-of-globally-distributed-databases/)  |
| Microsoft 365 Cosmos        | MongoDB → Cosmos 遷移、planet-scale 分析 | [Cosmos DB Microsoft 365 blog](https://azure.microsoft.com/en-us/blog/microsoft-365-boosts-usage-analytics-with-azure-cosmos-db/) |

## Engineering Blog 補充候選

當 AWS / GCP / Azure 案例缺乏某些工程紀律的深度（例如 chaos hypothesis、cell-based architecture 細節），補引 engineering blog 作為交叉驗證。候選來源：Shopify BFCM、Netflix Tech Blog、Amazon Builders' Library、Google SRE Book、LinkedIn Engineering、Stripe Engineering、Cloudflare Blog、Discord Engineering、Uber Engineering、Pinterest Engineering 等。這層不另開資料夾、補在主章「案例對照」段。

## 案例正文格式

每篇案例使用統一結構、方便快速比對。

1. **觀察**：客觀數字與事件序列。流量規模、實例配置、延遲分布、成本變化都用引用源的原始數字、不四捨五入。
2. **判讀**：把案例的工程決策翻成主章的問題節點。
3. **策略**：可重用的工程做法、去掉雲端 vendor 特異性。EKS、Auto Scaling、DynamoDB on-demand 等翻成跨平台等效概念。
4. **下一步路由**：往哪個主章或前置案例延伸閱讀。
5. **引用源**：雲端服務商官方 case study URL + 相關 Architecture Blog 連結。

## Tripwire

- 同一服務維度的 case 超過 5 個時、暫停擴張、改補其他維度。
- AWS 案例數字過於行銷、缺工程細節 → 補 AWS Architecture Blog 同主題文章作為交叉驗證。
- 案例只是「我們用了 X 服務」、沒有具體量化結果 → 不收進案例庫、作為候選參考即可。
- 同一公司多個案例（例如 Coinbase 還有遷移案例）→ 拆 sub-case 而不是合成單一檔。
- GCP / Azure 覆蓋持續落後 AWS 超過 2 倍時 → 主動補 GCP / Azure 案例、不要讓案例庫變成 AWS-only。
