---
title: "1.6 資料庫轉換實作：雙寫、回填、切流與回滾"
date: 2026-05-13
description: "同 DB 內 schema 演進與資料變更的可分段驗證流程、跟 1.12 cross-DB migration 分工"
weight: 6
tags: ["backend", "database", "migration"]
---

資料庫轉換實作的核心責任是讓 schema、資料與流量切換都可分段驗證、並在任一階段可安全回退。這一頁不討論要不要轉換、專注回答「決定要換之後怎麼做」。

本章跟 [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) 分工：

- **1.6 同 DB 內**：schema 演進、資料變更、新舊欄位共存、雙寫驗證、切流。例：加欄位、改欄位、拆表、合表、加 partition。
- **1.12 跨 DB 引擎**：換 vendor（PostgreSQL → Aurora、MongoDB → Cosmos DB、TiDB → DynamoDB）。例：[9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)、[9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)。

兩者用同樣的工程方法論（dual-write、shadow、cutover、rollback）、但 *stakes* 跟 *跨越的邊界* 不同。本章先處理 1.6 的同 DB schema 轉換、1.12 處理更大規模的 cross-engine。若來源是託管平台（Shopify / Firebase / WordPress）的匯出而非自建資料庫、整場遷出的資產線盤點與並行期設計見 [10.3 託管形態遷出](/backend/10-system-evolution/managed-platform-exit/)；資料落地自建後的 schema 演進回到本章、跨引擎搬遷走 1.12。

## 實作流程

| 階段        | 核心動作                                                                     | 交付成果                         |
| ----------- | ---------------------------------------------------------------------------- | -------------------------------- |
| 1. 邊界定義 | 定義 source of truth、切換範圍、不可中斷路徑                                 | migration scope 與 rollback 邊界 |
| 2. Expand   | 新欄位 / 新表先上線、應用可同時讀舊寫新或雙寫                                | 新舊版本相容窗口                 |
| 3. Backfill | 批次回填歷史資料、保留節流與 checkpoint                                      | 可追蹤的回填進度與失敗重試       |
| 4. 驗證     | [shadow read](/backend/knowledge-cards/shadow-read/)、checksum、業務指標對帳 | 一致性證據包                     |
| 5. Cutover  | 逐步切讀、再切寫、保留快速回切策略                                           | 切流完成且可回退                 |
| 6. Contract | 移除舊欄位與舊路徑、收斂技術債                                               | 單一資料語意落地                 |

## Expand-Contract 模式

[Expand / Contract](/backend/knowledge-cards/expand-contract/)（也叫 parallel change）是同 DB schema 演進的核心模式。

**為什麼需要這個模式**：

- 應用 deploy 跟 DB migration 不能 *原子* 完成
- 在 deploy window 內、有些 instance 跑舊 code、有些跑新 code
- DB 必須同時容納舊 code 跟新 code 的 schema

**Expand 階段**（加新欄位、不刪舊）：

- 加 `new_column`、允許 nullable
- 應用層 dual-write：同時寫 `old_column` 跟 `new_column`
- 應用層 read 仍走 `old_column`

**Backfill 階段**（資料同步）：

- 把歷史 row 的 `new_column` 補上值（從 `old_column` 算出來）
- 分批跑、用 checkpoint 追進度、避開 peak
- 監控：rate、error、progress、unaffected rows count

**Migrate Reads 階段**（切讀）：

- 應用層 read 改走 `new_column`
- 仍 dual-write、可以快速 fallback 回 `old_column`
- 持續 shadow read 驗證一致性

**Contract 階段**（刪舊）：

- 確認所有 application instance 都跑新 code 後
- 刪 `old_column`、停止 dual-write
- 移除應用層的 fallback 邏輯

每個階段都是 *可獨立 rollback* 的、不像 big-bang 一次切完。

## 同 DB 內常見 migration 類型

### Type A：加欄位（最簡單）

- 直接 `ALTER TABLE ADD COLUMN`（nullable 或 default）
- 應用層後續加寫入、讀取
- 風險：低
- 注意：大表 ADD COLUMN with DEFAULT 在 PostgreSQL 11+ 是 instant、之前要 rewrite

### Type B：刪欄位

- 先讓所有 application 不再讀寫該欄位
- 部署完成、確認後再 DROP COLUMN
- 風險：中
- 注意：DROP COLUMN 是 instant、但無法 rollback、必須 backup

### Type C：改欄位型別

- 用 expand-contract：加新欄位、dual-write、backfill、切讀、刪舊
- 風險：高（特別是大表）
- 注意：直接 `ALTER COLUMN TYPE` 可能 rewrite 整表、lock 時間長

### Type D：改欄位名 / 表名

- 同型別改名：用 expand-contract、加新名 + dual-write、切讀、刪舊
- DB 端 native rename 是 instant 但 application 需要同步 update — 不適合大規模 deploy

### Type E：拆表 / 合表

- 拆：先 dual-write 到新舊表、backfill、切讀、刪舊
- 合：先 dual-write 到新表、backfill、切讀、刪舊
- 風險：高 — 影響面廣

### Type F：加 index

- PostgreSQL：`CREATE INDEX CONCURRENTLY`（不 lock 表、可能 slow）
- MySQL：`gh-ost` / `pt-online-schema-change`（ghost table）
- 風險：低-中（看 index 大小）

### Type G：加 NOT NULL constraint

- 先確保 application 所有 instance 都不寫 null
- backfill null 為 default
- 加 NOT NULL constraint
- 風險：中

### Type H：加 partition

- 先把現有表變成 partition 0
- 加新 partition 接新資料
- 漸進把舊資料 move 到對應 partition
- 風險：高（schema 大變）

### Type I：加約束（CHECK / FK / NOT NULL 收緊）

對有存量資料的表加約束、風險形態跟加欄位不同：新約束要對「過去所有已寫入的資料」負責、不只對未來寫入負責。NOT NULL 是本類型的單欄特例（流程見 Type G）、CHECK 與 FK 走以下同一套順序。哪些規則該下沉成約束、哪些留在文件、分工標準見 [1.15 資料契約文件](/backend/01-database/data-contract-document/)；FK 強約束 vs 應用層保護的取捨回到 [1.2 schema design](/backend/01-database/schema-design/) 的外鍵段。

**約束前移原則**（為什麼值得做這種 migration）：

- 沒有約束時、非法值照樣寫入、問題被推給讀取端
- 讀取端對非法值做 fallback（當 0、當預設值、跳過該 row）看似穩健、實際是靜默翻轉業務語意——負數金額被當 0 加總、懸空引用被跳過、報表少算了沒有訊號
- CHECK / FK 把失敗前移到寫入當下：寫入方立刻收到顯性錯誤、當下有完整的呼叫脈絡可修
- 對偶關係：寫入時顯性失敗（吵、但可修）vs 讀取時靜默 fallback（安靜、但語意漂移）。約束層要的是前者

**宣告 vs 執法落差**：

schema 宣告了約束、不等於引擎正在執法。三種常見落差：

- 連線層開關：SQLite 的 FK 檢查是 per-connection 的 `PRAGMA foreign_keys`、預設 OFF——DDL 寫了 `REFERENCES` 但沒開 pragma、FK 形同註解
- 約束狀態：PostgreSQL `NOT VALID` 狀態的約束只檢查新寫入、存量不保證合規
- Storage engine：MySQL MyISAM 忽略 FK 定義、只有 InnoDB 執法

判讀依據：懸空參照（子表引用不存在的父 row）一旦出現、即證明該 row 寫入當下 FK 執法未生效——可能是執法開啟前的遺留、NOT VALID 半執法期、或 session 級旁路（bulk load 關閉檢查）。執法中的 FK 不會讓懸空參照寫得進去。

**存量處理順序 SOP**（先盤點、再修復、最後開執法）：

1. **盤點違規存量**：用 validation query 找出所有違反新約束的 row（懸空參照、CHECK 不符、該收緊的 NULL）
2. **修復或顯性處置**：逐類決定處置——修正資料、刪除、或顯性標記為已知例外。禁止在 migration 內靜默改寫（`UPDATE ... SET amount = 0 WHERE amount < 0` 埋進 migration script、語意翻轉沒有人 review 過）
3. **開啟執法**：存量乾淨後才啟用約束

PostgreSQL 把這個 SOP 做成引擎原生的兩段式、可當 vendor-agnostic 的順序錨點：

```sql
ALTER TABLE orders ADD CONSTRAINT fk_orders_user
  FOREIGN KEY (user_id) REFERENCES users(id) NOT VALID;
-- 此刻起只檢查新寫入、存量不動、不長時間持鎖（仍短暫取鎖）

-- 依盤點結果修復存量（顯性處置、非靜默 UPDATE）

ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_user;
-- 全表掃描驗證存量、通過後約束完全生效
```

沒有 `NOT VALID` 的引擎照同一順序操作：先跑 validation query 盤點、修完存量、再上約束（SQLite 走表重建、MySQL `ADD CONSTRAINT` 會直接全表驗證、要挑離峰）。

- 風險：中-高（違規存量數量未知前、無法估 migration 時長與修復工作量）
- 注意：違規存量修不完時、migration 應該失敗停下、不推進版本標記——「宣告了但沒 VALIDATE」的半套約束比沒約束更誤導
- 注意：upsert 類寫入（`ON CONFLICT` / `REPLACE`）只解唯一鍵／主鍵類衝突、不消解 CHECK 違反——衝突解消路徑不會吸收非法值、CHECK 違反仍以錯誤失敗

## Online Schema Change 工具

大表 ALTER TABLE 直接跑會 lock。生產級 migration 用 online schema change 工具：

**PostgreSQL**：

- `CREATE INDEX CONCURRENTLY`（內建）
- `pg_repack`（vacuum + reindex without lock）
- `pgroll`（zero-downtime migration）
- Atlas（schema-as-code）

**MySQL**：

- `gh-ost`（GitHub 開源、無觸發器、推薦）
- `pt-online-schema-change`（Percona、用觸發器）
- Vitess online DDL（managed via Vitess）

**機制概要**：

- 建 ghost table（新 schema）
- copy 資料到 ghost table（漸進、avoid peak）
- 用 trigger 或 binlog 同步 ongoing changes
- 切換：原 table → ghost table（atomic rename）

對應 [MySQL vendor page](/backend/01-database/vendors/mysql/) 跟 [PostgreSQL vendor page](/backend/01-database/vendors/postgresql/) 的相關段落。

## Validation Query 設計

migration 過程中必須有 *validation query* 確認資料一致性。

**Checksum 對比**：

- 跑 `MD5(new_column) = MD5(derived_from_old)`
- 抽樣 10% 跑、不打全表
- 不一致 → 修轉換函式、不直接修資料

**Row count 對比**：

- 新欄位 NULL count 跟預期 backfill 進度比對
- 過慢 → 增加 backfill worker
- 不一致 → 找出 backfill 漏跑的 batch

**業務指標對比**：

- 跟業務 metric 對齊（訂單金額總和、用戶數）
- 比 row-level checksum 更貼近 business correctness

詳見 [Validation Query 卡片](/backend/knowledge-cards/validation-query/) 跟 [1.7 Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)。

## Backfill 設計

backfill 是 migration 中最 *容易出錯* 的環節 — 大量寫、影響 production。

**設計要點**：

1. **節流（throttle）**：每秒寫入限制、跟 production peak 錯開
2. **Checkpoint**：紀錄進度、可 resume
3. **錯誤分類**：可 retry 的錯誤 vs 必須人工處理
4. **dry-run mode**：先看會修改多少、不實際寫
5. **monitoring**：rate、error、progress、replica lag

**backfill 反模式**：

- 一個大 transaction 跑全表 → lock 太久、可能 OOM
- 沒 checkpoint → 中途失敗從頭開始
- 沒 throttle → 影響 production read

對應 [Backfill 卡片](/backend/knowledge-cards/backfill/)。

## 各階段監控訊號

每階段都要監控、不只是「最後驗證」：

| 階段     | 主要訊號                                                    |
| -------- | ----------------------------------------------------------- |
| Expand   | DDL 執行時間、replication lag                               |
| Backfill | rate、error rate、checkpoint progress、production load 影響 |
| 驗證     | shadow read 不一致率、checksum 結果、業務 metric 差異       |
| Cutover  | error rate、p99 latency、rollback trigger 是否就緒          |
| Contract | DDL 執行時間、無 application 還在用舊 column 的證據         |

## 判讀訊號

| 訊號                            | 判讀重點                                            | 對應動作                                                  |
| ------------------------------- | --------------------------------------------------- | --------------------------------------------------------- |
| 回填速度不穩、延遲飆高          | 可能與線上流量競爭 IOPS                             | 降低批次大小、加節流、避開 peak                           |
| 雙寫成功率高但 shadow read 漂移 | 業務語意映射不一致                                  | 先修轉換函式、再重跑對帳                                  |
| 切流後 error rate 升高          | 新庫讀寫路徑與索引未對齊                            | 回切舊讀路徑、補索引後再灰度                              |
| rollback 時間超出 RTO           | 回退流程過度人工                                    | 把回退腳本化並演練                                        |
| 大表 ALTER TABLE 卡住           | online 工具沒用對 / lock                            | 用 gh-ost / pgroll、或分批執行                            |
| Backfill 後 NULL count 不歸零   | 有漏跑的 batch、或新寫入沒走 dual-write             | 補檢查 dual-write 邏輯、re-run backfill                   |
| 加了 FK 之後仍出現懸空參照      | 約束宣告了但執法未開（pragma / NOT VALID / engine） | 檢查連線層開關與約束狀態、依 Type I SOP 修存量後 VALIDATE |

## 常見誤區

把資料庫轉換當成單次 DDL 任務、會讓風險集中在 cutover 當下。穩定做法是把每一階段都做成可驗證、可回退的獨立里程碑。

把 dual-write 當成最終保障也常出錯。雙寫只能保證「兩邊都有寫」、不保證「語意一致」、仍要配 shadow read 與業務對帳。

把 online schema change 工具當「萬能」也是錯。gh-ost / pgroll 仍有 *限制*（例如 trigger 限制、IO 影響）、要按工具規格操作。

## 案例回寫

- 選型層案例： [0.C4 營運後技術轉換](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/)
- 可靠性治理： [6.11 Migration Safety](/backend/06-reliability/migration-safety/)
- 事故反饋： [GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/)
- 大規模跨 DB 遷移： [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)（[Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)、[Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)、[Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) 等 case）

這組案例主要支撐的是「分段切換與可回退驗證」判讀、不直接支撐快取 TTL 或 broker delivery 參數；若問題核心在快取新鮮度或投遞語意、應轉到 2.x 或 3.x。

## 跨模組路由

1. 與 1.2 的交接：欄位演進與命名語意回到 [schema design](/backend/01-database/schema-design/)。
2. 與 1.3 的交接：交易邊界與副作用切分回到 [transaction boundary](/backend/01-database/transaction-boundary/)。
3. 與 1.7 的交接：production rollout 證據實作 — [Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)。
4. 與 1.12 的交接：跨 DB 引擎遷移 — [大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)。
5. 與 4.20 的交接：validation query 與一致性證據進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
6. 與 6.11 / 6.8 的交接：放行與停損條件進入 [Migration Safety](/backend/06-reliability/migration-safety/) 與 [Release Gate](/backend/06-reliability/release-gate/)。
7. 與 8.19 的交接：pause、rollback、[fail-forward](/backend/knowledge-cards/fail-forward/) 決策記錄到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

若你還在判斷是否該轉換、先回 [0.C4](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/) 看決策訊號。若你要把這套流程寫成 production rollout evidence、接著讀 [1.7 Schema Migration Rollout 證據實作示範](/backend/01-database/schema-migration-rollout-evidence/)。若你在設計放行與演練、接著看 [6.11](/backend/06-reliability/migration-safety/) 與 [6.8](/backend/06-reliability/release-gate/)。若你在事故回溯、接著看 [8.23 Post-incident Review](/backend/08-incident-response/post-incident-review/)。若你要做 *跨 DB 引擎遷移*、看 [1.12](/backend/01-database/large-scale-db-migration/)。
