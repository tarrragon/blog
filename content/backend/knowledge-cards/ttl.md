---
title: "TTL"
date: 2026-04-23
description: "說明資料過期時間如何影響快取新鮮度、成本與一致性"
weight: 19
---

TTL 的核心概念是「資料在指定時間後自動過期」。TTL 常用在 cache、session、presence、temporary token、匯出檔案與去重紀錄，讓系統用時間控制資料有效性。 可先對照 [Unacked Message](/backend/knowledge-cards/unacked-message/)。

## 跟其他概念的關係

TTL 是資料新鮮度與操作成本的取捨。TTL 長可以提高命中率與降低下游壓力；TTL 短可以降低過期資料風險，但會增加重新載入與下游查詢。 可先對照 [Unacked Message](/backend/knowledge-cards/unacked-message/)。

## 可觀察訊號與例子

系統需要調整 TTL 的訊號是資料過期造成錯誤體驗，或 cache miss 造成下游壓力。商品價格 cache 的 TTL 通常短於熱門文章榜；presence 狀態需要跟心跳頻率一起設計。

## 判斷條件與後果

TTL 的長度由資料過期之後還被讀到的代價決定。讀到舊值會造成錯誤的資料（商品價格）TTL 短，或在寫入時主動失效、改用版本鍵，代價是更多 cache miss 與下游查詢；舊一陣子無妨的資料（熱門文章榜）TTL 長，換到較高的命中率。全部資料共用一個 TTL 時，這個值對價格太長、對榜單太短，兩種代價同時付。重建成本高的 key 同時過期時，下游在同一刻收到大量重建查詢，背景刷新把重建提前到過期之前。所以 runbook 查得到 key 剩餘時間、命中率、miss rate 與重建成本，才分得出問題出在哪一級資料的 TTL。
