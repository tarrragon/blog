---
title: "Event Source"
date: 2026-05-21
description: "說明 serverless 與事件驅動流程中觸發來源如何影響 retry、dead-letter 與回復策略"
tags: ["CD", "serverless", "event", "knowledge-card"]
weight: 26
---

Event Source 的核心概念是「觸發執行的事件入口」。它決定 serverless function 或 worker 何時執行、如何重試、如何進入 dead-letter，並影響 [Function Alias](/ci/knowledge-cards/function-alias/) 的 rollout 與回復策略。

## 概念位置

Event Source 位在 queue、topic、HTTP gateway、object storage、scheduler 與 [function](/ci/knowledge-cards/function-alias/) / worker 之間，負責把外部事件轉成執行請求。

## 可觀察訊號

- 函式部署成功，但 invocation 因 trigger 設定失敗。
- Queue event 重試造成同一筆資料被重複處理。
- 事件 schema 漂移導致 subscriber 解析失敗。

## 接近真實服務的例子

Queue 觸發的 function 以 batch 方式處理訊息。新版本解析失敗時，訊息進入 dead-letter queue；團隊先停用 trigger，再修復 function 或重放事件。

## 設計責任

Event Source 要定義 trigger 條件、batch size、retry、dead-letter、replay、權限與 schema 契約，讓事件驅動發布具備可觀測回復路徑。
