---
title: "7.R4 資源濫用與可用性破壞"
date: 2026-04-24
description: "說明攻擊者如何把合法操作放大成容量壓力或服務退化"
weight: 714
---

資源濫用的核心概念是「合法請求也可能被用來消耗大量資源」。紅隊不只看能不能打進系統，也看能不能把系統拖慢、拖垮、拖到失去服務能力。

## 概念位置

資源濫用會落在 [Unrestricted Resource Consumption](../../knowledge-cards/unrestricted-resource-consumption/)、[rate limit](../../knowledge-cards/rate-limit/)、[WAF](../../knowledge-cards/waf/)、[backpressure](../../knowledge-cards/backpressure/)、[load shedding](../../knowledge-cards/load-shedding/) 與 [timeout](../../knowledge-cards/timeout/) 的交界。它關心的是昂貴操作、無限放大、重試風暴、批次匯出與 queue saturation。

## 可觀察訊號與例子

當某個功能可以觸發大量查詢、很大的輸出、很深的遞迴、很多下游呼叫或很高的 fan-out，紅隊就會把它視為可被放大的操作。像是匯出全量報表、過度細分搜尋、重複提交重試、批量建立資源與自動化 bot 操作，都可能把局部請求變成整體壓力。

## 設計責任

要先定義昂貴操作的上限，再決定 rate limit、配額、分段處理、排隊、拒絕與降級策略。若某個功能的成本遠高於一般請求，就不應該讓它跟一般入口共用同一套處理節奏。
