---
title: "0.0 後端需求分類地圖"
date: 2026-04-23
description: "先從需求形狀辨識狀態、讀取、非同步、即時、診斷、交付與可靠性問題"
weight: 0
---

後端需求分類的核心原則是先辨識「工程問題的形狀」。同一個產品功能可能同時包含狀態保存、讀取壓力、非同步處理、即時推送、診斷、部署與可靠性驗證；選型前要先把問題拆開，才有辦法討論服務能力。

## 本章目標

學完本章後，你將能夠：

1. 把後端需求拆成可討論的工程類型
2. 用產品情境辨識狀態、讀取、非同步、即時、診斷與交付需求
3. 找出需求討論中的常見陷阱
4. 把需求類型連到後續選型章節

---

## 【觀察】產品功能通常混合多種後端需求

需求分類的第一個判斷是「這個功能其實包含哪些後端責任」。例如一個電商結帳流程看起來是單一功能，但它可能同時需要保存訂單、查商品與庫存、呼叫付款、寄通知、更新報表、記錄操作訊號與支援發版回滾。

| 需求類型   | 核心問題                     | 常見情境                                                                                                                                                         |
| ---------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 狀態保存   | 系統承認哪份資料是正式狀態   | 訂單、會員、付款、權限                                                                                                                                           |
| 讀取壓力   | 同一份資料被大量重複讀取     | 商品頁、權限摘要、首頁推薦                                                                                                                                       |
| 非同步工作 | request 結束後仍要可靠處理   | 寄信、轉檔、同步外部系統                                                                                                                                         |
| 即時互動   | client 需要持續接收狀態變化  | 聊天、通知、進度更新、presence                                                                                                                                   |
| 操作診斷   | 出事時要知道原因與影響範圍   | [log](/backend/knowledge-cards/log/)、metric、[trace](/backend/knowledge-cards/trace/)、[dashboard](/backend/knowledge-cards/dashboard/)                         |
| 服務交付   | 服務要穩定發版、擴容與接流量 | [container](/backend/knowledge-cards/container/)、[load balancer](/backend/knowledge-cards/load-balancer/)、[readiness](/backend/knowledge-cards/readiness/)     |
| 可靠性驗證 | 事故前要驗證容量與失敗情境   | [CI pipeline](/backend/knowledge-cards/ci-pipeline/)、[load test](/backend/knowledge-cards/load-test/)、fuzz、[chaos test](/backend/knowledge-cards/chaos-test/) |

這張表是需求索引。每個類型後面都會對應到不同的能力地圖，但實際功能常會同時命中多列。

## 【判讀】狀態保存需求要先找正式狀態

狀態保存需求的核心訊號是「資料會被後續流程承認」。當使用者、營運人員、付款系統或稽核流程都需要相信某份資料，這份資料就需要明確的 [source of truth](/backend/knowledge-cards/source-of-truth/)。

接近真實網路服務的例子包括：

- 訂單建立後，付款、出貨、客服與退款都依賴同一筆訂單狀態。
- 會員升級方案後，API 權限、帳單與使用量限制都要讀到同一個 plan。
- 文章發布後，公開頁面、搜尋索引與後台審核都要知道目前版本。

這類需求的陷阱是把「看起來能存資料」的地方都當成正式狀態。快取、搜尋索引、log 與事件流可能保存資料副本，但它們承擔的責任不同。正式狀態要回答誰能寫入、哪些欄位要一致、失敗後如何恢復。

下一步可讀：[狀態與資料儲存選型](/backend/00-service-selection/state-storage-selection/)。

## 【判讀】讀取壓力需求要先找重複讀取路徑

讀取壓力需求的核心訊號是「同一類資料被大量重複讀取」。這種壓力通常先出現在熱門頁面、權限檢查、設定查詢、推薦摘要或即時狀態查詢。

接近真實網路服務的例子包括：

- 活動商品頁在短時間內被大量瀏覽，但商品描述變更頻率低。
- 每個 API request 都要讀取使用者權限與 [Feature Flag](/backend/knowledge-cards/feature-flag/)。
- 即時通知服務需要頻繁查詢 [topic](/backend/knowledge-cards/topic/) 的在線訂閱者。

這類需求的陷阱是把所有慢查詢都當成快取問題。若查詢慢是因為資料模型、索引、N+1 request、外部 API [timeout](/backend/knowledge-cards/timeout/) 或資料量爆炸，快取只能暫時吸收症狀。讀取壓力要先確認是否有明確 [source of truth](/backend/knowledge-cards/source-of-truth/)、資料能否重建、失效後是否能接受短暫不一致。

下一步可讀：[後端服務能力地圖](/backend/00-service-selection/service-capability-map/) 與 [狀態與資料儲存選型](/backend/00-service-selection/state-storage-selection/)。

## 【判讀】非同步需求要先找 request 邊界

非同步需求的核心訊號是「使用者不需要等到所有後續工作完成」。一個 request 可以先完成主要承諾，後續工作由背景流程、[queue](/backend/knowledge-cards/queue/)、stream 或 outbox 接續處理。

接近真實網路服務的例子包括：

- 付款成功頁先回應使用者，email、推播與報表更新在後面完成。
- 使用者上傳影片後先看到處理中狀態，轉檔與縮圖由背景 worker 執行。
- 外部 [webhook](/backend/knowledge-cards/webhook/) 進來後先驗證與保存，再由後續流程重試與分派。

這類需求的陷阱是把「放到背景」視為可靠性保證。背景工作離開 request 後，系統還要回答是否可遺失、是否重試、是否允許重複、是否需要順序、process 重啟後工作是否仍存在。

下一步可讀：[非同步與事件傳遞選型](/backend/00-service-selection/async-delivery-selection/)。

## 【判讀】即時互動需求要先找狀態補償方式

即時互動需求的核心訊號是「client 持續在線，並期待快速看到變化」。聊天、通知、進度更新、多人協作、presence 與 dashboard 都屬於這類需求。

接近真實網路服務的例子包括：

- 客服聊天室需要把新訊息推給在線客服與使用者。
- 任務處理頁需要即時顯示轉檔進度。
- 共同編輯工具需要讓其他使用者看到狀態變化。

這類需求的陷阱是把即時通道當成唯一可靠資料來源。[WebSocket](/backend/knowledge-cards/websocket/)、[Server-Sent Events (SSE)](/backend/knowledge-cards/sse/) 或 [pub/sub](/backend/knowledge-cards/pub-sub/) 適合降低延遲，但 client 斷線、server 重啟、網路切換都會造成缺口。即時需求要先決定離線後如何 [offline catch-up](/backend/knowledge-cards/offline-catchup/)、哪些訊息可丟、哪些訊息需要正式保存。

下一步可讀：[非同步與事件傳遞選型](/backend/00-service-selection/async-delivery-selection/) 與 [操作平台選型](/backend/00-service-selection/operations-platform-selection/)。

## 【判讀】操作診斷需求要先找決策問題

操作診斷需求的核心訊號是「團隊需要用訊號做決策」。log、metric、trace、dashboard 與 [alert](/backend/knowledge-cards/alert/) 的用途不同；它們都應服務某個排障、容量、告警或產品營運問題。

接近真實網路服務的例子包括：

- API 延遲上升時，要判斷瓶頸在資料庫、外部 API、queue 還是某個版本。
- queue lag 增加時，要判斷 [producer](/backend/knowledge-cards/producer/) 變快、[consumer](/backend/knowledge-cards/consumer/) 變慢，還是下游失敗。
- 某地區 [WebSocket](/backend/knowledge-cards/websocket/) disconnect 增加時，要知道是 client 版本、網路入口還是部署節點問題。

這類需求的陷阱是先買平台，再補欄位語意。沒有穩定欄位、[trace context](/backend/knowledge-cards/trace-context/)、錯誤分類與 [runbook](/backend/knowledge-cards/runbook/)，觀測平台只能保存大量難以操作的訊號。

下一步可讀：[操作平台選型](/backend/00-service-selection/operations-platform-selection/)。

## 【判讀】交付與可靠性需求要先找變更風險

交付與可靠性需求的核心訊號是「系統變更本身帶來風險」。當服務需要頻繁發版、水平擴容、處理尖峰、承受下游失敗或保證回歸品質，部署平台與可靠性驗證就會變成需求的一部分。

接近真實網路服務的例子包括：

- 發版時新版本尚未 ready 就接到流量，造成部分 request 失敗。
- 活動流量前沒有容量證據，只能靠臨時加機器。
- 重要 parser 一次更新後影響大量 [webhook](/backend/knowledge-cards/webhook/)，缺少 fuzz 或回歸案例。

這類需求的陷阱是把可靠性視為上線後的補救工作。交付與可靠性要在設計時就定義 readiness、shutdown、rollback、[load test](/backend/knowledge-cards/load-test/)、資料 [migration](/backend/knowledge-cards/migration/) 與事故演練的檢查點。

下一步可讀：[操作平台選型](/backend/00-service-selection/operations-platform-selection/)。

## 小結

後端需求分類要先拆問題，再談服務。狀態保存、讀取壓力、非同步工作、即時互動、操作診斷、服務交付與可靠性驗證各自有不同判斷訊號。需求形狀清楚後，後續才進入資料庫、快取、queue、觀測平台與部署平台的能力比較。
