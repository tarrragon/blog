---
title: "Stream Pipeline"
date: 2026-04-23
description: "說明連續資料流經多個處理階段時如何管理吞吐、順序與背壓"
weight: 128
---

Stream pipeline 的核心概念是「資料連續流經多個處理階段」。每個階段讀取輸入、處理資料、送到下一階段；整體吞吐取決於最慢階段與階段之間的 buffer。

## 概念位置

Stream pipeline 常出現在 event stream、log processing、[CDC](../change-data-capture/)、ETL、即時分析、IoT readings 與訊息轉換流程。它需要處理 ordering、[partition](../partition/)、[checkpoint](../checkpoint/)、[backpressure](../backpressure/)、[retry](../retry-policy/) 與資料完整性。

## 可觀察訊號與例子

系統需要 stream pipeline 設計的訊號是資料會持續進入，且需要多步驟加工。訂單事件先做清洗，再寫入搜尋索引與報表系統；任一階段變慢，都會讓上游 lag 擴大。

## 設計責任

Stream pipeline 要定義階段邊界、[buffer](../buffer/)、checkpoint、錯誤隔離、[重放](../replay-runbook/)、lag 指標與 [correctness check](../correctness-check/)。每個階段都要能被單獨觀測與限速。
