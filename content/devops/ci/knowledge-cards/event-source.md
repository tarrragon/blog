---
title: "Event Source"
date: 2026-05-21
description: "說明 serverless 與事件驅動流程中觸發來源如何影響 retry、dead-letter 與回復策略"
tags: ["CD", "serverless", "event", "knowledge-card"]
weight: 26
aliases: ["/ci/knowledge-cards/event-source/"]
---

Event Source 的核心概念是「觸發執行的事件入口」。它決定 serverless function 或 worker 何時執行、如何重試、如何進入 dead-letter，並影響 [Function Alias](/devops/ci/knowledge-cards/function-alias/) 的 rollout 與回復策略。

## 跟其他概念的關係

Event Source 位在 queue、topic、HTTP gateway、object storage、scheduler 與 [function](/devops/ci/knowledge-cards/function-alias/) / worker 之間，負責把外部事件轉成執行請求。

## 可觀察訊號

- 函式部署成功，但 invocation 因 trigger 設定失敗。
- Queue event 重試造成同一筆資料被重複處理。
- 事件 schema 漂移導致 subscriber 解析失敗。

## 接近真實服務的例子

Queue 觸發的 function 以 batch 方式處理訊息。新版本解析失敗時，訊息進入 dead-letter queue；團隊先停用 trigger，再修復 function 或重放事件。

## 判斷條件與後果

Event Source 的設定決定事件處理失敗之後是否能回復，各項設定沒有處理時的狀態：

- **trigger 條件與權限**：篩選條件寫錯或 function 缺少讀取來源的權限時，function 部署成功，invocation 卻失敗或從未觸發。
- **retry 與 batch size**：失敗的事件會被重新投遞，處理邏輯不具冪等性時，同一筆資料被處理多次；平台以整批為單位重試時，batch 越大，一筆壞資料連帶重試的正常訊息越多。
- **dead-letter 與 replay**：沒有 dead-letter 時，重試用盡的事件被丟棄；有 dead-letter 而沒有 replay 的方法時，function 修好之後那些事件仍然沒被處理。
- **schema 契約**：producer 改了事件格式而 subscriber 沒有跟著更新時，新版本解析失敗。
