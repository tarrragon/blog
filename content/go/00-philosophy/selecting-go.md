---
title: "0.4 什麼時候選 Go"
date: 2026-04-23
description: "用選型條件判斷 Go 是否適合高併發服務、背景工作與長連線場景"
weight: 4
---

選擇 Go 的核心判斷是工作場景是否需要長時間運行、明確邊界、穩定併發與簡單部署。這一章用工程條件判斷 Go 是否適合目前問題；若工作更依賴框架模板、快速表單 CRUD、動態行為或大量 runtime magic，其他語言或框架可能更符合需求。

選型文章的目標是建立判斷路徑。讀者未來面對的可能是 API service、[WebSocket](../../../backend/knowledge-cards/websocket/) server、[queue](../../../backend/knowledge-cards/queue/) worker、內部工具或資料處理流程；同一個語言在不同工作負載下會有不同價值。先理解判斷條件，再進入語法細節，才不會把「我會寫 Go」誤解成「所有問題都該用 Go」。

## 本章目標

學完本章後，你將能夠：

1. 判斷哪些工作負載適合 Go
2. 看出哪些系統型態特別適合 Go
3. 區分 Go 的強項與不適合硬上的場景
4. 用工程條件取代語言偏好來做選型
5. 為後續語法與實作章節建立正確的閱讀順序

---

## 【觀察】先看工作負載，再看語言

Go 最常被選中的場景，是需要穩定處理大量服務型工作的系統。這些工作通常包含等待外部 I/O、管理長生命週期、持續處理背景任務或維持清楚服務邊界：

| 工作型態    | 為什麼適合 Go                                                                                                                      |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 高併發 I/O  | goroutine 成本低，適合大量等待型工作                                                                                               |
| 長連線服務  | 容易管理生命週期、取消與資源清理                                                                                                   |
| 背景 worker | 可以把工作拆成小單位並持續處理                                                                                                     |
| 事件處理    | channel、select 與明確邊界很適合事件流                                                                                             |
| API service | 標準庫直接支撐 HTTP、context、[log](../../../backend/knowledge-cards/log/) 與 [timeout](../../../backend/knowledge-cards/timeout/) |

如果工作本質就是一堆等待外部 I/O 的操作，Go 往往比把整個問題放進單線程迴圈更自然。

### 高併發 I/O：先看服務是否長時間等待外部回應

高併發 I/O 的核心特徵是「同時有很多工作在等待網路、檔案、資料庫或外部 API」。判斷時可以先看 request 的時間花在哪裡：如果大部分時間都在等下游回應，CPU 計算只占一小段，這就是等待型工作。

接近真實網路服務的例子包括：

- API gateway 同時轉送請求到多個下游服務
- 價格比較網站同時查詢多個供應商 API
- 檔案上傳服務同時處理大量 client 的上傳進度
- [webhook](../../../backend/knowledge-cards/webhook/) receiver 同時接收付款、物流、通知平台的 callback

這類服務的主要工程問題是「同時有很多等待中的工作，而且每個工作都需要容量邊界」。Go 的 goroutine 可以讓每個等待中的 request 有清楚的執行單位，`context` 可以控制 [timeout](../../../backend/knowledge-cards/timeout/) 與取消，channel 或 semaphore 可以限制同時打到下游的數量。Go 的價值在於讓等待、取消與容量控制都變成明確程式結構。

### 長連線服務：先看 client 是否會持續留在線上

長連線服務的核心特徵是「client 連上來之後不會立刻結束」。判斷時可以看連線是否需要維持數分鐘、數小時，甚至整個工作階段；只要 server 要持續追蹤 client 狀態，就會遇到生命週期管理問題。

接近真實網路服務的例子包括：

- 即時聊天室與客服對話
- 線上協作文件的多人編輯狀態
- 股票、運動比分或遊戲狀態的即時推送
- 後台任務進度頁面的 [WebSocket](../../../backend/knowledge-cards/websocket/) / [SSE](../../../backend/knowledge-cards/sse/) 更新

這類服務的主要工程問題是「連線會斷、client 會變慢、server 要清理資源」。Go 很適合把 read loop、write loop、heartbeat、subscription、shutdown 拆成不同 goroutine 與 channel 邊界。當連線失效時，`context`、[deadline](../../../backend/knowledge-cards/deadline/) 與 unregister 流程可以把清理責任收斂到同一個地方。

### 背景 worker：先看工作是否不適合卡住 request

背景 worker 的核心特徵是「工作需要持續處理，並且適合從使用者 request 的等待時間中拆出來」。判斷時可以看某個操作是否需要重試、排程、批次處理，或等待外部系統完成。

接近真實網路服務的例子包括：

- 寄送 email、簡訊或推播通知
- 影片轉檔、圖片壓縮與報表產生
- 每晚同步 CRM、金流或庫存資料
- 消費 [queue](../../../backend/knowledge-cards/queue/) message 並更新內部狀態

這類服務的主要工程問題是「工作要能開始、停止、重試、記錄錯誤並控制速率」。Go 的 `Run(ctx)`、ticker、[worker pool](../../../backend/knowledge-cards/worker-pool/)、channel [queue](../../../backend/knowledge-cards/queue/) 與 structured [log](../../../backend/knowledge-cards/log/) 可以把 worker 生命週期寫清楚。Go 的好處是讓背景流程仍然可取消、可觀測、可測試，而不只是把工作丟到背景。

### 事件處理：先看系統是否圍繞已發生的事流動

事件處理的核心特徵是「系統收到某件已發生的事，再依規則更新狀態或觸發後續行為」。判斷時可以看資料是否常以 `created`、`updated`、`failed`、`completed` 這類事實形式流動。

接近真實網路服務的例子包括：

- 訂單付款成功後更新訂單狀態並發送通知
- 使用者註冊完成後建立歡迎流程與分析事件
- CI job 狀態改變後推送到 [dashboard](../../../backend/knowledge-cards/dashboard/)
- IoT 裝置上報 sensor reading 後觸發告警

這類服務的主要工程問題是「事件來源多、順序可能不同、重複事件需要處理」。Go 的型別可以定義穩定 event envelope，channel 或 [queue](../../../backend/knowledge-cards/queue/) adapter 可以把來源收斂到 processor，processor 再集中處理 validation、dedup、state transition 與 publish。Go 的價值在於讓事件流的每一段責任清楚可測。

### API service：先看服務是否需要清楚的 request 邊界

API service 的核心特徵是「外部 client 用明確 request 取得資料或要求系統執行動作」。判斷時可以看服務是否需要穩定路由、輸入驗證、timeout、error response、[log](../../../backend/knowledge-cards/log/) 與 [metrics](../../../backend/knowledge-cards/metrics/)。

接近真實網路服務的例子包括：

- 手機 App 的會員、訂單、通知 API
- SaaS 產品提供給客戶整合的 public API
- 內部微服務之間的 HTTP/gRPC API
- [dashboard](../../../backend/knowledge-cards/dashboard/) 查詢目前狀態與操作後端任務的 API

這類服務的主要工程問題是「request 進來後要有清楚邊界」。Go 標準庫的 `net/http`、`context`、`encoding/json`、`log/slog` 與 testing package 已經提供服務骨架需要的基本能力。當 API 邊界清楚時，handler 可以專注在傳輸格式，usecase 處理行為規則，repository 或 external client 處理資料依賴。

例如一個通知服務需要同時處理三件事：接收 HTTP callback、把事件放進背景處理流程、再把結果推送給已訂閱的 client。這個服務的主要成本通常在於同時等待網路、管理 client 連線、控制 queue 滿載與清理失效資源；單次計算反而只是其中一小部分。Go 的 goroutine、channel、context 與標準庫 HTTP 可以把這些生命週期寫成明確的程式結構。

相反地，一個只需要三個表單頁面、幾個後台列表和現成權限模板的內部管理系統，主要成本可能在 UI、表單驗證、ORM convention 與後台 scaffolding。這種工作也能用 Go 完成，但選型時應先問：「主要成本是在服務生命週期，還是在框架已經提供的業務頁面組裝？」這個問題比語言效能更接近真正瓶頸。

## 【判讀】架構邊界是否清楚

Go 特別適合邊界清楚的後端服務。當一個系統可以自然拆成輸入、協調、狀態、輸出幾層時，Go 的 struct、interface、package 與明確依賴會讓責任更容易看見。

例如以下這類系統通常是 Go 的好候選：

- [WebSocket](../../../backend/knowledge-cards/websocket/) 即時服務
- notification service
- queue [consumer](../../../backend/knowledge-cards/consumer/)
- log / event pipeline
- 需要清楚 ports/adapters 的 backend service

產品若高度依賴框架提供的大量現成功能，或核心價值在於快速拼接大量業務頁面與模板，選型時應把框架生態列為主要條件。這類情境可以先評估 Python、Ruby、JavaScript/TypeScript 或其他更貼近既有生態的方案。

判斷架構邊界時，可以先畫出資料如何通過系統：

1. 外部請求或事件從哪裡進來
2. 哪一層負責驗證與轉換
3. 哪一層負責狀態轉移或業務規則
4. 哪一層負責回應、推送或記錄

如果這四個問題能自然拆成幾個責任清楚的元件，Go 會讓這些邊界很容易被程式碼表達。handler 可以處理傳輸格式，usecase 可以處理行為規則，repository 或 state owner 可以處理狀態，publisher 或 response layer 可以處理輸出。這種設計不需要大型框架先定義所有路徑，Go 的簡單型別與小介面就能支撐。

如果團隊還在探索商業流程，連資料模型、頁面流程與權限規則都會每天改，框架的 convention 可能更重要。這時候語言選型的重點是「顯式設計的成本是否值得現在承擔」。Go 會鼓勵你把邊界寫清楚；當邊界本身仍在頻繁變動，這種清楚有時會變成前置設計成本。

## 【策略】runtime 與部署條件也是選型的一部分

Go 的優勢不只是語法，還包括 runtime 與部署形態：

- 單一 binary，部署流程簡單
- 啟動速度快，適合 container 與短週期交付
- 標準庫完整，很多服務不需要先找一堆框架
- 可讀性高，長期維護成本較容易控制

如果你的團隊很在意：

- 記憶體用量
- 啟動時間
- 觀測與除錯
- 服務在高流量下的穩定性

那 Go 的工程價值就會很明顯。

部署條件會影響語言價值，因為服務最終要在開發機之外的環境長期運行。假設一個團隊要把多個小服務放進 container，每個服務都需要 [health check](../../../backend/knowledge-cards/health-check-liveness/)、timeout、structured log、[graceful shutdown](../../../backend/knowledge-cards/graceful-shutdown/) 與固定資源限制。Go 的單一 binary 和標準庫讓這些能力可以用相對少的外部依賴完成；服務啟動、部署與回滾也比較容易被平台工程師理解。

另一個常見例子是 CLI 工具或 sidecar service。這類程式常被放進 CI、Kubernetes job、systemd service 或部署腳本中。Go 編譯後的 binary 可以降低 runtime 安裝與版本衝突問題。這是交付形態優勢：當程式要在很多環境中穩定啟動，少一層 runtime 依賴就是一個可觀的工程收益。

## 【執行】哪些情況要先評估其他方案

選型的執行規則是先確認主要瓶頸，再決定語言。以下情境通常應先評估其他語言、框架或平台能力：

| 情境                        | 原因                                      |
| --------------------------- | ----------------------------------------- |
| 極度偏 CRUD 模板系統        | 框架生態可能比語言特性更重要              |
| 大量動態行為與 runtime 配置 | Go 會要求更多顯式設計                     |
| 團隊主要目標是快速試錯      | Go 的工程紀律可能比腳本型語言更有前置成本 |
| 主要瓶頸在前端整合流程      | 主要解法在前端工具鏈、元件生態與產品流程  |

Go 可以處理其中部分情境，但它的工程價值未必對準主要瓶頸。當主要成本在框架生態、動態流程或前端整合時，下一步應先比較那些領域更成熟的工具。

### 極度偏 CRUD 模板系統：先看頁面是否圍繞資料表轉

CRUD 模板系統的核心特徵是「大部分功能都在新增、查詢、修改、刪除資料」。判斷時可以先看產品畫面：如果主要頁面都是列表、篩選、表單、詳情頁、權限設定與匯出報表，系統很可能偏 CRUD。

接近真實網路服務的例子包括：

- 電商平台的商品、訂單、會員、優惠券後台
- 餐廳訂位系統的店家、桌位、時段、訂單管理
- 客服工單系統的 ticket 列表、狀態修改、負責人指派
- 活動報名系統的活動、票種、參加者、付款狀態管理

這類系統的主要工作通常在「快速產生穩定後台功能」。框架如果已經提供 [authentication](../../../backend/knowledge-cards/authentication/)、[authorization](../../../backend/knowledge-cards/authorization/)、ORM、form validation、admin scaffolding、pagination 與 search，團隊會先從框架生態獲得產能。Go 仍然可以負責其中的高流量 API、背景同步、付款 callback 或報表生成，但整個後台產品的主體未必需要先用 Go 開始。

判斷問題可以這樣問：如果拿掉後台表單、列表與權限頁，系統還剩下什麼核心工程問題？如果答案很少，框架模板可能就是主要能力。

### 大量動態行為與 runtime 配置：先看規則是否由使用者定義

動態行為系統的核心特徵是「行為在執行期間由設定、腳本、規則或使用者操作改變」。判斷時可以先觀察：工程師是否常常需要讓非工程使用者自己新增欄位、調整流程、改驗證規則或配置通知條件。

接近真實網路服務的例子包括：

- 表單建置器：使用者可以自己新增欄位、驗證規則與送出後動作
- 工作流系統：管理者可以設定「訂單超過金額就送審」、「狀態改變就寄信」
- CMS：編輯可以建立不同內容模型、欄位與發布流程
- 行銷自動化工具：使用者可以用條件組合出不同受眾與觸發規則

這類系統的主要工程問題在於「如何安全表達動態規則」。Go 的靜態型別會鼓勵你把資料結構與行為先定義清楚；這對穩定服務很有價值，但對高度動態的產品，可能需要額外設計 rule engine、schema registry、plugin boundary 或 DSL。若產品核心就是讓使用者自由配置流程，選型時應把動態模型能力列為主要評估項目。

Go 的合理位置通常在規則執行引擎、事件處理器或高併發 delivery service。管理介面、規則編輯器與 schema 設計器則可能更依賴前端與動態框架生態。

### 團隊主要目標是快速試錯：先看需求是否每天改方向

快速試錯情境的核心特徵是「產品問題尚未被驗證」。判斷時可以觀察需求文件與會議紀錄：如果資料模型、頁面流程、定價方式、權限規則與使用者角色都還在頻繁改，團隊此時最需要的是降低改方向的成本。

接近真實網路服務的例子包括：

- 新創產品的第一版 MVP
- 內部工具的概念驗證
- 尚未確定商業模式的 marketplace
- 正在測試轉換率的報名、購買或 onboarding 流程

這類階段的主要問題是「學到使用者真正需要什麼」。腳本型語言、full-stack framework、低程式碼工具或現成 SaaS 可能更適合先驗證流程。Go 的型別、錯誤處理與顯式邊界會提高長期可維護性，但在問題尚未穩定時，過早建立完整邊界可能會讓每次方向調整都需要較多工程變更。

Go 仍然可以在試錯產品中出現，但通常適合放在已經確定會留下的部分，例如 [webhook](../../../backend/knowledge-cards/webhook/) receiver、背景任務、匯入匯出服務或需要穩定運行的小型 API。產品流程本身可以先用更容易改動的工具探索。

### 主要瓶頸在前端整合流程：先看使用者價值是否發生在介面

前端整合型產品的核心特徵是「使用者價值主要發生在互動介面」。判斷時可以先看產品成功條件：如果最重要的是頁面轉換率、互動動畫、表單體驗、SEO、設計系統、第三方前端 SDK 或多裝置呈現，後端語言通常只是整體解法的一部分。

接近真實網路服務的例子包括：

- 行銷 landing page 與 A/B testing 流程
- 電商結帳頁、購物車、折扣碼與付款 UI
- 內容網站、文件站、會員訂閱頁
- 需要大量拖拉、預覽、即時編輯的設計工具

這類系統的主要工程問題在於前端狀態、元件設計、瀏覽器限制、SEO、分析追蹤與使用者流程。Go 可以提供穩定 API、授權、訂單狀態或事件接收，但選型時要先確認後端 runtime 是否真的在解主要瓶頸。若瓶頸集中在 UI 與產品流程，Next.js、Remix、Nuxt 或其他前端框架生態可能是更直接的評估起點。

判斷問題可以這樣問：使用者感受到的主要差異來自 server 的併發能力，還是來自畫面反應、表單流程、SEO 與第三方整合？如果主要差異在後者，Go 可以是後端配角，不一定是產品主體的第一個選型決策。

選型可以用三個問題收斂：

1. **主要瓶頸是什麼？** 如果瓶頸是大量 I/O、長連線、背景處理、部署穩定性，Go 值得優先評估；如果瓶頸是 UI scaffolding、資料後台或快速試錯，框架生態可能更關鍵。
2. **邊界是否已經清楚？** 如果輸入、規則、狀態與輸出能被穩定拆開，Go 的顯式設計會帶來可讀性；如果流程每天改，先用 convention 強的工具驗證產品可能更合理。
3. **團隊要優化短期探索還是長期維護？** Go 會把錯誤處理、型別、依賴與生命週期攤開寫清楚；這對長期服務是優點，對一次性探索則可能顯得偏重。

因此，選 Go 的結論應該長得像工程判斷。例如：「這個服務會維持上千條長連線，需要明確 timeout、[backpressure](../../../backend/knowledge-cards/backpressure/) 與 [shutdown](../../../backend/knowledge-cards/graceful-shutdown/) 所以 Go 是好候選。」或是：「這個系統主要是後台 CRUD 和權限頁面，框架產能比 runtime 特性更重要，所以先評估 Django、Rails 或 Next.js 生態。」這樣的句子能讓團隊看見選型依據，也能在條件改變時重新評估。

## 小結

Go 適合的是工作負載明確、邊界清楚、需要高併發與穩定維護的服務型系統。它的價值通常出現在長時間運行、明確生命週期、簡單部署與可預期維護上。先把選型條件講清楚，後面的語法與實作才不會變成「學會了工具卻不知道何時使用」。
