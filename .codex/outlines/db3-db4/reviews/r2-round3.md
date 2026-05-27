# R2-R3：案例引用準確性 Round 3 Final Verification

> Stage 6 polish commit `2de160f` 後 final verification、verify Polish 1 / Polish 2 是否提升 fidelity 至 92-95% 區間、是否引入新陷阱。

## 評分變化軌跡

- Round 1：90-93%
- Round 2：91-94%
- **Round 3：92-94%** — 達 92-95% 目標下緣、邊緣達標
- 提升驅動：Polish 1 Coinbase Low issue 真的修了；Polish 2 大部分新加段引用準確
- 提升受限：Polish 2 引入 1 處 Genesys compliance 過度推論 (Trap 1) + 1 處 5 模式 frame 不對齊 SSoT (Trap 6) — 不算 critical、屬 Low issue

## Polish 1 verification

### Coinbase 兩口徑分清（L32 / L55）

**狀態：✓ 真的修了、但 polish agent 加了 case 沒明說的分類詞**

逐項對齊 case 原文 `coinbase-mongodb-document-platform.md`：

- case L18：`Deploy 時 MongoDB 連線尖峰：~60K connections / minute（單 cluster）` — 單位「per minute」、屬 rate 性質
- case L19：`mongobetween 後連線降幅：30K → ~2K（一個量級）` — 「降幅」屬瞬時 count 前後對比

Polish 後 deep article L32 / L55：

- L32：「deploy 尖峰 *connection event rate* ~60K connections / 分鐘」「mongobetween 後 *steady-state concurrent connections* 由 ~30K 降到 ~2K」「兩者口徑不同、不是同一數字的連續變化」
- L55：「deploy 尖峰時 *connection event rate* 是 ~60K connections / 分鐘（unique connection 事件量、rate）」「mongobetween 介入後 *steady-state concurrent connection 數* 由 ~30K 降到 ~2K（瞬時量、前後對比、一個量級）」「引用時把 rate 跟瞬時 concurrent count 分開、不要壓成『60K 收斂到 2K』」

**過度推論風險評估**：case 原文用「per minute」跟「降幅」、沒用「event rate」/「steady-state concurrent」這兩個技術分類詞。Polish agent 把單位 hint 延伸成正式類別詞 — *屬合理工程推論*（per minute 確實是 rate 性質、降幅確實是瞬時 count 對比）、但屬「polish 加的分類層」不是「case 原文直接揭露」。

- 風險評估：Low — 推論方向正確、且加了「兩者口徑不同」明示口徑分層、不是壓縮成單一連續數字（這正是 Round 1 抓出的核心問題）
- 改進建議：未來引用時可加「（口徑分類為 polish agent 工程推論、case 原文以 per minute / 降幅 兩種單位呈現）」 — 屬選做

**結論**：Coinbase Low issue 從「合成成 60K → 2K」改進成「兩獨立口徑、不是連續變化」— Round 1 抓的核心問題真的修了、新加分類詞屬合理推論、不算 critical 編造。

### Spanner 5 處改寫的 case 引用對齊

**狀態：✓ 5 處 case 引用 0 誤傷**

逐項 diff verify（純單詞替換、無觸及 case 引用）：

- `truetime-api-depth.md` L23/L45/L61：3 處「寫稿時」→「引用時」 — Fact source 分層警告 / commit wait ≈ 2ε 數學引用紀律均純單詞替換、9.C10 dogfood 邊界 / OSDI 2012 論文出處 / 1-7ms ε 範圍出處保留
- `migrate-from-cloud-sql-pg.md` L45/L70：2 處「寫稿時」→「判讀時」/「引用時」 — 9.C10 dogfood 邊界 / 9.C14 Standard Chartered 對照 case anchor 保留

跨檔 spot check：vendors/ 下「寫稿時」零殘留（commit message 宣稱）— 確認已達。

## Polish 2 verification（10 檔 Frame audit 新加段）

### 逐篇新加段 case 引用 verify

#### aurora/read-replica-scaling.md Frame 8 段（L229-237）

**狀態：⚠ Low issue — 5 模式 frame 不對齊 SSoT**

case 引用 verify：

- FanDuel 季賽 cycle / 平日→playoff→championship→Super Bowl：case L31 直接揭露 — ✓
- Hard Rock 100→33→100 node：case L18-19 + L31 直接揭露「100 → 33 → 100 賽季常態 / 年度循環」— ✓
- DraftKings 讀寫雙峰錯位：在 Aurora L24 + L165 已 case-anchor、Frame 8 段 reference 之 — ✓

**Frame 不對齊 issue (Trap 6 風險)**：

Aurora L231 寫：「DynamoDB on-demand-vs-provisioned 的 5 模式分類（flash-sale spike / predictable peak / sustained growth / season cycle / surge baseline permanent shift / B2B 高可用）共軸」— 括號內列 6 項、宣稱是「5 模式」。

對照 SSoT on-demand-vs-provisioned.md L259-263 5 模式實際列舉：

1. flash-sale spike
2. predictable peak
3. sustained growth
4. surge baseline permanent shift
5. B2B sustained + 高可用

**`season cycle` 不在 SSoT 5 模式內** — Polish agent 自創「season cycle」作為 FanDuel + Hard Rock 共通的合成標籤、但宣稱是 SSoT 既有分類、且把 6 項稱為「5 模式」。

- 風險評估：Low — case fact 本身正確（FanDuel + Hard Rock 都揭露賽季循環）、但 frame 標籤 invent + 數字不一致（5 vs 6）屬 cross-chapter consistency issue
- 影響評分：case fidelity 本身不掉、但 Frame 8 共軸宣稱的紀律掉了

#### dynamodb/single-table-design-pattern.md Frame 3 退化段（L185-200）

**狀態：✓ 符合跨案合成 frame 明示紀律**

case 引用 verify：

- Aurora 200 cluster：DraftKings case L22 揭露「200 個 individual databases」— ✓
- CockroachDB 380+ cluster：Netflix case L17 揭露「380+ cluster」— ✓
- MongoDB 20 DB blast radius：Toyota case 已 anchor 在 vendor _index — ✓
- DynamoDB partition 自動 split / merge + 不走 fleet of clusters：屬 vendor 公開行為（managed feature）、非 case 揭露 — ✓ Trap 7 處理正確（managed 自動 partition 是工程常識、不偽裝成 case 揭露）

合成 frame 明示：表格 header 標「跨 vendor 共通 frame」、每 row 都有 case anchor / vendor capability 依據 — ✓

#### dynamodb/global-tables-conflict.md Frame 5 段（L208-223）

**狀態：⚠ Low issue — Genesys 合規角度為 over-inference**

case 引用 verify：

- Disney+ cross-device sync：pre-polish 已主寫、新段 reference 合理 — ✓
- Genesys 15 region active-active：case L19-21 直接揭露 — ✓

**Trap 1 risk (skeleton case 擴寫成 fact)**：

L210 寫：「9.C24 Genesys 15 region active-active 不全為『跨 region 同步』、也為『各市場合規分離』— 受監管市場的客服資料 pin 在當地 region、跨 region replication 只在合規允許的範圍內開啟」
L223 寫：「Genesys 15 region 中部分市場屬此型、不是 15 個 region 全互相 replicate」

對照 Genesys case 原文：

- L33（判讀 #3）case 明寫 15 region 動機是 *延遲就近接入*（「全球客戶就近接入」+「agent 操作介面卡 1 秒、客服效率掉一半」）、**非合規 driver**
- L38 case 自承「案例 *沒有* 提具體 QPS / RPS、訊息量、延遲分布」— case 對細粒度 region replication 配置零揭露
- case 全文無一處提到 GDPR / PIPL / LGPD / region-pinning / 合規分離 — 0 詞匹配

Polish agent 把 *vendor 通用能力*（DynamoDB Global Tables 確實支援 attribute 級 region 開關、屬公開能力 / pre-polish L68 + L71 已有 region-pinned data 框架）跟 *Genesys 案例細節* 綁定、attributes 給 Genesys「部分市場屬此型」的具體配置 — case 沒揭露這個。

- 風險評估：Low-Medium — 通用 vendor 能力宣稱正確、但 Genesys 個案配置屬編造
- 改進建議：拆兩段：
  1. 「DynamoDB Global Tables 支援 attribute 級 region pinning（vendor capability）」— 不綁案
  2. 「Genesys 15 region 是否 *全 active-active 或 部分 pinned* — case 未揭露、屬未知」— 明示不確定

#### mongodb/replica-set-read-preference.md Frame 5 段（L208-223）

**狀態：✓ vendor capability + GDPR engineering frame 處理得當**

claim verify：

- MongoDB / Atlas 無 row-level locality：屬 vendor 公開能力對比 — ✓
- cluster-per-region 拓樸吸收合規：屬 engineering frame、不是 case 揭露 — ✓ frame 來自 vendor 能力推論、不偽裝 case
- Atlas global cluster (zone sharding) GDPR 軟條款 fit：vendor capability 明示、未綁特定 case — ✓

無 case 過度引用、無 Trap 1 / Trap 3。

#### 8 篇 Frame 1 cross-link（blockquote 前置判讀）

**狀態：✓ SSoT 指向正確、無 case 升級**

8 篇（4 MongoDB + 4 DynamoDB）blockquote 統一模式「進到 X 設計前先確認 workload 在 Y 適用區 — 詳見 SSoT、本篇不重複展開」：

- DynamoDB 4 軸 SSoT：single-table-design-pattern L13「DynamoDB 適用度前置判讀（4 軸）」存在 — ✓
- MongoDB 3 軸 SSoT：schema-design-pattern L15「MongoDB 適用度的前置判讀有三件事」存在 — ✓
- cross-link 內容只標 SSoT 位置 + 路由判讀、無 case 細節引用、無「case 揭露適用度」這種錯誤升級 — Trap 8 風險避開 ✓

### 8 陷阱重 audit（針對 Polish 動到 13 檔）

| 陷阱                           | Round 1 | Round 2 | Round 3                           |
| ------------------------------ | ------- | ------- | --------------------------------- |
| 1 skeleton case 擴寫成 fact    | 0       | 0       | 1 Low (Genesys 合規 over-infer)   |
| 2 完整 case 過度合成           | 0       | 0       | 0                                 |
| 3 dogfood 數字當 production    | 0       | 0       | 0（Spanner 9.C10 邊界全保留）     |
| 4 觀察 / 判讀分層              | 維持    | 維持    | 維持                              |
| 5 case 自帶警示被刪            | 0       | 0       | 0（FanDuel 5-10x scope 保留）     |
| 6 跨案合成 frame 未明示        | 0       | 0       | 1 Low (5 模式列 6 項數字不一致)   |
| 7 通用估算 vs case 揭露混淆    | 0       | 0       | 0（partition managed 處理正確）   |
| 8 跨案合成升級成 case 揭露適用 | 0       | 0       | 0（Frame 1 blockquote 無此 risk） |

## 最終 case fidelity 評分

**Round 3 case fidelity：92-94%**（邊緣達標 92-95% 目標、Round 2 91-94% 微幅提升）

提升項：

- Coinbase Low issue Round 1 → Round 3 修復（從合成「60K → 2K」改為兩獨立口徑明示）— 唯一持續性 Low issue 清掉
- Polish 1 Spanner 5 處純單詞替換、case 引用 0 退化
- Polish 2 大部分 frame audit 段 case-backed（Frame 3 Aurora/CRDB/MongoDB 數字 / Frame 8 FanDuel/Hard Rock 季賽 / Frame 5 MongoDB vendor capability）
- 8 篇 Frame 1 blockquote SSoT 指向正確、無 Trap 8 升級風險

新引入小 issue（不影響邊緣達標）：

- Genesys 合規角度 over-inference（global-tables-conflict L210 / L223 — Trap 1 Low）
- Aurora Frame 8 段 5 模式列 6 項 + 自創「season cycle」frame 標籤（Trap 6 Low、case fact 本身正確）

**邊緣達標、未達 95% 上緣** — 兩處 Low issue 都屬「polish agent 為了強化 frame 共軸而加了 case 沒明說的細節」、屬 Stage 6 強化動作的 trade-off。Critical / High issue 仍是 0。

### 跟 7 個 case-first batch 對比

| Batch                        | Round 結束 fidelity            |
| ---------------------------- | ------------------------------ |
| backend/01 db3-db4 (本批 R3) | **92-94%**                     |
| backend/01 db3-db4 R2        | 91-94%                         |
| backend/01 db3-db4 R1        | 90-93%                         |
| 此前 6 batch（baseline）     | 85-90%（per round 1 sampling） |

**結論**：本批 Round 3 達 case-first methodology 7 batch 以來最高 baseline、邊緣達 92-95% 目標下緣、模組可發布。

## 剩餘 polish backlog（建議 Stage 7 或下次模組）

1. **Genesys 合規角度過度推論修正**（low priority、可留下次）：global-tables-conflict L210 / L223 改成「vendor capability + Genesys 未揭露」雙段
2. **Aurora Frame 8 段 5 模式列舉對齊 SSoT**（low priority、可留下次）：把括號內 6 項改成 SSoT 既有 5 項、`season cycle` 改成 SSoT 中對應的模式名 / 或在 SSoT 補第 6 模式
3. **Coinbase 兩口徑可加 polish agent 明示**（optional）：「（口徑分類為工程推論、case 以 per minute / 降幅 呈現）」

3 條都屬 polish 後的細節微調、不影響模組發布。

## 結論

Polish 1 / Polish 2 整體成功 — Coinbase Low issue 真的修了、Spanner 5 處改寫 0 誤傷、10 檔 Frame audit 新加段大部分 case-backed。新引入 2 處 Low issue（Genesys 合規 over-infer / Aurora 5 模式 frame 不對齊）屬「強化 frame 共軸」trade-off、不算 critical regression。

Round 3 case fidelity 92-94%、邊緣達 92-95% 目標下緣、模組品質維持 case-first methodology 7 batch 以來最高 baseline、可發布。
