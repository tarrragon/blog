---
title: "Replication Lag"
date: 2026-04-23
description: "說明資料副本落後正式來源多久，以及它如何影響讀取正確性"
weight: 81
---

Replication lag 的核心概念是「資料副本落後正式來源的時間或位置差距」。Replica、搜尋索引、read model、cache 與資料倉儲都可能有 lag。 可先對照 [Database](/backend/knowledge-cards/database/)。

## 跟其他概念的關係

Replication lag 是資料一致性與讀取路徑的風險指標。讀 replica 可以降低正式 [database](/backend/knowledge-cards/database/) 壓力，但 lag 會讓剛寫入的資料在副本上暫時看不到；哪些查詢被送到副本，由應用程式、ORM 或代理的路由規則決定，見 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/)〈讀寫分離與多個資料庫：連線的路由由哪一層決定〉。

## 可觀察訊號與例子

系統需要 replication lag 觀測的訊號是使用者寫入後立刻讀取。使用者更新地址後，客服後台若讀 replica，可能短時間內仍看到舊地址；付款與出貨流程則應讀 [source of truth](/backend/knowledge-cards/source-of-truth/)。

## 判斷條件與後果

同一份副本上的 lag，對不同讀取路徑的後果不同。能容忍舊資料的路徑（客服後台顯示地址）讀副本，代價是使用者剛寫入的資料在 lag 期間看不到；需要強一致的路徑（付款、出貨）讀到舊狀態時會照舊資料做決定，所以讀 source of truth。可接受延遲沒有定義時，lag 變大也沒有門檻判斷何時把讀取切回 source of truth 或啟用 [fallback](/backend/knowledge-cards/fallback/)。觀測只看整體平均時，看不出是哪一個 replica、index 或 [stream pipeline](/backend/knowledge-cards/stream-pipeline/) 落後，所以 lag 按副本分開看，並看最舊未同步的資料停在什麼時間。
