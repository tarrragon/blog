---
title: "4.1 log schema 與搜尋規劃"
date: 2026-04-23
description: "整理 log 欄位、索引與搜尋策略"
weight: 1
---

## 大綱

- structured [log schema](/backend/knowledge-cards/log-schema/)
- [correlation id](/backend/knowledge-cards/correlation-id/) / [request id](/backend/knowledge-cards/request-id/) fields
- index 與 [retention](/backend/knowledge-cards/retention/)
- query pattern

## 概念定位

[log schema](/backend/knowledge-cards/log-schema/) 是把事件紀錄從文字輸出變成可查詢資料的契約，責任是讓不同服務在事故時能用同一組欄位還原脈絡。

這一頁處理的是欄位與搜尋路徑。log 的價值不在於寫得多，而在於事故時能用穩定欄位找到同一個 request、同一個 tenant、同一個 dependency call 與同一段錯誤鏈。

## 核心判讀

判讀 log schema 時，先看 correlation fields 是否穩定，再看 [search index](/backend/knowledge-cards/search-index/) 與 [retention](/backend/knowledge-cards/retention/) 是否對齊查詢需求。

重點訊號包括：

- [request id](/backend/knowledge-cards/request-id/)、[trace id](/backend/knowledge-cards/trace-id/)、[tenant boundary](/backend/knowledge-cards/tenant-boundary/) 與 service name 是否跨服務一致
- high-cardinality 欄位是否被放進可控索引，並受查詢價值與成本預算約束
- [retention](/backend/knowledge-cards/retention/) 是否依 operational debug、audit、compliance 分層
- query pattern 是否能支援 [incident timeline](/backend/knowledge-cards/incident-timeline/) 還原

## 判讀訊號

- log 欄位 schema 漂移、跨服務 correlation id 對不上
- 事故時靠 grep 拼湊事件、無結構化查詢入口
- log 索引爆量、查詢退化但無清理流程
- log 含大量 free-form text、無一致關鍵欄位
- retention 策略全平、舊事件查不到 / 不該留的還在留

## 交接路由

- 04.7 [metric cardinality](/backend/knowledge-cards/metric-cardinality/) / cost：label 預算與保留階梯
- 04.8 訊號治理閉環：log-based alert 的生命週期
- 04.12 [audit log](/backend/knowledge-cards/audit-log/)：稽核訊號跟 operational log 的邊界
