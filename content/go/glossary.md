---
title: "Go 教材核心術語"
date: 2026-04-22
description: "整理 Go 入門與進階篇共用的架構、事件、狀態與邊界詞彙"
weight: 99
---

本頁整理 Go 入門篇與進階篇反覆使用的詞彙。核心目的不是建立一套大型架構名詞表，而是讓同一個概念在不同章節中保持同一種意思。

Go 教材中的術語應先服務可讀性：詞彙要幫助工程師判斷責任邊界，而不是把簡單程式包裝成複雜架構。小程式可以只有 `main.go`，服務變大後才逐步引入 event、repository、port、adapter、[projection](../../backend/knowledge-cards/projection/) 等詞彙。

## 輸入與行為

### Action

`action` 表示 client 對服務提出的意圖。它通常來自 [WebSocket](../../backend/knowledge-cards/websocket/) message、HTTP request 或 CLI input，還沒有完成驗證、授權或業務規則套用。

例如 `subscribe_topic` 可以是 WebSocket action，代表 client 想訂閱某個 [topic](../../backend/knowledge-cards/topic/)。它進入系統後，router 會先解析 payload，再交給 usecase 或 subscription manager。

延伸閱讀：[如何新增一個 WebSocket action](../06-practical/new-websocket-action/)、[訂閱模型與訊息路由](../../go-advanced/02-networking-websocket/subscription-routing/)。

### Command

`command` 表示 application layer 接受的行為輸入。它已經脫離 HTTP JSON、WebSocket frame 或 CLI flag 的外部格式，變成 usecase 可以理解的資料。

例如 `CreateNotificationCommand` 可以由 HTTP handler、WebSocket router 或背景 worker 建立。handler 負責把 request DTO 轉成 command，usecase 負責處理 command 的規則。

延伸閱讀：[把 handler 邏輯拆成可測單元](../07-refactoring/handler-boundary/)。

### Usecase

`usecase` 表示一個 application 行為。它負責協調 validation、repository、event publisher、clock、[transaction](../../backend/knowledge-cards/transaction/) 等能力，並保留「這件事如何完成」的規則。

usecase 的重點是行為邊界，不是資料夾名稱。小型程式可以先用函式表達 usecase；當 handler、worker、WebSocket action 都需要共用同一套規則時，再把 usecase 抽出來。

延伸閱讀：[把 handler 邏輯拆成可測單元](../07-refactoring/handler-boundary/)、[逐步遷移到 ports/adapters 架構](../07-refactoring/hexagonal-migration/)。

## 事件系統

### Domain Event

`domain event` 表示系統承認已經發生的內部事實。它和 action 不同：action 是請求，domain event 是經過系統語意整理後的事實。

例如 `notification.created` 可以表示通知已被建立。這個事件可以來自 HTTP request、WebSocket action、[queue](../../backend/knowledge-cards/queue/) message 或 background worker，但進入 processor 前應先被 normalize 成同一種內部模型。

延伸閱讀：[如何新增一種事件類型](../06-practical/new-event-type/)、[事件來源、處理流程與狀態邊界](../../go-advanced/04-architecture-boundaries/component-boundaries/)。

### DomainEvent

`DomainEvent` 是範例程式中用來承載 domain event 的 Go 型別。它通常包含事件類型、來源、主體、發生時間、接收時間與 payload。

名稱使用 PascalCase 是因為它是 Go 型別；概念說明時使用 `domain event`，程式碼型別使用 `DomainEvent`。

### Event Envelope

`event envelope` 是事件外層的穩定欄位集合。它通常描述 event id、event type、source、subject、occurred time、received time、schema version、[correlation id](../../backend/knowledge-cards/correlation-id/) 與 payload。

envelope 的價值是讓不同事件共享同一種路由、去重、記錄與觀測方式。payload 則保留每種事件自己的資料內容。

延伸閱讀：[如何新增一種事件類型](../06-practical/new-event-type/)、[多來源 event 融合](../../go-advanced/04-architecture-boundaries/event-fusion/)。

### Event Log

`event log` 表示記錄 domain event 的事實紀錄。它用來追蹤系統承認過哪些事件，重點是事件語意、順序、去重與後續查詢。

[event [log](../../backend/knowledge-cards/log/)](../backend/knowledge-cards/event-log) 和 structured log 的用途不同。structured log 服務操作診斷，event log 服務業務事實追蹤；兩者可以共享 `trace_id`、`event_id`、`subject_id` 等欄位，但不應互相取代。

延伸閱讀：[如何新增結構化記錄欄位](../06-practical/structured-recording/)、[結構化日誌欄位設計](../../go-advanced/06-production-operations/log-fields/)。

### Event Store

`event store` 是具備持久化、排序、replay、schema 演進與 transaction 語意的事件儲存。它比 event log 承擔更高的資料一致性責任。

教材中的 event log 先用來建立事件記錄概念；當系統需要 replay、跨節點處理或以事件歷史作為狀態來源時，才需要討論 event store。

延伸閱讀：[Durable queue、outbox 與 idempotency](../../go-advanced/07-distributed-operations/outbox-idempotency/)。

### Event Sourcing

`event sourcing` 表示以事件歷史作為狀態真相來源。系統不是只保存目前狀態，而是透過事件序列重建狀態。

保留 event log 不等於採用 event sourcing。許多服務會記錄 domain event 作為審計或整合用途，但 [source of truth](../../backend/knowledge-cards/source-of-truth/) 仍然是資料庫中的 current state。

延伸閱讀：[Source of Truth：狀態邊界](../../backend/knowledge-cards/source-of-truth/)。

### Dedup Key

`dedup key` 表示用 domain 語意判斷兩筆事件是否是同一件事的 key。它通常由 subject kind、subject id、event type、外部序號或時間窗口組成。

dedup key 的重點是「同一件事」，不是「同一份 bytes」。raw payload hash 可以偵測完全相同的輸入，但無法處理不同來源描述同一個 domain fact 的情境。

延伸閱讀：[事件去重邏輯的重構策略](../07-refactoring/dedup-refactor/)、[事件去重與語義鍵設計](../../go-advanced/04-architecture-boundaries/dedup-key/)。

### Idempotency Key

`idempotency key` 表示外部呼叫或重試流程用來安全重複執行的 key。它常出現在 HTTP request、queue message 或 outbox publish 流程中。

[idempotency](../../backend/knowledge-cards/idempotency/) key 和 dedup key 的責任不同。idempotency key 保護同一次操作的重試；dedup key 保護 domain 層面上同一件事的重複描述。

延伸閱讀：[Durable queue、outbox 與 idempotency](../../go-advanced/07-distributed-operations/outbox-idempotency/)。

## 狀態與資料模型

### Repository

`repository` 表示狀態或資料存取的邊界。它負責保存與讀取某一類資料，並讓外部呼叫者不需要知道資料目前存在 memory、[database](../../backend/knowledge-cards/database/) 或遠端服務。

repository 的核心價值是權責集中。當狀態轉移、copy boundary、transaction 或查詢模型開始變複雜時，把資料能力集中在 repository 會比讓 handler 直接操作 map 更穩定。

延伸閱讀：[如何新增 repository port](../06-practical/repository-port/)、[狀態管理的安全邊界](../07-refactoring/state-boundary/)。

### Repository Port

`repository port` 表示 application layer 需要的資料能力介面。它由 usecase 的需求定義，而不是由資料庫表格或具體儲存技術定義。

例如 usecase 只需要 `Save` 和 `FindByID`，port 就只暴露這兩個方法。memory repository、SQL repository 或 test fake 都可以實作同一個 port。

延伸閱讀：[如何新增 repository port](../06-practical/repository-port/)、[資料庫 transaction 與 schema migration](../../go-advanced/07-distributed-operations/database-transactions/)。

### State Owner

`state owner` 表示擁有某份可變狀態寫入權的元件。它可以是 mutex 保護的 repository，也可以是單一 goroutine 持有狀態並透過 channel 接收 command。

state owner 的重點是只有一個地方能決定狀態如何改變。其他元件應送入 command 或 event，而不是直接修改內部 map、slice 或 pointer。

延伸閱讀：[共享狀態與複製邊界](../../go-advanced/01-concurrency-patterns/shared-state/)、[Source of Truth：狀態邊界](../../backend/knowledge-cards/source-of-truth/)。

### Source of Truth

`source of truth` 表示狀態轉移的寫入權責。它不是某一種資料庫，也不是某一份 struct，而是系統承認「誰能決定目前狀態」的邊界。

小型服務的 source of truth 可能是 memory repository；加入資料庫後，source of truth 仍然包含 application 的狀態規則、transaction 邊界與持久化資料。

延伸閱讀：[Source of Truth：狀態邊界](../../backend/knowledge-cards/source-of-truth/)。

### Projection / Read Model

`projection` 或 `read model` 表示為讀取需求整理出的資料模型。它可以來自 domain state、event history 或其他來源，目標是讓查詢、列表、即時推送或 UI 顯示更直接。

projection 可以提升讀取效率與簡化 response 組裝，但它不應反過來成為狀態真相。狀態規則仍然應由 repository、state owner 或 usecase 控制。

延伸閱讀：[如何擴展狀態資料欄位](../06-practical/state-fields/)、[Source of Truth：狀態邊界](../../backend/knowledge-cards/source-of-truth/)。

### Response View

`response view` 表示對外輸出的資料形狀。它負責 JSON tag、`omitempty`、顯示文字、相容性欄位與 API contract。

response view 的核心責任是翻譯內部資料給外部使用者。顯示文字、前端 badge、API 版本相容欄位通常應放在 response view，而不是混進 domain state。

延伸閱讀：[如何擴展狀態資料欄位](../06-practical/state-fields/)。

### DTO

`DTO` 表示資料傳輸形狀。它常用於 HTTP request、HTTP response、queue message、WebSocket payload 或外部 API client。

DTO 的責任是描述邊界格式。它可以有 JSON tag、相容性欄位與外部命名慣例，但不應直接取代 domain model、repository model 或 command。

延伸閱讀：[把 handler 邏輯拆成可測單元](../07-refactoring/handler-boundary/)、[以 domain 重新整理 package](../07-refactoring/domain-packages/)。

### Copy Boundary

`copy boundary` 表示回傳或接收 slice、map、pointer 時用複製保護狀態所有權的邊界。它防止呼叫端透過引用修改 repository 內部資料。

Go 的 slice、map 與 pointer 都可能共享底層資料，所以 repository 回傳資料時要判斷是否需要 shallow copy 或 deep copy。資料量大時，可以改用分頁、projection 或 snapshot cache 來控制成本。

延伸閱讀：[指標與資料複製邊界](../02-types-data/pointers-copy/)、[共享狀態與複製邊界](../../go-advanced/01-concurrency-patterns/shared-state/)。

## 架構邊界

### Port

`port` 表示 application 依賴的能力介面。它描述「我需要什麼能力」，例如儲存通知、發布事件、讀取外部資料或取得現在時間。

Go 的 port 通常是小 interface。它應由使用方定義，讓 application 可以依賴抽象能力，而不是依賴具體資料庫、message [broker](../../backend/knowledge-cards/broker/) 或 [HTTP client](../../backend/knowledge-cards/http-client/)。

延伸閱讀：[用 interface 隔離外部依賴](../07-refactoring/interface-boundary/)、[逐步遷移到 ports/adapters 架構](../07-refactoring/hexagonal-migration/)。

### Adapter

`adapter` 表示把外部技術或協定接到 application port 的實作或轉換層。它可以是 HTTP handler、WebSocket router、SQL repository、queue [consumer](../../backend/knowledge-cards/consumer/) 或 external API client。

adapter 的核心責任是翻譯邊界格式。application 不應知道 HTTP body、SQL row、queue message 或 WebSocket frame 的細節。

延伸閱讀：[逐步遷移到 ports/adapters 架構](../07-refactoring/hexagonal-migration/)。

### Inbound Adapter

`inbound adapter` 表示把外部輸入轉成 application command 或 domain event 的 adapter。HTTP handler、WebSocket router、CLI command、queue consumer 都可以是 inbound adapter。

inbound adapter 通常負責 parsing、基本 validation、身份資訊提取與錯誤轉換。行為規則應交給 usecase 或 processor。

延伸閱讀：[把 handler 邏輯拆成可測單元](../07-refactoring/handler-boundary/)、[read pump / write pump 模式](../../go-advanced/02-networking-websocket/read-write-pump/)。

### Outbound Adapter

`outbound adapter` 表示實作 application port 並連接外部系統的 adapter。SQL repository、Redis cache、message publisher、email sender、external API client 都屬於這類。

outbound adapter 的重點是隔離技術細節。usecase 依賴 port；adapter 承擔 retry、serialization、connection、[timeout](../../backend/knowledge-cards/timeout/) 與外部錯誤轉換。

延伸閱讀：[如何新增 repository port](../06-practical/repository-port/)、[資料庫 transaction 與 schema migration](../../go-advanced/07-distributed-operations/database-transactions/)。

### Normalizer

`normalizer` 表示把 raw input 轉成內部模型的元件。它常出現在事件系統中，負責把 HTTP callback、queue message 或外部 API response 轉成 `DomainEvent`。

normalizer 的責任是建立內部一致性。不同來源可以有不同 raw format，但進入 processor 前應變成一致的 domain event。

延伸閱讀：[事件來源、處理流程與狀態邊界](../../go-advanced/04-architecture-boundaries/component-boundaries/)。

### Processor

`processor` 表示處理 domain event 或 background job 的元件。它負責套用規則、去重、更新狀態、寫入 event log 或呼叫 publisher。

processor 應處理已經 normalize 的資料。它不應依賴 HTTP request body、WebSocket frame 或 queue message 的原始格式。

延伸閱讀：[如何新增背景工作流程](../06-practical/new-background-worker/)、[事件來源、處理流程與狀態邊界](../../go-advanced/04-architecture-boundaries/component-boundaries/)。

## 工具與靜態分析

### AST Walker

`AST walker` 表示用 visitor pattern 對解析後的抽象語法樹做 DFS 走訪，並在每個節點上套用規則或收集資訊的處理方式。在 Go 中，`ast.Walk` 是 `go/ast` 與 `goldmark/ast` 都採用的 API 慣例：傳入 root node 跟 walker 函式，framework 負責遞迴下降、把 entering / exiting 時機告訴你。

walker 的責任是**把樹的走訪邏輯外部化**，讓規則本身只關心「這個節點我要做什麼」。多條規則可以共用同一次走訪；複雜的 context（例如父節點是什麼、目前在哪個 heading 層級）由 walker 狀態機累積，不污染 rule 程式碼。Block vs inline 節點的判讀是 walker 用法最常見的陷阱 — 對 inline 節點呼叫 `Lines()` 會 panic，因此需要走上去找最近的 block 節點再取位置。

延伸閱讀：[goldmark AST 入門](../09-tooling-and-analysis/goldmark-ast-basics/)、[什麼是 AST](../../posts/what-is-ast/)。

### Idempotent 文字改寫

`idempotent 文字改寫` 表示對同一輸入跑一次或多次、結果相同的轉換契約。應用在 `gofmt`、`prettier`、`ruff fix` 這類 formatter 與 fixer 上，契約讓工具能安全地接到 pre-commit hook（重複跑不會累積漂移）、能用 `--check` 跟 `--fix` 共用同一套邏輯（差別只在要不要寫檔）、能分段除錯。

實作上的核心技巧是**每條規則自己冪等**：判斷「違規才修」而非「無論如何都套用」。多規則串成流水線時，每條規則的輸出要是下一條的合法輸入；行數變動時要重建 LineContext 索引。測試可以用「跑兩次結果相等」當斷言，直接驗證契約。

延伸閱讀：[AST 驅動的 idempotent 文字改寫](../09-tooling-and-analysis/ast-idempotent-rewriting/)、[Pre-commit hook 與 CI 整合](../09-tooling-and-analysis/pre-commit-and-ci/)。

### 跨檔案 Link Graph

`跨檔案 link graph` 表示把整個 repo 的檔案視為節點、檔案間連結視為邊的資料結構，用一次 parse 之後的 in-memory map 支援反向查詢（這個目標被誰引用？這個連結的目標存在嗎？）。避免 N² 的「每次查詢都重 parse 全部檔案」成本。

典型應用包含 orphan 偵測（節點沒有 inbound edge）、broken link 偵測（邊指到不存在的節點）、dependency cycle 偵測（graph 有環）、reverse index 建構（哪些檔案引用了 X）。Graph 一次建好後，所有後續 query 都是 map lookup 或 slice scan，microsecond 級。

延伸閱讀：[跨檔案圖分析](../09-tooling-and-analysis/cross-file-graph-analysis/)。

### Tripwire 決策

`tripwire 決策` 表示用事前約定的可量測條件，在命中時觸發「重新評估是否升級」的決策方法。目的是避開「太早升級」（過度工程化）跟「太晚升級」（信譽破產）兩種失敗。

tripwire 的重點是**把評估時機從模糊直覺變成明確觸發**。設計時要選合適的訊號（誤判率、維護成本、使用者投訴頻率），並定期檢驗條件是否仍然合理。適用於技術選型（regex vs AST、Python vs Go）、架構升級（單體 → 微服務）、工具邊界（lint vs full type-check）等決策。

延伸閱讀：[工具決策的 tripwire](../09-tooling-and-analysis/tool-decision-tripwire/)。

### Pre-commit Hook 定位

`pre-commit hook` 表示 git commit 流程中、commit 實際建立前自動觸發的檢查點。定位上它是**快速守門員**，負責秒級可完成的 lint / fmt / 基本驗證，把錯誤攔在本機、讓作者早期回饋。

跟 CI 的分工是：hook 守本機（快、只看 staged 檔案），CI 守共享 branch（慢、乾淨環境、完整 test）。兩者互補、共用同一套工具與規則。落地時要處理 re-staging（hook 自動修檔後 `git add` 回 staged）、exit code 語意（0 = pass、1 = violation block、2 = tool failure）、`--no-verify` 繞過的邊界（原則上禁止，緊急情境有條件例外）。

延伸閱讀：[Pre-commit hook 與 CI 整合](../09-tooling-and-analysis/pre-commit-and-ci/)。

## 使用方式

閱讀章節時若遇到同一個詞在不同情境出現，先回到本頁確認它的核心責任。入門篇會用簡化範例建立語感；進階篇會把同一批詞彙放進並發、WebSocket、資料庫、觀測與部署壓力中重新檢查；工具類章節會把型別、interface、package 等概念落到 CLI、parser、graph analysis 等非服務場景。
