---
title: "1.12 大規模 DB 遷移實戰"
date: 2026-05-13
description: "跨 DB 遷移的 dual-write、[shadow read](/backend/knowledge-cards/shadow-read/)、cutover、rollback 流程 — 從實戰案例提煉的工程做法"
weight: 12
tags: ["backend", "database", "migration"]
---

## 概念定位

DB 遷移是後端工程中 *風險最高的長期工作* 之一。一次失敗的遷移可能造成資料丟失、用戶體驗劣化、合規違約、團隊信心受挫。本章整理近 5 年公開的大規模 DB 遷移案例、提煉出可重用的工程流程。

跟 [1.6 database migration playbook](/backend/01-database/database-migration-playbook/) 的關係：1.6 是 *generic playbook*、本章針對「*跨 DB 種類*」遷移（PostgreSQL → Aurora、TiDB → DynamoDB、MongoDB → Cosmos DB）、規模較大、風險較高。

跟 [1.7 Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/) 的關係：1.7 處理 *同一 DB 內* 的 schema 演進、本章處理 *換 DB engine* 的遷移。兩者都用 evidence-based gate、但 stakes 不同。

讀完後讀者能回答：跨 DB 遷移該怎麼分階段、dual-write 怎麼設計、shadow read 怎麼驗證、cutover 怎麼安全進行、rollback window 訂多久。

## 遷移類型分類

DB 遷移不是單一概念、按 *變動範圍* 分四類、每類風險跟流程不同。

**Type 1：scale-up（換 instance）**：

- 例：m5.large → m5.4xlarge
- 變動：硬體規格、不變 schema、不變 DB engine
- 風險：低、通常 minutes downtime 即可
- 工具：vendor 提供 in-place scaling

**Type 2：schema migration**：

- 例：加欄位、加 index、改 data type
- 變動：schema 結構、不變 DB engine
- 風險：中、需要 expand-contract 模式
- 詳見 [1.7 Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)

**Type 3：cross-DB engine migration**：

- 例：PostgreSQL → Aurora、SQL Server → PostgreSQL、TiDB → DynamoDB
- 變動：DB engine、可能 schema、可能 query language
- 風險：高、可能需要應用層改寫、cutover 風險大
- 本章重點

**Type 4：cross-model migration**：

- 例：RDBMS → KV、Document → Graph
- 變動：資料模型、必須應用層大改寫
- 風險：極高、通常分 service 漸進遷移、不會一次切完
- 對應 [9.C20 Zomato TiDB → DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)

## 為什麼要做大規模 DB 遷移

不是所有遷移都值得做。理由要強過 *成本 + 風險*、不然不該開工。

**合理動機**：

- **舊系統規模上限**：[9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) TiDB 必須長期 over-provision 應付 spike、成本不划算 → 換 DynamoDB on-demand 後 50% 成本下降
- **舊系統運維成本**：[9.C9 Spotify](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/) 自管 Kafka 工程成本太高 → 換 managed Pub/Sub 釋放 SRE
- **舊系統失能**：[9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 多套 RDBMS（PostgreSQL、MySQL、Oracle）DBA 負擔重 → 統一到 Aurora、效能 +75% 成本 -28%
- **vendor 終止支援**：mongoDB 改授權、TiDB 改授權、Mesos 被棄、Oracle 升級費高
- **合規要求**：[9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 新市場上線、需要本地合規 cluster
- **新功能需求**：[9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) 需要 global distribution、原 MongoDB 達不到

**不合理動機（要警惕）**：

- 「新技術好酷」：fad-driven、通常會後悔
- 「vendor sales 推銷」：sales 利益跟你 ROI 不一致
- 「同行 X 也在遷」：人家的場景跟你不同
- 「主管要看到 transformation」：政治、不是工程

## 遷移階段流程

成熟的大規模 DB 遷移分五階段、每階段有明確 exit criteria。

### 階段 1：可行性評估（T-180 ~ T-90）

**輸出**：可行性報告、決定 go / no-go。

**評估項目**：

- workload 在新 DB 上是否真的能跑（不是 marketing、是實測 POC）
- 應用層改寫成本（哪些 query 需要改、哪些 ORM 需要換）
- 遷移時程預估（含 *合規審查* lead time、如金融業可能 3-12 個月）
- 成本對比（總成本曲線、不只當下 snapshot）
- 失敗代價（如果遷移失敗、business 影響多大）

**跨雲遷移特有 gap 分析**：當遷移橫跨雲廠商時、評估項目要加上 [0.19 雲端服務對照地圖](/backend/00-service-selection/cloud-vendor-capability-mapping/) 的「對應 ≠ 等價」差異維度：

- 一致性模型差異（如 DynamoDB eventual vs Cosmos DB 五級可選）
- failover 時間差異（vendor 文件 vs 實測長尾）
- 計價模型差異（per-request vs provisioned capacity 換算）
- 配額差異（partition 上限、batch size、throttling 行為）
- Data gravity / egress lock-in（PB 級資料的 egress fee 常是被低估的單筆最大成本）

跨雲遷移的失敗多數來自 0.19 對照表沒做完整 gap 分析、把「名稱對應」當「能力等價」。

**對應案例**：

- [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — POC 驗證 DynamoDB 撐得住、再決定遷移
- [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — MongoDB API 相容讓 POC 成本低、加速決策

### 階段 2：應用層相容性改造（T-90 ~ T-30）

**輸出**：應用層支援 *新舊 DB 雙寫*、可以隨時切換。

**改造項目**：

- Repository adapter 抽象化（[1.4 Repository Adapter](/backend/01-database/repository-adapter/)）
- 新增 *新 DB* 的 adapter 實作
- 配置「寫入 mode」：old only / dual-write / new only
- query 端「讀取 mode」：old / new / shadow（讀兩邊比對）
- error handling 兼容（不同 DB 的錯誤碼）

**API-compatible 遷移的優勢**：

- [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) MongoDB → Cosmos DB MongoDB API — 應用層幾乎不用改、只換 connection string
- Aurora PostgreSQL-compatible → 不改 SQL 跟 ORM
- 缺點：API 相容不等於行為完全相同、要 *特定 query pattern* 驗證

### 階段 3：Dual-write + shadow read 驗證（T-30 ~ T-7）

dual-write / shadow read / backfill 的 *generic 機制* 詳見 [1.6 database migration playbook](/backend/01-database/database-migration-playbook/) 跟 [1.7 schema migration rollout evidence](/backend/01-database/schema-migration-rollout-evidence/)（含 Dual-write divergence schema 詳細分類）；本章只強調 *跨 DB engine* 遷移的特殊取捨。

**輸出**：新 DB 已 *並行寫入*、跟舊 DB 結果一致。

**Dual-write 流程**：

1. 應用層同時寫入 old 跟 new DB
2. 用 old DB 結果回應用戶
3. log 兩邊寫入是否成功、有差異就 alert
4. backfill 之前的歷史資料到 new DB

**Shadow read 驗證**：

1. 應用層查 old DB 拿結果回用戶
2. *也* 查 new DB、比對結果是否一致
3. 不一致記錄到 audit log
4. 跑 N 天（建議 7-14 天）確認一致性高

**注意事項**：

- Dual-write 期間 *兩邊都要可寫*、寫失敗的 fallback 流程明確
- 新 DB 還沒承擔流量、容量規劃要 *提前 ramp up*、不要等 cutover 才發現容量不夠
- 監控指標：write success rate、cross-DB inconsistency rate、replication lag、performance metrics

對應案例：[9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — 遷移前用 dual-write 驗證 4 倍吞吐改善是真的、不是 POC marketing。

### 階段 4：Cutover（T-7 ~ T-0）

**輸出**：用戶流量切到 new DB、old DB 變成 fallback。

**Cutover 策略**：

**Big-bang cutover**：一次切全部流量

- 優點：簡單、不必維護 *跨 DB consistency*
- 缺點：風險集中、rollback 困難
- 適合：小規模、low-stakes

**Gradual cutover**（推薦）：分階段切

- T-7：1% 流量到 new DB、觀察 1 天
- T-6：5% → 觀察 1 天
- T-5：25% → 觀察 1 天
- T-3：50% → 觀察 2 天
- T-1：100%

**Reverse rollout**：某些工作負載先切（read-only first、再 write）

- T-7：所有 read 切到 new DB（write 還在 old）
- T-3：write 切到 new DB（read 已驗證）

### 階段 5：Rollback window + 清理（T+0 ~ T+30+）

**Rollback window**：cutover 後保持 *可隨時 rollback 回 old DB* 的狀態。

**Rollback window 設計**：

- 短期（T+7）：保持 dual-write、可以即時切回 old DB
- 中期（T+30）：保留 old DB read-only、需要 manual 切回但快
- 長期（T+90）：保留 old DB snapshot、disaster recovery 用
- 結束：徹底刪除 old DB（含 backup、ETL pipeline 改寫）

**Cleanup 工作**：

- 移除 dual-write code
- 移除 shadow read code
- 簡化 repository adapter（只保留 new DB）
- 文件更新（runbook、onboarding doc）
- decommission old DB（不立即砍、保留至少 90 天備援）

對應案例：[9.C9 Spotify Kafka → Pub/Sub](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/) — 大規模事件交付系統的 multi-month 漸進遷移、有明確 rollback path。

## API-compatible vs 應用層改寫

跨 DB 遷移的關鍵決策：要不要追求 *應用層零改動*。

**API-compatible 遷移**：

- 新 DB 提供舊 DB 的 wire protocol / API
- 應用層只換 connection string、不改 query
- 例：MongoDB → Cosmos DB（MongoDB API）、Cassandra → Cosmos DB（Cassandra API）、MySQL → Aurora（MySQL）

**優點**：

- 遷移成本低（不必改 application code）
- 風險低（不會引入 query bug）
- 時程快（不必等 application 改寫）

**缺點**：

- 行為可能不完全一致（subtle bug）
- 性能可能不是最佳（compat 層有 overhead）
- vendor lock-in 更深

**應用層改寫**：

- 換 query 風格、ORM、access pattern
- 例：PostgreSQL → DynamoDB（SQL → NoSQL access pattern）

**何時必須應用層改寫**：

- 跨 model（RDBMS → KV）
- 跨 query paradigm（SQL → MongoDB 風格）
- 想拿 native 性能 / 成本優勢

**對應案例**：

- [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — MongoDB API compat、應用層幾乎不改
- [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — 多套 RDBMS → Aurora、PostgreSQL / MySQL 相容、最小應用層改動
- [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — TiDB（SQL）→ DynamoDB（KV）、必須改 access pattern、不能 API compat

## 容量規劃在遷移中的角色

DB 遷移期間有特殊的容量挑戰、跟一般 capacity planning 不同。

**遷移期容量需求**：

- old DB 持續服務 production
- new DB 接 dual-write（額外負載）
- backfill historical data（額外負載）
- shadow read（讀兩倍）
- 應用層擴容（dual-write 邏輯吃 CPU）

**典型容量增加**：

- 應用層 +20-30%（dual-write、cross-DB logic、metric）
- new DB 必須 *提前 provision* 接 100% 流量
- 監控 / log 容量 +50%（要追蹤更多事件）

**對應 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)**：遷移期是「臨時 over-provisioning 期」、要算進 cost。遷移完才能 right-sizing。

**對應 [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)**：dual-write 跟 shadow read 是 production validation 的特殊形式、要按 9.10 的安全邊界設計。

## 案例對照

| 案例                                                                                             | 遷移類型                          | 教學重點                                  |
| ------------------------------------------------------------------------------------------------ | --------------------------------- | ----------------------------------------- |
| [9.C9 Spotify](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/)    | self-managed → managed            | 7500 萬用戶事件交付系統遷移、人力成本驅動 |
| [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)        | NewSQL → KV NoSQL                 | 對照 over-provisioning 成本、50% 帳單下降 |
| [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)            | 多套 RDBMS → 統一 Aurora          | DB consolidation 釋放 DBA、效能 +75%      |
| [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) | MongoDB → Cosmos DB（API compat） | API 相容遷移路徑、planet-scale 分析       |

## 遷移評估的成本曲線

遷移 ROI 評估常見錯誤是 *只看當下流量下的成本對照*、忽略未來流量曲線。決策時要算 12-24 個月的累積成本、不是 snapshot。

對應 [9.C20 Zomato TiDB → DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — Zomato 帳單系統「成本降 50%」是當下流量下的對照。如果未來流量繼續成長、DynamoDB on-demand 的單位成本可能比 TiDB 自管 cluster 高、達到某規模後 TiDB 反而更便宜。

**評估公式**：

```text
未來 N 個月累積成本 = sum(月流量 × 月單位成本)
```

各 DB 的「月單位成本 vs 流量」曲線形狀不同：

- **DynamoDB on-demand**：線性、按用量計費、單位成本固定
- **DynamoDB provisioned + reserved**：階梯、預訂量越大單價越低
- **自管 TiDB / PostgreSQL**：階梯 + 固定基線、低流量時單位成本高（基線分攤）、高流量時單位成本低
- **Aurora Serverless**：線性、但有最低 ACU 基線
- **Spanner**：節點數 × 單價、增量是 100 pu 一單位

**曲線交叉點是選型決策的關鍵**：DynamoDB on-demand 跟自管 PostgreSQL 在某個流量水位交叉、流量低於此值前者便宜（無基線成本）、高於此值後者便宜（基線分攤後單價低）。Aurora Serverless 跟 Aurora provisioned 也有類似交叉、波動大的 workload 在 Serverless 划算、穩定的在 provisioned 划算。Spanner 因為節點數階梯式增加、跨節點交叉點通常在 *每節點 70-80% 利用率* — 過了就要加節點、新節點利用率掉回 50% 是常態。判讀重點：選型不該只看 *當下流量點*、要看未來 12-24 月的流量曲線會跨過哪些交叉點、再決定哪種計費模式總成本最低。

**遷移 ROI 評估的維度**：

| 維度               | 應該算進去                                         |
| ------------------ | -------------------------------------------------- |
| Infra 成本         | 當下 + 預期成長下的累積、不是 snapshot             |
| 人力成本           | DBA、SRE、on-call 工時、跟 vendor 整合工時         |
| 機會成本           | 遷移期間不能做新功能的時間成本                     |
| Lock-in 成本       | 換 vendor 的退場成本、合約年限                     |
| 合規 lead time     | 受監管產業每市場 3-12 月審查、不算進來時程會崩     |
| Migration 本身成本 | dual-write infra、shadow read 雙倍負載、人力、風險 |

**機會成本延伸**：機會成本是遷移期間 *不能做新功能* 的時間。大型遷移通常綁住核心 team 6-12 個月、期間業務側看不到產品演進、可能流失市場機會。實務上要算「如果這 6 個月去做新產品、營收 / 競爭優勢值多少」、若超過遷移節省的 infra 成本、遷移不划算。

**Lock-in 成本延伸**：vendor lock-in 不是「不能換」、是「換的時候要付多少」。包含：(1) 應用層改寫成本（DynamoDB → Spanner 要改 access pattern）、(2) 合約終止 penalty（reserved capacity 提前解約罰款）、(3) 資料導出成本（雲商出口流量費）、(4) 人才再訓練（DBA 從 Aurora 轉 Spanner 需要時間）。選 vendor 時就要評估這四項、即使沒打算換、合約年限到時也要面對。

判讀重點：「遷移後成本降 50%」這種敘述只看 infra 成本、且只看當下。完整評估要看所有六個維度跨 12-24 月、決策才不會出「短期省、長期更貴」或「短期看似賺、合規卡 1 年」的事故。

## 合規審查 lead time 是時程主要拉力

受監管產業（金融、醫療、電信、政府）的 DB 遷移、*合規審查* 通常是時程主導因素、不是技術整合。

對應 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 跨 7 個受監管市場遷移到 Aurora、每個市場各自審查（中央銀行 / 金融監管機關 / 個資主管機關）、單一市場審查 3-12 個月、總時程是「市場數 × 平均審查月份」、不是「技術遷移月份」。

**合規 lead time 的常見項目**：

- 中央銀行核心系統變更審查（金融業）
- 個資主管機關的跨境傳輸審批（GDPR / 各國個資法）
- 醫療資料的隱私審查（HIPAA / 各國醫療法）
- 雲端服務商的合規認證對應（PCI-DSS、ISO 27001、SOC 2）
- 跨市場資料駐留限制（中國《數據安全法》、印度資料保護法、歐盟 GDPR）

**規劃含義**：

- 技術側 ready ≠ 可上線、合規簽核才是 cutover gate
- 合規審查通常 serial、不能 parallel（單一審查機關沒法平行處理多 case）
- 高風險變更（DB 換 vendor、cross-border）審查週期最長
- 跨市場部署、各市場各自審、不能用某市場結果代替

判讀重點：受監管產業的遷移計畫、預設技術側 50%、合規 50% 工時、不是「技術 90% / 合規 10%」。低估合規 lead time 會讓專案在最後關頭卡關、且無法用工程資源補。

## Benchmark 對照基準的解讀

遷移案例的「X% improvement」要追問 *跟什麼基準比*、否則容易誤導。

對應 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 「10x throughput」是 *vs 舊系統*、不是 *vs 競爭對手*。受監管銀行的舊系統通常是 1990s-2000s 的 mainframe 或自建 OLTP、性能本來就低、改善幅度大不代表絕對性能領先。

對應 [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — 「up to 75% improvement」是 *跨多個 workload 的最大改善幅度*、不是「每個 workload 都 +75%」。實際每個 workload 改善從 10% 到 75% 不等、平均可能 30-40%。

**benchmark 解讀的關鍵問題**（遷移情境專屬）：

- *vs 什麼基準*：跟舊系統比 vs 跟競爭對手比 vs 跟理論最佳比
- *哪個 workload*：是平均 vs 最快 vs 最慢
- *規模對照*：在多大流量下測的、自家業務規模類似嗎

讀 vendor 案例研究時、這三個遷移專屬維度都要對照、否則「75% 改善」可能變成「在某個 cherry-picked workload、跟舊系統比、規模跟自家不同」、實際搬過去未必有對應收益。

**規模對照延伸**：vendor 案例研究最容易誤判的維度。讀者要識別三個訊號才能判斷規模是否類似 — (1) *資料量*（vendor 揭露的是 GB 還是 PB？自家在哪個量級？）、(2) *QPS 分布*（vendor 是 sustained 還是 bursty？自家流量形狀是否類似？）、(3) *讀寫比*（vendor 案例是 write-heavy 還是 read-heavy？自家業務性質是否吻合？）。三個訊號至少要有兩個跟自家對齊、benchmark 數字才有參考價值。對應 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 案例的 18:1 讀寫比、跟一般電商的 5:1 完全不同、不能用同一份 benchmark 推論。

**Percentile 跟時間窗口維度** — 是更通用的容量數字判讀問題、詳見 [1.1 高併發資料存取的「讀峰值數字的工程細節」](/backend/01-database/high-concurrency-access/) 段（容量三口徑、p50/p99/p999 解讀）。遷移情境只需在這個基礎上加「vs 基準 / workload / 規模對照」三個遷移專屬問題。

## 「預設 DB」治理 pattern

大規模平台選 DB 的做法是建立「預設 DB」規則、新團隊用其他要 *justify*、逐案決定在這個規模行不通。這個治理 pattern 簡化 onboarding、降低 DB 種類太多的運維成本。

對應 [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) — Genesys Cloud 的 Chief Architect 明確說「Amazon DynamoDB is our primary data layer by default, and teams have to justify the use of something else」。對應 [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — 把多套 RDB 整合到 Aurora、降低 DB 種類就是降低運維 surface area。

**預設 DB 治理的工程含義**：

- 新團隊預設用 X、特殊需求才評估其他、減少 DB 評估的認知負擔
- DBA / SRE 知識集中、不必養多個 vendor 的專業
- 監控、backup、compliance 流程統一、運維成本下降
- 多個服務的 schema migration / capacity planning 可以共用 tooling

**選擇預設 DB 的判讀條件**：

- 平台規模夠大（10+ 微服務）、運維 surface area 是真實成本
- 業務需求大部分可以收斂到單一 DB（OLTP 90%、KV 10% 可以選 OLTP 為預設）
- vendor 提供完整能力組合（managed + multi-region + auto-scaling）

**預設 DB 對應**：

- AWS 生態大規模 OLTP → Aurora（Netflix）
- AWS 生態大規模 KV → DynamoDB（Genesys、Capcom、Disney+）
- Azure 生態 multi-model → Cosmos DB
- GCP 生態 OLTP → Spanner / AlloyDB

**同一雲廠商兩個預設 DB 怎麼選邊界**：AWS 生態同時有 Aurora（OLTP 預設）跟 DynamoDB（KV 預設）、不衝突、但要清楚兩者邊界。預設選 Aurora 的條件是「需要 SQL JOIN / ACID 跨表 transaction / 既有 ORM」、預設選 DynamoDB 的條件是「access pattern 已知且固定 / 預期跨 region 寫入 / surge 場景下 connection-based DB 撐不住」。這條邊界要寫進平台的 onboarding doc、否則新 team 會在「Aurora 還是 DynamoDB」之間反覆 review、抵消預設 DB 治理的價值。

判讀重點：小規模平台（< 5 微服務）不必預設 DB 治理、case-by-case 決定即可。隨著服務數量增加、DB 種類失控成為大規模平台的隱性成本、預設 DB 治理變成規模化階段的工程紀律。

## Vendor dogfood 是 selection signal

Vendor dogfood signal 是 vendor 自家 production-critical workload 對該服務的使用程度、反映 vendor 對自家服務的真實信任度。讀 vendor 案例研究時、這個訊號比 sales material 更可信、因為 vendor 自己賭身家。

對應 [9.C1 AWS Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) — Amazon Prime Day 用自家 DynamoDB + Aurora 撐 1.51 億 RPS + 500B txn。對應 [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — Google 自家 Ads、Play、Search 都用 Spanner。對應 [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — Microsoft 365 usage analytics 用自家 Cosmos DB。

**Dogfood 訊號為什麼重要**：

- vendor 自家賭身家、出問題自己第一個踩
- 內部 dogfood 通常比外部 customer earlier 用、bug 修得快
- vendor sales team 的「能撐 X」如果跟內部 dogfood 不一致、是 marketing
- 內部用量大、vendor 對該服務的工程投入比 marginal customer 多

**Dogfood 訊號的限制**：

- vendor 內部享有專屬資源配額跟內部成本機制、外部用戶在公開計費下、單位成本邊界不同
- vendor 內部享有深度 API 客製化跟特殊 SLA、外部用戶實際可取得的能力是公開版本
- vendor 自家業務的 workload pattern 反映 vendor 自己的業務需求、跟你業務的 workload 可能不同

判讀重點：dogfood 是必要訊號、不是充分訊號。看 vendor 自家用代表服務經過嚴格驗證；但「自家業務 vs 你業務」的相似度（資料量、QPS、讀寫比、一致性需求）才是 dogfood signal 是否能套用的判讀條件。

## 反模式

大規模 DB 遷移的常見錯誤：

- **沒做 POC 就 commit 遷移**：發現新 DB 撐不住某個 query pattern、時程崩
- **dual-write 沒 monitoring**：兩邊不一致沒被發現、cutover 後資料錯亂。divergence 該怎麼分類追蹤、詳見 [1.7 Dual-write divergence schema](/backend/01-database/schema-migration-rollout-evidence/)
- **shadow read 跑太短**：1-2 天就 cutover、long-tail bug 沒暴露
- **沒 rollback path**：cutover 後發現問題、回不去
- **app 跟 DB 一起遷**：兩個 risk source 疊加、追根因困難
- **忽略合規 lead time**：技術側 ready 但合規審查還在跑、整個 stuck
- **忽略 ETL pipeline**：production cutover 完、下游 BI / analytics 還在打 old DB

## 下一步路由

- 上游：[1.6 database migration playbook](/backend/01-database/database-migration-playbook/)（基本流程）/ [1.7 Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)（schema 演進）
- 平行：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) / [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)
- 跨模組：[9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)（dual-write、shadow）、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[6.11 Migration Safety](/backend/06-reliability/migration-safety/)、[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 跨 vendor 實戰深入：[Cosmos DB MongoDB API vs SQL API](/backend/01-database/vendors/cosmosdb/mongodb-api-vs-sql-api/)（document → multi-model）、[Aurora 從自管 PG / MySQL 遷入](/backend/01-database/vendors/aurora/migrate-from-self-managed-pg-mysql/)、[Spanner 從 Cloud SQL PG 遷入](/backend/01-database/vendors/spanner/migrate-from-cloud-sql-pg/)、[MongoDB 遷入 Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/)

## 既建知識卡片

- [Schema Migration](/backend/knowledge-cards/schema-migration/)
- [Expand / Contract](/backend/knowledge-cards/expand-contract/)
- [Dual Write](/backend/knowledge-cards/dual-write/)
- [Backfill](/backend/knowledge-cards/backfill/)
- [Cutover Window](/backend/knowledge-cards/cutover-window/)
- [Rollback Window](/backend/knowledge-cards/rollback-window/)
- [Shadow Traffic](/backend/knowledge-cards/shadow-traffic/)
- [Fallback Read](/backend/knowledge-cards/fallback-read/)
