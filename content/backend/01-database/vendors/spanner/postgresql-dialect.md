---
title: "Spanner PostgreSQL dialect：PG-compatible interface vs GoogleSQL、相容子集邊界、何時選 PG dialect"
date: 2026-06-02
description: "Spanner PostgreSQL dialect 是建在 Spanner 分散式引擎之上的 PG-compatible 介面、提供 PostgreSQL 語法、型別與 wire protocol、但不是完整 PostgreSQL。本文先定義 PG dialect 跟 GoogleSQL dialect 的責任差異、再劃相容子集邊界（哪些 PG 功能不在、哪些 Spanner-only 概念仍要懂）、最後給選 dialect 的決策判準與 dialect 不可變更的失敗代價"
weight: 35
tags: ["backend", "database", "spanner", "global-sql", "postgresql-dialect", "googlesql", "deep-article"]
---

> 本文是 [Cloud Spanner](/backend/01-database/vendors/spanner/) overview 的 implementation-layer deep article、寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。Overview 已說明 Spanner 在全球 OLTP 譜系的定位、本文聚焦 *PostgreSQL dialect* — Spanner 為降低 PostgreSQL 生態遷入門檻提供的 PG-compatible 介面、跟原生 GoogleSQL dialect 的差異與邊界。

---

## 核心定位：PG dialect 是介面層、不是換引擎

Spanner PostgreSQL dialect 的責任是讓 PostgreSQL 生態的語法、型別系統與 wire protocol 能跑在 Spanner 的分散式引擎之上、降低團隊既有 PostgreSQL 知識與工具的遷移成本。它改變的是 *query 語言與 client 介面*、不改變底層的 split-based 儲存、Paxos 複製、TrueTime commit 與 external consistency — 這些 Spanner 的分散式語意在兩種 dialect 下完全一致。

把這條定位放在最前面、是因為最常見的誤解是「選了 PG dialect 就等於用 PostgreSQL」。實際上 PG dialect 是「用 PostgreSQL 的方言跟 Spanner 對話」、不是「在 Spanner 裡裝一個 PostgreSQL」。team 帶著 PostgreSQL 的 `psql`、libpq driver、PG 語法進來、但要寫的仍是 Spanner — 一個沒有 single-primary、沒有本地 sequence、partition 由系統管理的分散式 SQL。

GoogleSQL dialect 是 Spanner 原生方言、語法接近 BigQuery 的 GoogleSQL、攜帶 Spanner-specific 的 `INTERLEAVE IN PARENT`、array 型別、`PENDING_COMMIT_TIMESTAMP` 等原生概念。兩種 dialect 是 instance / database 建立時就固定的選擇、之後不可變更。

## 問題情境：PostgreSQL 團隊想遷入 Spanner、但不想重寫所有 SQL

PostgreSQL dialect 的存在價值、在「既有 PostgreSQL 應用要拿到 Spanner 的全球強一致與線性擴展、但團隊的 SQL、ORM、tooling、人員技能都綁在 PostgreSQL」這個壓力下浮現。讀者徵兆：團隊評估 Spanner 時發現 GoogleSQL 語法陌生、ORM（如 SQLAlchemy、Hibernate）的 PostgreSQL dialect 已深度整合、DBA 熟悉 `psql` 與 PG 工具鏈、不想為了遷移把整套 SQL 知識重學。

真實壓力場景：一個建在 Cloud SQL for PostgreSQL 上的金融 ledger、撞到 single-primary 寫入上限、需要遷到 Spanner 拿跨 region 強一致;團隊有數萬行 PostgreSQL SQL、用 libpq-based driver、若 target 是 GoogleSQL、application 層改動範圍會大到讓遷移 ROI 不成立。PG dialect 把這個改動範圍縮小到「相容子集邊界內的 SQL 多數可沿用、邊界外的功能需要改寫」。

Case anchor：本主題在 case 庫覆蓋稀薄。9.C10 是 Google internal dogfood case、未展開 dialect 選擇細節、且不是 customer-facing 參考。本文 dialect 機制、相容子集邊界、wire protocol 行為均以 GCP vendor 規格 + 通用遷移工程展開、case 僅作「為什麼 PostgreSQL 團隊要遷 Spanner」的壓力 anchor。延伸的遷移流程在 sibling [migrate-from-cloud-sql-pg](../migrate-from-cloud-sql-pg/)。

## 相容子集邊界：哪些 PostgreSQL 功能不在範圍內

PG dialect 提供 PostgreSQL 語法、型別、function 與 wire protocol 的 *一個子集*、邊界由「Spanner 分散式引擎能不能支援該語意」決定、不是 PostgreSQL 有什麼就有什麼。理解邊界的關鍵是分清三類：相容沿用的、Spanner 用不同方式達成的、根本不存在的。

### 相容沿用：多數標準 SQL

標準 DML（`SELECT` / `INSERT` / `UPDATE` / `DELETE`）、多數 JOIN、聚合、CTE、常見型別（`bigint` / `text` / `numeric` / `timestamptz` / `bool` / `jsonb`）、prepared statement、parameterized query 在 PG dialect 下沿用 PostgreSQL 語法。libpq-based driver 與 `psql` 可直接連、wire protocol 相容讓 PostgreSQL client 工具多數可用。

### Spanner 用不同方式達成：sequence、schema change、PK

PostgreSQL 的 `SERIAL` / `bigserial` 在分散式系統下會製造熱點（單調遞增的 PK 集中寫到同一個 split）、Spanner 引導用 UUID 或 bit-reversed sequence 分散寫入。schema change 在 PG dialect 下仍是 Spanner 的 long-running operation、不是 PostgreSQL 的同步 DDL — DDL 語法是 PG 風格、但執行語意是 Spanner 的（見 [schema-migration-interleaved-tables](../schema-migration-interleaved-tables/)）。primary key 設計直接決定資料分布、跟 PostgreSQL 把 PK 當邏輯約束的心智不同。

### 根本不存在：PostgreSQL 重度功能

部分 PostgreSQL 的進階功能不在 PG dialect 範圍內、團隊若依賴它們、遷移要先找替代路徑。常見的缺口包含：自訂 extension（PostGIS、pgvector 等需另尋路徑）、stored procedure / 觸發器生態、部分 window function 與進階型別、`LISTEN` / `NOTIFY`、以及 PostgreSQL 特有的 lock 與 vacuum 心智。這些缺口不是 bug、是「Spanner 不是 PostgreSQL」的直接後果。

> **Scope warning**：PG dialect 的具體支援清單（支援哪些型別、function、語法）逐版本擴充、本文列舉的相容子集邊界屬 GCP 規格、實作前必須 cross-verify [Spanner PostgreSQL dialect 官方文件](https://cloud.google.com/spanner/docs/postgresql-interface) 的當前支援矩陣、不能依本文清單當最終依據。

## 操作流程：建立 PG dialect database、連線、驗證相容性

### Step 1：建立 PG dialect database

dialect 在建立 database 時指定、不可事後變更。建立時明確選 PostgreSQL dialect：

```bash
gcloud spanner databases create my-pg-db \
  --instance=my-instance \
  --database-dialect=POSTGRESQL
```

驗證：查 database metadata 確認 dialect 是 POSTGRESQL。這步若選錯、唯一修法是建新 database 重遷、沒有 in-place 轉換 — 這是本文反覆強調的不可逆決策。

### Step 2：用 PostgreSQL client 連線

PG dialect 接受 PostgreSQL wire protocol、可用 `psql` 或 libpq-based driver 連線（透過 PGAdapter proxy 或支援的 client library）。

```bash
# 透過 PGAdapter 用 psql 連線
psql -h localhost -p 5432 -d my-pg-db
```

驗證：跑一個簡單 `SELECT 1`、確認 wire protocol 通;再跑一個帶 PG 型別的 query、確認型別映射正確。

### Step 3：相容性 audit — 跑既有 SQL 測邊界

把既有 PostgreSQL application 的 SQL 集合在 PG dialect database 上跑一遍、標出哪些直接通過、哪些報不支援。這步是遷移評估的核心 evidence — 它把「相容子集邊界」從文件文字變成「我的 SQL 有多少落在邊界內」的具體數字。

驗證點：統計通過率、把不通過的 SQL 分類（用 different way 達成 vs 根本不支援）、對「根本不支援」的部分評估改寫成本。若改寫成本過高、這是 PG dialect 路徑的 no-go 訊號。

### Step 4：rollback boundary

dialect 不可變更、所以 rollback boundary 在「遷移評估階段」、不在「上線後」。決策樹是：相容性 audit 通過率高 + 改寫成本可控 → 選 PG dialect;通過率低 + 大量 Spanner-only 優化需求 → 直接學 GoogleSQL。一旦 database 建好、dialect 就鎖定、rollback 等於重建 database 重遷。

## 失敗模式：把 PG dialect 當完整 PostgreSQL、與 dialect 鎖定

### 把 PG dialect 當完整 PostgreSQL 用

團隊假設「PG dialect = PostgreSQL」、直接把依賴 extension、stored procedure、`SERIAL` PK 的應用搬過來、上線後發現 extension 不存在、`SERIAL` 製造熱點、p99 write latency 因 PK 集中而退化。徵兆是特定 PK range 的 split CPU 飆高、其餘 split 閒置。修法是審查 PK 設計改用分散式友善的 key（UUID / bit-reversed sequence）、把 extension 依賴改成 application 層或外部服務。這個失敗的根因是心智模型錯位、不是 bug。

### Dialect 鎖定後才發現需要另一種 dialect

dialect 是 database 建立時的不可逆選擇、團隊選了 PG dialect、後續發現需要 GoogleSQL 才有的某個原生能力（或反之）、唯一路徑是建新 database 重遷全部資料。這個失敗的代價遠高於一般 config 錯誤 — 它不是改一行設定、是一次完整的資料遷移 + application cutover + 驗證 + rollback 規劃。回退路徑是把它當成一次 Type E migration（見 [migrate-from-cloud-sql-pg](../migrate-from-cloud-sql-pg/) 的 paradigm shift 結構）、不能當成 hotfix。預防勝於回退：在 Step 3 的相容性 audit 階段就要把「未來可能需要哪種 dialect 的能力」一起評估、而不是只看當下的 SQL 通過率。

### 以為換了 PG dialect 就不用懂 Spanner 分散式語意

PG dialect 降低語法門檻、但 Spanner 的 split、hot range、interleaved table、commit wait、cross-region quorum 在 PG dialect 下完全一樣。團隊若以為「用 PG 語法就能當 PostgreSQL 維運」、會在 hot partition、跨 region latency、schema change 是 long-running operation 這些 Spanner-specific 議題上踩雷。修法是不論選哪種 dialect、Spanner 的分散式機制都要懂 — dialect 是介面、不是引擎。

## 容量與觀測：dialect 不改變容量模型

PG dialect 跟 GoogleSQL 共用同一個 Spanner 引擎、容量模型、metric、sizing 完全一致 — 選 dialect 不影響容量規劃。核心觀測仍是 Spanner instance 的 CPU、split distribution、commit latency、跟原生 GoogleSQL database 沒有差別。

需要額外觀測的是 PG dialect 特有的接入層：若透過 PGAdapter proxy 連線、proxy 本身是一跳、要監控 proxy 的延遲與可用性、避免它成為單點。

```text
Spanner CPU utilization        → 跟 dialect 無關、共用引擎指標
split / hot range distribution → PK 設計（含 SERIAL 熱點）直接反映在這
PGAdapter proxy latency        → PG dialect 接入層的額外一跳（若使用）
commit_latencies               → external consistency 的 commit wait、兩 dialect 一致
```

容量規劃路由回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) — sizing 邏輯跟 dialect 無關。觀測接 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。

> **Scope warning**：PGAdapter 的部署模型（sidecar / standalone proxy）與其延遲特性屬 GCP 規格、cross-verify 官方文件、非 9.C10 case 揭露。

## 邊界與整合：何時選 PG dialect、何時選 GoogleSQL

### 選 PG dialect 的條件

既有 PostgreSQL 應用要遷入、SQL / ORM / tooling 深度綁 PostgreSQL、相容性 audit 通過率高、且不需要大量 Spanner-only 原生優化 — 這是 PG dialect 的適用條件。它讓遷移的 application 層改動最小化、保留團隊既有 PostgreSQL 技能。

### 選 GoogleSQL 的條件

全新專案、團隊願意學 Spanner 原生方言、需要深度用 interleaved table、array 型別、Spanner-specific 優化、或想跟 BigQuery 的 GoogleSQL 生態對齊 — 選 GoogleSQL。它是 Spanner 的一等公民方言、新功能通常先在 GoogleSQL 落地。

### 何時兩者都不選（不該升 Spanner）

若 workload 是單 region、不需要全球強一致、PostgreSQL dialect 的相容性吸引力不該成為升 Spanner 的理由 — Cloud SQL for PostgreSQL 是真正的 PostgreSQL、相容性 100%、成本更低。Anti-recommendation 的判準是：PG dialect 的價值在「已經要遷 Spanner、想降低遷移成本」、不在「因為它像 PostgreSQL 所以選 Spanner」。把 dialect 相容性當升級理由是把次要因素當主要決策。

### Sibling deep articles 路由

- [migrate-from-cloud-sql-pg](../migrate-from-cloud-sql-pg/)：PG dialect 是 Cloud SQL → Spanner 遷移降低改動成本的關鍵、本文的相容子集邊界對應該 playbook 的 diff audit
- [schema-migration-interleaved-tables](../schema-migration-interleaved-tables/)：PG dialect 下 DDL 仍是 Spanner long-running operation、interleaved table 在兩 dialect 都要懂
- [consistency-models-comparison](../consistency-models-comparison/)：兩 dialect 共用 external consistency、dialect 不改變一致性語意

### 跟 knowledge card 的互引

- [distributed-sql](/backend/knowledge-cards/distributed-sql/) — PG dialect 是 distributed SQL 上的相容介面、不改變 distributed SQL 的本質
- [isolation-level](/backend/knowledge-cards/isolation-level/) — 兩 dialect 共用 Spanner 的 external consistency、isolation 語意一致

### 跟其他 vendor 的對照路由

- [CockroachDB vendor](/backend/01-database/vendors/cockroachdb/)：CockroachDB 走 PostgreSQL wire 相容是其核心策略、跟 Spanner PG dialect 是兩種「PostgreSQL 相容的 distributed SQL」路線、相容程度與邊界不同
