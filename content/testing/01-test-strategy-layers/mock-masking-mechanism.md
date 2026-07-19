---
title: "Mock 遮蔽機制分析"
date: 2026-06-19
description: "Mock 在 API 層、協議層、環境層之間製造的結構性盲區 — 斷裂點在哪、為什麼 mock 無法也不應該模擬協議行為"
weight: 2
tags: ["testing", "mock", "protocol", "api-contract", "blindspot"]
---

[Mock 遮蔽](/testing/knowledge-cards/mock-masking/)是 mock 的設計邊界。「遮蔽」描述的是機制 — mock 讓協議層差異變得不可見；「盲區」描述的是結果 — 被遮蔽的範圍形成結構性的驗證缺口。Mock 的職責是模擬程式語言層面的 API 契約 — 方法簽名、參數型別、回傳值結構。協議層行為（frame type、handshake 步驟、編碼格式）不在 API 契約的描述範圍內，mock 沒有模擬這些行為的義務，也不應該被期待模擬。

## 三層語意與斷裂點

程式碼和外部服務之間的互動經過三層語意轉換，每一層描述不同粒度的行為。Mock 模擬的是最上層，真實行為發生在下面兩層。

### API 層：程式語言的方法簽名

API 層描述的是「這個方法接受什麼參數、回傳什麼型別」。Dart 的 `WebSocketSink.add` 簽名是 `void add(dynamic event)` — 從 API 層看，傳 `String` 和傳 `Uint8List` 都合法，都不會拋出例外。

`FakeWebSocketChannel` 忠實實作了這個 API 契約。`sink.add("hello")` 和 `sink.add(Uint8List.fromList([104, 101, 108, 108, 111]))` 在 fake 的行為完全相同 — 資料進入內部 buffer，test 可以從 buffer 讀取驗證。Mock 的行為在 API 層是正確的。

### 協議層：通訊標準的語意規則

協議層描述的是「這個資料在網路上如何被編碼、對方如何解讀」。WebSocket 協議（RFC 6455）定義 text frame 用 opcode 0x1、binary frame 用 opcode 0x2 — 兩者語意不同，接收端可以選擇只處理其中一種。

Dart 的 `IOWebSocketChannel`（真實實作）根據 `sink.add` 的參數型別決定 frame type：`String` 產生 text frame，`List<int>` 或 `Uint8List` 產生 binary frame。這個行為是 `IOWebSocketChannel` 的實作細節，不是 `WebSocketSink` 介面契約的一部分 — API 簽名用 `dynamic` 把型別資訊抹除了（[T.C1](/testing/cases/ws-text-binary-frame-mock-blindspot/)）。

ttyd 只接受 text frame，收到 binary frame 靜默忽略。從 API 層看，`sink.add(Uint8List(...))` 合法；從協議層看，這產生了 ttyd 不處理的 binary frame。斷裂點在 API 層和協議層之間 — mock 模擬了前者，但後者的語意差異只有真實 `IOWebSocketChannel` + 真實 ttyd 才會浮現。

同構的斷裂點也出現在瀏覽器擴充功能的訊息通道：Manifest V3 把「listener 回傳 Promise」解讀為認領回應權 — 這是通道層語意，mock 掉 `chrome.runtime` 的單元測試看不到，「提取成功被誤報失敗」的事故只有跨 context 的端對端測試才會現形（[U.C9](/ux-design/cases/async-listener-false-failure/)）。

### 環境層：執行環境的行為差異

環境層描述的是「同一段程式碼在不同執行環境下行為不同」。DNS 解析、TLS 憑證驗證、防火牆規則、作業系統的 socket 實作 — 這些在 test 環境可能和 production 不同。

環境層的遮蔽比協議層更難處理，因為即使用真實服務做 protocol integration test，test 環境和 production 環境仍可能有差異。本模組不深入環境層議題。

## 遮蔽的兩種模式

Mock 遮蔽在實務上有兩種不同的表現，需要不同的偵測策略。

### 模式一：功能存在但行為錯誤

程式碼有對應的實作，但實作的行為和真實服務期望的行為不一致。Mock 讓這個不一致變得不可見，因為 mock 接受了實際上外部服務不會接受的輸入。

T.C1 就是這種模式。`sendData()` 實作了「發送鍵盤輸入」的功能，但發送的是 binary frame 而非 text frame。Mock 的 `sink.add(dynamic)` 接受 `Uint8List` 不報錯，真實 ttyd 靜默忽略 binary frame。功能存在，行為錯誤，mock 遮蔽了錯誤。

這種模式的偵測策略是 protocol integration test — 對真實服務發送相同輸入，比對回應是否符合預期。

### 模式二：功能根本沒實作

程式碼缺少應有的功能步驟，但 mock 不需要這個步驟就能進入成功狀態。Mock 把多步驟的協議流程簡化成單步操作，讓開發者不知道還有缺少的步驟。

T.C2 就是這種模式。ttyd 要求連線後發送 auth token，但 `ConnectionManager` 沒有實作這個步驟。`FakeWebSocketChannel.ready` 立即完成不需認證，`stream` 由開發者手動控制，不依賴 auth 狀態。Mock 把「TCP 握手 → WS 握手 → auth token → 驗證通過 → 推送資料」這個多步驟流程簡化成「`ready` 完成 → `stream` 有資料」（[T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/)）。

功能缺失比功能錯誤更難被偵測。功能錯誤至少有一段程式碼可以被 test 覆蓋（只是斷言的對象不夠深）；功能缺失意味著沒有程式碼可以寫 test。只有 protocol integration test 對真實服務跑完整流程，才能暴露「應該有但沒有」的步驟。

## Mock 不應該模擬協議行為

面對 mock 遮蔽的第一個直覺反應通常是「讓 mock 更逼真」— 在 `FakeWebSocketChannel` 裡加入 frame type 區分、auth handshake 驗證等邏輯。這個方向有結構性問題。

Mock 的價值在於簡化 — 把複雜的外部依賴替換成行為可預測的替身，讓 unit test 專注在程式碼邏輯。如果 mock 開始模擬協議行為，mock 本身變成需要維護和驗證的複雜元件。Mock 的正確性由誰保證？如果外部服務更新了協議版本，誰負責更新 mock？

更根本的問題是：即使 mock 完美複製了當前版本的協議行為，它仍然是開發者對協議的理解的副本，不是協議本身。如果開發者對協議的理解就有偏差（例如不知道 ttyd 需要 auth token），mock 會忠實複製這個偏差。

正確的分工是：mock 負責 API 層，protocol integration test 負責協議層。每一層用正確的工具驗證。

這條界線針對協議層。業務行為層存在一種紀律化的例外：[語意級假後端](/testing/01-test-strategy-layers/semantic-fake-backend/)。分界在兩條：第一，模擬止於應用層行為（後端動詞的效果：建立、釋放、狀態轉換），協議層仍歸 protocol integration test；第二，每條行為有實測出處，不是開發者理解的副本，且配對的真實後端驗證測試承擔行為漂移的警報。兩條缺一，它就退化成本章批評的對象。

## 下一步路由

- 如何辨認偽裝成 integration test 的 mock test → [名義 integration test 的識別與修正](/testing/01-test-strategy-layers/nominal-integration-test/)
- 判斷自己的服務是否存在這種斷裂 → [判斷原則：什麼時候需要 protocol integration test](/testing/01-test-strategy-layers/when-protocol-integration-test/)
- 想看 SDK 自動攔截如何影響 mock 遮蔽 → [monitoring 模組三 SDK 設計](/monitoring/03-sdk-design/)
