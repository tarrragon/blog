---
title: "開發測試實務指南"
date: 2026-06-19
description: "測試全過而實機全壞、或程式碼由 agent 產出而無法逐行讀時，用來決定驗證該掛在哪幾層、每一層各自守不住什麼"
weight: 35
tags: ["testing"]
---

開發測試教材的核心目標是教讀者理解「測試通過」和「產品正確」之間的差距如何產生、如何消除。Unit test 用 mock 遮蔽了協議差異、integration test 名為整合實為 fake、widget test 不覆蓋導航路徑 — 這些是測試策略的結構性盲區，來自設計取捨而非疏忽。本教材把品質驗證拆成可分層理解、可分步落地的知識路線。

## 教學出發點

這個系列從一個具體事件出發：一個 Flutter app 有 192 個 unit test 全部通過，但部署到真實 iOS 裝置後，WebSocket 連線、認證握手、終端機渲染三個核心功能全部失敗。根因是所有 test 都用同一個 `FakeWebSocketChannel`，永遠不觸碰真實 WebSocket 協議 — text vs binary frame 差異、auth token handshake、ANSI 控制序列多樣性，全部被 mock 完美遮蔽。

這個事件揭示的是一個跨語言、跨框架的結構性問題：**當被測元件的正確性取決於與外部服務的協議契約時，mock 從結構上就無法驗證這件事。**

程式碼由 agent 產出時，失效的是另一件事：判準的**來源**。測試可能與實作出自同一次生成，於是它編碼的是實作以為自己該做什麼——分層照舊成立，可信度不成立。這條線走[模組六](/testing/06-agent-authored-code/)。

## 教學範圍

本系列聚焦「開發團隊能自己建立的品質驗證體系」，不討論 QA 組織或測試管理流程。

| 放在本系列                                                      | 放在其他系列                                                                                     |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 測試策略分層（unit / protocol integration / screen state）      | 特定語言的測試框架語法（放語言教材）                                                             |
| 客戶端可觀測性（連線生命週期 log、protocol 訊息 log、錯誤回報） | 伺服器端可觀測性平台（放 [Backend 04](/backend/04-observability/)）                              |
| 自架 log 收集（同區網、自有伺服器、開發期用途）                 | 商業 APM / crash reporting 產品評測                                                              |
| 協議整合測試（WS、gRPC、MQTT 等對真實服務驗證）                 | 負載測試、壓力測試（放 [Backend 09](/backend/09-performance-capacity/)）                         |
| 自動化 UI 驗證（widget test、Playwright、螢幕狀態覆蓋）         | 手動 QA 流程、測試案例管理工具                                                                   |
| 測試設計判斷（mock 邊界、assertion 設計、flaky 診斷）           | CI pipeline 設定（放 [Backend 06](/backend/06-reliability/)）                                    |
| Agent 產出程式碼的驗證（判準出處、等價類、突變分數）            | LLM 模型本身的評估與 benchmark（放 [LLM 04](/llm/04-applications/benchmarking-and-evaluation/)） |

## 與 Backend 的關係

Backend 教材的 [可靠性驗證模組](/backend/06-reliability/) 聚焦「CI pipeline、load test、fuzz、chaos testing」— 伺服器端的品質閘門。本系列聚焦客戶端和協議層的驗證，兩者互補：

- Backend 回答「伺服器怎麼確保自己沒壞」
- 本系列回答「客戶端怎麼確保跟伺服器的互動沒壞」

交叉點是 [contract test](/testing/03-protocol-integration-test/http-contract-test/) 和 integration test — Backend 從伺服器端看、本系列從客戶端看，同一個介面的兩面。

## 教學模組

### 模組一：測試策略分層

回答「什麼測試抓什麼問題」。把測試分為三層，每層有明確的職責和盲區：

| 層                   | 職責           | 驗證什麼                               | 抓不到什麼                         |
| -------------------- | -------------- | -------------------------------------- | ---------------------------------- |
| Unit（mock）         | 內部邏輯正確性 | 狀態轉換、錯誤處理、資料轉換           | 協議差異、真實服務行為、環境特異性 |
| Protocol integration | 協議契約正確性 | frame type、auth handshake、序列完整性 | UI 互動、畫面渲染、用戶體驗        |
| Screen state         | UI 行為正確性  | 狀態轉換 UI、導航、用戶操作            | 底層協議、網路行為                 |

Unit 這一層的「單元」有兩種定義，決定替身出現在模組邊界還是類別之間，見 [Sociable vs Solitary Unit Test](/testing/knowledge-cards/unit-definition-two-schools/)。

判斷原則：被測元件直接對接外部協議（WS、gRPC、SMTP）→ 需要 protocol integration test。外部服務可在本機啟動 → 成本低，強烈建議。Mock 和真實服務之間有協議語意差異 → 必須。

分層之外的補充形態：當 bug 的成因是「我們對後端行為的假設錯誤」時，由測試餵資料的 stub 從結構上驗證不出來（假設與斷言出自同一人之手）。對策是[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)——持有狀態、模擬已證實的後端行為，讓多個前端服務走完整互動鏈；並與模組三的[真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)配對，讓後端行為漂移有地方現形。

> 案例入口：[192 個測試全過、實機全壞](/work-log/testing_three_layer_strategy/) — 三個被 mock 遮蔽的真實問題
>
> 案例入口：[T.C5 凍結參照失效被 stub 遮蔽](/testing/cases/stale-reference-stub-blindspot/) → [T.C6 流程測試首跑抓到順序 bug](/testing/cases/flow-test-first-run-ordering-catch/) — stub 盲區與流程測試補位的成對案例
>
> 章節入口：[無測試 legacy 專案的起步順序](/testing/01-test-strategy-layers/legacy-test-bootstrap/) — 接手零測試專案、從風險集中處判斷第一批測試該從哪層開始建

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

> 章節入口：[三層 log 設計](/testing/02-client-observability/three-layer-log-design/)、[功能規格中的 log 點定義方法](/testing/02-client-observability/log-point-in-spec/)、[自架 log endpoint vs 商業方案的取捨判斷](/testing/02-client-observability/log-endpoint-tradeoff/)、[「事後補 log」vs「設計產物 log」的品質差異](/testing/02-client-observability/hotfix-log-vs-designed-log/)

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

> 章節入口：[WebSocket 協議測試](/testing/03-protocol-integration-test/websocket-protocol-test/)、[HTTP contract test](/testing/03-protocol-integration-test/http-contract-test/)、[服務 fixture 管理](/testing/03-protocol-integration-test/service-fixture-management/)、[測試憑證管理](/testing/03-protocol-integration-test/credential-management/)
>
> 案例入口：[T.C7 症狀相同、成因兩種](/testing/cases/dual-semantics-attribution/) — 用雙行為測試＋真實後端驗證切開前後端責任

### 模組四：自動化 UI 驗證

回答「畫面元素是否如設計運作」。Widget test、Playwright、screen state coverage。

> 章節入口：[Widget test 的狀態覆蓋策略](/testing/04-ui-automation/state-coverage-strategy/)、[Playwright 瀏覽器驗證流程](/testing/04-ui-automation/playwright-verification/)、[螢幕截圖比對](/testing/04-ui-automation/visual-regression/)、[導航路徑 test](/testing/04-ui-automation/navigation-path-test/)

### 模組五：測試設計判斷

回答「這個斷言該怎麼寫」。Mock 邊界判斷、assertion 設計（計時依賴、浮點精度、快取驗證）、flaky test 診斷，以及[測試註解與命名紀律](/testing/05-test-design-judgment/test-comment-and-naming-discipline/)——測試內容由名稱與斷言自述、reason 寫失敗後果與處置、檔頭陳述目的不論證需求、分析詞彙與開發過程不入程式碼。

> 章節入口：[mock 邊界判斷](/testing/05-test-design-judgment/mock-boundary-decision/)、[斷言品質三問](/testing/05-test-design-judgment/assertion-quality/)、[flaky test 根因分類](/testing/05-test-design-judgment/flaky-test-root-cause/)、[Flaky test 團隊治理](/testing/05-test-design-judgment/flaky-team-governance/)、[Test data 代表性](/testing/05-test-design-judgment/test-data-representativeness/)、[測試的價值發生在它變紅的那一刻](/testing/05-test-design-judgment/test-as-change-guard/)
>
> 案例入口：[T.C8 fire-and-forget 編排的測試競態](/testing/cases/fire-and-forget-test-race/)、[T.C9 外接螢幕訊息序列斷言](/testing/cases/outbox-sequence-external-display/)

### 模組六：Agent 產出程式碼的驗證

回答「這段程式碼不是我寫的，我憑什麼相信它是對的」。前五個模組預設寫程式的人與寫測試的人是同一位、而且那個人會讀自己的程式碼；程式碼由 agent 產出時這兩個前提各失效一半。失效的不是分層，是判準的來源與可信度。

| 位置     | 前五模組的前提         | Agent 產出時的實情                     |
| -------- | ---------------------- | -------------------------------------- |
| 判準來源 | 測試由懂需求的人寫     | 測試可能與實作同源，編碼的是實作的理解 |
| 交付條件 | 驗收條件通過即可交付   | 通過的是一個等價類，不是一個程式       |
| 品質指標 | 覆蓋率高代表測試寫得夠 | 覆蓋率可以在斷言為空的情況下達成       |
| 判準形態 | 預期值人算得出來       | 產出規模讓逐例斷言成為瓶頸             |

> 章節入口：[判準的推導來源](/testing/06-agent-authored-code/test-provenance-independence/)、[驗收條件的等價類](/testing/06-agent-authored-code/acceptance-equivalence-class/)、[品質閘門的更替](/testing/06-agent-authored-code/coverage-to-mutation-gate/)、[判準寫不下來的時候](/testing/06-agent-authored-code/oracle-beyond-examples/)
>
> 案例入口：[T.C10 同一組驗收通過八個不同的程式](/testing/cases/acceptance-passes-eight-different-programs/) — 外部公開實驗，把關卡放行的等價類實際量了一次

## 學習路線

| 路線                    | 適合讀者                                            | 建議順序                                                                                                  | 讀完能做什麼                                                         |
| ----------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 測試策略入門            | 想理解測試為什麼會漏掉真實問題                      | 模組一 → 模組三 → 模組二                                                                                  | 能判斷哪些行為需要 protocol test、哪些 mock 就夠                     |
| 客戶端品質閉環          | 想在開發期就收集到 runtime 資訊                     | 模組二 → 模組三 → 模組四                                                                                  | 能設計 log 收集方案並在 CI 中驗證協議正確性                          |
| 測試設計精進            | 已有測試但常遇 flaky 或 false positive              | 模組五 → [單元的兩種定義](/testing/knowledge-cards/unit-definition-two-schools/) → 模組一（重新審視分層） | 能診斷 flaky 根因、改善 assertion 設計、判斷測試耦合的是行為還是結構 |
| 後端不可控的前端防線    | 後端服務碰不到、只有共用測試環境、想從零建防線      | 模組一（語意級假後端）→ 模組三（真實後端驗證）→ 模組五                                                    | 能建立有狀態假後端跑流程測試、並讓後端行為漂移有地方現形             |
| 驗證 agent 產出的程式碼 | 程式碼由 agent 寫、不打算逐行讀，想知道驗證該落在哪 | 模組六 → 模組五（mock 邊界判斷與斷言品質）                                                                | 能量出驗收條件的射程、挑不會被灌水的品質閘門、指出哪些工作交不出去   |

## Backlog

| 項目                                                  | 類型   | 前置條件                                              | 規模         |
| ----------------------------------------------------- | ------ | ----------------------------------------------------- | ------------ |
| 案例庫三處覆蓋缺口（模組二、四、五）                  | 案例   | 清單與逐項條件在[案例庫的覆蓋缺口段](/testing/cases/) | 小（3 則）   |
| 突變測試工具對照（Stryker / PIT / mutmut）            | vendor | 模組六的判準在實際專案用過一輪之後，且工具名單重查過  | 小（1 篇）   |
| 性質式測試工具對照（Hypothesis / fast-check / jqwik） | vendor | 同上；工具生態逐年變動，動工前重查現行實作            | 小（1 篇）   |
| 探究（exploratory）的操作層                           | 主章   | 模組六已界定它的存在與邊界、站內無操作方法            | 中（2-3 章） |
| LLM 04 兩章回指 Testing 的反向路由                    | 跨模組 | 模組六已補去程（評估章與人機協作章各一條），回程待補  | 小（2 條）   |
| Solitary 的操作層（由外而內的節奏、替身當設計手段）   | 主章   | 站內有實際用 Solitary 做過一輪的紀錄；目前只指向原著  | 小（1 章）   |
| 模組邊界怎麼認（測試單元意義下）                      | 知識卡 | 待驗證：全站五處各給一種答案、無一處承接這個判斷本身  | 小（1 張）   |
| Test-First vs Test-Last                               | 知識卡 | 待驗證：八篇以上裸用、無卡；屬支撐術語且在基線外      | 小（1 張）   |
| 測試維護成本怎麼量                                    | 主章   | 待驗證：三個計量單位站內無人承接怎麼取得              | 小（1 章）   |

### 規劃敘事

補出探究章時要回頭改兩個地方——#277 修法 4 與本段——它們現在都寫著「站內目前只界定了這一區、沒有操作方法」，那句話會在那一天變成錯的，而沒有任何機制會自動發現。

後三項全部由 Round 3 的共同前提盤點產出，形態相同：某個判斷被多篇當前提使用、而沒有任何一篇承接它。「模組邊界怎麼認」在五處各有一種說法（對外承諾什麼 / 一組類別加公開 API / UseCase 層），而 [TDD 的兩種做法](/record/behavior-first-tdd-methodology/)自己就寫著「邊界找錯的常見形態」——等於承認這是會出錯的判斷，卻只用一句帶過。「測試維護成本怎麼量」更尖銳：那篇給了三個計量單位，而同一篇的正文說沒有人在量（「改測試的人就是改實作的人，同一次提交內完成」）。判準要的輸入，文章自己說取不到。三項都標**待驗證**，動筆前要先跑一次全站反證，錯誤的缺卡宣告會誘發重複建卡、比漏報更貴。

Solitary 操作層那一項與探究是同一形態的缺口——界定了它存在、沒說走進去之後做什麼。[TDD 的兩種做法](/record/behavior-first-tdd-methodology/)說明了選 Solitary 的兩類理由、並明說它的操作層不展開，而站內目前只把讀者指向 Freeman 與 Pryce 的原著。它跟探究一樣要先有實際紀錄再動筆：由外而內的節奏與替身當設計手段，照書抄一遍寫得出章、但給不出「什麼時候該停止往內推」這種只有做過才知道的判準。

探究那一項是多輪審查抓出來的：模組六有四處說「判準寫不下來的那一區交不出去、把人力移過去」，而沒有一處說移過去之後做什麼。站內目前只有 [testing vs checking](/testing/knowledge-cards/testing-vs-checking/) 界定了這一區的存在與邊界，操作方法一個字都沒有——寫之前要先有實際做過探索式測試的紀錄，否則會變成把書上的清單抄一遍。

模組六目前的四章走的是判準這條線（來源、射程、品質、形態），刻意不碰工具操作——突變測試與性質式測試的工具生態變動快，判準穩定而工具不穩定，混寫會讓整章的半衰期跟著工具走。vendor 那兩篇要等模組六的判準在實際專案裡用過一輪之後再寫，否則會退化成安裝教學。

案例的三個缺口都受限於採集而非寫作，逐項條件寫在案例庫自己的覆蓋缺口段、這裡不複製第二份：自架 log 與量化 flaky 需要真實資料，widget test 的 false negative 要找到有完整前後對照的公開案例。T.C10 開了外部案例這條路之後，後兩項的門檻降低——可回溯的公開 repo 與 CI 統計都算合格來源。

## 教學寫作方向

本系列的寫作原則與 Backend 一致：先回答「這個能力解決什麼問題」，再展開判讀訊號、風險擴散、決策順序。

具體到測試教材的補充：

1. **每個測試層級都要說明「抓不到什麼」** — 知道盲區比知道能力更重要
2. **自架方案先於商業方案** — 本系列的讀者多數是小團隊或個人開發者，先教能自己建的，再說什麼時候該引入商業方案
3. **Log 設計是需求，不是 debug 工具** — 連線生命週期 log 應該在功能規格階段就確定，跟 API schema 一樣

---

_文件版本：v0.3.0_
_最後更新：2026-08-24_
_系列狀態：新增模組六（Agent 產出程式碼的驗證，4 章）、知識卡擴充 7 張（判準與出處 3 張、判準品質 4 張）、案例庫收入首則外部案例 T.C10、補 Backlog 段_
