# Round 6-B：Navigation Final Verification

> Frame: Round 6 navigation regression. Verify Polish 4 (f863de6 + 9652a9c) closed Round 5-B reader simulation 跟 Round 5-C outbound impact 兩條斷裂、4 reader journey 重跑 + Task A/B/C/D 抽樣 verify。只 review、不修檔。

## 評分變化軌跡

- R5-B baseline（reader journey）: B+/A-
- R5-C baseline（outbound impact）: F（斷裂）
- **Round 6-B 新分數：A / A-**（reader journey + outbound 主路徑接通、partition key 可逆性 SSoT 殘留為唯一中型 issue）

## Polish 4 verify

### Task A — vendors/_index.md SSoT 標 + 8 條 SSoT 清單

通過。覆蓋表 6 cell 加 SSoT 短標（L42-47）：

- L42 mongodb/schema-design-pattern `(SSoT Frame 1 MongoDB 適用度)`
- L43 dynamodb/single-table `(SSoT Frame 1 DynamoDB 適用度)` + on-demand-vs-provisioned `(SSoT Frame 8 event-driven scaling)`
- L44 aurora/read-replica-scaling `(SSoT Aurora fleet 治理 + Frame 8 共寫)`
- L46 cosmosdb/mongodb-api-vs-sql-api `(SSoT Document 三型遷移 + Cosmos Frame 1)` + multi-region-write-conflict `(SSoT Strong + multi-region 互斥)`
- L47 cockroachdb/aurora-dsql-spanner-decision-tree `(SSoT DB4 entry + cluster boundary 顆粒)`

新增「Cross-vendor SSoT 主寫位置」段（L51-64）列 8 條 SSoT、跟 multi-region-write-conflict.md L11 內 SSoT 自宣告對齊。跟 `_module-outline.md` Section G 6 條 SSoT 表對齊（G 是 outline-level SSoT、_index.md 是 article-level anchor、兩層不衝突）。

**殘留**：8 條 SSoT 沒列出「partition key 可逆性跨 vendor」SSoT — 此 frame 在 DB3 entry L160 / L172 + 3 deep article 各有對照表、但沒一處被 _index.md SSoT 列為主寫位置。

### Task B — DB3 entry「從 RDB 撞牆來的快速路徑」段

通過。位置正確（L113-121、第三型「換 vendor 保留 model」後、Federated DB 段前）。3 條撞牆訊號清晰：connection limit → single-table durable queue、單 primary 寫入上限 → DB4 entry Path A、單 DB 撐不下 → federated（Coinbase + Lemino）。反模式提醒 L121「connection limit 訊號必要但不充分、KV 適用度 4 軸還是要走完」對 R1 讀者明示前提門檻。

3 broken link 修完：dynamodb/single-table-design-pattern 用絕對路徑 `/backend/01-database/vendors/dynamodb/...`、Lemino slug 為 `ntt-docomo-lemino-japanese-streaming`（檔案實際存在）、cockroachdb/aurora-dsql-spanner-decision-tree 全絕對路徑。`mdtools cards content/backend/01-database/vendors/` 全綠。

### Task C — 17 case 反向 link（抽 10 sample）

通過。5 anchor case 全有：

- 9.C4 DraftKings → aurora/storage-architecture + aurora/read-replica-scaling（L55-56）
- 9.C23 Netflix Aurora → aurora/storage-architecture（L57）
- 9.C14 Standard Chartered → aurora/cross-az-failover-rto + global-database-multi-region + aurora-dsql-spanner-decision-tree（L51-53）
- 9.C5 Amazon Ads → dynamodb/partition-key-antipatterns + single-table-design-pattern（L49-50）
- 9.C10 Spanner → spanner/truetime-api-depth + consistency-models-comparison（L52-53）

5 其他 case 全有 link（Tixcraft 2 / Genesys 3 / Toyota 4 / Microsoft 365 2 / Coinbase 3）。額外抽 7 case（Zoom / Capcom / Disney+ / PayPay / Hard Rock / DoorDash / FanDuel）每篇都有 2-6 條 link、平均 2-3 條符合 commit message claim。

### Task D — 9 篇 1.x 反向 link（抽 3 高 impact）

通過。1.10 kv-document-capacity-planning L362-364 三條 link 涵蓋 DynamoDB 4 篇 + Cosmos DB 3 篇 + MongoDB 3 篇 deep article。1.11 global-distributed-oltp L344-347 四條 link 涵蓋 Spanner 3 篇 + CockroachDB 4 篇 + Aurora 2 篇 + Cosmos DB 2 篇。1.5 red-team-data-layer L353 link 到 Aurora global-database + 跨 AZ failover + Data Residency 知識卡。3 篇都在「下一步路由」段或對應主題段加 link、不是只在「相關章節」段堆。

## Manual reader test 4 reader

### R1：PG connection limit → KV

**R5-B baseline ⚠ → Round 6 ✓**。Polish 4-B 加 DB3 entry RDB 段 L113-121 直接打中 R1 路徑：vendors/_index.md → DB3 entry 第二段（已標 connection limit）→ 新「從 RDB 撞牆」段精準 route 到 single-table-design-pattern。verify single-table-design-pattern.md L212-215 確有 durable queue / write buffer 段。R1 從 entry 進深 article 的路徑 30 秒可走通、不再需要先讀 180 行 4 軸前置判讀。

### R2：全球 OLTP 三家比較

**R5-B baseline ✓ → Round 6 ✓+**。vendors/_index.md SSoT 段 L57 直指 multi-region-write-conflict SSoT、L47 標 aurora-dsql-spanner-decision-tree 為 DB4 entry SSoT、L51-62 提供 Strong+multi-region 互斥 + 跨 vendor frame anchor。R2 從 _index.md 點 DB4 entry 第一段就看到 Path A/B/C driver path、SSoT 標讓「我該讀哪篇」決策成本降低。

### R3：DBA Aurora fleet 治理

**R5-B baseline ⚠（看不出 fleet）→ Round 6 ✓**。vendors/_index.md L44 read-replica-scaling 後直接帶 `(SSoT Aurora fleet 治理 + Frame 8 共寫)` 標籤、DBA 一眼識別。SSoT 段 L55 進一步描述「DraftKings 200 cluster fleet、何時拆 cluster vs 加 replica 的 6 條判讀順序」、明示這篇承擔 fleet 議題。R3 入口判讀斷裂完全閉合。

### R4：partition key 跨 vendor 比較

**R5-B baseline ⚠ → Round 6 ⚠（部分閉合）**。DB3 entry L160 + L172 確實承擔「Partition / shard key 可逆性」frame（10 軸對照表 + 軸延伸段）、cosmosdb/partition-key-design L80 + mongodb/shard-key-selection L74 各有「跨 vendor 對照」內部表。但：

- vendors/_index.md SSoT 段未列出 partition key 可逆性 SSoT
- 3 deep article（dynamodb/partition-key-antipatterns / cosmosdb/partition-key-design / mongodb/shard-key-selection）沒 cross-link 回 DB3 entry 對應軸、各自仍承擔內部對照表

R4 讀者從任一 deep article 進來、仍須自己回 DB3 entry 才能整合 frame。R5-B medium finding 3 部分閉合（DB3 entry 承擔 frame）、但 SSoT 角色未明示 + deep article 未 cross-link 回 SSoT。

## 新 issue（如有）

1. **partition key 可逆性 SSoT 未明示**（中、R5-B medium finding 3 殘留）：vendors/_index.md SSoT 段建議加第 9 條 `Partition / shard key 可逆性跨 vendor 對照：[db3-vendor-selection](db3-vendor-selection/) 軸 6 + 軸延伸段 — 三家不可逆性遞增`；dynamodb/partition-key-antipatterns / cosmosdb/partition-key-design / mongodb/shard-key-selection 在「可逆性對照」段加 cross-link「詳見 DB3 entry 跨 vendor 可逆性 SSoT」、各自只展開本 vendor 不可逆性具體含義。可進 Polish 5 處理、不阻擋 Round 6 簽收。
2. **「適用度前置判讀」block-quote 同質化**（低、R5-B 跨讀者 issue 2 殘留）：12+ 篇 article 同 banner 模式未變異、reader 麻痺感未處理。Polish 4 範圍未涵蓋、可作為長期可優化項。
3. **DB4 entry「Cluster boundary 顆粒」段位置標籤**（低、R5-B medium finding 4 殘留）：未verify 是否補「本段是已選 CockroachDB 後的拓樸決策」位置標籤。本輪未抽查。

## 預估評分

- **Round 6-B 路由滿足度：A / A-**
- 4 reader journey 中 3 條從 R5-B ⚠/✓ 升 ✓/✓+、1 條（R4）部分閉合
- R5-C outbound impact: F → A（17 case + 9 篇 1.x 反向 link 接通主路徑）
- 殘留 3 issue 都是中低風險、不阻擋簽收、可進 Polish 5 backlog
