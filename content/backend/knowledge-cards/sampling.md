---
title: "Sampling"
date: 2026-04-23
description: "說明觀測資料如何抽樣以控制成本並保留診斷能力"
weight: 104
---

Sampling 的核心概念是「只保留部分觀測資料」。高流量系統若收集所有 log、trace 或事件，成本與查詢壓力可能快速上升；sampling 用代表性資料保留診斷能力。 可先對照 [Schema Migration](/backend/knowledge-cards/schema-migration/)。

## 跟其他概念的關係

Sampling 是觀測成本控制工具。它可以是固定比例、依錯誤保留、依延遲保留、依 tenant 保留或 adaptive sampling。 可先對照 [Schema Migration](/backend/knowledge-cards/schema-migration/)。

## 可觀察訊號與例子

系統需要 sampling 的訊號是 trace 或 log 成本隨流量快速成長。Checkout 成功 request 可低比例採樣，錯誤與高延遲 request 則應提高保留率。

## 判斷條件與後果

採樣規則的代價由被丟棄的那些資料決定：事後要用到的資料被丟掉時，就再也拿不回來。固定比例採樣時，錯誤與高延遲的 request 跟成功的 request 以同樣比例被丟棄，事故時要找的那幾筆可能不在樣本裡，所以錯誤與高延遲的 request 用較高的保留率。採樣後的資料看得出趨勢，計數與比例卻要換算回採樣率才對得上實際流量，查詢的人不知道採樣規則時會低估量級，或把採樣造成的偏差讀成真實的分布。audit 或法規要求完整保留的資料被採樣時，丟掉的紀錄事後無法補回。事故期間調高保留率留得下更多診斷資料，代價是成本在事故期間跟著上升。

監控 SDK 中靜態取樣和動態取樣（背壓觸發）的具體實作見 [監控知識卡：Sampling](/devops/monitoring/knowledge-cards/sampling/)。
