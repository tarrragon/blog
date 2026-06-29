---
title: "從 Firestore 遷往自建 relational：撞牆驅動的 Type E 重建模、存取模型反轉與並行期"
date: 2026-06-16
description: "Firestore → 自建後端 + relational 不是匯資料而是反轉存取模型：client 直連變 API 中介、Security Rules 授權變後端授權、document 反正規化變正規 schema、realtime listener 與 offline 同步要重建；本文走 Type E paradigm shift 結構、展開為何字面遷移不成立、哪些該遷哪些先留、dual-write + shadow read 階段化與遷出代價判讀"
weight: 11
tags: ["backend", "database", "firestore", "migration", "paradigm-shift", "migration-playbook", "baas"]
---

> 本文是 [Firestore](/backend/01-database/vendors/firestore/) overview 的 migration playbook。寫作參照 [Migration Playbook 寫作方法論](/posts/migration-playbook-methodology/)。BaaS 託管平台整場遷出的資產線盤點與並行期總覽見 [10.3 託管形態遷出](/backend/10-system-evolution/managed-platform-exit/)；本文聚焦資料層的跨 paradigm 重建模。

「我們把 Firestore 整包匯出，匯進 PostgreSQL 就好。」這句話低估了遷移的真正內容 — Firestore 遷往自建 relational 的難點是**反轉整個存取模型**，搬資料只是其中最容易的一條線。Firestore 是 client 用 SDK 直連資料庫、授權寫在 Security Rules；自建 relational 是 client 打自己的後端 API、授權在後端中介層。資料可以匯出，但反正規化的 document 形狀、沿查詢限制長出來的資料模型、realtime listener 與 offline 同步能力，都沒有 1:1 的對應物。字面意義的「匯出再匯入」只搬走了最容易的那部分。本文走 paradigm shift 結構：先講為何字面遷移不成立、再講哪些該遷哪些先留、最後才是階段化執行。

## 遷移的 driver：三面牆，不是「relational 比較好」

Firestore 遷往自建很少因為「relational 比較好」這種空泛動機，而是撞到 [0.21](/backend/00-service-selection/delivery-mode-selection/) BaaS 段描述的三面具體的牆。先確認 driver 真的成立、再啟動遷移：

| Driver          | 撞牆訊號                                                   | 遷移要解的問題                                  |
| --------------- | ---------------------------------------------------------- | ----------------------------------------------- |
| 報表 / 分析查詢 | 跨 collection 報表查不出來、已經在維護資料複製管線         | 把資料放回支援 JOIN / aggregation 的 relational |
| 成本曲線轉折    | read / write 計費隨流量線性成長、超過自建 + cache 的成本   | 用自管資料庫 + 應用層快取壓低單位成本           |
| 授權控制面失控  | Security Rules 長到難以測試 / review、授權邏輯沒有版本治理 | 把授權拉回後端 API 中介層、可測試可審查         |

> **No-go condition**：產品仍以多裝置 realtime 同步與 offline-first 為核心賣點、且查詢需求簡單、成本仍在舒適區 → 先不要遷。這些正是 Firestore 的主場，硬遷會把 realtime / offline 這層平台白送的能力變成自己要重建的工程。遷移前先問「撞的是哪面牆」，三面牆都沒撞到就是 [0.22](/backend/00-service-selection/capability-buy-vs-build/) 講的偽自建。

逐能力遷出是常態而非整包搬離：[0.22 的「成長期 SaaS」例子](/backend/00-service-selection/capability-buy-vs-build/) 就是只把撞牆的資料層搬到自管 PostgreSQL、認證留在原平台。本文預設的也是這種逐能力遷出 — 遷的是資料層，不一定連認證、儲存一起搬。

## 6 維 diff audit：主導維度是 paradigm + application change

遷移前先盤點 source 跟 target 的差異落在哪幾維、決定 playbook 結構：

| 維度               | Firestore → 自建 relational                                         | 程度   |
| ------------------ | ------------------------------------------------------------------- | ------ |
| Schema / API       | document / collection → 正規 table、SDK query → 後端 API + SQL      | High   |
| Operational model  | serverless 全託管 → 自管 / managed 資料庫、自己擔 backup / failover | High   |
| Paradigm           | client 直連 + 規則授權 → API 中介 + 後端授權                        | High   |
| Components 數量    | 單一平台 → 新增一層自建後端服務 + 資料庫                            | High   |
| Application change | 前端拔 SDK 改打 API、realtime / offline 要重建                      | High   |
| Data topology      | 平台複製 → 自己設計 replica / 多 region / DR                        | Medium |

主導維度是 **paradigm 與 application change**：六維裡五維落在 High。這定義了結構 — **Type E paradigm shift**（排除 schema 翻譯 Type A 和 drop-in Type B）：存取模型反轉、部分能力重建、可能長期混合（資料層自建、認證仍留平台）。

## 為什麼字面遷移不成立：存取模型反轉

Firestore 的存取模型是 *前端即客戶端、資料庫直接面向公網、授權在規則層*；自建 relational 是 *前端打後端、後端面向資料庫、授權在服務層*。這個反轉是遷移的核心難點，不在資料搬運。

**反正規化 document → 正規 schema**：

- Firestore 為了繞開查詢限制，常把關聯資料冗餘寫進同一 document（一份資料複製多處）
- 遷往 relational 要把冗餘拆回正規化 table、重建外鍵關係，這是逆向工程：要先讀懂當初為什麼這樣存
- 反過來說，有些 document 的巢狀結構在 relational 用 JSONB 保留更省事（見 [PostgreSQL jsonb](/backend/01-database/vendors/postgresql/jsonb-deep-dive/)）— 不是所有 document 都要拆成 table

**Security Rules 授權 → 後端授權**：

- Firestore 的授權邏輯散在 Security Rules DSL 裡，遷移要把每一條規則翻譯成後端 API 的權限檢查
- 這層翻譯是安全敏感的：漏一條規則等於開一個越權查詢的洞，對應 [1.5 資料層紅隊](/backend/01-database/red-team-data-layer/)

**SDK 直連 → API 中介**：

- 前端原本用 Firestore SDK 直接讀寫，遷移後要拔掉 SDK、改打自建 API
- 這是 application 層的大改，不是資料庫換連線字串

**realtime listener / offline persistence → 自己重建**：

- snapshot listener 的即時推送、offline 讀寫快取，是平台白送的能力
- 自建要用 WebSocket / SSE 重建即時層（見 [03 訊息佇列](/backend/03-message-queue/) 與 presence 設計）、用前端本地儲存重建 offline — 這是遷移最容易被漏估的工作量

所以遷移的第一步不是匯資料，是**盤點 application 對 Firestore 的所有依賴面**：查詢路徑、授權規則、realtime 訂閱、offline 行為。這份清單決定哪些能直接遷、哪些要重建、哪些先留在平台。

## 哪些該遷、哪些先留（逐能力混合）

Type E 的本質是不收斂 — 不必把所有 Firebase 能力一次搬完。判讀標準：

| Workload / 能力特徵                           | 去向                                            |
| --------------------------------------------- | ----------------------------------------------- |
| 需要報表 / JOIN / aggregation 的資料          | 遷自建 relational                               |
| 讀取量大、成本敏感、access pattern 穩定的資料 | 遷自建 + [應用層快取](/backend/02-cache-redis/) |
| 仍以 realtime 同步為核心、查詢簡單的資料      | 先留 Firestore / 或最後再遷                     |
| 認證（Firebase Auth）                         | 可留平台、逐能力決定（見 0.22）                 |
| 檔案儲存（Firebase Storage）                  | 可留平台、與資料層解耦後再評估                  |

[0.22 的成長期 SaaS](/backend/00-service-selection/capability-buy-vs-build/) 是這個判讀的 case anchor：撞牆的是資料層的 query 複雜度與成本，遷的就是資料層，認證留在原地。混合不是過渡失敗，是逐能力選型的穩態。

## Phase plan：存取模型反轉的階段化

paradigm shift 的階段化把不可逆動作放到最後、每階段有獨立驗證門檻：

#### Phase 1：依賴面盤點

列出 application 對 Firestore 的所有讀寫路徑、Security Rules 授權條件、realtime 訂閱點、offline 行為。標每項的頻率、安全敏感度、是否可重建。這份清單不完整不進下一階段。

#### Phase 2：relational 重建模

把反正規化 document 設計回正規 schema、決定哪些巢狀結構用 JSONB 保留。同步設計後端 API 的端點與授權檢查、把 Security Rules 逐條翻譯成服務層權限。對應 [1.2 schema design](/backend/01-database/schema-design/) 與 [1.5 資料層紅隊](/backend/01-database/red-team-data-layer/)。

#### Phase 3：自建後端 + dual-write

立起自建後端 API 與資料庫，前端關鍵寫入路徑同時寫 Firestore 與新後端。Firestore 仍是 source of truth、新庫累積資料。dual-write 要處理一邊失敗的補償（對應 [1.9 Reconciliation](/backend/01-database/reconciliation-data-repair/)）。

#### Phase 4：backfill 歷史資料

把 Firestore 既有 document 按新 schema 轉換寫入新庫。backfill 與 dual-write 並行時要處理覆蓋順序，backfill 不能蓋掉 dual-write 的新值。轉換過程記 checksum / row count 對照。

#### Phase 5：shadow read 驗證

讀路徑同時打 Firestore 與新後端、比對結果、記錄差異但仍以 Firestore 回應用戶。差異率降到可接受才進 cutover。對應 [1.7 Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/) 的 evidence 方法。

#### Phase 6：漸進 cutover + 重建即時層

前端逐步把讀寫從 Firestore SDK 切到自建 API（按比例 / 按功能模組），保留切回能力。若產品需要 realtime，這階段要把 snapshot listener 換成自建即時層（WebSocket / SSE）並驗證延遲與斷線重連。cutover 完成後資料層的 source of truth 轉到自建；未遷的能力（認證、儲存）仍在平台 — 混合架構成立。

## Evidence：每階段的前進依據

每個階段用資料證明可前進、不靠感覺：

| 階段        | Evidence                                                                       |
| ----------- | ------------------------------------------------------------------------------ |
| dual-write  | 雙寫成功率、寫入失敗補償紀錄、兩邊 document / row 數差異                       |
| backfill    | 已轉換比例、轉換錯誤數、checksum 對照、反正規化還原正確性抽查                  |
| shadow read | 新舊結果差異率、差異分類（建模差異 vs 真錯誤）、授權翻譯漏洞掃描               |
| cutover     | 切流比例、新 API latency p99、error rate、realtime 推送延遲、rollback 是否觸發 |

這些 evidence 對齊 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)（Source / Time range / Query link / Owner / Data quality）與 [6.8 release gate](/backend/06-reliability/release-gate/)。授權翻譯這項要特別當成 gate 條件 — 它是安全邊界、不只是功能正確性。

## Cutover 與 rollback 決策

資料庫切流失敗代價高、加上這裡牽涉授權正確性，決策權責要寫清楚：

- **cutover window**：選低流量時段、明確切流比例階梯（如 1% → 10% → 50% → 100%），按功能模組切比按全站切安全
- **rollback condition**：新 API error rate / latency 超閾值、shadow read 差異率異常、或發現授權翻譯漏洞 → 切回 Firestore
- **decision owner**：誰有權喊停、依據什麼 evidence、記錄在 [8.19 incident decision log](/backend/08-incident-response/incident-decision-log/)
- **realtime 連續性**：若即時層同步切換，要驗證切換期間訂閱不中斷、或明確告知短暫降級

對應 [rollback window](/backend/knowledge-cards/rollback-window/)、[rollback condition](/backend/knowledge-cards/rollback-condition/)。

## Cleanup 與長期混合

Type E 的 cleanup 通常不是「關掉整個 Firebase」— 多數情況認證、儲存仍留平台：

- 已遷資料路徑的 Firestore collection、Security Rules、dual-write code path 退役
- shadow read 比對 code 移除
- 前端殘留的 Firestore SDK 依賴清掉（資料層已不走它）
- 但 Firebase Auth / Storage 若仍在用，保留；明確標示哪條資料路徑的 source of truth 是自建庫、哪條仍在平台
- Firestore 的資料匯出備份保留到確認新庫穩定，對應 [10.3](/backend/10-system-evolution/managed-platform-exit/) 的並行期退役判準

混合架構不是遷移失敗、是逐能力選型的穩態 — 撞牆的資料層自建、沒撞牆的認證 / 儲存留在平台。

## 失敗模式

production 常見的 5 個踩雷：

#### Case 1：只匯資料、漏了存取模型反轉

把 Firestore 匯出匯進 PostgreSQL 就以為遷完、忘了前端還在打 SDK、授權還在 Security Rules。修法：依賴面盤點是 Phase 1、資料搬運只是其中一條線，存取模型反轉才是主體。

#### Case 2：Security Rules 翻譯漏洞

把規則翻成後端授權時漏一條、開了越權查詢的洞、上線後資料外洩。修法：授權翻譯要逐條對照 + 紅隊驗證（[1.5](/backend/01-database/red-team-data-layer/)）、當成 cutover gate 條件、不是功能 bug。

#### Case 3：反正規化還原錯誤

document 的冗餘副本拆回 table 時還原錯關係、新庫資料關聯接錯。修法：Phase 2 先讀懂當初為何反正規化、backfill 後抽查還原正確性、shadow read 比對抓出建模差異。

#### Case 4：低估 realtime / offline 重建工作量

以為遷資料庫就好、上線才發現 snapshot listener 與 offline 同步整層要自己重建、進度爆炸。修法：依賴面盤點就把 realtime 訂閱點與 offline 行為標出來、列入工作量、必要時這層最後遷或先保留。

#### Case 5：dual-write 一邊失敗沒補償

dual-write 時新庫寫成功 Firestore 失敗（或反之）、兩邊分歧、cutover 後資料不完整。修法：dual-write 要有失敗補償（記錄、重試、標記人工對帳），對應 [1.9 Reconciliation](/backend/01-database/reconciliation-data-repair/)。

**Anti-recommendation**：產品仍重度依賴 realtime / offline、或團隊還沒有自建後端與資料庫的營運能力（backup、failover、授權設計）→ 先不要遷。可先把一塊撞牆最明顯、realtime 需求最低的資料（例如報表來源資料）試點、累積自建營運經驗再擴大。

## 容量與成本：crossover 判讀

遷移的成本判讀關鍵是 *遷移後的總帳*、不是只看 Firestore 帳單：

- **遷移當下**：高 read 流量下，自管資料庫 + 應用層快取的單位成本常低於 Firestore 的 per-read 計費
- **但要加回自建的隱性成本**：後端服務的開發與維運、資料庫的 backup / failover / 擴容、realtime 層的重建與維護、團隊人力
- **判讀分層**：撞到成本牆且已有後端團隊 → 自建總帳通常划算；仍是小團隊、realtime 是核心、流量不大 → Firestore 的「平台白送能力」可能仍比自建總帳便宜

> **Scope warning**：crossover 隨流量形狀、region pricing、團隊成本結構變動、無通用閾值。遷移省下的 Firestore 帳單要扣掉自建後端 + 資料庫 + 即時層的維運成本後再比，不是直接拿兩邊資料庫帳單對照。

接回 [0.6 成本、風險與選型取捨](/backend/00-service-selection/cost-risk-tradeoffs/)、[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)。

## 邊界與整合

### 跟其他遷移路徑的關係

- **保留 document model**：若只是要逃離 Firestore 的查詢限制、但 document 形狀仍適合，遷 [MongoDB](/backend/01-database/vendors/mongodb/) 比遷 relational 的 paradigm 跨度小、不必反正規化還原
- **整包託管遷出**：若連認證、儲存一起搬離 Firebase，整場資產線盤點與並行期走 [10.3 託管形態遷出](/backend/10-system-evolution/managed-platform-exit/)、本文是其中資料層那一條
- **反向視角**：哪些資料當初就不該進 Firestore（報表來源、強一致交易），見 [Firestore overview 的不適用場景](/backend/01-database/vendors/firestore/#不適用場景)

### Sibling 與 cross-link

- [Firestore overview](/backend/01-database/vendors/firestore/) — 服務定位與查詢邊界
- [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/) — 通用 dual-write / shadow read / cutover 框架
- [1.5 資料層紅隊](/backend/01-database/red-team-data-layer/) — Security Rules 授權翻譯的安全驗證
- [1.9 Reconciliation 與 Data Repair](/backend/01-database/reconciliation-data-repair/) — dual-write 失敗補償與資料對帳
- [從 RDS / MongoDB 遷往 DynamoDB](/backend/01-database/vendors/dynamodb/migrate-rds-mongodb-to-dynamodb/) — 同為 Type E paradigm shift 的對照（方向相反：遷入 NoSQL vs 遷出 BaaS）
- [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/) / [0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/) — 遷移 driver 的選型層背景
