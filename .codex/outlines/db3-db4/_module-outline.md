# DB3 / DB4 整體模組大綱（case-first 校準）

> **Status**: L4.5 module-level outline、整合 71 findings × 24 cases × 29 L5 outlines 後的 case-driven 大綱。寫稿前以本檔對齊 reader journey、outline 校準、scope warning。
>
> **產出來源**：4 個平行 case audit agent（F1 DynamoDB / F2 Document model / F3 Managed+Global SQL / F4 CockroachDB）的 findings 彙整、見 `.codex/outlines/db3-db4/findings/f*.md`。

## A. Reader Journey 三層架構

case-first audit 揭露 *當前 29 outline 比重失衡*：機制深化層佔太多、選型層跟跨層架構層薄弱（F2 frame、F3 frame）。校準後 reader journey 分三層：

### Layer 1 — vendor 選型層（cross-vendor）

讀者在這層回答「該不該選這個 vendor」、輸入是 workload shape / 業務壓力 / 團隊能力、輸出是 vendor candidate list。文章主要承擔者是各 vendor `_index.md` 跟新增的 cross-vendor decision tree。

當前缺口（F1.3 / F1.6 / F1.20 / F2.16 / F2.17 / F2.10 / F4.6）：

- DynamoDB「適用度前置判讀」（PK 天然均勻度 / control plane vs data plane / consistency 可接受 eventual / access pattern 穩定）— 5 篇 outline 都跳過
- MongoDB-API vs SQL-API trade-off — Cosmos DB outline 只說「Azure 生態 lock-in」太單薄
- Document model 跨雲 hedging — MongoDB 5 篇 outline 集體缺
- Cassandra → distributed SQL 路徑 — CockroachDB decision tree 漏

### Layer 2 — 機制深化層（per-vendor）

讀者在這層回答「該怎麼配置、踩什麼坑、容量怎麼估」。當前 29 outline 主體在這層、findings 大致支撐。但有 *scope blindness* 跟 *accuracy blindness* 需校準 — 見 Section E（outline 校準清單）。

### Layer 3 — production 跨層架構層（cross-vendor）

讀者在這層回答「DB + cache + queue + connection proxy 怎麼合作、單一 DB 撐不下怎麼補」。當前 29 outline 集體缺這層。Findings 揭露 production 真實系統是 *DB + 周邊工具組合*，不是單一 DB（F2 frame 4、F1 frame 2）。

當前缺口：

- MongoDB connection layer + cache + freshness token（F2.2、F2.4）
- DynamoDB durable queue / write buffer access pattern（F1.3）
- DynamoDB control plane vs data plane 系統角色（F1.6）
- Aurora fleet management vs single-cluster 視角（F3.1、F3.11）
- Federated DB by workload pattern（F2.18）

## B. 跨 vendor 共通 frame（8 條）

從 71 findings 萃取的 cross-cutting frames — 不只影響單篇 outline、影響整體模組結構與寫作紀律。

### Frame 1：vendor 適用度的前置判讀條件

KV / document / managed SQL 各有 *不同維度* 的適用度前置判讀，當前 outline 集體跳過：

| Vendor      | 前置判讀維度                                                                                     | 來源                         |
| ----------- | ------------------------------------------------------------------------------------------------ | ---------------------------- |
| DynamoDB    | PK 天然均勻度 / control plane vs data plane / consistency 可接受 eventual / access pattern 穩定  | F1.3 / F1.6 / F1.20、frame 1 |
| MongoDB     | document shape 是否主導資料 / contract layer 該放哪 / 跨雲 hedging 是否需要                      | F2.1 / F2.3 / F2.10          |
| Cosmos DB   | API model 是否固定 / RU 思維轉換成本 / multi-model 差異化是否真用上                              | F2.12 / F2.16                |
| Aurora      | 是否真的需要跨 AZ failover / fleet 數量 / 合規邊界                                               | F3.7 / F3.1                  |
| Spanner     | external consistency 是否產品契約 / sizing barrier / GCP lock-in                                 | F3.14 / F3.16                |
| CockroachDB | 是不是從 single-primary 撞牆來 vs 從 eventual consistency 來 / team size 是否撐得起 self-managed | F4.2 / F4.6 / F4.9 / F4.14   |

**對 outline 結構的影響**：每篇 outline 問題情境段應補 vendor-specific 適用度前置判讀，不直接跳到設計細節。

### Frame 2：vendor 選型 / migration 路徑分型

Migration 路徑在 case 庫呈現 *至少 3 型*，當前 outline 把所有 migration 壓成一條 playbook：

- **保留原 DB + 補周邊工具**：Coinbase mongobetween / freshness token（F2.1）、PG sharding 出獨立 cluster（F4.3 階段一）
- **同 DB 換託管**：Forbes 自管 → Atlas 6 個月（F2.1）、自管 PG/MySQL → Aurora（F3.10）
- **同 model 換 vendor**：Microsoft 365 MongoDB → Cosmos DB MongoDB API（F2.1）
- **paradigm shift（換引擎）**：Aurora → CockroachDB（F4.3 階段二）、Cloud SQL → Spanner、Aurora → Aurora DSQL

**對 outline 結構的影響**：`mongodb-api-vs-sql-api.md` 跟 `migrate-from-self-managed-pg-mysql.md` 跟 `migrate-from-cloud-sql-pg.md` 都該在開頭分型，不是壓平。

### Frame 3：fleet 治理 vs single instance — production scale 必然走 fleet

5 個 case 揭露同一 frame：production scale 不是「單一巨型 cluster」而是 fleet of clusters，但 driver 各異：

| Case                     | Vendor        | Fleet 規模   | Driver                              |
| ------------------------ | ------------- | ------------ | ----------------------------------- |
| 9.C4 DraftKings          | Aurora        | 200 cluster  | Business sharding                   |
| 9.C23 Netflix            | Aurora        | 多 cluster   | Microservice ownership              |
| 9.C14 Standard Chartered | Aurora        | 7 cluster    | 合規市場 boundary                   |
| 9.C40 Netflix            | CockroachDB   | 380+ cluster | Microservice + polyglot persistence |
| 9.C38 Toyota Connected   | MongoDB Atlas | 20 DB        | Microservice + blast radius         |

**對 outline 結構的影響**：5 篇 Aurora outline + 5 篇 CockroachDB outline + MongoDB shard-key-selection 都該補「fleet vs single instance」軸（F3.1、F3.11、F4.7、F2.6）。當前都用 single-cluster 視角寫，這是最大 scope blindness。

### Frame 4：capacity 抽象單位的思維差異

不同 vendor 用不同 capacity 抽象，*思維遷移* 成本可能高過 vendor 價差（F2.12）：

| Vendor      | Capacity 抽象                                       | 思維                  |
| ----------- | --------------------------------------------------- | --------------------- |
| MongoDB     | CPU + IOPS + working set RAM                        | 三軸                  |
| DynamoDB    | WCU/RCU + on-demand/provisioned + adaptive capacity | mode 選擇 + PK 均勻度 |
| Cosmos DB   | RU + 5 consistency level                            | RU 預算               |
| Aurora      | instance class + replica count + storage IOPS       | provisioned           |
| Spanner     | processing unit (100 pu 起跳)                       | node count            |
| CockroachDB | range × replication factor × node count             | distributed           |

**對 outline 結構的影響**：`ru-cost-model-sizing.md`（Cosmos DB）跟 `on-demand-vs-provisioned.md`（DynamoDB）都該補「思維遷移成本」段（F2.12、F1.18）— 不是只看 monthly bill。

### Frame 5：合規邊界的處理方式 — vendor 拓樸差異

合規（受監管市場、GDPR、Wire Act）在不同 vendor 用不同機制吸收：

- **Aurora**：fleet 拓樸吸收（每市場獨立 cluster、合規禁止跨境 = Global Database 反指標、F3.6、F3.8）
- **CockroachDB**：locality + placement 吸收（Hard Rock Outposts + 邏輯一個 cluster + region pinning、F4.10、F4.13）
- **DynamoDB**：region-pinned global table 吸收（Genesys 15 region / 各市場合規分離、F1.11）
- **MongoDB / Cosmos DB**：cluster-per-region 吸收（無 row-level locality 等價物）

**對 outline 結構的影響**：

- `global-database-multi-region.md`（Aurora）已正確標 Standard Chartered 為 anti-recommendation（F3.6 ✓）
- `migrate-from-self-managed-pg-mysql.md` 漏合規 lead time 跟 no-go condition（F3.8、F3.6）
- `locality-aware-schema.md` 該從合成 GDPR 場景改為 Hard Rock concrete case 主導（F4.10）

### Frame 6：production 跨層架構 — 單一 DB 撐不下是常態

3 個 rich case 揭露 production 真實系統是 *DB + 周邊工具* 組合：

- **Coinbase**：MongoDB Atlas + DynamoDB + Memcached + mongobetween + freshness token + ML predictive scaling（F2.4、F2.18）
- **Tixcraft**：DynamoDB 寫入緩衝 + 傳統 server 慢消費（F1.3、F1.21）
- **PayPay**：DynamoDB + 下游 APNs/FCM 受 quota 限制（F1.15）
- **Toyota Connected**：MongoDB Atlas 20 DB + Lambda + Kinesis + Redis + Kubernetes（F2.6）

**對 outline 結構的影響**：MongoDB 缺新 sibling `connection-management-and-cache-layer`（F2.2、F2.4）；DynamoDB `single-table-design-pattern.md` 該補 durable queue / write buffer 正向用例（F1.3）。

### Frame 7：vendor case 數字要分口徑讀 — meta 寫作紀律

4 個 case 自帶警示揭露 *讀 vendor 數字要分口徑*：

- 9.C5 Amazon Ads「90M reads/sec」是年度峰值最高一秒、非平均（F1.10）
- 9.C20 Zomato「90% latency 降」可能只 p50、p99/p999 改善幅度小（F1.10）
- 9.C24 Genesys「99.999%」是 12 個月滾動歷史值、非未來承諾（F1.10）
- 9.C10 Spanner「10 億 req/sec」是 Google 全使用者加總、非單客戶配額（F3.17）

**對 outline 結構的影響**：屬寫作紀律、不是單篇 outline 主議題。但每篇 outline 引用 case 數字時都該明示口徑（最大瞬時 / 99 百分位 / 常態 / 滾動 / dogfood / customer-facing）。

### Frame 8：event-driven scaling 模式分類 — 不是一律 10x

5 個 case 揭露 *至少 5 種* 不同的 event-driven scaling 形狀，當前 outline 把它們壓成「Super Bowl peak」單一類型：

- **flash-sale spike**：Tixcraft 6750x in seconds（F1.21）
- **predictable peak**：Disney+ 新片首發 / Aurora Super Bowl（F1.16、F3.4）
- **sustained growth**：Amazon Ads / Capcom（F1.5）
- **season cycle**：Hard Rock NFL/NBA 100→33→100 node（F4.12）
- **surge baseline permanent shift**：Zoom 30x DAU 不會回去（F1.5）
- **dual-peak misalignment**：DraftKings 讀寫雙峰錯位（F3.5）

**對 outline 結構的影響**：`on-demand-vs-provisioned.md`（DynamoDB）跟 `read-replica-scaling.md`（Aurora）都該補事件分級表（F3.13、F1.16），不是用「peak/avg > 5x」單一閾值決策。

## C. DB3 模組大綱（MongoDB + DynamoDB + Cosmos DB）

DB3 三個 vendor 都在 document / KV 層、跨 vendor frame 高度相關（document model 三型遷移、partition key 可逆性、cross-cloud hedging）。

### C.1 DB3 entry point 建議：cross-vendor decision article

當前缺：一篇進 DB3 的 entry point article、回答「我的 workload 是 document / KV / multi-model 哪一類」、把讀者導向 MongoDB / DynamoDB / Cosmos DB 子組。

**候選新 outline**：`.codex/outlines/db3-db4/db3-vendor-selection.md`（或進 `vendors/_index.md` 整合段）

內容支撐：F2.1 三型 migration / F2.16 multi-model 差異化 / F2.18 federated DB / F1.3 durable queue / F1.20 PK 天然均勻

### C.2 MongoDB 子組（現有 5 outline + 1 新 sibling 候選）

| Outline                                                    | 狀態        | 校準動作                                                                                                                                              | Findings 來源              |
| ---------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| `schema-design-pattern.md`                                 | rewrite     | frame 從「embedded vs reference」推到「contract layer 在哪」（DB-layer validator / app-layer abstraction / 混合）；補 time-series collection 適用情境 | F2.3、F2.8                 |
| `shard-key-selection.md`                                   | keep + 補強 | 補單 cluster vs 多 cluster 對比（Toyota 20 DB blast radius）；補 reshardCollection vs DynamoDB / Cosmos DB 可逆性對照                                 | F2.6、F2.15                |
| `aggregation-pipeline-optimization.md`                     | keep        | findings 直接支撐弱、機制深化議題                                                                                                                     | （無 high-impact finding） |
| `replica-set-read-preference.md`                           | rewrite     | 補 causal consistency session（DB 層）vs freshness token（cache 層）對照、揭露讀者真實系統是跨層的                                                    | F2.4                       |
| `change-streams-kafka.md`                                  | keep        | 機制議題、findings 支撐弱                                                                                                                             | （無 high-impact finding） |
| **新 sibling**：`connection-management-and-cache-layer.md` | **add**     | connection storm + cache + predictive scaling 整合一篇，補 5 篇 outline 集體缺的 connection layer 視角                                                | F2.2、F2.4、F2.5           |

### C.3 DynamoDB 子組（現有 5 outline、無新增）

| Outline                          | 狀態    | 校準動作                                                                                                                                                                                                                | Findings 來源                   |
| -------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `partition-key-antipatterns.md`  | keep    | 補 mode × partition 交叉判讀（同一現象在 on-demand / provisioned 不同表現）                                                                                                                                             | F1.1、F1.2、F1.20               |
| `single-table-design-pattern.md` | rewrite | 問題情境段補 DynamoDB 適用度前置判讀（PK 天然均勻 / control plane vs data plane / consistency / access pattern 穩定）；補 durable queue / write-buffer 正向用例；補 connection limit 機制對照 RDB                       | F1.3、F1.6、F1.7、F1.20         |
| `gsi-lsi-design.md`              | keep    | 補 DAX 作為讀峰值補位（F1.8 derive 注意分層）                                                                                                                                                                           | F1.8                            |
| `on-demand-vs-provisioned.md`    | rewrite | 從「peak/avg ratio 單軸」擴成多軸（read/write ratio trend / surge 永久 baseline 上移 / DBA 工時釋放 / vendor vs 自管 cost crossover / predictable-peak vs flash-sale）；補「DynamoDB vs 自管 cluster cost crossover」段 | F1.4、F1.5、F1.16、F1.18、F1.19 |
| `global-tables-conflict.md`      | keep    | 補正向 access pattern（cross-device sync / global read / DR failover）、不只講 conflict；強化 B2B vs B2C 業務 driver                                                                                                    | F1.11、F1.12、F1.17             |

### C.4 Cosmos DB 子組（現有 5 outline、無新增）

| Outline                             | 狀態        | 校準動作                                                                                                                                                                                     | Findings 來源             |
| ----------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| `consistency-levels-engineering.md` | keep        | SSoT 對齊：Strong + multi-region 互斥議題交給 `multi-region-write-conflict.md`，本篇 cross-link 不展開                                                                                       | F2.14                     |
| `partition-key-design.md`           | keep + 補強 | 補 latency budget 拆解（vendor SLA 是 DB 端 / 實測是 end-to-end）                                                                                                                            | F2.13                     |
| `ru-cost-model-sizing.md`           | rewrite     | 問題情境補「RU 思維 vs CPU+IOPS 思維」學習曲線；操作流程補「依負載形狀選容量模式」對照表；失敗模式補「autoscale min ceiling 是 reactive、預測性流量必須 scheduled scaling 或 pre-provision」 | F2.5、F2.11、F2.12        |
| `mongodb-api-vs-sql-api.md`         | rewrite     | 開頭補三型遷移路徑對照、補 dogfood frame 限制（數字不公開不能當 benchmark）、補 multi-model 差異化、補跨雲 vs 單雲 hedging frame                                                             | F2.1、F2.10、F2.16、F2.17 |
| `multi-region-write-conflict.md`    | keep + 補強 | 容量觀測補「廣告 SLA vs 實測可用性 = DB SLA × 網路 SLA × 應用層 SLA」拆解                                                                                                                    | F2.7                      |

## D. DB4 模組大綱（Aurora + CockroachDB + Spanner）

DB4 三個 vendor 是 *paradigm shift 譜系*：Aurora（managed single-primary）→ CockroachDB（distributed multi-primary 跨雲）/ Spanner（global SQL GCP-only）。最大 cross-cutting frame 是 *Aurora → distributed SQL 不是「加強版」、是 paradigm shift*（F3 frame）。

### D.1 DB4 entry point 建議：升級 decision tree

當前 `cockroachdb/aurora-dsql-spanner-decision-tree.md` 已大致承擔此角色，但 F4 audit 揭露多個 add：

- 加「決策樹前置問題：你的撞牆訊號是哪條路徑」（single-primary 撞牆 vs Cassandra 缺口 vs 合規驅動、F4.6 + F4 frame 1）
- 加「PostgreSQL 相容性 audit checklist」（serializable default / retry semantics / partial index 三項、F4.4）
- 加「team size 是 distributed SQL 適配的決策訊號」（Hard Rock 50 人 case、F4.14）
- 加 sizing barrier 討論（Spanner 100 pu 起跳對中小 PG workload 成本門檻、F3.16）

**建議**：把 decision-tree 從 CockroachDB 子目錄提升為 DB4 entry point、或新建 `.codex/outlines/db3-db4/db4-paradigm-shift-decision.md`。

### D.2 Aurora 子組（現有 5 outline、無新增）

| Outline                                 | 狀態           | 校準動作                                                                                                                                                                                                                                  | Findings 來源                   |
| --------------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `storage-architecture.md`               | rewrite + 補強 | 容量觀測補 DraftKings 6ms 寫 / <1ms 讀 production reference；加「韌性 + 性能不是 trade-off」frame；加「OLTP workload shape（讀寫雙峰錯位）」段                                                                                            | F3.2、F3.5、F3.7、F3.9          |
| `cross-az-failover-rto.md`              | keep           | Standard Chartered anchor 充分                                                                                                                                                                                                            | F3.6                            |
| `read-replica-scaling.md`               | rewrite        | 拆「Auto-scaling 接不住秒級尖峰」明示 DraftKings +50% no sweat = headroom 預留；補 FanDuel 雙 SLO 並行 frame（避免把 5-10x 壓成單一數字）；補事件型分級表（playoff/championship/Super Bowl）；邊界段「何時拆 cluster」加微服務拆分 driver | F3.4、F3.5、F3.11、F3.12、F3.13 |
| `global-database-multi-region.md`       | keep           | anti-recommendation 設計（合規禁止跨境 → 用 fleet 不用 Global Database）正確                                                                                                                                                              | F3.6                            |
| `migrate-from-self-managed-pg-mysql.md` | rewrite        | Driver / No-go 段補「合規禁止跨境複製」no-go condition；加「合規驅動遷移的時程模型」（市場數 × 審查月份）；案例對照引 Netflix 時補「Aurora 不是 all-purpose store、Netflix 仍用 Cassandra / EVCache」邊界                                 | F3.6、F3.8、F3.10               |

### D.3 CockroachDB 子組（現有 5 outline、無新增）

| Outline                                | 狀態                               | 校準動作                                                                                                                                                                                                                                  | Findings 來源            |
| -------------------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| `hlc-raft-consensus.md`                | keep + 補強                        | 容量段補「per-cluster 容量規劃」訊號（Netflix 380+ cluster artery of small DBs frame）；scope warning：latency 數字明示「通用工程估算、case 未揭露」                                                                                      | F4.7、scope warning      |
| `survival-goals.md`                    | keep + 補強                        | 核心機制段補「為什麼選 region survival」業務動機判讀（Netflix Gaming 48-node = survival 不是 latency）；操作流程段補「從業務 SLO 倒推 survival goal」步驟（Hard Rock bet placement RPO=0）                                                | F4.8、F4.11              |
| `transaction-retry-pattern.md`         | **高 scope warning**（F4 frame 2） | DoorDash case *沒* 直接揭露 retry pattern 是核心議題、本篇是跨 case 合成 frame；寫稿時必須明示「DoorDash 沒寫 retry contract 重塑、是從 PG 相容性視角推論」；走 standard-driven（vendor 文件） + DoorDash 作為 trigger context            | F4.1、F4.4、frame 2      |
| `locality-aware-schema.md`             | rewrite                            | framing 從「合成 GDPR 場景」改為「Hard Rock 跨州合規 + 邏輯一個 cluster」concrete case 主導；失敗模式段補「拆獨立 cluster 解合規但破壞業務邏輯」反模式（對比 Standard Chartered）；補「Outposts 是合規工具、不是 latency 工具」反直覺判讀 | F4.10、F4.13             |
| `aurora-dsql-spanner-decision-tree.md` | rewrite + 提升 entry point         | 加「撞牆訊號哪條路徑」前置問題（F4.6）；加 PostgreSQL 相容性 audit checklist（F4.4）；加 team size 決策軸（F4.14）；加 Spanner sizing barrier（F3.16）                                                                                    | F3.16、F4.4、F4.6、F4.14 |

### D.4 Spanner 子組（現有 4 outline、無新增）

| Outline                                  | 狀態    | 校準動作                                                                                                                                                                                                                    | Findings 來源    |
| ---------------------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| `truetime-api-depth.md`                  | rewrite | 開頭補「TrueTime 目的是消滅 single coordinator bottleneck、達成 line-rate scaling」商業邏輯先行段；明示 9.C10 dogfood 邊界（不是 customer-facing capacity）                                                                 | F3.14、F3.17     |
| `consistency-models-comparison.md`       | rewrite | 加 cross-region quorum 100-200ms 數量級 anchor；加 line-rate scaling 對照表（為什麼 PG serializable 多 node 拿不到 line-rate）；SSoT 對齊：Strong + multi-region 互斥議題若已寫進 Cosmos DB outline，此處 cross-link 不展開 | F3.14、F3.15     |
| `schema-migration-interleaved-tables.md` | keep    | 機制議題、findings 支撐弱                                                                                                                                                                                                   | （無強 finding） |
| `migrate-from-cloud-sql-pg.md`           | rewrite | Driver / No-go 段加 sizing barrier（Spanner 100 pu 起跳對中小 PG 成本門檻）；加「應用層延遲容忍 < 50ms write」no-go condition（跨 region Spanner write 100-200ms）                                                          | F3.15、F3.16     |

## E. 29 outline 校準清單彙整

### Keep（13 篇、機制本身 + findings 支撐充分）

| Vendor      | Outline                                  | 校準動作                              |
| ----------- | ---------------------------------------- | ------------------------------------- |
| MongoDB     | `aggregation-pipeline-optimization.md`   | 無                                    |
| MongoDB     | `change-streams-kafka.md`                | 無                                    |
| DynamoDB    | `partition-key-antipatterns.md`          | 補 mode 交叉判讀                      |
| DynamoDB    | `gsi-lsi-design.md`                      | 補 DAX 補位（標明 derive）            |
| DynamoDB    | `global-tables-conflict.md`              | 補正向 access pattern + B2B/B2C frame |
| Cosmos DB   | `consistency-levels-engineering.md`      | SSoT 對齊                             |
| Cosmos DB   | `partition-key-design.md`                | 補 latency budget 拆解                |
| Cosmos DB   | `multi-region-write-conflict.md`         | 容量段補 SLA 拆解                     |
| Aurora      | `cross-az-failover-rto.md`               | 無                                    |
| Aurora      | `global-database-multi-region.md`        | 無                                    |
| CockroachDB | `hlc-raft-consensus.md`                  | 補 per-cluster 容量段                 |
| CockroachDB | `survival-goals.md`                      | 補業務動機判讀 + SLO 倒推             |
| Spanner     | `schema-migration-interleaved-tables.md` | 無                                    |

### Rewrite（13 篇、framing 校準）

| Vendor      | Outline                                 | 主要 rewrite 方向                                          |
| ----------- | --------------------------------------- | ---------------------------------------------------------- |
| MongoDB     | `schema-design-pattern.md`              | frame 推到「contract layer 在哪」                          |
| MongoDB     | `shard-key-selection.md`                | 補單/多 cluster 對比 + 可逆性對照                          |
| MongoDB     | `replica-set-read-preference.md`        | 補 DB 層 vs cache 層對照                                   |
| DynamoDB    | `single-table-design-pattern.md`        | 問題情境段補適用度前置判讀 + durable queue 正向用例        |
| DynamoDB    | `on-demand-vs-provisioned.md`           | mode 選擇從單軸擴成多軸                                    |
| Cosmos DB   | `ru-cost-model-sizing.md`               | 補 RU 思維學習曲線 + 負載形狀 × mode 對照                  |
| Cosmos DB   | `mongodb-api-vs-sql-api.md`             | 補三型遷移路徑 + dogfood 限制 + multi-model + 跨雲 hedging |
| Aurora      | `storage-architecture.md`               | 補 production reference + 韌性=性能 frame + 雙峰錯位       |
| Aurora      | `read-replica-scaling.md`               | 拆 headroom 預留 + 雙 SLO + 事件分級 + 微服務拆分 driver   |
| Aurora      | `migrate-from-self-managed-pg-mysql.md` | 補合規 no-go + 合規 lead time + Aurora 非 all-purpose      |
| CockroachDB | `locality-aware-schema.md`              | framing 改 Hard Rock concrete case 主導                    |
| CockroachDB | `aurora-dsql-spanner-decision-tree.md`  | 提升 entry point + 補 4 個前置決策軸                       |
| Spanner     | `truetime-api-depth.md`                 | 開頭補商業邏輯先行 + dogfood 邊界                          |
| Spanner     | `consistency-models-comparison.md`      | 補 quorum 數量級 + line-rate 對照                          |
| Spanner     | `migrate-from-cloud-sql-pg.md`          | 補 sizing barrier + 跨 region latency no-go                |

### Add（5 篇新 outline + 1 entry article 候選）

| 候選 outline                                                                  | 來源 findings             | 優先序                                         |
| ----------------------------------------------------------------------------- | ------------------------- | ---------------------------------------------- |
| `mongodb/connection-management-and-cache-layer.md`                            | F2.2、F2.4、F2.5          | 高（補集體缺的 connection layer）              |
| `db3-vendor-selection.md`（cross-vendor entry）                               | F2.1、F2.16、F2.18、F1.20 | 高（DB3 reader entry point）                   |
| `aurora/fleet-management-vs-single-cluster.md`（或併入 storage-architecture） | F3.1、F3.11               | 中（也可在 read-replica-scaling rewrite 內補） |
| `dynamodb/durable-queue-write-buffer.md`（或併入 single-table）               | F1.3、F1.21               | 中（也可在 single-table rewrite 內補）         |
| `db4-paradigm-shift-decision.md`（DB4 entry article，或從 cockroachdb 提升）  | F3 frame、F4 frame 1      | 中（也可在 decision-tree rewrite 內補）        |

### High scope warning（避免 over-extrapolation 的關鍵 outlines）

| Outline                                                                  | 風險                                                                           | 寫稿時必須明示                                                                |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| `cockroachdb/transaction-retry-pattern.md`                               | DoorDash case *沒* 揭露 retry pattern；本篇整篇是跨 case 合成 frame            | 「DoorDash 沒直接揭露 serializable retry contract、本章從 PG 相容性視角推論」 |
| `dynamodb/on-demand-vs-provisioned.md`                                   | 多處自生數字（peak/avg > 5x、30-60 分鐘 scheduled、idempotency 加 request_id） | 「為經驗值 / 通用工程知識、case 未揭露具體閾值」                              |
| `dynamodb/partition-key-antipatterns.md`                                 | shard 數 10-100、單 logical key 峰值 WCU 除以 800 是通用工程數字               | fact vs derive 分層                                                           |
| `cockroachdb/hlc-raft-consensus.md`                                      | latency 數字（single-region 3-5ms、multi-region 100-150ms）是通用估算          | 「case 未揭露具體 p99 數字、屬通用工程估算」                                  |
| `cosmosdb/mongodb-api-vs-sql-api.md`                                     | Microsoft 365 case 數字不公開、dogfood case 不能當 benchmark                   | 「Microsoft 365 dogfood = 高權重 selection signal、但數字不公開」             |
| `spanner/truetime-api-depth.md`、`consistency-models-comparison.md`      | Spanner 10 億 req/sec 是 Google 全使用者加總                                   | 「Google internal dogfood、不是 customer-facing capacity」                    |
| `mongodb/schema-design-pattern.md`（time-series collection 引用 Toyota） | Toyota case 自承未揭露是否用 time-series collection                            | 「IoT 場景該考慮 time-series collection、Toyota 未揭露實際使用」              |

## F. 寫作起手順序建議

依 *case anchor 強度* 跟 *findings 支撐密度* 排序，優先寫的 deep article：

### 第一輪（case anchor 最強、findings 支撐充分、scope warning 低）

1. **Aurora `storage-architecture.md`** — 9.C23 Netflix +75% findings 充分（F3.9）、機制邊界明確、rewrite 動作清楚（補 production reference + 韌性=性能 frame）
2. **Aurora `cross-az-failover-rto.md`** — 9.C14 Standard Chartered anchor 充分（F3.6）、keep 狀態
3. **DynamoDB `partition-key-antipatterns.md`** — 9.C15 Tixcraft + 9.C5 Amazon Ads findings 充分（F1.1、F1.2、F1.20）、keep + 補強

### 第二輪（case anchor 中等、需 rewrite framing）

4. **DynamoDB `single-table-design-pattern.md`** — rewrite 動作清楚（補適用度前置判讀）
5. **Aurora `read-replica-scaling.md`** — rewrite 動作清楚（事件分級 + 雙 SLO）
6. **CockroachDB `survival-goals.md`** — Hard Rock + Netflix anchor 充分（F4.8、F4.11）
7. **Cosmos DB `partition-key-design.md`** — Minecraft Earth + ASOS anchor 充分（F2.13、F2.15）

### 第三輪（rewrite 重、framing 變動大）

8. **MongoDB `schema-design-pattern.md`** — contract layer frame 推進
9. **CockroachDB `locality-aware-schema.md`** — Hard Rock case 主導 framing
10. **DynamoDB `on-demand-vs-provisioned.md`** — 多軸擴展

### 第四輪（高 scope warning、需嚴格 fact vs derive 分層）

11. **CockroachDB `transaction-retry-pattern.md`** — 標明跨 case 合成 frame
12. **Spanner `truetime-api-depth.md`** — 商業邏輯先行 + dogfood 邊界

### 第五輪（新 outline 候選）

13. **MongoDB `connection-management-and-cache-layer.md`**（新 sibling）— Coinbase mongobetween + freshness token + predictive scaling
14. **`db3-vendor-selection.md`**（cross-vendor entry article）— 三型遷移 + multi-model + federated

### 後續

剩餘 outline（aggregation / change streams / consistency levels / multi-region conflict 等）依需要進入第六輪以後。建議每寫完 3 篇進一次 Stage 3-5（agent team review + 修正循環）、確保 case fidelity 不漂移。

## G. 跨 outline SSoT 對應規則

避免重複展開同議題、降低 audit 維護成本：

| 議題                                   | SSoT outline                                                                                              | 其他相關 outline 處理                               |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Strong consistency + multi-region 互斥 | `cosmosdb/consistency-levels-engineering.md`                                                              | `multi-region-write-conflict.md` cross-link、不展開 |
| Aurora fleet 治理                      | `aurora/read-replica-scaling.md`（邊界段擴）或新 sibling                                                  | `storage-architecture.md` cross-link、不展開        |
| CockroachDB cluster boundary 顆粒      | `aurora-dsql-spanner-decision-tree.md`（per-app vs shared cluster 決策軸）                                | `hlc-raft-consensus.md` cross-link                  |
| Document model 三型遷移路徑            | `cosmosdb/mongodb-api-vs-sql-api.md` 開頭段                                                               | MongoDB outline cross-link                          |
| Frame 7 vendor 數字口徑紀律            | 不寫進單篇、屬寫作方法論                                                                                  | 每篇 outline 引用 case 數字時明示口徑               |
| Frame 8 event-driven scaling 5 種模式  | `dynamodb/on-demand-vs-provisioned.md` 跟 `aurora/read-replica-scaling.md` 共寫、各自從本 vendor 視角切入 | cross-link 即可                                     |

## H. 下一步路由

本檔完成 Stage 2（findings 彙整 + 整體大綱）。後續：

- **Stage 3**：依本檔的 keep/rewrite/add 清單，校準 29 個 L5 outline 的 framing — 估 ~10-15 個 outline 要動，可分 batch 派多 agent
- **Stage 4**：從 Section F 第一輪 case anchor 最強的 outline 開始寫 deep article — Aurora `storage-architecture.md` 是建議起手點
- **Stage 5**：每寫完 3 篇 deep article 進一次 agent team review（寫作規範 / 案例引用準確性 / 跨章一致性 三維 reviewer）

Findings 檔路徑：

- `.codex/outlines/db3-db4/findings/f1-dynamodb.md`（22 findings）
- `.codex/outlines/db3-db4/findings/f2-document.md`（18 findings）
- `.codex/outlines/db3-db4/findings/f3-managed-global-sql.md`（17 findings）
- `.codex/outlines/db3-db4/findings/f4-cockroachdb.md`（14 findings）

L5 outline 路徑：`.codex/outlines/db3-db4/{mongodb,dynamodb,aurora,cockroachdb,spanner,cosmosdb}/*.md`
