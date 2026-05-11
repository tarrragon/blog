---
title: "Query Link"
date: 2026-05-11
description: "說明證據包如何保存可重跑查詢入口，而不是只保留截圖或口頭結論"
weight: 319
tags: ["backend", "knowledge-card", "observability", "incident-response"]
---

Query link 的核心概念是「保存可重跑的查詢入口」。它連接 [evidence package](/backend/knowledge-cards/evidence-package/)、[time range](/backend/knowledge-cards/time-range/) 與 [data quality](/backend/knowledge-cards/data-quality/)，讓後續接手者能重新驗證同一個判讀。

## 概念位置

Query link 位在 [dashboard](/backend/knowledge-cards/dashboard/)、[validation query](/backend/knowledge-cards/validation-query/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 之間。截圖適合溝通當下狀態，query link 則保留可回放、可調整、可驗證的入口。

## 可觀察訊號

系統需要 query link 的訊號是：

- 事故交班時下一班需要重跑同一個判讀
- release gate 要引用具體查詢結果，而不是貼圖表摘要
- PIR reviewer 需要查證當時資料限制
- dashboard panel 版本變動可能改變圖表語意

## 接近真實網路服務的例子

Checkout API evidence package 可以保存錯誤率 query、p95 latency query 與 provider timeout query 的連結。資料庫 migration evidence package 則可以保存 row count、mismatch sample 與 replication lag query link。

## 設計責任

Query link 要保留查詢版本、參數、time range、資料來源與 owner。它要搭配 [known gap](/backend/knowledge-cards/known-gap/) 記錄查詢未覆蓋的資料範圍，避免截圖或 dashboard 名稱被誤當成完整證據。
