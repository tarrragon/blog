---
title: "Protocol integration test 定義"
date: 2026-06-19
description: "Protocol integration test 和 unit test / E2E test 的邊界 — 驗證程式碼和真實服務的協議契約，不驗證 UI 也不用 mock"
weight: 1
tags: ["testing", "integration-test", "protocol", "definition", "boundary"]
---

Protocol integration test 驗證的是程式碼和真實外部服務之間的協議互動 — 連線方式、認證流程、資料編碼、回應格式。它和 unit test 的差別是不用 mock，和 E2E test 的差別是不經過 UI。

## 三種 test 的邊界

### Unit test

驗證程式碼邏輯。外部依賴全部用 mock 替代。斷言對象是函式的回傳值、狀態變化、例外拋出。

Unit test 無法驗證的：程式碼和真實外部服務之間的行為差異（mock 遮蔽了這些差異，見 [Mock 遮蔽機制分析](/testing/01-test-strategy-layers/mock-masking-mechanism/)）。

### Protocol integration test

驗證程式碼和真實服務的協議互動。不用 mock — 對真實的服務實例發送請求、觀察真實的回應。不經過 UI — 直接呼叫 client 端的連線函式或 HTTP client。

Protocol integration test 驗證的是：連線能否建立、認證流程是否正確、發送的資料格式是否被接受、回應是否符合預期。

### E2E test

驗證完整的使用者操作流程。從 UI 操作開始（點擊按鈕），經過 client 端邏輯，到達真實服務，再回到 UI 顯示結果。

E2E test 的覆蓋範圍最廣但成本最高 — 需要啟動 app、操作 UI、等待網路回應、斷言 UI 狀態。E2E test 通常執行慢、不穩定（UI 動畫、網路延遲、裝置狀態影響結果）。

## Protocol integration test 的定位

Protocol integration test 填補 unit test 和 E2E test 之間的空隙。Unit test 覆蓋程式碼邏輯，E2E test 覆蓋端到端流程，protocol integration test 覆蓋「程式碼和外部服務的互動」這個特定層。

這一層的 test 用程式碼直接呼叫 client 端的連線函式（跳過 UI），對真實的服務實例執行操作（跳過 mock），然後斷言服務的回應是否符合協議規格。

以 app_tunnel 為例，一個 protocol integration test 的結構：

```text
1. 啟動本機 ttyd 服務
2. 用 IOWebSocketChannel 連線到 ttyd
3. 發送 auth token JSON frame
4. 斷言收到 terminal output
5. 發送 Uint8List 鍵盤輸入
6. 斷言 ttyd 沒有回應（binary frame 被忽略）
7. 發送 String 鍵盤輸入
8. 斷言 ttyd 有回應（text frame 被處理）
```

這個 test 不需要 Flutter UI、不需要 FakeWebSocketChannel，直接驗證「我的程式碼送出的資料，真實 ttyd 是否正確處理」。

## 下一步路由

- WebSocket 的 protocol test 實作 → [WebSocket 協議測試實作](/testing/03-protocol-integration-test/websocket-protocol-test/)
- 什麼時候值得寫 protocol integration test → [成本判斷表](/testing/03-protocol-integration-test/cost-judgment/)
- Protocol integration test 和 mock test 的關係 → [testing 模組一 測試策略分層](/testing/01-test-strategy-layers/)
