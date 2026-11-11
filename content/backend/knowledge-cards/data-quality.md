---
title: "Data Quality"
date: 2026-05-11
description: "說明證據欄位如何標示 completeness、freshness、sampling 與資料限制"
weight: 321
tags: ["backend", "knowledge-card", "observability", "incident-response"]
---

Data quality 的核心概念是「證據資料本身的完整度、新鮮度與限制」。它連接 [evidence package](/backend/knowledge-cards/evidence-package/)、[sampling](/backend/knowledge-cards/sampling/) 與 [known gap](/backend/knowledge-cards/known-gap/)，讓下游知道這份 evidence 能支持到哪個判斷範圍。

## 跟其他概念的關係

Data quality 位在 [metrics](/backend/knowledge-cards/metrics/)、[trace](/backend/knowledge-cards/trace/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 之間。Metric、log、trace、audit log 都可能有延遲、抽樣、drop、masking 或 schema drift，這些限制要跟證據一起交接。

## 可觀察訊號

系統需要 data quality 的訊號是：

- trace sampling 讓某些 request path 無法完整重建
- log pipeline 有 ingest delay 或 drop
- query 只跑 primary、replica 或部分 tenant
- dashboard 結論需要標示 freshness 或 completeness 限制

## 接近真實網路服務的例子

資料庫 migration 的 evidence package 可以標示 `primary only; replica lag still recovering`，表示 validation query 可信，但 replica 讀取路徑還不能用同一份 evidence 直接放行。

## 判斷條件與後果

一份 evidence 能支持到哪個判斷範圍，取決於它的限制是否跟著交接。completeness、freshness、sampling、masking、retention 與 owner 沒有標示時，下游拿到的是一個看起來完整的結論：trace sampling 漏掉的 request path、log pipeline drop 掉的事件、只在 primary 跑過的 query，都不會出現在結論裡。release gate 或 incident decision log 把這種結論當成完整事實時，放行的範圍超過證據實際涵蓋的範圍，例如只驗過 primary 的 migration 連 replica 讀取路徑一起放行。這些限制跟證據一起標示時，下游才能依 [confidence](/backend/knowledge-cards/confidence/) 決定這份證據放行到哪裡。
