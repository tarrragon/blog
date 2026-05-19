---
title: "Vendor 深度技術文章的寫作方法論：從 overview 到 implementation"
date: 2026-05-18
description: "在 vendor overview 已齊全的前提下、如何規劃跟撰寫 vendor 之下的深度技術文章（pgBouncer 配置、Patroni HA、Vault dynamic credential 等）— 結構、選題、寫作流程跟跟 overview 的職責劃分"
tags: ["writing-methodology", "vendor-article", "technical-writing", "case-first"]
---

Vendor overview 文章回答「這個服務該不該選 / 跟同類差在哪 / 失效模式有什麼」、是 *選型層* 教材。Vendor 之下的深度技術文章回答「這個 vendor 的某個功能怎麼設、踩哪些坑、容量怎麼規劃、跟其他元件怎麼整合」— 是 *實作層* 教材。兩者的目標、結構、長度、寫作節奏完全不同。本文整理深度文章的方法論：選題判準、結構模板、跟 overview 的職責劃分、寫作流程。

寫這篇之前的背景：backend 模組已完成 [07-security-data-protection](/backend/07-security-data-protection/) 51 個 vendor overview + [08-incident-response](/backend/08-incident-response/) 9 個 + [09-performance-capacity](/backend/09-performance-capacity/) 15 個 vendor 加深、跨 4 個 S 批次 + 3 個 B 批次 + 5 個 C 批次的累積經驗。Vendor overview 層飽和後、自然的下一步是「PostgreSQL 那頁尾的 9 項預計實作話題、Vault 那頁尾的 8 項、Kubernetes 那頁尾的 N 項 ...」怎麼寫。

## 為什麼需要不同的方法論

Vendor overview 跟 deep article 是 *不同產品*、共用方法論會兩邊都做不好。

**Overview 的目標讀者**是「不熟這個 vendor、想評估」的人；deep article 的目標讀者是「已選了這個 vendor、要實作或除錯」的人。前者要 *broad coverage + 取捨清楚*、後者要 *narrow scope + 操作細節*。把兩者塞在同一篇會出現「定位段落太短不夠評估、實作段落太簡單不夠操作」的兩頭不到位。

**Overview 的結構**是 11 章節 case-driven framework（服務定位 → 取捨表 → 案例回寫 → 路由）；deep article 的結構是 *問題情境 → 概念 → 配置 → 演練 → 邊界 → 整合*、是 implementation-driven flow。

**Overview 的長度** 130-160 行 sweet spot（reviewer 一致共識）；deep article 通常 200-400 行才足以覆蓋一個議題（更短就是 overview 重複、更長就是該拆兩篇）。

## 選題判準（決定要不要寫一篇深度文章）

不是每個 vendor 都需要深度文章、不是每個議題都值得獨立成篇。判準三條：

### 判準一：vendor overview 頁尾「預計實作話題」backlog 中、被讀者問或被自己在生產踩過的議題

PostgreSQL 頁尾列了 pgBouncer / Patroni HA / Debezium CDC / 升級 Aurora / schema migration 工具對比 / index 決策樹 / vacuum tuning / partitioning / FDW — 共 9 項。9 項都重要、但寫作 ROI 不一樣。優先寫 *讀者最常問* 或 *自己踩最痛* 的、不是清單前幾項。pgBouncer 配置在中等規模公司是必踩；FDW 多數人一輩子用不到。

### 判準二：跨 vendor 議題、不適合塞單一 vendor overview 但有獨立教學價值

例：「production 從 Splunk 遷移到 Elastic Security 的 detection rule 翻譯方法論」— 跨 [Splunk](/backend/07-security-data-protection/vendors/splunk/) 跟 [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) overview、寫在任一頁都偏。深度文章可以獨立、cross-link 兩個 vendor overview。

### 判準三：vendor overview 的「進階主題」段落已經點到、但 7-15 行說不清楚

例：[HashiCorp Vault](/backend/07-security-data-protection/vendors/hashicorp-vault/) overview 中 dynamic credential engine 段提到「對應 [Failure: Credential Rotation Without Scope](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/)」、但 dynamic credential 怎麼從 application code call 起、lease renewal 怎麼處理、過期前 grace period 怎麼設 — 都不是 overview 該寫的。需要獨立深度文章。

**反向判準（不該寫深度文章的情境）**：

- vendor 文件已經寫得夠好、自己加一篇只是 paraphrase（例：AWS WAF managed rule 列表）
- 議題太小、塞進 vendor overview 的某段裡 200 字解決即可
- 沒有 production 經驗或 case 支撐、純 spec 復述（會變成低品質內容）

## Deep article 的結構（vs overview 11 章節）

Overview 11 章節是 *選型 framework*、deep article 是 *implementation flow*。建議 6 段結構：

| 段落                    | 內容                                                              | 比例 |
| ----------------------- | ----------------------------------------------------------------- | ---- |
| 1. 問題情境             | 「為什麼會踩到這個」— 真實場景觸發、不是 textbook intro           | 10%  |
| 2. 核心概念             | 該 vendor 特有的概念（不是通用 concept、是 *這個 vendor 怎麼解*） | 15%  |
| 3. 配置 step-by-step    | 真實可跑的 config + code + command（不是偽 code）                 | 30%  |
| 4. 故障演練 / 邊界 case | 「踩到哪些坑、什麼徵兆、怎麼修」— production 經驗最有價值的段     | 25%  |
| 5. 容量 / cost 規劃     | 在什麼規模下這個配置適用、超出後要換什麼                          | 10%  |
| 6. 整合 / 下一步        | 跟其他 vendor 怎麼接、什麼 case 後該 revisit                      | 10%  |

跟 overview 11 章節比、deep article *不該重複* 服務定位 / 核心取捨表 — 這些已經在 overview。如果讀者沒看 overview 就直接讀 deep article、開頭一段引用 overview link 即可、不要重寫。

## 跟 overview 的職責劃分（避免重複）

明確邊界：

| Overview 該寫                | Deep article 該寫                      |
| ---------------------------- | -------------------------------------- |
| 跟同類 vendor 取捨           | 該 vendor 內部的 sub-tool 取捨         |
| 整體 first-class concept     | 該 sub-tool 的 first-class concept     |
| 案例回寫（vendor-level）     | 案例對照（feature-level）              |
| 何時改走別家 vendor          | 何時換 sub-tool（同 vendor 內）        |
| 計費 trap（vendor-level）    | 配置 cost（feature-level）             |
| 跨 vendor 整合（high-level） | 跨 vendor 整合（implementation-level） |

例：Vault 的 dynamic credential engine

- **Overview** 寫：dynamic credential engine 是 Vault 跟雲廠 secret store 的核心差異、適合 DB / cloud / SSH 場景、cost trade-off 是 lease management overhead
- **Deep article** 寫：怎麼設 PostgreSQL dynamic credential（具體 backend config + role + max_ttl）、application 怎麼 call、lease renewal 邏輯、connection pool 跟 lease 生命週期不對齊的踩坑、grace period 設多久

兩者 cross-link、不互相吃對方場景。

## 寫作流程（vs S1-S4 workflow）

S1-S4 用的 case-first + agent team review 流程適合 vendor overview 批次。Deep article 流程不同：

### Step 1：選題 + 經驗驗證

從 vendor overview 頁尾 backlog 挑一個、確認自己 *在 production 踩過或處理過該議題*。沒踩過的議題寫不出有價值的故障演練 / 邊界 case 段。

### Step 2：草稿 outline + 真實 config 範例

先列 6 段結構、把 *真實能跑的 config / code* 放進 step-by-step 段、留 placeholder 給文字。不從文字寫起、從 config 寫起 — 確保 implementation 段有實質內容。

### Step 3：補敘事文字

回頭把每段補敘事 — 為什麼這樣配、跟 default 差異、邊界什麼時候會踩。這時要 *對著 config 寫*、不是憑印象寫。

### Step 4：故障演練段是核心

deep article 的 *差異化價值* 在故障演練段。Production 經驗、debug log、metric 截圖（不直接放、但描述徵兆）、recovery 步驟。沒這段就跟 vendor 官方 docs 沒差。

### Step 5：cross-link 回 overview + case

開頭 link 到 vendor overview、結尾 link 到 *被引用的 case*（如果 deep article 對應某個 case 的失效模式）。

### Step 6：單一 reviewer 即可

不需要 S1-S4 那種 3-reviewer 分維度（規範 / 案例 / 一致性）— deep article 的 *跨章一致性* 風險低（焦點窄）、案例引用也少（通常 1-2 個對照）。單一 reviewer 看「config 對不對 + 敘事流暢」就足夠。

### Step 7：取捨「廣度」vs「深度」

寫到 400 行還沒寫完時、決定 *拆兩篇* 或 *再壓縮*。一篇深度文章不該超過 500 行 — 超過就是該拆 sub-articles。

## 何時不該套這個方法論

- 純 vendor doc 翻譯整理：直接連 vendor docs、不寫 deep article
- News-driven 短文（某 CVE 揭露、某 vendor 收購）：寫在 [posts/](/posts/) 不寫在 vendor directory
- 純 case study：寫在 case 庫（[07/cases](/backend/07-security-data-protection/cases/) 或對應模組）、不是 deep article
- Cross-cutting 概念（observability vs SRE vs platform）：寫在 [report/](/report/) 或 [posts/](/posts/) — 不綁單一 vendor

## Demo backlog（第一輪推薦寫的深度文章）

基於 vendor overview 完成後的自然延續、第一輪推薦 5 篇 demo（**5/5 完成、2026-05-18**）：

1. **[pgBouncer 配置 + 連線池治理](/backend/01-database/vendors/postgresql/pgbouncer-config/)**（262 行、完成）— transaction pooling vs session、3-layer pool sizing、5 大失敗 case
2. **[Vault PostgreSQL dynamic credential](/backend/07-security-data-protection/vendors/hashicorp-vault/dynamic-credential/)**（222 行、完成）— lease lifecycle、5 大踩雷（renewal race / DB max_connections / sealed / token expire / CircleCI 對照）
3. **[Kubernetes graceful shutdown](/backend/05-deployment-platform/vendors/kubernetes/graceful-shutdown/)**（213 行、完成）— termination 5 步序列、5 case（502 / drain race / init container restart / StatefulSet 串行 / Job 不 graceful）
4. **[Splunk Risk-Based Alerting](/backend/07-security-data-protection/vendors/splunk/risk-based-alerting/)**（193 行、完成）— RBA 三層 model、ES SPL 配置、4 大 tuning playbook
5. **[Cloudflare Page Shield](/backend/07-security-data-protection/vendors/cloudflare-waf/page-shield-csp-sri/)**（214 行、完成）— CSP / SRI / monitoring 三層、attack × defense 對照、4 case

5 篇總計 1,104 行、單篇 193-262 行、全落在 sweet spot 200-300 行 range。寫作時間單篇 1-2 小時（含驗證 config）— 比原預估 2-4 小時短、vendor overview 已建立的選型 context 大幅降低 deep article 開場成本。

## 第一輪 demo 驗證（2026-05-18）

5 demo 完成後、檢視方法論預期跟實際結果：

### 6 段 framework 多數成立、但 *章節名稱跟切入點* 可變

6 段內容指引（問題情境 → 概念 → 配置 → 演練 → 容量 → 整合）在 5 篇都成立、但章節 1 entry 的 framing 因主題本質不同自然分化：

| 篇                       | 章節 1 entry framing                              |
| ------------------------ | ------------------------------------------------- |
| pgBouncer                | 標準「問題情境」                                  |
| Vault dynamic credential | 標準「問題情境」                                  |
| K8s graceful shutdown    | 痛點宣告「沒做對、500 期間每次 deploy 都吃 502」  |
| Splunk RBA               | 概念反向定義「alert fatigue 是 detection 天花板」 |
| Cloudflare Page Shield   | 對照表驅動「Attack pattern × Defense mechanism」  |

5 種 entry framing 都成立、章節 1 不必死守「問題情境」標題。內容仍對應「為什麼會踩到這個」、只是 framing 因主題本質不同。

### 跨檔 cadence 驗證：刻意 variant 解 cadence collapse

方法論寫作時、[backend/07 51 vendor batch](/backend/07-security-data-protection/vendors/) 揭露 *批量寫作 cadence 同質化* 系統性問題（51/51 都用「四件事任一缺失就是 X 邊界」cadence、跨章連讀預期化）。本批後 4 篇（Vault / K8s / Splunk / Cloudflare）寫作前主動規劃 4 種 framing variant、跨檔 cadence audit 結果：

| 維度                             | backend/07 51 vendor | deep article 後 4 篇 |
| -------------------------------- | -------------------- | -------------------- |
| Cadence 「任一缺失」族重複       | 51/51 (100%)         | 0/4 (0%)             |
| 章節 1 entry framing 種類        | 1 種                 | 4 種                 |
| 過渡詞密度（實際上 / 進一步 等） | 未量化               | 全 0 hits            |
| Lint / emoji / MD036 違規        | 0                    | 0                    |

證實 *寫作前主動規劃 variant* 在 sub-threshold N=4 仍有效。對應 case-first-module-workflow skill 的 cadence-sampling principle — 寫作前準備 N 種 framing 變體、不是寫完再 polish；批次 ≥ 5 篇時抽樣 checkpoint 設在進度 10-20%。

### Reviewer 單人足夠：deep article 跨章一致性風險低

方法論第六步「單一 reviewer 即可」驗證成立。5 篇都採此流程、未出現需要 multi-axis review 的盲點。原因：

- Deep article 焦點窄（單一 feature）、跨章 frame 重複風險自然低
- 跟 vendor overview 比、case 引用密度低（1-2 個對照）、case fidelity reviewer 不必要
- 跨 module link 少（多在同 vendor 內）、cross-link reviewer 不必要

5 篇 lint + cards check + 自審 + 跨檔 cadence audit 就達到 ship 品質、沒跑 3-reviewer team。

### 方法論小修（第一輪 demo 後）

1. **寫作時間預估從 2-4 小時下修到 1-2 小時**：vendor overview 已建立的 context 大幅減少 deep article 開場成本；overview 不完整時才需要 2-4 小時
2. **6 段 framework 是 *內容指引*、不是 *章節標題模板***：章節名稱可隨主題調整、不必死寫「問題情境 / 核心概念 / 配置 step-by-step」
3. **批次寫 deep article ≥ 4 篇時、pilot phase variant 應強制**：跟 case-first-module-workflow skill 的 cadence-sampling principle 對齊、寫作前準備 N 種 framing 變體；sub-threshold（< 5）也適用

## 第二輪 batch 驗證：PostgreSQL sub-tool 系列（2026-05-18 同日）

第一輪驗證完成後當日、立即跑第二輪 N=5 batch — 5 篇 PostgreSQL sub-tool deep article（Patroni HA / autovacuum tuning / declarative partitioning / logical replication + Debezium / PITR + WAL archiving）。第二輪設計刻意選 *cadence collapse 最高風險場景*：同 vendor、同 article type、同 audience、同 6-section framework — 比第一輪跨 vendor 共同 context 更多。

| 篇                             | Variant              | 章節 1 entry framing                                                                | 行數 |
| ------------------------------ | -------------------- | ----------------------------------------------------------------------------------- | ---- |
| Patroni HA                     | E lifecycle-driven   | 「Failover lifecycle 5 段不是一條曲線」                                             | 243  |
| autovacuum tuning              | B pain-driven        | 「你的 autovacuum 永遠追不上 bloat — 為什麼」                                       | 202  |
| declarative partitioning       | C concept-reversed   | 「Partition 不是『把大表切小』、是『讓 planner pruning + 縮小 maintenance scope』」 | 243  |
| logical replication + Debezium | D table-driven       | 「Replication slot × Failure × Recovery 對照」                                      | 225  |
| PITR + WAL archiving           | A standard 6-section | 「問題情境」                                                                        | 266  |

5 篇 1,179 行、單篇 200-266 行、全 sweet spot。

### 跨兩輪 batch 對照

| 維度                               | 第一輪 N=4（跨 vendor） | 第二輪 N=5（同 vendor sub-tool 系列） |
| ---------------------------------- | ----------------------- | ------------------------------------- |
| Variant 種類                       | 4（A / B / C / D）      | 5（A / B / C / D / E）                |
| Cadence collapse「任一缺失」族重複 | 0/4 (0%)                | 0/5 (0%)                              |
| 章節 1 entry framing 種類          | 4                       | 5                                     |
| 過渡詞密度                         | 全 0 hits               | 全 0 hits                             |
| 共同 context                       | 6-section framework     | 6-section + 同 vendor + 同 audience   |
| 寫作時間 / 篇                      | 1-2 hr                  | 1-2 hr                                |

關鍵驗證：

1. **N=5 full-threshold 仍 0% collapse**：第二輪 N=5 進入 cadence-sampling principle 的「真實閾值」範圍、5 種 variant 在這個 sample size 仍能完全錯開
2. **同 vendor sub-tool 系列是 cadence collapse 最高風險場景、variant 規劃仍能 cover**：第二輪 5 篇共享 PostgreSQL context、5 種 variant 都能對應主題本質、不是「為了不同而不同」
3. **5 variant 不耗盡**：原方法論 demo backlog 只列 5 篇、擔心 variant 是否足夠覆蓋；實測 5 種變體（lifecycle / pain / reverse / table / standard）對應的是 *主題自然進入方式*、不是強制配對、未來更多 deep article 仍能找到自然 variant
4. **第二輪小修**：cadence audit 抽樣的最佳位置從「進度 10-20%」修正到「進度 60-80%」— 進度 10-20% 只有 1 樣本訊號弱、進度 60-80% 有 4 樣本對照訊號強

## 跟 Case-First Workflow 的對照

[Case-First Agent Team Review Workflow](/posts/case-first-agent-team-review-workflow/) 是 *批次寫多個 vendor overview* 的流程。Deep article 不適合套：

- Case-first 適合 *broad coverage*、deep article 是 *narrow depth*
- Agent team review 適合 *cross-page consistency*、deep article 焦點窄不需要
- 批次寫 7-10 個 vendor 平行 background 適合 *結構相同*、deep article 每篇結構雖然 6 段 framework 一致但 *內容差異大*、平行寫品質低

Deep article 是 *個別深耕*、近似傳統 technical blog post 寫作流程、不是工廠化批次。

## 下一步

第一輪 + 第二輪 batch 共 10 篇 deep article 完成（pgBouncer / Vault dynamic credential / K8s graceful shutdown / Splunk RBA / Cloudflare Page Shield / Patroni HA / autovacuum tuning / partitioning / logical replication + Debezium / PITR + WAL archiving）、方法論已兩輪小修、cadence-sampling principle 在 N=4 + N=5 雙閾值驗證。第三輪規劃方向：

- **跨 vendor 議題**：例如「production 從 Splunk 遷移到 Elastic Security 的 detection rule 翻譯」「Postgres → Aurora 升級的 schema migration playbook」「Redis → DragonflyDB 評估遷移」— 這類議題對應方法論「選題判準二（跨 vendor）」、單 vendor overview 塞不下
- **演練 / 治理流程深度**：例如「Vault disaster recovery + auto-unseal failover 演練」「K8s rolling update 失敗的 rollback playbook」— 這類內容跟 case-first 模組的「治理流程」章節呼應、但 implementation 深度更高
- **N ≥ 10 大批量極限測試**：第三輪可選擇繼續 PostgreSQL series（pgvector RAG / connection pooling 深度 / Citus 分散式）或 K8s sub-tool 系列（admission controller / scheduling profile / network policy / RBAC patterns）— 累積到 N=10+ 觀察 variant 設計是否耗盡

Deep article 是 long-tail 投資、不是 sprint。pace 上跟 vendor overview 批次完全不同 — 後者是 *封閉的選型框架補完*、前者是 *open-ended 的實作經驗沉澱*。

## 相關連結

- [Case-First Agent Team Review Workflow](/posts/case-first-agent-team-review-workflow/) — vendor overview 批次寫作流程
- [Compositional Writing skill](/skills/compositional-writing/) — atomic 寫作原則
- [Markdown Writing Spec](/posts/markdown-writing-spec/) — 排版規範
- [07 Vendor 模組總覽](/backend/07-security-data-protection/vendors/) — 51 個 vendor overview 完整集
- [09 Vendor 模組](/backend/09-performance-capacity/vendors/) — vendor overview 加深 reference
