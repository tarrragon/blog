---
title: "CockroachDB Survival Goals：zone 級 vs region 級配置與業務 SLO 倒推流程"
date: 2026-05-27
description: "CockroachDB 用 SURVIVE ZONE FAILURE / SURVIVE REGION FAILURE 兩種 survival goal 宣告式控制 Raft replica 分佈、決定 RTO / RPO。本文走 Hard Rock Digital bet placement RPO=0 倒推流程、Netflix Gaming 48-node 跨 4 region 「為求 survival 而非 latency」的反直覺判讀、配置語法、寫入 latency 暴漲跟 cost 暴漲兩條失敗模式、合規邊界對比"
weight: 40
tags: ["backend", "database", "cockroachdb", "distributed-sql", "survival-goals", "rto", "rpo", "deep-article"]
---

> 本文整理 CockroachDB 的 survival goal 怎麼從業務 SLO 倒推、以及為什麼跨 region 配置換到的是 region 失效時不停服而不是更低的延遲。Raft replica 的分佈機制是前置知識，見 [HLC + Raft consensus](../hlc-raft-consensus/)。

---

## Multi-region 上線前的兩個錯誤期待

multi-region CockroachDB cluster 上線時、團隊最常踩的兩個錯誤期待：

- *「default 配置應該就好、上線後再說」*：default 是 `SURVIVE ZONE FAILURE`，voting replica 全部放在 database 的 primary region，primary region 一失效、這個 database 的寫入就停擺，客訴湧入才發現要重新配
- *「跨 region 應該會讓全球用戶都更快」*：跨 region quorum 物理上必然 *增* 寫入 latency、把 multi-region 動機誤判成 latency 優化會在 production 撞牆

讀者進來最常問：

- `SURVIVE ZONE FAILURE` 跟 `SURVIVE REGION FAILURE` 差在哪？
- 為什麼 region survival 的寫入 latency 比 zone survival 高？
- Default 配置是什麼、上線前該不該改？

要回答這三題、必須先把 survival goal 跟業務 SLO 的對應關係講清楚。

[Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/) 提供最 concrete 的 SLO 倒推路徑：sportsbook 中 *bet placement 不能 lose* — 玩家下注後系統 crash 沒紀錄、對博彩牌照是合規事故。CockroachDB Raft 3-replica + 跨 AZ + survival goal 配置是把這個業務不可丟事件翻譯成 DB 層保證。

[Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) 則提供反直覺判讀：60+ multi-region cluster 主要動機是 *region failure 0 downtime*、不是降 latency。Gaming cluster 48-node 跨 4 region 就是為了「region failover 不停服」、不是讓玩家延遲變低。

對照 [Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 走另一條路：銀行受監管市場資料 *不能跨境*、不可用 region survival、必須拆每市場獨立 Aurora cluster + 多 AZ 部署。這個 anti-recommendation 提醒「survival goal 不是越強越好、合規邊界優先於技術 HA 配置」。

## 核心機制：兩種 survival goal + replica placement

### 兩種宣告式配置

CockroachDB 把 HA 配置抽象成兩個 database-level 宣告：

- **`SURVIVE ZONE FAILURE`**（default）：失去 1 個 AZ 仍能寫入。replica 跨 AZ 分佈、但可能集中在同一個 region 內。對應 RTO ~ 數秒（Raft + [Leaseholder](/backend/knowledge-cards/leaseholder/) 自動 failover）、RPO = 0（已 commit 資料不丟）
- **`SURVIVE REGION FAILURE`**：失去 1 個整個 region 仍能寫入。voting replica 強制跨 region、需要至少 3 個 region。對應 RTO ~ 數秒、RPO = 0、但寫入 latency 因跨 region quorum 結構性增加

survival goal 是 *宣告式* 配置 — application 端不用手動指定 [Range Sharding](/backend/knowledge-cards/range-sharding/) 的 replica placement、Raft 根據 survival goal + locality 自動分佈、用 [Hybrid Logical Clock](/backend/knowledge-cards/hybrid-logical-clock/) 串接 commit ordering。對比通用 HA 設計（如 PostgreSQL streaming + Patroni manual failover）、CockroachDB 把這層邏輯壓進系統內。

### Voting vs non-voting replica

region survival 模式下、CockroachDB 區分兩種 replica：

- **Voting replica**：參與 Raft majority 決策、commit 必須等 voting majority ack。region survival 下 voting replica 強制跨 region — 這就是 [Cross-Region Quorum](/backend/knowledge-cards/cross-region-quorum/) 拓樸、commit latency 受跨洲 RTT 物理硬限主導
- **Non-voting replica**：只用來 serve [Follower Read](/backend/knowledge-cards/follower-read/)、不參與 Raft commit。可以放在「不想列入 quorum 但希望本地 read 快」的 region

實務影響：region survival 下、CockroachDB 為每個 range 放 5 個 voting replica，其中 2 個在 primary region、其餘分到其他 region（每個 region 至少 1 個）。majority 是 3，所以寫入要等 primary region 的 2 個 replica 加上另一個 region 至少 1 個 replica 的 ack，也就是至少一次到最近 region 的 round trip。若想讓第 4 個 region 也能本地 read、可以加 non-voting replica、不影響 commit latency 但增加 storage cost。

### 配置語法

```sql
-- survival goal 只能設在 database 上，table 沒有自己的 survival goal
ALTER DATABASE mydb SURVIVE REGION FAILURE;

-- 驗證
SHOW SURVIVAL GOAL FROM DATABASE mydb;
SHOW ZONE CONFIGURATION FOR DATABASE mydb;
```

對應 [quorum 卡](/backend/knowledge-cards/quorum/)、[rto 卡](/backend/knowledge-cards/rto/)、[rpo 卡](/backend/knowledge-cards/rpo/)、[blast radius 卡](/backend/knowledge-cards/blast-radius/) 的具體機制實現。

### 為什麼選 region survival 是業務動機判讀、不是技術 fact

Netflix 60+ multi-region cluster 揭露的反直覺結論：*主要動機是 region failure 0 downtime、不是降 latency*。跨 region quorum 物理上必然增 latency — 跨洲 round trip 物理 ~70-80ms、Raft majority 要等 primary region 以外至少一個 region 的 ack、寫入 p99 因此被光速下界限制。

Gaming cluster 48-node 跨 4 region 就是為了「region failover 不停服」、不是讓玩家延遲變低。**Scope warning**：case 沒揭露 Gaming cluster 具體 p99 數字、只揭露「48-node、跨 4 region、region failure 不停服」這個拓樸 fact 跟業務動機釐清。

region survival 對用戶體驗的貢獻是 region 失效時服務不中斷，不是延遲變低；把跨 region 配置當成降低延遲的手段，是選 survival goal 時最常見的錯誤起點。

## 操作流程：從業務 SLO 倒推 survival goal

### 配置前置

region survival 的最小可運行配置：

- cluster 至少 3 個 region
- 每 region 至少 3 個節點（保證單一 region 內也能扛 AZ failure）
- locality tag 配齊（region + zone）

```bash
# Region us-east1 的節點
cockroach start --locality=region=us-east1,zone=us-east1-a ...

# Region us-west2 的節點
cockroach start --locality=region=us-west2,zone=us-west2-a ...

# Region eu-west1 的節點
cockroach start --locality=region=eu-west1,zone=eu-west1-a ...
```

### 從業務 SLO 倒推（Hard Rock）

Hard Rock Digital sportsbook 揭露的 5 步倒推流程：

1. **列業務「不能丟」事件清單**：bet placement、payment、order commit、settlement 等業務事件
2. **對每個事件決定 RPO**：bet placement → RPO = 0（不可丟）、log audit → RPO = 1 分鐘（可接受 short-window 丟失）
3. **對 RPO = 0 事件決定故障域容忍**：Hard Rock 案例 *Outpost 或 AZ 失敗不丟* 是業務要求、跨 region failure 不是 sportsbook 的硬需求（因為各州各自合規邊界）
4. **故障域容忍翻譯成 survival goal**：
   - Outpost / AZ 失敗 → `SURVIVE ZONE FAILURE` 即可
   - region 失敗也不丟 → `SURVIVE REGION FAILURE`
5. **反過來驗 replica 分佈**：survival goal 配置產出的 replica 分佈是否覆蓋業務故障域。Hard Rock CockroachDB Raft 3-replica + 跨 AZ → Outpost 失敗時其他 replica 在、自動 failover、滿足 bet placement RPO = 0

### 跟業務動機釐清的互補

Netflix 從技術配置 *反推*「為什麼選 region survival」（survival 動機、不是 latency）、Hard Rock 從業務不能丟事件 *正推* 該選哪個 survival goal。兩個方向是同一條路徑：

- 正推（Hard Rock）：業務不能丟 → RPO → 故障域 → survival goal
- 反推（Netflix）：survival goal 配置 → 揭露的不是「會變快」而是「region failover 不停服」

兩個方向互相驗證、避免把跨 region 配置誤解成 latency 工具。

### 升級流程跟 rollback 邊界

zone survival → region survival 是 *非破壞性* 配置變更、Raft 自動 rebalance replica。但要注意：

- rebalance 期間 cross-region traffic 暴增、p99 短期波動
- replication factor 增加 → storage 用量 × 新 RF
- 升級後 application 寫入 latency 結構性上升、要先在 staging 量過

監控 rebalance：

```sql
-- 看 range 數量變化跟 rebalance queue
-- crdb_internal 在 v26.3 預設禁止查詢，要先開這個 session 變數（官方標示為不支援的內部介面）
SET allow_unsafe_internals = true;
SELECT range_count, used FROM crdb_internal.kv_store_status;

-- CockroachDB Console「Rebalance queue size」應該歸零
```

Rollback：survival goal 可即時降級（region → zone）、replica 自動 rebalance、無不可逆動作。但 application 端如果已經依賴 region failover 0 downtime、降級回 zone survival 後 voting replica 回到只在 primary region，primary region 失效時這個 database 的寫入會停擺 — 配置 rollback 容易、業務 SLO rollback 不容易。

## 失敗模式：survival goal 跟 region 數、成本、locality 與合規的錯配

### Default zone survival 期待 region survival

最常見：上線後 primary region 掛、這個 database 的寫入停擺、客訴。要在 production 前 *明確選* survival goal、不依賴 default。

### Region survival 但只配 2 region

Raft majority 需要 3 個獨立 fault domain：只有 2 個 region 時，任一 region 失敗，剩下那個 region 的 replica 拿不到 majority。CockroachDB 因此直接拒絕這個配置，database 只有 2 個 region 時 `ALTER DATABASE ... SURVIVE REGION FAILURE` 回錯誤 `at least 3 regions are required for surviving a region failure`。要 region survival *至少* 3 region。

### Cross-region cost 暴漲

region survival 強制 voting replica 跨 region、每次 write 跨 region traffic × 3。AWS / GCP 的 cross-region data transfer 是高 markup、月費可能 2-3 倍。

production 前必須估：

- 寫 QPS × row size × 3 = cross-region traffic GB/day
- 對應 cloud provider 定價（AWS 跨 region $0.02/GB、GCP 類似量級）
- 月度 traffic cost 加總、跟 single-region 配置比

### Locality 跟 survival goal 衝突

業務想把 user data partition by region 留 local（locality 配置）、但 survival goal 要求跨 region replica、結果 replica 仍跑遠端。這是 locality + survival 的互動議題、見 [locality-aware schema](../locality-aware-schema/) 詳細展開。

### 合規邊界 violation

受監管市場（金融 / 醫療 / 博彩）資料 *不能跨境*、但 region survival 強制 voting replica 跨 region — 這直接違反合規。對照 [Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 走的是「每市場獨立 Aurora cluster + 多 AZ 部署」、不是 region survival。

合規邊界判讀：

- 跨境合規 *禁止* 跨 region replica → 不可用 region survival、走 cluster-per-市場
- 跨州合規 *允許* 跨州但要求資料留國內 → 可用 region survival、選同國內的 region
- 業務邏輯要求跨 boundary（如 Hard Rock 跨州統一帳戶）→ 不可拆獨立 cluster、必須 locality + placement

## 容量與觀測

### 必看 metric

- `Raft replicas per node`：replica 分佈均勻度
- `Range count by survival mode`：region survival 配置的 range 數量
- `Cross-region write latency p99`：跨 region quorum 實測 latency
- `Rebalance queue size`：rebalance 是否完成
- `Network traffic by direction`：cross-region 流量、cost signal

### 容量公式

- region survival 最小：region count × 3 nodes
- replica factor 預設 3、storage 用量 × replication factor
- cross-region traffic = write QPS × row size × primary region 以外的 replica 數（3 region 的 region survival 預設是 3）

### Write latency 預算（屬通用工程估算、case 未揭露具體 latency 數字）

**Scope warning**：以下數字屬通用工程估算（跨 region 物理光速下界推導）、**Netflix / Hard Rock case 都沒揭露 zone / region survival 的 p99 latency 數字**：

- zone survival single-region 寫入 p99 5-10ms（跨 AZ Raft round trip）
- region survival 同洲跨 region p99 30-60ms（跨 region round trip × Raft majority）
- region survival 跨洲 p99 100-150ms（跨洲 round trip ~70-80ms 起跳）

數字屬「合理的工程估算量級」、不是 case 揭露的 p99。讀者用這些做容量規劃時應該自己 benchmark、不要直接套。

### 賽季型容量擺盪（Hard Rock）

sportsbook 業務年度循環：NFL / NBA 季初季末流量結構性差異 — Hard Rock 100 nodes ↔ 33 nodes 擺盪是 *計畫內*、不是異常事件。CockroachDB 加減節點靠 range rebalance、不停服。

容量規劃要點：

- NFL / NBA / 國際賽事曆塞進預測模型、不要當 surprise
- scale up 提前 1-2 週執行、留 rebalance 時間
- scale down 在淡季低流量時段執行、避免 rebalance 期間 p99 spike

### 回路徑

- [9.6 容量規劃模型](/backend/09-performance-capacity/) survival goal 對 replica count / cost 影響
- [9.11 高峰事件準備](/backend/09-performance-capacity/) event-driven scaling
- [latency budget 卡](/backend/knowledge-cards/latency-budget/) cross-region 預算

## 邊界與整合

### 同 vendor 的其他文章

- [HLC + Raft consensus](../hlc-raft-consensus/)：Raft 機制是 survival goal 的基礎
- [locality-aware schema](../locality-aware-schema/)：locality + survival 一起決定 placement
- [transaction retry pattern](../transaction-retry-pattern/)：cross-region latency 加長 retry window

### 跟 Aurora 對照

- Aurora cross-AZ failover：zone-level survival 等價、但只在 single-region 內
- Aurora Global Database：跨 region async replication、不是 sync — region failure 仍會丟 last seconds
- CockroachDB region survival：sync majority、region failure RPO = 0

Aurora 沒有 row-level locality 配置、跨 region 強一致要走 Aurora DSQL（AWS 2024-12 re:Invent 發表 preview、2025-05-27 GA）。

### Aurora DSQL / Spanner 對比

完整三家 distributed SQL 在 multi-region survival 的取捨、見 [aurora-dsql-spanner-decision-tree](../aurora-dsql-spanner-decision-tree/)。

### 1.x 章節互引

- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 上游
- [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) distributed transaction

### 何時不用 region survival

- single-region 已滿足業務 SLO → zone survival 即可
- 預算敏感、cross-region traffic cost 不划算
- 合規禁止跨境 → 必須拆每市場獨立 cluster + zone survival

## 相關連結

- [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/)
- [Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)（bet placement RPO=0 倒推）
- [Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（Gaming 48-node 跨 4 region survival）
- [Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)（anti-recommendation、為何 *不用* region survival）
- [quorum 卡](/backend/knowledge-cards/quorum/) / [rto 卡](/backend/knowledge-cards/rto/) / [rpo 卡](/backend/knowledge-cards/rpo/) / [blast radius 卡](/backend/knowledge-cards/blast-radius/)
- 官方：[CockroachDB Multi-Region Survival Goals](https://www.cockroachlabs.com/docs/stable/multiregion-survival-goals.html) / [Multi-Region Capabilities Overview](https://www.cockroachlabs.com/docs/stable/multiregion-overview.html)
