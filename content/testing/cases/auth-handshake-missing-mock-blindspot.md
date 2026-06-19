---
title: "T.C2 Auth handshake 邏輯缺失被 FakeWebSocketChannel 遮蔽"
date: 2026-06-19
description: "ttyd 連線後需要發送 auth token JSON frame 完成認證，整個邏輯未實作 — FakeWebSocketChannel 的 ready 立即完成不需認證，test 永遠看到連線成功"
weight: 2
tags: ["testing", "case-study", "websocket", "mock", "protocol-integration", "authentication"]
---

這個案例的核心責任是說明 mock 如何讓「功能缺失」變得不可見。不同於 T.C1（功能存在但行為錯誤），這個案例是功能根本沒實作 — 因為 mock 不需要這個功能就能通過所有 test。

## 觀察

ttyd WebSocket 協議要求連線建立後發送一個 JSON frame 包含 base64 編碼的帳密（`{"AuthToken":"base64(user:pass)"}`），ttyd 驗證通過後才開始推送 terminal output。app_tunnel 的 `ConnectionManager` 建立 WS 連線後直接開始監聽 stream，沒有發送 auth token。

| 指標                  | 值                                                                         |
| --------------------- | -------------------------------------------------------------------------- |
| 影響範圍              | 連線建立後 ttyd 不推送資料（等 auth token），app 顯示空白終端機            |
| Unit test 結果        | 10 個 ConnectionManager test 全過（`FakeWebSocketChannel.ready` 立即完成） |
| Integration test 結果 | 11 個 connection_flow_test 全過（同樣用 `FakeWebSocketChannel`）           |
| 實機表現              | 連線成功，終端機空白無輸出                                                 |
| 修復                  | 新增 `_sendAuthTokenIfNeeded()` 在 `_establishWebSocket()` 內呼叫          |

## 判讀

1. **Mock 的 happy path 比真實服務寬鬆**。`FakeWebSocketChannel` 的 `ready` 是 `Future.value()`（立即完成），`stream` 是開發者手動控制的 `StreamController`。真實 ttyd 的行為是：`ready` 完成代表 TCP+WS 握手成功，但 stream 要等 auth token 驗證後才有資料。Mock 把兩步合成一步。

2. **Integration test 名為整合實為 fake**。`connection_flow_test.dart` 標題是「端對端整合測試」，但內部使用 `FakeWebSocketChannel` + `FakeBiometricService` + `InMemoryCredentialRepository` — 三個核心依賴全是 fake。這個 test 驗證的是「假設所有外部服務都正常，內部狀態機是否正確」，不是「真實服務互動是否正確」。

3. **功能缺失比功能錯誤更難被 test 抓到**。功能錯誤（T.C1 text vs binary）至少有一個實作可以斷言；功能缺失意味著沒有程式碼可以 test。只有 protocol integration test（對真實服務跑）才能暴露「應該有但沒有」的行為。

## 策略

1. **Protocol integration test 必須涵蓋 auth handshake**：連線 → 發送正確 auth token → 斷言收到 output；連線 → 不發送 auth token → 斷言 timeout 或斷線。
2. **在企劃階段列出協議握手步驟**：ttyd WS 協議的 auth handshake 應該在 spec 文件中明確列出，不依賴開發者記得實作。
3. **區分「名義 integration」和「真實 integration」**：test 名稱含 integration 但全用 fake，應標明 `fake-integration` 或改名 `connection-state-machine-test`。

## 下一步路由

- 想區分 mock 層級 → [模組一：測試策略分層](/testing/)
- 想建 protocol integration test → [模組三：協議整合測試](/testing/)
- 想設計 auth 機制的 UX fallback → [U.C2 biometricOnly 無 fallback](/ux-design/cases/biometric-only-no-fallback/)
