---
title: "192 個測試全過、實機全壞：Mock 遮蔽真實行為的三層測試策略"
date: 2026-06-19
draft: false
description: "unit test 全綠、實機部署後功能卻整片壞掉時回來看。揭露 mock-only 策略的結構盲區（text vs binary frame、缺 auth handshake、ANSI 控制序列多樣性都被 FakeWebSocketChannel 遮蔽），提出 unit / protocol-integration / screen-state 三層各抓什麼、各遮蔽什麼。"
tags: ["testing", "flutter", "websocket", "integration-test", "mock", "ttyd"]
---

## 這篇要解決什麼

**192 個 unit test 全綠、實機部署後全部功能壞掉。**

這不是測試寫得差 — 每個 test 都有明確斷言、覆蓋了正常和錯誤路徑。問題出在測試策略的結構：所有 test 都用 `FakeWebSocketChannel` 替代真實 WebSocket，永遠不會觸碰真實協議行為。結果是 mock 和真實服務之間的差異，在整個測試套件中完全不可見。

本文拆解三個被 mock 遮蔽的真實問題、分析 mock 遮蔽的機制、提出三層測試策略作為防護。

---

## 三個被 Mock 遮蔽的真實問題

### 問題 1：text frame vs binary frame

ttyd 的 WebSocket 協議期望 **text frame**，Flutter 的 `WebSocketChannel.sink.add(Uint8List)` 預設發送 **binary frame**。兩者在 WebSocket 協議層是不同的 opcode（0x1 text vs 0x2 binary），ttyd 收到 binary frame 會靜默忽略。

```dart
// 原始寫法 — Uint8List 走 binary frame，ttyd 靜默忽略
void sendData(dynamic data) {
  _channel!.sink.add(data); // data 是 Uint8List → binary frame
}

// 修正 — 轉成 String 走 text frame
void sendData(dynamic data) {
  if (data is Uint8List) {
    _channel!.sink.add(String.fromCharCodes(data)); // text frame
  } else {
    _channel!.sink.add(data);
  }
}
```

**為什麼 mock 抓不到**：`FakeWebSocketChannel` 的 `sink.add` 接受 `dynamic`，不區分 `String` 和 `Uint8List`，兩者都直接存入 `_sinkItems` list。Mock 層沒有 frame type 的概念 — 它模擬的是 Dart API，不是 WebSocket 協議。

### 問題 2：auth token handshake 缺失

ttyd 連線後需要發送一個 auth token JSON frame 完成認證，否則 ttyd 關閉連線。整個 auth handshake 的邏輯根本沒實作，因為 `FakeWebSocketChannel` 不需要認證就能「連線成功」。

```dart
// 缺失的 auth handshake — 連線建立後需發送
void _sendAuthTokenIfNeeded(Credential credential) {
  final token = base64Encode(
    utf8.encode('${credential.ttydUser}:${credential.ttydPass}'),
  );
  final frame = _protocol.buildAuthTokenFrame(authToken: token);
  if (frame != null) {
    _channel!.sink.add(frame);
  }
}
```

**為什麼 mock 抓不到**：`FakeWebSocketChannel` 的 `ready` 立即完成、`stream` 立即可用。真實 ttyd 需要收到正確的 auth token 才會開始推送 terminal output；mock 不需要，所以 test 永遠看到「連線成功」。

### 問題 3：ANSI 控制序列多樣性

真實 shell 輸出包含 OSC 序列（`ESC]...BEL` 終端機標題設定）、CSI private mode（`ESC[?...h/l` 游標隱藏、括號貼上模式）等控制序列。ANSI parser 只處理基本 SGR 色彩碼，其他序列全部殘留在輸出中顯示為亂碼。

**為什麼 mock 抓不到**：test 的輸入資料是手寫的乾淨 ANSI 字串（如 `\x1B[31mred\x1B[0m`），不包含真實 shell 會產生的 OSC/CSI private mode 序列。真實 zsh prompt 一打開就送幾十種控制序列，但 test data 是人工挑選的乾淨子集。

---

## Mock 遮蔽的機制

三個問題有共同的結構：

| 問題                 | Mock 模擬的層級                | 真實差異存在的層級       |
| -------------------- | ------------------------------ | ------------------------ |
| text vs binary frame | Dart API（`sink.add`）         | WebSocket 協議（opcode） |
| auth handshake       | 連線生命週期（`ready` future） | 應用層協議（ttyd 握手）  |
| ANSI 多樣性          | 輸入資料（手寫測試字串）       | 真實環境（shell output） |

**共同模式**：mock 忠實模擬了 Dart API 的行為契約，但 Dart API 和真實服務之間還有一層協議語意（WebSocket frame type、ttyd auth handshake、shell 完整輸出），mock 把這層完全跳過了。

**這不是 mock 的缺陷，而是 mock 的本質**。Mock 的職責是讓 unit test 快速、確定性、不依賴外部服務。但當被測元件的正確性取決於「與外部服務的協議契約」時，mock 從結構上就無法驗證這件事。

---

## 三層測試策略

| 層                              | 職責           | 驗證什麼                               | 抓不到什麼                         |
| ------------------------------- | -------------- | -------------------------------------- | ---------------------------------- |
| **Unit（mock）**                | 內部邏輯正確性 | 狀態轉換、錯誤處理、資料轉換           | 協議差異、真實服務行為、環境特異性 |
| **Protocol integration**        | 協議契約正確性 | frame type、auth handshake、序列完整性 | UI 互動、畫面渲染、用戶體驗        |
| **Screen state（widget test）** | UI 行為正確性  | 狀態轉換 UI、導航、用戶操作            | 底層協議、網路行為                 |

### Unit test（已有，保留）

用 `FakeWebSocketChannel` 驗證 `ConnectionManager` 的狀態機：idle → connecting → connected → disconnected，錯誤處理路徑（biometric 失敗、credential 缺失、timeout）。192 個 test 全部保留。

### Protocol integration test（新增）

**對真實 ttyd + proxy 驗證 WebSocket 協議契約。** 這一層的關鍵是：不用 mock，直接連真實服務。

```dart
// 概念示例 — 對真實 ttyd 驗證協議
test('auth token handshake succeeds against real ttyd', () async {
  // 前提：本機 ttyd 已啟動（test fixture 或 CI 腳本啟動）
  final channel = IOWebSocketChannel.connect(
    Uri.parse('ws://127.0.0.1:7681/ws'),
    protocols: ['tty'],
  );
  await channel.ready;

  // 發送 auth token
  final token = base64Encode(utf8.encode('testuser:testpass'));
  channel.sink.add('{"AuthToken":"$token"}');

  // 驗證收到 terminal output（text frame，prefix '0'）
  final firstFrame = await channel.stream.first;
  expect(firstFrame, isA<String>()); // text frame, not binary
  expect(firstFrame[0], '0');        // ttyd output prefix
});
```

**為什麼這層成本低**：ttyd 和 proxy 都在本機，`ttyd --port 7681 --credential "test:test" /bin/echo hello` 一行就能啟動一個最小測試服務。CI 腳本先啟動 ttyd → 跑 Dart integration test → 停止 ttyd。不需要模擬器、不需要真實手機。

### Screen state test（補強）

Widget test 覆蓋所有畫面狀態的 UI 行為：每個狀態顯示什麼 widget、哪些按鈕可按、按了之後導航到哪裡。這層已有 7 個 test，但不覆蓋 back 按鈕和 text input。

---

## 判斷原則：什麼時候需要 protocol integration test

不是所有專案都需要三層。判斷標準：

| 條件                                       | 需要 protocol integration test |
| ------------------------------------------ | ------------------------------ |
| 被測元件直接對接外部協議（WS、gRPC、SMTP） | 是                             |
| Mock 和真實服務之間有協議語意差異          | 是                             |
| 外部服務可在本機啟動（成本低）             | 強烈建議                       |
| 被測元件只做資料轉換（不碰網路）           | 不需要                         |
| 外部服務只能在雲端啟動（成本高）           | 用 contract test 替代          |

**app_tunnel 的特殊優勢**：server 和 client 都在同一台機器上。啟動 ttyd + proxy 然後跑 Dart test，成本極低但價值極高 — 三個實機問題中的兩個（text/binary frame、auth handshake）都能在這層直接抓到。

---

## 反模式：用 mock 數量彌補 mock 盲區

「192 個 test 全過」給了虛假的信心。常見的反應是「測試不夠多」然後再加更多 mock test，但問題不在數量 — 300 個用同一個 `FakeWebSocketChannel` 的 test 仍然抓不到 text vs binary frame。

**測試策略的品質不是用數量衡量、而是用層級覆蓋衡量。** 一個對真實 ttyd 的 5 行 protocol test，比 50 個新增的 mock test 更能防止實機部署失敗。

## 延伸閱讀

本文的觀察和判讀在 [Testing 測試策略](/testing/) 教學系列中展開為系統性的教學模組：[三層定義與職責表](/testing/01-test-strategy-layers/three-layer-definition/)、[Mock 遮蔽機制分析](/testing/01-test-strategy-layers/mock-masking-mechanism/)、[Protocol integration test](/testing/03-protocol-integration-test/)。
