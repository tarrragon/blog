---
title: "Write-Through Cache"
date: 2026-04-23
description: "說明寫入時同步更新快取與正式來源的策略"
weight: 94
---

Write-through cache 的核心概念是「寫入正式來源時同步更新快取」。它讓後續讀取更容易命中新資料，降低讀取路徑遇到舊資料的機率。 可先對照 [Write-Behind Cache](/backend/knowledge-cards/write-behind-cache/)。

## 跟其他概念的關係

Write-through 是寫入路徑上的快取策略。它適合更新頻率可控、讀取頻繁且資料新鮮度重要的場景；寫入延遲會因同步更新快取而增加。 可先對照 [Write-Behind Cache](/backend/knowledge-cards/write-behind-cache/)。

## 可觀察訊號與例子

系統需要 write-through 的訊號是寫入後立刻讀取很常見。使用者更新個人設定後，下一個 request 通常會立刻讀取設定摘要；同步更新快取可以降低讀到舊資料的機率。

## 判斷條件與後果

Write-through 每次寫入更新兩個位置，正式來源寫入成功而快取寫入失敗時，快取留著舊值，之後的讀取命中舊資料，直到快取過期或下一次寫入。這個分支有幾種處置，各自付出不同的代價：回報失敗讓使用者重試，而這時正式來源已經寫入；刪除快取讓下一次讀取 miss 後重建，代價是一次較慢的讀取；延後修復保留一段讀到舊值的窗口。這個分支沒有定義時，實際行為取決於錯誤處理程式碼當初的寫法，讀到舊值的窗口長度無從預測。
