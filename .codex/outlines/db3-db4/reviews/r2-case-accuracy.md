# R2：案例引用準確性 Review Report

> Stage 5 reviewer R2、維度 *案例引用準確性*。Review 範圍：31 篇 deep article + DB3 entry（commit `13b0c11` + Round 2 fixes `98c1e8d`）。對照 8 個陷阱（case-first methodology Stage 3）跟高 scope warning 篇要求。

## Overall 案例 fidelity 評分

**整體 case fidelity 推估：90-93%**（接近本方法論歷史最高 backend/04 的 92.9%、明顯高於 backend/05-07 batch 1 baseline 70-88%）。

**8 個陷阱分布**：

| 陷阱類型                          | Critical（編造） | High | Medium / Low  |
| --------------------------------- | ---------------- | ---- | ------------- |
| 1. Skeleton case 擴寫成 fact      | 0                | 0    | 1（次要量化） |
| 2. Medium case 實作層擴寫         | 0                | 0    | 0             |
| 3. Dogfood 數字當 benchmark       | 0                | 0    | 0             |
| 4. Rich case 觀察 vs 判讀分層失敗 | 0                | 0    | 1（次要分層） |
| 5. Case 自帶警示被刪              | 0                | 0    | 0             |
| 6. 跨 case 合成 frame 未明示      | 0                | 0    | 0             |
| 7. 通用工程估算 vs case 揭露混淆  | 0                | 0    | 0             |
| 8. 合成 frame 升級成 case 揭露    | 0                | 0    | 0             |

**總計 issue：~2 個 Low / Medium**（無 critical 編造、無 high）。Stage 4 Round 2 review fixes（commit `98c1e8d`）後、剩餘 issue 都是次要量化口徑、不是 frame / fact 錯位。

**最 critical 的 3 個發現**：

1. **沒有 critical 編造**。寫稿端的 scope warning labels（DoorDash 1.636M / Netflix +75% / FanDuel 5-10x / Microsoft 365 dogfood / Spanner 10億 dogfood / Standard Chartered 匿名）都明確保留 case 自帶警示原話。
2. **跨 case 合成 frame 一律明示**。所有合成段落（DB3 entry 三型遷移 / federated DB / partition key 可逆性對照 / CockroachDB transaction-retry / Aurora event 分級 / Cosmos DB 廣告 SLA vs 實測）都帶 `本章合成 frame、case 原文沒有此分類` / `跨 case 合成 frame` 明示。陷阱 8（07 batch 1 新發現）零殘留、是本批 audit 的最大進步。
3. **唯一較弱處**：MongoDB connection-management-and-cache-layer 在 case anchor 段（line 32）寫「60K → ~2K connections」、實際 case 表格揭露 `Deploy 時連線尖峰 ~60K` 跟 `mongobetween 後連線降幅 30K → ~2K` 兩個獨立 row、文章把兩者壓成一句。屬陷阱 4 邊界（觀察口徑壓縮、case 自己用兩段描述）— Low issue。

## 各篇案例引用 issue 清單

### DynamoDB（5 篇）

#### `single-table-design-pattern.md`

No critical issue、案例引用 fidelity 高。9.C15 / 9.C29 / 9.C18 / 9.C19 引用都明示「access pattern 凍結場景」邊界、Lemino connection limit / control plane vs data plane / partition key 天然均勻三軸都帶 case 原文支撐。

#### `partition-key-antipatterns.md`

No critical issue。「shard 數 10-100、單 logical key 峰值 WCU 除以 800」明確標為通用工程估算（line 69）、9.C15 Tixcraft 引用嚴守「揭露概念、未揭露具體 shard 數」紀律（line 184「case 揭露概念、未揭露具體 shard 數」）。Tixcraft 案例的 composite key 寫成 `event_id#shard` 範例符合 case 策略段「composite key（event_id + user_id_hash）或 write sharding（event_id + random_suffix）」原文範圍、未編造「Tixcraft 用 X 不用 Y」這類 case 未揭露的決策。

#### `gsi-lsi-design.md`

No critical issue、處理 Capcom DAX 是 derive 的紀律到位。4 處 scope warning（line 26 / 106 / 139 / 145 / 177 / 185）。**最關鍵**：「Capcom DAX 是判讀層 derive、不是 case fact」(line 47) + 「Lemino DAX 是 case 直接揭露」分層清楚、避免 F1.8 提醒的「DAX 是作者判讀層、Capcom 沒公開使用」陷阱。

#### `on-demand-vs-provisioned.md`

No critical issue。3 個明確 scope warning：「peak/avg > 5x」屬經驗值（line 44）、「4-8 週 / 70% 閾值」是通用工程估算（line 67）、「scheduled scaling 30-60 分鐘」屬經驗值（line 85）。指標口徑紀律段（line 245）明示 9.C5 / 9.C20 / 9.C18 數字的口徑邊界、符合 Frame 7 要求。

#### `global-tables-conflict.md`

No critical issue、4 個 scope warning（line 33 / 116 / 136 / 166）。9.C24 Genesys 99.999% 揭露「滾動指標非永久承諾」明示（line 33 對應 F1.10 原話）、PayPay idempotency 寫法降溫成「PayPay 揭露需求分層、idempotency 為通用工程實作」（line 116 對應陷阱 4 處理）、DynamoDB Streams 標明 case *沒* 明示用 Streams（line 136）— 紀律完整。

### MongoDB（6 篇）

#### `schema-design-pattern.md`

No critical issue。Toyota time-series collection 標明「case study 沒揭露、不可寫成 Toyota 使用 time-series collection」（line 64）— 完全對齊 F2.8 要求。Forbes abstraction layer 引用扎實、跨 case 合成 frame 明示「本章合成、Toyota + Forbes 共同揭露」（line 42）。

#### `shard-key-selection.md`

No critical issue。「跨 case 合成 frame：橫向擴展不是只有 sharded cluster 一條路、多 cluster 是另一條路」明示（line 54）、Toyota 20 DB blast radius 對應扎實。

#### `replica-set-read-preference.md`

No critical issue。Causal consistency session（DB 層）vs freshness token（cache 層）對照 frame 對接 connection-management-and-cache-layer、不重複展開。

#### `aggregation-pipeline-optimization.md`

No critical issue、機制議題、findings 支撐弱（如 F2 outline 所述）但寫稿沒擴寫不存在的 case 細節。

#### `change-streams-kafka.md`

No critical issue、機制議題、無 case-driven 過度推論。

#### `connection-management-and-cache-layer.md`

**1 個 Low issue**（陷阱 4 邊界）：

- **Connection 數字口徑壓縮**：line 32 / 55 寫「60K → ~2K connections」、實際 case 表格（line 17-19）揭露 `Deploy 時 MongoDB 連線尖峰 ~60K connections/minute` 跟 `mongobetween 後連線降幅 30K → ~2K` 是 *兩個獨立的觀察口徑*、case 表格沒明說 60K 是被 mongobetween 縮成 2K。
  - case 原文 row 17-19 兩段口徑各自獨立、文章合成成一句「60K → ~2K」
  - 文章 line 17 跟 line 52 單獨寫「60K connections/min」對齊 case row 17（口徑：deploy 尖峰）— 這部分正確
  - 文章 line 32 case anchor + line 55 合併寫「60K → ~2K」屬「兩個觀察口徑」壓縮
- 嚴重程度：Low（case 警語段 line 39 寫「1.5M reads/sec 是合成」屬同一精神、但具體數字組合需要分行寫更精確）
- 影響：讀者可能誤以為 mongobetween 把 60K 直接降到 2K、實際 case 的兩個口徑是 deploy 尖峰 vs 一般 reduction
- 建議：line 32 / line 55 改成「mongobetween 把 connection 從 30K 降到 ~2K（一個量級）、deploy 尖峰 60K 也被同類機制收斂」

其他三處 scope warning（line 57 mongobetween Ruby+GVL 限定 / line 74 1.5M reads 含 cache / line 89 ML 預測有 false positive）都明確、跟 case 警語段一一對應。F2.2 + F2.4 + F2.5 三個 finding 整合扎實。

### Cosmos DB（5 篇）

#### `consistency-levels-engineering.md`

No critical issue、9.C11 + 9.C21 引用扎實、Strong + multi-region 互斥 SSoT 對齊到 multi-region-write-conflict。

#### `partition-key-design.md`

No critical issue、2 個合成 frame 明示（line 55 synthetic key 細節屬 outline knowledge 推論 / line 78 + 88 跨 vendor 可逆性對照本章合成）。

#### `ru-cost-model-sizing.md`

No critical issue、4 個合成 frame 明示（line 41 跨 vendor capacity 抽象差距 / line 122 random surge anchor / line 134 serverless 場景 / line 136 跨 4 case 合成表 / line 222 思維遷移成本）。9.C11 1M RU/s 壓測通過數字明示「壓測非持續、case 自己警示」（line 49）— 完整對應 F2.12 紀律。

#### `mongodb-api-vs-sql-api.md`

No critical issue、是本批 dogfood 紀律最高的篇之一。Microsoft 365 處理：

- 三型遷移路徑明示「本章合成、case 原文沒有此分類」（line 39）
- dogfood 是 selection signal 不是 production benchmark（line 43-57）
- 「100% wire compat」是行銷話術（line 162 + db3-vendor-selection.md line 105）
- 「不能拿 dogfood 數字當 benchmark」明示為 failure 5（line 178）

#### `multi-region-write-conflict.md`

No critical issue、廣告 SLA vs 實測可用性拆解標「本章合成 frame」（line 223）。

### Aurora（5 篇）

#### `storage-architecture.md`

No critical issue。Netflix +75% 處理符合 F3.9 要求：

- 「+75% 是跨多 workload 最大改善幅度、不是每個 workload 都 +75%」明示為 case 自帶警示原話（line 237-239）
- DraftKings 6ms / <1ms 作為 production reference number（F3.2 要求）
- 「韌性即性能」frame 引 case 判讀段第 2 點原話（line 48）

#### `cross-az-failover-rto.md`

No critical issue。Standard Chartered 處理：

- 「未公開是 PostgreSQL 還是 MySQL、未公開具體 cost 數字、屬『相關 case study』匿名對照」（line 213）明示
- 9.C14 「判讀」段第 1 點原話引用扎實

#### `read-replica-scaling.md`

No critical issue、是本批 scope warning 最密集的一篇：

- FanDuel 5-10x 是 betting 服務 Aurora 擴容倍數、不是 streaming（line 205-209）明示
- 「AWS 案例沒提具體 betting transaction TPS / concurrent streams / 延遲分布」case 自承段（line 211）保留
- 5-10x 是峰值倍數、不是 peak 持續時間（line 229-231）case 自帶警示保留
- Standard Chartered 「相關 case study」匿名標明保留（line 287）
- Netflix Cassandra / EVCache 邊界（line 275）case 自帶 scope 警示保留

#### `global-database-multi-region.md`

No critical issue。Standard Chartered anti-recommendation 引 case 「判讀」段第 1 點原話（line 186）、FanDuel 5-10x scope warning（line 217-220）。

#### `migrate-from-self-managed-pg-mysql.md`

No critical issue、是本批合規 lead time 處理最完整的篇：

- 合規 lead time 3-12 個月 + 7 市場 × 6 個月 ≈ 3.5 年最壞情況（line 259-260）明示為 Standard Chartered case 揭露範圍
- 「實際合規 lead time 隨產業 / 國家差異大、不是恆定數字、讀者要把自家對應監管框架實際 lead time 算進來」（line 271）case 自帶警示保留
- Netflix「Aurora 非 all-purpose store」邊界（line 351 + 358-359 不該遷的 workload 表）明示

### CockroachDB（5 篇）

#### `hlc-raft-consensus.md`

No critical issue、是本批 scope warning 最強的篇之一：

- DoorDash 1.636M QPS 在問題情境段（line 25）就明示「case 自己警示不是 CockroachDB throughput claim」
- write latency 預算明示「屬通用工程估算、case 未揭露具體數字」（line 213-215）
- 專門「DoorDash 1.636 M QPS 引用紀律」段（line 224-226）重申 case 自帶警示原話

#### `survival-goals.md`

No critical issue。Netflix Gaming 48-node 跨 4 region 揭露 line 74 明示「case 沒揭露具體 p99 數字」、write latency 預算屬通用工程估算 case 未揭露（line 189-191）。

#### `transaction-retry-pattern.md`

**No critical issue、是本批 scope warning 最徹底的篇**：

- Frontmatter description 直接寫「整篇是跨 case 合成 frame」（line 4）
- 開篇 blockquote scope warning 段（line 11）明示「3 個 CockroachDB direct case 都沒寫 40001 / SAVEPOINT cockroach_restart / hot row contention / retry loop pattern、本章從 Cockroach Labs 官方 SQL Layer docs + PG → CockroachDB 通用 contract 重塑視角合成」
- 專屬「Scope warning explicit label」段（line 28-36）明示正確引用口徑 vs 不能寫的合成口徑
- Case anchor 段（line 37-41）明示「trigger context、不是 ground truth」
- 核心機制段開頭「來源分層」（line 45）明示「機制來源是 Cockroach Labs 官方 SQL Layer docs + Transaction Retry docs (standard-driven)、不是從 case 抽取」
- 失敗模式末段「跨 case 合成 Scope warning」（line 254-258）明示 DraftKings 對照本身是合成
- 相關連結（line 329-330）標 DoorDash 為「trigger context — PG wire 相容警語」、DraftKings 為「合成對照 — Aurora sharding 路徑」

**統計**：6 處 explicit scope warning labels — 超過 5+ 處的 audit 要求。徹底符合 _module-outline.md Section E 對「最高 scope warning 篇」要求。

#### `locality-aware-schema.md`

No critical issue。「Outposts 是合規工具、不是 latency 工具」反直覺判讀明示（line 181-189）、Standard Chartered vs Hard Rock 對比 frame 處理扎實（line 162-179）— 完整對應 F4.10 + F4.13。

#### `aurora-dsql-spanner-decision-tree.md`

No critical issue：

- DoorDash 1.636M QPS scope warning（line 51）case 自帶警示原話
- 成熟度比對「3 case 都沒揭露成熟度比對、本軸依 case + vendor 公開文件 + 外部知識合成」明示來源層次（line 105）
- Hard Rock 50 人 / 10-20 工程師「機會成本不是節省支出」明示（line 207）符合 F4.14 紀律

### Spanner（4 篇）

#### `truetime-api-depth.md`

No critical issue、是本批 dogfood 紀律最完整的篇：

- Frontmatter description 直接帶「9.C10 Google internal dogfood」（line 4）
- Dogfood 邊界 blockquote 段（line 21）明示「10 億 req/sec 是 Google 全使用者加總、不是單一 instance 配額」
- Fact vs derive 分層警告段（line 23）明示「coordinator bottleneck → TrueTime + Paxos」frame 是合成 frame
- Case anchor 段（line 31）「dogfood 邊界明示」
- Fact source 分層警告段（line 45）明示 1-7ms 是 Google 2012 OSDI 論文 + Spanner 公開文件、不是 9.C10 case 直接揭露
- Commit wait ≈ 2ε 來源分層（line 61）明示來自論文 + 官方文件、不是 case
- 容量段（line 145）明示「2 → 4 nodes = 45K → 90K reads/sec 是 Google internal dogfood 線性模式、不是客戶 SLA 承諾」
- 邊界段（line 155）單 region workload 拿不到 dogfood benefit
- 文末 checklist（line 175）「每處引用都明示 Google internal dogfood、不是 customer-facing capacity」

**統計**：8 處 dogfood 邊界 explicit labels — 遠超 5+ 處要求。

#### `consistency-models-comparison.md`

No critical issue。Dogfood 邊界明示 4 處（line 19 case anchor / line 49 9.C10 揭露的線性擴展數字 / line 72 9.C10 揭露的數量級 / line 87 實際 latency 依 region 配置 scope warning）、line-rate scaling 對照表（line 57）明示「9.C10 揭露 dogfood 線性模式」邊界。

#### `schema-migration-interleaved-tables.md`

No critical issue。Case anchor 段（line 19）明示「缺案例。9.C10 未展開 schema migration 細節、且 9.C10 不是 customer-facing capacity reference、本文用通用 pattern + 官方文件 + 反向回 PostgreSQL Online Schema Change 對照、待後續 customer case audit 補強」— 完全符合 standard-driven + dogfood 分層紀律。

#### `migrate-from-cloud-sql-pg.md`

No critical issue。Sizing barrier 100 pu 起跳處理（line 30-45）+ 跨 region < 50ms write latency no-go（line 51）+ case anchor + dogfood 邊界段（line 68-70）明示「無強 customer case、9.C10 是 Google internal dogfood」、Standard Chartered 受監管 banking 對照（line 350）扎實。

### DB3 entry

#### `db3-vendor-selection.md`

No critical issue、是本批選型篇章 dogfood / wire compat / 跨 case 合成 frame 處理最完整：

- Migration path 三型段（line 64-66）明示「本段是跨 case 合成 frame、不是單一 case 揭露」
- Forbes 25% TCO scope warning（line 92）明示「Forbes 特定流量規模下數字、不普適」
- Microsoft 365 dogfood scope warning（line 103）明示「dogfood 是高權重 selection signal、但不是 production benchmark」
- 100% wire compat scope warning（line 105）明示「是 vendor 行銷話術、實際是某些 query pattern 下相容」
- Federated DB 段（line 113-115）明示「跨 case 合成 frame」
- 反模式 4 + 5（line 190-200）明示 federated 假設「全用 X」+ dogfood 誤判風險
- Dogfood signal vs production benchmark 反覆強調

## 跨篇 batch-wide 案例引用 pattern

### Dogfood frame 處理（Spanner / Cosmos DB / DynamoDB / DB3 entry）

**全部 4 處該明示的地方都明示完整**：

- Spanner 4 篇：truetime-api-depth（8 處）/ consistency-models-comparison（4 處）/ schema-migration-interleaved-tables（1 處明示缺案例）/ migrate-from-cloud-sql-pg（4 處）— *全到位*
- Cosmos DB mongodb-api-vs-sql-api：Microsoft 365 dogfood 在 framing 2 + failure 5 + 反覆強調 *全到位*
- DB3 entry db3-vendor-selection：Microsoft 365 + Amazon Prime Day + Google Spanner 三組 dogfood 同類處理 *全到位*
- DynamoDB Amazon Prime Day 雖然 9.C5 Amazon Ads 不是 dogfood、但「90M reads/sec 是年度峰值最高一秒」warning 在 on-demand-vs-provisioned / partition-key-antipatterns / global-tables-conflict 都保留

### Case 自帶警示保留（DoorDash / Netflix / FanDuel / Standard Chartered）

**全部保留、無一刪除**：

- DoorDash 1.636M QPS 警示在 hlc-raft-consensus / aurora-dsql-spanner-decision-tree / transaction-retry-pattern 三處都明示原話
- Netflix +75% 跨多 workload 警示在 storage-architecture / migrate-from-self-managed-pg-mysql 兩處明示
- Netflix「Aurora 非 all-purpose store」邊界在 read-replica-scaling / migrate-from-self-managed-pg-mysql 兩處明示
- FanDuel 5-10x betting only 警示在 read-replica-scaling / global-database-multi-region 兩處明示
- Standard Chartered 匿名 / 未公開 PG vs MySQL 在 cross-az-failover-rto / global-database-multi-region / read-replica-scaling / migrate-from-self-managed-pg-mysql 四處都明示

### 跨 case 合成 frame 明示「本章合成」

**全部跨 case 合成段落都帶明示標籤**：

- DB3 entry：migration path 三型 / federated DB / dogfood signal 三段都明示「跨 case 合成 frame」
- CockroachDB transaction-retry-pattern：整篇 frontmatter + 6 處 inline scope warning
- Cosmos DB partition-key-design / ru-cost-model-sizing：跨 vendor 可逆性對照 / capacity 抽象差距等都明示「本章合成、case 原文沒有此對比」
- Cosmos DB multi-region-write-conflict：廣告 SLA vs 實測可用性拆解明示「本章合成 frame」
- MongoDB schema-design-pattern：document model contract layer 三條路徑明示「本章合成、Toyota + Forbes 共同揭露」
- MongoDB shard-key-selection：blast radius 切分明示「跨 case 合成」

### 通用工程估算 vs case 揭露分層

**全部數字都帶來源層次明示**：

- DynamoDB partition-key-antipatterns：shard 數 10-100 / 800 WCU 留 buffer 明示「通用工程估算」（line 69）
- DynamoDB on-demand-vs-provisioned：peak/avg 5x / 4-8 週 70% / 30-60 分鐘 scheduled 三組數字明示「經驗值 / 通用工程估算」
- CockroachDB hlc-raft-consensus：single-region 3-5ms / multi-region 100-150ms 明示「通用工程估算、case 未揭露」（line 213）
- CockroachDB survival-goals：zone → region survival latency 跳變明示「通用工程估算、case 未揭露具體 latency 數字」（line 189）
- Spanner truetime-api-depth：commit wait ≈ 2ε 來源明示為 Google 2012 OSDI 論文 + 官方文件（line 45, 61）

## Fact vs derive 分層健康度

### 分層完整篇

- **CockroachDB transaction-retry-pattern**：陷阱 8 高風險篇、6 處 explicit scope warning labels、frontmatter 直接寫「整篇是跨 case 合成 frame」、來源層次明示完整。
- **Spanner truetime-api-depth**：8 處 dogfood 邊界 explicit labels、commit wait 數學 + ε 範圍 + line-rate scaling 三組數字都帶來源層次。
- **DynamoDB gsi-lsi-design**：「Capcom DAX 是 derive、Lemino DAX 是 case fact」分層明示、4 處 scope warning。
- **Aurora storage-architecture**：Netflix +75% 跨多 workload 警示原話保留、DraftKings 6ms / <1ms 作為 production reference 明示。
- **Aurora migrate-from-self-managed-pg-mysql**：合規 lead time 3-12 個月明示為 Standard Chartered case 揭露範圍、不是普適數字。

### 分層需要再加強的地方

- **MongoDB connection-management-and-cache-layer**：60K → ~2K 口徑壓縮為「兩個獨立觀察口徑」合成、line 32 / line 55 需要分行寫。Low issue、不影響 frame fidelity。

### Case 自帶警示保留 vs 被刪數量

**保留：~25 處（全部該保留的都保留）**

- DoorDash 警示 3 處 / Netflix +75% 警示 2 處 / Netflix all-purpose store 警示 2 處 / FanDuel betting only 警示 2 處 / Standard Chartered 匿名警示 4 處 / Microsoft 365 dogfood 警示 5 處 / Spanner 10億 dogfood 警示 8 處 / Forbes 25% TCO 警示 1 處 / Coinbase 1.5M reads/sec 含 cache 警示 2 處 / 9.C11 Minecraft Earth 100萬 RU/s 壓測警示 1 處 / Toyota time-series collection 未揭露警示 1 處 / Capcom DAX 是 derive 警示 3 處 / Hard Rock 50 人機會成本警示 1 處

**被刪：0 處**

### 跨 case 合成 frame 是否標明「本章合成」

**100% 標明**。本批 Stage 5 audit 是 case-first 方法論 7 個模組以來 *跨 case 合成 frame 紀律最徹底的 batch*。

## 需要新建 case 的位置（needs new case placeholder 檢查）

**MongoDB 5 個 incident 類缺口檢查**：

- **三代 schema 並存 incident**：在 schema-design-pattern.md case anchor 段（line 29）明示「早期 startup MongoDB 三代 schema 並存的具體 incident 細節需未來 case 補完、本文先以『常見 failure pattern』處理」— 正確標 placeholder、不編造。
- **Hot shard incident**：未在 shard-key-selection.md 顯式標 placeholder、但內容嚴守 9.C38 Toyota 揭露範圍、未編造 hot shard 具體事故敘事。
- **Aggregation pipeline 跑爆 incident**：aggregation-pipeline-optimization.md findings 支撐弱、寫稿沒擴寫不存在的 case 事故、走通用機制論述。
- **Stale read incident**：replica-set-read-preference.md 處理 causal consistency / freshness token 機制、不擴寫 stale read 具體 incident。
- **CDC resume token incident**：change-streams-kafka.md 處理機制議題、connection-management-and-cache-layer.md 邊界段（line 175）標明 CDC sink 在 federated DB 同步角色、未擴寫 resume token 失效具體 incident。

**Spanner schema migration 缺案例 placeholder 標明**：

- schema-migration-interleaved-tables.md case anchor 段（line 19）明示「缺案例。9.C10 是 Google internal dogfood case、未展開 schema migration 細節、本文用通用 pattern + 官方文件補強、待後續 customer case audit 補強」— 正確標 placeholder。

**整體 placeholder 紀律：完整**。31 篇文章沒有為了填 case anchor 而編造 incident、缺案例的地方明示「缺、待後續補」、不擴寫不存在的事故敘事。

## 整體評語

本批 31 篇 deep article + DB3 entry 的 *案例引用準確性* 是 case-first 方法論 7 個模組以來最高的 batch：

1. **零 critical 編造**、零 high issue、僅 1-2 個 Low（MongoDB connection 口徑壓縮）
2. **跨 case 合成 frame 紀律徹底**（陷阱 8 零殘留、7 batch 1 新發現的最大失分類型在本批完全防範）
3. **Dogfood 紀律完整**（Spanner / Cosmos DB / DynamoDB / DB3 entry 4 處該明示都到位、最高 8 處 explicit labels）
4. **Case 自帶警示 100% 保留**（DoorDash / Netflix +75% / FanDuel / Standard Chartered / Microsoft 365 / Spanner 10億 / Forbes 25% TCO / Coinbase 1.5M reads/sec 全保留）
5. **Fact vs derive 分層健康度高**（最高風險篇 CockroachDB transaction-retry-pattern 6 處 scope warning labels 完整覆蓋）

推估 case fidelity 落在 90-93% 區間、明顯高於 backend/05-07 batch 1 baseline 70-88%。Stage 4 Round 2 review fixes（commit `98c1e8d`）後、剩餘 issue 屬量化口徑微調、不是 frame / fact 層議題。本批可作為 case-first 方法論未來 batch 的 *引用紀律 reference standard*。
