---
title: "MySQL → PlanetScale：managed Vitess + branch-based schema workflow 的 hybrid shift"
date: 2026-05-19
description: "自管 MySQL → PlanetScale 加上 Vitess sharding 跟 branch-based schema workflow。本文走 6 維 audit（Paradigm + Operational + Schema 多軸）、4-phase migration、5 production 踩雷、何時不要遷。"
weight: 27
tags: ["backend", "database", "mysql", "vendor", "migration", "type-e", "paradigm-shift", "planetscale"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [MySQL](/backend/01-database/vendors/mysql/) 跟 PlanetScale。走 [Migration playbook methodology](/posts/migration-playbook-methodology/) Type E paradigm shift 結構。

| 維度              | 自管 MySQL               | PlanetScale                                  |
| ----------------- | ------------------------ | -------------------------------------------- |
| Sharding          | 自己配 Vitess 或不 shard | Vitess 透明（即使單 keyspace 也走 Vitess）   |
| Schema migration  | gh-ost / pt-osc 跑 ALTER | **Branch + Deploy Request** workflow         |
| Failover          | Orchestrator 自管        | PlanetScale 自動                             |
| Branching         | 不存在概念               | **DB branch（git-like）+ revert**            |
| Connection limit  | max_connections 自己設   | PlanetScale connection pool / per-plan limit |
| Foreign key       | 支援                     | 有限支援（Vitess 18+ / 2023 起、需明確啟用） |
| `SUPER` privilege | 自己有                   | **無**                                       |
| Multi-region      | 自己配 binlog ship       | PlanetScale 內建（Boost feature）            |
| Per-month cost    | EC2 + EBS + ops          | per-row-read + per-row-written + storage     |

從 *application 連線* 視角：跟 [Aurora MySQL migration](/backend/01-database/vendors/mysql/migrate-to-aurora/) 一樣低、connection string 換就完事。從 *schema management* 視角：PlanetScale 強推 *branch-based workflow* — 改 schema 不再是「跑 gh-ost」、是「開 branch → Deploy Request → review → merge」。整個 schema change 工作流跟 git 同型、跟 application code review 同 workflow。

這是 *workflow + schema-tooling shift* — Aurora 是「同 workflow + managed」、PlanetScale 是「同 protocol + 不同 schema workflow + branch tooling」。Database paradigm（OLTP relational）跟 application change 都 Low、主要 shift 在 DBA / dev 操作介面。

## 為什麼是 Type E（Paradigm + Operational + Schema 多軸）

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/#寫前的-diff-dimension-audit)：

| 維度        | 評          | 說明                                                                         |
| ----------- | ----------- | ---------------------------------------------------------------------------- |
| Schema      | Medium-High | MySQL wire protocol 一致、FK 有限支援（Vitess 18+）、部分 INSTANT DDL 行為差 |
| Operational | High        | branch lifecycle、Deploy Request workflow、connection pooler 不同            |
| Paradigm    | High        | branch-based schema management、跟自管 gh-ost / pt-osc 思維完全不同          |
| Components  | Medium      | PlanetScale CLI / Console / API / connection pooler 都進團隊工具             |
| App change  | Low         | connection string + 移除 FK 約束                                             |
| Topology    | Low-Medium  | Vitess 透明 sharding 即使單 keyspace                                         |

Paradigm + Operational + Schema 三軸 High。按優先序 Schema > Paradigm > Operational、預設選 Type A。但 *讀者最關心* 的是 schema workflow paradigm 轉變、不是 schema field translation — Type E 結構更貼合「不收斂、部分 adopt」的真實 migration 流程。

→ **Type E paradigm shift**、4-phase partial migration（多數 org 停 Phase 2-3 hybrid）。

## Driver：Branch-based workflow + Vitess transparent sharding + zero DBA

從自管 MySQL 遷 PlanetScale 的核心 driver 有三條：

**Branch-based schema workflow**：

- 改 schema 開 branch（`pscale branch create`）、在 branch 上跑 ALTER、跑 application code 改、merge 進 main 前 Deploy Request review
- Deploy Request 顯示 schema diff、跟 GitHub PR 同概念
- Merge 後 PlanetScale 自動跑 *no-downtime schema migration*（內部 VReplication）
- 出問題可 *revert*（48 小時內、用 Vitess VReplication 反向 ship 資料）

這條 workflow 對 *developer ergonomic* 拉力大 — schema change 不再是「DBA 工作」、是「dev 自己處理、跟 code review 同流程」。

**Vitess transparent sharding**：

- PlanetScale 強制每個 cluster 走 Vitess（即使單 keyspace 看似 unsharded）
- 寫吞吐成長到需要 shard 時、加 shard 是 PlanetScale internal 操作、application 看不到
- 不用養 Vitess SRE 團隊

**Zero DBA**：

- PlanetScale 接管所有 ops（failover / backup / parameter / scaling）
- 跟 Aurora 同等級「managed」、加上 branch workflow

FK 處理：早期 Vitess（< 18）不支援 FK、PlanetScale 對應期間建議全 drop FK + 改 application enforcement。Vitess 18（2023 末）後加 FK 支援、PlanetScale 在合適 plan 內可啟用、但 *cross-shard FK* 仍受限。Phase 1 audit 重點不再是「全 drop FK」、而是「驗證 FK 行為（特別 cascade / cross-shard）跟自管 MySQL 預期一致」。

## 4-phase partial migration（不收斂）

### Phase 1：FK 行為驗證 + schema audit、PlanetScale shadow cluster 起來

第一步是 *FK 行為驗證* + schema layout audit。Vitess 18+ / PlanetScale 已支援 FK、但行為跟自管 MySQL 有差異：

- 列所有 FK：`SELECT * FROM information_schema.KEY_COLUMN_USAGE WHERE REFERENCED_TABLE_NAME IS NOT NULL`
- 對每個 FK 評估：
   - *Cross-shard FK*：PlanetScale 不允許 FK 跨 shard、parent 跟 child 必須同 shard（透過 Vindex 設計）
   - *Cascade 行為*：cross-shard DELETE cascade 在 PlanetScale 不執行、改 application 層處理
   - *Native FK 啟用 vs application enforcement*：依 Vitess 18+ 行為決定保留 FK 或改 app-level
- *PlanetScale shadow cluster* 起來、跑 application schema、用 Vitess Connector 從自管 binlog ship 資料

工作主要塊：

- FK 行為 audit + 改 cross-shard cascade（依 FK 數量、weeks 工作量）
- Schema dump → PlanetScale import（用 `pscale shell`）
- Vitess Connector 設定 binlog stream

完成標準：PlanetScale shadow cluster 有完整 production schema、cross-shard FK 已處理、binlog stream lag < 1 秒。

### Phase 2：Read traffic 切 PlanetScale

跟 [Aurora migration](/backend/01-database/vendors/mysql/migrate-to-aurora/) Phase 2 同概念：read query 切 PlanetScale connection string、寫入仍自管 MySQL。

差異：

- PlanetScale connection 有 *per-plan rate limit*（Scaler Plan: 10K connections、Enterprise: 100K）
- 必須走 *PlanetScale connection pool*（不是直接連、有 SSL handshake overhead）
- 監控 `pscale_io_read_query_throttled_total` 確認沒撞 plan limit

跑 2-4 週、確認：

- PlanetScale read latency 跟自管 replica latency 接近（PlanetScale Boost cache 可能比自管快）
- Vitess Connector stream 穩定
- Application 對 PlanetScale row read 量符合 cost forecast

### Phase 3：Schema workflow 切 PlanetScale + write cutover

關鍵 paradigm shift：*停 gh-ost / pt-osc*、改用 PlanetScale branch workflow。

訓練步驟：

1. *第一個 small schema change* 用 PlanetScale branch + Deploy Request 跑
2. 開發團隊熟悉 `pscale branch create` / `pscale deploy-request create` CLI
3. CI integration：把 PlanetScale CLI 加進 deploy pipeline
4. 退役 gh-ost / pt-osc CI integration

完成 schema workflow 訓練後 write cutover：

```bash
# 1. PlanetScale 把 shadow cluster promote 為 primary（用 PlanetScale console / API）
# 透過 PlanetScale Console 啟用 production write 或用 `pscale` CLI 對應 promotion 命令
# （CLI 命令名稱隨 pscale 版本變動、以 pscale --help 為準）

# 2. Application connection string 切 PlanetScale writer
# 自管 → mysql://primary.example.com:3306/production
# PlanetScale → mysql://...@xxx.connect.psdb.cloud/production?sslaccept=strict

# 3. Vitess Connector 反向（PlanetScale → 自管）作為 rollback insurance
```

完成標準：寫入流量 100% 進 PlanetScale、自管 MySQL 接 PlanetScale binlog（rollback buffer）。

### Phase 4：自管 MySQL 退役 / 保留作 rollback buffer

跟 Aurora migration Phase 4 同模式：

- 自管保留 30-90 天作 cold buffer
- 確認 PlanetScale cost forecast 跟 actual 一致（per-row read / write 計費可能超預期）
- 確認 branch workflow 在 production team 內 adopt（不是「PlanetScale 在用、但團隊還是用 gh-ost on staging」這種 stuck 狀態）

多數 org 在 *Phase 3* 停留更久（半年-一年）— Vitess Connector 反向 binlog ship 是穩定 rollback path、Phase 4 不急。

## 5 個 Production 踩雷

### 1. Cross-shard FK — PlanetScale 跟 native MySQL 行為不同

Vitess 18+ / PlanetScale 已支援 FK、但 *cross-shard cascade* 不執行。同 shard 內 FK 跟 native MySQL 一致；parent 跟 child 跨 shard 時、`ON DELETE CASCADE` 在 PlanetScale 不會跨 shard 觸發 child delete、結果 application 看到 *orphan row*。

修法：

- Phase 1 audit 出哪些 FK 跨 shard（Vindex 設計決定 parent / child 是否同 shard）
- 同 shard FK：直接保留、行為跟自管 MySQL 一致
- Cross-shard cascade：改 application 層 transaction 內 explicit DELETE child、或 *background reconciliation job*（定期掃 orphan）
- 把 *parent / child 強制同 shard*（用相同 Vindex column）是預防 cross-shard FK 議題的根本解

### 2. Deploy Request 思維轉換不到位 — 團隊仍用「跑 ALTER」心智模型

DBA / SRE 習慣 *直接連 PlanetScale 跑 ALTER* —但 PlanetScale 在 production branch 上 *禁止 DDL*（必須走 Deploy Request）。失敗訊息 *not actionable*（ERROR: not authorized）、DBA 找不到原因、production maintenance 卡住。

修法：

- Phase 3 *訓練步驟* 不能跳：找一個 small schema change 在 staging 走完整 branch workflow、團隊每個 DBA / SRE 都 hands-on 過
- 在 ops runbook 寫明 *production schema change must go through Deploy Request*、列 CLI 命令模板
- 緊急 schema change（事故中）也走 branch + Deploy Request、PlanetScale 可加速 Deploy（不能 bypass workflow）

### 3. Schema diff 邊界 — PlanetScale 看不到 application-level INSERT changes

Deploy Request 顯示 *schema-level diff*（CREATE / ALTER / DROP）、不顯示 *data diff*。如果 branch 上有 INSERT 進去（測試資料 / seed data）、merge 進 main 時 *資料不會搬*（只搬 schema）、application 預期有資料但 production 沒。

修法：

- 把 *seed data INSERT* 放 application migration / fixture、不在 PlanetScale branch 內
- 用 PlanetScale CLI *export branch data* 跟 *import to main*（手動操作）作為 escape hatch
- 教育團隊：PlanetScale branch = *schema branch*、不是 git-like *data branch*

### 4. Branch lifecycle ops cost — 100 個 stale branch

每個 PR 都開一個 PlanetScale branch、PR merge 後忘記刪、累積 100 個 stale branch。每個 branch 佔 storage cost、PlanetScale plan limit 也限制 branch 數量。

修法：

- CI integration：PR close 自動 `pscale branch delete <branch-name>`
- 設 *branch retention policy*（30 天無活動自動刪）
- 監控 `pscale branch list | wc -l` 數量、超 threshold alert
- 把 branch lifecycle 寫進 *team playbook*（不是 PlanetScale 教、是團隊內部規範）

### 5. 無 `SUPER` privilege — 部分操作不可行

PlanetScale connection 拿到的 MySQL user 沒有 `SUPER` privilege。需要 `SUPER` 的操作直接失敗：

- `SET GLOBAL`（不能改 runtime variable）
- `KILL` 別人的 query（PlanetScale console 提供 alt 介面）
- `SHOW MASTER STATUS` / `SHOW SLAVE STATUS`（PlanetScale 抽象掉、不暴露）
- `INSTALL PLUGIN`（managed、不允許）
- `STOP SLAVE` / `START SLAVE`（Vitess 內部）

修法：

- 評估 application 跟 ops tool 是否依賴 `SUPER` privilege
- 改用 PlanetScale console / API 等價操作
- 部分監控 query（`SHOW SLAVE STATUS`）用 *PlanetScale 內建 dashboard* 代替

## Schema translation 主要工作量塊

雖然 Type E 結構不以 schema translation 為主、但 schema diff 在 Phase 1 仍佔多數時間：

| 自管 MySQL             | PlanetScale (Vitess)                       | 翻譯難度          |
| ---------------------- | ------------------------------------------ | ----------------- |
| FOREIGN KEY constraint | （無）+ application enforcement            | 高                |
| INSTANT DDL            | 部分支援、其他走 Vitess online DDL         | 低-中             |
| Stored procedure       | 支援                                       | 低                |
| Trigger                | 支援                                       | 低                |
| User-defined function  | 受限                                       | 中                |
| INSERT 跨表（CTE）     | 支援                                       | 低                |
| Cross-shard JOIN       | 必須用 Vindex（user_id 等 shard key 同表） | 中-高             |
| `SUPER` 行為           | 不支援                                     | 中（ops tool 改） |
| `RELOAD` privilege     | 不支援                                     | 中                |

## 容量與成本對照

PlanetScale 計費 *很不同*：

| 項目             | 自管 MySQL（EC2）      | PlanetScale Scaler Pro                 |
| ---------------- | ---------------------- | -------------------------------------- |
| Per-row read     | 不計費                 | 按量計費、$1 per 1B row read           |
| Per-row written  | 不計費                 | 按量計費、$1.50 per 1M row write       |
| Storage          | EBS、$0.10/GB-month    | $1.50/GB-month + replication overhead  |
| Connection limit | max_connections 自己設 | per-plan limit、可加 Connection pooler |
| Branch           | 不適用                 | 每 branch 含 storage cost              |
| Boost cache      | 不適用                 | additional cost                        |
| Ops headcount    | 1-2 FTE                | < 0.2 FTE                              |

PlanetScale 適合 *小-中規模 + high developer productivity priority*：

- 流量 < 10K WPS：cost 接近自管、developer productivity 顯著提升
- 流量 10-50K WPS：cost 開始貴、但 ops saving 仍大於 cost increase
- 流量 > 100K WPS：PlanetScale Enterprise 議價、要 commit pricing

對 high-traffic 場景 cost forecast 必須跑 *真實 workload trace* — PlanetScale 提供 `pscale analytics` 預估 read / write 量、用 production binlog replay 在 staging 跑、估算 row read / write 計費。

## 何時不要遷

- **FK 是 application core constraint**：cascade DELETE / SET NULL 廣泛使用、application 改不動
- **大量 `SUPER`-required ops 自動化**：DBA tools / monitoring 寫死 `SUPER`、改不動
- **OS-level customization 需求**：跟 Aurora 一樣、PlanetScale 完全 managed
- **流量極大 + 預算敏感**：> 100K WPS row read 計費可能比 EC2 貴 5x、需要 Enterprise commit pricing
- **跨雲 portability 是 requirement**：PlanetScale 跑在自家 cloud（背後 AWS / GCP）、不像自管 Vitess 可跨雲

## 跟 Aurora MySQL 對比（同 batch 的選擇）

| 維度            | Aurora MySQL                       | PlanetScale                           |
| --------------- | ---------------------------------- | ------------------------------------- |
| Type            | C operational hybrid               | E paradigm shift                      |
| 工作量主軸      | parameter group + IAM + endpoint   | FK audit + branch workflow            |
| Sharding        | 不 shard、single-region scaling    | Vitess 透明 sharding                  |
| Schema workflow | 仍用 gh-ost / pt-osc               | Branch + Deploy Request               |
| FK              | 支援                               | 不支援                                |
| Cost model      | per-hour instance + per-GB storage | per-row read / write + per-GB storage |
| 適合規模        | 100 GB - 50 TB                     | 100 GB - 1 PB                         |
| 跨雲            | AWS-only                           | PlanetScale 背後 AWS / GCP            |

選擇邏輯：

- *AWS-heavy ecosystem + 不想 schema workflow paradigm shift* → Aurora
- *Developer-first culture + 想 branch-based schema workflow + 接受 FK 限制* → PlanetScale

兩者不互斥、有 org 用 Aurora 給 OLTP core、PlanetScale 給 newer microservices（branch workflow 帶價值）。

## 相關連結

- 平行 batch：→ Aurora MySQL migration playbook（同 batch、不同 paradigm）
- 上游：[MySQL vendor overview](/backend/01-database/vendors/mysql/) / [Vitess sharding 設計](/backend/01-database/vendors/mysql/vitess-sharding/)
- 跨章節：[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/) — Deploy Request workflow 對 release gate 的影響
- 既有 vendor 對照：[Aurora vendor page](/backend/01-database/vendors/aurora/) / [PlanetScale 官方](https://planetscale.com/)
- 方法論：[Migration Playbook Methodology](/posts/migration-playbook-methodology/)（Type E paradigm shift 結構說明）
- 官方：[PlanetScale Migration Guide](https://planetscale.com/docs/imports/migrate-from-mysql)
