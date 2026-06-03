---
title: "Spanner Graph (2024)：property graph 能力、跟 relational 表共存、適用場景與邊界"
date: 2026-06-02
description: "Spanner Graph 是建在 Spanner relational 引擎上的 property graph 能力、用 GQL 查詢 node 與 edge、底層仍是 relational table、graph 跟 SQL 共用同一份資料與 transaction。本文走 graph 物件模型（node / edge table 映射）、跟 relational 共存的設計、GQL 查詢、graph schema 不可逆設計的失敗代價、何時用 graph、何時用純 relational 或專用 graph DB"
weight: 36
tags: ["backend", "database", "spanner", "global-sql", "spanner-graph", "property-graph", "gql", "deep-article"]
---

> 本文是 [Cloud Spanner](/backend/01-database/vendors/spanner/) overview 的 implementation-layer deep article、寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。Overview 已說明 Spanner 在全球 OLTP 譜系的定位、本文聚焦 *Spanner Graph*（2024 推出）— 建在 relational 引擎上的 property graph 能力、跟 SQL 表共用同一份資料與 transaction。

---

## 核心定位：graph 是 relational 表上的視圖、不是另一個資料庫

Spanner Graph 的責任是讓「實體之間的多跳關係查詢」用 property graph 模型（node、edge、property）表達、底層仍儲存在 Spanner 的 relational table、graph 與 SQL 共用同一份資料、同一個 transaction、同一套 external consistency。它不是在 Spanner 旁邊掛一個獨立的 graph database、是在既有 relational 表之上定義一層 graph 映射、讓同一份資料能同時被 SQL query 與 GQL graph query 存取。

把這條定位放最前面、是因為 graph database 常被想成「需要單獨的儲存引擎、單獨的資料同步管線」。Spanner Graph 的設計取捨相反：node table 跟 edge table 就是普通的 Spanner table、graph schema 定義它們之間的映射、查詢時引擎在 relational 儲存上執行圖遍歷。這帶來兩個直接後果 — graph 與 transactional 寫入天然強一致（同一份資料、同一個 commit）、不需要把資料從 OLTP 同步到專用 graph DB;但也意味著 graph 效能受 relational 引擎的特性約束、不是專用 graph engine 的記憶體圖結構。

## 問題情境：關係查詢在 SQL 裡變成難以維護的多層 self-JOIN

Graph 能力的價值、在「資料本質是關係網絡、但被迫用 relational JOIN 表達多跳查詢」的壓力下浮現。讀者徵兆：反詐欺團隊要查「跟某個可疑帳號在 3 跳內共用過裝置 / 地址 / 付款方式的所有帳號」、寫成 SQL 是 3-4 層 self-JOIN、query 既難寫又難優化;推薦團隊要查「買過 A 的人也買過什麼」的多跳關聯;權限團隊要查「使用者透過群組 / 角色繼承鏈能存取哪些資源」的傳遞閉包。這些查詢的共同形狀是「沿著關係邊走 N 跳」、用 JOIN 表達時跳數越多 SQL 越複雜、優化器越難處理。

真實壓力場景：金融反詐欺系統把交易、帳號、裝置、地址存在 Spanner、需要即時查可疑帳號的關係網絡;這份資料同時要支援交易的強一致寫入。傳統做法是把資料從 OLTP ETL 到專用 graph DB（Neo4j 等）、付出資料同步延遲 + 兩套系統的運維成本 + graph DB 上的資料不是強一致快照。Spanner Graph 讓「強一致的交易資料」與「圖遍歷查詢」在同一個系統、避開同步管線。

Case anchor：本主題在 case 庫覆蓋稀薄。9.C10 是 Google internal dogfood case、未展開 graph 能力、且不是 customer-facing 參考。本文 graph 物件模型、GQL 語意、relational 共存機制均以 GCP vendor 規格 + 通用 graph 工程展開、case 僅作「全球大規模 OLTP 之上要做關係查詢」的壓力 anchor。Spanner Graph 是 2024 推出的較新能力、所有能力 claim 屬時間敏感、實作前查官方文件。

## 核心機制：node table、edge table、graph schema 映射

Spanner Graph 用 *property graph* 模型 — node 代表實體（帳號、裝置）、edge 代表關係（共用、轉帳）、兩者都可帶 property。底層每個 node 類型對應一張 relational table、每個 edge 類型對應一張記錄「來源 PK → 目標 PK」的 relational table、graph schema 用 DDL 把這些表宣告成 node / edge。

```sql
-- 底層仍是普通 relational table
CREATE TABLE Account (
  id INT64 NOT NULL,
  risk_score FLOAT64,
) PRIMARY KEY (id);

CREATE TABLE AccountTransfersAccount (
  src_id INT64 NOT NULL,
  dst_id INT64 NOT NULL,
  amount NUMERIC,
) PRIMARY KEY (src_id, dst_id);

-- graph schema 把表映射成 node / edge
CREATE PROPERTY GRAPH FraudGraph
  NODE TABLES (Account)
  EDGE TABLES (
    AccountTransfersAccount
      SOURCE KEY (src_id) REFERENCES Account(id)
      DESTINATION KEY (dst_id) REFERENCES Account(id)
  );
```

關鍵是 edge table 的 PK 設計直接決定圖遍歷效能。edge table 通常用 `(src_id, dst_id)` 當 PK、讓「從某 node 出發的所有 out-edge」落在相鄰的 key range、遍歷時是一次 range scan 而非散落查詢。這個物理 layout 跟 [interleaved table](../schema-migration-interleaved-tables/) 的思路相通 — 把一起查的資料在 storage 上放近。

### GQL 查詢：用 pattern matching 表達遍歷

graph 查詢用 GQL（ISO graph query language）的 pattern matching 語法、把多跳遍歷寫成 path pattern、比多層 SQL JOIN 直觀。

```sql
-- 查跟某帳號 1-3 跳內有轉帳關係的高風險帳號
GRAPH FraudGraph
MATCH (a:Account {id: 12345})-[:AccountTransfersAccount]->{1,3}(b:Account)
WHERE b.risk_score > 0.8
RETURN b.id, b.risk_score;
```

`->{1,3}` 表達 1 到 3 跳的可變長度路徑 — 這在 SQL 裡需要 recursive CTE 或多個 self-JOIN、在 GQL 裡是一個 pattern。引擎把 pattern 編譯成在底層 relational 表上的遍歷計劃。

> **Scope warning**：Spanner Graph 是 2024 推出的能力、GQL 語法、支援的 pattern、graph schema DDL 均屬 GCP 規格且逐版本演進。本文語法為示意、實作前必須 cross-verify [Spanner Graph 官方文件](https://cloud.google.com/spanner/docs/graph/overview) 的當前語法與支援範圍、不可依本文當最終依據。

### graph 與 relational 共存的語意

同一份資料能同時被 SQL 與 GQL 查 — 對 Account 表的 SQL UPDATE 立即反映在 graph 查詢、因為它們是同一份 storage。寫入走標準 Spanner transaction、graph 查詢看到的是 external-consistent 的快照。這個共存是 Spanner Graph 跟「ETL 到專用 graph DB」最根本的差異：沒有同步延遲、graph 看到的就是 OLTP 的當前一致狀態。

## 操作流程：定義 graph、查詢、驗證遍歷效能

### Step 1：設計 node / edge table 與 PK layout

先設計底層 relational table、edge table 的 PK 用 `(src, dst)` 讓 out-edge 連續。這步是 graph 效能的決定性步驟、也是最難回退的步驟（見失敗模式）。驗證：對「最高頻的遍歷方向」確認 edge table PK 讓該方向的 out-edge 落在連續 key range。

### Step 2：建立 property graph schema

用 `CREATE PROPERTY GRAPH` 宣告 node / edge 映射。驗證：查 information schema 確認 graph 已建立、node / edge 映射符合預期、edge 的 source / destination key 正確 reference 到 node 的 PK。

### Step 3：跑代表性 GQL 查詢並量遍歷成本

用真實業務的代表性遍歷（例如反詐欺的 3 跳查詢）跑 GQL、用 query plan 確認遍歷走 range scan 而非 full scan、量 latency 與掃描的 row 數。驗證點：跳數增加時 latency 的成長曲線 — 圖查詢的成本對「每跳的扇出（fan-out）」非常敏感、高扇出的 node（super node、例如被百萬帳號連到的熱門裝置）會讓遍歷成本急遽放大。

### Step 4：rollback boundary

graph schema 本身可加可改（在相容範圍內）、`DROP PROPERTY GRAPH` 不刪底層 relational 資料 — graph 是視圖層、刪 graph schema 不影響 SQL 存取。真正難回退的是底層 edge table 的 PK 設計（見失敗模式）。所以 rollback boundary 分兩層：graph schema 層可逆、底層 table layout 層接近不可逆。

## 失敗模式：edge table layout 設計錯誤的高代價

graph 的失敗模式跟前述機制型文章不同 — 它的核心風險是「資料模型的物理設計錯誤、且代價不可逆」、所以這節用更完整的代價與回退敘事處理、不壓成兩句式。

### Edge table PK 方向選錯、最高頻遍歷變成 full scan

這是 graph 設計最高代價、最難回退的失敗。edge table 的 PK 決定哪個遍歷方向是連續 range scan、哪個是散落查詢。若團隊把 PK 設成 `(dst_id, src_id)`、但 99% 的查詢是「從 src 出發找 dst」、那最高頻的遍歷變成對整張 edge table 的 scan、隨資料量線性退化。

代價之所以高、是因為它不在上線時暴露 — 小資料量下 full scan 也快、效能崩塌在資料長到一定規模、流量打到 production 之後才浮現。徵兆是特定遍歷的 latency 隨 edge table 成長而單調惡化、query plan 顯示 full scan 而非 range scan、Spanner CPU 被掃描打滿。

回退路徑的代價是這個失敗的關鍵：edge table 的 PK 不能 in-place 變更、修正需要建一張新的 edge table（正確 PK 方向）、backfill 全部 edge、更新 graph schema 指向新表、驗證遍歷走 range scan、再 drop 舊表。對 100 億 edge 的圖、backfill 是數小時到數天的 long-running operation、期間要管 capacity 升幅、要保證 graph 查詢在切換期間的正確性。這不是 hotfix、是一次完整的 schema migration。所以這個失敗的真正教訓是「在 Step 1 設計階段就把最高頻遍歷方向定死」、而不是「上線後再優化」 — 設計階段花一天想清楚遍歷方向、勝過上線後花一週重建 edge table。

### Super node 讓遍歷扇出急遽放大

某些 node 的 degree（連出的 edge 數）極高 — 例如一個被百萬帳號共用的熱門 IP、一個被千萬使用者關注的明星帳號。多跳遍歷經過 super node 時、單跳就扇出百萬條 edge、查詢成本急遽放大、可能拖垮整個 instance。徵兆是「多數遍歷快、少數遍歷極慢」、慢的那些都經過已知的高 degree node。修法不是純技術 — 要在業務層決定如何處理 super node：限制遍歷的 degree（只取前 N 條 edge）、把 super node 的關係單獨建模、或在應用層對經過 super node 的查詢設上限。這個失敗的代價在「它讓 tail latency 不可預測」、容量規劃要把 super node 的扇出當成 worst-case。

### 把 graph 當專用 graph DB 的全功能替代

團隊把 Spanner Graph 當 Neo4j 用、期待專用 graph DB 的所有演算法（PageRank、community detection、複雜圖分析）與圖原生效能。Spanner Graph 的強項是「跟強一致 OLTP 共存的關係查詢」、不是「重度圖分析引擎」。徵兆是想跑的圖演算法不在支援範圍、或重度分析查詢效能不如專用引擎。**Anti-recommendation（何時不用）**：純圖分析、不需要跟 OLTP transaction 共用資料、需要豐富圖演算法庫的場景、用專用 graph DB 或圖分析框架;Spanner Graph 的定位是「OLTP 資料順便要做關係查詢」、不是「圖是核心工作負載」。

## 容量與觀測：遍歷扇出是核心容量訊號

graph 查詢的容量壓力不在「資料量」、在「遍歷的扇出與跳數」 — 同樣的資料量、低扇出的遍歷便宜、高扇出的急遽放大。核心觀測是 graph query 掃描的 row 數與 query plan 的遍歷形狀。

```text
GQL query 掃描的 row / edge 數    → 遍歷扇出的直接指標
query plan: range scan vs full scan → edge table PK layout 是否匹配遍歷方向
Spanner CPU during graph query    → 高扇出遍歷會打滿 CPU
特定遍歷的 p99 latency 隨資料成長  → edge layout 錯誤的早期訊號
```

容量規劃要把「最壞情況遍歷」（經過 super node 的高扇出多跳）當 worst-case 算進 sizing、不能只用平均遍歷成本、回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)。用 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 把「遍歷掃描 row 數」跟「Spanner CPU」配成 evidence pair：掃描 row 數突增且 CPU 飽和、是某個查詢撞到 super node 或 layout 退化。

> **Scope warning**：Spanner Graph 的具體效能特性、query plan 工具、graph 相關 metric 屬 2024 後的新能力規格、隨版本演進、cross-verify 官方文件、非 9.C10 case 揭露。

## 邊界與整合：何時用 graph、何時用純 relational 或專用 graph DB

### 選 Spanner Graph 的條件

資料已在 Spanner、本質是關係網絡、需要多跳遍歷查詢、且這份資料同時要支援強一致的 OLTP 寫入 — 這是 Spanner Graph 的適用條件。它的核心價值是「免去 OLTP → graph DB 的同步管線、graph 看到的就是強一致的當前資料」。反詐欺、權限傳遞、即時推薦這類「在交易資料上做關係查詢」的場景最適合。

### 何時用純 relational

關係查詢的跳數固定且淺（1-2 跳）、用標準 SQL JOIN 已足夠清晰、不值得引入 graph schema 的額外概念。graph 的價值隨跳數與遍歷複雜度上升、淺查詢用 relational 反而簡單。判準是：若查詢用 JOIN 寫起來不痛、就不需要 graph。

### 何時用專用 graph DB

純圖工作負載、需要豐富圖演算法（PageRank、最短路徑、社群偵測）、不需要跟 OLTP transaction 共用強一致資料 — 用專用 graph DB 或圖分析框架。Spanner Graph 不是要取代專用 graph engine、是要服務「OLTP 順便要關係查詢」的場景。把重度圖分析硬塞 Spanner Graph 是用錯工具。

### Sibling deep articles 路由

- [schema-migration-interleaved-tables](../schema-migration-interleaved-tables/)：edge table 的 PK layout 思路跟 interleaved table 相通、都是「把一起查的資料在 storage 上放近」、且 graph 的 edge layout 錯誤回退跟 schema migration 同代價
- [consistency-models-comparison](../consistency-models-comparison/)：graph 查詢繼承 external consistency、graph 看到的快照跟 OLTP 一致
- [bigquery-federation](../bigquery-federation/)：重度圖分析若超出 graph 即時查詢範圍、可考慮把資料分到分析層

### 跟 knowledge card 的互引

- [distributed-sql](/backend/knowledge-cards/distributed-sql/) — Spanner Graph 是 distributed SQL 引擎上的 property graph 層、繼承其分散式語意

### 跟其他 vendor / 章節的對照

- [DynamoDB vendor](/backend/01-database/vendors/dynamodb/)：DynamoDB 的 adjacency list 設計是另一種「在 KV 上做關係查詢」的路線、跟 Spanner Graph 的 native graph 是不同取捨
- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)：graph 是 Spanner 在 OLTP 之上擴展的查詢能力之一
