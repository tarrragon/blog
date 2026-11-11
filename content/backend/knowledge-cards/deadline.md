---
title: "Deadline"
date: 2026-04-23
description: "說明整體操作的截止時間如何沿著服務邊界傳遞"
weight: 45
---

Deadline 的核心概念是「整體操作必須完成的截止時間」。[Timeout](/backend/knowledge-cards/timeout/) 常是單一步驟的等待上限；deadline 則是整條 request、job 或 workflow 的總時間預算。

## 跟其他概念的關係

Deadline 讓多層呼叫共享同一份時間預算。入口 request 若只剩 200ms，下游呼叫就應知道剩餘時間，並選擇快速回應、[fallback](/backend/knowledge-cards/fallback/)、[degradation](/backend/knowledge-cards/degradation/) 或停止開始昂貴工作。

## 可觀察訊號與例子

系統需要 deadline 的訊號是多個下游各自 [retry policy](/backend/knowledge-cards/retry-policy/)，導致整體時間遠超使用者可接受範圍。搜尋 API 需要查庫存、價格與推薦時，deadline 可以讓每個下游根據剩餘時間調整策略。

## 判斷條件與後果

Deadline 只在入口生效、沒有傳到下游時，入口只剩 200ms，下游仍照自己的 timeout 與 retry policy 執行：使用者已經收到逾時錯誤，後端還在為這個 request 做昂貴的工作。傳到下游之後，retry、fallback 與 cancellation 讀的是同一份剩餘時間時才有效果：retry 不看剩餘時間時，重試次數乘上單次 timeout 超過整體預算；沒有 cancellation 時，入口放棄之後下游的工作照樣跑完。[Log](/backend/knowledge-cards/log/) 與 [trace](/backend/knowledge-cards/trace/) 沒有記錄 deadline exceeded、剩餘時間與造成超時的依賴時，只看得到 request 逾時，看不出時間耗在哪一個下游。
