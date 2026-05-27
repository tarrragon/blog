# R1-R4：寫作規範 Round 4 Final Final Verification

Reviewer: R1 (writing-spec dimension, round 4 final)
Scope: Polish 3 commit `ea7ae93`（8 檔 +15/-7 行 surgical edits）regression check + 5 自動化掃描 + 跨 vendor Frame 1 cross-link 句型一致性 final pass
Method: 逐 task 讀 diff、比對既有 MongoDB / DynamoDB Frame 1 cross-link 句型 baseline、自動化掃描全清

## 評分變化軌跡

- Round 1: A- (4.3 / 5)
- Round 2: A (4.6 / 5)
- Round 3: A+ (4.85 / 5)
- Round 4: **A+ (4.9 / 5)** — 微幅進步、Round 3 4 個 Low backlog 全清且無 regression

變化驅動：

- Task A Aurora Frame 8 對齊 SSoT 5 模式（self-created `season cycle` 標籤移除、改述為 `predictable peak` 時間序列展開）— 跨 vendor 共寫 SSoT 紀律拉滿
- Task B Genesys over-inference 降溫 — DynamoDB vendor capability vs case fidelity 明示分層、不犧牲教學深度（capability 三類場景仍列出、只是把合規應用標為「可能維度而非 case 已驗證」）
- Task C 4 處 dead link 全清 — 移除連結後純文字過渡自然、無斷句
- Task D Cosmos DB 4 篇 Frame 1 cross-link 補齊 — 路由完備性跟 MongoDB 4 篇 + DynamoDB 4 篇對齊

未達 5/5 主因：負向句 top 5 維持 Round 3 同水位（合理 scope warning 載重、polish pass 無 scope 處理、不算違規）。

## Polish 3 verification

### Task A：Aurora Frame 8 對齊 ✓

- 5 模式列項清晰：✓ — `flash-sale spike / predictable peak / sustained growth / surge baseline permanent shift / B2B sustained + 高可用` 確實是 5 項、跟 DynamoDB on-demand SSoT 對齊
- 流暢度：✓ — 首句「本表是 Aurora 端從讀峰視角切入的事件分級、跟 [DynamoDB on-demand] 的 5 模式分類共軸」說明段落責任（原則一）；「FanDuel 季賽 cycle 在 5 模式分類中對應 *predictable peak* 的時間序列展開」對應論述清楚、補強「事件 tier 已知 + 重複出現」的 predictable peak 在多 tier 結構下延伸的判讀邏輯
- §8 markdown spec：表格前後空行、列表前後空行、CJK 雙寬全通過
- 加分點：移除原 6 項列表的自創 `season cycle` 標籤、改成「FanDuel 季賽 cycle」+「predictable peak 時間序列展開」雙層對應 — 既保留 case fidelity（FanDuel 自帶 season cycle 語意）、又對齊 SSoT 5 模式分類

### Task B：DynamoDB Genesys 改寫 ✓

- vendor capability vs case 分層自然：✓
- 改後 L210 結構為三段式：
  1. capability 層描述（`region-pinned replication` 三類場景：合規分離 / cost-latency / 災備）
  2. Genesys case 揭露的事實（15 region 延遲就近接入、B2B SaaS 拓樸、未明示合規應用）
  3. capability 可能維度 vs case 已驗證實踐的分層判讀
- L223 補強：「具體是否套用、要看 *讀者自己的市場合規清單*、不是把 Genesys 規模當必然證據」— 把讀者操作判準（原則七）跟 case fidelity 紀律（避免 over-inference）合在一起、無編寫層 over-engineering
- 教學深度未犧牲：原本「DynamoDB 在這個 frame 退化最輕」的核心論述（attribute 級 region 開關）保留、只是合規應用層加上 fidelity 註記

### Task C：4 處 module-outline dead link 全清 ✓

- 4 處純文字過渡自然：✓
- dynamodb/global-tables-conflict L212：「跨 vendor 對照」— 表格前單句、自然
- dynamodb/single-table-design-pattern L187：「production scale 走 *fleet of clusters*（Aurora 200 cluster / CockroachDB 380+ cluster / MongoDB Atlas 20 DB 都是這個 frame）」— 括號內 inline 三 vendor 證據、不需要外部連結也讀得通
- mongodb/replica-set-read-preference L212：「跨 vendor 對照」— 跟 dynamodb/global-tables-conflict 同模式、表格前單句
- cosmosdb/multi-region-write-conflict L46：「— 本篇是 SSoT 主寫位置」— 直接結束、語意完整
- 觀察：4 處全用「移除連結 + 保留純文字」處理、不是改連結到別處、避免引入新的 broken link 風險

### Task D：Cosmos DB 4 篇 Frame 1 cross-link ✓

- 句型一致：✓ — 4 篇都用統一範本：

  > **Cosmos DB 適用度前置判讀**：本篇假設 workload 已通過 Cosmos DB 適用度四層 framing（API model 三型遷移路徑 / RU 思維轉換成本 / multi-model 差異化是否真用上 / 跨雲 hedging vs 單雲 lock-in）— 詳見 [mongodb-api-vs-sql-api 開頭四層 framing](../mongodb-api-vs-sql-api/#四層-framingvendor-selection-的真實決策軸)、本篇不重複展開。{議題} 是 *已選 Cosmos DB 後* 的 {決策類型}；若 workload 不適用 Cosmos DB、{議題} 無法救回 vendor 選錯的 {成本 / 風險}。

- 客製化結尾子句精準針對各篇主議題、非一刀切：
  - consistency-levels-engineering：「read / write 語義決策」+「level 選擇無法救回 vendor 選錯的取捨」
  - partition-key-design：「硬約束議題」+「無法救回 vendor 選錯的不可逆性風險」
  - ru-cost-model-sizing：「成本決策」+「無法救回 vendor 選錯的成本結構落差」
  - multi-region-write-conflict：「拓樸決策」+「strong global consistency 必要的 workload 應走 Spanner 或 Cosmos DB Strong（單一 write region）、不是用 LWW 補」 — 這篇結尾子句最強、直接點出 vendor 選錯的 fallback path
- 跨 vendor 句型一致性：跟 MongoDB shard-key（3 軸前置判讀）+ DynamoDB on-demand（4 軸前置判讀）對齊 — 軸數隨各 vendor 適用度判讀軸不同（MongoDB 3 / DynamoDB 4 / Cosmos DB 4 層 framing）、但句型結構完全相同

## 自動化掃描結果

| 項目                                        | Round 3 | Round 4 | 狀態 |
| ------------------------------------------- | ------- | ------- | ---- |
| 「寫稿時」vendors/ 殘留                     | 0       | **0**   | 維持 |
| 「season cycle」殘留                        | -       | **0**   | 全清 |
| 「Section B Frame / 模組 outline」dead link | 4       | **0**   | 全清 |
| emoji / 裝飾性 unicode 殘留                 | 0       | **0**   | 維持 |
| .md extension link 殘留                     | 0       | **0**   | 維持 |

5 個掃描全 0 hits、無 regression、無新引入 issue。

## 最終 polish backlog

無 critical 殘留、無新 issue。Round 3 列的 2 個邊緣 issue 狀態：

1. **負向句 top 5 維持原狀**：Round 4 維持同判讀（合理 scope warning 載重、非 polish pass scope）。Task A Aurora Frame 8 改寫含「靠的不是 mode 切換而是 replica fleet size」等負向句、屬合理載重、不影響段落主導句式。
2. **Polish 2 Frame 5 兩篇對照表 row 順序略有差異**：Polish 3 未動 row 順序、Round 4 維持 Round 3 判讀（nit、不影響可讀性）。若未來再做 polish 可統一順序、但 ROI 低。

## 主 flow 行動建議

- Polish 3 4 task 全通過寫作規範驗證、無 regression
- 5 個自動化掃描全清、整體模組寫作規範品質達 A+ (4.9 / 5)
- DB3 / DB4 / Cosmos DB 模組可直接發布、進入下一階段
- 不需要進 round 5、剩餘 2 個邊緣 issue 都屬合理載重 / nit、修改 ROI 低
