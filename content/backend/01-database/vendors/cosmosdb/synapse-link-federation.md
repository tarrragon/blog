---
title: "Cosmos DB ↔ Azure Synapse Link：analytical store、HTAP federation、何時把分析 workload 從 OLTP 分出去"
date: 2026-06-02
description: "Cosmos DB Azure Synapse Link 的工程展開：column-oriented analytical store 自動同步、HTAP federation 讓分析 query 不打 OLTP transactional store、no-ETL 對 RU 的隔離、何時把分析 workload 從 Cosmos OLTP 分出去 vs 何時 federate 到專用 OLAP — 從 Microsoft 365 analytics 切入"
weight: 75
tags: ["backend", "database", "cosmosdb", "synapse-link", "federation", "htap", "deep-article"]
---

本文是 [Cosmos DB](/backend/01-database/vendors/cosmosdb/) overview 的 deep article、寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。Azure Synapse Link 把 Cosmos DB 的交易型資料自動同步到一個 column-oriented 的 analytical store、讓 Synapse（或其他 analytics engine）直接查分析資料、而 *不消耗 OLTP 的 RU、不打 transactional store*。它是一種 [federation](/backend/knowledge-cards/federation/) — 同一份資料的 OLTP 與 OLAP 存取被分到兩個各自最佳化的 store、由平台保持同步。本文先講 analytical store 與 HTAP federation 的精確語義、再進啟用流程、最後拆「何時把分析 workload 分出去、何時 federate 到專用 OLAP」的判準。

Case anchor 是 [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — Microsoft 自家把使用分析平台建在 Cosmos DB 上、planet-scale 全球分散式分析。case 自承沒揭露具體 throughput / latency / cost 數字、也沒明說用了 Synapse Link、本文只取「analytics workload 建在 Cosmos 上」這個情境 anchor、機制以 Azure vendor 規格與 HTAP / federation 通用工程展開。

## 問題情境

典型觸發場景：交易資料在 Cosmos DB、business 想跑分析 — 跨日期彙總、跨 partition 聚合、ad-hoc 報表、餵 ML。直接在 Cosmos OLTP container 上跑這些 query 有兩個問題：一是 NoSQL query 引擎不擅長大範圍掃描與聚合、二是 *分析 query 吃掉 OLTP 的 RU*、跑一個全表聚合可能把線上交易的 RU budget 耗光、造成 OLTP throttle（429）。團隊被迫在「分析準確性」與「OLTP 穩定性」之間二選一。

讀者徵兆：

- 「在 Cosmos OLTP container 跑分析 query、把線上交易的 RU 吃光、OLTP 開始 429」
- 「想做 analytics 但不想自己搭 ETL pipeline 把資料抽到 data warehouse」
- 「分析資料可以晚幾分鐘、但不想為了分析犧牲 OLTP 容量」
- 「什麼時候 Synapse Link 夠、什麼時候要把資料 ETL 到專用 OLAP（BigQuery / Snowflake）」

真實壓力：OLTP store 為點查與小範圍寫入最佳化、分析 query 為大範圍掃描與聚合最佳化、兩者對 storage layout 與資源的需求衝突。在同一個 store 同時服務兩者、不是 RU 互搶就是 query 形狀不對。Synapse Link 的價值是用 federation 把這個衝突拆開 — OLTP 與 OLAP 各有最佳化的 store、平台自動同步。

## 核心機制：analytical store + HTAP federation

Synapse Link 的核心是 Cosmos DB container 的 *analytical store*。

analytical store 是 column-oriented 的自動複本。在 container 啟用 analytical store 後、Cosmos DB 把 transactional store（row / document、為 OLTP 最佳化）的資料自動同步到一份 column-oriented 表示（為大範圍掃描與聚合最佳化）。兩份共存、同一份資料兩種 layout。

同步是 no-ETL、auto-sync。寫入 transactional store 後、平台在背景把變更同步到 analytical store（通常分鐘級延遲、時間敏感、查文件）。team 不寫 ETL、不維護 pipeline。

關鍵隔離：analytical store query *不消耗 OLTP 的 RU*。Synapse engine 查 analytical store、走的是 analytical store 的計費與資源、跟 transactional store 的 provisioned RU 分離。這是 federation 對 OLTP 的核心保護 — 分析跑再重也不會 throttle 線上交易。

這是 HTAP（Hybrid Transactional/Analytical Processing）的一種實現：同一資料源、OLTP 與 OLAP 共存、不需要把資料搬到獨立 warehouse 就能做近即時分析。對應 [federation](/backend/knowledge-cards/federation/) 的「同一份資料、多個各自最佳化的存取路徑」概念。

### 跟自己搭 Change Feed pipeline 的差別

[Change Feed](../change-feed-cdc/) 也能把資料同步到別處做分析、但那要自己寫 consumer、自己維護 target store、自己處理 schema 演進與 backfill。Synapse Link 是平台託管的 analytical store + auto-sync、省掉這整條 pipeline。判準：需求是「Cosmos 資料的近即時 column-oriented 分析」、Synapse Link 直接給；需求是「自訂 transform、餵特定下游、複雜 routing」、Change Feed 提供控制權但要自己搭。

## 操作流程

### 在 container 啟用 analytical store

```bash
# 建 container 時開 analytical store TTL（-1 = 跟 transactional 同壽命）
az cosmosdb sql container create \
  --account-name mycosmos --resource-group myrg \
  --database-name catalog --name orders \
  --partition-key-path "/customerId" \
  --analytical-storage-ttl -1
```

驗證：container 的 `analyticalStorageTtl` 已設；account 層的 Synapse Link feature 已啟用（account 設定、時間敏感、查文件）。注意 analytical store 通常需要 *建 container 時* 啟用、既有 container 的開啟支援度要查文件。

### 從 Synapse 查 analytical store

```sql
-- Synapse serverless SQL pool 直接查 analytical store、不打 OLTP
SELECT customerId, COUNT(*) AS orders, SUM(amount) AS revenue
FROM OPENROWSET(
    PROVIDER = 'CosmosDB',
    CONNECTION = 'Account=mycosmos;Database=catalog',
    OBJECT = 'orders',
    SERVER_CREDENTIAL = 'cosmos-cred'
) WITH (customerId varchar(64), amount float) AS orders
GROUP BY customerId;
```

驗證：query 跑大範圍聚合期間、Cosmos OLTP container 的 `NormalizedRUConsumption` *不受影響*（這是 federation 隔離生效的關鍵證據）。對照同樣 query 直接打 transactional store、會看到 RU 飆升甚至 429。

### 驗證同步延遲

寫一筆到 transactional store、隔一段時間在 analytical store 查到 — 量同步延遲（分鐘級）。驗證：延遲在業務可接受的分析新鮮度範圍內；要秒級新鮮度的分析、Synapse Link 不是對的工具。

### Rollback boundary

Synapse Link 是讀取側 federation、停用不影響 transactional store 的 OLTP。analytical store 是衍生複本、刪掉重建可重新同步（從 transactional store）。OLTP 寫入路徑完全不受 analytical store 啟用與否影響。

## 何時分出去、何時 federate 到專用 OLAP

這是本文主判讀段。Synapse Link 在「OLTP 資料要近即時分析、但不想犧牲 OLTP 容量也不想搭 ETL」的場景成立；它不是所有分析需求的答案。

用 Synapse Link（在 Cosmos federation 內做分析）的條件：

- 分析的主資料源就是 Cosmos OLTP container、且分析可接受分鐘級新鮮度
- 主要痛點是「分析 query 搶 OLTP 的 RU」— federation 的 RU 隔離直接解這個
- 不想維護 ETL pipeline — no-ETL auto-sync 省掉這條
- 分析 query 形狀適合 column-oriented 掃描聚合（多數 BI / 報表 / 彙總）

把分析 workload federate 到專用 OLAP（BigQuery / Snowflake / 專用 warehouse）的條件：

- 分析要 *跨多個資料源* join（Cosmos + 其他 DB + 外部資料）— 需要一個獨立的 warehouse 做集中、Synapse Link 只給 Cosmos 單源
- 分析是重型 data warehouse workload（複雜多表 join、長期歷史、大規模 transform）— 專用 OLAP 的引擎與成本模型更合適
- 已有成熟的 data platform（Snowflake / BigQuery / lakehouse）、Cosmos 只是其中一個 source — 把 Cosmos 資料用 Change Feed / connector 餵進既有 platform、不另起 Synapse Link

判讀句：Synapse Link 是 *Cosmos 單源、近即時、column-oriented* 分析的省力路徑；分析需求一旦跨源、變重型 warehouse、或已有集中 data platform、就 federate 到專用 OLAP。Cosmos DB overview 已標明「純 OLAP 分析」交給 Synapse / BigQuery / Snowflake — Synapse Link 是兩者之間的橋、不是把 Cosmos 變成 data warehouse。

## 失敗模式

### 不啟用 Synapse Link、直接在 OLTP 跑分析

team 在 OLTP container 直接跑全表聚合報表、分析 query 吃光 provisioned RU、線上交易 429。徵兆是「跑月報的時段、線上交易 latency 飆 / 出現 throttle」。修法是啟用 analytical store + Synapse Link、分析 query 改打 analytical store、RU 隔離後 OLTP 不再受影響；或退一步、把分析 query 移到離峰、但這只是緩解、根本解是 federation 隔離。

### 期待 analytical store 即時反映寫入

把 Synapse Link 當即時分析用、寫入後立刻在 analytical store 查、查不到剛寫的。analytical store 同步是分鐘級、不是即時。徵兆是「剛下的訂單在分析報表看不到」。修法是接受分析的分鐘級新鮮度、需要即時數字的場景（如即時庫存）走 OLTP 點查、不走 analytical store。

### 把 Synapse Link 當跨源 data warehouse

分析需要 join Cosmos 資料與其他系統的資料、期待 Synapse Link 解決、發現 analytical store 只有 Cosmos 單一 container / account 的資料。徵兆是「分析做到一半發現缺其他系統的維度資料、Synapse Link 帶不進來」。修法是跨源分析用獨立 warehouse（BigQuery / Snowflake / Synapse dedicated pool）集中、Cosmos 資料用 Synapse Link 或 Change Feed 餵進去當其中一個 source、不期待 Synapse Link 自己做跨源 join。

### 既有 container 才想開、發現要重建

analytical store 通常要建 container 時啟用、production 跑一陣子才想開、發現既有 container 的開啟有限制（時間敏感、查文件）、可能要新建 container + 遷資料。徵兆是「想開 analytical store 但介面不讓開 / 要重建」。修法是新 container 規劃時就評估未來是否需要分析、預先開 analytical store TTL（不用時成本影響有限）；既有 container 要開時、按文件評估是否需建新 container 遷移。

### Anti-recommendation：分析需求很輕不要起 federation

分析只是偶爾跑、資料量小、OLTP RU 有餘裕扛、且新鮮度要求即時 — 這種場景直接在 OLTP 上 query 或加少量 read 容量更簡單、不需要 analytical store 的額外儲存與 Synapse 的接入。Synapse Link 的價值在「分析會搶 OLTP 容量」或「不想搭 ETL」這兩個痛點明確時才成立；痛點不存在就引入 federation 是多一層東西要管。

## 容量與觀測

- 必看 metric：OLTP container 的 `NormalizedRUConsumption`（驗證分析 query 沒污染它）、analytical store 同步延遲、Synapse 端 query 的掃描量與成本
- 成本模型分離：analytical store 有獨立的 storage + 寫入計費、Synapse query 有自己的計費（serverless 按掃描量、dedicated 按 pool）— 跟 OLTP 的 RU 完全分開、不要混進 [ru-cost-model-sizing](../ru-cost-model-sizing/) 的 RU 公式、那篇主寫 transactional store 的 RU
- federation 的隔離證據：跑重型分析時 OLTP RU 平穩、就是 federation 生效；若 OLTP RU 仍隨分析波動、表示分析 query 其實打到了 transactional store、要檢查 query 是否真的走 analytical store
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：OLTP 容量與 analytical 容量分兩條 budget 規劃、這正是 federation 的容量規劃價值 — 兩個 workload 不再互相競爭資源
- Alert：analytical store 同步延遲異常增長、OLTP RU 出現非預期的分析時段波動（隔離失效）

## 邊界與整合

- Sibling deep articles：[change-feed-cdc](../change-feed-cdc/)（自訂 transform / 跨源 routing 用 Change Feed、近即時 Cosmos 單源分析用 Synapse Link）、[ru-cost-model-sizing](../ru-cost-model-sizing/)（analytical store 成本獨立於 OLTP RU、不混算）、[consistency-levels-engineering](../consistency-levels-engineering/)（analytical store 是分鐘級延遲的衍生複本、不適用 OLTP 的 consistency level 語義）
- federation 概念：[federation](/backend/knowledge-cards/federation/) — OLTP / OLAP 各自最佳化 store + 平台同步
- 跨源 / 重型分析的升級路由：Synapse dedicated pool / BigQuery / Snowflake — Cosmos DB overview「純 OLAP 分析」段已標明
- 回 overview：[Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) 的「跟 Azure Synapse Link 整合（OLTP / OLAP federation）」backlog 與「純 OLAP 分析」不適用場景
- Microsoft 365 analytics 主 anchor：[9.C30](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — analytics workload 建在 Cosmos 上的情境

## 相關連結

- [Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) — 本文是該頁尾 Synapse Link backlog 的深度展開
- [9.C30 Microsoft 365 case](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — Cosmos 上的全球分析平台情境 anchor
- [change-feed-cdc](../change-feed-cdc/) — 自訂 pipeline 的對照路徑
- [ru-cost-model-sizing](../ru-cost-model-sizing/) — OLTP RU 與 analytical 成本的分離
- [Federation 卡片](/backend/knowledge-cards/federation/) — OLTP / OLAP federation 概念基底
- 官方：[Azure Synapse Link for Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/synapse-link) / [Analytical store](https://learn.microsoft.com/azure/cosmos-db/analytical-store-introduction)
