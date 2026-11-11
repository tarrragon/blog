---
title: "Data Bag"
tags: ["資料袋", "Data Bag", "貧血模型", "Anemic Model"]
date: 2026-07-10
description: "判斷一個型別要不要投資領域模型設計時使用。資料袋是欄位組合全部合法、沒有不變式要守的型別——DTO、API model、UI state 都屬於這一類。"
weight: 5
aliases: ["/ddd/knowledge-cards/data-bag/"]
---

資料袋承擔資料的搬運與呈現：DTO、API model、UI state、設定物件。它的特徵是任何欄位組合都是合法狀態——修改其中一欄、其餘欄位的意義照舊成立。因為組合全部合法、逐欄位覆寫工具（copyWith、setter、builder）在資料袋上語意清晰、沒有代價。DDD 社群常用「貧血模型（anemic model）」指沒有行為的資料容器——語意接近、但資料袋是正確形態而非缺陷，判定依[不變式](/software-design/ddd/knowledge-cards/invariant/)有無而定。

## 跟其他概念的關係

資料袋跟領域模型是型別類別的兩端。判斷標準是「有沒有不允許任意組合的欄位」——有就是領域模型、沒有就是資料袋。資料袋裡照樣可以放語意封閉的 [value object](/software-design/ddd/knowledge-cards/value-object/)（如 Money）；容器的類別判定跟欄位的封閉性是正交的兩條軸。資料袋可以隨業務演進升級成領域模型——升級時機由演化訊號決定、而非預測。

## 可觀察訊號

型別的每個欄位都可以獨立修改且不影響其餘欄位的語意——資料袋。型別上出現「請用某方法修改」的註解但欄位仍全部 public 可寫——判定可能錯了、讀 [資料袋與領域模型](/software-design/ddd/data-bag-vs-domain-model/) 重新檢視。

## 判斷條件與後果

一個型別歸資料袋還是領域模型，看它是否有不允許任意組合的欄位。沒有這種欄位時，每一種欄位組合都是合法狀態，工廠、私有建構子與變更方法沒有規則可以檢查，加上去只多出一層 boilerplate，每改一個欄位都要多經過一個方法。有這種欄位時，public 可寫的欄位與 copyWith 讓呼叫端組得出業務上不該存在的狀態，那條規則要靠領域模型的建構路徑強制，這個型別就是領域模型。完整判斷標準見 [資料袋與領域模型](/software-design/ddd/data-bag-vs-domain-model/)。
