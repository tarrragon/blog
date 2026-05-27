# R1：寫作規範 Review Report

Reviewer: R1 (writing-spec dimension)
Scope: 31 篇 deep article + DB3 entry（commit 13b0c11 + 98c1e8d）
Method: 逐篇抽樣 review + 全 batch 自動化掃描（負向句 / emoji / H1 / TLD / weight / tag / 完稿檢查 / 寫稿時 meta talk）

## Overall 健康度

**整體分數：A-（4.3 / 5）**

31 篇 + DB3 entry 整體寫作規範品質很高、原則一-八的核心結構（核心原則先行、商業邏輯先於 case、可操作判準、情境優先）在絕大多數段落都嚴格遵守。Frontmatter 完整度、表格延伸段、negative 句作為 scope warning 的紀律都是 production-ready。Markdown 排版層面零 emoji、零裸 URL、weight unique。

### 跨篇系統性 pattern（最 critical 的 3 個發現）

1. **「完稿檢查（讀者導向）」editorial residue 殘留 3 篇 Spanner**：`spanner/truetime-api-depth.md:172`、`spanner/schema-migration-interleaved-tables.md:265`、`spanner/migrate-from-cloud-sql-pg.md:348` 末尾各有 `## 完稿檢查（讀者導向）` 章節、內含 `- [ ]` 任務 checklist。這些是寫稿時的 self-audit checklist、不是讀者導向內容（即使標題寫「讀者導向」）。每段話檢查的是「本文有沒有寫到 X」、屬寫作 backlog 而非教學內容。讀者讀到只會困惑。
2. **「寫稿時」meta-writer talk 跨 11 篇出現 26 次**：`寫稿時要明示 / 寫稿時必須 / 寫稿時要把` 等語法把作者意圖暴露在文章內、違反原則六（讀者定位用內容體現）。讀者要看的是「該怎麼做」、不是「作者該怎麼寫」。最高頻：`cosmosdb/ru-cost-model-sizing.md` (4 次)、`cosmosdb/mongodb-api-vs-sql-api.md` (4 次)、`spanner/truetime-api-depth.md` (3 次)、`cockroachdb/aurora-dsql-spanner-decision-tree.md` (3 次)。
3. **`migrate-from-cloud-sql-pg.md` 缺 `deep-article` tag**：其他 30 篇都有、此篇 frontmatter tags 列表獨缺、frontmatter 一致性 break。

## 各篇 issue 清單

### MongoDB

#### schema-design-pattern.md

- No issue。核心原則先行、contract layer 三路徑配合 case 引用、結構乾淨。負向句 9 / 206 行（多數是 scope warning，合理）。

#### shard-key-selection.md

- Low: 負向句密度 15 / 205 行（7%）— 多為 anti-pattern / no-go condition 的合理使用、但可審視是否有可改寫成正向陳述的句子（非優先）。

#### replica-set-read-preference.md

- No issue。

#### aggregation-pipeline-optimization.md

- No issue。

#### change-streams-kafka.md

- No issue。負向句最低（5 / 188）、寫得很正向。

#### connection-management-and-cache-layer.md

- No issue。

### DynamoDB

#### single-table-design-pattern.md

- No issue。4 軸前置判讀 + access pattern 反推 PK/SK + durable queue 正向用例三段都核心原則先行、案例引用紮實。

#### partition-key-antipatterns.md

- No issue。

#### gsi-lsi-design.md

- No issue。負向句密度高（17 / 208）合理 — 主題是 antipattern。

#### on-demand-vs-provisioned.md

- Low: 負向句 20 / 275、主因是 6 軸決策含多個「不該用 X 的條件」boundary。合理。

#### global-tables-conflict.md

- No issue。B2B vs B2C driver 表後段段延伸、表格沒留乾。

### Cosmos DB

#### consistency-levels-engineering.md

- Low: 「寫稿時」出現 1 次（line 4 description 內也有「engineering」keyword 但無問題）— 一筆 meta talk、不影響理解。

#### partition-key-design.md

- Medium: 「寫稿時必須明示」出現 2 次（line 88、240）— 把作者紀律寫進文章。建議改成 reader-facing「讀者引用 case 時要明示」或乾脆刪去（已有 scope warning 段落）。

#### ru-cost-model-sizing.md

- Medium: 「寫稿時」出現 4 次（line 70、136、209、222）— 跨篇 batch top 1。建議統一改成 reader-facing 表達。

#### mongodb-api-vs-sql-api.md

- Medium: 「寫稿時」出現 4 次（line 25、39、69、80）— 跨篇 batch top 1。同上、改 reader-facing。
- 注意：本篇結構 framing 4 層很強、四段 framing 各有業務邏輯先行、整體品質 A 級、只有 meta-writer talk 一處批評。

#### multi-region-write-conflict.md

- Low: 「寫稿時」出現 1 次（line 241）。

### Aurora

#### storage-architecture.md

- No issue。負向句 24 / 278（多為 scope warning 跟 anti-pattern、合理）。

#### cross-az-failover-rto.md

- No issue。

#### read-replica-scaling.md

- Low: 負向句 31 / 371 全篇最高、但本篇主題包含多個 antipattern / no-go / scope warning（合規邊界、雙 SLO 不該壓單一數字、FanDuel scope warning）— 合理。表格 + 延伸段結構嚴格、跨篇 top 質量之一。

#### global-database-multi-region.md

- No issue。

#### migrate-from-self-managed-pg-mysql.md

- No issue。負向句 22 / 426 自身比例不高（5%）、主題是 migration playbook 含大量 no-go condition、合理。

### CockroachDB

#### hlc-raft-consensus.md

- No issue。

#### survival-goals.md

- Low: 「寫稿時」line 76 出現一次。

#### transaction-retry-pattern.md

- Medium: line 303 `[PostgreSQL MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model.md)` link href 帶 `.md` extension — Hugo route 通常不含 `.md`、可能 broken link。line 331 同樣問題。建議改 `mvcc-lock-model/` 對齊其他 link 格式。

#### locality-aware-schema.md

- No issue。

#### aurora-dsql-spanner-decision-tree.md

- Medium: 「寫稿時」出現 3 次（line 111、212、244）— meta talk 偏多。

### Spanner

#### truetime-api-depth.md

- **High**: line 172-179 末尾 `## 完稿檢查（讀者導向）` 章節是 editorial residue、應移除或改寫成讀者實際可用的「自審 checklist」（用 `- 動詞句` 而非 `- [ ] 任務描述`）。
- Medium: 「寫稿時」出現 3 次（line 23、45、61）— 集中在 fact source 分層警告段、可改成「讀者引用時要 / 工程紀律是」等 reader-facing 語法。

#### consistency-models-comparison.md

- Low: 「寫稿時」line 85 出現一次。

#### schema-migration-interleaved-tables.md

- **High**: line 265 末尾 `## 完稿檢查（讀者導向）` editorial residue checklist。

#### migrate-from-cloud-sql-pg.md

- **High**: line 348 末尾 `## 完稿檢查（讀者導向）` editorial residue checklist。
- **High**: frontmatter 缺 `deep-article` tag（line 6）— 跟其他 30 篇不一致。建議補上。
- Medium: 「寫稿時」出現 2 次（line 45、70）。

### DB3 entry

#### db3-vendor-selection.md

- No issue。entry-point 結構（三軸前置判讀 + migration path 三型 + federated DB 視角 + 10 軸對比 + 7 反模式）非常完整、case anchor 覆蓋六個 unique 角度、跨 case 合成 frame 明示標記。負向句 22 / 259（多為 anti-recommendation、Scope warning、合理）。

## 跨篇 batch-wide pattern

### Pattern 1（High 影響）：editorial residue 殘留 3 篇 Spanner

`## 完稿檢查（讀者導向）` 章節在 3 篇 Spanner article 末尾、含 `- [ ]` task checklist 形式。標題雖寫「讀者導向」、內容實為作者 self-audit backlog（「Driver 段含 X」「9.C10 數字引用都明示 Y」這類元任務）。讀者讀到困惑、且這 3 篇是同一 vendor、推測是同一寫稿 session 的 carry-over。

**建議批次修正**：

- 移除 3 篇末尾的 `## 完稿檢查（讀者導向）` 整段
- 若想保留「讀者自審 checklist」概念、改寫成 reader-actionable 形式：「讀者套用本文前要確認的問題」+ 開放式 question（非 `- [ ]` task）

### Pattern 2（Medium 影響）：「寫稿時」meta-writer talk 跨 11 篇 26 次

`寫稿時要明示` / `寫稿時必須` / `寫稿要` 等語法把作者意圖暴露在文章內、違反原則六（讀者定位用內容體現）。Top 5：

| 篇                                               | 出現次數 |
| ------------------------------------------------ | -------- |
| cosmosdb/ru-cost-model-sizing.md                 | 4        |
| cosmosdb/mongodb-api-vs-sql-api.md               | 4        |
| spanner/truetime-api-depth.md                    | 3        |
| cockroachdb/aurora-dsql-spanner-decision-tree.md | 3        |
| cosmosdb/partition-key-design.md                 | 2        |

**建議批次修正**（sed 可批改）：

| 原語法             | reader-facing 改寫                    |
| ------------------ | ------------------------------------- |
| `寫稿時要明示 X`   | `引用時要明示 X` / `讀者引用要明示 X` |
| `寫稿時必須 X`     | `工程紀律是 X` / `判讀要 X`           |
| `寫稿時不可宣稱 X` | `不可宣稱 X`（直接刪「寫稿時」前綴）  |

### Pattern 3（Medium 影響）：frontmatter `deep-article` tag 缺漏

`spanner/migrate-from-cloud-sql-pg.md` 唯一缺 `deep-article` tag 的 article。其他 30 篇都有、是 frontmatter 一致性 break。

**建議**：補 `deep-article` 到 tags 陣列。

### Pattern 4（Low 影響）：`.md` extension 在內部 link

`cockroachdb/transaction-retry-pattern.md` line 303 / 331 兩處 `[...](.md)` 形式 — Hugo route 通常不含 `.md`、可能 broken link。其他 30 篇都用 `[...](/path/)` 或 `[...](./relative-name/)`。

**建議**：刪 `.md` extension、改 `mvcc-lock-model/`。

### Pattern 5（觀察、不必修）：負向句密度跨篇分布

跨篇負向句最高 5 篇都是合理場景：

- `aurora/read-replica-scaling.md` 31 / 371（fleet 治理 SSoT、含合規 no-go + 雙 SLO scope warning + FanDuel 警示）
- `cosmosdb/mongodb-api-vs-sql-api.md` 30 / 223（4 framing 含 6 個 failure pattern + anti-recommendation）
- `aurora/storage-architecture.md` 24 / 278（含 anti-pattern + boundary）
- `aurora/migrate-from-self-managed-pg-mysql.md` 22 / 426（migration playbook 多 no-go condition）
- `spanner/schema-migration-interleaved-tables.md` 22 / 272（schema migration 含多種反指標）

這些 negative sentence 都是 *載重負擔的 scope warning*（不可擴寫、不能套用、不該誤判）、不是逆向陳述主導段落。維持原狀。

## Polish pass 候選

不需要重寫、用 sed / 簡單 edit 批次修的字句層 issue（按優先序）：

1. **3 篇 Spanner 刪「完稿檢查」段**（High、5 分鐘工作量）
2. **batch sed `寫稿時` → reader-facing 改寫**（Medium、跨 11 篇 26 處、~ 20 分鐘）
3. **補 `migrate-from-cloud-sql-pg.md` frontmatter `deep-article` tag**（Medium、< 1 分鐘）
4. **修 `transaction-retry-pattern.md` 兩處 `.md` 結尾 link**（Medium、< 1 分鐘）

總計：4 個 batch-wide 修正、約 30 分鐘工作量、就能把整體分數推到 A / A+。

## 規範掃描自動化結果

### 負向句掃描 top 3 篇

1. `aurora/read-replica-scaling.md` — 31 / 371 行（8.4%、合理 — fleet 治理含多個合規 no-go + scope warning）
2. `cosmosdb/mongodb-api-vs-sql-api.md` — 30 / 223 行（13.5%、合理 — 4 framing + 6 failure pattern）
3. `aurora/storage-architecture.md` — 24 / 278 行（8.6%、合理）

判讀：負向句密度高的篇都是 *含大量 boundary condition / scope warning / no-go condition* 的篇、不是反例主導段落。維持原狀。

### Emoji / 裝飾性 unicode 掃描

`✅|❌|⚠️|🚨|🟡|🟢|⭐|📌|✓|✗` — **零殘留**（清乾淨）。

### H1 在 body 掃描

8 篇有 `^# ` line 命中、全部都是 *bash / shell / properties code block 內的 comment*（`#` 開頭的 shell comment）、不是 markdown body H1。**零真實違規**。

### 「新手 / 新人」字樣掃描

**零殘留**（原則六遵守度滿分）。

### 裸 URL 掃描

**零裸 URL**（所有 URL 都包在 markdown link 語法內）。

### TLD 顯示文字一致性掃描

**零違規**（無 TLD 顯示文字跟 href domain 不一致）。

### Frontmatter weight 唯一性

每 vendor 內 weight 唯一、無重複、無跳號。`migrate-from-cloud-sql-pg.md` 缺 `deep-article` tag 是唯一 frontmatter 一致性 break。

### Frontmatter date / description / tags 完整性

**全 31 篇都有 date / description / tags**。`date` 全部 2026-05-27。`description` 全部含具體 keyword 跟 case anchor。

---

## 主 flow 行動建議

進 Round 3 修正循環、優先處理 4 個 batch-wide pattern。所有 issue 都是 polish-pass 等級、無需重寫任何段落。31 篇整體寫作規範品質達到 production-ready 標準、修完 4 個 batch pattern 後可直接 ship。
