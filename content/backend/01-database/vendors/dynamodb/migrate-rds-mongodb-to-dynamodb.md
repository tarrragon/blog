---
title: "從 RDS / MongoDB 遷移到 DynamoDB：access-pattern-first 重建模、混合架構與 cost crossover"
date: 2026-06-02
description: "RDS / MongoDB → DynamoDB 不是搬 schema 而是換 paradigm；本文走 Type E paradigm shift 結構，展開為何字面遷移不成立、access pattern 重建模、哪些 workload 該遷哪些該留的混合架構、dual-write + shadow read 階段化，以及 Zomato cost crossover 的長期成本判讀"
weight: 39
tags: ["backend", "database", "dynamodb", "migration", "paradigm-shift", "migration-playbook"]
---

> 本文是 [DynamoDB](/backend/01-database/vendors/dynamodb/) overview 的 migration playbook。寫作參照 [Migration Playbook 寫作方法論](/posts/migration-playbook-methodology/)。

「我們要把 RDS 整個搬到 DynamoDB。」這句話本身就藏著最大的誤解 — DynamoDB 遷移不是把 table schema 1:1 搬過去。RDS 的 normalized schema、JOIN、ad-hoc query 在 DynamoDB 沒有對應物；MongoDB 的彈性 document、二級索引、aggregation pipeline 也不能直接映射。字面意義的「遷移」不成立 — 遷移的動作不是搬資料、而是 *從 access pattern 重新設計資料模型*。能不能遷、該遷多少，取決於 workload 的查詢形狀是否固定、一致性需求是否能放寬。本文走 paradigm shift 結構：先講為何字面遷移不成立、再講哪些該遷哪些該留、最後才是階段化執行。

## 6 維 diff audit：主導維度是 paradigm

遷移前先盤點 source 跟 target 的差異落在哪幾維、決定 playbook 結構：

| 維度               | RDS / MongoDB → DynamoDB                               | 程度   |
| ------------------ | ------------------------------------------------------ | ------ |
| Schema / API       | SQL / document query → KV `GetItem` / `Query`、無 JOIN | High   |
| Operational model  | self-managed / RDS-managed → fully managed serverless  | Medium |
| Paradigm           | relational / document model → access-pattern-first KV  | High   |
| Components 數量    | 單 DB → 單 DB（不拆分）                                | Low    |
| Application change | ORM / query layer 全改、access pattern 先行            | High   |
| Data topology      | partition key 設計、無跨 region transaction            | Medium |

主導維度是 **paradigm**（其次 schema / application change）。這定義了結構 — 不是 schema 翻譯（Type A）、不是 drop-in（Type B），而是 **Type E paradigm shift**：部分遷移、長期混合架構、不收斂到「全部搬完」。

> **No-go condition**：workload 需要 ad-hoc 分析查詢、跨實體 JOIN、頻繁 schema 變動下的彈性查詢、或複雜多表交易 → 不該遷 DynamoDB。這些是 relational / document 的主場、硬遷會把複雜度推給 application 層（自己做 JOIN、自己維護冗餘）。

## 為什麼字面遷移不成立：paradigm gap

RDS / MongoDB 是 *先有資料模型、再支援任意查詢*；DynamoDB 是 *先有查詢、才設計資料模型*。這個順序顛倒是遷移的核心難點。

**relational → DynamoDB 的斷層**：

- JOIN 消失：relational 用 JOIN 組合多表、DynamoDB 要嘛預先反正規化（把關聯資料寫在同一 item / 同一 partition）、要嘛 application 多次查詢自己組
- ad-hoc query 消失：RDS 可以對任意欄位下 `WHERE`、DynamoDB 只能用 PK/SK 或預建 GSI 查（對應 [gsi-lsi-design](/backend/01-database/vendors/dynamodb/gsi-lsi-design/)）
- 強一致交易縮窄：relational 任意多表交易 → DynamoDB 有限的 TransactWriteItems（對應 [transactions-conditional-writes](/backend/01-database/vendors/dynamodb/transactions-conditional-writes/)）

**document（MongoDB）→ DynamoDB 的斷層**：

- 看似接近（都是 NoSQL / document-ish）、實際 MongoDB 的二級索引彈性、aggregation pipeline、彈性 query 在 DynamoDB 都沒有對應
- MongoDB 可以「先存進去、之後再想怎麼查」；DynamoDB 不行、access pattern 沒想清楚就建表、後面要重做

所以遷移的第一步不是匯資料、是 **窮舉 access pattern**：列出 application 對這份資料的所有讀寫路徑、每條路徑對應 DynamoDB 的 PK/SK/GSI 設計。access pattern 列不完整、就還不能開始遷。

## 哪些 workload 該遷、哪些該留（混合架構）

Type E 的本質是 *不收斂* — 不是所有資料都該進 DynamoDB、混合架構會長期存在。判讀標準：

| Workload 特徵                               | 去向                         |
| ------------------------------------------- | ---------------------------- |
| access pattern 固定、key-based 查詢、高吞吐 | 遷 DynamoDB                  |
| 可接受 eventually consistent                | 遷 DynamoDB                  |
| 需要 ad-hoc 分析 / 報表 / JOIN              | 留 RDS / 或進 analytics 系統 |
| 需要強一致複雜交易                          | 留 RDS                       |
| schema 頻繁演進、查詢需求不穩               | 留 MongoDB / RDS             |

`9.C20 Zomato` 是這個判讀的 case anchor：Zomato 遷的是 *billing platform*（帳單事件、access pattern 固定、可接受 eventually consistent）、不是把整家公司的資料庫都搬。帳單系統從 TiDB 遷到 DynamoDB 後吞吐 2,000 → 8,000 RPM（4x）、延遲降 90%、成本降 50%；動機是 TiDB 必須為突發流量峰值預先 over-provision、DynamoDB on-demand「pay only for what we use」避免常態浪費。

> **Scope warning**：Zomato 的「成本降 50%」是 *當下流量* 下的對照、不是永久結論；「延遲降 90%」可能主要是 p50、p99/p999 改善幅度通常較小。這兩點 case 原文已標明、引用時不可升級成「DynamoDB 永遠更便宜更快」。crossover 判讀見下方容量段。

## Phase plan：access-pattern-first 階段化

paradigm shift 的階段化把不可逆動作放到最後、每階段有獨立驗證門檻：

#### Phase 1：access pattern 窮舉

列出 application 對目標資料的所有讀寫路徑、標每條的頻率、一致性需求、是否可放寬。這份清單是後續所有設計的輸入、不完整不進下一階段。

#### Phase 2：DynamoDB 資料建模

依 access pattern 設計 PK/SK、single-table 結構、需要的 GSI、capacity mode。對應 [single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/)、[partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)。

#### Phase 3：dual-write

application 同時寫舊（RDS / MongoDB）跟新（DynamoDB）。舊系統仍是 source of truth、DynamoDB 累積資料。dual-write 要處理寫入失敗一致性（其中一邊失敗如何補償）。

#### Phase 4：backfill 歷史資料

把舊系統既有資料按新模型轉換寫入 DynamoDB。backfill 跟 dual-write 並行時要處理覆蓋順序（backfill 不能覆蓋掉 dual-write 的新值）。

#### Phase 5：shadow read 驗證

讀路徑同時打舊跟新、比對結果、記錄差異但仍以舊系統回應用戶。shadow read 是 cutover 前的信心來源 — 差異率降到可接受才進 cutover。對應 [1.7 Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/) 的 evidence 方法。

#### Phase 6：漸進 cutover

讀流量逐步從舊切到新（按比例 / 按 user segment）、保留隨時切回的能力。cutover 完成後 DynamoDB 成為該 workload 的 source of truth；但其他未遷 workload 仍在 RDS / MongoDB — 混合架構成立。

## Evidence：每階段的前進依據

每個階段用資料證明可前進、不靠感覺：

| 階段        | Evidence                                                    |
| ----------- | ----------------------------------------------------------- |
| dual-write  | 雙寫成功率、寫入失敗補償紀錄、兩邊 row count 差異           |
| backfill    | 已 backfill 比例、轉換錯誤數、checksum 對照                 |
| shadow read | 新舊結果差異率、差異分類（可接受的 eventual vs 真錯誤）     |
| cutover     | 切流比例、新系統 latency p99、error rate、rollback 是否觸發 |

這些 evidence 對齊 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)（Source / Time range / Query link / Owner / Data quality）與 [6.8 release gate](/backend/06-reliability/release-gate/) 的 gate 決策。

## Cutover 與 rollback 決策

資料庫切流失敗代價高、決策權責要寫清楚：

- **cutover window**：選低流量時段、明確切流比例階梯（如 1% → 10% → 50% → 100%）
- **rollback condition**：新系統 error rate / latency 超過閾值、或 shadow read 差異率異常 → 切回舊系統
- **decision owner**：誰有權喊停、依據什麼 evidence、記錄在 [8.19 incident decision log](/backend/08-incident-response/incident-decision-log/)（Timestamp / Decision / Context / Evidence / Owner / Rollback condition）
- **資料凍結策略**：cutover 期間若需要凍結寫入、明確凍結範圍與時長

對應 [rollback window](/backend/knowledge-cards/rollback-window/)、[rollback condition](/backend/knowledge-cards/rollback-condition/)。

## Cleanup 與長期混合

Type E 的 cleanup 不一定是「退役舊系統」— 多數情況舊系統仍服務未遷 workload：

- 已遷 workload 的舊 schema / 舊 writer / dual-write code path 退役
- shadow read 比對 code 移除
- 但 RDS / MongoDB 本身保留（服務 analytics / 強一致 / 彈性查詢 workload）
- 明確標示哪條資料路徑的 source of truth 是 DynamoDB、哪條仍是 RDS / MongoDB、避免「到底哪個是真的」混亂

混合架構不是過渡失敗、是 paradigm shift 的穩態 — 每個 workload 待在最適合它的儲存層。

## 失敗模式

production 常見的 5 個踩雷：

#### Case 1：先匯資料才想 access pattern

把 RDS table 結構直接搬成 DynamoDB item、上線後發現查不出要的資料、要重建表。修法：access pattern 窮舉是 Phase 1、資料建模是 Phase 2；順序不能顛倒。

#### Case 2：把 JOIN 邏輯推給 application 卻沒評估成本

遷了關聯資料、application 每次查詢做 N 次 DynamoDB 呼叫自己組 JOIN、latency 跟成本爆炸。修法：關聯資料在建模階段反正規化（同 partition / 同 item）；無法反正規化的關聯查詢、該 workload 可能不適合遷。

#### Case 3：dual-write 一邊失敗沒補償

dual-write 時 DynamoDB 寫成功 RDS 失敗（或反之）、兩邊資料分歧、cutover 後發現新系統資料不完整。修法：dual-write 要有失敗補償（記錄失敗、重試、或標記該筆需人工對帳）；對應 [1.9 Reconciliation 與 Data Repair](/backend/01-database/reconciliation-data-repair/)。

#### Case 4：跳過 shadow read 直接 cutover

對自己的建模有信心、省掉 shadow read、cutover 後才發現 access pattern 漏了某個查詢路徑、生產出錯。修法：shadow read 是 cutover 前唯一能在真實流量下驗證新模型的階段、不能省。

#### Case 5：只看當下成本忽略 crossover

遷移時算出成本降 50% 就下決策、未來流量成長後 DynamoDB cost-per-request 累積超過自管 cluster、反而更貴。修法：算 12-24 個月在預期流量下的成本曲線、不是當下 snapshot（見容量段）。

**Anti-recommendation**：workload 查詢需求還在快速變化、或團隊對 access-pattern-first 建模沒經驗 → 先不要遷；用一個低風險、access pattern 已穩定的 workload 試點（如 Zomato 的 billing platform）、累積經驗再擴大。

## 容量與成本：crossover 判讀

DynamoDB 成本判讀的關鍵是 *未來流量曲線*、不是遷移當下的 snapshot：

- **遷移當下**：相對 over-provisioned 的自管 cluster、DynamoDB on-demand 常更便宜（Zomato -50%）
- **流量成長後**：DynamoDB cost-per-request 隨用量線性成長、自管 cluster 在高且可預測流量下有 crossover 點、可能反超便宜
- **判讀分層**：小/中流量或流量不可預測 → DynamoDB 划算；大且可預測流量 + 已有 DBA 團隊 → 算自管 crossover

這條 vendor-level 成本軸主寫於 [on-demand-vs-provisioned 軸 6](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/#軸-6dynamodb-vs-自管-cluster-cost-crossover)；本篇從遷移決策角度引用、不重複展開 6 軸。

> **Scope warning**：crossover 點隨 region pricing、workload shape、團隊成本結構變動、無通用閾值；Zomato 的具體百分比是單一 case 當下對照、不可外推。

接回 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)、[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)。

## 邊界與整合

### 跟其他遷移路徑的關係

- **DynamoDB → SQL / search / analytics split**（遷出方向）：當 DynamoDB workload 長出 ad-hoc 查詢需求、把分析部分拆到 OpenSearch / 數倉、是反向路徑、屬另一篇 playbook scope
- **MongoDB → Atlas**：若只是要 managed MongoDB 而非換 paradigm、走 [MongoDB → Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/)、不必遷 DynamoDB（保留 document paradigm）
- **跨平台等效**：RDS → Aurora（保留 relational）、MongoDB → Cosmos DB（保留 document）、都比遷 DynamoDB 的 paradigm 跨度小；先確認真的需要換 paradigm

### Sibling 與 cross-link

- [single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) — 遷移 Phase 2 資料建模的核心
- [partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) — 建模時 PK 均勻度判讀
- [transactions-conditional-writes](/backend/01-database/vendors/dynamodb/transactions-conditional-writes/) — 遷移後寫一致性如何在 DynamoDB 重建
- [on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) — cost crossover 軸 6 SSoT
- [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/) — 通用 dual-write / shadow read / cutover 框架
- 跟 [Zomato 9.C20](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) 互引：billing platform 遷移的可量化對照與 cost crossover 警示
