---
title: "4.19 Debuggability by Design"
date: 2026-05-02
description: "把可診斷性前移到 API、async workflow、dependency call 與錯誤模型設計"
weight: 19
---

## 大綱

- debuggability by design 的責任：讓系統設計本身支援定位、重現與證據收集
- API 設計：request id、error code、idempotency key、semantic status
- async workflow：message id、correlation id、retry count、dead-letter reason
- dependency call：timeout、fallback、upstream response、circuit state
- error model：可分類錯誤、可追蹤錯誤鏈、可對應使用者影響
- 診斷入口：[diagnostic endpoint](/backend/knowledge-cards/diagnostic-endpoint/)、health check、probe
- 跟語言教材的分工：語言處理 logger / error chain，04 處理跨服務診斷能力
- 反模式：事後補 log；錯誤只回 500；async 任務缺 correlation id；依賴失敗無上下文

Debuggability by design 的核心是讓系統在設計時就暴露足夠上下文。事故時需要的資訊若沒有在 API、message、dependency call 層留下來，後端平台再完整也只能收集到片段訊號。

## 概念定位

Debuggability by design 是把可診斷性當成服務設計輸入的做法，責任是讓系統在出問題時自然留下定位所需的脈絡。

這一頁處理的是設計前移。觀測工具只能收集系統吐出的訊號；如果 API、async workflow、dependency call 與 error model 沒有診斷欄位，事後補平台也只能看到破碎片段。

這層與可觀測平台互補：平台負責收、存、查，設計負責產生可判讀語意。兩者任一缺失，都會讓事故定位時間呈倍數增加。

## 核心判讀

判讀 debuggability 時，先看關鍵流程是否保留 correlation，再看錯誤是否能路由到下一步。

重點訊號包括：

- API request 是否有穩定 [request id](/backend/knowledge-cards/request-id/) 與錯誤分類
- async message 是否有 correlation id、retry count 與 DLQ reason
- dependency call 是否記錄 upstream、timeout、fallback 與 response class
- error chain 是否能連到 trace、log 與 user impact
- diagnostic endpoint 是否能支援 on-call 的低風險查詢

| 設計層        | 最小可診斷欄位                           | 事故價值                   |
| ------------- | ---------------------------------------- | -------------------------- |
| API           | request id、error code、idempotency key  | 快速對齊請求與結果         |
| Async / Queue | message id、correlation id、retry reason | 還原跨流程事件鏈           |
| Dependency    | upstream、timeout、fallback state        | 分辨本地問題與外部依賴問題 |
| Error Model   | error class、context、impact hint        | 路由到正確處理流程         |

## 判讀訊號

- 事故時只能看到「500」，需要重跑才能定位原因
- queue message 進 DLQ 後缺少原始 request 脈絡
- 外部 API timeout 無 upstream 名稱、耗時與 fallback 狀態
- 錯誤被包裝後 trace 與 error chain 斷裂
- health check 顯示 healthy，但核心旅程已經失效

典型情境是 queue 任務在三次重試後進 DLQ，但缺少 request 與 tenant 脈絡。工程師可以看到「失敗很多」，後續需要先補「誰受影響、哪個流程壞、該先修哪一段」的判讀資訊。這就是設計期缺欄位造成的診斷斷點。

## 交接路由

- 04.1 log schema：定義診斷欄位
- 04.3 tracing：保留跨服務 context
- 04.11 telemetry pipeline：確保診斷訊號能被採集
- 06.10 contract testing：把錯誤模型與外部契約納入驗證
- 08.18 incident intake：把設計期留下的診斷欄位轉成 evidence
