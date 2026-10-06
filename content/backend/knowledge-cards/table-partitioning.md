---
title: "Table Partitioning"
date: 2026-05-22
description: "說明單一資料庫內如何把大表拆成多個分區，並由查詢規劃器只掃相關片段"
weight: 334
---

Table Partitioning 的核心概念是在單一資料庫內，把一張大表按 range、list 或 hash 拆成 parent 表加多個 child 分區，讓查詢規劃器只掃描相關分區。它讓大表的查詢、維護與資料清理可以按分區進行，代價是分區鍵要選得讓多數查詢都帶得到。它和跨節點的 [Database Sharding](/backend/knowledge-cards/database-sharding/) 不同層 — table partitioning 仍在同一個資料庫內，[Hot Partition](/backend/knowledge-cards/hot-partition/) 是它失衡時的訊號。

## 概念位置

Table Partitioning 位在單機資料庫的表結構層。它和 messaging 的 [Partition](/backend/knowledge-cards/partition/) 名稱相近但語意不同：[Partition](/backend/knowledge-cards/partition/) 切的是事件流、處理並行與順序；table partitioning 切的是一張資料庫表、處理查詢範圍與資料生命週期。要跨節點水平擴展時，才接到 [Database Sharding](/backend/knowledge-cards/database-sharding/)。

## 可觀察訊號與例子

適合 table partitioning 的訊號是一張表很大、但查詢通常只碰最近一段時間或某個範圍，例如時序事件表、訂單表。time-based 分區讓「清掉 90 天前資料」變成卸載一個分區，而不是大範圍 DELETE。要特別注意的訊號是查詢沒帶分區鍵 — 規劃器無法做 partition pruning，查詢會退化成掃描全部分區。

另一個要先查的是表上的唯一約束。PostgreSQL 的唯一約束由各分區自己的索引執行，所以必須包含分區鍵：依 `created_at` 分區的表建 `UNIQUE (code)` 會回 `unique constraint on partitioned table must include all partitioning columns`，只能寫成 `UNIQUE (code, created_at)`，不同時間的兩列就可以有相同的 `code`。靠某一欄的唯一約束防止重複的表（例如短網址的短碼）依時間分區時，不能只靠分區表本身的唯一約束：做法是依那一欄的 hash 分區，或另建一張不分區的登記表（那一欄當主鍵）擔任唯一的仲裁者，代價是每次寫入多寫一張表，而登記表本身也不刪除、一直變大，見 [1.19 資料表長期成長的成本](/backend/01-database/table-growth-query-cost/)〈依時間分割與唯一約束〉。

## 設計責任

設計時要讓分區鍵和最常見的查詢條件對齊，並規劃分區的建立與卸載流程。time-based 分區要有自動建立未來分區、自動卸載過期分區的機制，並接回 [Retention](/backend/knowledge-cards/retention/)。observability 要看查詢是否命中 pruning，以及 default 分區是否意外累積資料。
