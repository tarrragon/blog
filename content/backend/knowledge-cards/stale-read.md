---
title: "Stale Read"
date: 2026-05-13
description: "讀取到落後於最新寫入版本的舊資料"
weight: 256
---

Stale read 的核心概念是「讀到的資料不是最新提交狀態」。它的責任是揭露一致性延遲在讀路徑的實際影響，常用於 [eventual-consistency](/backend/knowledge-cards/eventual-consistency/) 與 [bounded-staleness](/backend/knowledge-cards/bounded-staleness/) 的風險判讀。

## 概念位置

Stale read 常出現在 [replication-lag](/backend/knowledge-cards/replication-lag/) 拉開的 read replica、跨區同步、[cache-aside](/backend/knowledge-cards/cache-aside/) 與異步 [projection](/backend/knowledge-cards/projection/)。它需要先定義可接受窗口與超標處置、是否構成錯誤取決於業務容忍度；判讀粒度跟 [consistency-level](/backend/knowledge-cards/consistency-level/) 跟 [bounded-staleness](/backend/knowledge-cards/bounded-staleness/) 對齊。

## 可觀察訊號與例子

需要 stale read 判讀的訊號是「使用者剛完成操作，下一次查詢卻看不到結果」。例如付款成功後，訂單狀態頁仍顯示未付款，通常是讀路徑落後寫入收斂。

## 設計責任

處理 stale read 要同時提供技術與產品策略：技術上可用讀回主庫、版本比對或延遲容忍設計；產品上要明確呈現狀態轉換，避免把短暫收斂延遲誤解成資料錯誤。
