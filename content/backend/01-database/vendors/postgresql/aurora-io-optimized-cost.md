---
title: "Aurora PostgreSQL I/O-Optimized Cost"
date: 2026-05-22
description: "Aurora PostgreSQL Standard 與 I/O-Optimized 的成本模型、I/O 壓力、workload 判斷、遷移與回退條件"
tags: ["backend", "database", "postgresql", "aurora", "cost"]
---

Aurora PostgreSQL I/O-Optimized cost 的核心責任是把 Aurora storage configuration 從定價選項轉成 workload 決策。AWS 官方文件將 Aurora cluster storage configuration 分成 Aurora Standard 與 Aurora I/O-Optimized；前者適合一般 I/O 分布，後者針對 I/O 密集 workload 提供不同成本結構。

本文的判讀錨點是：I/O-Optimized 是成本與 workload profile 決策，而非效能保證。要看的是 read / write I/O charge、storage、instance、backup、replica、query pattern、maintenance 與未來成長。

官方文件路由的核心責任是固定時間敏感 claim。實作前先查 [Aurora storage configurations](https://docs.aws.amazon.com/en_us/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.StorageReliability.html) 與 [supported engines / regions](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.Aurora_Fea_Regions_DB-eng.Feature.storage-type.html)；本文最後檢查日是 2026-05-22。

## Cost Model

Cost model 的核心責任是拆解 Aurora bill 的來源。Aurora 成本通常包含 instance、storage、I/O request、backup、replica、data transfer 與 support / operation。

| 成本項            | Standard 判讀                   | I/O-Optimized 判讀                       |
| ----------------- | ------------------------------- | ---------------------------------------- |
| Instance          | 仍依 instance / capacity 計費   | 仍依 instance / capacity 計費            |
| Storage           | 依儲存使用量                    | 依 I/O-Optimized storage 設定            |
| I/O requests      | I/O 成本可成為主要變動項        | I/O charge 結構改變，適合高 I/O workload |
| Backup / snapshot | 依保留與使用量                  | 仍需納入總成本                           |
| Data transfer     | 跨 AZ / region / service 需審查 | 仍需納入總成本                           |

成本評估要用真實帳單和 CloudWatch 指標。只用平均 QPS 估算會漏掉 batch job、vacuum、index build、replica、backfill 與報表查詢帶來的 I/O 尖峰。

## Workload Signals

Workload signals 的核心責任是找出 I/O 是否為主要成本與瓶頸。

| 訊號                      | 意義                                  |
| ------------------------- | ------------------------------------- |
| I/O request 成本占比高    | Standard 可能受 I/O charge 影響大     |
| Buffer cache hit ratio 低 | 工作集超過 memory 或 query 掃描過重   |
| 大量 random read / write  | storage I/O 壓力明顯                  |
| ETL / backfill 經常跑     | 短期 I/O spike 可能影響帳單與 latency |
| Index / query 設計已優化  | 成本切換更能反映真實 workload         |

先做 query 與 index review。若 I/O 來自缺 index、全表掃描、過度 eager loading 或不必要 backfill，直接切 I/O-Optimized 只會把浪費制度化。

## Evaluation Process

Evaluation process 的核心責任是讓切換決策可回溯。

1. 收集 30 到 90 天成本：instance、storage、I/O、backup、transfer。
2. 收集 workload 指標：read/write IOPS、cache hit、slow query、top SQL。
3. 標記特殊事件：migration、backfill、incident、seasonality。
4. 建立 Standard vs I/O-Optimized 成本試算。
5. 在 staging / canary 確認 application behavior。
6. 設定切換後 7 / 14 / 30 天回顧點。

試算要包含季節性。月初結算、年度促銷、批次報表與資料重整都可能讓 I/O profile 和普通週不同。

## Migration and Rollback

Migration and rollback 的核心責任是把 storage configuration change 放進變更流程。Aurora storage configuration 是 cluster-level decision，應先確認支援區域、engine version、切換限制、維護窗口與回退條件。

| Step          | Evidence                                     |
| ------------- | -------------------------------------------- |
| Pre-check     | engine version、region support、current bill |
| Cost baseline | 近期成本與 I/O 指標                          |
| Change window | application traffic、maintenance             |
| Post-check    | latency、I/O、error、bill trend              |
| Review        | 7 / 14 / 30 天成本與效能                     |

Rollback 條件要明確。若切換後成本下降未達目標、latency 沒改善、或 workload profile 改變，應重新評估 Standard 與 query optimization。

## Anti-Patterns

Anti-pattern 的核心責任是避免把計費選項當成效能調校。

| 反模式                 | 風險                        | 修正方向                     |
| ---------------------- | --------------------------- | ---------------------------- |
| 未看 top SQL 直接切換  | 把壞 query 的成本包進新方案 | 先做 query / index review    |
| 用單日帳單推估全年     | 忽略 seasonality            | 至少看完整業務週期           |
| 忽略 backup / transfer | 總成本估算失真              | 全 bill component 一起比較   |
| 切換後無 review        | 成本漂移無 owner            | 設定 7 / 14 / 30 天 tripwire |

I/O-Optimized 的價值來自成本結構對齊 workload。它應該是 FinOps 與 database operation 的共同決策。

## 下一步路由

Aurora I/O-Optimized cost 完成後，Aurora 遷移讀 [PostgreSQL to Aurora Migration](../migrate-to-aurora/)；query 成本讀 [Query Optimization](../query-optimization/)；capacity 與瓶頸判斷讀 [Bottleneck Localization](/backend/09-performance-capacity/bottleneck-localization/)。
