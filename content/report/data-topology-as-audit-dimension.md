---
title: "Data topology 是 process content 的第 6 audit 維度"
date: 2026-05-19
weight: 128
description: "Process content 的 diff dimension audit 原本 5 維（schema / operational / paradigm / components / application change）漏了 *data topology* — 資料在 cluster / partition / region 之間的分佈拓樸；topology 不在既有 5 維任一個、但決定 re-sharding / partition redesign / multi-region rollout 的結構；本卡擴 audit 到 6 維、新增 Type F「Topology re-layout」結構"
tags: ["report", "事後檢討", "工程方法論", "原則", "抽象層", "Content-design", "Process-writing", "Audit-dimension"]
---

## 結論

Process content 的 [diff dimension audit](../content-structure-by-max-diff-dimension/) 原本 5 維 — schema / operational / paradigm / components / application change — 漏了 *data topology* 這軸。Topology 是 *資料在 cluster / partition / region 之間的分佈拓樸*、跟既有 5 維任一個都不對等：

| 維度                | 處理對象                              | 對 topology 的關係              |
| ------------------- | ------------------------------------- | ------------------------------- |
| Schema / API        | 資料結構（column / type / index）    | 不同層、schema 不變 topology 可能變 |
| Operational model   | 運維 stack（HA / backup / monitoring）| topology 可能影響 ops、但不是同一概念 |
| Paradigm            | 核心抽象（OLTP / log / pub-sub）     | 同 paradigm 內 topology 可變    |
| Components          | 元件數量（1 vs N）                    | 同 component 數可有不同 topology |
| Application change  | application code 改動量              | topology 變不必然 application 改 |
| **Data topology**   | **slot / shard / partition / region 分佈** | **本卡新增的第 6 維**      |

擴 audit 到 6 維、新增 [Type F「Topology re-layout」](../content-structure-by-max-diff-dimension/) 結構對映 *topology 高差異* 的 process content。

## Topology 的 5 個 sub-dimension

不同 source/target 配對對 topology 的影響不同、用 5 sub-dimension 描述具體變化：

| Sub-dimension          | 內容                                                              | 例                                          |
| ---------------------- | ----------------------------------------------------------------- | ------------------------------------------- |
| Sharding strategy      | Slot / hash / range / consistent hash / key-based                | Redis cluster slot 重分配                   |
| Partition strategy     | Declarative / range / list / hash / sub-partition                | PostgreSQL monthly → daily partition       |
| Replication topology   | Single primary / multi-master / star / hub-spoke / mesh           | Single-region → multi-region active-active |
| Region distribution    | Single / multi-AZ / multi-region / global                         | Cassandra single DC → multi-DC             |
| Co-location / locality | Locality-aware queries / row-level region pinning                 | CockroachDB region 強制 row 對應           |

任一 sub-dimension 變動就構成 topology layout 變動；多個 sub-dimension 同時變更（如「sharding strategy + region distribution 同時改」）是 *complex topology migration*、結構複雜度高。

## 為什麼 topology 不能塞進既有 5 維

Reviewer 質疑：為什麼不直接歸進 operational 或 paradigm？三個拒絕理由：

1. **Schema 不變但 topology 變**：PostgreSQL `partition strategy` 改（monthly → daily）— schema 完全相同、partition boundary 重劃；歸 Schema 維度錯位
2. **Operational stack 不變但 topology 變**：Redis cluster 加 node 重分 slot — Sentinel / monitoring / backup 不變、純粹是 slot mapping 重劃；歸 Operational 維度太寬
3. **Paradigm 不變但 topology 變**：Cassandra 從 single DC 加到 multi-DC — 同 distributed DB paradigm、co-location / replication topology 變；歸 Paradigm 維度誤導
4. **Components 不變但 topology 變**：Kafka topic re-partition（10 partitions → 100）— 同 1 個 cluster、partition count 變；歸 Components 維度錯位

Topology 是 *獨立的問題軸*、5 維 audit 漏掉時會誤判結構。

## 觸發 Type F 的情境

| 情境                             | Topology 變化                                          | 是否同 vendor       |
| -------------------------------- | ------------------------------------------------------ | ------------------- |
| Cluster re-sharding              | Slot / shard 重分配                                    | yes                 |
| Partition redesign               | Partition boundary / strategy 重劃                     | yes                 |
| Single-region → multi-region     | Region distribution + replication topology 雙變        | 多數 yes（同 vendor 加 region）|
| Multi-master rollout              | Replication topology 從 single primary 變 multi-master | yes                 |
| DynamoDB GSI / global tables    | Sharding + replication 雙變                            | yes                 |
| Kafka topic re-partitioning      | Sharding strategy 變                                   | yes                 |
| Cassandra keyspace re-balance    | Replication factor + token range 變                    | yes                 |
| MongoDB sharded cluster 加 shard | Sharding 重分布                                        | yes                 |

多數 Type F 場景是 *同 vendor* — 跟 [#127](../content-structure-by-max-diff-dimension/) Type A-E 預設「跨 vendor」對應、Type F 是 *同 vendor 內 topology 重劃*。

## 6 維 audit decision rule（updated）

擴 audit 到 6 維後、type 對映規則更新：

| 維度組合                            | 對映 type                                                 |
| ----------------------------------- | --------------------------------------------------------- |
| Schema = High（其他 Low）           | Type A phased rule translation                            |
| 全 Low                              | Type B drop-in                                            |
| Operational = High（其他 Low）      | Type C operational redesign hybrid                        |
| Components = High                   | Type D parallel streams                                   |
| Paradigm = High                     | Type E partial + 混合架構                                 |
| **Topology = High（其他 Low）**     | **Type F topology re-layout**（本卡新增）                 |
| 多軸 High                           | 按 [#127 多重歸類](../content-structure-by-max-diff-dimension/) 規則 |

主導維度判讀的優先序也擴張：Schema > Paradigm > Operational > Topology > Components。Topology 在 schema / paradigm / operational 之後、components 之前 — 因為 topology 對讀者 conceptual impact 通常比 components 拆分大、但比 schema / paradigm 小。

## Type F「Topology re-layout」結構 anatomy

從 [Redis cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/) 抽出的標準形態：

```text
1. 為什麼 re-layout（4-N 種 driver）
2. 結構 differentiator（re-layout 不是 migration）
3. Pre-layout analysis（current topology audit / hot key / slot 分佈）
4. Re-layout 機制（slot migration / partition split / shard rebalance）
5. Execution flow（per-step、含 rollback boundary）
6. 5 production 故障演練
7. Capacity / cost
8. 整合 / 下一步
```

7-9 章節、200-260 行。跟 Type B 對照、Type F 多了「topology audit」段、Step-by-step 比 Type B 細（per-step 不是 per-cutover）；跟 Type A phased 對照、Type F 不需要 schema translation / parallel run / cleanup phase（source / target 同 cluster）。

## Production 反模式

| 反模式                                   | 後果                                                       |
| ---------------------------------------- | ---------------------------------------------------------- |
| 把 re-sharding 套 Type B drop-in         | 漏掉 slot migration 機制段、cluster busy 跟 stale client cache 沒被處理 |
| 把 multi-region rollout 套 Type C        | 漏掉 locality-aware queries 跟 replication topology 設計   |
| Topology 變化只列在「容量」段             | 讀者把 topology 當 capacity 子議題、忽略 *結構* 影響        |
| 多 sub-dimension 同時變、只寫一個         | 例：Cassandra 加 DC 同時改 replication factor、只寫前者     |
| Type F 套錯場景（topology 沒變的 migration）| 強迫 phased per-step、phase 空白                          |

## 跟其他抽象層原則的關係

| 原則                                                                                            | 關係                                                                                                                              |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| [#127 Process content 結構由最大差異維度決定](../content-structure-by-max-diff-dimension/)       | 父卡 — 本卡擴 #127 的 audit 框架從 5 維到 6 維、新增 Type F；#127 的 5 type 仍適用、本卡加第 6 type                              |
| [#125 Collapse 是隱形預設](../collapse-is-implicit-default/)                                    | 同骨 — 5 維 audit 漏 topology 是「結構分類 collapse 掉 topology 軸」、是 #125 在 audit dimension surface 的子實例                |
| [#118 Standard-driven vs case-driven domain judgment](../standard-driven-vs-case-driven-domain-judgment/) | Sibling — 兩卡都是 *寫作前的 domain audit*、#118 判 case-driven vs standard-driven、本卡判 topology 是否需要 Type F           |
| [#122 Cadence 同質化是模板的隱形維度](../cadence-homogenization-in-batch-writing/)              | 同骨 — 模板有「內容欄位 / cadence」兩維度（#122）vs audit 有「6 維 / topology」兩 layer；都是「初始框架漏軸、用實證浮現補位」     |

## 判讀徵兆

| 訊號                                              | 該做的事                                                              |
| ------------------------------------------------- | --------------------------------------------------------------------- |
| 寫到一半發現 5 維 audit 都 Low、但內容跟 Type B drop-in 不一樣 | Topology 可能是漏掉的維度、補 6 維 audit                              |
| 「容量規劃」段比實作段還複雜                       | Topology 變動被誤歸 capacity、應該獨立段                              |
| Sharding / partition / region 任一變動            | 跑 topology audit、評估是否 Type F                                    |
| 同 vendor 內升級 / re-layout                       | 大概率不是 5 type、檢查 topology 是否變                              |
| Type B 結構寫不下實際內容                          | 可能是 Type F 而非 Type B                                             |
| 多個 sub-dimension 同時變                          | Complex topology migration、結構複雜度 +1 階                          |

**核心**：5 維 audit 漏 topology 是初始框架的盲點；topology 是 *資料分佈* 而非 *資料結構 / 元件 / 抽象*、需要獨立 audit 軸。Type F「Topology re-layout」對映 topology = High 的 process content、跟 Type A-E 並列；多軸 High 配對按 [#127](../content-structure-by-max-diff-dimension/) 多重歸類規則處理。
