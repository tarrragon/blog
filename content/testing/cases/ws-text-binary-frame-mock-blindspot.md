---
title: "T.C1 WebSocket text/binary frame 被 FakeWebSocketChannel 遮蔽"
date: 2026-06-19
description: "Flutter app 用 Uint8List 發送 WS 資料走 binary frame，ttyd 期望 text frame 靜默忽略 — FakeWebSocketChannel 的 sink.add 接受 dynamic 不區分 frame type，192 個 test 全過但實機無回應"
weight: 1
tags: ["testing", "case-study", "websocket", "mock", "protocol-integration", "flutter"]
---

這個案例的核心責任是說明 mock 的「API 層級模擬」和真實服務的「協議層級行為」之間的結構性斷裂。WebSocket 的 text frame（opcode 0x1）和 binary frame（opcode 0x2）在 Dart API 層面都是 `sink.add(dynamic)`，但在協議層是不同的 opcode，ttyd 只接受 text frame。

## 觀察

app_tunnel Flutter app 連接 ttyd WebSocket 終端機。`ConnectionManager.sendData()` 接收 `Uint8List` 型別的鍵盤輸入，直接傳給 `_channel!.sink.add(data)`。Dart 的 `IOWebSocketChannel` 對 `Uint8List` 發送 binary frame（opcode 0x2），ttyd 期望 text frame（opcode 0x1），收到 binary frame 靜默忽略。

| 指標           | 值                                                            |
| -------------- | ------------------------------------------------------------- |
| 影響範圍       | 所有鍵盤輸入無效（使用者打字無回應）                          |
| Unit test 結果 | 192 個全過（`FakeWebSocketChannel.sink.add` 不區分型別）      |
| 實機表現       | 連線成功但終端機完全無反應                                    |
| 修復           | `if (data is Uint8List) sink.add(String.fromCharCodes(data))` |

## 判讀

1. **Mock 模擬的是 Dart API 契約，不是 WebSocket 協議契約**。`FakeWebSocketChannel` 忠實實作了 `WebSocketChannel` 的 Dart interface — `sink.add(dynamic)` 接受任何型別。但 `IOWebSocketChannel` 的 `sink.add` 實際行為是：`String` → text frame，`List<int>` / `Uint8List` → binary frame。Mock 沒有也不應該模擬這個協議層行為。

2. **ttyd 的靜默忽略放大了問題**。如果 ttyd 對 binary frame 回傳錯誤碼或斷線，app 至少會進入 error 狀態讓開發者察覺。靜默忽略讓問題從「連線失敗」變成「連線成功但無回應」，debug 方向完全錯誤。

3. **型別系統幫不上忙**。Dart 的 `WebSocketSink.add` 簽名是 `void add(dynamic event)` — `dynamic` 吃掉了型別資訊。即使用強型別語言，如果 API 設計成 `dynamic`，型別檢查無法區分協議語意。

## 策略

1. **Protocol integration test**：對真實 ttyd 發送 `Uint8List` 和 `String`，斷言兩者行為差異。一個 5 行 test 就能抓到這個問題。
2. **在 sendData 層做型別轉換**：不依賴下游 channel 的行為，在自己的 API 邊界確保型別正確。
3. **Log 送出的 frame type**：`developer.log('WS send: type=${data.runtimeType}')` 讓 debug 時立即可見。

## 下一步路由

- 想寫 protocol integration test → [模組三：協議整合測試](/testing/03-protocol-integration-test/)
- 想理解 mock 遮蔽的系統性機制 → [Mock 遮蔽機制分析](/testing/01-test-strategy-layers/mock-masking-mechanism/)
- 類似案例（auth handshake） → [T.C2 Auth handshake 缺失](/testing/cases/auth-handshake-missing-mock-blindspot/)
