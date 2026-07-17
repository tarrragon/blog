---
title: "開發測試實務指南"
date: 2026-06-19
description: "整理測試策略分層、協議整合驗證、客戶端可觀測性、錯誤收集與自動化驗證 — 從「測試全過但實機全壞」的結構性盲區出發，建立可操作的品質驗證體系"
weight: 35
tags: ["testing"]
---

開發測試教材的核心目標是教讀者理解「測試通過」和「產品正確」之間的差距如何產生、如何消除。Unit test 用 mock 遮蔽了協議差異、integration test 名為整合實為 fake、widget test 不覆蓋導航路徑 — 這些是測試策略的結構性盲區，來自設計取捨而非疏忽。本教材把品質驗證拆成可分層理解、可分步落地的知識路線。

## 教學出發點

這個系列從一個具體事件出發：一個 Flutter app 有 192 個 unit test 全部通過，但部署到真實 iOS 裝置後，WebSocket 連線、認證握手、終端機渲染三個核心功能全部失敗。根因是所有 test 都用同一個 `FakeWebSocketChannel`，永遠不觸碰真實 WebSocket 協議 — text vs binary frame 差異、auth token handshake、ANSI 控制序列多樣性，全部被 mock 完美遮蔽。

這個事件揭示的是一個跨語言、跨框架的結構性問題：**當被測元件的正確性取決於與外部服務的協議契約時，mock 從結構上就無法驗證這件事。**

## 教學範圍

本系列聚焦「開發團隊能自己建立的品質驗證體系」，不討論 QA 組織或測試管理流程。

| 放在本系列                                                      | 放在其他系列                                                             |
| --------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 測試策略分層（unit / protocol integration / screen state）      | 特定語言的測試框架語法（放語言教材）                                     |
| 客戶端可觀測性（連線生命週期 log、protocol 訊息 log、錯誤回報） | 伺服器端可觀測性平台（放 [Backend 04](/backend/04-observability/)）      |
| 自架 log 收集（同區網、自有伺服器、開發期用途）                 | 商業 APM / crash reporting 產品評測                                      |
| 協議整合測試（WS、gRPC、MQTT 等對真實服務驗證）                 | 負載測試、壓力測試（放 [Backend 09](/backend/09-performance-capacity/)） |
| 自動化 UI 驗證（widget test、Playwright、螢幕狀態覆蓋）         | 手動 QA 流程、測試案例管理工具                                           |
| 測試設計判斷（mock 邊界、assertion 設計、flaky 診斷）           | CI pipeline 設定（放 [Backend 06](/backend/06-reliability/)）            |

## 與 Backend 的關係

Backend 教材的 [模組六：可靠性驗證](/backend/06-reliability/) 聚焦「CI pipeline、load test、fuzz、chaos testing」— 伺服器端的品質閘門。本系列聚焦客戶端和協議層的驗證，兩者互補：

- Backend 告訴你「伺服器怎麼確保自己沒壞」
- 本系列告訴你「客戶端怎麼確保跟伺服器的互動沒壞」

交叉點是 [contract test](/testing/03-protocol-integration-test/http-contract-test/) 和 integration test — Backend 從伺服器端看、本系列從客戶端看，同一個介面的兩面。

## 教學模組

### 模組一：測試策略分層

回答「什麼測試抓什麼問題」。把測試分為三層，每層有明確的職責和盲區：

| 層                   | 職責           | 驗證什麼                               | 抓不到什麼                         |
| -------------------- | -------------- | -------------------------------------- | ---------------------------------- |
| Unit（mock）         | 內部邏輯正確性 | 狀態轉換、錯誤處理、資料轉換           | 協議差異、真實服務行為、環境特異性 |
| Protocol integration | 協議契約正確性 | frame type、auth handshake、序列完整性 | UI 互動、畫面渲染、用戶體驗        |
| Screen state         | UI 行為正確性  | 狀態轉換 UI、導航、用戶操作            | 底層協議、網路行為                 |

判斷原則：被測元件直接對接外部協議（WS、gRPC、SMTP）→ 需要 protocol integration test。外部服務可在本機啟動 → 成本低，強烈建議。Mock 和真實服務之間有協議語意差異 → 必須。

分層之外的補充形態：當 bug 的成因是「我們對後端行為的假設錯誤」時，由測試餵資料的 stub 從結構上驗證不出來（假設與斷言出自同一人之手）。對策是[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)——持有狀態、模擬已證實的後端行為，讓多個前端服務走完整互動鏈；並與模組三的[真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)配對，讓後端行為漂移有地方現形。

> 案例入口：[192 個測試全過、實機全壞](/work-log/testing_three_layer_strategy/) — 三個被 mock 遮蔽的真實問題
>
> 案例入口：[T.C5 凍結參照失效被 stub 遮蔽](/testing/cases/stale-reference-stub-blindspot/) → [T.C6 流程測試首跑抓到順序 bug](/testing/cases/flow-test-first-run-ordering-catch/) — stub 盲區與流程測試補位的成對案例

### 模組二：客戶端可觀測性

回答「使用者的裝置上發生了什麼事」。開發者不在使用者旁邊，需要系統性地收集執行時資訊。

**三層 log 設計**：

| 層級          | 記錄什麼                                            | 誰需要               | 設計時機 |
| ------------- | --------------------------------------------------- | -------------------- | -------- |
| 連線生命週期  | connect / auth / handshake / data / disconnect 每步 | 開發者（debug）      | 企劃階段 |
| Protocol 訊息 | frame type、payload 前綴、auth 結果                 | 開發者（協議 debug） | 企劃階段 |
| 使用者行為    | 畫面切換、按鈕點擊、錯誤遭遇                        | 產品團隊（UX 改善）  | 企劃階段 |

**自架 vs 商業方案的取捨**：

市面上有成熟的監控服務（Sentry、Firebase Crashlytics、Datadog RUM）可以埋在 app 或網頁中收集使用者行為和錯誤資訊。但：

- 早期開發、開發者即使用者、同區網環境 → **自架 log endpoint 就夠**（打 HTTP POST 到自有伺服器、JSON 結構化 log、本機 grep 查詢）
- 多使用者、外部網路、需要 dashboard → 考慮商業方案或自架 ELK / Loki

**設計原則**：log 收集是開發需求的一部分，不是上線後才想的事後工程。連線生命週期的每一步該記什麼 log，應該在功能設計階段就確定 — 跟 API 規格和資料庫 schema 一樣是設計產物。

> 後續章節預定：自架 log endpoint 實作、結構化 log schema 設計、log 分級策略、開發期 vs 上線期 log 切換

### 模組三：協議整合測試

回答「我的 client 跟真實服務的互動是否正確」。這是 unit test（mock）和 E2E test（全棧）之間的一層，專注驗證協議契約。

適用場景：

| 協議      | 測試重點                                         | 成本判斷                  |
| --------- | ------------------------------------------------ | ------------------------- |
| WebSocket | frame type（text/binary）、子協議握手、auth 機制 | 本機啟動 server → 低成本  |
| gRPC      | protobuf 版本相容、stream lifecycle              | 本機 mock server → 中成本 |
| MQTT      | QoS level、retain、will message                  | 本機 broker → 低成本      |
| HTTP API  | status code 語意、header 契約、error format      | 本機 stub → 低成本        |

**自用工具的特殊優勢**：server 和 client 都在同一台機器上時，protocol integration test 的成本極低 — 啟動真實服務然後跑 test，不需要模擬器或真實裝置。

服務無法本機啟動、只有共用測試環境時，這一層以[真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)的形態存在：正規測試而非腳本、與整合套件同分類、預設可執行、離線降級為跳過、憑證失效必須紅燈——每一條設計都對應一個實際踩過的歧路。

> 章節入口：[WebSocket 協議測試](/testing/03-protocol-integration-test/websocket-protocol-test/)、[HTTP contract test](/testing/03-protocol-integration-test/http-contract-test/)、[服務 fixture 管理](/testing/03-protocol-integration-test/service-fixture-management/)
>
> 案例入口：[T.C7 症狀相同、成因兩種](/testing/cases/dual-semantics-attribution/) — 用雙行為測試＋真實後端驗證切開前後端責任

### 模組四：自動化 UI 驗證

回答「畫面上的東西是否如設計工作」。Widget test、Playwright、screen state coverage。

> 後續章節預定：widget test 的狀態覆蓋策略、Playwright 驗證流程、螢幕截圖比對

### 模組五：測試設計判斷

回答「這個斷言該怎麼寫」。Mock 邊界判斷、assertion 設計（計時依賴、浮點精度、快取驗證）、flaky test 診斷，以及[測試註解與命名紀律](/testing/05-test-design-judgment/test-comment-and-naming-discipline/)——測試內容由名稱與斷言自述、reason 寫失敗後果與處置、檔頭陳述目的不論證需求、分析詞彙與開發過程不入程式碼。

> 章節入口：[mock 邊界判斷](/testing/05-test-design-judgment/mock-boundary-decision/)、[斷言品質三問](/testing/05-test-design-judgment/assertion-quality/)、[flaky test 根因分類](/testing/05-test-design-judgment/flaky-test-root-cause/)
>
> 案例入口：[T.C8 fire-and-forget 編排的測試競態](/testing/cases/fire-and-forget-test-race/)、[T.C9 外接螢幕訊息序列斷言](/testing/cases/outbox-sequence-external-display/)

## 學習路線

| 路線           | 適合讀者                               | 建議順序                        | 讀完能做什麼                                     |
| -------------- | -------------------------------------- | ------------------------------- | ------------------------------------------------ |
| 測試策略入門   | 想理解測試為什麼會漏掉真實問題         | 模組一 → 模組三 → 模組二        | 能判斷哪些行為需要 protocol test、哪些 mock 就夠 |
| 客戶端品質閉環 | 想在開發期就收集到 runtime 資訊        | 模組二 → 模組三 → 模組四        | 能設計 log 收集方案並在 CI 中驗證協議正確性      |
| 測試設計精進   | 已有測試但常遇 flaky 或 false positive | 模組五 → 模組一（重新審視分層） | 能診斷 flaky 根因、改善 assertion 設計           |

## 教學寫作方向

本系列的寫作原則與 Backend 一致：先回答「這個能力解決什麼問題」，再展開判讀訊號、風險擴散、決策順序。

具體到測試教材的補充：

1. **每個測試層級都要說明「抓不到什麼」** — 知道盲區比知道能力更重要
2. **自架方案先於商業方案** — 本系列的讀者多數是小團隊或個人開發者，先教能自己建的，再說什麼時候該引入商業方案
3. **Log 設計是需求，不是 debug 工具** — 連線生命週期 log 應該在功能規格階段就確定，跟 API schema 一樣

---

_文件版本：v0.2.0_
_最後更新：2026-07-17_
_系列狀態：模組一/三補入假後端與真實後端驗證配對章節、模組五補入測試註解與命名紀律章、案例庫擴充 T.C5–T.C9_
