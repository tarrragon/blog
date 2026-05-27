# R1-R3：寫作規範 Round 3 Final Verification

Reviewer: R1 (writing-spec dimension, round 3 final)
Scope: Stage 6 polish pass commit `2de160f`（2 polish agent 平行、13 檔 +86/-8）對 Round 2 殘留 backlog 的修正驗證 + 新加段落寫作規範審查
Method: Polish 1（surgical fix 3 檔）+ Polish 2（Frame audit 10 檔）逐項 regression check + 自動化掃描 + cross-link 句型 / anchor 一致性 audit

## 評分變化軌跡

- Round 1: A- (4.3 / 5)
- Round 2: A (4.6 / 5)
- Round 3: **A+ (4.85 / 5)** — 達 A+ 目標
- 變化驅動：
  - Polish 1 Spanner 5 處「寫稿時」100% 清乾淨（Round 2 唯一扣 0.4 的議題）
  - Polish 1 Coinbase 兩口徑分清（rate vs concurrent count）讀者 context 充足、不過度技術
  - Polish 2 Frame 1 cross-link 8 篇句型完全一致（MongoDB 4 / DynamoDB 4）
  - Polish 2 Frame 3 / Frame 5 / Frame 8 新段全符合原則一（首句說段落責任）+ 原則四（表格後有延伸子段）
  - 自動化掃描 4 項全乾淨
- 未達滿分主因：負向句 top 5 維持原狀（合理 scope warning 載重、不是違規、polish pass 無 scope 處理）

## Polish 1 verification

### Spanner 5 處「寫稿時」批改

- 狀態：全清 0 殘留
- 證據：`grep -rn "寫稿時" content/backend/01-database/vendors/` 零命中
- 改後映射準確性（讀過原句 + 改後句）：
  - `truetime-api-depth.md` L23（Fact vs derive 分層警告）：「寫稿時這條分層在每段引用具體數字時都會重申」→「**引用時**這條分層...」— 動詞跟段落功能（讀者引用本文數字時要重申分層）匹配、語意對讀者完全成立
  - `truetime-api-depth.md` L45（Fact source 分層警告 1-7ms）：「寫稿時這組數字明標『來自 vendor docs / 2012 論文』」→「**引用時**這組數字明標...」— 同理、reader-facing
  - `truetime-api-depth.md` L61（commit wait ≈ 2ε 數學）：「寫稿時引用這條數學要附『來源 vendor docs / paper』」→「**引用**這條數學要附『來源...』」— 動詞精簡且精確
  - `migrate-from-cloud-sql-pg.md` L45（Cloud SQL HA cost vs Spanner 100 pu cost 對比）：「寫稿時要把 cost 對比清楚」→「**判讀時**要把 cost 對比清楚」— 對比的動作是讀者「判讀是否要升 Spanner」、映射準確（不是「引用」、是「判讀」）
  - `migrate-from-cloud-sql-pg.md` L70（9.C10 dogfood 邊界）：「寫稿時必須明示『9.C10 揭露的線性 scaling / line-rate 設計目標是 Spanner 設計依據』」→「**引用時**必須明示...」— reader-facing 引用紀律、正確

整體判讀：非機械替換、polish agent 依上下文選對「引用 / 判讀」、5 處都通過閱讀流暢度。

### Coinbase 兩口徑分清

- L32（case anchor 簡述）：「60K → ~2K connections」→「deploy 尖峰 *connection event rate* ~60K connections / 分鐘 / mongobetween 後 *steady-state concurrent connections* 由 ~30K 降到 ~2K — 兩者口徑不同、不是同一數字的連續變化」
- L55（mongobetween 機制段）：「connection 從 60K 降到 ~2K（一個量級）」→「9.C36 揭露兩個獨立口徑、不是同一數字的連續變化：deploy 尖峰時 *connection event rate* 是 ~60K connections / 分鐘（unique connection 事件量、rate）；mongobetween 介入後 *steady-state concurrent connection 數* 由 ~30K 降到 ~2K（瞬時量、前後對比、一個量級）。引用時把 rate 跟瞬時 concurrent count 分開、不要壓成『60K 收斂到 2K』。」
- 可讀性判讀：
  - 「connection event rate」+「steady-state concurrent connection 數」這兩個詞段內已附自然語言注釋（「unique connection 事件量、rate」/「瞬時量、前後對比」）、讀者不需要前置知識就能分辨兩口徑
  - L32 簡述 + L55 完整展開的兩階段處理符合原則一（先說段落責任）+ 原則四（case anchor 跟機制段各自承擔）
  - 沒有過度技術化反咬一口、改後句型不臃腫
- 判讀：通過、不需要再簡化

## Polish 2 verification

### Frame 1 cross-link 8 篇（MongoDB 4 + DynamoDB 4）

- 狀態：全通過
- 句型完全一致：8 篇都用 `> **{Vendor} 適用度前置判讀**：...詳見 [SSoT](...#anchor)、本篇不重複展開。{議題} 是 *已選 {Vendor} 後* 的 {決策類型}` 結構
- Anchor 驗證：
  - MongoDB 4 篇都指 `schema-design-pattern/#問題情境document-自由的後座力` — L13 H2 真實存在
  - DynamoDB 4 篇都指 `single-table-design-pattern/#dynamodb-適用度前置判讀4-軸` — L13 H2 真實存在
- 加分點：每篇結尾補一句「議題定位」（如 shard-key：「不是 vendor 選型決策」；on-demand：「mode 選擇無法救回 vendor 選錯的成本」；partition-key-anti：「若 4 軸不成立、改回 SQL 比補 composite key 更合理」）— 強化原則七可操作判準

### Frame 3 退化段（dynamodb/single-table-design-pattern.md）

- 通過
- 首句說段落責任：「跨 vendor 共通 frame：production scale 走 *fleet of clusters*... DynamoDB 在這 frame 退化得最徹底 — *不走 fleet of clusters*、是用 partition 內部自動切」— 原則一達標
- 表格 4 vendor 對照（DynamoDB / Aurora / CockroachDB / MongoDB）後有 2 個延伸子段：「DynamoDB 退化點」（partition 是 vendor 內部物理層、應用看到的永遠是一張 table）+「例外情境」（合規場景的「多 table per market」拓樸、動機跟 capacity scale 不同）— 原則四達標
- §8 markdown spec：aligned 表格 / CJK 雙寬 / 列表前後空行 / 無 emoji 全通過

### Frame 5 cluster-per-region 段（2 篇）

- **dynamodb/global-tables-conflict.md** 通過：
  - 首句「Global Tables 不只是高可用工具、也是 *合規邊界* 的吸收層」— 原則一達標
  - 4 vendor 對照表後 3 個延伸子段：「為什麼 DynamoDB 在這個 frame 退化得最輕」（attribute 級開關）+「何時 region-pinned 而非 active-active」（受監管金融 / GDPR strict / 中國 PIPL / 巴西 LGPD）— 原則四 + 原則七
  - Genesys 15 region 部分市場不加 replication 的具體判讀有保留情境敘事（不是抽象 best practice）— 原則三 + 原則八
- **mongodb/replica-set-read-preference.md** 通過：
  - 首句「MongoDB / Atlas 沒有 *row-level locality* 機制... 跨境合規必須以 *cluster-per-region* 拓樸吸收」— 原則一達標
  - 4 vendor 對照表後 2 個延伸子段：「MongoDB 在這 frame 的退化點」（read preference 解不了合規、即使 readPreferenceTags 路由到歐洲 secondary、primary 在亞洲 replication 仍跑、audit 不放行）+「Atlas 在合規場景的 fit」（zone sharding 軟條款 / strict 條款仍須 cluster-per-region）— 原則三 + 原則七

### Frame 8 雙向 cross-link（aurora/read-replica-scaling + dynamodb/on-demand-vs-provisioned）

- 通過
- aurora 端新加段位置正確（接 FanDuel 事件分級表後）、首句「本表是 Aurora 端從讀峰視角切入的事件分級、跟 [DynamoDB on-demand-vs-provisioned] 的 5 模式分類共軸」— 原則一達標
- 列出「DynamoDB 端的 5 模式分類」括號內展開（flash-sale spike / predictable peak / sustained growth / season cycle / surge baseline permanent shift / B2B 高可用）給讀者一個 mental map、不必先讀 DynamoDB 端
- DynamoDB 端 cross-link 句型也對應上：「本篇從 KV 層 mode 選擇切入、5 模式分類在本篇主寫；Aurora 從 SQL 讀副本視角切入、事件分級表... 在 Aurora 端主寫、本篇不重複展開」— 雙邊都明示 SSoT 分工
- 「兩 vendor 在 Frame 8 各自承擔」子列表（DynamoDB = 5 模式分類 SSoT / Aurora = read 峰值 headroom + 雙 SLO 並行 + fleet 治理）— 原則七可操作判準

### 跨段品質

- **Cross-link 句型一致性**：8 篇 Frame 1 cross-link + Frame 3/5/8 新段都用「詳見 ... 本篇不重複展開 / 本篇不展開」結構、無「見 / 參考 / 詳細」混用、句型紮實
- **新加表格規範**：3 個新 4 vendor 對照表（Frame 3 / Frame 5 × 2）欄寬一致、aligned 風格、CJK 雙寬、表格前後空行、無 emoji
- **章節編號 / cross-link target 真實性**：抽樣驗證 `single-table-design-pattern/#dynamodb-適用度前置判讀4-軸` / `schema-design-pattern/#問題情境document-自由的後座力` / Aurora read-replica-scaling FanDuel 事件分級表 — 都真實存在、anchor 對得上

## 自動化掃描結果

| 項目                        | Round 2 | Round 3 | 狀態           |
| --------------------------- | ------- | ------- | -------------- |
| 「寫稿時」vendors/ 殘留     | 5       | **0**   | 全清           |
| emoji / 裝飾性 unicode 殘留 | 0       | **0**   | 維持           |
| .md extension link 殘留     | 0       | **0**   | 維持           |
| 「新手 / 新人」殘留         | 0       | **0**   | 維持（DB3 外） |

### 負向句 top 5（對比 Round 2）

| 檔案                                              | Round 2 | Round 3 | 變化       |
| ------------------------------------------------- | ------- | ------- | ---------- |
| aurora/read-replica-scaling                       | 31      | 32      | +1（合理） |
| cosmosdb/mongodb-api-vs-sql-api                   | 30      | 30      | 維持       |
| aurora/storage-architecture                       | 24      | 24      | 維持       |
| db3-vendor-selection（取代 migrate-self-managed） | 22      | 22      | 排序變動   |
| aurora/migrate-from-self-managed-pg-mysql         | 22      | 22      | 維持       |

read-replica-scaling +1 來自 Polish 2 Frame 8 新加段含「靠的不是 mode 切換而是 replica fleet size」、屬合理 scope warning 載重、不是逆向陳述主導段落。Round 2 提出的「top 5 都是 scope warning 載重」結論在 Round 3 維持成立。

## 最終 polish backlog

無 critical 殘留。邊緣 issue：

1. **負向句 top 5 維持原狀**：Round 2 已判讀為合理 scope warning 載重、Round 3 維持同判讀。若未來想再壓、可考慮 read-replica-scaling 跟 cosmosdb/mongodb-api-vs-sql-api 兩篇做「以正向句重寫 no-go condition」實驗、但 ROI 低、不建議現在動。
2. **Polish 2 Frame 5 兩篇對照表 row 順序略有差異**：dynamodb/global-tables-conflict 表是「DynamoDB / Aurora / CockroachDB / MongoDB+Cosmos」、mongodb/replica-set-read-preference 表是「MongoDB+Cosmos / Aurora / CockroachDB / DynamoDB」— 兩篇都把主寫 vendor 放第一行、語意上可接受、不算違規。若要強迫一致可統一順序、但這是 nit、不影響可讀性。

兩個邊緣 issue 都不影響模組可發布。

---

## 主 flow 行動建議

- Stage 6 polish pass 整體成效：Round 2 唯一扣分項（Spanner 5 處）100% 解、Frame audit 把跨 vendor cross-link SSoT 分工打通、Coinbase 兩口徑分清也保住 case 引用準確性
- 寫作規範層達 A+ baseline（4.85 / 5）、production-ready
- 自動化掃描 4 項全乾淨、無 regression、無新引入 issue
- 模組可直接發布、進入下一階段（DB5+ 或其他模組）
