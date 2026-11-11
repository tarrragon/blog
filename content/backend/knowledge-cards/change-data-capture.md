---
title: "Change Data Capture"
date: 2026-04-23
description: "說明資料變更如何被捕捉並傳送到其他系統"
weight: 80
---

Change Data Capture 的核心概念是「捕捉 [database](/backend/knowledge-cards/database/) 變更並把變更傳送給其他系統」。CDC 可以用於同步搜尋索引、資料倉儲、cache、event stream 或新舊系統 [migration](/backend/knowledge-cards/migration/)。

## 跟其他概念的關係

CDC 是資料同步與事件化的橋樑。它通常從 database log、trigger、polling 或平台工具取得變更，再轉成可由 [consumer](/backend/knowledge-cards/consumer/) 處理的事件流。

## 可觀察訊號與例子

系統需要 CDC 的訊號是正式資料更新後，多個衍生系統都需要同步。會員資料變更後，搜尋、推薦、報表與客服系統可能都需要收到更新。

## 判斷條件與後果

CDC 把資料庫變更送進衍生系統，下面每一項沒有處理時，衍生系統以不同的方式跟正式資料分岔：

- **順序**：同一筆資料的兩次更新以相反順序送達時，衍生系統留下的是較舊的值。
- **[duplicate delivery](/backend/knowledge-cards/duplicate-delivery/)**：同一筆變更送達兩次而 consumer 沒有去重時，累加型的衍生資料（報表的計數）會多算。
- **schema 變更**：來源表加欄或改型別而事件格式沒有跟著版本化時，consumer 解析失敗，同步停下。
- **[backfill](/backend/knowledge-cards/backfill/)**：新接上的衍生系統只收得到接上之後的變更，既有資料不會自己出現。
- **[replay runbook](/backend/knowledge-cards/replay-runbook/)**：衍生系統的資料損壞時，沒有重放程序就只能整份重建。
- **[data masking](/backend/knowledge-cards/data-masking/)**：變更事件帶著原始的個資欄位送出時，每一個衍生系統都多保存了一份個資。

lag 由兩段組成：capture lag 是資料庫寫入到 CDC 讀到變更的延遲，delivery lag 是讀到之後送達 consumer 的延遲，兩段分開量才分辨得出慢在讀 log 還是送事件。最舊未同步資料的時間反映衍生系統目前落後正式資料多久，錯誤率反映有多少變更沒有送到。
