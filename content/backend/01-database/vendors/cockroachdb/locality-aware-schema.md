---
title: "CockroachDB Locality-Aware Schema：跨州合規 + 邏輯一個 cluster 的 region placement 策略"
date: 2026-05-27
description: "Hard Rock Digital 跨 8 州 sportsbook、用 AWS Outposts + region placement 把運算釘在州內、邏輯上仍是一個 CockroachDB cluster。本文走 REGIONAL BY ROW / REGIONAL BY TABLE / GLOBAL 三種 locality、Hard Rock 拓樸創新對比 Standard Chartered Aurora 7 cluster fleet、AWS Outposts 是合規工具不是 latency 工具的反直覺判讀"
weight: 60
tags: ["backend", "database", "cockroachdb", "distributed-sql", "locality", "multi-region", "data-residency", "deep-article"]
---

> 本文是 [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/) 的 implementation-layer deep article。Overview 已界定 CockroachDB 的 multi-region 能力、本文聚焦 *locality 配置怎麼解合規地理邊界 + 跨 boundary 業務邏輯需求* — 用 Hard Rock Digital 跨 8 州單一邏輯 cluster 作為 concrete framing。Replica placement 機制屬前置、見 [HLC + Raft consensus](../hlc-raft-consensus/)、survival goal 互動見 [survival goals](../survival-goals/)。

---

## 問題情境：Hard Rock 的跨州 sportsbook 拓樸創新

美國 sportsbook 受 *Wire Act* 規範、betting data 必須在下注州內處理 → 每個營運州都要有州內運算資源。傳統路徑是「每州一個獨立 silo、each silo 一個獨立 DB cluster」、合規上沒問題、但撞牆於三個業務需求：

- *跨州統一帳戶*：玩家在 NJ 跟 FL 兩州都有帳戶、登入要看到統一 portfolio
- *跨州 reporting*：總公司 BI / 財務 reporting 要橫跨所有州、不能 query N 個 cluster 後再合
- *跨州欺詐偵測*：同一張身分證在不同州 IP 同時下注 → 風控引擎要看 *cross-state aggregated* 資料

[9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/) 跨 8 州（AZ / IN / TN / FL / OH / IL / NJ / VA）用 AWS Outposts 把運算放進州內、但邏輯上仍是 *一個* CockroachDB cluster — region placement 配置決定哪些 range 釘在哪個 Outpost / AWS region。case 觀察段直接揭露「跨所有 region 一個 logical database」這個拓樸 fact。

讀者常問：

- 合規逼我每州一 cluster、但跨州帳戶 / 風控 / 欺詐偵測撞牆怎麼辦？
- `REGIONAL BY ROW` 跟 `REGIONAL BY TABLE` 怎麼選、`GLOBAL` 又在什麼場景？
- `GLOBAL` table 為什麼讀快但寫慢、預設為什麼不全部用？
- AWS Outposts 是 latency 工具還是合規工具？

對照 [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)：60+ multi-region cluster、最大 Gaming cluster 48-node 跨 4 region、locality 配置直接影響 cluster 規模治理。

對照 [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) Aurora 7 cluster fleet：銀行業跨國合規邊界、走的是「每市場獨立 Aurora cluster」路徑 — 跟 Hard Rock 邏輯一個 cluster 的拓樸完全不同。兩條路徑沒有對錯、trigger 條件不同（合規顆粒 × 跨 boundary 業務邏輯需求）。

## 核心機制：三種 table locality + row-level region 標記

### 三種 locality 模式

CockroachDB 用 [Range Sharding](/backend/knowledge-cards/range-sharding/) 把 multi-region table 抽象成三種 locality、配合 [Data Residency](/backend/knowledge-cards/data-residency/) 合規邊界決定 row 落在哪個 region：

| Locality            | Read 行為                                  | Write 行為                    | 適用場景                                  |
| ------------------- | ------------------------------------------ | ----------------------------- | ----------------------------------------- |
| `REGIONAL BY TABLE` | 本 region 快、其他 region 走 follower read | 本 region 快、其他 region 慢  | 整 table 服務單一 region（如：us-orders） |
| `REGIONAL BY ROW`   | 該 row 所在 region 快、其他 follower       | 該 row 所在 region 快、其他慢 | 用戶資料跟地理綁定（玩家 / 訂單 / 帳戶）  |
| `GLOBAL`            | 每 region local（快）                      | 跨 region quorum（慢）        | reference data（國碼、貨幣、規則表）      |

### REGIONAL BY ROW：每 row 帶 `crdb_region` 隱含欄位

`REGIONAL BY ROW` 是 Hard Rock 場景的主要選擇。每 row 自動帶一個 `crdb_region` 隱含欄位、根據這個欄位把 row 對應的 range 釘在指定 region：

```sql
ALTER DATABASE sportsbook PRIMARY REGION "us-east1-az";
ALTER DATABASE sportsbook ADD REGION "us-east1-nj";
ALTER DATABASE sportsbook ADD REGION "us-east1-fl";

ALTER TABLE bets SET LOCALITY REGIONAL BY ROW;

-- 寫入時指定 row 屬哪個 region
INSERT INTO bets (id, user_id, amount, crdb_region)
VALUES (..., ..., ..., 'us-east1-nj');
```

CockroachDB planner 自動感知 `crdb_region`、把 read / write 路由到 row 所在 region 的 leaseholder。application 不用手動配 shard key、不用 application 端路由邏輯 — 這是 distributed SQL 的「宣告式 locality」優勢。

### GLOBAL：每 region local read、跨 region sync write

`GLOBAL` table 適合 *reference data* — 變更少、read 頻繁、需要全球 local read latency：

- read：每 region 都有 leaseholder、本地 read p99 跟 single-region 一樣
- write：跨 region quorum、p99 100ms+

實務上 `GLOBAL` 只放國家代碼、貨幣表、規則 lookup 等 *變更頻率低* 的 reference data。把 high-write workload 設成 `GLOBAL` 是典型錯配（見失敗模式段）。

### Follower read：non-voting replica 提供本地 read

CockroachDB 區分 voting 跟 non-voting replica：

- voting replica 參與 Raft majority、決定 commit
- non-voting replica 不參與 commit、只 serve [Follower Read](/backend/knowledge-cards/follower-read/)

`REGIONAL BY ROW` + `SURVIVE REGION FAILURE` 配合時：row 所在 region 是 voting + [Leaseholder](/backend/knowledge-cards/leaseholder/)、其他 region 有 voting replica（survival 需要）+ non-voting replica（本地 follower read）。

Follower read 讀到的是 *closed timestamp* 之前的資料 — strong consistency 場景不能用（read-after-write 會 stale）、但 dashboard / reporting / 風控分析等 *容忍 stale* 場景大幅降低 cross-region latency。

### 配置語法跟驗證

```sql
-- 設 database 的 region
ALTER DATABASE mydb PRIMARY REGION "us-east1";
ALTER DATABASE mydb ADD REGION "europe-west1";

-- 設 table locality
ALTER TABLE users SET LOCALITY REGIONAL BY ROW;
ALTER TABLE country_codes SET LOCALITY GLOBAL;
ALTER TABLE orders_us SET LOCALITY REGIONAL BY TABLE IN "us-east1";

-- 驗證
SHOW LOCALITY FROM TABLE users;
SHOW RANGES FROM TABLE users;  -- 看 replica 分佈
EXPLAIN ANALYZE SELECT * FROM users WHERE id = 1;  -- 看 query plan 是否 local
```

對應 [stale read 卡](/backend/knowledge-cards/stale-read/)、[table partitioning 卡](/backend/knowledge-cards/table-partitioning/) 的具體機制實現。

## 操作流程：從合規 boundary 到 schema 配置

### 配置 multi-region database

第一步是把所有 region 加入 database：

```sql
-- 假設 cluster 已跨 8 個州（透過 AWS Outposts 在每州內）
ALTER DATABASE sportsbook PRIMARY REGION "us-east1-virginia";
ALTER DATABASE sportsbook ADD REGION "us-east1-nj";
ALTER DATABASE sportsbook ADD REGION "us-east1-fl";
ALTER DATABASE sportsbook ADD REGION "us-east1-az";
-- ...其他州
```

每個「region」對應一個 Outpost / AWS region 的 locality tag、CockroachDB Raft 根據 locality 自動分佈 replica。

### Table-level locality 配置

bet placement / settlement table 走 `REGIONAL BY ROW`（資料跟玩家所在州綁定）：

```sql
ALTER TABLE bets SET LOCALITY REGIONAL BY ROW;
ALTER TABLE settlements SET LOCALITY REGIONAL BY ROW;
```

account / user profile 跨州統一帳戶 — 玩家可能在多州下注、但 *主檔* 留 single region：

```sql
ALTER TABLE accounts SET LOCALITY REGIONAL BY TABLE IN "us-east1-virginia";
```

reference data（運動類別、賽事 metadata）— 全球變更少、每州都要快速 read：

```sql
ALTER TABLE sports_metadata SET LOCALITY GLOBAL;
```

### Application 端寫入

```sql
-- 顯式指定 row 所在 region（推薦、明確）
INSERT INTO bets (id, user_id, state, amount, crdb_region)
VALUES (..., ..., 'NJ', 100.00, 'us-east1-nj');

-- 或用 gateway_region() default（依 application 連到的 region）
INSERT INTO bets (id, user_id, state, amount)
VALUES (..., ..., 'NJ', 100.00);  -- crdb_region 自動填 gateway 端
```

`gateway_region()` 是便利但有風險的 default — 如果 application server 在 us-east1-fl 但 user 在 NJ 下注、row 會被放到 FL 而不是 NJ、違反 Wire Act 合規。Hard Rock 場景下顯式指定 `crdb_region` 是更安全的做法。

### Rollback 邊界

locality 變更即時生效、Raft 自動 rebalance — 無不可逆動作。但 rebalance 期間 cross-region traffic 暴增、p99 短期 spike。production 環境改 locality 應該選低流量時段、並監控 rebalance queue。

## 失敗模式

### 「拆獨立 cluster 解合規但破壞業務邏輯」反模式（Hard Rock 對比 Standard Chartered、F4.10）

直覺路徑是「合規要求資料留某地理邊界 → 每邊界開一個獨立 cluster」、合規上沒問題。但獨立 cluster 之間：

- 玩家統一帳戶撞牆 — 每 cluster 各自有 user table、跨 cluster query 麻煩
- 跨州 reporting 要 N 個 cluster + ETL pipeline
- 欺詐偵測要 *cross-state aggregated view* — 獨立 cluster 拼不出

Hard Rock 選擇 *邏輯一個 cluster + 物理跨州 Outpost placement* — 合規 boundary 用 region placement 表達、不是 cluster fragmentation。對比 Standard Chartered：

- **Standard Chartered Aurora 7 cluster fleet**：銀行業跨國合規邊界、*跨 cluster 業務邏輯需求弱*（每市場用戶獨立、跨境統一帳戶不是核心 driver）→ 用 fleet 拓樸吸收合規可行
- **Hard Rock Wire Act 跨州**：跨州統一帳戶 + 跨州 reporting + 欺詐偵測是 *核心業務需求* → 必須邏輯一個 cluster、用 locality + placement 吸收合規

兩條路徑沒有對錯、trigger 條件不同。判讀軸線：

- 合規顆粒（跨國 vs 跨州 vs 跨 AZ）
- 跨 boundary 業務邏輯需求強度（強 → CockroachDB locality / 弱 → 拆獨立 cluster 可行）
- 團隊運維能力（CockroachDB 邏輯一個 cluster vs Aurora 多 cluster fleet 的人月成本）

### 「Outposts 是 latency 工具」動機誤判（F4.13、case 反直覺判讀）

AWS Outposts 主要為「資料留某地理邊界」存在、latency 改善是 *副作用*。Hard Rock 策略段 2 明確警告：「決策時先看合規驅動力、latency 改善列為 bonus」。

若把 Outposts 當跨州 latency 改善工具、會在沒合規驅動的場景過度投資 — Outposts 硬體成本 + 維運複雜度遠高於純 AWS region 部署。實務判讀：

- 有合規驅動（Wire Act / GDPR / 各州博彩牌照）→ Outposts 是合理投資
- 純 latency 優化 → 用 AWS Local Zones、用 CDN、用 edge cache、不要碰 Outposts
- 兩者並存 → Outposts 投資按 *合規* 計算、latency 改善是 ROI 加分項

### `GLOBAL` table write 太慢

`GLOBAL` table 每次 write 跨 region quorum、p99 100ms+。用在 high-write workload 是典型錯配 — 該用在 reference data（國家代碼、貨幣表、規則 lookup）。

判讀：

- write QPS < 10 + read QPS 跨 region 高 → `GLOBAL` 合理
- write QPS > 100 → 不要用 `GLOBAL`、改 `REGIONAL BY ROW` + 接受 cross-region read 偶爾走 follower

### `REGIONAL BY ROW` 但 row 沒設 `crdb_region`

application 寫入時忘了設 `crdb_region`、default 走 `gateway_region()` — application server 所在 region 變成 row 的 region。常見後果：

- application server 集中部署 → 所有 row 跑同一 region、locality 失效
- application server 跟 user 不同 region → 合規 violation（Wire Act 場景）

修法：顯式指定 `crdb_region`、把 user 的合規區域當業務欄位明確管理。

### Cross-region join 跑爆 latency

兩個 `REGIONAL BY ROW` table join、planner 要跨 region 拉資料、p99 暴漲。

修法：

- 兩個 table partition by *同樣* 的 key（如：user_id）、保證 join 對應 row 在同 region
- 不能保證 co-location 時、考慮用 follower read 接受 stale 資料
- query 重寫成多步：先在各 region 算 local 結果、application 端 merge

### Follower read 假設 strong consistency

non-voting replica 是 *closed timestamp* 之前的資料、read-after-write 場景仍會 stale。

修法：

- read-after-write critical（如：剛下注立刻顯示「下注成功」）→ 不能走 follower、要走 leaseholder
- dashboard / 分析 / reporting 容忍 stale → follower read 安全、大幅降 latency

### Data residency 違規

受監管州 / 國資料應留 boundary 內、但 application 從別 region 寫入 row、沒設 `crdb_region`、資料跑出 boundary、合規 violation（Wire Act / GDPR / 各州博彩牌照都有類似條款）。

修法（schema-level + application-level 雙保險）：

- schema：`REGIONAL BY ROW` + `crdb_region` 是 NOT NULL + CHECK constraint 限制可選值
- application：寫入前明確驗證 `crdb_region` 對應 user 所在合規區
- 監控：定期跑 `SELECT crdb_region, count(*) FROM bets GROUP BY crdb_region` 確認分佈符合預期

### Hard Rock 場景的組合配置（9.C41）

bet placement / settlement / account management 都需要跨州資料存取 + 州內合規 placement。Hard Rock 案例揭露的具體組合：

- `REGIONAL BY ROW` + `crdb_region` 標州別 + region placement pin Outpost
- account 跨州統一 → `REGIONAL BY TABLE` IN primary region、其他州走 follower read
- sports metadata → `GLOBAL`、reference data 全州 local read

這是滿足 Wire Act + 跨州業務邏輯的組合、不是唯一解、但揭露了 schema 設計的 *判讀軸* — 不是「locality 越強越好」、是「locality 對應業務 + 合規邊界」。

## 容量與觀測

### 必看 metric

- `Range locality distribution`：range 分佈跟 locality 配置是否一致
- `Cross-region query count`：cross-region query 數量、locality 失效訊號
- `Follower read rate`：follower read 命中率、降 latency 效果
- `Leaseholder distribution by region`：leaseholder 在 region 間是否均勻

### 容量公式

- cross-region traffic = `GLOBAL` table write QPS × region count
- `REGIONAL BY ROW` 跨 region read = follower read rate × QPS
- storage 用量 = base storage × replication factor × (voting + non-voting replica count)

### 容量上限

- region count：建議 ≤ 5（多 region 增加 quorum latency + 維運複雜度）
- `GLOBAL` table 數量：建議只放 reference data、總 row 數 < 10 萬
- single range 寫 throughput ~1000 QPS（通用估算、見 [HLC + Raft consensus](../hlc-raft-consensus/)）

### 回路徑

- [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 判斷 cross-region-bound vs CPU-bound
- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 上游合規 / latency 取捨

## 邊界與整合

### Sibling deep articles

- [survival goals](../survival-goals/)：locality + survival goal 一起決定 replica placement
- [transaction retry pattern](../transaction-retry-pattern/)：partition 降低 hot row contention 的 schema 路徑
- [HLC + Raft consensus](../hlc-raft-consensus/)：leaseholder 跟 locality 的關係

### 跟 Aurora Global Database 對照

Aurora 不支援 row-level locality — 跨 region 只能 cluster-per-region + async replication。CockroachDB 在一個 cluster 內可以 fine-grained locality、application 不需要管 cross-cluster 路由。Aurora Global Database 適合 *async DR* 場景、不適合 *跨 region 強一致 + row-level locality* 需求。

### 跟 Spanner interleaved tables 對照

Spanner 的 [Interleaved Table](/backend/knowledge-cards/interleaved-table/) 跟 CockroachDB 的 `REGIONAL BY ROW` 概念類似（parent-child row co-location）、語法不同。Spanner 在 GCP region 內 placement、無 Outposts 等效 — Hard Rock 場景下 Spanner 不能直接套用。

### Aurora DSQL / Spanner 對比

完整三家 distributed SQL 在 locality / multi-region placement 的取捨、見 [aurora-dsql-spanner-decision-tree](../aurora-dsql-spanner-decision-tree/)。

### 1.x 章節互引

- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 上游
- [stale read 卡](/backend/knowledge-cards/stale-read/)
- [table partitioning 卡](/backend/knowledge-cards/table-partitioning/)

### 何時不用本文

- single-region 部署、無 data residency 需求 → 用 default locality 即可
- 合規邊界 *禁止* 跨境 replica（如 Standard Chartered 模式）→ 拆 cluster-per-市場、不走本文 locality 路徑
- 純 latency 優化、無合規驅動 → 用 CDN / cache / Local Zones、不必動 schema

## 相關連結

- [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/)
- [9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)（concrete framing — 跨 8 州 + Outposts + 邏輯一個 cluster）
- [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（多 region locality 規模治理）
- [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)（fleet 拓樸對照、不同合規邊界）
- [stale read 卡](/backend/knowledge-cards/stale-read/) / [table partitioning 卡](/backend/knowledge-cards/table-partitioning/)
- 官方：[CockroachDB Multi-Region Capabilities](https://www.cockroachlabs.com/docs/stable/multiregion-overview.html) / [Table Localities](https://www.cockroachlabs.com/docs/stable/table-localities.html) / [Follower Reads](https://www.cockroachlabs.com/docs/stable/follower-reads.html)
