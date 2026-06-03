---
title: "CockroachDB Multi-region Table 配置：三種 table locality 的選擇與 latency / 一致性取捨"
date: 2026-06-02
description: "CockroachDB 把 multi-region table 抽象成 REGIONAL BY TABLE / REGIONAL BY ROW / GLOBAL 三種 locality、每種對 read / write latency 跟一致性付不同成本。本文走三種 locality 的判讀軸、survival goal 怎麼跟 locality 一起決定副本拓樸（機制本身 cross-link survival-goals）、配置與驗證流程、選錯要重配的高代價回退、容量觀測訊號"
weight: 70
tags: ["backend", "database", "cockroachdb", "distributed-sql", "multi-region", "table-locality", "deep-article"]
---

> 本文是 [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/) 的 implementation-layer deep article。寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。本文聚焦 *三種 table locality 怎麼選、選錯的 latency / 一致性後果與重配代價*。Schema 怎麼配合 locality 設計（合規 boundary、跨州業務邏輯、Outposts 拓樸）主寫於 [locality-aware schema](../locality-aware-schema/)、survival goal 的存活機制主寫於 [survival goals](../survival-goals/)、本文兩者都 cross-link、不重複展開。

---

## 問題情境：multi-region cluster 起來了、每張 table 該設哪種 locality

團隊把 CockroachDB 跨 region 拉起來、`ALTER DATABASE ... ADD REGION` 也跑完了，接下來面對的是逐張 table 的 locality 決策。這個決策的成本結構很不對稱：設對了，read / write 走本地 leaseholder、latency 貼著單區水準；設錯了，每次寫入或讀取都吃一趟跨 region round trip，p99 從個位數毫秒跳到上百毫秒。

multi-region table locality 是 *把「資料的地理歸屬」跟「讀寫路徑」綁在一起* 的宣告。CockroachDB 提供三種 locality，對應三種「資料屬於誰、誰要快」的業務形狀：

- `REGIONAL BY TABLE`：整張 table 歸屬單一 region，該 region 讀寫快、其他 region 慢。
- `REGIONAL BY ROW`：每一 row 各自歸屬一個 region，row 所在 region 讀寫快。
- `GLOBAL`：資料屬於所有 region，每個 region 本地讀都快，但寫入要跨 region 達成共識。

讀者進來最常卡的三題：

- 三種 locality 對應什麼業務形狀、判讀軸是什麼？
- `GLOBAL` 既然每區讀都快，為什麼不全部設 `GLOBAL`？
- 上線後發現 locality 設錯，重配的代價有多高、能不能無痛改？

這三題都不是語法問題，而是 *把業務的資料歸屬與讀寫熱點，翻譯成副本拓樸* 的設計決策。

問題情境最常見的 trigger：[9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) 的 60+ multi-region cluster、最大 Gaming cluster 48-node 跨 4 region。case 揭露一個反直覺判讀 — multi-region 的主要動機是 *region failure 0 downtime*、不是降 latency；跨 region quorum 物理上會 *增* 寫入 latency。這條判讀直接決定 table locality 怎麼設：當 multi-region 的目的是 survival 而非 latency，把高寫入 table 設成 `GLOBAL`（跨區同步寫）就是把成本花在錯的地方。

[9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/) 則提供 row-level 歸屬的 concrete framing：跨 8 州 sportsbook、bet 資料按下注州歸屬、邏輯上仍是一個 cluster。case 觀察段揭露「跨所有 region 一個 logical database」這個拓樸 fact — 也就是 row-level locality 撐起了「合規分州 placement + 單一邏輯 DB」的組合。Hard Rock 的合規驅動與 schema 設計細節在 [locality-aware schema](../locality-aware-schema/) 展開，本文只取「row-level 歸屬」這個 locality 選擇本身。

## 核心機制：三種 locality 的判讀軸 + survival goal 互動

三種 table locality 的差異，本質是 *leaseholder（讀寫入口）跟資料歸屬 region 之間的關係*。leaseholder 機制屬前置、見 [HLC + Raft consensus](../hlc-raft-consensus/)；本文聚焦三種 locality 把 leaseholder 放在哪、因此誰快誰慢。

### 判讀軸：資料歸屬的顆粒 × 讀寫熱點分佈

選 locality 的第一個判讀軸是 *資料歸屬的顆粒*：整張 table 屬於一個 region（table 級），還是每 row 各屬一個 region（row 級），還是屬於所有 region（global）。第二個判讀軸是 *讀寫熱點落在哪*：本地讀為主、本地寫為主、還是全球讀為主。

| Locality            | 資料歸屬顆粒           | Read 快的條件          | Write 快的條件             | 對應業務形狀                           |
| ------------------- | ---------------------- | ---------------------- | -------------------------- | -------------------------------------- |
| `REGIONAL BY TABLE` | 整張 table 一個 region | 從歸屬 region 讀       | 從歸屬 region 寫           | 整張表服務單一市場（例：日本訂單表）   |
| `REGIONAL BY ROW`   | 每 row 一個 region     | 從 row 歸屬 region 讀  | 從 row 歸屬 region 寫      | 資料跟用戶地理綁定（玩家、帳戶、訂單） |
| `GLOBAL`            | 所有 region 共有       | 任何 region 本地讀都快 | 沒有「快」的寫（跨區共識） | reference data（國碼、貨幣、規則表）   |

每一格的判讀都要回到該情境，不能只看表。

`REGIONAL BY TABLE` 適合 *整張表的讀寫熱點集中在單一 region* 的情況。例如一張只服務日本市場的訂單表，把整張表的 leaseholder 釘在 `asia-northeast1`，日本端的應用讀寫都走本地 leaseholder，跨區應用偶爾讀則走 follower read 接受 stale。判讀訊號：這張表的寫入請求是否 95% 以上來自同一 region。如果不是，table 級歸屬會讓多數寫入吃跨區延遲。

`REGIONAL BY ROW` 適合 *每一 row 跟某個地理位置強綁定、但整張表跨多 region* 的情況。玩家帳戶、訂單、下注紀錄都屬於這類 — 每筆資料屬於某個用戶所在 region，但整張表服務所有 region 的用戶。row 透過隱含的 `crdb_region` 欄位決定歸屬，leaseholder 跟著 row 走。判讀訊號：同一張表的不同 row，讀寫熱點是否分散在不同 region。是的話，row 級歸屬讓每個 row 都貼著自己的用戶。

`GLOBAL` 適合 *讀遠多於寫、且每個 region 都要本地快讀* 的 reference data。國家代碼、貨幣表、運動賽事 metadata 這類資料變更稀少、但每個 region 的每次查詢都要用到。`GLOBAL` 讓每個 region 都能本地讀（讀到 closed timestamp 前的一致快照），代價是寫入要跨 region 達成共識。判讀訊號：寫入頻率是否低到「跨區寫的慢可以忽略」。

### 為什麼不全部設 GLOBAL

`GLOBAL` 的「每區讀都快」看似適合全表套用，但它對 *寫入* 收取跨 region quorum 的全額成本。`GLOBAL` table 的讀之所以能本地完成，是因為 CockroachDB 維護一個全球同步的 closed timestamp，讓每個 region 都能安全地本地讀稍早的快照；維護這個 timestamp 的代價是每次寫入都要跟所有 region 協調。

> **Scope warning**：`GLOBAL` table 的跨 region 寫入 p99、`REGIONAL BY ROW` 的本地寫入 p99、closed timestamp 的傳播間隔等具體數字，屬 vendor 規格與部署拓樸（region 距離、replica 數）的函數，三個 anchor case（DoorDash / Netflix / Hard Rock）都未揭露單一 table 的 latency 數字。本文只給量級判讀（本地 quorum vs 跨洲 quorum 差一到兩個數量級），具體值需 benchmark 自身拓樸並 cross-verify [CockroachDB Table Localities 文件](https://www.cockroachlabs.com/docs/stable/table-localities.html)。

因此「全部設 `GLOBAL`」會把所有寫入推上跨 region 路徑，等於放棄了 distributed SQL 把寫入分散到各 region 的核心優勢。`GLOBAL` 的正確用法是限定在 *變更頻率低、全球都要快讀* 的 reference data。

### Survival goal 怎麼跟 locality 一起決定副本拓樸

table locality 決定 *leaseholder 放哪、讀寫走哪條路徑*；survival goal 決定 *副本要分佈到幾個 failure domain 才能在故障後存活*。兩者一起決定每張 table 的副本拓樸。

survival goal 的存活機制本身（`SURVIVE ZONE FAILURE` vs `SURVIVE REGION FAILURE`、怎麼從業務 SLO 倒推、RTO / RPO 怎麼算）是 [survival goals](../survival-goals/) 的 SSoT，本文不重複展開。本文只取兩者 *互動* 的一個關鍵後果：把 `SURVIVE REGION FAILURE` 套到 `REGIONAL BY ROW` table 時，每個 region 的 row 不只需要本地 voting replica，還需要在 *其他 region* 放足夠的 voting replica 才能在整個 region 失效後仍達成 quorum。這會把跨 region 的 voting replica 數量推高，間接增加寫入要協調的範圍。

判讀路線：先依業務的資料歸屬與讀寫熱點選 locality（本文），再依業務的 region failure 容忍度選 survival goal（[survival goals](../survival-goals/)），兩者疊加後才得到最終副本拓樸與 latency 結構。

## 操作流程：配置、驗證、每步檢查生效

### 第一步：確認 database 已加入所有 region

table locality 的前提是 database 已宣告 region。先確認 region 列表正確，再設 table locality。

```sql
-- 看 database 已有哪些 region、哪個是 primary
SHOW REGIONS FROM DATABASE mydb;
```

驗證點：輸出的 region 數量與名稱要對齊實際部署的 region。少一個 region，後面把 table 設成該 region 的 `REGIONAL BY TABLE` 會直接報錯。

### 第二步：依判讀軸設定每張 table 的 locality

```sql
-- 整張表服務單一市場
ALTER TABLE orders_jp SET LOCALITY REGIONAL BY TABLE IN "asia-northeast1";

-- 資料跟用戶地理綁定
ALTER TABLE accounts SET LOCALITY REGIONAL BY ROW;

-- 低寫入、全球本地讀的 reference data
ALTER TABLE currency_codes SET LOCALITY GLOBAL;
```

驗證點：

```sql
-- 確認每張 table 的 locality 設定符合預期
SHOW CREATE TABLE accounts;   -- locality 子句會出現在輸出尾段
```

### 第三步：驗證讀寫路徑真的走本地

設了 locality 不代表查詢真的走本地路徑 — 寫入時 row 的 `crdb_region` 沒設對、或 query 沒帶上對應條件，仍會跨區。用 `EXPLAIN ANALYZE` 看實際 plan。

```sql
-- 看 query 是否在 row 歸屬 region 本地完成、有沒有跨 region 拉資料
EXPLAIN ANALYZE SELECT * FROM accounts WHERE id = $1;
```

驗證點：plan 中不應出現大量跨 region 的 distributed scan；`REGIONAL BY ROW` 的點查應落在 row 歸屬 region 的單一 leaseholder。

### 第四步：驗證副本分佈符合 locality + survival goal

```sql
-- 看每張 table 的 range 副本實際分佈在哪些 region
SHOW RANGES FROM TABLE accounts;
```

驗證點：副本分佈要同時滿足 locality（leaseholder 在歸屬 region）跟 survival goal（跨足夠 failure domain）。兩者衝突時，CockroachDB 以 survival goal 為硬約束調整副本數，這會反過來影響 latency — 對應 [survival goals](../survival-goals/) 的 latency 暴漲失敗模式。

## 失敗模式：locality 選錯的高代價回退

### `GLOBAL` 套到高寫入 table

把高寫入 table（訂單、下注、status 變更）設成 `GLOBAL`，每筆寫入都跨 region 共識，寫入 p99 結構性暴漲、寫入吞吐被跨區協調卡死。徵兆：CockroachDB Console 的跨 region network traffic 隨寫入量線性成長、寫入 p99 跟 region 距離正相關。

修法：把 table 改成 `REGIONAL BY ROW`（按用戶歸屬）或 `REGIONAL BY TABLE`（按市場歸屬）。

Anti-recommendation：reference data 之外的任何 table，預設都不要設 `GLOBAL`。`GLOBAL` 的判準是「寫入頻率低到跨區寫的慢可以忽略」，高寫入 workload 直接排除。

### `REGIONAL BY ROW` 但 row 沒帶正確 `crdb_region`

`REGIONAL BY ROW` 靠 `crdb_region` 決定 row 歸屬。寫入時沒顯式指定，default 走 `gateway_region()` — application server 所在 region 變成 row 歸屬。後果是 row 被釘在 application server 那一區，而非用戶所在區，locality 形同失效（甚至在合規場景違反 data residency，見 [locality-aware schema](../locality-aware-schema/)）。

修法：寫入時顯式指定 `crdb_region` 為用戶所在 region，並用 NOT NULL + CHECK constraint 把可選值鎖死。

### 選錯 locality 的重配代價（高代價不可逆情境的回退敘事）

table locality 選錯，重配本身語法上一行就能改（`ALTER TABLE ... SET LOCALITY ...`），但 *資料層面的重配代價高且有持續影響*，需要專屬回退計畫，不能比照「改個 config 重啟」對待。

重配 locality 會觸發 CockroachDB 把受影響 range 的副本搬到新拓樸對應的位置。把一張大 table 從 `GLOBAL` 改成 `REGIONAL BY ROW`，或從 single region 改成 row-level 跨多 region，意味著大量 range 要 rebalance — 期間跨 region network 流量暴增、leaseholder 反覆換手、p99 持續波動，table 越大、region 越多，rebalance 窗口越長。這不是秒級操作，而是隨資料量延長的背景過程。

更關鍵的是 `REGIONAL BY ROW` 的 `crdb_region` 是 *資料內容*，不只是 metadata。如果原本 row 的歸屬區設錯（例如全部落到 application server 那一區），重配 locality 不會自動把 row 搬到正確的用戶 region — 還要 *回填 `crdb_region` 欄位*，這是一次 data migration，不是 schema 變更。合規場景下，錯誤歸屬期間寫入的資料可能已經違反 data residency，回退時要連同合規證據一起盤點。

回退計畫的要素：

- 重配前估算受影響 range 數量與資料量，換算 rebalance 窗口，選低流量時段執行。
- 重配 `REGIONAL BY ROW` 時，分開處理「locality 宣告變更」與「`crdb_region` 回填」兩個動作，回填走分批 update 並監控 contention。
- 重配期間監控 rebalance queue 與跨 region traffic，設好「波動超過閾值就暫停 rebalance」的 tripwire。
- 合規場景下，先盤點錯誤歸屬期間的資料是否已違規，再決定回填策略與是否需要合規通報。

Anti-recommendation：不要在 production 高峰時段直接對大 table 改 locality 試效果。locality 是「上線前依業務形狀想清楚再設」的決策，不是「線上 A/B 試」的旋鈕。

### Cross-region join 跑爆 latency

兩張 `REGIONAL BY ROW` table join，若 join key 不保證兩邊 row 在同 region，planner 要跨 region 拉資料，p99 暴漲。

修法：兩張 table 用同一個歸屬 key（如 user_id），讓 join 對應的 row co-locate 在同 region；無法 co-locate 時，對容忍 stale 的查詢改走 follower read。

## 容量與觀測

### 必看 metric

- `Cross-region query count`：locality 是否生效的直接訊號，數值高代表查詢在跨區拉資料。
- `Leaseholder distribution by region`：leaseholder 是否落在資料歸屬 region，不均代表 locality 配置或 `crdb_region` 有偏。
- `Rebalance queue size`：locality 重配 / 副本搬遷期間的進度訊號，持續非零代表 rebalance 未收斂。
- `Cross-region network bytes`：`GLOBAL` table 寫入與 cross-region join 的成本訊號。

### 容量判讀

- `GLOBAL` table 的跨區寫入成本 ≈ 寫入 QPS × region 數，region 越多成本越高，所以 `GLOBAL` 只放低寫入 reference data。
- `REGIONAL BY ROW` 的跨區讀成本 ≈ 落到非歸屬 region 的讀 QPS，這部分若高，代表 `crdb_region` 歸屬與實際讀熱點不一致。
- region 數量建議維持精簡 — 每多一個 region，跨區協調與重配窗口都變長。

> **Scope warning**：region 數量上限建議、單 range 寫入吞吐量級、closed timestamp 傳播間隔等為 vendor 通用估算，非 case 揭露數字，容量規劃前以 [CockroachDB Multi-Region 文件](https://www.cockroachlabs.com/docs/stable/multiregion-overview.html) cross-verify 並 benchmark 自身拓樸。

### 回路徑

- [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 判斷 cross-region-bound vs CPU-bound。
- [9.6 容量規劃模型](/backend/09-performance-capacity/) region count × replica × latency budget。
- [latency budget 卡](/backend/knowledge-cards/latency-budget/) 跨 region quorum 預算。

## 邊界與整合

### Sibling deep articles

- [locality-aware schema](../locality-aware-schema/)：schema 怎麼配合 locality 設計 — 合規 boundary、跨州業務邏輯、Outposts 拓樸、`crdb_region` 作為合規欄位的管理。本文是「三種 locality 怎麼選」、該文是「選好後 schema 怎麼配合」，兩者互補不重複。
- [survival goals](../survival-goals/)：survival goal 的存活機制與 SLO 倒推 — 本文只取「survival goal 與 locality 互動如何影響副本拓樸」這一個交點，存活機制本身以該文為 SSoT。
- [HLC + Raft consensus](../hlc-raft-consensus/)：leaseholder 與 range 機制 — locality 決定 leaseholder 放哪，前置機制在該文。

### 跟 Spanner / Aurora 對照

Spanner 在 GCP region 內做 placement，無 AWS Outposts 等效；Aurora 不支援 row-level locality，跨 region 只能 cluster-per-region + async replication。完整三家 distributed SQL 在 multi-region placement 的選型對比，是 [aurora-dsql-spanner-decision-tree](../aurora-dsql-spanner-decision-tree/) 的 SSoT，本文不重展三方對比。

### 1.x 章節互引

- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 上游 latency / 一致性取捨。
- [stale read 卡](/backend/knowledge-cards/stale-read/)、[follower read 卡](/backend/knowledge-cards/follower-read/) — `GLOBAL` 與跨區讀的一致性語意。

### 何時不用本文

- single-region 部署：用 default locality 即可，三種 locality 在單區無差異。
- 從 PostgreSQL 遷到 CockroachDB 的整體流程：見 [PostgreSQL → CockroachDB migration](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/)，本文只處理遷移後的 table locality 配置。

## 相關連結

- [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/)
- [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（multi-region 動機是 survival 非 latency）
- [9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)（row-level 歸屬 + 單一邏輯 cluster）
- [distributed SQL 卡](/backend/knowledge-cards/distributed-sql/)
- 官方：[CockroachDB Table Localities](https://www.cockroachlabs.com/docs/stable/table-localities.html) / [Multi-Region Overview](https://www.cockroachlabs.com/docs/stable/multiregion-overview.html) / [Follower Reads](https://www.cockroachlabs.com/docs/stable/follower-reads.html)
