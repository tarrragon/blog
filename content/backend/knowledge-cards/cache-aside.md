---
title: "Cache Aside"
date: 2026-04-23
description: "說明 application 如何在讀取時自行管理快取與正式資料來源"
weight: 21
---

Cache aside 的核心概念是「application 先查快取，miss 時查正式來源，再把結果寫回快取」。這個模式讓 application 控制讀取流程、key 設計、TTL 與失效策略。 可先對照 [Cache Hit / Miss](/backend/knowledge-cards/cache-hit-miss/)。

## 跟其他概念的關係

Cache aside 適合可重建的讀取資料。商品詳情、權限摘要、設定檔與熱門內容常用這種方式加速讀取；正式資料仍然在資料庫或下游服務，快取只是副本。 可先對照 [Cache Hit / Miss](/backend/knowledge-cards/cache-hit-miss/)。

## 可觀察訊號與例子

系統適合 cache aside 的訊號是讀多寫少、資料可重建、讀取成本高。商品頁查詢頻繁時，cache aside 可以降低資料庫壓力；結帳確認價格時仍應回到正式來源或使用更嚴格一致性策略。

## 判斷條件與後果

Cache aside 把讀取流程交給 application，每一個分支的行為都由 application 的程式決定，程式沒寫到的分支在出錯當下才顯現。正式來源更新後沒有失效對應的 key 時，讀取持續拿到舊值，直到 TTL 到期；快取讀取或寫回失敗時沒有 fallback，快取服務一斷線，讀取就跟著回錯誤，即使正式來源還能服務；熱門 key 過期時沒有防止 [stampede](/backend/knowledge-cards/cache-stampede/) 的機制，所有 miss 同時回源，正式來源的負載瞬間升高。測試只覆蓋 hit 與 miss 時，正式來源失敗、快取寫入失敗與過期資料這幾個分支在上線前都沒有被執行過。
