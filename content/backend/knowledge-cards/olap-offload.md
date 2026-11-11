---
title: "OLAP Offload"
date: 2026-05-22
description: "說明如何把分析型查詢從 OLTP 主庫卸載，以保護線上交易效能"
weight: 337
---

OLAP Offload 的核心概念是把分析型查詢從線上交易（OLTP）主庫移開，讓重量級的彙總、掃描與報表查詢不影響線上讀寫。它讓交易效能和分析需求各自有容量，代價是要決定分析資料放哪、以及它和主庫之間的新鮮度差。它常透過 [Change Data Capture](/backend/knowledge-cards/change-data-capture/) 把資料送到分析側，分析側本身則是一種 [Read Model](/backend/knowledge-cards/read-model/)。

## 跟其他概念的關係

OLAP Offload 位在 OLTP 與分析系統之間的決策點。OLTP workload 是大量短交易，OLAP workload 是少量長查詢、掃大量資料；兩者放同一個資料庫會互相競爭 buffer、CPU 與 IO。卸載的路徑有 read replica、引擎內建的分析加速器，或用 [Change Data Capture](/backend/knowledge-cards/change-data-capture/) 同步到資料倉儲。

## 可觀察訊號與例子

需要 OLAP offload 的訊號是報表或分析查詢一跑，線上交易的延遲就升高。輕量做法是把分析查詢導到 read replica；查詢更重、要跨多來源或讀長期歷史資料時，要把資料同步到專門的分析系統。需要評估的取捨是資料新鮮度 — replica 與倉儲都有同步延遲，分析結果不是即時的。

## 判斷條件與後果

分析 workload 的形狀（頻率、掃描量、並發）決定哪一條卸載路徑有效。查詢輕、頻率低時，導到 read replica 就讓主庫的線上交易不再受報表影響，不必另外維運一套分析系統；查詢要跨多個來源或讀長期歷史資料時，replica 仍是同一種 OLTP 引擎、只保存同一份資料，重量級掃描在那裡一樣慢，也讀不到其他來源，這類 workload 要同步到專門的分析系統。分析側可接受的資料延遲沒有寫進 SLO 時，replica 或倉儲的同步延遲變大，報表用上過期的資料而沒有任何告警。OLTP 與 OLAP 的資源用量混在同一組指標裡時，卸載之後看不出主庫的交易延遲是否不再隨報表查詢上升。
