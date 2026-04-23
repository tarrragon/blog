---
title: "Replication Lag"
date: 2026-04-23
description: "說明資料副本落後正式來源多久，以及它如何影響讀取正確性"
weight: 80
---

Replication lag 的核心概念是「資料副本落後正式來源的時間或位置差距」。Replica、搜尋索引、read model、cache 與資料倉儲都可能有 lag。

## 概念位置

Replication lag 是資料一致性與讀取路徑的風險指標。讀 replica 可以降低正式 [database](../database/) 壓力，但 lag 會讓剛寫入的資料在副本上暫時看不到。

## 可觀察訊號與例子

系統需要 replication lag 觀測的訊號是使用者寫入後立刻讀取。使用者更新地址後，客服後台若讀 replica，可能短時間內仍看到舊地址；付款與出貨流程則應讀 [source of truth](../source-of-truth/)。

## 設計責任

Lag 設計要定義可接受延遲、讀取路徑、強一致需求與 [fallback](../fallback/)。觀測上要能看每個 replica、index 或 [stream pipeline](../stream-pipeline/) 的 lag 與最舊未同步資料。
