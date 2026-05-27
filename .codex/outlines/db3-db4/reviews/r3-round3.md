# R3-R3：跨章一致性 Round 3 Final Verification

## 評分變化軌跡

- Round 1: 8.0/10
- Round 2: 8.7/10
- Round 3: **9.1/10** — 達 9.0+/10 目標

三維健康度（變化）：

| 維度                       | R1   | R2     | R3         |
| -------------------------- | ---- | ------ | ---------- |
| SSoT 對應紀律              | 8/10 | 9/10   | **9.5/10** |
| Cross-link 雙向 + 路徑正確 | 6/10 | 8.5/10 | **9.5/10** |
| Frame 1-8 覆蓋             | 8/10 | 8/10   | **9/10**   |

Polish 2 commit `2de160f`（+86/-8 行、10 檔 Frame 1/3/5/8 強化 + 3 檔 surgical fix）把所有 R2 deferred 議題清完、沒引入新 critical issue。

## Frame 1/3/5/8 verification

### Frame 1（適用度判讀）— Polish 2 加 8 篇 cross-link

4 篇 MongoDB sibling cross-link：**全部 ✓**

| 篇                                | Cross-link 行 | 句型                                                     |
| --------------------------------- | ------------- | -------------------------------------------------------- |
| shard-key-selection               | L13           | `MongoDB 適用度前置判讀：... 詳見 schema-design-pattern` |
| replica-set-read-preference       | L13           | 同上                                                     |
| aggregation-pipeline-optimization | L13           | 同上                                                     |
| change-streams-kafka              | L13           | 同上                                                     |

4 篇 DynamoDB sibling cross-link：**全部 ✓**

| 篇                         | Cross-link 行 | 句型                                                            |
| -------------------------- | ------------- | --------------------------------------------------------------- |
| partition-key-antipatterns | L15           | `DynamoDB 適用度前置判讀：... 詳見 single-table-design-pattern` |
| gsi-lsi-design             | L13           | 同上                                                            |
| on-demand-vs-provisioned   | L15           | 同上                                                            |
| global-tables-conflict     | L15           | 同上                                                            |

句型一致性極佳：MongoDB 4 篇統一 `MongoDB 適用度前置判讀：進到 X 前先確認 workload 在 MongoDB 適用區（3 軸：document shape / contract layer / 跨雲 hedging）`；DynamoDB 4 篇統一 `DynamoDB 適用度前置判讀：本篇假設 workload 已通過 4 軸（PK 均勻 / control plane vs data plane / consistency / access pattern）`。每篇尾加「本篇是 *已選 X 後* 的 Y 議題」釐清層次。

Anchor target 命中驗證：

- `schema-design-pattern.md#問題情境document-自由的後座力` ↔ L13 `## 問題情境：document 自由的後座力` ✓
- `single-table-design-pattern.md#dynamodb-適用度前置判讀4-軸` ↔ L13 `## DynamoDB 適用度前置判讀（4 軸）` ✓

其他 vendor (Cosmos/Aurora/Cockroach/Spanner) 開頭段提及：**✓**

- Cosmos DB mongodb-api-vs-sql-api 開頭明示「三型遷移路徑、dogfood signal、multi-model、跨雲 hedging」四軸前置判讀
- Cosmos DB ru-cost-model-sizing 開頭明示「RU 思維 vs CPU+IOPS 思維」學習曲線
- Aurora 5 篇都有「前置閱讀建議 Aurora storage architecture」+ Aurora vendor 頁 cross-link
- CockroachDB hlc-raft 開頭明示「三題都不只是 spec 問題、而是 production 容量規劃跟 incident 訊號的根本前置」
- Spanner truetime-api 開頭明示「TrueTime 設計目的是消滅 single coordinator bottleneck」設計動機判讀
- Spanner migrate-from-cloud-sql-pg description 明列「sizing barrier + < 50ms write 兩條 no-go」

### Frame 3（fleet 治理）— Polish 2 加 DynamoDB 退化段

- Aurora SSoT 主寫：✓（read-replica-scaling L250-298「邊界與整合：Fleet 治理 SSoT」H2 + 3 driver H3）
- MongoDB SSoT 主寫：✓（shard-key-selection 單 cluster vs 多 cluster blast radius、Toyota 20 DB anchor）
- DynamoDB 退化段：✓（single-table-design-pattern L185+「Frame 3：DynamoDB 在 fleet 治理 frame 的退化」H3、4 vendor 對照表 + 退化點 + 合規例外指向 global-tables）
- CockroachDB cluster boundary 主寫：✓（decision-tree L224-289、Fix3 加的 67 行段、4 H3 子段含 Aurora fleet 差異對照）

跨 vendor 一致性：4 vendor 對照表結構統一（Vendor / Scale-out 拓樸 / 容量決策層 三欄）、case anchor 一致（Aurora 200 / Cockroach 380+ / MongoDB 20 / DynamoDB partition 自動）。Frame 3 退化段未重複展開 fleet 治理 SSoT 主寫的 driver 推導、只用 case 數字 + 拓樸對比、符合 cross-link 不展開規則。

### Frame 5（合規邊界）— Polish 2 加 2 篇新段

- Aurora fleet 拓樸吸收：✓（global-database-multi-region anti-recommendation 設計 + migrate-from-self-managed-pg-mysql Standard Chartered 合規 lead time）
- CockroachDB locality+placement：✓（locality-aware-schema Hard Rock concrete case framing + decision-tree Path C 合規驅動）
- DynamoDB region-pinned Global Tables：✓（global-tables-conflict L207-220 新段、Genesys 15 region 「部分 region 不加 replication」明示）
- MongoDB cluster-per-region：✓（replica-set-read-preference L207-220 新段、read preference 解不了合規退化點明示 + Atlas global cluster GDPR 軟條款 fit）

4 vendor 對照表一致性：兩篇新段都列 4 vendor（MongoDB / Cosmos DB / Aurora / CockroachDB / DynamoDB）。MongoDB 跟 Cosmos DB 合併成「MongoDB / Cosmos DB」一列、技術上正確（都用 cluster-per-region）— 兩篇都這樣處理、一致。

DynamoDB 在這 frame 的工程意義（退化得最輕 = attribute 級 region 開關 vs 整 cluster 拆）在 global-tables 新段明示、是 R2 沒做到的新加值。

### Frame 8（event-driven scaling 5 模式）— Polish 2 雙向 cross-link

- DynamoDB SSoT（5 模式）：✓（on-demand-vs-provisioned 5 模式分類主寫、cross-link 句強化為「KV 層 mode SSoT」）
- Aurora SSoT（事件分級表）：✓（read-replica-scaling 事件分級表 FanDuel + DraftKings 雙 SLO）
- 雙向 cross-link 真的成立：✓
  - Aurora → DynamoDB：read-replica-scaling L229「Frame 8 event-driven scaling 5 模式（跨 vendor 共寫）」段、明列 DynamoDB 5 模式 + FanDuel 季賽對應 *season cycle* + Hard Rock 100→33→100 同模式
  - DynamoDB → Aurora：on-demand-vs-provisioned L277 強化句、明示「本篇從 KV 層 mode 切入、5 模式分類在本篇主寫；Aurora 從 SQL 讀副本視角切入、事件分級 + 雙 SLO + fleet 治理在 Aurora 端主寫」
- 職責分工清楚：兩篇都明示對方主寫議題（DynamoDB 5 模式 + mode × 事件型 合成判讀 / Aurora headroom 預留 + 雙 SLO 並行 + fleet 治理）— 不重複展開、雙向引用層次清楚

## SSoT 對應再 audit（7 大議題）

| SSoT 議題                         | 主寫位置                                                             | Cross-link 篇                                               | 狀態                                    |
| --------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------- |
| Strong + multi-region 互斥        | cosmosdb/multi-region-write-conflict                                 | consistency-levels-engineering + spanner/consistency-models | **✓** 主寫 H2 + SSoT 標明               |
| Aurora fleet 治理                 | aurora/read-replica-scaling L250-298                                 | 其他 4 Aurora + DynamoDB single-table Frame 3 退化段        | **✓** 主寫含 3 driver H3                |
| CockroachDB cluster boundary 顆粒 | decision-tree L224-289（Fix3 67 行）                                 | hlc-raft L211/L254 + survival-goals L233 + locality L292    | **✓** 主寫 67 行 + 3 sibling cross-link |
| Document model 三型遷移           | cosmosdb/mongodb-api-vs-sql-api 開頭                                 | MongoDB outline + DB3 entry pointer                         | **✓** description 明示三型              |
| Frame 1 適用度判讀 (MongoDB)      | mongodb/schema-design-pattern                                        | 4 MongoDB sibling（Polish 2 加）                            | **✓** 8 篇句型統一                      |
| Frame 1 適用度判讀 (DynamoDB)     | dynamodb/single-table-design-pattern                                 | 4 DynamoDB sibling（Polish 2 加）                           | **✓** 同上                              |
| Frame 8 event-driven scaling      | dynamodb/on-demand-vs-provisioned + aurora/read-replica-scaling 共寫 | 雙向 cross-link（Polish 2 加）                              | **✓** 雙向成立                          |

7/7 SSoT 議題全部紙面成立 + 實質主寫 + cross-link 紀律完整。

## Reader journey 三層架構 final

**Layer 1 entry**：✓ 三條路徑全打通

- `vendors/_index.md` 線 → 「DB3 / DB4 batch 完成紀錄」段（line 99-106）明列 6 vendor + 31 篇 deep article + 2 篇 entry article、可直接點進去
- DB3 entry → `db3-vendor-selection.md`（workload shape 3 軸前置判讀 + migration path 3 型 + 3 vendor 對比 10 軸）
- DB4 entry → `aurora-dsql-spanner-decision-tree.md`（撞牆訊號 3 型分型 + PostgreSQL 相容性 audit + sizing barrier + cluster boundary SSoT）

**Layer 2 機制深化**：✓ 流暢

- 6 vendor `_index.md` 底部 Deep article 表全打通（R2 Issue 1 修的）
- sibling cross-link 紀律維持（MongoDB / DynamoDB / Aurora / CockroachDB 都有 sibling 互引）

**Layer 3 跨層架構**：✓ 強化

- MongoDB connection-management-and-cache-layer（三層合成 frame）
- DynamoDB single-table-design-pattern Frame 3 退化段 + control plane / metadata / state 角色定位
- Aurora read-replica-scaling fleet 治理 SSoT 主寫
- CockroachDB decision-tree cluster boundary SSoT 主寫
- Frame 8 雙向 cross-link 把 KV 層 + SQL 層 mode 決策合成跨 vendor 視角

Manual reader test 走法 1（外部進深度）：`backend/_index` → `01-database/_index` → `vendors/_index` → mongodb `_index` 底部 Deep article 表 → `replica-set-read-preference` → 看到 Frame 1 cross-link 跳回 SSoT `schema-design-pattern` → 看到 Frame 5 合規段 → 跨 vendor 對照看到 DynamoDB region-pinned → 跳 `dynamodb/global-tables-conflict` → 看到對方的 Frame 5 段 — 路徑流暢、跨 vendor 視角自然形成、無斷裂。

Manual reader test 走法 2（entry-driven）：`vendors/_index` → DB3 entry article → workload shape 3 軸 → 判定 KV-shaped → DynamoDB → `single-table-design-pattern` 4 軸前置判讀 → 通過後進 mode 決策（on-demand-vs-provisioned） → Frame 8 雙向 cross-link → Aurora read-replica-scaling 5 模式對照表 → 看到 FanDuel cycle 比照、判定不是該 case 適用 — 路徑也流暢。

## 新 issue（Polish 2 引入）

### Issue A（Low）：4 vendor 對照表的「模組 outline Section B Frame X」連結指向死 anchor

3 個對照表（DynamoDB single-table Frame 3、DynamoDB global-tables Frame 5、MongoDB replica-set Frame 5）都用 `[模組 outline Section B Frame X](../../../_index.md)` 連結。這 `../../../_index.md` 解析後 = `content/backend/_index.md`、但該檔不含 "Section B" / "Frame" 等內容。Module outline 只存在於 `.codex/outlines/db3-db4/_module-outline.md`、不對外公開、所以該 anchor 連結是 *語意死的*（target 檔案存在但內容不對應）。

`mdtools cards` lint 不會抓（target 檔存在），但讀者點進去會落到 backend 入口、不會看到 Frame 對照表。

影響範圍：3 個 table 共 3 處連結。屬 Low、不阻擋發布、modular outline 在 .codex/ 是設計如此、可考慮把連結改成「跨 vendor 對照表（[模組 outline Section B Frame X](../../../_index.md)）」改成「跨 vendor 對照表（本篇 + sibling 共寫）」或移除連結。

### Issue B（Informational）：cross-link 句型用詞統一

新加 Frame 1 8 篇 cross-link 都用「詳見 ... 開頭 N 軸前置判讀」、Frame 3/5/8 新段都用 H3 + 4 vendor 對照表、Frame 8 雙向 cross-link 都用「KV 層 vs SQL 層」職責分工框架 — 句型一致。沒「詳見 / 見 / 參考」混用問題。

### Issue C（Verified clean）：章節編號 / cross-link target

`grep -rnE "1\.[0-9]+\s|01\.[0-9]+"` 抽樣四檔（schema-design-pattern / change-streams-kafka / hlc-raft-consensus / consistency-models-comparison）— 4 處編號全部跟 target weight 對齊。`mdtools cards` 跑全 01-database/ 無 broken link 輸出。

## 最終跨章一致性評分

**9.1/10**（從 R2 8.7/10、+0.4）

- ✓ Frame 1 適用度判讀 cross-link 全打通：MongoDB 4 + DynamoDB 4 = 8 篇句型統一（+0.15）
- ✓ Frame 3 fleet 治理退化 frame 加 DynamoDB 段 + 4 vendor 對照表（+0.1）
- ✓ Frame 5 合規邊界 cluster-per-region 補 2 篇（DynamoDB region-pinned + MongoDB cluster-per-region）、4 vendor 對照完整（+0.1）
- ✓ Frame 8 event-driven scaling 雙向 cross-link 成立（KV 層 vs SQL 層職責分工）（+0.1）
- ✓ 7/7 SSoT 議題紙面 + 實質主寫全打通、cross-link 不重複展開規則符合
- ✓ Reader journey 三層架構全流暢、Manual reader test 兩條路徑都通
- ⚠ Issue A Low: 3 處「模組 outline Section B Frame X」連結指向 backend/_index.md、anchor 語意死（不阻擋發布、可考慮微調連結文字）
- 沒新 critical issue 引入、`mdtools cards` 全清

剩餘 backlog（不阻擋發布、可延後 polish）：

1. Issue A 三處 anchor 連結文字微調（或移除連結保留括號描述）
2. Cosmos DB 5 篇 sibling 是否考慮加 Frame 1 cross-link 統一句型（目前是 description / 開頭段散在式說明、不像 MongoDB / DynamoDB 統一 `> **X 適用度前置判讀**` 模板）— Round 3 沒做、屬於 nice-to-have、可在下個 batch 統一加

## 模組可發布性結論

**可發布**。Polish 2 commit 把 Stage 5 round 2 三維 reviewer 抓出的剩餘 backlog 清完、達 case-first methodology batch 1 以來最高 baseline。Frame 1/3/5/8 全打通、SSoT 對應 7/7、雙向 cross-link 成立、Reader journey 三層流暢、no broken link。

跨章一致性 9.1/10 達 9.0+/10 目標、預估 R1 寫作規範 4.8+/5 + R2 案例引用 92-95% — 三維平均 A+ 水準。
