---
title: "MySQL Vitess Sandbox Route"
date: 2026-05-22
description: "Vitess sandbox、keyspace、shard、VSchema、query routing、resharding preview 與 MySQL migration evidence"
tags: ["backend", "database", "mysql", "hands-on", "vitess"]
---

MySQL Vitess sandbox route 的核心責任是讓讀者用 sandbox 理解 Vitess 如何把 MySQL 拓展成 sharded database platform。這篇承接 [Vitess Sharding](../../vitess-sharding/) 與 [MySQL to PlanetScale](../../migrate-to-planetscale/)。

本文的驗收標準是：你能建立 sandbox、辨識 keyspace / shard / tablet / vtgate、跑基本 query，並記錄 resharding preview 的 evidence。

官方文件路由的核心責任是固定 sandbox 指令。實作前先查 [Vitess local install docs](https://vitess.io/docs/21.0/get-started/local/)；本文最後檢查日是 2026-05-22。

## Concept Map

Concept map 的核心責任是先建立 Vitess vocabulary。

| 概念         | 責任                                 |
| ------------ | ------------------------------------ |
| Keyspace     | logical database / routing boundary  |
| Shard        | keyrange 分片                        |
| Tablet       | MySQL instance + Vitess sidecar role |
| vtgate       | application query routing endpoint   |
| VSchema      | routing、vindex、sharding metadata   |
| VReplication | resharding / materialize workflow    |

Vitess 的重點是 routing 與 resharding。Application 看到的是 vtgate；底下是多個 MySQL tablet 與 topology service。

## Sandbox Setup

Sandbox setup 的核心責任是使用官方 sandbox 建立可丟棄環境。實際命令依 Vitess 版本調整，正式操作以 Vitess 官方文件為準。

```bash
# Conceptual route. Use the current Vitess examples for exact commands.
git clone https://github.com/vitessio/vitess.git
cd vitess/examples/local
./101_initial_cluster.sh
```

啟動後要記錄：

1. Vitess version。
2. Keyspace name。
3. Shard count。
4. vtgate host / port。
5. Tablet roles。

## Query Through vtgate

Query through vtgate 的核心責任是確認 application 走 routing layer。

```bash
mysql -h 127.0.0.1 -P 15306 -u user <<'SQL'
SHOW DATABASES;
USE commerce;
SHOW TABLES;
SELECT * FROM product LIMIT 5;
SQL
```

Evidence 要包含 query result、target keyspace、vtgate endpoint 與 tablet health。Production migration 要確認 ORM / driver 對 vtgate 的相容性。

## VSchema Review

VSchema review 的核心責任是理解 shard key 與 routing。

```bash
# Conceptual command; exact path depends on sandbox.
cat vschema_commerce_initial.json
```

審查問題：

1. 哪些 table 是 sharded。
2. shard key / vindex 是什麼。
3. lookup vindex 是否需要維護。
4. cross-shard query 是否存在。
5. sequence / id generation 如何處理。

VSchema 是 Vitess migration 的核心設計文件。選錯 shard key 會讓跨 shard transaction、hot shard 與 resharding 成本升高。

## Resharding Preview

Resharding preview 的核心責任是看見 Vitess 的主要價值與操作成本。

Resharding evidence 欄位：

```text
source shard:
target shards:
workflow name:
copy phase duration:
replication lag:
cutover time:
validation query:
rollback:
```

Resharding 是 production operation，不只是一次 migration。Runbook 要包含 throttling、lag、tablet health、cutover 與 application query validation。

## Migration Decision

Migration decision 的核心責任是判斷何時從 MySQL 走向 Vitess / PlanetScale 類路線。

| 訊號                          | 意義                               |
| ----------------------------- | ---------------------------------- |
| 單 MySQL writer 到頂          | 需要 horizontal write scaling      |
| tenant shard boundary 清楚    | Vitess keyspace / shard 有機會匹配 |
| online resharding 是核心需求  | Vitess value 高                    |
| app 缺少 routing 語意改造空間 | 先重構 repository / query          |

完成本篇後，設計細節讀 [Vitess Sharding](../../vitess-sharding/)；managed route 讀 [MySQL to PlanetScale](../../migrate-to-planetscale/)。
