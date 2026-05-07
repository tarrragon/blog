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

Debuggability by design 的核心是讓系統在設計時就暴露足夠上下文。事故時需要的資訊若沒有在 API、message、dependency call 與 error model 層留下來，後端平台再完整也只能收集到片段訊號。

## 概念定位

Debuggability by design 是把可診斷性當成服務設計輸入的做法，責任是讓系統在出問題時自然留下定位所需的脈絡。

這一頁處理的是設計前移。觀測工具只能收集系統吐出的訊號；如果 API、async workflow、dependency call 與 error model 沒有診斷欄位，事後補平台也只能看到破碎片段。

這層與可觀測平台互補：平台負責收、存、查，設計負責產生可判讀語意。兩者任一缺失，都會讓事故定位時間呈倍數增加。

## 設計輸入

Debuggability by design 的設計輸入是「未來出問題時需要回答什麼問題」。系統設計時先列出這些問題，才能決定 API、message、dependency call 與 error model 要留下哪些欄位。

| 問題                       | 需要的設計輸入                             | 常見位置                   |
| -------------------------- | ------------------------------------------ | -------------------------- |
| 這次失敗影響哪個請求或用戶 | request id、tenant、user journey           | API、log schema、trace     |
| 這個 async 任務從哪裡來    | correlation id、message id、causation id   | queue、worker、event log   |
| 失敗來自本服務還是外部依賴 | upstream name、timeout、response class     | HTTP client、adapter       |
| 這個錯誤能否重試或回放     | retry count、idempotency key、DLQ reason   | worker、consumer、DLQ      |
| 事故時能否安全查系統狀態   | diagnostic endpoint、probe、read-only view | admin / diagnostic surface |

Request id 與 trace id 的責任不同。request id 通常對應對外請求與支援查詢，trace id 對應跨服務路徑；兩者互相連結時，支援查詢與工程診斷都會有穩定入口。

Correlation id 與 causation id 能讓 async workflow 保留因果。事件進入 queue、fan-out、retry、DLQ 或 replay 後，團隊需要知道它從哪個 request 或上游事件來，並且知道目前是哪一次處理嘗試。

Diagnostic endpoint 的責任是提供低風險查詢入口。它是受權限、速率、遮罩與審計保護的操作面，讓 on-call 能查健康、依賴、queue、cache 或 feature flag 狀態。

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

## API 可診斷性

API 可診斷性的責任是讓每一次 request 都能被支援、工程與事故流程共同定位。API 不只回傳成功或失敗，也要留下足夠語意讓團隊知道錯在哪個層級。

| API 欄位        | 設計責任                          | 事故價值                     |
| --------------- | --------------------------------- | ---------------------------- |
| Request ID      | 對齊客訴、log、trace 與支援查詢   | 從用戶回報回到後端事件       |
| Error code      | 穩定分類錯誤語意                  | 分辨 validation、auth、quota |
| Idempotency key | 保護重試與重播                    | 避免 recovery 時重複副作用   |
| Semantic status | 表達可重試、已接受、部分完成      | 支援客戶端與後端一致處置     |
| Impact hint     | 標示 user-facing 或 internal-only | 支援 severity 初判           |

Request ID 是支援與工程之間的共同鑰匙。客戶只知道某次操作失敗，支援需要 request id 或可查詢等價欄位，才能把客訴轉成 incident intake evidence。

Error code 應該表達穩定語意，並保持內部實作封裝。`PAYMENT_PROVIDER_TIMEOUT`、`QUOTA_EXCEEDED`、`TOKEN_EXPIRED` 這類分類能支援路由；隨程式碼結構變動的錯誤字串則會讓查詢與客戶端處置不穩定。

Idempotency key 是 recovery 的診斷欄位。當 retry、rollback、replay 或補償流程啟動時，團隊需要知道哪些請求已被接受、哪些副作用已完成、哪些可以安全重送。

## Async Workflow 可診斷性

Async workflow 可診斷性的責任是讓事件離開同步 request 後仍保留因果鏈。queue、worker、event handler 與 scheduled job 會把時間拉長、路徑拉開，欄位不足時最容易形成診斷斷點。

| Async 欄位       | 設計責任                        | 事故價值                       |
| ---------------- | ------------------------------- | ------------------------------ |
| Message ID       | 標識單一訊息                    | 查詢 delivery、ack、redelivery |
| Correlation ID   | 串回原始 request 或 workflow    | 還原跨流程事件鏈               |
| Retry count      | 記錄處理嘗試次數                | 分辨 transient 與 poison case  |
| DLQ reason       | 記錄進入 dead-letter queue 原因 | 支援 replay 與修復排序         |
| Consumer version | 標示處理程式版本                | 追查 rollout 或 schema 相容性  |

Message ID 讓團隊能看見單一訊息的生命週期。它應該能串到 publish、broker delivery、consumer ack、redelivery、DLQ 與 replay。

Correlation ID 讓 async 任務保留業務脈絡。缺少 correlation id 時，DLQ dashboard 只能顯示失敗數量，tenant、request 與 user journey 影響範圍會留在人工追查階段。

Retry count 與 DLQ reason 讓回復路徑可排序。高 retry count 可能代表下游依賴失效，也可能代表 poison message；兩者需要不同處置。

## Dependency Call 可診斷性

Dependency call 可診斷性的責任是讓團隊分辨本地問題、下游問題與保護機制啟動。每一次外部依賴呼叫都應留下足夠上下文，支援等待、降級、切換或升級 vendor incident 的判斷。

| Dependency 欄位 | 設計責任                    | 事故價值                         |
| --------------- | --------------------------- | -------------------------------- |
| Upstream name   | 穩定標示依賴服務            | 分辨哪個下游失效                 |
| Deadline        | 標示呼叫預算                | 判斷 timeout 設計是否合理        |
| Response class  | 聚合成功、4xx、5xx、timeout | 支援 error rate 與 vendor triage |
| Fallback state  | 記錄是否進入降級            | 判斷用戶影響是否被吸收           |
| Circuit state   | 記錄 circuit breaker 狀態   | 分辨保護機制或真實恢復           |

Upstream name 需要是穩定維度。若每個 adapter 使用不同名稱，dashboard 與 trace 很難把同一個供應商或內部依賴聚合在一起。

Deadline 是 dependency call 的診斷欄位。timeout 發生時，團隊需要知道是下游慢、呼叫預算過短、queue backlog 導致開始太晚，還是 retry policy 放大壓力。

Fallback state 讓事故團隊知道保護是否生效。服務錯誤率可能沒上升，是因為 fallback 吸收了下游失敗；若沒有 fallback 訊號，團隊會低估風險。

## Error Model 可診斷性

Error model 可診斷性的責任是把錯誤轉成可分類、可路由、可復盤的語意。錯誤不只服務於程式控制流，也服務於事故判讀與使用者影響評估。

| 錯誤層級               | 設計責任                      | 路由方向                     |
| ---------------------- | ----------------------------- | ---------------------------- |
| Validation error       | 輸入不符合契約                | API contract / client 修正   |
| Authorization error    | 身分或權限不足                | IAM / security triage        |
| Dependency error       | 外部依賴回應失敗或超時        | vendor / downstream triage   |
| Capacity error         | 資源、queue 或 quota 不足     | capacity / load shedding     |
| Data consistency error | 寫入、讀取或 migration 不一致 | reliability / migration gate |

錯誤分類應該讓下一步明確。`internal error` 適合作為最後防線；主要分類需要支援 on-call 判斷是重試、降級、rollback、升級資安，還是進入資料修復。

Error chain 需要保留上下文。過度包裝錯誤會讓原始 dependency、timeout、request id 或 schema version 消失；完全不包裝則會把底層細節直接丟給外部使用者。好的 error model 會分開內部診斷語意與外部穩定契約。

## 判讀訊號

- 事故時只能看到「500」，需要重跑才能定位原因
- queue message 進 DLQ 後缺少原始 request 脈絡
- 外部 API timeout 無 upstream 名稱、耗時與 fallback 狀態
- 錯誤被包裝後 trace 與 error chain 斷裂
- health check 顯示 healthy，但核心旅程已經失效

典型情境是 queue 任務在三次重試後進 DLQ，但缺少 request 與 tenant 脈絡。工程師可以看到「失敗很多」，後續需要先補「誰受影響、哪個流程壞、該先修哪一段」的判讀資訊。這就是設計期缺欄位造成的診斷斷點。

## 控制面

Debuggability by design 的控制面是把診斷欄位納入設計審查與契約驗證。可診斷性若只靠事後補 log，會在每次新 API、新 workflow 或新 dependency 上重複遺漏。

1. 在 API design review 中檢查 request id、error code、idempotency 與 impact hint。
2. 在 async workflow review 中檢查 message id、correlation、retry 與 DLQ reason。
3. 在 dependency review 中檢查 timeout、deadline、fallback 與 upstream naming。
4. 在 error model review 中檢查分類、內外部語意與 error chain。
5. 在 contract testing 中驗證關鍵診斷欄位與錯誤語意。

設計審查需要明確區分必填欄位與情境欄位。request id、trace context、error class 與 owner 通常是跨服務必填；idempotency key、DLQ reason、circuit state 則依 workflow 與依賴類型決定。

Contract testing 可以保護可診斷性。若 API 或 event schema 調整後移除了 correlation id、error code 或 retry metadata，測試應該阻擋這類破壞，因為它會讓事故判讀退回人工拼接。

## 常見反模式

Debuggability by design 的反模式是把診斷能力推遲到事故後。事故後補 log 可以修下一次，已發生事件的證據缺口則會留在復盤限制中。

| 反模式                     | 表面現象                      | 修正方向                                |
| -------------------------- | ----------------------------- | --------------------------------------- |
| 事後補 log                 | 每次事故才知道缺哪個欄位      | 設計審查納入診斷欄位                    |
| 錯誤只回 500               | 客戶、支援與 on-call 缺少分類 | 建立穩定 error code 與 error class      |
| Async 缺 correlation       | DLQ 只有失敗數量，無業務脈絡  | message schema 保留因果欄位             |
| Dependency 黑箱            | timeout 只顯示本地錯誤        | adapter 統一 upstream 與 response class |
| Diagnostic endpoint 無治理 | 查詢有用但風險過高或無審計    | 權限、遮罩、速率與 audit log            |

事後補 log 的代價是已發生事故會留下復盤缺口。若缺少原始 request、tenant、message 或 dependency 欄位，工程師只能用間接推論重建時間線。

錯誤只回 500 會把所有問題導向同一條路由。validation、authorization、dependency、capacity 與 data consistency 的處置完全不同，錯誤模型應該支援這些分流。

Diagnostic endpoint 無治理會把可診斷性變成資安風險。診斷入口需要最小權限、資料遮罩、速率限制與 audit log，並且只提供事故判讀需要的 read-only 資訊。

## 與語言教材的分工

Debuggability by design 位在 Backend 服務設計層。語言教材負責如何在特定 runtime 中傳遞 context、包裝 error、實作 middleware、處理 async local storage 或 goroutine context；本章負責定義跨語言都需要保留的診斷語意。

同步 runtime 的重點是 thread-local、connection pool 與 blocking dependency call 是否能保留 request context。async runtime 的重點是 task、promise、callback 與 queue boundary 是否能保留 trace context。goroutine 或 lightweight task runtime 的重點是廉價並發是否放大下游壓力，並且是否保留 deadline 與 cancellation。

不同語言可以用不同實作方式，但 API、async workflow、dependency call 與 error model 的診斷責任相同。這也是 Backend 章節保留跨語言抽象的理由。

## 交接路由

- 04.1 log schema：定義診斷欄位
- 04.3 tracing：保留跨服務 context
- 04.11 telemetry pipeline：確保診斷訊號能被採集
- 06.10 contract testing：把錯誤模型與外部契約納入驗證
- 08.18 incident intake：把設計期留下的診斷欄位轉成 evidence
