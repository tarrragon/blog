---
title: "MySQL HeatWave OLAP Add-on"
date: 2026-05-22
description: "MySQL HeatWave、OLTP + OLAP hybrid、query offload、cost model、data freshness 與 warehouse 邊界"
tags: ["backend", "database", "mysql", "heatwave", "olap"]
---

MySQL HeatWave OLAP add-on 的核心責任是判斷 OLTP database 內建 analytics 加速何時比拆出 OLAP 系統更划算。HeatWave 這類 add-on 的價值是降低資料搬運與平台數量，但它也把 analytics workload、成本、freshness 與 query governance 帶回 MySQL 生態。

本文的判讀錨點是：OLAP add-on 做的是把分析查詢從 OLTP 路徑[卸載](/backend/knowledge-cards/olap-offload/)到專用引擎，解決特定 analytics workload 的 proximity 問題，而非 data warehouse 的完整替代。選型要看資料量、query pattern、freshness、concurrency、成本與團隊能力。

官方文件路由的核心責任是固定 HeatWave claim。實作前先查 [MySQL HeatWave User Guide](https://dev.mysql.com/doc/heatwave/en/index.html)；本文最後檢查日是 2026-05-22。

## Workload Fit

Workload fit 的核心責任是找出 HeatWave 類 OLAP add-on 的合理位置。

| 情境                     | 適合原因                                   |
| ------------------------ | ------------------------------------------ |
| MySQL 資料為主要分析來源 | 減少 ETL / CDC 複雜度                      |
| Dashboard 需要較新資料   | freshness 比 warehouse batch 更重要        |
| 分析 query 可被明確界定  | 可控 workload 便於成本與容量管理           |
| Team 想降低平台數        | MySQL 生態內完成 transactional + analytics |

適合的 workload 通常是「MySQL 內資料、分析需求清楚、資料量可控」。若需要跨多資料源、複雜 semantic layer、長期資料湖與 ML feature store，warehouse / lakehouse 仍然更合適。

## Boundary with OLTP

Boundary with OLTP 的核心責任是避免 analytics 壓力影響交易服務。OLTP query 要穩定、低延遲、可預測；OLAP query 常是大掃描、大聚合、長時間。

| 審查面        | 問題                                 |
| ------------- | ------------------------------------ |
| Resource      | OLAP 是否隔離 CPU / memory / storage |
| Freshness     | analytic data 和 source 差多久       |
| Query control | 誰能跑 heavy query、如何限流         |
| Cost          | add-on node、storage、egress         |
| Incident      | OLAP 故障是否影響 OLTP               |

OLAP add-on 要有 query admission policy。任何人都能跑任意分析 SQL，會把成本與穩定性風險放大。

## Freshness and Evidence

Freshness and evidence 的核心責任是定義分析結果多新。Dashboard、營運報表、風控、推薦特徵對 freshness 的要求不同。

| Freshness 等級 | 適合情境                    |
| -------------- | --------------------------- |
| 秒到分鐘       | operational dashboard、風控 |
| 小時           | 商業報表、營運分析          |
| 天             | 財務結算、長期趨勢          |

Freshness 要被量測。Runbook 要記錄 last load / sync time、query latency、failed refresh、data gap 與 fallback dashboard。

## Cost Model

Cost model 的核心責任是比較 add-on 和獨立 OLAP 系統。

| 成本項        | HeatWave 類 add-on | 獨立 warehouse                   |
| ------------- | ------------------ | -------------------------------- |
| Data movement | 較少 ETL           | 需要 CDC / batch pipeline        |
| Compute       | add-on capacity    | warehouse compute / auto scaling |
| Storage       | MySQL ecosystem 內 | separate storage                 |
| Governance    | MySQL 權限延伸     | data platform governance         |
| Lock-in       | provider-specific  | warehouse-specific               |

成本比較要包含人力。少一條 ETL pipeline 可能節省大量維運；但 provider-specific query 與管理模型也會增加 exit cost。

## No-Go Conditions

No-go conditions 的核心責任是避免把 OLAP add-on 推到資料平台的位置。

| 訊號                                    | 建議路由                     |
| --------------------------------------- | ---------------------------- |
| 分析跨多來源                            | warehouse / lakehouse        |
| 查詢需要 semantic layer / BI governance | dedicated analytics platform |
| 長期歷史資料遠大於 OLTP                 | warehouse / object storage   |
| ML feature / offline training           | feature store / lakehouse    |
| 成本需要獨立 chargeback                 | separate OLAP environment    |

HeatWave 類能力適合 MySQL-centered analytics。當分析需求超出單一 OLTP source，資料平台會比 add-on 更清楚。

## 下一步路由

HeatWave OLAP add-on 完成後，MySQL query 基礎讀 [Query Optimization](../query-optimization/)；資料平台邊界讀 backend analytics / warehouse 章節；若要保留 MySQL OLTP 並外接 CDC，讀 [Binlog CDC](../binlog-cdc/)。
