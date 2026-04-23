---
title: "Sampling"
date: 2026-04-23
description: "說明觀測資料如何抽樣以控制成本並保留診斷能力"
weight: 103
---

Sampling 的核心概念是「只保留部分觀測資料」。高流量系統若收集所有 log、trace 或事件，成本與查詢壓力可能快速上升；sampling 用代表性資料保留診斷能力。

## 概念位置

Sampling 是觀測成本控制工具。它可以是固定比例、依錯誤保留、依延遲保留、依 tenant 保留或 adaptive sampling。

## 可觀察訊號與例子

系統需要 sampling 的訊號是 trace 或 log 成本隨流量快速成長。Checkout 成功 request 可低比例採樣，錯誤與高延遲 request 則應提高保留率。

## 設計責任

Sampling 要定義保留規則、偏差、查詢限制與事故期間調整方式。抽樣後的資料適合診斷趨勢，但某些 audit 或法規資料需要完整保留。
