# R1-R2：寫作規範 Round 2 Verification

Reviewer: R1 (writing-spec dimension, round 2)
Scope: Stage 5.5 修正 commit `2991437` 對 31 篇 deep article + 2 entry article 的修正驗證
Method: 逐 issue regression check + Fix1/Fix3 新加段落 §1 / §8 audit + 自動化掃描

## Round 1 → Round 2 評分變化

- Round 1: A-（4.3 / 5）
- Round 2: A（4.6 / 5）
- 變化驅動：
  - Issue 1（Spanner editorial residue × 3）100% 清除、末尾過渡自然
  - Issue 2（deep-article tag）已補齊、31 篇 frontmatter 一致
  - Issue 3（.md extension link × 2）已改成 Hugo route
  - Issue 4（「寫稿時」meta talk）26 → 5（−21、80% 清除）、剩餘 5 處全集中 2 篇 Spanner、屬 Stage 5.5 未列入 Fix3 scope 的 Spanner side
  - Fix1 navigation 7 個 _index.md 表格全符合 §8 markdown spec（aligned style + CJK 雙寬）
  - Fix3 67 行 SSoT 段（aurora-dsql-spanner-decision-tree）4 個 H3 子段嚴格遵守原則一、表格全補延伸段、跟 Aurora fleet 治理本質差異對照清晰
- 扣 0.4 分主因：Spanner 2 篇 5 處「寫稿時」殘留（Fix3 漏 scope）

## Issue 1-4 修正驗證（逐項）

### Issue 1 — 3 Spanner editorial residue checklist

- 狀態：已修復
- 證據：
  - `grep -n "完稿檢查" content/backend/01-database/vendors/spanner/{truetime-api-depth,schema-migration-interleaved-tables,migrate-from-cloud-sql-pg}.md` 零命中
  - 3 篇末尾段過渡：truetime-api-depth.md L168 「Anti-recommendation」收尾、schema-migration-interleaved-tables.md L261 「Anti-recommendation」收尾、migrate-from-cloud-sql-pg.md L337 「Anti-recommendation」收尾。三篇 closing pattern 一致、`## Anti-recommendation` 自然承接前段、無 dangling
- 行數變化：truetime-api-depth −8、schema-migration −9、migrate-from-cloud-sql-pg −12（diff −29 行）跟 commit message 完全一致

### Issue 2 — migrate-from-cloud-sql-pg.md 缺 deep-article tag

- 狀態：已修復
- 證據：`tags: ["backend", "database", "spanner", "global-sql", "migration", "playbook", "postgresql", "cloud-sql", "deep-article"]` — deep-article 在最後一格
- 跟其他 30 篇 frontmatter 一致性：通過

### Issue 3 — transaction-retry-pattern.md .md extension link × 2

- 狀態：已修復
- 證據：
  - `grep -nE "\]\(/backend[^)]+\.md\)" content/backend/01-database/vendors/cockroachdb/transaction-retry-pattern.md` 零命中
  - L303 / L331 兩處 `mvcc-lock-model.md` → `mvcc-lock-model/`（Hugo route trailing slash）

### Issue 4 — 「寫稿時」meta-writer talk batch pattern

- 狀態：部分修復（26 → 5、80% 清除）
- 殘留 5 處（全集中 2 篇 Spanner、Fix3 未列入 scope）：
  - `spanner/truetime-api-depth.md:23` — Fact vs derive 分層警告段「寫稿時這條分層在每段引用具體數字時都會重申」
  - `spanner/truetime-api-depth.md:45` — Fact source 分層警告段「寫稿時這組數字明標『來自 Spanner vendor docs / 2012 論文』」
  - `spanner/truetime-api-depth.md:61` — commit wait 數學段「寫稿時引用這條數學要附『來源 vendor docs / paper』」
  - `spanner/migrate-from-cloud-sql-pg.md:45` — Cloud SQL HA / Spanner 100 pu cost 對比段「寫稿時要把 Cloud SQL HA cost vs Spanner 100 pu cost 對比清楚」
  - `spanner/migrate-from-cloud-sql-pg.md:70` — 無強 customer case 段「寫稿時必須明示『9.C10 揭露的線性 scaling / line-rate 設計目標是 Spanner 設計依據』」
- Fix3 commit message 自稱「7 篇 15 處」批改、原 round 1 統計是 26 處跨 11 篇 — 差值 11 處有部分在原統計外（如 cosmosdb/consistency-levels-engineering、cosmosdb/multi-region-write-conflict 各 1 處已修）、但 Spanner 兩篇 5 處未清乾淨
- 改後 cosmosdb / cockroachdb 樣本：「寫稿時必須明示」→「引用時必須明示」、「寫稿時要把 multi-model 當『條件性價值』」→「判讀時要把 multi-model 當『條件性價值』」、語意對讀者完全成立、不是機械替換
- 建議：Stage 6 polish pass 處理 Spanner 殘留 5 處

## Fix1 navigation 新增內容品質審查

### vendors/_index.md（覆蓋進度表 + Cross-vendor entry point 段）

- 表格列 mongodb / dynamodb / aurora / spanner / cosmosdb / cockroachdb 6 vendor 的 deep article 從「—」改成完整連結清單、表格符合 §8 aligned 規範（mdtools lint 通過）
- 新加「Cross-vendor entry point」段（L51-58）核心原則先行：「跨 vendor 選型不該直接讀單一 vendor overview — 先用 entry article 判斷 driver path、再進個別 vendor 深度」— 符合原則一
- DB3 / DB4 入口段 framing 對齊「driver-case-driven、不只是特性對照表」— 符合原則三（商業邏輯先於 case）

### 6 個 vendor _index.md（Deep article 已完成段）

- 6 個 vendor _index 全有「Deep article（已完成）」開頭段、句首先說段落責任（「本批 X 篇 deep article 已完成、覆蓋 Vendor 從 A 到 B 的核心 production 議題」）— 符合原則一
- 每篇表格 3 欄（主題 / 文章 / 對應 production 議題）符合 §8 aligned + CJK 雙寬規範
- 「production 議題」欄位明示 case anchor（DoorDash 1.636 M QPS / Netflix 380+ / Hard Rock RPO=0 / Microsoft 365 dogfood / 9.C10 / Toyota 99%）— 符合原則三 + 案例反推
- mdtools lint 通過

### 章節編號修正（4 處）

- mongodb/schema-design-pattern L198：「1.3 transaction boundary」指 `/backend/01-database/transaction-boundary/` — 正確
- mongodb/change-streams-kafka L182：「1.7 schema migration rollout evidence」+「1.9 reconciliation data repair」對應 `/schema-migration-rollout-evidence/` `/reconciliation-data-repair/` — 正確
- cockroachdb/hlc-raft-consensus L232：「1.6 database migration playbook」對應 `/database-migration-playbook/` — 正確
- spanner/consistency-models-comparison L101 + L193：SSoT 兩處改 `/cosmosdb/multi-region-write-conflict/` — 正確指向實際 SSoT 主寫位置

## Fix3 SSoT 主寫段品質審查（aurora-dsql-spanner-decision-tree.md L224-289）

### 原則一-八對照

- **原則一（核心原則先行）**：通過。L226 開頭句「選完 vendor 還有一個正交的拓樸決策：CockroachDB cluster 的『顆粒』要切多細」— 段落責任 + scope 明示先行
- **原則二（正向陳述優先）**：通過。負向句 1 處（「不是 vendor 選擇議題」）作為 scope warning、合理
- **原則三（商業邏輯先於 case）**：通過。每個 H3 先說機制再引 case（Netflix 380+ / Hard Rock 8 州）
- **原則四（表格不是終點）**：通過。兩個表格（判讀軸 6 行 / Aurora fleet vs CockroachDB 4 行）每個都跟在實際的判讀順序段（L265）或本質差異段（L280）後面 — 表格用於整理、不取代敘事
- **原則五（避免專案綁定）**：通過。F4.7 / F4.10 / F4.9 case 編號跟 outline 對齊、無 internal slug 違規
- **原則六（不用新手字樣）**：通過
- **原則七（可操作判準）**：通過。L265「判讀順序：先問跨服務 query 需要 transactional 嗎 → 再問 SLA / compliance 是否硬隔離」— 兩階段判讀路徑明示
- **原則八（情境優先於模板）**：通過。Per-app vs 邏輯一個 cluster 兩條路徑各自完整講判讀訊號 + 代價、不是同一欄位塞兩種情境

### 新加段落結構觀察

- 4 個 H3 子段順序：Per-app（Netflix 路徑） → 邏輯一個（Hard Rock 路徑） → 判讀軸對照 → 跟 Aurora fleet 本質差異 → 跨 vendor 路徑對照（這是子列表、不是 H3）
- 「跟 Aurora fleet 治理的本質差異」H3 是 Round 1 review 未及的 SSoT 補強點 — 明示 Aurora 拆 cluster 是被迫（繞 single-primary）、CockroachDB 拆 cluster 是選擇（治理）、本質差異對照表 4 行清晰
- 跨 vendor 路徑對照子列表（L284-287）4 種 case-driven 形貌：Aurora fleet / CockroachDB per-app / CockroachDB 邏輯一個 / CockroachDB fleet per-jurisdiction — 含 Standard Chartered 跟 Hard Rock 對照（合規顆粒粗 vs 細）、frame 紮實

### 沒引入新問題

- §8 markdown spec：aligned 表格 + CJK 雙寬 + 列表前後空行 + 無 emoji — 通過
- 無新負向句堆疊、無新 meta talk

## 自動化掃描結果

- 「寫稿時」殘留：5（全集中 spanner/truetime-api-depth.md × 3 + spanner/migrate-from-cloud-sql-pg.md × 2）
- emoji / 裝飾性 unicode 殘留：0
- .md extension internal link 殘留：0
- 「新手 / 新人」殘留：0（注意 mysql/proxysql-config.md L71 1 處「新手」在 DB1 batch 不在本次 scope）
- 裸 URL：0
- H1 在 body：0
- mdtools lint（vendor 全 batch + entry article）：通過、無 error 無 warning

### 負向句 top 5（變化）

- 主要 top 5 跟 Round 1 同（aurora/read-replica-scaling 31 / 371、cosmosdb/mongodb-api-vs-sql-api 30 / 223、aurora/storage-architecture 24 / 278、aurora/migrate-from-self-managed-pg-mysql 22 / 426、spanner/schema-migration-interleaved-tables 22 / 272）
- Fix3 SSoT 加 67 行只引入 1 處負向句（合理 scope warning）— 不改變排序、不違規
- 維持判讀：top 5 都是 scope warning / no-go condition 載重、不是逆向陳述主導

## 最終 polish pass 候選

- **Spanner 殘留 5 處「寫稿時」**（5 分鐘工作量）：
  - `spanner/truetime-api-depth.md` L23 / L45 / L61 — 全在 fact source 分層警告段、可改「引用時這條分層在每段引用具體數字時都會重申」/「引用時這組數字明標『來自 Spanner vendor docs / 2012 論文』」/「引用時這條數學要附『來源 vendor docs / paper』」
  - `spanner/migrate-from-cloud-sql-pg.md` L45 / L70 — 可改「判讀時要把 Cloud SQL HA cost vs Spanner 100 pu cost 對比清楚」/「引用時必須明示『9.C10 揭露的線性 scaling / line-rate 設計目標是 Spanner 設計依據』」
  - 這 5 處改完、Issue 4 就 100% 清除、總分上 A+
- 其他 Round 1 標記的負向句 top 5 維持原狀（合理 scope warning）

---

## 主 flow 行動建議

- Stage 5.5 修正循環整體成效顯著：3 個 High issue 100% 解、Medium batch pattern 80% 解、Fix1 / Fix3 新增內容品質高、無 regression
- 剩餘 5 處 Spanner「寫稿時」殘留是唯一 polish-pass 候選、5 分鐘可清乾淨
- 寫作規範層已達 production-ready、可進 Stage 6 final polish 或直接 ship
