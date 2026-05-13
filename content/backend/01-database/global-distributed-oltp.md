---
title: "1.11 全球分散式 OLTP"
date: 2026-05-13
description: "Spanner / Aurora DSQL / Cosmos DB multi-region write / CockroachDB / TiDB 的全球一致性取捨"
weight: 11
tags: ["backend", "database", "oltp", "global", "consistency"]
---

## 概念定位

全球分散式 OLTP 解決一個傳統 DB 做不到的問題：跨地理位置 *同時* 維持強一致性、低延遲、高可用性。CAP 定理過往把這視為「三選二」，但近 15 年的工程進展（Google Spanner、AWS Aurora DSQL、CockroachDB、Microsoft Cosmos DB 等）顯示「在投入 *專屬硬體* 或 *特殊演算法* 的條件下、可以同時拿到 strong consistency + global distribution + 可接受 latency」。

本章整理這類系統的工程設計、容量取捨、跟傳統 single-region OLTP 的差異。讀完後讀者能回答：什麼業務需求需要 global OLTP、跨 region quorum 的延遲代價、選 Spanner vs Aurora DSQL vs Cosmos DB 的決策依據。

跟 [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) 的關係：1.3 處理 single-region OLTP 的 transaction 設計、本章處理 multi-region OLTP 的特殊取捨。

跟 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 的關係：1.10 KV 通常 eventual consistency 全球分散容易、本章處理 *強一致* 全球分散的工程挑戰。

## CAP 跟 PACELC：理論工具

選擇全球 DB 前要先理解兩個理論框架。

**CAP 定理**：分散式系統 *發生分區（network partition）* 時、必須在 Consistency 跟 Availability 二選一。

- CP 系統：強一致、partition 時拒絕服務（Spanner、Cosmos DB strong）
- AP 系統：高可用、partition 時可能回舊資料（Cassandra、DynamoDB Global Tables）

**PACELC（Daniel Abadi 提出）**：擴充 CAP、加上「沒 partition 時」的取捨。

- 沒 partition 時：Latency vs Consistency 二選一
- 結合表示：PA/EL（partition 時選 Availability、平時選 Latency）vs PC/EC（partition 時選 Consistency、平時選 Consistency）

**工程含義**：

- Spanner、Aurora DSQL、Cosmos DB strong：PC/EC — 永遠選一致、付出 latency
- Cassandra、DynamoDB Global Tables：PA/EL — 永遠選快、付出可能不一致
- Cosmos DB session：PA/EL 但對同一 session 內保持 EC — 妥協方案

選 global DB 不是「哪個最好」、是「業務需要哪一邊」。金融交易、ticketing inventory、payment ledger 通常需要 EC；社群 feed、推薦、analytics 通常 EL 夠用。

## Spanner / TrueTime 模型

[Google Cloud Spanner](https://cloud.google.com/spanner) 是目前最成熟的 global strong-consistency OLTP。

**TrueTime API**：用 GPS + 原子鐘提供「全球 *unambiguous* 時間戳」、解決分散式系統最難的問題之一 — 跨節點時序排序。

**External consistency（線性化）**：用 TrueTime 保證「全球任何節點看到的交易順序、跟 wall clock 一致」。比 CAP 的 strong consistency 更強。

**容量特性**（引自 [9.C10 Spanner 案例](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)）：

- 內部峰值 > 10 億 requests / 秒
- 線性擴展：2 nodes → 45K reads/sec、4 nodes → 90K reads/sec
- 跨地區交易延遲 100-200ms（quorum round-trip 不可壓縮）
- multi-region instance 可設定 quorum location（影響哪幾個 region 必須同意）

### 線性擴展為什麼是 OLTP 設計的最高目標

「2 nodes → 45K reads/sec、4 nodes → 90K reads/sec」這個線性對應在傳統 OLTP（PostgreSQL、MySQL）做不到。原因是 *跨節點交易需要 coordinator 確認順序、coordinator 本身是 bottleneck*。加更多節點不會線性加吞吐、因為 coordinator 處理速度跟不上、其他節點得排隊等。

Spanner 用 Paxos + TrueTime 把 coordinator 變成「拓樸感知的多 leader」、每個 leader 只管自己 partition、不需要全域 coordinator。這層演算法 + 硬體（GPS + 原子鐘）配合、才達成線性擴展。

**為什麼這個 frame 對選型重要**：讀「Spanner 撐 10 億 req/sec」不該理解成「能力差距」、而是「設計差距」— 傳統 OLTP 不是「沒它快」、是「結構上做不到線性」。如果業務未來會跨 region 擴展、必須在最初就選 distributed SQL、不是先用 PostgreSQL 再「之後加 sharding」。

**對等技術跟取捨**：

- **AWS Aurora DSQL**：用其他協議（OCC + 分散式時鐘）達成跨 region strong consistency、不用 TrueTime 硬體。
- **CockroachDB**：用 HLC（Hybrid Logical Clock）+ Raft、可在通用硬體上跑、但 cross-region linearizability 需要 OCC retry。
- **TiDB**：用 TSO（Timestamp Oracle）服務發 global timestamp、TSO 本身是 single point、可用性要靠 TSO failover 設計。

TrueTime 是 *專屬硬體投資*、其他方案是 *軟體 only*、兩者一致性保證等級類似、但運維成本跟認證難度差很大。可複製性低的 TrueTime 是 Google 的競爭優勢、不是普遍 best practice。

**容量規劃**：

- 節點數量 = 容量單位（每年 review）
- 跨 region quorum 配置決定 latency baseline
- 不能像 single-region OLTP 那樣短期擴容、需要提前 ramp

**適用場景**：

- 金融交易、ticketing inventory
- 全球客戶但需要強一致
- 不能容忍跨地區 stale read 的業務

**不適用**：

- 跨洲低延遲（沒辦法、TrueTime 也壓不下 100ms 跨洲）
- 高 throughput 但容忍 eventual consistency（Bigtable / Cassandra 更便宜）

### 分散式 SQL 的 over-provision 屬結構性成本

分散式 SQL（TiDB、CockroachDB、Spanner）要求恆常 over-provision、是結構性成本、不是 capacity planning 失誤。三個原因都來自跨節點協調的物理需求：

- 跨節點 transaction 需要 coordinator 角色、leader election 在尖峰當下不能發生、否則整個 cluster 卡住。
- 預留 buffer 讓 leader / follower lag 在尖峰時仍能收斂、否則 replication lag 爆增、讀走 replica 的 query 拿到太舊資料。
- 跨 region quorum 在某個 region 暫時不可用時、剩下 region 要能繼續 quorum、所以每 region 的容量都要 >= quorum 所需。

對應 [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — Zomato 從 TiDB 遷出是業務需求側的判斷：該 workload 本身就能接受 eventually consistent、為 strong consistency 付的 over-provision 屬於浪費。判讀重點：strong consistency 是業務需求時、distributed SQL 的常態 over-provision 是合理代價；業務需求不到這個層級時、KV / 傳統 OLTP 是更划算的選項。

選型公式：先問業務需求要什麼一致性層級、再選 DB 類型、避免倒過來「先選 DB 再硬塞需求」。

## Aurora DSQL：AWS 的全球 strong consistency 答案

AWS 在 2024 re:Invent 推出 Aurora DSQL、是 AWS 對 Spanner 的回應。

**設計特點**（引自 [Aurora DSQL announcement](https://aws.amazon.com/blogs/database/amazon-aurora-dsql-for-global-scale-financial-transactions/)）：

- 跨 region active-active write
- 強一致性（線性化）
- PostgreSQL wire protocol compatible（應用層改動小）
- Serverless（不必管 instance）

**跟 Spanner 的差異**：

- Spanner 用 TrueTime 硬體、Aurora DSQL 用其他協議
- Aurora DSQL 跟 PostgreSQL 相容（容易遷移）、Spanner 是專屬 SQL dialect
- Aurora DSQL 較新（2024）、生態還在成長
- Spanner 服務時間長（內部 2007、外部 2017）、production 案例多

**適用場景**：

- AWS 生態用戶想要 global strong consistency
- 已用 Aurora / PostgreSQL、想擴展到 multi-region
- 應用層想保留 PostgreSQL ORM

## CockroachDB 跟 TiDB：自管選項

如果不想 vendor lock-in、或需要 on-prem 部署、選擇是 *self-managed* distributed SQL。

**CockroachDB**：

- 開源、可自管或用 Cockroach Cloud
- 跟 PostgreSQL wire protocol compatible
- 線性擴展、跨 region 部署、強一致
- 設計理念近 Spanner、但不用 TrueTime（用 HLC + Raft）

**TiDB**：

- 開源（PingCAP）、可自管或用 TiDB Cloud
- 跟 MySQL wire protocol compatible
- TiKV + TiDB 分層架構
- 中國市場大量使用、亞洲生態成熟

**選擇取捨**：

- vendor lock-in 風險 → 選 CockroachDB / TiDB
- 想 managed → 選 Spanner / Aurora DSQL
- 已用 PostgreSQL → 選 CockroachDB / Aurora DSQL（migration 容易）
- 已用 MySQL → 選 TiDB

對應案例：[9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) 從 TiDB 遷出（理由不是 TiDB 不好、是 NewSQL 必須 over-provision、KV NoSQL 對該 workload 更划算）。

## Cosmos DB multi-region write 模式

[Azure Cosmos DB](https://azure.microsoft.com/products/cosmos-db/) 提供 *五個一致性層級*、是 multi-region OLTP 最有彈性的選擇之一。

**五個 consistency level**（從強到弱）：

1. **Strong**：linearizable、跨 region quorum
2. **Bounded staleness**：訂版本 / 時間上限
3. **Session**：同 session 內強一致
4. **Consistent prefix**：保證寫入順序
5. **Eventual**：最便宜、最終一致

**Multi-region write 特色**：

- 每個 region 都能寫、不必所有寫入回主 region
- conflict resolution 用 LWW（Last-Writer-Wins）或自訂 stored procedure
- 跟 Spanner 的 strong consistency 不同 — 是 *AP 系統*、不保證 linearizability

**適用場景**：

- 全球用戶分布、想 *寫入本地 region* 減延遲
- 容忍 eventual consistency（電商商品評論、社群動態）
- 不能容忍跨 region failover 中斷

**對應案例**：

- [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — AR 玩家位置用 session consistency、跨 region 寫入
- [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — Black Friday 全球用戶、Cosmos DB 跨 region 複製
- [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — 分析 platform 用 weakest acceptable consistency、最大 throughput

## 跨地理合規：法規限制下的 global OLTP

部分產業（金融、醫療、政府）有 *資料駐留* 要求 — 特定國家的資料不能離境。這跟全球分散式 OLTP 的設計有 conflict。

**典型法規**：

- 歐盟 GDPR：歐洲用戶資料應留歐
- 中國《網路安全法》、《資料安全法》：中國用戶資料留中國
- 印度資料保護法：印度金融資料留印度
- 美國各州 healthcare（HIPAA）：醫療資料規範
- 金融業：各國央行通常規定本地交易資料留本地

**設計策略**：

- *多個獨立 cluster*、每個合規區一個。不是 single global cluster。
- meta-data 可以 global（用戶 profile 摘要）、transaction 必須 local
- 跨區查詢通過 federated query 或 ETL、不是直接 join

**對應案例**：

- [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 7 個受監管市場、各自獨立 Aurora cluster、不能合併
- [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) — 15 主 region + 5 衛星、按合規區分布
- [9.C32 Clearent](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) — 美國支付業務、Azure SQL Hyperscale + 美國 region

## 延遲代價：跨 region quorum 不可壓縮

全球 strong consistency 必須付的延遲代價來自物理。光速跑跨大西洋（紐約 ↔ 倫敦 5500 km）大約 27ms one-way、實際網路延遲 70-90ms（含路由 / 處理）。任何 strong consistency 系統都不能比這個快。

**典型跨 region quorum latency**：

- 同 region 跨 AZ：1-3ms
- 同 continent 跨 region（us-east-1 ↔ us-west-2）：50-80ms
- 跨 continent（us ↔ eu）：80-120ms
- 跨地球（us ↔ asia）：150-250ms

**工程含義**：

- SLO 訂 p99 < 50ms 跨 continent strong consistency → 不可能達成
- 必須在 SLO 設計時就接受跨 region 的物理 floor
- 業務不需要 strong consistency 的話、用 session / eventual 換 latency

**對應案例**：

- [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — sub-ms 需求、無法跨 region、用 single-AZ cluster placement
- [9.C12 Riot Games](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) — 35ms VALORANT 延遲門檻、靠 region cluster 滿足、不靠 global DB

詳見 [Latency Budget 卡片](/backend/knowledge-cards/latency-budget/)。

### 業務的不同延遲代價曲線

讀「100-200ms 跨洲延遲」這種數字、不能只看絕對值、要看 *業務代價怎麼隨延遲變化*。不同業務型態的延遲代價曲線不同、決定能不能用 strong consistency 全球分散。

**B2B agent 操作介面**（客服平台、CRM）：延遲代價的特性是 *累積*。agent 一通客戶電話內連續操作數十次、每次卡 1 秒、累積 30 秒讓 agent 在用戶面前沉默 — 客服效率直接掉一半、客戶等不及掛電話、agent 績效跟 NPS 同時下降。專屬訊號是「單次 latency 看似可接受、agent 體感卻變慢」。對應 [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) 用 15 個 region 把任一 agent 的 DB 延遲壓到 < 50ms — 客服 SaaS 對單次延遲的容忍區間遠窄於一般網路服務。

**B2C 終端用戶**（社群、電商）：延遲代價是 *一次性跳離*。用戶等 1 秒會抱怨、等 3 秒會跳離；但完成一個操作就走、不會像 B2B 累積多次。容忍區間在 200ms-500ms、超過就掉 conversion。專屬訊號是「session bounce rate 跟 latency p99 高度相關」、不是看平均。

**金融交易**（payment、trading）：延遲代價有兩面、是其他業務型態少見的結構。一面是用戶體驗（付款卡 = 結帳放棄）、另一面是 *系統正確性*（交易順序錯 = 對帳異常、稽核失敗）。後者讓金融業願意付 100-200ms 換 strong consistency、因為對帳成本遠高於延遲成本。專屬訊號是「願意接受比 B2C 更高的 latency budget、但拒絕任何 consistency 妥協」。對應 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 7 個受監管市場的設計。

**IoT / Telemetry**：延遲幾乎無業務代價（資料晚 10 秒進來、報表還是準）、但 throughput 才是主導指標。原因是這類業務的價值來自 *大量裝置的聚合趨勢*、不是 *單一裝置即時回應*；只要事件最終到達且順序合理、晚一點不影響決策。專屬訊號是「百萬裝置同時上報、寫入吞吐才是 SLO、latency 不在 alert 條件裡」。選型上 KV 或時序 DB 比 strong-consistency OLTP 更划算。

判讀重點：選 global OLTP 前先畫業務的延遲代價曲線、再決定能付多少 latency budget 給 strong consistency。「100ms 跨洲太慢」這個直覺反射只在沒有對帳 / 累積 / 趨勢這些業務代價時成立。

## 容量規劃：跟 single-region OLTP 完全不同

全球分散式 OLTP 的容量規劃有獨特挑戰。

**容量單位**：

- Spanner：節點數
- Aurora DSQL：serverless 自動（按 ACU 計費）
- Cosmos DB：RU/s（每個 region 獨立配置）
- CockroachDB / TiDB：節點數 + storage

**規劃要點**：

- 每個 region 獨立規劃（跨 region 不能 amortize）
- quorum 配置決定哪些 region 必須同意（影響 failure domain）
- 跨 region replication lag 是 SLO 一部分
- 不能像 single-region 那樣 reactive 擴容、必須 predictive

**對應 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)**：全球 OLTP 是「不可水平擴容服務」的延伸 — 不只「單機極限」、是「跨 region 協調的物理極限」。

## 可用性目標的成本曲線

「我們要 99.99% 還是 99.999%」這個問題不該用直覺答、要先看每多一個 9 帶來的成本是多少。可用性是非線性、不是線性。

**九的數學意義**：

| 可用性   | 年停機時間     | 月停機時間     | 適用場景                               |
| -------- | -------------- | -------------- | -------------------------------------- |
| 99%      | 87.6 小時 / 年 | 7.3 小時 / 月  | 開發 / 內部工具                        |
| 99.9%    | 8.76 小時 / 年 | 43.8 分鐘 / 月 | 一般 B2C 網站                          |
| 99.95%   | 4.38 小時 / 年 | 21.9 分鐘 / 月 | B2C SaaS、有 SLA 但非 mission-critical |
| 99.99%   | 52.6 分鐘 / 年 | 4.38 分鐘 / 月 | 受監管產業、付款                       |
| 99.999%  | 5.26 分鐘 / 年 | 26 秒 / 月     | 客服 SaaS、telco、5x9 是合約義務       |
| 99.9999% | 31.5 秒 / 年   | 2.6 秒 / 月    | 極特殊（核電、航空管制）               |

**為什麼 99.99 → 99.999 是指數成本而非線性**：每多一個 9、要求 *每一層基礎設施* 都要對等冗餘。

- 99.9 → 99.99：加 multi-AZ active-active、~2-3x 成本
- 99.99 → 99.999：加 multi-region active-active、+ DR 演練、+ failover 自動化、+ 監控覆蓋率拉滿、~5-10x 成本
- 99.999 → 99.9999：加多 cloud、+ 異地災備、+ 全自動 failover、+ 全鏈路演練、~20-50x 成本

**適用場景的業務理由**：

- **99.99%（受監管產業、付款）**：合約 SLA 通常落在這層。受監管金融在中央銀行 / 金融監管機關的書面要求下、年度書面合規會審查 downtime 紀錄、超過 52 分鐘 / 年要解釋；付款 gateway 對商家 SLA 通常承諾 99.99%、低於這個值會被合作夥伴扣保證金。
- **99.999%（客服 SaaS / telco）**：5x9 是 B2B 客服 SaaS 跟電信業的 *合約義務*、不是行銷話術。對應 [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) — 客服平台用 15 主 region + 5 衛星 region 達 99.999%、架構成本約是 single-region 的 15 倍、但 B2B 客服合約要 5x9、這是合理投資。對應 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — 廣告計費 1 分鐘斷線可能損失幾百萬美金廣告收入、5x9 對應真實營收邊界。電信業 911 緊急通話必須 5x9 是更嚴格的法規層級。
- **99.9999%（核電、航空管制）**：6x9 不只是工程目標、是 *公共安全法規*。核電廠 SCADA 系統、空管雷達、軌道交通信號這類業務 30 秒 / 年的中斷會威脅生命、所以付得起跨多 cloud / 異地災備 / 全鏈路演練的成本。一般網路服務談 6x9 通常是過度設計。

**SLO 木桶效應**：99.999% 是 *系統整體* 數字、不是 DB 單獨。DNS、load balancer、application、DB、storage 任何一層 single-region 就破壞整體 SLO。傳統工程師常以為「DB 多 region 就好」、忽略 application 跑在 single-region 的話、application down = 整體 down。

要達成 5x9、要 *每一層* 都 multi-region active-active、且 *failover 流程能自動執行*（人類在事故當下做不到 5 分鐘內完成切換）。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的跨 region 部署、跟 [06 可靠性驗證模組](/backend/06-reliability/) 的 DR 演練。

**Region 成本曲線**：N 個 region 的成本約是 1 個 region 的 N 倍（DB + compute + storage 都要複製）、但業務收益不是線性。

- 1 region：覆蓋本國用戶
- 3 region（同 continent）：覆蓋整 continent、延遲 < 50ms
- 6 region（跨 continent）：覆蓋全球、延遲 100-200ms
- 15 region：每個用戶 < 50ms 接入（如 Genesys 模式）

從 6 region → 15 region 的成本是 2.5x、但用戶體驗改善（50ms 延遲）對 B2B 客服很關鍵、對 B2C 推薦系統幾乎無感。region 數量選擇要看 *業務模型對延遲的敏感度*、不是工程「越多越好」。

## Sharding 粒度跟業務一致性需求

distributed SQL 跟 single-cluster SQL 之間還有一層：**多個獨立 cluster + 應用層 sharding**。選哪個跟業務的一致性需求有關。

**Hyperscale / Aurora 同類設計**（storage / compute 分離）：

- AWS Aurora、Azure SQL Hyperscale、GCP AlloyDB、Spanner 都採類似工程哲學 — log-structured 分散式 storage + 獨立 compute scale
- storage 最高通常 100 TB（Hyperscale）、超過要 sharding
- compute 上限是 instance type（80 vCore 等）、超過要 sharding 或換 distributed SQL

對應 [9.C32 Clearent](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) — 5 億筆/年支付交易、用 Hyperscale 撐單一 cluster、沒拆 sharding 是因為支付業需要 *跨 merchant 對帳一致性*、共用 OLTP 比拆 cluster 划算。

**選 vendor 看生態、不看技術**：Hyperscale 跟 Aurora 工程哲學一致、選哪家取決於 application 已在哪個 cloud。AWS 客戶選 Aurora、Azure 客戶選 Hyperscale、GCP 客戶選 AlloyDB / Spanner。技術差異小、生態差異大（IAM 整合、observability tooling、計費綁定）。

**業務一致性需求決定 sharding 粒度**：

- **微服務各自 OLTP**（Netflix Aurora consolidation）：每個微服務有自己的 Aurora cluster、跨服務一致性靠 application 層 saga / outbox。適合服務間業務 *天然解耦*（用戶服務、訂單服務、商品服務各自 owned data）。Query path 上、跨服務查詢必須走 API 而非 SQL JOIN、要接受查多個服務多次往返；一致性 path 上、跨服務 transaction 用 saga + compensation、容忍中間態。
- **微服務共用 OLTP**（Clearent Hyperscale）：所有微服務共用一個大 cluster、跨服務一致性靠 DB transaction。適合業務 *天然耦合*（payment 跟 refund 跟 chargeback 必須在同一 transaction）。Query path 上、可以用 SQL JOIN 直接查跨服務資料、簡單；一致性 path 上、所有微服務共享一個 schema 演進邊界、schema migration 影響所有服務、要協調。
- **Sharding by tenant**（B2B SaaS）：每個 enterprise tenant 自己 cluster、適合 tenant 之間完全隔離、大客戶可能要求專屬 cluster。Query path 上、跨 tenant 查詢（例如平台級報表）要走 federated query 或 ETL 聚合、不能直接 join；運維 path 上、每個 tenant cluster 的容量規劃、backup、upgrade 都獨立、運維工時隨 tenant 數量線性成長。
- **Sharding by region**（受監管產業）：每個合規市場自己 cluster、合規驅動、不是性能驅動。對應 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 7 個市場各自獨立。

判讀重點：sharding 不是「擴容到不夠才做」、是「業務模型決定的初始設計」。等到 single cluster 撐不住才開始 shard、會踩進「跨 shard 一致性」的工程地雷區、修改成本遠高於初期設計成本。Managed DB（Aurora、Hyperscale）的容量上限是 *已知* 的、設計時就該知道未來何時觸發 sharding。對應 [1.1 高併發資料存取](/backend/01-database/high-concurrency-access/) 的 storage 層 replication 段 — Hyperscale / Aurora / Spanner 同類設計的容量上限同樣是 sharding 觸發點。

## 案例對照

| 案例                                                                                                                  | 教學重點                                          |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)                         | 10 億 req/sec 線性擴展、TrueTime 實作             |
| [9.C11 Minecraft Earth Cosmos DB](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)           | turnkey global distribution、5 consistency levels |
| [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)                 | 受監管金融跨市場、必須各自獨立 cluster            |
| [9.C21 ASOS Cosmos DB](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)                           | 全球零售 multi-region、Black Friday 持續高峰      |
| [9.C24 Genesys 99.999%](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)                  | 跨 15 region active-active 達 5 個 9 可用性       |
| [9.C32 Clearent Azure SQL Hyperscale](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) | 美國支付業、storage / compute 分離擴展            |

## 下一步路由

- 上游：[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)（single-region OLTP）
- 平行：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)（KV 全球分散）
- 下游：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)（含「預設 DB 治理 pattern」— 平台規模化階段的 OLTP 選型治理）
- 跨模組：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/slo-performance-budget/)、[0.2 State Storage Selection](/backend/00-service-selection/state-storage-selection/)、[7.11 Data Residency](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)

## 既建知識卡片

- [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/)
- [Latency Budget](/backend/knowledge-cards/latency-budget/)
- [Universal Scalability Law](/backend/knowledge-cards/universal-scalability-law/)
- [Saturation Point](/backend/knowledge-cards/saturation-point/)
