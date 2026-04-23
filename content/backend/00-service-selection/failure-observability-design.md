---
title: "0.7 錯誤定位、觀測訊號與備援切換設計"
date: 2026-04-23
description: "從錯誤分類、定位線索、降級策略與 failover 設計服務可維護性"
weight: 7
---

服務可維護性的核心原則是把失敗設計成可分類、可定位、可降級、可恢復的狀態。穩定性表示服務在正常情況下能持續運行；可觀測性與備援設計則決定失敗發生時，團隊能否快速知道發生什麼、影響誰、如何降低傷害，以及如何切換到可用路徑。

## 本章目標

學完本章後，你將能夠：

1. 從需求面定義錯誤分類與定位線索
2. 判斷哪些錯誤需要對外回應、對內記錄、對平台告警
3. 設計可降級、可重試、可切換的服務行為
4. 把錯誤定位與備援需求連到 observability、deployment 與 reliability 模組

---

## 【觀察】錯誤設計是服務合約的一部分

錯誤設計的核心問題是「失敗時系統要留下什麼線索，並給誰什麼動作」。API response、domain error、log、metric、trace、alert、retry、fallback 與 failover 都是錯誤合約的一部分。

| 設計面向 | 要回答的問題 | 常見產出 |
| -------- | ------------ | -------- |
| 錯誤分類 | 這是輸入錯誤、權限錯誤、狀態衝突、下游失敗，還是系統故障 | error code、status、reason |
| 定位線索 | 工程師如何找到 request、使用者、資源、下游與版本 | trace id、request id、subject id、dependency |
| 對外回應 | 呼叫者能否理解下一步動作 | stable error response、retry hint |
| 操作訊號 | on-call 如何知道影響範圍與嚴重度 | log、metric、alert、dashboard |
| 降級策略 | 主要路徑失敗時能否提供較低能力服務 | fallback、cache、read-only、queue later |
| 切換策略 | 依賴或節點失效時能否轉到其他路徑 | failover、traffic shift、draining |

這張表是設計索引。錯誤定位與備援切換應在服務設計時討論，而非等事故後才補欄位。

## 【判讀】錯誤分類要服務呼叫者與維護者

錯誤分類的核心責任是讓不同角色知道下一步。呼叫者需要知道是否能修正輸入、稍後重試或停止操作；維護者需要知道錯誤來自程式規則、資料狀態、外部依賴、容量瓶頸或平台問題。

接近真實網路服務的例子包括：

- 使用者建立訂單時庫存不足，對外 response 要表達「目前狀態不允許」，對內 log 要能定位商品與庫存版本。
- 付款 API timeout，對外 response 要避免承諾付款結果，對內訊號要標出 payment provider、timeout duration 與 retry policy。
- [Webhook](../knowledge-cards/webhook/) payload 格式錯誤，對外要回穩定錯誤碼，對內要記錄 schema version 與來源系統。

這類設計的陷阱是只留下自由文字錯誤。自由文字適合人快速閱讀，但分類、查詢、告警與統計需要穩定欄位。錯誤分類要同時支援 API contract、log schema、metric label 與 runbook。

下一步可讀：[操作平台選型](operations-platform-selection/) 與 [可觀測性平台](../04-observability/)。

## 【判讀】定位線索要沿著 request 與事件流傳遞

定位線索的核心責任是讓工程師能把一個症狀追回完整路徑。當 request 跨過 API、資料庫、cache、queue、worker、外部服務與 WebSocket 推送時，線索需要跟著邊界傳遞。

接近真實網路服務的例子包括：

- checkout 變慢時，需要知道同一個 trace 經過 cart、payment、inventory 與 shipping 的哪一段。
- queue message 重試時，需要知道原始 request、event id、consumer、attempt count 與最後錯誤。
- 即時通知漏送時，需要知道 topic、client id、connection id、server instance 與 publish path。

這類設計的陷阱是每個元件各自產生無關 ID。request id、trace id、event id、subject id 與 dependency name 要有清楚用途，並在跨服務、跨 queue、跨 worker 時保留關聯。

下一步可讀：[可觀測性平台](../04-observability/)。

## 【判讀】對外錯誤要穩定，對內錯誤要可診斷

對外錯誤的核心責任是讓呼叫者知道可採取的動作；對內錯誤的核心責任是讓工程師定位原因。兩者可以關聯，但承擔不同責任。

接近真實網路服務的例子包括：

- 對外回 `payment_pending`，讓 client 顯示等待確認；對內保留 provider timeout、request payload hash、attempt count。
- 對外回 `rate_limited`，讓 client 根據 retry hint 延後；對內記錄 tenant、limit rule、current usage。
- 對外回 `resource_conflict`，讓使用者刷新狀態；對內記錄 expected version 與 actual version。

這類設計的陷阱是把內部錯誤直接暴露給 client，或把對外訊息當成唯一診斷資料。對外錯誤要穩定、安全、可被產品處理；對內錯誤要保留足夠脈絡、可查詢、可關聯。

下一步可讀：[操作平台選型](operations-platform-selection/)。

## 【判讀】降級策略要依資料語意分級

降級策略的核心問題是「主要能力失效時，哪些功能仍可提供」。降級可以是回舊資料、只讀模式、排隊稍後處理、停用非核心功能、限制流量或切換較慢但可靠的路徑。

接近真實網路服務的例子包括：

- 推薦服務失效時，首頁可以回熱門商品或預先產生的榜單。
- Email provider 暫時失敗時，通知工作可以進 queue 稍後重試。
- 搜尋服務延遲升高時，後台可以先提供精確 ID 查詢，暫停全文搜尋。

這類設計的陷阱是所有功能共用同一種失敗行為。付款、訊息、搜尋、推薦、通知與報表的失敗代價不同；降級策略要依資料是否可丟、是否可延遲、是否可重建、是否涉及金流或稽核分級。

下一步可讀：[成本、風險與選型取捨](cost-risk-tradeoffs/)。

## 【判讀】備援切換要先定義切換條件

備援切換的核心責任是讓系統在依賴、節點或區域失效時轉到可用路徑。切換可以發生在 client、load balancer、[service discovery](../knowledge-cards/service-discovery/)、application adapter、queue consumer 或資料層；每一層都需要明確條件。

接近真實網路服務的例子包括：

- 外部付款 provider 連續 timeout 後，系統暫停建立新付款並保留待確認狀態。
- 某個 service instance readiness 失敗後，load balancer 停止送新流量並進入 draining。
- 主要搜尋 cluster 延遲過高時，後台切到只讀快照或簡化查詢。

這類設計的陷阱是把 failover 想成自動且無代價。切換可能造成重複請求、順序改變、資料短暫不一致、成本上升或排障複雜度增加。切換條件、回切條件、資料一致性與告警都要一起設計。

下一步可讀：[部署平台與網路入口](../05-deployment-platform/) 與 [可靠性驗證流程](../06-reliability/)。

## 【判讀】備援設計需要驗證流程

備援設計的核心完成標準是能被演練。文件中宣稱可以重試、降級、切換或回復，只代表設計意圖；可靠性驗證要證明這些路徑在接近真實條件下能運作。

接近真實網路服務的例子包括：

- 在預備環境讓 payment provider adapter 回 timeout，驗證訂單狀態是否停在待確認。
- 在 [load test](../knowledge-cards/load-test/) 中提高 queue lag，驗證 dashboard、alert 與 consumer 擴容決策。
- 在 [chaos test](../knowledge-cards/chaos-test/) 中讓 broker 暫時中斷，驗證 outbox、retry 與 idempotency。

這類設計的陷阱是只測成功路徑。錯誤分類、定位線索、降級策略與 failover 都應有對應測試、演練或 release gate，否則事故發生時才會知道設計缺口。

下一步可讀：[可靠性驗證流程](../06-reliability/)。

## 【檢查】進入實作前的概念邊界清單

當以下問題都能回答時，代表本章的概念層已完成，可以進入觀測與事故治理實作章節：

1. 錯誤分類是否可被查詢與統計（對外碼、對內欄位）
2. 定位線索是否可跨邊界串接（request、trace、event）
3. 降級與切換條件是否明確（觸發條件、回切條件）
4. 演練與驗證入口是否明確（load、chaos、事故演練）

下一步建議路由：

- [04-observability](../04-observability/)
- [06-reliability](../06-reliability/)
- [08-incident-response](../08-incident-response/)

## 小結

可觀測性與備援設計要從服務需求開始。錯誤分類讓呼叫者與維護者知道下一步，定位線索讓症狀能追回路徑，對外與對內錯誤承擔不同責任，降級策略依資料語意分級，備援切換需要明確條件，可靠性驗證則確認這些設計能在失敗時運作。
