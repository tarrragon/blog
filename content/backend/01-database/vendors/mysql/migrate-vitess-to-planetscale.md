---
title: "自管 Vitess → PlanetScale：Vitess component ops outsource、加 schema workflow shift"
date: 2026-05-19
description: "自管 Vitess → PlanetScale 是 Type C operational hybrid — Vitess component（VTGate / VTTablet / VReplication / VSchema）ops outsource + branch workflow。本文走 6 維 audit、4-phase migration、5 production 踩雷、何時不要遷。"
weight: 28
tags: ["backend", "database", "mysql", "vendor", "migration", "type-c", "operational-hybrid", "vitess", "planetscale"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [Vitess sharding](/backend/01-database/vendors/mysql/vitess-sharding/) 跟 PlanetScale。走 [Migration playbook methodology](/posts/migration-playbook-methodology/) Type C operational hybrid 結構。

| 元件             | 自管 Vitess                          | PlanetScale                             |
| ---------------- | ------------------------------------ | --------------------------------------- |
| VTGate           | 自己部署 + LB                        | Managed、隱藏在 PlanetScale endpoint 後 |
| VTTablet         | 自己 per-MySQL deploy                | Managed                                 |
| VReplication     | 自己 trigger workflow                | Managed、透過 Console / API             |
| VSchema          | 自己維護（YAML / API）               | Managed、Console UI 編輯                |
| MySQL backend    | 自己 EC2 / on-prem                   | Managed (Aurora-like underlying)        |
| Schema migration | gh-ost / pt-osc 或 Vitess online DDL | **Branch + Deploy Request workflow**    |
| Failover         | 自己用 VTOrc                         | Managed                                 |
| Multi-region     | 自己配 VReplication 跨 region        | Boost / per-region cluster              |
| Cost model       | EC2 + EBS + ops headcount            | Per-row read / write + storage          |

這條 migration 跟 [→ Aurora MySQL](/backend/01-database/vendors/mysql/migrate-to-aurora/) 相似（self-managed → managed），但 *target 是 Vitess-native managed*、保留 sharding 能力。同時加上 [→ PlanetScale from self-managed MySQL](/backend/01-database/vendors/mysql/migrate-to-planetscale/) 的 branch workflow paradigm。

對 *已花心力建 Vitess team 但 ops cost 太大* 的 org 來說、這條 migration 比 *Vitess → distributed SQL* 風險低、保留 sharding investment。

## 為什麼是 Type C（不是 Type A 或 Type E）

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/#寫前的-diff-dimension-audit)：

| 維度        | 評     | 說明                                                                |
| ----------- | ------ | ------------------------------------------------------------------- |
| Schema      | Low    | Vitess wire protocol + VSchema 概念一致                             |
| Operational | High   | 4 個 component 的 ops 全部 outsource、branch workflow 是新 paradigm |
| Paradigm    | Medium | Vitess paradigm 不變、但加 branch workflow                          |
| Components  | Low    | 同 Vitess engine                                                    |
| App change  | Low    | Connection string 改、無 schema rewrite                             |
| Topology    | Low    | Vitess sharding 結構保留                                            |

Operational = High（其他 Low / Medium） → **Type C operational hybrid**。Branch workflow 是 *Medium paradigm shift* 但不是 dominant — 主要工作量在 *operational ownership 轉移*。

跟 [自管 MySQL → PlanetScale](/backend/01-database/vendors/mysql/migrate-to-planetscale/)（Type E paradigm shift）對比：那條 path 是 *no-Vitess → Vitess + branch*、要學 Vitess 概念 + branch；本條是 *已有 Vitess + 加 branch*、只學 branch、複雜度低很多。

## Driver：Ops headcount + Branch workflow + Vitess feature 加速

從自管 Vitess 遷 PlanetScale 的核心 driver：

**Ops headcount 削減**：

- 自管 Vitess 通常需要 *2-5 個 SRE/DBA 撐 production* —VTGate / VTTablet / VReplication / VSchema 各有議題
- PlanetScale 把這層全部 outsource、團隊 ops headcount 可降到 < 1 FTE
- 對 50-200 人 eng team、ops cost saving 是顯著 driver

**Branch workflow paradigm**：

- 自管 Vitess 仍用 gh-ost / pt-osc 或 Vitess online DDL 跑 schema migration、是 DBA 主導
- PlanetScale branch workflow 把 schema migration 變 *developer self-service*、開 branch / Deploy Request / merge、跟 git workflow 同節奏
- 對 *high-velocity engineering culture* 是文化升級

**Vitess upstream feature**：

- PlanetScale team 是 Vitess 的主要 contributor、新 feature 通常 PlanetScale 先 ship
- 自管 Vitess 升級慢、PlanetScale 用戶看到新 feature 早 3-6 個月

不適合 *跨雲 portability priority high* 或 *strict on-prem deployment* 的 org — PlanetScale 是 cloud-only。

## 4-phase migration

### Phase 1：Topology + VSchema audit

把當前自管 Vitess cluster 完整盤點：

```bash
# Vitess cluster topology
vtctldclient GetKeyspaces
vtctldclient GetShards <keyspace>
vtctldclient GetTablets

# VSchema
vtctldclient GetVSchema <keyspace>

# 跨 keyspace VReplication workflow
vtctldclient GetWorkflows
```

對每個 keyspace 檢查：

- *Shard 數量*：PlanetScale plan 對 shard 數量有 limit（Enterprise 才能超大規模）
- *VSchema features*：自管可能用 *PlanetScale 不支援的 Vindex*（custom Vindex）
- *Foreign key*：Vitess 18+（2023 末）才支援 FK、自管 Vitess 大多 < 18、cluster 內已 application-enforced；遷 PlanetScale 後可選擇啟用 native FK（同 shard 內）或繼續 application enforcement
- *Stored procedure / trigger*：PlanetScale 受限、確認是否 application 依賴

完成標準：寫 *blocker list*（PlanetScale 不支援的功能）+ *compatibility list*（功能對應）。

### Phase 2：Dual cluster + binlog stream

PlanetScale 內建 *Vitess Connector*、從外部 MySQL（包括其他 Vitess cluster）binlog stream import：

```bash
# 1. 用 PlanetScale CLI 建 cluster
pscale database create production --region us-east

# 2. Import schema（從自管 Vitess export）
pscale shell production main < schema.sql

# 3. 設 Vitess Connector 從自管 cluster import 資料
# （透過 PlanetScale Console）
```

Vitess Connector 從自管 VTTablet 的 MySQL primary 讀 binlog、寫進 PlanetScale。Lag 通常 < 1 秒。

跑 1-2 週、確認：

- Schema 完整 migrate
- VSchema 對應正確（Vindex 行為一致）
- Lag 穩定

### Phase 3：Application read 切 PlanetScale

跟 Aurora migration Phase 2 同概念。Application read query 切 PlanetScale endpoint：

- 連 PlanetScale connection string（`xxx.connect.psdb.cloud`）
- 仍寫自管 Vitess、Vitess Connector 同步 PlanetScale

跑 2-4 週、驗證：

- Query result 一致
- PlanetScale read latency 接近自管（PlanetScale Boost cache 可能加速）
- PlanetScale row read 計費跟預估一致

### Phase 4：Write cutover + 自管 Vitess 退役

```bash
# 1. PlanetScale 把 cluster promote 為 primary（透過 Console）
# 透過 PlanetScale Console 啟用 production write 或用 `pscale` CLI 對應 promotion 命令
# （CLI 命令名稱隨 pscale 版本變動、以 pscale --help 為準）

# 2. Application 寫 connection string 切 PlanetScale
# 自管 Vitess → PlanetScale

# 3. Vitess Connector 反向（PlanetScale → 自管）作為 rollback buffer

# 4. 跑 1-2 週確認、開始 decommission 自管 Vitess
```

Decommission 自管 Vitess 是大工程：

- VTGate / VTTablet pods 一個個關
- VReplication workflow 停掉
- MySQL backend 保留作 cold backup 1-3 月、然後 EBS snapshot + terminate

完成標準：所有 traffic 在 PlanetScale、自管 Vitess 資源全 release、ops headcount confirm 下降。

## 5 個 Production 踩雷

### 1. VSchema 不完全兼容 — Custom Vindex 必須改

自管 Vitess 可能用了 *custom Vindex*（自寫 Go plugin）、PlanetScale 不支援 custom Vindex（只支援 built-in：hash / lookup_hash / unicode 等）。

修法：

- Phase 1 audit 出所有 custom Vindex
- 對每個 custom Vindex 評估能否用 built-in 替代
- 不能替代的、考慮 *application 層 logic 取代 Vindex*（application 自己算 shard key）
- 或 *暫不遷該 keyspace*、保留自管 Vitess 跑 custom Vindex keyspace、其他遷 PlanetScale

### 2. Branch workflow 訓練不到位 — DBA 仍用「Vitess online DDL」心智模型

自管 Vitess team 習慣 `vtctldclient ApplySchema --strategy=vitess` 跑 online DDL、遷 PlanetScale 後仍想直接這樣 — 但 PlanetScale production branch 禁止 schema change、必須走 Deploy Request。

修法：

- Phase 3 *訓練步驟*：team 每個 DBA / SRE 都跑過完整 branch + Deploy Request workflow
- 寫 *team runbook*：production schema change must 走 branch
- 緊急 schema change（事故中）也走 branch、PlanetScale 可加速 Deploy

### 3. SUPER privilege 移除 — 自管 admin tool 失效

自管 Vitess 用 `SUPER` privilege 跑 admin script、PlanetScale 沒給 SUPER。常見失效：

- 自寫 monitor script 跑 `SHOW SLAVE STATUS`、PlanetScale 抽象掉
- 自寫 backup script 跑 `FLUSH TABLES WITH READ LOCK`、PlanetScale 不允許
- 自寫 cleanup script 跑 `KILL QUERY`、PlanetScale 受限

修法：

- Phase 1 audit 所有 admin script
- 改用 *PlanetScale Console / CLI / API* 等價操作
- PlanetScale 提供的 monitoring 介面替代自管監控

### 4. Connection limit — PlanetScale plan 比預期緊

PlanetScale Scaler Plan: 10K connection、Enterprise: 100K。自管 Vitess VTGate 通常設 50K-200K connection、遷 PlanetScale 後 hit limit。

修法：

- Phase 1 *connection forecast*：peak hour 多少 active connection
- 升 PlanetScale plan（Scaler Pro / Enterprise）
- 或在 application 端加 connection pool（HikariCP / pgBouncer 等價）降低 connection count

### 5. Cost model 翻盤 — Per-row read 計費超預期

PlanetScale 計費是 *per row read / written*。自管 Vitess cost = EC2 + EBS（線性 with infrastructure scale）。遷 PlanetScale 後計費跟 *application access pattern* 直接相關。

常見 surprise：

- Heavy analytics query（COUNT *、aggregation）讀大量 row、計費高
- N+1 query pattern（application 跑很多小 SELECT）讀很多 row、計費高
- Read-heavy workload 沒 Boost cache、每次 query 都 hit billing

修法：

- Phase 1 *cost forecast*：用 `pscale analytics` 預估 row read / write 量、估算月帳
- Phase 2 期間實際對 PlanetScale 跑 traffic、看實際 billing
- Heavy analytics 改 *材料化 view* / *async aggregation*、不是每次 query
- 高 read frequency 開 Boost cache（額外 cost、但比 row read 便宜）

## Capability mapping

| 自管 Vitess       | PlanetScale 對應                       | 兼容度                      |
| ----------------- | -------------------------------------- | --------------------------- |
| VTGate            | PlanetScale endpoint                   | 100%                        |
| VTTablet          | PlanetScale managed                    | 100%                        |
| VReplication      | PlanetScale Console + Deploy Request   | 90%（內部使用更受限）       |
| VSchema           | PlanetScale Console / pscale CLI       | 95%（custom Vindex 不支援） |
| Vitess online DDL | Deploy Request workflow                | 不同 paradigm、功能等價     |
| Backup            | PlanetScale 自動                       | 100%（且更好）              |
| Failover          | PlanetScale 自動                       | 100%                        |
| Multi-region      | PlanetScale Boost / per-region cluster | 90%                         |
| Custom plugin     | 不支援                                 | 0%                          |
| SUPER privilege   | 不支援                                 | 0%                          |

## 容量與成本對照

對 200 人 eng team 用自管 Vitess（10 shard、20 TB 資料、50K WPS）：

| 項目                | 自管 Vitess（自管 EC2）                | PlanetScale Scaler Pro           |
| ------------------- | -------------------------------------- | -------------------------------- |
| Infrastructure      | ~$15K-25K / mo（EC2 + EBS + LB）       | Variable（per row read / write） |
| Ops headcount       | 2-3 FTE × $150K / yr = $300K-450K / yr | < 0.5 FTE × $150K = $75K / yr    |
| Vitess upgrade cost | 每年 1-2 個 SRE × 2 週                 | 自動                             |
| Per-row read        | 不計費                                 | $1 per 1B row read               |
| Per-row written     | 不計費                                 | $1.50 per 1M row write           |
| Storage             | EBS $2K-5K / mo                        | $1.50 / GB / mo                  |
| **總帳**            | ~$400K-550K / yr                       | ~$200K-350K / yr（看 traffic）   |

對中型規模、PlanetScale 通常 break-even 或更便宜。對極大規模（> 200K WPS / > 100 TB）PlanetScale Enterprise 需要 commit pricing、不一定划算。

## 何時不要遷

- **跨雲 / on-prem 是 requirement**：PlanetScale cloud-only
- **Custom Vindex / 特殊 plugin** 大量使用：兼容度低、改造工作量大
- **規模極大** > 500K WPS / > 200 TB：PlanetScale plan 對應 Enterprise commit、議價辛苦
- **強合規 / 資料主權限制**：金融 / 政府 / 醫療場景、PlanetScale 不一定能 cover compliance
- **既有 Vitess team 強 + ops cost 低**：如果 ops 已經精實、不必為 outsource 而 outsource

## 跟其他模組整合

### 跟 [Vitess sharding](/backend/01-database/vendors/mysql/vitess-sharding/)

本 migration 保留 Vitess sharding 概念、application code 視角幾乎不變。Phase 1 audit 是 *Vitess concept 對應 PlanetScale concept*、不是 *拆 Vitess 換 distributed SQL*。

### 跟 [→ PlanetScale (from self-managed MySQL)](/backend/01-database/vendors/mysql/migrate-to-planetscale/)

本 migration 是 *Vitess → PlanetScale*、前者是 *MySQL → PlanetScale*。差異：

- *MySQL → PlanetScale* (Type E)：要學 Vitess 概念 + branch workflow + FK 處理
- *Vitess → PlanetScale* (Type C)：只學 branch workflow + ops outsource、保留所有 Vitess investment

選哪條 path 取決於起點。

### 跟 [Major Version Upgrade](/backend/01-database/vendors/mysql/major-version-upgrade/)

從自管 Vitess 上 MySQL 5.7 遷 PlanetScale 也是 *同時跨 major version*（PlanetScale 跑 8.0+ Vitess）。Application 必須同時處理 5.7 → 8.0 paradigm shift（charset / auth）。

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [Vitess Sharding](/backend/01-database/vendors/mysql/vitess-sharding/)（self-managed source）
- [→ PlanetScale from self-managed MySQL](/backend/01-database/vendors/mysql/migrate-to-planetscale/)（不同起點）
- [→ Aurora MySQL](/backend/01-database/vendors/mysql/migrate-to-aurora/)（另一條 self-managed → managed path）
- [Major Version Upgrade](/backend/01-database/vendors/mysql/major-version-upgrade/)（5.7 → 8.0 同期考量）
- 方法論：[Migration Playbook Methodology](/posts/migration-playbook-methodology/)（Type C operational hybrid）
- 官方：[PlanetScale Migration Guide](https://planetscale.com/docs/imports) / [Vitess Operator](https://github.com/planetscale/vitess-operator)
