# Consistency Models 對照：external consistency vs serializability vs linearizability

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：團隊在 Spanner / CockroachDB / Aurora DSQL 之間選型、看文件講 strict serializability、external consistency、linearizable、snapshot isolation、serializable — 五個詞混用、不確定買的是哪一種保證
- 讀者徵兆：「我們需要強一致」但說不出強到哪、把 serializable transaction 跟 linearizable read 當同一件事、debug 對帳時發現「兩個 transaction 都 commit 成功、順序卻違反 user 體感」
- 真實壓力場景：金融帳本 — A 在台北轉帳給 B、B 在東京立即收到通知然後查餘額、結果查到「轉帳前」的餘額 — serializable 允許這種行為、external consistency 不允許
- Case anchor: [9.C10 Cloud Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — Google Ads 計費需 external consistency；對照 PostgreSQL SSI、CockroachDB HLC、Aurora DSQL 的選擇

## 核心機制（Vendor-specific mechanism）

- 三個概念的精確定義：
  - **Serializability**：transaction 結果等同於 *某個* 序列順序執行；不要求順序跟 real-time 一致
  - **Linearizability**：單一 object 操作有全序、且全序跟 real-time wall-clock 一致；只談 single-object
  - **External consistency / Strict serializability**：transaction 層級的 serializability + 全序跟 real-time 一致；= 把 linearizability 推廣到 multi-object transaction
- Spanner 的 external consistency：用 TrueTime + commit wait 實作、保證 commit timestamp 順序 = real-time 順序
- CockroachDB 的對照：用 HLC（Hybrid Logical Clock）+ uncertainty interval、提供 serializable + per-key linearizable、不是完整 external consistency（有 read uncertainty restart 機制補）
- PostgreSQL SSI 的位置：serializable isolation、但 single-node、沒有跨節點時間保證
- Aurora DSQL（2024+）的位置：宣稱 strong consistency、internally serializable、跟 Spanner external consistency 的差異在 *跨 region* 行為（時間敏感 claim、實作前查官方文件）
- 對應 knowledge card：[linearizability](/backend/knowledge-cards/linearizability/)、[external-consistency](/backend/knowledge-cards/external-consistency/)、[isolation-level](/backend/knowledge-cards/isolation-level/)

## Line-rate scaling 對照：為什麼 PostgreSQL serializable 在 multi-node 拿不到 line-rate

- 核心責任：本段回答「為什麼 Spanner 不只是『更強的 serializable』、是『coordinator 換拓樸』的 paradigm shift」、扣商業邏輯先行 frame（finding F3.14）。寫稿時是讀者理解「強一致 + 線性擴展」並存的關鍵 anchor、必須在「失敗模式」前就位
- 9.C10 揭露的線性擴展數字：`2 nodes → 45K reads/sec、4 nodes → 90K reads/sec`（來源 9.C10「判讀」段第 1 點）— 這條揭露 Spanner external consistency 不是「加強版 serializable」、是把跨節點 coordinator 從 single-point 換成「拓樸感知的多 leader（Paxos group per split）」、所以擴 node 數可以線性拿 throughput
- 對照表（為什麼傳統 OLTP 拿不到 line-rate）：

  | 系統                 | Isolation 等級              | Multi-node scaling 路徑        | 為什麼撞天花板                                                           |
  | -------------------- | --------------------------- | ------------------------------ | ------------------------------------------------------------------------ |
  | PostgreSQL SSI       | Serializable                | single-primary + read replica  | 寫只能 single primary、跨節點交易要 2PC + coordinator                    |
  | CockroachDB          | Serializable + per-key 線性 | range-based + HLC              | range coordinator 仍存在、但拆細了；retry contract 接住跨 range conflict |
  | Spanner              | External consistency        | split-based + Paxos + TrueTime | coordinator 變多 leader、TrueTime 對齊 commit 順序、線性擴展             |
  | Aurora DSQL（2024+） | Strong consistency          | 文件未完全公開、查最新 docs    | 時間敏感 claim、不擴寫                                                   |

- 為什麼這個 frame 寫進 consistency 文章而不是純機制文章：讀者選 consistency 等級時、實際在選「系統的 scaling 路徑」、不只是「應用層 anomaly 哪些被排除」。external consistency 的 cost 包含 commit wait latency、但 benefit 包含 line-rate scaling — 兩者要一起講
- Scope warning（finding F3.17）：9.C10 是 Google internal dogfood、不是 customer-facing capacity reference。引用 45K / 90K reads/sec 時要明示「Google internal dogfood 揭露的線性擴展模式、不是客戶 SLA 承諾」

## Cross-region quorum 物理硬限：100-200ms 數量級 anchor

- 核心責任：external consistency + multi-region 不是「免費全球」、是「用 latency 換 consistency」。讀者若沒看到具體數量級、會誤把 Spanner 當作「強一致 + 全球 + 低延遲」的奇蹟、實際 cross-region write 在物理光速硬限下必須付跨洲 round-trip cost（finding F3.15）
- 9.C10 揭露的數量級：「external consistency 必須等多區 quorum、跨洲交易延遲可達 100-200ms」（來源 9.C10「判讀」段第 2 點 + 「策略」段第 3 點）— 這是 case 直接揭露的工程數字、不是本章 derive
- Latency 拆解模型（cross-region write）：

  ```text
  total write latency ≈ 2ε（commit wait、TrueTime ε 兩倍）
                       + max(quorum RTT across voting regions、跨洲 50-100ms one-way、來回 100-200ms)
                       + Spanner internal processing
  ```

  跨洲 quorum 在這個模型裡是 dominant term、不是 commit wait — 寫稿時要明示「commit wait 跟跨 region quorum 是兩個獨立的物理 cost、不能混用一個 latency 數字解釋兩者」
- Scope warning：100-200ms 是 9.C10 case 揭露的範圍、實際 latency 隨 voting region 配置變化（regional / dual-region / multi-region instance config 各不同）。引用要附條件「跨洲多 region instance、實際數字依 region 配置」、不能寫成「Spanner cross-region write 一律 100-200ms」
- 跟 commit wait 的關係：commit wait（≈ 2ε ≈ 2-14ms）是 *額外的* TrueTime cost、不取代 quorum cost；total latency = commit wait + quorum RTT、不是 max。寫稿時若把兩者混講會誤導讀者「Spanner 跨 region 100-200ms 是 commit wait」、實際 commit wait 只是其中一小段

## SSoT 對齊：Strong + multi-region 互斥議題不在此處展開

- 規則（_module-outline.md Section G）：Strong consistency + multi-region 互斥議題（包含 Cosmos DB 5 levels 的 Strong + multi-region 限制）的 SSoT 是 `cosmosdb/consistency-levels-engineering.md`。本篇 cross-link 不展開、避免重複展開同議題
- 本篇要展開的子議題：(a) external consistency / serializability / linearizability 的精確定義差異、(b) Spanner external consistency 的 TrueTime 實作機制、(c) cross-region quorum 的物理 cost、(d) line-rate scaling 對照表
- 寫稿時這條規則一定要在「邊界與整合」段明示、給讀者下一步路由

## 操作流程（Operations）

- 決策樹：先問「跨 multi-object transaction 嗎」→ 是 → 「跨 region 寫入嗎」→ 是 → 「real-time 順序是產品契約嗎」→ 是 → Spanner / Aurora DSQL；否 → CockroachDB / PostgreSQL serializable 足夠
- 驗證一致性等級的方法：Jepsen-style test、寫 read-write workload 跑 anomaly checker、量 dirty write / lost update / write skew / G2 anomaly
- SDK 層的選擇點：Spanner 預設就是 external consistency、但 read 可降到 bounded staleness；CockroachDB 預設 serializable、可選 `AS OF SYSTEM TIME` 換 stale read；PostgreSQL 要顯式 `SET TRANSACTION ISOLATION LEVEL SERIALIZABLE`
- 驗證點：跑 G2-item / write skew 經典 anomaly test、確認系統行為符合宣告等級
- Rollback boundary：若一致性等級從強降到弱、要審計應用層所有讀取點（特別是「讀後決策再寫」的 critical path）

## 失敗模式（Failure modes）

- 把「我們用 transaction」當「強一致」：transaction 只保證原子性、不保證 isolation level；預設 isolation 可能是 read committed、寫 skew 直接漏
- 假設 single-node serializable = distributed serializable：PostgreSQL SSI 跨 read replica 立刻失效（replica lag）、團隊以為加 replica 還是 serializable
- 跨系統 timestamp 假設：service A 用 Spanner、service B 用 Redis、用各自 timestamp 重組事件順序 — service B 的 clock 沒 TrueTime 保證、跨系統 external consistency 不成立
- 把 linearizability 跟 strong consistency 混用、忽略 multi-object 場景：DynamoDB strongly consistent read 是 single-item linearizability、不等於跨 item transaction 強一致
- 過度承諾 external consistency：dashboard / analytics 強寫 strong read、付不必要的 latency tax
- Case 對應根因：金融對帳失敗的根因常是「以為 serializable = external consistency」、跨 region read 拿到舊版本

## 容量與觀測（Capacity & observability）

- 一致性等級對 latency 的影響量化：external consistency ≈ baseline；bounded staleness 可節省 commit wait（10-50ms）；eventual 再砍 quorum RTT
- 跨 region 延遲量化（finding F3.15、來源 9.C10）：external consistency + multi-region instance config、跨洲 quorum 把 write latency 推到 100-200ms 數量級；單 region instance 的 commit wait 是 baseline（≈ 2ε ≈ 2-14ms）、跨 region quorum 是額外 dominant cost
- Cloud Monitoring：`spanner` 系列觀察 commit latency 分布、CockroachDB 觀察 `sql.txn.restart.serializable` 計數（serializable restart 率）
- 回到 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 把一致性等級當 release gate 的一部分
- Capacity 觀點：external consistency 的 commit wait 是「無法 scale away 的 latency 支出」、capacity planning 要先扣這部分；跨 region instance 的 quorum RTT 也是物理硬限、不能透過加 node 解

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[truetime-api-depth](./truetime-api-depth.md)（external consistency 的硬體基礎、商業邏輯先行 frame）、[schema-migration-interleaved-tables](./schema-migration-interleaved-tables.md)（schema change 的版本一致性）
- Migration playbook 連結：[migrate-from-cloud-sql-pg](./migrate-from-cloud-sql-pg.md) 的 Diff 階段要明確標示一致性等級從 SSI 升到 external consistency 的應用層影響
- SSoT cross-link（_module-outline.md Section G）：Strong consistency + multi-region 互斥議題的 SSoT 在 [Cosmos DB consistency-levels-engineering](../cosmosdb/consistency-levels-engineering.md)、本篇不重複展開
- 跟 1.x 章節的互引：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)、[1.6 Transaction 設計](/backend/01-database/transaction-design/) （若存在）
- Knowledge card 雙引用：本文當 [linearizability](/backend/knowledge-cards/linearizability/) 卡片的 vendor 應用範例

## 寫作前置 checklist

- [ ] case anchor 確認：9.C10 Spanner 為主（Google internal dogfood、不是 customer-facing capacity）、其他系統當對照組（PostgreSQL SSI / CockroachDB / Aurora DSQL）都不需強案例
- [ ] Line-rate scaling 對照表就位（finding F3.14）：扣商業邏輯先行 frame、回答「為什麼 Spanner 不只是更強 serializable」
- [ ] Cross-region quorum 100-200ms anchor 明示（finding F3.15）：明示是 9.C10 case 揭露的數字、附條件「跨洲多 region instance、實際依 region 配置」
- [ ] Dogfood 邊界明示（finding F3.17）：9.C10 引用時都標「Google internal dogfood、不是 customer SLA 承諾」
- [ ] SSoT 對齊：Strong + multi-region 互斥議題 cross-link 到 cosmosdb/consistency-levels-engineering、本篇不展開
- [ ] knowledge card 雙引用：linearizability + external-consistency + isolation-level 三張卡互引
- [ ] sibling 對比：concept-driven 文章、不需 production case 主導；用 anomaly example（write skew / G2）替代
- [ ] 預估寫作長度：320-380 行（三概念定義 + 對照表 + 反例展開 + line-rate scaling 對照 + cross-region quorum 數量級）
