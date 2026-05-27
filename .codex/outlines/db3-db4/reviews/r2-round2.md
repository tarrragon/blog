# R2-R2：案例引用準確性 Round 2 Verification

> Stage 5 reviewer R2 round 2、verify Stage 5.5 修正循環（commit `2991437`、21 檔 / +201/-160 行）是否 regression。Round 1 baseline 90-93% case fidelity。

## Round 1 → Round 2 評分變化

- Round 1：90-93% case fidelity（7 個 case-first batch 以來最高、0 critical 編造 / 0 High issue / 1 Low issue）
- Round 2：**91-94%** case fidelity（維持並微幅提升）
- 變化驅動：
  - **新加 67 行 SSoT 主寫段** 引入 4 個新 case 引用、全部回得到原文、跨案合成 frame 明示完整、未引入新陷阱
  - **7 篇 15 處「寫稿時」→「引用時/判讀時」** meta-talk batch rephrase 純單詞替換、無動到 case 引用本身
  - **3 篇 Spanner 末尾 editorial residue 刪除** 刪的是 editorial checklist、無 case 引用、未誤傷
  - **6 vendor _index.md description 更新** 全部對齊 deep article 既有 case anchor 與 scope warning、無編造、無壓縮
  - **唯一 Low issue（Coinbase 60K → 2K）** carry-forward 未處理、不影響整體評分（Stage 5.5 commit list 未含 `connection-management-and-cache-layer.md`）

## Regression check 結果

### A. 7 篇高密度修改 case 引用對齊

**狀態：✓ 維持（全部 7 篇 case 引用零退化）**

Fix3 meta-talk batch 動的 15 處全部是「寫稿時」→「引用時 / 判讀時」單詞替換、無觸及 case 引用本身。逐篇 diff 確認：

- **cosmosdb/mongodb-api-vs-sql-api.md（4 處）**：line 25 (Microsoft 365 dogfood)、line 39 (三型 frame 合成)、line 69 (multi-model 條件性價值)、line 80 (跨雲 hedging) — 4 處皆只動句首副詞、case fact / scope warning / 來源層次原話保留
- **cosmosdb/ru-cost-model-sizing.md（4 處）**：line 70 (index policy 判讀)、line 136 (合成表警示)、line 209 (ASOS 48ms 拆解)、line 222 (跨 vendor 對照合成) — 9.C21 ASOS 48ms 跟 9.C11 Minecraft Earth 1M RU/s 壓測 scope warning 完全保留
- **cosmosdb/multi-region-write-conflict.md（1 處）**：line 241 Toyota 99% 實測 + 鏈路問題保留
- **cosmosdb/partition-key-design.md（1 處）**：line 88「9.C11 沒直接揭露此對比、從 outline knowledge 跟 MongoDB shard-key-selection 對照得出」明示保留
- **spanner/consistency-models-comparison.md（2 處 + SSoT cross-link 改 target）**：跨洲 quorum vs commit wait 分層保留、9.C10 dogfood 邊界保留；SSoT cross-link 從 `consistency-levels-engineering` 改到 `multi-region-write-conflict` 是路由修正、不動 case
- **cockroachdb/survival-goals.md（1 處）**：Netflix Gaming 48-node 跨 4 region 判讀「不是 latency 優化」原話保留
- **cockroachdb/aurora-dsql-spanner-decision-tree.md（2 處）**：「Spanner 10+ 年」來源層次明示保留、self-managed cluster vs 平台團隊轉折點 case 沒講具體閾值警示保留

**Quote evidence**：ru-cost-model-sizing line 49「9.C11 揭露『100 萬 RU/s 壓測通過』 — 壓測通過數字、不是 production 持續跑（case 自己警示）」原話完整保留。

### B. Cluster boundary SSoT 主寫段 67 行 case 引用

**狀態：✓ 4 個 case anchor 全部回到原文、跨案合成 frame 100% 明示**

新加段（`cockroachdb/aurora-dsql-spanner-decision-tree.md` line 224-289）的 case 引用逐一 verify：

- **Netflix 380+ cluster artery of small DBs（F4.7 / 9.C40）**：對照 case 原文 line 17（總 cluster 380+）+ line 41（artery of small DBs 哲學）+ line 47（Database Platform Team） — *完全對齊*、無數字壓縮、無哲學詞創造
- **Hard Rock 邏輯一個 cluster（F4.10 / 9.C41）**：對照 case 原文 line 21（跨所有 region 一個 logical database）+ line 17（8 州營運）+ line 37（Wire Act 跨州統一帳戶 / reporting / 欺詐偵測 transactional） — *完全對齊*
- **DraftKings 200 cluster business sharding（F3.1 / 9.C4）**：對照 case 原文 line 22（200 個 individual databases）+ line 37（100 萬 ops/分鐘 = ~17K ops/秒、跨 200 個 databases 平均下來每個 DB 約 80 ops/秒） — *17K ops/sec / 80 ops/sec per cluster 數字精確、case 原文跟 SSoT 段一致*
- **Standard Chartered 7 cluster fleet（F3.6 / 9.C14）**：對照 case 原文 line 29（7 個受監管市場代表 7 個獨立 cluster、資料不能跨境）— SSoT 段稱「每監管市場一個 cluster、合規禁止跨市場資料流動時的 forced pattern」對齊原文

**跨 case 合成 frame 明示**：

- 「跟 Aurora fleet 治理的本質差異」段（line 254-271）明示「Aurora 拆是被迫（單 cluster 撐不住）、CockroachDB 拆是選擇（單 cluster 撐得住、拆是為了治理）」— 屬本章合成、case 原文無此對比、合成 frame 明示完整
- 「兩條路徑的判讀軸」對照表（line 240-249）case 原文未提供統一表格 — 屬本章合成、但每 row 都對齊到「per-app cluster」跟「邏輯一個 cluster」case fact
- 「跨 vendor 路徑對照」（line 273-279）每 row 都有 case anchor（DraftKings / Netflix / Hard Rock / Standard Chartered）— 無憑空編造、Aurora fleet 跟 Hard Rock 跨地理單一 cluster 跟 Standard Chartered fleet per-jurisdiction 三條路徑 *拆與不拆動機* 對照屬本章合成 frame

**結論**：67 行新加段引入 0 個新陷阱、case fidelity 提升（多了 4 個 case anchor 主寫位置、滿足 R3 抓的「link 紙面成立、實際沒主寫」issue）。

### C. Coinbase 60K → 2K Low issue

**狀態：✗ 未修復、carry-forward Low issue**

`mongodb/connection-management-and-cache-layer.md` 不在 Stage 5.5 commit `2991437` 的 21 檔 list 內、line 32 / line 55 仍合成「60K → ~2K connections」、跟 Round 1 同 Low issue 殘留。

具體：

- line 32 case anchor：「9.C36 Coinbase 是 rich case，含具體數字（60K → ~2K connections / 1.5M reads/sec 含 cache / 70 → 25 分鐘擴容）」 — 仍合成
- line 55：「mongobetween proxy（Coinbase 自建）：把多 application process 的連線合成少量到 MongoDB cluster 的連線、connection 從 60K 降到 ~2K（一個量級）」 — 仍合成

這個 issue Stage 5.5 標為 Low priority、留 Stage 6 polish pass、屬已知保留、不算 regression。

### D. Spanner editorial residue 刪除誤傷風險

**狀態：✓ 0 誤傷**

3 篇 Spanner 末尾刪除段為 H2「完稿檢查（讀者導向）」editorial checklist：

- `truetime-api-depth.md`：5 行 checklist（dogfood 邊界 / TrueTime ε 來源 / cross-reference 列表）— 全部是給作者的提醒、無 case 引用
- `schema-migration-interleaved-tables.md`：6 行 checklist（DDL long-running / interleaved storage-level / 9.C10 dogfood 邊界）— 同上
- `migrate-from-cloud-sql-pg.md`：9 行 checklist（Driver no-go / 9.C10 dogfood / cost crossover）— 同上

刪前的 case anchor（9.C10 / 9.C14）都在前段保留、Round 1 audit 確認的 8 處 truetime dogfood edge labels 跟 4 處 consistency-models-comparison dogfood edge labels 完整保留。

### E. Navigation description 編造風險評估

**狀態：✓ 0 編造、全部對齊 deep article 既有 case anchor + scope warning**

6 個 vendor _index.md description 逐一檢查：

- **aurora/_index.md**：DraftKings 6ms 寫 / <1ms 讀 標「production reference」對齊 Round 1 audit (storage-architecture line 122-126)、FanDuel「雙 SLO 並行」未壓縮成「5-10x peak」單一數字、Standard Chartered「合規 lead time」對齊 case 自帶警示（lead time 隨產業差異大）
- **cockroachdb/_index.md**：Netflix「380+ artery of small DBs」對齊 case 原文哲學、Hard Rock「RPO=0 倒推」對齊 case 揭露的業務動機、transaction-retry-pattern 明示「5 種 retry failure mode（跨 case 合成 frame）」 — 合成 frame 標籤完整
- **cosmosdb/_index.md**：Minecraft Earth「1M RU/s 壓測」 — 標「壓測」沒升級成「Cosmos DB 永久 capacity」、Microsoft 365「dogfood 邊界」對齊
- **dynamodb/_index.md**：Tixcraft「6750x 擴展」對齊 9.C15、Zomato 50% / Zoom 30x / Amazon Ads sustained workload 都是 case 揭露具體場景、Genesys「99.999% / 15 region」未升級成「永久承諾」
- **mongodb/_index.md**：Coinbase「mongobetween + freshness token + ML 預測擴容三件套」沒提具體 60K → 2K（避開 Low issue 風險）、Toyota「20 DB blast radius」對齊
- **spanner/_index.md**：所有 4 篇 deep article description 都明示「9.C10 Google internal dogfood」、commit wait 數學標「ε 暴衝失敗模式」屬 case 揭露範圍

**無編造、無壓縮 case 自帶警示、無跨多 workload 警示丟失**。

## 5 篇抽 sample 8 陷阱 audit

| 篇章                                                            | 1 編造 | 2 擴寫過頭 | 3 dogfood 誤用 | 4 觀察判讀分層 | 5 自帶警示刪除 | 6 跨案合成未明示 | 7 通用估算混淆 | 8 合成升級揭露 |
| --------------------------------------------------------------- | ------ | ---------- | -------------- | -------------- | -------------- | ---------------- | -------------- | -------------- |
| cosmosdb/mongodb-api-vs-sql-api.md（Fix3 改 4 處）              | 0      | 0          | 0              | 維持           | 0              | 0                | 0              | 0              |
| cosmosdb/ru-cost-model-sizing.md（Fix3 改 4 處）                | 0      | 0          | 0              | 維持           | 0              | 0                | 0              | 0              |
| cockroachdb/aurora-dsql-spanner-decision-tree.md（+67 行 SSoT） | 0      | 0          | 0              | 維持           | 0              | 0 *（4 處明示）* | 0              | 0              |
| cockroachdb/transaction-retry-pattern.md（Fix2 .md → route）    | 0      | 0          | 0              | 維持           | 0              | 0                | 0              | 0              |
| 3 篇 Spanner editorial residue 刪除                             | 0      | 0          | 0              | 維持           | 0              | 0                | 0              | 0              |

## 新 case 引用 issue（若有）

**無新 case 引用 issue**。Stage 5.5 修正循環沒有引入新陷阱。

唯一持續存在的議題：Round 1 抓的 Coinbase 60K → 2K Low issue carry-forward 未修復、屬已知保留、不算 regression。

## 最終 case fidelity 評分

**Round 2 case fidelity：91-94%**（維持並微幅提升）

- 維持 baseline：Round 1 的 90-93% baseline 在 21 檔修改後完全保留、無 case 引用退化
- 微幅提升：67 行 cluster boundary SSoT 主寫段引入 4 個高品質 case anchor（Netflix / Hard Rock / DraftKings / Standard Chartered），全部對應到 case 原文、跨案合成 frame 100% 明示、補強 R3 抓的「link 紙面成立、實際沒主寫」issue 同時不損失 case fidelity
- 唯一 carry-forward：Coinbase Low issue 留 Stage 6 polish pass（commit message 明示 Low priority 保留）

本批 Stage 5.5 修正循環是 case-first 方法論 *修正循環不引入新陷阱* 的高品質範例 — meta-talk batch 純語境化、SSoT 主寫補強 case anchor 對齊原文 + 合成 frame 明示完整、editorial residue 刪除避開 case 段、navigation description 嚴守不升級紀律。
