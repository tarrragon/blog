---
title: "Read Model"
date: 2026-04-23
description: "說明為查詢場景建立的讀取模型與正式狀態的責任分離"
weight: 150
---

Read model 的核心概念是「為查詢需求建立專用資料形狀」。它強調查詢效率與體驗，正式狀態仍由 [source of truth](../source-of-truth/) 承擔。

## 概念位置

Read model 常由資料庫、[event log](../event-log/) 或批次流程同步產生，常見於報表、列表頁與聚合查詢。

## 設計責任

設計時要定義同步延遲、重建流程、欄位語意與查詢邊界，避免把寫入責任混入 read model。
