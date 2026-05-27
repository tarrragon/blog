---
title: "Spanner Consistency Models 對照：external consistency vs serializability vs linearizability"
date: 2026-05-27
description: "external consistency、serializability、linearizability 是三個常被混用的概念。本文先精確定義三者差異、再用 line-rate scaling 對照表（PG SSI / CockroachDB / Spanner / Aurora DSQL）回答為什麼 Spanner 不只是『更強的 serializable』、最後用 9.C10 揭露的 cross-region quorum 100-200ms 物理硬限解釋『強一致 + 全球部署』的真實 cost"
weight: 31
tags: ["backend", "database", "spanner", "global-sql", "consistency", "external-consistency", "linearizability", "deep-article"]
---

> 本文是 [Cloud Spanner](/backend/01-database/vendors/spanner/) overview 的 concept-layer deep article。Overview 已說明 Spanner 在強一致 SQL 譜系的定位、本文聚焦 *consistency model* — 三個常被混用的概念（external consistency / serializability / linearizability）的精確差異、line-rate scaling 對照、跟 cross-region quorum 的物理硬限。

---

## 問題情境：五個詞混用的選型困境

團隊在 Spanner / CockroachDB / Aurora DSQL 之間選型、看文件講 strict serializability、external consistency、linearizable、snapshot isolation、serializable — 五個詞混用、不確定買的是哪一種保證。讀者徵兆通常是「我們需要強一致」但說不出強到哪、把 serializable transaction 跟 linearizable read 當同一件事、debug 對帳時發現「兩個 transaction 都 commit 成功、順序卻違反 user 體感」。

真實壓力場景：金融帳本 — A 在台北轉帳給 B、B 在東京立即收到通知然後查餘額、結果查到「轉帳前」的餘額。serializable 允許這種行為（兩 transaction 可以排成任意順序、不要求跟 wall clock 一致）、external consistency 不允許（必須等 commit 後的順序符合 real-time）。混用兩個詞會讓選型結論在系統實作後才被推翻、那時候改架構成本已經高了。

Case anchor：[9.C10 Cloud Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — Google Ads 計費需要 external consistency；對照 PostgreSQL SSI、CockroachDB HLC、Aurora DSQL。**dogfood 邊界明示**：9.C10 是 Google 內部 dogfood case、不是 customer-facing capacity 參考；本文引用其 line-rate scaling 數字時要附「Google internal dogfood 揭露的設計目標、不是客戶 SLA」邊界。

## 三個概念的精確定義

### Serializability

transaction 的執行結果等同於 *某個* 序列順序執行；不要求順序跟 real-time 一致。PostgreSQL SERIALIZABLE isolation level（SSI 實作）給的就是這個保證。它解決的問題是 *concurrent transaction 之間互相干擾的 anomaly*（dirty read / lost update / write skew / G2-item）、不解決「跨 transaction 的 wall-clock 順序」。

範例：A 在 10:00:00 commit T1（餘額 +100）、B 在 10:00:01 commit T2（查餘額）。serializable 允許系統把 T2 排在 T1 之前、B 看到舊餘額 — 兩 transaction 都成功、isolation 沒被破壞、但用戶體感違反順序。

### Linearizability

單一 object 操作有全序、且全序跟 real-time wall-clock 一致。只談 single-object、不談跨 object transaction。DynamoDB strongly consistent read 是 single-item linearizability、Redis `INCR` 是 single-key linearizability。對應 [linearizability](/backend/knowledge-cards/linearizability/) 卡。

linearizability 跟 serializability 是 *正交* 的兩個概念 — linearizability 講「單一 object 的 real-time 順序」、serializability 講「transaction 的 anomaly-free 執行」。一個系統可以是 linearizable 但不 serializable（單 object 強保證、跨 object transaction 沒有）、也可以是 serializable 但不 linearizable（PostgreSQL SSI single-node 在 replica lag 後就不 linearizable）。

### External consistency / Strict serializability

transaction 層級的 serializability + 全序跟 real-time 一致 — 等同於把 linearizability 推廣到 multi-object transaction。Spanner 用 TrueTime + commit wait 實作、保證 commit timestamp 順序 = real-time 順序。對應 [external-consistency](/backend/knowledge-cards/external-consistency/) 卡。

回到金融帳本例：external consistency 不允許 T2 排在 T1 之前、因為 T2 的 transaction timestamp 必須大於 T1 的 commit timestamp、用戶查餘額必看到 +100 後的金額。

## Line-rate scaling 對照：為什麼 PG serializable 在 multi-node 拿不到 line-rate

這段的核心責任是回答「為什麼 Spanner 不只是『更強的 serializable』、是『coordinator 換拓樸』的 paradigm shift」、扣 [truetime-api-depth](../truetime-api-depth/) 的商業邏輯先行 frame。讀者選 consistency 等級時、實際在選「系統的 scaling 路徑」、不只是「應用層 anomaly 哪些被排除」。

### 9.C10 揭露的線性擴展數字

「2 nodes → 45K reads/sec、4 nodes → 90K reads/sec」這條線性 scaling 揭露 Spanner external consistency 不是「加強版 serializable」、是把跨節點 coordinator 從 single-point 換成「拓樸感知的多 leader（每個 split 自己的 Paxos group）」、所以擴 node 數可以線性拿 throughput。

**Dogfood 邊界明示**：9.C10 數字是 Google internal dogfood、不是 customer-facing capacity 承諾。客戶能拿到的 line-rate 受 instance config、region layout、workload shape 影響、不會自動複製 Google 內部曲線。

### 對照表：四個系統的 scaling 路徑

| 系統           | Isolation / Consistency 等級        | Multi-node scaling 路徑        | 為什麼撞天花板（或不撞）                                                                                        |
| -------------- | ----------------------------------- | ------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| PostgreSQL SSI | Serializable                        | single-primary + read replica  | 寫只能 single primary、跨節點交易要 2PC + coordinator、replica 寫不了；scaling 路徑停在 single-primary 容量上限 |
| CockroachDB    | Serializable + per-key linearizable | range-based + HLC              | range coordinator 仍存在、但 range 拆細了；retry contract 接住跨 range conflict、扣 serializable restart cost   |
| Spanner        | External consistency                | split-based + Paxos + TrueTime | coordinator 變多 leader、TrueTime 對齊 commit 順序、線性擴展是設計目標（9.C10 揭露 dogfood 線性模式）           |
| Aurora DSQL    | Strong consistency（2024 推出）     | 文件未完全公開、查最新 docs    | 時間敏感 claim、本文不擴寫；讀者實作前查官方文件確認最新 scaling 模型                                           |

每個欄位都要回到具體的 scaling 機制讀。PostgreSQL SSI 跟「single-primary」綁定 — 想 scale write 只能 sharding；CockroachDB 把 range 拆細、coordinator 分布到 range 層、但跨 range conflict 還是會 trigger retry；Spanner 用 Paxos group per split、commit timestamp 用 TrueTime 對齊、不需要全局 coordinator 來決定順序；Aurora DSQL 是新系統、機制細節隨版本演進。

### 為什麼這個對照寫進 consistency 文章、不是純機制文章

讀者選 consistency 等級時、實際在選「系統的 scaling 路徑」、不只是「應用層 anomaly 哪些被排除」。external consistency 的 cost 包含 commit wait latency、但 benefit 包含 line-rate scaling — 兩者要一起講、不能拆開。把對照表放這裡、讓 consistency 跟 scaling 在同一段被讀者一起判讀、避免「我們需要強一致」這種需求被翻譯成「升級到 Spanner」這種跳號決策。

## Cross-region quorum 100-200ms 物理硬限：強一致 + 全球不是免費

[Cross-Region Quorum](/backend/knowledge-cards/cross-region-quorum/) + external consistency + multi-region 不是「免費全球」、是「用 latency 換 consistency」。讀者若沒看到具體數量級、會誤把 Spanner 當作「強一致 + 全球 + 低延遲」的奇蹟、實際 cross-region write 在物理光速硬限下必須付跨洲 round-trip cost。

### 9.C10 揭露的數量級

「external consistency 必須等多區 quorum、跨洲交易延遲可達 100-200ms」 — 這是 9.C10 case 直接揭露的工程數字、不是本章 derive。**Dogfood 邊界明示**：9.C10 case 揭露的是 Google internal dogfood 觀察到的數量級、不是 SLA 承諾；實際客戶的 cross-region write latency 隨 voting region 配置、network path 變化。

### Latency 拆解模型（cross-region write）

```text
total write latency ≈ 2ε（[Commit Wait](/backend/knowledge-cards/commit-wait/)、TrueTime ε 兩倍 ≈ 2-14ms）
                    + quorum RTT across voting regions
                       跨洲：50-100ms one-way、來回 100-200ms
                       跨大陸內：10-30ms
                       跨 zone（同 region）：< 5ms
                    + Spanner internal processing
```

跨洲 quorum 在這個模型裡是 *dominant term*、不是 [commit wait](/backend/knowledge-cards/commit-wait/) — 判讀時要明示「commit wait 跟跨 region quorum 是兩個獨立的物理 cost、不能混用一個 latency 數字解釋兩者」。讀者常見的誤解是把 100-200ms 寫成「Spanner commit wait」、實際 commit wait 只是其中 2-14ms、剩下 100ms+ 是物理光速限定的 quorum RTT。

### Scope warning：實際 latency 依 region 配置

100-200ms 是 9.C10 case 揭露的範圍、實際 latency 隨 voting region 配置變化：

| Instance config 類型          | Voting region 散布 | 典型 write p99 |
| ----------------------------- | ------------------ | -------------- |
| Regional（單 region 多 zone） | 同 region 內       | < 10ms         |
| Dual-region（同大陸）         | 跨大陸內           | 20-50ms        |
| Multi-region（跨洲）          | 跨大陸或跨洲       | 100-200ms      |

引用要附條件「跨洲多 region instance、實際數字依 region 配置」、不能寫成「Spanner cross-region write 一律 100-200ms」。讀者拿這條 latency anchor 做 capacity planning 時、必須先 audit 自家 instance 是哪種 config、不能套用 100-200ms 當基線。

## SSoT 對齊：Strong + multi-region 互斥議題不在此處展開

Strong consistency + multi-region 互斥議題（包含 Cosmos DB 5 levels 的 Strong + multi-region 限制）的 SSoT 是 [Cosmos DB multi-region-write-conflict](/backend/01-database/vendors/cosmosdb/multi-region-write-conflict/)。本篇 cross-link 不展開、避免重複展開同議題。

本篇展開的子議題：

- external consistency / serializability / linearizability 的精確定義差異
- Spanner external consistency 的 TrueTime 實作機制（細節在 [truetime-api-depth](../truetime-api-depth/)）
- cross-region quorum 的物理 cost 數量級
- line-rate scaling 對照表（為什麼 single-primary 系統拿不到線性）

兩個 SSoT 處理同一個讀者問題（強一致 vs multi-region）的不同切面 — 本篇從 *系統 scaling 路徑* 切入、Cosmos DB 文章從 *consistency level 選擇* 切入。讀者讀完本篇後若還在問「為什麼 Cosmos DB strong consistency 不能配 multi-region write」、跳 Cosmos DB SSoT。

## 操作流程：怎麼驗證 consistency 等級

### 決策樹

```text
跨 multi-object transaction 嗎？
├─ 否 → DynamoDB linearizable read / Redis single-key 足夠
└─ 是 →
   跨 region 寫入嗎？
   ├─ 否 → CockroachDB / PostgreSQL serializable 足夠
   └─ 是 →
      real-time 順序是產品契約嗎？
      ├─ 否 → CockroachDB multi-region 可接受
      └─ 是 → Spanner / Aurora DSQL
```

### 驗證 consistency 等級的方法

跑 Jepsen-style test、寫 read-write workload 跑 anomaly checker、量 dirty write / lost update / write skew / G2 anomaly。production 系統若不能跑完整 Jepsen、至少要在 staging 跑 *對應 anomaly 的具體 test case* — 例如金融帳本跑「轉帳後立即跨 region 查餘額、能不能看到舊值」這個具體 case、不是只看 isolation level 設定文字。

### SDK 層的選擇點

```text
Spanner          → 預設就是 external consistency、read 可降到 bounded staleness
CockroachDB      → 預設 serializable、可選 AS OF SYSTEM TIME 換 stale read
PostgreSQL       → 要顯式 SET TRANSACTION ISOLATION LEVEL SERIALIZABLE
DynamoDB         → 預設 eventually consistent、ConsistentRead=true 換強一致
```

每個 SDK 的 default 都不同、不能假設「沒設就是強的」。PostgreSQL default 是 READ COMMITTED、write skew 直接漏。

### Rollback boundary

若一致性等級從強降到弱、要審計應用層所有讀取點（特別是「讀後決策再寫」的 critical path）。降級不是 config 一行的事、是 audit 一遍應用層假設的事。

## 失敗模式：把 transaction 當「強一致」的五種誤用

### 把「我們用 transaction」當「強一致」

transaction 只保證原子性、不保證 isolation level；預設 isolation 可能是 READ COMMITTED、write skew 直接漏。修法是顯式設定 isolation level、跑對應 anomaly test 驗證、不靠「我們用 transaction」這種口頭契約。

### 假設 single-node serializable = distributed serializable

PostgreSQL SSI 跨 read replica 立刻失效（replica lag）、團隊以為加 replica 還是 serializable。實際 replica 的 read 是 eventually consistent、可能看到舊 snapshot。修法是區分 primary read vs replica read、replica read path 標 `bounded staleness`、不混用 isolation level 字眼。

### 跨系統 timestamp 假設

service A 用 Spanner、service B 用 Redis、用各自 timestamp 重組事件順序 — service B 的 clock 沒 TrueTime 保證、跨系統 external consistency 不成立。修法是跨系統事件順序要走 *單一系統的 timestamp* 或 *event sequence number*、不靠各系統自己的 wall-clock 拼出順序。

### 把 linearizability 跟 strong consistency 混用、忽略 multi-object 場景

DynamoDB strongly consistent read 是 single-item linearizability、不等於跨 item transaction 強一致。團隊以為「我用了 strongly consistent read 就 OK」、實際跨 item 的順序保證沒有。修法是區分 single-object vs multi-object、跨 item 邏輯如果有順序需求、要用 DynamoDB transaction API（付 2x WCU 的 cost）或換到 Spanner。

### 過度承諾 external consistency

dashboard / analytics 強寫 strong read、付不必要的 latency tax。修法是把 read path 分類、analytics / reporting 改 bounded staleness、保留 strong read 給 critical path。回 [truetime-api-depth](../truetime-api-depth/) 的「把 strong read 用在不需要的路徑」失敗模式。

## 容量與觀測：一致性等級的 latency 量化

| 一致性等級                     | latency 影響                                | 適用場景                      |
| ------------------------------ | ------------------------------------------- | ----------------------------- |
| External consistency（strong） | baseline = 2ε + quorum RTT                  | critical path、金融帳本、計費 |
| Bounded staleness（5-10s）     | 省 commit wait（10-50ms）、可讀本地 replica | dashboard、reporting          |
| Eventual                       | 砍 quorum RTT、只讀本地 replica             | analytics、推薦               |

跨 region 延遲量化（finding F3.15、來源 9.C10）：external consistency + multi-region instance config、跨洲 quorum 把 write latency 推到 100-200ms 數量級；單 region instance 的 commit wait 是 baseline（≈ 2ε ≈ 2-14ms）、跨 region quorum 是額外 dominant cost。

Cloud Monitoring：`spanner.googleapis.com/instance/clock_skew_ms` 觀察 ε、`api/api_request_latencies` for `Commit` 觀察 commit latency 分布；CockroachDB 觀察 `sql.txn.restart.serializable` 計數（serializable restart 率）。回到 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 把一致性等級當 release gate 的一部分。

Capacity 觀點：external consistency 的 commit wait 是「無法 scale away 的 latency 支出」、capacity planning 要先扣這部分；跨 region instance 的 quorum RTT 也是物理硬限、不能透過加 node 解。

## 邊界與整合：sibling 路由跟 anti-recommendation

### Sibling deep articles

- [truetime-api-depth](../truetime-api-depth/)：external consistency 的硬體基礎、TrueTime ε / commit wait 數學、商業邏輯先行 frame
- [schema-migration-interleaved-tables](../schema-migration-interleaved-tables/)：schema change 的版本一致性也用 TrueTime
- [migrate-from-cloud-sql-pg](../migrate-from-cloud-sql-pg/)：Diff 階段要明確標示一致性等級從 SSI 升到 external consistency 的應用層影響

### SSoT cross-link

Strong consistency + multi-region 互斥議題的 SSoT 在 [Cosmos DB multi-region-write-conflict](/backend/01-database/vendors/cosmosdb/multi-region-write-conflict/)、本篇不重複展開。

### 跟 1.x 章節的互引

- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)：Spanner 是 PC 系統的代表
- [transaction boundary](/backend/knowledge-cards/transaction-boundary/)：跨 transaction 順序保證

### Knowledge card 雙引用

- [linearizability](/backend/knowledge-cards/linearizability/) — 本文當這張卡的 vendor 應用範例
- [external-consistency](/backend/knowledge-cards/external-consistency/) — 本文擴展這張卡的實作機制
- [isolation-level](/backend/knowledge-cards/isolation-level/) — 本文澄清 isolation level 跟 consistency model 的差異

### Anti-recommendation

讀者讀完本文應該能判斷：「我們需要強一致」不等於「升級到 Spanner」 — 先問是 single-object 還是 multi-object、是 single region 還是 multi region、real-time 順序是否是產品契約。多數 OLTP workload 用 PostgreSQL serializable 已經夠、為 external consistency 付 GCP lock-in + 跨 region quorum cost 的判準很高。
