# R3-R2：跨章一致性 Round 2 Verification

## Round 1 → Round 2 評分變化

- Round 1: 8.0/10
- Round 2: **8.7/10**
- 變化驅動：
  - Layer 1 路徑斷裂全修（最 critical issue 解了，+0.4）
  - SSoT 紙面成立 vs 主寫缺口：CockroachDB cluster boundary 補 67 行主寫段（4 H3 + Aurora fleet 差異對照表 + 跨 vendor 路徑），議題真的展開（+0.2）
  - 4 處編號漂移修正 + cross-link target weight 都對得上（+0.1）
  - 但 Frame 8 雙向 cross-link 仍單向（commit message 已標 Stage 6 polish）— 不扣分但沒加分

三維健康度（變化）：

- **SSoT 對應**：8/10 → **9/10**（Spanner 兩處反向 link 已修、CockroachDB cluster boundary 從紙面 SSoT 升級成實質主寫）
- **Cross-link 雙向 + 路徑正確**：6/10 → **8.5/10**（4 處編號漂移全修、Layer 1 vendor `_index` 全補 deep article 表 + 跨 vendor entry；剩 Frame 8 Aurora→DynamoDB reverse 單向）
- **Frame 1-8 覆蓋**：8/10 → 8/10（本輪未動 Frame 1/3/5 強化、commit 已標延後）

## Issue 1-4 修復驗證

### Issue 1 — Layer 1 路徑斷裂（最 critical）

**6 vendor `_index.md`**：✓ 全部加上「Deep article（已完成）」H2 段

| Vendor      | 段位置（line） | 結構                                     |
| ----------- | -------------- | ---------------------------------------- |
| mongodb     | line 197-210   | 6 篇 deep article 表 + DB3 entry pointer |
| dynamodb    | line 204-217   | 5 篇 + DB3 entry pointer                 |
| cosmosdb    | line 204-216   | 5 篇 + DB3 entry pointer                 |
| aurora      | line 191-203   | 5 篇 + DB4 entry pointer                 |
| spanner     | line 176-187   | 4 篇 + DB4 entry pointer                 |
| cockroachdb | line 181-193   | 5 篇（含 DB4 entry 自己）+ entry 提示    |

每個 vendor 表結構一致：「主題 / 文章連結 / 對應 production 議題」三欄、卡片下方一行跨 vendor entry pointer。DynamoDB / Cosmos DB 用 DB3 entry、Aurora / Spanner 用 DB4 entry，CockroachDB 因 entry 在自家、改成本 vendor self-reference — 邏輯正確。

**`vendors/_index.md` 覆蓋進度表**：✓

- line 42-47 DB3/DB4 6 vendor 從「—」改成 slash 分隔的 deep article 連結清單（格式跟 PostgreSQL/MySQL row 一致、用相對連結）
- line 49 加總結句明示「31 篇新 deep article + 1 篇 DB3 entry + 1 篇 DB4 entry」、跟現實對齊
- 移除「DB3 / DB4 撰寫 backlog 排序建議」過時段，替換成 line 99-106「DB3 / DB4 batch 完成紀錄」段（紀錄完成順序）

**Cross-vendor entry point 段**：✓ line 51-58 新增 H2 段、明示兩個 entry article（DB3 vendor-selection / DB4 decision-tree）跟 case-driven driver path 切入方式。

**Manual reader test**（從外部走進 deep article）：

1. `backend/_index.md` → 1-database 模組 ✓
2. `01-database/_index.md` → `vendors/_index.md` ✓
3. `vendors/_index.md` line 33-49「內容覆蓋進度」表 → 看到每個 vendor 的 deep article 清單、可直接點進去 ✓
4. 或 `vendors/_index.md` line 51-58 → 先進 DB3/DB4 entry article 看 driver path、再進個別 vendor ✓
5. 個別 vendor `_index.md` → 底部 Deep article 表 → 任一 deep article ✓

路徑流暢、無斷裂。Reader 進場有兩條合理路徑（「先看清單表 → 逛 vendor」vs「先看 entry article 識別 driver → 進對應 vendor 深度」）、entry article 不再是「孤兒文章」。

### Issue 2 — SSoT 紙面成立 vs 實際沒主寫

**CockroachDB cluster boundary 67 行主寫段**：✓ `aurora-dsql-spanner-decision-tree.md` line 224-289

結構（H2 + 4 H3 + 表 + 路徑對照）：

- L224-226：H2 起手段 — 明示「本段是 CockroachDB cluster boundary 顆粒的主寫位置」
- L228-239：H3「Per-app cluster（Netflix 380+ 路徑、F4.7）」— 380+ cluster + artery of small DBs + ops surface area 線性成長 + 平台團隊代價
- L241-252：H3「邏輯一個 cluster（Hard Rock 路徑、F4.10）」— 跨 8 州 + Outposts + transactional cross-domain query + Wire Act 合規顆粒
- L254-265：H3「兩條路徑的判讀軸」— 6 軸對照表（服務隔離度 / 跨服務 query / Blast radius / Ops surface area / 容量規劃 / 平台團隊要求）+ 判讀順序兩問
- L267-280：H3「跟 Aurora fleet 治理的本質差異」— 4 軸對照表 + 「Aurora 拆是被迫 vs CockroachDB 拆是選擇」結論句（這段是 R3 round 1 抓的關鍵差異化）
- L282-289：H3「跨 vendor 路徑對照」— 4 路徑（DraftKings Aurora fleet / Netflix per-app / Hard Rock 邏輯一個 / Standard Chartered per-jurisdiction），把跨 vendor 視角顯式攤開
- L289：進階閱讀路由回 locality-aware-schema + hlc-raft-consensus

品質判讀：

- 主寫成立 — 不只是「提到」、是 67 行展開含 case anchor + 對照表 + 跟 Aurora fleet 區分
- 跟 Aurora fleet 對照清晰度高：明示「拆 cluster 動機本質不同」（Aurora 拆 = 繞 single-primary；CockroachDB 拆 = 業務 / 合規 / blast radius 邊界）
- 4 個案例都帶 case ID（9.C39 / 9.C40 / 9.C41 / DraftKings / Standard Chartered）— case fidelity 維持

**其他 CockroachDB sibling 是否 cross-link**：✓

- `hlc-raft-consensus.md` line 211 + line 254 兩處 cross-link 到 decision-tree
- `survival-goals.md` line 233 cross-link
- `locality-aware-schema.md` line 292 cross-link

sibling 都不重複展開 cluster boundary 議題、僅指回 SSoT — 跟 R3 round 1 對 Aurora fleet 的評語「cross-link 紀律最好的一個」現在 CockroachDB 也達到。

### Issue 3 — 4 處章節編號漂移

| 位置                                              | Before                                    | After                                | Target weight verify                                                                 |
| ------------------------------------------------- | ----------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------ |
| mongodb/schema-design-pattern L198                | 1.4 transaction boundary                  | 1.3                                  | transaction-boundary.md weight 3 ✓                                                   |
| mongodb/change-streams-kafka L182                 | 1.6 schema migration / 1.7 reconciliation | 1.7 / 1.9                            | schema-migration-rollout-evidence weight 7 ✓ / reconciliation-data-repair weight 9 ✓ |
| cockroachdb/hlc-raft-consensus L232               | 01.4 database migration playbook          | 1.6                                  | database-migration-playbook.md weight 6 ✓                                            |
| spanner/consistency-models-comparison L101 + L193 | cosmosdb/consistency-levels-engineering   | cosmosdb/multi-region-write-conflict | multi-region-write-conflict.md exists ✓                                              |

4 處編號 / target 路徑漂移全修、target chapter weight 全對齊。

### Issue 4 — Spanner SSoT 指向錯（已併入 Issue 3 最後一行）

兩處（line 101 + line 193）均改指向 `cosmosdb/multi-region-write-conflict.md`、跟 cosmosdb 那篇實際的主寫位置一致。

## 新 issue（Stage 5.5 引入）

**Fix1 vendors/_index.md 覆蓋表變動**：

- 6 row 的格式跟 PostgreSQL / MySQL 一致（slash 分隔的相對連結、`[name](path/)` 格式）— 無格式漂移
- 表格欄寬隨內容自動延展、aligned 風格符合 mdtools 規範
- 移除原 backlog 段、替換成完成紀錄段、語意正向（從「待補」改成「已完成」）

**Fix3 SSoT 段引入議題**：

- 67 行加在 H2 層級、不影響原有 7 問題決策樹結構
- H3 子段標號帶 case anchor（F4.7 / F4.10 / F3.16 / F4.14）— 跟模組 outline frame 對齊
- 「跟 Aurora fleet 治理的本質差異」表是 *新增加值* — outline Section G 沒明示要做、但解 R3 round 1 抓的「議題沒主寫」根因
- 跨 vendor 路徑表把 Standard Chartered 也納入比較（4 路徑、非 3 路徑）— 比 R3 round 1 建議的 3 路徑對比更完整

**章節編號修正連帶風險**：

- 跑 `grep "1\.[0-9]"` 沒找到其他文章引用「1.4 transaction boundary」、「1.6 schema migration」、「1.7 reconciliation」、「01.4 database migration」等漂移版本 — 修正乾淨
- `./bin/mdtools cards content/backend/01-database/` 通過、無 broken link

無新 critical issue 引入。

## Layer 1/2/3 對齊度

**Layer 1**：✓ 流暢（從 ✗ 升到 ✓）

- 6 vendor `_index.md` → 個別 deep article 路徑全打通
- 兩個 entry article（DB3 vendor-selection / DB4 decision-tree）在 `vendors/_index.md` 顯式入口段
- Reader 可從 vendors 表直接進 deep article、也可從 entry 走 driver path 路徑

**Layer 2**：✓ 仍流暢

- sibling cross-link 紀律維持
- CockroachDB sibling 全部 cross-link 到 cluster boundary SSoT
- Aurora fleet ↔ CockroachDB locality / cluster boundary 雙向引用清晰

**Layer 3**：✓ 仍流暢（無變動）

- MongoDB connection-management / DynamoDB single-table / Aurora read-replica-scaling 仍承擔 production 跨層架構議題
- 新增 CockroachDB cluster boundary SSoT 段補強了 cluster topology 視角的 Layer 3 缺口

## Frame 1-8 覆蓋健康度（變化）

| Frame                            | Round 1                    | Round 2 | 變化                                          |
| -------------------------------- | -------------------------- | ------- | --------------------------------------------- |
| Frame 1 vendor 適用度前置判讀    | ⚠ MongoDB / Cosmos DB 偏弱 | ⚠ 同    | 未動（commit 標 Stage 6 polish）              |
| Frame 2 vendor 選型路徑分型      | ✓                          | ✓       | 維持                                          |
| Frame 3 fleet vs single instance | ⚠ MongoDB / DynamoDB 偏弱  | ⚠ 同    | 未動                                          |
| Frame 4 capacity 抽象單位        | ✓                          | ✓       | 維持                                          |
| Frame 5 合規邊界                 | ⚠ DynamoDB 偏弱            | ⚠ 同    | 未動                                          |
| Frame 6 production 跨層架構      | ✓                          | ✓       | 維持 + 新增 CockroachDB cluster boundary 角度 |
| Frame 7 vendor 數字口徑          | ✓（最一致）                | ✓       | 維持                                          |
| Frame 8 event-driven scaling     | ✗ Aurora → DynamoDB 單向   | ✗ 同    | 未動（commit 標 Stage 6 polish）              |

Round 2 沒新增 Frame 覆蓋、僅修了 SSoT 主寫紀律。Frame 1/3/5/8 強化在 commit message 明標延後到 Stage 6 polish — 不算 regression、是 *已知 deferred*。

## 最終跨章一致性評分

**8.7/10**（從 8.0/10）

達成 commit message 預估的 8.5+ 目標、稍微超出。

- ✓ Layer 1 路徑斷裂全解（最 critical、單獨值 +0.4）
- ✓ SSoT 紙面 → 實質主寫（67 行、含 Aurora fleet 對照、+0.2）
- ✓ 4 處編號漂移全修、target weight 對齊（+0.1）
- ⚠ Frame 8 雙向 cross-link 仍單向、Frame 1/3/5 仍偏弱 — 但 commit message 已標 Stage 6 polish、不視為 regression
- 沒新 critical issue 引入

剩餘改進空間（Stage 6 polish 候選）：

1. Aurora read-replica-scaling 補 reverse cross-link 到 DynamoDB on-demand + Frame 8 5 模式對照
2. MongoDB 5 篇補「MongoDB 適用度前置判讀」Frame 1 段
3. DynamoDB 5 篇補「合規邊界」Frame 5 段（global-tables-conflict 從 9.C24 Genesys 切入）

這三項不是 Stage 5.5 的 scope、不影響 Round 2 verification 結論。
