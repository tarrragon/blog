# Cosmos DB 5 Consistency Levels：工程選擇邏輯

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：Cosmos DB 文件列 5 個 consistency level（Strong / Bounded staleness / Session / Consistent prefix / Eventual）、團隊要選一個當 account 預設、又要決定哪些 query 要 override；文件用 PACELC 講概念、卻沒給具體工程判準
- 讀者徵兆：「Session 跟 Eventual 看起來差不多、為什麼 Session 是預設」「Bounded staleness 的 K 跟 T 該設多少」「Strong 在 multi-region account 為什麼有額外限制」「跨 region read 拿到舊版本、是 consistency 設錯還是 partition key 問題」
- 真實壓力：購物車 — 加入購物車後立刻看「我的購物車」、結果讀到舊狀態；遊戲 — 玩家位置同步、跨 region 看到「玩家瞬移」回舊位置
- Case anchor: [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)（用 session consistency 撐 AR 全球同步）、[9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)（Black Friday 用較弱 consistency 換 throughput）

## 核心機制（Vendor-specific mechanism）

- 5 level 的精確語義：
  - **Strong**：read 拿到最新 commit；single-write region 限制；multi-region write 不可同時用 Strong（時間敏感 claim、查最新文件）
  - **Bounded staleness**：read 落後不超過 K 個 version 或 T 秒；單 region 內 linearizable、跨 region 有 bounded lag
  - **Session**：同一 session token 內讀寫一致；session 之外 eventual；*多數互動式產品的甜蜜點*
  - **Consistent prefix**：read 不會看到亂序的寫入（看到 A→B→C、不會看到 A→C→B）、但可能落後
  - **Eventual**：最便宜、無順序保證
- 跟 Cosmos DB account / container 的關係：account 預設一個 level、單一 request 可以 *降級*（讀更弱）、*不可升級*（讀更強）
- RU 成本差異：Strong / Bounded read ≈ 2x Session / Eventual；write 成本不直接受 read level 影響、但 multi-region replication 開銷會
- 跟通用 [consistency-level](/backend/knowledge-cards/consistency-level/) 卡片的對應：Cosmos DB 是少數把 5 level 都「商品化」的服務、其他系統通常只給 2-3 級
- 跟 [linearizability](/backend/knowledge-cards/linearizability/) 的關係：Strong = single-region linearizable、不是跨 region external consistency（跟 Spanner 不同）
- 對應 knowledge card：[consistency-level](/backend/knowledge-cards/consistency-level/)、[linearizability](/backend/knowledge-cards/linearizability/)、[stale-read](/backend/knowledge-cards/stale-read/)

### 進階設計策略：同一 application 內不同操作選不同 level

- 9.C11 Minecraft Earth 平台特性「一致性是 spectrum、不是 binary」段揭露：AR 遊戲玩家位置稍 stale OK（用 session / eventual）、庫存交易需要 strong；同一 application 內不同 collection / container 配不同 consistency 是進階策略、不一定是 account 一刀切
- 用 RequestOptions per-request override 把「寫入後立即讀」場景升 Bounded、批次分析降 Eventual；container 層無法獨立設定（時間敏感、查最新文件）、所以分流靠 *collection 切分* + *per-request override*
- 配合 [partition-key-design](./partition-key-design.md)：partition 失衡時即使 Strong 也看到 throttle、consistency 跟 partition 共同決定真實一致性體驗

### SSoT 對齊備註

- **Strong + multi-region write 互斥** 議題的主寫位置是 [multi-region-write-conflict](./multi-region-write-conflict.md)（容量觀測 + AP 取捨敘事）；本篇 Strong 段只說明「single-region linearizable / multi-region write 互斥」一句、cross-link 過去、不重複展開 conflict resolution 細節（依 _module-outline.md Section G SSoT 規則）

## 操作流程（Operations）

- account 層設定：portal / ARM template / CLI `az cosmosdb update --default-consistency-level Session`
- request 層 override：SDK 傳 `RequestOptions.ConsistencyLevel`（C# / Java / Node SDK 行為一致）
- Session token 管理：每個 read response 帶 session token、client 下次 read 帶回去；跨 service 共享 token 需顯式傳遞（不然每個 service 自己一個 session）
- 驗證 level 行為：寫入後立即 read 同 partition key、量 staleness window
- 驗證點：用 Cosmos DB Diagnostic Log 看 request 的實際 consistency level；對照 SDK 設定確認沒被預設 override
- Rollback boundary：account 預設可改、但 production 切換 level 需要 audit 所有 client 的 session 邏輯；container 層無法獨立設定（時間敏感、查最新文件）

## 失敗模式（Failure modes）

- 全用 Strong：互動式產品其實 Session 就夠、用 Strong 浪費 2x RU + 限制 multi-region write、cost 暴漲且 multi-region 配置受限
- Session token 沒回傳：read 後拿 token、下次 read 沒帶、實際變 Eventual；徵兆是「自己的寫立刻 read 看不到」、debug 才發現 SDK 設定漏
- 跨 service 共享 session 假設：service A 寫、service B 讀、B 沒拿到 A 的 session token → 看不到 A 的寫；解法是 session token 隨 request 傳遞（通常進 header）或改 account 層 Bounded staleness
- Bounded staleness 設太鬆：K = 100000、T = 1 hour、實際等於 Eventual、團隊以為自己有保護
- multi-region write 配 Strong：文件不允許 / 行為退化（時間敏感、查最新）— 必須改 Bounded / Session
- Consistent prefix 誤用：把它當 Session 用、跨 session read 還是 stale、但比 Eventual 多一個順序保證；用錯地方等於浪費

## 容量與觀測（Capacity & observability）

- 必看 metric：Cosmos DB `NormalizedRUConsumption`、`TotalRequestUnits`、`ReplicationLatency`（跨 region lag）；Diagnostic Log 看每個 request 的實際 consistency
- 成本計算：Strong / Bounded read 算 2x RU；multi-region 開後寫入成本 × region 數；level 跟 region 數的 cost matrix 是規劃必算
- 回到 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：把 consistency level 當「RU 倍數」進入容量公式
- Alert：`ReplicationLatency` 突增（跨 region 同步異常）；diagnostic log 偵測 Strong read 突增（成本失控）

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[partition-key-design](./partition-key-design.md)（partition key 跟 consistency 共同決定真實一致性體驗）、[ru-cost-model-sizing](./ru-cost-model-sizing.md)（RU 倍數量化）、[multi-region-write-conflict](./multi-region-write-conflict.md)（multi-region 下 consistency 的特殊行為）
- Migration playbook 連結：[mongodb-api-vs-sql-api](./mongodb-api-vs-sql-api.md) 的 migration audit 要明確 MongoDB read concern 對應 Cosmos DB 哪個 level
- 跟 1.x 章節：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 把 Cosmos DB 5 level 跟 Spanner external consistency 並陳
- Anti-recommendation：別把 Cosmos DB Strong 跟 Spanner external consistency 等同視之；產品需要真正全球 linearizable transaction 時、Cosmos DB 不是替代品

## 寫作前置 checklist

- [ ] case anchor 確認：9.C11 Minecraft Earth（session）+ 9.C21 ASOS（高 throughput + 較弱 level）為主案例
- [ ] knowledge card 雙引用：consistency-level、linearizability、stale-read
- [ ] sibling 對比：Spanner external consistency、DynamoDB strong/eventual、MongoDB read concern majority
- [ ] 預估寫作長度：280-340 行（5 level × 工程判讀 + 5 失敗模式）
