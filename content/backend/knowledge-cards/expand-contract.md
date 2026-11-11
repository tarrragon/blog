---
title: "Expand / Contract"
date: 2026-04-24
description: "說明先擴充相容面、再收斂舊路徑的遷移做法"
weight: 140
---

Expand / Contract 的核心概念是「先把新結構或新路徑加進去，確認相容後，再移除舊結構或舊路徑」。 可先對照 [Exponential Backoff](/backend/knowledge-cards/exponential-backoff/)。

## 跟其他概念的關係

Expand / Contract 位在 schema migration、online migration、deployment 與 release gate 之間。它是降低變更風險的遷移順序，不是單一工具。 可先對照 [Exponential Backoff](/backend/knowledge-cards/exponential-backoff/)。

## 可觀察訊號

系統需要 expand / contract 的訊號是：

- 舊版本與新版本會同時存在
- 新功能需要先讓舊程式不壞掉
- 移除舊欄位或舊路徑前，必須先讓新版本穩定接上
- migration 不能一次做完

## 接近真實網路服務的例子

新增欄位時先擴表、補預設值、讓新舊版本都能讀寫，再等舊版本完全退出後移除舊欄位；換搜尋索引時先讓新寫入同步到兩邊，等驗證完成後再收斂舊索引。這些都屬於 expand / contract。

## 判斷條件與後果

Expand / Contract 的每一步是否還有回頭路，看收斂條件與相容條件是否寫清楚。擴張階段只加新結構、不動舊結構，這段期間出錯可以直接退回，因為舊版本照常讀寫舊結構。沒有相容條件時，判斷不了新舊版本是否確實能同時讀寫，擴張完成也不代表可以進到下一步。沒有收斂條件、在舊版本還沒完全退出時就移除舊欄位，仍在執行的舊版本讀寫失敗，而且這一步之後退回舊版本也讀不到資料，回頭路就在這一步消失。沒有驗證方式時，收斂條件是否成立只能憑印象判斷；沒有回復方式時，任何一步出錯都要當場決定怎麼退。
