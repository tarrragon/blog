# Round 5-A：字句層 keyword bank + cadence + self-application

Scope：DB3 / DB4 模組 31 篇 deep article（6 vendor × 4-6 篇）+ DB3 entry `db3-vendor-selection.md`、共 31 檔（mongodb 6 / dynamodb 5 / cosmosdb 5 / aurora 5 / cockroachdb 5 / spanner 4 / db3 entry 1）。

Frame：Round 1-A 字句層 keyword bank grep + Round 2-A cadence frame + Round 3-A self-application sweep。前 4 輪沒明確跑 compositional-writing skill 的 5 keyword bank、本輪補上。

---

## 整體 keyword bank 殘留統計

| Bank                                                                     | 總 hit   | 必修   | 建議 / 可保留                            | 主要分布                                                                |
| ------------------------------------------------------------------------ | -------- | ------ | ---------------------------------------- | ----------------------------------------------------------------------- |
| **負向句**（`不[行可是要能該支對符夠必]\|無法\|沒[做有]\|而非\|而不是`） | 647 行   | ~10 處 | 主要為反例對照與 anti-pattern 表述、保留 | top 5 篇與 prompt hint 完全吻合                                         |
| **口語修辭**（`其實\|實務上\|真的\|碰巧\|立刻撞牆\|沒事`）               | 19 行    | 9      | 10                                       | 「真的」7 / 「實務上」5 / 「其實」4 / 「沒事」1 / 「碰巧」「立刻撞牆」0 |
| **地區用語**（`集群\|默認\|質量\|視頻\|函數\|文件夾\|接口`）             | **2 處** | 2      | 0                                        | 集群 1 / 默認 1（prompt 預期 4、實測較少）                              |
| **廢話前綴**（`值得注意的是\|需要說明的是\|實際上\|基本上\|事實上`）     | 3 處     | 3      | 0                                        | 「實際上」2 / 「基本上」1                                               |
| **裝飾符號**（`✅❌⚠️🚨🟡🟢⭐📌✓✗`）                                      | **0**    | 0      | 0                                        | 完整乾淨                                                                |

**負向句的主導性判讀**：top 5 篇平均每 50-80 行 1 處 hit、絕大多數是「不是 X、是 Y」contrastive、anti-pattern 列表（`不該`、`不能假設`）、scope warning（`不普適`、`不公開`）、合規語氣（`禁止跨境複製`）。沒有發現「整段被否定句主導、需要翻成正向陳述」的案例。Round 1-A 通過。

---

## 必修（High）

### 1. cosmosdb/mongodb-api-vs-sql-api.md:168

- before：`MongoDB 的 _id 默認 ObjectId、跟 Cosmos DB partition key 邏輯不同`
- after：`MongoDB 的 _id 預設 ObjectId、跟 Cosmos DB partition key 邏輯不同`
- 理由：地區用語（默認 → 預設）

### 2. mongodb/connection-management-and-cache-layer.md:142

- before：`修法是 proxy 集群 + health check + 客戶端 retry`
- after：`修法是 proxy 叢集 + health check + 客戶端 retry`
- 理由：地區用語（集群 → 叢集）

### 3. cosmosdb/multi-region-write-conflict.md:200

- before：`團隊以為「multi-region + Strong = 全球 linearizable」、實際上是設計 incompatibility`
- after：`團隊以為「multi-region + Strong = 全球 linearizable」、底層是設計 incompatibility`（或直接刪「實際上」）
- 理由：廢話前綴

### 4. spanner/schema-migration-interleaved-tables.md:148

- before：`這個流程基本上是 mini-migration、要走完整 migration playbook 的 phase plan`
- after：`這個流程是 mini-migration、要走完整 migration playbook 的 phase plan`
- 理由：廢話前綴（基本上）

### 5. cosmosdb/mongodb-api-vs-sql-api.md:108

- before：`MongoDB API → SQL API 的「升級」實際上是 export → recreate account → import + 重寫 application 的全量遷移`
- after：`MongoDB API → SQL API 的「升級」是 export → recreate account → import + 重寫 application 的全量遷移`
- 理由：廢話前綴（實際上）

### 6. cosmosdb/consistency-levels-engineering.md:165

- before：`互動式產品其實 Session 就夠、用 Strong 浪費 2x RU`
- after：`互動式產品 Session 就夠、用 Strong 浪費 2x RU`
- 理由：口語修辭（其實）— 判斷工具型段落、刪「其實」精度更高

### 7. cockroachdb/aurora-dsql-spanner-decision-tree.md:24

- before：`跨雲是真的硬需求還是被 fear 推的？`
- after：`跨雲是硬需求還是被 fear 推的？`
- 理由：口語修辭（真的）— 決策樹判讀問題、口語化稀釋

### 8. cockroachdb/aurora-dsql-spanner-decision-tree.md:171 / 295

- before：`90% 公司其實 single-cloud`（兩處同句）
- after：`多數公司 single-cloud`（或保留「90% 公司」、刪「其實」）
- 理由：口語修辭（其實）+ 兩篇同句重複（self-application：跨章重複用詞檢查）

### 9. cosmosdb/mongodb-api-vs-sql-api.md:86

- before：`MongoDB API 把 MongoDB 操作翻譯成 Cosmos DB internal、不是真的跑 MongoDB engine`
- after：`MongoDB API 把 MongoDB 操作翻譯成 Cosmos DB internal、實際上跑 Cosmos DB 自身 engine、不執行 MongoDB engine`
- 理由：口語修辭（真的）— 機制段落、應改技術描述

### 10. cockroachdb/hlc-raft-consensus.md:21

- before：`HLC clock skew 真的大會發生什麼？節點隨機 panic 嗎？`
- after：`HLC clock skew 超出容忍區間時會發生什麼？節點隨機 panic 嗎？`
- 理由：口語修辭（真的）— failure mode 機制段、應給可反推屬性

---

## 建議（Medium）

### 「真的」case-by-case 保留組（共 4 處）

以下「真的」屬 *narrative hook* 或 *讀者徵兆描述*、屬於進入論述的口語橋接、保留不修：

- dynamodb/gsi-lsi-design.md:185 `確認 DAX 真的減少 base 路徑壓力` — observability action 段、口語推進無傷
- cosmosdb/partition-key-design.md:206 `重新評估「真的需要 synthetic key 嗎」` — 讀者問題引用、口語化合理
- aurora/global-database-multi-region.md:144 `真的需要 active-active write 才考慮 Aurora DSQL` — routing 判讀、可保留
- spanner/schema-migration-interleaved-tables.md:15 `「Spanner ALTER 真的不卡寫入嗎」` — 引用讀者徵兆原句

### 「實務上」5 處（mongodb / aurora / cockroachdb / spanner）

`實務上` 在這 5 處都附接技術 evidence（具體數量 / 版本 / 規範）、屬於「實務經驗→規則化」橋接、保留。但 aurora/read-replica-scaling.md:48「實務上做不到」+ :183「實務上更常在 5-10 replica」+ cockroachdb/hlc-raft-consensus.md:147「實務上的影響」+ cockroachdb/locality-aware-schema.md:71「實務上 GLOBAL 只放」— 若 round 5-B 再 polish、可改成「實際 production 部署」「production 經驗」這類更精確的指稱。

### 「沒事」1 處

cosmosdb/multi-region-write-conflict.md:188 `團隊以為 proc 跑了就沒事` — 口語修辭典型 hit（colloquial-rhetoric.md 表格列「沒事」= 缺失條件描述）。建議改：「團隊以為 proc 跑了就無 side effect」或「團隊以為 proc 跑了就完成 conflict resolution」。

---

## Cadence 同骨化發現

### Pattern 1（最明顯）：DynamoDB vendor 內 5 篇用同一句型起 failure mode

5/5 DynamoDB deep article 在 ## 失敗模式 段下首行用：「**N 個 production 常見踩雷：**」（N=5 或 6）。具體：

- global-tables-conflict.md:158 / partition-key-antipatterns.md:134 / gsi-lsi-design.md:131 / on-demand-vs-provisioned.md:202 / single-table-design-pattern.md:143

讀者依序讀完 5 篇 DynamoDB 後、failure mode 開頭句失去新意。其他 5 個 vendor 沒有複製此 cadence（mongodb / cosmosdb / aurora / cockroachdb / spanner 用各自的開頭句）。建議至少 2 篇改寫（如「實際部署常見的 5 種失敗」、「production 觀察到的 5 個典型 anti-pattern」）。

### Pattern 2：問題情境 → 核心機制 → 失敗模式 三段骨架

21/31 文章用 `## 問題情境` 開頭、24/31 用 `## 核心機制`、25/31 用 `## 失敗模式`。屬於模組級教學模板、跨 vendor 提供統一閱讀體驗 — **這是預期的、屬 batch 內部一致性、不算同骨化**。但若 reader 在一週內連讀 30 篇、感受會偏單調。判讀：保留模板、模板內句型可在後續 polish round 局部變化。

### Pattern 3：scope warning 前綴

多篇用 `**Scope warning（...）**：...` 起 case 引用警示段（aurora/read-replica-scaling.md:211 / cosmosdb/mongodb-api-vs-sql-api.md / db3-vendor-selection.md:92, 103, 105 / cockroachdb/aurora-dsql-spanner-decision-tree.md:51 / cockroachdb/transaction-retry-pattern.md:11 / 34 等）— 屬於 case-citation discipline 的明示標記、ROI 高、保留。

---

## Self-application sweep 發現

### 同義變體未漏抓 — 同義詞使用受控

掃描 AGENTS.md §1 原則二「正向陳述優先」、`compositional-writing` 卡 colloquial / regional / cadence 規範定義的同義變體：

- `應該避免` 0 處（所有 hit 是 `不該` 而非 `應該避免`）
- `不該` 16 處 — 多為 routing / anti-pattern signal、屬「議題本身就是反指標」場景、保留語氣（AGENTS.md 規則：物理 / 法律事實例外保留）
- `本質上` / `實質上` 3 處 — 均為機制描述（「本質上是 oplog tail 包裝」「本質上就是跨 region storage replication」）、屬於工程精確語、保留
- `寫作時` / `撰寫時` 0 — 無此 meta 同義變體
- `禁止` 17 處 — 集中在合規語境（「合規禁止跨境複製」）、規範語氣、保留

### Self-application 發現的一個 cadence 同骨化漏抓

cockroachdb/aurora-dsql-spanner-decision-tree.md 內 line 171 跟 line 295 兩處用幾乎完全相同的句構「90% 公司其實 single-cloud、跨雲 ... 卻沒實際 multi-cloud 部署」 — 同一篇文章內部 self-duplication。建議第二處改寫成承接前句的指代（「上述 90% single-cloud 公司」）或變化句構（「fear-driven adoption 的 90% 公司、實際是 single-cloud 部署」）。

---

## 修法工時估算

| 類別                                                                        | 處數  | 預估時間                         |
| --------------------------------------------------------------------------- | ----- | -------------------------------- |
| **必修（High）** 地區用語 2 + 廢話前綴 3 + 口語修辭 5                       | 10 處 | 25-35 分鐘（單行替換、機械操作） |
| **建議（Medium）** 「實務上」精化 4 + 「沒事」改寫 1 + cockroachdb 重複句 1 | 6 處  | 20-30 分鐘                       |
| **Cadence DynamoDB pattern 1 改寫**（2-3 篇變化開頭句）                     | 3 處  | 15-20 分鐘                       |
| **Round 5-B verify**（修完跑 5 grep 確認 0 hit）                            | —     | 5-10 分鐘                        |
| **總計**                                                                    | 19 處 | **65-95 分鐘**（約 1-1.5 小時）  |

---

## Round 5-A 結論

- **裝飾符號 / 負向句主導 / self-application 同義變體**：3 個維度均通過、無系統性違規。
- **地區用語 / 廢話前綴**：合計 5 處硬性違規、必修、機械操作。
- **口語修辭**：19 處中 9 處應改（機制段 / 決策段 / failure mode hook），10 處屬 narrative hook / reader symptom quote、保留合理。
- **Cadence**：vendor 內模板化嚴格（DynamoDB「N 個 production 常見踩雷」一致 5 篇）、跨 vendor 三段骨架（問題情境 / 核心機制 / 失敗模式）達 70%+、屬於模組級閱讀體驗統一、可在 polish round 局部變化。
- **Self-application**：cockroachdb decision-tree 同篇 line 171 / 295 重複句構、Round 5-B 修。

整體品質維持 A+ — 字句層問題集中在「機械替換可清乾淨」的 maintenance scope、無架構性 rewriting 需求。

**下一步**：本報告交主 flow、由主決定是否進 Round 5-B polish；如進、優先處理 10 處必修 + Pattern 1 DynamoDB cadence 變化 2-3 篇 + cockroachdb decision-tree 同篇重複句。
