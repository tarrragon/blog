---
title: "Data Quality"
date: 2026-05-11
description: "說明證據欄位如何標示 completeness、freshness、sampling 與資料限制"
weight: 320
tags: ["backend", "knowledge-card", "observability", "incident-response"]
---

Data quality 的核心概念是「證據資料本身的完整度、新鮮度與限制」。它連接 [evidence package](/backend/knowledge-cards/evidence-package/)、[sampling](/backend/knowledge-cards/sampling/) 與 [known gap](/backend/knowledge-cards/known-gap/)，讓下游知道這份 evidence 能支持到哪個判斷範圍。

## 概念位置

Data quality 位在 [metrics](/backend/knowledge-cards/metrics/)、[trace](/backend/knowledge-cards/trace/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 之間。Metric、log、trace、audit log 都可能有延遲、抽樣、drop、masking 或 schema drift，這些限制要跟證據一起交接。

## 可觀察訊號

系統需要 data quality 的訊號是：

- trace sampling 讓某些 request path 無法完整重建
- log pipeline 有 ingest delay 或 drop
- query 只跑 primary、replica 或部分 tenant
- dashboard 結論需要標示 freshness 或 completeness 限制

## 接近真實網路服務的例子

資料庫 migration 的 evidence package 可以標示 `primary only; replica lag still recovering`，表示 validation query 可信，但 replica 讀取路徑還不能用同一份 evidence 直接放行。

## 設計責任

Data quality 要標示 completeness、freshness、sampling、masking、retention 與 owner。它要支援 [confidence](/backend/knowledge-cards/confidence/) 判讀，避免 release gate 或 incident decision log 把有限資料誤當成完整事實。
