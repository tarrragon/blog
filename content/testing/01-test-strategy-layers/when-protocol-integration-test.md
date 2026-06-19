---
title: "判斷原則：什麼時候需要 protocol integration test"
date: 2026-06-19
description: "從服務架構特徵判斷是否需要 protocol integration test 的決策流程 — 協議複雜度、mock 寬鬆度、失敗靜默度三個維度"
weight: 4
tags: ["testing", "protocol-integration", "decision", "strategy", "mock"]
---

[Protocol integration test](/testing/knowledge-cards/protocol-integration-test/) 有成本 — 需要真實服務實例、環境準備、執行速度較慢、結果可能因環境差異而不穩定。判斷是否需要這一層測試，依據的是服務架構的特徵，而非主觀的「寫多一點比較安心」。

## 三個判斷維度

### 維度一：協議複雜度

程式碼和外部服務之間的協議是否存在 API 層無法描述的語意？

HTTP REST API 的協議複雜度相對低：request body 是 JSON、response body 是 JSON、status code 有明確語意。Mock 一個 REST endpoint（回傳固定 JSON）和真實 endpoint 的行為差異主要在效能和邊界案例，核心語意差距小。

WebSocket 協議的複雜度較高：連線握手、frame type（text / binary / ping / pong / close）、分片（fragmentation）、壓縮擴展（permessage-deflate）、子協議協商 — 這些語意在 API 層（`sink.add(dynamic)`）是不可見的。gRPC 的 streaming、deadline propagation、metadata header 也有類似特徵。

判斷問題：**API 簽名是否隱藏了協議層的行為分支？** 如果 API 用 `dynamic`、`Object`、`Any` 等寬泛型別接受輸入，而協議層對不同輸入有不同處理方式，這就是需要 protocol integration test 的訊號。

app_tunnel 的 `sink.add(dynamic)` 就是這個模式 — API 簽名不區分 `String` 和 `Uint8List`，但協議層對兩者產生不同的 frame type（[T.C1](/testing/cases/ws-text-binary-frame-mock-blindspot/)）。

### 維度二：Mock 寬鬆度

Mock 的行為是否比真實服務更寬容？

Mock 通常是「最小可用」的實作 — 能讓 test 通過就好。這意味著 mock 的行為往往比真實服務寬鬆：不檢查認證、不限制速率、不要求特定順序、不區分輸入格式。

寬鬆本身不是問題，但寬鬆程度和真實服務的差距決定了 mock 遮蔽的風險大小。判斷問題：**Mock 跳過了真實服務的哪些步驟？每個被跳過的步驟在業務上是否關鍵？**

app_tunnel 的 `FakeWebSocketChannel` 跳過了 auth handshake — `ready` 立即完成不需認證。Auth handshake 在業務上是關鍵步驟（沒有認證，ttyd 不推送資料），mock 跳過這一步讓「功能根本沒實作」變得不可見（[T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/)）。

逐項列出 mock 跳過的步驟是一個實用的 audit 方法。寫出「`FakeWebSocketChannel` 和 `IOWebSocketChannel` 的行為差異清單」，每一個差異點就是潛在的遮蔽風險。

### 維度三：失敗靜默度

外部服務收到非預期輸入時，回應是明確的錯誤還是靜默忽略？

如果外部服務對錯誤輸入回傳 HTTP 400 或斷線，問題在實機測試時會快速浮現 — 程式碼進入 error 狀態，開發者看到明確的錯誤訊息。但如果外部服務靜默忽略，問題表現為「連線成功但沒有回應」，debug 方向可能完全錯誤。

ttyd 收到 binary frame 時靜默忽略，不回傳錯誤碼也不斷線。這讓問題的表現從「frame type 錯誤」變成「終端機無回應」，開發者的 debug 方向是「為什麼 terminal 沒反應」而非「為什麼 frame type 不對」。

判斷問題：**外部服務是否有靜默忽略的行為？** 如果有，protocol integration test 的價值更高 — 因為即使在實機測試階段，靜默忽略也會增加 debug 成本。

## 決策流程

以下流程不追求完備覆蓋所有情境，而是提供一個起點，根據上述三個維度的組合判斷 protocol integration test 的必要性。

**協議複雜度高（API 層和協議層有語意斷裂）：** 需要 protocol integration test。即使 mock 寬鬆度低、失敗回報明確，語意斷裂本身就是 mock 結構性無法覆蓋的盲區。

**協議複雜度低，但 mock 寬鬆度高（mock 跳過業務關鍵步驟）：** 需要 protocol integration test。Mock 跳過的步驟越多，「功能缺失不可見」的風險越大。

**協議複雜度低，mock 寬鬆度低：** 依失敗靜默度判斷。如果外部服務靜默忽略錯誤，protocol integration test 有較高價值；如果錯誤回報明確，可以依賴實機測試階段的 error 來發現問題。

**成本極低的情境：** 當外部服務可以在 test 環境輕鬆啟動時（自用工具 server+client 同機、Docker 一行啟動的 open source service），protocol integration test 的成本門檻大幅降低，三個維度中任何一個有疑慮就值得寫。

## 下一步路由

- 想實作 protocol integration test → [模組三：協議整合測試](/testing/03-protocol-integration-test/)
- 理解 mock 遮蔽的結構性原因 → [Mock 遮蔽機制分析](/testing/01-test-strategy-layers/mock-masking-mechanism/)
- 反模式：試圖用更多 mock test 補救 → [反模式：用 mock 數量彌補 mock 盲區](/testing/01-test-strategy-layers/anti-pattern-mock-quantity/)
