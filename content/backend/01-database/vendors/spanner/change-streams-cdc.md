---
title: "Spanner Change Streams (CDC)：捕捉資料變更、watch partition、下游整合與 DynamoDB Streams 對照"
date: 2026-06-02
description: "Change Streams 是 Spanner 把 commit 後的 row mutation 變成可消費事件流的 CDC 機制、用 data change record 攜帶 commit timestamp 把外部一致性延伸到下游。本文走 change stream 物件模型、watch partition 的 child partition 切分、Dataflow / Pub/Sub 下游整合、retention 與 staleness 失敗模式、跟 DynamoDB Streams 的 partition / ordering / retention 對照"
weight: 34
tags: ["backend", "database", "spanner", "global-sql", "change-streams", "cdc", "deep-article"]
---

> 本文是 [Cloud Spanner](/backend/01-database/vendors/spanner/) overview 的 implementation-layer deep article、寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。Overview 已說明 Spanner 在全球 OLTP 譜系的定位、本文聚焦 *Change Streams* — Spanner 把 commit 後的 row mutation 變成下游可消費事件流的 [CDC](/backend/knowledge-cards/change-data-capture/) 機制。

---

## 問題情境：OLTP 的變更要餵給搜尋、快取、分析三個下游

Change Streams 的責任是把 Spanner 內已 commit 的 row mutation 變成有序、可重放、攜帶 commit timestamp 的事件流、讓搜尋索引、快取、分析倉儲三類下游不用反覆 full-table scan 就能跟上主資料庫。OLTP 主庫負責正確寫入、下游各自負責自己的 query shape、兩邊之間需要一條「只送變更、不送全表」的管線、這條管線就是 CDC 的職責。

讀者徵兆通常從這幾個地方浮現：搜尋團隊每 5 分鐘跑一次 full scan 把 orders 重灌進 Elasticsearch、Spanner CPU 被掃表打到 70%；快取層靠 TTL 過期被動失效、使用者看到舊價格;分析團隊想做近即時 dashboard、卻只有每日 batch export。共同壓力是「主庫的變更沒有一條乾淨的出口」、每個下游各自發明輪子去 poll 主庫。

真實壓力場景：全球電商把訂單寫進 Spanner multi-region instance、需要把每筆訂單狀態變更同時推給 (1) 搜尋索引更新庫存可售性、(2) Pub/Sub 通知履約系統、(3) BigQuery 做近即時營收儀表板。三個下游對延遲、順序、retention 的要求不同、但都需要從同一條變更流取得資料。

Case anchor：[9.C10 Cloud Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 提供「全球大規模 OLTP 寫入」的壓力 anchor — Google Ads / Play 計費的寫入量級說明為什麼下游不能靠 full scan 跟上。**dogfood 邊界明示**：9.C10 是 Google 內部 dogfood case、未展開 change streams 實作細節；本文 change stream 的物件模型、partition 行為與 retention 上限均來自 GCP vendor 規格、不是 9.C10 case 揭露。

## 核心機制：data change record、partition token、commit timestamp

Change Stream 是一個用 DDL 建立、綁定到特定 table / column 集合的 schema 物件、commit 後 Spanner 把對應 row 的 mutation 寫成 *data change record* 供消費。它跟「在 application 層自己寫 outbox table」最大的差異是：change record 由 Spanner 內部跟 transaction commit 綁定產生、攜帶該 mutation 的 commit timestamp、繼承 [external consistency](/backend/knowledge-cards/external-consistency/) 的全序性質、不需要 application 額外保證原子性。

建立語法是 DDL：

```sql
-- 監看整個資料庫
CREATE CHANGE STREAM everything_stream FOR ALL;

-- 只監看特定 table 的特定欄位
CREATE CHANGE STREAM orders_stream
  FOR orders(status, total_amount), inventory(available_qty)
  OPTIONS (
    retention_period = '7d',
    value_capture_type = 'NEW_AND_OLD_VALUES'
  );
```

`value_capture_type` 決定 record 攜帶多少資料、三個選項對下游的意義不同：

| value_capture_type   | record 攜帶內容              | 適合下游                                |
| -------------------- | ---------------------------- | --------------------------------------- |
| `OLD_AND_NEW_VALUES` | 變更前後完整 row             | 需要 diff / 審計 / 反向補償的下游       |
| `NEW_VALUES`         | 變更後的值 + key             | 搜尋索引、快取 upsert（只要最新狀態）   |
| `NEW_ROW`            | 變更後完整 row（含未改欄位） | 不想自己拼 row 的下游、犧牲 record 體積 |

### Data change record 的關鍵欄位

每筆 data change record 攜帶 commit timestamp、record sequence、transaction tag、mod type（INSERT / UPDATE / DELETE）、以及 primary key 與依 capture type 決定的 value payload。下游靠 commit timestamp + record sequence 在同一個 transaction 內重建變更順序、跨 transaction 則靠 commit timestamp 的全序。這條順序保證是 Spanner CDC 跟「自己 poll updated_at column」的根本差異：poll updated_at 在 clock skew 下會漏序、change stream 的順序由 TrueTime 撐住。

### Watch partition：change stream 的 partition 模型

Change stream 的讀取單位是 *partition*、不是整條流。Spanner 把 change stream 依底層 key range 切成多個 partition、每個 partition 用一個 *partition token* 標識、消費者對每個 token 各開一個 `read` 呼叫並行讀。當底層資料 split 或 merge（Spanner 自動 re-balance key range）、partition 會產生 *child partition* — 父 partition 的 record 讀到結束時回傳 child partition token、消費者要接著去讀 child token、才不會漏掉 split 後的變更。

這個 child partition 的接力機制是 change stream 消費的核心複雜度。手刻消費者必須維護一張 partition token 的 watermark 表、處理 parent 結束 → child 開始的交棒、保證每個 token 只被一個 worker 讀。多數團隊不該手刻這層、應走 Dataflow connector（下節）讓它代管 partition 生命週期。

> **Scope warning**：本節 data change record 欄位、value_capture_type 選項、child partition 接力語意均屬 GCP Spanner change streams 規格、實作前 cross-verify [Spanner change streams 官方文件](https://cloud.google.com/spanner/docs/change-streams)。retention_period、partition 切分行為隨版本演進、非 9.C10 case 揭露。

## 操作流程：建立 change stream 到 Dataflow 下游

### Step 1：建立 change stream 並驗證

用 DDL 建立 change stream 後、用 information schema 確認它存在、並用 metadata 查詢確認監看範圍正確。

```sql
CREATE CHANGE STREAM orders_stream
  FOR orders, inventory
  OPTIONS (retention_period = '7d');
```

驗證：查 `INFORMATION_SCHEMA.CHANGE_STREAMS` 確認 stream 已建立、查 `CHANGE_STREAM_TABLES` 確認監看的 table 集合符合預期。若監看範圍寫錯（漏了某 table）、下游會靜默漏掉那張表的變更、這是高代價的靜默失敗、必須在這步驗證。

### Step 2：選消費路徑 — Dataflow connector 為預設

消費 change stream 有三條路徑、對應不同的下游能力與運維成本：

| 路徑                                       | partition 管理           | 適合場景                                       |
| ------------------------------------------ | ------------------------ | ---------------------------------------------- |
| Dataflow + Apache Beam SpannerIO connector | connector 代管           | 串到 BigQuery / GCS / Pub/Sub、需 exactly-once |
| Pub/Sub via Dataflow template              | template 代管            | fan-out 給多個事件驅動下游                     |
| 直接用 client library 讀 partition         | 自己維護 token watermark | 客製化邏輯、能承擔 partition 生命週期工程      |

Dataflow connector 是預設路徑、因為它代管 partition token 的 split / merge 接力、提供 checkpoint 與 exactly-once 到下游 sink。

### Step 3：部署 Dataflow pipeline 並驗證 end-to-end

用官方 Spanner-to-BigQuery 或 Spanner-to-PubSub Dataflow template 部署。驗證 end-to-end：在 Spanner 寫一筆變更、量它多久出現在下游、確認 commit timestamp 在下游被保留、確認 INSERT / UPDATE / DELETE 三種 mod type 都被正確處理（DELETE 特別容易在下游被漏掉、要專門測）。

### Step 4：rollback boundary

Change stream 是可加可刪的 schema 物件、`DROP CHANGE STREAM orders_stream` 即停止捕捉、不影響主表寫入。rollback boundary 在「停掉 Dataflow pipeline + 標記下游資料為 stale」、不是「改主庫 schema」 — change stream 本身對 OLTP write path 的影響極小、刪除它不需要 cutover window。

## 失敗模式：retention 過期、下游慢於 retention、DELETE 漏處理

### Retention 窗口過期導致 partition 不可讀

change stream 的 record 只保留 retention_period（預設 1 天、上限數天、查官方文件確認當前上限）。若下游消費者停機超過 retention 窗口、過期 partition 的 record 被 GC、消費者重啟後讀到 partition token 已失效的錯誤、那段變更永久漏掉。徵兆是消費者重啟後報 partition not found、下游資料出現一段空洞。修法是 retention_period 設成大於「最壞情況下游停機 + 重啟趕上」的時間、並對 change stream 的 consumer lag 設告警、lag 接近 retention 一半就 page。

> **Scope warning**：retention_period 的預設值與上限屬 GCP 規格、隨版本變動、cross-verify 官方文件。本段 lag 告警閾值（retention 一半）是通用工程估算、不是 9.C10 case 揭露的數字。

### 下游消費吞吐慢於主庫寫入速率

主庫 write rate 持續高於下游消費速率、consumer lag 單調上升、最終撞 retention 窗口漏資料。這在全球大規模 OLTP 寫入下是真實壓力 — 對應 9.C10 揭露的 Google internal dogfood 寫入量級（**dogfood 邊界**：該量級是 Google 全使用者加總、不是單一 instance 配額）。修法是擴 Dataflow worker、確認 partition 數足夠讓消費並行、必要時把單一 change stream 依 table 拆成多條降低單條負載。判讀訊號是 Dataflow backlog metric 持續成長、不是偶發 spike。

### DELETE 變更在下游被漏處理

下游 pipeline 只處理 INSERT / UPDATE 的 upsert、忘了處理 DELETE 的 tombstone、導致下游索引 / 快取殘留已刪除的資料。徵兆是搜尋結果出現主庫已不存在的項目、對帳發現下游 row count 高於主庫。修法是 pipeline 顯式 handle mod type = DELETE、依 capture type 決定能否拿到 old values 來反向補償；若用 `NEW_VALUES` capture、DELETE record 只攜帶 key、下游必須靠 key 刪除、不能假設拿得到完整 old row。

### 把 change stream 當可靠 message queue 用

change stream 是 *變更捕捉*、不是 general-purpose message bus。團隊若把它當成「任意事件都塞進來」的 queue、會發現它只能攜帶 row mutation、不能攜帶 application 自定義事件、且 retention 比專用 message broker 短。**Anti-recommendation（何時不用）**：需要長期保留、任意 payload、複雜 routing 的事件流、用 Pub/Sub 或 Kafka 當 SSoT、change stream 只負責「資料庫變更」這一類來源；把 application 業務事件硬塞進 change stream 是把 CDC 機制誤用成 event bus。

## 容量與觀測：consumer lag 是核心健康訊號

Change stream 的容量壓力集中在「下游能不能跟上主庫寫入」、核心 metric 是 consumer lag 與 partition 並行度。

必看 metric：

```text
Dataflow data freshness / system lag   → 下游落後主庫 commit 的時間
Dataflow backlog bytes / elements      → 未消費的 record 積壓量
Spanner change stream partition count  → 並行讀取單位、隨底層 split 變化
Spanner CPU utilization                → change stream 讀取也消耗主 instance CPU
```

Change stream 的讀取消耗主 instance 的 CPU 與 read capacity、不是免費旁路。容量規劃要把「change stream 消費」當成額外 read workload 算進 instance sizing、回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)。用 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 把 consumer lag 跟 Spanner CPU 配成 evidence pair：lag 上升且 CPU 飽和、是 instance 容量不足；lag 上升但 CPU 有餘、是 Dataflow worker 不足。

Alert 建議：

| Metric                        | Warn               | Page               |
| ----------------------------- | ------------------ | ------------------ |
| Dataflow data freshness       | > retention 的 1/4 | > retention 的 1/2 |
| Dataflow backlog 成長趨勢     | 持續成長 30 分鐘   | 持續成長 2 小時    |
| Spanner CPU（含 stream 讀取） | > 65%              | > 80%              |

> **Scope warning**：上述閾值為通用工程估算、依各團隊 retention 設定與 SLA 調整、非 9.C10 case 揭露的 production 數字。

## 邊界與整合：跟 DynamoDB Streams 對照、何時不用 change streams

### 跟 DynamoDB Streams 的對照

Change Streams 跟 DynamoDB Streams 都是 managed CDC、但 partition 模型、ordering 範圍、retention 的設計取捨不同、選型時這三軸最關鍵。

| 軸             | Spanner Change Streams                               | DynamoDB Streams                                       |
| -------------- | ---------------------------------------------------- | ------------------------------------------------------ |
| Ordering 範圍  | commit timestamp 全序（繼承 external consistency）   | 每個 shard / partition key 內有序、跨 partition 無全序 |
| Partition 模型 | 隨底層 key range split / merge、child partition 接力 | 對應 DynamoDB partition、shard 隨 partition 變化       |
| Retention      | retention_period 可設（天級、查官方上限）            | 固定 24 小時                                           |
| 消費路徑       | Dataflow / Pub/Sub / client library                  | Lambda trigger / Kinesis Adapter                       |
| Payload 控制   | value_capture_type 三選                              | StreamViewType 四選（KEYS_ONLY / NEW / OLD / BOTH）    |

關鍵差異在 ordering：Spanner change stream 繼承 external consistency、跨 partition 的 record 可用 commit timestamp 排出全序;DynamoDB Streams 只保證單 partition key 內有序、跨 partition 重組需要下游自己處理。retention 上 DynamoDB Streams 固定 24 小時、Spanner 可設更長、對「下游可能長時間停機」的場景 Spanner 較有彈性。消費模型上 DynamoDB Streams 跟 Lambda 整合最順、Spanner 跟 Dataflow / BigQuery 生態整合最順。

> **Scope warning**：DynamoDB Streams 24 小時 retention 與 StreamViewType 屬 AWS 規格、Spanner retention 上限屬 GCP 規格、兩者均隨版本演進、cross-verify 各自官方文件。

### 何時不用 change streams

單純需要「下游讀到最新狀態、不在意中間每筆變更」、且主庫變更率低、定期 batch export 反而更簡單、不必引入 change stream + Dataflow 的運維成本。對延遲不敏感的分析、走 BigQuery federation 直接查 Spanner（見 sibling）比建 CDC 管線更省。Anti-recommendation 的判準是：若下游不需要「每一筆變更的順序」、只需要「定期最新快照」、CDC 是過度工程。

### Sibling deep articles 路由

- [bigquery-federation](../bigquery-federation/)：不想建 CDC 管線、直接 federated query 查 Spanner 的 OLAP 路徑、跟 change stream → BigQuery 是兩條互補的整合方式
- [truetime-api-depth](../truetime-api-depth/)：change stream 的 commit timestamp 全序來自 TrueTime、理解順序保證的物理基礎
- [consistency-models-comparison](../consistency-models-comparison/)：change stream 繼承 external consistency、跟 DynamoDB Streams 的 per-partition ordering 對照回 linearizability 定義

### 跟 knowledge card 的互引

- [change-data-capture](/backend/knowledge-cards/change-data-capture/) — 本文是這張卡的 Spanner 實作範例
- [external-consistency](/backend/knowledge-cards/external-consistency/) — change stream 的全序保證來源

### 跟 04 / 09 章節的互引

- [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)：consumer lag × Spanner CPU 的 evidence pair
- [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：change stream 讀取當額外 read workload 算進 sizing
