---
title: "Spanner ↔ BigQuery federation：OLTP/OLAP 分工、federated query、Data Boost、何時把分析 workload 分出去"
date: 2026-06-02
description: "Spanner 是 OLTP、BigQuery 是 OLAP、federation 讓 BigQuery 直接查 Spanner 的活資料、Data Boost 讓分析查詢用獨立運算資源不搶 OLTP CPU。本文先定義 OLTP/OLAP 的責任分工、再走 external dataset federated query、Data Boost 的 workload 隔離機制、federation vs change-stream-to-BigQuery 兩條整合路線的取捨、以及何時該把分析 workload 完全分出去"
weight: 37
tags: ["backend", "database", "spanner", "global-sql", "bigquery", "federation", "olap", "deep-article"]
---

> 本文是 [Cloud Spanner](/backend/01-database/vendors/spanner/) overview 的 implementation-layer deep article、寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。Overview 已說明 Spanner 在全球 OLTP 譜系的定位、本文聚焦 *Spanner ↔ BigQuery federation* — OLTP 與 OLAP 的責任分工、以及讓分析查詢存取 OLTP 活資料的整合機制。

---

## 核心定位：OLTP 與 OLAP 是兩種不同的資料責任

Spanner ↔ BigQuery federation 的責任是讓「分析查詢」存取「交易資料」、同時把 OLTP 與 OLAP 兩種根本不同的工作負載分開、各自用適合的引擎與運算資源。Spanner 承擔交易責任 — 低延遲、高並發、行級讀寫、強一致;BigQuery 承擔分析責任 — 掃描大量資料、複雜聚合、欄式儲存、吞吐優先。federation 是讓這兩種責任協作的橋、不是讓一個引擎兼做兩件事。

把這條分工放最前面、是因為最常見的反模式是「在 OLTP 庫上直接跑分析查詢」。一個掃描全表做月度營收聚合的查詢、跑在 Spanner 上會吃掉本該服務交易的 CPU、把 OLTP 的 p99 latency 拖垮。federation 的價值是讓分析查詢「邏輯上看得到 OLTP 資料、物理上不搶 OLTP 資源」。理解這點、才能正確判斷哪些查詢該留在 Spanner、哪些該推到 BigQuery。

## 問題情境：分析查詢正在拖垮交易系統

federation 的價值、在「分析需求與交易需求共用同一個 OLTP 庫、互相干擾」的壓力下浮現。讀者徵兆：BI 團隊的 dashboard 每小時跑全表聚合、每次跑都讓 Spanner CPU spike、交易 p99 跟著抖;資料團隊想做 ad-hoc 分析、卻被告知「不要在 production Spanner 上跑大查詢」;為了避免干擾、團隊每天 batch export 一次到 BigQuery、但分析師抱怨資料延遲一天、看不到當天的活資料。

真實壓力場景：全球電商把訂單寫進 Spanner、營運團隊要即時看「過去一小時各區域的訂單趨勢」。這個查詢需要近即時的活資料（不能等隔日 batch）、又是掃描大量 row 的聚合（不該跑在 OLTP 上）。兩個需求拉扯：要新鮮就得查 Spanner 活資料、要不干擾交易就得分到分析引擎。federation + Data Boost 正是為了同時滿足這兩端 — 查 Spanner 的活資料、但用獨立運算資源。

Case anchor：[9.C10 Cloud Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 提供「Spanner 定位在 OLTP、analytics workload 交給 BigQuery」的分工 anchor — overview 已指出 Spanner 的不適用場景包含「需要 OLAP 分析能力」、替代是跟 BigQuery 整合。**dogfood 邊界明示**：9.C10 是 Google 內部 dogfood case、未展開 federation 實作細節;本文 federation 機制、Data Boost 行為均以 GCP vendor 規格 + 通用 OLTP/OLAP 工程展開、case 僅作分工壓力 anchor。

## 核心機制：external dataset federated query 與 Data Boost

federation 讓 BigQuery 把 Spanner database 註冊成 *external dataset*、之後用標準 BigQuery SQL 直接查 Spanner 的表、查詢在執行時把資料從 Spanner 拉進 BigQuery 的執行引擎。資料不複製、查的是 Spanner 當前狀態 — 這是 federation 跟「定期 export 一份 copy 到 BigQuery」的根本差異:federated query 看到的是活資料、export 看到的是某個時間點的快照。

```sql
-- BigQuery 端：透過 external connection 查 Spanner 活資料
SELECT region, COUNT(*) AS order_count, SUM(total) AS revenue
FROM EXTERNAL_QUERY(
  'my-project.us-central1.spanner-conn',
  'SELECT region, total FROM orders WHERE created_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)'
)
GROUP BY region;
```

### Data Boost：分析查詢的 workload 隔離

federated query 直接查 Spanner、預設仍消耗 Spanner instance 的運算資源 — 大分析查詢還是會干擾 OLTP。Data Boost 解的就是這層:它讓分析查詢用 *獨立的、按需配置的運算資源* 讀 Spanner 資料、不消耗服務交易的 instance CPU。Data Boost 讀的是同一份 storage、但用獨立 compute、所以「分析查詢看活資料」與「不干擾 OLTP」可以同時成立。

這是 federation 整套機制的關鍵 — 沒有 Data Boost、federated query 只是把查詢入口換到 BigQuery、底層仍搶 Spanner CPU;有了 Data Boost、workload 隔離才真正成立。Data Boost 適合 batch / ad-hoc 的大型分析讀取、按使用量計費、不需要預先 provision。

> **Scope warning**：external dataset / EXTERNAL_QUERY 的語法、Data Boost 的計費模型與資源隔離邊界屬 GCP 規格、逐版本演進。實作前 cross-verify [BigQuery Spanner federation](https://cloud.google.com/bigquery/docs/spanner-federated-queries) 與 [Data Boost 官方文件](https://cloud.google.com/spanner/docs/databoost/databoost-overview)、不可依本文當最終依據。

### 兩條整合路線：federation vs change-stream-to-BigQuery

把 Spanner 資料給 BigQuery 分析有兩條路線、取捨不同：

| 路線                         | 資料新鮮度       | 對 OLTP 影響                 | 適合場景                                 |
| ---------------------------- | ---------------- | ---------------------------- | ---------------------------------------- |
| Federated query + Data Boost | 查詢當下的活資料 | Data Boost 隔離、不搶 CPU    | ad-hoc 分析、即時 dashboard、低頻大查詢  |
| Change stream → BigQuery     | 近即時持續同步   | change stream 讀取耗少量 CPU | 高頻分析、需要在 BigQuery 落地的歷史資料 |

federation 是「需要時去查」、change stream 是「持續推一份到 BigQuery 落地」。federation 適合不需要把資料常駐 BigQuery、偶爾查活資料的場景;change stream（見 [change-streams-cdc](../change-streams-cdc/)）適合要在 BigQuery 累積歷史、做高頻或需要 BigQuery 原生效能的分析。兩者不互斥 — 即時 ad-hoc 用 federation、長期歷史分析用 change stream 落地。

## 操作流程：建立 connection、federated query、啟用 Data Boost

### Step 1：建立 BigQuery → Spanner external connection

在 BigQuery 建立指向 Spanner 的 external connection、設定 IAM 讓 BigQuery service account 有讀 Spanner 的權限。驗證：用 `EXTERNAL_QUERY` 跑一個簡單 `SELECT 1` 確認 connection 通、權限正確。

### Step 2：跑 federated query 並確認查的是活資料

跑一個帶時間條件的 federated query、在 Spanner 端寫一筆新資料、立即用 federated query 確認讀得到 — 驗證它查的是活資料、不是快照。這步確立 federation 的核心性質。

### Step 3：對大分析查詢啟用 Data Boost 並驗證隔離

對會掃描大量資料的分析查詢啟用 Data Boost、然後在跑分析查詢的同時觀測 Spanner OLTP 的 CPU 與 p99 latency。驗證點：開 Data Boost 後、大分析查詢執行期間 Spanner OLTP CPU 不應 spike、交易 p99 不應退化。這是 Data Boost 隔離是否生效的直接 evidence — 若 OLTP CPU 仍 spike、表示查詢沒走 Data Boost。

### Step 4：rollback boundary

federation 是讀取路徑、不改 Spanner 資料、rollback 成本低 — 停掉 federated query 即可、不影響 OLTP。決策的回退在「分析需求是否該用 federation」:若 federated query 即使開 Data Boost 仍無法滿足效能 / 成本、回退路徑是改用 change stream 把資料落地 BigQuery、用 BigQuery 原生效能查。

## 失敗模式：未隔離的查詢拖垮 OLTP、資料一致性誤解、過度依賴 federation

### Federated query 未開 Data Boost、拖垮 OLTP

團隊用 federated query 跑大分析查詢、但沒啟用 Data Boost、查詢直接吃 Spanner instance CPU、把交易 p99 拖垮。徵兆是「BI 查詢一跑、交易 latency 就抖」、Spanner CPU 在分析查詢期間 spike。修法是對所有大分析查詢啟用 Data Boost、把「federation = workload 隔離」這個假設明確驗證 — federation 本身不保證隔離、Data Boost 才保證。這個失敗的代價是它直接傷害 production 交易、不是只影響分析。

### 把 federated query 的快照當成跨系統強一致

federated query 讀的是 Spanner 的活資料、但這份分析結果是「查詢執行那一刻」的快照、不是跟某個 OLTP transaction 綁定的一致點。團隊若把 federated 分析結果當成「跟某筆交易嚴格對齊的數字」、會在[對帳](/backend/knowledge-cards/data-reconciliation/)場景出錯 — 分析查詢跨多張表掃描時、不同表讀到的時間點可能略有差異、不像單一 OLTP transaction 有 external consistency 的全序保證。

這個失敗的代價在它的隱蔽性:多數分析場景對「秒級的時間點差異」不敏感、所以平時看不出問題;但在「分析數字被當成財務對帳依據」的場景、這個鬆散的一致性會讓對帳對不上、且很難 debug — 因為資料「看起來都對」、只是時間點不嚴格對齊。修法是分清分析查詢的一致性需求:近似趨勢分析、federation 的快照足夠;需要跟交易嚴格對齊的對帳、要用 Spanner 的 read-only transaction 配明確 timestamp bound、或在 OLTP 側生成對帳快照、不靠跨表 federated 掃描拼湊。回退路徑是把「需要強一致對帳」的查詢移回 Spanner read-only transaction、不要硬用 federation 省事。

### 把所有分析都堆在 federation、不評估落地 BigQuery

團隊把所有分析都用 federated query 直查 Spanner、即使是高頻、重複、不需要活資料的查詢。federated query 每次都從 Spanner 拉資料、高頻重複查的成本與延遲都高於「資料已落地 BigQuery、用 BigQuery 原生欄式儲存查」。徵兆是同樣的分析查詢高頻跑、每次都付 federation 的拉取成本。**Anti-recommendation（何時不該用 federation）**:高頻、重複、可容忍近即時延遲的分析、用 change stream 把資料落地 BigQuery 更划算;federation 的適用範圍是低頻、ad-hoc、需要活資料的查詢。把高頻分析硬塞 federation 是用錯整合路線。

## 容量與觀測：OLTP CPU 隔離與 federation 拉取成本

federation 的容量壓力分兩端 — Spanner 側看「分析查詢有沒有被 Data Boost 隔離開」、BigQuery 側看「federated query 的拉取量與成本」。

```text
Spanner OLTP CPU during analytics   → Data Boost 隔離是否生效的關鍵指標
Spanner read capacity used by 分析   → 未隔離的 federated query 會吃這部分
BigQuery federated query bytes 處理量 → federation 拉取成本的計費基礎
分析查詢 latency vs OLTP p99 抖動相關性 → 隔離失效會讓兩者正相關
```

核心容量判讀是「分析查詢執行期間、OLTP CPU 與 p99 是否穩定」 — 若穩定、Data Boost 隔離生效;若兩者正相關、隔離失效、分析查詢正在消耗本該服務 OLTP 的資源。用 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 把「分析查詢時段」跟「OLTP p99」配成 evidence pair。容量規劃上、若走 federation + Data Boost、OLTP sizing 不需為分析加碼（Data Boost 用獨立 compute）;若 federated query 未隔離、OLTP sizing 要把分析尖峰算進去、回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)。

> **Scope warning**：Data Boost 的計費單位、federated query 的 bytes 計費、隔離的資源邊界屬 GCP 規格、隨版本演進、cross-verify 官方文件、非 9.C10 case 揭露的 production 數字。

## 邊界與整合：何時把分析 workload 完全分出去

### 何時用 federation + Data Boost

分析需要 Spanner 的活資料、查詢低頻或 ad-hoc、不想維護資料同步管線 — 這是 federation 的適用條件。Data Boost 讓它不干擾 OLTP、按需計費。即時營運 dashboard、臨時資料探索、不需要常駐 BigQuery 的分析都適合。

### 何時把分析完全分到 BigQuery（change stream 落地）

分析是高頻、重複、需要 BigQuery 原生欄式效能、或需要在 BigQuery 累積跨年歷史 — 把資料用 change stream 持續同步到 BigQuery 落地、分析直接查 BigQuery、不再回 Spanner。判準是:當分析 workload 穩定且高頻、落地的一次性同步成本會被「不再每次 federated 拉取」攤平。這是「分析 workload 完全分出去」的訊號 — OLTP 與 OLAP 不只查詢入口分開、連儲存都分開。

### 何時都不需要（分析量小）

若分析需求很小、Spanner 本身的 read capacity 有餘、偶爾在低峰跑個聚合不影響交易 — 不需要引入 federation 的額外設定。Anti-recommendation 的判準是:federation / Data Boost 的價值隨「分析與交易互相干擾的程度」上升;若兩者本來就不打架、保持簡單。

### Sibling deep articles 路由

- [change-streams-cdc](../change-streams-cdc/)：federation 的互補路線、高頻分析用 change stream 把資料落地 BigQuery、跟 federation 的「需要時去查」是兩種整合取捨
- [consistency-models-comparison](../consistency-models-comparison/)：federated query 的快照一致性鬆於 OLTP transaction 的 external consistency、對帳場景的差異對應該文的一致性等級定義
- [truetime-api-depth](../truetime-api-depth/)：需要嚴格時間點的分析要用 read-only transaction 配 timestamp bound、回該文的 staleness 選項

### 跟 knowledge card 的互引

- [federation](/backend/knowledge-cards/federation/) — 本文是這張卡在 Spanner ↔ BigQuery 的具體應用
- [distributed-sql](/backend/knowledge-cards/distributed-sql/) — Spanner 作為 OLTP distributed SQL、跟 BigQuery 的 OLAP 分工

### 跟其他章節的對照路由

- [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：OLTP / OLAP 分工後各自的 sizing 不同、Data Boost 讓分析 sizing 跟 OLTP 解耦
- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)：Spanner 定位在 OLTP、analytics 分到 BigQuery 是清楚的責任邊界
