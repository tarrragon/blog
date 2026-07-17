---
title: "WebSocket 協議測試實作"
date: 2026-06-19
description: "對真實 ttyd 驗證 frame type 和 auth handshake — 從 T.C1 和 T.C2 的教訓推導出的 protocol integration test 設計"
weight: 2
tags: ["testing", "integration-test", "websocket", "protocol", "ttyd"]
---

WebSocket 協議測試的目標是驗證 client 端的 WebSocket 操作在真實服務上的行為。這個層級的 test 直接使用 `IOWebSocketChannel`（真實實作）連線到真實 ttyd 服務，不用 `FakeWebSocketChannel`。

## 要驗證什麼

從 T.C1 和 T.C2 的案例推導出 WebSocket protocol test 至少需要覆蓋的場景：

### Frame type 驗證

`IOWebSocketChannel` 對 `String` 和 `Uint8List` 產生不同的 frame type（text vs binary）。ttyd 只接受 text frame，收到 binary frame 靜默忽略（[T.C1](/testing/cases/ws-text-binary-frame-mock-blindspot/)）。

Protocol test 需要驗證：

- 發送 `String` → ttyd 回應（text frame 被處理）
- 發送 `Uint8List` → ttyd 不回應（binary frame 被忽略）
- 確認 `sendData()` 函式實際發送的是 text frame

### Auth handshake 驗證

ttyd 連線後需要發送 auth token JSON frame 完成認證，認證通過後才推送 terminal output（[T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/)）。

Protocol test 需要驗證：

- 連線後發送正確的 auth token → 收到 terminal output
- 連線後不發送 auth token → 逾時無 output
- 連線後發送錯誤的 auth token → 連線被斷開或無 output

### 連線生命週期驗證

WebSocket 連線的建立、維持、斷開在 mock 環境中都是瞬間完成的。真實環境中有延遲、可能失敗、可能逾時。

Protocol test 需要驗證：

- 連線建立的成功路徑（TCP → WS 升級 → ready）
- 連線逾時的行為（server 不可達時 client 的回應）
- 連線斷開後的狀態（stream 是否正確關閉）

## Test 結構

```text
setUp: 啟動本機 ttyd（Process.start('ttyd', ['bash'])）
tearDown: 停止 ttyd（process.kill()）

test('text frame is accepted by ttyd'):
  channel = IOWebSocketChannel.connect('ws://localhost:7681/ws')
  await channel.ready
  channel.sink.add('{"AuthToken":"base64(user:pass)"}')
  channel.sink.add('echo hello')  // String → text frame
  output = await channel.stream.first.timeout(5s)
  expect(output, contains('hello'))

test('binary frame is silently ignored by ttyd'):
  channel = IOWebSocketChannel.connect(...)
  await channel.ready
  channel.sink.add('{"AuthToken":"..."}')
  channel.sink.add(Uint8List.fromList(utf8.encode('echo hello')))
  expect(channel.stream.first.timeout(2s), throwsTimeoutException)

test('auth token required before output'):
  channel = IOWebSocketChannel.connect(...)
  await channel.ready
  // 不發 auth token，直接發指令
  channel.sink.add('echo hello')
  expect(channel.stream.first.timeout(2s), throwsTimeoutException)
```

## 執行成本

一個遠端終端機 app 的 server（ttyd）和 client 在同一台機器上。啟動 ttyd 是一行指令（`ttyd bash`），不需要 Docker、不需要雲端服務、不需要網路。整個 test suite 的執行時間主要是連線建立和逾時等待，每個 test case 約 2-5 秒。

這個低成本是自用工具的結構優勢 — server 可以在 test 的 setUp 中啟動、tearDown 中停止，不需要共享的 test 環境（本章合成，TF-8 Derive）。

## 下一步路由

- HTTP 的 contract test 設計 → [HTTP contract test 設計](/testing/03-protocol-integration-test/http-contract-test/)
- CI 中的服務管理 → [CI 中的服務 fixture 管理](/testing/03-protocol-integration-test/service-fixture-management/)
- 什麼時候值得寫 protocol integration test → [成本判斷表](/testing/03-protocol-integration-test/cost-judgment/)
