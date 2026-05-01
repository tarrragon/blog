---
title: "4.1 log schema 與搜尋規劃"
date: 2026-04-23
description: "整理 log 欄位、索引與搜尋策略"
weight: 1
---

## 大綱

- structured [log schema](/backend/knowledge-cards/log-schema/)
- correlation fields
- index 與 [retention](/backend/knowledge-cards/retention/)
- query pattern

## 判讀訊號

- log 欄位 schema 漂移、跨服務 correlation id 對不上
- 事故時靠 grep 拼湊事件、無結構化查詢入口
- log 索引爆量、查詢退化但無清理流程
- log 含大量 free-form text、無一致關鍵欄位
- retention 策略全平、舊事件查不到 / 不該留的還在留

## 交接路由

- 04.7 cardinality / cost：label 預算與保留階梯
- 04.8 訊號治理閉環：log-based alert 的生命週期
- 04.12 audit log：稽核訊號跟 operational log 的邊界
