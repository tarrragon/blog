---
title: "TTL"
date: 2026-04-23
description: "說明資料過期時間如何影響快取新鮮度、成本與一致性"
weight: 18
---


TTL 的核心概念是「資料在指定時間後自動過期」。TTL 常用在 cache、session、presence、temporary token、匯出檔案與去重紀錄，讓系統用時間控制資料有效性。 可先對照 [Unacked Message](/backend/knowledge-cards/unacked-message/)。

## 概念位置

TTL 是資料新鮮度與操作成本的取捨。TTL 長可以提高命中率與降低下游壓力；TTL 短可以降低過期資料風險，但會增加重新載入與下游查詢。 可先對照 [Unacked Message](/backend/knowledge-cards/unacked-message/)。

## 可觀察訊號與例子

系統需要調整 TTL 的訊號是資料過期造成錯誤體驗，或 cache miss 造成下游壓力。商品價格 cache 的 TTL 通常短於熱門文章榜；presence 狀態需要跟心跳頻率一起設計。

## 設計責任

TTL 要依資料語意分級，並搭配主動失效、版本鍵或背景刷新。Runbook 應能查 key 剩餘時間、命中率、miss rate 與過期後重建成本。
