---
title: "Bucket"
date: 2026-04-23
description: "說明 histogram 分桶如何決定觀測解析度與成本"
weight: 100
---

Bucket 的核心概念是「histogram 中用來統計觀測值範圍的界線」。每個 bucket 代表小於等於某個上限的觀測值累積數。 可先對照 [Buffer](/backend/knowledge-cards/buffer/)。

## 跟其他概念的關係

Bucket 是 histogram 可用性的關鍵。Bucket 應圍繞 SLO 門檻與常見延遲分布設計；錯誤 bucket 會讓 dashboard 看起來有資料，卻回答不了服務是否達標。 可先對照 [Buffer](/backend/knowledge-cards/buffer/)。

## 可觀察訊號與例子

系統需要調整 bucket 的訊號是 p95 / p99 查詢不穩，或 SLO 門檻附近缺乏解析度。若 checkout SLO 是 300ms，bucket 應在 100ms、200ms、300ms、500ms 附近提供足夠區分。

## 判斷條件與後果

Bucket 的位置決定 histogram 在哪個延遲範圍有解析度。SLO 門檻附近沒有 bucket 時（checkout SLO 是 300ms，而 bucket 只設在 100ms 與 1s），p99 落在 300ms 的哪一邊算不出來，dashboard 有資料，卻判斷不了服務是否達標。每多一個 bucket，每組 label 就多一條時間序列，bucket 數量乘上 label 組合就是 histogram 的 cardinality，儲存與查詢成本隨之增加。所以 bucket 集中在 SLO 門檻與常見延遲附近，不同 endpoint 或任務類型的延遲分布相差很遠時，才各自定義一組 bucket。
