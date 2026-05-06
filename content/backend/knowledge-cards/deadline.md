---
title: "Deadline"
date: 2026-04-23
description: "說明整體操作的截止時間如何沿著服務邊界傳遞"
weight: 44
---


Deadline 的核心概念是「整體操作必須完成的截止時間」。[Timeout](/backend/knowledge-cards/timeout/) 常是單一步驟的等待上限；deadline 則是整條 request、job 或 workflow 的總時間預算。

## 概念位置

Deadline 讓多層呼叫共享同一份時間預算。入口 request 若只剩 200ms，下游呼叫就應知道剩餘時間，並選擇快速回應、[fallback](/backend/knowledge-cards/fallback/)、[degradation](/backend/knowledge-cards/degradation/) 或停止開始昂貴工作。

## 可觀察訊號與例子

系統需要 deadline 的訊號是多個下游各自 [retry policy](/backend/knowledge-cards/retry-policy/)，導致整體時間遠超使用者可接受範圍。搜尋 API 需要查庫存、價格與推薦時，deadline 可以讓每個下游根據剩餘時間調整策略。

## 設計責任

Deadline 要跨服務傳遞，並和 retry policy、fallback、cancellation 與 observability 對齊。[Log](/backend/knowledge-cards/log/) 與 [trace](/backend/knowledge-cards/trace/) 應記錄 deadline exceeded、剩餘時間與造成超時的依賴。
