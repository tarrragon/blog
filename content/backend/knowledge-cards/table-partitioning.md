---
title: "Table Partitioning"
date: 2026-05-22
description: "說明單一資料庫內如何把大表拆成多個分區，並由查詢規劃器只掃相關片段"
weight: 333
---

Table Partitioning 的核心概念是在單一資料庫內，把一張大表按 range、list 或 hash 拆成 parent 表加多個 child 分區，讓查詢規劃器只掃描相關分區。它讓大表的查詢、維護與資料清理可以按分區進行，代價是分區鍵要選得讓多數查詢都帶得到。它和跨節點的 [Database Sharding](/backend/knowledge-cards/database-sharding/) 不同層 — table partitioning 仍在同一個資料庫內，[Hot Partition](/backend/knowledge-cards/hot-partition/) 是它失衡時的訊號。

## 概念位置

Table Partitioning 位在單機資料庫的表結構層。它和 messaging 的 [Partition](/backend/knowledge-cards/partition/) 名稱相近但語意不同：[Partition](/backend/knowledge-cards/partition/) 切的是事件流、處理並行與順序；table partitioning 切的是一張資料庫表、處理查詢範圍與資料生命週期。要跨節點水平擴展時，才接到 [Database Sharding](/backend/knowledge-cards/database-sharding/)。

## 可觀察訊號與例子

適合 table partitioning 的訊號是一張表很大、但查詢通常只碰最近一段時間或某個範圍，例如時序事件表、訂單表。time-based 分區讓「清掉 90 天前資料」變成卸載一個分區，而不是大範圍 DELETE。要特別注意的訊號是查詢沒帶分區鍵 — 規劃器無法做 partition pruning，查詢會退化成掃描全部分區。

## 設計責任

設計時要讓分區鍵和最常見的查詢條件對齊，並規劃分區的建立與卸載流程。time-based 分區要有自動建立未來分區、自動卸載過期分區的機制，並接回 [Retention](/backend/knowledge-cards/retention/)。observability 要看查詢是否命中 pruning，以及 default 分區是否意外累積資料。
