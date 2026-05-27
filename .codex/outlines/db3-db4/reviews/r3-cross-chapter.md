# R3：跨章一致性 Review Report

## Overall 跨章健康度

31 篇跨章一致性整體在 **8.0/10** — SSoT 對應規則大致到位、Frame 1-8 多數有覆蓋、cross-link 結構清晰、reader Layer 2/3 路徑流暢、vendor 間對比沒明顯矛盾。但有 **三個 critical batch-wide 議題**會影響讀者旅程跟模組外部界面：

1. **Reader Layer 1 → Layer 2 路徑斷裂**：vendor `_index.md`（6 份 + vendors/_index.md）跟新增的 31 篇 deep article 之間沒有任何連結，readers 從 vendor overview 進不了 deep article、`db3-vendor-selection.md` 跟 `aurora-dsql-spanner-decision-tree.md` 兩個 entry article 也不被任何 `_index.md` 指向 — Layer 1 整層架構在書面上不存在
2. **Spanner consistency-models-comparison 的 SSoT 指向錯誤**：兩處（line 101 / line 193）標 Strong + multi-region 互斥的 SSoT 是 `cosmosdb/consistency-levels-engineering.md`，但實際 SSoT 是 `cosmosdb/multi-region-write-conflict.md`（後者展開議題、前者 cross-link）— 跨章 SSoT 表述漂移、讀者跟著 link 跳到的不是真正的展開位置
3. **章節編號漂移 3 處**：MongoDB schema-design-pattern 寫「1.4 transaction boundary」（正確 1.3）、MongoDB change-streams-kafka 寫「1.6 schema migration rollout evidence」+「1.7 reconciliation data repair」（正確 1.7 / 1.9）、CockroachDB hlc-raft-consensus 寫「01.4 database migration playbook」（正確 1.6）

三維健康度：

- **SSoT 對應**：8/10（4 大議題主寫位置都正確展開，1 處 Spanner 反向 link 錯）
- **Cross-link 雙向 + 路徑正確**：6/10（章節編號 3 處漂移 + vendor `_index` 完全沒指向新 deep article + Frame 8 跨 vendor link 不對稱）
- **Frame 1-8 覆蓋**：8/10（多數 frame 在多篇被引用、表述一致、少數 frame 跨 vendor link 缺失）

## SSoT 對應檢查結果

### Strong + multi-region 互斥（4 大議題之一）

**SSoT 主寫位置**：`cosmosdb/multi-region-write-conflict.md`

- ✓ 主寫位置展開充分（line 29-44「AP 取捨的硬約束」段 + 3 種 conflict resolution policy + LWW / custom merge / conflict feed 完整實作）
- ✓ 主寫位置明示「本篇是 SSoT 主寫位置」（line 44）
- ✓ `cosmosdb/consistency-levels-engineering.md` 正確 cross-link 不展開（line 9 / line 39「詳見 multi-region-write-conflict.md 的 AP 取捨段、本篇不展開」、line 203）
- ✗ **`spanner/consistency-models-comparison.md` line 101 / line 193 寫 SSoT 在 `cosmosdb/consistency-levels-engineering.md`、實際 SSoT 在 `cosmosdb/multi-region-write-conflict.md`** — 讀者跟著 link 跳過去看到的是 cross-link 段、不是展開段
- ⚠ **`_module-outline.md` Section G 跟實作有衝突**：Section G 表格寫 SSoT 在 `consistency-levels-engineering.md`、實作改成 `multi-region-write-conflict.md`。實作的選擇較合理（議題 = conflict resolution、放在 multi-region-write-conflict 更精準），但 outline 跟實作沒對齊 — outline 應更新、Spanner 文章 SSoT 指向也應修

### Aurora fleet 治理（4 大議題之二）

**SSoT 主寫位置**：`aurora/read-replica-scaling.md` 邊界段

- ✓ 主寫位置展開充分（line 241-303「Fleet 治理 SSoT」段、含 3 條 driver 表格 + 各 driver 展開 + 何時拆 vs 加 replica 判讀順序 6 條）
- ✓ 主寫位置明示「本段是 Aurora fleet 治理軸 SSoT」（line 243）
- ✓ 所有 4 篇 sibling Aurora outline 正確 cross-link 不重複展開：
  - `storage-architecture.md` line 245-251 有 fleet 簡介 + 明示「SSoT 在 read replica scaling 邊界段」
  - `cross-az-failover-rto.md` line 211 / line 259 兩處 cross-link
  - `global-database-multi-region.md` line 195 / line 297 兩處 cross-link
  - `migrate-from-self-managed-pg-mysql.md` line 11 / 84 / 364 / 374 / 402 / 423 多處 cross-link
- ✓ 跨 vendor cross-link 完整：`cockroachdb/locality-aware-schema.md` line 172 + 311 引 Standard Chartered Aurora 7 cluster fleet 作對照，路徑正確
- 評：這是 4 個 SSoT 議題中 cross-link 紀律最好的一個

### CockroachDB cluster boundary 顆粒（4 大議題之三）

**SSoT 主寫位置**：`cockroachdb/aurora-dsql-spanner-decision-tree.md`（per-app vs shared cluster 決策軸）

- ⚠ 主寫位置 **沒有專門展開 per-app vs shared cluster 決策軸** — outline 預期該軸主寫在這篇，但實際內容偏「三家 vendor 對比 + driver path 分型」、cluster boundary 顆粒議題散落在 team size（line 204-216）+ self-managed Netflix Database Platform Team frame、不是顯式主寫
- ✓ `hlc-raft-consensus.md` line 211「per-app cluster vs shared cluster 的決策軸主寫於 aurora-dsql-spanner-decision-tree、本篇 cross-link 不展開」— cross-link 標示正確
- ✓ `survival-goals.md` line 233 cross-link、`locality-aware-schema.md` line 292 cross-link
- 建議：aurora-dsql-spanner-decision-tree.md 補一段「cluster boundary 顆粒：何時拆獨立 cluster vs 邏輯一個 cluster」、把 Hard Rock（邏輯一個 cluster）vs Netflix（380+ 微服務私有 cluster）vs Standard Chartered（fleet）三條路徑顯式對比、否則 SSoT 對應只是 link 紙面成立、議題實際沒被「主寫」

### Document model 三型遷移路徑（4 大議題之四）

**SSoT 主寫位置**：`cosmosdb/mongodb-api-vs-sql-api.md` 開頭段

- ✓ 主寫位置展開充分（line 29-41「Framing 1：document model 三型遷移路徑對照」段、三型 frame + 風險 + ROI + scope warning 完整）
- ✓ 主寫位置明示「三型 frame 是本章合成、case 原文沒有此分類」（line 39）
- ✓ DB3 entry article 也展開三型（`db3-vendor-selection.md` line 64-111）— **這個是設計取捨**：entry article 為 reader Layer 1 路由需要先做三型分型、跟 mongodb-api-vs-sql-api 同議題不同 framing 切入，兩處內容不完全重複（前者為選型路徑、後者為 Cosmos DB 視角的選型決策）— 但需檢視兩處說法是否有漂移
- ⚠ **檢視兩處說法**：DB3 entry article 三型（保留 + 補周邊 / 同 DB 換託管 / 換 vendor 保留 model）vs mongodb-api-vs-sql-api 三型（保留主 DB 補周邊工具 / 同 DB 換託管 / 同 model 換 vendor）— 字面對齊、無漂移
- ✓ `mongodb/schema-design-pattern.md` line 195-196 cross-link 三型對照
- ⚠ MongoDB sibling deep article 沒有明示 SSoT 在 mongodb-api-vs-sql-api、只是順帶提 Coinbase / Forbes / Microsoft 365 三 case — 跨 vendor cross-link 紀律弱、不像 Aurora fleet 那麼明確

## 跨 vendor 共通 frame 一致性檢查

### Frame 1：vendor 適用度前置判讀條件

- ✓ DynamoDB single-table 開頭 4 軸前置判讀展開充分（line 13-50「DynamoDB 適用度前置判讀」）
- ✓ DB3 entry article 3 軸前置判讀展開（軸 1 資料形狀 / 軸 2 access pattern / 軸 3 consistency）
- ⚠ MongoDB outline 集體缺前置判讀段 — schema-design-pattern 從「contract layer 在哪」切入、shard-key-selection 從「shard key 選型」切入、沒有明確的「MongoDB 適用度 3 條」前置判讀；對照 DynamoDB single-table 形成不對稱
- ⚠ Cosmos DB mongodb-api-vs-sql-api 從「四層問題」切入但沒明確的「Cosmos DB 適用度前置判讀」段
- Aurora migrate-from-pg-mysql、Spanner migrate-from-cloud-sql-pg、CockroachDB decision-tree 都有明確的 driver / no-go 段、覆蓋此 frame
- 評：DynamoDB 套用 frame 最完整、MongoDB / Cosmos DB 偏弱

### Frame 2：vendor 選型 / migration 路徑分型

- ✓ Cosmos DB mongodb-api-vs-sql-api.md 是 SSoT、三型展開充分
- ✓ DB3 entry article 三型展開
- ✓ Aurora migrate-from-pg-mysql 走 Type B drop-in / Type F topology re-layout 對照
- ✓ Spanner migrate-from-cloud-sql-pg 明示 paradigm shift（Type E）
- 評：覆蓋好、跨 vendor 表述一致

### Frame 3：fleet 治理 vs single instance

- ✓ Aurora read-replica-scaling SSoT 主寫
- ✓ CockroachDB locality-aware-schema 對照 Standard Chartered fleet 跟 Hard Rock 邏輯一個 cluster
- ⚠ MongoDB shard-key-selection 提到 Toyota 20 DB blast radius、但沒做完整 fleet vs single cluster 對比
- ⚠ DynamoDB 5 篇都沒明確「fleet 治理」視角（DynamoDB 本身單一 table 跨 region 模型不同、可能不適用 fleet frame、但應顯式說明 frame 在 DynamoDB 退化）
- 評：Aurora + CockroachDB 對 frame 3 收斂、MongoDB / DynamoDB 偏弱

### Frame 4：capacity 抽象單位思維差異

- ✓ Cosmos DB ru-cost-model-sizing 補「RU 思維 vs CPU+IOPS 思維」學習曲線
- ✓ DynamoDB on-demand-vs-provisioned 走「mode 選擇 + adaptive capacity」
- ✓ CockroachDB hlc-raft-consensus per-cluster 容量段、aurora-dsql-spanner-decision-tree 加 sizing barrier
- ⚠ MongoDB connection-management-and-cache-layer 走「CPU + IOPS + working set RAM」三軸但沒明示這是 vendor 思維對比的一個點
- DB3 entry article 對比表 line 148 直接列出三家 capacity 抽象差異、跟 outline Section B Frame 4 對齊
- 評：覆蓋一致、frame 4 在 DB3 entry 跟各 vendor outline 之間有對應

### Frame 5：合規邊界

- ✓ Aurora global-database-multi-region 明示「合規禁止跨境 → 用 fleet 不用 Global Database」anti-recommendation
- ✓ CockroachDB locality-aware-schema 從 Hard Rock concrete case 主導（line 30 + 172）+ 補 Outposts 是合規工具不是 latency 工具的反直覺判讀
- ✓ Aurora migrate-from-pg-mysql line 54 明示合規 no-go condition
- ⚠ DynamoDB global-tables-conflict 沒展開合規邊界視角（DynamoDB 用 region-pinned global table 吸收合規、case 9.C24 Genesys 15 region 應該對應 outline Section B Frame 5 但 outline 沒明示）
- 評：Aurora + CockroachDB 對 frame 5 收斂、DynamoDB 偏弱

### Frame 6：production 跨層架構

- ✓ MongoDB connection-management-and-cache-layer 是這個 frame 的 SSoT（Coinbase mongobetween + freshness token + ML predictive scaling 三件套）
- ✓ MongoDB replica-set-read-preference 走 DB 層 causal session vs cache 層 freshness token 對照
- ✓ DynamoDB single-table-design-pattern line 185-198 控制平面 vs 資料平面段
- ✓ Cosmos DB consistency-levels-engineering 跨 service session token 管理段
- 評：MongoDB 對 frame 6 處理最深、DynamoDB 跟上、其他 vendor 偏弱（合理、因 Coinbase 是這個 frame 的 rich case）

### Frame 7：vendor 數字口徑紀律

- ✓ Spanner 4 篇都明示 9.C10 dogfood 邊界（truetime-api-depth line 21、consistency-models-comparison line 19、migrate-from-cloud-sql-pg line 34、schema-migration-interleaved-tables line 19）
- ✓ DynamoDB on-demand-vs-provisioned line 245「指標口徑紀律」段、明示 9.C5 / 9.C20 / 9.C18 不同口徑
- ✓ DB3 entry article 反模式 5（line 196-200）明示「誤判 dogfood case 數字」
- ✓ Cosmos DB mongodb-api-vs-sql-api 明示 Microsoft 365 dogfood scope warning
- ✓ Aurora read-replica-scaling line 211 + 229-234 明示 FanDuel scope warning + DraftKings 200 cluster 加總 vs 單 cluster 警示
- 評：覆蓋完整、紀律統一、是 frame 中最一致的一個

### Frame 8：event-driven scaling 5 模式

- ✓ DynamoDB on-demand-vs-provisioned line 253-263 完整列出 5 種模式（flash-sale / predictable / sustained / season / surge baseline / B2B 高可用）— 跟 outline Section B Frame 8 對齊
- ⚠ Aurora read-replica-scaling 事件分級表只覆蓋體育博彩 cycle（平日 / playoff / championship / Super Bowl）— 沒明示「跟 DynamoDB on-demand frame 8 共寫」、沒列出 5 模式對應、只用 FanDuel 視角切入
- ✗ **Frame 8 雙向 cross-link 不對稱**：DynamoDB on-demand-vs-provisioned line 275 寫「跟 Aurora read-replica-scaling 共軸 cross-link」、但 Aurora read-replica-scaling 沒有 reverse link 回 DynamoDB on-demand — outline Section G「Frame 8 共寫、各自 vendor 視角切入、cross-link 即可」紀律單向成立
- 評：DynamoDB 端展開完整、Aurora 端片段、frame 對齊不足、應補 Aurora 端 reverse cross-link 跟 5 模式對應

## Reader journey 三層架構檢查

### Layer 1 — vendor 選型層

**狀態**：✗ **路徑斷裂**

- ✓ DB3 entry article（`db3-vendor-selection.md`）跟 DB4 entry article（`cockroachdb/aurora-dsql-spanner-decision-tree.md`）內容上承擔 Layer 1
- ✗ **vendor `_index.md`（6 份）沒有任何指向 entry article 的 link**：reader 從 vendors/_index.md 表格進到 mongodb/_index.md、找不到「先看 DB3 cross-vendor selection」的入口
- ✗ **vendors/_index.md 的「DB3 / DB4 撰寫 backlog 排序建議」段（line 90-153）描述當前 deep article 還是規劃中**、但實際 31 篇已寫完 — 文檔過時、跟 reader 真實看到的內容矛盾
- ✗ **vendors/_index.md「內容覆蓋進度」表（line 37-47）DB3/DB4 vendor 行全寫「—」**、實際每個 vendor 都有 5-6 篇 deep article

### Layer 2 — 機制深化層

**狀態**：✓ **路徑流暢**

- 各 deep article 之間 sibling cross-link 大致完整（Cosmos DB sibling 連結最完整、Aurora 次之、CockroachDB 良好）
- 內部章節展開合理、每篇都有「邊界與整合 / 相關連結」段做下一步路由
- 跨 vendor cross-link 路徑正確（Aurora fleet ↔ CockroachDB locality、Cosmos DB Strong ↔ Spanner external consistency 等）

### Layer 3 — production 跨層架構層

**狀態**：✓ **路徑流暢、有少量缺口**

- ✓ MongoDB connection-management-and-cache-layer 承擔 frame 6 SSoT
- ✓ DynamoDB single-table-design-pattern 補 durable queue / write buffer 正向用例 + control plane / data plane
- ✓ Aurora read-replica-scaling 承擔 fleet 治理
- ⚠ Spanner / Cosmos DB 沒專門承擔 production 跨層架構文章、但屬 layer 3 在這兩 vendor 的退化形式（vendor 自己更 self-contained）— 可接受

### 整體 reader journey 流暢度

Layer 2 → Layer 3 流暢、Layer 1 是 batch 中最大的結構缺口。Reader 從外部進來時看不到 entry article，從 vendor _index.md 也找不到 deep article — Layer 1 的設計實作了 Layer 2/3，但沒實作 Layer 1 自己的「入口」。

## Vendor 之間對比一致性

### DynamoDB / MongoDB / Cosmos DB 三 vendor 對比

- ✓ DB3 entry article 三 vendor 對比 10 軸（line 142-156）跟各 vendor 自己文章說法一致
- ✓ 「Partition / shard key 可逆性」軸（MongoDB 可改 / DynamoDB 可 backfill / Cosmos DB 不可改）— 跟 cosmosdb/partition-key-design 一致
- ✓ 「Multi-region write」軸（MongoDB 手動 conflict / DynamoDB LWW / Cosmos DB multi-region write 跟 Strong 互斥）— 跟 cosmosdb/multi-region-write-conflict + dynamodb/global-tables-conflict 一致
- ⚠ Cosmos DB 「Dogfood signal」軸寫「Microsoft 365 dogfood」、DynamoDB 寫「Amazon 自家高頻使用」、MongoDB 寫「無（MongoDB 是獨立公司、不適用）」— 表面對等、但 Microsoft 365 跟 Amazon Ads 的 dogfood 性質不同（Microsoft 365 是 dogfood / 不公開數字、Amazon Ads 是 production customer 但同公司 / 數字部分公開）— 應該在 DB3 entry article 對比表加 scope warning 註腳區分

### Aurora / Spanner / CockroachDB 三 vendor 對比

- ✓ `aurora-dsql-spanner-decision-tree.md` 三家對比跟各自 vendor 文章說法一致
- ✓ 「Consensus 機制」軸（HLC + Raft / TrueTime + Paxos / 類 Spanner）跟 hlc-raft-consensus + truetime-api-depth 一致
- ✓ 「PostgreSQL 相容性」軸（CockroachDB wire / Aurora DSQL native PG / Spanner GoogleSQL + PG dialect）跟各 vendor 文章一致
- ✓ Sizing barrier（Spanner 100 pu）frame 在 aurora-dsql-spanner-decision-tree + spanner/migrate-from-cloud-sql-pg 表述一致

### Anti-recommendation 跟 sibling vendor use case 對齊

- ✓ Aurora global-database 「合規禁止跨境 = anti-recommendation」 ↔ CockroachDB locality-aware-schema 「合規驅動拓樸」use case 對齊
- ✓ Cosmos DB anti「不是跨雲服務」 ↔ MongoDB 「Atlas 跨雲」use case 對齊
- ✓ DynamoDB single-table「access pattern 變動快不適用」 ↔ DB3 entry「資料模型還在探索回 PG + JSONB」use case 對齊
- ✓ Spanner consistency-models-comparison anti「我們需要強一致 ≠ 升 Spanner」 ↔ CockroachDB aurora-dsql-spanner-decision-tree「single-region OLTP 不該換 distributed SQL」use case 對齊

整體：DB3 / DB4 vendor 對比說法一致、沒明顯矛盾。一致性紀律是 batch 強項。

## Cross-link 失效或漂移

### 章節編號漂移（3 處）

- ✗ `mongodb/schema-design-pattern.md` line 198：「1.4 transaction boundary」 → 應為 **1.3**（transaction-boundary.md weight: 3）
- ✗ `mongodb/change-streams-kafka.md` line 182：「1.6 schema migration rollout evidence」 → 應為 **1.7**（schema-migration-rollout-evidence.md weight: 7）；「1.7 reconciliation data repair」 → 應為 **1.9**（reconciliation-data-repair.md weight: 9）
- ✗ `cockroachdb/hlc-raft-consensus.md` line 232：「01.4 database migration playbook」 → 應為 **1.6**（database-migration-playbook.md weight: 6）

每處 link target slug 都正確、僅是 prefix 編號顯示錯誤。讀者跟著 link 跳得到正確頁面、但編號跟章節 weight 不對齊會造成 SSoT 認知漂移。

### 跨 vendor cross-link 漂移（1 處）

- ✗ `spanner/consistency-models-comparison.md` line 101 / line 193：「Strong + multi-region 互斥議題的 SSoT 是 Cosmos DB consistency-levels-engineering」 → 實際 SSoT 在 `multi-region-write-conflict.md`，需修正兩處

### 既有非 31 篇文章未補 deep article entry（vendor _index.md）

vendor _index.md 沒指向新 deep article 不算「broken link」、但是 reader navigation 缺口。屬下一輪 batch 必補項。

### 不存在的章節編號引用

無 — 所有 1.x / 4.20 / 9.5 / 9.6 / 9.11 / 8.x 引用目標都存在。

## 跨篇修正建議

### Critical（影響 reader 體驗）

1. **修 vendor _index.md 路由**：6 個 vendor _index.md 加「下一步路由 / Deep article」段、列出本 vendor 的 5-6 篇 deep article + 指回 DB3 / DB4 entry article。同時更新 vendors/_index.md「內容覆蓋進度」表跟 backlog 段，把 31 篇已寫完的反映出來
2. **修 Spanner consistency-models-comparison SSoT 指向**：line 101 + line 193 把「cosmosdb/consistency-levels-engineering」改成「cosmosdb/multi-region-write-conflict」（兩處）
3. **修 3 處章節編號漂移**：mongodb/schema-design-pattern line 198 / mongodb/change-streams-kafka line 182（2 個編號）/ cockroachdb/hlc-raft-consensus line 232

### Recommended（一致性提升）

4. **修 _module-outline.md Section G 跟實作對齊**：把 Strong + multi-region 互斥 SSoT 從 `consistency-levels-engineering.md` 改成 `multi-region-write-conflict.md`（這是 outline 跟實作的衝突源頭、修 outline 比修文章更合理、因實作的議題切分更精準）
5. **補 Aurora read-replica-scaling 跟 DynamoDB on-demand-vs-provisioned 雙向 cross-link**：Aurora 端補 frame 8 5 模式對照 + reverse link 回 DynamoDB on-demand、跟 outline Section G「Frame 8 共寫」紀律對齊
6. **補 CockroachDB aurora-dsql-spanner-decision-tree 的 cluster boundary 顆粒主寫段**：把 Hard Rock 邏輯一個 cluster vs Netflix 380+ 微服務私有 cluster vs Standard Chartered 7 cluster fleet 三條路徑顯式對比、讓「per-app vs shared cluster 決策軸」議題真的被主寫，而不只是 SSoT 標籤

### Polish pass 候選

7. **DB3 entry article dogfood signal 對比表加 scope warning 註腳**：line 153 區分 Microsoft 365 dogfood / Amazon Ads same-company customer / MongoDB N/A 三種不同性質
8. **MongoDB 5 篇缺「MongoDB 適用度前置判讀」frame 1 段**：對照 DynamoDB single-table 開頭 4 軸 + Cosmos DB mongodb-api-vs-sql-api 四層、補 MongoDB-specific 3 軸前置判讀
9. **DynamoDB 5 篇缺「合規邊界」frame 5 段**：global-tables-conflict 可補 9.C24 Genesys 15 region 從合規視角切入、不只當高可用 frame
