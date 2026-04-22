---
title: "Go 入門實戰指南"
date: 2026-04-22
description: "理解 Go 語言精神與核心開發能力"
weight: 32
---

本教學文件專為想學會 Go 的工程師設計。核心目標不是先學會某一種框架或某一類應用，而是理解 Go 的語言精神：簡單、顯式、組合、並發，以及用標準工具寫出可讀、可測、可維護的程式。

範例會從小型 CLI、資料處理、HTTP handler、背景工作與即時通知程式逐步展開。網路服務會作為延伸情境出現，但不是理解本系列的前提。

## 目標讀者

- 有程式經驗的工程師（非 Go 專家）
- 需要維護現有 Go 專案，或準備開發新的 Go 應用
- 想理解 Go 的語言取捨，而不只是記語法
- 需要掌握 Go 的型別、錯誤處理、並發與標準庫
- 未來可能開發 CLI、API、背景服務或即時系統的人

## 學習目標

1. 理解 Go 的設計哲學：簡單、顯式、組合優先
2. 能看懂 Go 專案的 package、module、struct、interface
3. 掌握 Go 的控制流程、錯誤處理、資料建模與測試方法
4. 理解 goroutine、channel、mutex 的設計目的
5. 熟悉 `fmt`、`time`、`encoding/json`、`net/http`、`context` 等常用標準庫
6. 能把 Go 的語言特性應用到 CLI、資料處理與網路服務

## 共用術語

本系列從入門到進階會反覆使用 action、command、domain event、repository、port、adapter、projection 等詞彙。閱讀實戰或重構章節前，可以先參考 [Go 教材核心術語](glossary/)，確認每個詞在本教材中的責任邊界。

## 與 Backend 教材的分工

Go 教材的核心責任是語言能力與程式邊界：package、interface、context、error、goroutine、channel、testing、handler、repository port 與 ports/adapters。具體外部服務的操作與選型會放在跨語言的 [Backend 服務實務指南](../backend/)。

判斷方式很簡單：如果內容是在說「Go 程式如何定義 interface、呼叫依賴、處理取消、包裝錯誤、寫 fake 或 contract test」，它屬於 Go；如果內容是在說「SQLite、PostgreSQL、Redis、RabbitMQ、Kubernetes、Prometheus 這些外部服務如何設定與操作」，它屬於 Backend。Python 或其他後端語言也會用同一套 Backend 分類承接實作知識。

## 教學模組

### [模組零：Go 設計哲學（序章）](00-philosophy/)

從可讀性與維護成本理解 Go 的語言取捨。

- [Go 的簡單哲學與認知負擔](00-philosophy/simplicity/)
- [組合優先：小介面與明確依賴](00-philosophy/composition/)
- [錯誤處理：把失敗路徑寫出來](00-philosophy/error-thinking/)

### [模組一：Go 基礎概念](01-basics/)

快速建立閱讀 Go 專案需要的基本模型。

- [Go 專案結構與 module](01-basics/modules/)
- [變數、零值與短變數宣告](01-basics/variables-zero-values/)
- [控制流程：if、for、switch](01-basics/control-flow/)
- [package、檔案與可見性](01-basics/packages/)
- [從單檔到多檔案](01-basics/growing-files-packages/)
- [函式、方法與 receiver](01-basics/functions-methods/)
- [從入口程式看應用啟動流程](01-basics/main-flow/)
- [Go tooling 與日常開發流程](01-basics/go-tooling-workflow/)

### [模組二：型別、資料與介面](02-types-data/)

用 struct、interface、constant、slice、map 與 JSON tag 表達資料。

- [struct 與 JSON tag](02-types-data/struct-json/)
- [slice 與 map](02-types-data/slices-maps/)
- [interface：用行為定義依賴](02-types-data/interfaces/)
- [常數與 typed string](02-types-data/constants/)
- [指標與資料複製邊界](02-types-data/pointers-copy/)
- [struct embedding 與組合式設計](02-types-data/embedding-composition/)
- [generics 入門：型別參數與約束](02-types-data/generics-basics/)

### [模組三：標準庫實戰](03-stdlib/)

Go 標準庫如何支撐檔案處理、JSON、時間、HTTP 與結構化日誌。

- [fmt、strings 與基本文字處理](03-stdlib/fmt-strings/)
- [time：時間與 duration](03-stdlib/time/)
- [os/io：檔案與輸入輸出](03-stdlib/files-io/)
- [encoding/json：資料交換](03-stdlib/json/)
- [net/http 與 handler 設計](03-stdlib/http-handler/)
- [log/slog：結構化日誌](03-stdlib/slog/)
- [context：取消、逾時與生命週期](03-stdlib/context/)
- [defer 與資源清理](03-stdlib/defer-cleanup/)
- [flag、os/env 與設定邊界](03-stdlib/config-flags-env/)

### [模組四：並發模型](04-concurrency/)

從語言設計理解 goroutine、channel、select 與 mutex。

- [goroutine：背景工作與服務生命週期](04-concurrency/goroutine/)
- [channel：事件流與背壓](04-concurrency/channel/)
- [select：同時等待多種事件](04-concurrency/select/)
- [sync.RWMutex：保護共享狀態](04-concurrency/rwmutex/)

### [模組五：錯誤處理與測試](05-error-testing/)

讓 Go 程式能被驗證、能被除錯、能承受失敗。

- [錯誤回傳與早期返回](05-error-testing/errors/)
- [testing 基礎](05-error-testing/testing-basics/)
- [table-driven test](05-error-testing/table-driven-test/)
- [HTTP handler 測試](05-error-testing/http-handler-test/)
- [時間注入與 deterministic test](05-error-testing/time-injection/)
- [並發行為測試](05-error-testing/concurrency-test/)

### [模組六：實戰應用](06-practical/)

把概念應用到常見 Go 開發工作。這裡開始加入較多網路服務情境。

- [如何新增一個 WebSocket action](06-practical/new-websocket-action/)
- [如何新增一種事件類型](06-practical/new-event-type/)
- [如何擴展狀態資料欄位](06-practical/state-fields/)
- [如何新增背景工作流程](06-practical/new-background-worker/)
- [如何新增結構化記錄欄位](06-practical/structured-recording/)
- [如何新增 repository port](06-practical/repository-port/)

### [模組七：維護與重構](07-refactoring/)

從現有程式中辨識邊界、降低耦合、控制並發風險。

- [把 handler 邏輯拆成可測單元](07-refactoring/handler-boundary/)
- [用 interface 隔離外部依賴](07-refactoring/interface-boundary/)
- [事件去重邏輯的重構策略](07-refactoring/dedup-refactor/)
- [狀態管理的安全邊界](07-refactoring/state-boundary/)
- [以 domain 重新整理 package](07-refactoring/domain-packages/)
- [逐步遷移到 ports/adapters 架構](07-refactoring/hexagonal-migration/)
- [composition root 與依賴組裝](07-refactoring/composition-root/)

## 主題導讀

同一個主題會在不同階段重複出現，這是刻意安排：前面先學 Go 語法與標準庫，後面再把同一概念放進服務設計、重構與生產情境。遇到重疊時，可以依照下列路線閱讀。

| 主題                 | 入門基礎                                                                    | 實戰與重構                                                                                                                               | 進階延伸                                                                                                                                             | Backend 實作                                                                                 |
| -------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| 結構化日誌           | [log/slog](03-stdlib/slog/)                                                 | [結構化記錄欄位](06-practical/structured-recording/)                                                                                     | [結構化日誌欄位設計](../go-advanced/06-production-operations/log-fields/)                                                                            | [可觀測性平台](../backend/04-observability/)                                                 |
| 時間與測試           | [time](03-stdlib/time/)                                                     | [時間注入](05-error-testing/time-injection/)                                                                                             | [時間控制測試](../go-advanced/05-testing-reliability/time-control/)                                                                                  | [部署平台](../backend/05-deployment-platform/)、[可靠性驗證流程](../backend/06-reliability/) |
| 狀態與資料邊界       | [指標與資料複製邊界](02-types-data/pointers-copy/)                          | [狀態欄位](06-practical/state-fields/)、[repository port](06-practical/repository-port/)、[狀態管理重構](07-refactoring/state-boundary/) | [Source of Truth](../go-advanced/04-architecture-boundaries/source-of-truth/)                                                                        | [資料庫與持久化](../backend/01-database/)                                                    |
| 事件系統             | [typed string](02-types-data/constants/)                                    | [新增 domain event](06-practical/new-event-type/)、[事件去重重構](07-refactoring/dedup-refactor/)                                        | [事件去重語義鍵](../go-advanced/04-architecture-boundaries/dedup-key/)、[多來源 event 融合](../go-advanced/04-architecture-boundaries/event-fusion/) | [訊息佇列與事件傳遞](../backend/03-message-queue/)                                           |
| WebSocket 與即時服務 | [HTTP handler](03-stdlib/http-handler/)、[channel](04-concurrency/channel/) | [新增 WebSocket action](06-practical/new-websocket-action/)                                                                              | [WebSocket 服務架構](../go-advanced/02-networking-websocket/)、[跨節點 WebSocket](../go-advanced/07-distributed-operations/cross-node-websocket/)    | [快取與 Redis](../backend/02-cache-redis/)、[訊息佇列](../backend/03-message-queue/)         |
| 專案成長與架構       | [從單檔到多檔案](01-basics/growing-files-packages/)                         | [domain package](07-refactoring/domain-packages/)、[ports/adapters](07-refactoring/hexagonal-migration/)                                 | [架構邊界與事件系統](../go-advanced/04-architecture-boundaries/)                                                                                     | [Backend 服務實務指南](../backend/)                                                          |

## 範例方式

本系列使用中立範例，不要求讀者知道任何特定專案。入門章節會先使用小型、可獨立理解的程式：

```text
examples/
├── hello.go                 # 基本程式入口
├── config.go                # struct、map、錯誤處理
├── parser.go                # 字串與 JSON 處理
├── worker.go                # goroutine、channel、context
└── server.go                # HTTP handler 與背景服務
```

延伸章節會使用一個簡化的即時通知服務：

```text
notify-service/
├── main.go                  # 服務入口、依賴組裝、HTTP route 註冊
├── websocket.go             # WebSocket 連線管理與訊息路由
├── hub.go                   # 訂閱者管理與訊息廣播
├── repository.go            # 狀態儲存與並發保護
├── worker.go                # 背景工作與外部事件讀取
├── handler.go               # HTTP endpoint
├── models.go                # 資料結構與 JSON schema
└── *_test.go                # 單元測試與整合測試
```

這些範例是教學用的簡化版本，目標是說明 Go 語言與工程設計概念，不是要求你熟悉某個既有專案。

## 如何使用本教學

1. **快速查閱**：直接跳到正在處理的概念所在模組
2. **系統學習**：按模組順序閱讀，建立完整 Go 語言模型
3. **實戰練習**：先完成小程式，再進入網路服務範例

---

_文件版本：v0.1.0_
_最後更新：2026-04-22_
_系列狀態：核心初稿完成_
